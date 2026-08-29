import os
import json
import re
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from discord import app_commands


# ============================================================
# CONFIG
# ============================================================

with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Railway uses DISCORD_TOKEN.
# For local testing, bot_token can also be used.
TOKEN = os.getenv("DISCORD_TOKEN") or CONFIG.get("bot_token", "").strip()

PREFIXES = CONFIG.get("prefixes", ["$", "!"])

GUILD_ID = int(CONFIG.get("guild_id", 0))

EMBED_COLOR = int(
    CONFIG.get("embed_color", "FFFFFF").replace("#", ""),
    16
)

WELCOME_CHANNEL_ID = int(CONFIG.get("welcome_channel_id", 0))
REVIEWS_CHANNEL_ID = int(CONFIG.get("reviews_channel_id", 0))
REQUESTS_CHANNEL_ID = int(CONFIG.get("requests_channel_id", 0))
PURCHASE_CHANNEL_ID = int(CONFIG.get("purchase_channel_id", 0))
TICKET_CATEGORY_ID = int(CONFIG.get("ticket_category_id", 0))

SUPPORT_STAFF_ROLE_ID = int(
    CONFIG.get("support_staff_role_id", 0)
)

PURCHASE_STAFF_ROLE_ID = int(
    CONFIG.get("purchase_staff_role_id", 0)
)

VERIFIED_ROLE_ID = int(
    CONFIG.get("verified_role_id", 0)
)

FREE_TOOLS_ROLE_ID = int(
    CONFIG.get("free_tools_role_id", 0)
)

REQUIRED_STATUS = CONFIG.get(
    "free_tools_required_text",
    "discord.gg/CdHc6Vk6jZ | Free Tools"
)

LOGO_URL = CONFIG.get("logo_url", "")

SERVER_NAME = "Void Tools"
SERVER_INVITE = "discord.gg/CdHc6Vk6jZ"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    help_command=None
)

commands_synced = False


# ============================================================
# EMBED HELPER
# ============================================================

def make_embed(title, description=""):
    embed = discord.Embed(
        title=title,
        description=description,
        color=EMBED_COLOR
    )

    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)

    embed.set_footer(
        text=f"{SERVER_NAME} • {SERVER_INVITE}"
    )

    return embed


# ============================================================
# CONFIG HELPERS
# ============================================================

def get_channel(channel_id):
    if not channel_id:
        return None

    return bot.get_channel(channel_id)


def get_role(guild, role_id):
    if not role_id:
        return None

    return guild.get_role(role_id)


def member_has_role(member, role_id):
    if not role_id:
        return False

    return any(
        role.id == role_id
        for role in member.roles
    )


# ============================================================
# FREE TOOLS STATUS CHECK
# ============================================================

def has_required_status(member):
    """
    Checks the user's Discord Custom Status.

    Required text:
    discord.gg/CdHc6Vk6jZ | Free Tools

    Discord bots cannot normally read a user's personal
    About Me/bio through the standard bot API.
    """

    for activity in member.activities:

        if isinstance(activity, discord.CustomActivity):

            state = activity.state or ""

            if REQUIRED_STATUS.lower() in state.lower():
                return True

    return False


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    global commands_synced

    if not commands_synced:

        try:

            if GUILD_ID:

                guild = discord.Object(id=GUILD_ID)

                # Copy commands to the selected guild.
                bot.tree.copy_global_to(guild=guild)

                synced = await bot.tree.sync(
                    guild=guild
                )

                print(
                    f"[SYNC] Synced {len(synced)} "
                    f"slash commands to guild {GUILD_ID}."
                )

            else:

                synced = await bot.tree.sync()

                print(
                    f"[SYNC] Synced {len(synced)} "
                    "global slash commands."
                )

            commands_synced = True

        except discord.Forbidden as error:

            print(
                f"[SYNC ERROR] Missing Access: {error}"
            )

            print(
                "[SYNC HELP] Make sure the bot is inside "
                "the configured server and was invited with "
                "the applications.commands scope."
            )

        except Exception as error:

            print(
                f"[SYNC ERROR] "
                f"{type(error).__name__}: {error}"
            )

    if not status_checker.is_running():
        status_checker.start()

    print(
        f"[ONLINE] Logged in as "
        f"{bot.user} ({bot.user.id})"
    )


