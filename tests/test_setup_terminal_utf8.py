"""scripts/setup_terminal_utf8.sh must be safe to run more than once."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup_terminal_utf8.sh"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="runs on Linux only",
)


def _run(home: Path) -> subprocess.CompletedProcess:
    env = {"HOME": str(home), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, check=False)


def test_adds_one_block_before_the_interactive_guard_and_is_idempotent(tmp_path):
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text('case $- in\n    *i*) ;;\n      *) return;;\nesac\nalias ll="ls -l"\n', encoding="utf-8")
    (tmp_path / ".profile").write_text("# profile\n", encoding="utf-8")

    for _ in range(2):
        result = _run(tmp_path)
        assert result.returncode == 0, result.stderr

    text = bashrc.read_text(encoding="utf-8")
    assert text.count("# >>> oiteru: UTF-8 >>>") == 1
    assert text.index("export PYTHONUTF8=1") < text.index("case $- in")
    assert 'alias ll="ls -l"' in text
    assert (tmp_path / ".profile").read_text(encoding="utf-8").count("oiteru: UTF-8 >>>") == 1
    assert "quotepath = false" in (tmp_path / ".gitconfig").read_text(encoding="utf-8")


def test_resulting_shell_uses_utf8(tmp_path):
    assert _run(tmp_path).returncode == 0
    out = subprocess.run(
        ["bash", "-c", f". {tmp_path / '.profile'}; echo $LC_ALL; python3 -c 'import sys; print(sys.stdout.encoding)'"],
        capture_output=True, text=True, env={"PATH": os.environ["PATH"], "LC_ALL": "C"}, check=True,
    ).stdout.split()
    assert out[0].endswith("UTF-8")
    assert out[1].lower() == "utf-8"
