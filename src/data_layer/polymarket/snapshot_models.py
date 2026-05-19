"""Read-only snapshot persistence models for Polymarket market data.

Normalized, provenance-tagged dataclasses for local JSONL snapshot storage.
These models carry no trading, signing, credential, or order authority.

PROHIBITED — this module must never contain:
- Order placement, cancellation, signing, or submission logic.
- Credentials, API keys, private keys, wallet keys, or mnemonics.
- Authenticated request logic.
- Scheduled polling or bot-loop behavior.
- Network calls of any kind.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from typing import Optional

ADAPTER_VERSION = "wp10"
READ_ONLY_PROVENANCE = "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only"
MARKET_SOURCE = "gamma-api/markets"
ORDER_BOOK_SOURCE = "clob-api/book"
TOOL_NAME = "capture_market_snapshots"
WORK_PACKAGE = "WP10"


def generate_snapshot_id(dt: Optional[datetime] = None) -> str:
    """Return a timestamp-based snapshot run ID.

    Deterministic when a fixed datetime is provided (for testing).
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return f"snap_{dt.strftime('%Y%m%d_%H%M%S_%f')}"


def utc_iso_now(dt: Optional[datetime] = None) -> str:
    """Return ISO-format UTC timestamp string."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


@dataclasses.dataclass
class MarketMetadataSnapshotRecord:
    """Normalized, provenance-tagged market metadata record for local snapshot storage.

    Captures public market metadata via GET /markets only.
    Carries no trading authority, credentials, or order methods.
    """

    snapshot_id: str
    captured_at_utc: str
    source: str
    adapter_version: str
    market_id: str
    condition_id: str
    question: str
    market_status: str
    outcome_labels: list
    token_ids: list
    resolution_date: Optional[str]
    category: Optional[str]
    raw_field_names: list
    read_only_provenance: str = dataclasses.field(default=READ_ONLY_PROVENANCE)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict())


@dataclasses.dataclass
class OrderBookSnapshotRecord:
    """Normalized, provenance-tagged order-book snapshot record for local storage.

    Captures public CLOB book data via GET /book only.
    bids and asks are lists of {"price": str, "size": str} dicts.
    Carries no trading authority, credentials, or order methods.
    """

    snapshot_id: str
    captured_at_utc: str
    source: str
    adapter_version: str
    token_id: str
    bids: list
    asks: list
    raw_field_names: list
    read_only_provenance: str = dataclasses.field(default=READ_ONLY_PROVENANCE)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict())


@dataclasses.dataclass
class SnapshotManifest:
    """Run-level provenance metadata for a single snapshot capture session."""

    snapshot_id: str
    created_at_utc: str
    tool_name: str
    work_package: str
    markets_requested: int
    markets_written: int
    order_books_requested: int
    order_books_written: int
    network_used: bool
    output_files: list
    notes: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclasses.dataclass
class SnapshotWriteResult:
    """Result returned by SnapshotWriter after a write operation."""

    output_dir: str
    markets_file: Optional[str]
    order_books_file: Optional[str]
    manifest_file: Optional[str]
    markets_written: int
    order_books_written: int
    success: bool
    error: Optional[str] = None
