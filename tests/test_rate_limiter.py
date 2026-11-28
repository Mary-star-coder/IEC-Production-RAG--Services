from threading import Thread

import pytest

import app.rate_limiter as rate_limiter
from app.rate_limiter import RequestPacer


def test_request_pacer_spaces_calls_and_honors_retry_delay(monkeypatch):
    clock = {"now": 0.0}
    request_starts = []

    def sleep(seconds):
        clock["now"] += seconds

    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(rate_limiter.time, "sleep", sleep)
    pacer = RequestPacer(requests_per_minute=60)

    pacer.call(lambda: request_starts.append(clock["now"]))
    pacer.call(lambda: request_starts.append(clock["now"]))

    def rejected_request():
        request_starts.append(clock["now"])
        raise RuntimeError("upstream busy")

    with pytest.raises(RuntimeError, match="upstream busy"):
        pacer.call(rejected_request, retry_delay=lambda exc: 5.0)
    pacer.call(lambda: request_starts.append(clock["now"]))

    assert request_starts == [0.0, 1.0, 2.0, 7.0]


def test_request_pacer_serializes_concurrent_calls(monkeypatch):
    clock = {"now": 0.0}
    request_starts = []

    def sleep(seconds):
        clock["now"] += seconds

    monkeypatch.setattr(rate_limiter.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(rate_limiter.time, "sleep", sleep)
    pacer = RequestPacer(requests_per_minute=60)
    threads = [
        Thread(
            target=lambda: pacer.call(
                lambda: request_starts.append(clock["now"])
            )
        )
        for _ in range(2)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(request_starts) == [0.0, 1.0]


@pytest.mark.parametrize("requests_per_minute", [0, -1])
def test_request_pacer_rejects_nonpositive_limits(requests_per_minute):
    with pytest.raises(ValueError, match="at least 1"):
        RequestPacer(requests_per_minute)
