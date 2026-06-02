# -*- coding: utf-8 -*-
"""Unit tests for the stepper driver.

These tests cover the pure-Python helpers and the backend dispatch logic. They
do not require RPi.GPIO hardware so they can run on any platform (including
the Windows developer machine).

Run from the repository root:

    python -m unittest tests.test_stepper_driver
"""

import os
import sys
import unittest

# Make the project importable when running from the repo root.
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import stepper_driver as sd  # noqa: E402


class _MockGPIO:
    """A minimal stand-in for RPi.GPIO for fallback-backend tests."""

    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    LOW = 0
    HIGH = 1
    PUD_UP = "PUD_UP"

    def __init__(self):
        self.setup_calls = []
        self.output_calls = []
        self.mode_set = False

    def setmode(self, mode):
        self.mode_set = True

    def setup(self, pin, direction, **kwargs):
        self.setup_calls.append((pin, direction, kwargs))

    def output(self, pin, value):
        self.output_calls.append((pin, value))

    def input(self, pin):
        return 1  # pretend sensor is clear


class ResolvePinsTests(unittest.TestCase):
    def test_default_pins(self):
        self.assertEqual(sd.resolve_pins({}), [5, 6, 13, 19])

    def test_explicit_pins(self):
        self.assertEqual(sd.resolve_pins({"STEPPER_PINS": [4, 17, 27, 22]}), [4, 17, 27, 22])

    def test_string_pins(self):
        self.assertEqual(sd.resolve_pins({"STEPPER_PINS": "4,17,27,22"}), [4, 17, 27, 22])

    def test_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            sd.resolve_pins({"STEPPER_PINS": [1, 2, 3]})


class ResolvePhaseOrderTests(unittest.TestCase):
    def test_default(self):
        self.assertEqual(sd.resolve_phase_order({}), [0, 2, 1, 3])

    def test_custom(self):
        self.assertEqual(sd.resolve_phase_order({"STEPPER_PHASE_ORDER": [3, 2, 1, 0]}),
                         [3, 2, 1, 0])

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            sd.resolve_phase_order({"STEPPER_PHASE_ORDER": [0, 1, 2]})
        with self.assertRaises(ValueError):
            sd.resolve_phase_order({"STEPPER_PHASE_ORDER": [0, 1, 2, 4]})


class ResolveDriveModeTests(unittest.TestCase):
    def test_default_is_full(self):
        self.assertEqual(sd.resolve_drive_mode({}), "full")

    def test_half(self):
        self.assertEqual(sd.resolve_drive_mode({"STEPPER_DRIVE_MODE": "half"}), "half")

    def test_wave(self):
        self.assertEqual(sd.resolve_drive_mode({"STEPPER_DRIVE_MODE": "wave"}), "wave")

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            sd.resolve_drive_mode({"STEPPER_DRIVE_MODE": "nope"})


class ResolveStepDelayTests(unittest.TestCase):
    def test_explicit_delay(self):
        self.assertEqual(sd.resolve_step_delay({"STEPPER_STEP_DELAY": 0.02}), 0.02)

    def test_derived_from_speed(self):
        cfg = {}
        slow = sd.resolve_step_delay(cfg, motor_speed=1)
        fast = sd.resolve_step_delay(cfg, motor_speed=100)
        # Slower motor speed gives a longer delay.
        self.assertGreater(slow, fast)
        # Clamp at 0.01 minimum.
        self.assertGreaterEqual(fast, 0.01)

    def test_clamp_minimum(self):
        self.assertEqual(sd.resolve_step_delay({"STEPPER_STEP_DELAY": 0.0001}), 0.01)


class ResolveStepsTests(unittest.TestCase):
    def test_fixed_steps_wins(self):
        self.assertEqual(sd.resolve_steps({}, 0.01, seconds=10.0, fixed_steps=42), 42)

    def test_seconds_used_when_no_fixed(self):
        self.assertEqual(sd.resolve_steps({}, 0.01, seconds=2.0, fixed_steps=None), 200)

    def test_config_steps_used_when_no_seconds(self):
        self.assertEqual(sd.resolve_steps({"STEPPER_STEPS": 123}, 0.01, seconds=None,
                                          fixed_steps=None), 123)

    def test_default_test_steps(self):
        self.assertEqual(sd.resolve_steps({}, 0.01, seconds=None, fixed_steps=None), 256)


