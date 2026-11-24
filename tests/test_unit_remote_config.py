"""Regression tests for applying a settings update on a child."""

import pytest

from unit import unit_client


@pytest.mark.parametrize("saved", [False, True])
def test_remote_settings_are_only_applied_after_successful_save(monkeypatch, saved):
    current = dict(
        unit_client.DEFAULT_CONFIG,
        HEARTBEAT_INTERVAL=30,
        UNIT_PASSWORD="device-secret",
        _unit_api_token="session-token",
    )
    original = current.copy()
    persisted = []

    def save_candidate(candidate):
        assert current == original
        persisted.append(candidate.copy())
        return saved

    monkeypatch.setattr(unit_client, "save_config", save_candidate)
    assert unit_client.apply_remote_config({"HEARTBEAT_INTERVAL": 35}, current) is saved
    assert len(persisted) == 1
    assert persisted[0]["HEARTBEAT_INTERVAL"] == 35
    assert current["HEARTBEAT_INTERVAL"] == (35 if saved else 30)
    assert current["UNIT_PASSWORD"] == original["UNIT_PASSWORD"]
    assert current["_unit_api_token"] == original["_unit_api_token"]
    if not saved:
        assert current == original
