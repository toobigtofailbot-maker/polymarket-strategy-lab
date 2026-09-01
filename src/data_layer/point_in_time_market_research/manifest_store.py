"""Bounded local SQLite persistence for validated WP160 manifest objects.

The module has no path discovery, configuration, migration, retry, network, or
execution authority.  Callers select one explicit local path.  SQLite's DELETE
journal and explicit transactions provide the durability primitive; WP160's
builders and complete-chain validator remain the semantic authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
import os
from pathlib import Path
import sqlite3
from typing import Sequence

from .manifest_reference import (
    DatasetSnapshotReference,
    ManifestChainValidationResult,
    ManifestEntry,
    build_dataset_snapshot_reference,
    build_manifest_entry,
    validate_manifest_chain,
)
from .records import canonical_json_bytes, sha256_hex


MANIFEST_STORE_LABEL = "POINT_IN_TIME_LOCAL_SQLITE_MANIFEST_STORE"
MANIFEST_STORE_POSTURE = (
    "BOUNDED_LOCAL_SQLITE_TRANSACTIONAL_APPEND_AND_VERIFIED_READ"
)
MANIFEST_STORE_FORMAT_ID = "point-in-time-manifest-store"
MANIFEST_STORE_SCHEMA_VERSION = 1

MANIFEST_STORE_STATUSES = (
    "STORE_INITIALIZED",
    "STORE_ALREADY_INITIALIZED",
    "STORE_APPEND_COMMITTED",
    "STORE_APPEND_IDEMPOTENT",
    "STORE_LOADED_VERIFIED",
    "STORE_REJECTED",
)

MANIFEST_STORE_ERROR_CODES = (
    "STORE_PATH_INVALID",
    "STORE_NOT_FOUND",
    "STORE_OPEN_FAILED",
    "STORE_BUSY",
    "STORE_SCHEMA_UNSUPPORTED",
    "STORE_CONFIGURATION_INVALID",
    "STORE_SQLITE_INTEGRITY_FAILED",
    "STORE_INPUT_INVALID",
    "STORE_REFERENCE_INVALID",
    "STORE_ENTRY_INVALID",
    "STORE_PAYLOAD_INVALID",
    "STORE_DUPLICATE_CONFLICT",
    "STORE_LIMIT_EXCEEDED",
    "STORE_CHAIN_INVALID",
    "STORE_WRITE_FAILED",
)

_ERROR_ORDER = {code: index for index, code in enumerate(MANIFEST_STORE_ERROR_CODES)}
_MAX_ROWS = 256
_MAX_PAYLOAD_BYTES = 65_536

_CREATE_STORE_META = """CREATE TABLE store_meta (
    singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),
    format_id TEXT NOT NULL CHECK (format_id = 'point-in-time-manifest-store'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
)"""

_CREATE_DATASET_REFERENCES = """CREATE TABLE dataset_references (
    dataset_snapshot_reference_id TEXT PRIMARY KEY NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL
)"""

_CREATE_MANIFEST_ENTRIES = """CREATE TABLE manifest_entries (
    manifest_entry_id TEXT PRIMARY KEY NOT NULL,
    manifest_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
    dataset_snapshot_reference_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    UNIQUE (manifest_id, sequence_number),
    FOREIGN KEY (dataset_snapshot_reference_id)
        REFERENCES dataset_references(dataset_snapshot_reference_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
)"""

_EXPECTED_TABLE_INFO = {
    "store_meta": (
        (0, "singleton", "INTEGER", 1, None, 1),
        (1, "format_id", "TEXT", 1, None, 0),
        (2, "schema_version", "INTEGER", 1, None, 0),
    ),
    "dataset_references": (
        (0, "dataset_snapshot_reference_id", "TEXT", 1, None, 1),
        (1, "payload_json", "TEXT", 1, None, 0),
        (2, "payload_sha256", "TEXT", 1, None, 0),
    ),
    "manifest_entries": (
        (0, "manifest_entry_id", "TEXT", 1, None, 1),
        (1, "manifest_id", "TEXT", 1, None, 0),
        (2, "sequence_number", "INTEGER", 1, None, 0),
        (3, "dataset_snapshot_reference_id", "TEXT", 1, None, 0),
        (4, "payload_json", "TEXT", 1, None, 0),
        (5, "payload_sha256", "TEXT", 1, None, 0),
    ),
}


@dataclass(frozen=True)
class ManifestStoreSnapshot:
    dataset_references: tuple[DatasetSnapshotReference, ...]
    manifest_entries: tuple[ManifestEntry, ...]
    chain_validation: ManifestChainValidationResult | None
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ManifestStoreResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    snapshot: ManifestStoreSnapshot | None
    inserted_dataset_reference_ids: tuple[str, ...]
    inserted_manifest_entry_ids: tuple[str, ...]
    idempotent_dataset_reference_ids: tuple[str, ...]
    idempotent_manifest_entry_ids: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool


class _StoreFailure(Exception):
    """Internal control-flow exception carrying only a closed error code."""

    def __init__(self, code: str):
        self.code = code


def _ordered_codes(codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, 999)))


def _rejected(*codes: str) -> ManifestStoreResult:
    return ManifestStoreResult(
        is_valid=False,
        status="STORE_REJECTED",
        error_codes=_ordered_codes(codes),
        warning_codes=(),
        snapshot=None,
        inserted_dataset_reference_ids=(),
        inserted_manifest_entry_ids=(),
        idempotent_dataset_reference_ids=(),
        idempotent_manifest_entry_ids=(),
        advisory_only=True,
        no_execution_authority=True,
    )


def _valid_result(
    status: str,
    snapshot: ManifestStoreSnapshot,
    *,
    inserted_references: tuple[str, ...] = (),
    inserted_entries: tuple[str, ...] = (),
    idempotent_references: tuple[str, ...] = (),
    idempotent_entries: tuple[str, ...] = (),
) -> ManifestStoreResult:
    return ManifestStoreResult(
        is_valid=True,
        status=status,
        error_codes=(),
        warning_codes=(),
        snapshot=snapshot,
        inserted_dataset_reference_ids=inserted_references,
        inserted_manifest_entry_ids=inserted_entries,
        idempotent_dataset_reference_ids=idempotent_references,
        idempotent_manifest_entry_ids=idempotent_entries,
        advisory_only=True,
        no_execution_authority=True,
    )


def _normalize_path(path: object, *, must_exist: bool) -> Path:
    try:
        if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
            raise _StoreFailure("STORE_PATH_INVALID")
        raw = os.fspath(path)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise _StoreFailure("STORE_PATH_INVALID")
        normalized = Path(raw).absolute()
        if normalized.is_symlink():
            raise _StoreFailure("STORE_PATH_INVALID")
        if must_exist:
            if not normalized.exists():
                raise _StoreFailure("STORE_NOT_FOUND")
            if not normalized.is_file():
                raise _StoreFailure("STORE_PATH_INVALID")
        else:
            if normalized.exists() and not normalized.is_file():
                raise _StoreFailure("STORE_PATH_INVALID")
            parent = normalized.parent
            if not parent.exists() or not parent.is_dir():
                raise _StoreFailure("STORE_PATH_INVALID")
    except _StoreFailure:
        raise
    except Exception:
        raise _StoreFailure("STORE_PATH_INVALID") from None
    return normalized


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        raise _StoreFailure("STORE_PATH_INVALID") from None


def _remove_created_store(path: Path) -> None:
    """Remove only a regular non-symlink target created by this operation."""

    try:
        if path.is_symlink() or not path.is_file() or path.is_symlink():
            return
        path.unlink()
    except Exception:
        # Cleanup must not replace the original bounded store failure.
        pass


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
        raise _StoreFailure("STORE_OPEN_FAILED") from None


def _is_busy(error: sqlite3.Error) -> bool:
    code = getattr(error, "sqlite_errorcode", None)
    return isinstance(code, int) and (code & 0xFF) in {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    }


def _journal_mode(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA journal_mode").fetchone()
    if row is None or len(row) != 1 or not isinstance(row[0], str):
        raise _StoreFailure("STORE_CONFIGURATION_INVALID")
    return row[0].lower()


def _require_delete_journal(connection: sqlite3.Connection) -> None:
    if _journal_mode(connection) != "delete":
        raise _StoreFailure("STORE_CONFIGURATION_INVALID")


def _configure_writable(connection: sqlite3.Connection) -> None:
    _require_delete_journal(connection)
    connection.execute("PRAGMA synchronous=FULL")
    synchronous = connection.execute("PRAGMA synchronous").fetchone()
    if synchronous != (2,):
        raise _StoreFailure("STORE_CONFIGURATION_INVALID")
    connection.execute("PRAGMA foreign_keys=ON")
    foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
    if foreign_keys != (1,):
        raise _StoreFailure("STORE_CONFIGURATION_INVALID")


def _is_pristine(connection: sqlite3.Connection) -> bool:
    version = connection.execute("PRAGMA user_version").fetchone()
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return version == (0,) and objects == []


def _verify_indexes(connection: sqlite3.Connection) -> None:
    dataset_indexes = connection.execute(
        "PRAGMA index_list(dataset_references)"
    ).fetchall()
    manifest_indexes = connection.execute("PRAGMA index_list(manifest_entries)").fetchall()
    meta_indexes = connection.execute("PRAGMA index_list(store_meta)").fetchall()
    if meta_indexes:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")

    def signatures(rows: list[tuple[object, ...]]) -> list[tuple[object, tuple[str, ...]]]:
        result = []
        for row in rows:
            if len(row) < 5 or not isinstance(row[1], str):
                raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
            info = connection.execute(f'PRAGMA index_info("{row[1]}")').fetchall()
            columns = tuple(item[2] for item in info if len(item) >= 3)
            result.append((row[3], columns))
        return sorted(result, key=lambda item: (str(item[0]), item[1]))

    if signatures(dataset_indexes) != [("pk", ("dataset_snapshot_reference_id",))]:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    if signatures(manifest_indexes) != [
        ("pk", ("manifest_entry_id",)),
        ("u", ("manifest_id", "sequence_number")),
    ]:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA user_version").fetchone() != (
        MANIFEST_STORE_SCHEMA_VERSION,
    ):
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    ).fetchall()
    if objects != [
        ("table", "dataset_references"),
        ("table", "manifest_entries"),
        ("table", "store_meta"),
    ]:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    expected_sql = {
        "store_meta": _CREATE_STORE_META,
        "dataset_references": _CREATE_DATASET_REFERENCES,
        "manifest_entries": _CREATE_MANIFEST_ENTRIES,
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
            raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    for table, expected in _EXPECTED_TABLE_INFO.items():
        actual = tuple(connection.execute(f'PRAGMA table_info("{table}")').fetchall())
        if actual != expected:
            raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    if connection.execute(
        "SELECT singleton, format_id, schema_version FROM store_meta"
    ).fetchall() != [(1, MANIFEST_STORE_FORMAT_ID, MANIFEST_STORE_SCHEMA_VERSION)]:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    _verify_indexes(connection)
    foreign_keys = connection.execute("PRAGMA foreign_key_list(manifest_entries)").fetchall()
    if foreign_keys != [
        (
            0,
            0,
            "dataset_references",
            "dataset_snapshot_reference_id",
            "dataset_snapshot_reference_id",
            "RESTRICT",
            "RESTRICT",
            "NONE",
        )
    ]:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")
    explicit_indexes = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ).fetchall()
    if explicit_indexes:
        raise _StoreFailure("STORE_SCHEMA_UNSUPPORTED")


def _verify_sqlite_integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise _StoreFailure("STORE_SQLITE_INTEGRITY_FAILED")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise _StoreFailure("STORE_SQLITE_INTEGRITY_FAILED")


def _object_mapping(value: object) -> dict[str, object]:
    # Field-driven serialization: whatever dataclass fields WP160 defines are
    # persisted and rebuilt through the public builders. This is why WP166's
    # schema-2.0.0 lineage-delta references (which add the external-parent id set
    # and the prior-head backlink field) round-trip with NO SQLite table, column,
    # index, or PRAGMA user_version change, and why a pre-WP166 v1 payload that
    # lacks the new field still decodes to its identical v1 identity.
    return {field.name: getattr(value, field.name) for field in fields(value)}


def _serialize(value: object) -> tuple[str, str]:
    try:
        payload = canonical_json_bytes(_object_mapping(value))
        if len(payload) > _MAX_PAYLOAD_BYTES:
            raise _StoreFailure("STORE_PAYLOAD_INVALID")
        text = payload.decode("utf-8")
        return text, sha256_hex(payload)
    except _StoreFailure:
        raise
    except (AttributeError, TypeError, ValueError, UnicodeError):
        raise _StoreFailure("STORE_PAYLOAD_INVALID") from None


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
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    try:
        payload_bytes = payload_json.encode("utf-8")
    except UnicodeError:
        raise _StoreFailure("STORE_PAYLOAD_INVALID") from None
    if len(payload_bytes) > _MAX_PAYLOAD_BYTES:
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
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
        raise _StoreFailure("STORE_PAYLOAD_INVALID") from None
    if canonical != payload_bytes or sha256_hex(canonical) != payload_sha256:
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    return decoded


def _rebuild_reference(row: tuple[object, ...]) -> DatasetSnapshotReference:
    if len(row) != 3 or not isinstance(row[0], str):
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    mapping = _decode_payload(row[1], row[2])
    try:
        result = build_dataset_snapshot_reference(mapping)
    except Exception:
        raise _StoreFailure("STORE_REFERENCE_INVALID") from None
    if not result.is_valid or result.reference is None:
        raise _StoreFailure("STORE_REFERENCE_INVALID")
    if result.reference.dataset_snapshot_reference_id != row[0]:
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    return result.reference


def _rebuild_entry(row: tuple[object, ...]) -> ManifestEntry:
    if len(row) != 6 or not isinstance(row[0], str):
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    mapping = _decode_payload(row[4], row[5])
    try:
        result = build_manifest_entry(mapping)
    except Exception:
        raise _StoreFailure("STORE_ENTRY_INVALID") from None
    if not result.is_valid or result.entry is None:
        raise _StoreFailure("STORE_ENTRY_INVALID")
    entry = result.entry
    if (
        entry.manifest_entry_id != row[0]
        or entry.manifest_id != row[1]
        or entry.sequence_number != row[2]
        or entry.dataset_snapshot_reference_id != row[3]
    ):
        raise _StoreFailure("STORE_PAYLOAD_INVALID")
    return entry


def _load_snapshot(connection: sqlite3.Connection) -> ManifestStoreSnapshot:
    _require_delete_journal(connection)
    _verify_schema(connection)
    _verify_sqlite_integrity(connection)
    reference_rows = connection.execute(
        "SELECT dataset_snapshot_reference_id, payload_json, payload_sha256 "
        "FROM dataset_references ORDER BY dataset_snapshot_reference_id"
    ).fetchall()
    entry_rows = connection.execute(
        "SELECT manifest_entry_id, manifest_id, sequence_number, "
        "dataset_snapshot_reference_id, payload_json, payload_sha256 "
        "FROM manifest_entries ORDER BY sequence_number"
    ).fetchall()
    if len(reference_rows) > _MAX_ROWS or len(entry_rows) > _MAX_ROWS:
        raise _StoreFailure("STORE_LIMIT_EXCEEDED")
    references = tuple(_rebuild_reference(row) for row in reference_rows)
    entries = tuple(_rebuild_entry(row) for row in entry_rows)
    chain: ManifestChainValidationResult | None = None
    if entries:
        chain = validate_manifest_chain(entries, dataset_references=references)
        if not chain.is_valid or chain.status != "CHAIN_VALID":
            raise _StoreFailure("STORE_CHAIN_INVALID")
        if len({entry.manifest_id for entry in entries}) != 1:
            raise _StoreFailure("STORE_CHAIN_INVALID")
    human_review = (
        (chain.human_review_required if chain is not None else False)
        or any(reference.human_review_required for reference in references)
    )
    return ManifestStoreSnapshot(
        dataset_references=references,
        manifest_entries=entries,
        chain_validation=chain,
        human_review_required=bool(human_review),
        advisory_only=True,
        no_execution_authority=True,
    )


def _load_path(path: Path) -> ManifestStoreResult:
    connection: sqlite3.Connection | None = None
    try:
        connection = _connect(path, "ro")
        snapshot = _load_snapshot(connection)
        return _valid_result("STORE_LOADED_VERIFIED", snapshot)
    except _StoreFailure as failure:
        return _rejected(failure.code)
    except sqlite3.Error:
        return _rejected("STORE_SQLITE_INTEGRITY_FAILED")
    except (OSError, TypeError, ValueError, UnicodeError):
        return _rejected("STORE_OPEN_FAILED")
    except Exception:
        return _rejected("STORE_OPEN_FAILED")
    finally:
        if connection is not None:
            connection.close()


def initialize_manifest_store(path: object) -> ManifestStoreResult:
    """Create the exact schema or verify an existing compatible store."""

    try:
        normalized = _normalize_path(path, must_exist=False)
        existed = _path_exists(normalized)
    except _StoreFailure as failure:
        return _rejected(failure.code)

    if existed:
        existing = _load_path(normalized)
        if existing.is_valid and existing.snapshot is not None:
            return _valid_result("STORE_ALREADY_INITIALIZED", existing.snapshot)
        # Probe an incompatible pre-existing file read-only.  Only the exact
        # pristine SQLite state may proceed to a writable initialization; an
        # unrelated, corrupt, drifted, or WAL database is never opened writable
        # by initialization and is never repaired.
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
            return existing if existed else _rejected("STORE_SCHEMA_UNSUPPORTED")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(_CREATE_STORE_META)
        connection.execute(_CREATE_DATASET_REFERENCES)
        connection.execute(_CREATE_MANIFEST_ENTRIES)
        connection.execute(
            "INSERT INTO store_meta (singleton, format_id, schema_version) VALUES (?, ?, ?)",
            (1, MANIFEST_STORE_FORMAT_ID, MANIFEST_STORE_SCHEMA_VERSION),
        )
        connection.execute(f"PRAGMA user_version={MANIFEST_STORE_SCHEMA_VERSION}")
        _verify_schema(connection)
        connection.execute("COMMIT")
        committed = True
    except _StoreFailure as failure:
        if connection is not None and connection.in_transaction:
            connection.execute("ROLLBACK")
        return _rejected(failure.code)
    except sqlite3.Error as error:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("STORE_BUSY" if _is_busy(error) else "STORE_WRITE_FAILED")
    except Exception:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("STORE_WRITE_FAILED")
    finally:
        if connection is not None:
            connection.close()
        if created_here and not committed:
            # Never remove pre-existing caller data.  A brand-new file that did
            # not commit the exact schema is cleaned up before returning.
            _remove_created_store(normalized)

    verified = _load_path(normalized)
    if not verified.is_valid or verified.snapshot is None:
        if created_here:
            _remove_created_store(normalized)
        return verified
    return _valid_result("STORE_INITIALIZED", verified.snapshot)


def load_and_verify_manifest_store(path: object) -> ManifestStoreResult:
    """Read one existing store in SQLite read-only mode and verify everything."""

    try:
        normalized = _normalize_path(path, must_exist=True)
    except _StoreFailure as failure:
        return _rejected(failure.code)
    return _load_path(normalized)


def _validate_reference_input(value: object) -> DatasetSnapshotReference:
    if type(value) is not DatasetSnapshotReference:
        raise _StoreFailure("STORE_REFERENCE_INVALID")
    try:
        result = build_dataset_snapshot_reference(_object_mapping(value))
    except Exception:
        raise _StoreFailure("STORE_REFERENCE_INVALID") from None
    if not result.is_valid or result.reference != value:
        raise _StoreFailure("STORE_REFERENCE_INVALID")
    return value


def _validate_entry_input(value: object) -> ManifestEntry:
    if type(value) is not ManifestEntry:
        raise _StoreFailure("STORE_ENTRY_INVALID")
    try:
        result = build_manifest_entry(_object_mapping(value))
    except Exception:
        raise _StoreFailure("STORE_ENTRY_INVALID") from None
    if not result.is_valid or result.entry != value:
        raise _StoreFailure("STORE_ENTRY_INVALID")
    return value


def _validated_batch(
    dataset_references: object,
    manifest_entries: object,
) -> tuple[tuple[DatasetSnapshotReference, ...], tuple[ManifestEntry, ...]]:
    if type(dataset_references) not in (list, tuple) or type(manifest_entries) not in (
        list,
        tuple,
    ):
        raise _StoreFailure("STORE_INPUT_INVALID")
    reference_tuple = tuple(dataset_references)
    entry_tuple = tuple(manifest_entries)
    references = tuple(_validate_reference_input(value) for value in reference_tuple)
    entries = tuple(_validate_entry_input(value) for value in entry_tuple)
    return references, entries


def _deduplicate_batch(
    values: tuple[object, ...], id_field: str
) -> tuple[dict[str, object], set[str]]:
    unique: dict[str, object] = {}
    repeated: set[str] = set()
    for value in values:
        identity = getattr(value, id_field)
        prior = unique.get(identity)
        if prior is None:
            unique[identity] = value
        elif prior == value:
            repeated.add(identity)
        else:
            raise _StoreFailure("STORE_DUPLICATE_CONFLICT")
    return unique, repeated


def _after_insert_hook() -> None:
    """Private deterministic test seam; production behavior is a no-op."""


def append_manifest_store_batch(
    path: object,
    *,
    dataset_references: Sequence[DatasetSnapshotReference] = (),
    manifest_entries: Sequence[ManifestEntry] = (),
) -> ManifestStoreResult:
    """Atomically append a bounded batch of already-valid WP160 objects."""

    try:
        proposed_references, proposed_entries = _validated_batch(
            dataset_references, manifest_entries
        )
    except _StoreFailure as failure:
        return _rejected(failure.code)
    try:
        normalized = _normalize_path(path, must_exist=True)
    except _StoreFailure as failure:
        return _rejected(failure.code)

    if not proposed_references and not proposed_entries:
        loaded = _load_path(normalized)
        if not loaded.is_valid or loaded.snapshot is None:
            return loaded
        return _valid_result("STORE_APPEND_IDEMPOTENT", loaded.snapshot)

    connection: sqlite3.Connection | None = None
    try:
        unique_references, repeated_references = _deduplicate_batch(
            tuple(proposed_references), "dataset_snapshot_reference_id"
        )
        unique_entries, repeated_entries = _deduplicate_batch(
            tuple(proposed_entries), "manifest_entry_id"
        )
        connection = _connect(normalized, "rw")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        existing_snapshot = _load_snapshot(connection)

        existing_references = {
            value.dataset_snapshot_reference_id: value
            for value in existing_snapshot.dataset_references
        }
        existing_entries = {
            value.manifest_entry_id: value for value in existing_snapshot.manifest_entries
        }
        prospective_references = dict(existing_references)
        prospective_entries = dict(existing_entries)
        insert_references: dict[str, DatasetSnapshotReference] = {}
        insert_entries: dict[str, ManifestEntry] = {}
        idempotent_references = set(repeated_references)
        idempotent_entries = set(repeated_entries)

        for identity, raw_value in unique_references.items():
            value = raw_value
            assert isinstance(value, DatasetSnapshotReference)
            prior = existing_references.get(identity)
            if prior is not None:
                if prior != value:
                    raise _StoreFailure("STORE_DUPLICATE_CONFLICT")
                idempotent_references.add(identity)
            else:
                prospective_references[identity] = value
                insert_references[identity] = value

        sequence_registry = {
            (entry.manifest_id, entry.sequence_number): entry
            for entry in existing_snapshot.manifest_entries
        }
        for identity, raw_value in unique_entries.items():
            value = raw_value
            assert isinstance(value, ManifestEntry)
            prior = existing_entries.get(identity)
            if prior is not None:
                if prior != value:
                    raise _StoreFailure("STORE_DUPLICATE_CONFLICT")
                idempotent_entries.add(identity)
                continue
            sequence_key = (value.manifest_id, value.sequence_number)
            sequence_prior = sequence_registry.get(sequence_key)
            if sequence_prior is not None and sequence_prior != value:
                raise _StoreFailure("STORE_DUPLICATE_CONFLICT")
            sequence_registry[sequence_key] = value
            prospective_entries[identity] = value
            insert_entries[identity] = value

        if len(prospective_references) > _MAX_ROWS or len(prospective_entries) > _MAX_ROWS:
            raise _StoreFailure("STORE_LIMIT_EXCEEDED")
        ordered_references = tuple(
            prospective_references[key] for key in sorted(prospective_references)
        )
        ordered_entries = tuple(
            sorted(prospective_entries.values(), key=lambda entry: entry.sequence_number)
        )
        if ordered_entries:
            chain = validate_manifest_chain(
                ordered_entries, dataset_references=ordered_references
            )
            if not chain.is_valid or chain.status != "CHAIN_VALID":
                raise _StoreFailure("STORE_CHAIN_INVALID")

        for identity in sorted(insert_references):
            value = insert_references[identity]
            payload_json, payload_digest = _serialize(value)
            connection.execute(
                "INSERT INTO dataset_references "
                "(dataset_snapshot_reference_id, payload_json, payload_sha256) "
                "VALUES (?, ?, ?)",
                (identity, payload_json, payload_digest),
            )
            _after_insert_hook()
        for value in sorted(insert_entries.values(), key=lambda entry: entry.sequence_number):
            payload_json, payload_digest = _serialize(value)
            connection.execute(
                "INSERT INTO manifest_entries "
                "(manifest_entry_id, manifest_id, sequence_number, "
                "dataset_snapshot_reference_id, payload_json, payload_sha256) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    value.manifest_entry_id,
                    value.manifest_id,
                    value.sequence_number,
                    value.dataset_snapshot_reference_id,
                    payload_json,
                    payload_digest,
                ),
            )
            _after_insert_hook()
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise _StoreFailure("STORE_SQLITE_INTEGRITY_FAILED")
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
        return _rejected("STORE_BUSY" if _is_busy(error) else "STORE_WRITE_FAILED")
    except Exception:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("STORE_WRITE_FAILED")
    finally:
        if connection is not None:
            connection.close()

    verified = _load_path(normalized)
    if not verified.is_valid or verified.snapshot is None:
        return verified
    inserted_reference_ids = tuple(sorted(insert_references))
    inserted_entry_ids = tuple(
        entry.manifest_entry_id
        for entry in sorted(insert_entries.values(), key=lambda item: item.sequence_number)
    )
    idempotent_entry_ids = tuple(
        entry.manifest_entry_id
        for entry in sorted(
            (prospective_entries[identity] for identity in idempotent_entries),
            key=lambda item: item.sequence_number,
        )
    )
    status = (
        "STORE_APPEND_COMMITTED"
        if inserted_reference_ids or inserted_entry_ids
        else "STORE_APPEND_IDEMPOTENT"
    )
    return _valid_result(
        status,
        verified.snapshot,
        inserted_references=inserted_reference_ids,
        inserted_entries=inserted_entry_ids,
        idempotent_references=tuple(sorted(idempotent_references)),
        idempotent_entries=idempotent_entry_ids,
    )
