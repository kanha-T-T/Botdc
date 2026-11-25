# ==============================
# VEXORA BOT - PART 1
# ==============================

import discord
from discord.ext import commands
import os
import sqlite3
import random
import asyncio
import time
from datetime import datetime, timedelta

# ---------- CONFIG ----------

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1495419933943922920

SUPPORT_SERVER = "https://discord.gg/ZBaRByVFBC"

PREFIXES = ["!", "?", ".", "$", "-"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.invites = True
intents.reactions = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    case_insensitive=True,
    help_command=None
)

# ---------- DATABASE ----------

db = sqlite3.connect("vexora.db")
cursor = db.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS premium (
    guild_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS reputation (
    guild_id INTEGER,
    user_id INTEGER,
    rep INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS custom_commands (
    guild_id INTEGER,
    name TEXT,
    response TEXT,
    PRIMARY KEY (guild_id, name)
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER,
    name TEXT,
    value TEXT,
    PRIMARY KEY (guild_id, name)
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    emoji TEXT,
    role_id INTEGER
);
""")

db.commit()


def execute(query, values=()):
    cursor.execute(query, values)
    db.commit()
    return cursor


def fetchone(query, values=()):
    return cursor.execute(query, values).fetchone()


def fetchall(query, values=()):
    return cursor.execute(query, values).fetchall()


# ---------- EMBEDS ----------

def make_embed(title, description=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_rgb(190, 190, 190),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="VEXORA • One Bot. Endless Possibilities.")
    return embed


def success(ctx, message):
    return make_embed("✓ Success", message)


def error(ctx, message):
    return make_embed("✕ Error", message)


def info(ctx, message):
    return make_embed("VEXORA", message)


# ---------- CHECKS ----------

def owner_only():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)


def is_premium(guild_id):
    return fetchone(
        "SELECT guild_id FROM premium WHERE guild_id = ?",
        (guild_id,)
    ) is not None


# ---------- GENERAL COMMANDS ----------

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(embed=make_embed("🏓 Pong!", f"Latency: `{latency}ms`"))


@bot.command()
async def botinfo(ctx):
    embed = make_embed(
        "VEXORA",
        "**One Bot. Endless Possibilities.**"
    )
    embed.add_field(name="Servers", value=f"`{len(bot.guilds)}`")
    embed.add_field(name="Users", value=f"`{len(bot.users)}`")
    embed.add_field(name="Latency", value=f"`{round(bot.latency * 1000)}ms`")
    await ctx.send(embed=embed)


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    if not guild:
        return

    embed = make_embed(guild.name)
    embed.add_field(name="Members", value=str(guild.member_count))
    embed.add_field(name="Owner", value=str(guild.owner))
    embed.add_field(name="Channels", value=str(len(guild.channels)))
    embed.add_field(name="Roles", value=str(len(guild.roles)))
    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = make_embed(str(member))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id))
    embed.add_field(name="Joined", value=member.joined_at.strftime("%d %b %Y"))
    embed.add_field(name="Created", value=member.created_at.strftime("%d %b %Y"))
    await ctx.send(embed=embed)


@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = make_embed(f"{member.display_name}'s Avatar")
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def support(ctx):
    await ctx.send(embed=make_embed(
        "Support Server",
        f"[Join VEXORA Support]({SUPPORT_SERVER})"
    ))


# ---------- MODERATION ----------

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if member == ctx.author or member == bot.user:
        return await ctx.send(embed=error(ctx, "You cannot ban that user."))

    await member.ban(reason=reason)
    await ctx.send(embed=success(ctx, f"**{member}** was banned.\nReason: {reason}"))


@bot.command()
@commands.has_permissions(kick_members=True)
async def modkick(ctx, member: discord.Member, *, reason="No reason provided"):
    if member == ctx.author or member == bot.user:
        return await ctx.send(embed=error(ctx, "You cannot kick that user."))

    await member.kick(reason=reason)
    await ctx.send(embed=success(ctx, f"**{member}** was kicked.\nReason: {reason}"))


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason="No reason provided"):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(embed=success(ctx, f"Unbanned **{user}**."))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    if minutes < 1 or minutes > 40320:
        return await ctx.send(embed=error(ctx, "Choose a duration from 1 to 40320 minutes."))

    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(embed=success(ctx, f"Timed out **{member}** for `{minutes}` minutes."))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(embed=success(ctx, f"Timeout removed for **{member}**."))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        return await ctx.send(embed=error(ctx, "Choose between 1 and 100 messages."))

    deleted = await ctx.channel.purge(limit=amount + 1)
    message = await ctx.send(embed=success(ctx, f"Deleted `{len(deleted) - 1}` messages."))
    await asyncio.sleep(4)
    await message.delete()


@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=False
    )
    await ctx.send(embed=success(ctx, "Channel locked."))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=True
    )
    await ctx.send(embed=success(ctx, "Channel unlocked."))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if seconds < 0 or seconds > 21600:
        return await ctx.send(embed=error(ctx, "Slowmode must be between 0 and 21600 seconds."))

    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(embed=success(ctx, f"Slowmode set to `{seconds}` seconds."))


# ---------- WARNINGS ----------

@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    execute(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (ctx.guild.id, member.id, ctx.author.id, reason)
    )
    await ctx.send(embed=success(ctx, f"Warned **{member}**.\nReason: {reason}"))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warnings(ctx, member: discord.Member):
    rows = fetchall(
        "SELECT reason, moderator_id FROM warnings WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    if not rows:
        return await ctx.send(embed=info(ctx, f"**{member}** has no warnings."))

    description = ""
    for number, (reason, moderator_id) in enumerate(rows, 1):
        description += f"**{number}.** {reason} — <@{moderator_id}>\n"

    await ctx.send(embed=make_embed(f"Warnings: {member}", description))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def clearwarns(ctx, member: discord.Member):
    execute(
        "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )
    await ctx.send(embed=success(ctx, f"Cleared warnings for **{member}**."))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def staff(ctx):
    roles = [
        role.mention for role in ctx.guild.roles
        if role.permissions.manage_messages or role.permissions.administrator
    ]

    roles = list(dict.fromkeys(roles))
    await ctx.send(embed=make_embed(
        "Staff Roles",
        "\n".join(roles) if roles else "No staff roles found."
    ))


# ---------- LEVELS ----------

@bot.listen("on_message")
async def level_message(message):
    if message.author.bot or not message.guild:
        return

    user_id = message.author.id
    guild_id = message.guild.id

    row = fetchone(
        "SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )

    if row is None:
        xp, level = 0, 0
        execute(
            "INSERT INTO levels (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)",
            (guild_id, user_id)
        )
    else:
        xp, level = row

    xp += random.randint(5, 12)
    new_level = int((xp / 100) ** 0.5)

    execute(
        "UPDATE levels SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
        (xp, new_level, guild_id, user_id)
    )

    if new_level > level:
        await message.channel.send(
            embed=make_embed(
                "🎉 Level Up!",
                f"{message.author.mention} reached level `{new_level}`!"
            )
        )


@bot.command(aliases=["level"])
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    xp, level = row if row else (0, 0)

    await ctx.send(embed=make_embed(
        f"{member.display_name}'s Rank",
        f"Level: `{level}`\nXP: `{xp}`"
    ))


@bot.command()
async def levels(ctx):
    rows = fetchall(
        "SELECT user_id, xp, level FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = ""
    for number, (user_id, xp, level) in enumerate(rows, 1):
        description += f"`{number}.` <@{user_id}> — Level `{level}` | `{xp}` XP\n"

    await ctx.send(embed=make_embed(
        "🏆 Level Leaderboard",
        description or "No levels recorded yet."
    ))


# ---------- REPUTATION ----------

@bot.command()
async def rep(ctx, member: discord.Member):
    if member.bot or member == ctx.author:
        return await ctx.send(embed=error(ctx, "You cannot give reputation to that user."))

    row = fetchone(
        "SELECT rep FROM reputation WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    if row is None:
        execute(
            "INSERT INTO reputation (guild_id, user_id, rep) VALUES (?, ?, 1)",
            (ctx.guild.id, member.id)
        )
        total = 1
    else:
        total = row[0] + 1
        execute(
            "UPDATE reputation SET rep = ? WHERE guild_id = ? AND user_id = ?",
            (total, ctx.guild.id, member.id)
        )

    await ctx.send(embed=success(ctx, f"{member.mention} now has `{total}` reputation."))


@bot.command()
async def reps(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT rep FROM reputation WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    total = row[0] if row else 0
    await ctx.send(embed=info(ctx, f"{member.mention} has `{total}` reputation."))


@bot.command()
async def repboard(ctx):
    rows = fetchall(
        "SELECT user_id, rep FROM reputation WHERE guild_id = ? ORDER BY rep DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = ""
    for number, (user_id, rep_count) in enumerate(rows, 1):
        description += f"`{number}.` <@{user_id}> — `{rep_count}` rep\n"

    await ctx.send(embed=make_embed(
        "🏆 Reputation Leaderboard",
        description or "No reputation recorded yet."
    ))


# ---------- PREMIUM MANAGEMENT ----------

@bot.group(invoke_without_command=True)
async def premium(ctx):
    active = is_premium(ctx.guild.id)
    await ctx.send(embed=info(
        ctx,
        f"This server's Premium status: **{'Active' if active else 'Inactive'}**"
    ))


@premium.command(name="add")
@owner_only()
async def premium_add(ctx, guild_id: int):
    execute(
        "INSERT OR IGNORE INTO premium (guild_id) VALUES (?)",
        (guild_id,)
    )
    await ctx.send(embed=success(ctx, f"Premium enabled for server `{guild_id}`."))


@premium.command(name="remove")
@owner_only()
async def premium_remove(ctx, guild_id: int):
    execute("DELETE FROM premium WHERE guild_id = ?", (guild_id,))
    await ctx.send(embed=success(ctx, f"Premium removed from server `{guild_id}`."))


@premium.command(name="check")
@owner_only()
async def premium_check(ctx, guild_id: int):
    active = is_premium(guild_id)
    await ctx.send(embed=info(ctx, f"Server `{guild_id}` Premium: **{active}**"))


@premium.command(name="list")
@owner_only()
async def premium_list(ctx):
    rows = fetchall("SELECT guild_id FROM premium")
    description = "\n".join(f"`{row[0]}`" for row in rows)
    await ctx.send(embed=make_embed("Premium Servers", description or "No Premium servers."))
    # ==============================
# VEXORA BOT - PART 2
# ==============================

# ---------- EXTRA DATABASE TABLES ----------

cursor.executescript("""
CREATE TABLE IF NOT EXISTS afk (
    guild_id INTEGER,
    user_id INTEGER,
    reason TEXT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS invite_counts (
    guild_id INTEGER,
    user_id INTEGER,
    regular INTEGER DEFAULT 0,
    leaves INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS giveaways (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    prize TEXT,
    end_time REAL,
    ended INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    owner_id INTEGER,
    claimed_by INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ftr_scores (
    guild_id INTEGER,
    user_id INTEGER,
    wins INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);
""")

db.commit()


# ---------- SETTINGS HELPERS ----------

def get_setting(guild_id, name):
    row = fetchone(
        "SELECT value FROM settings WHERE guild_id = ? AND name = ?",
        (guild_id, name)
    )
    return row[0] if row else None


def set_setting(guild_id, name, value):
    execute(
        "INSERT OR REPLACE INTO settings (guild_id, name, value) VALUES (?, ?, ?)",
        (guild_id, name, str(value))
    )


# ---------- AFK ----------

@bot.command()
async def afk(ctx, *, reason="AFK"):
    execute(
        "INSERT OR REPLACE INTO afk (guild_id, user_id, reason) VALUES (?, ?, ?)",
        (ctx.guild.id, ctx.author.id, reason)
    )

    await ctx.send(embed=success(ctx, f"You are now AFK: **{reason}**"))


@bot.listen("on_message")
async def afk_listener(message):
    if message.author.bot or not message.guild:
        return

    row = fetchone(
        "SELECT reason FROM afk WHERE guild_id = ? AND user_id = ?",
        (message.guild.id, message.author.id)
    )

    if row:
        execute(
            "DELETE FROM afk WHERE guild_id = ? AND user_id = ?",
            (message.guild.id, message.author.id)
        )
        await message.channel.send(
            embed=info(None, f"Welcome back {message.author.mention}! Your AFK status was removed.")
        )

    for member in message.mentions:
        row = fetchone(
            "SELECT reason FROM afk WHERE guild_id = ? AND user_id = ?",
            (message.guild.id, member.id)
        )

        if row:
            await message.channel.send(
                embed=info(None, f"**{member.display_name}** is AFK: {row[0]}")
            )


# ---------- CONFESSIONS ----------

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confessionset(ctx, channel: discord.TextChannel):
    set_setting(ctx.guild.id, "confession_channel", channel.id)
    await ctx.send(embed=success(ctx, f"Confession channel set to {channel.mention}"))


@bot.command()
async def confess(ctx, *, message):
    channel_id = get_setting(ctx.guild.id, "confession_channel")

    if not channel_id:
        return await ctx.send(embed=error(ctx, "Confessions haven't been configured."))

    channel = ctx.guild.get_channel(int(channel_id))

    if not channel:
        return await ctx.send(embed=error(ctx, "Confession channel not found."))

    embed = make_embed("Anonymous Confession", message)
    embed.set_footer(text="VEXORA • Anonymous")

    await channel.send(embed=embed)
    await ctx.send(embed=success(ctx, "Your confession was submitted anonymously."))


# ---------- SUGGESTIONS ----------

@bot.command()
@commands.has_permissions(manage_guild=True)
async def suggestionset(ctx, channel: discord.TextChannel):
    set_setting(ctx.guild.id, "suggestion_channel", channel.id)
    await ctx.send(embed=success(ctx, f"Suggestion channel set to {channel.mention}"))


@bot.command()
async def suggest(ctx, *, suggestion):
    channel_id = get_setting(ctx.guild.id, "suggestion_channel")

    if not channel_id:
        return await ctx.send(embed=error(ctx, "Suggestions haven't been configured."))

    channel = ctx.guild.get_channel(int(channel_id))

    if not channel:
        return await ctx.send(embed=error(ctx, "Suggestion channel not found."))

    embed = make_embed("New Suggestion", suggestion)
    embed.add_field(name="Submitted by", value=ctx.author.mention)

    message = await channel.send(embed=embed)
    await message.add_reaction("👍")
    await message.add_reaction("👎")

    await ctx.send(embed=success(ctx, "Suggestion submitted."))


# ---------- POLLS ----------

@bot.command()
async def poll(ctx, *, question):
    embed = make_embed("📊 Poll", question)
    embed.add_field(name="Vote", value="👍 Yes\n👎 No")

    message = await ctx.send(embed=embed)
    await message.add_reaction("👍")
    await message.add_reaction("👎")


# ---------- ANIME FUN COMMANDS ----------

ANIME_GIFS = {
    "kiss": "https://media.tenor.com/9Z3Q7Vq7X8AAAAAC/anime-kiss.gif",
    "punch": "https://media.tenor.com/2roX3uxz_68AAAAC/anime-punch.gif",
    "kick": "https://media.tenor.com/5Vb5Z7Y5b2AAAAAC/anime-kick.gif"
}


async def anime_action(ctx, member, action):
    if member.bot and member == bot.user:
        return await ctx.send(embed=error(ctx, "You cannot target me!"))

    embed = make_embed(
        f"Anime {action.title()}",
        f"{ctx.author.mention} used **{action}** on {member.mention}!"
    )
    embed.set_image(url=ANIME_GIFS[action])

    await ctx.send(embed=embed)


@bot.command()
async def kiss(ctx, member: discord.Member):
    await anime_action(ctx, member, "kiss")


@bot.command()
async def punch(ctx, member: discord.Member):
    await anime_action(ctx, member, "punch")


@bot.command()
async def kick(ctx, member: discord.Member):
    await anime_action(ctx, member, "kick")


# ---------- PREMIUM CUSTOM COMMANDS ----------

@bot.group(invoke_without_command=True)
async def cc(ctx):
    await ctx.send(embed=make_embed(
        "Custom Commands",
        "`!cc add <name> <response>`\n"
        "`!cc edit <name> <response>`\n"
        "`!cc remove <name>`\n"
        "`!cc list`\n"
        "`!cc info <name>`"
    ))


@cc.command(name="add")
@commands.has_permissions(manage_guild=True)
async def cc_add(ctx, name: str, *, response: str):
    if not is_premium(ctx.guild.id):
        return await ctx.send(embed=error(ctx, "Custom commands require Premium."))

    name = name.lower()

    if not name.isalnum():
        return await ctx.send(embed=error(ctx, "Use only letters and numbers in command names."))

    if bot.get_command(name):
        return await ctx.send(embed=error(ctx, "That command name is already in use."))

    existing = fetchone(
        "SELECT name FROM custom_commands WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, name)
    )

    if existing:
        return await ctx.send(embed=error(ctx, "That custom command already exists."))

    execute(
        "INSERT INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?)",
        (ctx.guild.id, name, response)
    )

    await ctx.send(embed=success(ctx, f"Custom command `!{name}` created."))


@cc.command(name="edit")
@commands.has_permissions(manage_guild=True)
async def cc_edit(ctx, name: str, *, response: str):
    if not is_premium(ctx.guild.id):
        return await ctx.send(embed=error(ctx, "Custom commands require Premium."))

    name = name.lower()

    existing = fetchone(
        "SELECT name FROM custom_commands WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, name)
    )

    if not existing:
        return await ctx.send(embed=error(ctx, "Custom command not found."))

    execute(
        "UPDATE custom_commands SET response = ? WHERE guild_id = ? AND name = ?",
        (response, ctx.guild.id, name)
    )

    await ctx.send(embed=success(ctx, f"Updated `!{name}`."))


@cc.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def cc_remove(ctx, name: str):
    if not is_premium(ctx.guild.id):
        return await ctx.send(embed=error(ctx, "Custom commands require Premium."))

    execute(
        "DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, name.lower())
    )

    await ctx.send(embed=success(ctx, f"Removed `!{name}` if it existed."))


@cc.command(name="list")
async def cc_list(ctx):
    rows = fetchall(
        "SELECT name FROM custom_commands WHERE guild_id = ?",
        (ctx.guild.id,)
    )

    if not rows:
        return await ctx.send(embed=info(ctx, "No custom commands created."))

    description = "\n".join(f"`!{row[0]}`" for row in rows)

    await ctx.send(embed=make_embed("Custom Commands", description))


@cc.command(name="info")
async def cc_info(ctx, name: str):
    row = fetchone(
        "SELECT response FROM custom_commands WHERE guild_id = ? AND name = ?",
        (ctx.guild.id, name.lower())
    )

    if not row:
        return await ctx.send(embed=error(ctx, "Custom command not found."))

    await ctx.send(embed=make_embed(
        f"Custom Command: {name}",
        row[0][:4000]
    ))


@bot.listen("on_message")
async def custom_command_listener(message):
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()

    if not content or content[0] not in PREFIXES:
        return

    command_name = content[1:].split()[0].lower()

    if bot.get_command(command_name):
        return

    row = fetchone(
        "SELECT response FROM custom_commands WHERE guild_id = ? AND name = ?",
        (message.guild.id, command_name)
    )

    if row:
        await message.channel.send(
            row[0][:2000],
            allowed_mentions=discord.AllowedMentions.none()
        )


# ---------- INVITE TRACKING ----------

invite_cache = {}


@bot.event
async def on_ready():
    print(f"VEXORA is online as {bot.user}")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except discord.Forbidden:
            print(f"Cannot read invites in {guild.name}")

    for row in fetchall(
        "SELECT message_id, end_time FROM giveaways WHERE ended = 0"
    ):
        message_id, end_time = row
        delay = max(0, end_time - time.time())
        asyncio.create_task(giveaway_timer(message_id, delay))


@bot.event
async def on_invite_create(invite):
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except discord.Forbidden:
        pass


@bot.event
async def on_invite_delete(invite):
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except discord.Forbidden:
        pass


@bot.event
async def on_member_join(member):
    guild = member.guild

    try:
        new_invites = await guild.invites()
        old_invites = invite_cache.get(guild.id, [])

        used_invite = None

        for new in new_invites:
            for old in old_invites:
                if new.code == old.code and new.uses > old.uses:
                    used_invite = new
                    break

            if used_invite:
                break

        invite_cache[guild.id] = new_invites

        if used_invite and used_invite.inviter:
            inviter_id = used_invite.inviter.id

            execute("""
                INSERT INTO invite_counts (guild_id, user_id, regular)
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET regular = regular + 1
            """, (guild.id, inviter_id))

    except discord.Forbidden:
        pass


@bot.event
async def on_member_remove(member):
    rows = fetchall(
        "SELECT user_id, regular FROM invite_counts WHERE guild_id = ?",
        (member.guild.id,)
    )

    # Invite leave counts are updated separately when the inviter is known.
    # The bot does not guess which invite was used.


@bot.command(aliases=["i", "lb"])
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT regular, leaves FROM invite_counts WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    regular, leaves = row if row else (0, 0)

    await ctx.send(embed=make_embed(
        f"{member.display_name}'s Invites",
        f"Invites: `{regular}`\nLeaves: `{leaves}`"
    ))


@bot.command()
async def inviter(ctx, member: discord.Member):
    await ctx.send(embed=info(
        ctx,
        "Invite tracking records new joins from this point onward. "
        "Previous invite history cannot be recovered."
    ))


@bot.command()
async def inviteinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT regular, leaves FROM invite_counts WHERE guild_id = ? AND user_id = ?",
        (ctx.guild.id, member.id)
    )

    regular, leaves = row if row else (0, 0)

    await ctx.send(embed=make_embed(
        f"Invite Info: {member.display_name}",
        f"Regular Invites: `{regular}`\nLeaves: `{leaves}`"
    ))


@bot.command()
async def topinvites(ctx):
    rows = fetchall(
        "SELECT user_id, regular FROM invite_counts WHERE guild_id = ? ORDER BY regular DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = "\n".join(
        f"`{index}.` <@{user_id}> — `{count}` invites"
        for index, (user_id, count) in enumerate(rows, 1)
    )

    await ctx.send(embed=make_embed(
        "🏆 Invite Leaderboard",
        description or "No invites recorded yet."
    ))


# ---------- REACTION ROLES ----------

@bot.group(invoke_without_command=True)
async def rr(ctx):
    await ctx.send(embed=make_embed(
        "Reaction Roles",
        "`!rr add #channel message_id emoji @role`\n"
        "`!rr remove message_id emoji`\n"
        "`!rr list`"
    ))


@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(
    ctx,
    channel: discord.TextChannel,
    message_id: int,
    emoji: str,
    role: discord.Role
):
    try:
        message = await channel.fetch_message(message_id)
        await message.add_reaction(emoji)

        execute(
            "INSERT INTO reaction_roles (guild_id, channel_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?, ?)",
            (ctx.guild.id, channel.id, message_id, emoji, role.id)
        )

        await ctx.send(embed=success(ctx, f"Reaction role added for {role.mention}."))

    except discord.NotFound:
        await ctx.send(embed=error(ctx, "Message not found."))


@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, *, emoji: str):
    execute(
        "DELETE FROM reaction_roles WHERE guild_id = ? AND message_id = ? AND emoji = ?",
        (ctx.guild.id, message_id, emoji)
    )

    await ctx.send(embed=success(ctx, "Reaction role configuration removed."))


@rr.command(name="list")
async def rr_list(ctx):
    rows = fetchall(
        "SELECT message_id, emoji, role_id FROM reaction_roles WHERE guild_id = ?",
        (ctx.guild.id,)
    )

    description = "\n".join(
        f"Message `{message_id}` — {emoji} — <@&{role_id}>"
        for message_id, emoji, role_id in rows
    )

    await ctx.send(embed=make_embed(
        "Reaction Roles",
        description or "No reaction roles configured."
    ))


@bot.event
async def on_raw_reaction_add(payload):
    if payload.member is None or payload.member.bot:
        return

    row = fetchone(
        "SELECT role_id FROM reaction_roles WHERE guild_id = ? AND message_id = ? AND emoji = ?",
        (payload.guild_id, payload.message_id, str(payload.emoji))
    )

    if row:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(row[0]) if guild else None

        if role:
            try:
                await payload.member.add_roles(role)
            except discord.Forbidden:
                pass


@bot.event
async def on_raw_reaction_remove(payload):
    row = fetchone(
        "SELECT role_id FROM reaction_roles WHERE guild_id = ? AND message_id = ? AND emoji = ?",
        (payload.guild_id, payload.message_id, str(payload.emoji))
    )

    if row:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id) if guild else None
        role = guild.get_role(row[0]) if guild else None

        if member and role:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                pass


# ---------- TICKETS ----------

@bot.command()
@commands.has_permissions(manage_guild=True)
async def ticketsetup(ctx):
    category = await ctx.guild.create_category("VEXORA TICKETS")

    set_setting(ctx.guild.id, "ticket_category", category.id)

    await ctx.send(embed=success(
        ctx,
        f"Ticket category created: **{category.name}**"
    ))


@bot.command()
async def ticket(ctx):
    category_id = get_setting(ctx.guild.id, "ticket_category")

    if not category_id:
        return await ctx.send(embed=error(ctx, "An admin must run `!ticketsetup` first."))

    category = ctx.guild.get_channel(int(category_id))

    if not category:
        return await ctx.send(embed=error(ctx, "Ticket category not found."))

    existing = fetchone(
        "SELECT channel_id FROM tickets WHERE guild_id = ? AND owner_id = ?",
        (ctx.guild.id, ctx.author.id)
    )

    if existing:
        channel = ctx.guild.get_channel(existing[0])
        if channel:
            return await ctx.send(embed=info(ctx, f"You already have a ticket: {channel.mention}"))

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True
        )
    }

    channel = await ctx.guild.create_text_channel(
        f"ticket-{ctx.author.name}".lower()[:90],
        category=category,
        overwrites=overwrites
    )

    execute(
        "INSERT INTO tickets (channel_id, guild_id, owner_id) VALUES (?, ?, ?)",
        (channel.id, ctx.guild.id, ctx.author.id)
    )

    await channel.send(
        embed=make_embed(
            "Support Ticket",
            f"Hello {ctx.author.mention}!\nExplain your issue here.\n"
            "Staff can use `!claim` and `!close`."
        )
    )

    await ctx.send(embed=success(ctx, f"Ticket created: {channel.mention}"))


@bot.command()
@commands.has_permissions(manage_channels=True)
async def claim(ctx):
    row = fetchone(
        "SELECT owner_id FROM tickets WHERE channel_id = ?",
        (ctx.channel.id,)
    )

    if not row:
        return await ctx.send(embed=error(ctx, "This is not a ticket channel."))

    execute(
        "UPDATE tickets SET claimed_by = ? WHERE channel_id = ?",
        (ctx.author.id, ctx.channel.id)
    )

    await ctx.send(embed=success(ctx, f"Ticket claimed by {ctx.author.mention}."))


@bot.command()
async def close(ctx):
    row = fetchone(
        "SELECT owner_id FROM tickets WHERE channel_id = ?",
        (ctx.channel.id,)
    )

    if not row:
        return await ctx.send(embed=error(ctx, "This is not a ticket channel."))

    if ctx.author.id != row[0] and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error(ctx, "Only the ticket owner or staff can close this ticket."))

    execute(
        "DELETE FROM tickets WHERE channel_id = ?",
        (ctx.channel.id,)
    )

    await ctx.send(embed=success(ctx, "Ticket closing in 3 seconds."))
    await asyncio.sleep(3)
    await ctx.channel.delete()


# ---------- SNIPE ----------

sniped_messages = {}


@bot.listen("on_message_delete")
async def save_snipe(message):
    if message.guild and not message.author.bot:
        sniped_messages[message.channel.id] = {
            "author": str(message.author),
            "content": message.content or "No text content.",
            "time": datetime.utcnow()
        }


@bot.command()
async def snipe(ctx):
    data = sniped_messages.get(ctx.channel.id)

    if not data:
        return await ctx.send(embed=error(ctx, "Nothing to snipe."))

    embed = make_embed(
        "Last Deleted Message",
        data["content"][:4000]
    )
    embed.add_field(name="Author", value=data["author"])
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearsnipe(ctx):
    sniped_messages.pop(ctx.channel.id, None)
    await ctx.send(embed=success(ctx, "Snipe history cleared."))


# ---------- GIVEAWAYS ----------

giveaway_tasks = {}


async def finish_giveaway(message_id):
    row = fetchone(
        "SELECT guild_id, channel_id, prize, ended FROM giveaways WHERE message_id = ?",
        (message_id,)
    )

    if not row or row[3]:
        return

    guild_id, channel_id, prize, ended = row

    channel = bot.get_channel(channel_id)

    if not channel:
        return

    try:
        message = await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))
        return

    reaction = discord.utils.get(message.reactions, emoji="🎉")

    if reaction is None:
        winner = None
    else:
        users = [
            user async for user in reaction.users()
            if not user.bot
        ]
        winner = random.choice(users) if users else None

    execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))

    embed = make_embed("🎉 Giveaway Ended", f"Prize: **{prize}**")

    if winner:
        embed.add_field(name="Winner", value=winner.mention)
        await channel.send(embed=embed)
    else:
        embed.add_field(name="Winner", value="No valid entries.")
        await channel.send(embed=embed)


async def giveaway_timer(message_id, delay):
    await asyncio.sleep(delay)
    await finish_giveaway(message_id)
    giveaway_tasks.pop(message_id, None)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, minutes: int, *, prize):
    if minutes < 1 or minutes > 10080:
        return await ctx.send(embed=error(ctx, "Choose between 1 and 10080 minutes."))

    end_time = time.time() + minutes * 60

    embed = make_embed(
        "🎉 GIVEAWAY",
        f"**Prize:** {prize}\n"
        f"**Hosted by:** {ctx.author.mention}\n"
        f"**Duration:** {minutes} minutes\n\n"
        "React with 🎉 to enter!"
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    execute(
        "INSERT INTO giveaways (message_id, guild_id, channel_id, prize, end_time, ended) VALUES (?, ?, ?, ?, ?, 0)",
        (message.id, ctx.guild.id, ctx.channel.id, prize, end_time)
    )

    giveaway_tasks[message.id] = asyncio.create_task(
        giveaway_timer(message.id, minutes * 60)
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    row = fetchone(
        "SELECT ended FROM giveaways WHERE message_id = ? AND guild_id = ?",
        (message_id, ctx.guild.id)
    )

    if not row:
        return await ctx.send(embed=error(ctx, "Giveaway not found."))

    if row[0]:
        return await ctx.send(embed=error(ctx, "Giveaway already ended."))

    task = giveaway_tasks.pop(message_id, None)

    if task:
        task.cancel()

    await finish_giveaway(message_id)
    await ctx.send(embed=success(ctx, "Giveaway ended."))


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gcancel(ctx, message_id: int):
    row = fetchone(
        "SELECT ended FROM giveaways WHERE message_id = ? AND guild_id = ?",
        (message_id, ctx.guild.id)
    )

    if not row:
        return await ctx.send(embed=error(ctx, "Giveaway not found."))

    task = giveaway_tasks.pop(message_id, None)

    if task:
        task.cancel()

    execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))

    await ctx.send(embed=success(ctx, "Giveaway cancelled."))


@bot.command()
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    row = fetchone(
        "SELECT channel_id, prize, ended FROM giveaways WHERE message_id = ? AND guild_id = ?",
        (message_id, ctx.guild.id)
    )

    if not row or not row[2]:
        return await ctx.send(embed=error(ctx, "Giveaway not found or not ended."))

    channel = bot.get_channel(row[0])

    if not channel:
        return await ctx.send(embed=error(ctx, "Giveaway channel not found."))

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        return await ctx.send(embed=error(ctx, "Giveaway message not found."))

    reaction = discord.utils.get(message.reactions, emoji="🎉")

    users = [
        user async for user in reaction.users()
        if not user.bot
    ] if reaction else []

    if not users:
        return await ctx.send(embed=error(ctx, "No valid entries."))

    winner = random.choice(users)

    await ctx.send(embed=make_embed(
        "🎉 Giveaway Rerolled",
        f"New winner: {winner.mention}\nPrize: **{row[1]}**"
    ))


# ---------- FTR: FIRST TO REACT ----------

active_ftr = {}


@bot.group(invoke_without_command=True)
async def ftr(ctx):
    await ctx.send(embed=make_embed(
        "First To React",
        "`!ftr start <seconds>`\n"
        "`!ftr stop`\n"
        "`!ftr winner`\n"
        "`!ftr leaderboard`"
    ))


@ftr.command(name="start")
@commands.has_permissions(manage_guild=True)
async def ftr_start(ctx, seconds: int = 30):
    if seconds < 5 or seconds > 300:
        return await ctx.send(embed=error(ctx, "Choose between 5 and 300 seconds."))

    if ctx.guild.id in active_ftr:
        return await ctx.send(embed=error(ctx, "An FTR event is already running."))

    message = await ctx.send(embed=make_embed(
        "⚡ FIRST TO REACT",
        f"React with 🎯!\nTime limit: `{seconds}` seconds."
    ))

    await message.add_reaction("🎯")

    active_ftr[ctx.guild.id] = {
        "message_id": message.id,
        "winner": None
    }

    def check(reaction, user):
        return (
            reaction.message.id == message.id
            and str(reaction.emoji) == "🎯"
            and not user.bot
        )

    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            timeout=seconds,
            check=check
        )

        active_ftr[ctx.guild.id]["winner"] = user.id

        execute("""
            INSERT INTO ftr_scores (guild_id, user_id, wins)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET wins = wins + 1
        """, (ctx.guild.id, user.id))

        await ctx.send(embed=make_embed(
            "🏆 FTR Winner",
            f"{user.mention} reacted first!"
        ))

    except asyncio.TimeoutError:
        await ctx.send(embed=info(ctx, "FTR ended. Nobody reacted in time."))

    finally:
        active_ftr.pop(ctx.guild.id, None)


@ftr.command(name="stop")
@commands.has_permissions(manage_guild=True)
async def ftr_stop(ctx):
    if ctx.guild.id not in active_ftr:
        return await ctx.send(embed=error(ctx, "No FTR event is running."))

    active_ftr.pop(ctx.guild.id, None)
    await ctx.send(embed=success(ctx, "FTR event stopped."))


@ftr.command(name="winner")
async def ftr_winner(ctx):
    await ctx.send(embed=info(ctx, "The winner is announced automatically when an FTR event ends."))


@ftr.command(name="leaderboard")
async def ftr_leaderboard(ctx):
    rows = fetchall(
        "SELECT user_id, wins FROM ftr_scores WHERE guild_id = ? ORDER BY wins DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = "\n".join(
        f"`{index}.` <@{user_id}> — `{wins}` wins"
        for index, (user_id, wins) in enumerate(rows, 1)
    )

    await ctx.send(embed=make_embed(
        "🏆 FTR Leaderboard",
        description or "No FTR wins yet."
    ))


# ---------- BOT STATUS ----------

@bot.command()
@owner_only()
async def playing(ctx, *, text):
    await bot.change_presence(
        activity=discord.Game(name=text)
    )
    await ctx.send(embed=success(ctx, f"Playing status changed to **{text}**."))


@bot.command()
@owner_only()
async def stext(ctx, *, text):
    await bot.change_presence(
        activity=discord.CustomActivity(name=text)
    )
    await ctx.send(embed=success(ctx, f"Custom status changed to **{text}**."))


@bot.command()
@owner_only()
async def status(ctx, state: str):
    statuses = {
        "online": discord.Status.online,
        "offline": discord.Status.invisible,
        "dnd": discord.Status.dnd,
        "sleep": discord.Status.idle
    }

    state = state.lower()

    if state not in statuses:
        return await ctx.send(embed=error(
            ctx,
            "Choose: `online`, `offline`, `dnd`, or `sleep`."
        ))

    await bot.change_presence(status=statuses[state])

    await ctx.send(embed=success(ctx, f"Bot status changed to **{state}**."))


# ---------- GLOBAL ANNOUNCEMENTS ----------

pending_announcement = None


@bot.command()
@owner_only()
async def announce(ctx, *, message):
    global pending_announcement

    pending_announcement = message

    await ctx.send(embed=make_embed(
        "Announcement Preview",
        f"{message}\n\nUse `!announceconfirm` to send or `!announcecancel` to cancel."
    ))


@bot.command()
@owner_only()
async def announceconfirm(ctx):
    global pending_announcement

    if not pending_announcement:
        return await ctx.send(embed=error(ctx, "No announcement is waiting."))

    message = pending_announcement
    pending_announcement = None

    sent = 0

    for guild in bot.guilds:
        channel = guild.system_channel

        if channel is None:
            channel = next(
                (
                    c for c in guild.text_channels
                    if c.permissions_for(guild.me).send_messages
                ),
                None
            )

        if channel:
            try:
                await channel.send(embed=make_embed("📢 VEXORA Announcement", message))
                sent += 1
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

    await ctx.send(embed=success(ctx, f"Announcement sent to `{sent}` servers."))


@bot.command()
@owner_only()
async def announcecancel(ctx):
    global pending_announcement

    pending_announcement = None

    await ctx.send(embed=success(ctx, "Announcement cancelled."))


# ---------- HELP ----------

@bot.command()
async def help(ctx, *, command_name=None):
    if command_name:
        command = bot.get_command(command_name)

        if not command:
            return await ctx.send(embed=error(ctx, "Command not found."))

        embed = make_embed(
            f"Help: {command.qualified_name}",
            command.help or "No description available."
        )

        embed.add_field(
            name="Usage",
            value=f"`{PREFIXES[0]}{command.signature}`"
        )

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{a}`" for a in command.aliases)
            )

        return await ctx.send(embed=embed)

    categories = {
        "General": ["ping", "botinfo", "serverinfo", "userinfo", "avatar", "support"],
        "Moderation": ["ban", "modkick", "unban", "timeout", "untimeout", "purge", "lock", "unlock", "slowmode", "warn", "warnings", "clearwarns", "staff"],
        "Levels & Reputation": ["rank", "levels", "rep", "reps", "repboard"],
        "Premium": ["premium", "cc"],
        "Social": ["afk", "confess", "confessionset", "suggest", "suggestionset", "poll"],
        "Fun": ["kiss", "punch", "kick"],
        "Invites": ["invites", "inviter", "inviteinfo", "topinvites"],
        "Reaction Roles": ["rr"],
        "Tickets": ["ticketsetup", "ticket", "claim", "close"],
        "Giveaways": ["gstart", "gend", "gcancel", "greroll"],
        "Other": ["snipe", "clearsnipe", "ftr"]
    }

    embed = make_embed(
        "VEXORA Help",
        "**One Bot. Endless Possibilities.**\n"
        "Use `!help command` for command details."
    )

    for category, names in categories.items():
        available = [
            f"`{name}`"
            for name in names
            if bot.get_command(name)
        ]

        if available:
            embed.add_field(
                name=category,
                value=" • ".join(available),
                inline=False
            )

    embed.set_footer(text="Prefixes: !  ?  .  $  -")

    await ctx.send(embed=embed)


# ---------- ERROR HANDLER ----------

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(embed=error_embed(
            "Missing argument. Use `!help command` to see the correct usage."
        ))

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send(embed=error_embed(
            "You don't have permission to use this command."
        ))

    if isinstance(error, commands.BotMissingPermissions):
        return await ctx.send(embed=error_embed(
            "VEXORA is missing the required permissions."
        ))

    if isinstance(error, commands.MemberNotFound):
        return await ctx.send(embed=error_embed("Member not found."))

    if isinstance(error, commands.UserNotFound):
        return await ctx.send(embed=error_embed("User not found."))

    if isinstance(error, commands.BadArgument):
        return await ctx.send(embed=error_embed("Invalid argument."))

    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=error_embed(
            f"Try again in {error.retry_after:.1f} seconds."
        ))

    if isinstance(error, commands.CheckFailure):
        return await ctx.send(embed=error_embed(
            "You are not allowed to use this command."
        ))

    print(f"Command error: {repr(error)}")

    await ctx.send(embed=error_embed(
        "Something went wrong. Check the Railway logs for the error."
    ))


def error_embed(message):
    return make_embed("✕ Error", message)


# ---------- START BOT ----------

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing. Add BOT_TOKEN in Railway Variables."
    )

bot.run(TOKEN)
