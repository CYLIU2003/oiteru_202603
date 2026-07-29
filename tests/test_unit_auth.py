"""Tests for persisted and revocable child-device session tokens."""

from __future__ import annotations

import sqlite3

from app import state
from app.auth.unit_auth import issue_unit_session_token, validate_unit_token


def test_device_token_is_persisted_and_revoked_when_rotated():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE units (name TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO units (name) VALUES ('unit-01')")
    state.ensure_state_tables(conn)

    first_token = issue_unit_session_token(conn, "unit-01", ttl_seconds=900)
    conn.commit()
    assert validate_unit_token(conn, "unit-01", first_token)

    second_token = issue_unit_session_token(conn, "unit-01", ttl_seconds=900)
    conn.commit()
    assert not validate_unit_token(conn, "unit-01", first_token)
    assert validate_unit_token(conn, "unit-01", second_token)

    stored = conn.execute("SELECT token_hash FROM device_sessions").fetchall()
    assert all(row["token_hash"] not in {first_token, second_token} for row in stored)
