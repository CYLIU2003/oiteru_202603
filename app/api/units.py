"""Unit heartbeat, config, log, and command API endpoints."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Dict

import requests
from flask import Blueprint, jsonify, request, session

from app.auth.auth_manager import hash_secret
from app.auth.unit_auth import (
    get_push_headers,
    issue_unit_session_token,
    get_unit_session_tokens,
)
from app.logger import get_logger
from app.models.schemas import UnitConfigData
from app.repositories.unit_repository import UnitRepository
from app.services.unit_service import (
    heartbeat_update,
    pending_unit_config_updates,
    unregistered_units,
    unit_configs,
)
from db_adapter import get_connection

logger = get_logger(__name__)

unit_bp = Blueprint("unit", __name__)

_unit_repo = UnitRepository()

unit_logs: Dict[str, deque] = {}
UNIT_LOG_LIMIT = 100

# Unit config normalization (from server.py)
from app.services.settings_service import server_settings


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
        "SENSOR_GPIO_PIN": _clamp_int(config.get("SENSOR_GPIO_PIN"), 22, 0, 40),
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
    from app.auth.auth_manager import verify_secret
    from app.auth.unit_auth import validate_unit_token

    unit = _unit_repo.find_by_name(conn, unit_name)
    if not unit:
        return None
    if unit_token and validate_unit_token(unit_name, unit_token):
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

    if not all([unit_name, unit_password]):
        return jsonify({"error": "Unit name and password required"}), 400

    with get_connection() as conn:
        from app.auth.auth_manager import verify_secret
        unit = _unit_repo.find_by_name(conn, unit_name)

        if unit:
            if not verify_secret(unit.password, unit_password):
                return jsonify({"error": "Invalid password"}), 401

            unit_record, response = heartbeat_update(
                conn, unit_name, ip_address, unit_config
            )

            token = get_unit_session_tokens().get(unit_name) or issue_unit_session_token(unit_name)
            response["unit_api_token"] = token

            if unit_name in pending_unit_config_updates:
                response["config_update"] = pending_unit_config_updates.pop(unit_name)

            return jsonify(response)
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if unit_name not in unregistered_units:
                unregistered_units[unit_name] = {
                    "password_hash": hash_secret(unit_password),
                    "ip_address": ip_address,
                    "first_seen": now,
                    "last_seen": now,
                    "heartbeat_count": 1,
                }
            else:
                unregistered_units[unit_name]["last_seen"] = now
                unregistered_units[unit_name]["heartbeat_count"] += 1
                unregistered_units[unit_name]["ip_address"] = ip_address
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
        logger.info("[%s] %s", unit_name, message)
        from app.repositories.history_repository import HistoryRepository
        HistoryRepository().insert(f"[{unit_name}] {message}")

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
    if unit_name in unit_configs:
        return jsonify({"success": True, "unit_name": unit_name, **unit_configs[unit_name]})
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

    pending_unit_config_updates[unit_name] = new_config

    if unit_name in unit_configs:
        unit_configs[unit_name]["config"] = new_config
        unit_configs[unit_name]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        unit_configs[unit_name] = {
            "config": new_config,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": None,
        }

    with get_connection() as conn:
        unit = _unit_repo.find_by_name(conn, unit_name)

    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    unit_ip = unit.ip_address
    push_headers = get_push_headers(unit_name)
    push_success = False
    push_error = None

    if unit_ip and unit.connect == 1 and push_headers:
        try:
            response = requests.post(
                f"http://{unit_ip}:5001/api/config/update",
                json={"config": new_config},
                headers=push_headers,
                timeout=5,
            )
            if response.status_code == 200:
                push_success = True
                pending_unit_config_updates.pop(unit_name, None)
            else:
                push_error = f"子機が設定を受け付けませんでした (status: {response.status_code})"
        except requests.exceptions.Timeout:
            push_error = "子機への接続がタイムアウトしました"
        except requests.exceptions.ConnectionError:
            push_error = "子機に接続できませんでした"
        except Exception as exc:
            push_error = f"エラー: {exc}"
    else:
        push_error = "子機がオフライン、または認証トークン未取得です"

    return jsonify({
        "success": True,
        "push_success": push_success,
        "push_error": push_error,
        "message": (
            "設定を即座に送信しました" if push_success
            else f"設定変更を予約しました（{push_error}）。次回ハートビートで子機に同期されます。"
        ),
        "pending_config": new_config,
    })


@unit_bp.route("/api/unit/<unit_name>/command", methods=["POST"])
def api_send_unit_command(unit_name):
    err = _require_admin()
    if err:
        return err

    data = request.json
    command = data.get("command")
    if not command:
        return jsonify({"error": "Command required"}), 400

    with get_connection() as conn:
        unit = _unit_repo.find_by_name(conn, unit_name)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    unit_ip = unit.ip_address
    push_headers = get_push_headers(unit_name)
    if not unit_ip or unit.connect == 0 or not push_headers:
        return jsonify({"error": "Unit is offline"}), 503

    try:
        response = requests.post(
            f"http://{unit_ip}:5001/api/command",
            json={"command": command},
            headers=push_headers,
            timeout=10,
        )
        if response.status_code == 200:
            return jsonify({"success": True, "result": response.json(), "message": "コマンドを送信しました"})
        return jsonify({"success": False, "error": f"子機がエラーを返しました (status: {response.status_code})"})
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "タイムアウト"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "接続エラー"}), 503
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
