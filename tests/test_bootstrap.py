"""Tests for the common parent bootstrap ordering."""

from __future__ import annotations

import server


def test_bootstrap_runs_migrations_before_settings(monkeypatch):
    calls = []

    monkeypatch.setattr(server, "load_environment", lambda: calls.append("environment"))
    monkeypatch.setattr(server, "init_db", lambda: calls.append("init"))
    monkeypatch.setattr(server, "ensure_admin_password", lambda: calls.append("admin"))
    monkeypatch.setattr(server, "load_settings_from_db", lambda: calls.append("settings"))
    monkeypatch.setattr(server, "start_background_services", lambda: calls.append("background"))
    monkeypatch.setattr(
        "app.auth.auth_manager.validate_runtime_security", lambda **_: []
    )
    monkeypatch.setattr(
        "app.migrations.run_all_migrations", lambda: calls.append("migrations")
    )

    server.bootstrap_parent(start_background=True)

    assert calls == ["environment", "init", "migrations", "admin", "settings", "background"]


def _bootstrap_with_strict(monkeypatch, env_value):
    """Run bootstrap_parent and return the strict flag passed to security."""
    monkeypatch.setattr(server, "load_environment", lambda: None)
    monkeypatch.setattr(server, "init_db", lambda: None)
    monkeypatch.setattr(server, "ensure_admin_password", lambda: None)
    monkeypatch.setattr(server, "load_settings_from_db", lambda: None)
    monkeypatch.setattr(server, "start_background_services", lambda: None)
    monkeypatch.setattr("app.migrations.run_all_migrations", lambda: None)
    captured = {}

    def fake_validate(db_type, strict):
        captured["strict"] = strict
        captured["db_type"] = db_type
        return []

    monkeypatch.setattr(
        "app.auth.auth_manager.validate_runtime_security", fake_validate
    )
    if env_value is None:
        monkeypatch.delenv("OITERU_STRICT_SECURITY", raising=False)
    else:
        monkeypatch.setenv("OITERU_STRICT_SECURITY", env_value)

    server.bootstrap_parent(start_background=False)
    return captured


def test_bootstrap_respects_strict_security_false_env(monkeypatch):
    captured = _bootstrap_with_strict(monkeypatch, "false")
    assert captured["strict"] is False


def test_bootstrap_defaults_strict_for_mysql(monkeypatch):
    monkeypatch.setattr(server.db, "db_type", "mysql")
    captured = _bootstrap_with_strict(monkeypatch, None)
    assert captured["strict"] is True


def test_bootstrap_allows_non_strict_for_mysql_when_env_set(monkeypatch):
    monkeypatch.setattr(server.db, "db_type", "mysql")
    captured = _bootstrap_with_strict(monkeypatch, "false")
    assert captured["strict"] is False


def test_legacy_server_settings_aliases_the_service_snapshot():
    assert server.server_settings is server.settings_service.server_settings


def test_authenticated_state_change_requires_csrf_token():
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True

    response = client.post("/api/settings", json={"usage_limit": 1})

    assert response.status_code == 400
    assert response.json["error"] == "CSRF validation failed"


def test_operations_api_state_change_requires_csrf_token():
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True
        session["admin_user_id"] = 1

    response = client.post(
        "/api/v1/admin/operations/units/1/stock-movements",
        json={
            "movement_type": "restock",
            "quantity_delta": 1,
            "reason": "test",
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "CSRF validation failed"
