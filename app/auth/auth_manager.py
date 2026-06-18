"""Authentication & security utilities for OITERU.

Handles:
- Password hashing (Werkzeug + legacy SHA-256 compat)
- Session management helpers
- Login brute-force protection
- Default / weak password detection
- Card UID hashing for storage
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Dict, Optional, Set

from werkzeug.security import check_password_hash, generate_password_hash

from app.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Insecure value blocklists
# ---------------------------------------------------------------------------
INSECURE_ADMIN_PASSWORDS: Set[str] = {
    "admin",
    "password",
    "change-this-admin-password",
    "12345678",
    "123456789",
}

INSECURE_FLASK_SECRET_KEYS: Set[str] = {
    "change-this-secret-key",
    "secret",
    "flask-secret",
}

INSECURE_MYSQL_PASSWORDS: Set[str] = {
    "change-this-mysql-password",
    "rootpassword",
    "password",
    "oiteru_password_2025",
}

DEFAULT_ADMIN_HASHES: Set[str] = {
    hashlib.sha256("admin".encode()).hexdigest(),
    hashlib.sha256("change-this-admin-password".encode()).hexdigest(),
    "1b2169971e65007dea2905a92b3f93cceea332f35baf0d1acc74c0dbb3426368",
}

# ---------------------------------------------------------------------------
# Password / secret hashing
# ---------------------------------------------------------------------------


def hash_secret(secret_value: str) -> str:
    """Hash a password or shared secret using Werkzeug pbkdf2."""
    return generate_password_hash(secret_value)


def verify_secret(stored_secret: str, provided_secret: str) -> bool:
    """Verify a secret against a stored hash (Werkzeug + legacy compat)."""
    if not stored_secret or not provided_secret:
        return False

    # Constant-time direct comparison (necessary for legacy plaintext secrets)
    if hmac.compare_digest(stored_secret, provided_secret):
        return True

    # Werkzeug pbkdf2/scrypt hashes
    try:
        if stored_secret.startswith(("pbkdf2:", "scrypt:")):
            return check_password_hash(stored_secret, provided_secret)
    except (ValueError, TypeError):
        pass

    # Legacy SHA-256 hash compatibility
    legacy_hash = hashlib.sha256(provided_secret.encode()).hexdigest()
    return hmac.compare_digest(stored_secret, legacy_hash)


def is_default_admin_secret(stored_secret: str) -> bool:
    """Return True if the stored secret uses a known-default value."""
    return stored_secret in DEFAULT_ADMIN_HASHES or stored_secret == "admin"


def generate_event_id() -> str:
    """Generate a cryptographically random event ID."""
    return secrets.token_hex(16)


def generate_session_token() -> str:
    """Generate a URL-safe session token."""
    return secrets.token_urlsafe(24)


# ---------------------------------------------------------------------------
# Card UID hashing (for storage)
# ---------------------------------------------------------------------------


def hash_card_uid(card_id: str) -> str:
    """Return a one-way hash of a card UID for pseudonymous storage.

    Uses HMAC-SHA256 keyed with ``FLASK_SECRET_KEY`` so that the mapping is
    deterministic within a deployment but cannot be reversed without the key.
    """
    key = (os.getenv("FLASK_SECRET_KEY") or "change-this-secret-key").encode()
    return hmac.new(key, card_id.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Login brute-force protection
# ---------------------------------------------------------------------------


class LoginRateLimiter:
    """In-memory rate limiter for admin login attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, list] = {}

    def _prune(self):
        cutoff = time.time() - self.window_seconds
        expired = [
            ip
            for ip, attempts in self._attempts.items()
            if attempts and attempts[-1] < cutoff
        ]
        for ip in expired:
            del self._attempts[ip]

    def is_blocked(self, ip_address: str) -> bool:
        self._prune()
        attempts = [
            t
            for t in self._attempts.get(ip_address, [])
            if t >= time.time() - self.window_seconds
        ]
        self._attempts[ip_address] = attempts
        return len(attempts) >= self.max_attempts

    def record_failure(self, ip_address: str):
        self._prune()
        self._attempts.setdefault(ip_address, []).append(time.time())

    def clear(self, ip_address: str):
        self._attempts.pop(ip_address, None)


# ---------------------------------------------------------------------------
# Runtime security validation
# ---------------------------------------------------------------------------


def validate_runtime_security(
    *, db_type: str, strict: bool = False
) -> list:
    """Validate security-critical environment variables at startup.

    Returns a list of (severity, message) tuples.  Callers should decide
    whether warnings should be treated as fatal.
    """
    issues: list = []  # (severity: "error"|"warning", message)

    secret_key = (os.getenv("FLASK_SECRET_KEY") or "").strip()
    if not secret_key:
        msg = "FLASK_SECRET_KEY が未設定です。"
        issues.append(("error" if strict else "warning", msg))
    elif secret_key in INSECURE_FLASK_SECRET_KEYS or len(secret_key) < 32:
        msg = "FLASK_SECRET_KEY が既定値または短すぎる値です（32文字以上推奨）。"
        issues.append(("error" if strict else "warning", msg))

    admin_password = (os.getenv("OITERU_ADMIN_PASSWORD") or "").strip()
    if not admin_password:
        msg = "OITERU_ADMIN_PASSWORD が未設定です。"
        issues.append(("error" if strict else "warning", msg))
    elif admin_password.lower() in INSECURE_ADMIN_PASSWORDS:
        issues.append(("error", "OITERU_ADMIN_PASSWORD に既定値/弱い値は使用できません。"))
    elif len(admin_password) < 12:
        msg = "OITERU_ADMIN_PASSWORD は12文字以上を推奨します。"
        issues.append(("error" if strict else "warning", msg))

    if db_type == "mysql":
        mysql_password = (os.getenv("MYSQL_PASSWORD") or "").strip()
        if not mysql_password:
            issues.append(("error", "MYSQL_PASSWORD が未設定です。"))
        elif mysql_password in INSECURE_MYSQL_PASSWORDS:
            issues.append(("error", "MYSQL_PASSWORD に既定値/弱い値は使用できません。"))

    return issues
