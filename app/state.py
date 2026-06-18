"""Persistent state management for OITERU server.

Replaces in-memory dicts with database-backed stores for:
- pending (unregistered) units
- unit config snapshots
- pending config updates
"""

from __future__ import annotations

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
