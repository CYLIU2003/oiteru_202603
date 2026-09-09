"""Tests for durable child pairing and configuration delivery state."""

from __future__ import annotations

import sqlite3

from app import state


def _connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            initial_stock INTEGER DEFAULT 0,
            connect INTEGER DEFAULT 0,
            available INTEGER DEFAULT 1,
            last_seen TEXT,
            ip_address TEXT
        )"""
    )
    conn.execute("INSERT INTO units (name, password) VALUES ('unit-01', 'secret')")
    state.ensure_state_tables(conn)
    return conn


def test_config_update_is_retained_until_matching_ack():
    conn = _connection()
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


def test_pending_device_secret_conflict_does_not_replace_original_hash():
    conn = _connection()
    state.upsert_pending_unit(conn, "pending-01", "first-device-secret", "192.0.2.1")
    original = state.get_pending_unit(conn, "pending-01")["password_hash"]

    conflict = state.upsert_pending_unit(
        conn, "pending-01", "different-device-secret", "192.0.2.2"
    )
    pending = state.get_pending_unit(conn, "pending-01")

    assert conflict is True
    assert pending["password_hash"] == original
    assert pending["credential_conflict"] == 1
