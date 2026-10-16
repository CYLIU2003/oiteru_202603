"""Round-trip encrypted backups using the database-scoped application privileges."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    sys.platform == "win32"
    or any(shutil.which(name) is None for name in ("bash", "mysqldump", "mysql", "openssl", "gzip")),
    reason="MySQL backup scripts require the Linux command-line tools",
)


def test_encrypted_backup_restores_data_without_global_process_privilege(mysql_conn, tmp_path):
    username = "backup_test_" + secrets.token_hex(4)
    password = secrets.token_hex(24)
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT DATABASE() AS name")
        database = cursor.fetchone()["name"]
        cursor.execute("CREATE TABLE backup_example (id INT PRIMARY KEY, quantity INT NOT NULL)")
        cursor.execute("INSERT INTO backup_example VALUES (1, 3)")
        cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (username, password))
    mysql_conn.commit()
    try:
        with mysql_conn.cursor() as cursor:
            identifier = database.replace("`", "``")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{identifier}`.* TO %s@'localhost'", (username,))
        mysql_conn.commit()
        env_file = tmp_path / "backup.env"
        settings = {
            "MYSQL_HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
            "MYSQL_USER": username,
            "MYSQL_PASSWORD": password,
            "MYSQL_DATABASE": database,
        }
        # Quote configuration as shell data; real credentials never enter argv.
        env_file.write_text(
            "\n".join(f"{key}={shlex.quote(value)}" for key, value in settings.items()) + "\n",
            encoding="utf-8",
        )
        env_file.chmod(0o600)
        backup_dir = tmp_path / "backups"
        environment = dict(
            os.environ,
            OITERU_ENV_FILE=str(env_file),
            OITERU_BACKUP_DIR=str(backup_dir),
            OITERU_BACKUP_KEY=secrets.token_hex(32),
        )
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/backup_mysql.sh")],
            env=environment, capture_output=True, text=True, check=False, timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "Access denied" not in result.stderr
        assert "Encrypted backup created:" in result.stdout
        backups = list(backup_dir.glob("*.sql.gz.enc"))
        assert len(backups) == 1
        assert backups[0].stat().st_mode & 0o777 == 0o600
        with mysql_conn.cursor() as cursor:
            cursor.execute("UPDATE backup_example SET quantity = 99 WHERE id = 1")
        mysql_conn.commit()
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/restore_mysql.sh"), str(backups[0])],
            env=environment, input="RESTORE\n", capture_output=True, text=True,
            check=False, timeout=60,
        )
        assert result.returncode == 0, result.stderr
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT quantity FROM backup_example WHERE id = 1")
            assert cursor.fetchone()["quantity"] == 3
    finally:
        with mysql_conn.cursor() as cursor:
            cursor.execute("DROP USER IF EXISTS %s@'localhost'", (username,))
        mysql_conn.commit()
