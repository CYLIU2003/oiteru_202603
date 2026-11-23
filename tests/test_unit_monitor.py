"""Focused DB-free unit tests for child-unit monitoring and heartbeat evaluation."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from typing import Any

from flask import Flask
import pytest

from app import state
from app.api import units as units_api
from app.models.schemas import (
    MaintenanceTicketRecord,
    SettingsRecord,
    UnitRecord,
    _bool_or_default,
    _int_or_default,
)
from app.services import unit_service
from app.services.unit_service import (
    _optional_bool,
    build_unit_monitor_item,
    evaluate_unit_heartbeat,
    get_unit_monitor_dashboard,
    heartbeat_update,
)


def _make_unit_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "test-unit-monitor-secret"
    app.register_blueprint(units_api.unit_bp)
    return app


def _collect_keys(obj: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys.update(_collect_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_collect_keys(item))
    return keys


class TestEvaluateUnitHeartbeat:
    def test_fresh_heartbeat_with_connect_one_is_online(self):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        seen = ref - timedelta(seconds=20)

        result = evaluate_unit_heartbeat(
            last_seen=seen,
            connect=1,
            reference_time=ref,
            timeout_seconds=60,
        )

        assert result["connection_status"] == "online"
        assert result["heartbeat_fresh"] is True
        assert result["heartbeat_overdue"] is False
        assert result["seconds_ago"] == 20.0
        assert result["last_seen"] == "2026-11-23 11:59:40"
        assert result["reported_connect_flag"] == 1
        assert result["status_reason"] is None

    def test_overdue_heartbeat_is_offline(self):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        seen = (ref - timedelta(seconds=61)).strftime("%Y-%m-%d %H:%M:%S")

        result = evaluate_unit_heartbeat(
            last_seen=seen,
            connect=1,
            reference_time=ref,
            timeout_seconds=60,
        )

        assert result["connection_status"] == "offline"
        assert result["heartbeat_fresh"] is False
        assert result["heartbeat_overdue"] is True
        assert result["seconds_ago"] == 61.0
        assert result["status_reason"] is not None
        assert "60" in result["status_reason"]

    @pytest.mark.parametrize("missing_value", [None, "", "   ", "not-a-timestamp"])
    def test_missing_or_invalid_timestamp_is_unknown(self, missing_value):
        ref = datetime(2026, 11, 23, 12, 0, 0)

        result = evaluate_unit_heartbeat(
            last_seen=missing_value,
            connect=1,
            reference_time=ref,
            timeout_seconds=60,
        )

        assert result["connection_status"] == "unknown"
        assert result["heartbeat_fresh"] is False
        assert result["heartbeat_overdue"] is True
        assert result["last_seen"] is None
        assert result["seconds_ago"] is None
        assert result["status_reason"] is not None

    def test_future_timestamp_beyond_tolerance_is_unknown(self):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        future_seen = ref + timedelta(seconds=10)

        result = evaluate_unit_heartbeat(
            last_seen=future_seen,
            connect=1,
            reference_time=ref,
            timeout_seconds=60,
        )

        assert result["connection_status"] == "unknown"
        assert result["heartbeat_fresh"] is False
        assert result["heartbeat_overdue"] is False
        assert result["seconds_ago"] is None
        assert result["last_seen"] == "2026-11-23 12:00:10"
        assert "未来" in (result["status_reason"] or "")

    def test_recent_timestamp_with_connect_zero_inconsistency_is_unknown(self):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        seen = ref - timedelta(seconds=15)

        result = evaluate_unit_heartbeat(
            last_seen=seen,
            connect=0,
            reference_time=ref,
            timeout_seconds=60,
        )

        assert result["connection_status"] == "unknown"
        assert result["heartbeat_fresh"] is False
        assert result["heartbeat_overdue"] is False
        assert result["reported_connect_flag"] == 0
        assert "不整合" in (result["status_reason"] or "")


class TestBuildUnitMonitorItemHeartbeatInterval:
    def test_heartbeat_interval_over_60s_uses_double_threshold_without_false_offline(self):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        unit = UnitRecord(
            id=10,
            name="unit-long-hb",
            password="hidden-password",
            stock=15,
            initial_stock=20,
            connect=1,
            available=1,
            last_seen=(ref - timedelta(seconds=110)).strftime("%Y-%m-%d %H:%M:%S"),
            ip_address="192.0.2.55",
        )
        snapshot = {
            "unit_name": "unit-long-hb",
            "config": {
                "HEARTBEAT_INTERVAL": 90,
                "MOTOR_TYPE": "STEPPER",
                "CONTROL_METHOD": "RASPI_DIRECT",
                "USE_SENSOR": True,
            },
            "last_updated": (ref - timedelta(seconds=110)).strftime("%Y-%m-%d %H:%M:%S"),
        }

        item = build_unit_monitor_item(
            unit,
            reference_time=ref,
            timeout_seconds=60,
            config_snapshot=snapshot,
        )

        assert item.heartbeat_interval_seconds == 90
        assert item.heartbeat_timeout_seconds == 180
        assert item.connection_status == "online"
        assert item.heartbeat_fresh is True
        assert item.heartbeat_overdue is False
        assert item.monitor_status == "READY"
        assert item.can_dispense is True
        assert item.config_stale is False

        stale_unit = UnitRecord(
            id=10,
            name="unit-long-hb",
            stock=15,
            initial_stock=20,
            connect=1,
            available=1,
            last_seen=(ref - timedelta(seconds=185)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        overdue_item = build_unit_monitor_item(
            stale_unit,
            reference_time=ref,
            timeout_seconds=60,
            config_snapshot=snapshot,
        )

        assert overdue_item.heartbeat_timeout_seconds == 180
        assert overdue_item.connection_status == "offline"
        assert overdue_item.heartbeat_overdue is True
        assert overdue_item.monitor_status == "OFFLINE"


class TestUnitRecordFromRowAndFalseStringParsing:
    def test_unit_record_from_row_preserves_zero_and_handles_null_safely(self):
        zero_row = {
            "id": 0,
            "name": "unit-zero",
            "password": "",
            "stock": 0,
            "initial_stock": 0,
            "connect": 0,
            "available": 0,
            "last_seen": None,
            "ip_address": "   ",
        }
        zero_record = UnitRecord.from_row(zero_row)

        assert zero_record.id == 0
        assert zero_record.name == "unit-zero"
        assert zero_record.stock == 0
        assert zero_record.initial_stock == 0
        assert zero_record.connect == 0
        assert zero_record.available == 0
        assert zero_record.last_seen is None
        assert zero_record.ip_address is None

        null_row = {
            "id": None,
            "name": None,
            "password": None,
            "stock": None,
            "initial_stock": None,
            "connect": None,
            "available": None,
            "last_seen": None,
            "ip_address": None,
        }
        null_record = UnitRecord.from_row(null_row)

        assert null_record.id == 0
        assert null_record.name == ""
        assert null_record.password == ""
        assert null_record.stock == 0
        assert null_record.initial_stock == 100
        assert null_record.connect == 0
        assert null_record.available == 1
        assert null_record.last_seen is None
        assert null_record.ip_address is None

    @pytest.mark.parametrize("false_str", ["false", "False", " FALSE ", "0", "no", "n", "off"])
    def test_string_false_is_not_treated_as_true_across_parsers(self, false_str):
        assert _bool_or_default(false_str, default=True) is False
        assert _optional_bool(false_str) is False
        assert units_api._parse_bool(false_str) is False

        if false_str.strip().lower() in {"false", "no", "n", "off", "0"}:
            assert _int_or_default(false_str, default=1) == 0

        record = UnitRecord.from_row(
            {
                "id": 5,
                "name": "unit-str-false",
                "stock": 3,
                "initial_stock": 10,
                "connect": false_str,
                "available": false_str,
            }
        )
        assert record.connect == 0
        assert record.available == 0

        settings = SettingsRecord.from_row(
            {"id": 1, "auto_register_mode": false_str}
        )
        assert settings.auto_register_mode is False

        ref = datetime(2026, 11, 23, 12, 0, 0)
        hb = evaluate_unit_heartbeat(
            last_seen=ref - timedelta(seconds=10),
            connect=false_str,
            reference_time=ref,
        )
        assert hb["reported_connect_flag"] == 0
        assert hb["connection_status"] == "unknown"

        item = build_unit_monitor_item(
            record,
            reference_time=ref,
            config_snapshot={"config": {"USE_SENSOR": false_str}},
        )
        assert item.available is False
        assert item.available_int == 0
        assert item.monitor_status == "DISABLED"
        assert item.can_dispense is False
        assert item.use_sensor is False

        normalized = units_api.normalize_unit_config(
            {
                "MOTOR_REVERSE": false_str,
                "USE_SENSOR": false_str,
                "SENSOR_CHECK_PRE": false_str,
                "SENSOR_CHECK_POST": false_str,
            }
        )
        assert normalized["MOTOR_REVERSE"] is False
        assert normalized["USE_SENSOR"] is False
        assert normalized["SENSOR_CHECK_PRE"] is False
        assert normalized["SENSOR_CHECK_POST"] is False

    def test_heartbeat_update_config_ack_applied_string_false_records_failed(self, monkeypatch):
        fake_unit = UnitRecord(
            id=1,
            name="unit-01",
            password="hashed-password",
            stock=4,
            initial_stock=10,
            connect=1,
            available=1,
        )
        ack_calls: list[tuple[Any, ...]] = []
        status_calls: list[tuple[Any, ...]] = []

        monkeypatch.setattr(unit_service._unit_repo, "find_by_name", lambda _c, _n: fake_unit)
        monkeypatch.setattr(unit_service._unit_repo, "update_heartbeat", lambda *_a: None)
        monkeypatch.setattr(state, "get_config_update_for_delivery", lambda *_a: None)

        def fake_ack(conn, unit_name, update_id, version, applied, error):
            ack_calls.append((unit_name, update_id, version, applied, error))
            return True

        monkeypatch.setattr(state, "acknowledge_config_update", fake_ack)
        monkeypatch.setattr(
            state,
            "record_device_status",
            lambda _c, u_name, status, detail=None: status_calls.append((u_name, status, detail)),
        )

        heartbeat_update(
            object(),
            "unit-01",
            "192.0.2.10",
            config=None,
            config_ack={
                "config_update_id": "upd-123",
                "config_version": 3,
                "applied": "false",
                "error": "GPIO conflict",
            },
        )

        assert len(ack_calls) == 1
        assert ack_calls[0][3] is False
        assert status_calls == [("unit-01", "config_failed", None)]


class TestAdminMonitorApiSecurity:
    def test_unauthenticated_monitor_api_returns_401_without_touching_db(self, monkeypatch):
        monkeypatch.setattr(
            units_api,
            "get_connection",
            lambda: pytest.fail("get_connection must not be called when unauthenticated"),
        )
        monkeypatch.setattr(
            units_api,
            "get_unit_monitor_dashboard",
            lambda *_a, **_kw: pytest.fail(
                "get_unit_monitor_dashboard must not be called when unauthenticated"
            ),
        )

        client = _make_unit_app().test_client()
        response = client.get("/api/v1/admin/units/monitor")

        assert response.status_code == 401
        assert response.json["success"] is False
        assert response.json["code"] == "UNAUTHORIZED"

    def test_monitor_payload_excludes_passwords_hashes_and_tokens(self, monkeypatch):
        ref = datetime(2026, 11, 23, 12, 0, 0)
        secret_unit_pw = "pbkdf2:sha256:600000$unit-secret-password-value"
        secret_pending_hash = "pbkdf2:sha256:600000$pending-secret-hash-value"
        secret_token_val = "secret-session-token-value"

        class FakeOperationsRepo:
            def list_units(self, _conn):
                return [
                    UnitRecord(
                        id=1,
                        name="unit-alpha",
                        password=secret_unit_pw,
                        stock=5,
                        initial_stock=20,
                        connect=1,
                        available=1,
                        last_seen="2026-11-23 11:59:45",
                        ip_address="192.0.2.11",
                    )
                ]

            def list_active_tickets(self, _conn):
                return [
                    MaintenanceTicketRecord(
                        id=101,
                        unit_id=1,
                        category="jam",
                        status="in_progress",
                        source="admin",
                        description="出口詰まり確認",
                        created_at="2026-11-23 11:30:00",
                        unit_name="unit-alpha",
                    )
                ]

            def count_active_tickets_by_unit(self, _conn):
                return {1: 1}

        monkeypatch.setattr(unit_service, "_operations_repo", FakeOperationsRepo())
        monkeypatch.setattr(
            state,
            "list_unit_config_snapshots",
            lambda _conn, unit_names=None: {
                "unit-alpha": {
                    "unit_name": "unit-alpha",
                    "config": {
                        "HEARTBEAT_INTERVAL": 30,
                        "MOTOR_TYPE": "STEPPER",
                        "CONTROL_METHOD": "RASPI_DIRECT",
                        "USE_SENSOR": True,
                    },
                    "ip_address": "192.0.2.11",
                    "last_updated": "2026-11-23 11:59:45",
                }
            },
        )
        monkeypatch.setattr(
            state,
            "list_latest_config_updates",
            lambda _conn, unit_names=None: {
                "unit-alpha": {
                    "unit_name": "unit-alpha",
                    "config_version": 2,
                    "status": "applied",
                    "created_at": "2026-11-23 11:00:00",
                    "sent_at": "2026-11-23 11:00:10",
                    "acked_at": "2026-11-23 11:00:20",
                    "error": None,
                }
            },
        )
        monkeypatch.setattr(
            state,
            "list_recent_device_status_logs",
            lambda _conn, per_unit_limit=5, unit_names=None: {
                "unit-alpha": [
                    {
                        "status": "online",
                        "detail": None,
                        "created_at": "2026-11-23 11:59:45",
                    }
                ]
            },
        )
        monkeypatch.setattr(
            state,
            "get_pending_units",
            lambda _conn, unit_names=None: [
                {
                    "id": 9,
                    "unit_name": "unit-pending-01",
                    "password_hash": secret_pending_hash,
                    "password": secret_pending_hash,
                    "unit_token": secret_token_val,
                    "token_hash": secret_token_val,
                    "ip_address": "192.0.2.99",
                    "first_seen": "2026-11-23 11:58:00",
                    "last_seen": "2026-11-23 11:59:50",
                    "heartbeat_count": 3,
                    "credential_conflict": "false",
                    "credential_conflict_at": None,
                }
            ],
        )

        @contextmanager
        def fake_connection():
            yield object()

        monkeypatch.setattr(units_api, "get_connection", fake_connection)
        monkeypatch.setattr(
            units_api,
            "get_unit_monitor_dashboard",
            lambda conn: get_unit_monitor_dashboard(conn, now=ref),
        )

        client = _make_unit_app().test_client()
        with client.session_transaction() as sess:
            sess["admin_logged_in"] = True

        response = client.get("/api/v1/admin/units/monitor")

        assert response.status_code == 200
        assert response.headers.get("Cache-Control") == "no-store"
        payload = response.json
        assert payload["success"] is True
        assert payload["summary"]["total_units"] == 1
        assert payload["summary"]["online_count"] == 1
        assert payload["summary"]["pending_unit_count"] == 1
        assert payload["pending_units"][0]["credential_conflict"] is False

        forbidden_keys = {
            "password",
            "password_hash",
            "unit_password",
            "unit_token",
            "unit_api_token",
            "token_hash",
        }
        all_keys = _collect_keys(payload)
        assert forbidden_keys.isdisjoint(all_keys)

        serialized = json.dumps(payload, ensure_ascii=False)
        assert secret_unit_pw not in serialized
        assert secret_pending_hash not in serialized
        assert secret_token_val not in serialized
