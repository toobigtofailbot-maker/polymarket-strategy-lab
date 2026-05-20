from __future__ import annotations

import datetime
import pathlib

import pytest

from src.data_layer.polymarket.errors import PolymarketHTTPError, PolymarketReadOnlyError
from src.data_layer.polymarket.models import AdapterResult, ReadOnlyRequestInfo
from src.data_layer.polymarket.rate_limit_guard import (
    EndpointBudget,
    RateLimitGuard,
    RateLimitWindow,
)
from src.data_layer.polymarket.readonly_polling_runner import (
    ReadonlyPollingRunConfig,
    build_readonly_polling_plan,
    run_readonly_polling,
)


class FakeClient:
    def __init__(self, *, markets_error=None, book_error=None):
        self.markets_calls = []
        self.book_calls = []
        self.markets_error = markets_error
        self.book_error = book_error

    def get_markets(self, limit=None):
        self.markets_calls.append(limit)
        if self.markets_error:
            raise self.markets_error
        data = [{"id": str(index)} for index in range(limit or 0)]
        return AdapterResult(
            data=data,
            request_info=ReadOnlyRequestInfo(
                method="GET",
                url="https://gamma-api.polymarket.com/markets",
                status_code=200,
                latency_ms=1.0,
            ),
        )

    def get_order_book_snapshot(self, token_id):
        self.book_calls.append(token_id)
        if self.book_error:
            raise self.book_error
        return AdapterResult(
            data={"asset_id": token_id, "bids": [], "asks": []},
            request_info=ReadOnlyRequestInfo(
                method="GET",
                url="https://clob.polymarket.com/book",
                status_code=200,
                latency_ms=1.0,
            ),
        )


class IncrementingClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        self.value += 100.0
        return self.value


def fixed_utc():
    return datetime.datetime(2026, 5, 20, 12, 0, 0, tzinfo=datetime.UTC)


def test_default_run_builds_plan_and_makes_zero_client_calls():
    client = FakeClient()
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(),
        client=client,
        utcnow_provider=fixed_utc,
    )

    assert summary.dry_run is True
    assert summary.stopped_reason == "dry_run_no_network"
    assert len(summary.planned_request_list) == 1
    assert summary.guard_decisions == []
    assert client.markets_calls == []
    assert client.book_calls == []


def test_allow_network_calls_fake_client_within_finite_bounds():
    client = FakeClient()
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=2),
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert client.markets_calls == [2]
    assert summary.attempted_request_count == 1
    assert summary.successful_request_count == 1
    assert summary.outcomes[0].public_item_count == 2


def test_rate_limit_guard_is_consulted_before_each_fake_request():
    client = FakeClient()
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(
            allow_network=True,
            markets_limit=1,
            order_books_limit=2,
            token_ids=("token-a", "token-b"),
        ),
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert [log.request.endpoint_key for log in summary.guard_decisions] == [
        "gamma_markets",
        "clob_book",
        "clob_book",
    ]
    assert client.markets_calls == [1]
    assert client.book_calls == ["token-a", "token-b"]


def test_denied_guard_decision_prevents_fake_client_call():
    budgets = {
        "gamma_markets": EndpointBudget(
            endpoint_key="gamma_markets",
            window=RateLimitWindow(max_requests=1, window_seconds=60.0),
            minimum_interval_seconds=999.0,
        )
    }
    guard = RateLimitGuard(budgets)
    client = FakeClient()
    first = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=1),
        client=client,
        guard=guard,
        now_provider=lambda: 1.0,
        utcnow_provider=fixed_utc,
    )
    second = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=1),
        client=client,
        guard=guard,
        now_provider=lambda: 2.0,
        utcnow_provider=fixed_utc,
    )

    assert first.outcomes[0].success is True
    assert second.guard_decisions[0].decision.allowed is False
    assert second.outcomes[0].outcome == "guard_denied"
    assert client.markets_calls == [1]


def test_max_markets_per_run_is_enforced_by_policy_bound():
    plan = build_readonly_polling_plan(
        ReadonlyPollingRunConfig(allow_network=False, markets_limit=999)
    )

    assert plan[0].limit == 25


def test_order_books_limit_default_is_zero():
    plan = build_readonly_polling_plan(
        ReadonlyPollingRunConfig(markets_limit=0, token_ids=("a", "b"))
    )

    assert plan == []


def test_order_books_are_token_bounded_and_guard_enforced():
    config = ReadonlyPollingRunConfig(
        allow_network=True,
        markets_limit=0,
        order_books_limit=999,
        token_ids=tuple(f"token-{index}" for index in range(25)),
    )
    client = FakeClient()
    summary = run_readonly_polling(
        config,
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert len(summary.planned_request_list) == 20
    assert len(summary.guard_decisions) == 20
    assert len(client.book_calls) == 20


def test_429_failure_is_recorded_without_retry():
    client = FakeClient(
        markets_error=PolymarketHTTPError(
            429, "https://gamma-api.polymarket.com/markets", "limited"
        )
    )
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=2),
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert client.markets_calls == [2]
    assert summary.outcomes[0].outcome == "http_429"
    assert summary.stopped_reason == "http_429"
    assert summary.attempted_request_count == 1


def test_5xx_failure_is_recorded_without_retry():
    client = FakeClient(
        markets_error=PolymarketHTTPError(
            503, "https://gamma-api.polymarket.com/markets", "down"
        )
    )
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=2),
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert summary.outcomes[0].outcome == "http_5xx"
    assert summary.stopped_reason == "http_5xx"
    assert summary.attempted_request_count == 1


def test_network_like_failure_is_recorded_without_retry():
    client = FakeClient(markets_error=PolymarketReadOnlyError("connection refused"))
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(allow_network=True, markets_limit=2),
        client=client,
        now_provider=IncrementingClock(),
        utcnow_provider=fixed_utc,
    )

    assert summary.outcomes[0].outcome == "network_error"
    assert summary.stopped_reason == "network_error"
    assert summary.attempted_request_count == 1


def test_summary_dict_is_sanitized_and_small():
    summary = run_readonly_polling(
        ReadonlyPollingRunConfig(),
        client=FakeClient(),
        utcnow_provider=fixed_utc,
    )
    data = summary.to_dict()

    assert "planned_request_list" in data
    assert "outcomes" in data
    assert "PRIVATE_KEY" not in repr(data)
    assert len(repr(data)) < 10000


def test_runner_source_contains_no_forbidden_terms():
    source = pathlib.Path(
        "src/data_layer/polymarket/readonly_polling_runner.py"
    ).read_text(encoding="utf-8")
    forbidden_terms = [
        "py_clob_client_v2",
        "PRIVATE_KEY",
        "CLOB_API_KEY",
        "CLOB_SECRET",
        "CLOB_PASS_PHRASE",
        "mnemonic",
        "create_and_post_order",
        "create_order",
        "post_order",
        "submit_order",
        "cancel_order",
        "sign_order",
        "execute_trade",
        "buy",
        "sell",
        "generate_signal",
        "create_trade_proposal",
        "backtest",
        "fill_order",
        "simulate_fill",
        "apscheduler",
        "celery",
        "schedule",
        "while True",
        "time.sleep",
        "requests",
        "httpx",
        "aiohttp",
        "websockets",
    ]
    lowered = source.lower()
    offenders = [term for term in forbidden_terms if term.lower() in lowered]

    assert offenders == []


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        ReadonlyPollingRunConfig(markets_limit=-1)
