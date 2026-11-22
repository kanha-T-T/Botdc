import os
import time
import random
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands
import aiosqlite

# CONFIG
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1495419933943922920
SUPPORT_SERVER = "https://discord.gg/ZBaRByVFBC"
DB_PATH = "bot.db"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(
    command_prefix=["!", "?", ".", "$"],
    intents=intents,
    help_command=None
)

invite_cache = {}
active_ftr = {}
ftr_wins = {}


# DATABASE
async def db_exec(query, args=(), fetchone=False, fetchall=False):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, args)
        result = None
        if fetchone:
            result = await cur.fetchone()
        elif fetchall:
            result = await cur.fetchall()
        await db.commit()
        return result


async def setup_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS premium (
            guild_id INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invites (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS inviters (
            guild_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            inviter_id INTEGER,
            code TEXT,
            PRIMARY KEY (guild_id, member_id)
        );
        CREATE TABLE IF NOT EXISTS reaction_roles (
            guild_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, message_id, emoji)
        );
        CREATE TABLE IF NOT EXISTS staff_roles (
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            host_id INTEGER NOT NULL,
            prize TEXT NOT NULL,
            winners INTEGER NOT NULL,
            end_time INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS giveaway_host_roles (
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS server_profiles (
            guild_id INTEGER PRIMARY KEY,
            bio TEXT
        );
        """)
        await db.commit()


async def is_premium(guild_id):
    row = await db_exec(
        "SELECT 1 FROM premium WHERE guild_id = ?",
        (guild_id,), fetchone=True
    )
    return row is not None


def premium_only():
    async def predicate(ctx):
        if not ctx.guild or not await is_premium(ctx.guild.id):
            raise commands.CheckFailure(
                "This server does not have Premium."
            )
        return True
    return commands.check(predicate)


async def get_staff_role(guild_id):
    row = await db_exec(
        "SELECT role_id FROM staff_roles WHERE guild_id = ?",
        (guild_id,), fetchone=True
    )
    return row[0] if row else None


async def can_manage_giveaways(ctx):
    if ctx.author.guild_permissions.manage_guild:
        return True

    row = await db_exec(
        "SELECT role_id FROM giveaway_host_roles WHERE guild_id = ?",
        (ctx.guild.id,), fetchone=True
    )

    return bool(
        row and any(r.id == row[0] for r in ctx.author.roles)
    )


# READY + INVITE CACHE
@bot.event
async def on_ready():
    await setup_database()
    print(f"Logged in as {bot.user} ({bot.user.id})")
    print(f"Serving {len(bot.guilds)} servers")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = {
                inv.code: inv.uses
                for inv in await guild.invites()
            }
        except (discord.Forbidden, discord.HTTPException):
            invite_cache[guild.id] = {}


@bot.event
async def on_guild_join(guild):
    try:
        invite_cache[guild.id] = {
            inv.code: inv.uses
            for inv in await guild.invites()
        }
    except (discord.Forbidden, discord.HTTPException):
        invite_cache[guild.id] = {}


# BASIC COMMANDS
@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def botinfo(ctx):
    users = sum(g.member_count or 0 for g in bot.guilds)
    await ctx.send(
        f"🤖 **{bot.user}**\n"
        f"Servers: `{len(bot.guilds)}`\n"
        f"Members (approx.): `{users}`"
    )


# HELP COMMAND
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="Bot Commands",
        description="Prefixes: `!` `?` `.` `$`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Moderation",
        value="`ban` `kick` `timeout` `untimeout` `mute` "
              "`unmute` `purge` `lock` `unlock` `slowmode` "
              "`warn` `warnings` `unban`",
        inline=False
    )

    embed.add_field(
        name="Invites",
        value="`invites` `inviter` `inviteinfo` `topinvites` "
              "plus `-I` and `-lb`",
        inline=False
    )

    embed.add_field(
        name="Giveaways (FREE)",
        value="`gstart` `gend` `greroll` `gcancel` `glist` `grole`",
        inline=False
    )

    embed.add_field(
        name="Reaction Roles (FREE)",
        value="`rr create` `rr add` `rr remove` `rr list` `rr delete`",
        inline=False
    )

    embed.add_field(
        name="First To React (FREE)",
        value="`ftr start` `ftr stop` `ftr winner` `ftr leaderboard`",
        inline=False
    )

    embed.add_field(
        name="Premium",
        value="`premium` `premium add` `premium remove` "
              "`premium check` `premium list`",
        inline=False
    )

    embed.add_field(
        name="Premium Staff",
        value="`staffset` `staff` `staffremove` `staffrole`",
        inline=False
    )

    embed.add_field(
        name="Server Profile (Premium)",
        value="`setpfp` `setbanner` `setbio` `setname` "
              "`botprofile` `botpfp` `botbanner` `botbio` `botname`",
        inline=False
    )

    embed.add_field(
        name="Owner",
        value="`announce <message>`",
        inline=False
    )

    embed.set_footer(
        text=f"Support: {SUPPORT_SERVER} | If expired, DM @n0pw"
    )

    await ctx.send(embed=embed)


# MODERATION
@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(
        f"🔨 Banned {member.mention}. Reason: {reason}"
    )


@bot.command()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(
        f"👢 Kicked {member.mention}. Reason: {reason}"
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def timeout(
    ctx, member: discord.Member, minutes: int,
    *, reason="No reason provided"
):
    if minutes < 1 or minutes > 40320:
        return await ctx.send(
            "Choose a duration from 1 to 40320 minutes (28 days)."
        )

    await member.timeout(
        timedelta(minutes=minutes),
        reason=reason
    )
    await ctx.send(
        f"⏳ Timed out {member.mention} for {minutes} minutes."
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(
        f"✅ Removed timeout from {member.mention}."
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(
    ctx, member: discord.Member, minutes: int,
    *, reason="No reason provided"
):
    await timeout.callback(ctx, member, minutes, reason=reason)


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await untimeout.callback(ctx, member)


@bot.command()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        return await ctx.send(
            "Choose an amount from 1 to 100."
        )

    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(
        f"🧹 Deleted {len(deleted) - 1} messages."
    )
    await asyncio.sleep(4)
    await msg.delete()


@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=False
    )
    await ctx.send("🔒 Channel locked.")


@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        send_messages=None
    )
    await ctx.send("🔓 Channel unlocked.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    if not 0 <= seconds <= 21600:
        return await ctx.send(
            "Slowmode must be between 0 and 21600 seconds."
        )

    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(
        f"🐢 Slowmode set to {seconds} seconds."
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    await db_exec(
        "INSERT INTO warnings "
        "(guild_id,user_id,moderator_id,reason) VALUES (?,?,?,?)",
        (ctx.guild.id, member.id, ctx.author.id, reason)
    )
    await ctx.send(
        f"⚠️ Warned {member.mention}. Reason: {reason}"
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member):
    rows = await db_exec(
        "SELECT reason, moderator_id FROM warnings "
        "WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id),
        fetchall=True
    )

    if not rows:
        return await ctx.send("No warnings found.")

    lines = [
        f"{i}. {reason} — moderator <@{moderator_id}>"
        for i, (reason, moderator_id) in enumerate(rows, 1)
    ]

    await ctx.send("\n".join(lines[:20]))


@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(
    ctx, user_id: int, *, reason="No reason provided"
):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f"✅ Unbanned {user}.")
  # PREMIUM + GLOBAL ANNOUNCEMENT

@bot.group(name="premium", invoke_without_command=True)
async def premium(ctx):
    embed = discord.Embed(
        title="Premium Features",
        description=(
            "Premium includes staff management and server-specific bot profile "
            "customization.\n\n"
            f"Support: {SUPPORT_SERVER}\n"
            "If the invite expires, DM @n0pw."
        ),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


@premium.command(name="add")
async def premium_add(ctx, guild_id: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bot owner only.")

    await db_exec(
        "INSERT OR IGNORE INTO premium (guild_id) VALUES (?)",
        (guild_id,)
    )
    await ctx.send(f"✅ Premium enabled for `{guild_id}`.")


@premium.command(name="remove")
async def premium_remove(ctx, guild_id: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bot owner only.")

    await db_exec(
        "DELETE FROM premium WHERE guild_id=?",
        (guild_id,)
    )
    await ctx.send(f"✅ Premium removed from `{guild_id}`.")


@premium.command(name="check")
async def premium_check(ctx, guild_id: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bot owner only.")

    status = await is_premium(guild_id)
    await ctx.send(
        f"`{guild_id}` Premium: **{'ON' if status else 'OFF'}**"
    )


@premium.command(name="list")
async def premium_list(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bot owner only.")

    rows = await db_exec(
        "SELECT guild_id FROM premium",
        fetchall=True
    )

    result = "\n".join(f"`{r[0]}`" for r in rows)
    await ctx.send(result[:1900] if result else "No Premium servers.")


@bot.command()
async def announce(ctx, *, message: str):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Bot owner only.")

    sent = 0
    failed = 0

    for guild in bot.guilds:
        channel = next(
            (
                ch for ch in guild.text_channels
                if ch.permissions_for(guild.me).send_messages
            ),
            None
        )

        if channel is None:
            failed += 1
            continue

        try:
            await channel.send(
                f"📢 **Announcement from the bot owner**\n{message}"
            )
            sent += 1
            await asyncio.sleep(1)
        except discord.HTTPException:
            failed += 1

    await ctx.send(
        f"✅ Sent to {sent} servers. Could not send to {failed}."
    )


# INVITE TRACKING

async def invite_counts(guild_id, user_id):
    row = await db_exec(
        "SELECT count FROM invites WHERE guild_id=? AND user_id=?",
        (guild_id, user_id),
        fetchone=True
    )
    return row[0] if row else 0


@bot.event
async def on_invite_create(invite):
    try:
        invite_cache.setdefault(
            invite.guild.id, {}
        )[invite.code] = invite.uses
    except AttributeError:
        pass


@bot.event
async def on_invite_delete(invite):
    try:
        invite_cache.setdefault(
            invite.guild.id, {}
        ).pop(invite.code, None)
    except AttributeError:
        pass


@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter = None
    used_code = None

    try:
        new_invites = await guild.invites()
        old = invite_cache.get(guild.id, {})

        for inv in new_invites:
            if inv.uses and inv.uses > old.get(inv.code, 0):
                inviter = inv.inviter
                used_code = inv.code
                break

        invite_cache[guild.id] = {
            inv.code: inv.uses for inv in new_invites
        }

    except (discord.Forbidden, discord.HTTPException):
        pass

    if inviter:
        await db_exec("""
            INSERT INTO invites (guild_id,user_id,count)
            VALUES (?,?,1)
            ON CONFLICT(guild_id,user_id)
            DO UPDATE SET count=count+1
        """, (guild.id, inviter.id))

        await db_exec(
            "INSERT OR REPLACE INTO inviters "
            "(guild_id,member_id,inviter_id,code) VALUES (?,?,?,?)",
            (guild.id, member.id, inviter.id, used_code)
        )


@bot.command()
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = await invite_counts(ctx.guild.id, member.id)

    await ctx.send(
        f"📨 {member.mention} has **{count}** tracked invites."
    )


@bot.command()
async def inviter(ctx, member: discord.Member = None):
    member = member or ctx.author

    row = await db_exec(
        "SELECT inviter_id FROM inviters "
        "WHERE guild_id=? AND member_id=?",
        (ctx.guild.id, member.id),
        fetchone=True
    )

    if row and row[0]:
        await ctx.send(
            f"{member.mention} was invited by <@{row[0]}>."
        )
    else:
        await ctx.send("I couldn't identify their inviter.")


@bot.command()
async def inviteinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = await invite_counts(ctx.guild.id, member.id)

    row = await db_exec(
        "SELECT COUNT(*) FROM inviters "
        "WHERE guild_id=? AND inviter_id=?",
        (ctx.guild.id, member.id),
        fetchone=True
    )

    await ctx.send(
        f"**Invite info for {member}**\n"
        f"Tracked invites: `{count}`\n"
        f"Known joins: `{row[0] if row else 0}`"
    )


@bot.command()
async def topinvites(ctx):
    rows = await db_exec(
        "SELECT user_id,count FROM invites "
        "WHERE guild_id=? ORDER BY count DESC LIMIT 10",
        (ctx.guild.id,),
        fetchall=True
    )

    if not rows:
        return await ctx.send("No invite data yet.")

    lines = [
        f"**{i}.** <@{uid}> — `{count}`"
        for i, (uid, count) in enumerate(rows, 1)
    ]

    await ctx.send("🏆 **Invite Leaderboard**\n" + "\n".join(lines))
  # GIVEAWAYS (FREE)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def grole(ctx, role: discord.Role):
    await db_exec(
        "INSERT OR REPLACE INTO giveaway_host_roles "
        "(guild_id,role_id) VALUES (?,?)",
        (ctx.guild.id, role.id)
    )
    await ctx.send(
        f"✅ Giveaway host role set to {role.mention}."
    )


@bot.command()
async def gstart(ctx, duration: str, winners: int, *, prize: str):
    if not await can_manage_giveaways(ctx):
        return await ctx.send(
            "❌ You need the giveaway host role or Manage Server."
        )

    if winners < 1 or winners > 20:
        return await ctx.send(
            "Winners must be between 1 and 20."
        )

    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    try:
        amount = int(duration[:-1])
        seconds = amount * units[duration[-1].lower()]

        if amount < 1 or seconds > 30 * 86400:
            raise ValueError

    except (ValueError, KeyError, IndexError):
        return await ctx.send(
            "Use duration like `30s`, `10m`, `2h`, or `1d`."
        )

    end_time = int(time.time()) + seconds

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"**Prize:** {prize}\n"
            f"**Winners:** {winners}\n"
            f"**Ends:** <t:{end_time}:R>\n"
            "React with 🎉 to enter!"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text=f"Hosted by {ctx.author}")

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    await db_exec(
        "INSERT INTO giveaways VALUES (?,?,?,?,?,?,?)",
        (
            message.id,
            ctx.guild.id,
            ctx.channel.id,
            ctx.author.id,
            prize,
            winners,
            end_time
        )
    )


async def finish_giveaway(ctx, message_id, reroll=False):
    row = await db_exec(
        "SELECT guild_id,channel_id,host_id,prize,winners,end_time "
        "FROM giveaways WHERE message_id=?",
        (message_id,),
        fetchone=True
    )

    if not row:
        return await ctx.send("Giveaway not found.")

    guild_id, channel_id, host_id, prize, winner_count, end_time = row

    if guild_id != ctx.guild.id:
        return await ctx.send(
            "That giveaway belongs to another server."
        )

    if not await can_manage_giveaways(ctx):
        return await ctx.send(
            "❌ You need the giveaway host role or Manage Server."
        )

    if not reroll and int(time.time()) < end_time:
        return await ctx.send(
            "That giveaway has not ended yet."
        )

    channel = bot.get_channel(channel_id)

    if channel is None:
        return await ctx.send(
            "Giveaway channel not found."
        )

    try:
        message = await channel.fetch_message(message_id)
        reaction = discord.utils.get(
            message.reactions,
            emoji="🎉"
        )

        entrants = []

        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    entrants.append(user)

    except discord.HTTPException:
        return await ctx.send(
            "Could not read giveaway entries."
        )

    if not entrants:
        await ctx.send("No valid entrants.")

        if not reroll:
            await db_exec(
                "DELETE FROM giveaways WHERE message_id=?",
                (message_id,)
            )
        return

    chosen = random.sample(
        entrants,
        min(winner_count, len(entrants))
    )

    await ctx.send(
        f"🎉 {'New winners' if reroll else 'Winner(s)'} "
        f"for **{prize}**: "
        + ", ".join(u.mention for u in chosen)
    )

    if not reroll:
        await db_exec(
            "DELETE FROM giveaways WHERE message_id=?",
            (message_id,)
        )


@bot.command()
async def gend(ctx, message_id: int):
    await finish_giveaway(ctx, message_id)


@bot.command()
async def greroll(ctx, message_id: int):
    await finish_giveaway(ctx, message_id, reroll=True)


@bot.command()
async def gcancel(ctx, message_id: int):
    if not await can_manage_giveaways(ctx):
        return await ctx.send(
            "❌ You need the giveaway host role or Manage Server."
        )

    await db_exec(
        "DELETE FROM giveaways WHERE message_id=? AND guild_id=?",
        (message_id, ctx.guild.id)
    )

    await ctx.send(
        "✅ Giveaway record cancelled (the original message remains)."
    )


@bot.command()
async def glist(ctx):
    rows = await db_exec(
        "SELECT message_id,prize,end_time FROM giveaways "
        "WHERE guild_id=? ORDER BY end_time",
        (ctx.guild.id,),
        fetchall=True
    )

    if not rows:
        return await ctx.send("No active giveaways.")

    lines = [
        f"`{mid}` — **{prize}** — <t:{end}:R>"
        for mid, prize, end in rows
    ]

    await ctx.send("\n".join(lines)[:1900])


# REACTION ROLES (FREE)

@bot.group(name="rr", invoke_without_command=True)
async def rr(ctx):
    await ctx.send(
        "Reaction roles:\n"
        "`!rr create`\n"
        "`!rr add <messageID> <emoji> @Role`\n"
        "`!rr remove <messageID> <emoji>`\n"
        "`!rr list`\n"
        "`!rr delete <messageID>`"
    )


@rr.command(name="create")
@commands.has_permissions(manage_roles=True)
async def rr_create(ctx):
    msg = await ctx.send(
        "React to this message, then use `!rr add` with its ID."
    )
    await ctx.send(f"Message ID: `{msg.id}`")


@rr.command(name="add")
@commands.has_permissions(manage_roles=True)
async def rr_add(
    ctx, message_id: int, emoji: str, role: discord.Role
):
    try:
        message = await ctx.channel.fetch_message(message_id)
        await message.add_reaction(emoji)

    except (
        discord.NotFound,
        discord.HTTPException,
        discord.Forbidden
    ):
        return await ctx.send(
            "Couldn't find that message or add the reaction."
        )

    await db_exec(
        "INSERT OR REPLACE INTO reaction_roles VALUES (?,?,?,?)",
        (ctx.guild.id, message_id, emoji, role.id)
    )

    await ctx.send(
        f"✅ {emoji} now gives {role.mention}."
    )


@rr.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def rr_remove(ctx, message_id: int, *, emoji: str):
    await db_exec(
        "DELETE FROM reaction_roles "
        "WHERE guild_id=? AND message_id=? AND emoji=?",
        (ctx.guild.id, message_id, emoji)
    )

    await ctx.send(
        "✅ Reaction role mapping removed."
    )


@rr.command(name="list")
async def rr_list(ctx):
    rows = await db_exec(
        "SELECT message_id,emoji,role_id "
        "FROM reaction_roles WHERE guild_id=?",
        (ctx.guild.id,),
        fetchall=True
    )

    if not rows:
        return await ctx.send(
            "No reaction roles configured."
        )

    await ctx.send(
        "\n".join(
            f"Message `{mid}` | {emoji} → <@&{rid}>"
            for mid, emoji, rid in rows
        )[:1900]
    )


@rr.command(name="delete")
@commands.has_permissions(manage_roles=True)
async def rr_delete(ctx, message_id: int):
    await db_exec(
        "DELETE FROM reaction_roles "
        "WHERE guild_id=? AND message_id=?",
        (ctx.guild.id, message_id)
    )

    await ctx.send(
        "✅ All reaction role mappings for that message removed."
    )


@bot.event
async def on_raw_reaction_add(payload):
    if payload.member and payload.member.bot:
        return

    guild = bot.get_guild(payload.guild_id)

    if guild is None:
        return

    emoji = str(payload.emoji)

    row = await db_exec(
        "SELECT role_id FROM reaction_roles "
        "WHERE guild_id=? AND message_id=? AND emoji=?",
        (payload.guild_id, payload.message_id, emoji),
        fetchone=True
    )

    if row:
        role = guild.get_role(row[0])
        member = guild.get_member(payload.user_id)

        if role and member:
            try:
                await member.add_roles(
                    role,
                    reason="Reaction role"
                )
            except discord.HTTPException:
                pass


@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)

    if guild is None:
        return

    emoji = str(payload.emoji)

    row = await db_exec(
        "SELECT role_id FROM reaction_roles "
        "WHERE guild_id=? AND message_id=? AND emoji=?",
        (payload.guild_id, payload.message_id, emoji),
        fetchone=True
    )

    if row:
        role = guild.get_role(row[0])
        member = guild.get_member(payload.user_id)

        if role and member:
            try:
                await member.remove_roles(
                    role,
                    reason="Reaction role removed"
                )
            except discord.HTTPException:
                pass


# FIRST TO REACT (FREE)

@bot.group(name="ftr", invoke_without_command=True)
async def ftr(ctx):
    await ctx.send(
        "Use `!ftr start [seconds]`, `!ftr stop`, "
        "`!ftr winner`, `!ftr leaderboard`."
    )


@ftr.command(name="start")
async def ftr_start(ctx, seconds: int = 30):
    if not 5 <= seconds <= 300:
        return await ctx.send("Choose 5–300 seconds.")

    if ctx.guild.id in active_ftr:
        return await ctx.send(
            "An FTR game is already running."
        )

    msg = await ctx.send(
        f"⚡ **FIRST TO REACT!** "
        f"React with ⚡ within {seconds} seconds!"
    )

    await msg.add_reaction("⚡")

    active_ftr[ctx.guild.id] = {
        "channel_id": ctx.channel.id,
        "message_id": msg.id,
        "winner": None,
        "end": time.time() + seconds
    }

    await asyncio.sleep(seconds)

    game = active_ftr.get(ctx.guild.id)

    if game and game["message_id"] == msg.id:
        await ctx.send("⏰ FTR round ended!")


@ftr.command(name="stop")
@commands.has_permissions(manage_guild=True)
async def ftr_stop(ctx):
    if active_ftr.pop(ctx.guild.id, None):
        await ctx.send("🛑 FTR game stopped.")
    else:
        await ctx.send("No active FTR game.")


@ftr.command(name="winner")
async def ftr_winner(ctx):
    game = active_ftr.get(ctx.guild.id)

    if not game or not game["winner"]:
        return await ctx.send(
            "No winner has reacted yet."
        )

    await ctx.send(
        f"🏆 Winner: <@{game['winner']}>"
    )


@ftr.command(name="leaderboard")
async def ftr_leaderboard(ctx):
    rows = sorted(
        ftr_wins.get(ctx.guild.id, {}).items(),
        key=lambda item: item[1],
        reverse=True
    )

    if not rows:
        return await ctx.send(
            "No FTR wins recorded yet."
        )

    await ctx.send(
        "\n".join(
            f"**{i}.** <@{uid}> — `{wins}` wins"
            for i, (uid, wins) in enumerate(rows[:10], 1)
        )
    )


@bot.listen("on_reaction_add")
async def ftr_reaction(reaction, user):
    if user.bot or str(reaction.emoji) != "⚡":
        return

    guild = reaction.message.guild

    if guild is None:
        return

    game = active_ftr.get(guild.id)

    if not game or game["message_id"] != reaction.message.id:
        return

    if time.time() > game["end"] or game["winner"]:
        return

    game["winner"] = user.id

    ftr_wins.setdefault(guild.id, {})
    ftr_wins[guild.id][user.id] = (
        ftr_wins[guild.id].get(user.id, 0) + 1
    )

    await reaction.message.channel.send(
        f"🏆 {user.mention} was first to react!"
    )
  # PREMIUM STAFF MANAGEMENT

@bot.command()
@premium_only()
@commands.has_permissions(manage_roles=True)
async def staffset(ctx, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await ctx.send(
            "❌ Put the bot's role above the staff role."
        )

    await db_exec(
        "INSERT OR REPLACE INTO staff_roles VALUES (?,?)",
        (ctx.guild.id, role.id)
    )

    await ctx.send(
        f"✅ Staff role set to {role.mention}."
    )


@bot.command()
@premium_only()
@commands.has_permissions(manage_roles=True)
async def staff(ctx, member: discord.Member):
    role_id = await get_staff_role(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None

    if not role:
        return await ctx.send(
            "Set a staff role first with `!staffset @Role`."
        )

    if role >= ctx.guild.me.top_role:
        return await ctx.send(
            "❌ Bot role must be above the staff role."
        )

    await member.add_roles(
        role,
        reason=f"Staff assigned by {ctx.author}"
    )

    await ctx.send(
        f"✅ Added {role.mention} to {member.mention}."
    )


@bot.command()
@premium_only()
@commands.has_permissions(manage_roles=True)
async def staffremove(ctx, member: discord.Member):
    role_id = await get_staff_role(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None

    if not role:
        return await ctx.send(
            "No staff role is configured."
        )

    await member.remove_roles(
        role,
        reason=f"Staff removed by {ctx.author}"
    )

    await ctx.send(
        f"✅ Removed {role.mention} from {member.mention}."
    )


@bot.command()
@premium_only()
async def staffrole(ctx):
    role_id = await get_staff_role(ctx.guild.id)
    role = ctx.guild.get_role(role_id) if role_id else None

    await ctx.send(
        f"Staff role: {role.mention}"
        if role else "No staff role configured."
    )


# SERVER-SPECIFIC BOT PROFILE

def profile_access():
    async def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        if not await is_premium(ctx.guild.id):
            raise commands.CheckFailure(
                "This server needs Premium."
            )

        if not ctx.author.guild_permissions.manage_guild:
            raise commands.CheckFailure(
                "You need Manage Server permission."
            )

        return True

    return commands.check(predicate)


async def attached_image(ctx):
    if not ctx.message.attachments:
        await ctx.send(
            "❌ Attach an image to the command."
        )
        return None

    attachment = ctx.message.attachments[0]

    if (
        attachment.content_type
        and not attachment.content_type.startswith("image/")
    ):
        await ctx.send(
            "❌ Please attach an image."
        )
        return None

    if attachment.size > 8 * 1024 * 1024:
        await ctx.send(
            "❌ Image must be 8 MB or smaller."
        )
        return None

    return await attachment.read()


@bot.command()
@profile_access()
async def setpfp(ctx):
    data = await attached_image(ctx)

    if data is None:
        return

    await ctx.guild.me.edit(avatar=data)

    await ctx.send(
        "✅ Actual bot avatar updated for this server!"
    )


@bot.command()
@profile_access()
async def setbanner(ctx):
    data = await attached_image(ctx)

    if data is None:
        return

    await ctx.guild.me.edit(banner=data)

    await ctx.send(
        "✅ Actual bot banner updated for this server!"
    )


@bot.command()
@profile_access()
async def setbio(ctx, *, bio: str):
    if bio.lower() == "clear":
        await ctx.guild.me.edit(bio=None)
        return await ctx.send(
            "✅ Server-specific bio cleared."
        )

    if len(bio) > 190:
        return await ctx.send(
            "❌ Bio must be 190 characters or fewer."
        )

    await ctx.guild.me.edit(bio=bio)

    await ctx.send(
        "✅ Actual bot bio updated for this server!"
    )


@bot.command()
@profile_access()
async def setname(ctx, *, name: str):
    if not 1 <= len(name) <= 32:
        return await ctx.send(
            "❌ Name must be 1–32 characters."
        )

    await ctx.guild.me.edit(nick=name)

    await ctx.send(
        "✅ Bot nickname updated for this server!"
    )


@bot.command()
@commands.guild_only()
async def botprofile(ctx):
    member = ctx.guild.me

    embed = discord.Embed(
        title=f"{member.display_name} — Server Profile",
        description=(
            "Open the bot's actual profile in this server "
            "to view its guild-specific details."
        ),
        color=discord.Color.blurple()
    )

    if member.guild_avatar:
        embed.set_thumbnail(
            url=member.guild_avatar.url
        )

    if member.guild_banner:
        embed.set_image(
            url=member.guild_banner.url
        )

    await ctx.send(embed=embed)


@bot.command()
@commands.guild_only()
async def botpfp(ctx):
    avatar = ctx.guild.me.guild_avatar

    await ctx.send(
        avatar.url if avatar
        else "No server avatar is set."
    )


@bot.command()
@commands.guild_only()
async def botbanner(ctx):
    banner = ctx.guild.me.guild_banner

    await ctx.send(
        banner.url if banner
        else "No server banner is set."
    )


@bot.command()
@commands.guild_only()
async def botname(ctx):
    await ctx.send(
        f"Server nickname: **{ctx.guild.me.display_name}**"
    )


@bot.command()
@commands.guild_only()
async def botbio(ctx):
    await ctx.send(
        "Open the bot's profile in this server to view "
        "its server-specific bio."
    )


# SHORT ALIASES: -I AND -lb

@bot.listen("on_message")
async def short_invite_aliases(message):
    if message.author.bot or not message.guild:
        return

    ctx = await bot.get_context(message)

    if message.content.strip().lower() == "-i":
        await invites.callback(ctx, None)

    elif message.content.strip().lower() == "-lb":
        await topinvites.callback(ctx)


# ERROR HANDLING

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send(
            "❌ You don't have permission to use that command."
        )

    if isinstance(error, commands.BotMissingPermissions):
        return await ctx.send(
            "❌ I don't have the required permissions."
        )

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            f"❌ Missing argument: `{error.param.name}`."
        )

    if isinstance(error, commands.BadArgument):
        return await ctx.send(
            "❌ Invalid argument. Check the command format."
        )

    if isinstance(error, commands.CheckFailure):
        return await ctx.send(f"❌ {error}")

    if isinstance(error, discord.Forbidden):
        return await ctx.send(
            "❌ Discord denied that action. Check permissions and role order."
        )

    if isinstance(error, discord.HTTPException):
        return await ctx.send(
            "❌ Discord couldn't complete that action. Try again."
        )

    print(f"Command error: {repr(error)}")

    await ctx.send(
        "❌ Something went wrong. Check the bot host logs."
    )


# START BOT

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add it as a secret/environment "
            "variable in your hosting service. Never put it in this file."
        )

    bot.run(TOKEN)
