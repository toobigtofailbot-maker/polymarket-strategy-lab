"""WP168 pmxt-v2 -> Nautilus conversion, provenance, ordering & serialization tests.

Covers R010-R017, R041, R043-R044, R046-R047, R049-R050, R052-R059, R061 (field coverage).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
from decimal import Decimal

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
    stream = valid_stream(tmp_path)
    assert stream.is_valid
    counts = dict(stream.input_event_counts_by_type)
    assert counts["book"] == 1


def test_price_change_conversion(tmp_path):
    stream = valid_stream(tmp_path)
    assert dict(stream.input_event_counts_by_type)["price_change"] == 2


def test_last_trade_price_to_trade_tick(tmp_path):
    from nautilus_trader.model.data import TradeTick
    stream = valid_stream(tmp_path)
    assert dict(stream.input_event_counts_by_type)["last_trade_price"] == 1
    assert any(isinstance(obj, TradeTick) for obj in stream.converted_events)


def test_event_and_receive_timestamp_mapping(tmp_path):
    from nautilus_trader.model.data import OrderBookDeltas
    stream = valid_stream(tmp_path)
    snapshot = next(o for o in stream.converted_events if isinstance(o, OrderBookDeltas))
    first_delta = snapshot.deltas[0]
    assert first_delta.ts_event == 1000 * 1_000_000   # source event time
    assert first_delta.ts_init == 1005 * 1_000_000    # source receive time


def test_decimal_to_price_quantity_is_exact_no_float(tmp_path):
    from nautilus_trader.model.data import TradeTick
    stream = valid_stream(tmp_path)
    tick = next(o for o in stream.converted_events if isinstance(o, TradeTick))
    assert str(tick.price) == "0.410"


def test_tick_size_change_committed_as_regime_metadata(tmp_path):
    stream = valid_stream(tmp_path)
    assert stream.tick_size_regime_sequence == (("0.0100", "0.0010", 1100 * 1_000_000),)
    assert stream.source_dataset_kind == SOURCE_DATASET_KIND
    assert stream.conversion_policy_version == CONVERSION_POLICY_VERSION


def test_all_prices_are_exact_multiples_of_finest_increment(tmp_path):
    # 0.5850 is a multiple of 0.001; 0.5855 is not -> fail closed.
    ok = valid_stream(tmp_path, rows=[price_change(1, 2, "0.5850", "1.000000", "BUY")])
    assert ok.is_valid
    bad = valid_stream(tmp_path, rows=[price_change(1, 2, "0.5855", "1.000000", "BUY")])
    assert bad.is_valid is False
    assert bad.error_codes == (CONVERSION_ERROR,)


# --------------------------- ordering / duplicates ---------------------------

def test_receive_time_primary_ordering_when_event_time_disagrees(tmp_path):
    # Event A: ts_event=2000, ts_init=1000. Event B: ts_event=1000, ts_init=2000.
    # Receive-time-primary => A (ts_init 1000) before B (ts_init 2000).
    rows = [
        trade(2000, 1000, "0.4000", "1.000000", "BUY", "0x" + "a" * 64),
        trade(1000, 2000, "0.4000", "1.000000", "BUY", "0x" + "b" * 64),
    ]
    stream = valid_stream(tmp_path, rows=rows)
    from nautilus_trader.model.data import TradeTick
    ticks = [o for o in stream.converted_events if isinstance(o, TradeTick)]
    assert [t.ts_init for t in ticks] == [1000 * 1_000_000, 2000 * 1_000_000]


def test_equal_ts_init_events_have_deterministic_tie_order(tmp_path):
    # Same ts_init and ts_event, different event kinds -> event_kind_rank orders them.
    rows = [
        trade(1000, 1000, "0.4000", "1.000000", "BUY", "0x" + "c" * 64),        # rank 2
        price_change(1000, 1000, "0.4000", "1.000000", "BUY"),                   # rank 1
    ]
    stream = valid_stream(tmp_path, rows=rows)
    from nautilus_trader.model.data import OrderBookDelta, TradeTick
    kinds = [type(o).__name__ for o in stream.converted_events
             if isinstance(o, (OrderBookDelta, TradeTick))]
    assert kinds == ["OrderBookDelta", "TradeTick"]  # price_change (1) before trade (2)


test_event_kind_rank_orders_equal_ts_init_mixed_types = test_equal_ts_init_events_have_deterministic_tie_order


def test_input_enumeration_order_invariance(tmp_path):
    rows = default_rows()
    forward = valid_stream(tmp_path / "a", rows=list(rows))
    reversed_rows = list(reversed(rows))
    backward = valid_stream(tmp_path / "b", rows=reversed_rows)
    assert forward.ordered_event_digests == backward.ordered_event_digests


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
    rows = [
        trade(1000, 1000, "0.5000", "1.000000", "BUY", "0x" + "2" * 64),
        trade(1000, 1000, "0.4000", "1.000000", "BUY", "0x" + "1" * 64),
    ]
    stream = valid_stream(tmp_path, rows=rows)
    from nautilus_trader.model.data import TradeTick
    prices = [str(o.price) for o in stream.converted_events if isinstance(o, TradeTick)]
    # Deterministic content order (by digest then bytes); stable across runs.
    again = valid_stream(tmp_path / "again", rows=list(reversed(rows)))
    assert stream.ordered_event_digests == again.ordered_event_digests
    assert len(prices) == 2


# --------------------------- provenance / semantics --------------------------

def test_descriptor_provider_version_source_class_mismatch_rejected(tmp_path):
    source = _write_files(tmp_path, [default_rows()], wrong_provider=True)
    stream = convert_pmxt_v2_events(source, _context())
    assert stream.is_valid is False
    assert stream.error_codes == (CONVERSION_ERROR,)


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
        assert offline.scan_public_result_for_echo(result, ("Traceback", "\\", str(tmp_path))) == ()
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
    extra = _write_files(tmp_path / "extra", [default_rows()], extra_object=True)
    assert convert_pmxt_v2_events(extra, _context()).is_valid is False
    dup = _write_files(tmp_path / "dup", [default_rows(), default_rows()], duplicate_name=True)
    assert convert_pmxt_v2_events(dup, _context()).is_valid is False


def test_source_hash_revalidation_failure_fails_closed(tmp_path):
    source = _write_files(tmp_path, [default_rows()], corrupt_hash=True)
    stream = convert_pmxt_v2_events(source, _context())
    assert stream.is_valid is False
    assert stream.error_codes == (CONVERSION_ERROR,)
    assert offline.scan_public_result_for_echo(stream, ("Traceback", "\\", str(tmp_path))) == ()


def test_event_semantic_matrix_owned_and_null_fields(tmp_path):
    # price_change with a null owned field (side) -> fail closed.
    bad_owned = row("price_change", 1, 2, price=Decimal("0.4000"), size=Decimal("1.000000"),
                    side=None, best_bid=Decimal("0.4000"), best_ask=Decimal("0.6000"))
    assert valid_stream(tmp_path / "a", rows=[bad_owned]).is_valid is False
    # book with an unowned field populated (price) -> fail closed.
    bad_unowned = row("book", 1, 2, bids=json.dumps([["0.4000", "1.000000"]]),
                      asks=json.dumps([["0.6000", "1.000000"]]), price=Decimal("0.4000"))
    assert valid_stream(tmp_path / "b", rows=[bad_unowned]).is_valid is False
    # invalid side token -> fail closed.
    bad_side = price_change(1, 2, "0.4000", "1.000000", "HODL")
    assert valid_stream(tmp_path / "c", rows=[bad_side]).is_valid is False


def test_unsupported_pmxt_event_and_malformed_book_rejected(tmp_path):
    bad_event = row("weird_event", 1, 2)
    assert valid_stream(tmp_path / "a", rows=[bad_event]).is_valid is False
    malformed = book(1, 2, [["0.4000"]], [["0.6000", "1.000000"]])  # bid pair has 1 item
    assert valid_stream(tmp_path / "b", rows=[malformed]).is_valid is False


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


# --------------------------- field coverage (R061) ---------------------------

def test_every_public_dataclass_field_is_classified():
    # Exact frozen field sets for every public dataclass (mechanical completeness gate).
    expected = {
        NautilusRuntimeCompatibilityResult: {
            "is_valid", "status", "error_codes", "nautilus_version",
            "python_version", "advisory_only", "no_execution_authority"},
        BinaryOptionMarketContext: {
            "condition_id", "outcome_token_id", "outcome_label", "description",
            "activation_ns", "expiration_ns", "price_increment", "size_increment",
            "maker_fee", "taker_fee", "ts_event_ns", "ts_init_ns"},
        BinaryOptionMappingResult: {
            "is_valid", "status", "error_codes", "instrument_id", "price_increment",
            "size_increment", "warnings", "binary_option"},
        PmxtV2ReplaySource: {"descriptor", "source_files"},
        ConvertedEventStream: {
            "is_valid", "status", "error_codes", "instrument_id", "source_dataset_kind",
            "source_external_dataset_id", "conversion_policy_version", "ordered_event_digests",
            "input_event_counts_by_type", "tick_size_regime_sequence", "first_event_time_ns",
            "last_event_time_ns", "warnings", "converted_events"},
        CatalogBuildResult: {
            "is_valid", "status", "error_codes", "instrument_registered", "written_delta_count",
            "written_trade_count", "catalog_dir", "stream_ref_digest"},
        CatalogQueryResult: {
            "is_valid", "status", "error_codes", "queried_delta_count",
            "queried_trade_count", "round_trip_matches"},
        NautilusReplayReceipt: {
            "is_valid", "status", "error_codes", "schema_id", "schema_version",
            "source_dataset_kind", "source_external_dataset_id", "conversion_policy_version",
            "nautilus_version", "instrument_id", "input_event_counts_by_type",
            "first_event_time_ns", "last_event_time_ns", "tick_size_regime_sequence",
            "replay_processed_event_count", "replay_digest", "warnings", "execution_authority"},
    }
    for cls, fields in expected.items():
        assert dataclasses.is_dataclass(cls)
        assert {f.name for f in dataclasses.fields(cls)} == fields, cls.__name__


def test_converted_stream_source_external_dataset_id(tmp_path):
    stream = valid_stream(tmp_path)
    assert stream.source_external_dataset_id == "ext:pmxt:test0001"


def test_bounded_iter_batches_source_processing(tmp_path, monkeypatch):
    # The certified prompt requires bounded per-row processing: iter_batches, not read_table.
    import inspect
    import pyarrow.parquet as pq
    import src.research_runtime.nautilus_offline.conversion as conv

    source_text = inspect.getsource(conv._read_rows)
    assert "iter_batches" in source_text
    assert "MAX_ROW_BATCH" in source_text
    assert "pq.read_table(" not in source_text  # no whole-file table read

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
