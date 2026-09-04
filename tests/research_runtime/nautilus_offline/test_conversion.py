"""WP168 pmxt-v2 -> Nautilus conversion, provenance, ordering & serialization tests.

Covers R010-R017, R041, R043-R044, R046-R047, R049-R050, R052-R059, R061 (field coverage).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
from decimal import Decimal

import pytest

import pyarrow as pa
import pyarrow.parquet as pq

from src.data_layer.analytical_research import (
    PMXT_V2_DATASET_NAME,
    PMXT_V2_DATASET_VERSION,
    PMXT_V2_PROVIDER_ID,
    PMXT_V2_SOURCE_CLASS,
    ExternalDatasetDescriptor,
    ExternalSourceObject,
    PmxtV2SourceFile,
)

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline.conversion import _scan_public_result_for_echo
from src.research_runtime.nautilus_offline import (
    CONVERSION_ERROR,
    CONVERSION_POLICY_VERSION,
    SOURCE_DATASET_KIND,
    BinaryOptionMappingResult,
    BinaryOptionMarketContext,
    CatalogBuildResult,
    CatalogQueryResult,
    ConvertedEventStream,
    NautilusReplayReceipt,
    NautilusRuntimeCompatibilityResult,
    PmxtV2ReplaySource,
    convert_pmxt_v2_events,
    run_offline_replay,
)

MARKET = "0x" + "a" * 64
TOKEN = "92544998123698303655208967887569360731013655782348975589292031774495159624905"

SCHEMA = pa.schema([
    ("timestamp_received", pa.timestamp("ms", tz="UTC")),
    ("timestamp", pa.timestamp("ms", tz="UTC")),
    ("market", pa.binary(66)),
    ("event_type", pa.string()),
    ("asset_id", pa.string()),
    ("bids", pa.string()),
    ("asks", pa.string()),
    ("price", pa.decimal128(9, 4)),
    ("size", pa.decimal128(18, 6)),
    ("side", pa.string()),
    ("best_bid", pa.decimal128(9, 4)),
    ("best_ask", pa.decimal128(9, 4)),
    ("fee_rate_bps", pa.uint16()),
    ("transaction_hash", pa.string()),
    ("old_tick_size", pa.decimal128(9, 4)),
    ("new_tick_size", pa.decimal128(9, 4)),
])


def _t(ms: int) -> dt.datetime:
    return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(milliseconds=ms)


def row(event_type: str, ts_ms: int, rx_ms: int, **fields) -> dict:
    record = {name: None for name in SCHEMA.names}
    record["timestamp"] = _t(ts_ms)
    record["timestamp_received"] = _t(rx_ms)
    record["market"] = MARKET.encode("ascii")
    record["asset_id"] = TOKEN
    record["event_type"] = event_type
    record.update(fields)
    return record


def book(ts, rx, bids, asks):
    return row("book", ts, rx, bids=json.dumps(bids), asks=json.dumps(asks))


def price_change(ts, rx, price, size, side):
    return row("price_change", ts, rx, price=Decimal(price), size=Decimal(size), side=side,
               best_bid=Decimal("0.4000"), best_ask=Decimal("0.6000"))


def trade(ts, rx, price, size, side, tx):
    return row("last_trade_price", ts, rx, price=Decimal(price), size=Decimal(size), side=side,
               fee_rate_bps=0, transaction_hash=tx)


def tick_change(ts, rx, old, new):
    return row("tick_size_change", ts, rx, old_tick_size=Decimal(old), new_tick_size=Decimal(new))


def default_rows():
    return [
        book(1000, 1005, [["0.4000", "50.000000"]], [["0.6000", "50.000000"]]),
        price_change(1000, 1006, "0.4100", "10.000000", "BUY"),
        trade(1000, 1007, "0.4100", "5.000000", "BUY", "0x" + "d" * 64),
        tick_change(1100, 1101, "0.0100", "0.0010"),
        price_change(1200, 1205, "0.5850", "7.000000", "SELL"),
    ]


def _context(**overrides) -> BinaryOptionMarketContext:
    base = dict(
        condition_id=MARKET, outcome_token_id=TOKEN, outcome_label="Yes",
        description="Will the outcome be Yes?", activation_ns=0,
        expiration_ns=1_800_000_000_000_000_000, price_increment="0.001",
        size_increment="0.000001", maker_fee=None, taker_fee=None,
        ts_event_ns=0, ts_init_ns=0,
    )
    base.update(overrides)
    return BinaryOptionMarketContext(**base)


def _write_files(tmp_path, files_rows, *, corrupt_hash=False, wrong_provider=False,
                 extra_object=False, missing_object=False, duplicate_name=False):
    """Write parquet file(s) and build a matching PmxtV2ReplaySource."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    source_files = []
    objects = []
    for index, rows in enumerate(files_rows):
        name = "part-0.parquet" if duplicate_name else f"part-{index}.parquet"
        path = tmp_path / name
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if corrupt_hash and index == 0:
            digest = "0" * 64
        partition = f"p{index}"
        objects.append(ExternalSourceObject(
            object_name=name, source_sha256=digest, byte_length=path.stat().st_size,
            partition_identity=partition))
        source_files.append(PmxtV2SourceFile(path=str(path), object_name=name, partition_identity=partition))
    if extra_object:
        objects.append(ExternalSourceObject(object_name="part-extra.parquet",
            source_sha256="1" * 64, byte_length=1, partition_identity="pX"))
    if missing_object:
        objects = objects[:-1]
    descriptor = ExternalDatasetDescriptor(
        schema_id="polymarket-external-dataset-descriptor", schema_version="1.0.0",
        external_dataset_id="ext:pmxt:test0001",
        provider_id="other" if wrong_provider else PMXT_V2_PROVIDER_ID,
        dataset_name=PMXT_V2_DATASET_NAME, dataset_version=PMXT_V2_DATASET_VERSION,
        source_class=PMXT_V2_SOURCE_CLASS, coverage_start="2024-01-01T00:00:00Z",
        coverage_end="2024-01-02T00:00:00Z", source_objects=tuple(objects),
        source_schema_fingerprint_sha256="0" * 64,
        source_timestamp_semantics="SOURCE_EVENT_TIME_UTC_MS",
        receive_timestamp_semantics="EXPORTER_RECEIVE_TIME_UTC_MS",
        event_types=("book", "price_change", "last_trade_price", "tick_size_change"),
        known_gap_policy="NONE", quality_tier="representative",
        importer_id="wp167-pmxt-v2-adapter", importer_version="1.0.0",
        license_id="TEST", attribution="test", advisory_only=True, no_execution_authority=True)
    return PmxtV2ReplaySource(descriptor=descriptor, source_files=tuple(source_files))


def valid_stream(tmp_path, rows=None):
    source = _write_files(tmp_path, [rows if rows is not None else default_rows()])
    return convert_pmxt_v2_events(source, _context())


# --------------------------- conversion happy path ---------------------------

