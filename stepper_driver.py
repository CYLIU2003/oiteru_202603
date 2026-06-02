# -*- coding: utf-8 -*-
"""Stepper motor driver for 28BYJ-48 + ULN2003AN on Raspberry Pi.

This module centralises stepper control on the unit (sub) machine so that the
rest of the code does not need to know which GPIO library is in use.

Backend priority:

1. ``RpiMotorLib`` (BYJMotor) - preferred, well-tested 28BYJ-48 driver.
2. Direct GPIO fallback - in case the library is not installed or fails to
   import. The fallback uses the same excitation sequence as the existing
   ``stepping_patch.STEPPER_DIRECT_BRANCH`` so behaviour is preserved.

The module is intentionally pure-Python on the parameter / sequencing side so
that it can be unit-tested without RPi.GPIO hardware. Hardware interaction
happens only behind the backend classes.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Pure helpers (no GPIO, no library import).  Safe to import on any platform.
# ---------------------------------------------------------------------------

DEFAULT_PINS: List[int] = [5, 6, 13, 19]
DEFAULT_PHASE_ORDER: List[int] = [0, 2, 1, 3]
DEFAULT_DRIVE_MODE: str = "full"
DEFAULT_STEP_DELAY: float = 0.01
DEFAULT_TEST_STEPS: int = 256
DEFAULT_STEPS_PER_REV: int = 2048

VALID_DRIVE_MODES: Tuple[str, ...] = ("full", "half", "wave")


def _to_int_list(value: Any, default: Sequence[int]) -> List[int]:
    """Accept either ``[5,6,13,19]`` or the string ``"5,6,13,19"``."""
    if value in (None, ""):
        value = default
    if isinstance(value, str):
        return [int(x.strip()) for x in value.split(",") if x.strip()]
    return [int(x) for x in value]


def resolve_pins(config: Dict[str, Any]) -> List[int]:
    """Return the 4 BCM pins in IN1,IN2,IN3,IN4 order."""
    pins = _to_int_list(config.get("STEPPER_PINS"), DEFAULT_PINS)
    if len(pins) != 4:
        raise ValueError(f"STEPPER_PINS は IN1,IN2,IN3,IN4 の4本必要です: {pins}")
    return pins


def resolve_phase_order(config: Dict[str, Any]) -> List[int]:
    """Return the permutation of 0..3 used to remap pins to drive phases."""
    order = _to_int_list(config.get("STEPPER_PHASE_ORDER"), DEFAULT_PHASE_ORDER)
    if sorted(order) != [0, 1, 2, 3]:
        raise ValueError(f"STEPPER_PHASE_ORDER は 0,1,2,3 の並べ替えで指定してください: {order}")
    return order


def resolve_drive_mode(config: Dict[str, Any]) -> str:
    """Return normalised ``full``/``half``/``wave`` string."""
    mode = str(config.get("STEPPER_DRIVE_MODE", DEFAULT_DRIVE_MODE)).strip().lower()
    if mode not in VALID_DRIVE_MODES:
        raise ValueError(
            f"STEPPER_DRIVE_MODE は {VALID_DRIVE_MODES} のいずれかである必要があります: {mode}"
        )
    return mode


def resolve_step_delay(config: Dict[str, Any], motor_speed: int = 100) -> float:
    """Resolve the inter-step delay in seconds.

    If ``STEPPER_STEP_DELAY`` is set explicitly, use it.  Otherwise derive a
    value from ``motor_speed`` (1..100) where 1 is the slowest and 100 is the
    fastest.  The 28BYJ-48 stalls above ~10ms; we clamp the minimum to 0.01s.
    """
    configured = config.get("STEPPER_STEP_DELAY")
    if configured not in (None, ""):
        delay = float(configured)
    else:
        speed = max(1, min(100, int(motor_speed)))
        # 28BYJ-48 stalls when driven too fast.
        delay = 0.030 - (speed - 1) * (0.020 / 99.0)
    return max(0.01, delay)


def resolve_steps_per_rev(drive_mode: str) -> int:
    """Return the 28BYJ-48 steps-per-revolution for the given drive mode.

    28BYJ-48 with 1:64 gear:
    - half step: 4096
    - full step / wave drive: 2048
    """
    return 4096 if drive_mode == "half" else 2048


def resolve_steps(
    config: Dict[str, Any],
    step_delay: float,
    seconds: Optional[float],
    fixed_steps: Optional[int],
    default_test_steps: int = DEFAULT_TEST_STEPS,
) -> int:
    """Return the number of step control signal sequences to issue."""
    if fixed_steps is not None and int(fixed_steps) > 0:
        return max(1, int(fixed_steps))
    if seconds is not None and float(seconds) > 0:
        return max(1, int(float(seconds) / step_delay))
    configured = config.get("STEPPER_STEPS", 0)
    try:
        configured = int(configured)
    except (TypeError, ValueError):
        configured = 0
    if configured > 0:
        return configured
    return int(config.get("STEPPER_TEST_STEPS", default_test_steps))


def get_phase_sequence(drive_mode: str, reverse: bool = False) -> List[Tuple[int, int, int, int]]:
    """Return the 4-tuple coil sequence for the drive mode.

    The returned list is the per-step pattern over IN1..IN4.  When ``reverse``
    is True, the sequence is reversed in-place to spin the motor the other way.
    """
    if drive_mode == "half":
        seq: List[Tuple[int, int, int, int]] = [
            (1, 0, 0, 0),
            (1, 1, 0, 0),
            (0, 1, 0, 0),
            (0, 1, 1, 0),
            (0, 0, 1, 0),
            (0, 0, 1, 1),
            (0, 0, 0, 1),
            (1, 0, 0, 1),
        ]
    elif drive_mode == "wave":
        seq = [
            (1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0, 1),
        ]
    else:  # "full"
        seq = [
            (1, 1, 0, 0),
            (0, 1, 1, 0),
            (0, 0, 1, 1),
            (1, 0, 0, 1),
        ]
    if reverse:
        seq = list(reversed(seq))
    return seq


def build_drive_pins(pins: List[int], phase_order: List[int]) -> List[int]:
    """Reorder IN1..IN4 by ``phase_order`` to match the coil phasing."""
    return [pins[i] for i in phase_order]


def step_delay_for_drive_mode(drive_mode: str, base_delay: float) -> float:
    """Adjust the base delay to suit the chosen drive mode.

    Half-step benefits from a slightly slower delay because each step moves
    the rotor by less.  The adjustment is small and respects the user's
    configured delay as a minimum.
    """
    if drive_mode == "half":
        return max(base_delay, 0.0015)
    if drive_mode == "wave":
        return max(base_delay, 0.005)
    return max(base_delay, 0.005)


# ---------------------------------------------------------------------------
# Optional RpiMotorLib import.  Kept at module level so importing this module
# is safe on any platform (Windows, Mac, PC-mode unit) - the import only
# succeeds on Raspberry Pi OS.
# ---------------------------------------------------------------------------

try:
    import RpiMotorLib as _RpiMotorLib  # type: ignore
    _RPIMOTORLIB_AVAILABLE = True
    _RPIMOTORLIB_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # ImportError, RuntimeError, OSError, ...
    _RpiMotorLib = None  # type: ignore
    _RPIMOTORLIB_AVAILABLE = False
    _RPIMOTORLIB_IMPORT_ERROR = repr(exc)


def library_available() -> bool:
    """Return True if RpiMotorLib is importable in the current Python."""
    return _RPIMOTORLIB_AVAILABLE


def library_import_error() -> Optional[str]:
    """Return the original import error message, or None."""
    return _RPIMOTORLIB_IMPORT_ERROR


# ---------------------------------------------------------------------------
# Logging helper.  Defaults to print so we integrate with the existing unit
# client which uses print() for runtime feedback.  A real project logger can
# be installed via ``set_logger(callable)``.
# ---------------------------------------------------------------------------

_logger: Optional[Callable[[str], None]] = None


def set_logger(func: Optional[Callable[[str], None]]) -> None:
    """Install a custom line-logger.  ``None`` restores the default printer."""
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
# Backends
# ---------------------------------------------------------------------------


class StepperBackend:
    """Abstract base for the two backends."""

    name: str = "abstract"

    def is_available(self) -> bool:
        raise NotImplementedError

    def run(
        self,
        pins: List[int],
        steps: int,
        wait: float,
        reverse: bool,
        drive_mode: str,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def coils_off(self, pins: List[int]) -> None:
        raise NotImplementedError


class RpiMotorLibBackend(StepperBackend):
    """Primary backend that delegates to ``RpiMotorLib.BYJMotor``."""

    name = "RpiMotorLib"

    def __init__(self, motor_name: str = "OiteruStepper", verbose: bool = False) -> None:
        self.motor_name = motor_name
        self.verbose = verbose
        self._motor = None
        self._init_error: Optional[str] = None
        if _RpiMotorLib is not None:
            try:
                self._motor = _RpiMotorLib.BYJMotor(motor_name, "28BYJ")
            except Exception as exc:
                self._motor = None
                self._init_error = repr(exc)

    def is_available(self) -> bool:
        return self._motor is not None

    def init_error(self) -> Optional[str]:
        return self._init_error

    def run(
        self,
        pins: List[int],
        steps: int,
        wait: float,
        reverse: bool,
        drive_mode: str,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        if self._motor is None:
            raise RuntimeError(
                f"RpiMotorLib backend not initialised: {self._init_error}"
            )
        if drive_mode not in VALID_DRIVE_MODES:
            raise ValueError(f"unsupported drive mode for library backend: {drive_mode}")

        # Coarse-grained abort: we ask the library to run in chunks of 64
        # steps so the stop_check can stop the motor between chunks.  This is
        # a deliberate trade-off: a finer-grained abort would require writing
        # our own stepper loop, which defeats the point of using a library.
        remaining = max(0, int(steps))
        chunk = 64
        while remaining > 0:
            if stop_check is not None and stop_check():
                _log("[STEPPER] 停止要求を検知しました")
                return {"ok": True, "completed": steps - remaining, "aborted": True}
            take = min(chunk, remaining)
            self._motor.motor_run(
                GPIOPins=list(pins),
                wait=float(wait),
                steps=int(take),
                ccwise=bool(reverse),
                verbose=bool(self.verbose),
                steptype=str(drive_mode),
                initdelay=0.001,
            )
            remaining -= take
        return {"ok": True, "completed": steps, "aborted": False}

    def coils_off(self, pins: List[int]) -> None:
        # RpiMotorLib turns coils off after each motor_run.  Nothing to do
        # here, but we keep the method for API symmetry with the fallback.
        return None


class GpioFallbackBackend(StepperBackend):
    """GPIO-direct backend used when RpiMotorLib is not importable."""

    name = "GPIO"

    def __init__(self, gpio_module: Any) -> None:
        self._gpio = gpio_module
        self._mode_set = False

    def _ensure_mode(self) -> None:
        if self._mode_set:
            return
        try:
            self._gpio.setmode(self._gpio.BCM)
        except Exception:
            pass
        self._mode_set = True

    def is_available(self) -> bool:
        return self._gpio is not None

    def _setup_pins(self, pins: List[int]) -> None:
        self._ensure_mode()
        for pin in pins:
            try:
                self._gpio.setup(pin, self._gpio.OUT, initial=self._gpio.LOW)
            except Exception:
                # Pin may already be set up; ignore.
                pass

    def run(
        self,
        pins: List[int],
        steps: int,
        wait: float,
        reverse: bool,
        drive_mode: str,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        self._setup_pins(pins)
        sequence = get_phase_sequence(drive_mode, reverse=reverse)
        completed = 0
        aborted = False
        for idx in range(int(steps)):
            if stop_check is not None and stop_check():
                _log("[STEPPER] 停止要求を検知しました")
                aborted = True
                break
            phase = sequence[idx % len(sequence)]
            for pin, value in zip(pins, phase):
                self._gpio.output(pin, self._gpio.HIGH if value else self._gpio.LOW)
            time.sleep(float(wait))
            completed += 1
        return {"ok": True, "completed": completed, "aborted": aborted}

    def coils_off(self, pins: List[int]) -> None:
        self._ensure_mode()
        for pin in pins:
            try:
                self._gpio.output(pin, self._gpio.LOW)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# High-level entry points
# ---------------------------------------------------------------------------


def _resolve_backend_name(config: Dict[str, Any]) -> str:
    """Translate the configured ``STEPPER_BACKEND`` into a canonical name.

    Valid values:
    - ``auto``    : prefer library, fall back to GPIO (default)
    - ``library`` : require library, raise if unavailable
    - ``gpio``    : always use GPIO direct control
    """
    raw = str(config.get("STEPPER_BACKEND", "auto")).strip().lower() or "auto"
    if raw not in ("auto", "library", "gpio"):
        return "auto"
    return raw


def _log_dispense_header(
    backend_name: str,
    pins: List[int],
    phase_order: List[int],
    drive_pins: List[int],
    drive_mode: str,
    steps: int,
    wait: float,
    reverse: bool,
) -> None:
    _log(
        f"[STEPPER] backend={backend_name} pins(IN1-4)={pins} "
        f"phase_order={phase_order} drive_pins={drive_pins} "
        f"mode={drive_mode} steps={steps} wait={wait:.4f}s reverse={reverse}"
    )


def _log_coils_off() -> None:
    _log("[STEPPER] coils off")


def run_stepper(
    gpio_module: Any,
    config: Dict[str, Any],
    *,
    steps: Optional[int] = None,
    seconds: Optional[float] = None,
    reverse: Optional[bool] = None,
    motor_speed: int = 100,
    backend: Optional[str] = None,
    stop_check: Optional[Callable[[], bool]] = None,
    coils_off_after: bool = True,
    label: str = "manual",
) -> Dict[str, Any]:
    """High-level stepper runner.

    Parameters
    ----------
    gpio_module:
        An object providing the RPi.GPIO interface (``setmode``/``setup``/
        ``output``/``input``/constants).  May be ``None`` on PC mode; the
        function will then refuse to run hardware operations.
    config:
        Configuration dictionary.  Honours ``STEPPER_PINS``,
        ``STEPPER_PHASE_ORDER``, ``STEPPER_DRIVE_MODE``, ``STEPPER_STEP_DELAY``,
        ``STEPPER_STEPS``, ``STEPPER_BACKEND``.
    steps / seconds:
        Mutually exclusive overrides.  ``steps`` wins if both are provided.
    reverse:
        If ``None``, falls back to ``MOTOR_REVERSE``.
    motor_speed:
        Used to derive ``wait`` when ``STEPPER_STEP_DELAY`` is unset.
    backend:
        ``"auto"`` / ``"library"`` / ``"gpio"``.  Defaults to
        ``config["STEPPER_BACKEND"]`` or ``"auto"``.
    stop_check:
        Optional callable returning True to abort mid-run.
    label:
        Tag printed in the log line to identify the caller (e.g. "CUI",
        "NFC dispense", "scan:0").
    """
    pins = resolve_pins(config)
    phase_order = resolve_phase_order(config)
    drive_mode = resolve_drive_mode(config)
    base_delay = resolve_step_delay(config, motor_speed=motor_speed)
    wait = step_delay_for_drive_mode(drive_mode, base_delay)
    if reverse is None:
        reverse = bool(config.get("MOTOR_REVERSE", False))
    steps_to_run = resolve_steps(
        config, wait, seconds=seconds, fixed_steps=steps, default_test_steps=DEFAULT_TEST_STEPS
    )

    selected = backend or _resolve_backend_name(config)

    chosen_backend: Optional[StepperBackend] = None
    backend_label: str = "unknown"
    if selected in ("auto", "library"):
        lib = RpiMotorLibBackend(motor_name=f"OiteruStepper-{label}")
        if lib.is_available():
            chosen_backend = lib
            backend_label = lib.name
        elif selected == "library":
            raise RuntimeError(
                f"STEPPER_BACKEND=library ですが RpiMotorLib が使えません: {lib.init_error()}"
            )
        else:
            _log(f"[STEPPER] RpiMotorLib を使えないため GPIO フォールバック: {lib.init_error() or 'unknown'}")
    if chosen_backend is None:
        if gpio_module is None:
            raise RuntimeError(
                "GPIO モジュールが無く RpiMotorLib も利用できません。Raspberry Pi 上で実行してください。"
            )
        chosen_backend = GpioFallbackBackend(gpio_module)
        backend_label = chosen_backend.name

    if steps_to_run <= 0:
        _log("[STEPPER] steps=0 のためスキップ")
        return {"ok": True, "backend": backend_label, "steps": 0, "aborted": False}

    _log_dispense_header(
        backend_label,
        pins,
        phase_order,
        build_drive_pins(pins, phase_order),
        drive_mode,
        steps_to_run,
        wait,
        reverse,
    )
    _log(f"[STEPPER] start ({label})")

    result: Dict[str, Any]
    try:
        if isinstance(chosen_backend, RpiMotorLibBackend):
            result = chosen_backend.run(
                pins=pins,
                steps=steps_to_run,
                wait=wait,
                reverse=reverse,
                drive_mode=drive_mode,
                stop_check=stop_check,
            )
        else:
            drive_pins = build_drive_pins(pins, phase_order)
            result = chosen_backend.run(
                pins=drive_pins,
                steps=steps_to_run,
                wait=wait,
                reverse=reverse,
                drive_mode=drive_mode,
                stop_check=stop_check,
            )
    except Exception as exc:
        _log(f"[STEPPER] 失敗 ({label}): {exc!r}")
        if coils_off_after and gpio_module is not None:
            try:
                for pin in pins:
                    gpio_module.output(pin, gpio_module.LOW)
            except Exception:
                pass
        return {"ok": False, "backend": backend_label, "error": repr(exc)}

    _log(f"[STEPPER] done ({label})")
    if coils_off_after:
        try:
            chosen_backend.coils_off(pins)
        except Exception:
            pass
        _log_coils_off()

    result.setdefault("backend", backend_label)
    result.setdefault("steps", steps_to_run)
    return result


def coils_off(gpio_module: Any, config: Dict[str, Any]) -> None:
    """Force all configured stepper pins LOW.  Safe on PC mode (no-op)."""
    if gpio_module is None:
        _log("[STEPPER] coils off: GPIO モジュール無し、スキップ")
        return
    try:
        pins = resolve_pins(config)
    except Exception as exc:
        _log(f"[STEPPER] coils off 設定エラー: {exc}")
        return
    try:
        for pin in pins:
            gpio_module.output(pin, gpio_module.LOW)
        _log(f"[STEPPER] coils off: pins={pins}")
    except Exception as exc:
        _log(f"[STEPPER] coils off 失敗: {exc}")


def summarise(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict of resolved parameters for CUI display / logging."""
    try:
        pins = resolve_pins(config)
    except Exception as exc:
        pins = DEFAULT_PINS
    try:
        phase_order = resolve_phase_order(config)
    except Exception:
        phase_order = DEFAULT_PHASE_ORDER
    try:
        drive_mode = resolve_drive_mode(config)
    except Exception:
        drive_mode = DEFAULT_DRIVE_MODE
    delay = resolve_step_delay(config)
    return {
        "backend": _resolve_backend_name(config),
        "library_available": library_available(),
        "library_import_error": library_import_error(),
        "pins": pins,
        "phase_order": phase_order,
        "drive_pins": build_drive_pins(pins, phase_order),
        "drive_mode": drive_mode,
        "step_delay": delay,
        "steps_per_rev": resolve_steps_per_rev(drive_mode),
        "test_steps": int(config.get("STEPPER_TEST_STEPS", DEFAULT_TEST_STEPS)),
    }
