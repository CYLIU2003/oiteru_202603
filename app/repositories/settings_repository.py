"""Settings & Info repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.schemas import InfoRecord, SettingsRecord
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository):
    """Data access for ``settings`` table."""

    def find(self, conn) -> Optional[SettingsRecord]:
        row = self.fetch_one(conn, "SELECT * FROM settings WHERE id = 1")
        return SettingsRecord.from_row(row) if row else None

    def upsert(
        self,
        conn,
        auto_register_mode: bool,
        auto_register_stock: int,
        usage_limit: int,
        limit_period: str,
        version: int,
    ) -> int:
        existing = self.fetch_one(conn, "SELECT id FROM settings WHERE id = 1")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        auto_flag = 1 if auto_register_mode else 0

        if existing:
            return self.update(
                conn,
                """UPDATE settings SET
                    auto_register_mode = ?, auto_register_stock = ?,
                    usage_limit = ?, limit_period = ?, version = ?, updated_at = ?
                   WHERE id = 1""",
                (auto_flag, auto_register_stock, usage_limit, limit_period, version, now),
            )
        else:
            return self.insert(
                conn,
                """INSERT INTO settings
                   (id, auto_register_mode, auto_register_stock, usage_limit, limit_period, version, updated_at)
                   VALUES (1, ?, ?, ?, ?, ?, ?)""",
                (auto_flag, auto_register_stock, usage_limit, limit_period, version, now),
            )


class InfoRepository(BaseRepository):
    """Data access for ``info`` table."""

    def find(self, conn) -> Optional[InfoRecord]:
        row = self.fetch_one(conn, "SELECT * FROM info WHERE id = 1")
        return InfoRecord.from_row(row) if row else None

    def insert_or_update(self, conn, password_hash: str) -> int:
        existing = self.fetch_one(conn, "SELECT id FROM info WHERE id = 1")
        if existing:
            return self.update(
                conn, "UPDATE info SET pass = ? WHERE id = 1", (password_hash,)
            )
        return self.insert(
            conn, "INSERT INTO info (id, pass) VALUES (1, ?)", (password_hash,)
        )
