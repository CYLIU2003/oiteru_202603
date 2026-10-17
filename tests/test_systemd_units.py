"""Checks for the parent systemd unit templates and scripts/parent.sh install."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "scripts" / "parent.sh"

# parent.sh is for the Linux production parent. On Windows "bash" is often
# WSL, which cannot run a script by its Windows path.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="parent.sh runs only on Linux",
)


def run_installer(*args):
    return subprocess.run(
        ["bash", str(PARENT), "install", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_templates_have_no_machine_specific_values():
    for unit in ("oiteru-parent.service", "oiteru-card-reader.service"):
        text = (ROOT / "systemd" / unit).read_text(encoding="utf-8")
        assert "hirameki-3" not in text
        assert "@OITERU_ROOT@" in text


def test_dependencies_cannot_stop_parent_for_good():
    """A MySQL upgrade or reader failure must not leave the parent stopped."""
    raw = (ROOT / "systemd" / "oiteru-parent.service").read_text(encoding="utf-8")
    text = "\n".join(line for line in raw.splitlines() if not line.startswith("#"))
    assert "Requires=" not in text
    assert "BindsTo=" not in text
    wants = text.split("\nWants=", 1)[1].splitlines()[0]
    assert "mysql.service" in wants
    assert "oiteru-card-reader.service" in wants
    assert "mysql.service" in text.split("\nAfter=", 1)[1].splitlines()[0]
    assert "Restart=always" in text
    assert "ExecStartPre" not in text
    assert "PermissionsStartOnly" not in text


def test_dry_run_renders_user_and_root(tmp_path):
    result = run_installer("--dry-run", "--user", "oiteru", "--root", str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "@OITERU_" not in result.stdout
    assert "User=oiteru" in result.stdout
    assert f"WorkingDirectory={tmp_path}" in result.stdout
    assert f"ExecStart={tmp_path}/.venv/bin/gunicorn --config {tmp_path}/gunicorn.conf.py wsgi:app" in result.stdout
    assert f"ExecStart=/bin/bash {tmp_path}/scripts/init_card_reader.sh" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--root", "relative/path"),
        ("--root", "/path with space"),
        ("--user", "root"),
        ("--user", "bad;name"),
    ],
)
def test_rejects_unsafe_arguments(args):
    result = run_installer("--dry-run", *args)
    assert result.returncode == 1
    assert "エラー" in result.stderr


def test_parent_help_and_unknown_command():
    help_result = subprocess.run(["bash", str(PARENT), "help"], capture_output=True, text=True, check=False)
    assert help_result.returncode == 0
    for command in ("status", "restart", "logs", "install"):
        assert command in help_result.stdout

    unknown = subprocess.run(["bash", str(PARENT), "start"], capture_output=True, text=True, check=False)
    assert unknown.returncode == 1
    assert "不明なコマンド" in unknown.stderr


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


def test_install_succeeds_with_exit_code_zero(tmp_path):
    """A successful install must end with exit code 0 and no shell error.

    Real sudo/systemctl/curl are replaced so the whole install path runs
    without touching the machine. Regression: the EXIT trap read a function
    local variable after it went out of scope and failed with "unbound
    variable" right after printing that everything was fine.
    """
    import getpass

    user = getpass.getuser()
    if not user or not user[0].isalpha() or user != user.lower() or user == "root":
        pytest.skip("needs an ordinary lowercase login user")

    root = tmp_path / "repo"
    (root / ".venv" / "bin").mkdir(parents=True)
    _stub(root / ".venv" / "bin", "gunicorn", "exit 0")
    (root / ".env").write_text("DB_TYPE=mysql\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "sudo", "exit 0")
    _stub(bin_dir, "systemctl", "exit 0")
    _stub(bin_dir, "tmux", "exit 1")
    _stub(bin_dir, "curl", "echo '{\"status\":\"ok\"}'")

    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    result = subprocess.run(
        ["bash", str(PARENT), "install", "--user", user, "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unbound variable" not in result.stderr
    assert "問題ありません。" in result.stdout
