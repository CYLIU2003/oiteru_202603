"""Regression checks for public configuration templates."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_child_configuration_templates_do_not_embed_a_device_secret():
    configuration = json.loads(
        (PROJECT_ROOT / "config.example.json").read_text(encoding="utf-8")
    )

    assert "UNIT_PASSWORD" not in configuration
    assert configuration["UNIT_SECRET_FILE"]
