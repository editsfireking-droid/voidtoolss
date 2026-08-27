# OpenSource Discord Bot — Setup

## Important limitation about the bio requirement

A normal Discord bot can receive supported presence/custom-status data, but Discord does not expose a standard bot API field for reading a member's personal **About Me/bio**. Therefore this bot automatically checks:

- the `Verified` role
- the required custom-status phrase

It cannot automatically verify the personal bio or detect removal of only the bio text.

Do **not** use a user token/self-bot to bypass this limitation. Discord prohibits automating normal user accounts.

## Install

Windows:

```text
py -m pip install -r requirements.txt
```

## Developer Portal

Create the bot, copy its token, and put it in `config.json`.

Under **Bot → Privileged Gateway Intents**, enable:

- Server Members Intent
- Message Content Intent
- Presence Intent

The current discord.py release used by this project is 2.7.1.

## Permissions

Recommended bot permissions:

- View Channels
- Send Messages
- Embed Links
- Read Message History
- Manage Channels
- Manage Roles
- Ban Members
- Moderate Members

Put the bot's role above the Free Tools role and any roles it needs to manage.

## config.json

Replace every placeholder ID with the real Discord ID.

Enable Developer Mode in Discord, then right-click a channel/role/server and choose **Copy ID**.

`guild_id` is the server where slash commands are synced immediately.

## Run

```text
py bot.py
```

## Commands

### Admin

- `/embedcreate header text footer`
- `/stfu @user 10m reason`
- `$gtfo @user reason`
- `$tpanel`

### Everyone

- `/review description`
- `/request product`
- `!ftools-`

### Ticket names

- `support-username`
- `purchase-username`

The ticket panel uses the server's current icon automatically, so no separate logo URL is required.

## Free Tools

Default required custom status:

```text
discord.gg/yourlink | Free Tools
```

Extra status text is allowed. For example:

```text
Playing Roblox | discord.gg/yourlink | Free Tools | OpenSource
```

When the detectable custom status no longer contains the required phrase, the bot removes the Free Tools role.

The bio requirement needs manual verification because the standard bot API cannot read the personal About Me field.
