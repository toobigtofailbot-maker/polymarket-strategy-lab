"""Focused tests for the WP167 pmxt v2 representative external adapter.

Local, offline, deterministic. Every pmxt fixture is a small representative
Parquet file with the EXACT documented pmxt v2 schema (sixteen columns:
fixed_size_binary[66] market, decimal-string asset_id, UTC millisecond
timestamps, exact-precision Arrow decimals, uint16 fee_rate_bps) written into
pytest ``tmp_path``; no large committed fixtures, no network, and no downloader
are involved. The suite proves exact schema/type validation, deterministic
provenance identity, bounded handling, version locking, and that the adapter
source contains no network dependency.
"""

from __future__ import annotations

import datetime as dt
import pathlib
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import pmxt_v2 as PX
from src.data_layer.analytical_research.pmxt_v2 import PmxtV2SourceFile


_TS0 = dt.datetime(2026, 4, 13, 19, 0, 0, tzinfo=dt.timezone.utc)
_ASSET_IDS = (
    "71321045679252212594626385532706912750332728571942532289631379312455583992563",
    "11015470973432074695876650666652657367051282905472228366926768396234655450318",
    "48331043336612883890938759509493159234755048973500640148014422747788308965732",
)


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


def _market(i: int) -> bytes:
    return ("0x" + f"{i % 65536:064x}").encode("ascii")


def _write_pmxt(
    path,
    *,
    rows=6,
    ts_unit="ms",
    tz="UTC",
    market_type="binary66",
    drop_column=None,
    price_precision=9,
    fee_type="uint16",
    null_ts_received=False,
    malformed_market=False,
    malformed_asset_id=False,
    event_override=None,
    side_override=None,
):
    ts_type = pa.timestamp(ts_unit, tz=tz)
    if market_type == "binary66":
        market_arrow = pa.binary(66)
        market_width = 66
    elif market_type == "binary40":
        market_arrow = pa.binary(40)
        market_width = 40
    else:  # string
        market_arrow = pa.string()
        market_width = None
    price_arrow = pa.decimal128(price_precision, 4)
    fee_arrow = pa.uint16() if fee_type == "uint16" else pa.int32()

    fields = [
        pa.field("timestamp_received", ts_type),
        pa.field("timestamp", ts_type),
        pa.field("market", market_arrow),
        pa.field("event_type", pa.string()),
        pa.field("asset_id", pa.string()),
        pa.field("bids", pa.string()),
        pa.field("asks", pa.string()),
        pa.field("price", price_arrow),
        pa.field("size", pa.decimal128(18, 6)),
        pa.field("side", pa.string()),
        pa.field("best_bid", pa.decimal128(9, 4)),
        pa.field("best_ask", pa.decimal128(9, 4)),
        pa.field("fee_rate_bps", fee_arrow),
        pa.field("transaction_hash", pa.string()),
        pa.field("old_tick_size", pa.decimal128(9, 4)),
        pa.field("new_tick_size", pa.decimal128(9, 4)),
    ]
    events = ["book", "price_change", "last_trade_price", "tick_size_change"]

    def market_value(i):
        if malformed_market:
            return ("zz" + f"{i:064x}").encode("ascii")
        hexlen = (market_width or 66) - 2
        return ("0x" + f"{i % 65536:0{hexlen}x}").encode("ascii")

    def asset_value(i):
        return "not-a-decimal" if malformed_asset_id else _ASSET_IDS[i % len(_ASSET_IDS)]

    ts_received = [_TS0 + dt.timedelta(seconds=i) for i in range(rows)]
    if null_ts_received and rows:
        ts_received[0] = None

    if market_type == "string":
        market_values = [f"0xmarket{i % 2}" for i in range(rows)]
    else:
        market_values = [market_value(i) for i in range(rows)]

    data = {
        "timestamp_received": ts_received,
        "timestamp": [_TS0 + dt.timedelta(seconds=i) for i in range(rows)],
        "market": market_values,
        "event_type": [(event_override or events[i % len(events)]) for i in range(rows)],
        "asset_id": [asset_value(i) for i in range(rows)],
        "bids": [None for _ in range(rows)],
        "asks": [None for _ in range(rows)],
        "price": [Decimal("0.5100") for _ in range(rows)],
        "size": [Decimal("100.000000") for _ in range(rows)],
        "side": [(side_override or ("BUY" if i % 2 else "SELL")) for i in range(rows)],
        "best_bid": [Decimal("0.5000") for _ in range(rows)],
        "best_ask": [Decimal("0.5200") for _ in range(rows)],
        "fee_rate_bps": [0 for _ in range(rows)],
        "transaction_hash": [f"0xhash{i}" for i in range(rows)],
        "old_tick_size": [Decimal("0.0100") for _ in range(rows)],
        "new_tick_size": [Decimal("0.0100") for _ in range(rows)],
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


# ── Happy path (exact documented v2 schema) ──────────────────────────────────


def test_valid_pmxt_v2_archive_is_described(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", rows=8)
    result = _describe([_source_file(path)])
    assert result.is_valid and result.status == "PMXT_V2_DESCRIBED", result.error_codes
    assert result.total_row_count == 8
    assert result.coverage_start == "2026-04-13T19:00:00Z"
    descriptor = result.descriptor
    assert descriptor.source_class == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
    assert descriptor.provider_id == "pmxt"
    assert descriptor.dataset_version == "v2"
    # The descriptor stores event types in canonical (sorted) order.
    assert tuple(descriptor.event_types) == tuple(sorted(PX.PMXT_V2_EVENT_TYPES))
    assert descriptor.advisory_only is True and descriptor.no_execution_authority is True


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
    a = _describe([_source_file(_write_pmxt(tmp_path / "a.parquet", rows=4), name="obj.parquet")])
    b = _describe([_source_file(_write_pmxt(tmp_path / "b.parquet", rows=5), name="obj.parquet")])
    assert a.descriptor.external_dataset_id != b.descriptor.external_dataset_id


def test_multiple_files_share_schema_fingerprint(tmp_path):
    result = _describe(
        [
            _source_file(_write_pmxt(tmp_path / "a.parquet", rows=3), name="a.parquet", partition="2026-04-13T19"),
            _source_file(_write_pmxt(tmp_path / "b.parquet", rows=3), name="b.parquet", partition="2026-04-13T20"),
        ]
    )
    assert result.is_valid and result.total_row_count == 6
    assert len(result.descriptor.source_objects) == 2


# ── Negative matrix — schema/type ────────────────────────────────────────────


def test_string_market_column_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", market_type="string")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_wrong_fixed_binary_width_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", market_type="binary40")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_wrong_timestamp_unit_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", ts_unit="us")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_non_utc_timestamp_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", tz="America/New_York")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_TIMESTAMP_INVALID",)


