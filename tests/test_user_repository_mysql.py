"""MySQL behaviour of user allowance updates."""

from __future__ import annotations

from app.repositories.user_repository import UserRepository
from tests.conftest import run_sql


def test_restore_stock_and_total_never_makes_total_negative(mysql_conn):
    run_sql(
        mysql_conn,
        """CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            card_id VARCHAR(255) UNIQUE NOT NULL,
            allow TINYINT DEFAULT 1,
            stock INT DEFAULT 0,
            total INT DEFAULT 0
        )""",
    )
    run_sql(mysql_conn, "INSERT INTO users (card_id, stock, total) VALUES ('ref-1', 0, 0)")

    assert UserRepository().restore_stock_and_total(mysql_conn, "ref-1") == 1

    row = run_sql(mysql_conn, "SELECT stock, total FROM users WHERE card_id = 'ref-1'")[0]
    assert (row["stock"], row["total"]) == (1, 0)
