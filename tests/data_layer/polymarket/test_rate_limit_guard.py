"""Offline tests for the WP16 local rate-limit guard."""

from __future__ import annotations

from pathlib import Path

from src.data_layer.polymarket.rate_limit_guard import (
    EndpointBudget,
    RateLimitGuard,
    RateLimitWindow,
)


def _guard() -> RateLimitGuard:
    return RateLimitGuard(
        [
            EndpointBudget(
                endpoint_key="gamma_markets",
                window=RateLimitWindow(max_requests=2, window_seconds=10.0),
                minimum_interval_seconds=3.0,
            ),
            EndpointBudget(
                endpoint_key="clob_book",
                window=RateLimitWindow(max_requests=1, window_seconds=5.0),
                minimum_interval_seconds=1.0,
            ),
        ]
    )


def test_first_request_is_allowed_and_recorded():
    guard = _guard()

    decision = guard.record_allowed("gamma_markets", now=100.0)

    assert decision.allowed is True
    assert decision.reason == "first_request_allowed"
    assert decision.retry_after_seconds == 0.0


def test_second_request_inside_minimum_interval_is_rejected_with_retry_after():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)

    decision = guard.record_allowed("gamma_markets", now=101.0)

    assert decision.allowed is False
    assert decision.reason == "minimum_interval_not_elapsed"
    assert decision.retry_after_seconds == 2.0
    assert decision.next_allowed_at == 103.0


def test_max_requests_per_window_are_enforced():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)
    guard.record_allowed("gamma_markets", now=103.0)

    decision = guard.record_allowed("gamma_markets", now=106.0)

    assert decision.allowed is False
    assert decision.reason == "window_exhausted"
    assert decision.retry_after_seconds == 4.0
    assert decision.requests_in_window == 2


def test_requests_are_allowed_again_after_window_expires():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)
    guard.record_allowed("gamma_markets", now=103.0)

    decision = guard.record_allowed("gamma_markets", now=110.1)

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_endpoint_states_are_independent():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)

    decision = guard.record_allowed("clob_book", now=100.0)

    assert decision.allowed is True
    assert decision.endpoint_key == "clob_book"


def test_reset_clears_specific_endpoint_state():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)
    guard.record_allowed("clob_book", now=100.0)

    guard.reset("gamma_markets")

    assert guard.record_allowed("gamma_markets", now=101.0).allowed is True
    assert guard.record_allowed("clob_book", now=101.0).allowed is False


def test_reset_clears_all_state():
    guard = _guard()
    guard.record_allowed("gamma_markets", now=100.0)
    guard.record_allowed("clob_book", now=100.0)

    guard.reset()

    assert guard.record_allowed("gamma_markets", now=101.0).allowed is True
    assert guard.record_allowed("clob_book", now=101.0).allowed is True


def test_rate_limit_guard_source_has_no_network_scheduler_or_delay_loop_terms():
    source = Path("src/data_layer/polymarket/rate_limit_guard.py").read_text(encoding="utf-8")
    forbidden = [
        "urllib.request",
        "import requests",
        "from requests",
        "httpx",
        "aiohttp",
        "websockets",
        "apscheduler",
        "celery",
        "schedule",
        "while True",
        "time.sleep",
        "PolymarketPublicClient",
        "py_clob_client_v2",
    ]

    for term in forbidden:
        assert term not in source
