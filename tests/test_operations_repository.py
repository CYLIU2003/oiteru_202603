"""Integration-style checks for the operations schema and repository."""

from __future__ import annotations

import sqlite3

from app import migrations
from app.repositories.operations_repository import OperationsRepository


def test_operations_migration_creates_history_and_prevents_unit_deletion(
    monkeypatch,
):
    """The repository must retain operations history even on SQLite test setups."""
    monkeypatch.setattr(migrations._db, "db_type", "sqlite")
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE units (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE admin_users (id INTEGER PRIMARY KEY)")
    try:
        migrations._migration_010(connection)
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"stock_movements", "maintenance_tickets"} <= table_names

        connection.execute("INSERT INTO units (id) VALUES (1)")
        connection.execute("INSERT INTO units (id) VALUES (2)")
        connection.execute("INSERT INTO admin_users (id) VALUES (1)")
        connection.execute(
            """INSERT INTO stock_movements
               (unit_id, movement_type, quantity_delta, stock_before, stock_after,
                reason, admin_user_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                1,
                "restock",
                5,
                0,
                5,
                "scheduled refill",
                1,
                "2026-08-11 10:00:00",
                "2026-08-11 10:00:00",
            ),
        )

        repository = OperationsRepository()
        assert repository.delete_unit_without_operations_history(connection, 1) == 0
        assert repository.delete_unit_without_operations_history(connection, 2) == 1
        assert connection.execute("SELECT id FROM units WHERE id = 1").fetchone()
        assert not connection.execute("SELECT id FROM units WHERE id = 2").fetchone()
    finally:
        connection.close()
