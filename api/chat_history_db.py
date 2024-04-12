import aiosqlite

DATABASE_PATH = "chat_history.db"


async def init_chat_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                server_id TEXT,
                message TEXT,
                role TEXT
            )
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS system_prompts (
                server_id TEXT PRIMARY KEY,
                additional_prompt TEXT
            )
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_prompts (
                user_id TEXT PRIMARY KEY,
                additional_prompt TEXT
            )
        """
        )
        await db.commit()


async def get_server_prompt(server_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT additional_prompt FROM system_prompts WHERE server_id = ?",
            (server_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return ""


async def get_user_prompt(user_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT additional_prompt FROM user_prompts WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return ""


async def get_chat_history(server_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT message, role FROM chat_history WHERE server_id = ?", (server_id,)
        ) as cursor:
            return await cursor.fetchall()


async def insert_chat_history(server_id, message, role):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO chat_history (server_id, message, role) VALUES (?, ?, ?)",
            (server_id, message, role),
        )
        await db.commit()


async def clear_chat_history(server_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM chat_history WHERE server_id = ?", (server_id,))
        await db.commit()


async def delete_single_chat(server_id, message, role):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM chat_history WHERE server_id = ? AND message = ? AND role = ?",
            (server_id, message, role),
        )
        await db.commit()


async def update_server_prompt(server_id, prompt):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO system_prompts (server_id, additional_prompt)
            VALUES (?, ?)
            ON CONFLICT(server_id) DO UPDATE SET
            additional_prompt=excluded.additional_prompt;
        """,
            (server_id, prompt),
        )
        await db.commit()


async def update_user_prompt(user_id, prompt):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_prompts (user_id, additional_prompt)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            additional_prompt=excluded.additional_prompt;
        """,
            (user_id, prompt),
        )
        await db.commit()
