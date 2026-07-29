"""Unit heartbeat, config, log, and command API endpoints."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Dict

from flask import Blueprint, jsonify, request, session

from app import state
from app.auth.auth_manager import hash_secret, verify_secret
from app.auth.unit_auth import issue_unit_session_token, validate_unit_token
from app.logger import get_logger
from app.repositories.unit_repository import UnitRepository
from app.services.unit_service import heartbeat_update
from db_adapter import get_connection
from unit.configuration import validate_gpio_config

logger = get_logger(__name__)

unit_bp = Blueprint("unit", __name__)

_unit_repo = UnitRepository()

unit_logs: Dict[str, deque] = {}
UNIT_LOG_LIMIT = 100

def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


def _clamp_int(value, default, minimum=None, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _clamp_float(value, default, minimum=None, maximum=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _parse_number_list(value, default):
    if value in (None, ""):
        return list(default)
    if isinstance(value, str):
        values = [item.strip() for item in value.split(",") if item.strip()]
    else:
        values = value
    try:
        return [int(item) for item in values]
    except (TypeError, ValueError):
        return list(default)


def normalize_unit_config(config: dict) -> dict:
    config = dict(config or {})
    motor_type = str(config.get("MOTOR_TYPE", "STEPPER")).upper()
    if motor_type not in ("SERVO", "STEPPER"):
        motor_type = "STEPPER"
    control_method = str(config.get("CONTROL_METHOD", "RASPI_DIRECT")).upper()
    if control_method not in ("RASPI_DIRECT", "ARDUINO_SERIAL"):
        control_method = "RASPI_DIRECT"

    drive_mode = str(config.get("STEPPER_DRIVE_MODE", "half")).lower()
    if drive_mode not in ("full", "half", "wave"):
        drive_mode = "half"
    backend = str(config.get("STEPPER_BACKEND", "auto")).lower()
    if backend not in ("auto", "pigpio", "library", "gpio"):
        backend = "auto"

    stepper_pins = _parse_number_list(config.get("STEPPER_PINS"), [21, 17, 27, 22])
    if len(stepper_pins) != 4:
        stepper_pins = [21, 17, 27, 22]
    phase_order = _parse_number_list(config.get("STEPPER_PHASE_ORDER"), [0, 1, 2, 3])
    if sorted(phase_order) != [0, 1, 2, 3]:
        phase_order = [0, 1, 2, 3]

    return {
        "MOTOR_TYPE": motor_type,
        "CONTROL_METHOD": control_method,
        "MOTOR_SPEED": _clamp_int(config.get("MOTOR_SPEED"), 80, 1, 100),
        "MOTOR_DURATION": _clamp_float(config.get("MOTOR_DURATION"), 2.0, 0.1, 60.0),
        "MOTOR_REVERSE": _parse_bool(config.get("MOTOR_REVERSE")),
        "USE_SENSOR": _parse_bool(config.get("USE_SENSOR")),
        "SENSOR_GPIO_PIN": _clamp_int(config.get("SENSOR_GPIO_PIN"), 13, 0, 27),
        "GREEN_LED_PIN": _clamp_int(config.get("GREEN_LED_PIN"), 5, 0, 27),
        "RED_LED_PIN": _clamp_int(config.get("RED_LED_PIN"), 6, 0, 27),
        "SENSOR_TIMEOUT": _clamp_float(config.get("SENSOR_TIMEOUT"), 5.0, 0.1, 120.0),
        "SENSOR_CHECK_PRE": _parse_bool(config.get("SENSOR_CHECK_PRE", True)),
        "SENSOR_CHECK_POST": _parse_bool(config.get("SENSOR_CHECK_POST", True)),
        "JAM_CLEAR_ATTEMPTS": _clamp_int(config.get("JAM_CLEAR_ATTEMPTS"), 3, 0, 10),
        "HEARTBEAT_INTERVAL": _clamp_int(config.get("HEARTBEAT_INTERVAL"), 30, 5, 300),
        "ARDUINO_PORT": str(config.get("ARDUINO_PORT") or "/dev/ttyUSB0"),
        "PCA9685_CHANNEL": _clamp_int(config.get("PCA9685_CHANNEL"), 15, 0, 15),
        "STEPPER_PINS": stepper_pins,
        "STEPPER_PHASE_ORDER": phase_order,
        "STEPPER_STEP_DELAY": _clamp_float(config.get("STEPPER_STEP_DELAY"), 0.01, 0.001, 1.0),
        "STEPPER_DRIVE_MODE": drive_mode,
        "STEPPER_STEPS": _clamp_int(config.get("STEPPER_STEPS"), 0, 0, 200000),
        "STEPPER_STEPS_PER_REV": 2048,
        "STEPPER_TEST_STEPS": _clamp_int(config.get("STEPPER_TEST_STEPS"), 2048, 1, 200000),
        "STEPPER_BACKEND": backend,
    }


def get_authenticated_unit(conn, unit_name, unit_password=None, unit_token=None):
    unit = _unit_repo.find_by_name(conn, unit_name)
    if not unit:
        return None
    if unit_token and validate_unit_token(conn, unit_name, unit_token):
        return unit
    if unit_password and verify_secret(unit.password, unit_password):
        return unit
    return None


# --- Heartbeat ---

@unit_bp.route("/api/unit/heartbeat", methods=["POST"])
def api_unit_heartbeat():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data received"}), 400

    unit_name = data.get("unit_name") or data.get("name")
    unit_password = data.get("unit_password") or data.get("password")
    ip_address = request.remote_addr
    unit_config = data.get("config", {})

    unit_token = data.get("unit_token")
    if not unit_name or not (unit_password or unit_token):
        return jsonify({"error": "Unit name and credentials required"}), 400

    with get_connection() as conn:
        from app.auth.auth_manager import verify_secret
        unit = _unit_repo.find_by_name(conn, unit_name)

        if unit:
            authenticated_by_password = bool(
                unit_password and verify_secret(unit.password, unit_password)
            )
            authenticated_by_token = bool(
                unit_token and validate_unit_token(conn, unit_name, unit_token)
            )
            if not (authenticated_by_password or authenticated_by_token):
                return jsonify({"error": "Invalid unit credentials"}), 401

            _, response = heartbeat_update(
                conn, unit_name, ip_address, unit_config
            )
            if authenticated_by_password:
                response["unit_api_token"] = issue_unit_session_token(conn, unit_name)

            return jsonify(response)

        if not unit_password:
            return jsonify({"error": "Password required for unregistered unit"}), 401
        state.upsert_pending_unit(
            conn, unit_name, hash_secret(unit_password), ip_address
        )
        return jsonify({"error": "Unit not registered", "pending": True}), 404


# --- Log endpoint ---

@unit_bp.route("/api/log", methods=["POST"])
def api_add_log():
    data = request.json or {}
    message = data.get("message")
    unit_name = data.get("unit_name", "不明な子機")
    unit_password = data.get("unit_password")
    unit_token = data.get("unit_token")

    with get_connection() as conn:
        unit = get_authenticated_unit(conn, unit_name, unit_password, unit_token)
        if not unit:
            return jsonify({"success": False, "error": "Invalid unit credentials"}), 401

        if message:
            from app.repositories.history_repository import HistoryRepository
            HistoryRepository().insert(conn, f"[{unit_name}] {message}")

    if message:
        logger.info("[%s] %s", unit_name, message)

        if unit_name not in unit_logs:
            unit_logs[unit_name] = deque(maxlen=UNIT_LOG_LIMIT)
        unit_logs[unit_name].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
        })
        return jsonify({"success": True}), 200

    return jsonify({"success": False, "error": "Message not provided"}), 400


# --- Admin: unit config endpoints ---

def _require_admin():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    return None


@unit_bp.route("/api/unit/<string:unit_name>/config", methods=["GET"])
def api_get_unit_config(unit_name):
    err = _require_admin()
    if err:
        return err
    with get_connection() as conn:
        snapshot = state.get_unit_config_snapshot(conn, unit_name)
    if snapshot:
        return jsonify(
            {
                "success": True,
                "unit_name": unit_name,
                "config": snapshot["config"],
                "last_updated": snapshot.get("last_updated"),
                "ip_address": snapshot.get("ip_address"),
            }
        )
    return jsonify({"success": False, "error": "Unit config not found"}), 404


@unit_bp.route("/api/unit/<string:unit_name>/config", methods=["POST"])
def api_update_unit_config(unit_name):
    err = _require_admin()
    if err:
        return err

    new_config = request.json
    if not new_config:
        return jsonify({"error": "No config provided"}), 400
    new_config = normalize_unit_config(new_config)
    try:
        validate_gpio_config(new_config)
    except ValueError as exc:
        return jsonify({"error": "Invalid GPIO configuration", "detail": str(exc)}), 400

    with get_connection() as conn:
        unit = _unit_repo.find_by_name(conn, unit_name)
        if not unit:
            return jsonify({"error": "Unit not found"}), 404
        snapshot = state.get_unit_config_snapshot(conn, unit_name)
        state.set_pending_config_update(conn, unit_name, new_config)
        state.upsert_unit_config_snapshot(
            conn,
            unit_name,
            new_config,
            snapshot.get("ip_address") if snapshot else unit.ip_address,
        )
        state.record_device_status(conn, unit_name, "config_update_pending")

    return jsonify({
        "success": True,
        "queued": True,
        "message": "設定変更を予約しました。次回ハートビートで子機に同期されます。",
        "pending_config": new_config,
    }), 202


@unit_bp.route("/api/unit/<unit_name>/command", methods=["POST"])
def api_send_unit_command(unit_name):
    err = _require_admin()
    if err:
        return err

    return jsonify({
        "success": False,
        "error": "Remote commands are disabled. Use a local maintenance procedure.",
    }), 410
