"""Tests for inventory and maintenance operational safeguards."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models.enums import (
    MaintenanceTicketStatus,
    StockMovementType,
)
from app.models.schemas import MaintenanceTicketRecord, UnitRecord
from app.services import operations_service


class FakeInventoryRepository:
    def __init__(self, stock: int = 7):
        self.stock = stock
        self.inserted_movement = None

    def find_unit(self, _conn, unit_id):
        if unit_id != 3:
            return None
        return UnitRecord(
            id=3,
            name="unit-03",
            password="not-exposed",
            stock=self.stock,
            initial_stock=20,
            available=1,
        )

    def apply_stock_delta(self, _conn, unit_id, quantity_delta):
        assert unit_id == 3
        if self.stock + quantity_delta < 0:
            return 0
        self.stock += quantity_delta
        return 1

    def insert_stock_movement(self, _conn, **kwargs):
        self.inserted_movement = kwargs
        return 41


def test_restock_records_before_after_and_admin_audit(monkeypatch):
    repository = FakeInventoryRepository(stock=7)
    audit_calls = []
    monkeypatch.setattr(operations_service, "_operations_repo", repository)
    monkeypatch.setattr(
        operations_service._admin_user_repo,
        "record_audit",
        lambda *args: audit_calls.append(args),
    )

    movement = operations_service.record_stock_movement(
        object(),
        unit_id=3,
        movement_type=StockMovementType.RESTOCK,
        quantity_delta=5,
        reason="scheduled refill",
        admin_user_id=9,
    )

    assert movement.id == 41
    assert movement.stock_before == 7
    assert movement.stock_after == 12
    assert movement.quantity_delta == 5
    assert repository.inserted_movement["stock_before"] == 7
    assert repository.inserted_movement["stock_after"] == 12
    assert audit_calls[0][2] == "stock_restock"
    assert audit_calls[0][4] == "41"


def test_stock_movement_rejects_negative_result_without_writing_history(monkeypatch):
    repository = FakeInventoryRepository(stock=2)
    monkeypatch.setattr(operations_service, "_operations_repo", repository)

    with pytest.raises(operations_service.OperationsConflictError):
        operations_service.record_stock_movement(
            object(),
            unit_id=3,
            movement_type=StockMovementType.DISPOSAL,
            quantity_delta=-3,
            reason="damaged stock",
            admin_user_id=9,
        )

    assert repository.inserted_movement is None


def test_manual_stock_update_refuses_stale_overwrite(monkeypatch):
    class StaleInventoryRepository(FakeInventoryRepository):
        def set_stock_if_unchanged(self, *_args):
            return 0

    repository = StaleInventoryRepository(stock=7)
    monkeypatch.setattr(operations_service, "_operations_repo", repository)

    with pytest.raises(operations_service.OperationsConflictError):
        operations_service.update_unit_operational_state(
            object(),
            unit_id=3,
            target_stock=12,
            initial_stock=20,
            available=1,
            stock_change_reason="inventory count",
            admin_user_id=9,
        )


def test_unit_with_operations_history_cannot_be_deleted(monkeypatch):
    class HistoryAwareRepository:
        def find_unit(self, _conn, unit_id):
            return UnitRecord(id=unit_id, name="unit-03", password="not-exposed")

        def delete_unit_without_operations_history(self, _conn, _unit_id):
            return 0

    monkeypatch.setattr(
        operations_service, "_operations_repo", HistoryAwareRepository()
    )

    with pytest.raises(operations_service.OperationsConflictError, match="history"):
        operations_service.delete_unit_without_operations_history(
            object(),
            unit_id=3,
            admin_user_id=9,
        )


def test_resolving_ticket_requires_recovery_note(monkeypatch):
    class TicketRepository:
        def find_ticket(self, _conn, ticket_id):
            return MaintenanceTicketRecord(
                id=ticket_id,
                unit_id=3,
                category="jam",
                status=MaintenanceTicketStatus.IN_PROGRESS,
                source="admin",
                description="jammed",
            )

    monkeypatch.setattr(operations_service, "_operations_repo", TicketRepository())

    with pytest.raises(operations_service.OperationsValidationError):
        operations_service.update_maintenance_ticket(
            object(),
            ticket_id=8,
            status=MaintenanceTicketStatus.RESOLVED,
            resolution_note="",
            admin_user_id=9,
        )


def test_ticket_resolution_is_state_checked_and_audited(monkeypatch):
    class TicketRepository:
        def __init__(self):
            self.updated = None
            self.after_update = False

        def find_ticket(self, _conn, ticket_id):
            if self.after_update:
                return MaintenanceTicketRecord(
                    id=ticket_id,
                    unit_id=3,
                    category="jam",
                    status=MaintenanceTicketStatus.RESOLVED,
                    source="admin",
                    description="jammed",
                    resolution_note="cleared and tested",
                    resolved_by_admin_user_id=9,
                )
            return MaintenanceTicketRecord(
                id=ticket_id,
                unit_id=3,
                category="jam",
                status=MaintenanceTicketStatus.IN_PROGRESS,
                source="admin",
                description="jammed",
            )

        def update_maintenance_ticket(self, _conn, **kwargs):
            self.updated = kwargs
            self.after_update = True
            return 1

        def find_unit(self, _conn, unit_id):
            return UnitRecord(
                id=unit_id,
                name="unit-03",
                password="not-exposed",
            )

    repository = TicketRepository()
    audit_calls = []
    device_status_calls = []
    monkeypatch.setattr(operations_service, "_operations_repo", repository)
    monkeypatch.setattr(
        operations_service._admin_user_repo,
        "record_audit",
        lambda *args: audit_calls.append(args),
    )
    monkeypatch.setattr(
        operations_service.state,
        "record_device_status",
        lambda *args: device_status_calls.append(args),
    )

    ticket = operations_service.update_maintenance_ticket(
        object(),
        ticket_id=8,
        status=MaintenanceTicketStatus.RESOLVED,
        resolution_note="cleared and tested",
        admin_user_id=9,
    )

    assert ticket.status == MaintenanceTicketStatus.RESOLVED
    assert repository.updated["expected_status"] == MaintenanceTicketStatus.IN_PROGRESS
    assert repository.updated["resolved_by_admin_user_id"] == 9
    assert repository.updated["resolution_note"] == "cleared and tested"
    assert audit_calls[0][2] == "maintenance_ticket_resolved"
    assert device_status_calls[0][2] == "maintenance_ticket_resolved"


def test_ticket_can_be_resolved_when_an_existing_assignee_is_now_inactive(monkeypatch):
    class TicketRepository:
        def __init__(self):
            self.after_update = False

        def find_ticket(self, _conn, ticket_id):
            return MaintenanceTicketRecord(
                id=ticket_id,
                unit_id=3,
                category="jam",
                status=(
                    MaintenanceTicketStatus.RESOLVED
                    if self.after_update
                    else MaintenanceTicketStatus.IN_PROGRESS
                ),
                source="admin",
                description="jammed",
                assigned_to_admin_user_id=44,
                resolution_note=(
                    "cleared and tested" if self.after_update else None
                ),
                resolved_by_admin_user_id=9 if self.after_update else None,
            )

        def update_maintenance_ticket(self, _conn, **_kwargs):
            self.after_update = True
            return 1

        def find_unit(self, _conn, unit_id):
            return UnitRecord(id=unit_id, name="unit-03", password="not-exposed")

    repository = TicketRepository()
    monkeypatch.setattr(operations_service, "_operations_repo", repository)
    monkeypatch.setattr(
        operations_service._admin_user_repo,
        "find_active_by_id",
        lambda *_args: pytest.fail("existing assignee must not block ticket closure"),
    )
    monkeypatch.setattr(
        operations_service._admin_user_repo, "record_audit", lambda *_args: None
    )
    monkeypatch.setattr(
        operations_service.state, "record_device_status", lambda *_args: None
    )

    ticket = operations_service.update_maintenance_ticket(
        object(),
        ticket_id=8,
        status=MaintenanceTicketStatus.RESOLVED,
        resolution_note="cleared and tested",
        assigned_to_admin_user_id=44,
        admin_user_id=9,
    )

    assert ticket.status == MaintenanceTicketStatus.RESOLVED


def test_new_ticket_rejects_an_inactive_assignee(monkeypatch):
    monkeypatch.setattr(
        operations_service._admin_user_repo, "find_active_by_id", lambda *_args: None
    )

    with pytest.raises(
        operations_service.OperationsValidationError,
        match="active administrator",
    ):
        operations_service.create_maintenance_ticket(
            object(),
            unit_id=3,
            category="jam",
            description="jammed",
            admin_user_id=9,
            assigned_to_admin_user_id=44,
        )


def test_dashboard_reuses_existing_sixty_second_heartbeat_contract(monkeypatch):
    class DashboardRepository:
        def list_units(self, _conn):
            return [
                UnitRecord(
                    id=1,
                    name="online",
                    password="not-exposed",
                    stock=2,
                    last_seen="2026-08-11 10:00:30",
                ),
                UnitRecord(
                    id=2,
                    name="empty-and-stale",
                    password="not-exposed",
                    stock=0,
                    last_seen="2026-08-11 09:58:00",
                ),
            ]

        def list_active_tickets(self, _conn):
            return []

        def list_recent_stock_movements(self, _conn):
            return []

    monkeypatch.setattr(operations_service, "_operations_repo", DashboardRepository())

    dashboard = operations_service.get_operations_dashboard(
        object(),
        now=datetime(2026, 8, 11, 10, 1, 0),  # noqa: DTZ001 - mirrors existing local heartbeat records
    )

    assert [unit.name for unit in dashboard["out_of_stock_units"]] == [
        "empty-and-stale"
    ]
    assert [unit.name for unit in dashboard["heartbeat_overdue_units"]] == [
        "empty-and-stale"
    ]
