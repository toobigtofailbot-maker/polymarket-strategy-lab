"""WP167 pmxt v2 Polymarket Orderbook Archive representative external adapter.

This adapter proves the generic external-history boundary with exactly one
representative, high-value, Parquet-native source: the pmxt Polymarket Orderbook
Archive v2. It accepts only explicitly supplied LOCAL Parquet file paths. It
performs NO URL retrieval, NO HTTP, NO Polymarket API call, NO object-store SDK,
and NO downloader of any kind — its imports are PyArrow (metadata + bounded
batched scans), the standard library, and the sibling external-descriptor module.

For each file it computes the exact source content hash and byte length,
inspects the Arrow/Parquet schema without materializing the whole file, validates
the required columns and their types, validates event types, UTC timestamps, and
decimal/side semantics through bounded batched scans, records the schema
fingerprint, and rejects unsupported material schema drift. Real pmxt files are
large, so nothing is ever read into a single whole-file Python list; row access is
metadata-first and batched at ``MAX_ROW_BATCH``.

pmxt v2 is always classified ``THIRD_PARTY_NATIVE_FRAME_ARCHIVE``; a request to
describe it as a native official capture is refused. Every result fixes
``advisory_only=True`` and ``no_execution_authority=True`` and never echoes an
absolute path, raw source row, exception text, or environment value.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from ..point_in_time_market_research import canonical_json_bytes, sha256_hex
from .external_dataset import (
    ExternalDatasetBuildResult,
    ExternalSourceObject,
    build_external_dataset_descriptor,
    valid_utc_timestamp,
)
from .research_dataset import MAX_ROW_BATCH

# ── Locked pmxt v2 contract ──────────────────────────────────────────────────

PMXT_V2_ADAPTER_LABEL = "PMXT_V2_POLYMARKET_ORDERBOOK_ARCHIVE"
PMXT_V2_ADAPTER_POSTURE = "LOCAL_OFFLINE_PARQUET_ONLY_NO_DOWNLOADER_NO_NETWORK"

PMXT_V2_PROVIDER_ID = "pmxt"
PMXT_V2_DATASET_NAME = "pmxt_polymarket_orderbook_archive"
PMXT_V2_DATASET_VERSION = "v2"
PMXT_V2_SOURCE_CLASS = "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
PMXT_V2_IMPORTER_ID = "wp167-pmxt-v2-adapter"
PMXT_V2_IMPORTER_VERSION = "1.0.0"
PMXT_V2_SOURCE_TIMESTAMP_SEMANTICS = "SOURCE_EVENT_TIME_UTC"
PMXT_V2_RECEIVE_TIMESTAMP_SEMANTICS = "EXPORTER_RECEIVE_TIME_UTC"

PMXT_V2_REQUIRED_COLUMNS = (
    "timestamp_received",
    "timestamp",
    "market",
    "event_type",
    "asset_id",
)
PMXT_V2_TIMESTAMP_COLUMNS = ("timestamp_received", "timestamp")
PMXT_V2_STRING_REQUIRED_COLUMNS = ("market", "asset_id")
PMXT_V2_EVENT_TYPES = ("book", "price_change", "last_trade_price", "tick_size_change")
PMXT_V2_DECIMAL_COLUMNS = (
    "price",
    "size",
    "best_bid",
    "best_ask",
    "fee_rate_bps",
    "old_tick_size",
    "new_tick_size",
)
PMXT_V2_SIDE_COLUMN = "side"
PMXT_V2_VALID_SIDES = ("BUY", "SELL")

_UTC_TZ_NAMES = frozenset({"UTC", "Etc/UTC", "+00:00", "Z", "00:00"})

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


# ── Schema fingerprint and column-type validation ────────────────────────────


def pmxt_v2_schema_fingerprint(schema: pa.Schema) -> str:
    descriptor = [[field.name, str(field.type)] for field in schema]
    return sha256_hex(canonical_json_bytes(descriptor))


def _is_string_type(dtype: pa.DataType) -> bool:
    if pa.types.is_string(dtype) or pa.types.is_large_string(dtype):
        return True
    return pa.types.is_dictionary(dtype) and (
        pa.types.is_string(dtype.value_type) or pa.types.is_large_string(dtype.value_type)
    )


def _is_utc_timestamp_type(dtype: pa.DataType) -> bool:
    return pa.types.is_timestamp(dtype) and dtype.tz is not None and (
        dtype.tz in _UTC_TZ_NAMES or dtype.tz.upper() == "UTC"
    )


def _validate_schema(schema: pa.Schema) -> None:
    names = set(schema.names)
    for required in PMXT_V2_REQUIRED_COLUMNS:
        if required not in names:
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
    for column in PMXT_V2_TIMESTAMP_COLUMNS:
        if not _is_utc_timestamp_type(schema.field(column).type):
            # A non-UTC or non-timestamp source-time column is a timestamp fault,
            # not a generic schema fault.
            dtype = schema.field(column).type
            if pa.types.is_timestamp(dtype):
                raise _PmxtFailure("EXTERNAL_SOURCE_TIMESTAMP_INVALID")
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
    if not _is_string_type(schema.field("event_type").type):
        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
    for column in PMXT_V2_STRING_REQUIRED_COLUMNS:
        if not _is_string_type(schema.field(column).type):
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
    # Optional decimal-bearing columns must never be stored as binary float, which
    # would forfeit exact decimal identity.
    for column in PMXT_V2_DECIMAL_COLUMNS:
        if column in names and pa.types.is_floating(schema.field(column).type):
            raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
    if PMXT_V2_SIDE_COLUMN in names and not _is_string_type(
        schema.field(PMXT_V2_SIDE_COLUMN).type
    ):
        raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")


# ── Bounded row-level validation ─────────────────────────────────────────────


def _decimal_ok(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, Decimal):
        return True
    if isinstance(value, str):
        try:
            Decimal(value)
            return True
        except InvalidOperation:
            return False
    # int is exact; float (binary) is decimal-unsafe and never accepted here.
    if isinstance(value, bool):
        return False
    return isinstance(value, int)


def _validate_and_scan_file(
    parquet_file: pq.ParquetFile, present_columns: set[str]
) -> tuple[int, Any, Any]:
    """Batched validation of one pmxt file; returns (rows, min_ts, max_ts).

    Never reads the whole file into one Python list; each batch is bounded by
    ``MAX_ROW_BATCH``. Raises ``_PmxtFailure`` with a closed code on any fault.
    """

    scan_columns = [
        column
        for column in (
            "event_type",
            "timestamp",
            "market",
            "asset_id",
            PMXT_V2_SIDE_COLUMN,
            *PMXT_V2_DECIMAL_COLUMNS,
        )
        if column in present_columns
    ]
    total_rows = 0
    min_ts: Any = None
    max_ts: Any = None
    decimal_present = [c for c in PMXT_V2_DECIMAL_COLUMNS if c in present_columns]
    side_present = PMXT_V2_SIDE_COLUMN in present_columns

    for batch in parquet_file.iter_batches(
        batch_size=MAX_ROW_BATCH, columns=scan_columns
    ):
        event_types = batch.column("event_type").to_pylist()
        for value in event_types:
            if value is None:
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
            if value not in PMXT_V2_EVENT_TYPES:
                raise _PmxtFailure("EXTERNAL_SOURCE_EVENT_INVALID")
        for column in ("market", "asset_id"):
            for value in batch.column(column).to_pylist():
                if value is None:
                    raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
        timestamps = batch.column("timestamp").to_pylist()
        for value in timestamps:
            if value is None:
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
            if getattr(value, "tzinfo", None) is None:
                raise _PmxtFailure("EXTERNAL_SOURCE_TIMESTAMP_INVALID")
            if value.utcoffset().total_seconds() != 0:
                raise _PmxtFailure("EXTERNAL_SOURCE_TIMESTAMP_INVALID")
            if min_ts is None or value < min_ts:
                min_ts = value
            if max_ts is None or value > max_ts:
                max_ts = value
        if side_present:
            for value in batch.column(PMXT_V2_SIDE_COLUMN).to_pylist():
                if value is not None and value not in PMXT_V2_VALID_SIDES:
                    raise _PmxtFailure("EXTERNAL_SOURCE_EVENT_INVALID")
        for column in decimal_present:
            for value in batch.column(column).to_pylist():
                if not _decimal_ok(value):
                    raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")
        total_rows += batch.num_rows

    if total_rows == 0 or min_ts is None or max_ts is None:
        raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID")
    return total_rows, min_ts, max_ts


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


def _isoformat_utc(value: Any) -> str:
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
    directly. pmxt v2 is always a third-party native frame archive; requesting a
    native official capture class is refused as unsupported.
    """

    if source_class != PMXT_V2_SOURCE_CLASS:
        return _rejected("EXTERNAL_SOURCE_UNSUPPORTED")
    if type(source_files) not in (list, tuple) or not source_files:
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")
    files = tuple(source_files)
    if any(type(entry) is not PmxtV2SourceFile for entry in files):
        return _rejected("EXTERNAL_SOURCE_FILE_INVALID")

    fingerprint: str | None = None
    objects: list[ExternalSourceObject] = []
    total_rows = 0
    coverage_min: Any = None
    coverage_max: Any = None

    try:
        for entry in files:
            resolved = _normalize_local_path(entry.path)
            try:
                parquet_file = pq.ParquetFile(resolved)
            except Exception:
                raise _PmxtFailure("EXTERNAL_SOURCE_FILE_INVALID") from None
            schema = parquet_file.schema_arrow
            _validate_schema(schema)

            file_fingerprint = pmxt_v2_schema_fingerprint(schema)
            if fingerprint is None:
                fingerprint = file_fingerprint
            elif file_fingerprint != fingerprint:
                raise _PmxtFailure("EXTERNAL_SOURCE_SCHEMA_INVALID")

            rows, min_ts, max_ts = _validate_and_scan_file(
                parquet_file, set(schema.names)
            )
            total_rows += rows
            if coverage_min is None or min_ts < coverage_min:
                coverage_min = min_ts
            if coverage_max is None or max_ts > coverage_max:
                coverage_max = max_ts

            source_sha256, byte_length = _file_sha256_and_length(resolved)
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
        dataset_version=dataset_version,
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
