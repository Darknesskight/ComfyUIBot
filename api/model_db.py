import aiosqlite

DATABASE_PATH = "model.db"

async def init_model_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
               """
               CREATE TABLE IF NOT EXISTS model_defaults (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               model TEXT NOT NULL,
               prompt_template TEXT,
               negative_prompt TEXT,
               width INTEGER,
               height INTEGER,
               steps INTEGER,
               cfg REAL,
               sampler TEXT,
               scheduler TEXT,
               hires TEXT,
               hires_strength REAL,

               UNIQUE(model)
            );
               """
        )
        await db.execute(
               """
               CREATE TABLE IF NOT EXISTS sd_defaults (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               sd_type TEXT NOT NULL,
               model TEXT NOT NULL,
               prompt_template TEXT NOT NULL,
               negative_prompt TEXT,
               width INTEGER NOT NULL,
               height INTEGER NOT NULL,
               steps INTEGER NOT NULL,
               cfg REAL NOT NULL,
               sampler TEXT NOT NULL,
               scheduler TEXT NOT NULL,
               hires TEXT NOT NULL,
               hires_strength REAL NOT NULL,

               UNIQUE(sd_type)
            );
               """
        )
        await db.commit()

async def get_model_default(model):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM model_defaults WHERE model = ?", (model,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row is not None else dict()

async def get_sd_default(sd_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sd_defaults WHERE sd_type = ?", (sd_type,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row is not None else dict()


async def upsert_model_default(model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO model_defaults (model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model) DO UPDATE SET
                prompt_template=excluded.prompt_template,
                negative_prompt=excluded.negative_prompt,
                width=excluded.width,
                height=excluded.height,
                steps=excluded.steps,
                cfg=excluded.cfg,
                sampler=excluded.sampler,
                scheduler=excluded.scheduler,
                hires=excluded.hires,
                hires_strength=excluded.hires_strength;
            """,
            (model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
        )
        await db.commit()

async def upsert_sd_default(sd_type, model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO sd_defaults (sd_type, model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sd_type) DO UPDATE SET
                model=excluded.model,
                prompt_template=excluded.prompt_template,
                negative_prompt=excluded.negative_prompt,
                width=excluded.width,
                height=excluded.height,
                steps=excluded.steps,
                cfg=excluded.cfg,
                sampler=excluded.sampler,
                scheduler=excluded.scheduler,
                hires=excluded.hires,
                hires_strength=excluded.hires_strength;
            """,
            (sd_type, model, prompt_template, negative_prompt, width, height, steps, cfg, sampler, scheduler, hires, hires_strength)
        )
        await db.commit()

async def delete_model_default(model):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            DELETE FROM model_defaults WHERE model = ?;
            """,
            (model,)
        )
        await db.commit()


async def delete_sd_default(sd_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            DELETE FROM sd_defaults WHERE sd_type = ?;
            """,
            (sd_type,)
        )
        await db.commit()
