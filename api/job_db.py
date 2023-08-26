import sqlite3
import json

_conn = sqlite3.connect('job.db')

def init_db():
    _conn.cursor().execute("CREATE TABLE IF NOT EXISTS job (id INTEGER PRIMARY KEY AUTOINCREMENT, data json);")

def add_job(data):
    c = _conn.cursor()
    c.execute("INSERT INTO job (data) VALUES (?)", (json.dumps(data),))
    _conn.commit()

    return c.lastrowid

def get_job(id):
    c = _conn.cursor()
    c.execute("SELECT data FROM job WHERE id=?", (id,))
    return json.loads(c.fetchone()[0])