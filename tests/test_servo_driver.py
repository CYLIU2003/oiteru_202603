"""Tests for unit/servo_driver.py."""

from unit.servo_driver import (
    ServoResult,
    servo_pwm_for_speed,
    run_servo,
    pca9685_available,
    pca9685_import_error,
    MockServoBackend,
    _clamp_duration,
    DEFAULT_CHANNEL,
    PWM_MIN,
    PWM_MAX,
)


class TestServoPwmForSpeed:
    def test_min_speed(self):
        # speed=1 → 150 + 1/100*450 = 154.5 → 154
        pwm = servo_pwm_for_speed(1)
        assert pwm == 154

    def test_max_speed(self):
        pwm = servo_pwm_for_speed(100)
        assert pwm == PWM_MAX  # 600

    def test_mid_speed(self):
        pwm = servo_pwm_for_speed(50)
        expected = int(PWM_MIN + 0.5 * (PWM_MAX - PWM_MIN))
        assert abs(pwm - expected) <= 1

    def test_reverse_inverts(self):
        forward = servo_pwm_for_speed(100, reverse=False)
        reverse = servo_pwm_for_speed(100, reverse=True)
        assert forward == PWM_MAX  # 600
        assert reverse == PWM_MIN  # 150

    def test_clamp_below_1(self):
        # -10 clamped to 1 → 150 + 1/100*450 = 154
        pwm = servo_pwm_for_speed(-10)
        assert pwm == 154

    def test_clamp_above_100(self):
        pwm = servo_pwm_for_speed(200)
        assert pwm == PWM_MAX

    def test_zero_speed(self):
        # 0 clamped to 1 → 150 + 1/100*450 = 154
        pwm = servo_pwm_for_speed(0)
        assert pwm == 154


class TestClampDuration:
    def test_normal(self):
        assert _clamp_duration(2.0) == 2.0

    def test_clamp_below_min(self):
        assert _clamp_duration(0.01) == 0.1

    def test_clamp_above_max(self):
        assert _clamp_duration(120.0) == 60.0


class TestPca9685Available:
    def test_returns_bool(self):
        result = pca9685_available()
        assert isinstance(result, bool)

    def test_import_error_is_none_when_available(self):
        if pca9685_available():
            assert pca9685_import_error() is None
        else:
            assert pca9685_import_error() is not None


class TestMockServoBackend:
    def test_is_available(self):
        b = MockServoBackend()
        assert b.is_available()

    def test_run_returns_ok(self):
        b = MockServoBackend()
        result = b.run(channel=0, pwm_value=300, duration=1.0)
        assert result.ok
        assert result.pwm_value == 300
        assert result.duration == 1.0
        assert result.channel == 0
        assert "mock" in result.message.lower()

    def test_tracks_last_values(self):
        b = MockServoBackend()
        b.run(channel=12, pwm_value=555, duration=2.5)
        assert b.last_channel == 12
        assert b.last_pwm == 555

    def test_stop_is_noop(self):
        b = MockServoBackend()
        b.stop(5)
        # no exception = pass


class TestRunServoEntryPoint:
    def test_uses_config_defaults(self):
        config = {
            "MOTOR_SPEED": 50,
            "MOTOR_REVERSE": False,
            "MOTOR_DURATION": 2.0,
            "PCA9685_CHANNEL": 7,
        }
        result = run_servo(config, label="test")
        assert result.ok
        assert result.channel == 7
        assert result.duration == 2.0

    def test_explicit_overrides_config(self):
        config = {
            "MOTOR_SPEED": 50,
            "MOTOR_REVERSE": False,
            "MOTOR_DURATION": 2.0,
            "PCA9685_CHANNEL": 7,
        }
        result = run_servo(config, speed=80, reverse=True, duration=3.0, channel=2, label="test")
        assert result.channel == 2
        assert result.duration == 3.0

    def test_clamps_channel_range(self):
        config = {"MOTOR_SPEED": 50, "MOTOR_REVERSE": False, "MOTOR_DURATION": 1.0, "PCA9685_CHANNEL": 999}
        result = run_servo(config, label="test")
        assert 0 <= result.channel <= 15

    def test_clamps_duration(self):
        config = {"MOTOR_SPEED": 50, "MOTOR_REVERSE": False, "MOTOR_DURATION": 0.0, "PCA9685_CHANNEL": 0}
        result = run_servo(config, label="test")
        assert result.duration >= 0.1

    def test_label_does_not_crash(self):
        config = {"MOTOR_SPEED": 50, "MOTOR_REVERSE": False, "MOTOR_DURATION": 1.0}
        result = run_servo(config, label="integration-test-42")
        assert result.ok


class TestServoResult:
    def test_defaults(self):
        r = ServoResult()
        assert r.ok is True
        assert r.channel == DEFAULT_CHANNEL
        assert r.pwm_value == 0

    def test_failure_result(self):
        r = ServoResult(ok=False, message="I2C bus error")
        assert not r.ok
        assert "I2C" in r.message
