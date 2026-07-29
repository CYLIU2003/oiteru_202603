"""Tests for unambiguous Flask routing."""

import pytest
from flask import Flask

from app.routing import assert_unique_routes, find_duplicate_routes


def test_find_duplicate_routes_identifies_matching_url_and_method():
    app = Flask(__name__)
    app.add_url_rule("/api/example", endpoint="first", view_func=lambda: "first")
    app.add_url_rule("/api/example", endpoint="second", view_func=lambda: "second")

    assert find_duplicate_routes(app) == {
        ("/api/example", "GET"): ["first", "second"],
        ("/api/example", "HEAD"): ["first", "second"],
    }
    with pytest.raises(RuntimeError, match="/api/example"):
        assert_unique_routes(app)


def test_unique_routes_allow_distinct_methods():
    app = Flask(__name__)
    app.add_url_rule("/api/example", endpoint="read", view_func=lambda: "read")
    app.add_url_rule(
        "/api/example", endpoint="write", view_func=lambda: "write", methods=["POST"]
    )

    assert find_duplicate_routes(app) == {}
    assert_unique_routes(app)
