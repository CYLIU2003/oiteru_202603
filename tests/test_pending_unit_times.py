"""Pending child units must work with the datetime values MySQL returns.

PyMySQL returns DATETIME columns as ``datetime`` objects. Code written for the
old SQLite strings treated them as unparsable, so a device that had just
asked to join showed "9999秒前" and the v1 approval API rejected it as expired.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from flask import Flask

import server
from app import state
from app.api import units as units_api


@contextmanager
def _fake_connection():
    yield object()


def _pending(seen: datetime) -> dict:
    return {
        "unit_name": "unit-01",
        "ip_address": "192.0.2.10",
        "first_seen": seen,
        "last_seen": seen,
        "heartbeat_count": 1,
        "credential_conflict": 0,
        "credential_conflict_at": None,
        "password_hash": "hash",
    }


def test_as_datetime_accepts_mysql_and_legacy_values():
    moment = datetime(2026, 10, 17, 13, 33, 27)
    assert state.as_datetime(moment) is moment
    assert state.as_datetime("2026-10-17 13:33:27") == moment
    assert state.as_datetime("not a time") is None
    assert state.as_datetime(None) is None
    assert state.format_db_time(moment) == "2026-10-17 13:33:27"


def test_recent_pending_unit_is_not_expired():
    assert units_api._pending_unit_expired(_pending(datetime.now())) is False
    assert units_api._pending_unit_expired(_pending(datetime.now() - timedelta(days=2))) is True
    assert units_api._pending_unit_expired({"first_seen": None}) is True


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setattr(server, "get_connection", _fake_connection)
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True
    return client


def test_unregistered_list_reports_real_seconds_and_local_time(admin_client, monkeypatch):
    seen = datetime.now() - timedelta(seconds=30)
    monkeypatch.setattr(state, "get_pending_units", lambda _conn: [_pending(seen)])

    unit = admin_client.get("/api/unregistered_units").json["units"][0]

    assert 25 <= unit["seconds_ago"] < 120
    assert unit["first_seen"] == seen.strftime("%Y-%m-%d %H:%M:%S")
    assert "GMT" not in unit["last_seen"]


def test_v1_pending_list_and_approval_accept_mysql_datetimes(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(units_api.unit_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True

    pending = _pending(datetime.now())
    inserted = {}
    monkeypatch.setattr(units_api, "get_connection", _fake_connection)
    monkeypatch.setattr(state, "get_pending_units", lambda _conn: [pending])
    monkeypatch.setattr(state, "get_pending_unit", lambda _conn, _name: pending)
    monkeypatch.setattr(state, "delete_pending_unit", lambda _conn, _name: None)
    monkeypatch.setattr(state, "record_device_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(units_api._unit_repo, "find_by_name", lambda _conn, _name: None)
    monkeypatch.setattr(
        units_api._unit_repo, "insert", lambda _conn, **kwargs: inserted.update(kwargs)
    )
    from app.repositories import history_repository

    monkeypatch.setattr(
        history_repository.HistoryRepository, "insert", lambda *_args, **_kwargs: None
    )

    device = client.get("/api/v1/admin/pending-devices").json["devices"][0]
    assert device["expired"] is False
    assert device["first_seen"] == pending["first_seen"].strftime("%Y-%m-%d %H:%M:%S")

    response = client.post("/api/v1/admin/pending-devices/unit-01/approve", json={"stock": 5})
    assert response.status_code == 201, response.json
    assert inserted["name"] == "unit-01"
    assert inserted["stock"] == 5
