"""Shared SQLite storage and schema management for ENTROPY."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import config

SCHEMA_VERSION = 2

_EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT,
    file_path     TEXT,
    event_type    TEXT,
    entropy       REAL,
    entropy_delta REAL,
    pid           INTEGER,
    process_name  TEXT,
    action        INTEGER,
    status        TEXT,
    requested_action INTEGER,
    outcome       TEXT,
    dry_run       INTEGER
)
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open the application database with consistent connection settings."""
    database_path = path or config.DB_PATH
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_events_columns(connection: sqlite3.Connection) -> None:
    """Upgrade the original Day 1 table without destroying existing data."""
    existing = {
        row[1] for row in connection.execute("PRAGMA table_info(events)")
    }
    columns = {
        "timestamp": "TEXT",
        "file_path": "TEXT",
        "event_type": "TEXT",
        "entropy": "REAL",
        "entropy_delta": "REAL",
        "pid": "INTEGER",
        "process_name": "TEXT",
        "action": "INTEGER",
        "status": "TEXT",
        "requested_action": "INTEGER",
        "outcome": "TEXT",
        "dry_run": "INTEGER",
    }
    for name, definition in columns.items():
        if name not in existing:
            connection.execute(
                f"ALTER TABLE events ADD COLUMN {name} {definition}"
            )


def init_db(path: str | None = None) -> sqlite3.Connection:
    """Create or migrate the shared events schema and return a connection."""
    database_path = Path(path or config.DB_PATH)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(str(database_path))
    connection.execute(_EVENTS_SCHEMA)
    _ensure_events_columns(connection)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_events_action ON events(action)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_events_file_path ON events(file_path)")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()
    return connection
