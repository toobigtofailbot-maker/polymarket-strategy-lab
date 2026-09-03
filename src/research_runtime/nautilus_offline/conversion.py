"""WP168 WP167-pmxt-v2 -> NautilusTrader deterministic event conversion (offline).

Consumes the frozen :class:`PmxtV2ReplaySource` (a WP167 ``ExternalDatasetDescriptor`` plus
its ``PmxtV2SourceFile`` tuple), validates provenance and revalidates every source hash via
WP167 public boundaries, validates the pmxt-v2 event-semantic matrix, and produces the
canonical, receive-time-primary, physical-order-independent ordered event stream plus a
tick-size regime schedule and per-type counts. Exact decimals; no float; closed
``NAUTILUS_EVENT_CONVERSION_INVALID`` with no raw path/source-row/exception echo.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.data_layer.analytical_research import (
    PMXT_V2_DATASET_NAME,
    PMXT_V2_DATASET_VERSION,
    PMXT_V2_EVENT_TYPES,
    PMXT_V2_PROVIDER_ID,
    PMXT_V2_SOURCE_CLASS,
    PMXT_V2_VALID_SIDES,
    ExternalDatasetDescriptor,
    ExternalSourceObject,
    PmxtV2SourceFile,
    revalidate_pmxt_v2_source_hash,
)
from src.data_layer.analytical_research.pmxt_v2 import (
    PMXT_V2_DECIMAL_SPECS,
    PMXT_V2_IMPORTER_ID,
    PMXT_V2_IMPORTER_VERSION,
    PMXT_V2_RECEIVE_TIMESTAMP_SEMANTICS,
    PMXT_V2_SOURCE_TIMESTAMP_SEMANTICS,
)

from .instruments import BinaryOptionMarketContext, build_binary_option

CONVERSION_POLICY_VERSION = "wp168-nautilus-pmxt-v2-conversion/1.0.0"
SOURCE_DATASET_KIND = "WP167_EXTERNAL_DATASET_DESCRIPTOR"

EVENT_KIND_RANK = {
    "book": 0,
    "price_change": 1,
    "last_trade_price": 2,
    "tick_size_change": 3,
}

CONVERSION_STATUS_OK = "NAUTILUS_EVENTS_CONVERTED"
CONVERSION_STATUS_REJECTED = "NAUTILUS_EVENT_CONVERSION_REJECTED"
CONVERSION_ERROR = "NAUTILUS_EVENT_CONVERSION_INVALID"

_MS_TO_NS = 1_000_000
_OWNED_FIELDS = {
    "book": ("bids", "asks"),
    "price_change": ("price", "size", "side", "best_bid", "best_ask"),
    "last_trade_price": ("price", "size", "side", "fee_rate_bps", "transaction_hash"),
    "tick_size_change": ("old_tick_size", "new_tick_size"),
}
_EVENT_SPECIFIC_FIELDS = (
    "bids", "asks", "price", "size", "side", "best_bid", "best_ask",
    "fee_rate_bps", "transaction_hash", "old_tick_size", "new_tick_size",
)


def canonical_json_bytes(value: object) -> bytes:
    """Deterministic UTF-8 canonical JSON (sorted keys, compact, no NaN)."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def scan_public_result_for_echo(value: object, forbidden: tuple[str, ...]) -> tuple[str, ...]:
    """Recursively scan a public result for forbidden substrings; return the hits found.

    Nautilus third-party objects and bytes are treated as opaque (never traversed for
    project identity), matching the frozen EXCLUDED classification.
    """
    hits: list[str] = []

    def _walk(node: object) -> None:
        if isinstance(node, str):
            for needle in forbidden:
                if needle and needle in node:
                    hits.append(needle)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)
        elif isinstance(node, dict):
            for key, item in node.items():
                _walk(key)
                _walk(item)
        elif hasattr(node, "__dataclass_fields__"):
            for field_name in node.__dataclass_fields__:
                _walk(getattr(node, field_name))
        # ints/floats/bools/None and opaque third-party objects are not traversed.

    _walk(value)
    return tuple(dict.fromkeys(hits))


