"""Tests for safe, format-preserving log masking."""

import logging

from app.logger import SensitiveDataFilter


def test_sensitive_filter_masks_card_id_without_breaking_numeric_formatting():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Auto-reset card_id=%s to %d",
        args=("TEST-CARD-0001", 2),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record)
    assert record.getMessage() == "Auto-reset card_id=*** to 2"
