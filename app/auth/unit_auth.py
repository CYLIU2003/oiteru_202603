"""Authorization helpers for child devices (units)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from app import state


def issue_unit_session_token(conn, unit_name: str, ttl_seconds: int = 900) -> str:
    """Issue a persisted, revocable short-lived token for one child device."""
    token = secrets.token_urlsafe(32)
    issued_at = datetime.now()
    state.create_device_session(
        conn,
        unit_name,
        token,
        (issued_at + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S"),
        issued_at.strftime("%Y-%m-%d %H:%M:%S"),
    )
    return token


def validate_unit_token(conn, unit_name: str, provided_token: str) -> bool:
    return state.validate_device_session(
        conn,
        unit_name,
        provided_token,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
