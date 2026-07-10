"""Database migration management for OITERU."""

from __future__ import annotations

from app.logger import get_logger
from db_adapter import db as _db, get_connection

logger = get_logger(__name__)

MIGRATIONS = [
    "001_add_dispense_events",
    "002_add_settings_usage_limit",
    "003_add_settings_limit_period",
    "004_add_users_last_reset_date",
    "005_add_card_id_hash",
    "006_add_state_tables",
]


def run_all_migrations():
    """Run all pending migrations."""
    from datetime import datetime

    with get_connection() as conn:
        # Ensure migration tracking table exists
        _db.execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """ if _db.db_type == "mysql" else
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )

        applied = {
            row["name"]
            for row in _db.fetchall(conn, "SELECT name FROM schema_migrations") or []
        }

        for migration_name in MIGRATIONS:
            if migration_name in applied:
                continue
            logger.info("Running migration: %s", migration_name)
            _apply_migration(conn, migration_name)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _db.execute(
                conn,
                "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
                (migration_name, now),
            )
            logger.info("Migration applied: %s", migration_name)


def _apply_migration(conn, name: str):
    if name == "001_add_dispense_events":
        _migration_001(conn)
    elif name == "002_add_settings_usage_limit":
        _migration_002(conn)
    elif name == "003_add_settings_limit_period":
        _migration_003(conn)
    elif name == "004_add_users_last_reset_date":
        _migration_004(conn)
    elif name == "005_add_card_id_hash":
        _migration_005(conn)
    elif name == "006_add_state_tables":
        _migration_006(conn)


def _migration_001(conn):
    if _db.db_type == "mysql":
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS dispense_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_id VARCHAR(64) UNIQUE NOT NULL,
                unit_name VARCHAR(255) NOT NULL,
                card_id VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL,
                error_code VARCHAR(64),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
    else:
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS dispense_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                unit_name TEXT NOT NULL,
                card_id TEXT NOT NULL,
                status TEXT NOT NULL,
                error_code TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)


def _migration_002(conn):
    _safe_add_column(conn, "settings", "usage_limit", "INT DEFAULT 2")


def _migration_003(conn):
    col_type = "VARCHAR(10) DEFAULT 'day'" if _db.db_type == "mysql" else "TEXT DEFAULT 'day'"
    _safe_add_column(conn, "settings", "limit_period", col_type)


def _migration_004(conn):
    col_type = "DATE" if _db.db_type == "mysql" else "TEXT"
    _safe_add_column(conn, "users", "last_reset_date", col_type)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        _db.execute(conn, "UPDATE users SET last_reset_date = ? WHERE last_reset_date IS NULL", (today,))
    except Exception:
        pass


def _migration_005(conn):
    """Add card_id_hash column for pseudonymous card UID storage."""
    col_type = "VARCHAR(255) DEFAULT ''" if _db.db_type == "mysql" else "TEXT DEFAULT ''"
    _safe_add_column(conn, "users", "card_id_hash", col_type)

    # Backfill existing rows with hash
    from app.auth.auth_manager import hash_card_uid
    users = _db.fetchall(conn, "SELECT id, card_id FROM users WHERE card_id_hash IS NULL OR card_id_hash = ''")
    for user in (users or []):
        hashed = hash_card_uid(str(user.get("card_id", "")))
        _db.execute(
            conn,
            "UPDATE users SET card_id_hash = ? WHERE id = ?",
            (hashed, user["id"]),
        )
    logger.info("Backfilled card_id_hash for %d users", len(users or []))


def _migration_006(conn):
    """Create state tables for pending units, config snapshots, pending updates."""
    from app.state import ensure_state_tables
    ensure_state_tables(conn)


def _safe_add_column(conn, table: str, column: str, col_type: str):
    try:
        _db.execute(conn, f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        logger.info("  Added column %s.%s", table, column)
    except Exception:
        pass  # Column already exists
