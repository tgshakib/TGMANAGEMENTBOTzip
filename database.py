import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict

DB_PATH = "subscriptions.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            joined_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            package_id      INTEGER NOT NULL,
            package_name    TEXT NOT NULL,
            start_date      TEXT,
            end_date        TEXT,
            status          TEXT DEFAULT 'pending',  -- pending/active/expired/rejected
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            subscription_id INTEGER,
            package_id      INTEGER NOT NULL,
            package_name    TEXT NOT NULL,
            amount          INTEGER NOT NULL,
            screenshot_file_id TEXT,
            status          TEXT DEFAULT 'pending',  -- pending/approved/rejected
            submitted_at    TEXT DEFAULT (datetime('now')),
            reviewed_at     TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS scheduled_alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            message     TEXT NOT NULL,
            send_at     TEXT NOT NULL,
            repeat_times INTEGER DEFAULT 1,
            sent_count   INTEGER DEFAULT 0,
            interval_hours INTEGER DEFAULT 24,
            status      TEXT DEFAULT 'pending',  -- pending/done
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminder_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            sub_id      INTEGER NOT NULL,
            days_before INTEGER NOT NULL,
            sent_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)

        # Migration: add broker_name column to payments if missing
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(payments)").fetchall()]
        if "broker_name" not in cols:
            conn.execute("ALTER TABLE payments ADD COLUMN broker_name TEXT")

        # Seed admin_id from env var only if not already stored
        env_admin = os.environ.get("ADMIN_ID", "0")
        if env_admin and env_admin != "0":
            conn.execute("""
                INSERT INTO settings (key, value) VALUES ('admin_id', ?)
                ON CONFLICT(key) DO NOTHING
            """, (env_admin,))

    print("✅ Database initialized.")

# ── Settings helpers ───────────────────────────────────────
def get_admin_id() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='admin_id'").fetchone()
        if row:
            return int(row["value"])
    return int(os.environ.get("ADMIN_ID", "0"))

def set_admin_id(new_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES ('admin_id', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (str(new_id),))

def get_admin_transfer_log() -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT value FROM settings WHERE key LIKE 'admin_transfer_%'
            ORDER BY key DESC LIMIT 10
        """).fetchall()
        return [r["value"] for r in rows]

# ── User helpers ───────────────────────────────────────────
def upsert_user(user_id: int, username: str, full_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name
        """, (user_id, username or "", full_name or ""))

def get_user(user_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

# ── Subscription helpers ───────────────────────────────────
def get_active_subscription(user_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM subscriptions
            WHERE user_id=? AND status='active'
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,)).fetchone()
        return dict(row) if row else None

def get_all_active_subscriptions() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.*, u.username, u.full_name
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status='active'
            ORDER BY s.end_date ASC
        """).fetchall()
        return [dict(r) for r in rows]

def create_subscription(user_id: int, package_id: int, package_name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO subscriptions (user_id, package_id, package_name, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, package_id, package_name))
        return cur.lastrowid

def activate_subscription(sub_id: int, days: int):
    start = datetime.now()
    end = start + timedelta(days=days)
    with get_conn() as conn:
        conn.execute("""
            UPDATE subscriptions
            SET status='active', start_date=?, end_date=?
            WHERE id=?
        """, (start.isoformat(), end.isoformat(), sub_id))

def expire_subscriptions():
    """Mark expired subscriptions and return list with user_id + package info."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id, s.user_id, s.package_name, s.end_date,
                   u.username, u.full_name
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status='active' AND s.end_date < ?
        """, (now,)).fetchall()
        if rows:
            ids = [r["id"] for r in rows]
            conn.execute(f"""
                UPDATE subscriptions SET status='expired'
                WHERE id IN ({','.join('?' * len(ids))})
            """, ids)
        return [dict(r) for r in rows]

def get_subscriptions_expiring_in_days(days: int) -> List[Dict]:
    """Get active subscriptions expiring within `days` days."""
    now = datetime.now()
    target = (now + timedelta(days=days)).isoformat()
    target_end = (now + timedelta(days=days+1)).isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.*, u.username, u.full_name
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status='active' AND s.end_date BETWEEN ? AND ?
        """, (target, target_end)).fetchall()
        return [dict(r) for r in rows]

