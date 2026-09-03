"""WP168 ParquetDataCatalog build/query round-trip tests (R018-R020)."""

from __future__ import annotations

import dataclasses

import pytest

import src.research_runtime.nautilus_offline as offline
from src.research_runtime.nautilus_offline import (
    CATALOG_QUERY_ERROR,
    CATALOG_WRITE_ERROR,
    CatalogBuildResult,
    CatalogQueryResult,
    build_catalog,
    query_catalog,
    stream_identity_digest,
)

from test_conversion import valid_stream


def test_catalog_write_registers_instrument_before_data(tmp_path):
    stream = valid_stream(tmp_path / "src")
    result = build_catalog(stream, tmp_path / "catalog")
    assert result.is_valid
    assert result.instrument_registered is True
    assert result.written_delta_count == 5
    assert result.written_trade_count == 1
    assert result.stream_ref_digest == stream_identity_digest(stream)
    # caller catalog_dir is physical evidence, not identity.
    assert result.catalog_dir is not None


def test_catalog_query_round_trip(tmp_path):
    stream = valid_stream(tmp_path / "src")
    build_result = build_catalog(stream, tmp_path / "catalog")
    query_result = query_catalog(build_result)
    assert query_result.is_valid
    assert query_result.round_trip_matches is True
    assert query_result.queried_delta_count == build_result.written_delta_count
    assert query_result.queried_trade_count == build_result.written_trade_count


def test_catalog_query_representative_values_round_trip(tmp_path):
    # R019: representative delta/trade price/size/timestamp values round-trip, not only counts.
    from nautilus_trader.model.data import OrderBookDelta, OrderBookDeltas, TradeTick
    from nautilus_trader.model.enums import BookAction
    from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

    stream = valid_stream(tmp_path / "src")
    build_result = build_catalog(stream, tmp_path / "catalog")
    assert build_result.is_valid

    # Expected representative values taken from the converted source stream.
    expected_deltas = []
    expected_trades = []
    for obj in stream.converted_events[1:]:
        if isinstance(obj, OrderBookDeltas):
            expected_deltas.extend(obj.deltas)
        elif isinstance(obj, OrderBookDelta):
            expected_deltas.append(obj)
        elif isinstance(obj, TradeTick):
            expected_trades.append(obj)

    catalog = ParquetDataCatalog(build_result.catalog_dir)
    queried_deltas = catalog.query(data_cls=OrderBookDelta)
    queried_trades = catalog.query(data_cls=TradeTick)

    # Representative ADD delta: exact price/size/timestamps round-trip.
    exp_add = next(d for d in expected_deltas if d.action == BookAction.ADD)
    got_add = next(
        d for d in queried_deltas
        if d.action == BookAction.ADD and str(d.order.price) == str(exp_add.order.price)
    )
    assert str(got_add.order.size) == str(exp_add.order.size)
    assert got_add.ts_event == exp_add.ts_event
    assert got_add.ts_init == exp_add.ts_init

    # Representative trade: exact price/size/timestamps round-trip.
    exp_trade = expected_trades[0]
    got_trade = next(t for t in queried_trades if str(t.price) == str(exp_trade.price))
    assert str(got_trade.size) == str(exp_trade.size)
    assert got_trade.ts_event == exp_trade.ts_event
    assert got_trade.ts_init == exp_trade.ts_init


def test_catalog_real_count_mismatch_fails_closed(tmp_path):
    # A real round-trip count mismatch must fail closed, not report a valid query.
    stream = valid_stream(tmp_path / "src")
    build_result = build_catalog(stream, tmp_path / "catalog")
    assert build_result.is_valid
    # Craft a build result whose recorded counts disagree with the persisted catalog.
    mismatched = dataclasses.replace(
        build_result, written_delta_count=build_result.written_delta_count + 1
    )
    result = query_catalog(mismatched)
    assert result.is_valid is False
    assert result.status == "NAUTILUS_CATALOG_QUERY_REJECTED"
    assert result.error_codes == (CATALOG_QUERY_ERROR,)
    assert result.round_trip_matches is False
    assert offline.scan_public_result_for_echo(result, ("Traceback", "\\", str(tmp_path))) == ()


def test_catalog_query_exception_fails_closed(tmp_path):
    # An actual query exception (unreadable catalog dir) fails closed with no echo.
    stream = valid_stream(tmp_path / "src")
    build_result = build_catalog(stream, tmp_path / "catalog")
    broken = dataclasses.replace(build_result, catalog_dir=str(tmp_path / "does_not_exist"))
    result = query_catalog(broken)
    assert result.is_valid is False
    assert result.error_codes == (CATALOG_QUERY_ERROR,)


def test_catalog_corruption_or_query_mismatch_rejected(tmp_path):
    # An invalid stream cannot be catalogued.
    from src.research_runtime.nautilus_offline import ConvertedEventStream
    invalid = ConvertedEventStream(
        is_valid=False, status="X", error_codes=("NAUTILUS_EVENT_CONVERSION_INVALID",),
        instrument_id=None, source_dataset_kind=None, source_external_dataset_id=None,
        conversion_policy_version=None, ordered_event_digests=(), input_event_counts_by_type=(),
        tick_size_regime_sequence=(), first_event_time_ns=None, last_event_time_ns=None,
        warnings=(), converted_events=())
    build_rejected = build_catalog(invalid, tmp_path / "c1")
    assert build_rejected.is_valid is False
    assert build_rejected.error_codes == (CATALOG_WRITE_ERROR,)
    # Querying a rejected build fails closed.
    query_rejected = query_catalog(build_rejected)
    assert query_rejected.is_valid is False
    assert query_rejected.error_codes == (CATALOG_QUERY_ERROR,)
    assert offline.scan_public_result_for_echo(query_rejected, ("Traceback", "\\")) == ()


def test_catalog_results_are_frozen(tmp_path):
    stream = valid_stream(tmp_path / "src")
    build_result = build_catalog(stream, tmp_path / "catalog")
    assert dataclasses.is_dataclass(CatalogBuildResult)
    assert dataclasses.is_dataclass(CatalogQueryResult)
    with pytest.raises(dataclasses.FrozenInstanceError):
        build_result.is_valid = False  # type: ignore[misc]
