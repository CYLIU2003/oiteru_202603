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
            card_id=str(row.get("card_id") or ""),
            card_id_hash=str(row.get("card_id_hash") or ""),
            allow=_int_or_default(row.get("allow"), 1),
            entry=row.get("entry"),
            stock=_int_or_default(row.get("stock"), 2),
            today=_int_or_default(row.get("today"), 0),
            total=_int_or_default(row.get("total"), 0),
            last_reset_date=_normalize_date_str(row.get("last_reset_date")),
        )


@dataclass
class UnitRecord:
    id: int
    name: str
    password: str = ""
    stock: int = 0
    initial_stock: int = 100
    connect: int = 0
    available: int = 1
    last_seen: Optional[str] = None
    ip_address: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "UnitRecord":
        raw_ip = row.get("ip_address")
        ip_address = str(raw_ip).strip() if raw_ip is not None and str(raw_ip).strip() else None
        return cls(
            id=_int_or_default(row.get("id"), 0),
            name=str(row.get("name") or ""),
            password=str(row.get("password") or ""),
            stock=_int_or_default(row.get("stock"), 0),
            initial_stock=_int_or_default(row.get("initial_stock"), 100),
            connect=_int_or_default(row.get("connect"), 0),
            available=_int_or_default(row.get("available"), 1),
            last_seen=_normalize_date_str(row.get("last_seen")),
            ip_address=ip_address,
        )


@dataclass
class StockMovementRecord:
    id: int
    unit_id: int
    movement_type: str
    quantity_delta: int
    stock_before: int
    stock_after: int
    reason: str
    admin_user_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    unit_name: str | None = None
    admin_username: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> StockMovementRecord:
        return cls(
            id=int(row["id"]),
            unit_id=int(row["unit_id"]),
            movement_type=str(row["movement_type"]),
            quantity_delta=int(row["quantity_delta"]),
            stock_before=int(row["stock_before"]),
            stock_after=int(row["stock_after"]),
            reason=str(row["reason"]),
            admin_user_id=_optional_int(row.get("admin_user_id")),
            created_at=_normalize_date_str(row.get("created_at")),
            updated_at=_normalize_date_str(row.get("updated_at")),
            unit_name=row.get("unit_name"),
            admin_username=row.get("admin_username"),
        )


@dataclass
class MaintenanceTicketRecord:
    id: int
    unit_id: int
    category: str
    status: str
    source: str
    description: str
    opened_by_admin_user_id: int | None = None
    assigned_to_admin_user_id: int | None = None
    resolution_note: str | None = None
    resolved_by_admin_user_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    resolved_at: str | None = None
    unit_name: str | None = None
    assigned_to_username: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> MaintenanceTicketRecord:
        return cls(
            id=int(row["id"]),
            unit_id=int(row["unit_id"]),
            category=str(row["category"]),
            status=str(row["status"]),
            source=str(row["source"]),
            description=str(row["description"]),
            opened_by_admin_user_id=_optional_int(row.get("opened_by_admin_user_id")),
            assigned_to_admin_user_id=_optional_int(row.get("assigned_to_admin_user_id")),
            resolution_note=row.get("resolution_note"),
            resolved_by_admin_user_id=_optional_int(row.get("resolved_by_admin_user_id")),
            created_at=_normalize_date_str(row.get("created_at")),
            updated_at=_normalize_date_str(row.get("updated_at")),
            resolved_at=_normalize_date_str(row.get("resolved_at")),
            unit_name=row.get("unit_name"),
            assigned_to_username=row.get("assigned_to_username"),
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
            id=_int_or_default(row.get("id"), 0),
            txt=str(row.get("txt") or ""),
            type=str(row.get("type") or "usage"),
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
        usage_limit_raw = row.get("usage_limit")
        if usage_limit_raw is None:
            usage_limit_raw = row.get("daily_limit")
        return cls(
            id=_int_or_default(row.get("id"), 1),
            auto_register_mode=_bool_or_default(row.get("auto_register_mode"), False),
            auto_register_stock=_int_or_default(row.get("auto_register_stock"), 2),
            usage_limit=_int_or_default(usage_limit_raw, 2),
            limit_period=str(row.get("limit_period") or "day"),
            version=_int_or_default(row.get("version"), 0),
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


@dataclass
class UnitStatusLogEntry:
    status: str
    status_label: str
    detail: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class UnitActiveTicketSummary:
    id: int
    category: str
    category_label: str
    status: str
    status_label: str
    created_at: Optional[str] = None


@dataclass
class UnitMonitorAlert:
    level: str
    level_label: str
    unit_name: str
    message: str
    unit_id: Optional[int] = None
    code: str = ""


@dataclass
class UnitMonitorItem:
    id: int
    name: str
    ip_address: Optional[str] = None
    connect: int = 0
    db_connect: int = 0
    reported_connect_flag: int = 0
    available: bool = True
    available_int: int = 1
    stock: Optional[int] = None
    initial_stock: Optional[int] = None
    dispensed_estimate: Optional[int] = None
    stock_status: str = "unknown"
    stock_status_label: str = "未取得"
    last_seen: Optional[str] = None
    seconds_ago: Optional[float] = None
    heartbeat_timeout_seconds: int = 60
    heartbeat_interval_seconds: Optional[int] = None
    heartbeat_fresh: bool = False
    heartbeat_overdue: bool = True
    connection_status: str = "unknown"
    connection_label: str = "状態不明"
    monitor_status: str = "UNKNOWN"
    monitor_status_label: str = "状態不明"
    can_dispense: bool = False
    needs_attention: bool = True
    attention_reasons: List[str] = field(default_factory=list)
    motor_type: Optional[str] = None
    control_method: Optional[str] = None
    use_sensor: Optional[bool] = None
    nfc_status: str = "unknown"
    motor_status: str = "unknown"
    sensor_status: str = "unknown"
    hardware_telemetry_status: str = "unacquired"
    hardware_telemetry_label: str = "追加telemetry未取得"
    mcu_status: str = "unacquired"
    mcu_status_label: str = "追加telemetry未取得"
    config_reported_at: Optional[str] = None
    config_stale: bool = True
    config_sync_status: str = "unknown"
    config_sync_label: str = "未取得"
    config_sync_error: Optional[str] = None
    active_ticket_count: int = 0
    active_tickets: List[UnitActiveTicketSummary] = field(default_factory=list)
    recent_status_logs: List[UnitStatusLogEntry] = field(default_factory=list)
    last_status_log_at: Optional[str] = None


@dataclass
class UnitMonitorSummary:
    total_units: int = 0
    online_count: int = 0
    offline_count: int = 0
    unknown_count: int = 0
    ready_count: int = 0
    attention_count: int = 0
    available_count: int = 0
    unavailable_count: int = 0
    out_of_stock_count: int = 0
    heartbeat_overdue_count: int = 0
    active_ticket_count: int = 0
    pending_unit_count: int = 0
    alert_count: int = 0
    heartbeat_timeout_seconds: int = 60
    default_heartbeat_interval_seconds: int = 30
    poll_interval_seconds: int = 10
    checked_at: str = ""


def _normalize_date_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value) if value else None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    return int(value)


def _int_or_default(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "on"}:
            return 1
        if lowered in {"false", "no", "n", "off"}:
            return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_or_default(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off", ""}:
            return False
    return default
