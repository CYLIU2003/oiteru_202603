"""Regression checks for public configuration templates."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_child_configuration_templates_do_not_embed_a_device_secret():
    for relative_path in (
        "config.example.json",
        "config_templates/config_unit.template.json",
    ):
        configuration = json.loads(
            (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        )

        assert "UNIT_PASSWORD" not in configuration
        assert configuration["UNIT_SECRET_FILE"]


def test_sub_parent_template_requires_a_replaced_database_password():
    configuration = json.loads(
        (PROJECT_ROOT / "config_templates/config_sub_parent.template.json").read_text(
            encoding="utf-8"
        )
    )

    assert configuration["MYSQL_PASSWORD"] == "change-this-mysql-password"
