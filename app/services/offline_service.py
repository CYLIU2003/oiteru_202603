"""Child standalone (offline) mode: allowance cache and event synchronization.

When a child cannot reach the parent it may still dispense, within limits the
parent handed it earlier (the *offline cache*).  Every standalone dispense is
queued on the child and sent back here once the parent is reachable again.

The parent stays the source of truth.  Offline events are recorded exactly
once (``event_id`` is unique), counted in the period they physically happened
(``occurred_at``), and any mismatch with the parent's view, such as a card
that had no allowance left, is kept as a machine-readable ``error_code`` on
the recorded event instead of being dropped.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.auth.auth_manager import card_uid_hmac_key, is_card_ref
from app.logger import get_logger
from app.models.enums import DispenseErrorCode, DispenseStatus, UnitAvailableStatus
from app.models.schemas import UnitRecord
from app.repositories.dispense_event_repository import DispenseEventRepository
from app.repositories.history_repository import HistoryRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository
from app.services import settings_service
from app.services.user_service import check_and_reset_user_stock, get_period_start_date

logger = get_logger(__name__)

_event_repo = DispenseEventRepository()
_history_repo = HistoryRepository()
_unit_repo = UnitRepository()
_user_repo = UserRepository()

MAX_EVENTS_PER_REQUEST = 200
_EVENT_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,64}")
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class OfflinePolicy:
    enabled: bool
    per_card_limit: int
    max_age_hours: int
    max_events: int


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def offline_policy() -> OfflinePolicy:
    """Read the standalone-mode limits from the parent's environment (.env)."""
    return OfflinePolicy(
        enabled=os.getenv("OITERU_OFFLINE_MODE", "true").strip().lower() == "true",
        per_card_limit=_env_int("OITERU_OFFLINE_PER_CARD_LIMIT", 1, 0, 10),
        max_age_hours=_env_int("OITERU_OFFLINE_CACHE_MAX_AGE_HOURS", 72, 1, 24 * 14),
        max_events=_env_int("OITERU_OFFLINE_MAX_EVENTS", 300, 0, 5000),
    )


def build_offline_cache(conn, unit: UnitRecord) -> dict:
    """Return what a child needs to authorize cards while the parent is down.

    ``cards`` maps a card ref to the number of standalone dispenses allowed for
    it: never more than the policy limit, the user's remaining allowance, or
    what is left of the current period.  Denied users are simply absent.
    """
    policy = offline_policy()
    cache = {
        "enabled": policy.enabled,
        "issued_at": datetime.now().strftime(_TIME_FORMAT),
        "max_age_hours": policy.max_age_hours,
        "per_card_limit": policy.per_card_limit,
        "max_events": policy.max_events,
        "unit_stock": unit.stock,
        "cards": {},
    }
    if not policy.enabled or policy.per_card_limit <= 0:
        cache["enabled"] = False
        return cache

    settings = settings_service.server_settings
    period_start = get_period_start_date(settings["limit_period"])
    usage_limit = int(settings["usage_limit"])
    reset_stock = int(settings["auto_register_stock"])
    used = _event_repo.count_recorded_by_card_since(conn, period_start)

    cards = {}
    for user in _user_repo.find_allowed(conn):
        ref = user.card_id_hash
        if not is_card_ref(ref):
            continue
        # A user whose counter has not been reset for this period yet will be
        # reset on the next online use, so use the reset value here as well.
        stock = user.stock if (user.last_reset_date or "") >= period_start else reset_stock
        remaining = min(policy.per_card_limit, usage_limit - used.get(ref, 0), stock)
        if remaining > 0:
            cards[ref] = remaining

    cache["cards"] = cards
    # The child needs the same key to turn a tapped UID into a card ref.  It is
    # only sent to an authenticated child and stored there with mode 0600.
    cache["card_key"] = card_uid_hmac_key().decode()
    return cache