def already_reminded(user_id: int, sub_id: int, days_before: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 1 FROM reminder_log
            WHERE user_id=? AND sub_id=? AND days_before=?
        """, (user_id, sub_id, days_before)).fetchone()
        return row is not None

def log_reminder(user_id: int, sub_id: int, days_before: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reminder_log (user_id, sub_id, days_before)
            VALUES (?, ?, ?)
        """, (user_id, sub_id, days_before))

# ── Payment helpers ────────────────────────────────────────
def create_payment(user_id: int, package_id: int, package_name: str, amount: int) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO payments (user_id, package_id, package_name, amount)
            VALUES (?, ?, ?, ?)
        """, (user_id, package_id, package_name, amount))
        return cur.lastrowid

def attach_screenshot(payment_id: int, file_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE payments SET screenshot_file_id=? WHERE id=?", (file_id, payment_id))

def attach_broker_name(payment_id: int, broker_name: str):
    with get_conn() as conn:
        conn.execute("UPDATE payments SET broker_name=? WHERE id=?", (broker_name, payment_id))

def get_payment(payment_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        return dict(row) if row else None

def approve_payment(payment_id: int) -> Optional[Dict]:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE payments SET status='approved', reviewed_at=? WHERE id=?
        """, (now, payment_id))
        return get_payment(payment_id)

def reject_payment(payment_id: int):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE payments SET status='rejected', reviewed_at=? WHERE id=?
        """, (now, payment_id))

def count_approved_payments(user_id: int, category: str) -> int:
    """category: 'paid' (non-forex) or 'forex'"""
    with get_conn() as conn:
        if category == "forex":
            row = conn.execute("""
                SELECT COUNT(*) AS c FROM payments
                WHERE user_id=? AND status='approved'
                  AND package_name LIKE '%FOREX%'
            """, (user_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT COUNT(*) AS c FROM payments
                WHERE user_id=? AND status='approved'
                  AND package_name NOT LIKE '%FOREX%'
            """, (user_id,)).fetchone()
        return int(row["c"]) if row else 0

def get_pending_payments() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.*, u.username, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.status='pending'
            ORDER BY p.submitted_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

# ── Scheduled alert helpers ────────────────────────────────
def create_alert(title: str, message: str, send_at: str, repeat_times: int, interval_hours: int) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO scheduled_alerts (title, message, send_at, repeat_times, interval_hours)
            VALUES (?, ?, ?, ?, ?)
        """, (title, message, send_at, repeat_times, interval_hours))
        return cur.lastrowid

def get_pending_alerts() -> List[Dict]:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM scheduled_alerts
            WHERE status='pending' AND send_at <= ? AND sent_count < repeat_times
        """, (now,)).fetchall()
        return [dict(r) for r in rows]

def mark_alert_sent(alert_id: int, sent_count: int, repeat_times: int, interval_hours: int):
    if sent_count >= repeat_times:
        with get_conn() as conn:
            conn.execute("UPDATE scheduled_alerts SET status='done', sent_count=? WHERE id=?",
                         (sent_count, alert_id))
    else:
        next_send = (datetime.now() + timedelta(hours=interval_hours)).isoformat()
        with get_conn() as conn:
            conn.execute("""
                UPDATE scheduled_alerts SET sent_count=?, send_at=? WHERE id=?
            """, (sent_count, next_send, alert_id))

def get_all_alerts() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM scheduled_alerts ORDER BY send_at DESC LIMIT 20").fetchall()
        return [dict(r) for r in rows]

# Initialize on import
init_db()
