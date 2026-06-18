"""Unit (child-device) management service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.logger import get_logger
from app.models.enums import UnitAvailableStatus, UnitConnectStatus
from app.models.schemas import ServerSettings, UnitConfigData, UnitRecord
from app.repositories.unit_repository import UnitRepository
from app.services import settings_service

logger = get_logger(__name__)

_unit_repo = UnitRepository()


# In-memory stores (will be migrated to DB in P11)
unregistered_units: Dict[str, dict] = {}
unit_configs: Dict[str, dict] = {}
pending_unit_config_updates: Dict[str, dict] = {}


def get_unit_config_data() -> Dict[str, Any]:
    return {
        k: v for k, v in unit_configs.items()
    }


def heartbeat_update(
    conn,
    unit_name: str,
    ip_address: str,
    config: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Process a unit heartbeat. Returns (unit_record or None, response_dict)."""
    unit = _unit_repo.find_by_name(conn, unit_name)

    if config and unit_name:
        unit_configs[unit_name] = {
            "config": config,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": ip_address,
        }

    if unit:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _unit_repo.update_heartbeat(conn, unit_name, now, ip_address)

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

        # Pending config update
        if unit_name in pending_unit_config_updates:
            response["config_update"] = pending_unit_config_updates.pop(unit_name)

        return unit, response

    # Unregistered unit
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if unit_name not in unregistered_units:
        unregistered_units[unit_name] = {
            "ip_address": ip_address,
            "first_seen": now,
            "last_seen": now,
            "heartbeat_count": 1,
        }
    else:
        unregistered_units[unit_name]["last_seen"] = now
        unregistered_units[unit_name]["heartbeat_count"] += 1
        unregistered_units[unit_name]["ip_address"] = ip_address

    return None, {"error": "Unit not registered", "pending": True}
