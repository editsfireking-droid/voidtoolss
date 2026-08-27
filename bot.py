import os
import json
import re
import asyncio
from pathlib import Path
TOKEN = os.environ.get('TOKEN')
    bot.run(TOKEN)
import discord
from discord.ext import commands, tasks
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.json not found")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()
TOKEN = os.getenv("DISCORD_TOKEN") or CONFIG.get("bot_token", "")
PREFIXES = CONFIG.get("prefixes", ["$", "!"])
GUILD_ID = int(CONFIG.get("guild_id", 0) or 0)
LOGO_URL = CONFIG.get("logo_url", "")
REQUIRED_STATUS = CONFIG.get(
    "free_tools_required_text",
    "discord.gg/CdHc6Vk6jZ | Free Tools",
)
SERVER_INVITE = CONFIG.get("server_invite", "https://discord.gg/CdHc6Vk6jZ")


def id_value(name):
    value = CONFIG.get(name, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


WELCOME_CHANNEL_ID = id_value("welcome_channel_id")
REVIEWS_CHANNEL_ID = id_value("reviews_channel_id")
REQUESTS_CHANNEL_ID = id_value("requests_channel_id")
PURCHASE_CHANNEL_ID = id_value("purchase_channel_id")
TICKET_CATEGORY_ID = id_value("ticket_category_id")
SUPPORT_STAFF_ROLE_ID = id_value("support_staff_role_id")
PURCHASE_STAFF_ROLE_ID = id_value("purchase_staff_role_id")
VERIFIED_ROLE_ID = id_value("verified_role_id")
FREE_TOOLS_ROLE_ID = id_value("free_tools_role_id")


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True


class VoidToolsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(*PREFIXES),
            intents=intents,
            help_command=None,
        )
        self.synced_once = False

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"[SYNC] Synced {len(synced)} slash commands to guild {GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            print(f"[SYNC] Synced {len(synced)} global slash commands.")
        self.free_tools_checker.start()

    async def on_ready(self):
        print(f"[ONLINE] Logged in as {self.user} ({self.user.id})")

    @tasks.loop(minutes=2)
    async def free_tools_checker(self):
        if not GUILD_ID or not FREE_TOOLS_ROLE_ID:
            return
        guild = self.get_guild(GUILD_ID)
        if guild is None:
            return
        role = guild.get_role(FREE_TOOLS_ROLE_ID)
        if role is None:
            return
        for member in guild.members:
            if member.bot or role not in member.roles:
                continue
            if not has_required_status(member):
                try:
                    await member.remove_roles(role, reason="Free Tools status requirement removed")
                except discord.HTTPException:
                    pass

    @free_tools_checker.before_loop
    async def before_free_tools_checker(self):
        await self.wait_until_ready()


bot = VoidToolsBot()


