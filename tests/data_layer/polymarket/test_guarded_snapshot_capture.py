"""WP18 tests for guarded manual snapshot capture.

All tests are offline and use fake clients, guards, and clocks.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

from src.data_layer.polymarket.rate_limit_guard import RateLimitDecision
from src.data_layer.polymarket.snapshot_capture import capture_market_snapshots

ROOT = Path(__file__).resolve().parents[3]
CAPTURE_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "snapshot_capture.py"
CAPTURE_TOOL = ROOT / "tools" / "polymarket" / "capture_market_snapshots.py"

FORBIDDEN_SOURCE_TERMS = {
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
    "generate_signal",
    "create_trade_proposal",
    "backtest",
    "fill_order",
    "simulate_fill",
    "apscheduler",
    "celery",
    "while True",
    "time.sleep",
    "requests",
    "httpx",
    "aiohttp",
    "websockets",
}


class TrackingGuard:
    def __init__(self, sequence: list[str], *, deny: set[str] | None = None) -> None:
        self.sequence = sequence
        self.deny = deny or set()
        self.calls: list[tuple[str, float | None]] = []

    def record_allowed(self, endpoint_key: str, *, now=None) -> RateLimitDecision:
        self.sequence.append(f"guard:{endpoint_key}")
        self.calls.append((endpoint_key, now))
        allowed = endpoint_key not in self.deny
        return RateLimitDecision(
            allowed=allowed,
            endpoint_key=endpoint_key,
            reason="allowed" if allowed else "test_denied",
            retry_after_seconds=0.0 if allowed else 10.0,
            requests_in_window=0,
            next_allowed_at=float(now or 0.0),
        )


def _market_result(token_ids: str = '["tok1","tok2","tok3"]') -> MagicMock:
    result = MagicMock()
    result.data = [
        {
            "id": "540817",
            "conditionId": "0xabc123",
            "question": "Will X happen?",
            "active": "True",
            "clobTokenIds": token_ids,
            "outcomes": '["Yes","No"]',
            "endDate": "2026-12-31",
            "category": "politics",
        }
    ]
    return result


def _order_book_result() -> MagicMock:
    result = MagicMock()
    result.data = {
        "bids": [{"price": "0.55", "size": "100"}],
        "asks": [{"price": "0.58", "size": "50"}],
        "asset_id": "tok1",
    }
    return result


class SequencedClient:
    def __init__(self, sequence: list[str]) -> None:
        self.sequence = sequence
        self.market_limits: list[int | None] = []
        self.order_book_tokens: list[str] = []

    def get_markets(self, limit=None):
        self.sequence.append("client:gamma_markets")
        self.market_limits.append(limit)
        return _market_result()

    def get_order_book_snapshot(self, token_id: str):
        self.sequence.append(f"client:clob_book:{token_id}")
        self.order_book_tokens.append(token_id)
        return _order_book_result()


def test_allow_network_false_causes_zero_client_calls():
    client = MagicMock()
    try:
        capture_market_snapshots(allow_network=False, client=client)
    except RuntimeError:
        pass
    client.get_markets.assert_not_called()
    client.get_order_book_snapshot.assert_not_called()


def test_gamma_capture_consults_guard_before_client_call():
    sequence: list[str] = []
    guard = TrackingGuard(sequence)
    client = SequencedClient(sequence)

    capture_market_snapshots(
        allow_network=True,
        client=client,
        guard=guard,  # type: ignore[arg-type]
        now_provider=lambda: 100.0,
    )

    assert sequence[:2] == ["guard:gamma_markets", "client:gamma_markets"]
    assert guard.calls == [("gamma_markets", 100.0)]


def test_gamma_guard_denial_prevents_client_call():
    sequence: list[str] = []
    guard = TrackingGuard(sequence, deny={"gamma_markets"})
    client = SequencedClient(sequence)

    market_records, order_book_records, manifest = capture_market_snapshots(
        allow_network=True,
        client=client,
        guard=guard,  # type: ignore[arg-type]
        now_provider=lambda: 101.0,
    )

    assert market_records == []
    assert order_book_records == []
    assert client.market_limits == []
    assert "Guard denials: 1" in manifest.notes
    assert "gamma_markets denied" in manifest.notes


def test_order_book_capture_consults_guard_once_per_token_before_client_calls():
    sequence: list[str] = []
    guard = TrackingGuard(sequence)
    client = SequencedClient(sequence)

    capture_market_snapshots(
        allow_network=True,
        include_order_books=True,
        max_order_books=2,
        client=client,
        guard=guard,  # type: ignore[arg-type]
        now_provider=lambda: 102.0,
    )

    assert guard.calls == [
        ("gamma_markets", 102.0),
        ("clob_book", 102.0),
        ("clob_book", 102.0),
    ]
    assert sequence == [
        "guard:gamma_markets",
        "client:gamma_markets",
        "guard:clob_book",
        "client:clob_book:tok1",
        "guard:clob_book",
        "client:clob_book:tok2",
    ]


def test_markets_limit_is_bounded_by_wp16_policy():
    sequence: list[str] = []
    client = SequencedClient(sequence)

    _, _, manifest = capture_market_snapshots(
        allow_network=True,
        markets_limit=999,
        client=client,
        guard=TrackingGuard(sequence),  # type: ignore[arg-type]
    )

    assert client.market_limits == [25]
    assert "Markets requested vs bounded: 999 vs 25" in manifest.notes


def test_max_order_books_is_bounded_by_wp16_policy():
    sequence: list[str] = []
    client = SequencedClient(sequence)

    _, ob_records, manifest = capture_market_snapshots(
        allow_network=True,
        include_order_books=True,
        max_order_books=999,
        client=client,
        guard=TrackingGuard(sequence),  # type: ignore[arg-type]
    )

    assert len(ob_records) == 3
    assert client.order_book_tokens == ["tok1", "tok2", "tok3"]
    assert "Order books requested vs bounded: 999 vs 20" in manifest.notes


def test_cli_default_remains_offline_and_exits_zero():
    result = subprocess.run(
        [sys.executable, str(CAPTURE_TOOL)],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0
    assert "No network calls made" in result.stdout
    assert "Guard enforced: WP16 local policy" in result.stdout


def test_capture_sources_do_not_contain_forbidden_runtime_terms():
    combined_source = (
        CAPTURE_MODULE.read_text(encoding="utf-8")
        + "\n"
        + CAPTURE_TOOL.read_text(encoding="utf-8")
    )
    found = {term for term in FORBIDDEN_SOURCE_TERMS if term in combined_source}
    assert found == set()
