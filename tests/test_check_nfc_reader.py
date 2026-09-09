"""Hardware-free regression checks for the NFC diagnostic CLI."""

import logging
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tools import check_nfc_reader as diagnostic


@pytest.fixture
def reader(monkeypatch):
    frontend = MagicMock()
    nfc = SimpleNamespace(
        ContactlessFrontend=MagicMock(return_value=frontend),
        clf=MagicMock(),
        tag=MagicMock(),
    )
    monkeypatch.setitem(sys.modules, "nfc", nfc)
    monkeypatch.setattr(sys, "argv", ["check_nfc_reader.py"])
    return nfc, frontend


def test_usb_fallback(reader):
    nfc, frontend = reader
    nfc.ContactlessFrontend.side_effect = [OSError()] * 3 + [frontend]
    assert diagnostic.main() == 0
    assert nfc.ContactlessFrontend.call_args.args == ("usb",)
    frontend.close.assert_called_once()


def test_unopened_frontends_fail_and_close(reader):
    nfc, _ = reader
    candidates = [MagicMock() for _ in range(4)]
    for candidate in candidates:
        candidate.__bool__.return_value = False
    nfc.ContactlessFrontend.side_effect = candidates
    assert diagnostic.main() == 1
    for candidate in candidates:
        candidate.close.assert_called_once()


def test_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "nfc", None)
    monkeypatch.setattr(sys, "argv", ["check_nfc_reader.py"])
    assert diagnostic.main() == 1


def test_detection_error_does_not_expose_details(reader, caplog):
    nfc, _ = reader
    nfc.ContactlessFrontend.side_effect = OSError("private-value")
    assert diagnostic.main() == 1
    assert "OSError" in caplog.text
    assert "private-value" not in caplog.text


@pytest.mark.parametrize("outcome", ["success", "timeout", "error", "interrupt"])
def test_read_cleanup_and_privacy(reader, monkeypatch, caplog, outcome):
    nfc, frontend = reader
    monkeypatch.setattr(sys, "argv", ["check_nfc_reader.py", "--read"])
    caplog.set_level(logging.INFO)
    nfc.tag.activate.return_value = SimpleNamespace(identifier=b"private-card-uid")
    if outcome == "timeout":
        monkeypatch.setattr(diagnostic.time, "monotonic", MagicMock(side_effect=[0, 11]))
    elif outcome == "error":
        frontend.sense.side_effect = OSError("private-card-uid")
    elif outcome == "interrupt":
        frontend.sense.side_effect = KeyboardInterrupt()
    if outcome == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            diagnostic.main()
    else:
        assert diagnostic.main() == (0 if outcome == "success" else 1)
    frontend.close.assert_called_once()
    assert "private-card-uid" not in caplog.text
    assert b"private-card-uid".hex().upper() not in caplog.text
