
import discord
from discord.ext import commands
import os
import random
import sqlite3
import time
import asyncio
import datetime
import re

# ==========================================
# VEXORA CONFIGURATION
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1495419933943922920

SUPPORT_SERVER = "https://discord.gg/ZBaRByVFBC"

PREFIXES = ["!", "?", ".", "$", "-"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.reactions = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

COLOR = discord.Color.from_rgb(175, 175, 175)

def embed(title, description=None):
    e = discord.Embed(
        title=title,
        description=description,
        color=COLOR
    )
    e.set_footer(
        text="VEXORA • One Bot. Endless Possibilities."
    )
    return e

async def success(ctx, message):
    await ctx.send(embed=embed("SUCCESS", "✅ " + message))

async def error(ctx, message):
    await ctx.send(embed=embed("ERROR", "❌ " + message))

async def info(ctx, message):
    await ctx.send(embed=embed("VEXORA", message))


# ==========================================
# DATABASE
# ==========================================

db = sqlite3.connect("vexora.db")
db.row_factory = sqlite3.Row

def execute(query, params=()):
    cur = db.cursor()
    cur.execute(query, params)
    db.commit()
    return cur

def fetchone(query, params=()):
    return execute(query, params).fetchone()

def fetchall(query, params=()):
    return execute(query, params).fetchall()

db.executescript("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS premium (
    guild_id INTEGER PRIMARY KEY,
    expires INTEGER
);

CREATE TABLE IF NOT EXISTS economy (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    daily INTEGER DEFAULT 0,
    weekly INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reputation (
    guild_id INTEGER,
    user_id INTEGER,
    reps INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);
""")
db.commit()


# ==========================================
# PERMISSION CHECKS
# ==========================================

def owner_only():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def staff_only():
    async def predicate(ctx):
        return (
            ctx.author.id == OWNER_ID
            or ctx.author.guild_permissions.manage_messages
            or ctx.author.guild_permissions.administrator
        )
    return commands.check(predicate)

async def is_premium(guild_id):
    row = fetchone(
        "SELECT expires FROM premium WHERE guild_id=?",
        (guild_id,)
    )

    if not row:
        return False

    expires = row["expires"]

    if expires == 0:
        return True

    if expires <= int(time.time()):
        execute(
            "DELETE FROM premium WHERE guild_id=?",
            (guild_id,)
        )
        return False

    return True

def get_balance(user_id):
    row = fetchone(
        "SELECT balance FROM economy WHERE user_id=?",
        (user_id,)
    )

    if not row:
        execute(
            "INSERT INTO economy (user_id, balance) VALUES (?, 0)",
            (user_id,)
        )
        return 0

    return row["balance"]


# ==========================================
# EVENTS
# ==========================================

@bot.event
async def on_ready():
    print("================================")
    print(f"VEXORA ONLINE: {bot.user}")
    print(f"BOT ID: {bot.user.id}")
    print(f"SERVERS: {len(bot.guilds)}")
    print("================================")


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandNotFound):
        return

    if isinstance(err, commands.MissingRequiredArgument):
        return await error(
            ctx,
            f"Missing argument: `{err.param.name}`"
        )

    if isinstance(err, commands.MissingPermissions):
        return await error(
            ctx,
            "You don't have the required permissions."
        )

    if isinstance(err, commands.NotOwner):
        return await error(
            ctx,
            "Only the bot owner can use this command."
        )

    if isinstance(err, commands.CheckFailure):
        return await error(ctx, "You cannot use this command.")

    if isinstance(err, commands.CommandOnCooldown):
        return await error(
            ctx,
            f"Try again in {err.retry_after:.1f} seconds."
        )

    print("COMMAND ERROR:", repr(err))
    await error(ctx, "Something went wrong. Check Railway logs.")


# ==========================================
# GENERAL COMMANDS
# ==========================================

@bot.command()
async def ping(ctx):
    ms = round(bot.latency * 1000)
    await ctx.send(embed=embed("PONG", f"🏓 `{ms}ms`"))

@bot.command()
async def botinfo(ctx):
    e = embed(
        "VEXORA INFORMATION",
        "One Bot. Endless Possibilities."
    )
    e.add_field(name="Servers", value=len(bot.guilds))
    e.add_field(name="Users", value=len(bot.users))
    e.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms")
    await ctx.send(embed=e)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    e = embed("SERVER INFORMATION")
    e.add_field(name="Name", value=g.name)
    e.add_field(name="Members", value=g.member_count)
    e.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown")
    e.add_field(name="Created", value=g.created_at.strftime("%d %b %Y"))
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    await ctx.send(embed=e)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = embed("USER INFORMATION")
    e.add_field(name="Username", value=str(member))
    e.add_field(name="ID", value=member.id)
    e.add_field(name="Joined", value=member.joined_at.strftime("%d %b %Y") if member.joined_at else "Unknown")
    e.add_field(name="Created", value=member.created_at.strftime("%d %b %Y"))
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = embed(f"{member.display_name}'s Avatar")
    e.set_image(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def support(ctx):
    await ctx.send(
        embed=embed(
            "VEXORA SUPPORT",
            f"[Join our support server]({SUPPORT_SERVER})"
        )
    )


# ==========================================
# MODERATION
# ==========================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await success(ctx, f"{member} has been banned.\nReason: {reason}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def modkick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await success(ctx, f"{member} has been kicked.\nReason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await success(ctx, f"Unbanned {user}.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    if minutes < 1 or minutes > 40320:
        return await error(ctx, "Choose between 1 and 40320 minutes.")

    await member.timeout(
        datetime.timedelta(minutes=minutes),
        reason=reason
    )
    await success(ctx, f"{member.mention} timed out for {minutes} minutes.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await success(ctx, f"Timeout removed for {member.mention}.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        return await error(ctx, "Choose between 1 and 100 messages.")

    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(
        embed=embed("PURGED", f"Deleted `{len(deleted) - 1}` messages.")
    )
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=False
    )
    await success(ctx, "Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=True
    )
    await success(ctx, "Channel unlocked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if seconds < 0 or seconds > 21600:
        return await error(ctx, "Choose 0–21600 seconds.")

    await ctx.channel.edit(slowmode_delay=seconds)
    await success(ctx, f"Slowmode set to {seconds} seconds.")


# ==========================================
# WARNINGS
# ==========================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    execute(
        "INSERT INTO warnings (guild_id,user_id,moderator_id,reason) VALUES (?,?,?,?)",
        (ctx.guild.id, member.id, ctx.author.id, reason)
    )
    await success(ctx, f"{member.mention} has been warned.\nReason: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    rows = fetchall(
        "SELECT reason, moderator_id FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    e = embed(f"WARNINGS: {member}")
    if not rows:
        e.description = "No warnings found."
    else:
        for i, row in enumerate(rows, 1):
            e.add_field(
                name=f"Warning {i}",
                value=f"{row['reason']}\nModerator ID: {row['moderator_id']}",
                inline=False
            )
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    execute(
        "DELETE FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )
    await success(ctx, f"Cleared warnings for {member}.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def staff(ctx):
    members = [
        m for m in ctx.guild.members
        if m.guild_permissions.manage_messages
        or m.guild_permissions.administrator
    ]

    e = embed("SERVER STAFF")
    e.description = "\n".join(m.mention for m in members[:50]) or "No staff found."
    await ctx.send(embed=e)


# ==========================================
# PREMIUM MANAGEMENT
# ==========================================

@bot.group(invoke_without_command=True)
async def premium(ctx):
    active = await is_premium(ctx.guild.id)
    await ctx.send(
        embed=embed(
            "PREMIUM STATUS",
            "⭐ Premium is active." if active
            else "Premium is not active on this server."
        )
    )

@premium.command(name="add")
@owner_only()
async def premium_add(ctx, guild_id: int, days: int = 0):
    if days < 0:
        return await error(ctx, "Days cannot be negative.")

    expires = 0 if days == 0 else int(time.time()) + days * 86400

    execute(
        "INSERT OR REPLACE INTO premium (guild_id,expires) VALUES (?,?)",
        (guild_id, expires)
    )
    await success(
        ctx,
        f"Premium granted to server `{guild_id}`."
        + (" Lifetime." if days == 0 else f" For {days} days.")
    )

@premium.command(name="remove")
@owner_only()
async def premium_remove(ctx, guild_id: int):
    execute("DELETE FROM premium WHERE guild_id=?", (guild_id,))
    await success(ctx, f"Premium removed from `{guild_id}`.")

@premium.command(name="check")
@owner_only()
async def premium_check(ctx, guild_id: int):
    active = await is_premium(guild_id)
    await info(ctx, f"Server `{guild_id}` premium: `{active}`")

@premium.command(name="list")
@owner_only()
async def premium_list(ctx):
    rows = fetchall("SELECT guild_id, expires FROM premium")

    e = embed("PREMIUM SERVERS")
    if not rows:
        e.description = "No premium servers."
    else:
        for row in rows:
            expiry = "Lifetime" if row["expires"] == 0 else f"<t:{row['expires']}:R>"
            e.add_field(
                name=str(row["guild_id"]),
                value=expiry,
                inline=False
            )
    await ctx.send(embed=e)


# ==========================================
# ECONOMY
# ==========================================

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    amount = get_balance(member.id)
    await ctx.send(
        embed=embed("VEX BALANCE", f"{member.mention} has **{amount} VEX**.")
    )

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    row = fetchone(
        "SELECT daily FROM economy WHERE user_id=?",
        (ctx.author.id,)
    )
    get_balance(ctx.author.id)

    reward = 250
    execute(
        "UPDATE economy SET balance=balance+?, daily=? WHERE user_id=?",
        (reward, int(time.time()), ctx.author.id)
    )
    await success(ctx, f"You collected **{reward} VEX** daily.")

@bot.command()
@commands.cooldown(1, 604800, commands.BucketType.user)
async def weekly(ctx):
    get_balance(ctx.author.id)
    reward = 1000
    execute(
        "UPDATE economy SET balance=balance+?, weekly=? WHERE user_id=?",
        (reward, int(time.time()), ctx.author.id)
    )
    await success(ctx, f"You collected **{reward} VEX** weekly.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    reward = random.randint(30, 100)
    get_balance(ctx.author.id)
    execute(
        "UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id)
    )
    await success(ctx, f"You worked and earned **{reward} VEX**.")

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    reward = random.randint(5, 30)
    get_balance(ctx.author.id)
    execute(
        "UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id)
    )
    await success(ctx, f"Someone gave you **{reward} VEX**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await error(ctx, "Amount must be positive.")

    if member.bot or member.id == ctx.author.id:
        return await error(ctx, "Choose another member.")

    get_balance(ctx.author.id)
    get_balance(member.id)

    db.execute("BEGIN IMMEDIATE")
    try:
        sender = db.execute(
            "SELECT balance FROM economy WHERE user_id=?",
            (ctx.author.id,)
        ).fetchone()

        if sender["balance"] < amount:
            db.rollback()
            return await error(ctx, "You don't have enough VEX.")

        db.execute(
            "UPDATE economy SET balance=balance-? WHERE user_id=?",
            (amount, ctx.author.id)
        )
        db.execute(
            "UPDATE economy SET balance=balance+? WHERE user_id=?",
            (amount, member.id)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    await success(ctx, f"Sent **{amount} VEX** to {member.mention}.")

@bot.command()
async def leaderboard(ctx):
    rows = fetchall(
        "SELECT user_id,balance FROM economy ORDER BY balance DESC LIMIT 10"
    )

    e = embed("VEX LEADERBOARD")
    e.description = "\n".join(
        f"**{i}.** <@{r['user_id']}> — {r['balance']} VEX"
        for i, r in enumerate(rows, 1)
    ) or "No users yet."

    await ctx.send(embed=e)


# ==========================================
# SIMPLE GAMES
# ==========================================

@bot.command()
async def dice(ctx):
    result = random.randint(1, 6)
    await ctx.send(embed=embed("DICE", f"🎲 You rolled **{result}**!"))

@bot.command()
async def flip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(embed=embed("COIN FLIP", f"🪙 **{result}**"))

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    options = ["rock", "paper", "scissors"]

    if choice not in options:
        return await error(ctx, "Choose rock, paper or scissors.")

    bot_choice = random.choice(options)

    if choice == bot_choice:
        result = "It's a tie!"
    elif (
        (choice == "rock" and bot_choice == "scissors")
        or (choice == "paper" and bot_choice == "rock")
        or (choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win!"
    else:
        result = "I win!"

    await ctx.send(
        embed=embed(
            "ROCK PAPER SCISSORS",
            f"You: **{choice}**\nVEXORA: **{bot_choice}**\n\n{result}"
        )
    )


# ==========================================
# REPUTATION
# ==========================================

@bot.command()
async def rep(ctx, member: discord.Member):
    if member.bot or member.id == ctx.author.id:
        return await error(ctx, "You cannot give reputation to yourself or a bot.")

    execute(
        "INSERT OR IGNORE INTO reputation (guild_id,user_id,reps) VALUES (?,?,0)",
        (ctx.guild.id, member.id)
    )

    execute(
        "UPDATE reputation SET reps=reps+1 WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )
    await success(ctx, f"Gave reputation to {member.mention}.")

@bot.command()
async def reps(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT reps FROM reputation WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    amount = row["reps"] if row else 0
    await info(ctx, f"{member.mention} has **{amount} reputation**.")


# ==========================================
# LEVEL SYSTEM
# ==========================================

@bot.listen("on_message")
async def level_listener(message):
    if message.author.bot or not message.guild:
        return

    row = fetchone(
        "SELECT xp,level FROM levels WHERE guild_id=? AND user_id=?",
        (message.guild.id, message.author.id)
    )

    if not row:
        execute(
            "INSERT INTO levels (guild_id,user_id,xp,level) VALUES (?,?,0,0)",
            (message.guild.id, message.author.id)
        )
        xp = 0
        level = 0
    else:
        xp = row["xp"]
        level = row["level"]

    xp += random.randint(5, 15)
    needed = (level + 1) * 100

    if xp >= needed:
        xp -= needed
        level += 1
        await message.channel.send(
            embed=embed(
                "LEVEL UP!",
                f"{message.author.mention} reached level **{level}**!"
            )
        )

    execute(
        "UPDATE levels SET xp=?,level=? WHERE guild_id=? AND user_id=?",
        (xp, level, message.guild.id, message.author.id)
    )

@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT xp,level FROM levels WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    xp = row["xp"] if row else 0
    level = row["level"] if row else 0

    await ctx.send(
        embed=embed(
            "RANK CARD",
            f"**{member.display_name}**\nLevel: `{level}`\nXP: `{xp}/{(level + 1) * 100}`"
        )
    )

@bot.command()
async def level(ctx, member: discord.Member = None):
    await rank.callback(ctx, member)
    
# ==========================================
# AFK SYSTEM
# ==========================================

afk_users = {}

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await success(ctx, f"You are now AFK: {reason}")

@bot.listen("on_message")
async def afk_listener(message):
    if message.author.bot:
        return

    if message.author.id in afk_users:
        afk_users.pop(message.author.id, None)
        try:
            await message.channel.send(
                embed=embed("WELCOME BACK", f"{message.author.mention}, your AFK status was removed.")
            )
        except discord.HTTPException:
            pass

    for user in message.mentions:
        if user.id in afk_users:
            await message.channel.send(
                embed=embed("AFK USER", f"{user.mention} is AFK: {afk_users[user.id]}")
            )


# ==========================================
# CONFESSIONS
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS confessions (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER
);
CREATE TABLE IF NOT EXISTS suggestions (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER
);
""")
db.commit()

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confesssetup(ctx, channel: discord.TextChannel):
    execute(
        "INSERT OR REPLACE INTO confessions VALUES (?,?)",
        (ctx.guild.id, channel.id)
    )
    await success(ctx, f"Confessions channel set to {channel.mention}.")

@bot.command()
async def confess(ctx, *, message):
    row = fetchone(
        "SELECT channel_id FROM confessions WHERE guild_id=?",
        (ctx.guild.id,)
    )
    if not row:
        return await error(ctx, "Confessions are not configured.")

    channel = ctx.guild.get_channel(row["channel_id"])
    if not channel:
        return await error(ctx, "Configured channel no longer exists.")

    e = embed("ANONYMOUS CONFESSION", message)
    e.add_field(name="Server", value=ctx.guild.name)
    await channel.send(embed=e)
    await success(ctx, "Your confession was submitted.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confessionsoff(ctx):
    execute("DELETE FROM confessions WHERE guild_id=?", (ctx.guild.id,))
    await success(ctx, "Confessions disabled.")


# ==========================================
# SUGGESTIONS
# ==========================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def suggestsetup(ctx, channel: discord.TextChannel):
    execute(
        "INSERT OR REPLACE INTO suggestions VALUES (?,?)",
        (ctx.guild.id, channel.id)
    )
    await success(ctx, f"Suggestions channel set to {channel.mention}.")

@bot.command()
async def suggest(ctx, *, message):
    row = fetchone(
        "SELECT channel_id FROM suggestions WHERE guild_id=?",
        (ctx.guild.id,)
    )
    if not row:
        return await error(ctx, "Suggestions are not configured.")

    channel = ctx.guild.get_channel(row["channel_id"])
    if not channel:
        return await error(ctx, "Suggestion channel not found.")

    e = embed("NEW SUGGESTION", message)
    e.add_field(name="Suggested by", value=ctx.author.mention)
    msg = await channel.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await success(ctx, "Suggestion submitted.")


# ==========================================
# POLLS
# ==========================================

@bot.command()
async def poll(ctx, *, question):
    e = embed("📊 POLL", question)
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# ==========================================
# ANIME FUN COMMANDS
# ==========================================

ANIME_GIFS = {
    "kiss": [
        "https://klipy.com/gifs/shirayuki-zen-kiss-anime",
        "https://klipy.com/gifs/hells-paradise-yui"
    ],
    "punch": [
        "https://klipy.com/gifs/anime-punch-28",
        "https://klipy.com/gifs/spy-x-family-anya-forger-51"
    ],
    "kick": [
        "https://klipy.com/gifs/asdf-movie-20",
        "https://klipy.com/gifs/kick-angry-3"
    ]
}

async def anime_action(ctx, member, action):
    gif = random.choice(ANIME_GIFS[action])
    e = embed(
        f"{action.upper()}!",
        f"{ctx.author.mention} {action}s {member.mention}!\n[View anime GIF]({gif})"
    )
    await ctx.send(embed=e)

@bot.command()
async def kiss(ctx, member: discord.Member):
    await anime_action(ctx, member, "kiss")

@bot.command()
async def punch(ctx, member: discord.Member):
    await anime_action(ctx, member, "punch")

@bot.command()
async def kick(ctx, member: discord.Member):
    await anime_action(ctx, member, "kick")


# ==========================================
# GIVEAWAYS
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS giveaways (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    prize TEXT,
    winners INTEGER,
    end_time INTEGER,
    ended INTEGER DEFAULT 0
);
""")
db.commit()

giveaway_tasks = {}

def parse_duration(value):
    match = re.fullmatch(r"(\d+)([smhd])", value.lower())
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    seconds = amount * {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }[unit]

    if seconds < 10 or seconds > 2592000:
        return None

    return seconds

async def finish_giveaway(message_id):
    row = fetchone(
        "SELECT * FROM giveaways WHERE message_id=? AND ended=0",
        (message_id,)
    )
    if not row:
        return

    channel = bot.get_channel(row["channel_id"])
    if not channel:
        return

    try:
        msg = await channel.fetch_message(message_id)
        users = [
            user async for user in msg.reactions[0].users()
            if not user.bot
        ]

        winners = random.sample(
            users,
            min(len(users), row["winners"])
        ) if users else []

        winner_text = ", ".join(w.mention for w in winners) if winners else "No valid entries."

        e = embed("GIVEAWAY ENDED", f"Prize: **{row['prize']}**\nWinners: {winner_text}")
        await channel.send(embed=e)

    except discord.HTTPException:
        pass

    execute(
        "UPDATE giveaways SET ended=1 WHERE message_id=?",
        (message_id,)
    )

async def giveaway_timer(message_id, end_time):
    await asyncio.sleep(max(0, end_time - int(time.time())))
    await finish_giveaway(message_id)
    giveaway_tasks.pop(message_id, None)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, winners: int, *, prize):
    seconds = parse_duration(duration)

    if not seconds:
        return await error(ctx, "Use 10s, 5m, 2h or 1d. Maximum 30 days.")

    if winners < 1 or winners > 20:
        return await error(ctx, "Choose 1–20 winners.")

    end_time = int(time.time()) + seconds

    e = embed(
        "🎉 GIVEAWAY",
        f"Prize: **{prize}**\nWinners: `{winners}`\nEnds: <t:{end_time}:R>\nReact with 🎉 to enter!"
    )

    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎉")

    execute(
        "INSERT INTO giveaways (message_id,guild_id,channel_id,prize,winners,end_time) VALUES (?,?,?,?,?,?)",
        (msg.id, ctx.guild.id, ctx.channel.id, prize, winners, end_time)
    )

    giveaway_tasks[msg.id] = asyncio.create_task(
        giveaway_timer(msg.id, end_time)
    )

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    task = giveaway_tasks.pop(message_id, None)
    if task:
        task.cancel()
    await finish_giveaway(message_id)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gcancel(ctx, message_id: int):
    execute(
        "UPDATE giveaways SET ended=1 WHERE message_id=?",
        (message_id,)
    )
    task = giveaway_tasks.pop(message_id, None)
    if task:
        task.cancel()
    await success(ctx, "Giveaway cancelled.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    row = fetchone(
        "SELECT * FROM giveaways WHERE message_id=? AND ended=1",
        (message_id,)
    )
    if not row:
        return await error(ctx, "Ended giveaway not found.")

    channel = bot.get_channel(row["channel_id"])
    if not channel:
        return await error(ctx, "Channel not found.")

    try:
        msg = await channel.fetch_message(message_id)
        users = [
            user async for user in msg.reactions[0].users()
            if not user.bot
        ]
        if not users:
            return await error(ctx, "No eligible entries.")

        winner = random.choice(users)
        await channel.send(
            embed=embed("GIVEAWAY REROLL", f"New winner: {winner.mention}")
        )
    except discord.HTTPException:
        await error(ctx, "Could not retrieve giveaway entries.")


# ==========================================
# INVITE TRACKING
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS invites (
    guild_id INTEGER,
    user_id INTEGER,
    inviter_id INTEGER
);
""")
db.commit()

invite_cache = {}

@bot.event
async def on_ready():
    print(f"VEXORA ready: {bot.user}")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = {
                inv.code: inv.uses
                for inv in await guild.invites()
            }
        except discord.Forbidden:
            pass

    for row in fetchall("SELECT message_id,end_time FROM giveaways WHERE ended=0"):
        if row["message_id"] not in giveaway_tasks:
            giveaway_tasks[row["message_id"]] = asyncio.create_task(
                giveaway_timer(row["message_id"], row["end_time"])
            )

@bot.event
async def on_invite_create(invite):
    try:
        invite_cache[invite.guild.id] = {
            inv.code: inv.uses
            for inv in await invite.guild.invites()
        }
    except discord.Forbidden:
        pass

@bot.event
async def on_member_join(member):
    try:
        invites = await member.guild.invites()
        old = invite_cache.get(member.guild.id, {})
        used = next(
            (inv for inv in invites if inv.uses > old.get(inv.code, 0)),
            None
        )

        invite_cache[member.guild.id] = {
            inv.code: inv.uses for inv in invites
        }

        if used and used.inviter:
            execute(
                "INSERT INTO invites (guild_id,user_id,inviter_id) VALUES (?,?,?)",
                (member.guild.id, member.id, used.inviter.id)
            )
    except discord.Forbidden:
        pass

@bot.command(name="invites", aliases=["i", "I", "lb"])
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = fetchone(
        "SELECT COUNT(*) AS total FROM invites WHERE guild_id=? AND inviter_id=?",
        (ctx.guild.id, member.id)
    )

    await info(ctx, f"{member.mention} has `{row['total']}` tracked invites.")

@bot.command()
async def inviter(ctx, member: discord.Member):
    row = fetchone(
        "SELECT inviter_id FROM invites WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    if not row:
        return await info(ctx, "Inviter not found.")

    await info(ctx, f"{member.mention} was invited by <@{row['inviter_id']}>.")

@bot.command()
async def topinvites(ctx):
    rows = fetchall(
        "SELECT inviter_id,COUNT(*) AS total FROM invites WHERE guild_id=? GROUP BY inviter_id ORDER BY total DESC LIMIT 10",
        (ctx.guild.id,)
    )

    e = embed("INVITE LEADERBOARD")
    e.description = "\n".join(
        f"**{i}.** <@{r['inviter_id']}> — {r['total']}"
        for i, r in enumerate(rows, 1)
    ) or "No invites tracked."

    await ctx.send(embed=e)


# ==========================================
# REACTION ROLES
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS reaction_roles (
    message_id INTEGER,
    emoji TEXT,
    role_id INTEGER,
    PRIMARY KEY (message_id,emoji)
);
""")
db.commit()

@bot.group(invoke_without_command=True)
async def rr(ctx):
    await info(ctx, "Use `!rr add`, `!rr remove` or `!rr list`.")

@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(ctx, message_id: int, emoji: str, role: discord.Role):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.add_reaction(emoji)
    except (discord.HTTPException, discord.NotFound):
        return await error(ctx, "Could not find message or add reaction.")

    execute(
        "INSERT OR REPLACE INTO reaction_roles VALUES (?,?,?)",
        (message_id, emoji, role.id)
    )
    await success(ctx, f"Reaction role added for {role.mention}.")

@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, emoji: str):
    execute(
        "DELETE FROM reaction_roles WHERE message_id=? AND emoji=?",
        (message_id, emoji)
    )
    await success(ctx, "Reaction role removed.")

@bot.listen("on_raw_reaction_add")
async def reaction_role_add(payload):
    if payload.member is None or payload.member.bot:
        return

    row = fetchone(
        "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
        (payload.message_id, str(payload.emoji))
    )
    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = guild.get_role(row["role_id"])
    member = guild.get_member(payload.user_id)

    if role and member:
        try:
            await member.add_roles(role)
        except discord.HTTPException:
            pass

@bot.listen("on_raw_reaction_remove")
async def reaction_role_remove(payload):
    row = fetchone(
        "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
        (payload.message_id, str(payload.emoji))
    )
    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = guild.get_role(row["role_id"])
    member = guild.get_member(payload.user_id)

    if role and member and not member.bot:
        try:
            await member.remove_roles(role)
        except discord.HTTPException:
            pass


# ==========================================
# TICKETS
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    claimed_by INTEGER
);
CREATE TABLE IF NOT EXISTS server_settings (
    guild_id INTEGER PRIMARY KEY,
    ticket_category INTEGER
);
""")
db.commit()

@bot.command()
@commands.has_permissions(manage_guild=True)
async def ticketsetup(ctx, category: discord.CategoryChannel):
    execute(
        "INSERT OR REPLACE INTO server_settings VALUES (?,?)",
        (ctx.guild.id, category.id)
    )
    await success(ctx, f"Ticket category set to {category.name}.")

@bot.command()
async def ticket(ctx):
    row = fetchone(
        "SELECT ticket_category FROM server_settings WHERE guild_id=?",
        (ctx.guild.id,)
    )
    if not row:
        return await error(ctx, "Tickets are not configured.")

    category = ctx.guild.get_channel(row["ticket_category"])
    if not isinstance(category, discord.CategoryChannel):
        return await error(ctx, "Ticket category not found.")

    existing = fetchone(
        "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    )
    if existing:
        channel = ctx.guild.get_channel(existing["channel_id"])
        if channel:
            return await error(ctx, f"You already have {channel.mention}.")

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

    for role in ctx.guild.roles:
        if role.permissions.manage_channels:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

    channel = await ctx.guild.create_text_channel(
        f"ticket-{ctx.author.name}",
        category=category,
        overwrites=overwrites
    )

    execute(
        "INSERT INTO tickets VALUES (?,?,?,NULL)",
        (channel.id, ctx.guild.id, ctx.author.id)
    )

    await channel.send(
        embed=embed("SUPPORT TICKET", f"{ctx.author.mention}, describe your issue.\nUse `!claim` or `!close`.")
    )
    await success(ctx, f"Ticket created: {channel.mention}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def claim(ctx):
    row = fetchone("SELECT * FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    if not row:
        return await error(ctx, "This is not a ticket.")

    execute(
        "UPDATE tickets SET claimed_by=? WHERE channel_id=?",
        (ctx.author.id, ctx.channel.id)
    )
    await success(ctx, f"Ticket claimed by {ctx.author.mention}.")

@bot.command()
async def close(ctx):
    row = fetchone("SELECT * FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    if not row:
        return await error(ctx, "This is not a ticket.")

    if ctx.author.id != row["user_id"] and not ctx.author.guild_permissions.manage_channels:
        return await error(ctx, "You cannot close this ticket.")

    execute("DELETE FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    await success(ctx, "Ticket closing in 3 seconds.")
    await asyncio.sleep(3)
    await ctx.channel.delete()


# ==========================================
# SNIPER
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS snipes (
    channel_id INTEGER PRIMARY KEY,
    author_id INTEGER,
    content TEXT,
    deleted_at INTEGER
);
""")
db.commit()

@bot.event
async def on_message_delete(message):
    if message.guild and not message.author.bot and message.content:
        execute(
            "INSERT OR REPLACE INTO snipes VALUES (?,?,?,?)",
            (message.channel.id, message.author.id, message.content, int(time.time()))
        )

@bot.command(name="s")
async def snipe(ctx):
    row = fetchone("SELECT * FROM snipes WHERE channel_id=?", (ctx.channel.id,))
    if not row:
        return await info(ctx, "Nothing to snipe.")

    await ctx.send(
        embed=embed(
            "LAST DELETED MESSAGE",
            f"Author: <@{row['author_id']}>\nMessage: {row['content']}"
        )
    )

@bot.command()
async def cs(ctx):
    execute("DELETE FROM snipes WHERE channel_id=?", (ctx.channel.id,))
    await success(ctx, "Snipe cleared.")


# ==========================================
# ANNOUNCEMENTS
# ==========================================

pending_announcement = {}

@bot.command()
@owner_only()
async def announce(ctx, *, message):
    pending_announcement[ctx.author.id] = message

    await ctx.send(
        embed=embed(
            "ANNOUNCEMENT PREVIEW",
            message + "\n\nUse `!announceconfirm` to send or `!announcecancel` to cancel."
        )
    )

@bot.command()
@owner_only()
async def announceconfirm(ctx):
    message = pending_announcement.pop(ctx.author.id, None)
    if not message:
        return await error(ctx, "No pending announcement.")

    sent = 0
    for guild in bot.guilds:
        channel = guild.system_channel

        if not channel:
            channel = next(
                (
                    c for c in guild.text_channels
                    if c.permissions_for(guild.me).send_messages
                ),
                None
            )

        if channel:
            try:
                await channel.send(
                    embed=embed("VEXORA ANNOUNCEMENT", message),
                    allowed_mentions=discord.AllowedMentions.none()
                )
                sent += 1
            except discord.HTTPException:
                pass

    await success(ctx, f"Announcement sent to {sent} servers.")

@bot.command()
@owner_only()
async def announcecancel(ctx):
    pending_announcement.pop(ctx.author.id, None)
    await success(ctx, "Announcement cancelled.")


# ==========================================
# FIRST TO REACT
# ==========================================

ftr_games = {}

@bot.command()
@commands.has_permissions(manage_guild=True)
async def ftr(ctx, action="start", seconds: int = 15):
    action = action.lower()

    if action == "start":
        if ctx.channel.id in ftr_games:
            return await error(ctx, "A game is already running.")

        if seconds < 5 or seconds > 120:
            return await error(ctx, "Choose 5–120 seconds.")

        msg = await ctx.send(
            embed=embed("FIRST TO REACT", f"React with ⚡ first!\nTime: {seconds} seconds.")
        )
        await msg.add_reaction("⚡")

        ftr_games[ctx.channel.id] = {
            "message_id": msg.id,
            "winner": None
        }

        await asyncio.sleep(seconds)

        game = ftr_games.get(ctx.channel.id)
        if game:
            winner = game["winner"]
            if winner:
                execute(
                    "INSERT OR IGNORE INTO ftr_scores VALUES (?,?,0)",
                    (ctx.guild.id, winner)
                )
                execute(
                    "UPDATE ftr_scores SET wins=wins+1 WHERE guild_id=? AND user_id=?",
                    (ctx.guild.id, winner)
                )
                await ctx.send(embed=embed("FTR WINNER", f"<@{winner}> won!"))
            else:
                await ctx.send(embed=embed("FTR ENDED", "Nobody reacted in time."))
            ftr_games.pop(ctx.channel.id, None)

    elif action == "stop":
        ftr_games.pop(ctx.channel.id, None)
        await success(ctx, "FTR stopped.")

    else:
        await error(ctx, "Use `!ftr start` or `!ftr stop`.")

@bot.listen("on_raw_reaction_add")
async def ftr_reaction(payload):
    if str(payload.emoji) != "⚡" or payload.member is None or payload.member.bot:
        return

    game = ftr_games.get(payload.channel_id)
    if game and payload.message_id == game["message_id"] and not game["winner"]:
        game["winner"] = payload.user_id


# ==========================================
# BOT STATUS
# ==========================================

@bot.command()
@owner_only()
async def playing(ctx, *, text):
    await bot.change_presence(
        activity=discord.Game(name=text)
    )
    await success(ctx, f"Playing status changed to: {text}")

@bot.command()
@owner_only()
async def stext(ctx, *, text):
    await bot.change_presence(
        activity=discord.CustomActivity(name=text)
    )
    await success(ctx, f"Custom status changed to: {text}")

@bot.command()
@owner_only()
async def status(ctx, mode: str):
    modes = {
        "online": discord.Status.online,
        "offline": discord.Status.invisible,
        "dnd": discord.Status.dnd,
        "sleep": discord.Status.idle
    }

    mode = mode.lower()
    if mode not in modes:
        return await error(ctx, "Use online, offline, dnd or sleep.")

    await bot.change_presence(status=modes[mode])
    await success(ctx, f"Status changed to {mode}.")


# ==========================================
# PREMIUM CUSTOM COMMANDS
# ==========================================

db.executescript("""
CREATE TABLE IF NOT EXISTS custom_commands (
    guild_id INTEGER,
    name TEXT,
    response TEXT,
    created_by INTEGER,
    PRIMARY KEY (guild_id,name)
);
""")
db.commit()

@bot.group(invoke_without_command=True)
async def cc(ctx):
    await info(ctx, "Use `!cc add`, `!cc edit`, `!cc remove`, `!cc list` or `!cc info`.")

@cc.command(name="add")
@commands.has_permissions(manage_guild=True)
async def cc_add(ctx, name: str, *, response: str):
    if not await is_premium(ctx.guild.id):
        return await error(ctx, "Custom commands require server premium.")

    name = name.lower()

    if not re.fullmatch(r"[a-z0-9_-]{2,32}", name):
        return await error(ctx, "Use 2–32 letters, numbers, _ or -.")

    if bot.get_command(name):
        return await error(ctx, "That name is already a built-in command.")

    execute(
        "INSERT OR REPLACE INTO custom_commands VALUES (?,?,?,?)",
        (ctx.guild.id, name, response, ctx.author.id)
    )
    await success(ctx, f"Custom command `{name}` created.")

@cc.command(name="edit")
@commands.has_permissions(manage_guild=True)
async def cc_edit(ctx, name: str, *, response: str):
    if not await is_premium(ctx.guild.id):
        return await error(ctx, "Server premium required.")

    row = fetchone(
        "SELECT name FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name.lower())
    )
    if not row:
        return await error(ctx, "Custom command not found.")

    execute(
        "UPDATE custom_commands SET response=? WHERE guild_id=? AND name=?",
        (response, ctx.guild.id, name.lower())
    )
    await success(ctx, f"Updated `{name}`.")

@cc.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def cc_remove(ctx, name: str):
    execute(
        "DELETE FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name.lower())
    )
    await success(ctx, f"Removed `{name}`.")

@cc.command(name="list")
async def cc_list(ctx):
    rows = fetchall(
        "SELECT name FROM custom_commands WHERE guild_id=?",
        (ctx.guild.id,)
    )
    e = embed("CUSTOM COMMANDS")
    e.description = "\n".join(f"`{r['name']}`" for r in rows) or "No custom commands."
    await ctx.send(embed=e)

@cc.command(name="info")
async def cc_info(ctx, name: str):
    row = fetchone(
        "SELECT response,created_by FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name.lower())
    )
    if not row:
        return await error(ctx, "Custom command not found.")

    await ctx.send(
        embed=embed(
            f"CUSTOM COMMAND: {name}",
            f"Response: {row['response']}\nCreated by: <@{row['created_by']}>"
        )
    )

@bot.listen("on_message")
async def custom_command_listener(message):
    if message.author.bot or not message.guild:
        return

    prefix = next(
        (p for p in PREFIXES if message.content.startswith(p)),
        None
    )
    if not prefix:
        return

    name = message.content[len(prefix):].split(" ", 1)[0].lower()

    if not name or bot.get_command(name):
        return

    if not await is_premium(message.guild.id):
        return

    row = fetchone(
        "SELECT response FROM custom_commands WHERE guild_id=? AND name=?",
        (message.guild.id, name)
    )
    if row:
        await message.channel.send(
            row["response"],
            allowed_mentions=discord.AllowedMentions.none()
        )


# ==========================================
# DYNAMIC HELP COMMAND
# ==========================================

@bot.command()
async def help(ctx, command_name: str = None):
    if command_name:
        command = bot.get_command(command_name)
        if not command:
            return await error(ctx, "Command not found.")

        e = embed(
            f"HELP: {command.qualified_name}",
            command.help or "No description available."
        )

        if isinstance(command, commands.Group):
            e.add_field(
                name="Subcommands",
                value=", ".join(c.name for c in command.commands) or "None",
                inline=False
            )

        return await ctx.send(embed=e)

    categories = {
        "General": [],
        "Moderation": [],
        "Economy & Games": [],
        "Community": [],
        "Fun": [],
        "Server Tools": [],
        "Premium": [],
        "Owner": []
    }

    category_map = {
        "ping": "General", "botinfo": "General",
        "serverinfo": "General", "userinfo": "General",
        "avatar": "General", "support": "General",

        "ban": "Moderation", "unban": "Moderation",
        "modkick": "Moderation", "timeout": "Moderation",
        "untimeout": "Moderation", "purge": "Moderation",
        "lock": "Moderation", "unlock": "Moderation",
        "slowmode": "Moderation", "warn": "Moderation",
        "warnings": "Moderation", "clearwarns": "Moderation",
        "staff": "Moderation",

        "balance": "Economy & Games", "daily": "Economy & Games",
        "weekly": "Economy & Games", "work": "Economy & Games",
        "beg": "Economy & Games", "pay": "Economy & Games",
        "leaderboard": "Economy & Games", "dice": "Economy & Games",
        "flip": "Economy & Games", "rps": "Economy & Games",

        "afk": "Community", "confess": "Community",
        "confesssetup": "Community", "confessionsoff": "Community",
        "suggest": "Community", "suggestsetup": "Community",
        "poll": "Community", "rep": "Community",
        "reps": "Community", "rank": "Community",
        "level": "Community",

        "kiss": "Fun", "punch": "Fun", "kick": "Fun",

        "gstart": "Server Tools", "gend": "Server Tools",
        "gcancel": "Server Tools", "greroll": "Server Tools",
        "invites": "Server Tools", "inviter": "Server Tools",
        "topinvites": "Server Tools", "rr": "Server Tools",
        "ticket": "Server Tools", "ticketsetup": "Server Tools",
        "claim": "Server Tools", "close": "Server Tools",
        "s": "Server Tools", "cs": "Server Tools",
        "ftr": "Server Tools",

        "premium": "Premium", "cc": "Premium",

        "announce": "Owner", "announceconfirm": "Owner",
        "announcecancel": "Owner", "playing": "Owner",
        "status": "Owner", "stext": "Owner"
    }

    for command in bot.commands:
        if command.hidden:
            continue

        category = category_map.get(command.name, "General")
        categories[category].append(command.name)

    e = embed("VEXORA COMMANDS")

    for category, names in categories.items():
        if names:
            e.add_field(
                name=category,
                value=", ".join(f"`{n}`" for n in sorted(set(names))),
                inline=False
            )

    e.add_field(
        name="Prefixes",
        value="`!` `?` `.` `$` `-`",
        inline=False
    )
    e.add_field(
        name="Support",
        value=f"[Join here]({SUPPORT_SERVER})",
        inline=False
    )

    await ctx.send(embed=e)


# ==========================================
# FINAL STARTUP
# ==========================================

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing!")

bot.run(TOKEN)
