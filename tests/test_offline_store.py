"""Child-side standalone mode: local decisions, queue and sync (no hardware)."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

import pytest

from unit.offline import OfflineStore, OfflineSync

KEY = "test-card-key-32-characters-minimum"
UID = "0123456789abcdef"
NOW = datetime(2026, 10, 15, 12, 0, 0)


def ref_of(uid: str) -> str:
    return hmac.new(KEY.encode(), uid.lower().encode(), hashlib.sha256).hexdigest()


def make_cache(**overrides):
    cache = {
        "enabled": True,
        "issued_at": NOW.strftime("%Y-%m-%d %H:%M:%S"),
        "max_age_hours": 72,
        "per_card_limit": 1,
        "max_events": 10,
        "unit_stock": 5,
        "card_key": KEY,
        "cards": {ref_of(UID): 1},
    }
    cache.update(overrides)
    return cache


@pytest.fixture
def store(tmp_path):
    clock = {"now": NOW}
    s = OfflineStore(str(tmp_path / "offline"), now=lambda: clock["now"])
    s.clock = clock
    return s


def test_without_a_cache_nothing_is_dispensed(store):
    assert store.authorize(UID).reason == "NO_OFFLINE_CACHE"


def test_allowed_card_gets_exactly_its_allowance(store):
    store.save_cache(make_cache())

    decision = store.authorize(UID.upper())  # parent and child agree on case
    assert decision.allowed and decision.card_ref == ref_of(UID)
    store.record_dispense(decision.card_ref, success=True)

    assert store.authorize(UID).reason == "OFFLINE_LIMIT_REACHED"


def test_failed_dispense_does_not_use_up_the_allowance(store):
    store.save_cache(make_cache())
    store.record_dispense(ref_of(UID), success=False)

    assert store.authorize(UID).allowed
    assert store.pending()[0]["error_code"] == "DISPENSE_FAILED_CLIENT"


@pytest.mark.parametrize(
    ("cache", "reason"),
    [
        (make_cache(enabled=False), "OFFLINE_MODE_DISABLED_BY_PARENT"),
        (make_cache(cards={}), "CARD_NOT_ALLOWED_OFFLINE"),
        (make_cache(unit_stock=0), "UNIT_STOCK_EMPTY"),
        (make_cache(max_events=0), "OFFLINE_QUEUE_FULL"),
    ],
)
def test_refusals(store, cache, reason):
    store.save_cache(cache)
    assert store.authorize(UID).reason == reason


def test_old_cache_expires(store):
    store.save_cache(make_cache())
    store.clock["now"] = NOW + timedelta(hours=73)
    assert store.authorize(UID).reason == "OFFLINE_CACHE_EXPIRED"


def test_child_can_switch_the_mode_off(tmp_path):
    store = OfflineStore(str(tmp_path), enabled=False)
    store.save_cache(make_cache())
    assert store.authorize(UID).reason == "OFFLINE_MODE_DISABLED"


def test_queue_survives_a_torn_last_line_and_raw_uid_is_never_stored(store):
    store.save_cache(make_cache())
    entry = store.record_dispense(ref_of(UID), success=True)
    with open(store._queue_path, "a", encoding="utf-8") as handle:
        handle.write('{"kind": "offline_disp')  # power cut mid-write

    assert [e["event_id"] for e in store.pending()] == [entry["event_id"]]
    for name in ("queue.jsonl", "usage.json"):
        with open(f"{store.data_dir}/{name}", encoding="utf-8") as handle:
            assert UID not in handle.read().lower()


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


def test_sync_removes_settled_events_and_keeps_the_rest(store):
    store.save_cache(make_cache(cards={ref_of(UID): 2}, per_card_limit=2))
    first = store.record_dispense(ref_of(UID), success=True)
    result = store.enqueue_result("online-event-0001", True, None)
    sent = []

    def post(path, payload, timeout):
        sent.append(path)
        if path.endswith("offline-events"):
            return FakeResponse(200, {"results": [{"event_id": first["event_id"], "result": "recorded"}]})
        return FakeResponse(503)

    OfflineSync(store, post, log=lambda _m: None).flush()

    assert [e["event_id"] for e in store.pending()] == [result["event_id"]]
    assert sent == ["/api/v1/units/offline-events", "/api/dispense_result"]


def test_parent_error_keeps_the_queue(store):
    store.save_cache(make_cache())
    store.record_dispense(ref_of(UID), success=True)

    OfflineSync(store, lambda *_a: FakeResponse(500), log=lambda _m: None).flush()

    assert len(store.pending()) == 1


def test_cache_is_not_replaced_while_offline_dispenses_are_unsent(store):
    store.save_cache(make_cache())
    store.record_dispense(ref_of(UID), success=True)
    calls = []
    sync = OfflineSync(store, lambda *a: calls.append(a) or FakeResponse(200, {"cache": make_cache()}))

    assert sync.refresh_cache(force=True) is False
    assert calls == []
    assert store.authorize(UID).reason == "OFFLINE_LIMIT_REACHED"
