"""Integration-style checks for the operations schema and repository."""

from __future__ import annotations

from app import migrations
from app.repositories.operations_repository import OperationsRepository
from tests.conftest import run_sql


def test_operations_migration_creates_history_and_prevents_unit_deletion(mysql_conn):
    """The repository must retain operations history for units that have it."""
    connection = mysql_conn
    run_sql(connection, "CREATE TABLE units (id INT PRIMARY KEY)")
    run_sql(connection, "CREATE TABLE admin_users (id INT PRIMARY KEY)")

    migrations._migration_010(connection)
    table_names = {
        row["table_name"]
        for row in run_sql(
            connection,
            "SELECT table_name AS table_name FROM information_schema.tables"
            " WHERE table_schema = DATABASE()",
        )
    }
    assert {"stock_movements", "maintenance_tickets"} <= table_names

    run_sql(connection, "INSERT INTO units (id) VALUES (1)")
    run_sql(connection, "INSERT INTO units (id) VALUES (2)")
    run_sql(connection, "INSERT INTO admin_users (id) VALUES (1)")
    run_sql(
        connection,
        """INSERT INTO stock_movements
           (unit_id, movement_type, quantity_delta, stock_before, stock_after,
            reason, admin_user_id, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
    assert run_sql(connection, "SELECT id FROM units WHERE id = 1")
    assert not run_sql(connection, "SELECT id FROM units WHERE id = 2")
