"""Repository for inventory movements and maintenance tickets."""

from __future__ import annotations

from app.models.enums import MaintenanceTicketStatus
from app.models.schemas import (
    MaintenanceTicketRecord,
    StockMovementRecord,
    UnitRecord,
)
from app.repositories.base import BaseRepository


class OperationsRepository(BaseRepository):
    """Database access for the daily operations domain."""

    def find_unit(self, conn, unit_id: int) -> UnitRecord | None:
        row = self.fetch_one(conn, "SELECT * FROM units WHERE id = ?", (unit_id,))
        return UnitRecord.from_row(row) if row else None

    def list_units(self, conn) -> list[UnitRecord]:
        rows = self.fetch_all(conn, "SELECT * FROM units ORDER BY name ASC")
        return [UnitRecord.from_row(row) for row in rows]

    def apply_stock_delta(self, conn, unit_id: int, quantity_delta: int) -> int:
        """Apply a signed stock delta without allowing inventory below zero."""
        return self.update(
            conn,
            """UPDATE units
                  SET stock = stock + ?
                WHERE id = ? AND stock + ? >= 0""",
            (quantity_delta, unit_id, quantity_delta),
        )

    def set_stock_if_unchanged(
        self,
        conn,
        unit_id: int,
        expected_stock: int,
        target_stock: int,
    ) -> int:
        """Set stock only when no concurrent dispense changed the observed value."""
        return self.update(
            conn,
            "UPDATE units SET stock = ? WHERE id = ? AND stock = ?",
            (target_stock, unit_id, expected_stock),
        )

    def update_unit_operational_settings(
        self,
        conn,
        unit_id: int,
        initial_stock: int,
        available: int,
    ) -> int:
        return self.update(
            conn,
            """UPDATE units
                  SET initial_stock = ?, available = ?
                WHERE id = ?""",
            (initial_stock, available, unit_id),
        )

    def delete_unit_without_operations_history(self, conn, unit_id: int) -> int:
        """Delete a unit only if no durable operations record refers to it."""
        return self.delete(
            conn,
            """DELETE FROM units
                WHERE id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM stock_movements WHERE unit_id = ?
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM maintenance_tickets WHERE unit_id = ?
                  )""",
            (unit_id, unit_id, unit_id),
        )

    def insert_stock_movement(
        self,
        conn,
        *,
        unit_id: int,
        movement_type: str,
        quantity_delta: int,
        stock_before: int,
        stock_after: int,
        reason: str,
        admin_user_id: int,
        created_at: str,
    ) -> int:
        return self.insert(
            conn,
            """INSERT INTO stock_movements
               (unit_id, movement_type, quantity_delta, stock_before, stock_after,
                reason, admin_user_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unit_id,
                movement_type,
                quantity_delta,
                stock_before,
                stock_after,
                reason,
                admin_user_id,
                created_at,
                created_at,
            ),
        )

    def find_ticket(self, conn, ticket_id: int) -> MaintenanceTicketRecord | None:
        row = self.fetch_one(
            conn,
            "SELECT * FROM maintenance_tickets WHERE id = ?",
            (ticket_id,),
        )
        return MaintenanceTicketRecord.from_row(row) if row else None

    def insert_maintenance_ticket(
        self,
        conn,
        *,
        unit_id: int,
        category: str,
        source: str,
        description: str,
        opened_by_admin_user_id: int,
        assigned_to_admin_user_id: int | None,
        created_at: str,
    ) -> int:
        return self.insert(
            conn,
            """INSERT INTO maintenance_tickets
               (unit_id, category, status, source, description,
                opened_by_admin_user_id, assigned_to_admin_user_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unit_id,
                category,
                MaintenanceTicketStatus.OPEN,
                source,
                description,
                opened_by_admin_user_id,
                assigned_to_admin_user_id,
                created_at,
                created_at,
            ),
        )

    def update_maintenance_ticket(
        self,
        conn,
        *,
        ticket_id: int,
        expected_status: str,
        status: str,
        assigned_to_admin_user_id: int | None,
        resolution_note: str | None,
        resolved_by_admin_user_id: int | None,
        updated_at: str,
        resolved_at: str | None,
    ) -> int:
        return self.update(
            conn,
            """UPDATE maintenance_tickets
                  SET status = ?,
                      assigned_to_admin_user_id = ?,
                      resolution_note = ?,
                      resolved_by_admin_user_id = ?,
                      updated_at = ?,
                      resolved_at = ?
                WHERE id = ? AND status = ?""",
            (
                status,
                assigned_to_admin_user_id,
                resolution_note,
                resolved_by_admin_user_id,
                updated_at,
                resolved_at,
                ticket_id,
                expected_status,
            ),
        )

    def list_active_tickets(
        self,
        conn,
        limit: int = 100,
    ) -> list[MaintenanceTicketRecord]:
        rows = self.fetch_all(
            conn,
            """SELECT mt.*, u.name AS unit_name,
                      assignee.username AS assigned_to_username
                 FROM maintenance_tickets AS mt
                 JOIN units AS u ON u.id = mt.unit_id
                 LEFT JOIN admin_users AS assignee
                   ON assignee.id = mt.assigned_to_admin_user_id
                WHERE mt.status IN (?, ?, ?)
                ORDER BY mt.created_at ASC, mt.id ASC
                LIMIT ?""",
            (
                MaintenanceTicketStatus.OPEN,
                MaintenanceTicketStatus.IN_PROGRESS,
                MaintenanceTicketStatus.RESOLVED,
                limit,
            ),
        )
        return [MaintenanceTicketRecord.from_row(row) for row in rows]

    def list_recent_stock_movements(
        self,
        conn,
        limit: int = 20,
    ) -> list[StockMovementRecord]:
        rows = self.fetch_all(
            conn,
            """SELECT sm.*, u.name AS unit_name,
                      operator_account.username AS admin_username
                 FROM stock_movements AS sm
                 JOIN units AS u ON u.id = sm.unit_id
                 LEFT JOIN admin_users AS operator_account
                   ON operator_account.id = sm.admin_user_id
                ORDER BY sm.created_at DESC, sm.id DESC
                LIMIT ?""",
            (limit,),
        )
        return [StockMovementRecord.from_row(row) for row in rows]
