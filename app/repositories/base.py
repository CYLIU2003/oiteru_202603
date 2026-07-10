"""Base repository providing typed database access.

All repository methods operate on an already-opened connection so that
multiple operations can share a single transaction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from db_adapter import db as _db


class BaseRepository:
    """Thin typed wrapper around the db_adapter."""

    @staticmethod
    def fetch_one(conn, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        return _db.fetchone(conn, query, params)

    @staticmethod
    def fetch_all(conn, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        return _db.fetchall(conn, query, params)

    @staticmethod
    def execute(conn, query: str, params: Optional[Tuple] = None) -> Any:
        return _db.execute(conn, query, params)

    @staticmethod
    def insert(conn, query: str, params: Optional[Tuple] = None) -> int:
        return _db.insert(conn, query, params)

    @staticmethod
    def update(conn, query: str, params: Optional[Tuple] = None) -> int:
        return _db.update(conn, query, params)

    @staticmethod
    def delete(conn, query: str, params: Optional[Tuple] = None) -> int:
        return _db.delete(conn, query, params)

    @staticmethod
    def count(conn, query: str, params: Optional[Tuple] = None) -> int:
        row = _db.fetchone(conn, query, params)
        return int(row["count"]) if row and row.get("count") else 0
