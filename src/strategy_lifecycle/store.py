"""Append-only, hash-chained local SQLite strategy-lifecycle store (S10-STRAT-LIFE-01).

One explicit caller-selected ``.sqlite3`` file; no implicit path discovery, no
directory creation, no default path, and no migration. Every load verifies the exact
schema, triggers, SQLite identity, integrity, per-record payload hash, strict JSON,
content IDs, the entry hash chain, and all cross-record transitions by replay. The
current lifecycle state is never stored; it is derived by verified replay only.
Appends are single-record and transactional: a rejected append leaves the database
unchanged. Results expose closed codes only and never raw exception text.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3

from .models import (
    RECORD_KINDS,
    LifecycleRecord,
    StrategyLifecycleError,
    canonical_json_bytes,
    record_from_mapping,
    record_kind_of,
    sha256_hex,
    strict_json_loads,
)
from .policy import StrategyLifecycleSnapshot, _LifecycleState


STORE_FORMAT_ID = "s10-strategy-lifecycle-store"
STORE_SCHEMA_VERSION = 1
STORE_APPLICATION_ID = 0x53544C31  # 1398033457 ("STL1")
STORE_USER_VERSION = 1
MAX_STORE_RECORDS = 100_000
MAX_RECORD_PAYLOAD_BYTES = 262_144
MAX_AGGREGATE_PAYLOAD_BYTES = 536_870_912

STORE_STATUSES = (
    "STORE_INITIALIZED",
    "STORE_ALREADY_INITIALIZED",
    "STORE_APPEND_COMMITTED",
    "STORE_APPEND_IDEMPOTENT",
    "STORE_LOADED_VERIFIED",
    "STORE_REJECTED",
)

_KIND_SQL = ", ".join(f"'{kind}'" for kind in RECORD_KINDS)
_CREATE_META = (
    "CREATE TABLE lifecycle_meta ("
    " singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),"
    f" format_id TEXT NOT NULL CHECK (format_id = '{STORE_FORMAT_ID}'),"
    f" schema_version INTEGER NOT NULL CHECK (schema_version = {STORE_SCHEMA_VERSION})"
    ")"
)
_CREATE_RECORDS = (
    "CREATE TABLE lifecycle_records ("
    " sequence_number INTEGER PRIMARY KEY NOT NULL CHECK (sequence_number >= 0),"
    f" record_kind TEXT NOT NULL CHECK (record_kind IN ({_KIND_SQL})),"
    " record_id TEXT NOT NULL UNIQUE,"
    " payload_json TEXT NOT NULL,"
    " payload_sha256 TEXT NOT NULL,"
    " previous_entry_hash TEXT,"
    " entry_hash TEXT NOT NULL UNIQUE"
    ")"
)


def _trigger(table: str, operation: str) -> str:
    return (
        f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table}"
        f" BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
    )


_EXPECTED_OBJECTS = {
    ("table", "lifecycle_meta"): _CREATE_META,
    ("table", "lifecycle_records"): _CREATE_RECORDS,
    ("trigger", "lifecycle_meta_no_delete"): _trigger("lifecycle_meta", "DELETE"),
    ("trigger", "lifecycle_meta_no_update"): _trigger("lifecycle_meta", "UPDATE"),
    ("trigger", "lifecycle_records_no_delete"): _trigger("lifecycle_records", "DELETE"),
    ("trigger", "lifecycle_records_no_update"): _trigger("lifecycle_records", "UPDATE"),
}


@dataclass(frozen=True)
class StrategyLifecycleStoreResult:
    """Small closed public result; the snapshot is present only on success."""

    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    snapshot: StrategyLifecycleSnapshot | None
    record_id: str | None


def _rejected(code: str) -> StrategyLifecycleStoreResult:
    return StrategyLifecycleStoreResult(
        False, "STORE_REJECTED", (StrategyLifecycleError(code).code,), None, None
    )


def _accepted(
    status: str, snapshot: StrategyLifecycleSnapshot, record_id: str | None = None
) -> StrategyLifecycleStoreResult:
    return StrategyLifecycleStoreResult(True, status, (), snapshot, record_id)


def _fail(code: str) -> StrategyLifecycleError:
    return StrategyLifecycleError(code)


def _normalize_ddl(sql: object) -> str | None:
    return " ".join(sql.replace("(", " ( ").replace(")", " ) ").split()) if isinstance(sql, str) else None


def entry_hash(
    sequence_number: int,
    record_kind: str,
    record_id: str,
    payload_sha256: str,
    previous_entry_hash: str | None,
) -> str:
    """SHA-256 of the canonical JSON binding one entry to its exact predecessor."""

    return sha256_hex(
        canonical_json_bytes(
            {
                "sequence_number": sequence_number,
                "record_kind": record_kind,
                "record_id": record_id,
                "payload_sha256": payload_sha256,
                "previous_entry_hash": previous_entry_hash,
            }
        )
    )


# ---------------------------------------------------------------------------
# Path and connection safety.
# ---------------------------------------------------------------------------


def _validated_path(path: object, *, must_exist: bool) -> Path:
    if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
        raise _fail("FIELD_TYPE_INVALID")
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise _fail("FIELD_VALUE_INVALID")
    target = Path(raw).absolute()
    try:
        if target.suffix != ".sqlite3":
            raise _fail("FIELD_VALUE_INVALID")
        parent = target.parent
        if not parent.is_dir() or any(item.is_symlink() for item in (parent, *parent.parents)):
            raise _fail("FIELD_VALUE_INVALID")
        if target.is_symlink():
            raise _fail("FIELD_VALUE_INVALID")
        if target.exists():
            if not target.is_file() or target.lstat().st_nlink != 1:
                raise _fail("FIELD_VALUE_INVALID")
        elif must_exist:
            raise _fail("FIELD_VALUE_INVALID")
    except OSError:
        raise _fail("FIELD_VALUE_INVALID") from None
    return target


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    try:
        return sqlite3.connect(
            f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None, timeout=0.0
        )
    except sqlite3.Error:
        raise _fail("SCHEMA_CONFLICT") from None


def _configure_writable(connection: sqlite3.Connection) -> None:
    mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    if mode is None or str(mode[0]).lower() != "delete":
        raise _fail("INTERNAL_VALIDATION_FAILED")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA foreign_keys=ON")


# ---------------------------------------------------------------------------
# Verified load.
# ---------------------------------------------------------------------------


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA application_id").fetchone() != (STORE_APPLICATION_ID,):
        raise _fail("SCHEMA_CONFLICT")
    if connection.execute("PRAGMA user_version").fetchone() != (STORE_USER_VERSION,):
        raise _fail("SCHEMA_CONFLICT")
    objects = connection.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    actual = {(kind, name): _normalize_ddl(sql) for kind, name, sql in objects}
    expected = {key: _normalize_ddl(sql) for key, sql in _EXPECTED_OBJECTS.items()}
    if len(objects) != len(actual) or actual != expected:
        raise _fail("SCHEMA_CONFLICT")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise _fail("INTEGRITY_TAMPER")
    if connection.execute(
        "SELECT singleton, format_id, schema_version FROM lifecycle_meta"
    ).fetchall() != [(1, STORE_FORMAT_ID, STORE_SCHEMA_VERSION)]:
        raise _fail("INTEGRITY_TAMPER")


@dataclass(frozen=True)
class _Loaded:
    payloads: dict[str, str]
    state: _LifecycleState
    head: str | None
    rows: int
    payload_bytes: int

    def snapshot(self) -> StrategyLifecycleSnapshot:
        return self.state.snapshot(
            store_head_entry_hash=self.head,
            total_rows=self.rows,
            total_payload_bytes=self.payload_bytes,
        )


def _load(connection: sqlite3.Connection) -> _Loaded:
    _verify_schema(connection)
    count = connection.execute("SELECT COUNT(*) FROM lifecycle_records").fetchone()[0]
    if count > MAX_STORE_RECORDS:
        raise _fail("INTEGRITY_TAMPER")
    rows = connection.execute(
        "SELECT sequence_number, record_kind, record_id, payload_json, payload_sha256,"
        " previous_entry_hash, entry_hash FROM lifecycle_records ORDER BY sequence_number"
    ).fetchall()
    state = _LifecycleState()
    payloads: dict[str, str] = {}
    previous: str | None = None
    total_bytes = 0
    for index, row in enumerate(rows):
        sequence, kind, record_id, payload_json, payload_sha, previous_hash, current_hash = row
        if (
            sequence != index
            or kind not in RECORD_KINDS
            or not isinstance(record_id, str)
            or not isinstance(payload_json, str)
            or not isinstance(payload_sha, str)
            or previous_hash != previous
            or not isinstance(current_hash, str)
        ):
            raise _fail("INTEGRITY_TAMPER")
        payload_bytes = payload_json.encode("utf-8")
        total_bytes += len(payload_bytes)
        if len(payload_bytes) > MAX_RECORD_PAYLOAD_BYTES or total_bytes > MAX_AGGREGATE_PAYLOAD_BYTES:
            raise _fail("INTEGRITY_TAMPER")
        if sha256_hex(payload_bytes) != payload_sha:
            raise _fail("INTEGRITY_TAMPER")
        try:
            decoded = strict_json_loads(payload_json)
            if canonical_json_bytes(decoded) != payload_bytes:
                raise _fail("INTEGRITY_TAMPER")
            record = record_from_mapping(kind, decoded)
        except StrategyLifecycleError:
            raise _fail("INTEGRITY_TAMPER") from None
        if record.record_id != record_id:
            raise _fail("INTEGRITY_TAMPER")
        if entry_hash(sequence, kind, record_id, payload_sha, previous_hash) != current_hash:
            raise _fail("INTEGRITY_TAMPER")
        try:
            state.apply(record)
        except StrategyLifecycleError:
            raise _fail("INTEGRITY_TAMPER") from None
        payloads[record_id] = payload_json
        previous = current_hash
    return _Loaded(payloads, state, previous, len(rows), total_bytes)


def _load_path(path: Path) -> StrategyLifecycleStoreResult:
    connection = None
    try:
        connection = _connect(path, "ro")
        loaded = _load(connection)
        return _accepted("STORE_LOADED_VERIFIED", loaded.snapshot())
    except StrategyLifecycleError as failure:
        return _rejected(failure.code)
    except sqlite3.Error:
        return _rejected("INTEGRITY_TAMPER")
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
    finally:
        if connection is not None:
            connection.close()


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def initialize_strategy_lifecycle_store(path: object) -> StrategyLifecycleStoreResult:
    """Create the exact empty store, or verify an existing one. Never migrates."""

    try:
        target = _validated_path(path, must_exist=False)
    except StrategyLifecycleError as failure:
        return _rejected(failure.code)
    if target.exists():
        existing = _load_path(target)
        if not existing.is_valid:
            return existing
        return _accepted("STORE_ALREADY_INITIALIZED", existing.snapshot)  # type: ignore[arg-type]

    try:
        descriptor = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(descriptor)
    except OSError:
        return _rejected("FIELD_VALUE_INVALID")
    connection = None
    committed = False
    try:
        connection = _connect(target, "rw")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        for sql in _EXPECTED_OBJECTS.values():
            connection.execute(sql)
        connection.execute(
            "INSERT INTO lifecycle_meta (singleton, format_id, schema_version) VALUES (?, ?, ?)",
            (1, STORE_FORMAT_ID, STORE_SCHEMA_VERSION),
        )
        connection.execute(f"PRAGMA application_id={STORE_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={STORE_USER_VERSION}")
        connection.execute("COMMIT")
        committed = True
    except (StrategyLifecycleError, sqlite3.Error):
        pass
    finally:
        if connection is not None:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            connection.close()
        if not committed:
            try:
                target.unlink()
            except OSError:
                pass
    if not committed:
        return _rejected("INTERNAL_VALIDATION_FAILED")
    verified = _load_path(target)
    if not verified.is_valid:
        return verified
    return _accepted("STORE_INITIALIZED", verified.snapshot)  # type: ignore[arg-type]


def load_strategy_lifecycle_store(path: object) -> StrategyLifecycleStoreResult:
    """Read one existing store read-only and fully verify it by replay."""

    try:
        target = _validated_path(path, must_exist=True)
    except StrategyLifecycleError as failure:
        return _rejected(failure.code)
    return _load_path(target)


def append_strategy_lifecycle_record(
    path: object, record: LifecycleRecord
) -> StrategyLifecycleStoreResult:
    """Transactionally append exactly one record after full verification and replay."""

    try:
        target = _validated_path(path, must_exist=True)
        kind = record_kind_of(record)
        mapping = record.to_mapping()
        if record_from_mapping(kind, mapping) != record:
            raise _fail("IDENTITY_CONFLICT")
        payload_bytes = canonical_json_bytes(mapping)
    except StrategyLifecycleError as failure:
        return _rejected(failure.code)
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
    if len(payload_bytes) > MAX_RECORD_PAYLOAD_BYTES:
        return _rejected("LIMIT_EXCEEDED")
    payload_json = payload_bytes.decode("utf-8")
    payload_sha = sha256_hex(payload_bytes)
    record_id = record.record_id

    connection = None
    try:
        connection = _connect(target, "rw")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            loaded = _load(connection)
        except StrategyLifecycleError as failure:
            code = failure.code if failure.code == "SCHEMA_CONFLICT" else "INTEGRITY_TAMPER"
            raise _fail(code) from None
        existing = loaded.payloads.get(record_id)
        if existing is not None:
            if existing != payload_json:
                raise _fail("IDENTITY_CONFLICT")
            connection.execute("ROLLBACK")
            return _accepted("STORE_APPEND_IDEMPOTENT", loaded.snapshot(), record_id)
        if (
            loaded.rows + 1 > MAX_STORE_RECORDS
            or loaded.payload_bytes + len(payload_bytes) > MAX_AGGREGATE_PAYLOAD_BYTES
        ):
            raise _fail("LIMIT_EXCEEDED")
        candidate = loaded.state.copy()
        candidate.apply(record)
        current_hash = entry_hash(loaded.rows, kind, record_id, payload_sha, loaded.head)
        connection.execute(
            "INSERT INTO lifecycle_records (sequence_number, record_kind, record_id,"
            " payload_json, payload_sha256, previous_entry_hash, entry_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (loaded.rows, kind, record_id, payload_json, payload_sha, loaded.head, current_hash),
        )
        verified = _load(connection)
        if verified.head != current_hash or verified.rows != loaded.rows + 1:
            raise _fail("INTERNAL_VALIDATION_FAILED")
        connection.execute("COMMIT")
        return _accepted("STORE_APPEND_COMMITTED", verified.snapshot(), record_id)
    except StrategyLifecycleError as failure:
        return _rejected(failure.code)
    except sqlite3.Error:
        return _rejected("INTERNAL_VALIDATION_FAILED")
    except Exception:
        return _rejected("INTERNAL_VALIDATION_FAILED")
    finally:
        if connection is not None:
            if connection.in_transaction:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            connection.close()
