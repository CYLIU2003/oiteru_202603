"""Tests for persisted and revocable child-device session tokens."""

from __future__ import annotations

from app import state
from app.auth.unit_auth import issue_unit_session_token, validate_unit_token
from tests.conftest import run_sql


def test_device_token_is_persisted_and_revoked_when_rotated(mysql_conn):
    conn = mysql_conn
    run_sql(conn, "CREATE TABLE units (name VARCHAR(255) PRIMARY KEY)")
    run_sql(conn, "INSERT INTO units (name) VALUES ('unit-01')")
    state.ensure_state_tables(conn)

    first_token = issue_unit_session_token(conn, "unit-01", ttl_seconds=900)
    conn.commit()
    assert validate_unit_token(conn, "unit-01", first_token)

    second_token = issue_unit_session_token(conn, "unit-01", ttl_seconds=900)
    conn.commit()
    assert not validate_unit_token(conn, "unit-01", first_token)
    assert validate_unit_token(conn, "unit-01", second_token)

    stored = run_sql(conn, "SELECT token_hash FROM device_sessions")
    assert all(row["token_hash"] not in {first_token, second_token} for row in stored)
