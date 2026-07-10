"""Authorization helpers for child devices (units)."""

from __future__ import annotations

import hmac
import secrets
from typing import Dict, Optional


_unit_session_tokens: Dict[str, str] = {}


def issue_unit_session_token(unit_name: str) -> str:
    token = secrets.token_urlsafe(24)
    _unit_session_tokens[unit_name] = token
    return token


def validate_unit_token(unit_name: str, provided_token: str) -> bool:
    expected = _unit_session_tokens.get(unit_name)
    return bool(expected and provided_token) and hmac.compare_digest(
        expected, provided_token
    )


def get_push_headers(unit_name: str) -> dict:
    token = _unit_session_tokens.get(unit_name)
    if not token:
        return {}
    return {"X-Oiteru-Unit-Auth": token}


def get_unit_session_tokens() -> Dict[str, str]:
    return dict(_unit_session_tokens)
