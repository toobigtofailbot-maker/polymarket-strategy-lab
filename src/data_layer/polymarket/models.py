"""Read-only data models for the Polymarket public adapter.

All models represent observations from public GET endpoints.
No model carries order-placement, signing, or trading authority.
"""

from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass(frozen=True)
class MarketSummary:
    """Minimal market metadata record from the Gamma API."""

    market_id: str
    condition_id: str
    question: str
    market_status: str
    outcome_labels: tuple[str, ...]
    token_ids: tuple[str, ...]
    resolution_date: Optional[str] = None
    category: Optional[str] = None
    raw: dataclasses.field(default=None, repr=False) = dataclasses.field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_labels", tuple(self.outcome_labels))
        object.__setattr__(self, "token_ids", tuple(self.token_ids))


@dataclasses.dataclass(frozen=True)
class OrderBookLevel:
    """A single price/size level in an order-book snapshot."""

    price: str
    size: str


@dataclasses.dataclass(frozen=True)
class OrderBookSnapshot:
    """Point-in-time read-only order-book data for a single outcome token."""

    token_id: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    snapshot_timestamp: str
    source_url: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "bids", tuple(self.bids))
        object.__setattr__(self, "asks", tuple(self.asks))


@dataclasses.dataclass(frozen=True)
class ReadOnlyRequestInfo:
    """Provenance record for a single read-only HTTP GET request."""

    method: str
    url: str
    status_code: int
    latency_ms: float

    def __post_init__(self) -> None:
        if self.method.upper() != "GET":
            raise ValueError(
                f"ReadOnlyRequestInfo only permits GET; got {self.method!r}"
            )


@dataclasses.dataclass(frozen=True)
class AdapterResult:
    """Wrapper that pairs a parsed data value with its provenance."""

    data: object
    request_info: ReadOnlyRequestInfo
    read_only_provenance: str = "public-get-only"