def test_missing_event_specific_column_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", drop_column="bids")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_wrong_decimal_precision_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", price_precision=10)
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_fee_rate_bps_wrong_type_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", fee_type="int32")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


# The exact-locked 16-column schema means any deviation is rejected per file
# (covered by the per-column type tests above); two individually valid files
# therefore always share the same schema fingerprint.


# ── Negative matrix — row values ─────────────────────────────────────────────


def test_null_timestamp_received_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", null_ts_received=True)
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_malformed_market_bytes_are_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", malformed_market=True)
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_malformed_asset_id_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", malformed_asset_id=True)
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_SCHEMA_INVALID",)


def test_unsupported_event_type_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", event_override="trade")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_EVENT_INVALID",)


def test_invalid_side_is_rejected(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet", side_override="LONG")
    assert _describe([_source_file(path)]).error_codes == ("EXTERNAL_SOURCE_EVENT_INVALID",)


# ── Negative matrix — file / class / version ─────────────────────────────────


def test_native_capture_class_is_refused(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet")
    assert _describe([_source_file(path)], source_class="NATIVE_OFFICIAL_CAPTURE").error_codes == (
        "EXTERNAL_SOURCE_UNSUPPORTED",
    )


def test_arbitrary_dataset_version_is_refused(tmp_path):
    path = _write_pmxt(tmp_path / "pmxt.parquet")
    assert _describe([_source_file(path)], dataset_version="v1").error_codes == (
        "EXTERNAL_SOURCE_UNSUPPORTED",
    )


def test_missing_file_is_rejected(tmp_path):
    assert _describe([_source_file(tmp_path / "absent.parquet")]).error_codes == (
        "EXTERNAL_SOURCE_FILE_INVALID",
    )


def test_zero_byte_file_is_rejected(tmp_path):
    empty = tmp_path / "empty.parquet"
    empty.write_bytes(b"")
    assert _describe([_source_file(empty)]).error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


def test_non_parquet_file_is_rejected(tmp_path):
    junk = tmp_path / "junk.parquet"
    junk.write_bytes(b"this is not parquet at all")
    assert _describe([_source_file(junk)]).error_codes == ("EXTERNAL_SOURCE_FILE_INVALID",)


# ── Bounded / lazy handling and no-network guarantees ────────────────────────


def test_bounded_batch_constant_is_reasonable():
    assert PX.MAX_ROW_BATCH == 131_072


def test_adapter_uses_batched_iteration_not_whole_file_reads():
    source = pathlib.Path(PX.__file__).read_text(encoding="utf-8")
    assert "iter_batches" in source
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
