import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                person_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                score REAL NOT NULL,
                status TEXT NOT NULL,
                snapshot_path TEXT,
                details TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        conn.commit()

def log_event(
    person_id: str,
    event_type: str,
    score: float,
    status: str = "ACTIVE",
    snapshot_path: Optional[str] = None,
    details: str = ""
) -> int:
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (timestamp, person_id, event_type, score, status, snapshot_path, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now_iso, person_id, event_type, score, status, snapshot_path, details))
        conn.commit()
        return cursor.lastrowid

def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, person_id, event_type, score, status, snapshot_path, details
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def clear_events():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events")
        conn.commit()

# Initialize upon module load
init_db()
