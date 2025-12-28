import sqlite3
import time
from datetime import datetime, timedelta

class IdempotencyStore:
    def __init__(self, db_path="signals.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_signals (
                signal_id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def is_processed(self, signal_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM processed_signals WHERE signal_id = ?", (signal_id,))
        result = cur.fetchone()
        conn.close()
        return result is not None

    def mark_processed(self, signal_id: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("INSERT INTO processed_signals (signal_id) VALUES (?)", (signal_id,))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            # Already exists
            pass

idempotency = IdempotencyStore()
