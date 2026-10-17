"""Child and tmux starts must not depend on the Raspberry Pi's locale."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_venv_start_forces_utf8_before_running_python():
    # A child Pi set to LANG=ja_JP.EUC-JP crashed on print("✓ ...") because
    # stdout used euc_jp. PYTHONUTF8=1 makes every role started here use UTF-8.
    text = (ROOT / "venv-start.sh").read_text(encoding="utf-8")
    assert "export PYTHONUTF8=1" in text
    assert text.index("export PYTHONUTF8=1") < text.index('PYTHON_PATH="./.venv/bin/python"')
