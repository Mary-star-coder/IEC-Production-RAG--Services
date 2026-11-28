import time
from collections.abc import Callable
from threading import Lock
from typing import TypeVar


T = TypeVar("T")


class RequestPacer:
    """Serialize calls and enforce a minimum interval between request starts."""

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute must be at least 1.")
        self._interval = 60.0 / requests_per_minute
        self._next_allowed_at = 0.0
        self._lock = Lock()

    def call(
        self,
        operation: Callable[[], T],
        *,
        retry_delay: Callable[[Exception], float | None] | None = None,
    ) -> T:
        with self._lock:
            wait_seconds = max(
                0.0,
                self._next_allowed_at - time.monotonic(),
            )
            if wait_seconds:
                time.sleep(wait_seconds)

            started_at = time.monotonic()
            self._next_allowed_at = max(
                self._next_allowed_at,
                started_at + self._interval,
            )
            try:
                return operation()
            except Exception as exc:
                if retry_delay is not None:
                    delay = retry_delay(exc)
                    if delay is not None and delay > 0:
                        self._next_allowed_at = max(
                            self._next_allowed_at,
                            time.monotonic() + delay,
                        )
                raise
