import discord
from discord.ext import commands
import os
import sqlite3
import random
import asyncio
import time
import datetime
import re

# ================= CONFIG =================

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
    case_insensitive=True,
    help_command=None
)

# ================= DATABASE =================

db = sqlite3.connect("vexora.db")
db.row_factory = sqlite3.Row

def setup_db():
    tables = [
        """CREATE TABLE IF NOT EXISTS premium
        (guild_id INTEGER PRIMARY KEY, expires INTEGER)""",

        """CREATE TABLE IF NOT EXISTS economy
        (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0,
        daily INTEGER DEFAULT 0, weekly INTEGER DEFAULT 0)""",

        """CREATE TABLE IF NOT EXISTS warnings
        (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
        user_id INTEGER, moderator INTEGER, reason TEXT, created INTEGER)""",

        """CREATE TABLE IF NOT EXISTS levels
        (guild_id INTEGER, user_id INTEGER, xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0, PRIMARY KEY(guild_id,user_id))""",

        """CREATE TABLE IF NOT EXISTS reputation
        (user_id INTEGER PRIMARY KEY, reps INTEGER DEFAULT 0)""",

        """CREATE TABLE IF NOT EXISTS custom_commands
        (guild_id INTEGER, name TEXT, response TEXT,
        PRIMARY KEY(guild_id,name))""",

        """CREATE TABLE IF NOT EXISTS settings
        (guild_id INTEGER, name TEXT, value TEXT,
        PRIMARY KEY(guild_id,name))""",

        """CREATE TABLE IF NOT EXISTS reaction_roles
        (message_id INTEGER, emoji TEXT, role_id INTEGER,
        PRIMARY KEY(message_id,emoji))"""
    ]

    for table in tables:
        db.execute(table)
    db.commit()

setup_db()

def sql(query, values=()):
    cur = db.execute(query, values)
    db.commit()
    return cur

def one(query, values=()):
    return db.execute(query, values).fetchone()

def many(query, values=()):
    return db.execute(query, values).fetchall()

# ================= EMBEDS =================

EMBED_COLOR = discord.Color.from_rgb(175, 175, 175)

def embed(title, description="", color=EMBED_COLOR):
    e = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    e.set_footer(text="VEXORA • One Bot. Endless Possibilities.")
    return e

def success(ctx, message):
    return ctx.send(embed=embed("✓ Success", message))

def error(ctx, message):
    return ctx.send(embed=embed("✕ Error", message))

def info(ctx, message):
    return ctx.send(embed=embed("VEXORA", message))

# ================= PERMISSIONS =================

def owner_only():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_premium(guild_id):
    row = one("SELECT expires FROM premium WHERE guild_id=?", (guild_id,))
    if not row:
        return False
    if row["expires"] and row["expires"] < int(time.time()):
        sql("DELETE FROM premium WHERE guild_id=?", (guild_id,))
        return False
    return True

def get_balance(user_id):
    row = one("SELECT balance FROM economy WHERE user_id=?", (user_id,))
    if not row:
        sql("INSERT INTO economy(user_id,balance) VALUES(?,0)", (user_id,))
        return 0
    return row["balance"]

# ================= GENERAL =================

@bot.command()
async def ping(ctx):
    await ctx.send(embed=embed(
        "🏓 Pong!",
        f"Latency: `{round(bot.latency * 1000)}ms`"
    ))

@bot.command()
async def botinfo(ctx):
    e = embed("VEXORA • Bot Information")
    e.add_field(name="Servers", value=len(bot.guilds))
    e.add_field(name="Users", value=len(bot.users))
    e.add_field(name="Latency", value=f"{round(bot.latency*1000)}ms")
    e.add_field(name="Prefix", value="`! ? . $ -`")
    await ctx.send(embed=e)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    e = embed(g.name)
    e.add_field(name="Members", value=g.member_count)
    e.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown")
    e.add_field(name="Created", value=discord.utils.format_dt(g.created_at, "D"))
    e.add_field(name="Channels", value=len(g.channels))
    e.add_field(name="Roles", value=len(g.roles))
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    await ctx.send(embed=e)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = embed(str(member))
    e.add_field(name="ID", value=member.id)
    e.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "D"))
    e.add_field(name="Created", value=discord.utils.format_dt(member.created_at, "D"))
    e.add_field(name="Top Role", value=member.top_role.mention)
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
    await ctx.send(embed=embed(
        "VEXORA Support",
        f"[Join the support server]({SUPPORT_SERVER})"
    ))

# ================= MODERATION =================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await error(ctx, "You cannot ban someone with an equal or higher role.")
    await member.ban(reason=reason)
    await success(ctx, f"Banned {member.mention}\nReason: {reason}")

