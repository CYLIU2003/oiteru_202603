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
    "007_add_device_sessions_and_status_logs",
    "008_add_device_configuration_delivery",
    "009_add_admin_users_and_audit_logs",
    "010_add_operations_management",
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
    elif name == "007_add_device_sessions_and_status_logs":
        _migration_007(conn)
    elif name == "008_add_device_configuration_delivery":
        _migration_008(conn)
    elif name == "009_add_admin_users_and_audit_logs":
        _migration_009(conn)
    elif name == "010_add_operations_management":
        _migration_010(conn)


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


def _migration_007(conn):
    """Add persistent session and device status storage to existing installs."""
    from app.state import ensure_state_tables
    ensure_state_tables(conn)


def _migration_008(conn):
    """Add durable desired/reported configuration delivery state."""
    from app.state import ensure_state_tables

    ensure_state_tables(conn)
    conflict_type = "TINYINT DEFAULT 0" if _db.db_type == "mysql" else "INTEGER DEFAULT 0"
    conflict_time_type = "DATETIME NULL" if _db.db_type == "mysql" else "TEXT"
    _safe_add_column(conn, "pending_units", "credential_conflict", conflict_type)
    _safe_add_column(conn, "pending_units", "credential_conflict_at", conflict_time_type)


def _migration_009(conn):
    """Create individual admin accounts and an immutable operator audit trail."""
    if _db.db_type == "mysql":
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL,
                is_active TINYINT NOT NULL DEFAULT 1,
                last_login_at DATETIME NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_user_id INT NULL,
                action VARCHAR(100) NOT NULL,
                target_type VARCHAR(64) NULL,
                target_id VARCHAR(255) NULL,
                created_at DATETIME NOT NULL,
                INDEX idx_admin_audit_created (created_at),
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
        """)
    else:
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                created_at TEXT NOT NULL
            )
        """)


def _migration_010(conn):
    """Create durable inventory and maintenance records for daily operations."""
    if _db.db_type == "mysql":
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_id INT NOT NULL,
                movement_type VARCHAR(32) NOT NULL,
                quantity_delta INT NOT NULL,
                stock_before INT NOT NULL,
                stock_after INT NOT NULL,
                reason VARCHAR(255) NOT NULL,
                admin_user_id INT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                INDEX idx_stock_movements_unit_created (unit_id, created_at),
                INDEX idx_stock_movements_admin_created (admin_user_id, created_at),
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
        """)
        _db.execute(conn, """
            CREATE TABLE IF NOT EXISTS maintenance_tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                unit_id INT NOT NULL,
                category VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                source VARCHAR(32) NOT NULL,
                description VARCHAR(500) NOT NULL,
                opened_by_admin_user_id INT NULL,
                assigned_to_admin_user_id INT NULL,
                resolution_note VARCHAR(500) NULL,
                resolved_by_admin_user_id INT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                resolved_at DATETIME NULL,
                INDEX idx_maintenance_tickets_unit_status (unit_id, status),
                INDEX idx_maintenance_tickets_status_updated (status, updated_at),
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (opened_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_to_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (resolved_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
        """)
        return

    _db.execute(conn, """
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity_delta INTEGER NOT NULL,
            stock_before INTEGER NOT NULL,
            stock_after INTEGER NOT NULL,
            reason TEXT NOT NULL,
            admin_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
        )
    """)
    _db.execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_stock_movements_unit_created
        ON stock_movements (unit_id, created_at)
    """)
    _db.execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_stock_movements_admin_created
        ON stock_movements (admin_user_id, created_at)
    """)
    _db.execute(conn, """
        CREATE TABLE IF NOT EXISTS maintenance_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT NOT NULL,
            opened_by_admin_user_id INTEGER,
            assigned_to_admin_user_id INTEGER,
            resolution_note TEXT,
            resolved_by_admin_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (opened_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
            FOREIGN KEY (assigned_to_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
            FOREIGN KEY (resolved_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
        )
    """)
    _db.execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_unit_status
        ON maintenance_tickets (unit_id, status)
    """)
    _db.execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_status_updated
        ON maintenance_tickets (status, updated_at)
    """)


def _safe_add_column(conn, table: str, column: str, col_type: str):
    """Add a known migration column, without hiding real migration failures."""
    if _column_exists(conn, table, column):
        return
    _db.execute(conn, f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    logger.info("  Added column %s.%s", table, column)


def _column_exists(conn, table: str, column: str) -> bool:
    if _db.db_type == "mysql":
        row = _db.fetchone(
            conn,
            """SELECT 1 FROM information_schema.columns
               WHERE table_schema = DATABASE() AND table_name = ? AND column_name = ?""",
            (table, column),
        )
        return bool(row)
    rows = _db.fetchall(conn, f"PRAGMA table_info({table})")
    return any(row.get("name") == column for row in rows)
