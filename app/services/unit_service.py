"""Unit (child-device) management and monitoring service."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
import os
from typing import Any, Dict, List, Optional

from app import state
from app.logger import get_logger
from app.models.schemas import (
    UnitActiveTicketSummary,
    UnitMonitorAlert,
    UnitMonitorItem,
    UnitMonitorSummary,
    UnitRecord,
    UnitStatusLogEntry,
    _bool_or_default,
)
from app.repositories.history_repository import HistoryRepository
from app.repositories.operations_repository import OperationsRepository
from app.repositories.unit_repository import UnitRepository
from app.services import settings_service

logger = get_logger(__name__)

_unit_repo = UnitRepository()
_operations_repo = OperationsRepository()
_history_repo = HistoryRepository()

DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 60
DEFAULT_POLL_INTERVAL_SECONDS = 10
FUTURE_SKEW_TOLERANCE_SECONDS = 5.0

MONITOR_STATUS_LABELS: Dict[str, str] = {
    "READY": "稼働中（オンライン）",
    "ATTENTION": "要確認（オンライン）",
    "OUT_OF_STOCK": "在庫切れ",
    "OFFLINE": "オフライン",
    "UNKNOWN": "状態不明",
    "DISABLED": "利用停止中",
}

CONNECTION_STATUS_LABELS: Dict[str, str] = {
    "online": "オンライン",
    "offline": "オフライン",
    "unknown": "状態不明",
}

CONFIG_SYNC_LABELS: Dict[str, str] = {
    "applied": "反映済み",
    "pending": "反映待ち（予約中）",
    "delivered": "送信済み（ACK待ち）",
    "failed": "適用失敗",
    "reported": "取得済み",
    "unknown": "未取得",
}

ALERT_LEVEL_LABELS: Dict[str, str] = {
    "critical": "重大",
    "serious": "要対応",
    "warning": "注意",
}

ALERT_LEVEL_ORDER: Dict[str, int] = {
    "critical": 0,
    "serious": 1,
    "warning": 2,
}

STATUS_LOG_LABELS: Dict[str, str] = {
    "online": "オンライン復帰",
    "offline": "オフライン検知",
    "approved": "子機承認・登録",
    "config_update_pending": "設定変更を予約",
    "config_applied": "設定変更を適用完了",
    "config_failed": "設定変更の適用失敗",
    "maintenance_ticket_opened": "故障チケット登録",
    "maintenance_ticket_in_progress": "故障チケット対応中",
    "maintenance_ticket_resolved": "故障チケット復旧確認",
    "maintenance_ticket_closed": "故障チケット完了",
}

TICKET_CATEGORY_LABELS: Dict[str, str] = {
    "empty": "在庫切れ",
    "jam": "詰まり",
    "hardware": "機器故障",
    "network": "通信不良",
    "other": "その他",
}

TICKET_STATUS_LABELS: Dict[str, str] = {
    "open": "受付",
    "in_progress": "対応中",
    "resolved": "復旧確認",
    "closed": "完了",
}


def heartbeat_update(
    conn,
    unit_name: str,
    ip_address: str,
    config: Optional[Dict[str, Any]] = None,
    config_ack: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Process a unit heartbeat. Returns (unit_record or None, response_dict)."""
    unit = _unit_repo.find_by_name(conn, unit_name)

    if unit:
        if config:
            state.upsert_unit_config_snapshot(conn, unit_name, config, ip_address)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _unit_repo.update_heartbeat(conn, unit_name, now, ip_address)
        if not unit.connect:
            state.record_device_status(conn, unit_name, "online")

        if config_ack:
            applied = _bool_or_default(config_ack.get("applied"), False)
            acknowledged = state.acknowledge_config_update(
                conn,
                unit_name,
                str(config_ack.get("config_update_id") or ""),
                int(config_ack.get("config_version") or 0),
                applied,
                str(config_ack.get("error") or ""),
            )
            if acknowledged:
                state.record_device_status(
                    conn,
                    unit_name,
                    "config_applied" if applied else "config_failed",
                )

        response = {
            "success": True,
            "stock": unit.stock,
            "available": unit.available,
            "auto_register_mode": settings_service.server_settings["auto_register_mode"],
            "auto_register_stock": settings_service.server_settings["auto_register_stock"],
            "usage_limit": settings_service.server_settings["usage_limit"],
            "limit_period": settings_service.server_settings["limit_period"],
            "settings_version": settings_service.settings_version,
        }

        pending_config = state.get_config_update_for_delivery(conn, unit_name)
        if pending_config:
            response["config_update"] = pending_config

        return unit, response

    return None, {"error": "Unit not registered", "pending": True}


