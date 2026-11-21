"""Rate limiting and the deterministic result cache."""

import hashlib
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

from prawdowid.core.text import normalize_for_match
from prawdowid.schemas import CheckResult

SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 86_400


@dataclass
class RateLimiter:
    per_minute: int
    per_day: int
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def is_allowed(self, *keys: str) -> bool:
        now = time.monotonic()
        for key in keys:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > SECONDS_PER_DAY:
                hits.popleft()
            last_minute = sum(1 for hit in hits if now - hit <= SECONDS_PER_MINUTE)
            if last_minute >= self.per_minute or len(hits) >= self.per_day:
                return False
        for key in keys:
            self._hits[key].append(now)
        return True


def get_cache_key(input_type: str, content: str, corpus_version: str | None, model_id: str) -> str:
    material = "\x1f".join(
        [input_type, normalize_for_match(content), corpus_version or "", model_id]
    )
    return hashlib.sha256(material.encode()).hexdigest()


@dataclass
class ResultCache:
    """Same input + corpus + model → same result across channels (scenario G)."""

    max_items: int = 512
    _items: OrderedDict[str, CheckResult] = field(default_factory=OrderedDict)

    def get(self, key: str) -> CheckResult | None:
        result = self._items.get(key)
        if result is not None:
            self._items.move_to_end(key)
        return result

    def set(self, key: str, result: CheckResult) -> None:
        self._items[key] = result
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
