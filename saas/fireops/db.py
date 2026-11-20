"""SQLite persistence layer (stdlib only, WAL mode, one connection per unit of work)."""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    simulator_enabled INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','operator','viewer')),
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    width REAL NOT NULL DEFAULT 100,
    height REAL NOT NULL DEFAULT 60,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS robots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'FFHR-1',
    api_key_hash TEXT NOT NULL UNIQUE,
    api_key_prefix TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'offline',
    last_seen REAL,
    last_telemetry TEXT,
    risk_score REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    robot_id INTEGER NOT NULL REFERENCES robots(id) ON DELETE CASCADE,
    ts REAL NOT NULL,
    temperature REAL, smoke REAL, gas REAL, humidity REAL, flame INTEGER,
    battery REAL, water_level REAL, motor_temp REAL, x REAL, y REAL,
    risk_score REAL, severity TEXT
);
CREATE INDEX IF NOT EXISTS ix_tel_robot_ts ON telemetry(robot_id, ts);
CREATE INDEX IF NOT EXISTS ix_tel_org_ts ON telemetry(org_id, ts);
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    robot_id INTEGER REFERENCES robots(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    source TEXT NOT NULL,
    peak_risk REAL NOT NULL DEFAULT 0,
    x REAL, y REAL,
    assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at REAL NOT NULL,
    acknowledged_at REAL,
    resolved_at REAL
);
CREATE INDEX IF NOT EXISTS ix_inc_org ON incidents(org_id, status);
CREATE TABLE IF NOT EXISTS incident_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    user_id INTEGER
);
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    metric TEXT NOT NULL,
    op TEXT NOT NULL,
    threshold REAL NOT NULL,
    severity TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    robot_id INTEGER NOT NULL REFERENCES robots(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    params TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    result TEXT,
    issued_by INTEGER,
    created_at REAL NOT NULL,
    delivered_at REAL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS ix_cmd_robot ON commands(robot_id, status);
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,
    events TEXT NOT NULL DEFAULT '*',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_status TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    user_id INTEGER,
    ts REAL NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_audit_org ON audit_log(org_id, ts);
CREATE TABLE IF NOT EXISTS usage (
    org_id INTEGER NOT NULL,
    period TEXT NOT NULL,
    telemetry_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (org_id, period)
);
"""

_init_lock = threading.Lock()
_initialized_for: set[str] = set()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db() -> None:
    with _init_lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()
        _initialized_for.add(settings.database_path)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    if settings.database_path not in _initialized_for:
        init_db()
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def rows(rs) -> list[dict[str, Any]]:
    return [dict(r) for r in rs]


def now() -> float:
    return time.time()


def audit(conn: sqlite3.Connection, org_id: int, user_id: int | None, action: str, detail: Any = "") -> None:
    if not isinstance(detail, str):
        detail = json.dumps(detail, default=str)
    conn.execute(
        "INSERT INTO audit_log (org_id, user_id, ts, action, detail) VALUES (?,?,?,?,?)",
        (org_id, user_id, now(), action, detail),
    )
