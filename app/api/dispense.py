"""Dispense API endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.logger import get_logger
from app.models.enums import DispenseErrorCode
from app.services.dispense_service import (
    authorize_dispense,
    record_dispense_result,
)
from app.repositories.unit_repository import UnitRepository
from app.auth.auth_manager import verify_secret
from app.auth.unit_auth import validate_unit_token
from db_adapter import get_connection

logger = get_logger(__name__)

dispense_bp = Blueprint("dispense", __name__)
_unit_repo = UnitRepository()


def get_authenticated_unit_local(conn, unit_name, unit_password=None, unit_token=None):
    unit = _unit_repo.find_by_name(conn, unit_name)
    if not unit:
        return None
    if unit_token and validate_unit_token(unit_name, unit_token):
        return unit
    if unit_password and verify_secret(unit.password, unit_password):
        return unit
    return None


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


@dispense_bp.route("/api/record_usage", methods=["POST"])
def api_record_usage():
    data = request.json or {}
    card_id = data.get("card_id")
    unit_name = data.get("unit_name")
    unit_password = data.get("unit_password")
    unit_token = data.get("unit_token")

    if not all([card_id, unit_name]) or not (unit_password or unit_token):
        return jsonify(
            {"error": "Card ID, Unit Name and unit credentials are required"}
        ), 400

    try:
        with get_connection() as conn:
            unit = get_authenticated_unit_local(conn, unit_name, unit_password, unit_token)
            if not unit:
                return jsonify(
                    {"error": "Invalid unit credentials", "event_id": None}
                ), 401

            result = authorize_dispense(conn, card_id, unit_name, unit)

            if result.authorized:
                return jsonify({
                    "success": True,
                    "authorized": True,
                    "message": result.message,
                    "event_id": result.event_id,
                })

            return jsonify({
                "error": result.error,
                "auto_register": result.auto_register,
                "event_id": result.event_id,
                "message": result.message,
                "usage_count": result.usage_count,
                "usage_limit": result.usage_limit,
                "period": result.period,
            }), result.http_status

    except Exception as exc:
        logger.error("Dispense auth error: %s", exc, exc_info=True)
        return jsonify({"error": f"Database error: {exc}"}), 500


@dispense_bp.route("/api/dispense_result", methods=["POST"])
def api_dispense_result():
    data = request.json or {}
    event_id = data.get("event_id")
    unit_name = data.get("unit_name")
    unit_password = data.get("unit_password")
    unit_token = data.get("unit_token")
    dispense_success = _parse_bool(data.get("success"))
    error_code = data.get("error_code")

    if not all([event_id, unit_name]) or not (unit_password or unit_token):
        return jsonify(
            {"error": "Event ID, Unit Name and unit credentials are required"}
        ), 400

    try:
        with get_connection() as conn:
            unit = get_authenticated_unit_local(conn, unit_name, unit_password, unit_token)
            if not unit:
                return jsonify({"error": "Invalid unit credentials"}), 401

            result = record_dispense_result(
                conn, event_id, unit_name, unit, dispense_success, error_code
            )

            return jsonify({
                "success": result.success,
                "recorded": result.recorded,
                "idempotent": result.idempotent,
                "event_id": result.event_id,
                "error_code": result.error_code,
                "error": result.error,
                "user_stock": result.user_stock,
                "unit_stock": result.unit_stock,
            }), result.http_status

    except Exception as exc:
        logger.error("Dispense result error: %s", exc, exc_info=True)
        return jsonify({"error": f"Database error: {exc}"}), 500
