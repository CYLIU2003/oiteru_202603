"""User service - user registration, stock management, period reset."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.logger import get_logger
from app.models.enums import LimitPeriod, UserAllowStatus
from app.models.schemas import UserRecord
from app.repositories.user_repository import UserRepository
from app.services import settings_service

logger = get_logger(__name__)

_user_repo = UserRepository()


def get_period_start_date(period: str) -> str:
    now = datetime.now()
    if period == LimitPeriod.WEEK:
        start = now - timedelta(days=now.weekday())
        return start.strftime("%Y-%m-%d")
    elif period == LimitPeriod.MONTH:
        return now.strftime("%Y-%m-01")
    else:
        return now.strftime("%Y-%m-%d")


def get_period_display_name(period: str) -> str:
    return {
        LimitPeriod.DAY: "1日",
        LimitPeriod.WEEK: "1週間",
        LimitPeriod.MONTH: "1ヶ月",
    }.get(period, "1日")


def get_usage_count_in_period(conn, card_id: str, period: str) -> int:
    from app.repositories.dispense_event_repository import DispenseEventRepository
    event_repo = DispenseEventRepository()
    period_start = get_period_start_date(period)

    try:
        return event_repo.count_usage_in_period(conn, card_id, period_start)
    except Exception:
        from app.repositories.history_repository import HistoryRepository
        hist_repo = HistoryRepository()
        return hist_repo.count(
            conn,
            "SELECT COUNT(*) as count FROM history "
            "WHERE type = 'success' AND txt LIKE ? AND created_at >= ?",
            (f"%{card_id}%", period_start + " 00:00:00"),
        )


def check_and_reset_user_stock(
    conn, user: UserRecord, period: str, history_repo=None
) -> UserRecord:
    card_id = user.card_id
    last_reset = user.last_reset_date

    if not last_reset:
        today = datetime.now().strftime("%Y-%m-%d")
        _user_repo.update_last_reset_date(conn, card_id, today)
        user.last_reset_date = today
        return user

    if hasattr(last_reset, "strftime"):
        last_reset = last_reset.strftime("%Y-%m-%d")

    period_start = get_period_start_date(period)

    if last_reset < period_start:
        reset_stock = settings_service.server_settings["auto_register_stock"]
        today = datetime.now().strftime("%Y-%m-%d")
        _user_repo.update_stock_and_reset_date(conn, card_id, reset_stock, today)
        user.stock = reset_stock
        user.last_reset_date = today

        period_name = get_period_display_name(period)
        logger.info(
            "Auto-reset stock for card_id=%s to %d (new %s)",
            card_id, reset_stock, period_name,
        )
        if history_repo:
            history_repo.insert(
                f"[自動リセット] {period_name}が変わったため、カードID {card_id} の残数を {reset_stock} にリセットしました",
                "system",
            )

    return user


def auto_register_user(
    conn, card_id: str, unit_name: Optional[str] = None, card_id_hash: str = ""
) -> Optional[UserRecord]:
    if not settings_service.server_settings["auto_register_mode"]:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    initial_stock = settings_service.server_settings["auto_register_stock"]

    if not card_id_hash:
        from app.auth.auth_manager import hash_card_uid
        card_id_hash = hash_card_uid(card_id)

    logger.info("Auto-register card_id_hash=%s... stock=%d", card_id_hash[:16], initial_stock)

    _user_repo.insert(
        conn,
        card_id=card_id,
        entry=now,
        stock=initial_stock,
        allow=UserAllowStatus.ALLOWED,
        card_id_hash=card_id_hash,
        last_reset_date=today,
    )

    return _user_repo.find_by_card_id(conn, card_id)
