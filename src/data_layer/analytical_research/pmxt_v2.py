"""WP167 pmxt v2 Polymarket Orderbook Archive representative external adapter.

This adapter proves the generic external-history boundary with exactly one
representative, high-value, Parquet-native source: the pmxt Polymarket Orderbook
Archive v2. It accepts only explicitly supplied LOCAL Parquet file paths. It
performs NO URL retrieval, NO HTTP, NO Polymarket API call, NO object-store SDK,
and NO downloader of any kind — its imports are PyArrow (metadata + bounded
batched scans), the standard library, and the sibling external-descriptor module.

The adapter locks the actual documented pmxt v2 Arrow logical schema: exactly the
sixteen documented columns with their exact logical types (UTC millisecond source
and receive timestamps, a fixed-size-binary[66] ``0x`` + 64-hex ``market``, a
decimal-string ``asset_id`` token id, exact-precision Arrow decimals for price/size/
tick/fee-adjacent fields, and a uint16 ``fee_rate_bps``). Event-specific columns are
nullable *values*, not optional schema columns. For each file it computes the exact
source content hash and byte length, inspects the schema without materializing the
whole file, validates the required columns and their exact types, validates the
five always-populated columns row-wise (including the ``market`` byte form and the
``asset_id`` decimal-string form) through bounded batched scans, records the schema
fingerprint, and rejects unsupported material schema drift. Real pmxt files are
large, so nothing is ever read into a single whole-file Python list; row access is
metadata-first and batched at ``MAX_ROW_BATCH``.

pmxt v2 is always classified ``THIRD_PARTY_NATIVE_FRAME_ARCHIVE`` and always
described under ``dataset_version = "v2"``; a request to describe it as a native
official capture, or under an arbitrary version label, is refused. Every result
fixes ``advisory_only=True`` and ``no_execution_authority=True`` and never echoes an
absolute path, raw source row, exception text, or environment value.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..point_in_time_market_research import canonical_json_bytes, sha256_hex
from .external_dataset import (
    ExternalDatasetBuildResult,
    ExternalSourceObject,
    build_external_dataset_descriptor,
    valid_utc_timestamp,
)
from .research_dataset import MAX_ROW_BATCH

_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UNIT_TO_MICROS = {"s": 1_000_000, "ms": 1_000, "us": 1, "ns": None}

# ── Locked pmxt v2 contract ──────────────────────────────────────────────────

PMXT_V2_ADAPTER_LABEL = "PMXT_V2_POLYMARKET_ORDERBOOK_ARCHIVE"
PMXT_V2_ADAPTER_POSTURE = "LOCAL_OFFLINE_PARQUET_ONLY_NO_DOWNLOADER_NO_NETWORK"

PMXT_V2_PROVIDER_ID = "pmxt"
PMXT_V2_DATASET_NAME = "pmxt_polymarket_orderbook_archive"
PMXT_V2_DATASET_VERSION = "v2"
PMXT_V2_SOURCE_CLASS = "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
PMXT_V2_IMPORTER_ID = "wp167-pmxt-v2-adapter"
PMXT_V2_IMPORTER_VERSION = "1.0.0"
PMXT_V2_SOURCE_TIMESTAMP_SEMANTICS = "SOURCE_EVENT_TIME_UTC_MS"
PMXT_V2_RECEIVE_TIMESTAMP_SEMANTICS = "EXPORTER_RECEIVE_TIME_UTC_MS"

# The exact documented pmxt v2 timestamp unit and market byte form.
PMXT_V2_TIMESTAMP_UNIT = "ms"
PMXT_V2_MARKET_BYTE_WIDTH = 66  # "0x" + 64 hex characters

PMXT_V2_REQUIRED_COLUMNS = (
    "timestamp_received",
    "timestamp",
    "market",
    "event_type",
    "asset_id",
)
PMXT_V2_TIMESTAMP_COLUMNS = ("timestamp_received", "timestamp")
PMXT_V2_EVENT_TYPES = ("book", "price_change", "last_trade_price", "tick_size_change")
PMXT_V2_SIDE_COLUMN = "side"
PMXT_V2_VALID_SIDES = ("BUY", "SELL")

# Decimal columns and their exact documented (precision, scale).
PMXT_V2_DECIMAL_SPECS = {
    "price": (9, 4),
    "size": (18, 6),
    "best_bid": (9, 4),
    "best_ask": (9, 4),
    "old_tick_size": (9, 4),
    "new_tick_size": (9, 4),
}
PMXT_V2_DECIMAL_COLUMNS = tuple(PMXT_V2_DECIMAL_SPECS)
PMXT_V2_STRING_COLUMNS = ("event_type", "asset_id", "bids", "asks", "side", "transaction_hash")

# The complete, exact 16-column documented pmxt v2 schema (column -> checker key).
PMXT_V2_SCHEMA_COLUMNS = (
    "timestamp_received",
    "timestamp",
    "market",
    "event_type",
    "asset_id",
    "bids",
    "asks",
    "price",
    "size",
    "side",
    "best_bid",
    "best_ask",
    "fee_rate_bps",
    "transaction_hash",
    "old_tick_size",
    "new_tick_size",
)

_UTC_TZ_NAMES = frozenset({"UTC", "Etc/UTC", "+00:00", "Z", "00:00"})
_HEX_BYTES = frozenset(b"0123456789abcdefABCDEF")

PMXT_V2_STATUSES = ("PMXT_V2_DESCRIBED", "PMXT_V2_REJECTED")

# The pmxt adapter reports through the shared external-history error vocabulary.


@dataclass(frozen=True)
class PmxtV2SourceFile:
    path: object
    object_name: str
    partition_identity: str


@dataclass(frozen=True)
class PmxtV2DescribeResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    descriptor: object
    total_row_count: int
    coverage_start: str | None
    coverage_end: str | None
    advisory_only: bool
    no_execution_authority: bool


class _PmxtFailure(Exception):
    def __init__(self, code: str):
        self.code = code


def _rejected(*codes: str) -> PmxtV2DescribeResult:
    return PmxtV2DescribeResult(
        is_valid=False,
        status="PMXT_V2_REJECTED",
        error_codes=tuple(codes),
        descriptor=None,
        total_row_count=0,
        coverage_start=None,
        coverage_end=None,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Schema fingerprint and exact column-type validation ──────────────────────


def pmxt_v2_schema_fingerprint(schema: pa.Schema) -> str:
    descriptor = [[field.name, str(field.type)] for field in schema]
    return sha256_hex(canonical_json_bytes(descriptor))


def _is_string_type(dtype: pa.DataType) -> bool:
    if pa.types.is_string(dtype) or pa.types.is_large_string(dtype):
        return True
    return pa.types.is_dictionary(dtype) and (
        pa.types.is_string(dtype.value_type) or pa.types.is_large_string(dtype.value_type)
    )


def _is_utc_tz(tz: object) -> bool:
    return isinstance(tz, str) and (tz in _UTC_TZ_NAMES or tz.upper() == "UTC")


def _validate_schema(schema: pa.Schema) -> None:
    # Exactly the sixteen documented columns: no missing, no extra.
    if tuple(sorted(schema.names)) != tuple(sorted(PMXT_V2_SCHEMA_COLUMNS)):
        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

    for column in PMXT_V2_TIMESTAMP_COLUMNS:
        dtype = schema.field(column).type
        if not pa.types.is_timestamp(dtype):
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
        if dtype.tz is None or not _is_utc_tz(dtype.tz):
            raise _PmxtFailure("EXTERNAL_SOURCE_TIMESTAMP_INVALID")
        if dtype.unit != PMXT_V2_TIMESTAMP_UNIT:
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

    market_type = schema.field("market").type
    if not (
        pa.types.is_fixed_size_binary(market_type)
        and market_type.byte_width == PMXT_V2_MARKET_BYTE_WIDTH
    ):
        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

    for column in PMXT_V2_STRING_COLUMNS:
        if not _is_string_type(schema.field(column).type):
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

    for column, (precision, scale) in PMXT_V2_DECIMAL_SPECS.items():
        dtype = schema.field(column).type
        if not (
            pa.types.is_decimal(dtype)
            and dtype.precision == precision
            and dtype.scale == scale
        ):
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

    if not pa.types.is_uint16(schema.field("fee_rate_bps").type):
        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")


# ── Bounded row-level validation ─────────────────────────────────────────────


def _valid_market_bytes(value: object) -> bool:
    if not isinstance(value, (bytes, bytearray)) or len(value) != PMXT_V2_MARKET_BYTE_WIDTH:
        return False
    if value[:2] != b"0x":
        return False
    return all(byte in _HEX_BYTES for byte in value[2:])


def _valid_asset_id(value: object) -> bool:
    # Documented decimal-string token id form.
    return isinstance(value, str) and value != "" and value.isdigit()


def _epoch_to_utc(epoch: int, unit: str) -> datetime:
    """Convert an integer timestamp epoch (in ``unit``) to an aware UTC datetime.

    Uses only a fixed UTC offset and ``timedelta``, so no timezone database
    (``pytz``/``tzdata``) is required on any platform.
    """

    if unit == "ns":
        micros = epoch // 1_000
    else:
        micros = epoch * _UNIT_TO_MICROS[unit]
    return _EPOCH_UTC + timedelta(microseconds=micros)


def _validate_and_scan_file(
    parquet_file: pq.ParquetFile, schema: pa.Schema
) -> tuple[int, datetime, datetime]:
    """Batched validation of one pmxt file; returns (rows, min_utc, max_utc).

    Never reads the whole file into one Python list; each batch is bounded by
    ``MAX_ROW_BATCH``. Timestamp columns are inspected as their underlying int64
    epochs (via a zero-copy cast) rather than converted to Python datetimes, so no
    timezone database is required to compute coverage. Raises ``_PmxtFailure`` with
    a closed code on any fault.
    """

    ts_unit = schema.field("timestamp").type.unit
    side_present = PMXT_V2_SIDE_COLUMN in set(schema.names)
    scan_columns = ["event_type", "timestamp", "timestamp_received", "market", "asset_id"]
    if side_present:
        scan_columns.append(PMXT_V2_SIDE_COLUMN)

    total_rows = 0
    min_epoch: int | None = None
    max_epoch: int | None = None

    for batch in parquet_file.iter_batches(
        batch_size=MAX_ROW_BATCH, columns=scan_columns
    ):
        # Always-populated columns must never be null.
        for column in ("timestamp_received", "timestamp", "market", "event_type", "asset_id"):
            if batch.column(column).null_count > 0:
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

        for value in batch.column("event_type").to_pylist():
            if value not in PMXT_V2_EVENT_TYPES:
                raise _PmxtFailure("EXTERNAL_SOURCE_EVENT_INVALID")

        for value in batch.column("market").to_pylist():
            if not _valid_market_bytes(value):
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

        for value in batch.column("asset_id").to_pylist():
            if not _valid_asset_id(value):
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

        if side_present:
            for value in batch.column(PMXT_V2_SIDE_COLUMN).to_pylist():
                if value is not None and value not in PMXT_V2_VALID_SIDES:
                    raise _PmxtFailure("EXTERNAL_SOURCE_EVENT_INVALID")

        epochs = batch.column("timestamp").cast(pa.int64())
        batch_min = pc.min(epochs).as_py()
        batch_max = pc.max(epochs).as_py()
        if batch_min is not None:
            min_epoch = batch_min if min_epoch is None else min(min_epoch, batch_min)
            max_epoch = batch_max if max_epoch is None else max(max_epoch, batch_max)
        total_rows += batch.num_rows

    if total_rows == 0 or min_epoch is None or max_epoch is None:
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    return total_rows, _epoch_to_utc(min_epoch, ts_unit), _epoch_to_utc(max_epoch, ts_unit)


def _file_sha256_and_length(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    length = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1_048_576)
            if not chunk:
                break
            length += len(chunk)
            hasher.update(chunk)
    return hasher.hexdigest(), length


def _normalize_local_path(path: object) -> Path:
    import os

    if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    resolved = Path(raw)
    if resolved.is_symlink() or not resolved.exists() or not resolved.is_file():
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    if resolved.stat().st_size <= 0:
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    return resolved


def _isoformat_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


# ── Public adapter ───────────────────────────────────────────────────────────


def revalidate_pmxt_v2_source_hash(path: object, expected_sha256: object) -> bool:
    """Return True only if a local file's exact content hash still matches."""

    if not (isinstance(expected_sha256, str) and len(expected_sha256) == 64):
        return False
    try:
        resolved = _normalize_local_path(path)
        actual, _ = _file_sha256_and_length(resolved)
    except _PmxtFailure:
        return False
    return actual == expected_sha256


