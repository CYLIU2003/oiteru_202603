"""Tests for app models and enums."""

from app.models.enums import (
    DispenseStatus,
    DispenseErrorCode,
    LimitPeriod,
    MotorType,
    ControlMethod,
    StepperDriveMode,
    StepperBackend,
)


class TestDispenseStatus:
    def test_terminal_states(self):
        terminal = DispenseStatus.terminal_states()
        assert DispenseStatus.RECORDED in terminal
        assert DispenseStatus.FAILED in terminal
        assert DispenseStatus.REQUESTED not in terminal
        assert DispenseStatus.AUTHORIZED not in terminal

    def test_all_states_defined(self):
        assert len(DispenseStatus.ALL) == 6


class TestDispenseErrorCode:
    def test_all_codes_defined(self):
        assert DispenseErrorCode.INVALID_UNIT_CREDENTIALS is not None
        assert DispenseErrorCode.UNIT_STOCK_EMPTY is not None
        assert DispenseErrorCode.USER_NOT_FOUND is not None
        assert DispenseErrorCode.PERIOD_LIMIT_EXCEEDED is not None


class TestLimitPeriod:
    def test_all_periods(self):
        assert "day" in LimitPeriod.ALL
        assert "week" in LimitPeriod.ALL
        assert "month" in LimitPeriod.ALL


class TestMotorType:
    def test_valid_types(self):
        assert MotorType.SERVO in MotorType.ALL
        assert MotorType.STEPPER in MotorType.ALL
        assert "INVALID" not in MotorType.ALL


class TestStepperBackend:
    def test_valid_backends(self):
        assert StepperBackend.AUTO in StepperBackend.ALL
        assert StepperBackend.PIGPIO in StepperBackend.ALL
        assert StepperBackend.LIBRARY in StepperBackend.ALL
        assert StepperBackend.GPIO in StepperBackend.ALL
