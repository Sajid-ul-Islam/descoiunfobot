import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                request_count INTEGER DEFAULT 1,
                last_account_no TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                timestamp TIMESTAMP
            )
        """)
        conn.commit()

def track_user(user, command: str = "", account_no: str = ""):
    if not user:
        return
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    now = datetime.now()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, request_count FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            # Update existing user
            acc_update = ", last_account_no = ?" if account_no else ""
            params = [username, first_name, last_name, now]
            if account_no:
                params.append(account_no)
            params.append(user_id)

            cursor.execute(f"""
                UPDATE users 
                SET username = ?, first_name = ?, last_name = ?, last_seen = ?, request_count = request_count + 1 {acc_update}
                WHERE user_id = ?
            """, params)
        else:
            # Insert new user
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen, request_count, last_account_no)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (user_id, username, first_name, last_name, now, now, account_no))

        # Log activity
        if command:
            cursor.execute("""
                INSERT INTO activity_log (user_id, command, timestamp)
                VALUES (?, ?, ?)
            """, (user_id, command, now))

        conn.commit()

def get_admin_stats() -> dict:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE last_seen >= ?", (today_start,))
        active_today = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE last_seen >= ?", (week_start,))
        active_week = cursor.fetchone()["cnt"]

        cursor.execute("SELECT SUM(request_count) as cnt FROM users")
        row = cursor.fetchone()
        total_requests = row["cnt"] if row and row["cnt"] else 0

        cursor.execute("SELECT user_id, username, first_name, request_count, last_seen FROM users ORDER BY last_seen DESC LIMIT 5")
        recent_users = cursor.fetchall()

    return {
        "total_users": total_users,
        "active_today": active_today,
        "active_week": active_week,
        "total_requests": total_requests,
        "recent_users": [dict(r) for r in recent_users]
    }
