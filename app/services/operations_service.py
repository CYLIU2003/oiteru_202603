"""Business rules for inventory replenishment and maintenance operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app import state
from app.logger import get_logger
from app.models.enums import (
    MaintenanceTicketCategory,
    MaintenanceTicketSource,
    MaintenanceTicketStatus,
    StockMovementType,
)
from app.models.schemas import (
    MaintenanceTicketRecord,
    StockMovementRecord,
    UnitRecord,
)
from app.repositories.admin_user_repository import AdminUserRepository
from app.repositories.operations_repository import OperationsRepository

logger = get_logger(__name__)

_operations_repo = OperationsRepository()
_admin_user_repo = AdminUserRepository()

_UNSET = object()


class OperationsError(Exception):
    """Base exception for a safe, user-facing operations failure."""

    error_code = "OPERATIONS_ERROR"


class OperationsValidationError(OperationsError):
    error_code = "OPERATIONS_VALIDATION_ERROR"


class OperationsNotFoundError(OperationsError):
    error_code = "OPERATIONS_NOT_FOUND"


class OperationsConflictError(OperationsError):
    error_code = "OPERATIONS_CONFLICT"


@dataclass(frozen=True)
class UnitOperationalUpdate:
    """Result of a unit's inventory/settings update."""

    unit: UnitRecord
    movement: StockMovementRecord | None


def record_stock_movement(
    conn,
    *,
    unit_id: int,
    movement_type: str,
    quantity_delta: int,
    reason: str,
    admin_user_id: int,
) -> StockMovementRecord:
    """Atomically change inventory and retain an immutable movement record."""
    unit_id = _require_positive_int(unit_id, "unit_id")
    admin_user_id = _require_positive_int(admin_user_id, "admin_user_id")
    movement_type = _validate_stock_movement_type(movement_type)
    quantity_delta = _require_nonzero_int(quantity_delta, "quantity_delta")
    _validate_delta_direction(movement_type, quantity_delta)
    reason = _require_text(reason, "reason", maximum_length=255)

    if not _operations_repo.find_unit(conn, unit_id):
        raise OperationsNotFoundError("Unit not found")

    if _operations_repo.apply_stock_delta(conn, unit_id, quantity_delta) != 1:
        current_unit = _operations_repo.find_unit(conn, unit_id)
        if not current_unit:
            raise OperationsNotFoundError("Unit not found")
        raise OperationsConflictError(
            "Inventory changed concurrently or the requested movement would make stock negative"
        )

    updated_unit = _operations_repo.find_unit(conn, unit_id)
    if not updated_unit:
        raise OperationsNotFoundError("Unit not found after inventory update")

    now = _now()
    stock_before = updated_unit.stock - quantity_delta
    movement_id = _operations_repo.insert_stock_movement(
        conn,
        unit_id=unit_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        stock_before=stock_before,
        stock_after=updated_unit.stock,
        reason=reason,
        admin_user_id=admin_user_id,
        created_at=now,
    )
    _admin_user_repo.record_audit(
        conn,
        admin_user_id,
        f"stock_{movement_type}",
        "stock_movement",
        str(movement_id),
    )
    logger.info(
        "Recorded stock movement: movement_id=%s unit_id=%s delta=%s",
        movement_id,
        unit_id,
        quantity_delta,
    )
    return StockMovementRecord(
        id=movement_id,
        unit_id=unit_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        stock_before=stock_before,
        stock_after=updated_unit.stock,
        reason=reason,
        admin_user_id=admin_user_id,
        created_at=now,
        updated_at=now,
        unit_name=updated_unit.name,
    )


