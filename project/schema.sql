-- ============================================================
-- Smart Reminder and Personal Protection System - SQLite schema
-- Safe to run repeatedly (CREATE ... IF NOT EXISTS).
-- ============================================================

PRAGMA foreign_keys = ON;

-- Regular app users -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    phone         TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Reminders ---------------------------------------------------------------
-- due_at is stored as local time text: 'YYYY-MM-DD HH:MM'
CREATE TABLE IF NOT EXISTS reminders (
    reminder_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title             TEXT    NOT NULL,
    description       TEXT,
    reminder_type     TEXT    NOT NULL DEFAULT 'task'
                      CHECK (reminder_type IN ('task', 'event', 'recurring')),
    due_at            TEXT    NOT NULL,
    recurrence_rule   TEXT    CHECK (recurrence_rule IS NULL
                                     OR recurrence_rule IN ('daily', 'weekly', 'monthly')),
    notify_before_min INTEGER NOT NULL DEFAULT 10,
    status            TEXT    NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'completed', 'snoozed', 'cancelled'))
);
CREATE INDEX IF NOT EXISTS idx_reminders_user_due ON reminders(user_id, due_at);

-- Notifications generated for reminders -----------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_id     INTEGER NOT NULL REFERENCES reminders(reminder_id) ON DELETE CASCADE,
    channel         TEXT    NOT NULL DEFAULT 'in_app',
    scheduled_at    TEXT    NOT NULL,
    sent_at         TEXT,
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed'))
);
-- Duplicate protection: one notification per reminder + time slot + channel.
CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_slot
    ON notifications(reminder_id, channel, scheduled_at);

-- Emergency contacts ------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergency_contacts (
    contact_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    contact_name TEXT    NOT NULL,
    phone        TEXT    NOT NULL,
    email        TEXT,
    relationship TEXT,
    priority     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON emergency_contacts(user_id, priority);

-- SOS events --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergency_events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    triggered_at TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'triggered'
                 CHECK (status IN ('triggered', 'cancelled', 'dispatched', 'failed')),
    message      TEXT,
    resolved_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_user ON emergency_events(user_id, triggered_at);

-- Locations captured ONLY as part of an SOS event (never tracked continuously)
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER REFERENCES emergency_events(event_id) ON DELETE CASCADE,
    latitude    REAL NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude   REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    accuracy_m  REAL,
    captured_at TEXT NOT NULL
);

-- Append-only activity history ---------------------------------------------
CREATE TABLE IF NOT EXISTS history (
    history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type TEXT    NOT NULL,   -- reminder | notification | contact | sos | location
    reference_id  INTEGER,            -- id of the related row (no FK: history must outlive it)
    details       TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_history_user_time ON history(user_id, created_at);

-- Enforce "append-only" at the database level.
CREATE TRIGGER IF NOT EXISTS history_no_update
BEFORE UPDATE ON history
BEGIN
    SELECT RAISE(ABORT, 'history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS history_no_delete
BEFORE DELETE ON history
WHEN (SELECT COUNT(*) FROM users WHERE user_id = OLD.user_id) > 0
BEGIN
    SELECT RAISE(ABORT, 'history is append-only');
END;

-- Admin accounts (separate from users) ---------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    admin_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin'
);
