"""Regression tests for repository insert and lookup contracts."""

from __future__ import annotations

import pytest

from app.repositories.base import BaseRepository
from app.repositories.dispense_event_repository import DispenseEventRepository
from app.repositories.history_repository import HistoryRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.parametrize(
    ("repository", "args", "expected_table"),
    [
        (
            UserRepository(),
            ("TEST-CARD-0001", "2026-07-29 12:00", 2),
            "users",
        ),
        (
            UnitRepository(),
            ("unit-01", "hashed-secret"),
            "units",
        ),
        (
            DispenseEventRepository(),
            ("event-0001", "unit-01", "TEST-CARD-0001"),
            "dispense_events",
        ),
    ],
)
def test_repository_insert_delegates_to_base(monkeypatch, repository, args, expected_table):
    """Repository inserts must call BaseRepository instead of themselves."""
    captured = {}

    def fake_insert(conn, query, params=None):
        captured.update(conn=conn, query=query, params=params)
        return 42

    monkeypatch.setattr(BaseRepository, "insert", staticmethod(fake_insert))
    connection = object()

    assert repository.insert(connection, *args) == 42
    assert captured["conn"] is connection
    assert f"INSERT INTO {expected_table}" in captured["query"]


def test_user_repository_register_and_find(monkeypatch):
    """A registered user can be looked up through the repository contract."""
    inserted = {}
    row = {
        "id": 7,
        "card_id": "TEST-CARD-0001",
        "card_id_hash": "test-hash",
        "entry": "2026-07-29 12:00",
        "stock": 2,
        "allow": 1,
        "total": 0,
        "last_reset_date": "2026-07-29",
    }

    def fake_insert(conn, query, params=None):
        inserted.update(conn=conn, query=query, params=params)
        return row["id"]

    monkeypatch.setattr(BaseRepository, "insert", staticmethod(fake_insert))
    monkeypatch.setattr(BaseRepository, "fetch_one", staticmethod(lambda conn, query, params=None: row))
    connection = object()
    repo = UserRepository()

    user_id = repo.insert(
        connection,
        card_id=row["card_id"],
        entry=row["entry"],
        stock=2,
        card_id_hash=row["card_id_hash"],
        last_reset_date=row["last_reset_date"],
    )
    user = repo.find_by_card_id(connection, row["card_id"])

    assert user_id == row["id"]
    assert inserted["conn"] is connection
    assert user is not None
    assert user.id == row["id"]
    assert user.card_id_hash == row["card_id_hash"]


def test_history_repository_insert_uses_supplied_connection(monkeypatch):
    """History writes participate in the caller's transaction."""
    captured = {}

    def fake_insert(conn, query, params=None):
        captured.update(conn=conn, query=query, params=params)
        return 9

    monkeypatch.setattr(BaseRepository, "insert", staticmethod(fake_insert))
    connection = object()

    assert HistoryRepository().insert(connection, "test message", "system") == 9
    assert captured["conn"] is connection
    assert captured["params"][0] == "test message"
    assert captured["params"][1] == "system"
