"""Health check and NFC reader API endpoints."""

from __future__ import annotations

import os

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({
        "status": "ok",
        "service": "oiteru-parent",
        "api_version": "1",
        "deployment_id": os.getenv("OITERU_DEPLOYMENT_ID", "local"),
    })