def stream_identity_preimage(stream: "ConvertedEventStream") -> dict[str, object]:
    """The committed-identity preimage of a converted stream (path-independent)."""
    return {
        "conversion_policy_version": stream.conversion_policy_version,
        "source_dataset_kind": stream.source_dataset_kind,
        "source_external_dataset_id": stream.source_external_dataset_id,
        "instrument_id": stream.instrument_id,
        "ordered_event_digests": list(stream.ordered_event_digests),
        "input_event_counts_by_type": [list(pair) for pair in stream.input_event_counts_by_type],
        "tick_size_regime_sequence": [list(item) for item in stream.tick_size_regime_sequence],
        "first_event_time_ns": stream.first_event_time_ns,
        "last_event_time_ns": stream.last_event_time_ns,
    }


def stream_identity_digest(stream: "ConvertedEventStream") -> str:
    """Deterministic SHA-256 hex over the committed stream-identity preimage."""
    return hashlib.sha256(canonical_json_bytes(stream_identity_preimage(stream))).hexdigest()


@dataclass(frozen=True)
class PmxtV2ReplaySource:
    descriptor: ExternalDatasetDescriptor
    source_files: tuple[PmxtV2SourceFile, ...]


@dataclass(frozen=True)
class ConvertedEventStream:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    instrument_id: str | None
    source_dataset_kind: str | None
    source_external_dataset_id: str | None
    conversion_policy_version: str | None
    ordered_event_digests: tuple[str, ...]
    input_event_counts_by_type: tuple[tuple[str, int], ...]
    tick_size_regime_sequence: tuple[tuple[str, str, int], ...]
    first_event_time_ns: int | None
    last_event_time_ns: int | None
    warnings: tuple[str, ...]
    converted_events: tuple[object, ...]


class _ConversionError(Exception):
    pass


def _rejected() -> ConvertedEventStream:
    return ConvertedEventStream(
        is_valid=False,
        status=CONVERSION_STATUS_REJECTED,
        error_codes=(CONVERSION_ERROR,),
        instrument_id=None,
        source_dataset_kind=None,
        source_external_dataset_id=None,
        conversion_policy_version=None,
        ordered_event_digests=(),
        input_event_counts_by_type=(),
        tick_size_regime_sequence=(),
        first_event_time_ns=None,
        last_event_time_ns=None,
        warnings=(),
        converted_events=(),
    )


def _decimal_text(value: Decimal, scale: int) -> str:
    return f"{value:.{scale}f}"


def _validate_descriptor(descriptor: ExternalDatasetDescriptor) -> None:
    if type(descriptor) is not ExternalDatasetDescriptor:
        raise _ConversionError()
    if descriptor.provider_id != PMXT_V2_PROVIDER_ID:
        raise _ConversionError()
    if descriptor.dataset_name != PMXT_V2_DATASET_NAME:
        raise _ConversionError()
    if descriptor.dataset_version != PMXT_V2_DATASET_VERSION:
        raise _ConversionError()
    if descriptor.source_class != PMXT_V2_SOURCE_CLASS:
        raise _ConversionError()
    if not descriptor.event_types or any(
        event not in PMXT_V2_EVENT_TYPES for event in descriptor.event_types
    ):
        raise _ConversionError()
    # Importer and timestamp semantics must be exactly compatible with the WP167 pmxt-v2
    # contract, so the receive/event-time replay semantics are bound to the verified source.
    if descriptor.importer_id != PMXT_V2_IMPORTER_ID:
        raise _ConversionError()
    if descriptor.importer_version != PMXT_V2_IMPORTER_VERSION:
        raise _ConversionError()
    if descriptor.source_timestamp_semantics != PMXT_V2_SOURCE_TIMESTAMP_SEMANTICS:
        raise _ConversionError()
    if descriptor.receive_timestamp_semantics != PMXT_V2_RECEIVE_TIMESTAMP_SEMANTICS:
        raise _ConversionError()
    if not isinstance(descriptor.source_objects, tuple) or not descriptor.source_objects:
        raise _ConversionError()