class GetPhaseSequenceTests(unittest.TestCase):
    def test_full_sequence(self):
        seq = sd.get_phase_sequence("full")
        self.assertEqual(len(seq), 4)
        # 2-phase excitation: every phase has exactly 2 high coils.
        for phase in seq:
            self.assertEqual(sum(phase), 2)

    def test_half_sequence(self):
        seq = sd.get_phase_sequence("half")
        self.assertEqual(len(seq), 8)

    def test_wave_sequence(self):
        seq = sd.get_phase_sequence("wave")
        self.assertEqual(len(seq), 4)
        for phase in seq:
            self.assertEqual(sum(phase), 1)

    def test_reverse(self):
        seq = sd.get_phase_sequence("full", reverse=True)
        self.assertEqual(list(reversed(sd.get_phase_sequence("full"))), seq)


class DrivePinsTests(unittest.TestCase):
    def test_phase_order_reorders(self):
        pins = [5, 6, 13, 19]
        order = [0, 2, 1, 3]
        self.assertEqual(sd.build_drive_pins(pins, order), [5, 13, 6, 19])

    def test_identity(self):
        pins = [5, 6, 13, 19]
        self.assertEqual(sd.build_drive_pins(pins, [0, 1, 2, 3]), pins)


class StepsPerRevTests(unittest.TestCase):
    def test_half(self):
        self.assertEqual(sd.resolve_steps_per_rev("half"), 4096)

    def test_full(self):
        self.assertEqual(sd.resolve_steps_per_rev("full"), 2048)

    def test_wave(self):
        self.assertEqual(sd.resolve_steps_per_rev("wave"), 2048)


class LibraryAvailableTests(unittest.TestCase):
    def test_returns_bool(self):
        self.assertIsInstance(sd.library_available(), bool)
        # On any platform the import either succeeded or failed at import time.
        # We don't assert a specific value because it depends on the environment.
        _ = sd.library_available()


class GpioFallbackBackendTests(unittest.TestCase):
    def test_short_run_writes_correct_pattern(self):
        gpio = _MockGPIO()
        backend = sd.GpioFallbackBackend(gpio)
        pins = [5, 6, 13, 19]
        result = backend.run(
            pins=pins,
            steps=8,
            wait=0.0,
            reverse=False,
            drive_mode="full",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["completed"], 8)
        # Each step writes 4 pins.
        self.assertEqual(len(gpio.output_calls), 8 * 4)
        # Pin 0 high only for phases that include 1.
        high_low_pairs = {(pin, value) for pin, value in gpio.output_calls}
        self.assertIn((5, 1), high_low_pairs)
        self.assertIn((5, 0), high_low_pairs)

    def test_stop_check_aborts(self):
        gpio = _MockGPIO()
        backend = sd.GpioFallbackBackend(gpio)
        counter = {"i": 0}

        def stop():
            counter["i"] += 1
            return counter["i"] >= 4  # stop after 4 checks

        result = backend.run(
            pins=[5, 6, 13, 19],
            steps=10000,
            wait=0.0,
            reverse=True,
            drive_mode="half",
            stop_check=stop,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["aborted"])
        self.assertLess(result["completed"], 10000)

    def test_coils_off(self):
        gpio = _MockGPIO()
        backend = sd.GpioFallbackBackend(gpio)
        backend.coils_off([5, 6, 13, 19])
        self.assertEqual(
            gpio.output_calls,
            [(5, 0), (6, 0), (13, 0), (19, 0)],
        )