def make_embed(title, description, footer=None):
    color = CONFIG.get("embed_color", "#FFFFFF")
    try:
        color_value = int(str(color).replace("#", ""), 16)
    except ValueError:
        color_value = 0xFFFFFF
    embed = discord.Embed(title=title, description=description, color=color_value)
    if footer:
        embed.set_footer(text=footer)
    elif CONFIG.get("welcome_footer"):
        embed.set_footer(text=CONFIG["welcome_footer"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    return embed


def get_custom_statuses(member: discord.Member):
    statuses = []
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            text = activity.name or ""
            if text:
                statuses.append(text)
    return statuses


def has_required_status(member: discord.Member):
    required = REQUIRED_STATUS.casefold()
    return any(required in status.casefold() for status in get_custom_statuses(member))


def has_role(member, role_id):
    return role_id and any(role.id == role_id for role in member.roles)


def mention_or_text(member):
    return member.mention if member else "Unknown user"


def parse_duration(duration: str):
    match = re.fullmatch(r"\s*(\d+)\s*(s|m|h|d|w)\s*", duration.lower())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    seconds = value * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
    if seconds < 1 or seconds > 28 * 86400:
        return None
    return seconds


def is_admin(interaction: discord.Interaction):
    return isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator


def admin_check():
    async def predicate(interaction: discord.Interaction):
        if is_admin(interaction):
            return True
        raise app_commands.CheckFailure("Administrator permission required.")
    return app_commands.check(predicate)


@bot.event
async def on_member_join(member: discord.Member):
    if not WELCOME_CHANNEL_ID:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        return
    embed = make_embed(
        f"Welcome to Void Tools, {member.display_name}!",
        f"Welcome {member.mention}!\n\nExplore the server for free tools, methods, source code and more.\n\n**Server:** {SERVER_INVITE}",
        CONFIG.get("welcome_footer", "Void Tools • Free Methods & Tools"),
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_image(url=member.display_avatar.url)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    message = str(error)
    if isinstance(error, app_commands.CheckFailure):
        message = "You need Administrator permission to use this command."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "I don't have the required Discord permissions for that."
    elif isinstance(error, app_commands.CommandInvokeError):
        print(f"[COMMAND ERROR] {error.original!r}")
        message = "Something went wrong while running that command. Check the bot logs."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="embedcreate", description="Create and send a custom embed.")
@app_commands.describe(header="Embed header/title", text="Embed description", footer="Embed footer")
@admin_check()
async def embedcreate(interaction: discord.Interaction, header: str, text: str, footer: str):
    embed = make_embed(header, text, footer)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stfu", description="Timeout a member.")
@app_commands.describe(user="Member to timeout", duration="Examples: 10m, 1h, 1d", reason="Reason")
@admin_check()
async def stfu(interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No reason provided"):
    seconds = parse_duration(duration)
    if seconds is None:
        await interaction.response.send_message("Invalid duration. Use values such as `10m`, `1h`, `1d`, or `1w` (max 28d).", ephemeral=True)
        return
    if user == interaction.user:
        await interaction.response.send_message("You can't timeout yourself with this command.", ephemeral=True)
        return
    try:
        await user.timeout(discord.utils.utcnow() + discord.timedelta(seconds=seconds), reason=reason)
    except AttributeError:
        await user.timeout(discord.utils.utcnow() + __import__('datetime').timedelta(seconds=seconds), reason=reason)
    except discord.Forbidden:
        await interaction.response.send_message("I can't timeout that member. Check my role position and Moderate Members permission.", ephemeral=True)
        return
    await interaction.response.send_message(f"🔇 Timed out {user.mention} for `{duration}`.\n**Reason:** {reason}")


@bot.command(name="gtfo")
@commands.has_guild_permissions(administrator=True)
async def gtfo(ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
    try:
        await user.ban(reason=reason, delete_message_days=0)
    except discord.Forbidden:
        await ctx.send("I can't ban that member. Check my Ban Members permission and role position.")
        return
    await ctx.send(f"🔨 Banned {user.mention}.\n**Reason:** {reason}")


@bot.command(name="tpanel")
@commands.has_guild_permissions(administrator=True)
async def tpanel(ctx: commands.Context):
    if not PURCHASE_CHANNEL_ID:
        await ctx.send("Set `purchase_channel_id` in config.json first.", delete_after=10)
        return
    channel = ctx.guild.get_channel(PURCHASE_CHANNEL_ID)
    if channel is None:
        await ctx.send("The configured purchase channel was not found.", delete_after=10)
        return
    embed = make_embed(
        "Void Tools Tickets",
        "Need help or want to purchase something? Open the appropriate ticket below.\n\n🛠️ **Support** — General questions and assistance.\n🛒 **Purchase** — Purchase-related tickets.",
        "Void Tools • Support & Purchases",
    )
    view = TicketPanelView()
    await channel.send(embed=embed, view=view)
    await ctx.send(f"Ticket panel sent to {channel.mention}.", delete_after=5)


@bot.tree.command(name="review", description="Post an embedded review in the reviews channel.")
@app_commands.describe(description="Your review")
async def review(interaction: discord.Interaction, description: str):
    if not REVIEWS_CHANNEL_ID:
        await interaction.response.send_message("The reviews channel is not configured yet.", ephemeral=True)
        return
    channel = interaction.guild.get_channel(REVIEWS_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("The configured reviews channel was not found.", ephemeral=True)
        return
    embed = make_embed("⭐ New Review", description, "Void Tools • Community Review")
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Reviewer", value=interaction.user.mention)
    await channel.send(embed=embed)
    await interaction.response.send_message("Your review has been posted!", ephemeral=True)


@bot.tree.command(name="request", description="Request a source code/product.")
@app_commands.describe(product="The source code or product you want requested")
async def request(interaction: discord.Interaction, product: str):
    if not REQUESTS_CHANNEL_ID:
        await interaction.response.send_message("The requests channel is not configured yet.", ephemeral=True)
        return
    channel = interaction.guild.get_channel(REQUESTS_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("The configured requests channel was not found.", ephemeral=True)
        return
    embed = make_embed("📦 New Product Request", f"**Requested product/source:**\n{product}", "Void Tools • Requests")
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await channel.send(embed=embed)
    await interaction.response.send_message("Your request has been submitted!", ephemeral=True)


class FreeToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Check", style=discord.ButtonStyle.secondary, custom_id="voidtools:free_check")
    async def check(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("I couldn't find you in the server.", ephemeral=True)
            return
        if not VERIFIED_ROLE_ID or not FREE_TOOLS_ROLE_ID:
            await interaction.response.send_message("Free Tools roles are not configured yet.", ephemeral=True)
            return
        if not has_role(member, VERIFIED_ROLE_ID):
            await interaction.response.send_message("❌ You need the **Verified** role first.", ephemeral=True)
            return
        if not has_required_status(member):
            await interaction.response.send_message(
                f"❌ Your custom status must contain exactly this phrase (other text is allowed):\n`{REQUIRED_STATUS}`",
                ephemeral=True,
            )
            return
        role = interaction.guild.get_role(FREE_TOOLS_ROLE_ID)
        if role is None:
            await interaction.response.send_message("The Free Tools role could not be found.", ephemeral=True)
            return
        try:
            await member.add_roles(role, reason="Passed Free Tools status and Verified checks")
        except discord.Forbidden:
            await interaction.response.send_message("I can't give you the Free Tools role. Move my bot role above it.", ephemeral=True)
            return
        await interaction.response.send_message("✅ Checks passed! You now have access to the Free Tools category.", ephemeral=True)


@bot.command(name="ftools-")
async def ftools_prefix(ctx: commands.Context):
    await send_ftools_panel(ctx.channel)


@bot.command(name="ftools")
async def ftools_prefix_alt(ctx: commands.Context):
    await send_ftools_panel(ctx.channel)


async def send_ftools_panel(channel):
    embed = make_embed(
        "🔓 Free Tools Access",
        "To access the Free Tools category, you must meet these requirements:\n\n**1. Verified role**\nYou must have the configured **Verified** role.\n\n**2. Custom status**\nYour custom status must contain:\n`discord.gg/CdHc6Vk6jZ | Free Tools`\n\nOther text can be before or after the required phrase.\n\nPress **Check** below once you have completed the requirements.",
        "Void Tools • Free Tools Verification",
    )
    await channel.send(embed=embed, view=FreeToolsView())


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", emoji="🛠️", style=discord.ButtonStyle.secondary, custom_id="voidtools:ticket_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "support")

    @discord.ui.button(label="Purchase", emoji="🛒", style=discord.ButtonStyle.secondary, custom_id="voidtools:ticket_purchase")
    async def purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "purchase")


async def create_ticket(interaction: discord.Interaction, kind: str):
    guild = interaction.guild
    member = interaction.user
    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message("The ticket category is not configured correctly.", ephemeral=True)
        return
    channel_name = f"{kind}-{re.sub(r'[^a-z0-9-]', '-', member.name.lower())}"[:100]
    existing = discord.utils.get(category.text_channels, name=channel_name)
    if existing:
        await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
        return
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    staff_role_id = SUPPORT_STAFF_ROLE_ID if kind == "support" else PURCHASE_STAFF_ROLE_ID
    if staff_role_id:
        staff_role = guild.get_role(staff_role_id)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    try:
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason=f"{kind.title()} ticket opened by {member}")
    except discord.Forbidden:
        await interaction.response.send_message("I can't create the ticket. Check Manage Channels permission.", ephemeral=True)
        return
    embed = make_embed(
        f"{kind.title()} Ticket",
        f"Welcome {member.mention}!\n\nPlease describe what you need help with. A staff member will assist you shortly.",
        "Void Tools • Ticket Support",
    )
    await channel.send(content=member.mention, embed=embed, view=TicketCloseView())
    await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="voidtools:ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member):
            return
        allowed = interaction.user.guild_permissions.administrator
        if not allowed:
            for role_id in (SUPPORT_STAFF_ROLE_ID, PURCHASE_STAFF_ROLE_ID):
                if has_role(interaction.user, role_id):
                    allowed = True
                    break
        if not allowed:
            await interaction.response.send_message("Only staff can close this ticket.", ephemeral=True)
            return
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.HTTPException:
            pass


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need Administrator permission to use that command.", delete_after=7)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`.", delete_after=7)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("I couldn't understand one of the arguments. For example: `$gtfo @User reason`.", delete_after=7)
        return
    print(f"[PREFIX ERROR] {error!r}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("No Discord bot token found. Set DISCORD_TOKEN in Railway or bot_token in config.json for local testing.")
    import os
    bot.run(TOKEN)
