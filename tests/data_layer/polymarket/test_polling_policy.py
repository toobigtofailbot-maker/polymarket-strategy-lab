"""Offline tests for the WP16 polling policy model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from src.data_layer.polymarket.polling_policy import (
    NETWORK_ENDPOINT_KEYS,
    PollingPolicy,
    default_polling_policy,
    validate_polling_policy,
)


def _policy_with(policy_key: str, **changes: object) -> PollingPolicy:
    policy = default_polling_policy()
    endpoints = dict(policy.endpoints)
    endpoints[policy_key] = dataclasses.replace(endpoints[policy_key], **changes)
    return dataclasses.replace(policy, endpoints=endpoints)


def test_default_polling_policy_is_valid_and_disables_automated_loops():
    policy = default_polling_policy()
    result = validate_polling_policy(policy)

    assert result.passed is True
    assert policy.automated_polling_enabled is False
    assert all(not endpoint.allow_automated_loop for endpoint in policy.endpoints.values())


def test_future_network_endpoints_require_explicit_network_and_are_disabled():
    policy = default_polling_policy()

    assert set(policy.endpoints) == set(NETWORK_ENDPOINT_KEYS)
    for endpoint in policy.endpoints.values():
        assert endpoint.requires_explicit_network is True
        assert endpoint.enabled_by_default is False


def test_policy_validation_fails_if_automated_loop_is_enabled():
    policy = _policy_with("gamma_markets", allow_automated_loop=True)

    result = validate_polling_policy(policy)

    assert result.passed is False
    assert any(issue.code == "AUTOMATED_LOOP_ENABLED" for issue in result.issues)


def test_policy_validation_fails_if_network_endpoint_lacks_explicit_network():
    policy = _policy_with("clob_book", requires_explicit_network=False)

    result = validate_polling_policy(policy)

    assert result.passed is False
    assert any(
        issue.code == "NETWORK_ENDPOINT_WITHOUT_EXPLICIT_NETWORK"
        for issue in result.issues
    )


def test_policy_validation_fails_for_excessive_budget():
    policy = _policy_with("gamma_markets", max_requests_per_window=7)

    result = validate_polling_policy(policy)

    assert result.passed is False
    assert any(issue.code == "EXCESSIVE_LOCAL_BUDGET" for issue in result.issues)


def test_policy_validation_fails_for_missing_notes_and_unknown_endpoint():
    policy = _policy_with("gamma_markets", endpoint_key="unknown_endpoint", notes="")

    result = validate_polling_policy(policy)

    codes = {issue.code for issue in result.issues}
    assert result.passed is False
    assert "UNKNOWN_ENDPOINT_KEY" in codes
    assert "MISSING_NOTES" in codes


def test_policy_validation_fails_for_non_positive_and_negative_values():
    policy = _policy_with(
        "clob_price",
        max_requests_per_window=0,
        window_seconds=0,
        minimum_interval_seconds=-1.0,
    )

    result = validate_polling_policy(policy)

    codes = {issue.code for issue in result.issues}
    assert result.passed is False
    assert "NON_POSITIVE_MAX_REQUESTS" in codes
    assert "NON_POSITIVE_WINDOW" in codes
    assert "NEGATIVE_MINIMUM_INTERVAL" in codes


def test_policy_source_has_no_network_scheduler_or_delay_loop_terms():
    source = Path("src/data_layer/polymarket/polling_policy.py").read_text(encoding="utf-8")
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


def test_polling_docs_keep_wp8_d002_open_and_deny_runtime_authority():
    doc = Path("docs/polymarket_readonly_polling_policy.md").read_text(encoding="utf-8")
    required = [
        "WP16 does not add automated polling.",
        "WP16 does not call Polymarket APIs.",
        "WP16 does not create network requests.",
        "WP16 does not add a scheduler, daemon, background worker, or bot loop.",
        "WP16 does not create strategy signals or trade proposals.",
        "WP8-D002 remains OPEN",
    ]

    for text in required:
        assert text in doc


def test_gamma_markets_keyset_policy_is_present_and_conservative():
    policy = default_polling_policy()
    assert "gamma_markets_keyset" in NETWORK_ENDPOINT_KEYS
    keyset = policy.endpoints["gamma_markets_keyset"]
    assert keyset.enabled_by_default is False
    assert keyset.requires_explicit_network is True
    assert keyset.allow_automated_loop is False
    assert keyset.max_requests_per_window == 6
    assert keyset.window_seconds == 60
    assert keyset.minimum_interval_seconds == 10.0
    assert keyset.max_markets_per_run == 100
    assert keyset.max_tokens_per_run == 0
    assert keyset.notes.strip()
    validation = validate_polling_policy(policy)
    assert validation.passed


def test_existing_endpoint_budgets_are_unchanged_by_wp166():
    policy = default_polling_policy()
    gamma = policy.endpoints["gamma_markets"]
    assert gamma.max_requests_per_window == 6 and gamma.max_markets_per_run == 25
    clob = policy.endpoints["clob_book"]
    assert clob.max_requests_per_window == 10 and clob.max_tokens_per_run == 20
    assert clob.minimum_interval_seconds == 6.0


# ── S10-WALLET-01 hard bounds and bounded wallet feed endpoints ──────────────
def test_wallet_hard_bounds_are_frozen_constants():
    from src.data_layer.polymarket import polling_policy as p

    assert p.WALLET_MAX_PAGES_PER_FEED == 10
    assert p.WALLET_MAX_PAGE_SIZE == 100
    assert p.WALLET_MAX_SOURCE_ROWS_PER_FEED_RUN == 1000
    assert p.WALLET_MAX_SOURCE_ROWS_TOTAL_RUN == 3000
    assert p.WALLET_MAX_RESPONSE_BYTES_PER_PAGE == 4_194_304
    assert p.WALLET_MAX_CURSOR_CHARS == 4096


def test_wallet_feed_endpoints_present_disabled_and_conservative():
    from src.data_layer.polymarket import polling_policy as p

    policy = default_polling_policy()
    for key in p.WALLET_FEED_ENDPOINT_KEYS:
        assert key in NETWORK_ENDPOINT_KEYS
        endpoint = policy.endpoints[key]
        assert endpoint.enabled_by_default is False
        assert endpoint.requires_explicit_network is True
        assert endpoint.allow_automated_loop is False
        assert endpoint.max_requests_per_window == p.WALLET_MAX_PAGES_PER_FEED
        assert endpoint.notes.strip()
    assert validate_polling_policy(policy).passed
