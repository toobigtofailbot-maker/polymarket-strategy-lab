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