@bot.command(name="kick", aliases=["modkick"])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await error(ctx, "You cannot kick someone with an equal or higher role.")
    await member.kick(reason=reason)
    await success(ctx, f"Kicked {member.mention}\nReason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await success(ctx, f"Unbanned **{user}**.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    if minutes < 1 or minutes > 40320:
        return await error(ctx, "Choose a timeout between 1 minute and 28 days.")
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await success(ctx, f"Timed out {member.mention} for `{minutes}` minutes.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await success(ctx, f"Removed timeout from {member.mention}.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        return await error(ctx, "Choose a number from 1 to 100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=embed("Purged", f"Deleted `{len(deleted)-1}` messages."))
    await asyncio.sleep(4)
    await msg.delete()

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await success(ctx, "Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await success(ctx, "Channel unlocked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if not 0 <= seconds <= 21600:
        return await error(ctx, "Slowmode must be between 0 and 21600 seconds.")
    await ctx.channel.edit(slowmode_delay=seconds)
    await success(ctx, f"Slowmode set to `{seconds}` seconds.")

# ================= WARNINGS =================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    sql(
        "INSERT INTO warnings(guild_id,user_id,moderator,reason,created) VALUES(?,?,?,?,?)",
        (ctx.guild.id, member.id, ctx.author.id, reason, int(time.time()))
    )
    await success(ctx, f"{member.mention} has been warned.\nReason: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    rows = many(
        "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC",
        (ctx.guild.id, member.id)
    )
    if not rows:
        return await info(ctx, "No warnings found.")
    e = embed(f"Warnings • {member}")
    for r in rows[:10]:
        e.add_field(
            name=f"Warning #{r['id']}",
            value=f"{r['reason']}\nModerator ID: `{r['moderator']}`",
            inline=False
        )
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    sql("DELETE FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id))
    await success(ctx, f"Cleared warnings for {member.mention}.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def staff(ctx):
    members = [m.mention for m in ctx.guild.members if m.guild_permissions.manage_messages]
    await ctx.send(embed=embed("Server Staff", "\n".join(members[:50]) or "No staff found."))

# ================= PREMIUM MANAGEMENT =================

@bot.group(invoke_without_command=True)
@owner_only()
async def premium(ctx):
    await info(ctx, "Use `!premium add`, `!premium remove`, `!premium check`, or `!premium list`.")

@premium.command(name="add")
@owner_only()
async def premium_add(ctx, guild_id: int, days: int = 30):
    expires = int(time.time()) + days * 86400
    sql("INSERT OR REPLACE INTO premium(guild_id,expires) VALUES(?,?)",
        (guild_id, expires))
    await success(ctx, f"Premium enabled for `{guild_id}` for `{days}` days.")

@premium.command(name="remove")
@owner_only()
async def premium_remove(ctx, guild_id: int):
    sql("DELETE FROM premium WHERE guild_id=?", (guild_id,))
    await success(ctx, f"Premium removed from `{guild_id}`.")

@premium.command(name="check")
@owner_only()
async def premium_check(ctx, guild_id: int):
    await info(ctx, f"Premium status: **{'Active' if is_premium(guild_id) else 'Inactive'}**")

@premium.command(name="list")
@owner_only()
async def premium_list(ctx):
    rows = many("SELECT * FROM premium")
    text = "\n".join(f"`{r['guild_id']}` — <t:{r['expires']}:R>" for r in rows)
    await ctx.send(embed=embed("Premium Servers", text or "No premium servers."))

# ================= ECONOMY =================

@bot.command(aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    amount = get_balance(member.id)
    await ctx.send(embed=embed("Wallet", f"{member.mention} has **{amount} coins**."))

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    reward = random.randint(100, 300)
    get_balance(ctx.author.id)
    sql("UPDATE economy SET balance=balance+?,daily=? WHERE user_id=?",
        (reward, int(time.time()), ctx.author.id))
    await success(ctx, f"You collected **{reward} coins**.")

@bot.command()
@commands.cooldown(1, 604800, commands.BucketType.user)
async def weekly(ctx):
    reward = random.randint(500, 1000)
    get_balance(ctx.author.id)
    sql("UPDATE economy SET balance=balance+?,weekly=? WHERE user_id=?",
        (reward, int(time.time()), ctx.author.id))
    await success(ctx, f"You collected **{reward} coins**.")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    reward = random.randint(50, 150)
    get_balance(ctx.author.id)
    sql("UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id))
    await success(ctx, f"You worked and earned **{reward} coins**.")

@bot.command()
@commands.cooldown(1, 1800, commands.BucketType.user)
async def beg(ctx):
    reward = random.randint(0, 50)
    get_balance(ctx.author.id)
    sql("UPDATE economy SET balance=balance+? WHERE user_id=?",
        (reward, ctx.author.id))
    await info(ctx, f"You received **{reward} coins**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot or member == ctx.author:
        return await error(ctx, "Choose another human member.")
    if amount <= 0:
        return await error(ctx, "Amount must be positive.")
    if get_balance(ctx.author.id) < amount:
        return await error(ctx, "You don't have enough coins.")
    get_balance(member.id)
    sql("UPDATE economy SET balance=balance-? WHERE user_id=?",
        (amount, ctx.author.id))
    sql("UPDATE economy SET balance=balance+? WHERE user_id=?",
        (amount, member.id))
    await success(ctx, f"Sent **{amount} coins** to {member.mention}.")

@bot.command(name="leaderboard")
async def economy_leaderboard(ctx):
    rows = many("SELECT user_id,balance FROM economy ORDER BY balance DESC LIMIT 10")
    lines = []
    for i, r in enumerate(rows, 1):
        lines.append(f"`{i}.` <@{r['user_id']}> — **{r['balance']} coins**")
    await ctx.send(embed=embed("Economy Leaderboard", "\n".join(lines) or "No data."))

# ================= GAMES =================

@bot.command()
async def dice(ctx):
    await info(ctx, f"🎲 You rolled **{random.randint(1,6)}**.")

@bot.command()
async def flip(ctx):
    await info(ctx, random.choice(["🪙 Heads!", "🪙 Tails!"]))

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    options = ["rock", "paper", "scissors"]
    if choice not in options:
        return await error(ctx, "Choose rock, paper, or scissors.")
    bot_choice = random.choice(options)
    if choice == bot_choice:
        result = "It's a tie!"
    elif (choice, bot_choice) in [
        ("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")
    ]:
        result = "You win!"
    else:
        result = "I win!"
    await info(ctx, f"You: **{choice}**\nMe: **{bot_choice}**\n\n{result}")

@bot.command()
async def guess(ctx, number: int):
    target = random.randint(1, 10)
    if number == target:
        await success(ctx, "Correct! You guessed it.")
    else:
        await info(ctx, f"Not quite! The number was `{target}`.")

@bot.command()
async def trivia(ctx):
    questions = [
        ("What is the capital of Japan?", "tokyo"),
        ("Which planet is known as the Red Planet?", "mars"),
        ("How many sides does a hexagon have?", "6"),
        ("What is the largest ocean?", "pacific"),
    ]
    question, answer = random.choice(questions)
    await ctx.send(embed=embed("Trivia", question))

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", timeout=20, check=check)
        if msg.content.lower().strip() == answer:
            await success(ctx, "Correct answer!")
        else:
            await info(ctx, f"The answer was **{answer}**.")
    except asyncio.TimeoutError:
        await info(ctx, f"Time's up! The answer was **{answer}**.")

# ================= REPUTATION =================

@bot.command()
async def rep(ctx, member: discord.Member):
    if member == ctx.author or member.bot:
        return await error(ctx, "You cannot give reputation to yourself or a bot.")
    row = one("SELECT reps FROM reputation WHERE user_id=?", (member.id,))
    if not row:
        sql("INSERT INTO reputation(user_id,reps) VALUES(?,1)", (member.id,))
    else:
        sql("UPDATE reputation SET reps=reps+1 WHERE user_id=?", (member.id,))
    await success(ctx, f"You gave a reputation point to {member.mention}.")

@bot.command()
async def reps(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = one("SELECT reps FROM reputation WHERE user_id=?", (member.id,))
    amount = row["reps"] if row else 0
    await info(ctx, f"{member.mention} has **{amount} reputation points**.")

@bot.command()
async def repboard(ctx):
    rows = many("SELECT user_id,reps FROM reputation ORDER BY reps DESC LIMIT 10")
    lines = [f"`{i}.` <@{r['user_id']}> — **{r['reps']}**" for i, r in enumerate(rows, 1)]
    await ctx.send(embed=embed("Reputation Leaderboard", "\n".join(lines) or "No data."))

# ================= LEVELS =================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild:
        row = one(
            "SELECT xp,level FROM levels WHERE guild_id=? AND user_id=?",
            (message.guild.id, message.author.id)
        )
        gained = random.randint(5, 15)
        if not row:
            sql("INSERT INTO levels(guild_id,user_id,xp,level) VALUES(?,?,?,0)",
                (message.guild.id, message.author.id, gained))
        else:
            xp = row["xp"] + gained
            level = row["level"]
            needed = (level + 1) * 100
            while xp >= needed:
                xp -= needed
                level += 1
                needed = (level + 1) * 100
                try:
                    await message.channel.send(
                        embed=embed("Level Up!", f"{message.author.mention} reached level **{level}**!")
                    )
                except discord.HTTPException:
                    pass
            sql("UPDATE levels SET xp=?,level=? WHERE guild_id=? AND user_id=?",
                (xp, level, message.guild.id, message.author.id))
    await bot.process_commands(message)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = one("SELECT xp,level FROM levels WHERE guild_id=? AND user_id=?",
              (ctx.guild.id, member.id))
    if not row:
        return await info(ctx, "No level data yet.")
    needed = (row["level"] + 1) * 100
    await ctx.send(embed=embed(
        f"{member.display_name}'s Rank",
        f"Level: **{row['level']}**\nXP: **{row['xp']}/{needed}**"
    ))

@bot.command()
async def level(ctx, member: discord.Member = None):
    await rank(ctx, member)

@bot.command()
async def levels(ctx):
    rows = many(
        "SELECT user_id,level,xp FROM levels WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10",
        (ctx.guild.id,)
    )
    lines = [
        f"`{i}.` <@{r['user_id']}> — Level **{r['level']}** ({r['xp']} XP)"
        for i, r in enumerate(rows, 1)
    ]
    await ctx.send(embed=embed("Server Level Leaderboard", "\n".join(lines) or "No data."))
    # ================= EXTRA DATABASE TABLES =================

extra_tables = [
    """CREATE TABLE IF NOT EXISTS giveaways
    (message_id INTEGER PRIMARY KEY, guild_id INTEGER, channel_id INTEGER,
    prize TEXT, end_time INTEGER, ended INTEGER DEFAULT 0)""",

    """CREATE TABLE IF NOT EXISTS tickets
    (channel_id INTEGER PRIMARY KEY, guild_id INTEGER, user_id INTEGER,
    claimed_by INTEGER DEFAULT 0)""",

    """CREATE TABLE IF NOT EXISTS invite_counts
    (guild_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
    PRIMARY KEY(guild_id,user_id))""",

    """CREATE TABLE IF NOT EXISTS invite_tracking
    (guild_id INTEGER, member_id INTEGER, inviter_id INTEGER,
    PRIMARY KEY(guild_id,member_id))"""
]

for table in extra_tables:
    db.execute(table)
db.commit()

# ================= SETTINGS =================

def set_setting(guild_id, name, value):
    sql(
        "INSERT OR REPLACE INTO settings(guild_id,name,value) VALUES(?,?,?)",
        (guild_id, name, str(value))
    )

def get_setting(guild_id, name):
    row = one(
        "SELECT value FROM settings WHERE guild_id=? AND name=?",
        (guild_id, name)
    )
    return row["value"] if row else None

# ================= AFK =================

afk_users = {}

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await success(ctx, f"AFK enabled: **{reason}**")

@bot.listen("on_message")
async def afk_listener(message):
    if message.author.bot:
        return

    if message.author.id in afk_users:
        afk_users.pop(message.author.id, None)
        try:
            await message.channel.send(
                embed=embed("Welcome Back", f"{message.author.mention}, your AFK status was removed.")
            )
        except discord.HTTPException:
            pass

    for member in message.mentions:
        if member.id in afk_users:
            try:
                await message.channel.send(
                    embed=embed("AFK", f"{member.mention} is AFK: **{afk_users[member.id]}**")
                )
            except discord.HTTPException:
                pass

# ================= CONFESSIONS =================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confesssetup(ctx, channel: discord.TextChannel):
    set_setting(ctx.guild.id, "confessions", channel.id)
    await success(ctx, f"Confessions channel set to {channel.mention}.")

@bot.command()
async def confess(ctx, *, message):
    channel_id = get_setting(ctx.guild.id, "confessions")
    if not channel_id:
        return await error(ctx, "Confessions have not been configured.")
    channel = ctx.guild.get_channel(int(channel_id))
    if not channel:
        return await error(ctx, "The confession channel no longer exists.")

    e = embed("Anonymous Confession", message)
    e.add_field(name="Submitted", value="Anonymous")
    await channel.send(embed=e)
    await success(ctx, "Your confession was submitted.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def confessionsoff(ctx):
    set_setting(ctx.guild.id, "confessions", "")
    await success(ctx, "Confessions disabled.")

# ================= SUGGESTIONS =================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def suggestsetup(ctx, channel: discord.TextChannel):
    set_setting(ctx.guild.id, "suggestions", channel.id)
    await success(ctx, f"Suggestions channel set to {channel.mention}.")

@bot.command()
async def suggest(ctx, *, suggestion):
    channel_id = get_setting(ctx.guild.id, "suggestions")
    if not channel_id:
        return await error(ctx, "Suggestions have not been configured.")
    channel = ctx.guild.get_channel(int(channel_id))
    if not channel:
        return await error(ctx, "The suggestions channel no longer exists.")

    e = embed("New Suggestion", suggestion)
    e.add_field(name="Submitted by", value=ctx.author.mention)
    msg = await channel.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await success(ctx, "Suggestion submitted.")

# ================= POLLS =================

@bot.command()
async def poll(ctx, *, question):
    e = embed("📊 Poll", question)
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

# ================= ANIME FUN =================

ANIME_GIFS = {
    "kiss": [
        "https://media.tenor.com/4J7b7qz5v0AAAAAC/anime-kiss.gif",
        "https://media.tenor.com/0nZ6q0p4Z2AAAAAC/anime-kiss.gif"
    ],
    "punch": [
        "https://media.tenor.com/7l9Y2q2Z0JAAAAAC/anime-punch.gif"
    ],
    "kick": [
        "https://media.tenor.com/2e3Q6Qx4vWAAAAAC/anime-kick.gif"
    ]
}

async def anime_action(ctx, action, member):
    if member.bot:
        return await error(ctx, "Choose a human member.")
    gif = random.choice(ANIME_GIFS[action])
    e = embed(f"Anime {action.title()}", f"{ctx.author.mention} {action}s {member.mention}!")
    e.set_image(url=gif)
    await ctx.send(embed=e)

@bot.command()
async def kiss(ctx, member: discord.Member):
    await anime_action(ctx, "kiss", member)

@bot.command()
async def punch(ctx, member: discord.Member):
    await anime_action(ctx, "punch", member)

@bot.command()
async def kick(ctx, member: discord.Member):
    await anime_action(ctx, "kick", member)

# ================= CUSTOM COMMANDS: PREMIUM =================

@bot.group(name="cc", invoke_without_command=True)
async def cc(ctx):
    await info(ctx, "Premium custom commands:\n`!cc add <name> <response>`\n`!cc edit <name> <response>`\n`!cc remove <name>`\n`!cc list`\n`!cc info <name>`")

def valid_cc_name(name):
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", name))

@cc.command(name="add")
@commands.has_permissions(manage_guild=True)
async def cc_add(ctx, name: str, *, response: str):
    if not is_premium(ctx.guild.id):
        return await error(ctx, "This server needs Premium.")
    if not valid_cc_name(name):
        return await error(ctx, "Use a command name with letters, numbers, _ or - (max 32 characters).")
    if one("SELECT name FROM custom_commands WHERE guild_id=? AND name=?",
           (ctx.guild.id, name.lower())):
        return await error(ctx, "That custom command already exists.")
    sql("INSERT INTO custom_commands(guild_id,name,response) VALUES(?,?,?)",
        (ctx.guild.id, name.lower(), response))
    await success(ctx, f"Custom command `!{name.lower()}` created.")

@cc.command(name="edit")
@commands.has_permissions(manage_guild=True)
async def cc_edit(ctx, name: str, *, response: str):
    if not is_premium(ctx.guild.id):
        return await error(ctx, "This server needs Premium.")
    row = one("SELECT name FROM custom_commands WHERE guild_id=? AND name=?",
              (ctx.guild.id, name.lower()))
    if not row:
        return await error(ctx, "Custom command not found.")
    sql("UPDATE custom_commands SET response=? WHERE guild_id=? AND name=?",
        (response, ctx.guild.id, name.lower()))
    await success(ctx, f"Updated `!{name.lower()}`.")

@cc.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def cc_remove(ctx, name: str):
    if not is_premium(ctx.guild.id):
        return await error(ctx, "This server needs Premium.")
    sql("DELETE FROM custom_commands WHERE guild_id=? AND name=?",
        (ctx.guild.id, name.lower()))
    await success(ctx, f"Removed `!{name.lower()}`.")

@cc.command(name="list")
async def cc_list(ctx):
    rows = many("SELECT name FROM custom_commands WHERE guild_id=?",
                (ctx.guild.id,))
    names = [f"`{r['name']}`" for r in rows]
    await ctx.send(embed=embed("Custom Commands", "\n".join(names) or "No custom commands."))

@cc.command(name="info")
async def cc_info(ctx, name: str):
    row = one("SELECT response FROM custom_commands WHERE guild_id=? AND name=?",
              (ctx.guild.id, name.lower()))
    if not row:
        return await error(ctx, "Custom command not found.")
    await ctx.send(embed=embed(f"Custom Command: {name}", row["response"][:4000]))

@bot.listen("on_message")
async def custom_command_listener(message):
    if message.author.bot or not message.guild:
        return
    if not is_premium(message.guild.id):
        return

    prefixes = ("!", "?", ".", "$", "-")
    content = message.content.strip()

    if not content.startswith(prefixes):
        return

    parts = content[1:].split(maxsplit=1)
    if not parts:
        return

    name = parts[0].lower()

    # Avoid overriding actual bot commands.
    if bot.get_command(name):
        return

    row = one(
        "SELECT response FROM custom_commands WHERE guild_id=? AND name=?",
        (message.guild.id, name)
    )
    if row:
        await message.channel.send(
            row["response"].replace("{user}", message.author.mention)
            .replace("{server}", message.guild.name)[:2000]
        )

# ================= INVITES =================

invite_cache = {}

@bot.event
async def on_ready():
    print(f"VEXORA online as {bot.user}")
    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except discord.Forbidden:
            invite_cache[guild.id] = []

    await restore_giveaways()

@bot.listen("on_invite_create")
async def invite_created(invite):
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except discord.Forbidden:
        pass

@bot.listen("on_invite_delete")
async def invite_deleted(invite):
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except discord.Forbidden:
        pass

@bot.listen("on_member_join")
async def invite_join(member):
    guild = member.guild
    try:
        current = await guild.invites()
        old = invite_cache.get(guild.id, [])
        used = None

        for invite in current:
            previous = next((x for x in old if x.code == invite.code), None)
            if previous and invite.uses > previous.uses:
                used = invite
                break

        invite_cache[guild.id] = current

        if used and used.inviter:
            inviter = used.inviter
            sql(
                """INSERT INTO invite_counts(guild_id,user_id,count)
                VALUES(?,?,1)
                ON CONFLICT(guild_id,user_id)
                DO UPDATE SET count=count+1""",
                (guild.id, inviter.id)
            )
            sql(
                "INSERT OR REPLACE INTO invite_tracking(guild_id,member_id,inviter_id) VALUES(?,?,?)",
                (guild.id, member.id, inviter.id)
            )
    except discord.Forbidden:
        pass

@bot.command(name="invites", aliases=["i", "lb"])
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = one("SELECT count FROM invite_counts WHERE guild_id=? AND user_id=?",
              (ctx.guild.id, member.id))
    count = row["count"] if row else 0
    await info(ctx, f"{member.mention} has **{count} tracked invites**.")

@bot.command()
async def inviter(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = one("SELECT inviter_id FROM invite_tracking WHERE guild_id=? AND member_id=?",
              (ctx.guild.id, member.id))
    if not row:
        return await info(ctx, "No inviter was recorded.")
    await info(ctx, f"{member.mention} was invited by <@{row['inviter_id']}>.")

@bot.command()
async def inviteinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    row = one("SELECT count FROM invite_counts WHERE guild_id=? AND user_id=?",
              (ctx.guild.id, member.id))
    count = row["count"] if row else 0
    await info(ctx, f"Invite information for {member.mention}\nTracked invites: **{count}**")

@bot.command()
async def topinvites(ctx):
    rows = many(
        "SELECT user_id,count FROM invite_counts WHERE guild_id=? ORDER BY count DESC LIMIT 10",
        (ctx.guild.id,)
    )
    lines = [f"`{i}.` <@{r['user_id']}> — **{r['count']}**" for i, r in enumerate(rows, 1)]
    await ctx.send(embed=embed("Invite Leaderboard", "\n".join(lines) or "No invite data."))

# ================= REACTION ROLES =================

@bot.group(name="rr", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def rr(ctx):
    await info(ctx, "`!rr add <message_id> <emoji> <role>`\n`!rr remove <message_id> <emoji>`\n`!rr list`")

@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(ctx, message_id: int, emoji: str, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await error(ctx, "My role must be higher than that role.")
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.add_reaction(emoji)
    except (discord.NotFound, discord.HTTPException):
        return await error(ctx, "I couldn't access that message or reaction.")
    sql("INSERT OR REPLACE INTO reaction_roles(message_id,emoji,role_id) VALUES(?,?,?)",
        (message_id, emoji, role.id))
    await success(ctx, "Reaction role added.")

@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, *, emoji: str):
    sql("DELETE FROM reaction_roles WHERE message_id=? AND emoji=?",
        (message_id, emoji))
    await success(ctx, "Reaction role removed.")

@rr.command(name="list")
async def rr_list(ctx):
    rows = many(
        """SELECT reaction_roles.message_id,reaction_roles.emoji,reaction_roles.role_id
        FROM reaction_roles"""
    )
    lines = [
        f"Message `{r['message_id']}` • {r['emoji']} • <@&{r['role_id']}>"
        for r in rows
    ]
    await ctx.send(embed=embed("Reaction Roles", "\n".join(lines) or "None configured."))

@bot.listen("on_raw_reaction_add")
async def reaction_role_add(payload):
    if payload.guild_id is None or payload.member is None or payload.member.bot:
        return
    row = one("SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
              (payload.message_id, str(payload.emoji)))
    if not row:
        return
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(row["role_id"]) if guild else None
    if role:
        try:
            await payload.member.add_roles(role, reason="Reaction role")
        except discord.HTTPException:
            pass

@bot.listen("on_raw_reaction_remove")
async def reaction_role_remove(payload):
    if payload.guild_id is None:
        return
    row = one("SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
              (payload.message_id, str(payload.emoji)))
    if not row:
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    role = guild.get_role(row["role_id"]) if guild else None
    if member and role:
        try:
            await member.remove_roles(role, reason="Reaction role removed")
        except discord.HTTPException:
            pass

# ================= TICKETS =================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def ticketsetup(ctx, category: discord.CategoryChannel):
    set_setting(ctx.guild.id, "ticket_category", category.id)
    await success(ctx, f"Ticket category set to **{category.name}**.")

@bot.command()
async def ticket(ctx):
    category_id = get_setting(ctx.guild.id, "ticket_category")
    if not category_id:
        return await error(ctx, "Tickets have not been configured.")
    category = ctx.guild.get_channel(int(category_id))
    if not category:
        return await error(ctx, "Ticket category no longer exists.")

    existing = one("SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=?",
                   (ctx.guild.id, ctx.author.id))
    if existing and ctx.guild.get_channel(existing["channel_id"]):
        return await error(ctx, "You already have an open ticket.")

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    channel = await ctx.guild.create_text_channel(
        f"ticket-{ctx.author.name}".lower()[:90],
        category=category,
        overwrites=overwrites
    )
    sql("INSERT OR REPLACE INTO tickets(channel_id,guild_id,user_id,claimed_by) VALUES(?,?,?,0)",
        (channel.id, ctx.guild.id, ctx.author.id))
    await channel.send(embed=embed("Support Ticket", f"{ctx.author.mention}, explain your issue here."))
    await success(ctx, f"Ticket created: {channel.mention}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def claim(ctx):
    row = one("SELECT * FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    if not row:
        return await error(ctx, "This is not a ticket channel.")
    sql("UPDATE tickets SET claimed_by=? WHERE channel_id=?",
        (ctx.author.id, ctx.channel.id))
    await success(ctx, f"Ticket claimed by {ctx.author.mention}.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    row = one("SELECT * FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    if not row:
        return await error(ctx, "This is not a ticket channel.")
    await success(ctx, "Ticket closing in 3 seconds.")
    await asyncio.sleep(3)
    sql("DELETE FROM tickets WHERE channel_id=?", (ctx.channel.id,))
    await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")

# ================= SNIPE =================

snipes = {}

@bot.listen("on_message_delete")
async def snipe_listener(message):
    if message.guild and not message.author.bot and message.content:
        snipes[message.channel.id] = {
            "author": str(message.author),
            "content": message.content[:1500]
        }

@bot.command(name="s", aliases=["snipe"])
async def snipe(ctx):
    data = snipes.get(ctx.channel.id)
    if not data:
        return await info(ctx, "Nothing to snipe.")
    await ctx.send(embed=embed(f"Deleted by {data['author']}", data["content"]))

@bot.command(name="cs", aliases=["clearsnipe"])
async def clearsnipe(ctx):
    snipes.pop(ctx.channel.id, None)
    await success(ctx, "Snipe cleared.")

# ================= GIVEAWAYS =================

giveaway_tasks = {}

async def finish_giveaway(message_id):
    row = one("SELECT * FROM giveaways WHERE message_id=? AND ended=0",
              (message_id,))
    if not row:
        return

    channel = bot.get_channel(row["channel_id"])
    if not channel:
        return

    try:
        msg = await channel.fetch_message(message_id)
        users = []
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)

        if users:
            winner = random.choice(users)
            await channel.send(embed=embed(
                "🎉 Giveaway Winner!",
                f"Prize: **{row['prize']}**\nWinner: {winner.mention}"
            ))
        else:
            await channel.send(embed=embed("Giveaway Ended", "No valid entries."))
    except discord.HTTPException:
        pass

    sql("UPDATE giveaways SET ended=1 WHERE message_id=?", (message_id,))
    giveaway_tasks.pop(message_id, None)

async def giveaway_timer(message_id, end_time):
    await asyncio.sleep(max(0, end_time - int(time.time())))
    await finish_giveaway(message_id)

async def restore_giveaways():
    for row in many("SELECT message_id,end_time FROM giveaways WHERE ended=0"):
        if row["message_id"] not in giveaway_tasks:
            giveaway_tasks[row["message_id"]] = asyncio.create_task(
                giveaway_timer(row["message_id"], row["end_time"])
            )

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, seconds: int, *, prize):
    if seconds < 10 or seconds > 2592000:
        return await error(ctx, "Duration must be between 10 seconds and 30 days.")
    end_time = int(time.time()) + seconds
    msg = await ctx.send(embed=embed(
        "🎉 Giveaway!",
        f"Prize: **{prize}**\nReact with 🎉 to enter!\nEnds <t:{end_time}:R>"
    ))
    await msg.add_reaction("🎉")
    sql("INSERT INTO giveaways(message_id,guild_id,channel_id,prize,end_time,ended) VALUES(?,?,?,?,?,0)",
        (msg.id, ctx.guild.id, ctx.channel.id, prize, end_time))
    giveaway_tasks[msg.id] = asyncio.create_task(giveaway_timer(msg.id, end_time))
    await success(ctx, "Giveaway started.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    await finish_giveaway(message_id)
    await success(ctx, "Giveaway ended if it was active.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gcancel(ctx, message_id: int):
    task = giveaway_tasks.pop(message_id, None)
    if task:
        task.cancel()
    sql("UPDATE giveaways SET ended=1 WHERE message_id=? AND guild_id=?",
        (message_id, ctx.guild.id))
    await success(ctx, "Giveaway cancelled.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    row = one("SELECT * FROM giveaways WHERE message_id=? AND guild_id=?",
              (message_id, ctx.guild.id))
    if not row:
        return await error(ctx, "Giveaway not found.")
    channel = bot.get_channel(row["channel_id"])
    try:
        msg = await channel.fetch_message(message_id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
        if not users:
            return await error(ctx, "No valid entrants.")
        await ctx.send(embed=embed("🎉 New Winner", random.choice(users).mention))
    except discord.HTTPException:
        await error(ctx, "Couldn't access that giveaway.")

# ================= FTR =================

ftr_games = {}

@bot.group(invoke_without_command=True)
async def ftr(ctx):
    await info(ctx, "`!ftr start <seconds>`\n`!ftr stop`\n`!ftr winner`\n`!ftr leaderboard`")

@ftr.command(name="start")
@commands.has_permissions(manage_guild=True)
async def ftr_start(ctx, seconds: int = 30):
    if seconds < 5 or seconds > 300:
        return await error(ctx, "Choose 5 to 300 seconds.")
    if ctx.channel.id in ftr_games:
        return await error(ctx, "A game is already running here.")
    end = int(time.time()) + seconds
    msg = await ctx.send(embed=embed(
        "⚡ First To React",
        f"React with ⚡ first!\nEnds <t:{end}:R>"
    ))
    await msg.add_reaction("⚡")
    ftr_games[ctx.channel.id] = {
        "message": msg.id,
        "winner": None,
        "task": None
    }

    async def finish():
        await asyncio.sleep(seconds)
        game = ftr_games.get(ctx.channel.id)
        if not game:
            return
        winner = game["winner"]
        if winner:
            await ctx.send(embed=embed("FTR Winner", winner.mention))
        else:
            await ctx.send(embed=embed("FTR Ended", "Nobody reacted first."))
        ftr_games.pop(ctx.channel.id, None)

    ftr_games[ctx.channel.id]["task"] = asyncio.create_task(finish())

@ftr.command(name="stop")
@commands.has_permissions(manage_guild=True)
async def ftr_stop(ctx):
    game = ftr_games.pop(ctx.channel.id, None)
    if not game:
        return await error(ctx, "No active game.")
    game["task"].cancel()
    await success(ctx, "FTR stopped.")

@ftr.command(name="winner")
async def ftr_winner(ctx):
    game = ftr_games.get(ctx.channel.id)
    if not game:
        return await error(ctx, "No active game.")
    await info(ctx, f"Winner: {game['winner'].mention if game['winner'] else 'Not decided yet.'}")

@ftr.command(name="leaderboard")
async def ftr_leaderboard(ctx):
    await info(ctx, "FTR leaderboard is not available yet.")

@bot.listen("on_raw_reaction_add")
async def ftr_reaction(payload):
    if str(payload.emoji) != "⚡" or payload.user_id == bot.user.id:
        return
    game = ftr_games.get(payload.channel_id)
    if not game or game["message"] != payload.message_id:
        return
    if game["winner"] is None:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id) if guild else None
        if member and not member.bot:
            game["winner"] = member

# ================= BOT STATUS =================

@bot.command()
@owner_only()
async def playing(ctx, *, text):
    await bot.change_presence(
        activity=discord.Game(name=text),
        status=discord.Status.online
    )
    await success(ctx, f"Playing status set to **{text}**.")

@bot.command()
@owner_only()
async def stext(ctx, *, text):
    await bot.change_presence(
        activity=discord.CustomActivity(name=text),
        status=discord.Status.online
    )
    await success(ctx, f"Custom status set to **{text}**.")

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
        return await error(ctx, "Choose online, offline, dnd, or sleep.")
    await bot.change_presence(status=modes[mode])
    await success(ctx, f"Status changed to **{mode}**.")

# ================= GLOBAL ANNOUNCEMENTS =================

announcement_pending = {}

@bot.command()
@owner_only()
async def announce(ctx, *, message):
    announcement_pending[ctx.author.id] = message
    await ctx.send(embed=embed(
        "Confirm Global Announcement",
        f"{message}\n\nType `!announceconfirm` to send or `!announcecancel` to cancel."
    ))

@bot.command()
@owner_only()
async def announceconfirm(ctx):
    message = announcement_pending.pop(ctx.author.id, None)
    if not message:
        return await error(ctx, "No pending announcement.")
    sent = 0
    for guild in bot.guilds:
        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            channel = next(
                (c for c in guild.text_channels
                 if c.permissions_for(guild.me).send_messages),
                None
            )
        if channel:
            try:
                await channel.send(embed=embed("VEXORA Announcement", message))
                sent += 1
            except discord.HTTPException:
                pass
    await success(ctx, f"Announcement sent to `{sent}` servers.")

@bot.command()
@owner_only()
async def announcecancel(ctx):
    announcement_pending.pop(ctx.author.id, None)
    await success(ctx, "Announcement cancelled.")

# ================= HELP =================

CATEGORY_MAP = {
    "General": ["ping", "botinfo", "serverinfo", "userinfo", "avatar", "support"],
    "Moderation": ["ban", "kick", "unban", "timeout", "untimeout", "purge", "lock", "unlock", "slowmode"],
    "Warnings": ["warn", "warnings", "clearwarns", "staff"],
    "Economy": ["balance", "daily", "weekly", "work", "beg", "pay", "leaderboard"],
    "Games": ["dice", "flip", "rps", "guess", "trivia"],
    "Reputation": ["rep", "reps", "repboard"],
    "Levels": ["rank", "level", "levels"],
    "Invites": ["invites", "inviter", "inviteinfo", "topinvites"],
    "Community": ["afk", "confesssetup", "confess", "confessionsoff", "suggestsetup", "suggest", "poll"],
    "Fun": ["kiss", "punch", "kick"],
    "Tickets": ["ticketsetup", "ticket", "claim", "close"],
    "Giveaways": ["gstart", "gend", "gcancel", "greroll"],
    "FTR": ["ftr"],
    "Premium": ["premium", "cc"],
    "Owner": ["playing", "stext", "status", "announce", "announceconfirm", "announcecancel"]
}

@bot.command(name="help", aliases=["commands"])
async def help_command(ctx, *, category=None):
    if category:
        key = next((k for k in CATEGORY_MAP if k.lower() == category.lower()), None)
        if not key:
            return await error(ctx, "Category not found.")
        names = CATEGORY_MAP[key]
        lines = []
        for name in names:
            command = bot.get_command(name)
            if command:
                lines.append(f"`{name}` — {command.short_doc or 'VEXORA command'}")
        return await ctx.send(embed=embed(key, "\n".join(lines) or "No commands."))

    e = embed("VEXORA Commands", "Prefixes: `!` `?` `.` `$` `-`\nUse `!help <category>` for details.")
    for category, names in CATEGORY_MAP.items():
        available = [n for n in names if bot.get_command(n)]
        e.add_field(name=category, value=", ".join(f"`{n}`" for n in available) or "None", inline=False)
    await ctx.send(embed=e)

# ================= ERROR HANDLING =================

@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandNotFound):
        return
    if isinstance(err, commands.MissingRequiredArgument):
        return await error(ctx, f"Missing argument: `{err.param.name}`.")
    if isinstance(err, commands.BadArgument):
        return await error(ctx, "Invalid argument. Check the command format.")
    if isinstance(err, commands.MissingPermissions):
        return await error(ctx, "You don't have permission to use this command.")
    if isinstance(err, commands.BotMissingPermissions):
        return await error(ctx, "I don't have the required permissions.")
    if isinstance(err, commands.CommandOnCooldown):
        return await error(ctx, f"Try again in `{round(err.retry_after)}` seconds.")
    if isinstance(err, commands.CheckFailure):
        return await error(ctx, "You are not allowed to use this command.")
    if isinstance(err, discord.Forbidden):
        return await error(ctx, "Discord denied that action. Check my permissions and role position.")
    if isinstance(err, discord.NotFound):
        return await error(ctx, "That Discord item could not be found.")
    print(f"Command error in {ctx.command}: {repr(err)}")
    await error(ctx, "Something went wrong. Check Railway logs for the full error.")

# ================= START =================

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from Railway Variables.")

bot.run(TOKEN)