def update_unit_operational_state(
    conn,
    *,
    unit_id: int,
    target_stock: int,
    initial_stock: int,
    available: int,
    stock_change_reason: str | None,
    admin_user_id: int,
) -> UnitOperationalUpdate:
    """Update admin-controlled unit fields without bypassing the stock ledger."""
    unit_id = _require_positive_int(unit_id, "unit_id")
    admin_user_id = _require_positive_int(admin_user_id, "admin_user_id")
    target_stock = _require_nonnegative_int(target_stock, "target_stock")
    initial_stock = _require_nonnegative_int(initial_stock, "initial_stock")
    available = _require_available_status(available)

    current_unit = _operations_repo.find_unit(conn, unit_id)
    if not current_unit:
        raise OperationsNotFoundError("Unit not found")

    movement: StockMovementRecord | None = None
    if target_stock != current_unit.stock:
        reason = _require_text(stock_change_reason, "stock_change_reason", maximum_length=255)
        quantity_delta = target_stock - current_unit.stock
        if (
            _operations_repo.set_stock_if_unchanged(
                conn,
                unit_id,
                current_unit.stock,
                target_stock,
            )
            != 1
        ):
            raise OperationsConflictError(
                "Inventory changed concurrently. Reload the unit before recording the adjustment."
            )

        now = _now()
        movement_id = _operations_repo.insert_stock_movement(
            conn,
            unit_id=unit_id,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity_delta=quantity_delta,
            stock_before=current_unit.stock,
            stock_after=target_stock,
            reason=reason,
            admin_user_id=admin_user_id,
            created_at=now,
        )
        _admin_user_repo.record_audit(
            conn,
            admin_user_id,
            "stock_adjustment",
            "stock_movement",
            str(movement_id),
        )
        movement = StockMovementRecord(
            id=movement_id,
            unit_id=unit_id,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity_delta=quantity_delta,
            stock_before=current_unit.stock,
            stock_after=target_stock,
            reason=reason,
            admin_user_id=admin_user_id,
            created_at=now,
            updated_at=now,
            unit_name=current_unit.name,
        )

    if (
        initial_stock != current_unit.initial_stock
        or available != current_unit.available
    ):
        _operations_repo.update_unit_operational_settings(
            conn,
            unit_id,
            initial_stock,
            available,
        )
        _admin_user_repo.record_audit(
            conn,
            admin_user_id,
            "unit_operational_settings_updated",
            "unit",
            str(unit_id),
        )

    updated_unit = _operations_repo.find_unit(conn, unit_id)
    if not updated_unit:
        raise OperationsNotFoundError("Unit not found after update")
    logger.info(
        "Updated unit operations: unit_id=%s stock_changed=%s settings_changed=%s",
        unit_id,
        movement is not None,
        (
            initial_stock != current_unit.initial_stock
            or available != current_unit.available
        ),
    )
    return UnitOperationalUpdate(unit=updated_unit, movement=movement)


def delete_unit_without_operations_history(
    conn,
    *,
    unit_id: int,
    admin_user_id: int,
) -> UnitRecord:
    """Delete only a unit with no inventory or maintenance history."""
    unit_id = _require_positive_int(unit_id, "unit_id")
    admin_user_id = _require_positive_int(admin_user_id, "admin_user_id")
    unit = _operations_repo.find_unit(conn, unit_id)
    if not unit:
        raise OperationsNotFoundError("Unit not found")
    if _operations_repo.delete_unit_without_operations_history(conn, unit_id) != 1:
        raise OperationsConflictError(
            "Units with operations history cannot be deleted; mark the unit unavailable instead"
        )
    _admin_user_repo.record_audit(
        conn,
        admin_user_id,
        "unit_deleted",
        "unit",
        str(unit_id),
    )
    logger.info("Deleted unit without operations history: unit_id=%s", unit_id)
    return unit


def create_maintenance_ticket(
    conn,
    *,
    unit_id: int,
    category: str,
    description: str,
    admin_user_id: int,
    source: str = MaintenanceTicketSource.ADMIN,
    assigned_to_admin_user_id: object = _UNSET,
) -> MaintenanceTicketRecord:
    """Open a traceable maintenance ticket without recording user identity."""
    unit_id = _require_positive_int(unit_id, "unit_id")
    admin_user_id = _require_positive_int(admin_user_id, "admin_user_id")
    category = _validate_ticket_category(category)
    source = _validate_ticket_source(source)
    description = _require_text(description, "description", maximum_length=500)
    assignee = (
        None
        if assigned_to_admin_user_id is _UNSET
        else _optional_positive_int(
            assigned_to_admin_user_id,
            "assigned_to_admin_user_id",
        )
    )
    _ensure_assignable_operator(conn, assignee)
    unit = _operations_repo.find_unit(conn, unit_id)
    if not unit:
        raise OperationsNotFoundError("Unit not found")

    now = _now()
    ticket_id = _operations_repo.insert_maintenance_ticket(
        conn,
        unit_id=unit_id,
        category=category,
        source=source,
        description=description,
        opened_by_admin_user_id=admin_user_id,
        assigned_to_admin_user_id=assignee,
        created_at=now,
    )
    _admin_user_repo.record_audit(
        conn,
        admin_user_id,
        "maintenance_ticket_opened",
        "maintenance_ticket",
        str(ticket_id),
    )
    state.record_device_status(
        conn,
        unit.name,
        "maintenance_ticket_opened",
        f"ticket_id={ticket_id}",
    )
    logger.info("Opened maintenance ticket: ticket_id=%s unit_id=%s", ticket_id, unit_id)
    return MaintenanceTicketRecord(
        id=ticket_id,
        unit_id=unit_id,
        category=category,
        status=MaintenanceTicketStatus.OPEN,
        source=source,
        description=description,
        opened_by_admin_user_id=admin_user_id,
        assigned_to_admin_user_id=assignee,
        created_at=now,
        updated_at=now,
        unit_name=unit.name,
    )