def parse_local_timestamp(value: Any) -> Optional[datetime]:
    """Parse a DB datetime or ISO string without inventing missing timestamps."""
    parsed = state.as_datetime(value)
    if parsed is not None:
        return parsed
    if isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip())
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            return None
    return None


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return None


def evaluate_unit_heartbeat(
    last_seen: Any,
    connect: Any,
    reference_time: datetime,
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Classify heartbeat state aligned with operations_service.

    - Valid timestamp within ``timeout_seconds`` and connect == 1 -> ``online``
    - Valid timestamp older than ``timeout_seconds`` (even if connect == 0 or 1) -> ``offline``
    - Missing, unparseable, future-skewed (>= 5s), or recent timestamp with connect != 1 -> ``unknown``
    """
    connect_flag = 1 if _bool_or_default(connect, False) else 0

    seen_at = parse_local_timestamp(last_seen)
    normalized_last_seen = (
        seen_at.strftime("%Y-%m-%d %H:%M:%S") if seen_at is not None else None
    )
    if seen_at is None:
        has_raw_value = last_seen is not None and str(last_seen).strip() != ""
        reason = (
            "最終 heartbeat 時刻の形式が不正なため状態不明です"
            if has_raw_value
            else "heartbeat 未受信（last_seen 未記録）のため状態不明です"
        )
        return {
            "last_seen": None,
            "seconds_ago": None,
            "heartbeat_fresh": False,
            "heartbeat_overdue": True,
            "connection_status": "unknown",
            "connection_label": CONNECTION_STATUS_LABELS["unknown"],
            "reported_connect_flag": connect_flag,
            "status_reason": reason,
        }

    raw_age = (reference_time - seen_at).total_seconds()
    if raw_age < -FUTURE_SKEW_TOLERANCE_SECONDS:
        return {
            "last_seen": normalized_last_seen,
            "seconds_ago": None,
            "heartbeat_fresh": False,
            "heartbeat_overdue": False,
            "connection_status": "unknown",
            "connection_label": CONNECTION_STATUS_LABELS["unknown"],
            "reported_connect_flag": connect_flag,
            "status_reason": "最終 heartbeat 時刻が親機時刻より 5 秒以上未来のため状態不明です",
        }

    age = max(0.0, raw_age)
    seconds_ago = round(age, 1)
    is_overdue = raw_age > timeout_seconds

    if is_overdue:
        connection_status = "offline"
        heartbeat_fresh = False
        status_reason = (
            f"最終 heartbeat から {int(seconds_ago)} 秒経過しています（閾値: {timeout_seconds} 秒）"
        )
    elif connect_flag == 1:
        connection_status = "online"
        heartbeat_fresh = True
        status_reason = None
    else:
        # Recent timestamp within timeout_seconds, but connect flag is 0 -> inconsistent
        connection_status = "unknown"
        heartbeat_fresh = False
        status_reason = (
            "直近の最終通信時刻がありますが connect フラグが 0（不整合）のため状態不明です"
        )

    return {
        "last_seen": normalized_last_seen,
        "seconds_ago": seconds_ago,
        "heartbeat_fresh": heartbeat_fresh,
        "heartbeat_overdue": is_overdue,
        "connection_status": connection_status,
        "connection_label": CONNECTION_STATUS_LABELS[connection_status],
        "reported_connect_flag": connect_flag,
        "status_reason": status_reason,
    }


def build_unit_monitor_item(
    unit: UnitRecord,
    *,
    reference_time: datetime,
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    config_snapshot: Optional[Dict[str, Any]] = None,
    latest_config_update: Optional[Dict[str, Any]] = None,
    active_tickets: Optional[List[Any]] = None,
    active_ticket_count: Optional[int] = None,
    status_logs: Optional[List[Dict[str, Any]]] = None,
) -> UnitMonitorItem:
    """Build a single child-unit monitoring view without exposing credentials."""
    reported_cfg = (
        config_snapshot.get("config")
        if isinstance(config_snapshot, dict) and isinstance(config_snapshot.get("config"), dict)
        else {}
    )
    config_reported_at = (
        state.format_db_time(config_snapshot.get("last_updated"))
        if isinstance(config_snapshot, dict)
        else None
    )

    hb_interval: Optional[int] = None
    if "HEARTBEAT_INTERVAL" in reported_cfg and not isinstance(
        reported_cfg["HEARTBEAT_INTERVAL"], bool
    ):
        try:
            parsed_interval = int(reported_cfg["HEARTBEAT_INTERVAL"])
            if 5 <= parsed_interval <= 300:
                hb_interval = parsed_interval
        except (TypeError, ValueError):
            hb_interval = None

    effective_timeout_seconds = (
        max(timeout_seconds, hb_interval * 2)
        if hb_interval is not None
        else timeout_seconds
    )

    hb = evaluate_unit_heartbeat(
        unit.last_seen,
        unit.connect,
        reference_time,
        timeout_seconds=effective_timeout_seconds,
    )

    available_bool = _bool_or_default(unit.available, False)
    available_int = 1 if available_bool else 0

    stock_val: Optional[int] = (
        int(unit.stock)
        if isinstance(unit.stock, int) and not isinstance(unit.stock, bool) and unit.stock >= 0
        else None
    )
    initial_stock_val: Optional[int] = (
        int(unit.initial_stock)
        if isinstance(unit.initial_stock, int)
        and not isinstance(unit.initial_stock, bool)
        and unit.initial_stock >= 0
        else None
    )
    dispensed_estimate: Optional[int] = (
        initial_stock_val - stock_val
        if (
            stock_val is not None
            and initial_stock_val is not None
            and initial_stock_val >= stock_val
        )
        else None
    )

    if stock_val is None:
        stock_status = "unknown"
        stock_status_label = "未取得"
    elif stock_val <= 0:
        stock_status = "empty"
        stock_status_label = "在庫切れ (0)"
    elif (
        initial_stock_val is not None
        and initial_stock_val > 0
        and stock_val < initial_stock_val
        and stock_val * 5 <= initial_stock_val
    ):
        stock_status = "low"
        stock_status_label = "残りわずか"
    else:
        stock_status = "ok"
        stock_status_label = "在庫あり"

    config_stale = True
    if config_reported_at:
        cfg_dt = parse_local_timestamp(config_reported_at)
        if cfg_dt is not None:
            cfg_age = (reference_time - cfg_dt).total_seconds()
            config_stale = not (
                -FUTURE_SKEW_TOLERANCE_SECONDS <= cfg_age <= effective_timeout_seconds
            )

    motor_type = str(reported_cfg["MOTOR_TYPE"]) if reported_cfg.get("MOTOR_TYPE") else None
    control_method = (
        str(reported_cfg["CONTROL_METHOD"]) if reported_cfg.get("CONTROL_METHOD") else None
    )
    use_sensor = (
        _optional_bool(reported_cfg["USE_SENSOR"])
        if "USE_SENSOR" in reported_cfg and reported_cfg["USE_SENSOR"] is not None
        else None
    )

    if control_method == "RASPI_DIRECT":
        hardware_telemetry_status = "unacquired"
        hardware_telemetry_label = "追加telemetry未取得（ラズパイ直結・外部MCUなし）"
        mcu_status = "not_applicable"
        mcu_status_label = "対象外（ラズパイ直結）"
    else:
        hardware_telemetry_status = "unacquired"
        hardware_telemetry_label = "追加telemetry未取得"
        mcu_status = "unacquired"
        mcu_status_label = "追加telemetry未取得"

    config_sync_status = "unknown"
    config_sync_error: Optional[str] = None
    if isinstance(latest_config_update, dict) and latest_config_update.get("status"):
        raw_sync = str(latest_config_update["status"]).lower()
        if raw_sync in CONFIG_SYNC_LABELS:
            config_sync_status = raw_sync
        if latest_config_update.get("error"):
            config_sync_error = str(latest_config_update["error"])
    elif config_reported_at:
        config_sync_status = "reported"
    config_sync_label = CONFIG_SYNC_LABELS.get(config_sync_status, "未取得")

    ip_address = (
        str(unit.ip_address).strip()
        if unit.ip_address and str(unit.ip_address).strip()
        else (
            str(config_snapshot.get("ip_address")).strip()
            if isinstance(config_snapshot, dict)
            and config_snapshot.get("ip_address")
            and str(config_snapshot.get("ip_address")).strip()
            else None
        )
    )

    ticket_summaries: List[UnitActiveTicketSummary] = []
    for ticket in active_tickets or []:
        category = str(getattr(ticket, "category", "") or "")
        t_status = str(getattr(ticket, "status", "") or "")
        ticket_summaries.append(
            UnitActiveTicketSummary(
                id=int(getattr(ticket, "id", 0)),
                category=category,
                category_label=TICKET_CATEGORY_LABELS.get(category, category or "不明"),
                status=t_status,
                status_label=TICKET_STATUS_LABELS.get(t_status, t_status or "不明"),
                created_at=getattr(ticket, "created_at", None),
            )
        )

    effective_ticket_count = (
        max(int(active_ticket_count), len(ticket_summaries))
        if active_ticket_count is not None
        else len(ticket_summaries)
    )

    log_summaries: List[UnitStatusLogEntry] = []
    for entry in status_logs or []:
        raw_status = str(entry.get("status") or "unknown")
        log_summaries.append(
            UnitStatusLogEntry(
                status=raw_status,
                status_label=STATUS_LOG_LABELS.get(raw_status, raw_status),
                detail=entry.get("detail"),
                created_at=entry.get("created_at"),
            )
        )
    last_status_log_at = log_summaries[0].created_at if log_summaries else None

    attention_reasons: List[str] = []
    if not available_bool:
        attention_reasons.append("管理画面で「使用不可（無効）」に設定されています")
    if hb["connection_status"] in {"unknown", "offline"} and hb.get("status_reason"):
        attention_reasons.append(str(hb["status_reason"]))
    if stock_val is None:
        attention_reasons.append("在庫数が未取得または不明です")
    elif stock_val <= 0:
        attention_reasons.append("在庫が 0 個です（補充必須）")
    elif stock_status == "low":
        attention_reasons.append(f"在庫が残りわずかです（残り {stock_val} 個）")
    if effective_ticket_count > 0:
        attention_reasons.append(
            f"対応中・復旧確認の故障チケットが {effective_ticket_count} 件あります"
        )
    if config_sync_status == "failed":
        err_suffix = f" ({config_sync_error})" if config_sync_error else ""
        attention_reasons.append(f"子機設定の適用失敗が報告されています{err_suffix}")
    elif config_sync_status in {"pending", "delivered"}:
        attention_reasons.append("子機設定の変更反映待ちです（次回 heartbeat で同期）")

    connection_status = hb["connection_status"]
    capabilities = reported_cfg.get("_capabilities")
    if config_stale or connection_status != "online" or not isinstance(capabilities, dict):
        capabilities = {}
    nfc_status, motor_status, sensor_status = (
        status if status in ("ready", "unavailable") else "unknown"
        for status in (capabilities.get(name) for name in ("nfc", "motor", "sensor"))
    )
    if nfc_status == "unavailable":
        attention_reasons.append("子機から NFC 利用不可が報告されています")
    if motor_status == "unavailable":
        attention_reasons.append("子機からモーター利用不可が報告されています")
    can_dispense = bool(
        available_bool
        and connection_status == "online"
        and stock_val is not None
        and stock_val > 0
        and nfc_status != "unavailable"
        and motor_status != "unavailable"
    )
    needs_attention = bool(attention_reasons)

    if not available_bool:
        monitor_status = "DISABLED"
    elif connection_status == "unknown":
        monitor_status = "UNKNOWN"
    elif connection_status == "offline":
        monitor_status = "OFFLINE"
    elif stock_val is not None and stock_val <= 0:
        monitor_status = "OUT_OF_STOCK"
    elif needs_attention:
        monitor_status = "ATTENTION"
    else:
        monitor_status = "READY"

    return UnitMonitorItem(
        id=unit.id,
        name=unit.name,
        ip_address=ip_address,
        connect=1 if connection_status == "online" else 0,
        db_connect=hb["reported_connect_flag"],
        reported_connect_flag=hb["reported_connect_flag"],
        available=available_bool,
        available_int=available_int,
        stock=stock_val,
        initial_stock=initial_stock_val,
        dispensed_estimate=dispensed_estimate,
        stock_status=stock_status,
        stock_status_label=stock_status_label,
        last_seen=hb["last_seen"],
        seconds_ago=hb["seconds_ago"],
        heartbeat_timeout_seconds=effective_timeout_seconds,
        heartbeat_interval_seconds=hb_interval,
        heartbeat_fresh=hb["heartbeat_fresh"],
        heartbeat_overdue=hb["heartbeat_overdue"],
        connection_status=connection_status,
        connection_label=hb["connection_label"],
        monitor_status=monitor_status,
        monitor_status_label=MONITOR_STATUS_LABELS[monitor_status],
        can_dispense=can_dispense,
        needs_attention=needs_attention,
        attention_reasons=attention_reasons,
        motor_type=motor_type,
        control_method=control_method,
        use_sensor=use_sensor,
        nfc_status=nfc_status,
        motor_status=motor_status,
        sensor_status=sensor_status,
        hardware_telemetry_status=hardware_telemetry_status,
        hardware_telemetry_label=hardware_telemetry_label,
        mcu_status=mcu_status,
        mcu_status_label=mcu_status_label,
        config_reported_at=config_reported_at,
        config_stale=config_stale,
        config_sync_status=config_sync_status,
        config_sync_label=config_sync_label,
        config_sync_error=config_sync_error,
        active_ticket_count=effective_ticket_count,
        active_tickets=ticket_summaries,
        recent_status_logs=log_summaries,
        last_status_log_at=last_status_log_at,
    )


def build_unit_monitor_alerts(
    items: List[UnitMonitorItem],
    pending_units: List[Dict[str, Any]],
) -> List[UnitMonitorAlert]:
    """Build severity-ordered alerts inspired by computer-cluster-control."""
    alerts: List[UnitMonitorAlert] = []

    for item in items:
        if item.connection_status == "offline":
            elapsed = (
                f"{int(item.seconds_ago)} 秒"
                if item.seconds_ago is not None
                else f"{item.heartbeat_timeout_seconds} 秒以上"
            )
            level = "critical" if item.available else "warning"
            alerts.append(
                UnitMonitorAlert(
                    level=level,
                    level_label=ALERT_LEVEL_LABELS[level],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="HEARTBEAT_OFFLINE",
                    message=f"オフライン: 最終 heartbeat から {elapsed} 経過（閾値: {item.heartbeat_timeout_seconds} 秒）",
                )
            )
        elif item.connection_status == "unknown":
            level = "serious" if item.available else "warning"
            alerts.append(
                UnitMonitorAlert(
                    level=level,
                    level_label=ALERT_LEVEL_LABELS[level],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="HEARTBEAT_UNKNOWN",
                    message="状態不明: heartbeat 未受信、または時刻・connect フラグが不整合です",
                )
            )

        if item.stock is None:
            alerts.append(
                UnitMonitorAlert(
                    level="serious",
                    level_label=ALERT_LEVEL_LABELS["serious"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="STOCK_UNKNOWN",
                    message="在庫数が未取得または不明です",
                )
            )
        elif item.stock <= 0:
            level = "critical" if item.available else "warning"
            alerts.append(
                UnitMonitorAlert(
                    level=level,
                    level_label=ALERT_LEVEL_LABELS[level],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="OUT_OF_STOCK",
                    message="在庫切れ（0 個）: 補充が必要です",
                )
            )
        elif item.stock_status == "low":
            alerts.append(
                UnitMonitorAlert(
                    level="warning",
                    level_label=ALERT_LEVEL_LABELS["warning"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="LOW_STOCK",
                    message=f"在庫残りわずか（残り {item.stock} 個）",
                )
            )

        if item.active_ticket_count > 0:
            categories = "・".join(t.category_label for t in item.active_tickets[:3])
            cat_suffix = f"（{categories}）" if categories else ""
            alerts.append(
                UnitMonitorAlert(
                    level="serious",
                    level_label=ALERT_LEVEL_LABELS["serious"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="ACTIVE_TICKET",
                    message=f"対応中・復旧確認の故障チケットが {item.active_ticket_count} 件あります{cat_suffix}",
                )
            )

        if item.config_sync_status == "failed":
            err_detail = f": {item.config_sync_error}" if item.config_sync_error else ""
            alerts.append(
                UnitMonitorAlert(
                    level="serious",
                    level_label=ALERT_LEVEL_LABELS["serious"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="CONFIG_SYNC_FAILED",
                    message=f"子機設定の適用失敗が報告されています{err_detail}",
                )
            )
        elif item.config_sync_status in {"pending", "delivered"}:
            alerts.append(
                UnitMonitorAlert(
                    level="warning",
                    level_label=ALERT_LEVEL_LABELS["warning"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="CONFIG_SYNC_PENDING",
                    message=f"子機設定が{item.config_sync_label}です（次回 heartbeat で同期）",
                )
            )

        if not item.available:
            alerts.append(
                UnitMonitorAlert(
                    level="warning",
                    level_label=ALERT_LEVEL_LABELS["warning"],
                    unit_id=item.id,
                    unit_name=item.name,
                    code="UNIT_DISABLED",
                    message="利用停止中（管理画面で「無効」に設定されています）",
                )
            )

    for pending in pending_units:
        p_name = str(pending.get("unit_name") or "未登録子機")
        if pending.get("credential_conflict"):
            alerts.append(
                UnitMonitorAlert(
                    level="critical",
                    level_label=ALERT_LEVEL_LABELS["critical"],
                    unit_id=None,
                    unit_name=p_name,
                    code="PENDING_CREDENTIAL_CONFLICT",
                    message="未承認子機で認証情報の競合が検知されました。なりすましや設定ミスを確認してください",
                )
            )
        elif not pending.get("expired"):
            alerts.append(
                UnitMonitorAlert(
                    level="warning",
                    level_label=ALERT_LEVEL_LABELS["warning"],
                    unit_id=None,
                    unit_name=p_name,
                    code="PENDING_UNIT_APPROVAL",
                    message="未登録の子機から接続要求（承認待ち）が届いています",
                )
            )

    alerts.sort(
        key=lambda a: (ALERT_LEVEL_ORDER.get(a.level, 99), a.unit_name, a.code)
    )
    return alerts


def _sanitize_pending_units(
    pending_rows: List[Dict[str, Any]],
    reference_time: datetime,
) -> List[Dict[str, Any]]:
    try:
        ttl_seconds = int(os.getenv("PENDING_UNIT_TTL_SECONDS", "86400"))
    except ValueError:
        ttl_seconds = 86400
    sanitized: List[Dict[str, Any]] = []
    for item in pending_rows or []:
        first_seen_dt = parse_local_timestamp(item.get("first_seen"))
        last_seen_dt = parse_local_timestamp(item.get("last_seen"))
        expired = (
            True
            if first_seen_dt is None
            else (first_seen_dt + timedelta(seconds=max(60, ttl_seconds)) < reference_time)
        )
        seconds_ago: Optional[float] = None
        if last_seen_dt is not None:
            raw_age = (reference_time - last_seen_dt).total_seconds()
            if raw_age >= -FUTURE_SKEW_TOLERANCE_SECONDS:
                seconds_ago = round(max(0.0, raw_age), 1)
        sanitized.append(
            {
                "unit_name": str(item.get("unit_name") or ""),
                "name": str(item.get("unit_name") or ""),
                "ip_address": (
                    str(item.get("ip_address")).strip()
                    if item.get("ip_address") and str(item.get("ip_address")).strip()
                    else None
                ),
                "first_seen": state.format_db_time(item.get("first_seen")),
                "last_seen": state.format_db_time(item.get("last_seen")),
                "seconds_ago": seconds_ago,
                "heartbeat_count": int(item.get("heartbeat_count") or 0),
                "credential_conflict": _bool_or_default(
                    item.get("credential_conflict"), False
                ),
                "credential_conflict_at": state.format_db_time(
                    item.get("credential_conflict_at")
                ),
                "expired": expired,
            }
        )
    return sanitized


def get_unit_logs(
    conn,
    unit_name: str,
    *,
    limit: int = 100,
) -> List[Dict[str, str]]:
    """Fetch and merge durable child-unit logs from device_status_logs and history."""
    bounded_limit = max(1, int(limit))
    status_entries = state.list_recent_device_status_logs(
        conn, unit_name=unit_name, per_unit_limit=bounded_limit
    ).get(unit_name, [])
    history_records = _history_repo.find_by_unit_name(
        conn, unit_name, limit=bounded_limit
    )

    prefix = f"[{unit_name}] "
    merged: List[tuple[str, int, Dict[str, str]]] = []
    seq = 0

    for entry in reversed(status_entries):
        raw_status = str(entry.get("status") or "")
        label = STATUS_LOG_LABELS.get(raw_status, raw_status)
        detail = entry.get("detail")
        msg = f"[状態] {label}" + (f" ({detail})" if detail else "")
        time_str = str(entry.get("created_at") or "")
        merged.append((time_str, seq, {"time": time_str, "message": msg}))
        seq += 1

    for record in reversed(history_records):
        txt = record.txt
        if txt.startswith(prefix):
            txt = txt[len(prefix):]
        time_str = str(record.created_at or "")
        merged.append((time_str, seq, {"time": time_str, "message": txt}))
        seq += 1

    merged.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in merged[-bounded_limit:]]


def get_unit_monitor_dashboard(
    conn,
    *,
    heartbeat_timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return a privacy-safe, credential-free monitoring snapshot for all child units."""
    if heartbeat_timeout_seconds <= 0:
        raise ValueError("heartbeat_timeout_seconds must be positive")
    reference_time = now or datetime.now()
    checked_at = reference_time.strftime("%Y-%m-%d %H:%M:%S")

    units = _operations_repo.list_units(conn)
    unit_names = [unit.name for unit in units]
    active_tickets = _operations_repo.list_active_tickets(conn)

    tickets_by_unit_id: Dict[int, List[Any]] = {}
    for ticket in active_tickets:
        tickets_by_unit_id.setdefault(ticket.unit_id, []).append(ticket)

    if hasattr(_operations_repo, "count_active_tickets_by_unit"):
        ticket_counts_by_unit_id = _operations_repo.count_active_tickets_by_unit(conn)
    else:
        ticket_counts_by_unit_id = {
            uid: len(t_list) for uid, t_list in tickets_by_unit_id.items()
        }

    config_snapshots = state.list_unit_config_snapshots(conn, unit_names=unit_names)
    latest_updates = state.list_latest_config_updates(conn, unit_names=unit_names)
    status_logs_by_unit = state.list_recent_device_status_logs(
        conn, per_unit_limit=5, unit_names=unit_names
    )
    pending_raw = state.get_pending_units(conn)
    pending_units = _sanitize_pending_units(pending_raw, reference_time)

    items: List[UnitMonitorItem] = []
    for unit in units:
        unit_tickets = tickets_by_unit_id.get(unit.id, [])
        exact_ticket_count = ticket_counts_by_unit_id.get(unit.id, len(unit_tickets))
        items.append(
            build_unit_monitor_item(
                unit,
                reference_time=reference_time,
                timeout_seconds=heartbeat_timeout_seconds,
                config_snapshot=config_snapshots.get(unit.name),
                latest_config_update=latest_updates.get(unit.name),
                active_tickets=unit_tickets,
                active_ticket_count=exact_ticket_count,
                status_logs=status_logs_by_unit.get(unit.name, []),
            )
        )

    alerts = build_unit_monitor_alerts(items, pending_units)

    online_count = sum(1 for item in items if item.connection_status == "online")
    offline_count = sum(1 for item in items if item.connection_status == "offline")
    unknown_count = sum(1 for item in items if item.connection_status == "unknown")
    ready_count = sum(1 for item in items if item.can_dispense)
    available_count = sum(1 for item in items if item.available)
    unavailable_count = len(items) - available_count
    out_of_stock_count = sum(
        1 for item in items if item.stock is not None and item.stock <= 0
    )
    heartbeat_overdue_count = sum(1 for item in items if item.heartbeat_overdue)
    attention_count = sum(1 for item in items if item.needs_attention)
    total_active_ticket_count = sum(item.active_ticket_count for item in items)

    summary = UnitMonitorSummary(
        total_units=len(items),
        online_count=online_count,
        offline_count=offline_count,
        unknown_count=unknown_count,
        ready_count=ready_count,
        attention_count=attention_count,
        available_count=available_count,
        unavailable_count=unavailable_count,
        out_of_stock_count=out_of_stock_count,
        heartbeat_overdue_count=heartbeat_overdue_count,
        active_ticket_count=total_active_ticket_count,
        pending_unit_count=len(pending_units),
        alert_count=len(alerts),
        heartbeat_timeout_seconds=heartbeat_timeout_seconds,
        default_heartbeat_interval_seconds=DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
        checked_at=checked_at,
    )

    return {
        "summary": asdict(summary),
        "alerts": [asdict(alert) for alert in alerts],
        "units": [asdict(item) for item in items],
        "pending_units": pending_units,
    }
