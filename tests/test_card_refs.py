"""Card UIDs are normalized and stored only as card refs."""

from __future__ import annotations

from contextlib import contextmanager

import pytest

import server
from app import migrations
from app.auth.auth_manager import hash_card_uid, is_card_ref, to_card_ref
from tests.conftest import run_sql

RAW_UID = "0123456789ABCDEF"


def test_uid_case_and_separators_do_not_change_the_card_ref():
    expected = hash_card_uid("0123456789abcdef")
    assert hash_card_uid(RAW_UID) == expected
    assert hash_card_uid("01:23:45:67:89:ab:cd:ef") == expected
    assert to_card_ref(RAW_UID) == expected
    assert to_card_ref(expected) == expected
    assert is_card_ref(expected) and not is_card_ref(RAW_UID)


def _create_tables(conn):
    run_sql(
        conn,
        """CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            card_id VARCHAR(255) UNIQUE NOT NULL,
            card_id_hash VARCHAR(255) DEFAULT '',
            allow TINYINT DEFAULT 1,
            entry VARCHAR(50),
            stock INT DEFAULT 2,
            today INT DEFAULT 0,
            total INT DEFAULT 0,
            last_reset_date DATE
        )""",
    )
    run_sql(
        conn,
        """CREATE TABLE dispense_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id VARCHAR(64) UNIQUE NOT NULL,
            unit_name VARCHAR(255) NOT NULL,
            card_id VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL
        )""",
    )
    run_sql(
        conn,
        """CREATE TABLE history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            txt TEXT NOT NULL,
            type VARCHAR(20) DEFAULT 'usage',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    )


def test_migration_replaces_raw_uids_everywhere(mysql_conn):
    conn = mysql_conn
    _create_tables(conn)
    ref = hash_card_uid(RAW_UID)
    run_sql(conn, "INSERT INTO users (card_id, card_id_hash) VALUES (%s, %s)", (RAW_UID, "stale"))
    run_sql(
        conn,
        "INSERT INTO dispense_events (event_id, unit_name, card_id, status)"
        " VALUES ('e1', 'unit-01', %s, 'recorded')",
        (RAW_UID.lower(),),
    )
    run_sql(conn, "INSERT INTO history (txt) VALUES (%s)", (f"新規登録({RAW_UID})",))

    migrations._migration_011(conn)

    user = run_sql(conn, "SELECT card_id, card_id_hash FROM users")[0]
    assert user == {"card_id": ref, "card_id_hash": ref}
    assert run_sql(conn, "SELECT card_id FROM dispense_events")[0]["card_id"] == ref
    history = run_sql(conn, "SELECT txt FROM history")[0]["txt"]
    assert RAW_UID not in history and RAW_UID.lower() not in history
    assert ref[:12] in history


def test_migration_leaves_a_duplicate_card_for_the_operator(mysql_conn):
    conn = mysql_conn
    _create_tables(conn)
    ref = hash_card_uid(RAW_UID)
    run_sql(conn, "INSERT INTO users (card_id, card_id_hash) VALUES (%s, %s)", (ref, ref))
    run_sql(conn, "INSERT INTO users (card_id, card_id_hash) VALUES (%s, '')", (RAW_UID,))

    migrations._migration_011(conn)

    card_ids = {row["card_id"] for row in run_sql(conn, "SELECT card_id FROM users")}
    assert card_ids == {ref, RAW_UID}


@pytest.fixture
def register_client(mysql_conn, monkeypatch):
    _create_tables(mysql_conn)

    @contextmanager
    def connection():
        yield mysql_conn
        mysql_conn.commit()

    monkeypatch.setattr(server, "get_connection", connection)
    monkeypatch.setattr(server, "add_history", lambda *_args: None)
    monkeypatch.setattr(server, "detect_local_nfc_reader", lambda: (False, "test"))
    return server.app.test_client()


def test_registration_stores_only_the_card_ref(register_client, mysql_conn):
    response = register_client.post("/register", data={"card_id": RAW_UID})

    assert response.status_code == 302
    rows = run_sql(mysql_conn, "SELECT card_id, card_id_hash FROM users")
    ref = hash_card_uid(RAW_UID)
    assert rows == [{"card_id": ref, "card_id_hash": ref}]


def test_usage_lookup_finds_a_card_registered_in_another_case(register_client, mysql_conn):
    register_client.post("/register", data={"card_id": RAW_UID})

    response = register_client.post("/usage", data={"card_id": RAW_UID.lower()})

    assert response.status_code == 200
