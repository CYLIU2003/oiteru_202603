"""Repository for individually authenticated administrative users."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.repositories.base import BaseRepository


class AdminUserRepository(BaseRepository):
    def find_by_username(self, conn, username: str) -> Optional[dict]:
        return self.fetch_one(
            conn,
            "SELECT * FROM admin_users WHERE username = ? AND is_active = 1",
            (username,),
        )

    def upsert_bootstrap_user(
        self, conn, username: str, password_hash: str, role: str = "administrator"
    ) -> None:
        existing = self.fetch_one(
            conn, "SELECT id FROM admin_users WHERE username = ?", (username,)
        )
        if existing:
            self.update(
                conn,
                """UPDATE admin_users
                      SET password_hash = ?, role = ?, is_active = 1, updated_at = ?
                    WHERE id = ?""",
                (password_hash, role, _now(), existing["id"]),
            )
            return
        self.insert(
            conn,
            """INSERT INTO admin_users
               (username, password_hash, role, is_active, created_at, updated_at)
               VALUES (?, ?, ?, 1, ?, ?)""",
            (username, password_hash, role, _now(), _now()),
        )

    def record_login(self, conn, user_id: int) -> None:
        self.update(
            conn,
            "UPDATE admin_users SET last_login_at = ? WHERE id = ?",
            (_now(), user_id),
        )

    def record_audit(
        self,
        conn,
        admin_user_id: int | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> None:
        self.insert(
            conn,
            """INSERT INTO admin_audit_logs
               (admin_user_id, action, target_type, target_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (admin_user_id, action, target_type, target_id, _now()),
        )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
