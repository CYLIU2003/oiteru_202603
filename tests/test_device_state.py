"""Tests for durable child pairing and configuration delivery state."""

from __future__ import annotations

import pytest

from app import state
from tests.conftest import run_sql


@pytest.fixture
def conn(mysql_conn):
    run_sql(
        mysql_conn,
        """CREATE TABLE units (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            stock INT DEFAULT 0,
            initial_stock INT DEFAULT 0,
            connect TINYINT DEFAULT 0,
            available TINYINT DEFAULT 1,
            last_seen DATETIME,
            ip_address VARCHAR(50)
        )""",
    )
    run_sql(mysql_conn, "INSERT INTO units (name, password) VALUES ('unit-01', 'secret')")
    state.ensure_state_tables(mysql_conn)
    mysql_conn.commit()
    return mysql_conn


def test_config_update_is_retained_until_matching_ack(conn):
    queued = state.queue_config_update(conn, "unit-01", {"MOTOR_SPEED": 80})

    first_delivery = state.get_config_update_for_delivery(conn, "unit-01")
    second_delivery = state.get_config_update_for_delivery(conn, "unit-01")

    assert first_delivery == second_delivery
    assert first_delivery["config_update_id"] == queued["config_update_id"]
    assert state.acknowledge_config_update(
        conn,
        "unit-01",
        queued["config_update_id"],
        queued["config_version"],
        applied=True,
    )
    assert state.get_config_update_for_delivery(conn, "unit-01") is None


def test_pending_device_secret_conflict_does_not_replace_original_hash(conn):
    state.upsert_pending_unit(conn, "pending-01", "first-device-secret", "192.0.2.1")
    original = state.get_pending_unit(conn, "pending-01")["password_hash"]

    conflict = state.upsert_pending_unit(
        conn, "pending-01", "different-device-secret", "192.0.2.2"
    )
    pending = state.get_pending_unit(conn, "pending-01")

    assert conflict is True
    assert pending["password_hash"] == original
    assert pending["credential_conflict"] == 1