def _parse_occurred_at(value) -> str | None:
    try:
        occurred = datetime.strptime(str(value), _TIME_FORMAT)
    except (TypeError, ValueError):
        return None
    # A child clock that runs ahead must not push events into the future.
    latest = datetime.now() + timedelta(minutes=5)
    return min(occurred, latest).strftime(_TIME_FORMAT)


def _reject(event_id, reason: str) -> dict:
    return {"event_id": event_id, "result": "rejected", "reason": reason}


def ingest_offline_events(conn, unit_name: str, events: list) -> list:
    """Record standalone dispenses reported by a child.  Safe to call twice.

    Returns one result per event.  The child removes every event whose result
    is ``recorded``, ``failed``, ``duplicate`` or ``rejected`` from its queue;
    retrying a rejected (malformed) event would never succeed.
    """
    results = []
    for raw in events[:MAX_EVENTS_PER_REQUEST]:
        event = raw if isinstance(raw, dict) else {}
        event_id = str(event.get("event_id") or "")
        if not _EVENT_ID_PATTERN.fullmatch(event_id):
            results.append(_reject(event_id, "INVALID_EVENT_ID"))
            continue
        card_ref = str(event.get("card_ref") or "")
        if not is_card_ref(card_ref):
            results.append(_reject(event_id, "INVALID_CARD_REF"))
            continue
        occurred_at = _parse_occurred_at(event.get("occurred_at"))
        if not occurred_at:
            results.append(_reject(event_id, "INVALID_OCCURRED_AT"))
            continue

        existing = _event_repo.find_by_event_id(conn, event_id)
        if existing:
            if existing.unit_name != unit_name:
                results.append(_reject(event_id, "EVENT_BELONGS_TO_OTHER_UNIT"))
            else:
                results.append({"event_id": event_id, "result": "duplicate"})
            continue

        if event.get("success") is not True:
            error_code = str(event.get("error_code") or DispenseErrorCode.DISPENSE_FAILED_CLIENT)[:64]
            _event_repo.insert_offline(
                conn, event_id, unit_name, card_ref, DispenseStatus.FAILED, occurred_at, error_code
            )
            results.append({"event_id": event_id, "result": "failed"})
            continue

        results.append(_record_offline_dispense(conn, unit_name, event_id, card_ref, occurred_at))
    return results


def _record_offline_dispense(conn, unit_name, event_id, card_ref, occurred_at) -> dict:
    """The item is already out of the machine: always record it, flag mismatches."""
    error_code = None
    user = _user_repo.find_by_card_ref(conn, card_ref)
    if user is None:
        error_code = DispenseErrorCode.OFFLINE_USER_UNKNOWN
    else:
        user = check_and_reset_user_stock(
            conn, user, settings_service.server_settings["limit_period"], _history_repo
        )
        if _user_repo.decrement_stock_and_total_if_available(conn, user.card_id) != 1:
            _user_repo.add_total_only(conn, user.card_id)
            error_code = DispenseErrorCode.OFFLINE_LIMIT_OVERRUN

    if _unit_repo.decrement_stock_floor_zero(conn, unit_name) != 1:
        error_code = error_code or DispenseErrorCode.OFFLINE_UNIT_STOCK_MISMATCH
    unit = _unit_repo.find_by_name(conn, unit_name)
    if unit and unit.stock <= 0 and unit.available != UnitAvailableStatus.UNAVAILABLE:
        _unit_repo.set_available(conn, unit_name, UnitAvailableStatus.UNAVAILABLE)
        _history_repo.insert(conn, f"[{unit_name}] 在庫0のため排出停止", "system")

    _event_repo.insert_offline(
        conn, event_id, unit_name, card_ref, DispenseStatus.RECORDED, occurred_at, error_code
    )
    note = f", 要確認: {error_code}" if error_code else ""
    _history_repo.insert(
        conn,
        f"[{unit_name}] オフライン利用を同期 (event_id: {event_id}, card_ref: {card_ref[:12]},"
        f" 排出時刻: {occurred_at}{note})",
        "success",
    )
    if error_code:
        logger.warning("Offline event %s recorded with %s", event_id, error_code)
    return {"event_id": event_id, "result": "recorded", "error_code": error_code}
