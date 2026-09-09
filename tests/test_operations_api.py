"""Tests for operations API authorization and response contracts."""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from flask import Flask

from app.api import operations as operations_api
from app.models.schemas import StockMovementRecord


def _make_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(operations_api.operations_bp)
    return app


def test_operations_summary_requires_admin_login():
    response = _make_app().test_client().get("/api/v1/admin/operations/summary")

    assert response.status_code == 401
    assert response.json["success"] is False


def test_operations_api_requires_authenticated_admin_identity():
    client = _make_app().test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True

    response = client.post(
        "/api/v1/admin/operations/units/3/stock-movements",
        json={
            "movement_type": "restock",
            "quantity_delta": 3,
            "reason": "scheduled refill",
        },
    )

    assert response.status_code == 403
    assert response.json["code"] == "ADMIN_IDENTITY_REQUIRED"


def test_stock_movement_api_returns_created_record_without_unit_password(monkeypatch):
    @contextmanager
    def fake_connection():
        yield object()

    def fake_record_stock_movement(_conn, **kwargs):
        assert kwargs["unit_id"] == 3
        assert kwargs["admin_user_id"] == 7
        return StockMovementRecord(
            id=11,
            unit_id=3,
            unit_name="unit-03",
            movement_type="restock",
            quantity_delta=4,
            stock_before=2,
            stock_after=6,
            reason="scheduled refill",
            admin_user_id=7,
            created_at="2026-08-11 10:00:00",
            updated_at="2026-08-11 10:00:00",
        )

    monkeypatch.setattr(operations_api, "get_connection", fake_connection)
    monkeypatch.setattr(
        operations_api.operations_service,
        "record_stock_movement",
        fake_record_stock_movement,
    )
    client = _make_app().test_client()
    with client.session_transaction() as session:
        session["admin_logged_in"] = True
        session["admin_user_id"] = 7

    response = client.post(
        "/api/v1/admin/operations/units/3/stock-movements",
        json={
            "movement_type": "restock",
            "quantity_delta": 4,
            "reason": "scheduled refill",
        },
    )

    assert response.status_code == 201
    assert response.json["movement"]["stock_after"] == 6
    assert "password" not in response.json["movement"]


@pytest.mark.parametrize("movement_type", ["restock", "disposal"])
def test_stock_movement_form_rejects_negative_quantity(movement_type):
    with pytest.raises(operations_api.operations_service.OperationsValidationError):
        operations_api._movement_delta_from_form(movement_type, -1)
