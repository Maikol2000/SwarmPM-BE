from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Deque


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = monotonic()
        with self._lock:
            queue = self._hits[key]
            threshold = now - window_seconds
            while queue and queue[0] < threshold:
                queue.popleft()

            if len(queue) >= max_requests:
                return False

            queue.append(now)
            return True


rate_limiter = InMemoryRateLimiter()
