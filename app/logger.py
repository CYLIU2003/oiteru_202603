"""Structured logger for OITERU.

Replaces all ``print()`` calls with a configured standard-library logger.
Sensitive fields (card_id, password, token) are automatically masked in log
output via a custom filter.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

SENSITIVE_KEYS = frozenset({
    "card_id", "password", "unit_password", "unit_token",
    "token", "secret", "api_token", "unit_api_token",
    "OITERU_ADMIN_PASSWORD", "FLASK_SECRET_KEY", "MYSQL_PASSWORD",
})

MAX_MASKED_LENGTH = 200


class SensitiveDataFilter(logging.Filter):
    """Mask sensitive values in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _mask_message(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _mask_value(k, v) for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    _mask_simple(str(v)) for v in record.args
                )
        return True


def _mask_message(msg: str) -> str:
    for key in SENSITIVE_KEYS:
        if key in msg:
            pos = msg.find(key)
            return msg[:pos + len(key) + 20] + "...[masked]"
    if len(msg) > MAX_MASKED_LENGTH:
        return msg[:MAX_MASKED_LENGTH] + "...[truncated]"
    return msg


def _mask_value(key: str, value: object) -> object:
    if key.lower().replace("_", "") in {k.lower().replace("_", "") for k in SENSITIVE_KEYS}:
        return "***"
    if isinstance(value, str) and len(value) > MAX_MASKED_LENGTH:
        return value[:MAX_MASKED_LENGTH] + "...[truncated]"
    return value


def _mask_simple(value: str) -> str:
    if len(value) > MAX_MASKED_LENGTH:
        return value[:MAX_MASKED_LENGTH] + "...[truncated]"
    return value


_logger: Optional[logging.Logger] = None


def get_logger(name: str = "oiteru") -> logging.Logger:
    """Return (and lazily configure) the application-wide logger."""
    global _logger
    if _logger is not None:
        return _logger

    level_name = os.getenv("OITERU_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = os.getenv(
        "OITERU_LOG_FORMAT",
        "%(asctime)s [%(levelname)s] %(name)s %(message)s",
    )
    datefmt = os.getenv("OITERU_LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    handler.addFilter(SensitiveDataFilter())

    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    _logger.handlers.clear()
    _logger.addHandler(handler)
    _logger.propagate = False

    log_file = os.getenv("OITERU_LOG_FILE", "")
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            from logging.handlers import RotatingFileHandler
            fh = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
            fh.addFilter(SensitiveDataFilter())
            _logger.addHandler(fh)
        except Exception:
            _logger.warning("Failed to set up log file handler", exc_info=True)

    return _logger
