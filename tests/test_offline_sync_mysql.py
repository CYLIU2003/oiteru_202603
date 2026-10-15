"""End to end: parent cache -> child standalone dispense -> sync back (MySQL)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pytest

import server
from app.api import offline as offline_api
from app.auth.auth_manager import card_uid_hmac_key, hash_card_uid
from app.models.schemas import UnitRecord
from app.services import settings_service
from tests.conftest import run_sql
from unit.offline import OfflineStore, OfflineSync

UID = "0123456789ABCDEF"
OTHER_UID = "fedcba9876543210"


def _schema(conn):
    run_sql(
        conn,
        """CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            card_id VARCHAR(255) UNIQUE NOT NULL,
            card_id_hash VARCHAR(255) DEFAULT '',
            allow TINYINT DEFAULT 1,
            entry VARCHAR(50),
            stock INT DEFAULT 2,
            today INT DEFAULT 0,
            total INT DEFAULT 0,
            last_reset_date DATE
        )""",
    )
    run_sql(
        conn,
        """CREATE TABLE units (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            stock INT DEFAULT 0,
            initial_stock INT DEFAULT 100,
            connect TINYINT DEFAULT 0,
            available TINYINT DEFAULT 1,
            last_seen DATETIME,
            ip_address VARCHAR(50)
        )""",
    )
    run_sql(
        conn,
        """CREATE TABLE dispense_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id VARCHAR(64) UNIQUE NOT NULL,
            unit_name VARCHAR(255) NOT NULL,
            card_id VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL,
            error_code VARCHAR(64),
            source VARCHAR(16) NOT NULL DEFAULT 'online',
            occurred_at DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    )
    run_sql(
        conn,
        """CREATE TABLE history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            txt TEXT NOT NULL,
            type VARCHAR(20) DEFAULT 'usage',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    )


@pytest.fixture
def parent(mysql_conn, monkeypatch):
    """A parent API whose database is the throwaway MySQL test database."""
    _schema(mysql_conn)
    today = datetime.now().strftime("%Y-%m-%d")
    for uid, allow in ((UID, 1), (OTHER_UID, 0)):
        ref = hash_card_uid(uid)
        run_sql(
            mysql_conn,
            "INSERT INTO users (card_id, card_id_hash, allow, stock, last_reset_date)"
            " VALUES (%s, %s, %s, 2, %s)",
            (ref, ref, allow, today),
        )
    run_sql(mysql_conn, "INSERT INTO units (name, password, stock) VALUES ('unit-01', 'x', 3)")
    mysql_conn.commit()

    @contextmanager
    def connection():
        try:
            yield mysql_conn
            mysql_conn.commit()
        except Exception:
            mysql_conn.rollback()
            raise

    def authenticate(_conn, unit_name, unit_password=None, unit_token=None):
        if unit_name == "unit-01" and unit_password == "unit-secret":
            return UnitRecord(id=1, name="unit-01", password="x", stock=3)
        return None

    monkeypatch.setattr(offline_api, "get_connection", connection)
    monkeypatch.setattr(offline_api, "get_authenticated_unit", authenticate)
    monkeypatch.setitem(settings_service.server_settings, "usage_limit", 2)
    monkeypatch.setitem(settings_service.server_settings, "limit_period", "day")
    monkeypatch.setitem(settings_service.server_settings, "auto_register_stock", 2)
    return server.app.test_client()


class _Response:
    """requests-style view of a Flask test response."""

    def __init__(self, response):
        self.status_code = response.status_code
        self._body = response.get_json()

    def json(self):
        return self._body


def _child(parent, tmp_path):
    def post(path, payload, timeout):
        body = {"unit_name": "unit-01", "unit_password": "unit-secret", **payload}
        return _Response(parent.post(path, json=body))

    store = OfflineStore(str(tmp_path / "offline"))
    return store, OfflineSync(store, post, log=lambda _m: None)


def test_wrong_unit_secret_gets_nothing(parent):
    response = parent.post(
        "/api/v1/units/offline-cache", json={"unit_name": "unit-01", "unit_password": "bad"}
    )
    assert response.status_code == 401
    assert "card_key" not in response.get_data(as_text=True)


def test_standalone_dispense_is_recorded_once_after_the_parent_returns(parent, mysql_conn, tmp_path):
    store, sync = _child(parent, tmp_path)

    # 1. Parent online: the child receives the allowance list.
    assert sync.refresh_cache(force=True)
    cache = store.load_cache()
    assert list(cache["cards"]) == [hash_card_uid(UID)]  # the denied user is absent

    # 2. Parent down: the child decides alone and queues the event.
    assert store.authorize(OTHER_UID).reason == "CARD_NOT_ALLOWED_OFFLINE"
    decision = store.authorize(UID.lower())
    assert decision.allowed
    store.record_dispense(decision.card_ref, success=True)
    assert store.authorize(UID).reason == "OFFLINE_LIMIT_REACHED"

    # 3. Parent back: the queue is sent and the parent's counters follow.
    sent = store.pending()
    assert sync.flush() == 1
    assert store.pending() == []

    user = run_sql(mysql_conn, "SELECT stock, total FROM users WHERE card_id = %s", (hash_card_uid(UID),))[0]
    unit = run_sql(mysql_conn, "SELECT stock FROM units WHERE name = 'unit-01'")[0]
    event = run_sql(mysql_conn, "SELECT status, source, error_code FROM dispense_events")[0]
    assert (user["stock"], user["total"], unit["stock"]) == (1, 1, 2)
    assert event == {"status": "recorded", "source": "offline", "error_code": None}

    # 4. A retry (lost response) must not count the same dispense twice.
    response = parent.post(
        "/api/v1/units/offline-events",
        json={"unit_name": "unit-01", "unit_password": "unit-secret", "events": sent},
    )
    assert response.get_json()["results"][0]["result"] == "duplicate"
    assert run_sql(mysql_conn, "SELECT COUNT(*) AS n FROM dispense_events")[0]["n"] == 1
    assert run_sql(mysql_conn, "SELECT stock FROM units WHERE name = 'unit-01'")[0]["stock"] == 2

    # 5. With the queue empty the child accepts a fresh cache again.
    assert sync.refresh_cache(force=True)


def test_dispense_beyond_the_allowance_is_recorded_and_flagged(parent, mysql_conn, tmp_path):
    run_sql(mysql_conn, "UPDATE users SET stock = 0 WHERE card_id = %s", (hash_card_uid(UID),))
    mysql_conn.commit()
    store, sync = _child(parent, tmp_path)
    store.save_cache(
        {
            "enabled": True,
            "issued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "max_age_hours": 72,
            "per_card_limit": 1,
            "max_events": 10,
            "unit_stock": 3,
            "card_key": card_uid_hmac_key().decode(),
            "cards": {hash_card_uid(UID): 1},
        }
    )
    decision = store.authorize(UID)
    store.record_dispense(decision.card_ref, success=True)

    sync.flush()

    event = run_sql(mysql_conn, "SELECT status, error_code FROM dispense_events")[0]
    user = run_sql(mysql_conn, "SELECT stock, total FROM users WHERE card_id = %s", (hash_card_uid(UID),))[0]
    assert event == {"status": "recorded", "error_code": "OFFLINE_LIMIT_OVERRUN"}
    assert (user["stock"], user["total"]) == (0, 1)


def test_malformed_events_are_rejected_not_retried(parent):
    response = parent.post(
        "/api/v1/units/offline-events",
        json={
            "unit_name": "unit-01",
            "unit_password": "unit-secret",
            "events": [{"event_id": "x", "card_ref": "y", "occurred_at": "z", "success": True}],
        },
    )
    assert response.get_json()["results"] == [
        {"event_id": "x", "result": "rejected", "reason": "INVALID_EVENT_ID"}
    ]
