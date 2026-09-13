"""WP168 pmxt-v2 converted-event adapter for deterministic edge evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal
import hashlib
import re

from src.research_runtime.nautilus_offline import (
    BinaryOptionMarketContext,
    PmxtV2ReplaySource,
    convert_pmxt_v2_events,
)

from .models import ExecutableEdgeError, canonical_bytes, decimal_text


@dataclass(frozen=True)
class MarketTruthEvent:
    kind: str
    event_time_ns: int
    receive_time_ns: int
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    side: str | None = None
    price: str | None = None
    size: str | None = None


@dataclass(frozen=True)
class MarketTruthWindow:
    lineage_id: str
    source_external_dataset_id: str
    instrument_id: str
    conversion_policy_version: str
    ordered_event_digests: tuple[str, ...]
    known_gap_policy: str
    continuity_complete: bool
    first_receive_time_ns: int
    last_receive_time_ns: int
    events: tuple[MarketTruthEvent, ...]
    advisory_only: bool
    no_execution_authority: bool


def _lineage_preimage(window: MarketTruthWindow) -> dict[str, object]:
    return {
        "source_external_dataset_id": window.source_external_dataset_id,
        "conversion_policy_version": window.conversion_policy_version,
        "instrument_id": window.instrument_id,
        "ordered_event_digests": list(window.ordered_event_digests),
        "known_gap_policy": window.known_gap_policy,
        "events": [asdict(event) for event in window.events],
    }


def identify_market_truth_window(window: MarketTruthWindow) -> str:
    return "markettruthwindow:sha256:" + hashlib.sha256(canonical_bytes(_lineage_preimage(window))).hexdigest()


def validate_market_truth_window(window: object) -> None:
    if type(window) is not MarketTruthWindow or not window.events:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    keys = [(event.receive_time_ns, 0 if event.kind == "BOOK" else 1, event.event_time_ns) for event in window.events]
    invalid_event = False
    for event in window.events:
        if event.event_time_ns < 0 or event.receive_time_ns < 0:
            invalid_event = True
        if event.kind == "BOOK":
            if event.side is not None or event.price is not None or event.size is not None or not event.bids or not event.asks:
                invalid_event = True
            try:
                bids = [(Decimal(price), Decimal(size)) for price, size in event.bids]
                asks = [(Decimal(price), Decimal(size)) for price, size in event.asks]
            except Exception:
                invalid_event = True
            else:
                if any(price < 0 or price > 1 or size <= 0 for price, size in bids + asks):
                    invalid_event = True
                if bids != sorted(bids, reverse=True) or asks != sorted(asks):
                    invalid_event = True
        elif event.kind == "TRADE":
            try:
                price = Decimal(event.price or "")
                size = Decimal(event.size or "")
            except Exception:
                invalid_event = True
            else:
                if event.side not in {"BUY", "SELL"} or event.bids or event.asks or price < 0 or price > 1 or size <= 0:
                    invalid_event = True
    if (
        keys != sorted(keys)
        or any(event.kind not in {"BOOK", "TRADE"} for event in window.events)
        or invalid_event
        or not window.source_external_dataset_id
        or not window.instrument_id
        or not window.conversion_policy_version
        or not window.ordered_event_digests
        or any(re.fullmatch(r"[0-9a-f]{64}:[0-9]+", digest) is None for digest in window.ordered_event_digests)
        or window.first_receive_time_ns != min(event.receive_time_ns for event in window.events)
        or window.last_receive_time_ns != max(event.receive_time_ns for event in window.events)
        or window.continuity_complete != (window.known_gap_policy == "NONE")
        or window.lineage_id != identify_market_truth_window(window)
        or not window.advisory_only
        or not window.no_execution_authority
    ):
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")


def _fixed(value: object) -> str:
    return decimal_text(Decimal(str(value)))


def _book_event(obj: object) -> MarketTruthEvent:
    bids: list[tuple[str, str]] = []
    asks: list[tuple[str, str]] = []
    for delta in obj.deltas:
        order = getattr(delta, "order", None)
        if order is None or str(getattr(delta, "action", "")) not in {"ADD", "1"}:
            continue
        level = (_fixed(order.price), _fixed(order.size))
        if str(order.side) in {"BUY", "1"}:
            bids.append(level)
        elif str(order.side) in {"SELL", "2"}:
            asks.append(level)
    bids.sort(key=lambda pair: Decimal(pair[0]), reverse=True)
    asks.sort(key=lambda pair: Decimal(pair[0]))
    return MarketTruthEvent("BOOK", int(obj.ts_event), int(obj.ts_init), tuple(bids), tuple(asks))


def build_market_truth_window(
    source: PmxtV2ReplaySource, context: BinaryOptionMarketContext
) -> MarketTruthWindow:
    stream = convert_pmxt_v2_events(source, context)
    if not stream.is_valid or stream.instrument_id is None or stream.source_external_dataset_id is None:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    events: list[MarketTruthEvent] = []
    for obj in stream.converted_events:
        name = type(obj).__name__
        if name == "OrderBookDeltas":
            events.append(_book_event(obj))
        elif name == "TradeTick":
            side = str(obj.aggressor_side)
            if side in {"BUYER", "1"}:
                side = "BUY"
            elif side in {"SELLER", "2"}:
                side = "SELL"
            else:
                continue
            events.append(MarketTruthEvent(
                "TRADE", int(obj.ts_event), int(obj.ts_init), (), (), side,
                _fixed(obj.price), _fixed(obj.size),
            ))
    if not events:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    events.sort(key=lambda event: (event.receive_time_ns, 0 if event.kind == "BOOK" else 1, event.event_time_ns))
    provisional = MarketTruthWindow(
        "",
        stream.source_external_dataset_id,
        stream.instrument_id,
        str(stream.conversion_policy_version),
        stream.ordered_event_digests,
        source.descriptor.known_gap_policy,
        source.descriptor.known_gap_policy == "NONE",
        min(event.receive_time_ns for event in events),
        max(event.receive_time_ns for event in events),
        tuple(events),
        True,
        True,
    )
    result = replace(provisional, lineage_id=identify_market_truth_window(provisional))
    validate_market_truth_window(result)
    return result
