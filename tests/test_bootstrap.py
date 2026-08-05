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


def test_legacy_server_settings_aliases_the_service_snapshot():
    assert server.server_settings is server.settings_service.server_settings


def test_authenticated_state_change_requires_csrf_token():
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True

    response = client.post("/api/settings", json={"usage_limit": 1})

    assert response.status_code == 400
    assert response.json["error"] == "CSRF validation failed"
