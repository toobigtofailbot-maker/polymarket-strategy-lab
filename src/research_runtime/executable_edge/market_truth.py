"""WP168 pmxt-v2 converted-event adapter for deterministic edge evaluation.

WP175E adds a parallel native path: a fail-closed, content-addressed bridge that
turns a verified uninterrupted WP169 public realtime capture epoch into a native
continuity-attested market-truth window, without touching the PMXT path above.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from src.research_runtime.nautilus_offline import (
    BinaryOptionMarketContext,
    PmxtV2ReplaySource,
    convert_pmxt_v2_events,
)
from src.data_layer.polymarket.market_truth_store import (
    AcceptedObservationRecord,
    GapEventRecord,
    MarketTruthStore,
    SessionEventRecord,
    read_accepted_asset_observations,
    read_gap_events,
    read_session_events,
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
    keys = [(event.receive_time_ns, event.event_time_ns, 0 if event.kind == "BOOK" else 1) for event in window.events]
    invalid_event = False
    for event in window.events:
        if event.event_time_ns < 0 or event.receive_time_ns < 0:
            invalid_event = True
        if event.kind == "BOOK":
            if event.side is not None or event.price is not None or event.size is not None:
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


def _enum_name(value: object) -> str:
    name = getattr(value, "name", None)
    return name if isinstance(name, str) else str(value)


def _apply_book_delta(
    delta: object, bids: dict[str, str], asks: dict[str, str]
) -> None:
    action = _enum_name(getattr(delta, "action", ""))
    if action in {"CLEAR", "4"}:
        bids.clear()
        asks.clear()
        return
    order = getattr(delta, "order", None)
    if order is None:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    side = _enum_name(getattr(order, "side", ""))
    levels = bids if side in {"BUY", "1"} else asks if side in {"SELL", "2"} else None
    if levels is None:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    price = _fixed(order.price)
    if action in {"DELETE", "3"}:
        levels.pop(price, None)
    elif action in {"ADD", "1", "UPDATE", "2"}:
        size = _fixed(order.size)
        if Decimal(size) <= 0:
            raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
        levels[price] = size
    else:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")


def _book_state_event(
    obj: object, bids: dict[str, str], asks: dict[str, str]
) -> MarketTruthEvent:
    bid_levels = tuple(sorted(bids.items(), key=lambda pair: Decimal(pair[0]), reverse=True))
    ask_levels = tuple(sorted(asks.items(), key=lambda pair: Decimal(pair[0])))
    return MarketTruthEvent(
        "BOOK", int(obj.ts_event), int(obj.ts_init), bid_levels, ask_levels
    )


def build_market_truth_window(
    source: PmxtV2ReplaySource, context: BinaryOptionMarketContext
) -> MarketTruthWindow:
    stream = convert_pmxt_v2_events(source, context)
    if not stream.is_valid or stream.instrument_id is None or stream.source_external_dataset_id is None:
        raise ExecutableEdgeError("MARKET_TRUTH_INVALID")
    events: list[MarketTruthEvent] = []
    bids: dict[str, str] = {}
    asks: dict[str, str] = {}
    for obj in stream.converted_events:
        name = type(obj).__name__
        if name == "OrderBookDeltas":
            for delta in obj.deltas:
                _apply_book_delta(delta, bids, asks)
            events.append(_book_state_event(obj, bids, asks))
        elif name == "OrderBookDelta":
            _apply_book_delta(obj, bids, asks)
            events.append(_book_state_event(obj, bids, asks))
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
    events.sort(key=lambda event: (
        event.receive_time_ns, event.event_time_ns, 0 if event.kind == "BOOK" else 1,
    ))
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


# ---------------------------------------------------------------------------
# WP175E native continuity-attested market-truth bridge (WP169 -> WP172).
#
# The native path never reinterprets or weakens the PMXT path above. It reads
# only durable WP169 evidence, proves continuity mechanically, and fails closed.
# A caller-provided boolean can never establish continuity.
# ---------------------------------------------------------------------------

NATIVE_ATTESTATION_PREFIX = "nativecontinuityattestation:sha256:"
NATIVE_CAPTURE_PREFIX = "nativecapture:sha256:"
NATIVE_WINDOW_PREFIX = "nativemarkettruthwindow:sha256:"
_NATIVE_MARKET_STATE_KINDS = ("book", "price_change", "last_trade_price")
_STREAMING = "STREAMING"
_OBSERVATION_ID_RE = re.compile(r"^markettruth:observation:sha256:[0-9a-f]{64}$")
_NATIVE_ATTESTATION_ID_RE = re.compile(
    r"^nativecontinuityattestation:sha256:[0-9a-f]{64}$"
)
_NATIVE_CAPTURE_ID_RE = re.compile(r"^nativecapture:sha256:[0-9a-f]{64}$")
_NATIVE_WINDOW_ID_RE = re.compile(r"^nativemarkettruthwindow:sha256:[0-9a-f]{64}$")
_MAX_NATIVE_READ_ROWS = 200_000


@dataclass(frozen=True)
class NativeMarketTruthContext:
    """Explicit instrument mapping for the WP169 bridge.

    Capture identity is deliberately absent: it is derived from the durable WP169
    WebSocket session id, never supplied as caller authority.
    """

    instrument_id: str


@dataclass(frozen=True)
class NativeContinuityAttestation:
    attestation_id: str
    source_capture_id: str
    asset_id: str
    start_received_at: str
    end_received_at: str
    initial_snapshot_observation_id: str
    first_observation_id: str
    last_observation_id: str
    observation_count: int
    session_id: str
    relevant_session_event_digest: str
    relevant_gap_event_digest: str
    gap_open_count: int
    gap_healed_count: int
    continuity_complete: bool = field(init=False, default=False)
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class NativeMarketTruthWindow:
    lineage_id: str
    source_capture_id: str
    instrument_id: str
    ordered_observation_ids: tuple[str, ...]
    first_receive_time_ns: int
    last_receive_time_ns: int
    events: tuple[MarketTruthEvent, ...]
    continuity_complete: bool
    continuity_attestation_id: str
    continuity_attestation: NativeContinuityAttestation
    advisory_only: bool
    no_execution_authority: bool


def _attestation_preimage(att: NativeContinuityAttestation) -> dict[str, object]:
    return {
        "source_capture_id": att.source_capture_id,
        "asset_id": att.asset_id,
        "start_received_at": att.start_received_at,
        "end_received_at": att.end_received_at,
        "initial_snapshot_observation_id": att.initial_snapshot_observation_id,
        "first_observation_id": att.first_observation_id,
        "last_observation_id": att.last_observation_id,
        "observation_count": att.observation_count,
        "session_id": att.session_id,
        "relevant_session_event_digest": att.relevant_session_event_digest,
        "relevant_gap_event_digest": att.relevant_gap_event_digest,
        "gap_open_count": att.gap_open_count,
        "gap_healed_count": att.gap_healed_count,
        "continuity_complete": att.continuity_complete,
    }


def identify_native_continuity_attestation(att: NativeContinuityAttestation) -> str:
    return NATIVE_ATTESTATION_PREFIX + hashlib.sha256(
        canonical_bytes(_attestation_preimage(att))
    ).hexdigest()


def _native_lineage_preimage(window: NativeMarketTruthWindow) -> dict[str, object]:
    return {
        "source_capture_id": window.source_capture_id,
        "instrument_id": window.instrument_id,
        "ordered_observation_ids": list(window.ordered_observation_ids),
        "first_receive_time_ns": window.first_receive_time_ns,
        "last_receive_time_ns": window.last_receive_time_ns,
        "continuity_attestation_id": window.continuity_attestation_id,
        "continuity_complete": window.continuity_complete,
        "events": [asdict(event) for event in window.events],
    }


def identify_native_market_truth_window(window: NativeMarketTruthWindow) -> str:
    return NATIVE_WINDOW_PREFIX + hashlib.sha256(
        canonical_bytes(_native_lineage_preimage(window))
    ).hexdigest()


def _native_capture_id(session_id: str) -> str:
    """Derive stable path-free capture provenance from the durable WS session."""
    return NATIVE_CAPTURE_PREFIX + hashlib.sha256(
        canonical_bytes({"version": "wp169-native-capture/1.0.0", "session_id": session_id})
    ).hexdigest()


def _session_event_digest(events: tuple[SessionEventRecord, ...]) -> str:
    return hashlib.sha256(
        canonical_bytes(
            [[e.sequence, e.session_id, e.state, e.received_at] for e in events]
        )
    ).hexdigest()


def _gap_event_digest(events: tuple[GapEventRecord, ...]) -> str:
    return hashlib.sha256(
        canonical_bytes(
            [[e.sequence, e.asset_id, e.state, e.reason, e.received_at] for e in events]
        )
    ).hexdigest()


def _receive_ns(value: str) -> int:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = parsed - epoch
    return (
        delta.days * 86_400_000_000_000
        + delta.seconds * 1_000_000_000
        + delta.microseconds * 1_000
    )


def _native_levels(raw: object, *, reverse: bool) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    levels: list[tuple[str, str]] = []
    seen_prices: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"price", "size"}:
            raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
        try:
            price = _fixed(item["price"])
            size = _fixed(item["size"])
        except (InvalidOperation, TypeError, ValueError):
            raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
        if (
            price in seen_prices
            or not Decimal("0") <= Decimal(price) <= Decimal("1")
            or Decimal(size) <= 0
        ):
            raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
        seen_prices.add(price)
        levels.append((price, size))
    return tuple(sorted(levels, key=lambda level: Decimal(level[0]), reverse=reverse))


def _ordered_book_event(
    event_ns: int, receive_ns: int, bids: dict[str, str], asks: dict[str, str]
) -> MarketTruthEvent:
    bid_levels = tuple(sorted(bids.items(), key=lambda p: Decimal(p[0]), reverse=True))
    ask_levels = tuple(sorted(asks.items(), key=lambda p: Decimal(p[0])))
    return MarketTruthEvent("BOOK", event_ns, receive_ns, bid_levels, ask_levels)


def _attest_native_continuity(
    store: MarketTruthStore,
    *,
    asset_id: str,
    start_received_at: str,
    end_received_at: str,
    context: NativeMarketTruthContext,
) -> tuple[NativeContinuityAttestation, tuple, int]:
    """Read durable WP169 evidence and derive an immutable continuity attestation.

    Returns the attestation, the ordered accepted WS market-state observations, and
    the index of the initial full book snapshot inside that ordered sequence. Raises
    a closed native error when no coherent market truth can be built at all.
    """
    if not isinstance(store, MarketTruthStore):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    try:
        observation_records = read_accepted_asset_observations(
            store,
            asset_id=asset_id,
            start_received_at=start_received_at,
            end_received_at=end_received_at,
            limit=_MAX_NATIVE_READ_ROWS,
        )
        sessions = read_session_events(
            store, upto_received_at=end_received_at, limit=_MAX_NATIVE_READ_ROWS
        )
        gaps = read_gap_events(
            store,
            asset_id=asset_id,
            upto_received_at=end_received_at,
            limit=_MAX_NATIVE_READ_ROWS,
        )
    except Exception:  # closed WP169 error surface; never echo
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None

    # Only ACCEPTED public WebSocket market-state observations may become truth.
    market_state_records = tuple(
        record
        for record in observation_records
        if record.observation.source_kind == "WS"
        and record.observation.event_kind in _NATIVE_MARKET_STATE_KINDS
    )
    if not market_state_records:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    market_state = tuple(record.observation for record in market_state_records)

    snapshot_index = next(
        (
            index
            for index, obs in enumerate(market_state)
            if obs.event_kind == "book" and obs.book_ready
        ),
        None,
    )
    if snapshot_index is None:
        # A delta before any valid start snapshot cannot establish market truth.
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    snapshot = market_state[snapshot_index]
    snap_at = snapshot.received_at

    # (B) the first included usable observation must itself be the full snapshot.
    leading_ok = snapshot_index == 0

    # (D, E, I) the interval itself -- not merely the suffix after the snapshot --
    # must lie inside one uninterrupted STREAMING epoch. A reconnect transition
    # before the snapshot but after the requested start therefore cannot be hidden.
    at_start = [s for s in sessions if s.received_at <= start_received_at]
    at_snapshot = [s for s in sessions if s.received_at <= snap_at]
    snapshot_session = at_snapshot[-1] if at_snapshot else None
    if snapshot_session is None or snapshot_session.state != _STREAMING:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    session_id = snapshot_session.session_id
    session_at_start = at_start[-1] if at_start else None
    transitions_inside = tuple(
        s for s in sessions if start_received_at < s.received_at <= end_received_at
    )
    session_ok = bool(
        session_at_start is not None
        and session_at_start.state == _STREAMING
        and session_at_start.session_id == session_id
        and snapshot_session.received_at < snap_at
        and not transitions_inside
        and all(record.session_id == session_id for record in market_state_records)
    )

    # (F, G, H) reconstruct exact per-asset gap state at interval start. Duplicate
    # OPEN, unmatched/mismatched HEALED, an already-open gap, or any transition in
    # the interval fails closed. Choosing a start strictly after a valid HEALED and
    # at a later full snapshot permits a fresh epoch without erasing history.
    active_gap_reason: str | None = None
    gap_history_valid = True
    for gap in gaps:
        if gap.received_at > start_received_at:
            break
        if gap.state == "OPEN":
            if active_gap_reason is not None:
                gap_history_valid = False
                break
            active_gap_reason = gap.reason
        else:
            if active_gap_reason is None or active_gap_reason != gap.reason:
                gap_history_valid = False
                break
            active_gap_reason = None
    gap_transition_inside = any(
        start_received_at < gap.received_at <= end_received_at for gap in gaps
    )
    healed_before_snapshot = all(
        gap.state != "HEALED" or gap.received_at < snap_at
        for gap in gaps
        if gap.received_at <= start_received_at
    )
    gap_ok = (
        gap_history_valid
        and active_gap_reason is None
        and healed_before_snapshot
        and not gap_transition_inside
    )

    continuity_complete = bool(leading_ok and session_ok and gap_ok)

    provisional = NativeContinuityAttestation(
        attestation_id="",
        source_capture_id=_native_capture_id(session_id),
        asset_id=asset_id,
        start_received_at=start_received_at,
        end_received_at=end_received_at,
        initial_snapshot_observation_id=snapshot.observation_id,
        first_observation_id=market_state[0].observation_id,
        last_observation_id=market_state[-1].observation_id,
        observation_count=len(market_state),
        session_id=session_id,
        relevant_session_event_digest=_session_event_digest(sessions),
        relevant_gap_event_digest=_gap_event_digest(gaps),
        gap_open_count=sum(1 for gap in gaps if gap.state == "OPEN"),
        gap_healed_count=sum(1 for gap in gaps if gap.state == "HEALED"),
        advisory_only=True,
        no_execution_authority=True,
    )
    object.__setattr__(provisional, "continuity_complete", continuity_complete)
    attestation = replace(
        provisional,
        attestation_id=identify_native_continuity_attestation(provisional),
    )
    object.__setattr__(attestation, "continuity_complete", continuity_complete)
    validate_native_continuity_attestation(attestation)
    return attestation, market_state, snapshot_index


def _reconstruct_native_events(
    market_state: tuple, snapshot_index: int
) -> tuple[list[MarketTruthEvent], list[str]]:
    """Rebuild BOOK/TRADE events from the snapshot onward using WP169 canonical
    payload semantics. Reconstruction starts at the full snapshot; leading deltas
    are never used as truth."""
    events: list[MarketTruthEvent] = []
    observation_ids: list[str] = []
    bids: dict[str, str] = {}
    asks: dict[str, str] = {}
    for obs in market_state[snapshot_index:]:
        try:
            payload = json.loads(obs.canonical_payload_json)
        except (TypeError, ValueError):
            raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
        if not isinstance(payload, dict):
            raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
        receive_ns = _receive_ns(obs.received_at)
        event_ns = _receive_ns(obs.event_time or obs.received_at)
        if obs.event_kind == "book":
            bids = dict(_native_levels(payload.get("bids"), reverse=True))
            asks = dict(_native_levels(payload.get("asks"), reverse=False))
            if bids and asks and max(Decimal(price) for price in bids) >= min(
                Decimal(price) for price in asks
            ):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
            events.append(_ordered_book_event(event_ns, receive_ns, bids, asks))
            observation_ids.append(obs.observation_id)
        elif obs.event_kind == "price_change":
            side = payload.get("side")
            price = payload.get("price")
            size = payload.get("size")
            levels = bids if side == "BUY" else asks if side == "SELL" else None
            if levels is None or not isinstance(price, str) or not isinstance(size, str):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
            try:
                canonical_price = _fixed(price)
                canonical_size = _fixed(size)
                if not Decimal("0") <= Decimal(canonical_price) <= Decimal("1"):
                    raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
                if Decimal(canonical_size) == 0:
                    if canonical_price not in levels:
                        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
                    levels.pop(canonical_price)
                elif Decimal(canonical_size) > 0:
                    levels[canonical_price] = canonical_size
                else:
                    raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
            except (InvalidOperation, TypeError, ValueError):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
            if bids and asks and max(Decimal(value) for value in bids) >= min(
                Decimal(value) for value in asks
            ):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
            events.append(_ordered_book_event(event_ns, receive_ns, bids, asks))
            observation_ids.append(obs.observation_id)
        elif obs.event_kind == "last_trade_price":
            side = payload.get("side")
            price = payload.get("price")
            size = payload.get("size")
            if side not in {"BUY", "SELL"} or not isinstance(price, str) or not isinstance(size, str):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
            try:
                fixed_price = _fixed(price)
                fixed_size = _fixed(size)
                if not Decimal("0") <= Decimal(fixed_price) <= Decimal("1") or Decimal(fixed_size) <= 0:
                    raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
                events.append(
                    MarketTruthEvent(
                        "TRADE", event_ns, receive_ns, (), (), side,
                        fixed_price, fixed_size,
                    )
                )
            except (InvalidOperation, TypeError, ValueError):
                raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
            observation_ids.append(obs.observation_id)
    return events, observation_ids


def validate_native_continuity_attestation(attestation: object) -> None:
    """Validate a native attestation as immutable, content-addressed evidence.

    The only construction path that can establish ``continuity_complete`` is the
    store-backed builder above. This validator detects any caller mutation of the
    result and binds the complete semantic record without accepting path data.
    """
    if type(attestation) is not NativeContinuityAttestation:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    string_fields = (
        attestation.attestation_id,
        attestation.source_capture_id,
        attestation.asset_id,
        attestation.start_received_at,
        attestation.end_received_at,
        attestation.initial_snapshot_observation_id,
        attestation.first_observation_id,
        attestation.last_observation_id,
        attestation.session_id,
        attestation.relevant_session_event_digest,
        attestation.relevant_gap_event_digest,
    )
    if (
        any(not isinstance(value, str) for value in string_fields)
        or type(attestation.observation_count) is not int
        or type(attestation.gap_open_count) is not int
        or type(attestation.gap_healed_count) is not int
        or type(attestation.continuity_complete) is not bool
        or type(attestation.advisory_only) is not bool
        or type(attestation.no_execution_authority) is not bool
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    if (
        _NATIVE_ATTESTATION_ID_RE.fullmatch(attestation.attestation_id) is None
        or attestation.attestation_id
        != identify_native_continuity_attestation(attestation)
        or _NATIVE_CAPTURE_ID_RE.fullmatch(attestation.source_capture_id) is None
        or attestation.source_capture_id != _native_capture_id(attestation.session_id)
        or not isinstance(attestation.asset_id, str)
        or not attestation.asset_id
        or _receive_ns(attestation.start_received_at)
        > _receive_ns(attestation.end_received_at)
        or _OBSERVATION_ID_RE.fullmatch(attestation.initial_snapshot_observation_id)
        is None
        or _OBSERVATION_ID_RE.fullmatch(attestation.first_observation_id) is None
        or _OBSERVATION_ID_RE.fullmatch(attestation.last_observation_id) is None
        or attestation.observation_count < 1
        or not attestation.session_id
        or re.fullmatch(r"[0-9a-f]{64}", attestation.relevant_session_event_digest)
        is None
        or re.fullmatch(r"[0-9a-f]{64}", attestation.relevant_gap_event_digest)
        is None
        or attestation.gap_open_count < 0
        or attestation.gap_healed_count < 0
        or attestation.advisory_only is not True
        or attestation.no_execution_authority is not True
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")


def validate_native_market_truth_window(window: object) -> None:
    if type(window) is not NativeMarketTruthWindow or not window.events:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    if (
        not isinstance(window.lineage_id, str)
        or not isinstance(window.source_capture_id, str)
        or not isinstance(window.instrument_id, str)
        or type(window.ordered_observation_ids) is not tuple
        or any(not isinstance(value, str) for value in window.ordered_observation_ids)
        or type(window.first_receive_time_ns) is not int
        or type(window.last_receive_time_ns) is not int
        or type(window.events) is not tuple
        or any(type(event) is not MarketTruthEvent for event in window.events)
        or type(window.continuity_complete) is not bool
        or not isinstance(window.continuity_attestation_id, str)
        or type(window.continuity_attestation) is not NativeContinuityAttestation
        or type(window.advisory_only) is not bool
        or type(window.no_execution_authority) is not bool
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    if any(
        not isinstance(event.kind, str)
        or type(event.event_time_ns) is not int
        or type(event.receive_time_ns) is not int
        or type(event.bids) is not tuple
        or type(event.asks) is not tuple
        or (event.side is not None and not isinstance(event.side, str))
        or (event.price is not None and not isinstance(event.price, str))
        or (event.size is not None and not isinstance(event.size, str))
        for event in window.events
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    keys = [
        (event.receive_time_ns, event.event_time_ns, 0 if event.kind == "BOOK" else 1)
        for event in window.events
    ]
    invalid_event = False
    for event in window.events:
        if event.event_time_ns < 0 or event.receive_time_ns < 0:
            invalid_event = True
        if event.kind == "BOOK":
            if event.side is not None or event.price is not None or event.size is not None:
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
    try:
        validate_native_continuity_attestation(window.continuity_attestation)
    except ExecutableEdgeError:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID") from None
    attestation = window.continuity_attestation
    if (
        keys != sorted(keys)
        or any(event.kind not in {"BOOK", "TRADE"} for event in window.events)
        or invalid_event
        or not window.source_capture_id
        or not window.instrument_id
        or not window.ordered_observation_ids
        or len(window.ordered_observation_ids) != len(window.events)
        or any(
            _OBSERVATION_ID_RE.fullmatch(obs_id) is None
            for obs_id in window.ordered_observation_ids
        )
        or _NATIVE_ATTESTATION_ID_RE.fullmatch(window.continuity_attestation_id) is None
        or window.continuity_attestation_id != attestation.attestation_id
        or window.source_capture_id != attestation.source_capture_id
        or window.continuity_complete != attestation.continuity_complete
        or window.ordered_observation_ids[0]
        != attestation.initial_snapshot_observation_id
        or len(window.ordered_observation_ids) > attestation.observation_count
        or window.first_receive_time_ns != min(event.receive_time_ns for event in window.events)
        or window.last_receive_time_ns != max(event.receive_time_ns for event in window.events)
        or not isinstance(window.continuity_complete, bool)
        or _NATIVE_WINDOW_ID_RE.fullmatch(window.lineage_id) is None
        or window.lineage_id != identify_native_market_truth_window(window)
        or window.advisory_only is not True
        or window.no_execution_authority is not True
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")


def build_native_market_truth_window(
    store: MarketTruthStore,
    *,
    asset_id: str,
    start_received_at: str,
    end_received_at: str,
    context: NativeMarketTruthContext,
) -> NativeMarketTruthWindow:
    """Convert a verified WP169 capture epoch for one asset into a native
    continuity-attested market-truth window. continuity_complete can be true only
    when every WP169-durable continuity condition is mechanically proven."""
    if type(context) is not NativeMarketTruthContext:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    if (
        not isinstance(context.instrument_id, str)
        or not context.instrument_id
    ):
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    attestation, market_state, snapshot_index = _attest_native_continuity(
        store,
        asset_id=asset_id,
        start_received_at=start_received_at,
        end_received_at=end_received_at,
        context=context,
    )
    events, observation_ids = _reconstruct_native_events(market_state, snapshot_index)
    if not events:
        raise ExecutableEdgeError("NATIVE_MARKET_TRUTH_INVALID")
    paired = sorted(
        zip(events, observation_ids),
        key=lambda pair: (
            pair[0].receive_time_ns,
            pair[0].event_time_ns,
            0 if pair[0].kind == "BOOK" else 1,
        ),
    )
    ordered_events = tuple(event for event, _ in paired)
    ordered_ids = tuple(obs_id for _, obs_id in paired)
    provisional = NativeMarketTruthWindow(
        "",
        attestation.source_capture_id,
        context.instrument_id,
        ordered_ids,
        min(event.receive_time_ns for event in ordered_events),
        max(event.receive_time_ns for event in ordered_events),
        ordered_events,
        attestation.continuity_complete,
        attestation.attestation_id,
        attestation,
        True,
        True,
    )
    result = replace(
        provisional, lineage_id=identify_native_market_truth_window(provisional)
    )
    validate_native_market_truth_window(result)
    return result
