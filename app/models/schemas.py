"""Data transfer schemas and type definitions for OITERU."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class UserRecord:
    id: int
    card_id: str
    card_id_hash: str = ""
    allow: int = 1
    entry: Optional[str] = None
    stock: int = 2
    today: int = 0
    total: int = 0
    last_reset_date: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "UserRecord":
        return cls(
            id=int(row["id"]),
            card_id=str(row.get("card_id", "")),
            card_id_hash=str(row.get("card_id_hash", "")),
            allow=int(row.get("allow", 1)),
            entry=row.get("entry"),
            stock=int(row.get("stock", 2)),
            today=int(row.get("today", 0)),
            total=int(row.get("total", 0)),
            last_reset_date=_normalize_date_str(row.get("last_reset_date")),
        )


@dataclass
class UnitRecord:
    id: int
    name: str
    password: str
    stock: int = 0
    initial_stock: int = 100
    connect: int = 0
    available: int = 1
    last_seen: Optional[str] = None
    ip_address: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "UnitRecord":
        return cls(
            id=int(row["id"]),
            name=str(row["name"]),
            password=str(row.get("password", "")),
            stock=int(row.get("stock", 0)),
            initial_stock=int(row.get("initial_stock", 100)),
            connect=int(row.get("connect", 0)),
            available=int(row.get("available", 1)),
            last_seen=_normalize_date_str(row.get("last_seen")),
            ip_address=row.get("ip_address"),
        )


@dataclass
class DispenseEventRecord:
    id: int
    event_id: str
    unit_name: str
    card_id: str
    status: str
    error_code: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "DispenseEventRecord":
        return cls(
            id=int(row["id"]),
            event_id=str(row["event_id"]),
            unit_name=str(row["unit_name"]),
            card_id=str(row["card_id"]),
            status=str(row["status"]),
            error_code=row.get("error_code"),
            created_at=_normalize_date_str(row.get("created_at")),
            updated_at=_normalize_date_str(row.get("updated_at")),
        )


@dataclass
class HistoryRecord:
    id: int
    txt: str
    type: str = "usage"
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "HistoryRecord":
        return cls(
            id=int(row["id"]),
            txt=str(row.get("txt", "")),
            type=str(row.get("type", "usage")),
            created_at=_normalize_date_str(row.get("created_at")),
        )


@dataclass
class SettingsRecord:
    id: int = 1
    auto_register_mode: bool = False
    auto_register_stock: int = 2
    usage_limit: int = 2
    limit_period: str = "day"
    version: int = 0
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "SettingsRecord":
        return cls(
            id=int(row.get("id", 1)),
            auto_register_mode=bool(row.get("auto_register_mode", 0)),
            auto_register_stock=int(row.get("auto_register_stock", 2)),
            usage_limit=int(row.get("usage_limit") or row.get("daily_limit", 2)),
            limit_period=str(row.get("limit_period", "day") or "day"),
            version=int(row.get("version", 0)),
            updated_at=_normalize_date_str(row.get("updated_at")),
        )


@dataclass
class InfoRecord:
    id: int = 1
    pass_: str = ""

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "InfoRecord":
        return cls(
            id=int(row.get("id", 1)),
            pass_=str(row.get("pass", "")),
        )


@dataclass
class UnitConfigData:
    MOTOR_TYPE: str = "STEPPER"
    CONTROL_METHOD: str = "RASPI_DIRECT"
    MOTOR_SPEED: int = 80
    MOTOR_DURATION: float = 2.0
    MOTOR_REVERSE: bool = False
    USE_SENSOR: bool = False
    SENSOR_GPIO_PIN: int = 22
    SENSOR_TIMEOUT: float = 5.0
    SENSOR_CHECK_PRE: bool = True
    SENSOR_CHECK_POST: bool = True
    JAM_CLEAR_ATTEMPTS: int = 3
    HEARTBEAT_INTERVAL: int = 30
    ARDUINO_PORT: str = "/dev/ttyUSB0"
    PCA9685_CHANNEL: int = 15
    STEPPER_PINS: List[int] = field(default_factory=lambda: [21, 17, 27, 22])
    STEPPER_PHASE_ORDER: List[int] = field(default_factory=lambda: [0, 1, 2, 3])
    STEPPER_STEP_DELAY: float = 0.01
    STEPPER_DRIVE_MODE: str = "half"
    STEPPER_STEPS: int = 0
    STEPPER_STEPS_PER_REV: int = 2048
    STEPPER_TEST_STEPS: int = 2048
    STEPPER_BACKEND: str = "auto"


@dataclass
class ServerSettings:
    auto_register_mode: bool = False
    auto_register_stock: int = 2
    usage_limit: int = 2
    limit_period: str = "day"
    server_name: str = "OITERU親機"
    server_location: str = "未設定"


@dataclass
class HeartbeatResponse:
    success: bool
    stock: int = 0
    available: int = 0
    unit_api_token: Optional[str] = None
    config_update: Optional[Dict[str, Any]] = None
    pending_config: Optional[Dict[str, Any]] = None
    settings_version: int = 0
    error: Optional[str] = None
    pending: bool = False


@dataclass
class DispenseResultResponse:
    success: bool
    recorded: bool = False
    idempotent: bool = False
    event_id: Optional[str] = None
    error_code: Optional[str] = None
    error: Optional[str] = None
    user_stock: Optional[int] = None
    unit_stock: Optional[int] = None


@dataclass
class ErrorResponse:
    error: str
    success: bool = False
    error_code: Optional[str] = None
    event_id: Optional[str] = None


@dataclass
class SuccessResponse:
    success: bool = True
    message: Optional[str] = None


def _normalize_date_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value) if value else None
