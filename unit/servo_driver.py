# -*- coding: utf-8 -*-
"""Servo motor driver via PCA9685 on Raspberry Pi I2C bus.

This module mirrors ``stepper_driver.py`` in philosophy: pure helpers for
parameter calculation, optional hardware backends, and a single high-level
``run_servo()`` entry point.

Hardware requirement:
    ``Adafruit_PCA9685`` library + I2C enabled on GPIO bus 1.
    On PC / non-Raspberry Pi the module imports safely and mock tests work.

PWM convention:
    Frequency = 60 Hz (standard servo).
    ``speed`` (1-100) maps to PWM 150-600::

        pwm = 150 + (speed / 100.0) * 450

    Higher PWM = more throttle.  ``reverse=True`` inverts the mapping.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


# ---------------------------------------------------------------------------
# Pure helpers (no hardware import).  Safe to import on any platform.
# ---------------------------------------------------------------------------

DEFAULT_CHANNEL: int = 15
DEFAULT_FREQ: int = 60
PWM_MIN: int = 150
PWM_MAX: int = 600


def servo_pwm_for_speed(speed: float = 100.0, reverse: bool = False) -> int:
    """Return the PWM duty value (out of 4095) for the given speed.

    ``speed`` is clamped to 1-100.  When ``reverse`` is True the PWM is
    inverted so the servo rotates the opposite direction.
    """
    s = max(1.0, min(100.0, float(speed)))
    raw = int(PWM_MIN + (s / 100.0) * (PWM_MAX - PWM_MIN))
    if reverse:
        raw = PWM_MAX - (raw - PWM_MIN)
    return max(0, min(4095, raw))


def _clamp_duration(duration: float) -> float:
    """Clamp servo-on duration to a safe 0.1-60 second range."""
    return max(0.1, min(60.0, float(duration)))


# ---------------------------------------------------------------------------
# Dataclass for return values
# ---------------------------------------------------------------------------


@dataclass
class ServoResult:
    ok: bool = True
    message: str = ""
    pwm_value: int = 0
    duration: float = 0.0
    channel: int = DEFAULT_CHANNEL


# ---------------------------------------------------------------------------
# Logging helper (mirrors stepper_driver)
# ---------------------------------------------------------------------------

_logger: Optional[Callable[[str], None]] = None


def set_logger(func: Optional[Callable[[str], None]]) -> None:
    global _logger
    _logger = func


def _log(line: str) -> None:
    if _logger is not None:
        try:
            _logger(line)
            return
        except Exception:
            pass
    print(line)


# ---------------------------------------------------------------------------
# Optional Adafruit_PCA9685 import
# ---------------------------------------------------------------------------

try:
    import Adafruit_PCA9685 as _Adafruit_PCA9685  # type: ignore
    _PCA9685_AVAILABLE = True
    _PCA9685_IMPORT_ERROR: Optional[str] = None
except Exception as exc:
    _Adafruit_PCA9685 = None  # type: ignore
    _PCA9685_AVAILABLE = False
    _PCA9685_IMPORT_ERROR = repr(exc)


def pca9685_available() -> bool:
    return _PCA9685_AVAILABLE


def pca9685_import_error() -> Optional[str]:
    return _PCA9685_IMPORT_ERROR


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


class Pca9685Backend:
    """Hardware backend: I2C PCA9685 PWM controller."""

    name = "PCA9685"

    def __init__(self, address: int = 0x40, busnum: int = 1) -> None:
        self._address = address
        self._busnum = busnum
        self._pwm = None
        self._init_error: Optional[str] = None
        if _Adafruit_PCA9685 is not None:
            try:
                self._pwm = _Adafruit_PCA9685.PCA9685(
                    address=address, busnum=busnum
                )
                self._pwm.set_pwm_freq(DEFAULT_FREQ)
            except Exception as exc:
                self._pwm = None
                self._init_error = repr(exc)

    def is_available(self) -> bool:
        return self._pwm is not None

    def init_error(self) -> Optional[str]:
        return self._init_error

    def run(
        self,
        channel: int,
        pwm_value: int,
        duration: float,
    ) -> ServoResult:
        if self._pwm is None:
            raise RuntimeError(
                f"PCA9685 backend not initialised: {self._init_error}"
            )
        try:
            self._pwm.set_pwm(channel, 0, pwm_value)
            time.sleep(duration)
            self._pwm.set_pwm(channel, 0, 0)
            return ServoResult(
                ok=True,
                message="servo completed",
                pwm_value=pwm_value,
                duration=duration,
                channel=channel,
            )
        except Exception as exc:
            self._pwm.set_pwm(channel, 0, 0)
            return ServoResult(
                ok=False,
                message=str(exc),
                pwm_value=pwm_value,
                duration=0.0,
                channel=channel,
            )

    def stop(self, channel: int) -> None:
        if self._pwm is not None:
            try:
                self._pwm.set_pwm(channel, 0, 0)
            except Exception:
                pass


class MockServoBackend:
    """Mock backend for PC-mode / unit tests."""

    name = "MockServo"

    def __init__(self) -> None:
        self.last_pwm: int = 0
        self.last_channel: int = DEFAULT_CHANNEL

    def is_available(self) -> bool:
        return True

    def init_error(self) -> Optional[str]:
        return None

    def run(
        self, channel: int, pwm_value: int, duration: float
    ) -> ServoResult:
        self.last_channel = channel
        self.last_pwm = pwm_value
        _log(f"[SERVO mock] ch={channel} pwm={pwm_value} dur={duration:.2f}s")
        return ServoResult(
            ok=True,
            message="mock servo completed",
            pwm_value=pwm_value,
            duration=duration,
            channel=channel,
        )

    def stop(self, channel: int) -> None:
        pass


# ---------------------------------------------------------------------------
# High-level entry point
# ---------------------------------------------------------------------------


def run_servo(
    config: Dict[str, Any],
    *,
    speed: Optional[int] = None,
    reverse: Optional[bool] = None,
    duration: Optional[float] = None,
    channel: Optional[int] = None,
    label: str = "servo-dispense",
) -> ServoResult:
    """High-level servo runner.

    Parameters
    ----------
    config:
        Configuration dict.  Uses ``MOTOR_SPEED``, ``MOTOR_REVERSE``,
        ``MOTOR_DURATION``, ``PCA9685_CHANNEL``.
    speed:
        Override motor speed (1-100).  Falls back to config.
    reverse:
        Override direction.  Falls back to config.
    duration:
        Override run duration in seconds.  Falls back to config.
    channel:
        PCA9685 channel (0-15).  Falls back to config.
    label:
        Tag used in log messages.
    """
    motor_speed = speed if speed is not None else int(config.get("MOTOR_SPEED", 100))
    motor_speed = max(1, min(100, int(motor_speed)))
    motor_reverse = (
        bool(reverse)
        if reverse is not None
        else bool(config.get("MOTOR_REVERSE", False))
    )
    motor_duration = (
        float(duration) if duration is not None else float(config.get("MOTOR_DURATION", 2.0))
    )
    motor_duration = _clamp_duration(motor_duration)
    servo_channel = (
        int(channel) if channel is not None else int(config.get("PCA9685_CHANNEL", DEFAULT_CHANNEL))
    )
    servo_channel = max(0, min(15, servo_channel))

    pwm_value = servo_pwm_for_speed(motor_speed, reverse=motor_reverse)

    _log(
        f"[SERVO] start ({label}) speed={motor_speed} reverse={motor_reverse} "
        f"pwm={pwm_value} dur={motor_duration:.2f}s ch={servo_channel}"
    )

    backend: Pca9685Backend | MockServoBackend
    if _PCA9685_AVAILABLE:
        backend = Pca9685Backend(address=0x40, busnum=1)
        if not backend.is_available():
            _log(f"[SERVO] PCA9685 init failed: {backend.init_error()}; using mock")
            backend = MockServoBackend()
    else:
        backend = MockServoBackend()

    result = backend.run(channel=servo_channel, pwm_value=pwm_value, duration=motor_duration)

    if result.ok:
        _log(f"[SERVO] done ({label})")
    else:
        _log(f"[SERVO] failed ({label}): {result.message}")

    return result


def servo_stop(config: Dict[str, Any], channel: Optional[int] = None) -> None:
    """Immediately stop the servo (set PWM to 0 on the configured channel)."""
    ch = (
        int(channel) if channel is not None else int(config.get("PCA9685_CHANNEL", DEFAULT_CHANNEL))
    )
    ch = max(0, min(15, ch))
    _log(f"[SERVO] stop ch={ch}")
    if _PCA9685_AVAILABLE:
        backend = Pca9685Backend(address=0x40, busnum=1)
        if backend.is_available():
            backend.stop(ch)
