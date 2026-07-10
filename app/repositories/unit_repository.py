"""Unit (child device) repository."""

from __future__ import annotations

from typing import List, Optional

from app.models.enums import UnitAvailableStatus, UnitConnectStatus
from app.models.schemas import UnitRecord
from app.repositories.base import BaseRepository


class UnitRepository(BaseRepository):
    """Data access for ``units`` table."""

    def find_by_name(self, conn, name: str) -> Optional[UnitRecord]:
        row = self.fetch_one(
            conn, "SELECT * FROM units WHERE name = ?", (name,)
        )
        return UnitRecord.from_row(row) if row else None

    def find_by_id(self, conn, uid: int) -> Optional[UnitRecord]:
        row = self.fetch_one(
            conn, "SELECT * FROM units WHERE id = ?", (uid,)
        )
        return UnitRecord.from_row(row) if row else None

    def find_all(self, conn) -> List[UnitRecord]:
        rows = self.fetch_all(conn, "SELECT * FROM units")
        return [UnitRecord.from_row(r) for r in rows]

    def find_recently_active(self, conn, seconds: int = 60) -> List[UnitRecord]:
        if hasattr(self, "_db_type") and getattr(self, "_db_type", None) == "mysql":
            from db_adapter import DB_TYPE
            if DB_TYPE == "mysql":
                rows = self.fetch_all(
                    conn,
                    """
                    SELECT name, last_seen, stock, connect,
                           TIMESTAMPDIFF(SECOND, last_seen, NOW()) as seconds_ago
                    FROM units
                    WHERE last_seen IS NOT NULL
                      AND TIMESTAMPDIFF(SECOND, last_seen, NOW()) < ?
                    ORDER BY last_seen DESC
                    """,
                    (seconds,),
                )
            else:
                rows = self.fetch_all(
                    conn,
                    """
                    SELECT name, last_seen, stock, connect,
                           (julianday('now') - julianday(last_seen)) * 86400.0 as seconds_ago
                    FROM units
                    WHERE last_seen IS NOT NULL
                      AND (julianday('now') - julianday(last_seen)) * 86400.0 < ?
                    ORDER BY last_seen DESC
                    """,
                    (seconds,),
                )
        else:
            rows = self.fetch_all(
                conn,
                """
                SELECT name, last_seen, stock, connect,
                       (julianday('now') - julianday(last_seen)) * 86400.0 as seconds_ago
                FROM units
                WHERE last_seen IS NOT NULL
                  AND (julianday('now') - julianday(last_seen)) * 86400.0 < ?
                ORDER BY last_seen DESC
                """,
                (seconds,),
            )
        return [UnitRecord.from_row(r) for r in rows]

    def count_all(self, conn) -> int:
        return self.count(conn, "SELECT COUNT(*) as count FROM units")

    def insert(
        self,
        conn,
        name: str,
        password: str,
        stock: int = 0,
        initial_stock: int = 100,
        connect: int = UnitConnectStatus.ONLINE,
        available: int = UnitAvailableStatus.AVAILABLE,
        ip_address: Optional[str] = None,
    ) -> int:
        return self.insert(
            conn,
            "INSERT INTO units (name, password, stock, initial_stock, connect, available, ip_address) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, password, stock, initial_stock, connect, available, ip_address),
        )

    def update_heartbeat(
        self, conn, name: str, last_seen: str, ip_address: str
    ) -> int:
        return self.update(
            conn,
            "UPDATE units SET connect = 1, last_seen = ?, ip_address = ? WHERE name = ?",
            (last_seen, ip_address, name),
        )

    def update_by_id(
        self, conn, uid: int, *, stock: int, initial_stock: int, available: int
    ) -> int:
        return self.update(
            conn,
            "UPDATE units SET stock = ?, initial_stock = ?, available = ? WHERE id = ?",
            (stock, initial_stock, available, uid),
        )

    def update_stock(self, conn, name: str, stock: int) -> int:
        return self.update(
            conn, "UPDATE units SET stock = ? WHERE name = ?", (stock, name)
        )

    def set_available(self, conn, name: str, available: int) -> int:
        return self.update(
            conn, "UPDATE units SET available = ? WHERE name = ?", (available, name)
        )

    def toggle_available(self, conn, uid: int) -> Optional[int]:
        unit = self.find_by_id(conn, uid)
        if not unit:
            return None
        new_val = (
            UnitAvailableStatus.UNAVAILABLE
            if unit.available == UnitAvailableStatus.AVAILABLE
            else UnitAvailableStatus.AVAILABLE
        )
        self.update(
            conn,
            "UPDATE units SET available = ? WHERE id = ?",
            (new_val, uid),
        )
        return new_val

    def delete_by_id(self, conn, uid: int) -> int:
        return self.delete(conn, "DELETE FROM units WHERE id = ?", (uid,))