def update_maintenance_ticket(
    conn,
    *,
    ticket_id: int,
    status: str,
    admin_user_id: int,
    resolution_note: object = _UNSET,
    assigned_to_admin_user_id: object = _UNSET,
) -> MaintenanceTicketRecord:
    """Move a maintenance ticket through an explicit, auditable state machine."""
    ticket_id = _require_positive_int(ticket_id, "ticket_id")
    admin_user_id = _require_positive_int(admin_user_id, "admin_user_id")
    status = _validate_ticket_status(status)

    current_ticket = _operations_repo.find_ticket(conn, ticket_id)
    if not current_ticket:
        raise OperationsNotFoundError("Maintenance ticket not found")
    _validate_ticket_transition(current_ticket.status, status)

    if resolution_note is _UNSET:
        next_resolution_note = current_ticket.resolution_note
    else:
        next_resolution_note = _optional_text(
            resolution_note,
            "resolution_note",
            maximum_length=500,
        )

    if assigned_to_admin_user_id is _UNSET:
        next_assignee = current_ticket.assigned_to_admin_user_id
    else:
        next_assignee = _optional_positive_int(
            assigned_to_admin_user_id,
            "assigned_to_admin_user_id",
        )
        if next_assignee != current_ticket.assigned_to_admin_user_id:
            _ensure_assignable_operator(conn, next_assignee)

    if status in {MaintenanceTicketStatus.RESOLVED, MaintenanceTicketStatus.CLOSED}:
        if not next_resolution_note:
            raise OperationsValidationError(
                "resolution_note is required when resolving or closing a ticket"
            )
        resolved_by_admin_user_id: int | None = admin_user_id
        resolved_at: str | None = _now()
    else:
        resolved_by_admin_user_id = None
        resolved_at = None

    now = _now()
    if (
        _operations_repo.update_maintenance_ticket(
            conn,
            ticket_id=ticket_id,
            expected_status=current_ticket.status,
            status=status,
            assigned_to_admin_user_id=next_assignee,
            resolution_note=next_resolution_note,
            resolved_by_admin_user_id=resolved_by_admin_user_id,
            updated_at=now,
            resolved_at=resolved_at,
        )
        != 1
    ):
        raise OperationsConflictError("Maintenance ticket changed concurrently")

    _admin_user_repo.record_audit(
        conn,
        admin_user_id,
        f"maintenance_ticket_{status}",
        "maintenance_ticket",
        str(ticket_id),
    )
    unit = _operations_repo.find_unit(conn, current_ticket.unit_id)
    if unit:
        state.record_device_status(
            conn,
            unit.name,
            f"maintenance_ticket_{status}",
            f"ticket_id={ticket_id}",
        )
    updated_ticket = _operations_repo.find_ticket(conn, ticket_id)
    if not updated_ticket:
        raise OperationsNotFoundError("Maintenance ticket not found after update")
    logger.info(
        "Updated maintenance ticket: ticket_id=%s status=%s",
        ticket_id,
        status,
    )
    return updated_ticket


def get_operations_dashboard(
    conn,
    *,
    heartbeat_timeout_seconds: int = 60,
    now: datetime | None = None,
) -> dict:
    """Return one bounded, privacy-safe view for daily operations."""
    if heartbeat_timeout_seconds <= 0:
        raise OperationsValidationError("heartbeat_timeout_seconds must be positive")
    reference_time = now or datetime.now()  # noqa: DTZ005 - legacy DB timestamps are local and naive
    units = _operations_repo.list_units(conn)
    active_tickets = _operations_repo.list_active_tickets(conn)
    tickets_by_unit_id: dict[int, int] = {}
    for ticket in active_tickets:
        tickets_by_unit_id[ticket.unit_id] = tickets_by_unit_id.get(ticket.unit_id, 0) + 1

    out_of_stock_units = [unit for unit in units if unit.stock <= 0]
    heartbeat_overdue_units = [
        unit
        for unit in units
        if _is_heartbeat_overdue(
            unit.last_seen,
            reference_time,
            heartbeat_timeout_seconds,
        )
    ]
    return {
        "units": units,
        "out_of_stock_units": out_of_stock_units,
        "heartbeat_overdue_units": heartbeat_overdue_units,
        "active_tickets": active_tickets,
        "active_ticket_count_by_unit_id": tickets_by_unit_id,
        "recent_stock_movements": _operations_repo.list_recent_stock_movements(conn),
        "heartbeat_timeout_seconds": heartbeat_timeout_seconds,
    }


