
import discord
from discord.ext import commands
import aiosqlite
import asyncio
import os
import random
import time
from datetime import datetime, timedelta, timezone

# ==========================================
# VEXORA CONFIGURATION
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1495419933943922920

PREFIXES = ["!", "?", ".", "$"]
DB_NAME = "vexora.db"

# BLACK / SILVER / WHITE THEME
BLACK = 0x101010
DARK = 0x202020
SILVER = 0xA8A8A8
WHITE = 0xFFFFFF
SUCCESS = 0xBFC7CE
ERROR = 0x555555

# ==========================================
# BOT INTENTS
# ==========================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.reactions = True
intents.invites = True
intents.messages = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# ==========================================
# EMBED SYSTEM
# ==========================================

def vex_embed(title, description=None, color=BLACK):
    embed = discord.Embed(
        title=f"◆ {title}",
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(
        text="VEXORA • One Bot. Endless Possibilities."
    )
    return embed


async def send_success(ctx, message):
    await ctx.send(
        embed=vex_embed("SUCCESS", message, SUCCESS),
        allowed_mentions=discord.AllowedMentions.none()
    )


async def send_error(ctx, message):
    await ctx.send(
        embed=vex_embed("ERROR", message, ERROR),
        allowed_mentions=discord.AllowedMentions.none()
    )


async def send_info(ctx, message):
    await ctx.send(
        embed=vex_embed("VEXORA", message, SILVER),
        allowed_mentions=discord.AllowedMentions.none()
    )


# ==========================================
# DATABASE
# ==========================================

async def setup_database():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS premium (
            guild_id INTEGER PRIMARY KEY,
            activated_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS economy (
            guild_id INTEGER,
            user_id INTEGER,
            balance INTEGER DEFAULT 0,
            last_daily REAL DEFAULT 0,
            last_weekly REAL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS reputation (
            guild_id INTEGER,
            giver_id INTEGER,
            receiver_id INTEGER,
            reason TEXT,
            created_at REAL
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            guild_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            channel_id INTEGER,
            prize TEXT,
            winners INTEGER,
            end_time REAL,
            host_id INTEGER,
            ended INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
            guild_id INTEGER,
            message_id INTEGER,
            emoji TEXT,
            role_id INTEGER,
            PRIMARY KEY (message_id, emoji)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            guild_id INTEGER,
            user_id INTEGER,
            inviter_id INTEGER,
            uses INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS confessions (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            enabled INTEGER DEFAULT 0,
            next_number INTEGER DEFAULT 1
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS snipes (
            channel_id INTEGER PRIMARY KEY,
            author_id INTEGER,
            content TEXT,
            deleted_at REAL
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            leave_channel INTEGER,
            log_channel INTEGER,
            suggestion_channel INTEGER,
            ticket_category INTEGER,
            welcome_message TEXT,
            leave_message TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS afk (
            guild_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            created_at REAL,
            PRIMARY KEY (guild_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS birthdays (
            guild_id INTEGER,
            user_id INTEGER,
            birthday TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
        """)

        await db.commit()


async def db_execute(query, params=()):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(query, params)
        await db.commit()


async def db_fetchone(query, params=()):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()


async def db_fetchall(query, params=()):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


# ==========================================
# PERMISSION HELPERS
# ==========================================

def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)


def is_staff():
    async def predicate(ctx):
        return (
            ctx.author.guild_permissions.administrator
            or ctx.author.guild_permissions.manage_guild
            or ctx.author.guild_permissions.manage_messages
        )
    return commands.check(predicate)


async def is_premium(guild_id):
    result = await db_fetchone(
        "SELECT guild_id FROM premium WHERE guild_id = ?",
        (guild_id,)
    )
    return result is not None


# ==========================================
# BOT EVENTS
# ==========================================

@bot.event
async def on_ready():
    await setup_database()

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="VEXORA | !help"
        )
    )

    print("--------------------------------")
    print(f"VEXORA is online as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("--------------------------------")


@bot.event
async def on_guild_join(guild):
    print(f"Joined server: {guild.name} ({guild.id})")


@bot.event
async def on_guild_remove(guild):
    print(f"Left server: {guild.name} ({guild.id})")


# ==========================================
# BASIC COMMANDS
# ==========================================

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)

    embed = vex_embed(
        "PONG",
        f"**Latency:** `{latency}ms`\n"
        f"**Status:** Online",
        SILVER
    )

    await ctx.send(embed=embed)


@bot.command(name="botinfo")
async def botinfo(ctx):
    embed = vex_embed(
        "BOT INFORMATION",
        "One Bot. Endless Possibilities.",
        SILVER
    )

    embed.add_field(
        name="Bot",
        value=bot.user.name,
        inline=True
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Users",
        value=str(len(bot.users)),
        inline=True
    )

    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="Prefixes",
        value="`!` `?` `.` `$`",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_command(ctx):
    embed = vex_embed(
        "VEXORA COMMANDS",
        "Use `!help` to view the command list.\n"
        "More command categories will be added in Part 2.",
        SILVER
    )

    embed.add_field(
        name="General",
        value="`!ping` `!botinfo` `!help`",
        inline=False
    )

    embed.add_field(
        name="Prefixes",
        value="`!` `?` `.` `$`",
        inline=False
    )

    await ctx.send(embed=embed)


# ==========================================
# ERROR HANDLING
# ==========================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await send_error(
            ctx,
            "You don't have permission to use this command."
        )
        return

    if isinstance(error, commands.BotMissingPermissions):
        await send_error(
            ctx,
            "I don't have the required permissions."
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await send_error(
            ctx,
            f"Missing argument: `{error.param.name}`"
        )
        return

    if isinstance(error, commands.BadArgument):
        await send_error(ctx, "Invalid argument.")
        return

    if isinstance(error, commands.CommandOnCooldown):
        await send_error(
            ctx,
            f"Try again in {error.retry_after:.1f} seconds."
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        await send_error(
            ctx,
            "This command can only be used in a server."
        )
        return

    if isinstance(error, discord.Forbidden):
        await send_error(
            ctx,
            "Discord denied that action. Check my permissions."
        )
        return

    print(f"Command error: {repr(error)}")

    await send_error(
        ctx,
        "Something went wrong while running that command."
    )


# ==========================================
# PART 2 GOES ABOVE THE FINAL STARTUP
# ==========================================


# ==========================================
# VEXORA PART 2
# PASTE DIRECTLY UNDER PART 1
# ==========================================

# ==========================================
# MODERATION
# ==========================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
        return await send_error(ctx, "You cannot ban someone with an equal or higher role.")

    await member.ban(reason=reason)
    await send_success(ctx, f"**{member}** was banned.\nReason: {reason}")


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await send_success(ctx, f"Unbanned **{user}**.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def modkick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await send_success(ctx, f"**{member}** was kicked.\nReason: {reason}")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    if not 1 <= minutes <= 40320:
        return await send_error(ctx, "Choose between 1 and 40320 minutes.")

    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await send_success(ctx, f"Timed out **{member}** for {minutes} minutes.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await send_success(ctx, f"Removed timeout from **{member}**.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if not 1 <= amount <= 100:
        return await send_error(ctx, "Choose an amount between 1 and 100.")

    deleted = await ctx.channel.purge(limit=amount + 1)
    await send_info(ctx, f"Deleted **{len(deleted) - 1}** messages.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=False
    )
    await send_success(ctx, "This channel has been locked.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=None
    )
    await send_success(ctx, "This channel has been unlocked.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if not 0 <= seconds <= 21600:
        return await send_error(ctx, "Choose 0–21600 seconds.")

    await ctx.channel.edit(slowmode_delay=seconds)
    await send_success(ctx, f"Slowmode set to **{seconds} seconds**.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    await db_execute(
        """INSERT INTO warnings
        (guild_id, user_id, moderator_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (
            ctx.guild.id,
            member.id,
            ctx.author.id,
            reason,
            datetime.now(timezone.utc).isoformat()
        )
    )
    await send_success(ctx, f"Warned **{member}**.\nReason: {reason}")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warnings(ctx, member: discord.Member):
    rows = await db_fetchall(
        "SELECT reason, moderator_id FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    embed = vex_embed("WARNINGS", f"Warnings for **{member}**", SILVER)

    if not rows:
        embed.description = "No warnings found."
    else:
        for index, (reason, moderator_id) in enumerate(rows, 1):
            embed.add_field(
                name=f"Warning {index}",
                value=f"{reason}\nModerator ID: `{moderator_id}`",
                inline=False
            )

    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    await db_execute(
        "DELETE FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )
    await send_success(ctx, f"Cleared warnings for **{member}**.")


@bot.command()
async def staff(ctx):
    roles = [
        role for role in ctx.guild.roles
        if role.name.lower() in (
            "staff", "admin", "administrator",
            "moderator", "mod", "management"
        )
    ]

    embed = vex_embed("SERVER STAFF", color=SILVER)

    if not roles:
        embed.description = "No staff roles were found."
    else:
        for role in roles:
            members = [m for m in role.members]
            names = ", ".join(m.display_name for m in members[:15]) or "No members"
            embed.add_field(
                name=f"{role.name} • {len(members)}",
                value=names,
                inline=False
            )

    await ctx.send(
        embed=embed,
        allowed_mentions=discord.AllowedMentions.none()
    )


# ==========================================
# PREMIUM MANAGEMENT
# ==========================================

@bot.group(invoke_without_command=True)
async def premium(ctx):
    embed = vex_embed(
        "VEXORA PREMIUM",
        "Premium features include:\n"
        "• Advanced server management\n"
        "• Custom server settings\n"
        "• Premium configuration features\n\n"
        "For premium information, visit our support server:\n"
        "https://discord.gg/ZBaRByVFBC\n\n"
        "If the invite expires, DM **@n0pw**.",
        SILVER
    )
    await ctx.send(embed=embed)


@premium.command(name="add")
@is_bot_owner()
async def premium_add(ctx, guild_id: int):
    await db_execute(
        "INSERT OR IGNORE INTO premium (guild_id, activated_at) VALUES (?, ?)",
        (guild_id, datetime.now(timezone.utc).isoformat())
    )
    await send_success(ctx, f"Premium enabled for server `{guild_id}`.")


@premium.command(name="remove")
@is_bot_owner()
async def premium_remove(ctx, guild_id: int):
    await db_execute(
        "DELETE FROM premium WHERE guild_id=?",
        (guild_id,)
    )
    await send_success(ctx, f"Premium removed from `{guild_id}`.")


@premium.command(name="check")
@is_bot_owner()
async def premium_check(ctx, guild_id: int):
    active = await is_premium(guild_id)
    await send_info(ctx, f"Server `{guild_id}` premium: **{'Active' if active else 'Inactive'}**")


@premium.command(name="list")
@is_bot_owner()
async def premium_list(ctx):
    rows = await db_fetchall("SELECT guild_id FROM premium")
    result = "\n".join(f"`{row[0]}`" for row in rows) or "No premium servers."
    await ctx.send(embed=vex_embed("PREMIUM SERVERS", result, SILVER))


# ==========================================
# VEX VIRTUAL ECONOMY
# NO REAL MONEY OR WAGERING
# ==========================================

async def ensure_economy(guild_id, user_id):
    await db_execute(
        "INSERT OR IGNORE INTO economy (guild_id, user_id) VALUES (?, ?)",
        (guild_id, user_id)
    )


@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ensure_economy(ctx.guild.id, member.id)

    row = await db_fetchone(
        "SELECT balance FROM economy WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    await ctx.send(embed=vex_embed(
        "VEX BALANCE",
        f"**{member.display_name}** has **{row[0]} VEX**.",
        SILVER
    ))


@bot.command()
async def daily(ctx):
    await ensure_economy(ctx.guild.id, ctx.author.id)

    row = await db_fetchone(
        "SELECT last_daily FROM economy WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    )

    now = time.time()
    if now - row[0] < 86400:
        remaining = int(86400 - (now - row[0]))
        return await send_error(ctx, f"Your next daily reward is available in {remaining // 3600} hours.")

    reward = random.randint(100, 250)

    await db_execute(
        "UPDATE economy SET balance=balance+?, last_daily=? WHERE guild_id=? AND user_id=?",
        (reward, now, ctx.guild.id, ctx.author.id)
    )

    await send_success(ctx, f"You received **{reward} VEX** as your daily reward!")


@bot.command()
async def weekly(ctx):
    await ensure_economy(ctx.guild.id, ctx.author.id)

    row = await db_fetchone(
        "SELECT last_weekly FROM economy WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    )

    now = time.time()
    if now - row[0] < 604800:
        return await send_error(ctx, "Your weekly reward is not ready yet.")

    reward = 750

    await db_execute(
        "UPDATE economy SET balance=balance+?, last_weekly=? WHERE guild_id=? AND user_id=?",
        (reward, now, ctx.guild.id, ctx.author.id)
    )

    await send_success(ctx, f"You received **{reward} VEX**!")


@bot.command()
async def work(ctx):
    await ensure_economy(ctx.guild.id, ctx.author.id)
    reward = random.randint(30, 100)

    await db_execute(
        "UPDATE economy SET balance=balance+? WHERE guild_id=? AND user_id=?",
        (reward, ctx.guild.id, ctx.author.id)
    )

    await send_success(ctx, f"You completed a task and earned **{reward} VEX**!")


@bot.command()
async def beg(ctx):
    await ensure_economy(ctx.guild.id, ctx.author.id)
    reward = random.randint(5, 25)

    await db_execute(
        "UPDATE economy SET balance=balance+? WHERE guild_id=? AND user_id=?",
        (reward, ctx.guild.id, ctx.author.id)
    )

    await send_info(ctx, f"Someone gave you **{reward} VEX**!")


@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id:
        return await send_error(ctx, "Choose another human member.")

    if amount <= 0:
        return await send_error(ctx, "Amount must be positive.")

    await ensure_economy(ctx.guild.id, ctx.author.id)
    await ensure_economy(ctx.guild.id, member.id)

    sender = await db_fetchone(
        "SELECT balance FROM economy WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    )

    if sender[0] < amount:
        return await send_error(ctx, "You don't have enough VEX.")

    await db_execute(
        "UPDATE economy SET balance=balance-? WHERE guild_id=? AND user_id=?",
        (amount, ctx.guild.id, ctx.author.id)
    )

    await db_execute(
        "UPDATE economy SET balance=balance+? WHERE guild_id=? AND user_id=?",
        (amount, ctx.guild.id, member.id)
    )

    await send_success(ctx, f"Transferred **{amount} VEX** to **{member.display_name}**.")


@bot.command(name="leaderboard")
async def economy_leaderboard(ctx):
    rows = await db_fetchall(
        "SELECT user_id, balance FROM economy WHERE guild_id=? ORDER BY balance DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = ""
    for index, (user_id, balance_value) in enumerate(rows, 1):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else f"User {user_id}"
        description += f"**{index}.** {name} — `{balance_value} VEX`\n"

    await ctx.send(embed=vex_embed(
        "VEX LEADERBOARD",
        description or "No balances yet.",
        SILVER
    ))


# ==========================================
# FREE-PLAY MINI GAMES
# NO BETS OR CURRENCY LOSSES
# ==========================================

@bot.command()
async def flip(ctx):
    result = random.choice(["Heads", "Tails"])
    await send_info(ctx, f"The coin landed on **{result}**!")


@bot.command()
async def dice(ctx):
    result = random.randint(1, 6)
    await send_info(ctx, f"Your dice rolled **{result}**!")


@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    choices = ["rock", "paper", "scissors"]

    if choice not in choices:
        return await send_error(ctx, "Choose rock, paper, or scissors.")

    bot_choice = random.choice(choices)

    if choice == bot_choice:
        result = "It's a draw!"
    elif (choice, bot_choice) in [
        ("rock", "scissors"),
        ("paper", "rock"),
        ("scissors", "paper")
    ]:
        result = "You win!"
    else:
        result = "VEXORA wins!"

    await send_info(ctx, f"You chose **{choice}**.\nI chose **{bot_choice}**.\n\n{result}")


@bot.command()
async def guess(ctx):
    number = random.randint(1, 5)
    await send_info(ctx, f"Your number is **{number}**! Try `!guess <number>` next time.")


@bot.command()
async def trivia(ctx):
    questions = [
        ("Which planet is known as the Red Planet?", "mars"),
        ("How many sides does a hexagon have?", "6"),
        ("What is the largest ocean?", "pacific"),
        ("What is H2O commonly called?", "water")
    ]

    question, answer = random.choice(questions)
    await send_info(ctx, f"**Question:** {question}\nAnswer: ||{answer}||")


# ==========================================
# REPUTATION SYSTEM
# ==========================================

@bot.command()
async def rep(ctx, member: discord.Member, *, reason="Being awesome"):
    if member.bot or member.id == ctx.author.id:
        return await send_error(ctx, "You cannot give reputation to yourself or a bot.")

    previous = await db_fetchone(
        """SELECT created_at FROM reputation
        WHERE guild_id=? AND giver_id=? AND receiver_id=?
        ORDER BY created_at DESC LIMIT 1""",
        (ctx.guild.id, ctx.author.id, member.id)
    )

    now = time.time()

    if previous and now - previous[0] < 86400:
        return await send_error(ctx, "You can give this person reputation once every 24 hours.")

    await db_execute(
        """INSERT INTO reputation
        (guild_id, giver_id, receiver_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (ctx.guild.id, ctx.author.id, member.id, reason[:300], now)
    )

    total = await db_fetchone(
        "SELECT COUNT(*) FROM reputation WHERE guild_id=? AND receiver_id=?",
        (ctx.guild.id, member.id)
    )

    embed = vex_embed(
        "+1 REPUTATION",
        f"**{member.display_name}** received +1 REP!\n\n"
        f"**Reason:** {reason}\n"
        f"**Total REP:** {total[0]}",
        SILVER
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="reps")
async def reps(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = await db_fetchone(
        "SELECT COUNT(*) FROM reputation WHERE guild_id=? AND receiver_id=?",
        (ctx.guild.id, member.id)
    )

    embed = vex_embed(
        "REPUTATION PROFILE",
        f"**Member:** {member.mention}\n**Total REP:** `{row[0]}`",
        SILVER
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def repboard(ctx):
    rows = await db_fetchall(
        """SELECT receiver_id, COUNT(*) AS total
        FROM reputation WHERE guild_id=?
        GROUP BY receiver_id ORDER BY total DESC LIMIT 10""",
        (ctx.guild.id,)
    )

    description = ""
    for index, (user_id, total) in enumerate(rows, 1):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else str(user_id)
        description += f"**{index}.** {name} — `{total} REP`\n"

    await ctx.send(embed=vex_embed(
        "REP LEADERBOARD",
        description or "No reputation yet.",
        SILVER
    ))


@bot.command()
@commands.has_permissions(manage_guild=True)
async def repremove(ctx, member: discord.Member):
    row = await db_fetchone(
        "SELECT id FROM reputation WHERE guild_id=? AND receiver_id=? ORDER BY created_at DESC LIMIT 1",
        (ctx.guild.id, member.id)
    )

    if not row:
        return await send_error(ctx, "No reputation found.")

    await db_execute("DELETE FROM reputation WHERE id=?", (row[0],))
    await send_success(ctx, f"Removed one REP from **{member}**.")


# ==========================================
# LEVELS AND XP
# ==========================================

XP_COOLDOWN = {}
XP_COOLDOWN_SECONDS = 60


def xp_required(level):
    return 100 + level * 50


@bot.listen("on_message")
async def leveling_listener(message):
    if message.author.bot or not message.guild or len(message.content.strip()) < 3:
        return

    key = (message.guild.id, message.author.id)
    now = time.time()

    if now - XP_COOLDOWN.get(key, 0) < XP_COOLDOWN_SECONDS:
        return

    XP_COOLDOWN[key] = now

    await db_execute(
        "INSERT OR IGNORE INTO levels (guild_id, user_id) VALUES (?, ?)",
        (message.guild.id, message.author.id)
    )

    row = await db_fetchone(
        "SELECT xp, level FROM levels WHERE guild_id=? AND user_id=?",
        (message.guild.id, message.author.id)
    )

    xp, level = row
    xp += random.randint(5, 15)

    while xp >= xp_required(level):
        xp -= xp_required(level)
        level += 1

        embed = vex_embed(
            "LEVEL UP",
            f"{message.author.mention} reached **Level {level}**!",
            SILVER
        )

        await message.channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

    await db_execute(
        "UPDATE levels SET xp=?, level=? WHERE guild_id=? AND user_id=?",
        (xp, level, message.guild.id, message.author.id)
    )


@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = await db_fetchone(
        "SELECT xp, level FROM levels WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    if not row:
        return await send_info(ctx, "This member has not earned XP yet.")

    xp, level = row
    embed = vex_embed(
        "RANK CARD",
        f"**Member:** {member.display_name}\n"
        f"**Level:** `{level}`\n"
        f"**XP:** `{xp}/{xp_required(level)}`",
        SILVER
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def level(ctx):
    await rank(ctx)


@bot.command()
async def levels(ctx):
    rows = await db_fetchall(
        "SELECT user_id, level, xp FROM levels WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10",
        (ctx.guild.id,)
    )

    description = ""
    for index, (user_id, level_value, xp) in enumerate(rows, 1):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else str(user_id)
        description += f"**{index}.** {name} — Level `{level_value}` ({xp} XP)\n"

    await ctx.send(embed=vex_embed(
        "LEVEL LEADERBOARD",
        description or "No levels yet.",
        SILVER
    ))


# ==========================================
# AFK SYSTEM
# ==========================================

@bot.command()
async def afk(ctx, *, reason="AFK"):
    await db_execute(
        """INSERT OR REPLACE INTO afk
        (guild_id, user_id, reason, created_at)
        VALUES (?, ?, ?, ?)""",
        (ctx.guild.id, ctx.author.id, reason[:200], time.time())
    )

    await send_info(ctx, f"AFK status enabled.\nReason: {reason}")


@bot.listen("on_message")
async def afk_listener(message):
    if message.author.bot or not message.guild:
        return

    own_afk = await db_fetchone(
        "SELECT reason FROM afk WHERE guild_id=? AND user_id=?",
        (message.guild.id, message.author.id)
    )

    if own_afk:
        await db_execute(
            "DELETE FROM afk WHERE guild_id=? AND user_id=?",
            (message.guild.id, message.author.id)
        )
        await message.channel.send(
            embed=vex_embed("WELCOME BACK", "Your AFK status has been removed.", SILVER)
        )

    for member in message.mentions:
        row = await db_fetchone(
            "SELECT reason FROM afk WHERE guild_id=? AND user_id=?",
            (message.guild.id, member.id)
        )
        if row:
            await message.channel.send(
                embed=vex_embed(
                    "MEMBER IS AFK",
                    f"**{member.display_name}** is AFK: {row[0]}",
                    SILVER
                )
            )


# ==========================================
# CONFESSIONS
# ==========================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confesssetup(ctx, channel: discord.TextChannel):
    await db_execute(
        """INSERT OR REPLACE INTO confessions
        (guild_id, channel_id, enabled, next_number)
        VALUES (?, ?, 1, 1)""",
        (ctx.guild.id, channel.id)
    )

    await send_success(ctx, f"Confessions enabled in {channel.mention}.")


@bot.command()
@commands.has_permissions(manage_guild=True)
async def confessionsoff(ctx):
    await db_execute(
        "UPDATE confessions SET enabled=0 WHERE guild_id=?",
        (ctx.guild.id,)
    )
    await send_success(ctx, "Confessions disabled.")


@bot.command()
async def confess(ctx, *, message: str):
    if len(message) > 1500:
        return await send_error(ctx, "Confession is too long.")

    row = await db_fetchone(
        "SELECT channel_id, enabled, next_number FROM confessions WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not row or not row[1]:
        return await send_error(ctx, "Confessions are not enabled.")

    channel = ctx.guild.get_channel(row[0])
    if not channel:
        return await send_error(ctx, "Confession channel was not found.")

    number = row[2]

    embed = vex_embed(
        f"ANONYMOUS CONFESSION #{number}",
        message,
        SILVER
    )

    await channel.send(
        embed=embed,
        allowed_mentions=discord.AllowedMentions.none()
    )

    await db_execute(
        "UPDATE confessions SET next_number=next_number+1 WHERE guild_id=?",
        (ctx.guild.id,)
    )

    await send_success(ctx, "Your confession was submitted.")

# Note: This hides the author's name in the public post.
# Server moderators may still have access to message logs.


# ==========================================
# SUGGESTIONS
# ==========================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def suggestsetup(ctx, channel: discord.TextChannel):
    await db_execute(
        """INSERT OR IGNORE INTO server_settings (guild_id)
        VALUES (?)""",
        (ctx.guild.id,)
    )

    await db_execute(
        "UPDATE server_settings SET suggestion_channel=? WHERE guild_id=?",
        (channel.id, ctx.guild.id)
    )

    await send_success(ctx, f"Suggestions will be posted in {channel.mention}.")


@bot.command()
async def suggest(ctx, *, idea: str):
    row = await db_fetchone(
        "SELECT suggestion_channel FROM server_settings WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not row or not row[0]:
        return await send_error(ctx, "Suggestion channel is not configured.")

    channel = ctx.guild.get_channel(row[0])
    if not channel:
        return await send_error(ctx, "Suggestion channel was not found.")

    embed = vex_embed(
        "NEW SUGGESTION",
        idea[:1500],
        SILVER
    )
    embed.add_field(name="Submitted by", value=ctx.author.display_name)

    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

    await send_success(ctx, "Your suggestion was submitted.")


# ==========================================
# POLLS
# ==========================================

@bot.command()
async def poll(ctx, *, question: str):
    embed = vex_embed("COMMUNITY POLL", question[:1500], SILVER)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# ==========================================
COMMANDS
# ==========================================




# ==========================================
# FINAL HELP COMMAND
# ==========================================

@bot.command(name="commands")
async def commands_list(ctx):
    embed = vex_embed("VEXORA COMMAND LIST", color=SILVER)

    sections = {
        "General": "!ping, !botinfo, !help",
        "Moderation": "!ban, !unban, !modkick, !timeout, !untimeout, !warn, !warnings, !clearwarns, !purge, !lock, !unlock, !slowmode, !staff",
        "Premium": "!premium, !premium add, !premium remove, !premium check, !premium list",
        "Economy": "!balance, !daily, !weekly, !work, !beg, !pay, !leaderboard",
        "Games": "!flip, !dice, !rps, !guess, !trivia",
        "Reputation": "!rep, !reps, !repboard, !repremove",
        "Levels": "!rank, !level, !levels",
        "Community": "!afk, !confess, !confesssetup, !confessionsoff, !suggest, !suggestsetup, !poll",
        "Fun": "!kiss, !punch, !kick"
    }

    for name, value in sections.items():
        embed.add_field(name=name, value=value, inline=False)

    await ctx.send(embed=embed)


# ==========================================
# VEXORA PART 3B
# ==========================================

# EXTRA DATABASE TABLES
async def setup_part3_database():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            guild_id INTEGER,
            channel_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            claimed_by INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ftr_scores (
            guild_id INTEGER,
            user_id INTEGER,
            wins INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
        """)
        await db.commit()


@bot.listen("on_ready")
async def part3_ready():
    await setup_part3_database()


# ==========================================
# GIVEAWAYS
# ==========================================

giveaway_tasks = {}


def parse_duration(value):
    import re
    match = re.fullmatch(r"(\d+)(s|m|h|d)", value.lower())
    if not match:
        return None
    return int(match.group(1)) * {
        "s": 1, "m": 60, "h": 3600, "d": 86400
    }[match.group(2)]


async def finish_giveaway(message_id):
    row = await db_fetchone(
        "SELECT guild_id, channel_id, prize, winners, ended "
        "FROM giveaways WHERE message_id=?",
        (message_id,)
    )
    if not row or row[4]:
        return

    guild = bot.get_guild(row[0])
    channel = guild.get_channel(row[1]) if guild else None
    if not channel:
        return

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        await db_execute(
            "UPDATE giveaways SET ended=1 WHERE message_id=?",
            (message_id,)
        )
        return

    reaction = discord.utils.get(message.reactions, emoji="🎉")
    entrants = []

    if reaction:
        async for user in reaction.users():
            if not user.bot:
                entrants.append(user)

    if entrants:
        winners = random.sample(entrants, min(row[3], len(entrants)))
        winner_text = ", ".join(user.mention for user in winners)
    else:
        winner_text = "No valid entries."

    await channel.send(embed=vex_embed(
        "🎉 GIVEAWAY ENDED",
        f"**Prize:** {row[2]}\n**Winner(s):** {winner_text}"
    ))

    await db_execute(
        "UPDATE giveaways SET ended=1 WHERE message_id=?",
        (message_id,)
    )
    giveaway_tasks.pop(message_id, None)


@bot.command(name="gstart")
@commands.has_guild_permissions(manage_guild=True)
async def gstart(ctx, duration: str, winners: int, *, prize: str):
    seconds = parse_duration(duration)

    if seconds is None or seconds < 10:
        return await send_error(ctx, "Use `10m`, `2h` or `1d`.")

    if not 1 <= winners <= 20:
        return await send_error(ctx, "Choose 1–20 winners.")

    end_time = time.time() + seconds
    embed = vex_embed(
        "🎉 VEXORA GIVEAWAY",
        f"**Prize:** {prize}\n"
        f"**Winners:** {winners}\n"
        f"**Host:** {ctx.author.mention}\n"
        f"**Ends:** <t:{int(end_time)}:R>\n\n"
        "React with 🎉 to enter!"
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    await db_execute("""
        INSERT INTO giveaways
        (message_id, guild_id, channel_id, prize, winners,
         end_time, host_id, ended)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        message.id, ctx.guild.id, ctx.channel.id,
        prize, winners, end_time, ctx.author.id
    ))

    async def timer():
        await asyncio.sleep(seconds)
        await finish_giveaway(message.id)

    giveaway_tasks[message.id] = asyncio.create_task(timer())


@bot.command(name="gend")
@commands.has_guild_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    await finish_giveaway(message_id)
    await send_success(ctx, "Giveaway ended if it was active.")


@bot.command(name="gcancel")
@commands.has_guild_permissions(manage_guild=True)
async def gcancel(ctx, message_id: int):
    await db_execute(
        "UPDATE giveaways SET ended=1 WHERE message_id=?",
        (message_id,)
    )
    task = giveaway_tasks.pop(message_id, None)
    if task:
        task.cancel()
    await send_success(ctx, "Giveaway cancelled.")


@bot.command(name="greroll")
@commands.has_guild_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    row = await db_fetchone(
        "SELECT channel_id FROM giveaways WHERE message_id=? AND ended=1",
        (message_id,)
    )
    if not row:
        return await send_error(ctx, "Finished giveaway not found.")

    channel = ctx.guild.get_channel(row[0])
    if not channel:
        return await send_error(ctx, "Giveaway channel not found.")

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        return await send_error(ctx, "Giveaway message not found.")

    reaction = discord.utils.get(message.reactions, emoji="🎉")
    entrants = []

    if reaction:
        async for user in reaction.users():
            if not user.bot:
                entrants.append(user)

    if not entrants:
        return await send_error(ctx, "No entrants to reroll.")

    winner = random.choice(entrants)
    await ctx.send(embed=vex_embed(
        "🎉 GIVEAWAY REROLL",
        f"New winner: {winner.mention}"
    ))


# ==========================================
# INVITE TRACKING
# ==========================================

invite_cache = {}
member_inviter = {}


@bot.listen("on_ready")
async def cache_invites():
    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = {
                invite.code: invite.uses
                for invite in await guild.invites()
            }
        except discord.Forbidden:
            pass


@bot.listen("on_member_join")
async def track_invite(member):
    try:
        new_invites = await member.guild.invites()
        old_invites = invite_cache.get(member.guild.id, {})
        used = None

        for invite in new_invites:
            if invite.uses > old_invites.get(invite.code, 0):
                used = invite
                break

        invite_cache[member.guild.id] = {
            invite.code: invite.uses for invite in new_invites
        }

        if used and used.inviter:
            member_inviter[member.id] = used.inviter.id
            await db_execute("""
                INSERT INTO invites (guild_id, user_id, inviter_id, uses)
                VALUES (?, ?, ?, 1)
            """, (
                member.guild.id, member.id, used.inviter.id
            ))
    except discord.Forbidden:
        pass


@bot.command(name="invites")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = await db_fetchone("""
        SELECT COUNT(*) FROM invites
        WHERE guild_id=? AND inviter_id=?
    """, (ctx.guild.id, member.id))
    count = row[0] if row else 0

    await ctx.send(embed=vex_embed(
        "📨 INVITES",
        f"{member.mention} has **{count}** tracked invites."
    ))


@bot.command(name="inviter")
async def inviter(ctx, member: discord.Member):
    inviter_id = member_inviter.get(member.id)
    if not inviter_id:
        return await send_info(ctx, "No inviter recorded for this member.")

    await ctx.send(embed=vex_embed(
        "📨 INVITER",
        f"{member.mention} was invited by <@{inviter_id}>."
    ))


@bot.command(name="inviteinfo")
async def inviteinfo(ctx, member: discord.Member):
    inviter_id = member_inviter.get(member.id)
    count = await db_fetchone("""
        SELECT COUNT(*) FROM invites
        WHERE guild_id=? AND inviter_id=?
    """, (ctx.guild.id, member.id))

    await ctx.send(embed=vex_embed(
        "📨 INVITE INFO",
        f"**Member:** {member.mention}\n"
        f"**Invited by:** {f'<@{inviter_id}>' if inviter_id else 'Unknown'}\n"
        f"**Invites:** {count[0] if count else 0}"
    ))


@bot.command(name="topinvites", aliases=["lb"])
async def topinvites(ctx):
    rows = await db_fetchall("""
        SELECT inviter_id, COUNT(*)
        FROM invites WHERE guild_id=?
        GROUP BY inviter_id ORDER BY COUNT(*) DESC LIMIT 10
    """, (ctx.guild.id,))

    if not rows:
        return await send_info(ctx, "No invite data yet.")

    description = "\n".join(
        f"**{i}.** <@{row[0]}> — **{row[1]}**"
        for i, row in enumerate(rows, 1)
    )
    await ctx.send(embed=vex_embed("🏆 INVITE LEADERBOARD", description))


@bot.command(name="i")
async def short_invites(ctx):
    await ctx.invoke(invites)


# ==========================================
# REACTION ROLES
# ==========================================

@bot.group(name="rr", invoke_without_command=True)
async def rr(ctx):
    await send_info(
        ctx,
        "Commands: `!rr create`, `!rr add`, `!rr remove`, `!rr delete`"
    )


@rr.command(name="create")
@commands.has_guild_permissions(manage_roles=True)
async def rr_create(ctx, *, text: str):
    message = await ctx.send(embed=vex_embed("🎭 REACTION ROLES", text))
    await send_success(ctx, f"Created message ID: `{message.id}`")


@rr.command(name="add")
@commands.has_guild_permissions(manage_roles=True)
async def rr_add(ctx, message_id: int, emoji: str, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await send_error(ctx, "My highest role must be above that role.")

    try:
        message = await ctx.channel.fetch_message(message_id)
        await message.add_reaction(emoji)
        await db_execute("""
            INSERT OR REPLACE INTO reaction_roles
            (guild_id, message_id, emoji, role_id)
            VALUES (?, ?, ?, ?)
        """, (ctx.guild.id, message_id, emoji, role.id))
        await send_success(ctx, "Reaction role added.")
    except discord.NotFound:
        await send_error(ctx, "Message not found in this channel.")
    except discord.HTTPException:
        await send_error(ctx, "Couldn't use that emoji.")


@rr.command(name="remove")
@commands.has_guild_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, emoji: str):
    await db_execute(
        "DELETE FROM reaction_roles WHERE message_id=? AND emoji=?",
        (message_id, emoji)
    )
    await send_success(ctx, "Reaction role removed.")


@rr.command(name="delete")
@commands.has_guild_permissions(manage_roles=True)
async def rr_delete(ctx, message_id: int):
    await db_execute(
        "DELETE FROM reaction_roles WHERE message_id=?",
        (message_id,)
    )
    await send_success(ctx, "Reaction roles deleted.")


@bot.listen("on_raw_reaction_add")
async def give_reaction_role(payload):
    if payload.member and payload.member.bot:
        return
    if payload.guild_id is None:
        return

    row = await db_fetchone("""
        SELECT role_id FROM reaction_roles
        WHERE message_id=? AND emoji=?
    """, (payload.message_id, str(payload.emoji)))

    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    role = guild.get_role(row[0]) if guild else None

    if member and role and role < guild.me.top_role:
        try:
            await member.add_roles(role, reason="VEXORA reaction role")
        except discord.Forbidden:
            pass


@bot.listen("on_raw_reaction_remove")
async def remove_reaction_role(payload):
    if payload.guild_id is None:
        return

    row = await db_fetchone("""
        SELECT role_id FROM reaction_roles
        WHERE message_id=? AND emoji=?
    """, (payload.message_id, str(payload.emoji)))

    if not row:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    role = guild.get_role(row[0]) if guild else None

    if member and role and role < guild.me.top_role:
        try:
            await member.remove_roles(role, reason="VEXORA reaction role")
        except discord.Forbidden:
            pass


# ==========================================
# TICKETS
# ==========================================

@bot.command(name="ticketsetup")
@commands.has_guild_permissions(manage_guild=True)
async def ticketsetup(ctx, category: discord.CategoryChannel):
    await db_execute("""
        INSERT OR REPLACE INTO server_settings (guild_id, ticket_category)
        VALUES (?, ?)
    """, (ctx.guild.id, category.id))
    await send_success(ctx, f"Ticket category set to **{category.name}**.")


@bot.command(name="ticket")
async def ticket(ctx):
    row = await db_fetchone(
        "SELECT ticket_category FROM server_settings WHERE guild_id=?",
        (ctx.guild.id,)
    )

    if not row or not row[0]:
        return await send_error(ctx, "Tickets aren't configured.")

    category = ctx.guild.get_channel(row[0])
    if not isinstance(category, discord.CategoryChannel):
        return await send_error(ctx, "Ticket category not found.")

    existing = await db_fetchone("""
        SELECT channel_id FROM tickets
        WHERE guild_id=? AND user_id=? AND status='open'
    """, (ctx.guild.id, ctx.author.id))

    if existing and ctx.guild.get_channel(existing[0]):
        return await send_info(ctx, f"You already have <#{existing[0]}>.")

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            manage_channels=True, read_message_history=True
        )
    }

    channel = await ctx.guild.create_text_channel(
        name=f"ticket-{ctx.author.id}",
        category=category,
        overwrites=overwrites
    )

    await db_execute("""
        INSERT INTO tickets (guild_id, channel_id, user_id)
        VALUES (?, ?, ?)
    """, (ctx.guild.id, channel.id, ctx.author.id))

    await channel.send(
        f"{ctx.author.mention}",
        embed=vex_embed(
            "🎫 SUPPORT TICKET",
            "Describe your issue here.\nStaff can use `!claim` and `!close`."
        )
    )
    await send_success(ctx, f"Ticket created: {channel.mention}")


@bot.command(name="claim")
async def claim(ctx):
    row = await db_fetchone(
        "SELECT channel_id FROM tickets WHERE channel_id=? AND status='open'",
        (ctx.channel.id,)
    )
    if not row:
        return await send_error(ctx, "This isn't an open ticket.")

    if not (
        ctx.author.guild_permissions.manage_channels
        or ctx.author.guild_permissions.manage_messages
    ):
        return await send_error(ctx, "Staff only.")

    await db_execute(
        "UPDATE tickets SET claimed_by=? WHERE channel_id=?",
        (ctx.author.id, ctx.channel.id)
    )
    await send_success(ctx, f"Claimed by {ctx.author.mention}.")


@bot.command(name="close")
async def close(ctx):
    row = await db_fetchone("""
        SELECT user_id FROM tickets
        WHERE channel_id=? AND status='open'
    """, (ctx.channel.id,))

    if not row:
        return await send_error(ctx, "This isn't an open ticket.")

    is_owner = row[0] == ctx.author.id
    is_staff = (
        ctx.author.guild_permissions.manage_channels
        or ctx.author.guild_permissions.manage_messages
    )

    if not is_owner and not is_staff:
        return await send_error(ctx, "Only the ticket owner or staff can close it.")

    await db_execute(
        "UPDATE tickets SET status='closed' WHERE channel_id=?",
        (ctx.channel.id,)
    )
    await send_success(ctx, "Ticket closing in 5 seconds.")
    await asyncio.sleep(5)
    await ctx.channel.delete(reason="Ticket closed")


# ==========================================
# SNIPE
# ==========================================

@bot.listen("on_message_delete")
async def save_snipe(message):
    if message.guild and not message.author.bot and message.content:
        await db_execute("""
            INSERT OR REPLACE INTO snipes
            (channel_id, author_id, content, deleted_at)
            VALUES (?, ?, ?, ?)
        """, (
            message.channel.id,
            message.author.id,
            message.content[:1500],
            int(time.time())
        ))


@bot.command(name="s")
async def snipe(ctx):
    row = await db_fetchone("""
        SELECT author_id, content, deleted_at
        FROM snipes WHERE channel_id=?
    """, (ctx.channel.id,))

    if not row:
        return await send_info(ctx, "Nothing to snipe here.")

    await ctx.send(embed=vex_embed(
        "🕵️ LAST DELETED MESSAGE",
        f"**Author:** <@{row[0]}>\n"
        f"**Message:** {row[1]}\n"
        f"**Deleted:** <t:{row[2]}:R>"
    ))


@bot.command(name="cs")
@commands.has_guild_permissions(manage_messages=True)
async def clearsnipe(ctx):
    await db_execute(
        "DELETE FROM snipes WHERE channel_id=?",
        (ctx.channel.id,)
    )
    await send_success(ctx, "Snipe cleared.")


# ==========================================
# OWNER GLOBAL ANNOUNCEMENTS
# ==========================================

pending_announcement = {}


@bot.command(name="announce")
async def announce(ctx, *, message: str):
    if not await is_bot_owner(ctx.author):
        return await send_error(ctx, "Bot owner only.")

    pending_announcement[ctx.author.id] = message
    await ctx.send(embed=vex_embed(
        "📢 ANNOUNCEMENT PREVIEW",
        f"{message}\n\n"
        "Use `!announceconfirm` to send it, "
        "or `!announcecancel` to cancel."
    ))


@bot.command(name="announceconfirm")
async def announceconfirm(ctx):
    if not await is_bot_owner(ctx.author):
        return await send_error(ctx, "Bot owner only.")

    message = pending_announcement.pop(ctx.author.id, None)
    if not message:
        return await send_error(ctx, "No pending announcement.")

    sent = 0

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(
                        embed=vex_embed("📢 VEXORA ANNOUNCEMENT", message),
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                    sent += 1
                    break
                except discord.HTTPException:
                    continue

    await ctx.send(embed=vex_embed(
        "📢 ANNOUNCEMENT COMPLETE",
        f"Sent to **{sent}** servers."
    ))


@bot.command(name="announcecancel")
async def announcecancel(ctx):
    if not await is_bot_owner(ctx.author):
        return await send_error(ctx, "Bot owner only.")
    pending_announcement.pop(ctx.author.id, None)
    await send_success(ctx, "Announcement cancelled.")


# ==========================================
# FTR — FIRST TO REACT
# ==========================================

active_ftr = {}
last_ftr_winner = {}


@bot.group(name="ftr", invoke_without_command=True)
async def ftr(ctx):
    await send_info(
        ctx,
        "Use `!ftr start`, `!ftr stop`, `!ftr winner`, "
        "or `!ftr leaderboard`."
    )


@ftr.command(name="start")
@commands.has_guild_permissions(manage_guild=True)
async def ftr_start(ctx, seconds: int = 60):
    if not 10 <= seconds <= 600:
        return await send_error(ctx, "Choose 10–600 seconds.")

    if ctx.channel.id in active_ftr:
        return await send_error(ctx, "FTR is already running here.")

    message = await ctx.send(embed=vex_embed(
        "⚡ FIRST TO REACT",
        f"React with ⚡ first!\nTime limit: **{seconds} seconds**"
    ))
    await message.add_reaction("⚡")

    active_ftr[ctx.channel.id] = {
        "message_id": message.id,
        "winner": None
    }

    async def timeout_game():
        await asyncio.sleep(seconds)
        game = active_ftr.get(ctx.channel.id)
        if game and game["message_id"] == message.id:
            active_ftr.pop(ctx.channel.id, None)
            await ctx.send(embed=vex_embed(
                "⏰ FTR ENDED",
                "Time's up! No winner this round."
            ))

    asyncio.create_task(timeout_game())


@bot.listen("on_raw_reaction_add")
async def ftr_reaction(payload):
    if str(payload.emoji) != "⚡":
        return
    if payload.user_id == bot.user.id or payload.guild_id is None:
        return

    game = active_ftr.get(payload.channel_id)
    if not game or game["message_id"] != payload.message_id:
        return

    active_ftr.pop(payload.channel_id, None)
    last_ftr_winner[payload.guild_id] = payload.user_id

    await db_execute("""
        INSERT INTO ftr_scores (guild_id, user_id, wins)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET wins=wins+1
    """, (payload.guild_id, payload.user_id))

    channel = bot.get_channel(payload.channel_id)
    if channel:
        await channel.send(embed=vex_embed(
            "🏆 FTR WINNER",
            f"<@{payload.user_id}> reacted first!"
        ))


@ftr.command(name="stop")
@commands.has_guild_permissions(manage_guild=True)
async def ftr_stop(ctx):
    if ctx.channel.id not in active_ftr:
        return await send_error(ctx, "No FTR game running.")
    active_ftr.pop(ctx.channel.id, None)
    await send_success(ctx, "FTR stopped.")


@ftr.command(name="winner")
async def ftr_winner(ctx):
    winner = last_ftr_winner.get(ctx.guild.id)
    if not winner:
        return await send_info(ctx, "No winner recorded yet.")
    await ctx.send(embed=vex_embed("🏆 LAST FTR WINNER", f"<@{winner}>"))


@ftr.command(name="leaderboard")
async def ftr_leaderboard(ctx):
    rows = await db_fetchall("""
        SELECT user_id, wins FROM ftr_scores
        WHERE guild_id=? ORDER BY wins DESC LIMIT 10
    """, (ctx.guild.id,))

    if not rows:
        return await send_info(ctx, "No FTR wins yet.")

    description = "\n".join(
        f"**{i}.** <@{row[0]}> — **{row[1]} wins**"
        for i, row in enumerate(rows, 1)
    )
    await ctx.send(embed=vex_embed("⚡ FTR LEADERBOARD", description))


# ==========================================
# END PART 3B
# ==========================================

# ==========================================
# FINAL STARTUP
# KEEP THIS AT THE VERY BOTTOM
# ==========================================

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

bot.run(TOKEN)
