"""Tests for child-device secret persistence and GPIO safety validation."""

from __future__ import annotations

import json
import os

import pytest

from unit.configuration import (
    find_gpio_conflicts,
    load_config,
    save_config,
    validate_gpio_config,
    validate_parent_url,
)


DEFAULTS = {
    "UNIT_NAME": "unit-01",
    "UNIT_PASSWORD": "",
    "MOTOR_TYPE": "STEPPER",
    "CONTROL_METHOD": "RASPI_DIRECT",
    "USE_SENSOR": True,
    "GREEN_LED_PIN": 5,
    "RED_LED_PIN": 6,
    "SENSOR_PIN": 13,
    "STEPPER_PINS": [21, 17, 27, 22],
}


def test_secret_is_not_written_to_public_config_and_survives_reload(tmp_path):
    config_path = tmp_path / "config.json"
    config = {**DEFAULTS, "UNIT_PASSWORD": "device-secret"}

    save_config(config_path, config)

    public_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert "UNIT_PASSWORD" not in public_config
    assert load_config(config_path, DEFAULTS)["UNIT_PASSWORD"] == "device-secret"
    if os.name != "nt":
        assert (config_path.with_suffix(".json.secret").stat().st_mode & 0o777) == 0o600


def test_legacy_hash_in_config_requires_secret_reprovisioning(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"UNIT_PASSWORD": "a" * 64, "UNIT_NAME": "unit-01"}),
        encoding="utf-8",
    )

    loaded = load_config(config_path, DEFAULTS)

    assert loaded["UNIT_PASSWORD"] == ""
    assert loaded["_unit_secret_migration_required"] is True


def test_gpio_conflicts_are_reported_before_hardware_is_initialized():
    config = {**DEFAULTS, "STEPPER_PINS": [21, 5, 6, 13]}

    assert find_gpio_conflicts(config) == {
        5: ["GREEN_LED_PIN", "STEPPER_PINS[2]"],
        6: ["RED_LED_PIN", "STEPPER_PINS[3]"],
        13: ["SENSOR_PIN", "STEPPER_PINS[4]"],
    }
    with pytest.raises(ValueError, match="GPIO pin conflict"):
        validate_gpio_config(config)


def test_non_overlapping_gpio_config_is_accepted():
    validate_gpio_config(DEFAULTS)


def test_out_of_range_gpio_config_is_rejected():
    with pytest.raises(ValueError, match="BCM values"):
        validate_gpio_config({**DEFAULTS, "SENSOR_PIN": 28})


def test_strict_mode_rejects_plaintext_remote_parent_url():
    with pytest.raises(ValueError, match="HTTPS"):
        validate_parent_url("http://192.0.2.10:5000", strict=True)
    validate_parent_url("https://oiteru-parent.example", strict=True)
    validate_parent_url("http://127.0.0.1:5000", strict=True)