def list_active_operators(conn) -> list[dict]:
    """Return assignable administrators without exposing authentication material."""
    return _admin_user_repo.list_active(conn)


def _validate_stock_movement_type(value: str) -> str:
    movement_type = str(value or "").strip().lower()
    if movement_type not in StockMovementType.ALL:
        raise OperationsValidationError("movement_type is invalid")
    return movement_type


def _ensure_assignable_operator(conn, admin_user_id: int | None) -> None:
    if admin_user_id is None:
        return
    if not _admin_user_repo.find_active_by_id(conn, admin_user_id):
        raise OperationsValidationError("assigned_to_admin_user_id must be an active administrator")


def _validate_delta_direction(movement_type: str, quantity_delta: int) -> None:
    if movement_type == StockMovementType.RESTOCK and quantity_delta <= 0:
        raise OperationsValidationError("restock requires a positive quantity_delta")
    if movement_type == StockMovementType.DISPOSAL and quantity_delta >= 0:
        raise OperationsValidationError("disposal requires a negative quantity_delta")


def _validate_ticket_category(value: str) -> str:
    category = str(value or "").strip().lower()
    if category not in MaintenanceTicketCategory.ALL:
        raise OperationsValidationError("category is invalid")
    return category


def _validate_ticket_source(value: str) -> str:
    source = str(value or "").strip().lower()
    if source not in MaintenanceTicketSource.ALL:
        raise OperationsValidationError("source is invalid")
    return source


def _validate_ticket_status(value: str) -> str:
    status = str(value or "").strip().lower()
    if status not in MaintenanceTicketStatus.ALL:
        raise OperationsValidationError("status is invalid")
    return status


def _validate_ticket_transition(current_status: str, next_status: str) -> None:
    transitions = {
        MaintenanceTicketStatus.OPEN: {
            MaintenanceTicketStatus.IN_PROGRESS,
            MaintenanceTicketStatus.RESOLVED,
        },
        MaintenanceTicketStatus.IN_PROGRESS: {
            MaintenanceTicketStatus.OPEN,
            MaintenanceTicketStatus.RESOLVED,
        },
        MaintenanceTicketStatus.RESOLVED: {
            MaintenanceTicketStatus.IN_PROGRESS,
            MaintenanceTicketStatus.CLOSED,
        },
        MaintenanceTicketStatus.CLOSED: {MaintenanceTicketStatus.IN_PROGRESS},
    }
    if current_status == next_status:
        return
    if next_status not in transitions.get(current_status, set()):
        raise OperationsConflictError(
            f"Invalid maintenance ticket transition: {current_status} -> {next_status}"
        )


def _require_positive_int(value: object, field_name: str) -> int:
    number = _coerce_int(value, field_name)
    if number <= 0:
        raise OperationsValidationError(f"{field_name} must be positive")
    return number


def _require_nonnegative_int(value: object, field_name: str) -> int:
    number = _coerce_int(value, field_name)
    if number < 0:
        raise OperationsValidationError(f"{field_name} must not be negative")
    return number


def _require_nonzero_int(value: object, field_name: str) -> int:
    number = _coerce_int(value, field_name)
    if number == 0:
        raise OperationsValidationError(f"{field_name} must not be zero")
    return number


def _optional_positive_int(value: object, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    return _require_positive_int(value, field_name)


def _coerce_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise OperationsValidationError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise OperationsValidationError(f"{field_name} must be an integer") from exc


def _require_available_status(value: object) -> int:
    available = _coerce_int(value, "available")
    if available not in {0, 1}:
        raise OperationsValidationError("available must be 0 or 1")
    return available


def _require_text(value: object, field_name: str, *, maximum_length: int) -> str:
    text = _optional_text(value, field_name, maximum_length=maximum_length)
    if not text:
        raise OperationsValidationError(f"{field_name} is required")
    return text


def _optional_text(
    value: object,
    field_name: str,
    *,
    maximum_length: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OperationsValidationError(f"{field_name} must be text")
    text = value.strip()
    if not text:
        return None
    if len(text) > maximum_length:
        raise OperationsValidationError(
            f"{field_name} must be {maximum_length} characters or fewer"
        )
    return text


def _is_heartbeat_overdue(
    last_seen: str | None,
    reference_time: datetime,
    timeout_seconds: int,
) -> bool:
    if not last_seen:
        return True
    try:
        seen_at = datetime.fromisoformat(str(last_seen))
    except ValueError:
        return True
    return (reference_time - seen_at).total_seconds() > timeout_seconds


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # noqa: DTZ005 - legacy DB timestamps are local and naive
