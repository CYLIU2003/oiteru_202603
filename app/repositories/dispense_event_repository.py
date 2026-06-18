"""Dispense event repository."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.models.enums import DispenseStatus
from app.models.schemas import DispenseEventRecord
from app.repositories.base import BaseRepository


class DispenseEventRepository(BaseRepository):
    """Data access for ``dispense_events`` table."""

    def find_by_event_id(self, conn, event_id: str) -> Optional[DispenseEventRecord]:
        row = self.fetch_one(
            conn, "SELECT * FROM dispense_events WHERE event_id = ?", (event_id,)
        )
        return DispenseEventRecord.from_row(row) if row else None

    def insert(
        self,
        conn,
        event_id: str,
        unit_name: str,
        card_id: str,
        status: str = DispenseStatus.REQUESTED,
        error_code: Optional[str] = None,
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.insert(
            conn,
            "INSERT INTO dispense_events (event_id, unit_name, card_id, status, error_code, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, unit_name, card_id, status, error_code, now, now),
        )

    def update_status(
        self, conn, event_id: str, status: str, error_code: Optional[str] = None
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.update(
            conn,
            "UPDATE dispense_events SET status = ?, error_code = ?, updated_at = ? WHERE event_id = ?",
            (status, error_code, now, event_id),
        )

    def transition_status(
        self,
        conn,
        event_id: str,
        to_status: str,
        from_statuses: List[str],
        error_code: Optional[str] = None,
    ) -> int:
        """Atomic status transition that checks current status."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, "_build_placeholders"):
            placeholders = ",".join(["?" for _ in from_statuses])
        else:
            placeholders = ",".join(["?" for _ in from_statuses])
        query = (
            "UPDATE dispense_events SET status = ?, error_code = ?, updated_at = ? "
            f"WHERE event_id = ? AND status IN ({placeholders})"
        )
        params = (to_status, error_code, now, event_id) + tuple(from_statuses)
        return self.update(conn, query, params)

    def count_usage_in_period(
        self, conn, card_id: str, period_start: str
    ) -> int:
        return self.count(
            conn,
            "SELECT COUNT(*) as count FROM dispense_events "
            "WHERE card_id = ? AND status = ? AND created_at >= ?",
            (card_id, DispenseStatus.RECORDED, period_start + " 00:00:00"),
        )

    def find_all(self, conn, limit: int = 100) -> List[DispenseEventRecord]:
        rows = self.fetch_all(
            conn,
            "SELECT * FROM dispense_events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [DispenseEventRecord.from_row(r) for r in rows]