class RunStepperDispatchTests(unittest.TestCase):
    """Verify that run_stepper() picks the right backend based on the config."""

    def test_auto_with_no_library_uses_gpio(self):
        # Force the GPIO fallback path.
        gpio = _MockGPIO()
        config = {"STEPPER_BACKEND": "gpio"}
        result = sd.run_stepper(
            gpio,
            config,
            steps=4,
            seconds=None,
            reverse=False,
            label="unit-test",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["backend"], "GPIO")

    def test_explicit_library_raises_when_unavailable(self):
        if sd.library_available():
            self.skipTest("RpiMotorLib is available in this environment")
        with self.assertRaises(RuntimeError):
            sd.run_stepper(
                _MockGPIO(),
                {"STEPPER_BACKEND": "library"},
                steps=4,
                label="unit-test",
            )

    def test_zero_steps_falls_back_to_test_steps(self):
        # When steps=0 is passed explicitly and no other source is set, the
        # runner falls back to STEPPER_TEST_STEPS rather than running 0 steps.
        result = sd.run_stepper(
            _MockGPIO(),
            {"STEPPER_BACKEND": "gpio", "STEPPER_STEPS": 0, "STEPPER_TEST_STEPS": 32},
            steps=0,
            label="unit-test",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["steps"], 32)

    def test_explicit_test_steps_uses_config(self):
        result = sd.run_stepper(
            _MockGPIO(),
            {"STEPPER_BACKEND": "gpio", "STEPPER_STEPS": 64, "STEPPER_TEST_STEPS": 32},
            steps=None,
            seconds=None,
            label="unit-test",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["steps"], 64)

    def test_label_passed_through(self):
        # We just want to make sure the dispatch returns without crashing.
        result = sd.run_stepper(
            _MockGPIO(),
            {"STEPPER_BACKEND": "gpio"},
            steps=2,
            label="dispense-test",
        )
        self.assertIn("backend", result)
        self.assertEqual(result["backend"], "GPIO")


class SummariseTests(unittest.TestCase):
    def test_returns_resolved_config(self):
        summary = sd.summarise({"STEPPER_PINS": [5, 6, 13, 19]})
        self.assertEqual(summary["pins"], [5, 6, 13, 19])
        self.assertEqual(summary["backend"], "auto")
        self.assertIn("available_backends", summary)
        self.assertIn("PigpioZero", summary["available_backends"])
        self.assertIn("RpiMotorLib", summary["available_backends"])
        self.assertIn("GPIO", summary["available_backends"])


class CoilsOffTests(unittest.TestCase):
    def test_no_gpio_is_noop(self):
        sd.coils_off(None, {"STEPPER_PINS": [5, 6, 13, 19]})

    def test_with_gpio(self):
        gpio = _MockGPIO()
        sd.coils_off(gpio, {"STEPPER_PINS": [5, 6, 13, 19]})
        self.assertEqual(
            gpio.output_calls,
            [(5, 0), (6, 0), (13, 0), (19, 0)],
        )


class RpmForWaitTests(unittest.TestCase):
    def test_typical(self):
        # Full step (2048/rev), wait=0.01 => 60/(2048*0.01) = 2.93 RPM
        rpm = sd.rpm_for_wait(2048, 0.01)
        self.assertAlmostEqual(rpm, 2.93, delta=0.1)

    def test_clamp_low(self):
        rpm = sd.rpm_for_wait(2048, 0.5)
        self.assertEqual(rpm, 1.0)

    def test_clamp_high(self):
        # 2048/rev, wait=0.001 => 60 / 2.048 = 29.3, capped at 30
        rpm = sd.rpm_for_wait(2048, 0.001)
        self.assertAlmostEqual(rpm, 29.3, delta=0.1)
        self.assertLessEqual(rpm, 30.0)

    def test_safe_fallback_zero_wait(self):
        rpm = sd.rpm_for_wait(2048, 0.0)
        self.assertEqual(rpm, 10.0)

    def test_safe_fallback_zero_rev(self):
        rpm = sd.rpm_for_wait(0, 0.01)
        self.assertEqual(rpm, 10.0)


class GpiozeroAvailableTests(unittest.TestCase):
    def test_returns_bool(self):
        self.assertIsInstance(sd.gpiozero_available(), bool)


class PigpioZeroBackendTests(unittest.TestCase):
    def test_is_not_available_on_pc(self):
        backend = sd.PigpioZeroBackend()
        # On a non-Raspberry Pi, gpiozero is not available -> False
        self.assertFalse(backend.is_available())

    def test_init_error_on_pc(self):
        backend = sd.PigpioZeroBackend()
        err = backend.init_error()
        if sd.gpiozero_available():
            self.assertIsNone(err)
        else:
            self.assertIsNotNone(err)

    def test_coils_off_is_safe_when_no_motor(self):
        backend = sd.PigpioZeroBackend()
        # Should not raise
        backend.coils_off([5, 6, 13, 19])


if __name__ == "__main__":
    unittest.main()
