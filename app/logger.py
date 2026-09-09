"""Structured logger for OITERU.

Replaces all ``print()`` calls with a configured standard-library logger.
Sensitive fields (card_id, password, token) are automatically masked in log
output via a custom filter.
"""

from __future__ import annotations

import logging
import os
import re
import sys

SENSITIVE_KEYS = frozenset({
    "card_id", "password", "unit_password", "unit_token",
    "token", "secret", "api_token", "unit_api_token",
    "OITERU_ADMIN_PASSWORD", "FLASK_SECRET_KEY", "MYSQL_PASSWORD",
})

MAX_MASKED_LENGTH = 200

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"\b(?P<key>" + "|".join(re.escape(key) for key in SENSITIVE_KEYS) +
    r")\b\s*(?P<separator>[:=])\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)


class SensitiveDataFilter(logging.Filter):
    """Mask sensitive values in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Render before masking.  Altering a format string while leaving its
            # original positional arguments attached can make logging itself fail
            # (for example, when a ``%d`` argument is converted to a string).
            try:
                message = record.getMessage()
            except (TypeError, ValueError):
                message = record.msg
            record.msg = _mask_message(message)
            record.args = ()
        return True


def _mask_message(msg: str) -> str:
    msg = _SENSITIVE_VALUE_PATTERN.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}***",
        msg,
    )
    if len(msg) > MAX_MASKED_LENGTH:
        return msg[:MAX_MASKED_LENGTH] + "...[truncated]"
    return msg


_logger: logging.Logger | None = None


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
