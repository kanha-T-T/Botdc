
import discord
from discord.ext import commands
import os
import asyncio
import aiosqlite
from datetime import timedelta

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1495419933943922920

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.reactions = True

bot = commands.Bot(
    command_prefix=["!", "?", ".", "$"],
    intents=intents,
    help_command=None
)

DB = "bot.db"

async def setup_database():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium (
                guild_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                reason TEXT
            )
        """)
        await db.commit()

@bot.event
async def on_ready():
    await setup_database()
    print(f"Logged in as {bot.user}")
    print("Discord bot is online!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(
        title="Bot Information",
        description=f"Bot: {bot.user.mention}\nServers: {len(bot.guilds)}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def premium(ctx):
    await ctx.send(
        "💎 **PREMIUM**\n\n"
        "✨ **PREMIUM FEATURES**\n"
        "• Staff Management System\n"
        "• Custom Bot Profile\n"
        "• Custom Profile Images\n\n"
        "🛒 **WANT PREMIUM?**\n"
        "Join our support server:\n"
        "https://discord.gg/ZBaRByVFBC\n\n"
        "Invite expired? DM @n0pw"
    )

@bot.command()
@commands.is_owner()
async def premiumadd(ctx, server_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO premium VALUES (?)",
            (server_id,)
        )
        await db.commit()
    await ctx.send("✅ Premium activated!")

@bot.command()
@commands.is_owner()
async def premiumremove(ctx, server_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "DELETE FROM premium WHERE guild_id = ?",
            (server_id,)
        )
        await db.commit()
    await ctx.send("✅ Premium removed!")

@bot.command()
async def bal(ctx):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT balance FROM balances WHERE user_id = ?",
            (ctx.author.id,)
        )
        result = await cursor.fetchone()

    amount = result[0] if result else 0
    await ctx.send(f"💰 Your demo balance: `{amount:.2f} credits`")

@bot.command()
async def addbal(ctx, amount: float, user_id: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Owner only!")

    if amount <= 0:
        return await ctx.send("Enter a positive amount.")

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            INSERT INTO balances (user_id, balance)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET balance = balance + excluded.balance
        """, (user_id, amount))
        await db.commit()

    await ctx.send("✅ Demo credits added!")

@bot.command()
async def tip(ctx, member: discord.Member, amount: float):
    if amount <= 0 or member.bot or member.id == ctx.author.id:
        return await ctx.send("❌ Invalid tip.")

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO balances (user_id) VALUES (?)",
            (ctx.author.id,)
        )
        await db.execute(
            "INSERT OR IGNORE INTO balances (user_id) VALUES (?)",
            (member.id,)
        )

        cursor = await db.execute(
            "SELECT balance FROM balances WHERE user_id = ?",
            (ctx.author.id,)
        )
        sender = await cursor.fetchone()

        if sender[0] < amount:
            return await ctx.send("❌ Not enough demo credits.")

        await db.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (amount, ctx.author.id)
        )
        await db.execute(
            "UPDATE balances SET balance = balance + ? WHERE user_id = ?",
            (amount, member.id)
        )
        await db.commit()

    await ctx.send(f"✅ Sent `{amount:.2f} demo credits` to {member.mention}!")

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in your hosting service's Secrets.")

bot.run(TOKEN)
