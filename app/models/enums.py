"""Domain enumerations for OITERU."""

from __future__ import annotations


class DispenseStatus:
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    DISPENSING = "dispensing"
    DISPENSED = "dispensed"  # physical dispense confirmed, not yet recorded
    RECORDED = "recorded"
    FAILED = "failed"

    ALL = {REQUESTED, AUTHORIZED, DISPENSING, DISPENSED, RECORDED, FAILED}

    @classmethod
    def terminal_states(cls) -> set:
        return {cls.RECORDED, cls.FAILED}


class DispenseErrorCode:
    INVALID_UNIT_CREDENTIALS = "INVALID_UNIT_CREDENTIALS"
    UNIT_STOCK_EMPTY = "UNIT_STOCK_EMPTY"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_DENIED = "USER_DENIED"
    USER_STOCK_EMPTY = "USER_STOCK_EMPTY"
    PERIOD_LIMIT_EXCEEDED = "PERIOD_LIMIT_EXCEEDED"
    DISPENSE_FAILED = "DISPENSE_FAILED"
    DISPENSE_FAILED_CLIENT = "DISPENSE_FAILED_CLIENT"


class LimitPeriod:
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

    ALL = {DAY, WEEK, MONTH}


class MotorType:
    SERVO = "SERVO"
    STEPPER = "STEPPER"

    ALL = {SERVO, STEPPER}


class ControlMethod:
    RASPI_DIRECT = "RASPI_DIRECT"
    ARDUINO_SERIAL = "ARDUINO_SERIAL"

    ALL = {RASPI_DIRECT, ARDUINO_SERIAL}


class StepperDriveMode:
    FULL = "full"
    HALF = "half"
    WAVE = "wave"

    ALL = {FULL, HALF, WAVE}


class StepperBackend:
    AUTO = "auto"
    PIGPIO = "pigpio"
    LIBRARY = "library"
    GPIO = "gpio"

    ALL = {AUTO, PIGPIO, LIBRARY, GPIO}


class UserAllowStatus:
    ALLOWED = 1
    DENIED = 0


class UnitConnectStatus:
    ONLINE = 1
    OFFLINE = 0


class UnitAvailableStatus:
    AVAILABLE = 1
    UNAVAILABLE = 0


class HistoryType:
    USAGE = "usage"
    SYSTEM = "system"
    SUCCESS = "success"
