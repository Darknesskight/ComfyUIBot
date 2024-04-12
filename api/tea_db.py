import aiosqlite

DATABASE_PATH = "tea.db"


async def init_tea_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS channels ("
            "guild_id INTEGER NOT NULL,"
            "channel_id INTEGER NOT NULL,"
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


async def get_channel_ids(guild_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT channel_id FROM channels WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            channel_ids = await cursor.fetchall()
    return [item[0] for item in channel_ids]


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


async def toggle_guild_autoreply(guild_id, channel_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        is_guild_autoreplying = await is_guild_autoreply(guild_id)
        if is_guild_autoreplying:
            await db.execute("DELETE FROM channels  WHERE guild_id = ?", (guild_id,))
        else:
            await db.execute(
                "INSERT INTO channels (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id),
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
