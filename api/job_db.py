import sqlite3
from models.sd_options import SDOptions

_conn = sqlite3.connect("job.db")


def init_db():
    _conn.cursor().execute(
        "CREATE TABLE IF NOT EXISTS job (id INTEGER PRIMARY KEY AUTOINCREMENT, data json);"
    )
    _conn.cursor().execute(
        "CREATE TABLE IF NOT EXISTS fluxjob (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT);"
    )
    _conn.cursor().execute(
        "CREATE TABLE IF NOT EXISTS videojob (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT);"
    )


def add_job(sd_options: SDOptions):
    c = _conn.cursor()
    c.execute("INSERT INTO job (data) VALUES (?)", (sd_options.to_json(),))
    _conn.commit()

    return c.lastrowid


def get_job(id: str) -> SDOptions:
    c = _conn.cursor()
    c.execute("SELECT data FROM job WHERE id=?", (id,))
    return SDOptions.from_json(c.fetchone()[0])


def add_fluxjob(prompt: str):
    c = _conn.cursor()
    c.execute("INSERT INTO fluxjob (prompt) VALUES (?)", (prompt,))
    _conn.commit()

    return c.lastrowid

def get_fluxjob(id: str) -> SDOptions:
    c = _conn.cursor()
    c.execute("SELECT prompt FROM fluxjob WHERE id=?", (id,))
    return c.fetchone()[0]

def add_videojob(prompt: str):
    c = _conn.cursor()
    c.execute("INSERT INTO videojob (prompt) VALUES (?)", (prompt,))
    _conn.commit()

    return c.lastrowid

def get_videojob(id: str) -> SDOptions:
    c = _conn.cursor()
    c.execute("SELECT prompt FROM videojob WHERE id=?", (id,))
    return c.fetchone()[0]
