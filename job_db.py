import sqlite3
import json

class JobDB:
    def __init__(self):
        self.conn = sqlite3.connect('job.db')
        self.init_db()
        
    def init_db(self):
        self.conn.cursor().execute("CREATE TABLE IF NOT EXISTS job (id INTEGER PRIMARY KEY AUTOINCREMENT, data json);")

    def add_job(self, data):
        c = self.conn.cursor()
        c.execute("INSERT INTO job (data) VALUES (?)", (json.dumps(data),))
        self.conn.commit()

        return c.lastrowid
    
    def get_job(self, id):
        c = self.conn.cursor()
        c.execute("SELECT data FROM job WHERE id=?", (id,))
        return json.loads(c.fetchone()[0])
