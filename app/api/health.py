"""Health check and NFC reader API endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "server": "oiteru"})