def validate_and_describe_pmxt_v2_archive(
    source_files: object,
    *,
    quality_tier: str,
    known_gap_policy: str,
    license_id: str,
    attribution: str,
    dataset_version: str = PMXT_V2_DATASET_VERSION,
    source_class: str = PMXT_V2_SOURCE_CLASS,
) -> PmxtV2DescribeResult:
    """Validate local pmxt v2 Parquet objects and build their external descriptor.

    ``source_files`` is a sequence of :class:`PmxtV2SourceFile`. The files are
    never rewritten; DuckDB/Polars are expected to scan the verified source files
    directly. pmxt v2 is always a third-party native frame archive described under
    the locked ``v2`` version; a native official capture class, or an arbitrary
    version label, is refused as unsupported.
    """

    if source_class != PMXT_V2_SOURCE_CLASS or dataset_version != PMXT_V2_DATASET_VERSION:
        return _rejected("EXTERNAL_SOURCE_UNSUPPORTED")
    if type(source_files) not in (list, tuple) or not source_files:
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")
    files = tuple(source_files)
    if any(type(entry) is not PmxtV2SourceFile for entry in files):
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")

    fingerprint: str | None = None
    objects: list[ExternalSourceObject] = []
    total_rows = 0
    coverage_min: datetime | None = None
    coverage_max: datetime | None = None

    try:
        for entry in files:
            resolved = _normalize_local_path(entry.path)
            source_sha256, byte_length = _file_sha256_and_length(resolved)
            # Open explicitly so the handle is always closed (pyarrow's ParquetFile
            # otherwise leaves a lingering handle that locks the file on Windows).
            try:
                with resolved.open("rb") as handle:
                    parquet_file = pq.ParquetFile(handle)
                    schema = parquet_file.schema_arrow
                    _validate_schema(schema)
                    file_fingerprint = pmxt_v2_schema_fingerprint(schema)
                    if fingerprint is None:
                        fingerprint = file_fingerprint
                    elif file_fingerprint != fingerprint:
                        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
                    rows, min_ts, max_ts = _validate_and_scan_file(parquet_file, schema)
            except _PmxtFailure:
                raise
            except Exception:
                raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID") from None

            total_rows += rows
            if coverage_min is None or min_ts < coverage_min:
                coverage_min = min_ts
            if coverage_max is None or max_ts > coverage_max:
                coverage_max = max_ts
            objects.append(
                ExternalSourceObject(
                    object_name=entry.object_name,
                    source_sha256=source_sha256,
                    byte_length=byte_length,
                    partition_identity=entry.partition_identity,
                )
            )
    except _PmxtFailure as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")

    assert fingerprint is not None and coverage_min is not None and coverage_max is not None
    coverage_start = _isoformat_utc(coverage_min)
    coverage_end = _isoformat_utc(coverage_max)
    if valid_utc_timestamp(coverage_start) is None or valid_utc_timestamp(coverage_end) is None:
        return _rejected("EXTERNAL_SOURCE_TIMESTAMP_INVALID")

    built: ExternalDatasetBuildResult = build_external_dataset_descriptor(
        provider_id=PMXT_V2_PROVIDER_ID,
        dataset_name=PMXT_V2_DATASET_NAME,
        dataset_version=PMXT_V2_DATASET_VERSION,
        source_class=PMXT_V2_SOURCE_CLASS,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        source_objects=tuple(objects),
        source_schema_fingerprint_sha256=fingerprint,
        source_timestamp_semantics=PMXT_V2_SOURCE_TIMESTAMP_SEMANTICS,
        receive_timestamp_semantics=PMXT_V2_RECEIVE_TIMESTAMP_SEMANTICS,
        event_types=PMXT_V2_EVENT_TYPES,
        known_gap_policy=known_gap_policy,
        quality_tier=quality_tier,
        importer_id=PMXT_V2_IMPORTER_ID,
        importer_version=PMXT_V2_IMPORTER_VERSION,
        license_id=license_id,
        attribution=attribution,
    )
    if not built.is_valid or built.descriptor is None:
        return _rejected(*(built.error_codes or ("EXTERNAL_DESCRIPTOR_INVALID",)))

    return PmxtV2DescribeResult(
        is_valid=True,
        status="PMXT_V2_DESCRIBED",
        error_codes=(),
        descriptor=built.descriptor,
        total_row_count=total_rows,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        advisory_only=True,
        no_execution_authority=True,
    )
