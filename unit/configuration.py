"""Safe child-device configuration and GPIO validation helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def get_unit_secret_path(config_path: str | Path, config: dict[str, Any]) -> Path:
    """Resolve the device secret path without placing the secret in JSON."""
    configured_path = os.getenv("OITERU_UNIT_SECRET_FILE") or config.get(
        "UNIT_SECRET_FILE"
    )
    if configured_path:
        return Path(str(configured_path)).expanduser()
    return Path(config_path).with_suffix(Path(config_path).suffix + ".secret")


def load_config(config_path: str | Path, defaults: dict[str, Any]) -> dict[str, Any]:
    """Load public JSON configuration and its separately stored device secret."""
    path = Path(config_path)
    config = dict(defaults)
    legacy_secret_present = False

    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            # A previous release wrote a non-reusable password hash here.  It
            # cannot authenticate after reboot, so never send it as a secret.
            legacy_secret_present = bool(loaded.pop("UNIT_PASSWORD", ""))
            config.update(loaded)

    secret_path = get_unit_secret_path(path, config)
    try:
        secret = secret_path.read_text(encoding="utf-8").strip()
    except OSError:
        secret = ""

    config["UNIT_PASSWORD"] = secret
    if legacy_secret_present and not secret:
        config["_unit_secret_migration_required"] = True
    return config


def save_config(config_path: str | Path, config: dict[str, Any]) -> None:
    """Persist public configuration and a 0600 device secret separately."""
    path = Path(config_path)
    public_config = {
        key: value
        for key, value in config.items()
        if key != "UNIT_PASSWORD" and not key.startswith("_")
    }
    secret_path = get_unit_secret_path(path, public_config)
    _atomic_write(path, json.dumps(public_config, indent=4, ensure_ascii=False) + "\n", 0o600)

    secret = str(config.get("UNIT_PASSWORD") or "")
    if secret:
        _atomic_write(secret_path, secret + "\n", 0o600)
    elif secret_path.exists():
        secret_path.unlink()


def find_gpio_conflicts(config: dict[str, Any]) -> dict[int, list[str]]:
    """Return GPIO pins assigned to multiple incompatible device functions."""
    assignments: dict[int, list[str]] = {}

    def add(pin_value: Any, purpose: str) -> None:
        try:
            pin = int(pin_value)
        except (TypeError, ValueError):
            return
        if not 0 <= pin <= 27:
            return
        assignments.setdefault(pin, []).append(purpose)

    add(config.get("GREEN_LED_PIN"), "GREEN_LED_PIN")
    add(config.get("RED_LED_PIN"), "RED_LED_PIN")
    if _as_bool(config.get("USE_SENSOR")):
        add(config.get("SENSOR_PIN", config.get("SENSOR_GPIO_PIN")), "SENSOR_PIN")

    if (
        str(config.get("MOTOR_TYPE", "STEPPER")).upper() == "STEPPER"
        and str(config.get("CONTROL_METHOD", "RASPI_DIRECT")).upper()
        == "RASPI_DIRECT"
    ):
        for index, pin in enumerate(config.get("STEPPER_PINS", []), start=1):
            add(pin, f"STEPPER_PINS[{index}]")

    return {
        pin: purposes for pin, purposes in assignments.items() if len(purposes) > 1
    }


def validate_gpio_config(config: dict[str, Any]) -> None:
    """Reject wiring conflicts before GPIO setup or a motor command."""
    invalid_pins = _invalid_gpio_pins(config)
    if invalid_pins:
        raise ValueError(
            "GPIO pins must be BCM values from 0 to 27: "
            + ", ".join(invalid_pins)
        )

    conflicts = find_gpio_conflicts(config)
    if conflicts:
        detail = "; ".join(
            f"GPIO {pin}: {', '.join(purposes)}"
            for pin, purposes in sorted(conflicts.items())
        )
        raise ValueError(f"GPIO pin conflict: {detail}")


def validate_parent_url(server_url: str, *, strict: bool) -> None:
    """Reject ambiguous URLs and plaintext remote parent connections."""
    parsed = urlparse(str(server_url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("SERVER_URL must be an absolute http(s) URL")
    if strict and parsed.scheme != "https" and parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        raise ValueError("strict security requires HTTPS for a non-local parent URL")


def _atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        if os.name != "nt":
            os.fchmod(file_descriptor, mode)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
        os.replace(temporary_name, path)
        if os.name != "nt":
            path.chmod(mode)
    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _invalid_gpio_pins(config: dict[str, Any]) -> list[str]:
    pins: list[tuple[str, Any]] = [
        ("GREEN_LED_PIN", config.get("GREEN_LED_PIN")),
        ("RED_LED_PIN", config.get("RED_LED_PIN")),
    ]
    if _as_bool(config.get("USE_SENSOR")):
        pins.append(("SENSOR_PIN", config.get("SENSOR_PIN", config.get("SENSOR_GPIO_PIN"))))
    if (
        str(config.get("MOTOR_TYPE", "STEPPER")).upper() == "STEPPER"
        and str(config.get("CONTROL_METHOD", "RASPI_DIRECT")).upper()
        == "RASPI_DIRECT"
    ):
        pins.extend(
            (f"STEPPER_PINS[{index}]", value)
            for index, value in enumerate(config.get("STEPPER_PINS", []), start=1)
        )

    invalid: list[str] = []
    for name, value in pins:
        try:
            pin = int(value)
        except (TypeError, ValueError):
            invalid.append(f"{name}={value!r}")
            continue
        if not 0 <= pin <= 27:
            invalid.append(f"{name}={pin}")
    return invalid
