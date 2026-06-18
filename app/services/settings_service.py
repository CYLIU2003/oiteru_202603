"""Settings service - manages global server configuration."""

from __future__ import annotations

import os
from typing import Optional

from db_adapter import get_connection
from app.logger import get_logger
from app.models.enums import LimitPeriod
from app.repositories.settings_repository import SettingsRepository

logger = get_logger(__name__)

_settings_repo = SettingsRepository()

# Default settings (overridden by DB on load)
server_settings = {
    "auto_register_mode": os.getenv("AUTO_REGISTER_MODE", "false").lower() == "true",
    "auto_register_stock": int(os.getenv("AUTO_REGISTER_STOCK", "2")),
    "usage_limit": int(os.getenv("USAGE_LIMIT", "2")),
    "limit_period": os.getenv("LIMIT_PERIOD", LimitPeriod.DAY),
    "server_name": os.getenv("SERVER_NAME", "OITERU親機"),
    "server_location": os.getenv("SERVER_LOCATION", "未設定"),
}

settings_version: int = 0


def load_settings_from_db() -> None:
    global server_settings, settings_version
    try:
        with get_connection() as conn:
            settings_row = _settings_repo.find(conn)
            if settings_row:
                server_settings["auto_register_mode"] = settings_row.auto_register_mode
                server_settings["auto_register_stock"] = settings_row.auto_register_stock
                server_settings["usage_limit"] = settings_row.usage_limit
                server_settings["limit_period"] = (
                    settings_row.limit_period or LimitPeriod.DAY
                )
                settings_version = settings_row.version
                logger.info(
                    "Loaded settings from DB auto_register=%s version=%d",
                    server_settings["auto_register_mode"],
                    settings_version,
                )
            else:
                logger.info("No settings row in DB; using defaults")
    except Exception as exc:
        logger.warning("Failed to load settings from DB (table may not exist): %s", exc)


def save_settings_to_db() -> bool:
    global settings_version
    settings_version += 1
    try:
        with get_connection() as conn:
            _settings_repo.upsert(
                conn,
                auto_register_mode=server_settings["auto_register_mode"],
                auto_register_stock=server_settings["auto_register_stock"],
                usage_limit=server_settings["usage_limit"],
                limit_period=server_settings["limit_period"],
                version=settings_version,
            )
        logger.info("Saved settings to DB (version %d)", settings_version)
        return True
    except Exception as exc:
        logger.error("Failed to save settings: %s", exc)
        return False
