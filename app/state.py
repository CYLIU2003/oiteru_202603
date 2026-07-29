"""Persistent state management for OITERU server.

Replaces in-memory dicts with database-backed stores for:
- pending (unregistered) units
- unit config snapshots
- pending config updates
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from db_adapter import db as _db, get_connection
from app.logger import get_logger

logger = get_logger(__name__)


def ensure_state_tables(conn):
    """Create state tables if they do not exist."""
    if _db.db_type == "mysql":
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS pending_units (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                ip_address VARCHAR(50),
                first_seen DATETIME,
                last_seen DATETIME,
                heartbeat_count INT DEFAULT 1
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS unit_config_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                ip_address VARCHAR(50),
                last_updated DATETIME,
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS pending_config_updates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) NOT NULL,
                token_hash CHAR(64) UNIQUE NOT NULL,
                issued_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                revoked_at DATETIME NULL,
                last_used_at DATETIME NULL,
                INDEX idx_device_sessions_unit_active (unit_name, expires_at),
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_status_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) NOT NULL,
                status VARCHAR(64) NOT NULL,
                detail VARCHAR(255) NULL,
                created_at DATETIME NOT NULL,
                INDEX idx_device_status_logs_unit_created (unit_name, created_at),
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)
    else:
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS pending_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                ip_address TEXT,
                first_seen TEXT,
                last_seen TEXT,
                heartbeat_count INTEGER DEFAULT 1
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS unit_config_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                ip_address TEXT,
                last_updated TEXT
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS pending_config_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                last_used_at TEXT,
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_status_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)


# ---------------------------------------------------------------------------
# Pending (unregistered) unit operations
# ---------------------------------------------------------------------------

def get_pending_units(conn) -> List[Dict[str, Any]]:
    rows = _db.fetchall(conn, "SELECT * FROM pending_units ORDER BY last_seen DESC")
    return [dict(r) for r in rows] if rows else []


def upsert_pending_unit(
    conn, unit_name: str, password_hash: str, ip_address: str
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = _db.fetchone(
        conn, "SELECT id, heartbeat_count FROM pending_units WHERE unit_name = ?", (unit_name,)
    )
    if existing:
        new_count = int(existing.get("heartbeat_count", 0)) + 1
        _db.execute(
            conn,
            "UPDATE pending_units SET ip_address = ?, last_seen = ?, heartbeat_count = ? WHERE unit_name = ?",
            (ip_address, now, new_count, unit_name),
        )
    else:
        _db.execute(
            conn,
            "INSERT INTO pending_units (unit_name, password_hash, ip_address, first_seen, last_seen, heartbeat_count) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (unit_name, password_hash, ip_address, now, now),
        )


def get_pending_unit(conn, unit_name: str) -> Optional[Dict[str, Any]]:
    row = _db.fetchone(
        conn, "SELECT * FROM pending_units WHERE unit_name = ?", (unit_name,)
    )
    return dict(row) if row else None


def delete_pending_unit(conn, unit_name: str) -> None:
    _db.execute(conn, "DELETE FROM pending_units WHERE unit_name = ?", (unit_name,))


# ---------------------------------------------------------------------------
# Unit config snapshot operations
# ---------------------------------------------------------------------------

def upsert_unit_config_snapshot(
    conn, unit_name: str, config: Dict[str, Any], ip_address: Optional[str] = None
) -> None:
    import json
    config_json = json.dumps(config, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = _db.fetchone(
        conn,
        "SELECT id FROM unit_config_snapshots WHERE unit_name = ?",
        (unit_name,),
    )
    if existing:
        _db.execute(
            conn,
            "UPDATE unit_config_snapshots SET config_json = ?, ip_address = ?, last_updated = ? WHERE unit_name = ?",
            (config_json, ip_address, now, unit_name),
        )
    else:
        _db.execute(
            conn,
            "INSERT INTO unit_config_snapshots (unit_name, config_json, ip_address, last_updated) "
            "VALUES (?, ?, ?, ?)",
            (unit_name, config_json, ip_address, now),
        )


def get_unit_config_snapshot(conn, unit_name: str) -> Optional[Dict[str, Any]]:
    import json
    row = _db.fetchone(
        conn,
        "SELECT * FROM unit_config_snapshots WHERE unit_name = ?",
        (unit_name,),
    )
    if not row:
        return None
    result = dict(row)
    try:
        result["config"] = json.loads(result.get("config_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        result["config"] = {}
    return result


# ---------------------------------------------------------------------------
# Pending config update operations
# ---------------------------------------------------------------------------

def set_pending_config_update(
    conn, unit_name: str, config: Dict[str, Any]
) -> None:
    import json
    config_json = json.dumps(config, ensure_ascii=False)
    existing = _db.fetchone(
        conn,
        "SELECT id FROM pending_config_updates WHERE unit_name = ?",
        (unit_name,),
    )
    if existing:
        _db.execute(
            conn,
            "UPDATE pending_config_updates SET config_json = ?, created_at = ? WHERE unit_name = ?",
            (config_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), unit_name),
        )
    else:
        _db.execute(
            conn,
            "INSERT INTO pending_config_updates (unit_name, config_json, created_at) VALUES (?, ?, ?)",
            (unit_name, config_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def pop_pending_config_update(
    conn, unit_name: str
) -> Optional[Dict[str, Any]]:
    import json
    row = _db.fetchone(
        conn,
        "SELECT * FROM pending_config_updates WHERE unit_name = ?",
        (unit_name,),
    )
    if not row:
        return None
    _db.execute(
        conn,
        "DELETE FROM pending_config_updates WHERE unit_name = ?",
        (unit_name,),
    )
    try:
        return json.loads(row.get("config_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        return None


def delete_pending_config_update(conn, unit_name: str) -> None:
    _db.execute(
        conn, "DELETE FROM pending_config_updates WHERE unit_name = ?", (unit_name,)
    )


# ---------------------------------------------------------------------------
# Device sessions and status logs
# ---------------------------------------------------------------------------

def create_device_session(
    conn, unit_name: str, token: str, expires_at: str, issued_at: str
) -> None:
    """Store only a hash of a short-lived device session token."""
    token_hash = _hash_token(token)
    _db.execute(
        conn,
        "UPDATE device_sessions SET revoked_at = ? WHERE unit_name = ? AND revoked_at IS NULL",
        (issued_at, unit_name),
    )
    _db.execute(
        conn,
        "INSERT INTO device_sessions (unit_name, token_hash, issued_at, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (unit_name, token_hash, issued_at, expires_at),
    )


def validate_device_session(conn, unit_name: str, token: str, now: str) -> bool:
    """Validate and touch a non-revoked, non-expired device session."""
    if not token:
        return False
    row = _db.fetchone(
        conn,
        "SELECT id FROM device_sessions WHERE unit_name = ? AND token_hash = ? "
        "AND revoked_at IS NULL AND expires_at > ?",
        (unit_name, _hash_token(token), now),
    )
    if not row:
        return False
    _db.execute(
        conn,
        "UPDATE device_sessions SET last_used_at = ? WHERE id = ?",
        (now, row["id"]),
    )
    return True


def record_device_status(
    conn, unit_name: str, status: str, detail: str | None = None
) -> None:
    _db.execute(
        conn,
        "INSERT INTO device_status_logs (unit_name, status, detail, created_at) "
        "VALUES (?, ?, ?, ?)",
        (unit_name, status, detail, _now()),
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
