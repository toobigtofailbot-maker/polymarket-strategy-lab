"""Normalized in-memory market catalog built from WP10 snapshot records.

Reads MarketMetadataSnapshotRecord objects and builds lookup structures for
offline research and inspection. Makes no network calls. Carries no trading,
signing, credential, or order authority.

PROHIBITED — this module must never contain:
- Network calls of any kind.
- Order placement, cancellation, signing, or submission logic.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Scheduled polling or bot-loop behavior.
- Database reads or writes.
- Imports of PolymarketPublicClient or any network adapter.
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from typing import Dict, List, Optional

from .snapshot_models import MarketMetadataSnapshotRecord


@dataclasses.dataclass
class CatalogOutcomeToken:
    """Maps a single token_id to its outcome label within a market."""

    token_id: str
    outcome_label: str
    market_id: str


@dataclasses.dataclass
class CatalogMarket:
    """Latest normalized view of a single market from snapshot records."""

    market_id: str
    condition_id: str
    question: str
    market_status: str
    outcome_labels: list
    token_ids: list
    resolution_date: Optional[str]
    category: Optional[str]
    snapshot_id: str
    captured_at_utc: str
    outcome_tokens: List[CatalogOutcomeToken]


@dataclasses.dataclass
class CatalogBuildResult:
    """Result returned by MarketCatalog.from_market_records()."""

    catalog: "MarketCatalog"
    total_records_processed: int
    unique_market_count: int
    duplicate_market_count: int
    warnings: List[str]


class MarketCatalog:
    """In-memory normalized market catalog built from snapshot records.

    Built via from_market_records(). Provides lookups by market_id, token_id,
    and condition_id. Carries no trading or execution authority.

    No order, execution, signal, or trading methods may ever be added here.
    See docs/polymarket_snapshot_replay_catalog.md for the full prohibition list.
    """

    def __init__(
        self,
        latest_by_market_id: Dict[str, MarketMetadataSnapshotRecord],
        history_by_market_id: Dict[str, List[MarketMetadataSnapshotRecord]],
    ) -> None:
        self._latest: Dict[str, MarketMetadataSnapshotRecord] = latest_by_market_id
        self._history: Dict[str, List[MarketMetadataSnapshotRecord]] = history_by_market_id

        self._token_to_market: Dict[str, str] = {}
        self._condition_to_market: Dict[str, str] = {}

        for market_id, record in self._latest.items():
            self._condition_to_market[record.condition_id] = market_id
            for token_id in record.token_ids:
                self._token_to_market[token_id] = market_id

    @classmethod
    def from_market_records(
        cls, records: List[MarketMetadataSnapshotRecord]
    ) -> CatalogBuildResult:
        """Build a MarketCatalog from a list of snapshot records.

        Latest record per market_id is determined by captured_at_utc (string
        lexicographic sort; ISO-8601 timestamps sort correctly this way).
        """
        latest: Dict[str, MarketMetadataSnapshotRecord] = {}
        history: Dict[str, List[MarketMetadataSnapshotRecord]] = defaultdict(list)
        warnings: List[str] = []
        duplicate_count = 0

        for record in records:
            mid = record.market_id
            history[mid].append(record)
            if mid in latest:
                duplicate_count += 1
                if record.captured_at_utc > latest[mid].captured_at_utc:
                    latest[mid] = record
            else:
                latest[mid] = record

        for mid in history:
            history[mid].sort(key=lambda r: r.captured_at_utc)

        catalog = cls(
            latest_by_market_id=latest,
            history_by_market_id=dict(history),
        )

        return CatalogBuildResult(
            catalog=catalog,
            total_records_processed=len(records),
            unique_market_count=len(latest),
            duplicate_market_count=duplicate_count,
            warnings=warnings,
        )

    def count(self) -> int:
        """Return the number of unique markets in the catalog."""
        return len(self._latest)

    def list_market_ids(self) -> List[str]:
        """Return a sorted list of all known market_ids."""
        return sorted(self._latest.keys())

    def get_market(self, market_id: str) -> Optional[CatalogMarket]:
        """Return the latest CatalogMarket for market_id, or None if not found."""
        record = self._latest.get(market_id)
        if record is None:
            return None
        return _record_to_catalog_market(record)

    def get_market_history(self, market_id: str) -> List[CatalogMarket]:
        """Return all CatalogMarket snapshots for market_id, oldest first."""
        return [
            _record_to_catalog_market(r)
            for r in self._history.get(market_id, [])
        ]

    def get_latest_markets(self) -> Dict[str, CatalogMarket]:
        """Return a dict of market_id → latest CatalogMarket for all markets."""
        return {mid: _record_to_catalog_market(r) for mid, r in self._latest.items()}

    def find_by_token_id(self, token_id: str) -> Optional[str]:
        """Return the market_id that owns token_id, or None."""
        return self._token_to_market.get(token_id)

    def find_by_condition_id(self, condition_id: str) -> Optional[str]:
        """Return the market_id for condition_id, or None."""
        return self._condition_to_market.get(condition_id)

    def summary(self) -> dict:
        """Return a sanitized summary dict for inspection and export."""
        category_counts: Dict[str, int] = defaultdict(int)
        status_counts: Dict[str, int] = defaultdict(int)
        snapshot_ids: set = set()
        total_tokens = 0

        for record in self._latest.values():
            cat = record.category or "unknown"
            category_counts[cat] += 1
            status_counts[record.market_status] += 1
            snapshot_ids.add(record.snapshot_id)
            total_tokens += len(record.token_ids)

        return {
            "unique_market_count": len(self._latest),
            "total_token_count": total_tokens,
            "category_distribution": dict(sorted(category_counts.items())),
            "status_distribution": dict(sorted(status_counts.items())),
            "snapshot_id_count": len(snapshot_ids),
            "snapshot_ids": sorted(snapshot_ids),
        }


def _record_to_catalog_market(record: MarketMetadataSnapshotRecord) -> CatalogMarket:
    outcome_tokens = []
    labels = record.outcome_labels or []
    token_ids = record.token_ids or []
    for i, token_id in enumerate(token_ids):
        label = labels[i] if i < len(labels) else f"outcome_{i}"
        outcome_tokens.append(
            CatalogOutcomeToken(
                token_id=token_id,
                outcome_label=label,
                market_id=record.market_id,
            )
        )
    return CatalogMarket(
        market_id=record.market_id,
        condition_id=record.condition_id,
        question=record.question,
        market_status=record.market_status,
        outcome_labels=record.outcome_labels,
        token_ids=record.token_ids,
        resolution_date=record.resolution_date,
        category=record.category,
        snapshot_id=record.snapshot_id,
        captured_at_utc=record.captured_at_utc,
        outcome_tokens=outcome_tokens,
    )
