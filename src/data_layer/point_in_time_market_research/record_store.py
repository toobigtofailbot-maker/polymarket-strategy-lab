"""Bounded local SQLite persistence for immutable point-in-time record objects.

This module is the first durable append-only store for the actual immutable
WP156/WP157 point-in-time research record objects (``MarketObservationRecord``,
``SourceSnapshotRecord``, ``ResolutionRuleSnapshotRecord``).  It initializes or
validates one explicit caller-selected local SQLite file, appends already-built
records transactionally and idempotently, closes and reopens the store, strictly
reconstructs every persisted immutable record, revalidates every record identity
and cross-record lineage, and materializes a WP160 ``DatasetSnapshotReference``
into the exact durable record objects it names.

The module has no path discovery, environment lookup, migration, retry, WAL,
network, credential, scheduler, strategy, or execution authority.  SQLite's
DELETE journal and explicit ``BEGIN IMMEDIATE`` transactions are the durability
primitive; WP156's public validation and WP160's public reference builder remain
the semantic authority.  Every result fails closed: an invalid result carries
only a fixed status and an ordered tuple of bounded closed error codes, never a
path, SQL string, payload, record repr, exception text, or environment value.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Sequence

from .manifest_reference import (
    DatasetSnapshotReference,
    build_dataset_snapshot_reference,
)
from .records import (
    MarketObservationRecord,
    PointInTimeEnvelope,
    ResolutionRuleSnapshotRecord,
    SourceSnapshotRecord,
    canonical_json_bytes,
    revalidate_review_conflict_record,
    sha256_hex,
    validate_record_batch,
)


# ── Locked labels and posture (WP163) ────────────────────────────────────────

POINT_IN_TIME_RECORD_STORE_LABEL = "POINT_IN_TIME_DURABLE_RECORD_STORE"
POINT_IN_TIME_RECORD_STORE_POSTURE = (
    "BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION"
)
POINT_IN_TIME_RECORD_STORE_FORMAT_ID = "point-in-time-record-store"
POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION = 1

POINT_IN_TIME_RECORD_STORE_STATUSES = (
    "RECORD_STORE_INITIALIZED",
    "RECORD_STORE_ALREADY_INITIALIZED",
    "RECORD_STORE_APPEND_COMMITTED",
    "RECORD_STORE_APPEND_IDEMPOTENT",
    "RECORD_STORE_LOADED_VERIFIED",
    "DATASET_REFERENCE_MATERIALIZED",
    "RECORD_STORE_REJECTED",
)

POINT_IN_TIME_RECORD_STORE_ERROR_CODES = (
    "RECORD_STORE_PATH_INVALID",
    "RECORD_STORE_NOT_FOUND",
    "RECORD_STORE_OPEN_FAILED",
    "RECORD_STORE_BUSY",
    "RECORD_STORE_SCHEMA_UNSUPPORTED",
    "RECORD_STORE_CONFIGURATION_INVALID",
    "RECORD_STORE_SQLITE_INTEGRITY_FAILED",
    "RECORD_STORE_INPUT_INVALID",
    "RECORD_STORE_RECORD_INVALID",
    "RECORD_STORE_PAYLOAD_INVALID",
    "RECORD_STORE_DUPLICATE_CONFLICT",
    "RECORD_STORE_LINEAGE_INVALID",
    "RECORD_STORE_AUTHORITY_VIOLATION",
    "RECORD_STORE_LIMIT_EXCEEDED",
    "RECORD_STORE_REFERENCE_INVALID",
    "RECORD_STORE_REFERENCE_MISSING_RECORD",
    "RECORD_STORE_REFERENCE_CONTENT_MISMATCH",
    "RECORD_STORE_WRITE_FAILED",
)

DATASET_MATERIALIZATION_VERIFICATION_MODES = (
    "VALIDATED_BATCH_RECOMPUTED",
    "AS_OF_REFERENCE_IDS_RESOLVED",
)

_ERROR_ORDER = {
    code: index for index, code in enumerate(POINT_IN_TIME_RECORD_STORE_ERROR_CODES)
}


# ── Bounds (WP163 Section 9) ──────────────────────────────────────────────────

_MAX_RECORDS_PER_APPEND = 256
_MAX_RECORDS_IN_STORE = 4_096
_MAX_PAYLOAD_BYTES_PER_ROW = 131_072
_MAX_TOTAL_PAYLOAD_BYTES = 134_217_728  # 128 MiB


_RECORD_TYPES = (
    MarketObservationRecord,
    SourceSnapshotRecord,
    ResolutionRuleSnapshotRecord,
)
_RECORD_TYPE_NAMES = frozenset(cls.__name__ for cls in _RECORD_TYPES)
_ENVELOPE_FIELD_NAMES = tuple(field.name for field in fields(PointInTimeEnvelope))
_ENVELOPE_FIELD_SET = frozenset(_ENVELOPE_FIELD_NAMES)
# Only these schema-defined record fields are JSON arrays that must be rebuilt as
# tuples; every other rebuilt field is used verbatim.
_TUPLE_FIELDS = {
    "MarketObservationRecord": (),
    "SourceSnapshotRecord": (),
    "ResolutionRuleSnapshotRecord": ("ambiguity_labels",),
}
_ENVELOPE_TUPLE_FIELDS = ("lineage_parent_ids",)
_FAMILY_ORDER = {
    "MARKET_OBSERVATION": 0,
    "SOURCE_SNAPSHOT": 1,
    "RESOLUTION_RULE_SNAPSHOT": 2,
}
_RECORD_TYPE_TO_FAMILY = {
    "MarketObservationRecord": "MARKET_OBSERVATION",
    "SourceSnapshotRecord": "SOURCE_SNAPSHOT",
    "ResolutionRuleSnapshotRecord": "RESOLUTION_RULE_SNAPSHOT",
}


# ── Exact SQLite schema (WP163 Section 12) ────────────────────────────────────

_CREATE_RECORD_STORE_META = """CREATE TABLE record_store_meta (
    singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),
    format_id TEXT NOT NULL CHECK (format_id = 'point-in-time-record-store'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
)"""

_CREATE_RECORDS = """CREATE TABLE records (
    record_version_id TEXT PRIMARY KEY NOT NULL,
    record_type TEXT NOT NULL CHECK (
        record_type IN (
            'MarketObservationRecord',
            'SourceSnapshotRecord',
            'ResolutionRuleSnapshotRecord'
        )
    ),
    record_family TEXT NOT NULL CHECK (
        record_family IN (
            'MARKET_OBSERVATION',
            'SOURCE_SNAPSHOT',
            'RESOLUTION_RULE_SNAPSHOT'
        )
    ),
    classification TEXT NOT NULL,
    human_review_required INTEGER NOT NULL CHECK (human_review_required IN (0,1)),
    observed_time TEXT NOT NULL,
    ingestion_time TEXT NOT NULL,
    event_time TEXT,
    parameter_set_id TEXT NOT NULL,
    validator_version TEXT NOT NULL,
    observation_kind TEXT,
    platform_id TEXT,
    event_id TEXT,
    market_id TEXT,
    token_id TEXT,
    source_id TEXT,
    resolution_source_id TEXT,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL
)"""

_CREATE_INDEX_INGESTION = (
    "CREATE INDEX idx_pit_records_ingestion_time "
    "ON records(ingestion_time, record_version_id)"
)
_CREATE_INDEX_OBSERVED = (
    "CREATE INDEX idx_pit_records_observed_time "
    "ON records(observed_time, record_version_id)"
)
_CREATE_INDEX_EVENT = (
    "CREATE INDEX idx_pit_records_event_time "
    "ON records(event_time, record_version_id)"
)
_CREATE_INDEX_MARKET = (
    "CREATE INDEX idx_pit_records_market_id "
    "ON records(market_id, ingestion_time, record_version_id)"
)
_CREATE_INDEX_SOURCE = (
    "CREATE INDEX idx_pit_records_source_id "
    "ON records(source_id, ingestion_time, record_version_id)"
)

_INDEX_DEFINITIONS = (
    ("idx_pit_records_ingestion_time", _CREATE_INDEX_INGESTION,
     ("ingestion_time", "record_version_id")),
    ("idx_pit_records_observed_time", _CREATE_INDEX_OBSERVED,
     ("observed_time", "record_version_id")),
    ("idx_pit_records_event_time", _CREATE_INDEX_EVENT,
     ("event_time", "record_version_id")),
    ("idx_pit_records_market_id", _CREATE_INDEX_MARKET,
     ("market_id", "ingestion_time", "record_version_id")),
    ("idx_pit_records_source_id", _CREATE_INDEX_SOURCE,
     ("source_id", "ingestion_time", "record_version_id")),
)

_EXPECTED_TABLE_INFO = {
    "record_store_meta": (
        (0, "singleton", "INTEGER", 1, None, 1),
        (1, "format_id", "TEXT", 1, None, 0),
        (2, "schema_version", "INTEGER", 1, None, 0),
    ),
    "records": (
        (0, "record_version_id", "TEXT", 1, None, 1),
        (1, "record_type", "TEXT", 1, None, 0),
        (2, "record_family", "TEXT", 1, None, 0),
        (3, "classification", "TEXT", 1, None, 0),
        (4, "human_review_required", "INTEGER", 1, None, 0),
        (5, "observed_time", "TEXT", 1, None, 0),
        (6, "ingestion_time", "TEXT", 1, None, 0),
        (7, "event_time", "TEXT", 0, None, 0),
        (8, "parameter_set_id", "TEXT", 1, None, 0),
        (9, "validator_version", "TEXT", 1, None, 0),
        (10, "observation_kind", "TEXT", 0, None, 0),
        (11, "platform_id", "TEXT", 0, None, 0),
        (12, "event_id", "TEXT", 0, None, 0),
        (13, "market_id", "TEXT", 0, None, 0),
        (14, "token_id", "TEXT", 0, None, 0),
        (15, "source_id", "TEXT", 0, None, 0),
        (16, "resolution_source_id", "TEXT", 0, None, 0),
        (17, "payload_json", "TEXT", 1, None, 0),
        (18, "payload_sha256", "TEXT", 1, None, 0),
    ),
}

_EXPECTED_OBJECTS = [
    ("index", "idx_pit_records_event_time"),
    ("index", "idx_pit_records_ingestion_time"),
    ("index", "idx_pit_records_market_id"),
    ("index", "idx_pit_records_observed_time"),
    ("index", "idx_pit_records_source_id"),
    ("table", "record_store_meta"),
    ("table", "records"),
]


# ── Immutable public dataclasses (WP163 Section 8) ────────────────────────────


@dataclass(frozen=True)
class PointInTimeRecordStoreSnapshot:
    records: tuple[
        MarketObservationRecord | SourceSnapshotRecord | ResolutionRuleSnapshotRecord,
        ...,
    ]
    ordinary_record_count: int
    review_conflict_record_count: int
    total_payload_bytes: int
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class PointInTimeRecordStoreResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    snapshot: PointInTimeRecordStoreSnapshot | None
    inserted_record_version_ids: tuple[str, ...]
    idempotent_record_version_ids: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class DatasetSnapshotMaterializationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    dataset_reference: DatasetSnapshotReference | None
    ordinary_records: tuple[
        MarketObservationRecord | SourceSnapshotRecord | ResolutionRuleSnapshotRecord,
        ...,
    ]
    review_conflict_records: tuple[
        MarketObservationRecord | SourceSnapshotRecord | ResolutionRuleSnapshotRecord,
        ...,
    ]
    verification_mode: str | None
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


class _StoreFailure(Exception):
    """Internal control-flow exception carrying only a closed error code."""

    def __init__(self, code: str):
        self.code = code


def _ordered_codes(codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, 999)))


def _rejected(*codes: str) -> PointInTimeRecordStoreResult:
    return PointInTimeRecordStoreResult(
        is_valid=False,
        status="RECORD_STORE_REJECTED",
        error_codes=_ordered_codes(codes),
        warning_codes=(),
        snapshot=None,
        inserted_record_version_ids=(),
        idempotent_record_version_ids=(),
        advisory_only=True,
        no_execution_authority=True,
    )


def _valid_result(
    status: str,
    snapshot: PointInTimeRecordStoreSnapshot,
    *,
    inserted: tuple[str, ...] = (),
    idempotent: tuple[str, ...] = (),
) -> PointInTimeRecordStoreResult:
    return PointInTimeRecordStoreResult(
        is_valid=True,
        status=status,
        error_codes=(),
        warning_codes=(),
        snapshot=snapshot,
        inserted_record_version_ids=inserted,
        idempotent_record_version_ids=idempotent,
        advisory_only=True,
        no_execution_authority=True,
    )


def _rejected_materialization(*codes: str) -> DatasetSnapshotMaterializationResult:
    return DatasetSnapshotMaterializationResult(
        is_valid=False,
        status="RECORD_STORE_REJECTED",
        error_codes=_ordered_codes(codes),
        warning_codes=(),
        dataset_reference=None,
        ordinary_records=(),
        review_conflict_records=(),
        verification_mode=None,
        human_review_required=False,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Path contract (WP163 Section 10) ──────────────────────────────────────────


def _normalize_path(path: object, *, must_exist: bool) -> Path:
    try:
        if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
            raise _StoreFailure("RECORD_STORE_PATH_INVALID")
        raw = os.fspath(path)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise _StoreFailure("RECORD_STORE_PATH_INVALID")
        normalized = Path(raw).absolute()
        if normalized.is_symlink():
            raise _StoreFailure("RECORD_STORE_PATH_INVALID")
        if must_exist:
            if not normalized.exists():
                raise _StoreFailure("RECORD_STORE_NOT_FOUND")
            if not normalized.is_file():
                raise _StoreFailure("RECORD_STORE_PATH_INVALID")
        else:
            if normalized.exists() and not normalized.is_file():
                raise _StoreFailure("RECORD_STORE_PATH_INVALID")
            parent = normalized.parent
            if not parent.exists() or not parent.is_dir():
                raise _StoreFailure("RECORD_STORE_PATH_INVALID")
    except _StoreFailure:
        raise
    except Exception:
        raise _StoreFailure("RECORD_STORE_PATH_INVALID") from None
    return normalized


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        raise _StoreFailure("RECORD_STORE_PATH_INVALID") from None


def _remove_created_store(path: Path) -> None:
    """Remove only a regular non-symlink target created by this operation."""

    try:
        if path.is_symlink() or not path.is_file():
            return
        path.unlink()
    except Exception:
        # Cleanup must never replace the original bounded store failure.
        pass


# ── SQLite configuration (WP163 Section 11) ───────────────────────────────────


def _uri(path: Path, mode: str) -> str:
    return f"{path.as_uri()}?mode={mode}"


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    try:
        return sqlite3.connect(
            _uri(path, mode),
            uri=True,
            isolation_level=None,
            timeout=0.0,
        )
    except sqlite3.Error:
        raise _StoreFailure("RECORD_STORE_OPEN_FAILED") from None


def _is_busy(error: sqlite3.Error) -> bool:
    code = getattr(error, "sqlite_errorcode", None)
    return isinstance(code, int) and (code & 0xFF) in {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    }


def _journal_mode(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA journal_mode").fetchone()
    if row is None or len(row) != 1 or not isinstance(row[0], str):
        raise _StoreFailure("RECORD_STORE_CONFIGURATION_INVALID")
    return row[0].lower()


def _require_delete_journal(connection: sqlite3.Connection) -> None:
    if _journal_mode(connection) != "delete":
        raise _StoreFailure("RECORD_STORE_CONFIGURATION_INVALID")


def _configure_writable(connection: sqlite3.Connection) -> None:
    _require_delete_journal(connection)
    connection.execute("PRAGMA synchronous=FULL")
    if connection.execute("PRAGMA synchronous").fetchone() != (2,):
        raise _StoreFailure("RECORD_STORE_CONFIGURATION_INVALID")
    connection.execute("PRAGMA foreign_keys=ON")
    if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
        raise _StoreFailure("RECORD_STORE_CONFIGURATION_INVALID")


def _is_pristine(connection: sqlite3.Connection) -> bool:
    version = connection.execute("PRAGMA user_version").fetchone()
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return version == (0,) and objects == []


def _verify_indexes(connection: sqlite3.Connection) -> None:
    # The record-store defines exactly five explicit indexes plus the primary-key
    # auto index; a wrong, missing, extra, or renamed index fails closed.
    if connection.execute("PRAGMA index_list(record_store_meta)").fetchall():
        raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    for name, expected_sql, expected_columns in _INDEX_DEFINITIONS:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
            (name,),
        ).fetchone()
        if (
            row is None
            or len(row) != 1
            or not isinstance(row[0], str)
            or " ".join(row[0].split()) != " ".join(expected_sql.split())
        ):
            raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
        info = connection.execute(f'PRAGMA index_info("{name}")').fetchall()
        columns = tuple(item[2] for item in info if len(item) >= 3)
        if columns != expected_columns:
            raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA user_version").fetchone() != (
        POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION,
    ):
        raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    ).fetchall()
    if objects != _EXPECTED_OBJECTS:
        raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    expected_sql = {
        "record_store_meta": _CREATE_RECORD_STORE_META,
        "records": _CREATE_RECORDS,
    }
    for table, expected in expected_sql.items():
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if (
            row is None
            or len(row) != 1
            or not isinstance(row[0], str)
            or " ".join(row[0].split()) != " ".join(expected.split())
        ):
            raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    for table, expected in _EXPECTED_TABLE_INFO.items():
        actual = tuple(connection.execute(f'PRAGMA table_info("{table}")').fetchall())
        if actual != expected:
            raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    if connection.execute(
        "SELECT singleton, format_id, schema_version FROM record_store_meta"
    ).fetchall() != [
        (1, POINT_IN_TIME_RECORD_STORE_FORMAT_ID, POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION)
    ]:
        raise _StoreFailure("RECORD_STORE_SCHEMA_UNSUPPORTED")
    _verify_indexes(connection)


def _verify_sqlite_integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise _StoreFailure("RECORD_STORE_SQLITE_INTEGRITY_FAILED")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise _StoreFailure("RECORD_STORE_SQLITE_INTEGRITY_FAILED")


# ── Canonical full-record payload (WP163 Section 13) ──────────────────────────


def _canonical_record_mapping(record: object) -> dict[str, object]:
    """Return the complete immutable record object as one canonical mapping."""

    envelope = getattr(record, "envelope")
    if type(envelope) is not PointInTimeEnvelope:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    envelope_mapping = {
        field.name: getattr(envelope, field.name)
        for field in fields(PointInTimeEnvelope)
    }
    mapping: dict[str, object] = {
        "record_type": type(record).__name__,
        "envelope": envelope_mapping,
    }
    for field in fields(type(record)):
        if field.name == "envelope":
            continue
        mapping[field.name] = getattr(record, field.name)
    return mapping


def _serialize(record: object) -> tuple[str, str]:
    try:
        payload = canonical_json_bytes(_canonical_record_mapping(record))
    except _StoreFailure:
        raise
    except (AttributeError, TypeError, ValueError, UnicodeError):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None
    if len(payload) > _MAX_PAYLOAD_BYTES_PER_ROW:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    return payload.decode("utf-8"), sha256_hex(payload)


def _reject_constant(_: str) -> object:
    raise ValueError("non-finite number")


def _pairs_to_dict(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _decode_payload(payload_json: object, payload_sha256: object) -> dict[str, object]:
    if not isinstance(payload_json, str) or not isinstance(payload_sha256, str):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    try:
        payload_bytes = payload_json.encode("utf-8")
    except UnicodeError:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None
    if len(payload_bytes) > _MAX_PAYLOAD_BYTES_PER_ROW:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    try:
        decoded = json.loads(
            payload_json,
            object_pairs_hook=_pairs_to_dict,
            parse_constant=_reject_constant,
        )
        if not isinstance(decoded, dict):
            raise ValueError("top-level object required")
        canonical = canonical_json_bytes(decoded)
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None
    if canonical != payload_bytes or sha256_hex(canonical) != payload_sha256:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    return decoded


def _reconstruct_record(mapping: dict[str, object]) -> object:
    record_type = mapping.get("record_type")
    if record_type not in _RECORD_TYPE_NAMES:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    envelope_mapping = mapping.get("envelope")
    if not isinstance(envelope_mapping, dict):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    if set(envelope_mapping.keys()) != _ENVELOPE_FIELD_SET:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    record_cls = {
        "MarketObservationRecord": MarketObservationRecord,
        "SourceSnapshotRecord": SourceSnapshotRecord,
        "ResolutionRuleSnapshotRecord": ResolutionRuleSnapshotRecord,
    }[record_type]
    record_field_names = frozenset(
        field.name for field in fields(record_cls) if field.name != "envelope"
    )
    expected_keys = {"record_type", "envelope"} | record_field_names
    if set(mapping.keys()) != expected_keys:
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
    envelope_kwargs = dict(envelope_mapping)
    for name in _ENVELOPE_TUPLE_FIELDS:
        value = envelope_kwargs.get(name)
        if not isinstance(value, list):
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        envelope_kwargs[name] = tuple(value)
    try:
        envelope = PointInTimeEnvelope(**envelope_kwargs)
    except (TypeError, ValueError):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None
    record_kwargs: dict[str, object] = {"envelope": envelope}
    for name in record_field_names:
        value = mapping[name]
        if name in _TUPLE_FIELDS[record_type]:
            if not isinstance(value, list):
                raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
            value = tuple(value)
        record_kwargs[name] = value
    try:
        return record_cls(**record_kwargs)
    except (TypeError, ValueError):
        raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None


# ── Indexed-column projection (WP163 Section 13) ──────────────────────────────


def _projected_columns(record: object) -> dict[str, object]:
    """Return the exact indexed-column projection for one record object."""

    envelope = record.envelope
    columns: dict[str, object] = {
        "record_version_id": envelope.record_version_id,
        "record_type": type(record).__name__,
        "record_family": envelope.record_family,
        "classification": envelope.classification,
        "human_review_required": 1 if envelope.human_review_required else 0,
        "observed_time": envelope.observed_time,
        "ingestion_time": envelope.ingestion_time,
        "event_time": envelope.event_time,
        "parameter_set_id": envelope.parameter_set_id,
        "validator_version": envelope.validator_version,
        "observation_kind": None,
        "platform_id": None,
        "event_id": None,
        "market_id": None,
        "token_id": None,
        "source_id": None,
        "resolution_source_id": None,
    }
    if isinstance(record, MarketObservationRecord):
        columns["observation_kind"] = record.observation_kind
        columns["platform_id"] = record.platform_id
        columns["event_id"] = record.event_id
        columns["market_id"] = record.market_id
        columns["token_id"] = record.token_id
        columns["source_id"] = record.source_id
    elif isinstance(record, SourceSnapshotRecord):
        columns["source_id"] = record.source_id
    else:  # ResolutionRuleSnapshotRecord
        columns["platform_id"] = record.platform_id
        columns["event_id"] = record.event_id
        columns["market_id"] = record.market_id
        columns["resolution_source_id"] = record.resolution_source_id
    return columns


_ROW_COLUMN_ORDER = (
    "record_version_id",
    "record_type",
    "record_family",
    "classification",
    "human_review_required",
    "observed_time",
    "ingestion_time",
    "event_time",
    "parameter_set_id",
    "validator_version",
    "observation_kind",
    "platform_id",
    "event_id",
    "market_id",
    "token_id",
    "source_id",
    "resolution_source_id",
)


def _verify_row_columns(record: object, row: tuple[object, ...]) -> None:
    """Verify the indexed row columns exactly match the reconstructed object."""

    projected = _projected_columns(record)
    for index, name in enumerate(_ROW_COLUMN_ORDER):
        if row[index] != projected[name]:
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")


# ── Record self-validation (WP163 Section 14) ─────────────────────────────────


def _self_validate_record(record: object) -> None:
    """Fail closed unless one record passes its WP156 self-integrity contract."""

    if type(record) not in _RECORD_TYPES:
        raise _StoreFailure("RECORD_STORE_RECORD_INVALID")
    envelope = getattr(record, "envelope", None)
    if type(envelope) is not PointInTimeEnvelope:
        raise _StoreFailure("RECORD_STORE_RECORD_INVALID")
    classification = envelope.classification
    if classification == "CONFLICT":
        if envelope.human_review_required is not True:
            raise _StoreFailure("RECORD_STORE_RECORD_INVALID")
        try:
            errors = revalidate_review_conflict_record(record)
        except Exception:
            raise _StoreFailure("RECORD_STORE_RECORD_INVALID") from None
        if errors != ():
            raise _StoreFailure("RECORD_STORE_RECORD_INVALID")
        return
    try:
        result = validate_record_batch(
            (record,),
            known_parent_record_ids=envelope.lineage_parent_ids,
        )
    except Exception:
        raise _StoreFailure("RECORD_STORE_RECORD_INVALID") from None
    if not result.is_valid or result.accepted_record_version_ids != (
        envelope.record_version_id,
    ):
        raise _StoreFailure("RECORD_STORE_RECORD_INVALID")


# ── Complete store lineage validation (WP163 Section 15) ──────────────────────


def _entity_identity(record: object) -> tuple[object, ...]:
    """Replicate the WP156 entity identity without importing private helpers."""

    if isinstance(record, MarketObservationRecord):
        return (
            "MARKET_OBSERVATION",
            record.platform_id,
            record.event_id,
            record.market_id,
            record.token_id,
            record.source_id,
            record.observation_kind,
        )
    if isinstance(record, SourceSnapshotRecord):
        return ("SOURCE_SNAPSHOT", record.source_id)
    return (
        "RESOLUTION_RULE_SNAPSHOT",
        record.platform_id,
        record.event_id,
        record.market_id,
        record.resolution_source_id,
    )


def _canonical_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_store_lineage(records_by_id: dict[str, object]) -> None:
    """Validate the complete cross-record lineage graph, or fail closed."""

    errors: list[str] = []
    is_conflict = {
        rid: record.envelope.classification == "CONFLICT"
        for rid, record in records_by_id.items()
    }

    for rid, record in records_by_id.items():
        envelope = record.envelope
        parents = envelope.lineage_parent_ids
        classification = envelope.classification

        if len(set(parents)) != len(parents):
            errors.append("RECORD_STORE_LINEAGE_INVALID")
        if rid in parents:
            errors.append("RECORD_STORE_LINEAGE_INVALID")
        if any(parent not in records_by_id for parent in parents):
            errors.append("RECORD_STORE_LINEAGE_INVALID")

        if classification == "CONFLICT":
            if envelope.human_review_required is not True:
                errors.append("RECORD_STORE_RECORD_INVALID")
        else:
            # Rule 6: an ordinary record may never take a CONFLICT record as an
            # authoritative lineage parent.
            if any(
                parent in records_by_id and is_conflict[parent]
                for parent in parents
            ):
                errors.append("RECORD_STORE_AUTHORITY_VIOLATION")

        supersedes = envelope.supersedes_record_version_id
        if supersedes is not None:
            if supersedes not in records_by_id:
                errors.append("RECORD_STORE_LINEAGE_INVALID")
            elif supersedes not in parents:
                errors.append("RECORD_STORE_LINEAGE_INVALID")
            elif is_conflict[supersedes]:
                errors.append("RECORD_STORE_AUTHORITY_VIOLATION")

        if classification in {
            "SOURCE_REVISION",
            "PROJECT_CORRECTION",
            "SOURCE_RETRACTION",
        }:
            parent = records_by_id.get(supersedes) if supersedes is not None else None
            if parent is None:
                errors.append("RECORD_STORE_LINEAGE_INVALID")
            else:
                if _entity_identity(record) != _entity_identity(parent):
                    errors.append("RECORD_STORE_LINEAGE_INVALID")
                if _canonical_time(envelope.ingestion_time) < _canonical_time(
                    parent.envelope.ingestion_time
                ):
                    errors.append("RECORD_STORE_LINEAGE_INVALID")

        if classification in {"EXACT_DUPLICATE", "SEMANTIC_DUPLICATE"}:
            reference_id = supersedes if supersedes is not None else (
                parents[0] if parents else None
            )
            parent = (
                records_by_id.get(reference_id) if reference_id is not None else None
            )
            if parent is None:
                errors.append("RECORD_STORE_LINEAGE_INVALID")
            elif is_conflict.get(reference_id):
                errors.append("RECORD_STORE_AUTHORITY_VIOLATION")
            else:
                if _entity_identity(record) != _entity_identity(parent):
                    errors.append("RECORD_STORE_LINEAGE_INVALID")
                if classification == "EXACT_DUPLICATE":
                    if (
                        envelope.canonical_payload_sha256
                        != parent.envelope.canonical_payload_sha256
                    ):
                        errors.append("RECORD_STORE_LINEAGE_INVALID")
                else:  # SEMANTIC_DUPLICATE
                    if envelope.observation_id != parent.envelope.observation_id:
                        errors.append("RECORD_STORE_LINEAGE_INVALID")

    _detect_cycles(records_by_id, errors)

    if errors:
        raise _StoreFailure(_ordered_codes(errors)[0])


def _detect_cycles(records_by_id: dict[str, object], errors: list[str]) -> None:
    graph = {
        rid: tuple(
            parent
            for parent in record.envelope.lineage_parent_ids
            if parent in records_by_id
        )
        for rid, record in records_by_id.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_found = False

    def visit(node: str) -> None:
        nonlocal cycle_found
        if node in visiting:
            cycle_found = True
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, ()):
            visit(parent)
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    if cycle_found:
        errors.append("RECORD_STORE_LINEAGE_INVALID")


# ── Snapshot assembly and read/verify (WP163 Section 19) ──────────────────────


def _snapshot_sort_key(record: object) -> tuple[object, ...]:
    envelope = record.envelope
    event_time = envelope.event_time
    return (
        _canonical_time(envelope.ingestion_time),
        _canonical_time(envelope.observed_time),
        event_time is None,
        _canonical_time(event_time) if event_time is not None else _canonical_time(
            "0001-01-01T00:00:00Z"
        ),
        _FAMILY_ORDER.get(envelope.record_family, 99),
        envelope.record_version_id,
    )


_ROW_SELECT = (
    "SELECT record_version_id, record_type, record_family, classification, "
    "human_review_required, observed_time, ingestion_time, event_time, "
    "parameter_set_id, validator_version, observation_kind, platform_id, "
    "event_id, market_id, token_id, source_id, resolution_source_id, "
    "payload_json, payload_sha256 FROM records"
)


def _load_snapshot(connection: sqlite3.Connection) -> PointInTimeRecordStoreSnapshot:
    _require_delete_journal(connection)
    _verify_schema(connection)
    _verify_sqlite_integrity(connection)
    rows = connection.execute(_ROW_SELECT).fetchall()
    if len(rows) > _MAX_RECORDS_IN_STORE:
        raise _StoreFailure("RECORD_STORE_LIMIT_EXCEEDED")

    total_payload_bytes = 0
    for row in rows:
        payload_json = row[17]
        if not isinstance(payload_json, str):
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        try:
            total_payload_bytes += len(payload_json.encode("utf-8"))
        except UnicodeError:
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID") from None
    if total_payload_bytes > _MAX_TOTAL_PAYLOAD_BYTES:
        raise _StoreFailure("RECORD_STORE_LIMIT_EXCEEDED")

    records_by_id: dict[str, object] = {}
    for row in rows:
        if len(row) != 19 or not isinstance(row[0], str):
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        mapping = _decode_payload(row[17], row[18])
        record = _reconstruct_record(mapping)
        if record.envelope.record_version_id != row[0]:
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        expected_family = _RECORD_TYPE_TO_FAMILY[type(record).__name__]
        if record.envelope.record_family != expected_family:
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        _verify_row_columns(record, row)
        _self_validate_record(record)
        if record.envelope.record_version_id in records_by_id:
            raise _StoreFailure("RECORD_STORE_PAYLOAD_INVALID")
        records_by_id[record.envelope.record_version_id] = record

    _validate_store_lineage(records_by_id)

    ordered = tuple(sorted(records_by_id.values(), key=_snapshot_sort_key))
    ordinary = sum(
        1 for record in ordered if record.envelope.classification != "CONFLICT"
    )
    review = sum(
        1 for record in ordered if record.envelope.classification == "CONFLICT"
    )
    return PointInTimeRecordStoreSnapshot(
        records=ordered,
        ordinary_record_count=ordinary,
        review_conflict_record_count=review,
        total_payload_bytes=total_payload_bytes,
        advisory_only=True,
        no_execution_authority=True,
    )


def _load_path(path: Path) -> PointInTimeRecordStoreResult:
    connection: sqlite3.Connection | None = None
    try:
        connection = _connect(path, "ro")
        snapshot = _load_snapshot(connection)
        return _valid_result("RECORD_STORE_LOADED_VERIFIED", snapshot)
    except _StoreFailure as failure:
        return _rejected(failure.code)
    except sqlite3.Error:
        return _rejected("RECORD_STORE_SQLITE_INTEGRITY_FAILED")
    except (OSError, TypeError, ValueError, UnicodeError):
        return _rejected("RECORD_STORE_OPEN_FAILED")
    except Exception:
        return _rejected("RECORD_STORE_OPEN_FAILED")
    finally:
        if connection is not None:
            connection.close()


# ── Initialization (WP163 Section 16) ─────────────────────────────────────────


def initialize_point_in_time_record_store(
    path: object,
) -> PointInTimeRecordStoreResult:
    """Create the exact schema or verify an existing compatible record store."""

    try:
        normalized = _normalize_path(path, must_exist=False)
        existed = _path_exists(normalized)
    except _StoreFailure as failure:
        return _rejected(failure.code)

    existing: PointInTimeRecordStoreResult | None = None
    if existed:
        existing = _load_path(normalized)
        if existing.is_valid and existing.snapshot is not None:
            return _valid_result("RECORD_STORE_ALREADY_INITIALIZED", existing.snapshot)
        probe: sqlite3.Connection | None = None
        try:
            probe = _connect(normalized, "ro")
            if not _is_pristine(probe):
                return existing
        except (_StoreFailure, sqlite3.Error):
            return existing
        finally:
            if probe is not None:
                probe.close()

    connection: sqlite3.Connection | None = None
    created_here = not existed
    committed = False
    try:
        connection = _connect(normalized, "rw" if existed else "rwc")
        if not _is_pristine(connection):
            return existing if existing is not None else _rejected(
                "RECORD_STORE_SCHEMA_UNSUPPORTED"
            )
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(_CREATE_RECORD_STORE_META)
        connection.execute(_CREATE_RECORDS)
        connection.execute(_CREATE_INDEX_INGESTION)
        connection.execute(_CREATE_INDEX_OBSERVED)
        connection.execute(_CREATE_INDEX_EVENT)
        connection.execute(_CREATE_INDEX_MARKET)
        connection.execute(_CREATE_INDEX_SOURCE)
        connection.execute(
            "INSERT INTO record_store_meta (singleton, format_id, schema_version) "
            "VALUES (?, ?, ?)",
            (
                1,
                POINT_IN_TIME_RECORD_STORE_FORMAT_ID,
                POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION,
            ),
        )
        connection.execute(
            f"PRAGMA user_version={POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION}"
        )
        _verify_schema(connection)
        connection.execute("COMMIT")
        committed = True
    except _StoreFailure as failure:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected(failure.code)
    except sqlite3.Error as error:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("RECORD_STORE_BUSY" if _is_busy(error) else "RECORD_STORE_WRITE_FAILED")
    except Exception:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("RECORD_STORE_WRITE_FAILED")
    finally:
        if connection is not None:
            connection.close()
        if created_here and not committed:
            _remove_created_store(normalized)

    verified = _load_path(normalized)
    if not verified.is_valid or verified.snapshot is None:
        if created_here:
            _remove_created_store(normalized)
        return verified
    return _valid_result("RECORD_STORE_INITIALIZED", verified.snapshot)


# ── Append input boundary and idempotency (WP163 Sections 17-18) ──────────────


def _validate_input_records(records: object) -> tuple[object, ...]:
    # Accept only an exact built-in list or tuple; never invoke custom iteration
    # on a subclass, string, bytes, mapping, set, generator, or iterator.
    if type(records) not in (list, tuple):
        raise _StoreFailure("RECORD_STORE_INPUT_INVALID")
    candidates = tuple(records)
    if len(candidates) > _MAX_RECORDS_PER_APPEND:
        raise _StoreFailure("RECORD_STORE_LIMIT_EXCEEDED")
    for candidate in candidates:
        _self_validate_record(candidate)
    return candidates


def _collapse_input_duplicates(candidates: tuple[object, ...]) -> dict[str, object]:
    unique: dict[str, object] = {}
    for record in candidates:
        identity = record.envelope.record_version_id
        prior = unique.get(identity)
        if prior is None:
            unique[identity] = record
        elif prior != record:
            raise _StoreFailure("RECORD_STORE_DUPLICATE_CONFLICT")
    return unique


def _after_insert_hook() -> None:
    """Private deterministic test seam; production behavior is a no-op."""


def append_point_in_time_records(
    path: object,
    records: object,
) -> PointInTimeRecordStoreResult:
    """Atomically append a bounded batch of already-built immutable records."""

    try:
        candidates = _validate_input_records(records)
    except _StoreFailure as failure:
        return _rejected(failure.code)
    try:
        normalized = _normalize_path(path, must_exist=True)
    except _StoreFailure as failure:
        return _rejected(failure.code)

    if not candidates:
        loaded = _load_path(normalized)
        if not loaded.is_valid or loaded.snapshot is None:
            return loaded
        return _valid_result("RECORD_STORE_APPEND_IDEMPOTENT", loaded.snapshot)

    connection: sqlite3.Connection | None = None
    insert_ids: list[str] = []
    idempotent_ids: set[str] = set()
    try:
        unique_input = _collapse_input_duplicates(candidates)
        connection = _connect(normalized, "rw")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        existing_snapshot = _load_snapshot(connection)
        existing = {
            record.envelope.record_version_id: record
            for record in existing_snapshot.records
        }
        prospective: dict[str, object] = dict(existing)
        insert_records: dict[str, object] = {}
        for identity, record in unique_input.items():
            prior = existing.get(identity)
            if prior is not None:
                if prior != record:
                    raise _StoreFailure("RECORD_STORE_DUPLICATE_CONFLICT")
                idempotent_ids.add(identity)
            else:
                prospective[identity] = record
                insert_records[identity] = record

        if len(prospective) > _MAX_RECORDS_IN_STORE:
            raise _StoreFailure("RECORD_STORE_LIMIT_EXCEEDED")

        serialized: dict[str, tuple[str, str]] = {}
        total_payload_bytes = 0
        for identity, record in prospective.items():
            payload_json, payload_sha256 = _serialize(record)
            serialized[identity] = (payload_json, payload_sha256)
            total_payload_bytes += len(payload_json.encode("utf-8"))
        if total_payload_bytes > _MAX_TOTAL_PAYLOAD_BYTES:
            raise _StoreFailure("RECORD_STORE_LIMIT_EXCEEDED")

        _validate_store_lineage(prospective)

        for identity in sorted(insert_records):
            record = insert_records[identity]
            payload_json, payload_sha256 = serialized[identity]
            columns = _projected_columns(record)
            connection.execute(
                "INSERT INTO records ("
                "record_version_id, record_type, record_family, classification, "
                "human_review_required, observed_time, ingestion_time, event_time, "
                "parameter_set_id, validator_version, observation_kind, platform_id, "
                "event_id, market_id, token_id, source_id, resolution_source_id, "
                "payload_json, payload_sha256"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    columns["record_version_id"],
                    columns["record_type"],
                    columns["record_family"],
                    columns["classification"],
                    columns["human_review_required"],
                    columns["observed_time"],
                    columns["ingestion_time"],
                    columns["event_time"],
                    columns["parameter_set_id"],
                    columns["validator_version"],
                    columns["observation_kind"],
                    columns["platform_id"],
                    columns["event_id"],
                    columns["market_id"],
                    columns["token_id"],
                    columns["source_id"],
                    columns["resolution_source_id"],
                    payload_json,
                    payload_sha256,
                ),
            )
            insert_ids.append(identity)
            _after_insert_hook()
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise _StoreFailure("RECORD_STORE_SQLITE_INTEGRITY_FAILED")
        connection.execute("COMMIT")
    except _StoreFailure as failure:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected(failure.code)
    except sqlite3.Error as error:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("RECORD_STORE_BUSY" if _is_busy(error) else "RECORD_STORE_WRITE_FAILED")
    except Exception:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("RECORD_STORE_WRITE_FAILED")
    finally:
        if connection is not None:
            connection.close()

    verified = _load_path(normalized)
    if not verified.is_valid or verified.snapshot is None:
        return verified
    persisted_ids = {
        record.envelope.record_version_id for record in verified.snapshot.records
    }
    if any(identity not in persisted_ids for identity in insert_ids):
        return _rejected("RECORD_STORE_WRITE_FAILED")
    inserted = tuple(sorted(insert_ids))
    status = (
        "RECORD_STORE_APPEND_COMMITTED"
        if inserted
        else "RECORD_STORE_APPEND_IDEMPOTENT"
    )
    return _valid_result(
        status,
        verified.snapshot,
        inserted=inserted,
        idempotent=tuple(sorted(idempotent_ids)),
    )


def load_and_verify_point_in_time_record_store(
    path: object,
) -> PointInTimeRecordStoreResult:
    """Read one existing record store in SQLite read-only mode and verify all."""

    try:
        normalized = _normalize_path(path, must_exist=True)
    except _StoreFailure as failure:
        return _rejected(failure.code)
    return _load_path(normalized)


# ── Dataset snapshot reference materialization (WP163 Sections 20-24) ─────────


def _reference_mapping(reference: DatasetSnapshotReference) -> dict[str, object]:
    return {
        field.name: getattr(reference, field.name)
        for field in fields(DatasetSnapshotReference)
    }


def _rebuild_reference(reference: object) -> DatasetSnapshotReference:
    if type(reference) is not DatasetSnapshotReference:
        raise _StoreFailure("RECORD_STORE_REFERENCE_INVALID")
    try:
        result = build_dataset_snapshot_reference(_reference_mapping(reference))
    except Exception:
        raise _StoreFailure("RECORD_STORE_REFERENCE_INVALID") from None
    if not result.is_valid or result.reference is None or result.reference != reference:
        raise _StoreFailure("RECORD_STORE_REFERENCE_INVALID")
    return result.reference


def _resolve_reference_ids(
    reference: DatasetSnapshotReference,
    records_by_id: dict[str, object],
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    ordinary: list[object] = []
    for identity in reference.ordinary_record_version_ids:
        record = records_by_id.get(identity)
        if record is None:
            raise _StoreFailure("RECORD_STORE_REFERENCE_MISSING_RECORD")
        if record.envelope.classification == "CONFLICT":
            raise _StoreFailure("RECORD_STORE_AUTHORITY_VIOLATION")
        ordinary.append(record)
    review: list[object] = []
    for identity in reference.review_conflict_record_version_ids:
        record = records_by_id.get(identity)
        if record is None:
            raise _StoreFailure("RECORD_STORE_REFERENCE_MISSING_RECORD")
        if (
            record.envelope.classification != "CONFLICT"
            or record.envelope.human_review_required is not True
        ):
            raise _StoreFailure("RECORD_STORE_AUTHORITY_VIOLATION")
        review.append(record)
    return tuple(ordinary), tuple(review)


def materialize_dataset_snapshot_reference(
    path: object,
    reference: object,
) -> DatasetSnapshotMaterializationResult:
    """Resolve a valid WP160 reference into its exact durable record objects."""

    # Reference validation happens before any store access, and no rejected
    # result ever exposes the caller reference.
    try:
        rebuilt = _rebuild_reference(reference)
    except _StoreFailure as failure:
        return _rejected_materialization(failure.code)

    try:
        normalized = _normalize_path(path, must_exist=True)
    except _StoreFailure as failure:
        return _rejected_materialization(failure.code)

    loaded = _load_path(normalized)
    if not loaded.is_valid or loaded.snapshot is None:
        return _rejected_materialization(
            *(loaded.error_codes or ("RECORD_STORE_OPEN_FAILED",))
        )

    records_by_id = {
        record.envelope.record_version_id: record
        for record in loaded.snapshot.records
    }

    try:
        ordinary_records, review_records = _resolve_reference_ids(
            rebuilt, records_by_id
        )
        verification_mode = _verify_materialization_mode(
            rebuilt, ordinary_records, review_records
        )
    except _StoreFailure as failure:
        return _rejected_materialization(failure.code)

    return DatasetSnapshotMaterializationResult(
        is_valid=True,
        status="DATASET_REFERENCE_MATERIALIZED",
        error_codes=(),
        warning_codes=(),
        dataset_reference=rebuilt,
        ordinary_records=ordinary_records,
        review_conflict_records=review_records,
        verification_mode=verification_mode,
        human_review_required=bool(rebuilt.human_review_required),
        advisory_only=True,
        no_execution_authority=True,
    )


def _verify_materialization_mode(
    reference: DatasetSnapshotReference,
    ordinary_records: tuple[object, ...],
    review_records: tuple[object, ...],
) -> str:
    if reference.derivation_mode == "VALIDATED_RECORD_BATCH":
        if review_records or not ordinary_records:
            raise _StoreFailure("RECORD_STORE_REFERENCE_CONTENT_MISMATCH")
        try:
            batch = validate_record_batch(ordinary_records)
        except Exception:
            raise _StoreFailure("RECORD_STORE_REFERENCE_CONTENT_MISMATCH") from None
        if (
            not batch.is_valid
            or batch.accepted_record_version_ids
            != reference.ordinary_record_version_ids
            or batch.canonical_batch_sha256 != reference.validated_batch_sha256
        ):
            raise _StoreFailure("RECORD_STORE_REFERENCE_CONTENT_MISMATCH")
        return "VALIDATED_BATCH_RECOMPUTED"

    # AS_OF_QUERY_RESULT: honest ID-resolution only. The reference alone cannot
    # replay the original WP157 query, so no query/batch hash is recomputed from
    # the output subset. Existence, authority, and reference-owned order were
    # already enforced during ID resolution.
    return "AS_OF_REFERENCE_IDS_RESOLVED"