def test_book_snapshot_conversion(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas
    from nautilus_trader.model.enums import BookAction, OrderSide
    rows = [book(1000, 1005, [["0.4000", "50.000000"], ["0.3900", "10.000000"]],
                 [["0.6000", "20.000000"]])]
    stream = valid_stream(tmp_path, rows=rows)
    assert stream.is_valid
    assert dict(stream.input_event_counts_by_type)["book"] == 1
    snapshots = [o for o in stream.converted_events if isinstance(o, OrderBookDeltas)]
    assert len(snapshots) == 1                        # exactly one snapshot
    deltas = snapshots[0].deltas
    assert deltas[0].action == BookAction.CLEAR       # CLEAR first
    adds = [d for d in deltas if d.action == BookAction.ADD]
    assert len(adds) == 3                             # 2 bids + 1 ask preserved
    bids = [(str(d.order.price), str(d.order.size)) for d in adds if d.order.side == OrderSide.BUY]
    asks = [(str(d.order.price), str(d.order.size)) for d in adds if d.order.side == OrderSide.SELL]
    assert bids == [("0.400", "50.000000"), ("0.390", "10.000000")]   # descending, sizes preserved
    assert asks == [("0.600", "20.000000")]

    # A book level with size 0 is a DELETE (not ADD); CLEAR still first, order preserved.
    zero_rows = [book(1000, 1005, [["0.4000", "0.000000"], ["0.3900", "10.000000"]],
                      [["0.6000", "20.000000"]])]
    z_stream = valid_stream(tmp_path / "zero", rows=zero_rows)
    z_deltas = next(o for o in z_stream.converted_events if isinstance(o, OrderBookDeltas)).deltas
    assert z_deltas[0].action == BookAction.CLEAR
    non_clear = z_deltas[1:]
    delete_prices = [str(d.order.price) for d in non_clear if d.action == BookAction.DELETE]
    add_prices = [str(d.order.price) for d in non_clear if d.action == BookAction.ADD]
    assert delete_prices == ["0.400"]                 # zero-size bid -> DELETE
    assert add_prices == ["0.390", "0.600"]           # positive levels -> ADD

    # A negative book level fails closed.
    neg_rows = [book(1, 2, [["0.4000", "-1.000000"]], [["0.6000", "1.000000"]])]
    assert valid_stream(tmp_path / "negbook", rows=neg_rows).is_valid is False


def test_price_change_conversion(tmp_path):
    from nautilus_trader.model.data import OrderBookDelta
    from nautilus_trader.model.enums import BookAction, OrderSide
    stream = valid_stream(tmp_path)
    assert dict(stream.input_event_counts_by_type)["price_change"] == 2
    # positive size -> UPDATE with exact side/price/size.
    upd = valid_stream(tmp_path / "u", rows=[price_change(1, 2, "0.4100", "3.000000", "SELL")])
    delta = next(o for o in upd.converted_events if isinstance(o, OrderBookDelta))
    assert delta.action == BookAction.UPDATE
    assert delta.order.side == OrderSide.SELL
    assert str(delta.order.price) == "0.410"
    assert str(delta.order.size) == "3.000000"
    # zero size -> DELETE.
    zero = valid_stream(tmp_path / "z", rows=[price_change(1, 2, "0.4100", "0.000000", "BUY")])
    assert next(o for o in zero.converted_events if isinstance(o, OrderBookDelta)).action == BookAction.DELETE
    # negative size -> fail closed.
    neg = valid_stream(tmp_path / "n", rows=[price_change(1, 2, "0.4100", "-1.000000", "BUY")])
    assert neg.is_valid is False and neg.error_codes == (CONVERSION_ERROR,)


def test_last_trade_price_to_trade_tick(tmp_path):
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.model.enums import AggressorSide
    stream = valid_stream(tmp_path)
    assert dict(stream.input_event_counts_by_type)["last_trade_price"] == 1
    # BUY -> BUYER, exact price/size/timestamps, deterministic nonempty TradeId.
    buy = valid_stream(tmp_path / "buy", rows=[trade(1000, 1007, "0.4100", "5.000000", "BUY", "0x" + "a" * 64)])
    tick = next(o for o in buy.converted_events if isinstance(o, TradeTick))
    assert str(tick.price) == "0.410"
    assert str(tick.size) == "5.000000"
    assert tick.aggressor_side == AggressorSide.BUYER
    assert str(tick.trade_id) != ""
    assert tick.ts_event == 1000 * 1_000_000
    assert tick.ts_init == 1007 * 1_000_000
    # SELL -> SELLER.
    sell = valid_stream(tmp_path / "sell", rows=[trade(1000, 1007, "0.4100", "5.000000", "SELL", "0x" + "b" * 64)])
    assert next(o for o in sell.converted_events if isinstance(o, TradeTick)).aggressor_side == AggressorSide.SELLER
    # Repeat conversion -> same TradeId (deterministic).
    buy2 = valid_stream(tmp_path / "buy2", rows=[trade(1000, 1007, "0.4100", "5.000000", "BUY", "0x" + "a" * 64)])
    assert str(next(o for o in buy2.converted_events if isinstance(o, TradeTick)).trade_id) == str(tick.trade_id)
    # Byte-identical duplicate rows -> deterministic UNIQUE TradeIds (via duplicate ordinal).
    tx = "0x" + "c" * 64
    dup = valid_stream(tmp_path / "dup", rows=[trade(1000, 1000, "0.4100", "5.000000", "BUY", tx)] * 2)
    dup_ids = [str(o.trade_id) for o in dup.converted_events if isinstance(o, TradeTick)]
    assert len(dup_ids) == 2 and dup_ids[0] != dup_ids[1]


def test_event_and_receive_timestamp_mapping(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas
    stream = valid_stream(tmp_path)
    snapshot = next(o for o in stream.converted_events if isinstance(o, OrderBookDeltas))
    first_delta = snapshot.deltas[0]
    assert first_delta.ts_event == 1000 * 1_000_000   # source event time
    assert first_delta.ts_init == 1005 * 1_000_000    # source receive time


def test_invalid_timestamp_value_fails_closed():
    # R027 category 5: an invalid timestamp (timezone-naive datetime, or a wrong-typed value)
    # is a real closed conversion failure, not silently coerced to a wall-clock or zero.
    import datetime as _dt
    from src.research_runtime.nautilus_offline.conversion import _as_ns, _ConversionError

    # A valid tz-aware datetime and integer-ms both normalize to exact nanoseconds.
    aware = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc) + _dt.timedelta(milliseconds=1500)
    assert _as_ns(aware) == 1500 * 1_000_000
    assert _as_ns(1500) == 1500 * 1_000_000

    # Timezone-naive datetime, string, float, bool, and None all fail closed.
    for bad in (_dt.datetime(1970, 1, 1, 0, 0, 1), "1500", 1500.0, True, None):
        with pytest.raises(_ConversionError):
            _as_ns(bad)


def test_decimal_to_price_quantity_is_exact_no_float(tmp_path):
    # R014: Price/Quantity are integer-backed fixed-point (no binary float), for both book
    # deltas and trades, at Nautilus FIXED_PRECISION. FIXED_PRECISION is a build-dependent
    # constant (9 on standard-precision wheels, 16 on high-precision), so the invariant is the
    # exact integer-backed scaling, not a hard-coded 9.
    from nautilus_trader.model.data import OrderBookDeltas, TradeTick
    from nautilus_trader.model.objects import FIXED_PRECISION, Price, Quantity
    assert isinstance(FIXED_PRECISION, int) and FIXED_PRECISION >= 9

    stream = valid_stream(tmp_path)
    tick = next(o for o in stream.converted_events if isinstance(o, TradeTick))
    assert str(tick.price) == "0.410"
    # Trade price/size are Nautilus Price/Quantity, integer-backed, exact, not Python floats.
    assert isinstance(tick.price, Price) and isinstance(tick.size, Quantity)
    assert isinstance(tick.price.raw, int) and isinstance(tick.size.raw, int)
    # 0.410 is stored exactly as an integer at the build's fixed precision (no binary float).
    assert tick.price.raw == 410 * 10 ** (FIXED_PRECISION - 3)
    assert tick.price == Price.from_str("0.410")

    # Book delta prices/sizes are likewise integer-backed Price/Quantity.
    snapshot = next(o for o in stream.converted_events if isinstance(o, OrderBookDeltas))
    add = next(d for d in snapshot.deltas if d.order.size.raw > 0)
    assert isinstance(add.order.price, Price) and isinstance(add.order.size, Quantity)
    assert isinstance(add.order.price.raw, int) and isinstance(add.order.size.raw, int)

    # Representative 9-decimal fixed-point values are exact/lossless (the frozen "within
    # FIXED_PRECISION 9" requirement). `>= 9` proves it on high-precision (16) wheels too.
    for text in ("0.123456789", "0.000000001", "0.999999999"):
        p = Price.from_str(text)
        q = Quantity.from_str(text)
        assert str(p) == text and str(q) == text                       # round-trip unchanged
        assert p == Price.from_str(text) and q == Quantity.from_str(text)
        assert isinstance(p.raw, int) and isinstance(q.raw, int)       # no binary float
        # integer scaling at the actual build precision, exact for 9 fractional digits.
        assert p.raw == int(Decimal(text) * (10 ** FIXED_PRECISION))
        assert Decimal(str(p)) == Decimal(text)


def test_tick_size_change_committed_as_regime_metadata(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas, OrderBookDelta, TradeTick
    from nautilus_trader.model.instruments import BinaryOption
    stream = valid_stream(tmp_path)
    assert stream.tick_size_regime_sequence == (("0.0100", "0.0010", 1100 * 1_000_000),)
    assert stream.source_dataset_kind == SOURCE_DATASET_KIND
    assert stream.conversion_policy_version == CONVERSION_POLICY_VERSION

    # A tick_size_change is regime metadata ONLY: it produces no market-data event, keeps the
    # single instrument identity, and is excluded from the semantic replay-event count.
    tick_only = valid_stream(tmp_path / "tickonly", rows=[
        tick_change(1100, 1101, "0.0100", "0.0010"),
        tick_change(1300, 1301, "0.0010", "0.0005")])
    assert tick_only.is_valid
    instruments = [o for o in tick_only.converted_events if isinstance(o, BinaryOption)]
    market_data = [o for o in tick_only.converted_events
                   if isinstance(o, (OrderBookDeltas, OrderBookDelta, TradeTick))]
    assert len(instruments) == 1
    assert market_data == []
    assert tick_only.tick_size_regime_sequence == (
        ("0.0100", "0.0010", 1100 * 1_000_000), ("0.0010", "0.0005", 1300 * 1_000_000))
    # No replayable (book/price_change/last_trade_price) event is counted for tick metadata.
    replayable = {"book", "price_change", "last_trade_price"}
    counts = dict(tick_only.input_event_counts_by_type)
    assert sum(v for k, v in counts.items() if k in replayable) == 0

    # A nonpositive tick size fails closed.
    assert valid_stream(tmp_path / "zt", rows=[tick_change(1, 2, "0.0000", "0.0010")]).is_valid is False
    assert valid_stream(tmp_path / "nt", rows=[tick_change(1, 2, "0.0100", "-0.0010")]).is_valid is False


def test_all_prices_are_exact_multiples_of_finest_increment(tmp_path):
    # Every validated historical price FIELD must be an exact multiple of the finest increment
    # (0.001): the traded price, best_bid, best_ask, book bid/ask prices, and the trade price.
    def pc(price, best_bid, best_ask):
        return row("price_change", 1, 2, price=Decimal(price), size=Decimal("1.000000"),
                   side="BUY", best_bid=Decimal(best_bid), best_ask=Decimal(best_ask))

    assert valid_stream(tmp_path / "ok", rows=[pc("0.5850", "0.4000", "0.6000")]).is_valid
    assert valid_stream(tmp_path / "p", rows=[pc("0.5855", "0.4000", "0.6000")]).is_valid is False   # price
    assert valid_stream(tmp_path / "bb", rows=[pc("0.5850", "0.4005", "0.6000")]).is_valid is False  # best_bid
    assert valid_stream(tmp_path / "ba", rows=[pc("0.5850", "0.4000", "0.6005")]).is_valid is False  # best_ask
    # book bid / ask prices.
    assert valid_stream(tmp_path / "bkb",
        rows=[book(1, 2, [["0.4005", "1.000000"]], [["0.6000", "1.000000"]])]).is_valid is False
    assert valid_stream(tmp_path / "bka",
        rows=[book(1, 2, [["0.4000", "1.000000"]], [["0.6005", "1.000000"]])]).is_valid is False
    # trade price.
    bad_trade = valid_stream(tmp_path / "tr",
        rows=[trade(1, 2, "0.4005", "1.000000", "BUY", "0x" + "a" * 64)])
    assert bad_trade.is_valid is False and bad_trade.error_codes == (CONVERSION_ERROR,)


# --------------------------- ordering / duplicates ---------------------------

def test_receive_time_primary_ordering_when_event_time_disagrees(tmp_path):
    # Event A: ts_event=2000, ts_init=1000. Event B: ts_event=1000, ts_init=2000.
    # Receive-time-primary => A (ts_init 1000) before B (ts_init 2000). A book snapshot at an
    # earlier receive time lets the offline engine replay so engine dispatch is also proven.
    rows = [
        book(400, 500, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
        trade(2000, 1000, "0.4000", "1.000000", "BUY", "0x" + "a" * 64),
        trade(1000, 2000, "0.4000", "1.000000", "BUY", "0x" + "b" * 64),
    ]
    stream = valid_stream(tmp_path / "src", rows=rows)
    from nautilus_trader.model.data import TradeTick
    ticks = [o for o in stream.converted_events if isinstance(o, TradeTick)]
    # 1. converted canonical order follows ts_init.
    assert [t.ts_init for t in ticks] == [1000 * 1_000_000, 2000 * 1_000_000]
    # 2/3. the BacktestEngine dispatches in the declared ts_init order (a valid receipt means
    # the engine-observed per-event trace equals the ts_init-primary canonical order).
    receipt = run_offline_replay(stream, tmp_path / "replay")
    assert receipt.is_valid
    assert receipt.replay_processed_event_count == 3


def _assert_four_kind_equal_ts_tie_order(tmp_path):
    """R015/R046 shared proof: all four event kinds at equal ts_init AND equal ts_event are
    ordered by the frozen total key, which here reduces to event_kind_rank
    book(0) < price_change(1) < last_trade_price(2) < tick_size_change(3), independent of
    physical input order."""
    from nautilus_trader.model.data import OrderBookDeltas, OrderBookDelta, TradeTick
    bk = book(1000, 1000, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]])
    pc = price_change(1000, 1000, "0.4000", "1.000000", "BUY")
    tr = trade(1000, 1000, "0.4000", "1.000000", "BUY", "0x" + "c" * 64)
    tk = tick_change(1000, 1000, "0.0100", "0.0010")

    def base_digest(single_row):
        st = valid_stream(tmp_path / f"one{single_row['event_type']}", rows=[single_row])
        assert st.is_valid and len(st.ordered_event_digests) == 1
        return st.ordered_event_digests[0].rsplit(":", 1)[0]

    expected = [base_digest(bk), base_digest(pc), base_digest(tr), base_digest(tk)]

    # Feed the four events scrambled/reversed relative to rank order.
    scrambled = valid_stream(tmp_path / "mixed", rows=[tk, tr, pc, bk])
    reversed_in = valid_stream(tmp_path / "mixed2", rows=[bk, pc, tr, tk])
    assert scrambled.is_valid and reversed_in.is_valid
    got = [d.rsplit(":", 1)[0] for d in scrambled.ordered_event_digests]
    assert got == expected  # book(0) < price_change(1) < last_trade_price(2) < tick_size_change(3)
    # Physical input order does not change the canonical ordering.
    assert scrambled.ordered_event_digests == reversed_in.ordered_event_digests
    # The three market-data objects also appear in book < price_change < trade order.
    md_kinds = [type(o).__name__ for o in scrambled.converted_events
                if isinstance(o, (OrderBookDeltas, OrderBookDelta, TradeTick))]
    assert md_kinds == ["OrderBookDeltas", "OrderBookDelta", "TradeTick"]


def test_equal_ts_init_events_have_deterministic_tie_order(tmp_path):
    # R015: distinct events with identical ts_init/ts_event are ordered deterministically by the
    # frozen total key (event_kind_rank book<price_change<last_trade_price<tick_size_change).
    _assert_four_kind_equal_ts_tie_order(tmp_path)


def test_event_kind_rank_orders_equal_ts_init_mixed_types(tmp_path):
    # R046: equal ts_init AND equal ts_event across all four event kinds are ordered by the
    # frozen event_kind_rank, independent of physical input order.
    _assert_four_kind_equal_ts_tie_order(tmp_path)


def test_input_enumeration_order_invariance(tmp_path):
    # R041: physical input enumeration order does not affect the canonical event digests OR the
    # replay identity.
    rows = default_rows()
    forward = valid_stream(tmp_path / "a", rows=list(rows))
    backward = valid_stream(tmp_path / "b", rows=list(reversed(rows)))
    assert forward.ordered_event_digests == backward.ordered_event_digests
    # Replay identity is likewise enumeration-order invariant.
    r_fwd = run_offline_replay(forward, tmp_path / "cf")
    r_bwd = run_offline_replay(backward, tmp_path / "cb")
    assert r_fwd.is_valid and r_bwd.is_valid
    assert r_fwd.replay_digest == r_bwd.replay_digest
    assert r_fwd == r_bwd  # full receipt identical (physical path excluded from identity)


def test_two_byte_identical_duplicates_retain_multiplicity_two(tmp_path):
    tx = "0x" + "e" * 64
    rows = [trade(1000, 1000, "0.4000", "1.000000", "BUY", tx),
            trade(1000, 1000, "0.4000", "1.000000", "BUY", tx)]
    stream = valid_stream(tmp_path, rows=rows)
    digests = stream.ordered_event_digests
    assert len(digests) == 2
    base = digests[0].rsplit(":", 1)[0]
    assert digests == (f"{base}:0", f"{base}:1")


def test_three_byte_identical_duplicates_retain_multiplicity_three(tmp_path):
    tx = "0x" + "f" * 64
    rows = [trade(1000, 1000, "0.4000", "1.000000", "BUY", tx) for _ in range(3)]
    stream = valid_stream(tmp_path, rows=rows)
    ordinals = [d.rsplit(":", 1)[1] for d in stream.ordered_event_digests]
    assert ordinals == ["0", "1", "2"]


def test_equal_timestamp_same_kind_orders_by_canonical_row_bytes(tmp_path):
    # R047: same ts_init + same ts_event + same kind + different content are ordered by
    # (canonical_row_digest, canonical_row_bytes). Independently recompute the tie key from the
    # frozen normalization helpers and prove the stream matches that exact order.
    from nautilus_trader.model.data import TradeTick
    from src.research_runtime.nautilus_offline.conversion import (
        _validate_and_normalize_row, _canonical_json_bytes)

    raw = [
        trade(1000, 1000, "0.5000", "1.000000", "BUY", "0x" + "2" * 64),
        trade(1000, 1000, "0.4000", "1.000000", "BUY", "0x" + "1" * 64),
    ]
    # 1-3. independently normalize each row, obtain canonical bytes + digest.
    computed = []
    for r in raw:
        canonical = _validate_and_normalize_row(r, MARKET, TOKEN)["_canonical"]
        row_bytes = _canonical_json_bytes(canonical)
        digest = hashlib.sha256(row_bytes).hexdigest()
        computed.append((digest, row_bytes, canonical["price"]))
    # 4. ts_init/ts_event/kind are all tied -> the total key reduces to (digest, bytes).
    expected = sorted(computed, key=lambda c: (c[0], c[1]))
    expected_digests = [c[0] for c in expected]
    expected_prices = [c[2] for c in expected]

    stream = valid_stream(tmp_path, rows=raw)
    # 5. stream ordered digest bases appear in the exact independently-computed order.
    got_digests = [d.rsplit(":", 1)[0] for d in stream.ordered_event_digests]
    assert got_digests == expected_digests
    # 6. converted TradeTick prices correspond to the same expected row order (numeric equality,
    #    display precision differs from the canonical decimal scale).
    got_prices = [Decimal(str(o.price)) for o in stream.converted_events if isinstance(o, TradeTick)]
    assert got_prices == [Decimal(p) for p in expected_prices]
    # 7. reversing physical input yields the identical canonical order.
    again = valid_stream(tmp_path / "again", rows=list(reversed(raw)))
    assert [d.rsplit(":", 1)[0] for d in again.ordered_event_digests] == expected_digests
    assert stream.ordered_event_digests == again.ordered_event_digests


# --------------------------- provenance / semantics --------------------------

def test_descriptor_provider_version_source_class_mismatch_rejected(tmp_path):
    source = _write_files(tmp_path, [default_rows()])
    desc = source.descriptor
    # Independently mutate each of the four provenance fields -> fail closed.
    for bad in (
        dataclasses.replace(desc, provider_id="not-pmxt"),
        dataclasses.replace(desc, dataset_name="some_other_archive"),
        dataclasses.replace(desc, dataset_version="v1"),
        dataclasses.replace(desc, source_class="NATIVE_OFFICIAL_CAPTURE"),
    ):
        bad_source = PmxtV2ReplaySource(descriptor=bad, source_files=source.source_files)
        result = convert_pmxt_v2_events(bad_source, _context())
        assert result.is_valid is False
        assert result.error_codes == (CONVERSION_ERROR,)
    # exact provider/dataset/version/source_class passes.
    assert convert_pmxt_v2_events(source, _context()).is_valid is True


def test_descriptor_importer_and_timestamp_semantics_mismatch_rejected(tmp_path):
    source = _write_files(tmp_path, [default_rows()])
    desc = source.descriptor
    for bad in (
        dataclasses.replace(desc, importer_id="not-the-wp167-adapter"),
        dataclasses.replace(desc, importer_version="9.9.9"),
        dataclasses.replace(desc, source_timestamp_semantics="WRONG_EVENT_SEMANTICS"),
        dataclasses.replace(desc, receive_timestamp_semantics="WRONG_RECEIVE_SEMANTICS"),
    ):
        bad_source = PmxtV2ReplaySource(descriptor=bad, source_files=source.source_files)
        result = convert_pmxt_v2_events(bad_source, _context())
        assert result.is_valid is False
        assert result.error_codes == (CONVERSION_ERROR,)
        assert _scan_public_result_for_echo(result, ("Traceback", "\\", str(tmp_path))) == ()
    # exact WP167 importer/timestamp semantics pass.
    assert convert_pmxt_v2_events(source, _context()).is_valid is True


def test_book_source_event_becomes_one_orderbookdeltas_snapshot(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas
    from nautilus_trader.model.enums import BookAction
    rows = [book(1, 2, [["0.4000", "1.000000"], ["0.3000", "2.000000"]],
                 [["0.6000", "1.000000"]])]
    stream = valid_stream(tmp_path, rows=rows)
    assert stream.is_valid
    snapshots = [o for o in stream.converted_events if isinstance(o, OrderBookDeltas)]
    assert len(snapshots) == 1  # one source book event -> exactly one snapshot
    deltas = snapshots[0].deltas
    assert deltas[0].action == BookAction.CLEAR
    adds = [d for d in deltas if d.action == BookAction.ADD]
    assert len(adds) == 3  # 2 bids + 1 ask


def test_book_snapshot_tied_with_other_event_orders_deterministically(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas, TradeTick
    # book (rank 0) and a trade (rank 2) at the same ts_init/ts_event.
    rows = [
        trade(1000, 1000, "0.4000", "1.000000", "BUY", "0x" + "7" * 64),
        book(1000, 1000, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
    ]
    stream = valid_stream(tmp_path, rows=rows)
    kinds = [type(o).__name__ for o in stream.converted_events
             if isinstance(o, (OrderBookDeltas, TradeTick))]
    assert kinds == ["OrderBookDeltas", "TradeTick"]  # book rank 0 before trade rank 2


def test_source_files_map_one_to_one_to_descriptor_objects(tmp_path):
    # extra descriptor object with no matching source file -> reject.
    extra = _write_files(tmp_path / "extra", [default_rows()], extra_object=True)
    assert convert_pmxt_v2_events(extra, _context()).is_valid is False
    # missing descriptor object for a supplied source file -> reject.
    missing = _write_files(tmp_path / "missing", [default_rows(), default_rows()], missing_object=True)
    assert convert_pmxt_v2_events(missing, _context()).is_valid is False
    # duplicate object_name -> reject.
    dup = _write_files(tmp_path / "dup", [default_rows(), default_rows()], duplicate_name=True)
    assert convert_pmxt_v2_events(dup, _context()).is_valid is False
    # matching object_name but wrong partition_identity -> reject (name AND partition bijection).
    good = _write_files(tmp_path / "wrongpart", [default_rows()])
    bad_file = dataclasses.replace(good.source_files[0], partition_identity="pDIFFERENT")
    wrong_partition = PmxtV2ReplaySource(descriptor=good.descriptor, source_files=(bad_file,))
    assert convert_pmxt_v2_events(wrong_partition, _context()).is_valid is False
    # valid strict bijection passes.
    assert convert_pmxt_v2_events(good, _context()).is_valid is True


def test_source_hash_revalidation_failure_fails_closed(tmp_path):
    source = _write_files(tmp_path, [default_rows()], corrupt_hash=True)
    stream = convert_pmxt_v2_events(source, _context())
    assert stream.is_valid is False
    assert stream.error_codes == (CONVERSION_ERROR,)
    assert _scan_public_result_for_echo(stream, ("Traceback", "\\", str(tmp_path))) == ()


# schema-valid non-null sample for every event-specific field (used to populate an unowned
# field, which must fail closed, and to build valid base rows).
_FIELD_SAMPLES = {
    "bids": json.dumps([["0.4000", "1.000000"]]),
    "asks": json.dumps([["0.6000", "1.000000"]]),
    "price": Decimal("0.4000"),
    "size": Decimal("1.000000"),
    "side": "BUY",
    "best_bid": Decimal("0.4000"),
    "best_ask": Decimal("0.6000"),
    "fee_rate_bps": 0,
    "transaction_hash": "0x" + "a" * 64,
    "old_tick_size": Decimal("0.0100"),
    "new_tick_size": Decimal("0.0010"),
}
_OWNED_BY_EVENT = {
    "book": ("bids", "asks"),
    "price_change": ("price", "size", "side", "best_bid", "best_ask"),
    "last_trade_price": ("price", "size", "side", "fee_rate_bps", "transaction_hash"),
    "tick_size_change": ("old_tick_size", "new_tick_size"),
}
_ALL_EVENT_SPECIFIC = tuple(_FIELD_SAMPLES)


def _base_row(event_type):
    return row(event_type, 1, 2, **{f: _FIELD_SAMPLES[f] for f in _OWNED_BY_EVENT[event_type]})


def _assert_event_semantic_matrix(tmp_path):
    """R058: for every event type, each owned field is required non-null, each unowned
    event-specific field must be null, invalid sides fail, and the canonical form carries the
    COMPLETE event-specific key set with every unowned field serialized as explicit None."""
    from src.research_runtime.nautilus_offline.conversion import _validate_and_normalize_row

    for event_type, owned in _OWNED_BY_EVENT.items():
        # (A) every owned field individually null -> exact CONVERSION_ERROR + no echo.
        for field_name in owned:
            bad = _base_row(event_type)
            bad[field_name] = None
            res = valid_stream(tmp_path / f"own_{event_type}_{field_name}", rows=[bad])
            assert res.is_valid is False, (event_type, field_name)
            assert res.error_codes == (CONVERSION_ERROR,), (event_type, field_name)
            assert _scan_public_result_for_echo(res, ("Traceback", "\\")) == ()
        # (B) every unowned event-specific field populated -> exact CONVERSION_ERROR + no echo.
        for field_name in _ALL_EVENT_SPECIFIC:
            if field_name in owned:
                continue
            bad = _base_row(event_type)
            bad[field_name] = _FIELD_SAMPLES[field_name]
            res = valid_stream(tmp_path / f"unown_{event_type}_{field_name}", rows=[bad])
            assert res.is_valid is False, (event_type, field_name)
            assert res.error_codes == (CONVERSION_ERROR,), (event_type, field_name)
            assert _scan_public_result_for_echo(res, ("Traceback", "\\")) == ()
        # (C) side-owning event types: invalid side token -> exact CONVERSION_ERROR.
        if "side" in owned:
            bad = _base_row(event_type)
            bad["side"] = "HODL"
            res = valid_stream(tmp_path / f"side_{event_type}", rows=[bad])
            assert res.is_valid is False and res.error_codes == (CONVERSION_ERROR,)
        # (E) valid base row: canonical form has the complete key set; unowned fields are None.
        norm = _validate_and_normalize_row(_base_row(event_type), MARKET, TOKEN)
        canonical = norm["_canonical"]
        for field_name in _ALL_EVENT_SPECIFIC:
            assert field_name in canonical, (event_type, field_name)
            if field_name in owned:
                assert canonical[field_name] is not None, (event_type, field_name)
            else:
                assert canonical[field_name] is None, (event_type, field_name)  # explicit null
        # canonical JSON therefore serializes the unowned keys as literal null.
        from src.research_runtime.nautilus_offline.conversion import _canonical_json_bytes
        text = _canonical_json_bytes(canonical).decode("utf-8")
        for field_name in _ALL_EVENT_SPECIFIC:
            if field_name not in owned:
                assert f'"{field_name}":null' in text, (event_type, field_name)
        # (Defect A trap #5) an omitted-field object is NOT byte-equivalent to the correct
        # explicit-null canonical object: absence and explicit null must never be conflated.
        unowned_present = [f for f in _ALL_EVENT_SPECIFIC if f not in owned]
        if unowned_present:
            omitted = {k: v for k, v in canonical.items() if k != unowned_present[0]}
            assert _canonical_json_bytes(omitted) != _canonical_json_bytes(canonical)

    # (F) tick sizes <= 0 remain rejected.
    for bad_val in ("0.0000", "-0.0010"):
        bad = _base_row("tick_size_change")
        bad["new_tick_size"] = Decimal(bad_val)
        assert valid_stream(tmp_path / f"tick{bad_val}", rows=[bad]).is_valid is False


def test_event_semantic_matrix_owned_and_null_fields(tmp_path):
    _assert_event_semantic_matrix(tmp_path)


def test_unsupported_pmxt_event_and_malformed_book_rejected(tmp_path):
    bad_event = row("weird_event", 1, 2)
    unsupported = valid_stream(tmp_path / "a", rows=[bad_event])
    assert unsupported.is_valid is False
    assert unsupported.error_codes == (CONVERSION_ERROR,)  # exactly NAUTILUS_EVENT_CONVERSION_INVALID
    # No raw event token / exception / traceback echoed in the closed result.
    assert _scan_public_result_for_echo(unsupported, ("weird_event", "Traceback", "Error")) == ()

    malformed = book(1, 2, [["0.4000"]], [["0.6000", "1.000000"]])  # bid pair has 1 item
    bad_book = valid_stream(tmp_path / "b", rows=[malformed])
    assert bad_book.is_valid is False
    assert bad_book.error_codes == (CONVERSION_ERROR,)
    assert _scan_public_result_for_echo(bad_book, ("Traceback", "0.4000")) == ()


def test_book_json_shape_and_canonical_ordering(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas
    from nautilus_trader.model.enums import BookAction, OrderSide
    rows = [book(1, 2, [["0.3000", "1.000000"], ["0.4000", "2.000000"]],
                 [["0.7000", "1.000000"], ["0.6000", "2.000000"]])]
    stream = valid_stream(tmp_path / "ok", rows=rows)
    assert stream.is_valid
    snapshot = next(o for o in stream.converted_events if isinstance(o, OrderBookDeltas))
    adds = [d for d in snapshot.deltas if d.action == BookAction.ADD]
    bid_prices = [str(d.order.price) for d in adds if d.order.side == OrderSide.BUY]
    ask_prices = [str(d.order.price) for d in adds if d.order.side == OrderSide.SELL]
    assert bid_prices == ["0.400", "0.300"]   # descending
    assert ask_prices == ["0.600", "0.700"]   # ascending
    # duplicate price on one side -> fail closed
    dup = [book(1, 2, [["0.4000", "1.000000"], ["0.4000", "2.000000"]], [["0.6000", "1.000000"]])]
    assert valid_stream(tmp_path / "dup", rows=dup).is_valid is False
    # numeric JSON value where a string is required -> fail closed.
    numeric = [book(1, 2, [[0.4, "1.000000"]], [["0.6000", "1.000000"]])]
    assert valid_stream(tmp_path / "num", rows=numeric).is_valid is False
    # non-2-item pair -> fail closed.
    triple = [book(1, 2, [["0.4000", "1.000000", "x"]], [["0.6000", "1.000000"]])]
    assert valid_stream(tmp_path / "tri", rows=triple).is_valid is False
    # non-exact decimal (too many places for the documented scale) -> fail closed.
    inexact = [book(1, 2, [["0.40005", "1.000000"]], [["0.6000", "1.000000"]])]
    assert valid_stream(tmp_path / "inx", rows=inexact).is_valid is False
    # malformed JSON string -> fail closed.
    malformed = [row("book", 1, 2, bids="not json", asks=json.dumps([["0.6000", "1.000000"]]))]
    assert valid_stream(tmp_path / "mal", rows=malformed).is_valid is False
    # Non-fixed-point book price/size strings fail closed: scientific notation, leading '+',
    # surrounding whitespace, NaN/Infinity, and non-ASCII (Unicode) digits.
    for i, bad in enumerate(("4e-1", "4E-1", "+0.4000", " 0.4000", "0.4000 ", "NaN",
                             "Infinity", "０.4000", "0.4０００")):
        bad_price = [book(1, 2, [[bad, "1.000000"]], [["0.6000", "1.000000"]])]
        assert valid_stream(tmp_path / f"bp{i}", rows=bad_price).is_valid is False
        bad_size = [book(1, 2, [["0.4000", bad]], [["0.6000", "1.000000"]])]
        assert valid_stream(tmp_path / f"bs{i}", rows=bad_size).is_valid is False


# --------------------------- field coverage (R061) ---------------------------

def _assert_public_dataclass_field_classification_complete():
    # Shared R026/R061 proof: every public dataclass field carries an explicit output-handling
    # classification (SCANNED / EXEMPT / OPAQUE_EXCLUDED) AND an explicit identity role
    # (COMMITTED / EXCLUDED / NONE). A future unclassified field fails the coverage gate.
    S, E, X = "SCANNED", "EXEMPT", "OPAQUE_EXCLUDED"
    classification = {
        NautilusRuntimeCompatibilityResult: {
            "is_valid": E, "status": S, "error_codes": S, "nautilus_version": S,
            "python_version": S, "advisory_only": E, "no_execution_authority": E},
        BinaryOptionMarketContext: {
            "condition_id": S, "outcome_token_id": S, "outcome_label": S, "description": S,
            "activation_ns": S, "expiration_ns": S, "price_increment": S, "size_increment": S,
            "maker_fee": S, "taker_fee": S, "ts_event_ns": S, "ts_init_ns": S},
        BinaryOptionMappingResult: {
            "is_valid": E, "status": S, "error_codes": S, "instrument_id": S,
            "price_increment": S, "size_increment": S, "warnings": S, "binary_option": X},
        PmxtV2ReplaySource: {"descriptor": X, "source_files": X},
        ConvertedEventStream: {
            "is_valid": E, "status": S, "error_codes": S, "instrument_id": S,
            "source_dataset_kind": S, "source_external_dataset_id": S,
            "conversion_policy_version": S, "ordered_event_digests": S,
            "input_event_counts_by_type": S, "tick_size_regime_sequence": S,
            "first_event_time_ns": S, "last_event_time_ns": S, "warnings": S,
            "converted_events": X},
        CatalogBuildResult: {
            "is_valid": E, "status": S, "error_codes": S, "instrument_registered": S,
            "written_delta_count": S, "written_trade_count": S, "catalog_dir": X,
            "stream_ref_digest": S},
        CatalogQueryResult: {
            "is_valid": E, "status": S, "error_codes": S, "queried_delta_count": S,
            "queried_trade_count": S, "round_trip_matches": S},
        NautilusReplayReceipt: {
            "is_valid": E, "status": S, "error_codes": S, "schema_id": S, "schema_version": S,
            "source_dataset_kind": S, "source_external_dataset_id": S,
            "conversion_policy_version": S, "nautilus_version": S, "instrument_id": S,
            "input_event_counts_by_type": S, "first_event_time_ns": S, "last_event_time_ns": S,
            "tick_size_regime_sequence": S, "replay_processed_event_count": S,
            "replay_digest": S, "warnings": S, "execution_authority": E},
    }

    def _coverage_ok(cls, table) -> bool:
        return {f.name for f in dataclasses.fields(cls)} == set(table)

    for cls, table in classification.items():
        assert dataclasses.is_dataclass(cls)
        assert _coverage_ok(cls, table), cls.__name__
        assert set(table.values()) <= {S, E, X}

    # Second, orthogonal dimension: each field's role in the committed replay identity.
    # C = committed into the identity preimage; XI = deliberately excluded; N = not an
    # identity input at all (control/echo/input field).
    C, XI, N = "COMMITTED", "EXCLUDED", "NONE"
    identity_role = {
        NautilusRuntimeCompatibilityResult: {k: N for k in classification[NautilusRuntimeCompatibilityResult]},
        BinaryOptionMarketContext: {k: N for k in classification[BinaryOptionMarketContext]},
        BinaryOptionMappingResult: {
            "is_valid": N, "status": N, "error_codes": N, "instrument_id": N,
            "price_increment": N, "size_increment": N, "warnings": N, "binary_option": XI},
        PmxtV2ReplaySource: {"descriptor": XI, "source_files": XI},
        ConvertedEventStream: {
            "is_valid": N, "status": N, "error_codes": N, "instrument_id": C,
            "source_dataset_kind": C, "source_external_dataset_id": C,
            "conversion_policy_version": C, "ordered_event_digests": C,
            "input_event_counts_by_type": C, "tick_size_regime_sequence": C,
            "first_event_time_ns": C, "last_event_time_ns": C, "warnings": N,
            "converted_events": XI},
        CatalogBuildResult: {
            "is_valid": N, "status": N, "error_codes": N, "instrument_registered": N,
            "written_delta_count": N, "written_trade_count": N, "catalog_dir": XI,
            "stream_ref_digest": C},
        CatalogQueryResult: {k: N for k in classification[CatalogQueryResult]},
        NautilusReplayReceipt: {
            "is_valid": N, "status": N, "error_codes": N, "schema_id": C, "schema_version": C,
            "source_dataset_kind": C, "source_external_dataset_id": C,
            "conversion_policy_version": C, "nautilus_version": C, "instrument_id": C,
            "input_event_counts_by_type": C, "first_event_time_ns": C, "last_event_time_ns": C,
            "tick_size_regime_sequence": C, "replay_processed_event_count": C,
            "replay_digest": C, "warnings": N, "execution_authority": N},
    }
    for cls, table in identity_role.items():
        assert _coverage_ok(cls, table), cls.__name__
        assert set(table.values()) <= {C, XI, N}
    # Anchor roles: the digest is committed; opaque payloads and caller paths are excluded;
    # control/exempt fields are never an identity input.
    assert identity_role[NautilusReplayReceipt]["replay_digest"] == C
    assert identity_role[ConvertedEventStream]["converted_events"] == XI
    assert identity_role[CatalogBuildResult]["catalog_dir"] == XI
    assert identity_role[NautilusReplayReceipt]["status"] == N
    assert identity_role[NautilusReplayReceipt]["execution_authority"] == N

    # A synthetic dataclass with a new, unclassified field must fail the same coverage gate.
    @dataclasses.dataclass(frozen=True)
    class _Synthetic:
        is_valid: bool
        new_unclassified_field: int

    assert _coverage_ok(_Synthetic, {"is_valid": E}) is False


def test_every_public_dataclass_field_is_classified():
    # R061: exact field classification coverage + identity role + synthetic-field failure.
    _assert_public_dataclass_field_classification_complete()


def test_converted_stream_source_external_dataset_id(tmp_path):
    stream = valid_stream(tmp_path)
    assert stream.source_external_dataset_id == "ext:pmxt:test0001"


def _rows_with_market(market_bytes):
    r = [book(1000, 1005, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
         price_change(1000, 1006, "0.4100", "1.000000", "BUY"),
         trade(1000, 1007, "0.4100", "1.000000", "BUY", "0x" + "d" * 64)]
    for rec in r:
        rec["market"] = market_bytes
    return r


def test_wp167_source_market_case_normalizes_to_lowercase(tmp_path):
    # R063 / Defect B: the WP167 source-row market accepts WP167-valid ASCII hex in either case
    # and canonicalizes the 64-hex body to lowercase; lowercase/uppercase/mixed representations
    # of the same semantic row produce identical canonical market, event digests, canonical
    # ordering, and replay identity. The context condition_id stays strict lowercase.
    from src.research_runtime.nautilus_offline import build_binary_option
    from src.research_runtime.nautilus_offline.conversion import (
        _normalize_market, _ConversionError)

    lower_market = "0x" + "a" * 64
    # unit: accept upper/mixed/lower, always canonicalize to lowercase (bytes and str).
    assert _normalize_market(("0x" + "A" * 64).encode("ascii")) == lower_market
    assert _normalize_market("0x" + "aA" * 32) == lower_market
    assert _normalize_market(("0x" + "a" * 64).encode("ascii")) == lower_market
    # unit: invalid variants fail closed.
    for bad in ("0x" + "g" * 64, "0x" + "G" * 64, "1x" + "a" * 64,
                "0x" + "a" * 63, "0x" + "a" * 65, "0x" + "ａ" * 64):
        with pytest.raises(_ConversionError):
            _normalize_market(bad)
    with pytest.raises(_ConversionError):            # non-ASCII bytes fail the strict decode
        _normalize_market(b"0x" + b"\xff" * 64)

    # integration: three case variants of the SAME semantic rows are semantically identical.
    lower = valid_stream(tmp_path / "lo", rows=_rows_with_market(("0x" + "a" * 64).encode("ascii")))
    upper = valid_stream(tmp_path / "up", rows=_rows_with_market(("0x" + "A" * 64).encode("ascii")))
    mixed = valid_stream(tmp_path / "mx", rows=_rows_with_market(("0x" + "aA" * 32).encode("ascii")))
    for s in (lower, upper, mixed):
        assert s.is_valid
        assert s.instrument_id == f"{lower_market}-{TOKEN}.POLYMARKET"   # canonical lowercase
    assert lower.ordered_event_digests == upper.ordered_event_digests == mixed.ordered_event_digests

    # replay identity is identical across the case variants (engine dispatch).
    rl = run_offline_replay(lower, tmp_path / "cl")
    ru = run_offline_replay(upper, tmp_path / "cu")
    rm = run_offline_replay(mixed, tmp_path / "cm")
    assert rl.is_valid and ru.is_valid and rm.is_valid
    assert rl.replay_digest == ru.replay_digest == rm.replay_digest

    # context condition_id remains a strict lowercase boundary (alternate case rejected).
    assert build_binary_option(_context(condition_id="0x" + "A" * 64)).is_valid is False
    assert build_binary_option(_context(condition_id="0x" + "aA" * 32)).is_valid is False


def test_distinct_trades_same_tx_time_have_distinct_trade_ids(tmp_path):
    # R047/Defect C (conversion level): two last_trade_price rows sharing transaction_hash,
    # ts_event, ts_init and side but differing in price/size are distinct canonical rows (each
    # duplicate ordinal 0); their canonical digests AND engine-facing TradeIds must be distinct.
    from nautilus_trader.model.data import TradeTick
    tx = "0x" + "e" * 64
    rows = [book(500, 500, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
            trade(1000, 1000, "0.4100", "1.000000", "BUY", tx),
            trade(1000, 1000, "0.4200", "2.000000", "BUY", tx)]
    stream = valid_stream(tmp_path / "src", rows=rows)
    assert stream.is_valid
    # distinct canonical digests (different content).
    trade_digests = [d for d in stream.ordered_event_digests]
    assert len(set(trade_digests)) == len(trade_digests)
    ticks = [o for o in stream.converted_events if isinstance(o, TradeTick)]
    assert len(ticks) == 2
    assert str(ticks[0].trade_id) != str(ticks[1].trade_id)   # collision-safe TradeId
    # byte-identical duplicate trades still get unique engine-facing ids.
    dup_rows = [book(500, 500, [["0.4000", "1.000000"]], [["0.6000", "1.000000"]]),
                trade(1000, 1000, "0.4100", "1.000000", "BUY", tx),
                trade(1000, 1000, "0.4100", "1.000000", "BUY", tx)]
    dup_stream = valid_stream(tmp_path / "dup", rows=dup_rows)
    dup_ticks = [o for o in dup_stream.converted_events if isinstance(o, TradeTick)]
    assert len(dup_ticks) == 2
    assert str(dup_ticks[0].trade_id) != str(dup_ticks[1].trade_id)   # unique despite identical bytes


def test_negative_matrix_categories_map_to_tests():
    # R027: all 15 repo negative-test categories are accounted for by a focused TEST node or
    # an explicit NOT_APPLICABLE reason (no invented wording filters).
    import pathlib

    matrix = {
        1: ("TEST", ["test_missing_or_malformed_market_identity_is_rejected",
                     "test_event_semantic_matrix_owned_and_null_fields"]),
        2: ("TEST", ["test_event_semantic_matrix_owned_and_null_fields"]),
        3: ("TEST", ["test_book_json_shape_and_canonical_ordering"]),
        4: ("TEST", ["test_unsupported_pmxt_event_and_malformed_book_rejected"]),
        5: ("TEST", ["test_invalid_timestamp_value_fails_closed",
                     "test_receive_time_primary_ordering_when_event_time_disagrees"]),
        6: ("TEST", ["test_receipt_field_coverage_and_invalid_result_no_echo",
                     "test_execution_authority_is_constant_false"]),
        7: ("NOT_APPLICABLE", "WP168 emits no free-text advisory surface; no wording filter exists."),
        8: ("NOT_APPLICABLE", "No credential inputs or outputs exist; no-echo scanning still guards leakage."),
        9: ("NOT_APPLICABLE", "No advisory/strategy output surface exists."),
        10: ("TEST", ["test_package_imports_no_forbidden_runtime_and_no_network"]),
        11: ("TEST", ["test_unsupported_pmxt_event_and_malformed_book_rejected",
                      "test_source_hash_revalidation_failure_fails_closed"]),
        12: ("TEST", ["test_two_byte_identical_duplicates_retain_multiplicity_two",
                      "test_source_files_map_one_to_one_to_descriptor_objects"]),
        13: ("NOT_APPLICABLE", "Inputs are typed pmxt-v2 columns/tokens, not free-text subject to typos."),
        14: ("TEST", ["test_wp167_source_market_case_normalizes_to_lowercase",
                      "test_missing_or_malformed_market_identity_is_rejected"]),
        15: ("TEST", ["test_book_snapshot_conversion", "test_offline_replay_processes_all_events"]),
    }
    assert set(matrix) == set(range(1, 16))

    # Collect every test function name defined in the scoped WP168 test files.
    test_dir = pathlib.Path(__file__).resolve().parent
    contract = test_dir.parents[1] / "test_nautilus_offline_kernel_contract_docs.py"
    defined = set()
    for path in list(test_dir.glob("test_*.py")) + [contract]:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("def test_") and "(" in line:
                defined.add(line[4:line.index("(")])

    for number, (kind, payload) in matrix.items():
        if kind == "TEST":
            for node in payload:
                assert node in defined, f"category {number} names missing test {node}"
        else:
            assert kind == "NOT_APPLICABLE" and isinstance(payload, str) and payload

    # Second mapping: every WP168 failure domain named by the frozen R027 expected_result maps
    # to a concrete focused test node that exists and is collected.
    wp168_failure_domains = {
        "unsupported_python": ["test_unsupported_python_runtime_fails_closed"],
        "dependency_version": ["test_wrong_nautilus_version_fails_closed"],
        "required_import": ["test_required_import_failure_fails_closed"],
        "instrument_market_id": ["test_missing_or_malformed_market_identity_is_rejected"],
        "precision": ["test_decimal_to_price_quantity_is_exact_no_float",
                      "test_all_prices_are_exact_multiples_of_finest_increment"],
        "ordering": ["test_equal_ts_init_events_have_deterministic_tie_order",
                     "test_equal_timestamp_same_kind_orders_by_canonical_row_bytes",
                     "test_receive_time_primary_ordering_when_event_time_disagrees"],
        "decimal": ["test_decimal_to_price_quantity_is_exact_no_float",
                    "test_book_json_shape_and_canonical_ordering"],
        "event": ["test_unsupported_pmxt_event_and_malformed_book_rejected",
                  "test_event_semantic_matrix_owned_and_null_fields"],
        "book": ["test_book_snapshot_conversion",
                 "test_unsupported_pmxt_event_and_malformed_book_rejected",
                 "test_book_json_shape_and_canonical_ordering"],
        "catalog_write": ["test_catalog_corruption_or_query_mismatch_rejected"],
        "catalog_query": ["test_catalog_corruption_or_query_mismatch_rejected"],
        "replay_count": ["test_replay_count_or_digest_mismatch_rejected"],
        "replay_digest_parity": ["test_replay_count_or_digest_mismatch_rejected",
                                 "test_identity_constants_and_digest_recomputation"],
        "no_echo": ["test_compatibility_result_supported_and_no_echo",
                    "test_unsupported_pmxt_event_and_malformed_book_rejected",
                    "test_catalog_corruption_or_query_mismatch_rejected",
                    "test_replay_count_or_digest_mismatch_rejected",
                    "test_receipt_field_coverage_and_invalid_result_no_echo"],
    }
    # category 5 (timestamp) is bounded to invalid-representation/receive-time ordering only.
    assert "test_invalid_timestamp_value_fails_closed" in defined
    # category 6 (execution authority) is a hard constant-False proof.
    assert "test_execution_authority_is_constant_false" in defined
    for domain, nodes in wp168_failure_domains.items():
        for node in nodes:
            assert node in defined, f"failure domain {domain} names missing test {node}"


def test_bounded_iter_batches_source_processing(tmp_path, monkeypatch):
    # The certified prompt requires bounded per-row processing: iter_batches, not read_table.
    import inspect
    import pyarrow.parquet as pq
    import src.research_runtime.nautilus_offline.conversion as conv

    # Bounded reader is a generator (yields rows), not a whole-file list return.
    assert not hasattr(conv, "_read_rows")
    source_text = inspect.getsource(conv._iter_source_rows)
    assert "iter_batches" in source_text
    assert "MAX_ROW_BATCH" in source_text
    assert "yield " in source_text                 # generator, not a materialized list
    assert "return rows" not in source_text        # no whole-file raw accumulation
    assert "pq.read_table(" not in source_text     # no whole-file table read
    import inspect as _inspect
    assert _inspect.isgeneratorfunction(conv._iter_source_rows)

    # Dynamic proof: if conversion called read_table it would raise here.
    def _forbidden_read_table(*args, **kwargs):
        raise AssertionError("conversion must not call pq.read_table")

    monkeypatch.setattr(pq, "read_table", _forbidden_read_table)
    baseline = convert_pmxt_v2_events(_write_files(tmp_path / "base", [default_rows()]), _context())
    assert baseline.is_valid

    # Multi-batch determinism: forcing batch_size 1 (several batches over the file) yields
    # identical canonical ordering and digests.
    monkeypatch.setattr(conv, "MAX_ROW_BATCH", 1)
    multi_batch = convert_pmxt_v2_events(_write_files(tmp_path / "multi", [default_rows()]), _context())
    assert multi_batch.is_valid
    assert multi_batch.ordered_event_digests == baseline.ordered_event_digests
    assert multi_batch.input_event_counts_by_type == baseline.input_event_counts_by_type
