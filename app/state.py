"""Persistent state management for OITERU server.

Replaces in-memory dicts with database-backed stores for:
- pending (unregistered) units
- unit config snapshots
- pending config updates
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
                heartbeat_count INT DEFAULT 1,
                credential_conflict TINYINT DEFAULT 0,
                credential_conflict_at DATETIME NULL
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
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS desired_unit_configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_name VARCHAR(255) UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                config_version INT NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (unit_name) REFERENCES units(name) ON DELETE CASCADE
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_config_updates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_update_id VARCHAR(64) UNIQUE NOT NULL,
                unit_name VARCHAR(255) NOT NULL,
                config_json TEXT NOT NULL,
                config_version INT NOT NULL,
                status VARCHAR(16) NOT NULL,
                created_at DATETIME NOT NULL,
                sent_at DATETIME NULL,
                acked_at DATETIME NULL,
                error VARCHAR(255) NULL,
                INDEX idx_device_config_updates_delivery (unit_name, status, config_version),
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
                heartbeat_count INTEGER DEFAULT 1,
                credential_conflict INTEGER DEFAULT 0,
                credential_conflict_at TEXT
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
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS desired_unit_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                config_version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS device_config_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_update_id TEXT UNIQUE NOT NULL,
                unit_name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                config_version INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                acked_at TEXT,
                error TEXT
            )
        """)


# ---------------------------------------------------------------------------
# Pending (unregistered) unit operations
# ---------------------------------------------------------------------------

def get_pending_units(conn) -> List[Dict[str, Any]]:
    rows = _db.fetchall(conn, "SELECT * FROM pending_units ORDER BY last_seen DESC")
    return [dict(r) for r in rows] if rows else []


def upsert_pending_unit(
    conn, unit_name: str, unit_secret: str, ip_address: str
) -> bool:
    """Record an unapproved unit without allowing a credential swap.

    Returns ``True`` when a different secret was presented for an existing
    name.  The original hash is deliberately retained for administrator review.
    """
    from app.auth.auth_manager import hash_secret, verify_secret

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = _db.fetchone(
        conn,
        "SELECT id, password_hash, heartbeat_count FROM pending_units WHERE unit_name = ?",
        (unit_name,),
    )
    if existing:
        new_count = int(existing.get("heartbeat_count", 0)) + 1
        conflict = not verify_secret(existing["password_hash"], unit_secret)
        _db.execute(
            conn,
            """UPDATE pending_units
                  SET ip_address = ?, last_seen = ?, heartbeat_count = ?,
                      credential_conflict = ?, credential_conflict_at = ?
                WHERE unit_name = ?""",
            (ip_address, now, new_count, 1 if conflict else 0, now if conflict else None, unit_name),
        )
        return conflict
    else:
        _db.execute(
            conn,
            """INSERT INTO pending_units
               (unit_name, password_hash, ip_address, first_seen, last_seen, heartbeat_count, credential_conflict)
               VALUES (?, ?, ?, ?, ?, 1, 0)""",
            (unit_name, hash_secret(unit_secret), ip_address, now, now),
        )
        return False


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
# Desired/reported configuration delivery operations
# ---------------------------------------------------------------------------

def get_desired_unit_config(conn, unit_name: str) -> Optional[Dict[str, Any]]:
    row = _db.fetchone(
        conn,
        "SELECT * FROM desired_unit_configs WHERE unit_name = ?",
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


def queue_config_update(conn, unit_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a desired config and an ACK-required delivery record."""
    current = get_desired_unit_config(conn, unit_name)
    version = int(current["config_version"]) + 1 if current else 1
    now = _now()
    config_json = json.dumps(config, ensure_ascii=False, sort_keys=True)
    if current:
        _db.execute(
            conn,
            """UPDATE desired_unit_configs
                  SET config_json = ?, config_version = ?, updated_at = ?
                WHERE unit_name = ?""",
            (config_json, version, now, unit_name),
        )
    else:
        _db.execute(
            conn,
            """INSERT INTO desired_unit_configs
               (unit_name, config_json, config_version, updated_at)
               VALUES (?, ?, ?, ?)""",
            (unit_name, config_json, version, now),
        )

    update_id = uuid4().hex
    _db.execute(
        conn,
        """INSERT INTO device_config_updates
           (config_update_id, unit_name, config_json, config_version, status, created_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (update_id, unit_name, config_json, version, now),
    )
    return {
        "config_update_id": update_id,
        "config_version": version,
        "status": "pending",
        "config": dict(config),
    }


def get_config_update_for_delivery(conn, unit_name: str) -> Optional[Dict[str, Any]]:
    """Return the latest unacknowledged update and retain it for retry."""
    row = _db.fetchone(
        conn,
        """SELECT * FROM device_config_updates
             WHERE unit_name = ? AND status IN ('pending', 'delivered')
             ORDER BY config_version DESC LIMIT 1""",
        (unit_name,),
    )
    if not row:
        return None
    result = dict(row)
    now = _now()
    _db.execute(
        conn,
        """UPDATE device_config_updates
              SET status = 'delivered', sent_at = ?
            WHERE id = ?""",
        (now, result["id"]),
    )
    try:
        config = json.loads(result.get("config_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        config = {}
    return {
        "config_update_id": result["config_update_id"],
        "config_version": int(result["config_version"]),
        "config": config,
    }


def acknowledge_config_update(
    conn,
    unit_name: str,
    config_update_id: str,
    config_version: int,
    applied: bool,
    error: str | None = None,
) -> bool:
    """Record a child ACK; only the matching queued update can change state."""
    row = _db.fetchone(
        conn,
        """SELECT id FROM device_config_updates
             WHERE unit_name = ? AND config_update_id = ? AND config_version = ?
               AND status IN ('pending', 'delivered')""",
        (unit_name, config_update_id, config_version),
    )
    if not row:
        return False
    status = "applied" if applied else "failed"
    _db.execute(
        conn,
        """UPDATE device_config_updates
              SET status = ?, acked_at = ?, error = ?
            WHERE id = ?""",
        (status, _now(), error[:255] if error else None, row["id"]),
    )
    return True


# ---------------------------------------------------------------------------
# Legacy pending-config helpers (kept only for a pre-ACK migration path)
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
