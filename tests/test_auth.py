"""Tests for auth module."""

import os

from app.auth.auth_manager import (
    hash_secret,
    verify_secret,
    is_default_admin_secret,
    hash_card_uid,
    generate_event_id,
    generate_session_token,
    LoginRateLimiter,
    validate_runtime_security,
    INSECURE_ADMIN_PASSWORDS,
    INSECURE_FLASK_SECRET_KEYS,
)


class TestHashSecret:
    def test_hash_is_not_plaintext(self):
        result = hash_secret("my-secret-password")
        assert result != "my-secret-password"
        assert result.startswith("pbkdf2:") or result.startswith("scrypt:")

    def test_verify_correct_password(self):
        hashed = hash_secret("correct-horse-battery-staple")
        assert verify_secret(hashed, "correct-horse-battery-staple")

    def test_verify_wrong_password(self):
        hashed = hash_secret("correct-horse-battery-staple")
        assert not verify_secret(hashed, "wrong-password")

    def test_verify_empty_inputs(self):
        assert not verify_secret("", "anything")
        assert not verify_secret("anything", "")
        assert not verify_secret("", "")

    def test_legacy_sha256_compat(self):
        import hashlib
        legacy_hash = hashlib.sha256("legacy-password".encode()).hexdigest()
        assert verify_secret(legacy_hash, "legacy-password")


class TestIsDefaultAdminSecret:
    def test_default_hash_is_detected(self):
        import hashlib
        default_hash = hashlib.sha256("admin".encode()).hexdigest()
        assert is_default_admin_secret(default_hash)

    def test_custom_hash_is_not_default(self):
        assert not is_default_admin_secret("pbkdf2:sha256:260000$...")

    def test_plain_admin_is_default(self):
        assert is_default_admin_secret("admin")


class TestHashCardUid:
    def test_hash_is_deterministic(self):
        h1 = hash_card_uid("test-card-123")
        h2 = hash_card_uid("test-card-123")
        assert h1 == h2

    def test_hash_is_different_for_different_inputs(self):
        h1 = hash_card_uid("card-aaa")
        h2 = hash_card_uid("card-bbb")
        assert h1 != h2

    def test_hash_length(self):
        assert len(hash_card_uid("test")) == 64  # SHA-256 hex


class TestGenerateEventId:
    def test_event_id_length(self):
        eid = generate_event_id()
        assert len(eid) == 32  # token_hex(16)

    def test_event_ids_are_unique(self):
        ids = {generate_event_id() for _ in range(100)}
        assert len(ids) == 100


class TestGenerateSessionToken:
    def test_token_is_urlsafe(self):
        token = generate_session_token()
        assert len(token) >= 32
        assert "/" not in token
        assert "+" not in token


class TestLoginRateLimiter:
    def test_not_blocked_initially(self):
        limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)
        assert not limiter.is_blocked("192.168.1.1")

    def test_blocked_after_max_attempts(self):
        limiter = LoginRateLimiter(max_attempts=3, window_seconds=900)
        limiter.record_failure("10.0.0.1")
        limiter.record_failure("10.0.0.1")
        limiter.record_failure("10.0.0.1")
        assert limiter.is_blocked("10.0.0.1")

    def test_clear_resets(self):
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=900)
        limiter.record_failure("10.0.0.2")
        limiter.record_failure("10.0.0.2")
        assert limiter.is_blocked("10.0.0.2")
        limiter.clear("10.0.0.2")
        assert not limiter.is_blocked("10.0.0.2")


class TestValidateRuntimeSecurity:
    def test_empty_flask_secret_key_warns(self):
        old = os.environ.pop("FLASK_SECRET_KEY", None)
        try:
            issues = validate_runtime_security(db_type="mysql", strict=False)
            assert any("FLASK_SECRET_KEY" in msg for _, msg in issues)
        finally:
            if old:
                os.environ["FLASK_SECRET_KEY"] = old

    def test_weak_admin_password_errors_on_strict(self):
        os.environ["FLASK_SECRET_KEY"] = "a" * 32
        os.environ["OITERU_ADMIN_PASSWORD"] = "admin"
        try:
            issues = validate_runtime_security(db_type="mysql", strict=True)
            errors = [msg for sev, msg in issues if sev == "error"]
            assert any("OITERU_ADMIN_PASSWORD" in msg for msg in errors)
        finally:
            os.environ.pop("OITERU_ADMIN_PASSWORD", None)
