"""Unit (child-device) management service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app import state
from app.logger import get_logger
from app.repositories.unit_repository import UnitRepository
from app.services import settings_service

logger = get_logger(__name__)

_unit_repo = UnitRepository()


def heartbeat_update(
    conn,
    unit_name: str,
    ip_address: str,
    config: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Process a unit heartbeat. Returns (unit_record or None, response_dict)."""
    unit = _unit_repo.find_by_name(conn, unit_name)

    if unit:
        if config:
            state.upsert_unit_config_snapshot(conn, unit_name, config, ip_address)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _unit_repo.update_heartbeat(conn, unit_name, now, ip_address)
        state.record_device_status(conn, unit_name, "heartbeat")

        response = {
            "success": True,
            "stock": unit.stock,
            "available": unit.available,
            "auto_register_mode": settings_service.server_settings["auto_register_mode"],
            "auto_register_stock": settings_service.server_settings["auto_register_stock"],
            "usage_limit": settings_service.server_settings["usage_limit"],
            "limit_period": settings_service.server_settings["limit_period"],
            "settings_version": settings_service.settings_version,
        }

        pending_config = state.pop_pending_config_update(conn, unit_name)
        if pending_config:
            response["config_update"] = pending_config

        return unit, response

    return None, {"error": "Unit not registered", "pending": True}
