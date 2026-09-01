"""WP167 canonical point-in-time -> derived research Parquet materialization.

This module is the local, offline, read-only-against-canonical, derived-data
writer for the WP167 analytical research plane. It reads verified canonical
point-in-time evidence exclusively through the merged WP163 public API, projects
it into deterministic Arrow tables that preserve the COMPLETE canonical
``PointInTimeEnvelope`` provenance/lineage semantics and all record-family fields,
and writes derived Parquet partitions whose *logical* identity is defined by the
canonical record content and explicit row order, never by the physical Parquet
bytes.

Authority posture: LOCAL, OFFLINE, READ-ONLY AGAINST CANONICAL PIT,
DERIVED-DATA WRITER ONLY, NO EXECUTION AUTHORITY. It never writes the canonical
SQLite/manifest stores, never opens a socket, never downloads anything, never
imports NautilusTrader, and never runs a strategy. Every public result fixes
``advisory_only=True`` and ``no_execution_authority=True``.

Canonical SQLite records and manifests remain the sole integrity authority.
Parquet produced here is derived analytical materialization only and can never
silently become canonical repo truth.

DuckDB is imported lazily inside the query helpers only. The native DuckDB
extension is blocked on some local Windows environments by Smart App Control;
importing this module (or scanning PyArrow/Polars tests) must never require
DuckDB, so the eager module-level imports are PyArrow and Polars only.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from ..point_in_time_market_research import (
    DATASET_MATERIALIZATION_VERIFICATION_MODES,
    DatasetSnapshotReference,
    MarketObservationRecord,
    ResolutionRuleSnapshotRecord,
    SourceSnapshotRecord,
    canonical_json_bytes,
    load_and_verify_point_in_time_record_store,
    materialize_dataset_snapshot_reference,
    sha256_hex,
)

# ── Locked labels, posture, and versions ─────────────────────────────────────

ANALYTICAL_RESEARCH_LABEL = "ANALYTICAL_RESEARCH_DERIVED_MATERIALIZATION"
ANALYTICAL_RESEARCH_POSTURE = (
    "LOCAL_OFFLINE_READ_ONLY_CANONICAL_DERIVED_PARQUET_WRITER_NO_EXECUTION_AUTHORITY"
)

ANALYTICAL_DATASET_SCHEMA_ID = "polymarket-analytical-research-dataset"
ANALYTICAL_DATASET_SCHEMA_VERSION = "1.0.0"
ANALYTICAL_SCHEMA_VERSION = "1.0.0"
ANALYTICAL_MATERIALIZER_VERSION = "wp167-analytical-materializer/1.0.0"

ANALYTICAL_LOGICAL_DATASET_ID_PREFIX = "analyticaldataset:sha256:"

SOURCE_KIND_CANONICAL_PIT = "CANONICAL_PIT_DATASET_SNAPSHOT_REFERENCE"

# Exact WP167 direct runtime dependency pins.
EXPECTED_PYARROW_VERSION = "25.0.1"
EXPECTED_DUCKDB_VERSION = "1.5.5"
EXPECTED_POLARS_VERSION = "1.44.1"
SUPPORTED_PYTHON_MIN = (3, 12)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 15)

ANALYTICAL_RESEARCH_STATUSES = (
    "ANALYTICAL_MATERIALIZED",
    "ANALYTICAL_RUNTIME_SUPPORTED",
    "ANALYTICAL_FILE_INTEGRITY_VERIFIED",
    "ANALYTICAL_REJECTED",
)

ANALYTICAL_RESEARCH_ERROR_CODES = (
    "ANALYTICAL_INPUT_INVALID",
    "ANALYTICAL_CANONICAL_STORE_INVALID",
    "ANALYTICAL_REFERENCE_INVALID",
    "ANALYTICAL_MATERIALIZATION_FAILED",
    "ANALYTICAL_SCHEMA_INVALID",
    "ANALYTICAL_IDENTITY_MISMATCH",
    "ANALYTICAL_FILE_INTEGRITY_INVALID",
    "ANALYTICAL_QUERY_VALIDATION_FAILED",
    "ANALYTICS_DEPENDENCY_VERSION_INVALID",
    "ANALYTICS_RUNTIME_UNSUPPORTED",
)
_ERROR_ORDER = {code: index for index, code in enumerate(ANALYTICAL_RESEARCH_ERROR_CODES)}

# Deterministic derived-table families (schema v1). The ordinary families are
# split by record family; conflict records go to a single review table.
TABLE_MARKET_OBSERVATIONS = "market_observations"
TABLE_SOURCE_SNAPSHOTS = "source_snapshots"
TABLE_RESOLUTION_RULE_SNAPSHOTS = "resolution_rule_snapshots"
TABLE_REVIEW_CONFLICTS = "review_conflicts"

# Fixed deterministic table order for identity and iteration.
ANALYTICAL_TABLE_ORDER = (
    TABLE_MARKET_OBSERVATIONS,
    TABLE_SOURCE_SNAPSHOTS,
    TABLE_RESOLUTION_RULE_SNAPSHOTS,
    TABLE_REVIEW_CONFLICTS,
)

_FAMILY_TO_ORDINARY_TABLE = {
    "MARKET_OBSERVATION": TABLE_MARKET_OBSERVATIONS,
    "SOURCE_SNAPSHOT": TABLE_SOURCE_SNAPSHOTS,
    "RESOLUTION_RULE_SNAPSHOT": TABLE_RESOLUTION_RULE_SNAPSHOTS,
}

# Bounded batch size for any explicit row iteration (WP167 Section 17).
MAX_ROW_BATCH = 131_072

_PARQUET_COMPRESSION = "zstd"

# ── Complete canonical projection schema (WP167 Blocker A) ───────────────────
# Every derived row retains the COMPLETE canonical PointInTimeEnvelope semantics,
# the record-family fields, and canonical_payload_json. Family columns are
# namespaced by family (mo_/ss_/rr_) so envelope/family and cross-family names
# never collide and the review-conflicts union table stays lossless.

# Envelope columns, in canonical PointInTimeEnvelope field order.
_ENVELOPE_COLUMNS = (
    "schema_id",
    "schema_version",
    "record_family",
    "record_version_id",
    "observation_id",
    "snapshot_id",
    "source_snapshot_id",
    "resolution_rule_snapshot_id",
    "ingestion_batch_id",
    "event_time",
    "observed_time",
    "ingestion_time",
    "lifecycle_state",
    "classification",
    "supersedes_record_version_id",
    "lineage_parent_ids",
    "canonical_payload_sha256",
    "source_content_sha256",
    "normalizer_version",
    "validator_version",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)
_ENVELOPE_BOOL_COLUMNS = frozenset(
    {"human_review_required", "advisory_only", "no_execution_authority"}
)
_ENVELOPE_LIST_COLUMNS = frozenset({"lineage_parent_ids"})

_COMMON_COLUMNS = _ENVELOPE_COLUMNS + ("analytical_role",)

# Family column specs: (analytical column name, record attribute, kind).
# kind is "str" | "int" | "list".
_FAMILY_COLUMN_SPECS: dict[str, tuple[tuple[str, str, str], ...]] = {
    TABLE_MARKET_OBSERVATIONS: (
        ("mo_observation_kind", "observation_kind", "str"),
        ("mo_platform_id", "platform_id", "str"),
        ("mo_event_id", "event_id", "str"),
        ("mo_market_id", "market_id", "str"),
        ("mo_token_id", "token_id", "str"),
        ("mo_source_id", "source_id", "str"),
        ("mo_source_assertion_id", "source_assertion_id", "str"),
    ),
    TABLE_SOURCE_SNAPSHOTS: (
        ("ss_source_id", "source_id", "str"),
        ("ss_source_type", "source_type", "str"),
        ("ss_source_reference", "source_reference", "str"),
        ("ss_media_type", "media_type", "str"),
        ("ss_raw_content_sha256", "raw_content_sha256", "str"),
        ("ss_byte_length", "byte_length", "int"),
        ("ss_retrieval_method", "retrieval_method", "str"),
        ("ss_retrieval_version", "retrieval_version", "str"),
        ("ss_upstream_revision", "upstream_revision", "str"),
        ("ss_prior_source_snapshot_id", "prior_source_snapshot_id", "str"),
        ("ss_access_classification", "access_classification", "str"),
    ),
    TABLE_RESOLUTION_RULE_SNAPSHOTS: (
        ("rr_platform_id", "platform_id", "str"),
        ("rr_event_id", "event_id", "str"),
        ("rr_market_id", "market_id", "str"),
        ("rr_resolution_source_id", "resolution_source_id", "str"),
        ("rr_source_snapshot_id", "source_snapshot_id", "str"),
        ("rr_rule_content_sha256", "rule_content_sha256", "str"),
        ("rr_source_declared_effective_time", "source_declared_effective_time", "str"),
        ("rr_ambiguity_labels", "ambiguity_labels", "list"),
        ("rr_source_hierarchy_rank", "source_hierarchy_rank", "str"),
        ("rr_human_review_state", "human_review_state", "str"),
    ),
}

# The review-conflicts union preserves every family's complete columns.
_REVIEW_FAMILY_SPECS: tuple[tuple[str, str, str], ...] = (
    _FAMILY_COLUMN_SPECS[TABLE_MARKET_OBSERVATIONS]
    + _FAMILY_COLUMN_SPECS[TABLE_SOURCE_SNAPSHOTS]
    + _FAMILY_COLUMN_SPECS[TABLE_RESOLUTION_RULE_SNAPSHOTS]
)

# Derived analytical UTC timestamp columns (physical only; excluded from logical
# identity so identity stays defined by canonical string fields). Stored tz-naive
# (UTC wall-clock) so DuckDB/Polars queries need no timezone database.
_UTC_TIMESTAMP_COLUMNS = ("observed_time_utc", "ingestion_time_utc", "event_time_utc")
_UTC_SOURCE = {
    "observed_time_utc": "observed_time",
    "ingestion_time_utc": "ingestion_time",
    "event_time_utc": "event_time",
}


def _family_specs_for_table(table_name: str) -> tuple[tuple[str, str, str], ...]:
    if table_name == TABLE_REVIEW_CONFLICTS:
        return _REVIEW_FAMILY_SPECS
    return _FAMILY_COLUMN_SPECS[table_name]


def _table_columns(table_name: str) -> tuple[str, ...]:
    family = tuple(col for col, _attr, _kind in _family_specs_for_table(table_name))
    return _COMMON_COLUMNS + family + _UTC_TIMESTAMP_COLUMNS + ("canonical_payload_json",)


def _column_arrow_type(name: str) -> pa.DataType:
    if name in _UTC_TIMESTAMP_COLUMNS:
        return pa.timestamp("us")
    if name in _ENVELOPE_BOOL_COLUMNS:
        return pa.bool_()
    if name in _ENVELOPE_LIST_COLUMNS:
        return pa.list_(pa.string())
    for specs in (_REVIEW_FAMILY_SPECS,):
        for col, _attr, kind in specs:
            if col == name:
                if kind == "int":
                    return pa.int64()
                if kind == "list":
                    return pa.list_(pa.string())
                return pa.string()
    return pa.string()


# ── Public immutable result dataclasses ──────────────────────────────────────


@dataclass(frozen=True)
class AnalyticalPartitionManifest:
    table_name: str
    relative_path: str
    row_count: int
    logical_rows_sha256: str
    parquet_file_sha256: str
    parquet_byte_length: int
    schema_fingerprint_sha256: str


@dataclass(frozen=True)
class AnalyticalDatasetManifest:
    schema_id: str
    schema_version: str
    logical_dataset_id: str
    source_kind: str
    source_reference_id: str
    analytical_schema_version: str
    materializer_version: str
    partition_manifests: tuple[AnalyticalPartitionManifest, ...]
    total_row_count: int
    pyarrow_version: str
    duckdb_version: str
    polars_version: str
    python_version: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class AnalyticalMaterializationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    manifest: AnalyticalDatasetManifest | None
    logical_dataset_id: str | None
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class AnalyticalRuntimeCompatibilityResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    pyarrow_version: str | None
    duckdb_version: str | None
    polars_version: str | None
    python_version: str | None
    advisory_only: bool
    no_execution_authority: bool


# ── Result constructors ──────────────────────────────────────────────────────


def _order(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, len(_ERROR_ORDER))))


def _rejected(*codes: str) -> AnalyticalMaterializationResult:
    return AnalyticalMaterializationResult(
        is_valid=False,
        status="ANALYTICAL_REJECTED",
        error_codes=_order(codes),
        manifest=None,
        logical_dataset_id=None,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Dependency / runtime compatibility ───────────────────────────────────────


def _installed_version(distribution: str) -> str | None:
    """Return an installed distribution version without importing its module.

    Uses packaging metadata only, so the DuckDB version is reported even when the
    native DuckDB extension cannot load in the local environment.
    """

    try:
        return importlib.metadata.version(distribution)
    except Exception:
        return None


def check_analytical_runtime() -> AnalyticalRuntimeCompatibilityResult:
    """Verify the exact WP167 dependency pins and the supported Python floor.

    This never imports the DuckDB native module; it inspects packaging metadata,
    so it succeeds in environments where the DuckDB shared library is blocked.
    """

    py = platform.python_version()
    info = (
        int(platform.python_version_tuple()[0]),
        int(platform.python_version_tuple()[1]),
    )
    pyarrow_v = _installed_version("pyarrow")
    duckdb_v = _installed_version("duckdb")
    polars_v = _installed_version("polars")

    codes: list[str] = []
    if not (SUPPORTED_PYTHON_MIN <= info < SUPPORTED_PYTHON_MAX_EXCLUSIVE):
        codes.append("ANALYTICS_RUNTIME_UNSUPPORTED")
    if pyarrow_v != EXPECTED_PYARROW_VERSION:
        codes.append("ANALYTICS_DEPENDENCY_VERSION_INVALID")
    if duckdb_v != EXPECTED_DUCKDB_VERSION:
        codes.append("ANALYTICS_DEPENDENCY_VERSION_INVALID")
    if polars_v != EXPECTED_POLARS_VERSION:
        codes.append("ANALYTICS_DEPENDENCY_VERSION_INVALID")

    if codes:
        return AnalyticalRuntimeCompatibilityResult(
            is_valid=False,
            status="ANALYTICAL_REJECTED",
            error_codes=_order(tuple(codes)),
            pyarrow_version=pyarrow_v,
            duckdb_version=duckdb_v,
            polars_version=polars_v,
            python_version=py,
            advisory_only=True,
            no_execution_authority=True,
        )
    return AnalyticalRuntimeCompatibilityResult(
        is_valid=True,
        status="ANALYTICAL_RUNTIME_SUPPORTED",
        error_codes=(),
        pyarrow_version=pyarrow_v,
        duckdb_version=duckdb_v,
        polars_version=polars_v,
        python_version=py,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Deterministic timestamp parsing (UTC analytical convenience columns) ──────


def _parse_utc(value: object) -> datetime | None:
    """Parse a canonical RFC3339/ISO-8601 UTC string into an aware UTC datetime.

    Returns ``None`` for a null event time. Any non-UTC or unparseable value
    raises ``ValueError`` so a materialization fails closed rather than silently
    storing an ambiguous timestamp.
    """

    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty string or None")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    if parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


# ── Canonical + family projection ────────────────────────────────────────────


def _envelope_value(record: Any, name: str) -> object:
    value = getattr(record.envelope, name)
    if name in _ENVELOPE_LIST_COLUMNS:
        return list(value)
    if name in _ENVELOPE_BOOL_COLUMNS:
        return bool(value)
    return value


def _family_value(record: Any, attr: str, kind: str) -> object:
    value = getattr(record, attr)
    if kind == "list":
        return None if value is None else list(value)
    if kind == "int":
        return None if value is None else int(value)
    return value


def _row_values(record: Any, table_name: str, role: str) -> dict[str, object]:
    """Return the full analytical column->value map for one record.

    Includes the complete envelope, the analytical role, the family fields (the
    record's own family for the review-conflicts union, with other families'
    columns null), the derived tz-naive UTC timestamps, and canonical_payload_json.
    """

    row: dict[str, object] = {}
    for name in _ENVELOPE_COLUMNS:
        row[name] = _envelope_value(record, name)
    row["analytical_role"] = role

    active_table = _FAMILY_TO_ORDINARY_TABLE[record.envelope.record_family]
    if table_name == TABLE_REVIEW_CONFLICTS:
        for owner in (
            TABLE_MARKET_OBSERVATIONS,
            TABLE_SOURCE_SNAPSHOTS,
            TABLE_RESOLUTION_RULE_SNAPSHOTS,
        ):
            for col, attr, kind in _FAMILY_COLUMN_SPECS[owner]:
                row[col] = (
                    _family_value(record, attr, kind) if owner == active_table else None
                )
    else:
        for col, attr, kind in _FAMILY_COLUMN_SPECS[table_name]:
            row[col] = _family_value(record, attr, kind)

    for name in _UTC_TIMESTAMP_COLUMNS:
        parsed = _parse_utc(getattr(record.envelope, _UTC_SOURCE[name]))
        row[name] = parsed.replace(tzinfo=None) if parsed is not None else None
    row["canonical_payload_json"] = record.canonical_payload_json
    return row


def _logical_row(record: Any, table_name: str, role: str) -> dict[str, object]:
    """Return the canonical logical row dict used for deterministic identity.

    Commits the complete envelope provenance/lineage, the family fields, and the
    exact canonical payload string. The derived UTC timestamp columns are physical
    conveniences and are intentionally excluded so logical identity is byte-stable
    across platforms and independent of the physical Parquet writer.
    """

    values = _row_values(record, table_name, role)
    return {name: values[name] for name in values if name not in _UTC_TIMESTAMP_COLUMNS}


def _logical_rows_sha256(rows: list[dict[str, object]]) -> str:
    """Bounded streaming digest over rows in canonical record-version-id order."""

    ordered = sorted(rows, key=lambda row: row["record_version_id"])
    hasher = hashlib.sha256()
    hasher.update(str(len(ordered)).encode("utf-8"))
    for row in ordered:
        hasher.update(b"\x00")
        hasher.update(sha256_hex(canonical_json_bytes(row)).encode("ascii"))
    return hasher.hexdigest()


# ── Arrow schema and table construction ──────────────────────────────────────


def _arrow_schema(table_name: str) -> pa.Schema:
    return pa.schema(
        [pa.field(name, _column_arrow_type(name)) for name in _table_columns(table_name)]
    )


def _schema_fingerprint(schema: pa.Schema) -> str:
    descriptor = [[field.name, str(field.type)] for field in schema]
    return sha256_hex(canonical_json_bytes(descriptor))


def _build_arrow_table(records: list[Any], table_name: str, role: str) -> pa.Table:
    columns = _table_columns(table_name)
    schema = _arrow_schema(table_name)
    ordered = sorted(records, key=lambda record: record.envelope.record_version_id)

    data: dict[str, list[object]] = {name: [] for name in columns}
    for record in ordered:
        row = _row_values(record, table_name, role)
        for name in columns:
            data[name].append(row[name])
    arrays = [pa.array(data[name], type=schema.field(name).type) for name in columns]
    return pa.table(arrays, schema=schema)


def _write_parquet(table: pa.Table, path: Path) -> None:
    pq.write_table(
        table,
        path,
        compression=_PARQUET_COMPRESSION,
        version="2.6",
        write_statistics=True,
    )


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


# ── Output-directory boundary ────────────────────────────────────────────────


def _normalize_output_directory(output_directory: object) -> Path | None:
    try:
        import os

        if isinstance(output_directory, (bool, bytes)) or not isinstance(
            output_directory, (str, os.PathLike)
        ):
            return None
        raw = os.fspath(output_directory)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            return None
        path = Path(raw)
        if path.is_symlink() or not path.exists() or not path.is_dir():
            return None
        return path
    except Exception:
        return None


# ── Public materializer ──────────────────────────────────────────────────────


def materialize_canonical_pit_dataset(
    record_store_path: object,
    dataset_reference: object,
    output_directory: object,
) -> AnalyticalMaterializationResult:
    """Materialize a verified WP160 dataset snapshot reference into research Parquet.

    The runtime compatibility (exact dependency pins + supported Python floor) is
    proven from installed package metadata before any derived output is claimed
    successful, and the manifest reports the actual installed versions. The record
    store is verified through the WP163 public API, the reference must be a genuine
    ``DatasetSnapshotReference`` re-materialized through the public materializer, and
    the derived logical dataset identity is defined by canonical record content
    (the complete envelope, family fields, and canonical payload) and explicit row
    order, never by physical Parquet bytes.
    """

    runtime = check_analytical_runtime()
    if not runtime.is_valid:
        return _rejected(*runtime.error_codes)
    if (
        runtime.pyarrow_version is None
        or runtime.duckdb_version is None
        or runtime.polars_version is None
        or runtime.python_version is None
    ):
        return _rejected("ANALYTICS_DEPENDENCY_VERSION_INVALID")

    if type(dataset_reference) is not DatasetSnapshotReference:
        return _rejected("ANALYTICAL_REFERENCE_INVALID")

    out_dir = _normalize_output_directory(output_directory)
    if out_dir is None:
        return _rejected("ANALYTICAL_INPUT_INVALID")

    try:
        loaded = load_and_verify_point_in_time_record_store(record_store_path)
    except Exception:
        return _rejected("ANALYTICAL_CANONICAL_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        return _rejected("ANALYTICAL_CANONICAL_STORE_INVALID")

    try:
        materialized = materialize_dataset_snapshot_reference(
            record_store_path, dataset_reference
        )
    except Exception:
        return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")
    if (
        not materialized.is_valid
        or materialized.status != "DATASET_REFERENCE_MATERIALIZED"
        or materialized.dataset_reference is None
        or materialized.verification_mode
        not in DATASET_MATERIALIZATION_VERIFICATION_MODES
    ):
        return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")

    reference = materialized.dataset_reference

    # Bucket ordinary records by family table; conflict records into the review
    # table, preserving the WP163 ordinary/review role split exactly.
    buckets: dict[str, list[Any]] = {name: [] for name in ANALYTICAL_TABLE_ORDER}
    try:
        for record in materialized.ordinary_records:
            family = record.envelope.record_family
            table_name = _FAMILY_TO_ORDINARY_TABLE.get(family)
            if table_name is None:
                return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")
            if record.envelope.classification == "CONFLICT":
                return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")
            buckets[table_name].append(record)
        for record in materialized.review_conflict_records:
            if record.envelope.classification != "CONFLICT":
                return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")
            buckets[TABLE_REVIEW_CONFLICTS].append(record)
    except Exception:
        return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")

    partitions: list[AnalyticalPartitionManifest] = []
    table_identity: list[dict[str, object]] = []
    total_rows = 0
    try:
        for table_name in ANALYTICAL_TABLE_ORDER:
            records = buckets[table_name]
            role = (
                "REVIEW_CONFLICT"
                if table_name == TABLE_REVIEW_CONFLICTS
                else "ORDINARY"
            )
            logical_rows = [_logical_row(r, table_name, role) for r in records]
            logical_digest = _logical_rows_sha256(logical_rows)
            arrow_table = _build_arrow_table(records, table_name, role)
            relative_path = f"{table_name}.parquet"
            file_path = out_dir / relative_path
            _write_parquet(arrow_table, file_path)
            file_sha, byte_length = _file_sha256_and_length(file_path)
            partitions.append(
                AnalyticalPartitionManifest(
                    table_name=table_name,
                    relative_path=relative_path,
                    row_count=len(records),
                    logical_rows_sha256=logical_digest,
                    parquet_file_sha256=file_sha,
                    parquet_byte_length=byte_length,
                    schema_fingerprint_sha256=_schema_fingerprint(arrow_table.schema),
                )
            )
            table_identity.append(
                {
                    "table_name": table_name,
                    "row_count": len(records),
                    "logical_rows_sha256": logical_digest,
                }
            )
            total_rows += len(records)
    except (ValueError, OSError, pa.ArrowInvalid):
        return _rejected("ANALYTICAL_SCHEMA_INVALID")
    except Exception:
        return _rejected("ANALYTICAL_MATERIALIZATION_FAILED")

    logical_preimage = {
        "analytical_schema_id": ANALYTICAL_DATASET_SCHEMA_ID,
        "analytical_schema_version": ANALYTICAL_SCHEMA_VERSION,
        "source_kind": SOURCE_KIND_CANONICAL_PIT,
        "source_reference_id": reference.dataset_snapshot_reference_id,
        "materializer_version": ANALYTICAL_MATERIALIZER_VERSION,
        "tables": table_identity,
    }
    logical_dataset_id = (
        ANALYTICAL_LOGICAL_DATASET_ID_PREFIX
        + sha256_hex(canonical_json_bytes(logical_preimage))
    )

    manifest = AnalyticalDatasetManifest(
        schema_id=ANALYTICAL_DATASET_SCHEMA_ID,
        schema_version=ANALYTICAL_DATASET_SCHEMA_VERSION,
        logical_dataset_id=logical_dataset_id,
        source_kind=SOURCE_KIND_CANONICAL_PIT,
        source_reference_id=reference.dataset_snapshot_reference_id,
        analytical_schema_version=ANALYTICAL_SCHEMA_VERSION,
        materializer_version=ANALYTICAL_MATERIALIZER_VERSION,
        partition_manifests=tuple(partitions),
        total_row_count=total_rows,
        pyarrow_version=runtime.pyarrow_version,
        duckdb_version=runtime.duckdb_version,
        polars_version=runtime.polars_version,
        python_version=runtime.python_version,
        advisory_only=True,
        no_execution_authority=True,
    )
    return AnalyticalMaterializationResult(
        is_valid=True,
        status="ANALYTICAL_MATERIALIZED",
        error_codes=(),
        manifest=manifest,
        logical_dataset_id=logical_dataset_id,
        advisory_only=True,
        no_execution_authority=True,
    )


def verify_partition_file_integrity(
    partition: object, output_directory: object
) -> tuple[bool, tuple[str, ...]]:
    """Recompute a partition's physical hash/length and compare to its manifest.

    Returns ``(True, ())`` on an exact match, otherwise ``(False, codes)`` with a
    closed error code. No path, byte, or exception text is ever echoed.
    """

    if type(partition) is not AnalyticalPartitionManifest:
        return False, ("ANALYTICAL_INPUT_INVALID",)
    out_dir = _normalize_output_directory(output_directory)
    if out_dir is None:
        return False, ("ANALYTICAL_INPUT_INVALID",)
    file_path = out_dir / partition.relative_path
    try:
        if file_path.is_symlink() or not file_path.is_file():
            return False, ("ANALYTICAL_FILE_INTEGRITY_INVALID",)
        file_sha, byte_length = _file_sha256_and_length(file_path)
    except Exception:
        return False, ("ANALYTICAL_FILE_INTEGRITY_INVALID",)
    if (
        file_sha != partition.parquet_file_sha256
        or byte_length != partition.parquet_byte_length
    ):
        return False, ("ANALYTICAL_FILE_INTEGRITY_INVALID",)
    return True, ()


# ── DuckDB access (lazy import; native module may be blocked locally) ─────────


def _import_duckdb() -> Any:
    """Import the DuckDB module on demand.

    DuckDB is never imported at module load. On environments where the native
    DuckDB extension is blocked (for example Windows Smart App Control), the
    ImportError propagates to the caller, which in the test suite is converted to
    a skip locally and to a hard failure under strict hosted CI.
    """

    import duckdb  # noqa: PLC0415  (intentional lazy import)

    return duckdb


def duckdb_row_count(parquet_path: object) -> int:
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)", [str(parquet_path)]
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


def duckdb_group_count(parquet_path: object, column: str) -> dict[object, int]:
    if not isinstance(column, str) or not column.isidentifier():
        raise ValueError("column must be a plain identifier")
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            f'SELECT "{column}" AS key, COUNT(*) AS n '
            "FROM read_parquet(?) GROUP BY 1 ORDER BY 1",
            [str(parquet_path)],
        ).fetchall()
        return {row[0]: int(row[1]) for row in rows}
    finally:
        connection.close()


def duckdb_timestamp_min_max(
    parquet_path: object, column: str
) -> tuple[object, object]:
    if not isinstance(column, str) or not column.isidentifier():
        raise ValueError("column must be a plain identifier")
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        row = connection.execute(
            f'SELECT MIN("{column}"), MAX("{column}") FROM read_parquet(?)',
            [str(parquet_path)],
        ).fetchone()
        return row[0], row[1]
    finally:
        connection.close()


def duckdb_filter_count(parquet_path: object, column: str, value: object) -> int:
    if not isinstance(column, str) or not column.isidentifier():
        raise ValueError("column must be a plain identifier")
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        row = connection.execute(
            f'SELECT COUNT(*) FROM read_parquet(?) WHERE "{column}" = ?',
            [str(parquet_path), value],
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


# ── Polars access (lazy scans) ───────────────────────────────────────────────


def polars_row_count(parquet_path: object) -> int:
    return int(pl.scan_parquet(str(parquet_path)).select(pl.len()).collect().item())


def polars_group_count(parquet_path: object, column: str) -> dict[object, int]:
    frame = (
        pl.scan_parquet(str(parquet_path))
        .group_by(column)
        .agg(pl.len().alias("n"))
        .sort(column)
        .collect()
    )
    return {row[column]: int(row["n"]) for row in frame.to_dicts()}


def polars_timestamp_min_max(
    parquet_path: object, column: str
) -> tuple[object, object]:
    frame = (
        pl.scan_parquet(str(parquet_path))
        .select(
            pl.col(column).min().alias("min_value"),
            pl.col(column).max().alias("max_value"),
        )
        .collect()
    )
    return frame["min_value"][0], frame["max_value"][0]


def polars_filter_count(parquet_path: object, column: str, value: object) -> int:
    return int(
        pl.scan_parquet(str(parquet_path))
        .filter(pl.col(column) == value)
        .select(pl.len())
        .collect()
        .item()
    )
