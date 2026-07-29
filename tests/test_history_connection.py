"""Regression tests for HistoryRepository transaction usage."""

from __future__ import annotations

from contextlib import contextmanager

from flask import Flask

from app.api import units as unit_api
from app.models.enums import DispenseStatus
from app.models.schemas import DispenseEventRecord, UnitRecord, UserRecord
from app.services import dispense_service, settings_service, user_service


def test_authorize_dispense_passes_connection_to_history(monkeypatch):
    connection = object()
    history_calls = []

    monkeypatch.setattr(dispense_service._event_repo, "insert", lambda *args: 1)
    monkeypatch.setattr(dispense_service._event_repo, "update_status", lambda *args: 1)
    monkeypatch.setattr(
        dispense_service._history_repo,
        "insert",
        lambda conn, message, hist_type="usage": history_calls.append(
            (conn, message, hist_type)
        ),
    )
    unit = UnitRecord(id=1, name="unit-01", password="secret", stock=0)

    result = dispense_service.authorize_dispense(
        connection, "TEST-CARD-0001", unit.name, unit
    )

    assert not result.authorized
    assert history_calls == [
        (connection, "[unit-01] 在庫不足のため利用不可 (カードID: TEST-CARD-0001)", "usage")
    ]


def test_failed_dispense_passes_connection_to_history(monkeypatch):
    connection = object()
    history_calls = []
    event = DispenseEventRecord(
        id=1,
        event_id="event-0001",
        unit_name="unit-01",
        card_id="TEST-CARD-0001",
        status=DispenseStatus.AUTHORIZED,
    )

    monkeypatch.setattr(
        dispense_service._event_repo, "find_by_event_id", lambda *args: event
    )
    monkeypatch.setattr(dispense_service._event_repo, "update_status", lambda *args: 1)
    monkeypatch.setattr(
        dispense_service._history_repo,
        "insert",
        lambda conn, message, hist_type="usage": history_calls.append(
            (conn, message, hist_type)
        ),
    )
    unit = UnitRecord(id=1, name="unit-01", password="secret", stock=1)

    result = dispense_service.record_dispense_result(
        connection, event.event_id, unit.name, unit, dispense_success=False
    )

    assert not result.success
    assert history_calls[0][0] is connection
    assert history_calls[0][2] == "usage"


def test_period_reset_passes_connection_to_history(monkeypatch):
    connection = object()
    history_calls = []
    user = UserRecord(
        id=1,
        card_id="TEST-CARD-0001",
        stock=0,
        last_reset_date="2000-01-01",
    )

    monkeypatch.setitem(settings_service.server_settings, "auto_register_stock", 2)
    monkeypatch.setattr(user_service._user_repo, "update_stock_and_reset_date", lambda *args: 1)

    class RecordingHistoryRepository:
        def insert(self, conn, message, hist_type="usage"):
            history_calls.append((conn, message, hist_type))

    user_service.check_and_reset_user_stock(
        connection, user, "day", RecordingHistoryRepository()
    )

    assert history_calls[0][0] is connection
    assert history_calls[0][2] == "system"


def test_unit_log_endpoint_records_history_in_authenticated_connection(monkeypatch):
    connection = object()
    history_calls = []

    @contextmanager
    def fake_connection():
        yield connection

    def fake_history_insert(self, received_connection, message, hist_type="usage"):
        history_calls.append((received_connection, message, hist_type))
        return 1

    monkeypatch.setattr(unit_api, "get_connection", fake_connection)
    monkeypatch.setattr(unit_api, "get_authenticated_unit", lambda *args: object())
    monkeypatch.setattr(
        "app.repositories.history_repository.HistoryRepository.insert",
        fake_history_insert,
    )
    unit_api.unit_logs.clear()

    app = Flask(__name__)
    app.register_blueprint(unit_api.unit_bp)
    response = app.test_client().post(
        "/api/log",
        json={"unit_name": "unit-01", "unit_token": "valid", "message": "ready"},
    )

    assert response.status_code == 200
    assert history_calls == [(connection, "[unit-01] ready", "usage")]


def test_unit_config_endpoint_rejects_gpio_conflicts_before_database_access():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(unit_api.unit_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True

    response = client.post(
        "/api/unit/unit-01/config",
        json={
            "MOTOR_TYPE": "STEPPER",
            "CONTROL_METHOD": "RASPI_DIRECT",
            "USE_SENSOR": True,
            "GREEN_LED_PIN": 5,
            "RED_LED_PIN": 6,
            "SENSOR_GPIO_PIN": 13,
            "STEPPER_PINS": [21, 5, 6, 13],
        },
    )

    assert response.status_code == 400
    assert response.json["error"] == "Invalid GPIO configuration"
