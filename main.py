
import discord
from discord.ext import commands
import os
import random
import asyncio
import sqlite3
import time
import datetime
import re

# =====================================
# VEXORA CONFIG
# =====================================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 1495419933943922920

SUPPORT_SERVER = "https://discord.gg/ZBaRByVFBC"

PREFIXES = ["!", "?", ".", "$", "-"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.reactions = True
intents.presences = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# =====================================
# EMBED SYSTEM
# =====================================

VEX_COLOR = discord.Color.from_rgb(175, 175, 175)

def vex_embed(title, description=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=VEX_COLOR
    )
    embed.set_footer(
        text="VEXORA • One Bot. Endless Possibilities."
    )
    return embed

async def send_success(ctx, message):
    await ctx.send(embed=vex_embed(
        "SUCCESS",
        f"✅ {message}"
    ))

async def send_error(ctx, message):
    await ctx.send(embed=vex_embed(
        "ERROR",
        f"❌ {message}"
    ))

async def send_info(ctx, message):
    await ctx.send(embed=vex_embed(
        "VEXORA",
        message
    ))

# =====================================
# PERMISSION CHECKS
# =====================================

def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_staff():
    async def predicate(ctx):
        return (
            ctx.author.id == OWNER_ID
            or ctx.author.guild_permissions.manage_messages
            or ctx.author.guild_permissions.administrator
        )
    return commands.check(predicate)

# =====================================
# DATABASE
# =====================================

db = sqlite3.connect("vexora.db")
db.row_factory = sqlite3.Row

def db_execute(query, params=()):
    cursor = db.cursor()
    cursor.execute(query, params)
    db.commit()
    return cursor

def db_fetchone(query, params=()):
    return db_execute(query, params).fetchone()

def db_fetchall(query, params=()):
    return db_execute(query, params).fetchall()

# =====================================
# DATABASE TABLES
# =====================================

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

CREATE TABLE IF NOT EXISTS custom_commands (
    guild_id INTEGER,
    name TEXT,
    response TEXT,
    created_by INTEGER,
    PRIMARY KEY (guild_id, name)
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

CREATE TABLE IF NOT EXISTS giveaways (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    prize TEXT,
    winners INTEGER,
    end_time INTEGER,
    host_id INTEGER,
    ended INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id INTEGER,
    message_id INTEGER,
    emoji TEXT,
    role_id INTEGER,
    PRIMARY KEY (message_id, emoji)
);

CREATE TABLE IF NOT EXISTS invites (
    guild_id INTEGER,
    user_id INTEGER,
    inviter_id INTEGER,
    uses INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS confessions (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS suggestions (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS server_settings (
    guild_id INTEGER PRIMARY KEY,
    ticket_category INTEGER
);

CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    claimed_by INTEGER
);

CREATE TABLE IF NOT EXISTS snipes (
    channel_id INTEGER PRIMARY KEY,
    author_id INTEGER,
    content TEXT,
    deleted_at INTEGER
);

CREATE TABLE IF NOT EXISTS afk (
    user_id INTEGER PRIMARY KEY,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS ftr_scores (
    guild_id INTEGER,
    user_id INTEGER,
    wins INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS polls (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER
);
""")

db.commit()

# =====================================
# PREMIUM CHECK
# =====================================

async def is_premium(guild_id):
    row = db_fetchone(
        "SELECT expires FROM premium WHERE guild_id=?",
        (guild_id,)
    )

    if not row:
        return False

    expires = row["expires"]

    if not expires:
        return True

    if int(expires) <= int(time.time()):
        db_execute(
            "DELETE FROM premium WHERE guild_id=?",
            (guild_id,)
        )
        return False

    return True

# =====================================
# BOT READY
# =====================================

@bot.event
async def on_ready():
    print("================================")
    print(f"VEXORA ONLINE: {bot.user}")
    print(f"BOT ID: {bot.user.id}")
    print(f"SERVERS: {len(bot.guilds)}")
    print("================================")

# =====================================
# ERROR HANDLER
# =====================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        return await send_error(
            ctx,
            f"Missing argument: `{error.param.name}`"
        )

    if isinstance(error, commands.MissingPermissions):
        return await send_error(
            ctx,
            "You don't have the required permissions."
        )

    if isinstance(error, commands.NotOwner):
        return await send_error(
            ctx,
            "Only the bot owner can use this command."
        )

    if isinstance(error, commands.CheckFailure):
        return await send_error(
            ctx,
            "You cannot use this command."
        )

    print("ERROR:", repr(error))

    await send_error(
        ctx,
        "An unexpected error occurred. Check Railway logs."
    )

# =====================================
# GENERAL COMMANDS
# =====================================

@bot.command()
async def ping(ctx):
    ms = round(bot.latency * 1000)
    await ctx.send(embed=vex_embed(
        "🏓 PONG!",
        f"Latency: `{ms}ms`"
    ))


@bot.command()
async def botinfo(ctx):
    members = sum(g.member_count or 0 for g in bot.guilds)

    embed = vex_embed(
        "🤖 VEXORA INFORMATION",
        f"""
**Name:** {bot.user}
**Servers:** {len(bot.guilds)}
**Members:** {members}
**Latency:** {round(bot.latency * 1000)}ms
**Version:** 1.0
"""
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.guild_only()
async def serverinfo(ctx):
    guild = ctx.guild

    embed = vex_embed(
        f"🏠 {guild.name}",
        f"""
**Owner:** {guild.owner}
**Members:** {guild.member_count}
**Channels:** {len(guild.channels)}
**Roles:** {len(guild.roles)}
**Created:** <t:{int(guild.created_at.timestamp())}:D>
"""
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)


@bot.command()
@commands.guild_only()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    joined = (
        f"<t:{int(member.joined_at.timestamp())}:D>"
        if member.joined_at else "Unknown"
    )

    embed = vex_embed(
        f"👤 {member}",
        f"""
**ID:** `{member.id}`
**Joined:** {joined}
**Created:** <t:{int(member.created_at.timestamp())}:D>
**Top Role:** {member.top_role.mention}
"""
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = vex_embed(
        f"🖼️ {member.display_name}'s Avatar",
        f"[Open Avatar]({member.display_avatar.url})"
    )
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# =====================================
# VEXORA ECONOMY
# =====================================

def get_balance(user_id):
    row = db_fetchone(
        "SELECT balance FROM economy WHERE user_id=?",
        (user_id,)
    )

    if not row:
        db_execute(
            "INSERT INTO economy (user_id, balance) VALUES (?, 0)",
            (user_id,)
        )
        return 0

    return row["balance"]


@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    amount = get_balance(member.id)

    await ctx.send(embed=vex_embed(
        "💰 VEX BALANCE",
        f"**{member.display_name}** has `{amount:,} VEX`."
    ))


@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    now = int(time.time())

    row = db_fetchone(
        "SELECT * FROM economy WHERE user_id=?",
        (user_id,)
    )

    if not row:
        db_execute(
            "INSERT INTO economy (user_id) VALUES (?)",
            (user_id,)
        )
        row = db_fetchone(
            "SELECT * FROM economy WHERE user_id=?",
            (user_id,)
        )

    if row["daily"] and now - row["daily"] < 86400:
        remaining = 86400 - (now - row["daily"])
        return await send_error(
            ctx, f"Daily reward available <t:{now + remaining}:R>."
        )

    reward = random.randint(100, 300)

    db_execute(
        """
        UPDATE economy
        SET balance=balance+?, daily=?
        WHERE user_id=?
        """,
        (reward, now, user_id)
    )

    await send_success(ctx, f"You received `{reward} VEX`!")


@bot.command()
async def weekly(ctx):
    user_id = ctx.author.id
    now = int(time.time())

    row = db_fetchone(
        "SELECT * FROM economy WHERE user_id=?",
        (user_id,)
    )

    if not row:
        db_execute(
            "INSERT INTO economy (user_id) VALUES (?)",
            (user_id,)
        )
        row = db_fetchone(
            "SELECT * FROM economy WHERE user_id=?",
            (user_id,)
        )

    if row["weekly"] and now - row["weekly"] < 604800:
        remaining = 604800 - (now - row["weekly"])
        return await send_error(
            ctx, f"Weekly reward available <t:{now + remaining}:R>."
        )

    reward = random.randint(500, 1000)

    db_execute(
        """
        UPDATE economy
        SET balance=balance+?, weekly=?
        WHERE user_id=?
        """,
        (reward, now, user_id)
    )

    await send_success(ctx, f"You received `{reward} VEX`!")


@bot.command()
async def work(ctx):
    reward = random.randint(50, 150)
    get_balance(ctx.author.id)

    db_execute(
        "UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id)
    )

    await send_success(ctx, f"You earned `{reward} VEX` from working!")


@bot.command()
async def beg(ctx):
    reward = random.randint(10, 50)
    get_balance(ctx.author.id)

    db_execute(
        "UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id)
    )

    await send_success(ctx, f"Someone gave you `{reward} VEX`!")


@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id:
        return await send_error(ctx, "Invalid recipient.")

    if amount <= 0:
        return await send_error(ctx, "Amount must be positive.")

    get_balance(ctx.author.id)
    get_balance(member.id)

    # Atomic balance transfer
    try:
        db.execute("BEGIN IMMEDIATE")

        sender = db.execute(
            "SELECT balance FROM economy WHERE user_id=?",
            (ctx.author.id,)
        ).fetchone()

        if sender["balance"] < amount:
            db.rollback()
            return await send_error(ctx, "Not enough VEX.")

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

    await send_success(
        ctx,
        f"Transferred `{amount:,} VEX` to {member.mention}."
    )


@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    rows = db_fetchall(
        """
        SELECT user_id, balance
        FROM economy
        ORDER BY balance DESC
        LIMIT 10
        """
    )

    if not rows:
        return await send_info(ctx, "No economy data yet.")

    lines = []

    for i, row in enumerate(rows, 1):
        lines.append(
            f"**{i}.** <@{row['user_id']}> — `{row['balance']:,} VEX`"
        )

    await ctx.send(embed=vex_embed(
        "🏆 VEX LEADERBOARD",
        "\n".join(lines)
    ))

# =====================================
# MINI GAMES
# =====================================

@bot.command()
async def flip(ctx):
    result = random.choice(["Heads", "Tails"])

    await ctx.send(embed=vex_embed(
        "🪙 COIN FLIP",
        f"Result: **{result}**"
    ))


@bot.command()
async def dice(ctx):
    result = random.randint(1, 6)

    await ctx.send(embed=vex_embed(
        "🎲 DICE ROLL",
        f"You rolled **{result}**!"
    ))


@bot.command()
async def rps(ctx, choice: str):
    choices = ["rock", "paper", "scissors"]

    choice = choice.lower()

    if choice not in choices:
        return await send_error(
            ctx, "Choose rock, paper, or scissors."
        )

    bot_choice = random.choice(choices)

    if choice == bot_choice:
        result = "It's a draw!"
    elif (
        (choice == "rock" and bot_choice == "scissors")
        or (choice == "paper" and bot_choice == "rock")
        or (choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win!"
    else:
        result = "VEXORA wins!"

    await ctx.send(embed=vex_embed(
        "✂️ ROCK PAPER SCISSORS",
        f"""
**You:** {choice.title()}
**VEXORA:** {bot_choice.title()}

**Result:** {result}
"""
    ))


# Guessing game: each user has their own active game
guess_games = {}


@bot.command()
async def guess(ctx, number: int = None):
    user_id = ctx.author.id

    if number is None:
        guess_games[user_id] = random.randint(1, 20)
        return await send_info(
            ctx, "I'm thinking of a number from 1 to 20. Use `!guess <number>`."
        )

    if user_id not in guess_games:
        return await send_error(ctx, "Start a game with `!guess` first.")

    if not 1 <= number <= 20:
        return await send_error(ctx, "Choose a number from 1 to 20.")

    answer = guess_games[user_id]

    if number == answer:
        del guess_games[user_id]
        await send_success(ctx, "Correct! You guessed it!")
    elif number < answer:
        await send_info(ctx, "Too low! Try again.")
    else:
        await send_info(ctx, "Too high! Try again.")


@bot.command()
async def trivia(ctx):
    questions = [
        ("What is the capital of Japan?", "tokyo"),
        ("How many sides does a hexagon have?", "6"),
        ("Which planet is known as the Red Planet?", "mars"),
        ("What is 12 x 12?", "144"),
        ("What is the largest ocean?", "pacific")
    ]

    question, answer = random.choice(questions)

    await ctx.send(embed=vex_embed(
        "🧠 TRIVIA",
        f"{question}\n\nReply with your answer!"
    ))

    def check(message):
        return (
            message.author == ctx.author
            and message.channel == ctx.channel
        )

    try:
        response = await bot.wait_for(
            "message",
            timeout=25,
            check=check
        )

        if response.content.lower().strip() == answer:
            await send_success(ctx, "Correct answer!")
        else:
            await send_info(ctx, f"The correct answer was **{answer}**.")

    except asyncio.TimeoutError:
        await send_info(ctx, f"Time's up! Answer: **{answer}**.")

# =====================================
# REPUTATION SYSTEM
# =====================================

@bot.command()
@commands.guild_only()
async def rep(ctx, member: discord.Member):
    if member.bot or member.id == ctx.author.id:
        return await send_error(ctx, "Invalid member.")

    existing = db_fetchone(
        """
        SELECT reps FROM reputation
        WHERE guild_id=? AND user_id=?
        """,
        (ctx.guild.id, member.id)
    )

    db_execute(
        """
        INSERT INTO reputation (guild_id, user_id, reps)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET reps=reps+1
        """,
        (ctx.guild.id, member.id)
    )

    await send_success(ctx, f"Gave reputation to {member.mention}!")


@bot.command()
@commands.guild_only()
async def reps(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = db_fetchone(
        """
        SELECT reps FROM reputation
        WHERE guild_id=? AND user_id=?
        """,
        (ctx.guild.id, member.id)
    )

    amount = row["reps"] if row else 0

    await ctx.send(embed=vex_embed(
        "⭐ REPUTATION",
        f"{member.mention} has `{amount}` reputation points."
    ))


@bot.command()
@commands.guild_only()
async def repboard(ctx):
    rows = db_fetchall(
        """
        SELECT user_id, reps
        FROM reputation
        WHERE guild_id=?
        ORDER BY reps DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    )

    if not rows:
        return await send_info(ctx, "No reputation data yet.")

    lines = [
        f"**{i}.** <@{row['user_id']}> — `{row['reps']} ⭐`"
        for i, row in enumerate(rows, 1)
    ]

    await ctx.send(embed=vex_embed(
        "⭐ REPUTATION LEADERBOARD",
        "\n".join(lines)
    ))

# =====================================
# LEVELING SYSTEM
# =====================================

level_cooldowns = {}


@bot.listen("on_message")
async def level_message(message):
    if message.author.bot or not message.guild:
        return

    now = time.time()
    key = (message.guild.id, message.author.id)

    if now - level_cooldowns.get(key, 0) < 60:
        return

    level_cooldowns[key] = now

    row = db_fetchone(
        """
        SELECT xp, level FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        key
    )

    if not row:
        db_execute(
            """
            INSERT INTO levels (guild_id, user_id, xp, level)
            VALUES (?, ?, 0, 0)
            """,
            key
        )
        xp = 0
        level = 0
    else:
        xp = row["xp"]
        level = row["level"]

    xp += random.randint(10, 20)

    required = (level + 1) * 100

    if xp >= required:
        xp -= required
        level += 1

        await message.channel.send(
            embed=vex_embed(
                "🎉 LEVEL UP!",
                f"{message.author.mention} reached level **{level}**!"
            )
        )

    db_execute(
        """
        UPDATE levels
        SET xp=?, level=?
        WHERE guild_id=? AND user_id=?
        """,
        (xp, level, *key)
    )


@bot.command()
@commands.guild_only()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = db_fetchone(
        """
        SELECT xp, level FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (ctx.guild.id, member.id)
    )

    xp = row["xp"] if row else 0
    level = row["level"] if row else 0

    required = (level + 1) * 100

    await ctx.send(embed=vex_embed(
        f"🏆 RANK • {member.display_name}",
        f"""
**Level:** `{level}`
**XP:** `{xp}/{required}`
**Remaining:** `{required - xp} XP`
"""
    ))


@bot.command()
@commands.guild_only()
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = db_fetchone(
        """
        SELECT level FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (ctx.guild.id, member.id)
    )

    amount = row["level"] if row else 0

    await send_info(ctx, f"{member.mention} is level `{amount}`.")


@bot.command()
@commands.guild_only()
async def levels(ctx):
    rows = db_fetchall(
        """
        SELECT user_id, level, xp
        FROM levels
        WHERE guild_id=?
        ORDER BY level DESC, xp DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    )

    if not rows:
        return await send_info(ctx, "No level data yet.")

    lines = [
        f"**{i}.** <@{r['user_id']}> — Level `{r['level']}`"
        for i, r in enumerate(rows, 1)
    ]

    await ctx.send(embed=vex_embed(
        "🏆 SERVER LEVELS",
        "\n".join(lines)
    ))

# =====================================
# AFK SYSTEM
# =====================================

@bot.command()
async def afk(ctx, *, reason="AFK"):
    db_execute(
        """
        INSERT INTO afk (user_id, reason)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET reason=excluded.reason
        """,
        (ctx.author.id, reason)
    )

    await send_success(ctx, f"AFK enabled: **{reason}**")


@bot.listen("on_message")
async def afk_message(message):
    if message.author.bot:
        return

    row = db_fetchone(
        "SELECT reason FROM afk WHERE user_id=?",
        (message.author.id,)
    )

    if row:
        db_execute(
            "DELETE FROM afk WHERE user_id=?",
            (message.author.id,)
        )

        await message.channel.send(
            f"Welcome back {message.author.mention}! Your AFK status was removed."
        )

    for mentioned in message.mentions:
        afk_user = db_fetchone(
            "SELECT reason FROM afk WHERE user_id=?",
            (mentioned.id,)
        )

        if afk_user:
            await message.channel.send(
                f"💤 {mentioned.display_name} is AFK: **{afk_user['reason']}**"
            )

# =====================================
# CONFESSIONS
# =====================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confesssetup(ctx, channel: discord.TextChannel):
    db_execute(
        """
        INSERT INTO confessions (guild_id, channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET channel_id=excluded.channel_id
        """,
        (ctx.guild.id, channel.id)
    )

    await send_success(ctx, f"Confessions channel set to {channel.mention}.")


@bot.command()
@commands.has_permissions(manage_guild=True)
async def confessionsoff(ctx):
    db_execute(
        "DELETE FROM confessions WHERE guild_id=?",
        (ctx.guild.id,)
    )

    await send_success(ctx, "Confessions disabled.")


@bot.command()
@commands.guild_only()
async def confess(ctx, *, message: str):
    row = db_fetchone(
        "SELECT channel_id FROM confessions WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not row:
        return await send_error(ctx, "Confessions are not configured.")

    channel = ctx.guild.get_channel(row["channel_id"])

    if not channel:
        return await send_error(ctx, "Confession channel not found.")

    if len(message) > 1500:
        return await send_error(ctx, "Confession is too long.")

    embed = vex_embed("🤍 ANONYMOUS CONFESSION", message)

    await channel.send(embed=embed)
    await send_success(ctx, "Your confession was sent.")

# =====================================
# SUGGESTIONS
# =====================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def suggestsetup(ctx, channel: discord.TextChannel):
    db_execute(
        """
        INSERT INTO suggestions (guild_id, channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET channel_id=excluded.channel_id
        """,
        (ctx.guild.id, channel.id)
    )

    await send_success(ctx, f"Suggestions channel set to {channel.mention}.")


@bot.command()
@commands.guild_only()
async def suggest(ctx, *, suggestion: str):
    row = db_fetchone(
        "SELECT channel_id FROM suggestions WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not row:
        return await send_error(ctx, "Suggestions are not configured.")

    channel = ctx.guild.get_channel(row["channel_id"])

    if not channel:
        return await send_error(ctx, "Suggestion channel not found.")

    if len(suggestion) > 1500:
        return await send_error(ctx, "Suggestion is too long.")

    embed = vex_embed("💡 NEW SUGGESTION", suggestion)
    embed.add_field(
        name="Suggested by",
        value=ctx.author.mention,
        inline=False
    )

    msg = await channel.send(embed=embed)

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

    await send_success(ctx, "Your suggestion was submitted!")

# =====================================
# POLLS
# =====================================

@bot.command()
@commands.guild_only()
async def poll(ctx, *, question: str):
    if len(question) > 1500:
        return await send_error(ctx, "Poll question is too long.")

    embed = vex_embed(
        "📊 SERVER POLL",
        f"**{question}**\n\n👍 = Yes\n👎 = No"
    )

    msg = await ctx.send(embed=embed)

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

# =====================================
# ANIME FUN COMMANDS
# =====================================

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


async def anime_action(ctx, action, member):
    if member.bot and member.id == bot.user.id:
        return await send_error(ctx, "You cannot use that on me!")

    gif = random.choice(ANIME_GIFS[action])

    embed = vex_embed(
        f"🎬 ANIME {action.upper()}",
        f"{ctx.author.mention} **{action}s** {member.mention}!\n\n"
        f"[View GIF]({gif})"
    )

    await ctx.send(embed=embed)


@bot.command()
async def kiss(ctx, member: discord.Member):
    await anime_action(ctx, "kiss", member)


@bot.command()
async def punch(ctx, member: discord.Member):
    await anime_action(ctx, "punch", member)


@bot.command()
async def kick(ctx, member: discord.Member):
    await anime_action(ctx, "kick", member)

# =====================================
# GIVEAWAY SYSTEM
# =====================================

giveaway_tasks = {}


def parse_duration(value):
    match = re.fullmatch(r"(\d+)([smhd])", value.lower())

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

    seconds = amount * multipliers[unit]

    if seconds < 10 or seconds > 2592000:
        return None

    return seconds


async def finish_giveaway(message_id, cancelled=False):
    row = db_fetchone(
        "SELECT * FROM giveaways WHERE message_id=?",
        (message_id,)
    )

    if not row or row["ended"]:
        return

    channel = bot.get_channel(row["channel_id"])

    if not channel:
        return

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        db_execute(
            "UPDATE giveaways SET ended=1 WHERE message_id=?",
            (message_id,)
        )
        return

    db_execute(
        "UPDATE giveaways SET ended=1 WHERE message_id=?",
        (message_id,)
    )

    task = giveaway_tasks.pop(message_id, None)

    if task and task != asyncio.current_task():
        task.cancel()

    if cancelled:
        embed = vex_embed(
            "❌ GIVEAWAY CANCELLED",
            f"**Prize:** {row['prize']}"
        )
        return await message.reply(embed=embed)

    reaction = discord.utils.get(
        message.reactions,
        emoji="🎉"
    )

    if not reaction:
        return await message.reply(
            embed=vex_embed("GIVEAWAY ENDED", "No entries found.")
        )

    users = [
        user async for user in reaction.users()
        if not user.bot
    ]

    if not users:
        return await message.reply(
            embed=vex_embed("GIVEAWAY ENDED", "No valid entries.")
        )

    winners = random.sample(
        users,
        min(row["winners"], len(users))
    )

    mentions = ", ".join(user.mention for user in winners)

    await message.reply(
        embed=vex_embed(
            "🎉 GIVEAWAY ENDED",
            f"**Prize:** {row['prize']}\n"
            f"**Winner(s):** {mentions}"
        )
    )


async def giveaway_timer(message_id, end_time):
    try:
        await asyncio.sleep(max(0, end_time - int(time.time())))
        await finish_giveaway(message_id)
    except asyncio.CancelledError:
        pass


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, winners: int, *, prize: str):
    seconds = parse_duration(duration)

    if seconds is None:
        return await send_error(
            ctx, "Use a duration like `10m`, `2h`, or `1d`."
        )

    if not 1 <= winners <= 20:
        return await send_error(ctx, "Winners must be between 1 and 20.")

    if len(prize) > 200:
        return await send_error(ctx, "Prize name is too long.")

    end_time = int(time.time()) + seconds

    embed = vex_embed(
        "🎉 VEXORA GIVEAWAY",
        f"""
**Prize:** {prize}
**Winners:** {winners}
**Hosted by:** {ctx.author.mention}
**Ends:** <t:{end_time}:R>

React with 🎉 to enter!
"""
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    db_execute(
        """
        INSERT INTO giveaways
        (message_id, guild_id, channel_id, prize, winners, end_time, host_id, ended)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            message.id,
            ctx.guild.id,
            ctx.channel.id,
            prize,
            winners,
            end_time,
            ctx.author.id
        )
    )

    giveaway_tasks[message.id] = asyncio.create_task(
        giveaway_timer(message.id, end_time)
    )


async def get_latest_giveaway(ctx):
    return db_fetchone(
        """
        SELECT * FROM giveaways
        WHERE guild_id=? AND channel_id=? AND ended=0
        ORDER BY end_time DESC
        LIMIT 1
        """,
        (ctx.guild.id, ctx.channel.id)
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx):
    row = await get_latest_giveaway(ctx)

    if not row:
        return await send_error(ctx, "No active giveaway in this channel.")

    await finish_giveaway(row["message_id"])


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gcancel(ctx):
    row = await get_latest_giveaway(ctx)

    if not row:
        return await send_error(ctx, "No active giveaway in this channel.")

    await finish_giveaway(row["message_id"], cancelled=True)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    row = db_fetchone(
        "SELECT * FROM giveaways WHERE message_id=? AND guild_id=?",
        (message_id, ctx.guild.id)
    )

    if not row or not row["ended"]:
        return await send_error(ctx, "Giveaway not found or not ended.")

    channel = bot.get_channel(row["channel_id"])

    if not channel:
        return await send_error(ctx, "Giveaway channel not found.")

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        return await send_error(ctx, "Giveaway message not found.")

    reaction = discord.utils.get(message.reactions, emoji="🎉")

    if not reaction:
        return await send_error(ctx, "No entries found.")

    users = [
        user async for user in reaction.users()
        if not user.bot
    ]

    if not users:
        return await send_error(ctx, "No valid entries.")

    winner = random.choice(users)

    await ctx.send(embed=vex_embed(
        "🔄 GIVEAWAY REROLL",
        f"New winner: {winner.mention}\nPrize: **{row['prize']}**"
    ))


@bot.listen("on_ready")
async def restore_giveaways():
    for row in db_fetchall(
        "SELECT message_id, end_time FROM giveaways WHERE ended=0"
    ):
        message_id = row["message_id"]

        if message_id not in giveaway_tasks:
            giveaway_tasks[message_id] = asyncio.create_task(
                giveaway_timer(message_id, row["end_time"])
            )

# =====================================
# INVITE TRACKING
# =====================================

invite_cache = {}


async def cache_guild_invites(guild):
    try:
        invites = await guild.invites()
        invite_cache[guild.id] = {
            invite.code: invite.uses or 0
            for invite in invites
        }
    except discord.Forbidden:
        print(f"Missing Manage Server permission in {guild.name}")
    except discord.HTTPException:
        pass


@bot.listen("on_ready")
async def load_invite_cache():
    for guild in bot.guilds:
        await cache_guild_invites(guild)


@bot.listen("on_guild_join")
async def joined_guild(guild):
    await cache_guild_invites(guild)


@bot.listen("on_invite_create")
async def invite_created(invite):
    await cache_guild_invites(invite.guild)


@bot.listen("on_invite_delete")
async def invite_deleted(invite):
    await cache_guild_invites(invite.guild)


@bot.listen("on_member_join")
async def track_invite(member):
    guild = member.guild

    old_invites = invite_cache.get(guild.id, {})

    try:
        new_invites = await guild.invites()
    except discord.Forbidden:
        return

    inviter_id = None
    updated_cache = {}

    for invite in new_invites:
        uses = invite.uses or 0
        updated_cache[invite.code] = uses

        if uses > old_invites.get(invite.code, 0):
            if invite.inviter:
                inviter_id = invite.inviter.id

    invite_cache[guild.id] = updated_cache

    if inviter_id is None:
        return

    db_execute(
        """
        INSERT INTO invites (guild_id, user_id, inviter_id, uses)
        VALUES (?, ?, ?, 1)
        """,
        (guild.id, member.id, inviter_id)
    )


@bot.command(name="invites", aliases=["i", "lb"])
@commands.guild_only()
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author

    rows = db_fetchall(
        """
        SELECT COUNT(*) AS total
        FROM invites
        WHERE guild_id=? AND inviter_id=?
        """,
        (ctx.guild.id, member.id)
    )

    total = rows[0]["total"]

    await ctx.send(embed=vex_embed(
        "📨 INVITE COUNT",
        f"{member.mention} has invited `{total}` members."
    ))


@bot.command()
@commands.guild_only()
async def inviter(ctx, member: discord.Member):
    row = db_fetchone(
        """
        SELECT inviter_id FROM invites
        WHERE guild_id=? AND user_id=?
        ORDER BY rowid DESC LIMIT 1
        """,
        (ctx.guild.id, member.id)
    )

    if not row:
        return await send_info(ctx, "No inviter information found.")

    await send_info(
        ctx,
        f"{member.mention} was invited by <@{row['inviter_id']}>."
    )


@bot.command()
@commands.guild_only()
async def inviteinfo(ctx):
    rows = db_fetchall(
        """
        SELECT COUNT(*) AS total
        FROM invites
        WHERE guild_id=? AND inviter_id=?
        """,
        (ctx.guild.id, ctx.author.id)
    )

    total = rows[0]["total"]

    await ctx.send(embed=vex_embed(
        "📊 YOUR INVITE INFO",
        f"""
**Inviter:** {ctx.author.mention}
**Tracked invites:** `{total}`
"""
    ))


@bot.command()
@commands.guild_only()
async def topinvites(ctx):
    rows = db_fetchall(
        """
        SELECT inviter_id, COUNT(*) AS total
        FROM invites
        WHERE guild_id=?
        GROUP BY inviter_id
        ORDER BY total DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    )

    if not rows:
        return await send_info(ctx, "No invite data yet.")

    lines = [
        f"**{i}.** <@{row['inviter_id']}> — `{row['total']}` invites"
        for i, row in enumerate(rows, 1)
    ]

    await ctx.send(embed=vex_embed(
        "🏆 TOP INVITERS",
        "\n".join(lines)
    ))

# =====================================
# REACTION ROLES
# =====================================

@bot.group(invoke_without_command=True)
@commands.guild_only()
async def rr(ctx):
    await send_info(
        ctx,
        """
**REACTION ROLE COMMANDS**

`!rr create <message>`
`!rr add <message_id> <emoji> @role`
`!rr remove <message_id> <emoji>`
`!rr delete <message_id>`
"""
    )


@rr.command(name="create")
@commands.has_permissions(manage_roles=True)
async def rr_create(ctx, *, message_text: str):
    if len(message_text) > 1500:
        return await send_error(ctx, "Message is too long.")

    embed = vex_embed("🎭 CHOOSE YOUR ROLES", message_text)
    message = await ctx.send(embed=embed)

    await send_success(
        ctx,
        f"Reaction-role message created. Message ID: `{message.id}`"
    )


@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(
    ctx,
    message_id: int,
    emoji: str,
    role: discord.Role
):
    if role.is_default() or role.managed:
        return await send_error(ctx, "That role cannot be assigned.")

    if role >= ctx.guild.me.top_role:
        return await send_error(
            ctx, "Move the bot's role above the selected role."
        )

    try:
        message = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        return await send_error(ctx, "Message not found in this channel.")

    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        return await send_error(ctx, "Invalid emoji or reaction unavailable.")

    db_execute(
        """
        INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(message_id, emoji)
        DO UPDATE SET role_id=excluded.role_id
        """,
        (ctx.guild.id, message_id, emoji, role.id)
    )

    await send_success(
        ctx, f"{emoji} now gives the **{role.name}** role."
    )


@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, *, emoji: str):
    db_execute(
        """
        DELETE FROM reaction_roles
        WHERE guild_id=? AND message_id=? AND emoji=?
        """,
        (ctx.guild.id, message_id, emoji)
    )

    await send_success(ctx, "Reaction role configuration removed.")


@rr.command(name="delete")
@commands.has_permissions(manage_roles=True)
async def rr_delete(ctx, message_id: int):
    db_execute(
        """
        DELETE FROM reaction_roles
        WHERE guild_id=? AND message_id=?
        """,
        (ctx.guild.id, message_id)
    )

    await send_success(ctx, "All reaction roles for that message removed.")


@bot.listen("on_raw_reaction_add")
async def reaction_role_add(payload):
    if payload.member is None or payload.member.bot:
        return

    row = db_fetchone(
        """
        SELECT role_id FROM reaction_roles
        WHERE guild_id=? AND message_id=? AND emoji=?
        """,
        (
            payload.guild_id,
            payload.message_id,
            str(payload.emoji)
        )
    )

    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = payload.member
    role = guild.get_role(row["role_id"])

    if role and role < guild.me.top_role:
        try:
            await member.add_roles(role, reason="VEXORA reaction role")
        except discord.Forbidden:
            pass


@bot.listen("on_raw_reaction_remove")
async def reaction_role_remove(payload):
    row = db_fetchone(
        """
        SELECT role_id FROM reaction_roles
        WHERE guild_id=? AND message_id=? AND emoji=?
        """,
        (
            payload.guild_id,
            payload.message_id,
            str(payload.emoji)
        )
    )

    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    role = guild.get_role(row["role_id"])

    if member and role and role < guild.me.top_role:
        try:
            await member.remove_roles(role, reason="VEXORA reaction role")
        except discord.Forbidden:
            pass

# =====================================
# TICKET SYSTEM
# =====================================

@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def ticketsetup(ctx, category: discord.CategoryChannel):
    db_execute(
        """
        INSERT INTO server_settings (guild_id, ticket_category)
        VALUES (?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET ticket_category=excluded.ticket_category
        """,
        (ctx.guild.id, category.id)
    )

    await send_success(ctx, f"Ticket category set to **{category.name}**.")


@bot.command()
@commands.guild_only()
async def ticket(ctx):
    existing = db_fetchone(
        """
        SELECT channel_id FROM tickets
        WHERE guild_id=? AND user_id=?
        """,
        (ctx.guild.id, ctx.author.id)
    )

    if existing:
        channel = ctx.guild.get_channel(existing["channel_id"])

        if channel:
            return await send_error(
                ctx, f"You already have a ticket: {channel.mention}"
            )

        db_execute(
            "DELETE FROM tickets WHERE channel_id=?",
            (existing["channel_id"],)
        )

    settings = db_fetchone(
        "SELECT ticket_category FROM server_settings WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not settings:
        return await send_error(ctx, "Ticket system is not configured.")

    category = ctx.guild.get_channel(settings["ticket_category"])

    if not isinstance(category, discord.CategoryChannel):
        return await send_error(ctx, "Ticket category not found.")

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        ctx.author: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True
        )
    }

    # Inherit category permissions for staff roles that can manage channels.
    for role in ctx.guild.roles:
        if role.permissions.manage_channels and role != ctx.guild.default_role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

    channel = await ctx.guild.create_text_channel(
        name=f"ticket-{ctx.author.name}".lower()[:90],
        category=category,
        overwrites=overwrites,
        reason="VEXORA ticket opened"
    )

    db_execute(
        """
        INSERT INTO tickets (channel_id, guild_id, user_id, claimed_by)
        VALUES (?, ?, ?, NULL)
        """,
        (channel.id, ctx.guild.id, ctx.author.id)
    )

    await channel.send(
        embed=vex_embed(
            "🎫 SUPPORT TICKET",
            f"Welcome {ctx.author.mention}!\n"
            "Please explain what you need help with.\n\n"
            "Staff can use `!claim` and `!close`."
        )
    )

    await send_success(ctx, f"Ticket created: {channel.mention}")


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def claim(ctx):
    row = db_fetchone(
        "SELECT * FROM tickets WHERE channel_id=? AND guild_id=?",
        (ctx.channel.id, ctx.guild.id)
    )

    if not row:
        return await send_error(ctx, "This is not a ticket channel.")

    if row["claimed_by"]:
        return await send_error(ctx, "This ticket is already claimed.")

    db_execute(
        "UPDATE tickets SET claimed_by=? WHERE channel_id=?",
        (ctx.author.id, ctx.channel.id)
    )

    await send_success(ctx, f"Ticket claimed by {ctx.author.mention}.")


@bot.command()
@commands.guild_only()
async def close(ctx):
    row = db_fetchone(
        "SELECT * FROM tickets WHERE channel_id=? AND guild_id=?",
        (ctx.channel.id, ctx.guild.id)
    )

    if not row:
        return await send_error(ctx, "This is not a ticket channel.")

    is_owner = row["user_id"] == ctx.author.id
    is_staff_member = (
        ctx.author.guild_permissions.manage_channels
        or ctx.author.guild_permissions.administrator
    )

    if not is_owner and not is_staff_member:
        return await send_error(ctx, "Only the ticket owner or staff can close it.")

    db_execute(
        "DELETE FROM tickets WHERE channel_id=?",
        (ctx.channel.id,)
    )

    await send_success(ctx, "Ticket closing in 3 seconds.")

    await asyncio.sleep(3)
    await ctx.channel.delete(reason="VEXORA ticket closed")

# =====================================
# SNIPE SYSTEM
# =====================================

@bot.listen("on_message_delete")
async def save_deleted_message(message):
    if not message.guild or message.author.bot:
        return

    content = message.content or ""

    db_execute(
        """
        INSERT INTO snipes (channel_id, author_id, content, deleted_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id)
        DO UPDATE SET
            author_id=excluded.author_id,
            content=excluded.content,
            deleted_at=excluded.deleted_at
        """,
        (
            message.channel.id,
            message.author.id,
            content[:1500],
            int(time.time())
        )
    )


@bot.command(name="s")
@commands.guild_only()
async def snipe(ctx):
    row = db_fetchone(
        "SELECT * FROM snipes WHERE channel_id=?",
        (ctx.channel.id,)
    )

    if not row:
        return await send_error(ctx, "Nothing to snipe.")

    embed = vex_embed(
        "🗑️ DELETED MESSAGE",
        row["content"] or "*No text content was saved.*"
    )

    embed.add_field(
        name="Author",
        value=f"<@{row['author_id']}>",
        inline=False
    )

    embed.add_field(
        name="Deleted",
        value=f"<t:{row['deleted_at']}:R>",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="cs")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def clearsnipe(ctx):
    db_execute(
        "DELETE FROM snipes WHERE channel_id=?",
        (ctx.channel.id,)
    )

    await send_success(ctx, "Saved snipe cleared.")

# =====================================
# SERVER UTILITY COMMANDS
# =====================================

@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def renamechannel(ctx, channel: discord.TextChannel, *, name: str):
    if len(name) > 100:
        return await send_error(ctx, "Channel name is too long.")

    await channel.edit(name=name)
    await send_success(ctx, f"Renamed channel to **{name}**.")


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_roles=True)
async def roleinfo(ctx, role: discord.Role):
    permissions = [
        name.replace("_", " ").title()
        for name, enabled in role.permissions
        if enabled
    ]

    embed = vex_embed(
        f"ROLE INFO • {role.name}",
        f"""
**ID:** `{role.id}`
**Members:** `{len(role.members)}`
**Mentionable:** `{role.mentionable}`
**Hoisted:** `{role.hoist}`
**Color:** `{role.color}`
"""
    )

    embed.add_field(
        name="Permissions",
        value=", ".join(permissions[:20]) or "None",
        inline=False
    )

    await ctx.send(embed=embed)

# =====================================
# OWNER ANNOUNCEMENTS
# =====================================

pending_announcement = None


@bot.command()
@is_bot_owner()
async def announce(ctx, *, message: str):
    global pending_announcement

    if len(message) > 1500:
        return await send_error(ctx, "Announcement is too long.")

    pending_announcement = message

    embed = vex_embed(
        "📢 ANNOUNCEMENT PREVIEW",
        message
    )

    embed.add_field(
        name="Delivery",
        value=f"Will be sent to {len(bot.guilds)} servers.",
        inline=False
    )

    await ctx.send(embed=embed)
    await send_info(
        ctx,
        "Use `!announceconfirm` to send, or `!announcecancel` to cancel."
    )


@bot.command()
@is_bot_owner()
async def announceconfirm(ctx):
    global pending_announcement

    if not pending_announcement:
        return await send_error(ctx, "No pending announcement.")

    message = pending_announcement
    pending_announcement = None

    success = 0
    failed = 0

    for guild in bot.guilds:
        channel = guild.system_channel

        if not channel or not channel.permissions_for(guild.me).send_messages:
            channel = next(
                (
                    ch for ch in guild.text_channels
                    if ch.permissions_for(guild.me).send_messages
                ),
                None
            )

        if not channel:
            failed += 1
            continue

        try:
            await channel.send(
                embed=vex_embed("📢 VEXORA ANNOUNCEMENT", message),
                allowed_mentions=discord.AllowedMentions.none()
            )
            success += 1
        except discord.HTTPException:
            failed += 1

        await asyncio.sleep(1)

    await send_info(
        ctx,
        f"Announcement finished.\n\n"
        f"**Sent:** `{success}`\n"
        f"**Failed:** `{failed}`"
    )


@bot.command()
@is_bot_owner()
async def announcecancel(ctx):
    global pending_announcement

    if not pending_announcement:
        return await send_error(ctx, "No pending announcement.")

    pending_announcement = None
    await send_success(ctx, "Announcement cancelled.")

# =====================================
# FIRST TO REACT GAME
# =====================================

ftr_active = {}


@bot.group(invoke_without_command=True)
@commands.guild_only()
async def ftr(ctx):
    await send_info(
        ctx,
        """
**FTR COMMANDS**

`!ftr start [seconds]`
`!ftr stop`
`!ftr winner`
`!ftr leaderboard`
"""
    )


@ftr.command(name="start")
@commands.has_permissions(manage_guild=True)
async def ftr_start(ctx, seconds: int = 30):
    if not 5 <= seconds <= 300:
        return await send_error(ctx, "Duration must be 5–300 seconds.")

    if ctx.channel.id in ftr_active:
        return await send_error(ctx, "FTR is already running here.")

    embed = vex_embed(
        "⚡ FIRST TO REACT",
        f"React with ⚡ first!\n\n**Time:** {seconds} seconds"
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("⚡")

    ftr_active[ctx.channel.id] = {
        "message_id": message.id,
        "winner": None,
        "ends": time.time() + seconds,
        "guild_id": ctx.guild.id
    }

    await asyncio.sleep(seconds)

    game = ftr_active.get(ctx.channel.id)

    if game and game["message_id"] == message.id:
        winner = game["winner"]
        del ftr_active[ctx.channel.id]

        if winner:
            await ctx.send(
                embed=vex_embed(
                    "🏆 FTR WINNER",
                    f"{winner.mention} reacted first!"
                )
            )
        else:
            await send_info(ctx, "FTR ended. Nobody reacted!")


@ftr.command(name="stop")
@commands.has_permissions(manage_guild=True)
async def ftr_stop(ctx):
    game = ftr_active.pop(ctx.channel.id, None)

    if not game:
        return await send_error(ctx, "No active FTR game.")

    await send_success(ctx, "FTR stopped.")


@ftr.command(name="winner")
async def ftr_winner(ctx):
    game = ftr_active.get(ctx.channel.id)

    if not game:
        return await send_error(ctx, "No active FTR game.")

    winner = game["winner"]

    if not winner:
        return await send_info(ctx, "No winner yet.")

    await send_info(ctx, f"Current winner: {winner.mention}")


@ftr.command(name="leaderboard")
@commands.guild_only()
async def ftr_leaderboard(ctx):
    rows = db_fetchall(
        """
        SELECT user_id, wins
        FROM ftr_scores
        WHERE guild_id=?
        ORDER BY wins DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    )

    if not rows:
        return await send_info(ctx, "No FTR wins yet.")

    lines = [
        f"**{i}.** <@{row['user_id']}> — `{row['wins']} wins`"
        for i, row in enumerate(rows, 1)
    ]

    await ctx.send(embed=vex_embed(
        "⚡ FTR LEADERBOARD",
        "\n".join(lines)
    ))


@bot.listen("on_raw_reaction_add")
async def ftr_reaction(payload):
    if str(payload.emoji) != "⚡":
        return

    if payload.member is None or payload.member.bot:
        return

    game = ftr_active.get(payload.channel_id)

    if not game or game["message_id"] != payload.message_id:
        return

    if game["winner"] is not None:
        return

    game["winner"] = payload.member

    db_execute(
        """
        INSERT INTO ftr_scores (guild_id, user_id, wins)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET wins=wins+1
        """,
        (payload.guild_id, payload.user_id)
    )

# =====================================
# BOT STATUS CONTROLS
# =====================================

@bot.command()
@is_bot_owner()
async def playing(ctx, *, text: str):
    await bot.change_presence(
        activity=discord.Game(name=text)
    )

    await send_success(ctx, f"Playing status changed to **{text}**.")


@bot.command()
@is_bot_owner()
async def status(ctx, state: str):
    statuses = {
        "online": discord.Status.online,
        "offline": discord.Status.invisible,
        "dnd": discord.Status.dnd,
        "sleep": discord.Status.idle
    }

    state = state.lower()

    if state not in statuses:
        return await send_error(
            ctx, "Choose: `online`, `offline`, `dnd`, or `sleep`."
        )

    await bot.change_presence(
        status=statuses[state]
    )

    await send_success(ctx, f"Bot status changed to **{state}**.")


@bot.command()
@is_bot_owner()
async def stext(ctx, *, text: str):
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=text
        )
    )

    await send_success(ctx, f"Activity text changed to **{text}**.")

# =====================================
# PREMIUM CUSTOM COMMANDS
# =====================================

@bot.group(invoke_without_command=True)
@commands.guild_only()
async def cc(ctx):
    await send_info(
        ctx,
        """
**PREMIUM CUSTOM COMMANDS**

`!cc add <name> <response>`
`!cc edit <name> <response>`
`!cc remove <name>`
`!cc list`
`!cc info <name>`

Custom commands are a Premium feature.
"""
    )


@cc.command(name="add")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def cc_add(ctx, name: str, *, response: str):
    if not await is_premium(ctx.guild.id):
        return await send_error(ctx, "This server needs Premium.")

    name = name.lower()

    if not re.fullmatch(r"[a-z0-9_-]{2,32}", name):
        return await send_error(
            ctx, "Use 2–32 letters, numbers, underscores or hyphens."
        )

    if bot.get_command(name):
        return await send_error(ctx, "That name is already a built-in command.")

    if len(response) > 1500:
        return await send_error(ctx, "Response is too long.")

    existing = db_fetchone(
        "SELECT name FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name)
    )

    if existing:
        return await send_error(ctx, "That custom command already exists.")

    db_execute(
        """
        INSERT INTO custom_commands (guild_id, name, response, created_by)
        VALUES (?, ?, ?, ?)
        """,
        (ctx.guild.id, name, response, ctx.author.id)
    )

    await send_success(ctx, f"Custom command `!{name}` created!")


@cc.command(name="edit")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def cc_edit(ctx, name: str, *, response: str):
    if not await is_premium(ctx.guild.id):
        return await send_error(ctx, "This server needs Premium.")

    name = name.lower()

    if len(response) > 1500:
        return await send_error(ctx, "Response is too long.")

    result = db_execute(
        """
        UPDATE custom_commands
        SET response=?
        WHERE guild_id=? AND name=?
        """,
        (response, ctx.guild.id, name)
    )

    if result.rowcount == 0:
        return await send_error(ctx, "Custom command not found.")

    await send_success(ctx, f"`!{name}` updated!")


@cc.command(name="remove")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def cc_remove(ctx, name: str):
    if not await is_premium(ctx.guild.id):
        return await send_error(ctx, "This server needs Premium.")

    result = db_execute(
        "DELETE FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name.lower())
    )

    if result.rowcount == 0:
        return await send_error(ctx, "Custom command not found.")

    await send_success(ctx, f"`!{name}` removed.")


@cc.command(name="list")
@commands.guild_only()
async def cc_list(ctx):
    if not await is_premium(ctx.guild.id):
        return await send_error(ctx, "This server needs Premium.")

    rows = db_fetchall(
        """
        SELECT name FROM custom_commands
        WHERE guild_id=?
        ORDER BY name
        """,
        (ctx.guild.id,)
    )

    if not rows:
        return await send_info(ctx, "No custom commands created yet.")

    names = [f"`!{row['name']}`" for row in rows]

    await ctx.send(embed=vex_embed(
        "⚙️ CUSTOM COMMANDS",
        "\n".join(names)
    ))


@cc.command(name="info")
@commands.guild_only()
async def cc_info(ctx, name: str):
    if not await is_premium(ctx.guild.id):
        return await send_error(ctx, "This server needs Premium.")

    row = db_fetchone(
        """
        SELECT name, response, created_by
        FROM custom_commands
        WHERE guild_id=? AND name=?
        """,
        (ctx.guild.id, name.lower())
    )

    if not row:
        return await send_error(ctx, "Custom command not found.")

    await ctx.send(embed=vex_embed(
        f"CUSTOM COMMAND • {row['name']}",
        f"**Response:**\n{row['response']}\n\n"
        f"**Created by:** <@{row['created_by']}>"
    ))


# Custom command execution listener
@bot.listen("on_message")
async def execute_custom_commands(message):
    if message.author.bot or not message.guild:
        return

    used_prefix = next(
        (
            prefix for prefix in PREFIXES
            if message.content.startswith(prefix)
        ),
        None
    )

    if not used_prefix:
        return

    content = message.content[len(used_prefix):].strip()

    if not content:
        return

    name = content.split(maxsplit=1)[0].lower()

    # Built-in commands always take priority.
    if bot.get_command(name):
        return

    if not await is_premium(message.guild.id):
        return

    row = db_fetchone(
        """
        SELECT response FROM custom_commands
        WHERE guild_id=? AND name=?
        """,
        (message.guild.id, name)
    )

    if not row:
        return

    await message.channel.send(
        row["response"],
        allowed_mentions=discord.AllowedMentions.none()
    )

# =====================================
# DYNAMIC HELP COMMAND
# =====================================

@bot.command(name="help")
async def help_command(ctx, *, command_name: str = None):

    if command_name:
        command = bot.get_command(command_name.lower())

        if not command:
            return await send_error(ctx, "Command not found.")

        description = command.help or command.short_doc or "No description."

        if isinstance(command, commands.Group):
            subcommands = [
                f"`{sub.name}`"
                for sub in command.commands
            ]

            description += "\n\n**Subcommands:**\n"
            description += ", ".join(subcommands) or "None"

        return await ctx.send(
            embed=vex_embed(
                f"HELP • {command.qualified_name}",
                description
            )
        )

    categories = {
        "General": [],
        "Moderation": [],
        "Economy & Games": [],
        "Social & Levels": [],
        "Server Tools": [],
        "Premium & Owner": []
    }

    moderation = {
        "ban", "unban", "modkick", "timeout", "untimeout",
        "purge", "lock", "unlock", "slowmode", "warn",
        "warnings", "clearwarns", "staff"
    }

    economy = {
        "balance", "daily", "weekly", "work", "beg",
        "pay", "leaderboard", "flip", "dice", "rps",
        "guess", "trivia"
    }

    social = {
        "rep", "reps", "repboard", "rank", "level",
        "levels", "afk", "kiss", "punch", "kick"
    }

    server_tools = {
        "confess", "confesssetup", "confessionsoff",
        "suggest", "suggestsetup", "poll", "invites",
        "inviter", "inviteinfo", "topinvites", "rr",
        "ticketsetup", "ticket", "claim", "close",
        "s", "cs", "renamechannel", "roleinfo",
        "gstart", "gend", "gcancel", "greroll",
        "ftr"
    }

    owner_tools = {
        "premium", "cc", "announce", "announceconfirm",
        "announcecancel", "playing", "status", "stext"
    }

    for command in bot.commands:
        if command.hidden:
            continue

        name = command.name

        if name == "help":
            categories["General"].append(name)
        elif name in moderation:
            categories["Moderation"].append(name)
        elif name in economy:
            categories["Economy & Games"].append(name)
        elif name in social:
            categories["Social & Levels"].append(name)
        elif name in server_tools:
            categories["Server Tools"].append(name)
        elif name in owner_tools:
            categories["Premium & Owner"].append(name)
        else:
            categories["General"].append(name)

    embed = vex_embed(
        "🤖 VEXORA COMMAND CENTER",
        "One Bot. Endless Possibilities.\n"
        "Use `!help <command>` for command details."
    )

    for category, names in categories.items():
        if names:
            embed.add_field(
                name=category,
                value=" • ".join(f"`{name}`" for name in sorted(set(names))),
                inline=False
            )

    embed.add_field(
        name="Prefixes",
        value="`!` `?` `.` `$` `-`",
        inline=False
    )

    embed.set_thumbnail(url=bot.user.display_avatar.url)

    await ctx.send(embed=embed)

# =====================================
# VEXORA STARTUP
# =====================================

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing!"
    )

bot.run(TOKEN)
