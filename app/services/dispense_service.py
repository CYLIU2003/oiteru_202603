"""Dispense service - the core dispense authorization and recording flow.

This is the most critical business logic in OITERU.  It enforces the
state machine: requested -> authorized -> dispensing -> recorded / failed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from app.auth.auth_manager import generate_event_id
from app.logger import get_logger
from app.models.enums import (
    DispenseErrorCode,
    DispenseStatus,
    LimitPeriod,
    UserAllowStatus,
    UnitAvailableStatus,
)
from app.models.schemas import DispenseEventRecord, UnitRecord, UserRecord
from app.repositories.dispense_event_repository import DispenseEventRepository
from app.repositories.history_repository import HistoryRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository
from app.services import settings_service
from app.services.user_service import (
    auto_register_user,
    check_and_reset_user_stock,
    get_period_display_name,
    get_usage_count_in_period,
)

logger = get_logger(__name__)

_event_repo = DispenseEventRepository()
_unit_repo = UnitRepository()
_user_repo = UserRepository()
_history_repo = HistoryRepository()


class DispenseAuthResult:
    def __init__(
        self,
        authorized: bool = False,
        event_id: Optional[str] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        http_status: int = 200,
        message: Optional[str] = None,
        usage_count: Optional[int] = None,
        usage_limit: Optional[int] = None,
        period: Optional[str] = None,
        auto_register: bool = False,
    ):
        self.authorized = authorized
        self.event_id = event_id
        self.error = error
        self.error_code = error_code
        self.http_status = http_status
        self.message = message
        self.usage_count = usage_count
        self.usage_limit = usage_limit
        self.period = period
        self.auto_register = auto_register


class DispenseResult:
    def __init__(
        self,
        success: bool = False,
        recorded: bool = False,
        idempotent: bool = False,
        event_id: Optional[str] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        http_status: int = 200,
        user_stock: Optional[int] = None,
        unit_stock: Optional[int] = None,
    ):
        self.success = success
        self.recorded = recorded
        self.idempotent = idempotent
        self.event_id = event_id
        self.error = error
        self.error_code = error_code
        self.http_status = http_status
        self.user_stock = user_stock
        self.unit_stock = unit_stock


def authorize_dispense(
    conn,
    card_id: str,
    unit_name: str,
    unit: UnitRecord,
) -> DispenseAuthResult:
    """Authorize a dispense request.  Returns a DispenseAuthResult."""
    event_id = generate_event_id()

    _event_repo.insert(conn, event_id, unit_name, card_id, DispenseStatus.REQUESTED)

    # 1. Unit stock & availability
    if unit.stock <= 0 or unit.available == UnitAvailableStatus.UNAVAILABLE:
        _history_repo.insert(
            f"[{unit_name}] 在庫不足のため利用不可 (カードID: {card_id})",
            "usage",
        )
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.UNIT_STOCK_EMPTY)
        return DispenseAuthResult(
            event_id=event_id,
            error="Unit has no stock remaining",
            error_code=DispenseErrorCode.UNIT_STOCK_EMPTY,
            http_status=400,
        )

    # 2. User lookup (with auto-register)
    user = _user_repo.find_by_card_id(conn, card_id)

    if not user:
        user = auto_register_user(conn, card_id, unit_name=unit_name)
        if not user:
            _history_repo.insert(
                f"[{unit_name}] 未登録カード (カードID: {card_id})",
                "usage",
            )
            _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_NOT_FOUND)
            return DispenseAuthResult(
                event_id=event_id,
                error="User not found",
                error_code=DispenseErrorCode.USER_NOT_FOUND,
                http_status=404,
                auto_register=False,
            )

    # 3. User deny check
    if user.allow == UserAllowStatus.DENIED:
        _history_repo.insert(
            f"[{unit_name}] 利用不許可 (カードID: {card_id})",
            "usage",
        )
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_DENIED)
        return DispenseAuthResult(
            event_id=event_id,
            error="User is not allowed",
            error_code=DispenseErrorCode.USER_DENIED,
            http_status=403,
        )

    # 4. Period-based stock reset
    period = settings_service.server_settings["limit_period"]
    user = check_and_reset_user_stock(conn, user, period, _history_repo)

    # 5. User stock check
    if user.stock <= 0:
        _history_repo.insert(
            f"[{unit_name}] 残数不足 (カードID: {card_id})",
            "usage",
        )
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_STOCK_EMPTY)
        return DispenseAuthResult(
            event_id=event_id,
            error="User has no stock remaining",
            error_code=DispenseErrorCode.USER_STOCK_EMPTY,
            http_status=400,
        )

    # 6. Period limit check
    usage_limit = settings_service.server_settings["usage_limit"]
    usage_count = get_usage_count_in_period(conn, card_id, period)

    if usage_count >= usage_limit:
        period_name = get_period_display_name(period)
        _history_repo.insert(
            f"[{unit_name}] {period_name}の上限({usage_limit}個)に達しています (カードID: {card_id})",
            "usage",
        )
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.PERIOD_LIMIT_EXCEEDED)
        return DispenseAuthResult(
            event_id=event_id,
            error="Period limit exceeded",
            error_code=DispenseErrorCode.PERIOD_LIMIT_EXCEEDED,
            http_status=429,
            usage_count=usage_count,
            usage_limit=usage_limit,
            period=period,
            message=f"{period_name}あたりの取得上限（{usage_limit}個）に達しました",
        )

    # Authorized
    _event_repo.update_status(conn, event_id, DispenseStatus.AUTHORIZED)
    _history_repo.insert(
        f"[{unit_name}] 排出認可 (event_id: {event_id}, カードID: {card_id})",
        "usage",
    )
    return DispenseAuthResult(
        authorized=True,
        event_id=event_id,
        message="Dispense authorized",
    )


def record_dispense_result(
    conn,
    event_id: str,
    unit_name: str,
    unit: UnitRecord,
    dispense_success: bool,
    error_code: Optional[str] = None,
) -> DispenseResult:
    """Record the physical dispensing result and finalize inventory."""

    # Look up the event
    event = _event_repo.find_by_event_id(conn, event_id)
    if not event:
        return DispenseResult(
            event_id=event_id,
            error="Event not found",
            http_status=404,
        )

    if event.unit_name != unit_name:
        return DispenseResult(
            event_id=event_id,
            error="Event does not belong to unit",
            http_status=403,
        )

    # Idempotency: already in terminal state
    if event.status == DispenseStatus.RECORDED:
        return DispenseResult(
            success=True,
            recorded=True,
            idempotent=True,
            event_id=event_id,
        )
    if event.status == DispenseStatus.FAILED:
        return DispenseResult(
            success=False,
            recorded=False,
            idempotent=True,
            event_id=event_id,
            error_code=event.error_code,
        )

    # Physical dispense failed
    if not dispense_success:
        fail_code = error_code or DispenseErrorCode.DISPENSE_FAILED
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, fail_code)
        _history_repo.insert(
            f"[{unit_name}] 排出失敗 (event_id: {event_id}, カードID: {event.card_id}, code: {fail_code})",
            "usage",
        )
        return DispenseResult(
            success=False,
            recorded=False,
            event_id=event_id,
            error_code=fail_code,
        )

    # Atomic transition to "dispensing"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transitioned = _event_repo.update(
        conn,
        "UPDATE dispense_events SET status = ?, updated_at = ? WHERE event_id = ? AND status IN (?, ?)",
        (DispenseStatus.DISPENSING, now, event_id, DispenseStatus.AUTHORIZED, DispenseStatus.REQUESTED),
    )
    if transitioned == 0:
        latest = _event_repo.find_by_event_id(conn, event_id)
        if latest and latest.status == DispenseStatus.RECORDED:
            return DispenseResult(success=True, recorded=True, idempotent=True, event_id=event_id)
        if latest and latest.status == DispenseStatus.FAILED:
            return DispenseResult(
                success=False, recorded=False, idempotent=True,
                event_id=event_id, error_code=latest.error_code,
            )
        return DispenseResult(
            event_id=event_id,
            error=f"Event is not processable (status: {latest.status if latest else 'unknown'})",
            http_status=409,
        )

    # Re-check all constraints
    user = _user_repo.find_by_card_id(conn, event.card_id)
    if not user:
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_NOT_FOUND)
        return DispenseResult(event_id=event_id, error="User not found", http_status=404)

    latest_unit = _unit_repo.find_by_name(conn, unit_name)
    if latest_unit and (latest_unit.stock <= 0 or latest_unit.available == UnitAvailableStatus.UNAVAILABLE):
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.UNIT_STOCK_EMPTY)
        return DispenseResult(event_id=event_id, error="Unit has no stock remaining", http_status=400)

    if user.allow == UserAllowStatus.DENIED:
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_DENIED)
        return DispenseResult(event_id=event_id, error="User is not allowed", http_status=403)

    period = settings_service.server_settings["limit_period"]
    user = check_and_reset_user_stock(conn, user, period, _history_repo)

    if user.stock <= 0:
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.USER_STOCK_EMPTY)
        return DispenseResult(event_id=event_id, error="User has no stock remaining", http_status=400)

    usage_limit = settings_service.server_settings["usage_limit"]
    usage_count = get_usage_count_in_period(conn, event.card_id, period)
    if usage_count >= usage_limit:
        _event_repo.update_status(conn, event_id, DispenseStatus.FAILED, DispenseErrorCode.PERIOD_LIMIT_EXCEEDED)
        period_name = get_period_display_name(period)
        return DispenseResult(
            event_id=event_id,
            error="Period limit exceeded",
            error_code=DispenseErrorCode.PERIOD_LIMIT_EXCEEDED,
            http_status=429,
        )

    # Decrement stocks
    new_user_stock = user.stock - 1
    new_total = user.total + 1
    _user_repo.update_stock_and_total(conn, event.card_id, new_user_stock, new_total)

    new_unit_stock = latest_unit.stock - 1
    _unit_repo.update_stock(conn, unit_name, new_unit_stock)

    if new_unit_stock <= 0:
        _unit_repo.set_available(conn, unit_name, UnitAvailableStatus.UNAVAILABLE)
        _history_repo.insert(f"[{unit_name}] 在庫0のため排出停止", "system")

    _event_repo.update_status(conn, event_id, DispenseStatus.RECORDED)
    _history_repo.insert(
        f"[{unit_name}] 利用成功 (event_id: {event_id}, カードID: {event.card_id}, 残数: {new_user_stock})",
        "success",
    )

    return DispenseResult(
        success=True,
        recorded=True,
        event_id=event_id,
        user_stock=new_user_stock,
        unit_stock=new_unit_stock,
    )
