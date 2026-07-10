"""History repository."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.models.schemas import HistoryRecord
from app.repositories.base import BaseRepository


class HistoryRepository(BaseRepository):
    """Data access for ``history`` table."""

    def insert(self, conn, message: str, hist_type: str = "usage") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return BaseRepository.insert(
            self,
            conn,
            "INSERT INTO history (txt, type, created_at) VALUES (?, ?, ?)",
            (message, hist_type, now),
        )

    def find_by_type(
        self, conn, hist_type: str, limit: int = 100, since: Optional[str] = None
    ) -> List[HistoryRecord]:
        if since:
            rows = self.fetch_all(
                conn,
                "SELECT * FROM history WHERE type = ? AND created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (hist_type, since, limit),
            )
        else:
            rows = self.fetch_all(
                conn,
                "SELECT * FROM history WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (hist_type, limit),
            )
        return [HistoryRecord.from_row(r) for r in rows]

    def count_success_since(self, conn, since: str) -> int:
        return self.count(
            conn,
            "SELECT COUNT(*) as count FROM history WHERE type = 'success' AND created_at >= ?",
            (since,),
        )

    def find_all_success_recent(self, conn, limit: int = 100) -> List[HistoryRecord]:
        return self.find_by_type(conn, "success", limit=limit)

    def find_all_success_since(
        self, conn, since: str, limit: Optional[int] = None
    ) -> List[HistoryRecord]:
        query = "SELECT txt, created_at FROM history WHERE type = 'success' AND created_at >= ? ORDER BY created_at DESC"
        params = (since,)
        if limit is not None:
            query += " LIMIT ?"
            params = (since, limit)
        rows = self.fetch_all(conn, query, params)
        return [HistoryRecord.from_row(r) for r in rows]

    def delete_all(self, conn) -> int:
        return self.delete(conn, "DELETE FROM history")
