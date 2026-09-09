"""Route-registration safety checks for the Flask application."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def find_duplicate_routes(flask_app) -> dict[tuple[str, str], list[str]]:
    """Return URL/method pairs registered by more than one endpoint.

    Flask accepts duplicate rules and dispatches to the first registered rule.
    That is unsafe here because an API request could silently select legacy
    logic rather than the intended service/repository implementation.
    """
    endpoints: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rule in flask_app.url_map.iter_rules():
        for method in _request_methods(rule.methods):
            endpoints[(rule.rule, method)].append(rule.endpoint)
    return {
        route: route_endpoints
        for route, route_endpoints in endpoints.items()
        if len(route_endpoints) > 1
    }


def assert_unique_routes(flask_app) -> None:
    """Raise an actionable error when URL dispatch would be ambiguous."""
    duplicates = find_duplicate_routes(flask_app)
    if not duplicates:
        return

    details = "; ".join(
        f"{path} [{method}]: {', '.join(endpoints)}"
        for (path, method), endpoints in sorted(duplicates.items())
    )
    raise RuntimeError(f"Duplicate Flask routes are not allowed: {details}")


def _request_methods(methods: Iterable[str]) -> set[str]:
    """Ignore Flask's automatic OPTIONS handler but include all dispatches."""
    return set(methods) - {"OPTIONS"}
