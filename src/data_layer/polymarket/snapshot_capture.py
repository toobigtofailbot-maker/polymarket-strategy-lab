"""Read-only snapshot capture for Polymarket market metadata.

Fetches public market data via the read-only adapter and returns normalized
snapshot records. Called only by the capture CLI or tests with mocked clients.

PROHIBITED — this module must never contain:
- POST, PUT, PATCH, DELETE network methods.
- Order placement, cancellation, signing, or submission.
- Credentials, API keys, private keys, wallet keys, or seed phrases.
- Authenticated request logic.
- Continuous loops or scheduled polling.
- Calls to CLOB /health (unverified per WP9-D001).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from .polling_policy import default_polling_policy
from .public_client import PolymarketPublicClient
from .rate_limit_guard import RateLimitGuard
from .snapshot_models import (
    ADAPTER_VERSION,
    MARKET_SOURCE,
    ORDER_BOOK_SOURCE,
    READ_ONLY_PROVENANCE,
    TOOL_NAME,
    WORK_PACKAGE,
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
    generate_snapshot_id,
    utc_iso_now,
)

DEFAULT_MARKETS_LIMIT = 3
DEFAULT_MAX_ORDER_BOOKS = 0

CaptureResult = Tuple[
    List[MarketMetadataSnapshotRecord],
    List[OrderBookSnapshotRecord],
    SnapshotManifest,
]


def capture_market_snapshots(
    allow_network: bool,
    markets_limit: int = DEFAULT_MARKETS_LIMIT,
    include_order_books: bool = False,
    max_order_books: int = DEFAULT_MAX_ORDER_BOOKS,
    snapshot_id: Optional[str] = None,
    _captured_at: Optional[datetime] = None,
    client: Optional[PolymarketPublicClient] = None,
    guard: Optional[RateLimitGuard] = None,
    now_provider: Optional[Callable[[], float]] = None,
) -> CaptureResult:
    """Capture read-only Polymarket market metadata snapshots.

    Returns (market_records, order_book_records, manifest).

    Raises RuntimeError if allow_network is False.
    Does not call CLOB /health (WP9-D001: returns 404, path unverified).
    Does not run continuously. Does not schedule repeated calls.
    Uses small limits by default (markets_limit=3, no order books).
    Uses WP16 local guard policy before public adapter calls.

    For order books: pass include_order_books=True and max_order_books=N.
    Order books require explicit opt-in because rate-limit policy is
    unconfirmed (WP8-D002 OPEN).
    """
    if not allow_network:
        raise RuntimeError(
            "Network access denied. "
            "Pass allow_network=True explicitly to allow GET-only network calls."
        )

    now = _captured_at or datetime.now(timezone.utc)
    snap_id = snapshot_id or generate_snapshot_id(now)
    captured_at = utc_iso_now(now)

    policy = default_polling_policy()
    gamma_policy = policy.endpoints["gamma_markets"]
    clob_policy = policy.endpoints["clob_book"]
    bounded_markets_limit = min(
        _non_negative(markets_limit),
        gamma_policy.max_markets_per_run,
    )
    bounded_max_order_books = min(
        _non_negative(max_order_books),
        clob_policy.max_tokens_per_run,
    )
    rate_guard = guard or RateLimitGuard(policy.endpoint_budgets())
    monotonic_now = now_provider or time.monotonic

    if client is None:
        client = PolymarketPublicClient()

    market_records: List[MarketMetadataSnapshotRecord] = []
    order_book_records: List[OrderBookSnapshotRecord] = []
    order_books_requested = 0
    guard_denials = 0
    guard_details: List[str] = []

    # Fetch markets via confirmed GET /markets endpoint.
    gamma_decision_time = float(monotonic_now())
    gamma_decision = rate_guard.record_allowed("gamma_markets", now=gamma_decision_time)
    if gamma_decision.allowed:
        result = client.get_markets(limit=bounded_markets_limit)
        raw_list = result.data if isinstance(result.data, list) else []
    else:
        guard_denials += 1
        guard_details.append(f"gamma_markets denied: {gamma_decision.reason}")
        raw_list = []

    for raw_market in raw_list:
        try:
            summary = PolymarketPublicClient.parse_market_summary(raw_market)
        except Exception:
            continue

        raw_field_names = (
            sorted(raw_market.keys()) if isinstance(raw_market, dict) else []
        )
        record = MarketMetadataSnapshotRecord(
            snapshot_id=snap_id,
            captured_at_utc=captured_at,
            source=MARKET_SOURCE,
            adapter_version=ADAPTER_VERSION,
            market_id=summary.market_id,
            condition_id=summary.condition_id,
            question=summary.question,
            market_status=summary.market_status,
            outcome_labels=list(summary.outcome_labels),
            token_ids=list(summary.token_ids),
            resolution_date=summary.resolution_date,
            category=summary.category,
            raw_field_names=raw_field_names,
        )
        market_records.append(record)

    # Optionally fetch order books via confirmed GET /book?token_id=...
    # Skips /health — WP9-D001: returns 404, path unknown.
    # WP8-D002 OPEN: rate-limit policy not confirmed; keep max_order_books small.
    if include_order_books and max_order_books > 0:
        token_ids_to_fetch: List[str] = []
        for mr in market_records:
            for tid in mr.token_ids:
                if tid and tid not in token_ids_to_fetch:
                    token_ids_to_fetch.append(tid)
                if len(token_ids_to_fetch) >= bounded_max_order_books:
                    break
            if len(token_ids_to_fetch) >= bounded_max_order_books:
                break

        order_books_requested = len(token_ids_to_fetch)
        for token_id in token_ids_to_fetch:
            clob_decision_time = float(monotonic_now())
            clob_decision = rate_guard.record_allowed("clob_book", now=clob_decision_time)
            if not clob_decision.allowed:
                guard_denials += 1
                guard_details.append(f"clob_book denied for token: {clob_decision.reason}")
                continue
            try:
                ob_result = client.get_order_book_snapshot(token_id)
                raw_ob = ob_result.data
                if not isinstance(raw_ob, dict):
                    continue
                bids = [
                    {"price": str(b["price"]), "size": str(b["size"])}
                    for b in raw_ob.get("bids", [])
                    if isinstance(b, dict)
                ]
                asks = [
                    {"price": str(a["price"]), "size": str(a["size"])}
                    for a in raw_ob.get("asks", [])
                    if isinstance(a, dict)
                ]
                ob_record = OrderBookSnapshotRecord(
                    snapshot_id=snap_id,
                    captured_at_utc=captured_at,
                    source=ORDER_BOOK_SOURCE,
                    adapter_version=ADAPTER_VERSION,
                    token_id=token_id,
                    bids=bids,
                    asks=asks,
                    raw_field_names=sorted(raw_ob.keys()),
                )
                order_book_records.append(ob_record)
            except Exception:
                continue

    manifest = SnapshotManifest(
        snapshot_id=snap_id,
        created_at_utc=captured_at,
        tool_name=TOOL_NAME,
        work_package=WORK_PACKAGE,
        markets_requested=markets_limit,
        markets_written=len(market_records),
        order_books_requested=order_books_requested,
        order_books_written=len(order_book_records),
        network_used=True,
        output_files=[],
        notes=(
            "Read-only research snapshot. No trading authority. "
            "Guard enforced: yes. Endpoint budgets used: local WP16 policy, "
            "not confirmed venue limits. "
            f"Guard denials: {guard_denials}. "
            f"Markets requested vs bounded: {markets_limit} vs {bounded_markets_limit}. "
            f"Order books requested vs bounded: {max_order_books} vs {bounded_max_order_books}. "
            "WP8-D002 remains OPEN. Not for automated or frequent scanning."
            + (f" Guard details: {'; '.join(guard_details)}." if guard_details else "")
        ),
    )

    return market_records, order_book_records, manifest


def _non_negative(value: int) -> int:
    return max(0, int(value))
