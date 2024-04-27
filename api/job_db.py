import sqlite3
import json
from models.sd_options import SDOptions

_conn = sqlite3.connect("job.db")


def init_db():
    _conn.cursor().execute(
        "CREATE TABLE IF NOT EXISTS job (id INTEGER PRIMARY KEY AUTOINCREMENT, data json);"
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
