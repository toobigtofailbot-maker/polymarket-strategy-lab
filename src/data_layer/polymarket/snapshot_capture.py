"""Read-only snapshot capture for Polymarket market metadata.

Fetches public market data via the read-only adapter and returns normalized
snapshot records. Called only by the capture CLI or tests with mocked clients.

PROHIBITED — this module must never contain:
- POST, PUT, PATCH, DELETE requests.
- Order placement, cancellation, signing, or submission.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Continuous loops or scheduled polling.
- Calls to CLOB /health (unverified per WP9-D001).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .public_client import PolymarketPublicClient
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
) -> CaptureResult:
    """Capture read-only Polymarket market metadata snapshots.

    Returns (market_records, order_book_records, manifest).

    Raises RuntimeError if allow_network is False.
    Does not call CLOB /health (WP9-D001: returns 404, path unverified).
    Does not run continuously. Does not schedule repeated requests.
    Uses small limits by default (markets_limit=3, no order books).

    For order books: pass include_order_books=True and max_order_books=N.
    Order books require explicit opt-in because rate-limit policy is
    unconfirmed (WP8-D002 OPEN).
    """
    if not allow_network:
        raise RuntimeError(
            "Network access denied. "
            "Pass allow_network=True explicitly to allow GET-only requests."
        )

    now = _captured_at or datetime.now(timezone.utc)
    snap_id = snapshot_id or generate_snapshot_id(now)
    captured_at = utc_iso_now(now)

    if client is None:
        client = PolymarketPublicClient()

    market_records: List[MarketMetadataSnapshotRecord] = []
    order_book_records: List[OrderBookSnapshotRecord] = []
    order_books_requested = 0

    # Fetch markets via confirmed GET /markets endpoint.
    result = client.get_markets(limit=markets_limit)
    raw_list = result.data if isinstance(result.data, list) else []

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
                if len(token_ids_to_fetch) >= max_order_books:
                    break
            if len(token_ids_to_fetch) >= max_order_books:
                break

        order_books_requested = len(token_ids_to_fetch)
        for token_id in token_ids_to_fetch:
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
            "Rate-limit policy not confirmed (WP8-D002 OPEN). "
            "Not for automated or frequent scanning."
        ),
    )

    return market_records, order_book_records, manifest
