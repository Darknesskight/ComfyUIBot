import aiosqlite

from models.autoreply import GuildAutoReply

DATABASE_PATH = "tea.db"


async def init_tea_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS channels ("
            "guild_id INTEGER NOT NULL,"
            "channel_id INTEGER NOT NULL,"
            "prefix TEXT,"
            "reverse_check INTEGER CHECK (reverse_check IN (0, 1)),"
            "PRIMARY KEY (guild_id, channel_id)"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS opt_out_users ("
            "user_id TEXT NOT NULL,"
            "PRIMARY KEY (user_id)"
            ")"
        )
        await db.commit()


async def get_guild_autoreply(guild_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT channel_id, prefix, reverse_check FROM channels WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return GuildAutoReply(row[0], row[1], bool(row[2]))


async def is_user_opt_out(user_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM opt_out_users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def is_guild_autoreply(guild_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT channel_id FROM channels WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def toggle_guild_autoreply(guild_id, guild_autoreply: GuildAutoReply):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        is_guild_autoreplying = await is_guild_autoreply(guild_id)
        if is_guild_autoreplying:
            await db.execute("DELETE FROM channels WHERE guild_id = ?", (guild_id,))
        else:
            await db.execute(
                "INSERT INTO channels (guild_id, channel_id, prefix, reverse_check) VALUES (?, ?, ?, ?)",
                (guild_id, guild_autoreply.channel_id, guild_autoreply.prefix, int(guild_autoreply.reverse_check)),
            )
        await db.commit()
        return not is_guild_autoreplying


async def toggle_user_optout(username):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        user_opted_out = await is_user_opt_out(username)

        if user_opted_out:
            await db.execute(
                "DELETE FROM opt_out_users  WHERE user_id = ?", (username,)
            )
        else:
            await db.execute(
                "INSERT INTO opt_out_users (user_id) VALUES (?)", (username,)
            )
        await db.commit()

        return not user_opted_out
