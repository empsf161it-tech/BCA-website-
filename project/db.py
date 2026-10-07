"""
db.py - SQLite helpers for the Smart Reminder and Personal Protection System.

Every query in the app goes through these helpers and uses
parameterized placeholders (?) - values are NEVER formatted into SQL strings.
"""
import os
import sqlite3
from datetime import datetime, timedelta

from flask import g
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "app.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Timestamp formats used across the app (local time, stored as text).
DT_MIN = "%Y-%m-%d %H:%M"          # reminders.due_at, notifications.scheduled_at
DT_SEC = "%Y-%m-%d %H:%M:%S"       # created_at / triggered_at / etc.


def now_str():
    """Current local time with seconds."""
    return datetime.now().strftime(DT_SEC)


def get_db():
    """Return the SQLite connection for the current request (created lazily)."""
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row            # rows behave like dicts
        conn.execute("PRAGMA foreign_keys = ON")  # enforce FK + cascades
        g.db = conn
    return g.db


def close_db(exception=None):
    """Close the connection at the end of the request."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query_all(sql, params=()):
    """Run a SELECT and return a list of rows."""
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    """Run a SELECT and return the first row (or None)."""
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE, commit, and return the cursor.

    Use cursor.lastrowid after an INSERT and cursor.rowcount after an UPDATE/DELETE.
    """
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur


def log_history(user_id, activity_type, reference_id, details):
    """Append one entry to the history log (the table is append-only)."""
    execute(
        "INSERT INTO history (user_id, activity_type, reference_id, details, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, activity_type, reference_id, details, now_str()),
    )


# ---------------------------------------------------------------------------
# Schema creation + seed data
# ---------------------------------------------------------------------------
def init_db(app):
    """Create tables from schema.sql (if missing) and seed demo data once."""
    with app.app_context():
        conn = get_db()
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        seed_demo_data()


def seed_demo_data():
    """Insert one demo user (with sample data) and one admin if they don't exist."""
    # --- Admin ---------------------------------------------------------
    if query_one("SELECT 1 FROM admins WHERE username = ?", ("admin",)) is None:
        execute(
            "INSERT INTO admins (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("Admin@1234"), "admin"),
        )

    # --- Demo user -----------------------------------------------------
    if query_one("SELECT 1 FROM users WHERE email = ?", ("demo@example.com",)) is not None:
        return

    cur = execute(
        "INSERT INTO users (full_name, email, password_hash, phone, is_active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        ("Demo User", "demo@example.com", generate_password_hash("Demo@1234"),
         "+919876543210", now_str()),
    )
    uid = cur.lastrowid

    # A few sample reminders relative to "now" so the dashboard isn't empty.
    now = datetime.now().replace(second=0, microsecond=0)
    samples = [
        ("Take medicine", "After lunch", "task",
         now + timedelta(minutes=5), None, 5),
        ("Team meeting", "Project sync on video call", "event",
         now + timedelta(hours=3), None, 15),
        ("Drink water", "Stay hydrated", "recurring",
         now + timedelta(hours=1), "daily", 5),
        ("Pay electricity bill", "Due this week", "task",
         now + timedelta(days=2), None, 60),
    ]
    for title, desc, rtype, due, rule, notify in samples:
        cur = execute(
            "INSERT INTO reminders (user_id, title, description, reminder_type, due_at, "
            "recurrence_rule, notify_before_min, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            (uid, title, desc, rtype, due.strftime(DT_MIN), rule, notify),
        )
        log_history(uid, "reminder", cur.lastrowid, f"Created reminder '{title}'")

    cur = execute(
        "INSERT INTO emergency_contacts (user_id, contact_name, phone, email, relationship, priority) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uid, "Asha Sharma", "+919812345678", "asha@example.com", "Sister", 1),
    )
    log_history(uid, "contact", cur.lastrowid, "Added emergency contact 'Asha Sharma'")
