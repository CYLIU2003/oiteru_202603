"""Tests for unit/hardware_controller.py."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from unit.hardware_controller import (
    DispenseRequest,
    DispenseResult,
    HardwareController,
)


# ---------------------------------------------------------------------------
# Mock GPIO (same pattern as stepper_driver tests)
# ---------------------------------------------------------------------------


class FakeGPIO:
    BCM = "BCM"
    BOARD = "BOARD"
    OUT = "OUT"
    IN = "IN"
    HIGH = 1
    LOW = 0
    PUD_UP = "PUD_UP"

    def __init__(self):
        self.pin_states = {}
        self.setups = []

    def setmode(self, mode):
        pass

    def setwarnings(self, flag):
        pass

    def setup(self, pin, mode, initial=None, pull_up_down=None):
        self.setups.append((pin, mode))
        self.pin_states[pin] = initial or self.LOW

    def output(self, pin, value):
        self.pin_states[pin] = value

    def input(self, pin):
        return self.pin_states.get(pin, self.HIGH)

    def cleanup(self):
        self.pin_states.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(motor_type="STEPPER", use_sensor=False, **kwargs):
    base = {
        "MOTOR_TYPE": motor_type,
        "MOTOR_SPEED": 100,
        "MOTOR_DURATION": 2.0,
        "MOTOR_REVERSE": False,
        "USE_SENSOR": use_sensor,
        "SENSOR_PIN": 22,
        "SENSOR_CHECK_PRE": True,
        "SENSOR_CHECK_POST": True,
        "JAM_CLEAR_ATTEMPTS": 3,
        "SENSOR_STABILIZE_TIME": 0.3,
        "GREEN_LED_PIN": 17,
        "RED_LED_PIN": 27,
        "STEPPER_PINS": [21, 17, 27, 22],
        "STEPPER_TEST_STEPS": 2048,
        "PCA9685_CHANNEL": 15,
    }
    base.update(kwargs)
    return base


def make_request(config=None, stop_event=None, on_log=None):
    return DispenseRequest(
        config=config or make_config(),
        stop_event=stop_event,
        on_log=on_log or (lambda _: None),
    )


# ---------------------------------------------------------------------------
# Mock stepper_driver at module level
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_stepper_driver():
    with patch("unit.hardware_controller._stepper") as mock:
        mock.run_stepper.return_value = {"ok": True, "completed": 2048, "aborted": False, "backend": "GPIO"}
        mock.coils_off.return_value = None
        mock.resolve_drive_mode.return_value = "half"
        mock.resolve_steps_per_rev.return_value = 2048
        yield mock


# ---------------------------------------------------------------------------
# Mock servo_driver
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_servo_driver():
    with patch("unit.hardware_controller.run_servo") as mock_run, \
         patch("unit.hardware_controller.servo_stop") as mock_stop:
        from unit.servo_driver import ServoResult
        mock_run.return_value = ServoResult(ok=True, message="servo ok", pwm_value=300, duration=2.0)
        yield mock_run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDispenseResult:
    def test_defaults(self):
        r = DispenseResult(success=True)
        assert r.motor_type == "STEPPER"
        assert r.sensor_pre_ok is True

    def test_failure_with_error(self):
        r = DispenseResult(success=False, error="JAMMED", motor_type="SERVO")
        assert not r.success
        assert r.error == "JAMMED"
        assert r.motor_type == "SERVO"


class TestHardwareControllerInit:
    def test_can_create_without_gpio(self):
        ctrl = HardwareController(platform="PC")
        assert ctrl._platform == "PC"
        assert ctrl._gpio is None

    def test_can_create_with_gpio(self):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        assert ctrl._gpio is gpio


class TestDispenseStepper:
    def test_pc_mode_returns_success(self):
        ctrl = HardwareController(platform="PC")
        result = ctrl.dispense(make_request(make_config("STEPPER", use_sensor=False)))
        assert result.success
        assert "PC" not in result.message  # run_stepper runs on PC with mock GPIO

    def test_delegates_to_run_stepper_with_seconds(self, mock_stepper_driver):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        config = make_config("STEPPER", use_sensor=False, MOTOR_DURATION=3.5, MOTOR_SPEED=80, MOTOR_REVERSE=True)
        ctrl.dispense(make_request(config))

        call_kwargs = mock_stepper_driver.run_stepper.call_args
        assert call_kwargs is not None
        _, kwargs = call_kwargs
        assert kwargs["seconds"] == 3.5
        assert kwargs["reverse"] is True
        assert kwargs["motor_speed"] == 80
        assert kwargs["label"] == "dispense"

    def test_run_stepper_failure_propagates(self, mock_stepper_driver):
        mock_stepper_driver.run_stepper.return_value = {"ok": False, "error": "GPIO error"}
        ctrl = HardwareController(platform="RASPI")
        request = make_request(make_config("STEPPER", use_sensor=False))
        result = ctrl.dispense(request)
        assert not result.success
        assert "GPIO error" in result.message

    def test_stop_event_aborts(self, mock_stepper_driver):
        stop_event = threading.Event()
        stop_event.set()
        ctrl = HardwareController(platform="RASPI")
        request = make_request(make_config("STEPPER", use_sensor=False), stop_event=stop_event)
        result = ctrl.dispense(request)
        assert not result.success
        assert "中断" in result.message

    def test_sensor_pre_jam_then_clear(self, mock_stepper_driver):
        gpio = FakeGPIO()
        # Simulate: 3 low readings (jam), then 3 high readings (clear)
        read_count = [0]

        def fake_input(pin):
            read_count[0] += 1
            # First 3 reads LOW (jam), then all HIGH (clear)
            return gpio.LOW if read_count[0] <= 3 else gpio.HIGH

        gpio.input = fake_input

        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        config = make_config("STEPPER", use_sensor=True, SENSOR_CHECK_PRE=True, JAM_CLEAR_ATTEMPTS=3)
        request = make_request(config, on_log=lambda _: None)
        result = ctrl.dispense(request)

        assert not result.sensor_pre_ok  # first check was jam
        assert result.jam_cleared is True  # second check cleared
        assert result.success


class TestDispenseServo:
    def test_delegates_to_run_servo(self, mock_servo_driver):
        ctrl = HardwareController(platform="RASPI")
        config = make_config("SERVO", use_sensor=False, MOTOR_SPEED=50, MOTOR_REVERSE=True, MOTOR_DURATION=3.0)
        result = ctrl.dispense(make_request(config))
        assert result.success
        assert result.motor_type == "SERVO"

        mock_servo_driver.assert_called_once()
        _, kwargs = mock_servo_driver.call_args
        assert kwargs["speed"] == 50
        assert kwargs["reverse"] is True
        assert kwargs["duration"] == 3.0

    def test_servo_failure_propagates(self, mock_servo_driver):
        from unit.servo_driver import ServoResult
        mock_servo_driver.return_value = ServoResult(ok=False, message="I2C error")
        ctrl = HardwareController(platform="RASPI")
        result = ctrl.dispense(make_request(make_config("SERVO", use_sensor=False)))
        assert not result.success
        assert "I2C error" in result.message


class TestUnknownMotorType:
    def test_returns_error(self):
        ctrl = HardwareController(platform="RASPI")
        result = ctrl.dispense(make_request(make_config("BRUSHLESS")))
        assert not result.success
        assert "未サポート" in result.message


class TestTestMotor:
    def test_stepper_test(self, mock_stepper_driver):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        result = ctrl.test_motor(make_config("STEPPER"), reverse=True, label="api-test")
        assert result.success
        assert result.motor_type == "STEPPER"

        _, kwargs = mock_stepper_driver.run_stepper.call_args
        assert kwargs["label"] == "api-test"
        assert kwargs["reverse"] is True

    def test_servo_test(self, mock_servo_driver):
        ctrl = HardwareController(platform="RASPI")
        result = ctrl.test_motor(make_config("SERVO"), reverse=False, label="ui-test")
        assert result.success
        assert result.motor_type == "SERVO"
        _, kwargs = mock_servo_driver.call_args
        assert kwargs["label"] == "ui-test"
        assert kwargs["duration"] == 1.0

    def test_pc_mode_returns_ok_without_hardware(self, mock_stepper_driver):
        ctrl = HardwareController(platform="PC")
        result = ctrl.test_motor(make_config("STEPPER"))
        assert result.success
        assert "PCモード" in result.message
        mock_stepper_driver.run_stepper.assert_not_called()

    def test_unknown_motor_type_test(self):
        ctrl = HardwareController(platform="RASPI")
        result = ctrl.test_motor(make_config("DC_MOTOR"))
        assert not result.success
        assert "未サポート" in result.message


class TestCoilsOff:
    def test_stepper_coils_off(self, mock_stepper_driver):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        ctrl.coils_off(make_config("STEPPER"))
        mock_stepper_driver.coils_off.assert_called_once()

    def test_servo_coils_off(self):
        ctrl = HardwareController(platform="RASPI")
        ctrl.coils_off(make_config("SERVO"))
        # servo_stop was called (via mock, no exception)


class TestCheckSensor:
    def test_sensor_disabled_returns_true(self):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        assert ctrl.check_sensor(make_config("STEPPER", use_sensor=False))

    def test_pc_mode_returns_true(self):
        ctrl = HardwareController(platform="PC")
        assert ctrl.check_sensor(make_config("STEPPER", use_sensor=True))

    def test_no_object_returns_true(self):
        gpio = FakeGPIO()
        gpio.pin_states[22] = gpio.HIGH  # clear
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        assert ctrl.check_sensor(make_config("STEPPER", use_sensor=True))

    def test_object_detected_returns_false(self):
        gpio = FakeGPIO()
        gpio.pin_states[22] = gpio.LOW  # object
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        assert not ctrl.check_sensor(make_config("STEPPER", use_sensor=True))


class TestIndicate:
    def test_indicate_success_high_then_low(self):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        ctrl.indicate_success(make_config())
        # LED should have been set HIGH then LOW after 2s
        assert gpio.pin_states.get(17) == gpio.LOW

    def test_indicate_failure_uses_red_pin(self):
        gpio = FakeGPIO()
        ctrl = HardwareController(gpio_module=gpio, platform="RASPI")
        ctrl.indicate_failure(make_config())
        assert gpio.pin_states.get(27) == gpio.LOW

    def test_pc_mode_noop(self):
        ctrl = HardwareController(platform="PC")
        ctrl.indicate_success(make_config())  # no exception

    def test_no_gpio_noop(self):
        ctrl = HardwareController(gpio_module=None, platform="RASPI")
        ctrl.indicate_failure(make_config())  # no exception


class TestDispenseRequest:
    def test_default_log_is_noop(self):
        req = DispenseRequest(config=make_config())
        req.on_log("test")  # no exception
