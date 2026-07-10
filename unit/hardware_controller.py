# -*- coding: utf-8 -*-
"""Unified hardware controller for OITERU unit (child) machine.

Orchestrates:
- Stepper motor dispense via ``stepper_driver``
- Servo motor dispense via ``unit.servo_driver``
- Photoreflector sensor (LBR-127HLD) pre/post checks
- Jam-clear / retry loops
- LED indication

All hardware-platform-dependent imports are lazy / optional so that the
controller can be instantiated (and tested) on any platform.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Event
from typing import Any, Callable, Dict, Optional

import stepper_driver as _stepper
from unit.servo_driver import run_servo, servo_stop


# ---------------------------------------------------------------------------
# Request / Response types
# ---------------------------------------------------------------------------


@dataclass
class DispenseRequest:
    config: Dict[str, Any]
    stop_event: Optional[Event] = None
    on_log: Callable[[str], None] = field(default=lambda _: None)


@dataclass
class DispenseResult:
    success: bool
    motor_type: str = "STEPPER"
    message: str = ""
    sensor_pre_ok: bool = True
    sensor_post_ok: bool = True
    jam_cleared: bool = False
    attempts: int = 1
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class HardwareController:
    """Stateless orchestrator.  Create once or per-dispense; either is safe."""

    def __init__(
        self,
        gpio_module: Any = None,
        platform: str = "PC",
    ) -> None:
        self._gpio = gpio_module
        self._platform = platform

    # ── Public API ──────────────────────────────────────────────────────

    def dispense(self, request: DispenseRequest) -> DispenseResult:
        """Execute a dispense operation for the configured motor type."""
        config = request.config
        motor_type = str(config.get("MOTOR_TYPE", "STEPPER")).upper()
        if motor_type == "STEPPER":
            return self._dispense_stepper(request)
        elif motor_type == "SERVO":
            return self._dispense_servo(request)
        else:
            return DispenseResult(
                success=False,
                motor_type=motor_type,
                message=f"未サポートのモータータイプ: {motor_type}",
            )

    def test_motor(
        self,
        config: Dict[str, Any],
        *,
        reverse: bool = False,
        label: str = "test",
    ) -> DispenseResult:
        """Run a motor test (from admin UI / API)."""
        motor_type = str(config.get("MOTOR_TYPE", "STEPPER")).upper()
        if motor_type == "STEPPER":
            return self._test_stepper(config, reverse=reverse, label=label)
        elif motor_type == "SERVO":
            return self._test_servo(config, reverse=reverse, label=label)
        else:
            return DispenseResult(
                success=False,
                motor_type=motor_type,
                message=f"未サポートのモータータイプ: {motor_type}",
            )

    def coils_off(self, config: Dict[str, Any]) -> None:
        """Force all motor outputs off."""
        motor_type = str(config.get("MOTOR_TYPE", "STEPPER")).upper()
        if motor_type == "STEPPER":
            _stepper.coils_off(self._gpio, config)
        elif motor_type == "SERVO":
            servo_stop(config)

    # ── Sensor ──────────────────────────────────────────────────────────

    def check_sensor(
        self,
        config: Dict[str, Any],
        description: str = "",
        stabilize: bool = True,
    ) -> bool:
        """Read LBR-127HLD photoreflector.

        Returns True = clear (no object), False = object detected.
        Always returns True when USE_SENSOR=False or PC mode.
        """
        use_sensor = bool(config.get("USE_SENSOR", False))
        sensor_pin = int(config.get("SENSOR_PIN", 22))
        if not use_sensor or self._platform != "RASPI" or self._gpio is None:
            return True

        if stabilize:
            time.sleep(0.05)

        readings = []
        for _ in range(3):
            try:
                readings.append(self._gpio.input(sensor_pin))
            except Exception:
                return True
            time.sleep(0.01)

        # Majority vote debounce
        val = max(set(readings), key=readings.count) if readings else 1
        is_clear = val == 1
        status = "クリア" if is_clear else "物体検知"
        msg = f"[センサーチェック{description}] 値={val} ({status}) [読み取り: {readings}]"
        print(msg)  # intentionally print for on-device visibility
        return is_clear

    # ── LED ─────────────────────────────────────────────────────────────

    def indicate_success(self, config: Dict[str, Any]) -> None:
        self._indicate(config, "success")

    def indicate_failure(self, config: Dict[str, Any]) -> None:
        self._indicate(config, "failure")

    # ── Internal: Stepper ───────────────────────────────────────────────

    def _dispense_stepper(self, req: DispenseRequest) -> DispenseResult:
        config = req.config
        stop_event = req.stop_event
        log = req.on_log
        use_sensor = bool(config.get("USE_SENSOR", False))
        sensor_pre = bool(config.get("SENSOR_CHECK_PRE", True))
        sensor_post = bool(config.get("SENSOR_CHECK_POST", True))
        jam_attempts = int(config.get("JAM_CLEAR_ATTEMPTS", 3))
        motor_reverse = bool(config.get("MOTOR_REVERSE", False))
        motor_speed = int(config.get("MOTOR_SPEED", 100))
        motor_duration = float(config.get("MOTOR_DURATION", 2.0))
        stabilize = float(config.get("SENSOR_STABILIZE_TIME", 0.3))

        def _stop():
            return stop_event is not None and stop_event.is_set()

        # 1. Pre-sensor check + jam clear
        sensor_pre_ok = True
        jam_cleared = False
        if use_sensor and sensor_pre:
            if not self.check_sensor(config, "(回転前)"):
                sensor_pre_ok = False
                log("警告: 排出前に残留物検知")
                for attempt in range(jam_attempts):
                    if _stop():
                        return DispenseResult(
                            success=False, motor_type="STEPPER",
                            message="中断されました",
                            sensor_pre_ok=False,
                            attempts=attempt + 1,
                        )
                    log(f"詰まり解消試行 {attempt + 1}/{jam_attempts}")
                    self._stepper_jam_clear(config, motor_reverse, _stop)
                    time.sleep(0.3)
                    if self.check_sensor(config, "(解消確認)"):
                        jam_cleared = True
                        log("詰まり解消成功")
                        break

        # 2. Main dispense via stepper_driver
        if _stop():
            return DispenseResult(
                success=False, motor_type="STEPPER",
                message="中断されました",
                sensor_pre_ok=sensor_pre_ok,
                jam_cleared=jam_cleared,
            )

        result = _stepper.run_stepper(
            self._gpio,
            config,
            seconds=motor_duration,
            reverse=motor_reverse,
            motor_speed=motor_speed,
            stop_check=_stop if stop_event else None,
            label="dispense",
        )

        if not result.get("ok"):
            return DispenseResult(
                success=False,
                motor_type="STEPPER",
                message=result.get("error", "stepper run failed"),
                sensor_pre_ok=sensor_pre_ok,
                jam_cleared=jam_cleared,
                error=result.get("error"),
            )

        # 3. Post-sensor check + retry
        sensor_post_ok = True
        attempts = 1
        if use_sensor and sensor_post:
            time.sleep(stabilize)
            if not self.check_sensor(config, "(回転後)"):
                sensor_post_ok = False
                log("警告: 排出後に物体残留")
                for attempt in range(jam_attempts):
                    attempts = attempt + 2
                    if _stop():
                        return DispenseResult(
                            success=False, motor_type="STEPPER",
                            message="中断されました",
                            sensor_pre_ok=sensor_pre_ok,
                            sensor_post_ok=False,
                            jam_cleared=jam_cleared,
                            attempts=attempts,
                        )
                    log(f"追加排出 {attempt + 1}/{jam_attempts}")
                    self._stepper_retry(config, motor_reverse, _stop)
                    time.sleep(0.3)
                    if self.check_sensor(config, "(追加確認)"):
                        sensor_post_ok = True
                        log("追加排出成功")
                        break

        if not sensor_post_ok:
            return DispenseResult(
                success=False,
                motor_type="STEPPER",
                message="排出失敗: 物体が詰まっています",
                sensor_pre_ok=sensor_pre_ok,
                sensor_post_ok=False,
                jam_cleared=jam_cleared,
                attempts=attempts,
                error="JAMMED",
            )

        return DispenseResult(
            success=True,
            motor_type="STEPPER",
            message="排出完了",
            sensor_pre_ok=sensor_pre_ok,
            sensor_post_ok=sensor_post_ok,
            jam_cleared=jam_cleared,
            attempts=attempts,
        )

    def _stepper_jam_clear(self, config, motor_reverse, stop_check):
        steps_per_rev = _stepper.resolve_steps_per_rev(
            _stepper.resolve_drive_mode(config)
        )
        _stepper.run_stepper(
            self._gpio, config,
            steps=max(64, steps_per_rev // 16),
            reverse=not motor_reverse,
            motor_speed=int(config.get("MOTOR_SPEED", 100)),
            stop_check=stop_check,
            label="jam-clear",
        )

    def _stepper_retry(self, config, motor_reverse, stop_check):
        steps_per_rev = _stepper.resolve_steps_per_rev(
            _stepper.resolve_drive_mode(config)
        )
        _stepper.run_stepper(
            self._gpio, config,
            steps=max(128, steps_per_rev // 8),
            reverse=motor_reverse,
            motor_speed=int(config.get("MOTOR_SPEED", 100)),
            stop_check=stop_check,
            label="retry",
        )

    # ── Internal: Servo ─────────────────────────────────────────────────

    def _dispense_servo(self, req: DispenseRequest) -> DispenseResult:
        config = req.config
        stop_event = req.stop_event
        log = req.on_log
        use_sensor = bool(config.get("USE_SENSOR", False))
        sensor_pre = bool(config.get("SENSOR_CHECK_PRE", True))
        sensor_post = bool(config.get("SENSOR_CHECK_POST", True))
        jam_attempts = int(config.get("JAM_CLEAR_ATTEMPTS", 3))
        motor_reverse = bool(config.get("MOTOR_REVERSE", False))
        motor_speed = int(config.get("MOTOR_SPEED", 100))
        motor_duration = float(config.get("MOTOR_DURATION", 2.0))
        stabilize = float(config.get("SENSOR_STABILIZE_TIME", 0.3))

        def _stop():
            return stop_event is not None and stop_event.is_set()

        # 1. Pre-sensor + jam clear
        sensor_pre_ok = True
        jam_cleared = False
        if use_sensor and sensor_pre:
            if not self.check_sensor(config, "(回転前)"):
                sensor_pre_ok = False
                log("警告: 排出前に残留物検知")
                for attempt in range(jam_attempts):
                    if _stop():
                        return DispenseResult(
                            success=False, motor_type="SERVO",
                            message="中断されました", sensor_pre_ok=False,
                            attempts=attempt + 1,
                        )
                    log(f"詰まり解消試行 {attempt + 1}/{jam_attempts}")
                    run_servo(config, speed=motor_speed, reverse=not motor_reverse, duration=0.3, label="jam-clear")
                    time.sleep(0.5)
                    if self.check_sensor(config, "(解消確認)"):
                        jam_cleared = True
                        log("詰まり解消成功")
                        break

        # 2. Main dispense
        if _stop():
            return DispenseResult(
                success=False, motor_type="SERVO",
                message="中断されました", sensor_pre_ok=sensor_pre_ok,
                jam_cleared=jam_cleared,
            )

        result = run_servo(
            config,
            speed=motor_speed,
            reverse=motor_reverse,
            duration=motor_duration,
            label="dispense",
        )

        if not result.ok:
            return DispenseResult(
                success=False, motor_type="SERVO",
                message=result.message, sensor_pre_ok=sensor_pre_ok,
                jam_cleared=jam_cleared, error=result.message,
            )

        # 3. Post-sensor + retry
        sensor_post_ok = True
        attempts = 1
        if use_sensor and sensor_post:
            time.sleep(stabilize)
            if not self.check_sensor(config, "(回転後)"):
                sensor_post_ok = False
                log("警告: 排出後に物体残留")
                for attempt in range(jam_attempts):
                    attempts = attempt + 2
                    if _stop():
                        return DispenseResult(
                            success=False, motor_type="SERVO",
                            message="中断されました", sensor_pre_ok=sensor_pre_ok,
                            sensor_post_ok=False, jam_cleared=jam_cleared,
                            attempts=attempts,
                        )
                    log(f"追加排出 {attempt + 1}/{jam_attempts}")
                    run_servo(config, speed=motor_speed, reverse=motor_reverse, duration=0.5, label="retry")
                    time.sleep(0.5)
                    if self.check_sensor(config, "(追加確認)"):
                        sensor_post_ok = True
                        log("追加排出成功")
                        break

        if not sensor_post_ok:
            return DispenseResult(
                success=False, motor_type="SERVO",
                message="排出失敗: 物体が詰まっています",
                sensor_pre_ok=sensor_pre_ok, sensor_post_ok=False,
                jam_cleared=jam_cleared, attempts=attempts,
                error="JAMMED",
            )

        return DispenseResult(
            success=True, motor_type="SERVO", message="排出完了",
            sensor_pre_ok=sensor_pre_ok, sensor_post_ok=sensor_post_ok,
            jam_cleared=jam_cleared, attempts=attempts,
        )

    # ── Internal: Motor test ────────────────────────────────────────────

    def _test_stepper(self, config, *, reverse=False, label="test") -> DispenseResult:
        if self._platform != "RASPI" or self._gpio is None:
            return DispenseResult(success=True, motor_type="STEPPER",
                                  message="PCモードのためモーターは動作しません")

        result = _stepper.run_stepper(
            self._gpio, config,
            steps=int(config.get("STEPPER_TEST_STEPS", 2048)),
            reverse=reverse,
            motor_speed=int(config.get("MOTOR_SPEED", 100)),
            label=label,
        )
        if result.get("ok"):
            return DispenseResult(success=True, motor_type="STEPPER",
                                  message=f"テスト完了 ({result.get('backend', '')})")
        return DispenseResult(success=False, motor_type="STEPPER",
                              message=str(result), error=str(result))

    def _test_servo(self, config, *, reverse=False, label="test") -> DispenseResult:
        if self._platform != "RASPI":
            return DispenseResult(success=True, motor_type="SERVO",
                                  message="PCモードのためモーターは動作しません")

        result = run_servo(config, reverse=reverse, duration=1.0, label=label)
        if result.ok:
            return DispenseResult(success=True, motor_type="SERVO",
                                  message=f"テスト完了 ch={result.channel} pwm={result.pwm_value}")
        return DispenseResult(success=False, motor_type="SERVO",
                              message=result.message, error=result.message)

    # ── Internal: LED ───────────────────────────────────────────────────

    def _indicate(self, config: Dict[str, Any], status: str) -> None:
        if self._platform != "RASPI" or self._gpio is None:
            return
        pin = int(config.get("GREEN_LED_PIN" if status == "success" else "RED_LED_PIN", 17))
        try:
            self._gpio.output(pin, self._gpio.HIGH)
            time.sleep(2)
            self._gpio.output(pin, self._gpio.LOW)
        except Exception:
            pass
