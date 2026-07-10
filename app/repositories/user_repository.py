"""User repository."""

from __future__ import annotations

from typing import List, Optional

from app.models.enums import UserAllowStatus
from app.models.schemas import UserRecord
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access for ``users`` table."""

    def find_by_card_id(self, conn, card_id: str) -> Optional[UserRecord]:
        row = self.fetch_one(
            conn, "SELECT * FROM users WHERE card_id = ?", (card_id,)
        )
        return UserRecord.from_row(row) if row else None

    def find_by_id(self, conn, uid: int) -> Optional[UserRecord]:
        row = self.fetch_one(
            conn, "SELECT * FROM users WHERE id = ?", (uid,)
        )
        return UserRecord.from_row(row) if row else None

    def find_all(self, conn) -> List[UserRecord]:
        rows = self.fetch_all(conn, "SELECT * FROM users")
        return [UserRecord.from_row(r) for r in rows]

    def count_all(self, conn) -> int:
        return self.count(conn, "SELECT COUNT(*) as count FROM users")

    def insert(
        self,
        conn,
        card_id: str,
        entry: str,
        stock: int,
        allow: int = UserAllowStatus.ALLOWED,
        card_id_hash: str = "",
        last_reset_date: Optional[str] = None,
    ) -> int:
        return self.insert(
            conn,
            "INSERT INTO users (card_id, card_id_hash, entry, stock, allow, last_reset_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (card_id, card_id_hash, entry, stock, allow, last_reset_date),
        )

    def update_by_id(
        self, conn, uid: int, *, card_id: str, allow: int, stock: int
    ) -> int:
        return self.update(
            conn,
            "UPDATE users SET card_id = ?, allow = ?, stock = ? WHERE id = ?",
            (card_id, allow, stock, uid),
        )

    def update_stock(self, conn, card_id: str, stock: int) -> int:
        return self.update(
            conn, "UPDATE users SET stock = ? WHERE card_id = ?", (stock, card_id)
        )

    def update_stock_and_total(
        self, conn, card_id: str, stock: int, total: int
    ) -> int:
        return self.update(
            conn,
            "UPDATE users SET stock = ?, total = ? WHERE card_id = ?",
            (stock, total, card_id),
        )

    def update_last_reset_date(
        self, conn, card_id: str, reset_date: str
    ) -> int:
        return self.update(
            conn,
            "UPDATE users SET last_reset_date = ? WHERE card_id = ?",
            (reset_date, card_id),
        )

    def update_stock_and_reset_date(
        self, conn, card_id: str, stock: int, reset_date: str
    ) -> int:
        return self.update(
            conn,
            "UPDATE users SET stock = ?, last_reset_date = ? WHERE card_id = ?",
            (stock, reset_date, card_id),
        )

    def update_allow(self, conn, uid: int, allow: int) -> int:
        return self.update(
            conn, "UPDATE users SET allow = ? WHERE id = ?", (allow, uid)
        )

    def delete_by_id(self, conn, uid: int) -> int:
        return self.delete(conn, "DELETE FROM users WHERE id = ?", (uid,))

    def update_last_reset_date_null(self, conn) -> int:
        """Set last_reset_date to today for users where it is NULL."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        return self.update(
            conn,
            "UPDATE users SET last_reset_date = ? WHERE last_reset_date IS NULL",
            (today,),
        )
