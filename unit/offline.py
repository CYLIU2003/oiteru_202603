"""Child standalone (offline) mode.

If the parent cannot be reached, the child may still dispense to cards the
parent allowed in its last *offline cache*, within the limits in that cache.
Every standalone dispense is written to a local queue first and sent to the
parent once it answers again (see ``OfflineSync``).

Files (default ``data/offline/``, mode 0600):

* ``cache.json``  - the parent's allowance list and limits
* ``usage.json``  - standalone dispenses per card since that cache was issued
* ``queue.jsonl`` - one JSON line per event still to be sent to the parent

Only card refs (HMAC of the UID) are stored, never the raw card UID.  This
module has no hardware or network code so it can be tested on any PC.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
OFFLINE_EVENTS_PATH = "/api/v1/units/offline-events"
OFFLINE_CACHE_PATH = "/api/v1/units/offline-cache"
DISPENSE_RESULT_PATH = "/api/dispense_result"


def normalize_card_uid(card_id: str) -> str:
    """Same normalization as the parent's ``app.auth.auth_manager``."""
    return re.sub(r"[\s:\-]", "", str(card_id)).lower()


@dataclass(frozen=True)
class OfflineDecision:
    allowed: bool
    reason: str
    card_ref: Optional[str] = None


class OfflineStore:
    """Local, crash-safe state for standalone mode.  Thread-safe."""

    def __init__(self, data_dir: str, enabled: bool = True, now: Callable[[], datetime] = datetime.now):
        self.data_dir = data_dir
        self.enabled = enabled
        self._now = now
        self._lock = threading.RLock()
        os.makedirs(data_dir, mode=0o700, exist_ok=True)
        self._cache_path = os.path.join(data_dir, "cache.json")
        self._usage_path = os.path.join(data_dir, "usage.json")
        self._queue_path = os.path.join(data_dir, "queue.jsonl")

    # -- files ---------------------------------------------------------------
    def _read_json(self, path: str, default):
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return default

    def _write_json(self, path: str, data) -> None:
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)

    def pending(self) -> list:
        """Queued entries, oldest first.  A torn last line (power loss) is skipped."""
        with self._lock:
            entries = []
            try:
                with open(self._queue_path, encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            entries.append(json.loads(line))
                        except ValueError:
                            continue
            except OSError:
                pass
            return entries

    def _append(self, entry: dict) -> None:
        with open(self._queue_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(self._queue_path, 0o600)

    def remove(self, event_ids) -> None:
        done = set(event_ids)
        if not done:
            return
        with self._lock:
            remaining = [e for e in self.pending() if e.get("event_id") not in done]
            temp_path = f"{self._queue_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                for entry in remaining:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self._queue_path)

    # -- cache ---------------------------------------------------------------
    def load_cache(self) -> dict:
        return self._read_json(self._cache_path, {})

    def save_cache(self, cache: dict) -> None:
        """Store a new cache from the parent.

        The parent has already counted every event it acknowledged, so the
        local usage counters start again from zero with the new cache.
        """
        with self._lock:
            self._write_json(self._cache_path, cache)
            self._write_json(self._usage_path, {})

    def has_unsent_dispenses(self) -> bool:
        return any(e.get("kind") == "offline_dispense" for e in self.pending())

    def set_unit_stock(self, stock) -> None:
        with self._lock:
            cache = self.load_cache()
            if cache and isinstance(stock, int):
                cache["unit_stock"] = stock
                self._write_json(self._cache_path, cache)

    def card_ref(self, card_id: str, cache: dict) -> Optional[str]:
        key = cache.get("card_key")
        if not key:
            return None
        return hmac.new(
            key.encode(), normalize_card_uid(card_id).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    # -- decisions -----------------------------------------------------------
    def authorize(self, card_id: str) -> OfflineDecision:
        """Decide whether this card may receive one item without the parent."""
        with self._lock:
            if not self.enabled:
                return OfflineDecision(False, "OFFLINE_MODE_DISABLED")
            cache = self.load_cache()
            if not cache:
                return OfflineDecision(False, "NO_OFFLINE_CACHE")
            if not cache.get("enabled"):
                return OfflineDecision(False, "OFFLINE_MODE_DISABLED_BY_PARENT")
            try:
                issued_at = datetime.strptime(cache["issued_at"], TIME_FORMAT)
                max_age = timedelta(hours=int(cache["max_age_hours"]))
            except (KeyError, TypeError, ValueError):
                return OfflineDecision(False, "NO_OFFLINE_CACHE")
            if self._now() - issued_at > max_age:
                return OfflineDecision(False, "OFFLINE_CACHE_EXPIRED")

            queued = [e for e in self.pending() if e.get("kind") == "offline_dispense"]
            if len(queued) >= int(cache.get("max_events", 0)):
                return OfflineDecision(False, "OFFLINE_QUEUE_FULL")
            unit_stock = cache.get("unit_stock")
            if isinstance(unit_stock, int) and unit_stock <= 0:
                return OfflineDecision(False, "UNIT_STOCK_EMPTY")

            ref = self.card_ref(card_id, cache)
            allowance = int(cache.get("cards", {}).get(ref, 0)) if ref else 0
            if allowance <= 0:
                return OfflineDecision(False, "CARD_NOT_ALLOWED_OFFLINE", ref)
            used = int(self._read_json(self._usage_path, {}).get(ref, 0))
            if used >= allowance:
                return OfflineDecision(False, "OFFLINE_LIMIT_REACHED", ref)
            return OfflineDecision(True, "OK", ref)

    def record_dispense(self, card_ref: str, success: bool, error_code: Optional[str] = None) -> dict:
        """Queue a standalone dispense.  Call this right after the motor ran."""
        entry = {
            "kind": "offline_dispense",
            "event_id": uuid.uuid4().hex,
            "card_ref": card_ref,
            "occurred_at": self._now().strftime(TIME_FORMAT),
            "success": bool(success),
            "error_code": None if success else (error_code or "DISPENSE_FAILED_CLIENT"),
        }
        with self._lock:
            self._append(entry)
            if success:
                usage = self._read_json(self._usage_path, {})
                usage[card_ref] = int(usage.get(card_ref, 0)) + 1
                self._write_json(self._usage_path, usage)
                cache = self.load_cache()
                if isinstance(cache.get("unit_stock"), int):
                    cache["unit_stock"] -= 1
                    self._write_json(self._cache_path, cache)
        return entry

    def enqueue_result(self, event_id: str, success: bool, error_code: Optional[str]) -> dict:
        """Keep an online dispense result that could not be delivered."""
        entry = {
            "kind": "dispense_result",
            "event_id": event_id,
            "success": bool(success),
            "error_code": error_code,
            "queued_at": self._now().strftime(TIME_FORMAT),
        }
        with self._lock:
            self._append(entry)
        return entry


class OfflineSync:
    """Send queued events to the parent and keep the offline cache fresh.

    ``post(path, payload, timeout)`` must add the unit credentials and return
    a ``requests``-style response; network errors propagate to the caller.
    """

    def __init__(self, store: OfflineStore, post, log=print, refresh_seconds: int = 600, now=datetime.now):
        self.store = store
        self.post = post
        self.log = log
        self.refresh_seconds = refresh_seconds
        self._now = now
        self._last_refresh: Optional[datetime] = None

    def flush(self) -> int:
        """Send everything queued.  Returns how many entries were settled."""
        entries = self.store.pending()
        if not entries:
            return 0
        settled = []

        dispenses = [e for e in entries if e.get("kind") == "offline_dispense"]
        for start in range(0, len(dispenses), 100):
            batch = dispenses[start:start + 100]
            response = self.post(
                OFFLINE_EVENTS_PATH,
                {"events": [{k: v for k, v in e.items() if k != "kind"} for e in batch]},
                10,
            )
            if response.status_code != 200:
                self.log(f"オフライン記録の送信に失敗 (HTTP {response.status_code})。あとで再送します")
                break
            for result in response.json().get("results", []):
                settled.append(result.get("event_id"))
                if result.get("result") == "rejected" or result.get("error_code"):
                    self.log(
                        f"オフライン記録 {str(result.get('event_id'))[:8]}:"
                        f" {result.get('result')} {result.get('reason') or result.get('error_code') or ''}"
                    )

        for entry in (e for e in entries if e.get("kind") == "dispense_result"):
            response = self.post(
                DISPENSE_RESULT_PATH,
                {
                    "event_id": entry["event_id"],
                    "success": entry["success"],
                    "error_code": entry.get("error_code"),
                },
                10,
            )
            # 200 = recorded/idempotent; 4xx = the parent has decided, retrying will not help.
            if response.status_code == 200 or 400 <= response.status_code < 500:
                settled.append(entry["event_id"])

        self.store.remove(settled)
        if settled:
            self.log(f"親機と同期しました: {len(settled)} 件")
        return len(settled)

    def refresh_cache(self, force: bool = False) -> bool:
        """Fetch a new cache, but only after every offline dispense was accepted."""
        if self.store.has_unsent_dispenses():
            return False
        due = (
            force
            or self._last_refresh is None
            or (self._now() - self._last_refresh).total_seconds() >= self.refresh_seconds
        )
        if not due:
            return False
        response = self.post(OFFLINE_CACHE_PATH, {}, 10)
        if response.status_code != 200:
            return False
        cache = response.json().get("cache")
        if not isinstance(cache, dict):
            return False
        self.store.save_cache(cache)
        self._last_refresh = self._now()
        return True

    def after_heartbeat(self, unit_stock=None) -> None:
        """Run after every successful heartbeat: send the queue, then refresh."""
        if isinstance(unit_stock, int):
            self.store.set_unit_stock(unit_stock)
        self.flush()
        self.refresh_cache()
