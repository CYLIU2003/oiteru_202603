"""Device API for child standalone (offline) mode."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.api.units import get_authenticated_unit
from app.logger import get_logger
from app.services.offline_service import (
    MAX_EVENTS_PER_REQUEST,
    build_offline_cache,
    ingest_offline_events,
)
from db_adapter import get_connection

logger = get_logger(__name__)

offline_bp = Blueprint("offline", __name__)


def _error(code: str, message: str, status: int):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


def _authenticate(conn, data: dict):
    unit_name = data.get("unit_name")
    if not unit_name:
        return None
    return get_authenticated_unit(
        conn, unit_name, data.get("unit_password"), data.get("unit_token")
    )


@offline_bp.route("/api/v1/units/offline-cache", methods=["POST"])
def offline_cache():
    """Hand an authenticated child the limits it may apply while offline."""
    data = request.get_json(silent=True) or {}
    try:
        with get_connection() as conn:
            unit = _authenticate(conn, data)
            if not unit:
                return _error("INVALID_UNIT_CREDENTIALS", "Invalid unit credentials", 401)
            cache = build_offline_cache(conn, unit)
        return jsonify({"success": True, "cache": cache})
    except Exception:
        logger.exception("Offline cache build failed")
        return _error("INTERNAL_ERROR", "Offline cache could not be built", 500)


@offline_bp.route("/api/v1/units/offline-events", methods=["POST"])
def offline_events():
    """Record dispenses a child made while it could not reach the parent."""
    data = request.get_json(silent=True) or {}
    events = data.get("events")
    if not isinstance(events, list):
        return _error("INVALID_REQUEST", "events must be a list", 400)
    if len(events) > MAX_EVENTS_PER_REQUEST:
        return _error(
            "TOO_MANY_EVENTS", f"Send at most {MAX_EVENTS_PER_REQUEST} events per request", 400
        )
    try:
        with get_connection() as conn:
            unit = _authenticate(conn, data)
            if not unit:
                return _error("INVALID_UNIT_CREDENTIALS", "Invalid unit credentials", 401)
            results = ingest_offline_events(conn, unit.name, events)
        return jsonify({"success": True, "results": results})
    except Exception:
        # The whole batch rolls back; the child keeps its queue and retries.
        logger.exception("Offline event sync failed")
        return _error("INTERNAL_ERROR", "Offline events could not be recorded", 500)
