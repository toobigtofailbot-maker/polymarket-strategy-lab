"""Focused tests for the WP167 pmxt v2 representative external adapter.

Local, offline, deterministic. Every pmxt fixture is a small representative
Parquet file written into pytest ``tmp_path``; no large committed fixtures, no
network, and no downloader are involved. The suite proves schema/event/timestamp/
decimal/side validation, deterministic provenance identity, bounded handling, and
that the adapter source contains no network dependency.
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import pmxt_v2 as PX
from src.data_layer.analytical_research.pmxt_v2 import PmxtV2SourceFile


_TS0 = dt.datetime(2026, 4, 13, 19, 0, 0, tzinfo=dt.timezone.utc)


def _duckdb_or_skip():
    import os

    strict = os.environ.get("WP167_STRICT_DUCKDB") == "1"
    try:
        import duckdb  # noqa: PLC0415

        return duckdb
    except Exception as exc:  # pragma: no cover - CI/local split
        if strict:
            raise
        pytest.skip(
            "DuckDB native module unavailable in local environment "
            f"(Windows Smart App Control): {type(exc).__name__}"
        )


def _write_pmxt(
    path,
    *,
    rows=6,
    tz="UTC",
    drop_column=None,
    price_type="string",
    event_override=None,
    side_override=None,
    null_market=False,
):
    ts_type = pa.timestamp("us", tz=tz)
    price_arrow = pa.float64() if price_type == "float" else pa.string()
    fields = [
        pa.field("timestamp_received", ts_type),
        pa.field("timestamp", ts_type),
        pa.field("market", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("asset_id", pa.string()),
        pa.field("price", price_arrow),
        pa.field("size", pa.string()),
        pa.field("side", pa.string()),
        pa.field("best_bid", pa.string()),
        pa.field("best_ask", pa.string()),
    ]
    events = ["book", "price_change", "last_trade_price", "tick_size_change"]
    data = {
        "timestamp_received": [_TS0 + dt.timedelta(seconds=i) for i in range(rows)],
        "timestamp": [_TS0 + dt.timedelta(seconds=i) for i in range(rows)],
        "market": [(None if (null_market and i == 0) else f"0xmarket{i % 2}") for i in range(rows)],
        "event_type": [(event_override or events[i % len(events)]) for i in range(rows)],
        "asset_id": [f"asset{i % 3}" for i in range(rows)],
        "price": [(0.51 if price_type == "float" else "0.51") for _ in range(rows)],
        "size": ["100.0" for _ in range(rows)],
        "side": [(side_override or ("BUY" if i % 2 else "SELL")) for i in range(rows)],
        "best_bid": ["0.50" for _ in range(rows)],
        "best_ask": ["0.52" for _ in range(rows)],
    }
    if drop_column is not None:
        fields = [f for f in fields if f.name != drop_column]
        data.pop(drop_column, None)
    table = pa.table(data, schema=pa.schema(fields))
    pq.write_table(table, path, compression="zstd")
    return path


def _source_file(path, name="pmxt_2026041319.parquet", partition="2026-04-13T19"):
    return PmxtV2SourceFile(path=str(path), object_name=name, partition_identity=partition)


def _describe(source_files, **overrides):
    kwargs = dict(
        quality_tier="RAW_NATIVE",
        known_gap_policy="AS_CAPTURED",
        license_id="pmxt-archive-terms",
        attribution="pmxt Polymarket Orderbook Archive",
    )
    kwargs.update(overrides)
    return ar.validate_and_describe_pmxt_v2_archive(source_files, **kwargs)


# ── Happy path ───────────────────────────────────────────────────────────────


def test_valid_pmxt_v2_archive_is_described(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", rows=8)
    result = _describe([_source_file(path)])
    assert result.is_valid and result.status == "PMXT_V2_DESCRIBED"
    assert result.total_row_count == 8
    assert result.coverage_start == "2026-04-13T19:00:00Z"
    descriptor = result.descriptor
    assert descriptor.source_class == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
    assert descriptor.provider_id == "pmxt"
    assert tuple(descriptor.event_types) == PX.PMXT_V2_EVENT_TYPES
    assert descriptor.advisory_only is True and descriptor.no_execution_authority is True
    assert len(descriptor.source_objects) == 1
    assert descriptor.source_objects[0].object_name == "pmxt_2026041319.parquet"


def test_all_four_event_types_are_accepted(tmp_path):
    for event in PX.PMXT_V2_EVENT_TYPES:
        path = _write_pmxt(tmp_path / f"{event}.parquet", rows=3, event_override=event)
        result = _describe([_source_file(path, name=f"{event}.parquet")])
        assert result.is_valid, (event, result.error_codes)


def test_source_hash_revalidation(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet")
    result = _describe([_source_file(path)])
    sha = result.descriptor.source_objects[0].source_sha256
    assert ar.revalidate_pmxt_v2_source_hash(str(path), sha) is True
    assert ar.revalidate_pmxt_v2_source_hash(str(path), "0" * 64) is False


def test_descriptor_identity_changes_when_source_bytes_change(tmp_path):
    path_a = _write_pmxt(tmp_path / "a.parquet", rows=4)
    path_b = _write_pmxt(tmp_path / "b.parquet", rows=5)
    a = _describe([_source_file(path_a, name="obj.parquet")])
    b = _describe([_source_file(path_b, name="obj.parquet")])
    assert a.descriptor.external_dataset_id != b.descriptor.external_dataset_id


def test_multiple_files_share_schema_fingerprint(tmp_path):
    path_a = _write_pmxt(tmp_path / "a.parquet", rows=3)
    path_b = _write_pmxt(tmp_path / "b.parquet", rows=3)
    result = _describe(
        [
            _source_file(path_a, name="a.parquet", partition="2026-04-13T19"),
            _source_file(path_b, name="b.parquet", partition="2026-04-13T20"),
        ]
    )
    assert result.is_valid and result.total_row_count == 6
    assert len(result.descriptor.source_objects) == 2


# ── Negative matrix ──────────────────────────────────────────────────────────


def test_native_capture_class_is_refused(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet")
    result = _describe([_source_file(path)], source_class="NATIVE_OFFICIAL_CAPTURE")
    assert result.error_codes == ("EXTERNAL_SOURCE_UNSUPPORTED",)


def test_missing_file_is_rejected(tmp_path):
    result = _describe([_source_file(tmp_path / "absent.parquet")])
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_zero_byte_file_is_rejected(tmp_path):
    empty = tmp_path / "empty.parquet"
    empty.write_bytes(b"")
    result = _describe([_source_file(empty)])
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_non_parquet_file_is_rejected(tmp_path):
    junk = tmp_path / "junk.parquet"
    junk.write_bytes(b"this is not parquet at all")
    result = _describe([_source_file(junk)])
    assert result.error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_missing_required_column_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", drop_column="asset_id")
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_non_utc_timestamp_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", tz="America/New_York")
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_TIMESTAMP_INVALID",)


def test_unsupported_event_type_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", event_override="trade")
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_EVENT_INVALID",)


def test_invalid_side_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", side_override="LONG")
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_EVENT_INVALID",)


def test_float_decimal_column_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", price_type="float")
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_null_required_value_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", null_market=True)
    result = _describe([_source_file(path)])
    assert result.error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_schema_drift_between_files_is_rejected(tmp_path):
    good = _write_pmxt(tmp_path / "good.parquet", rows=3)
    drift = _write_pmxt(tmp_path / "drift.parquet", rows=3, drop_column="best_ask")
    # Each file individually validates, but their schema fingerprints differ.
    result = _describe(
        [_source_file(good, name="good.parquet"), _source_file(drift, name="drift.parquet")]
    )
    assert result.error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


# ── Bounded / lazy handling and no-network guarantees ────────────────────────


def test_bounded_batch_constant_is_reasonable():
    assert PX.MAX_ROW_BATCH == 131_072


def test_adapter_uses_batched_iteration_not_whole_file_reads():
    source = pathlib.Path(PX.__file__).read_text(encoding="utf-8")
    assert "iter_batches" in source
    # A whole-file table read (read_table / to_pandas / to_pylist over a file) is
    # forbidden for the large pmxt archive; only bounded batch scans are used.
    assert "read_table" not in source
    assert "to_pandas" not in source


def test_adapter_source_contains_no_network_dependency():
    source = pathlib.Path(PX.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import socket",
        "import urllib",
        "from urllib",
        "http.client",
        "import requests",
        "import httpx",
        "aiohttp",
        "import websocket",
        "boto3",
        "botocore",
        "urlopen",
        "urlretrieve",
    ):
        assert forbidden not in source, forbidden


# ── DuckDB / Polars queryability over the verified pmxt source file ───────────


def test_duckdb_polars_count_parity_over_pmxt_source(tmp_path):
    _duckdb_or_skip()
    path = _write_pmxt(tmp_path / "pmxt.parquet", rows=8)
    assert _describe([_source_file(path)]).is_valid
    assert ar.duckdb_row_count(str(path)) == ar.polars_row_count(str(path))
    assert ar.duckdb_group_count(str(path), "event_type") == ar.polars_group_count(
        str(path), "event_type"
    )


def test_polars_scan_over_pmxt_source_without_duckdb(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", rows=8)
    assert ar.polars_row_count(str(path)) == 8
    grouped = ar.polars_group_count(str(path), "event_type")
    assert sum(grouped.values()) == 8