def _map_sources_one_to_one(
    descriptor: ExternalDatasetDescriptor, source_files: tuple[PmxtV2SourceFile, ...]
) -> list[tuple[PmxtV2SourceFile, ExternalSourceObject]]:
    if not isinstance(source_files, tuple) or not source_files:
        raise _ConversionError()
    if any(type(entry) is not PmxtV2SourceFile for entry in source_files):
        raise _ConversionError()

    objects_by_key: dict[tuple[str, str], ExternalSourceObject] = {}
    for obj in descriptor.source_objects:
        key = (obj.object_name, obj.partition_identity)
        if obj.object_name in {k[0] for k in objects_by_key} or key in objects_by_key:
            raise _ConversionError()  # duplicate object_name
        objects_by_key[key] = obj

    file_keys = [(f.object_name, f.partition_identity) for f in source_files]
    if len({k[0] for k in file_keys}) != len(file_keys):
        raise _ConversionError()  # duplicate source-file object_name
    if len(source_files) != len(descriptor.source_objects):
        raise _ConversionError()  # extra/missing

    mapped: list[tuple[PmxtV2SourceFile, ExternalSourceObject]] = []
    for source_file, key in zip(source_files, file_keys):
        obj = objects_by_key.get(key)
        if obj is None:
            raise _ConversionError()
        if not revalidate_pmxt_v2_source_hash(source_file.path, obj.source_sha256):
            raise _ConversionError()
        mapped.append((source_file, obj))
    return mapped


def _read_rows(source_file: PmxtV2SourceFile) -> list[dict[str, object]]:
    import pyarrow.parquet as pq  # local import; offline, no network

    table = pq.read_table(source_file.path)
    columns = {name: table.column(name).to_pylist() for name in table.column_names}
    row_count = table.num_rows
    rows: list[dict[str, object]] = []
    for index in range(row_count):
        rows.append({name: columns[name][index] for name in columns})
    return rows


def _normalize_market(value: object) -> str:
    if isinstance(value, bytes):
        text = value.decode("ascii")
    elif isinstance(value, str):
        text = value
    else:
        raise _ConversionError()
    if len(text) != 66 or not text.startswith("0x"):
        raise _ConversionError()
    body = text[2:]
    if any(ch not in "0123456789abcdef" for ch in body):
        raise _ConversionError()
    return text


def _normalize_asset_id(value: object) -> str:
    if not isinstance(value, str) or not value or any(ch not in "0123456789" for ch in value):
        raise _ConversionError()
    return value


def _as_ns(value: object) -> int:
    # pyarrow timestamp[ms, UTC] -> python datetime; convert to exact integer ns.
    import datetime as _dt

    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            raise _ConversionError()
        epoch = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
        delta = value - epoch
        micros = delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds
        return micros * 1_000
    if isinstance(value, int) and not isinstance(value, bool):
        return value * _MS_TO_NS
    raise _ConversionError()


def _decimal_at_scale(value: object, scale: int) -> Decimal:
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, str):
        try:
            dec = Decimal(value)
        except (InvalidOperation, ValueError):
            raise _ConversionError()
    else:
        raise _ConversionError()
    quantized = dec.quantize(Decimal(1).scaleb(-scale))
    if quantized != dec:
        raise _ConversionError()
    return dec


def _require_price_multiple(value: Decimal, increment: Decimal) -> None:
    ratio = value / increment
    if ratio != ratio.to_integral_value():
        raise _ConversionError()


def _normalize_book_side(raw: object, ascending: bool) -> list[tuple[Decimal, Decimal]]:
    if not isinstance(raw, str):
        raise _ConversionError()
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        raise _ConversionError()
    if not isinstance(parsed, list):
        raise _ConversionError()
    price_scale = PMXT_V2_DECIMAL_SPECS["best_bid"][1]
    size_scale = PMXT_V2_DECIMAL_SPECS["size"][1]
    levels: list[tuple[Decimal, Decimal]] = []
    seen_prices: set[Decimal] = set()
    for level in parsed:
        if not isinstance(level, list) or len(level) != 2:
            raise _ConversionError()
        price = _decimal_at_scale(level[0], price_scale)
        size = _decimal_at_scale(level[1], size_scale)
        if size < 0:
            raise _ConversionError()
        if price in seen_prices:
            raise _ConversionError()  # duplicate price level on one side
        seen_prices.add(price)
        levels.append((price, size))
    levels.sort(key=lambda pair: pair[0], reverse=not ascending)
    return levels