# ============================================================
# WELCOME MESSAGE
# ============================================================

@bot.event
async def on_member_join(member):

    channel = get_channel(
        WELCOME_CHANNEL_ID
    )

    if channel is None:
        return

    embed = make_embed(
        f"Welcome to {SERVER_NAME}!",
        (
            f"Welcome {member.mention}! 👋\n\n"
            "We're glad to have you here.\n"
            "Enjoy our tools, source codes and community!"
        )
    )

    embed.set_author(
        name=str(member),
        icon_url=member.display_avatar.url
    )

    try:

        await channel.send(
            embed=embed
        )

    except discord.HTTPException:

        pass


# ============================================================
# AUTOMATIC FREE TOOLS ROLE CHECK
# ============================================================

@tasks.loop(seconds=30)
async def status_checker():

    if not GUILD_ID:
        return

    if not FREE_TOOLS_ROLE_ID:
        return

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        return

    free_role = guild.get_role(
        FREE_TOOLS_ROLE_ID
    )

    if free_role is None:
        return

    for member in guild.members:

        if member.bot:
            continue

        if not member_has_role(
            member,
            FREE_TOOLS_ROLE_ID
        ):
            continue

        # If the required custom status disappears,
        # remove the Free Tools role.
        if not has_required_status(member):

            try:

                await member.remove_roles(
                    free_role,
                    reason=(
                        "Void Tools Free Tools "
                        "status requirement removed"
                    )
                )

            except discord.HTTPException:

                pass


@status_checker.before_loop
async def before_status_checker():

    await bot.wait_until_ready()


# ============================================================
# /EMBEDCREATE
# ============================================================

