"""Regression tests for the public user journey from the main screen."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

import server


@contextmanager
def _fake_connection():
    yield object()


@pytest.fixture
def public_client(monkeypatch):
    """Return an unauthenticated client with local hardware calls isolated."""
    monkeypatch.setattr(
        server,
        "detect_local_nfc_reader",
        lambda: (False, "reader unavailable for test"),
    )
    monkeypatch.setattr(server, "open_local_nfc_frontend", lambda: None)
    monkeypatch.setattr(server.db, "fetchall", lambda *_args, **_kwargs: [])
    return server.app.test_client()


@pytest.mark.parametrize("path", ["/", "/register", "/usage"])
def test_main_screen_user_pages_do_not_require_admin_login(public_client, path):
    response = public_client.get(path, follow_redirects=False)

    assert response.status_code == 200
    assert response.headers.get("Location") is None


def test_main_screen_makes_the_public_access_boundary_clear(public_client):
    response = public_client.get("/")
    page = response.get_data(as_text=True)

    assert "ログイン不要" in page
    assert 'href="/register"' in page
    assert 'href="/usage"' in page


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/local_nfc_reader", 200),
        ("/api/read_card", 404),
        ("/api/reader_status", 503),
    ],
)
def test_user_flow_support_apis_do_not_require_admin_login(
    public_client,
    path,
    expected_status,
):
    response = public_client.get(path, follow_redirects=False)

    assert response.status_code == expected_status
    assert response.headers.get("Location") is None


def test_card_registration_submission_does_not_require_admin_login(
    public_client,
    monkeypatch,
):
    executed_statements = []
    monkeypatch.setattr(server, "get_connection", _fake_connection)
    monkeypatch.setattr(
        server.db,
        "execute",
        lambda _conn, query, params=None: executed_statements.append((query, params)),
    )
    monkeypatch.setattr(server, "add_history", lambda *_args: None)

    response = public_client.post(
        "/register",
        data={"card_id": "TEST-CARD-0001"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")
    assert "INSERT INTO users" in executed_statements[0][0]


def test_usage_result_submission_does_not_require_admin_login(
    public_client,
    monkeypatch,
):
    monkeypatch.setattr(server, "get_connection", _fake_connection)
    monkeypatch.setattr(
        server.db,
        "fetchone",
        lambda *_args, **_kwargs: {
            "cardid": "TEST-CARD-0001",
            "stock": 2,
            "allow": 1,
            "entry_at": "2026-08-11 12:00",
            "total": 0,
        },
    )

    response = public_client.post(
        "/usage",
        data={"card_id": "TEST-CARD-0001"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.headers.get("Location") is None


def test_admin_routes_remain_protected_from_the_public_user_flow(public_client):
    dashboard_response = public_client.get("/admin/dashboard", follow_redirects=False)
    user_api_response = public_client.get("/api/users", follow_redirects=False)

    assert dashboard_response.status_code == 302
    assert dashboard_response.headers["Location"].endswith("/admin")
    assert user_api_response.status_code == 401