def convert_pmxt_v2_events(
    source: PmxtV2ReplaySource, context: BinaryOptionMarketContext
) -> ConvertedEventStream:
    """Return the closed converted event stream. Never raises, never echoes."""
    from nautilus_trader.model.data import (
        BookOrder,
        OrderBookDelta,
        OrderBookDeltas,
        TradeTick,
    )
    from nautilus_trader.model.enums import AggressorSide, BookAction, OrderSide
    from nautilus_trader.model.identifiers import TradeId
    from nautilus_trader.model.objects import Price, Quantity

    try:
        if type(source) is not PmxtV2ReplaySource:
            raise _ConversionError()
        descriptor = source.descriptor
        _validate_descriptor(descriptor)
        mapped = _map_sources_one_to_one(descriptor, source.source_files)

        mapping = build_binary_option(context)
        if not mapping.is_valid or mapping.binary_option is None:
            raise _ConversionError()
        instrument = mapping.binary_option
        instrument_id = instrument.id
        price_increment = Decimal(context.price_increment)
        price_precision = instrument.price_precision
        size_precision = instrument.size_precision

        market_expected = context.condition_id
        asset_expected = context.outcome_token_id

        # Read + validate every row into a canonical intermediate representation.
        canonical_rows: list[dict[str, object]] = []
        for source_file, _obj in mapped:
            for row in _read_rows(source_file):
                canonical_rows.append(
                    _validate_and_normalize_row(row, market_expected, asset_expected)
                )
        if not canonical_rows:
            raise _ConversionError()

        # Canonical bytes + digest per row; total order key; duplicate expansion.
        keyed: list[tuple[tuple[int, int, int, str, bytes], dict[str, object]]] = []
        for norm in canonical_rows:
            row_bytes = canonical_json_bytes(norm["_canonical"])
            digest = hashlib.sha256(row_bytes).hexdigest()
            key = (
                norm["ts_init"],
                norm["ts_event"],
                EVENT_KIND_RANK[norm["event_type"]],
                digest,
                row_bytes,
            )
            norm["_digest"] = digest
            keyed.append((key, norm))
        keyed.sort(key=lambda item: item[0])

        ordered_digests: list[str] = []
        converted_events: list[object] = []
        counts: dict[str, int] = {name: 0 for name in PMXT_V2_EVENT_TYPES}
        regime: list[tuple[str, str, int]] = []
        first_ns: int | None = None
        last_ns: int | None = None
        duplicate_run: dict[bytes, int] = {}
        sequence = 0

        for key, norm in keyed:
            row_bytes = key[4]
            ordinal = duplicate_run.get(row_bytes, 0)
            duplicate_run[row_bytes] = ordinal + 1
            ordered_digests.append(f"{norm['_digest']}:{ordinal}")

            event_type = norm["event_type"]
            counts[event_type] += 1
            ts_event = norm["ts_event"]
            ts_init = norm["ts_init"]
            first_ns = ts_event if first_ns is None else min(first_ns, ts_event)
            last_ns = ts_event if last_ns is None else max(last_ns, ts_event)

            if event_type == "book":
                deltas = [OrderBookDelta.clear(instrument_id, sequence, ts_event, ts_init)]
                for price, size in norm["bids"]:
                    _require_price_multiple(price, price_increment)
                    deltas.append(
                        OrderBookDelta(
                            instrument_id, BookAction.ADD,
                            BookOrder(
                                OrderSide.BUY,
                                Price.from_str(_decimal_text(price, price_precision)),
                                Quantity.from_str(_decimal_text(size, size_precision)),
                                0,
                            ),
                            0, sequence, ts_event, ts_init,
                        )
                    )
                for price, size in norm["asks"]:
                    _require_price_multiple(price, price_increment)
                    deltas.append(
                        OrderBookDelta(
                            instrument_id, BookAction.ADD,
                            BookOrder(
                                OrderSide.SELL,
                                Price.from_str(_decimal_text(price, price_precision)),
                                Quantity.from_str(_decimal_text(size, size_precision)),
                                0,
                            ),
                            0, sequence, ts_event, ts_init,
                        )
                    )
                # Certified mapping: one source `book` event becomes exactly one Nautilus
                # OrderBookDeltas snapshot (CLEAR + canonical ADDs). Persistence/replay
                # flatten it internally; the public semantic remains one snapshot.
                converted_events.append(
                    OrderBookDeltas(instrument_id=instrument_id, deltas=deltas)
                )
            elif event_type == "price_change":
                price = norm["price"]
                size = norm["size"]
                _require_price_multiple(price, price_increment)
                side = OrderSide.BUY if norm["side"] == "BUY" else OrderSide.SELL
                action = BookAction.DELETE if size == 0 else BookAction.UPDATE
                converted_events.append(
                    OrderBookDelta(
                        instrument_id, action,
                        BookOrder(
                            side,
                            Price.from_str(_decimal_text(price, price_precision)),
                            Quantity.from_str(_decimal_text(size, size_precision)),
                            0,
                        ),
                        0, sequence, ts_event, ts_init,
                    )
                )
            elif event_type == "last_trade_price":
                price = norm["price"]
                size = norm["size"]
                _require_price_multiple(price, price_increment)
                aggressor = (
                    AggressorSide.BUYER if norm["side"] == "BUY" else AggressorSide.SELLER
                )
                converted_events.append(
                    TradeTick(
                        instrument_id=instrument_id,
                        price=Price.from_str(_decimal_text(price, price_precision)),
                        size=Quantity.from_str(_decimal_text(size, size_precision)),
                        aggressor_side=aggressor,
                        trade_id=TradeId(
                            # Identity-excluded Nautilus id; duplicate ordinal keeps it unique
                            # for exact byte-identical duplicate rows (which share a hash).
                            hashlib.sha256(
                                f"{norm['transaction_hash']}:{ordinal}".encode("utf-8")
                            ).hexdigest()[:36]
                        ),
                        ts_event=ts_event,
                        ts_init=ts_init,
                    )
                )
            else:  # tick_size_change
                regime.append((norm["old_tick_size"], norm["new_tick_size"], ts_event))
            sequence += 1

        return ConvertedEventStream(
            is_valid=True,
            status=CONVERSION_STATUS_OK,
            error_codes=(),
            instrument_id=str(instrument_id),
            source_dataset_kind=SOURCE_DATASET_KIND,
            source_external_dataset_id=descriptor.external_dataset_id,
            conversion_policy_version=CONVERSION_POLICY_VERSION,
            ordered_event_digests=tuple(ordered_digests),
            input_event_counts_by_type=tuple(
                (name, counts[name]) for name in PMXT_V2_EVENT_TYPES
            ),
            tick_size_regime_sequence=tuple(regime),
            first_event_time_ns=first_ns,
            last_event_time_ns=last_ns,
            warnings=tuple(mapping.warnings),
            converted_events=(instrument,) + tuple(converted_events),
        )
    except _ConversionError:
        return _rejected()
    except Exception:
        return _rejected()