@bot.tree.command(
    name="embedcreate",
    description="Create and send a custom embed."
)
@app_commands.describe(
    header="Embed header/title",
    text="Embed text",
    footer="Embed footer"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def embedcreate(
    interaction: discord.Interaction,
    header: str,
    text: str,
    footer: str
):

    embed = discord.Embed(
        title=header,
        description=text,
        color=EMBED_COLOR
    )

    embed.set_footer(
        text=footer
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Embed sent.",
        ephemeral=True
    )


# ============================================================
# DURATION PARSER
# ============================================================

def parse_duration(value):

    match = re.fullmatch(
        r"(\d+)\s*(s|m|h|d)",
        value.lower().strip()
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    return timedelta(
        seconds=amount * multipliers[unit]
    )


# ============================================================
# /STFU
# ============================================================

@bot.tree.command(
    name="stfu",
    description="Timeout a member."
)
@app_commands.describe(
    user="Member to timeout",
    duration="Example: 10m, 1h, 1d",
    reason="Reason for the timeout"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def stfu(
    interaction: discord.Interaction,
    user: discord.Member,
    duration: str,
    reason: str = "No reason provided"
):

    delta = parse_duration(
        duration
    )

    if delta is None:

        await interaction.response.send_message(
            "❌ Invalid duration.\n"
            "Use `10m`, `1h`, or `1d`.",
            ephemeral=True
        )

        return

    try:

        await user.timeout(
            delta,
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 {user.mention} has been "
            f"timed out for `{duration}`."
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to "
            "timeout that member.",
            ephemeral=True
        )


# ============================================================
# $GTFO
# ============================================================

@bot.command(
    name="gtfo"
)
@commands.has_permissions(
    administrator=True
)
@commands.bot_has_permissions(
    ban_members=True
)
async def gtfo(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    try:

        await member.ban(
            reason=reason
        )

        await ctx.send(
            f"🔨 Banned **{member}**."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission "
            "to ban that member."
        )


# ============================================================
# /REVIEW
# ============================================================

@bot.tree.command(
    name="review",
    description="Submit a review about Void Tools."
)
@app_commands.describe(
    description="Your review"
)
async def review(
    interaction: discord.Interaction,
    description: str
):

    channel = get_channel(
        REVIEWS_CHANNEL_ID
    )

    if channel is None:

        await interaction.response.send_message(
            "❌ The reviews channel has not "
            "been configured yet.",
            ephemeral=True
        )

        return

    embed = make_embed(
        "⭐ New Review",
        description
    )

    embed.set_author(
        name=f"Review by {interaction.user}",
        icon_url=interaction.user.display_avatar.url
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Your review has been submitted!",
        ephemeral=True
    )


# ============================================================
# /REQUEST
# ============================================================

@bot.tree.command(
    name="request",
    description="Request a product or source code."
)
@app_commands.describe(
    product="Product or source code you want"
)
async def request(
    interaction: discord.Interaction,
    product: str
):

    channel = get_channel(
        REQUESTS_CHANNEL_ID
    )

    if channel is None:

        await interaction.response.send_message(
            "❌ The requests channel has not "
            "been configured yet.",
            ephemeral=True
        )

        return

    embed = make_embed(
        "📦 Product Request",
        (
            f"**Requested product:**\n"
            f"{product}\n\n"
            f"**Requested by:** "
            f"{interaction.user.mention}"
        )
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Your request has been submitted!",
        ephemeral=True
    )


# ============================================================
# TICKET PANEL
# ============================================================

class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    async def create_ticket(
        self,
        interaction,
        ticket_type
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )

            return

        category = None

        if TICKET_CATEGORY_ID:

            category = guild.get_channel(
                TICKET_CATEGORY_ID
            )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(
                "❌ The ticket category has not "
                "been configured.",
                ephemeral=True
            )

            return

        username = interaction.user.name

        ticket_name = (
            f"{ticket_type}-{username}"
        )[:100]

        existing = discord.utils.get(
            guild.text_channels,
            name=ticket_name
        )

        if existing:

            await interaction.response.send_message(
                f"❌ You already have a ticket: "
                f"{existing.mention}",
                ephemeral=True
            )

            return

        if ticket_type == "support":

            staff_role_id = (
                SUPPORT_STAFF_ROLE_ID
            )

        else:

            staff_role_id = (
                PURCHASE_STAFF_ROLE_ID
            )

        staff_role = None

        if staff_role_id:

            staff_role = guild.get_role(
                staff_role_id
            )

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True
                )
        }

        if staff_role:

            overwrites[staff_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            )

        try:

            channel = await guild.create_text_channel(
                ticket_name,
                category=category,
                overwrites=overwrites,
                reason=f"{ticket_type.title()} ticket"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to "
                "create ticket channels.",
                ephemeral=True
            )

            return

        embed = make_embed(
            f"{ticket_type.title()} Ticket",
            (
                f"Welcome {interaction.user.mention}!\n\n"
                "Please explain what you need. "
                "A staff member will assist you."
            )
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

    @discord.ui.button(
        label="Support",
        style=discord.ButtonStyle.secondary,
        custom_id="voidtools:support_ticket"
    )
    async def support(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "support"
        )

    @discord.ui.button(
        label="Purchase",
        style=discord.ButtonStyle.primary,
        custom_id="voidtools:purchase_ticket"
    )
    async def purchase(
        self,
        interaction,
        button
    ):

        await self.create_ticket(
            interaction,
            "purchase"
        )


# ============================================================
# /TPANEL
# ============================================================

@bot.tree.command(
    name="tpanel",
    description="Send the Void Tools ticket panel."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def tpanel(
    interaction: discord.Interaction
):

    channel = get_channel(
        PURCHASE_CHANNEL_ID
    )

    if channel is None:

        await interaction.response.send_message(
            "❌ The purchase channel has not "
            "been configured.",
            ephemeral=True
        )

        return

    embed = make_embed(
        "🎫 Void Tools Tickets",
        (
            "Need help or want to purchase "
            "something?\n\n"
            "Choose a button below."
        )
    )

    await channel.send(
        embed=embed,
        view=TicketView()
    )

    await interaction.response.send_message(
        "✅ Ticket panel sent.",
        ephemeral=True
    )


# ============================================================
# FREE TOOLS VIEW
# ============================================================

class FreeToolsView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Check",
        style=discord.ButtonStyle.primary,
        custom_id="voidtools:free_tools_check"
    )
    async def check(
        self,
        interaction,
        button
    ):

        guild = interaction.guild
        member = interaction.user

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )

            return

        verified_role = get_role(
            guild,
            VERIFIED_ROLE_ID
        )

        free_tools_role = get_role(
            guild,
            FREE_TOOLS_ROLE_ID
        )

        if (
            verified_role is None
            or free_tools_role is None
        ):

            await interaction.response.send_message(
                "❌ The Verified and Free Tools "
                "roles have not been configured.",
                ephemeral=True
            )

            return

        if not member_has_role(
            member,
            VERIFIED_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ You need the **Verified** role.",
                ephemeral=True
            )

            return

        if not has_required_status(
            member
        ):

            await interaction.response.send_message(
                "❌ Your custom status must contain:\n\n"
                f"`{REQUIRED_STATUS}`",
                ephemeral=True
            )

            return

        try:

            await member.add_roles(
                free_tools_role,
                reason=(
                    "Void Tools Free Tools verification"
                )
            )

            await interaction.response.send_message(
                "✅ Verification successful!\n"
                "You now have Free Tools access.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I can't give you the Free Tools role.\n"
                "Make sure the bot's role is above "
                "the Free Tools role.",
                ephemeral=True
            )


# ============================================================
# FREE TOOLS PREFIX COMMAND
# ============================================================

@bot.command(
    name="ftools-",
    aliases=["ftools"]
)
@commands.cooldown(
    1,
    5,
    commands.BucketType.user
)
async def ftools_prefix(ctx):

    embed = make_embed(
        "🔓 Free Tools Access",
        (
            "**Requirements**\n\n"
            "1. Your custom status must contain:\n"
            f"`{REQUIRED_STATUS}`\n\n"
            "2. You must have the **Verified** role.\n\n"
            "Press **Check** below to verify."
        )
    )

    await ctx.send(
        embed=embed,
        view=FreeToolsView()
    )


# ============================================================
# /FTOOLS
# ============================================================

@bot.tree.command(
    name="ftools",
    description="Check Free Tools access."
)
async def ftools(
    interaction: discord.Interaction
):

    embed = make_embed(
        "🔓 Free Tools Access",
        (
            "**Requirements**\n\n"
            "1. Your custom status must contain:\n"
            f"`{REQUIRED_STATUS}`\n\n"
            "2. You must have the **Verified** role.\n\n"
            "Press **Check** below to verify."
        )
    )

    await interaction.response.send_message(
        embed=embed,
        view=FreeToolsView()
    )


# ============================================================
# PREFIX COMMAND ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ Administrator permission required."
        )

        return

    if isinstance(
        error,
        commands.BotMissingPermissions
    ):

        await ctx.send(
            "❌ I don't have the required permission."
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ You're missing a required argument."
        )

        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):

        await ctx.send(
            "❌ I couldn't find that member."
        )

        return

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):

        await ctx.send(
            f"⏳ Try again in "
            f"{error.retry_after:.1f} seconds."
        )

        return

    print(
        f"[COMMAND ERROR] "
        f"{type(error).__name__}: {error}"
    )


# ============================================================
# TOKEN CHECK
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "No Discord bot token found.\n"
        "For Railway, create a variable named "
        "DISCORD_TOKEN.\n"
        "For local testing, you can put the token "
        "in config.json as bot_token."
    )


# ============================================================
# START BOT
# ============================================================

bot.run(TOKEN)
