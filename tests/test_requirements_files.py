"""Requirements files must be readable by every pip a newcomer may have."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "name", ["requirements.txt", "requirements-dev.txt", "requirements-client.txt"]
)
def test_requirements_are_ascii(name):
    # pip 24.0 (bundled with Python 3.11) decodes these files with the locale
    # codec, so on Japanese Windows (cp932) a UTF-8 comment stops the install.
    data = (ROOT / name).read_bytes()
    assert data.isascii(), f"{name} must contain ASCII only (comments in English)"