def _validate_and_normalize_row(
    row: dict[str, object], market_expected: str, asset_expected: str
) -> dict[str, object]:
    event_type = row.get("event_type")
    if event_type not in PMXT_V2_EVENT_TYPES:
        raise _ConversionError()
    market = _normalize_market(row.get("market"))
    if market != market_expected:
        raise _ConversionError()
    asset_id = _normalize_asset_id(row.get("asset_id"))
    if asset_id != asset_expected:
        raise _ConversionError()
    ts_event = _as_ns(row.get("timestamp"))
    ts_init = _as_ns(row.get("timestamp_received"))

    owned = _OWNED_FIELDS[event_type]
    # Unowned event-specific fields must be null.
    for field_name in _EVENT_SPECIFIC_FIELDS:
        if field_name not in owned and row.get(field_name) is not None:
            raise _ConversionError()
    # Owned fields must be present/non-null.
    for field_name in owned:
        if row.get(field_name) is None:
            raise _ConversionError()

    norm: dict[str, object] = {
        "event_type": event_type,
        "market": market,
        "asset_id": asset_id,
        "ts_event": ts_event,
        "ts_init": ts_init,
    }

    if event_type == "book":
        bids = _normalize_book_side(row.get("bids"), ascending=False)
        asks = _normalize_book_side(row.get("asks"), ascending=True)
        norm["bids"] = bids
        norm["asks"] = asks
        norm["_canon_bids"] = [
            [_decimal_text(p, PMXT_V2_DECIMAL_SPECS["best_bid"][1]),
             _decimal_text(s, PMXT_V2_DECIMAL_SPECS["size"][1])]
            for p, s in bids
        ]
        norm["_canon_asks"] = [
            [_decimal_text(p, PMXT_V2_DECIMAL_SPECS["best_ask"][1]),
             _decimal_text(s, PMXT_V2_DECIMAL_SPECS["size"][1])]
            for p, s in asks
        ]
    elif event_type in ("price_change", "last_trade_price"):
        side = row.get("side")
        if side not in PMXT_V2_VALID_SIDES:
            raise _ConversionError()
        price = _decimal_at_scale(row.get("price"), PMXT_V2_DECIMAL_SPECS["price"][1])
        size = _decimal_at_scale(row.get("size"), PMXT_V2_DECIMAL_SPECS["size"][1])
        if size < 0:
            raise _ConversionError()
        norm["side"] = side
        norm["price"] = price
        norm["size"] = size
        if event_type == "price_change":
            best_bid = _decimal_at_scale(row.get("best_bid"), PMXT_V2_DECIMAL_SPECS["best_bid"][1])
            best_ask = _decimal_at_scale(row.get("best_ask"), PMXT_V2_DECIMAL_SPECS["best_ask"][1])
            norm["best_bid"] = _decimal_text(best_bid, PMXT_V2_DECIMAL_SPECS["best_bid"][1])
            norm["best_ask"] = _decimal_text(best_ask, PMXT_V2_DECIMAL_SPECS["best_ask"][1])
        else:
            fee_rate_bps = row.get("fee_rate_bps")
            if not isinstance(fee_rate_bps, int) or isinstance(fee_rate_bps, bool) or fee_rate_bps < 0:
                raise _ConversionError()
            transaction_hash = row.get("transaction_hash")
            if not isinstance(transaction_hash, str) or not transaction_hash:
                raise _ConversionError()
            norm["fee_rate_bps"] = fee_rate_bps
            norm["transaction_hash"] = transaction_hash
    else:  # tick_size_change
        old_tick = _decimal_at_scale(row.get("old_tick_size"), PMXT_V2_DECIMAL_SPECS["old_tick_size"][1])
        new_tick = _decimal_at_scale(row.get("new_tick_size"), PMXT_V2_DECIMAL_SPECS["new_tick_size"][1])
        norm["old_tick_size"] = _decimal_text(old_tick, PMXT_V2_DECIMAL_SPECS["old_tick_size"][1])
        norm["new_tick_size"] = _decimal_text(new_tick, PMXT_V2_DECIMAL_SPECS["new_tick_size"][1])

    # Build the canonical (semantic-bytes) view: decimals as fixed-point text, null for
    # unowned, book levels normalized. Internal keys prefixed with "_" are excluded.
    canonical = {k: v for k, v in norm.items() if not k.startswith("_") and k not in ("bids", "asks")}
    if event_type == "book":
        canonical["bids"] = norm["_canon_bids"]
        canonical["asks"] = norm["_canon_asks"]
    if event_type in ("price_change", "last_trade_price"):
        canonical["price"] = _decimal_text(norm["price"], PMXT_V2_DECIMAL_SPECS["price"][1])
        canonical["size"] = _decimal_text(norm["size"], PMXT_V2_DECIMAL_SPECS["size"][1])
    norm["_canonical"] = canonical
    return norm
