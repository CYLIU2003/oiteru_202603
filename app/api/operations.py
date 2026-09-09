"""Admin-facing inventory and maintenance operation endpoints."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.models.enums import StockMovementType
from app.services import operations_service
from db_adapter import get_connection

operations_bp = Blueprint("operations", __name__)


@operations_bp.route("/admin/operations")
def admin_operations():
    """Render the privacy-safe daily operations work queue."""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    selected_unit_id = request.args.get("unit_id", type=int)
    with get_connection() as conn:
        dashboard = operations_service.get_operations_dashboard(conn)
        operators = operations_service.list_active_operators(conn)
    active_operator_ids = {operator["id"] for operator in operators}
    return render_template(
        "admin_operations.html",
        selected_unit_id=selected_unit_id,
        operators=operators,
        active_operator_ids=active_operator_ids,
        **dashboard,
    )


@operations_bp.route("/admin/operations/stock-movements", methods=["POST"])
def admin_create_stock_movement():
    """Handle the inventory form without bypassing the operations service."""
    admin_user_id = _current_admin_user_id()
    if admin_user_id is None:
        return redirect(url_for("admin_login"))

    unit_id = request.form.get("unit_id")
    movement_type = request.form.get("movement_type", "")
    try:
        quantity_delta = _movement_delta_from_form(
            movement_type,
            request.form.get("quantity"),
        )
        with get_connection() as conn:
            operations_service.record_stock_movement(
                conn,
                unit_id=unit_id,
                movement_type=movement_type,
                quantity_delta=quantity_delta,
                reason=request.form.get("reason", ""),
                admin_user_id=admin_user_id,
            )
    except operations_service.OperationsError as exc:
        flash(str(exc), "error")
    else:
        flash("在庫操作を記録しました。", "success")
    return redirect(_operations_redirect(unit_id))


@operations_bp.route("/admin/operations/tickets", methods=["POST"])
def admin_create_maintenance_ticket():
    """Handle a maintenance report from an authenticated operator."""
    admin_user_id = _current_admin_user_id()
    if admin_user_id is None:
        return redirect(url_for("admin_login"))

    unit_id = request.form.get("unit_id")
    try:
        with get_connection() as conn:
            operations_service.create_maintenance_ticket(
                conn,
                unit_id=unit_id,
                category=request.form.get("category", ""),
                description=request.form.get("description", ""),
                admin_user_id=admin_user_id,
                assigned_to_admin_user_id=request.form.get(
                    "assigned_to_admin_user_id"
                ),
            )
    except operations_service.OperationsError as exc:
        flash(str(exc), "error")
    else:
        flash("故障チケットを登録しました。", "success")
    return redirect(_operations_redirect(unit_id))


@operations_bp.route("/admin/operations/tickets/<int:ticket_id>", methods=["POST"])
def admin_update_maintenance_ticket(ticket_id: int):
    """Update an existing ticket through the same state machine as the API."""
    admin_user_id = _current_admin_user_id()
    if admin_user_id is None:
        return redirect(url_for("admin_login"))

    unit_id = request.form.get("unit_id")
    try:
        with get_connection() as conn:
            operations_service.update_maintenance_ticket(
                conn,
                ticket_id=ticket_id,
                status=request.form.get("status", ""),
                resolution_note=request.form.get("resolution_note"),
                assigned_to_admin_user_id=request.form.get(
                    "assigned_to_admin_user_id"
                ),
                admin_user_id=admin_user_id,
            )
    except operations_service.OperationsError as exc:
        flash(str(exc), "error")
    else:
        flash("故障チケットを更新しました。", "success")
    return redirect(_operations_redirect(unit_id))


@operations_bp.route("/api/v1/admin/operations/summary", methods=["GET"])
def api_operations_summary():
    """Return the current work queue without exposing unit credentials."""
    auth_error, _ = _require_api_admin()
    if auth_error:
        return auth_error
    with get_connection() as conn:
        dashboard = operations_service.get_operations_dashboard(conn)
    return jsonify(
        {
            "success": True,
            "summary": {
                "out_of_stock_count": len(dashboard["out_of_stock_units"]),
                "heartbeat_overdue_count": len(dashboard["heartbeat_overdue_units"]),
                "active_ticket_count": len(dashboard["active_tickets"]),
                "heartbeat_timeout_seconds": dashboard["heartbeat_timeout_seconds"],
            },
            "out_of_stock_units": [
                _serialize_unit(unit) for unit in dashboard["out_of_stock_units"]
            ],
            "heartbeat_overdue_units": [
                _serialize_unit(unit) for unit in dashboard["heartbeat_overdue_units"]
            ],
            "active_tickets": [
                asdict(ticket) for ticket in dashboard["active_tickets"]
            ],
            "recent_stock_movements": [
                asdict(movement) for movement in dashboard["recent_stock_movements"]
            ],
        }
    )


@operations_bp.route(
    "/api/v1/admin/operations/units/<int:unit_id>/stock-movements",
    methods=["POST"],
)
def api_create_stock_movement(unit_id: int):
    """Create a durable restock, correction, or disposal record."""
    auth_error, admin_user_id = _require_api_admin()
    if auth_error:
        return auth_error
    payload = _json_object_or_error()
    if isinstance(payload, tuple):
        return payload
    try:
        with get_connection() as conn:
            movement = operations_service.record_stock_movement(
                conn,
                unit_id=unit_id,
                movement_type=payload.get("movement_type", ""),
                quantity_delta=payload.get("quantity_delta"),
                reason=payload.get("reason", ""),
                admin_user_id=admin_user_id,
            )
    except operations_service.OperationsError as exc:
        return _operations_error_response(exc)
    return jsonify({"success": True, "movement": asdict(movement)}), 201


@operations_bp.route("/api/v1/admin/operations/maintenance-tickets", methods=["POST"])
def api_create_maintenance_ticket():
    """Open a maintenance ticket for a registered unit."""
    auth_error, admin_user_id = _require_api_admin()
    if auth_error:
        return auth_error
    payload = _json_object_or_error()
    if isinstance(payload, tuple):
        return payload
    try:
        with get_connection() as conn:
            kwargs: dict[str, Any] = {
                "unit_id": payload.get("unit_id"),
                "category": payload.get("category", ""),
                "description": payload.get("description", ""),
                "admin_user_id": admin_user_id,
            }
            if "assigned_to_admin_user_id" in payload:
                kwargs["assigned_to_admin_user_id"] = payload[
                    "assigned_to_admin_user_id"
                ]
            ticket = operations_service.create_maintenance_ticket(conn, **kwargs)
    except operations_service.OperationsError as exc:
        return _operations_error_response(exc)
    return jsonify({"success": True, "ticket": asdict(ticket)}), 201


@operations_bp.route(
    "/api/v1/admin/operations/maintenance-tickets/<int:ticket_id>",
    methods=["PATCH"],
)
def api_update_maintenance_ticket(ticket_id: int):
    """Advance, resolve, close, reopen, or assign a maintenance ticket."""
    auth_error, admin_user_id = _require_api_admin()
    if auth_error:
        return auth_error
    payload = _json_object_or_error()
    if isinstance(payload, tuple):
        return payload
    try:
        with get_connection() as conn:
            kwargs: dict[str, Any] = {
                "ticket_id": ticket_id,
                "status": payload.get("status", ""),
                "admin_user_id": admin_user_id,
            }
            if "resolution_note" in payload:
                kwargs["resolution_note"] = payload["resolution_note"]
            if "assigned_to_admin_user_id" in payload:
                kwargs["assigned_to_admin_user_id"] = payload[
                    "assigned_to_admin_user_id"
                ]
            ticket = operations_service.update_maintenance_ticket(conn, **kwargs)
    except operations_service.OperationsError as exc:
        return _operations_error_response(exc)
    return jsonify({"success": True, "ticket": asdict(ticket)})


def _require_api_admin() -> tuple[Any | None, int | None]:
    if not session.get("admin_logged_in"):
        return (jsonify({"success": False, "error": "Unauthorized"}), 401), None
    admin_user_id = _current_admin_user_id()
    if admin_user_id is None:
        return (
            (
                jsonify(
                    {
                        "success": False,
                        "error": "Authenticated administrator identity is required",
                        "code": "ADMIN_IDENTITY_REQUIRED",
                    }
                ),
                403,
            ),
            None,
        )
    return None, admin_user_id


def _current_admin_user_id() -> int | None:
    value = session.get("admin_user_id")
    if isinstance(value, bool):
        return None
    try:
        admin_user_id = int(value)
    except (TypeError, ValueError):
        return None
    return admin_user_id if admin_user_id > 0 else None


def _json_object_or_error() -> dict[str, Any] | tuple[Any, int]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "A JSON object is required"}), 400
    return payload


def _movement_delta_from_form(movement_type: str, quantity: object) -> int:
    if isinstance(quantity, bool):
        raise operations_service.OperationsValidationError("quantity must be an integer")
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise operations_service.OperationsValidationError(
            "quantity must be an integer"
        ) from exc
    normalized_type = str(movement_type or "").strip().lower()
    if normalized_type == StockMovementType.RESTOCK:
        if value <= 0:
            raise operations_service.OperationsValidationError(
                "quantity must be positive for restock"
            )
        return value
    if normalized_type == StockMovementType.DISPOSAL:
        if value <= 0:
            raise operations_service.OperationsValidationError(
                "quantity must be positive for disposal"
            )
        return -value
    return value


def _operations_redirect(unit_id: object):
    try:
        parsed_unit_id = int(unit_id)
    except (TypeError, ValueError):
        return url_for("operations.admin_operations")
    return url_for("operations.admin_operations", unit_id=parsed_unit_id)


def _operations_error_response(exc: operations_service.OperationsError):
    if isinstance(exc, operations_service.OperationsNotFoundError):
        status_code = 404
    elif isinstance(exc, operations_service.OperationsConflictError):
        status_code = 409
    else:
        status_code = 400
    return (
        jsonify(
            {
                "success": False,
                "error": str(exc),
                "code": exc.error_code,
            }
        ),
        status_code,
    )


def _serialize_unit(unit) -> dict[str, Any]:
    """Expose operational state, never the device credential."""
    return {
        "id": unit.id,
        "name": unit.name,
        "stock": unit.stock,
        "initial_stock": unit.initial_stock,
        "available": bool(unit.available),
        "connected": bool(unit.connect),
        "last_seen": unit.last_seen,
    }
