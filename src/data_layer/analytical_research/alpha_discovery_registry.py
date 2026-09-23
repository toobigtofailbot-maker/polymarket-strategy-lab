"""Bounded append-only SQLite memory for S10-ALPHA-02 decision evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Mapping

from .alpha_discovery import (
    AlphaDiscoveryPolicy,
    AlphaResearchQueueSnapshot,
    AlphaUniverseSnapshot,
    MarketTriageDecision,
    MaterialChangeEvent,
    _validate_alpha_discovery_record,
    alpha_discovery_record_from_mapping,
    alpha_discovery_record_to_mapping,
)


ALPHA_DISCOVERY_REGISTRY_FORMAT_ID = "s10-alpha-discovery-registry"
ALPHA_DISCOVERY_REGISTRY_SCHEMA_VERSION = 1
ALPHA_DISCOVERY_REGISTRY_APPLICATION_ID = 1464877426
MAX_DISCOVERY_APPEND_BATCH = 1024
MAX_DISCOVERY_REGISTRY_RECORDS = 100_000
MAX_DISCOVERY_RECORD_PAYLOAD_BYTES = 1_048_576
MAX_DISCOVERY_STORE_PAYLOAD_BYTES = 536_870_912

DISCOVERY_RECORD_KIND_TYPES = (
    ("DISCOVERY_POLICY", AlphaDiscoveryPolicy, "alpha_discovery_policy_id"),
    ("UNIVERSE_SNAPSHOT", AlphaUniverseSnapshot, "alpha_universe_snapshot_id"),
    ("MATERIAL_CHANGE", MaterialChangeEvent, "material_change_event_id"),
    ("TRIAGE_DECISION", MarketTriageDecision, "market_triage_decision_id"),
    ("RESEARCH_QUEUE", AlphaResearchQueueSnapshot, "alpha_research_queue_snapshot_id"),
)
_KIND_TO_TYPE = {kind: cls for kind, cls, _ in DISCOVERY_RECORD_KIND_TYPES}
_TYPE_TO_KIND = {cls: (kind, id_field) for kind, cls, id_field in DISCOVERY_RECORD_KIND_TYPES}
_KIND_RANK = {kind: rank for rank, (kind, _, _) in enumerate(DISCOVERY_RECORD_KIND_TYPES)}

ALPHA_DISCOVERY_REGISTRY_STATUSES = (
    "REGISTRY_INITIALIZED", "REGISTRY_ALREADY_INITIALIZED", "REGISTRY_APPEND_COMMITTED",
    "REGISTRY_APPEND_IDEMPOTENT", "REGISTRY_LOADED_VERIFIED", "REGISTRY_REJECTED",
)
ALPHA_DISCOVERY_REGISTRY_ERROR_CODES = (
    "PATH_INVALID", "PATH_NOT_FOUND", "PATH_AMBIGUOUS", "REGISTRY_SCHEMA_CONFLICT",
    "REGISTRY_INTEGRITY_INVALID", "REGISTRY_IDENTITY_CONFLICT", "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID", "REFERENCE_INVALID", "LIMIT_EXCEEDED", "INTERNAL_VALIDATION_FAILED",
)


@dataclass(frozen=True)
class AlphaDiscoveryRegistryEntry:
    sequence_number: int
    record_kind: str
    record_id: str
    payload_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    record: object


@dataclass(frozen=True)
class AlphaDiscoveryRegistrySnapshot:
    schema_id: str
    schema_version: str
    entries: tuple[AlphaDiscoveryRegistryEntry, ...]
    total_rows: int
    total_payload_bytes: int
    head_entry_hash: str | None
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AlphaDiscoveryRegistryResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    snapshot: AlphaDiscoveryRegistrySnapshot | None
    inserted_record_ids: tuple[str, ...]
    idempotent_record_ids: tuple[str, ...]
    advisory_only: bool = True
    no_execution_authority: bool = True
    no_strategy_authority: bool = True
    no_qualification_authority: bool = True


class _Failure(Exception):
    def __init__(self, code: str): self.code = code


def _reject(code: str) -> AlphaDiscoveryRegistryResult:
    if code not in ALPHA_DISCOVERY_REGISTRY_ERROR_CODES: code = "INTERNAL_VALIDATION_FAILED"
    return AlphaDiscoveryRegistryResult(False, "REGISTRY_REJECTED", (code,), None, (), ())


def _ok(status: str, snapshot: AlphaDiscoveryRegistrySnapshot, inserted=(), idempotent=()) -> AlphaDiscoveryRegistryResult:
    return AlphaDiscoveryRegistryResult(True, status, (), snapshot, tuple(inserted), tuple(idempotent))


def _path(value: object, *, must_exist: bool) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise _Failure("PATH_INVALID")
    raw = os.fspath(value)
    if not raw or raw == ":memory:" or "\x00" in raw:
        raise _Failure("PATH_INVALID")
    target = Path(raw)
    if target.suffix != ".sqlite3" or not target.is_absolute():
        raise _Failure("PATH_INVALID")
    parent = target.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise _Failure("PATH_INVALID")
    if must_exist and not target.exists():
        raise _Failure("PATH_NOT_FOUND")
    if target.exists():
        stat = target.lstat()
        if target.is_symlink() or not target.is_file() or stat.st_nlink != 1:
            raise _Failure("PATH_AMBIGUOUS")
    return target.resolve(strict=must_exist)


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode={mode}", uri=True, isolation_level=None)
    connection.execute("PRAGMA busy_timeout=0")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    actual = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
    if str(actual).lower() != "delete":
        connection.close(); raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    return connection


_CREATE_META = """CREATE TABLE discovery_registry_meta(
singleton INTEGER PRIMARY KEY CHECK(singleton=1), format_id TEXT NOT NULL, schema_version INTEGER NOT NULL) STRICT"""
_KINDS_SQL = ",".join(f"'{x[0]}'" for x in DISCOVERY_RECORD_KIND_TYPES)
_CREATE_RECORDS = f"""CREATE TABLE discovery_registry_records(
sequence_number INTEGER PRIMARY KEY, record_kind TEXT NOT NULL CHECK(record_kind IN ({_KINDS_SQL})),
record_id TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
previous_entry_hash TEXT, entry_hash TEXT NOT NULL UNIQUE) STRICT"""
_CREATE_UPDATE = """CREATE TRIGGER discovery_registry_no_update BEFORE UPDATE ON discovery_registry_records BEGIN SELECT RAISE(ABORT,'append-only'); END"""
_CREATE_DELETE = """CREATE TRIGGER discovery_registry_no_delete BEFORE DELETE ON discovery_registry_records BEGIN SELECT RAISE(ABORT,'append-only'); END"""


def _canonical(mapping: Mapping[str, object]) -> str:
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _serialize(record: object) -> tuple[str, str, str, str]:
    info = _TYPE_TO_KIND.get(type(record))
    if info is None: raise _Failure("FIELD_TYPE_INVALID")
    kind, id_field = info
    try:
        _validate_alpha_discovery_record(record)
        mapping = alpha_discovery_record_to_mapping(record)
    except ValueError:
        raise _Failure("FIELD_VALUE_INVALID") from None
    payload = _canonical(mapping)
    encoded = payload.encode()
    if len(encoded) > MAX_DISCOVERY_RECORD_PAYLOAD_BYTES: raise _Failure("LIMIT_EXCEEDED")
    return kind, getattr(record, id_field), payload, hashlib.sha256(encoded).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("duplicate key")
        result[key] = value
    return result


def _decode(kind: str, payload: str) -> object:
    cls = _KIND_TO_TYPE.get(kind)
    if cls is None: raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    try:
        mapping = json.loads(payload, object_pairs_hook=_pairs, parse_float=lambda _: (_ for _ in ()).throw(ValueError()))
        return alpha_discovery_record_from_mapping(cls, mapping)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise _Failure("REGISTRY_INTEGRITY_INVALID") from None


def _entry_hash(sequence: int, kind: str, record_id: str, payload_sha: str, previous: str | None) -> str:
    value = {"sequence_number": sequence, "record_kind": kind, "record_id": record_id,
             "payload_sha256": payload_sha, "previous_entry_hash": previous}
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA application_id").fetchone()[0] != ALPHA_DISCOVERY_REGISTRY_APPLICATION_ID: raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    if connection.execute("PRAGMA user_version").fetchone()[0] != ALPHA_DISCOVERY_REGISTRY_SCHEMA_VERSION: raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok": raise _Failure("REGISTRY_INTEGRITY_INVALID")
    meta = connection.execute("SELECT format_id,schema_version FROM discovery_registry_meta WHERE singleton=1").fetchall()
    if meta != [(ALPHA_DISCOVERY_REGISTRY_FORMAT_ID, ALPHA_DISCOVERY_REGISTRY_SCHEMA_VERSION)]: raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    required = {"discovery_registry_meta", "discovery_registry_records"}
    actual = {x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table'") if not x[0].startswith("sqlite_")}
    if actual != required: raise _Failure("REGISTRY_SCHEMA_CONFLICT")
    triggers = {x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    if triggers != {"discovery_registry_no_update", "discovery_registry_no_delete"}: raise _Failure("REGISTRY_SCHEMA_CONFLICT")


def _cross(entries: tuple[AlphaDiscoveryRegistryEntry, ...]) -> None:
    by_id = {e.record_id: e.record for e in entries}
    for entry in entries:
        r = entry.record
        if isinstance(r, AlphaUniverseSnapshot):
            if not isinstance(by_id.get(r.policy_id), AlphaDiscoveryPolicy): raise _Failure("REFERENCE_INVALID")
        elif isinstance(r, MaterialChangeEvent):
            if not isinstance(by_id.get(r.policy_id), AlphaDiscoveryPolicy) or not isinstance(by_id.get(r.prior_universe_id), AlphaUniverseSnapshot) or not isinstance(by_id.get(r.current_universe_id), AlphaUniverseSnapshot): raise _Failure("REFERENCE_INVALID")
        elif isinstance(r, MarketTriageDecision):
            universe = by_id.get(r.universe_id)
            if not isinstance(by_id.get(r.policy_id), AlphaDiscoveryPolicy) or not isinstance(universe, AlphaUniverseSnapshot): raise _Failure("REFERENCE_INVALID")
            if r.material_change_event_id and not isinstance(by_id.get(r.material_change_event_id), MaterialChangeEvent): raise _Failure("REFERENCE_INVALID")
            if isinstance(universe, AlphaUniverseSnapshot) and r.market_id not in {m.market_id for m in universe.markets}: raise _Failure("REFERENCE_INVALID")
        elif isinstance(r, AlphaResearchQueueSnapshot):
            universe = by_id.get(r.universe_id)
            if not isinstance(by_id.get(r.policy_id), AlphaDiscoveryPolicy) or not isinstance(universe, AlphaUniverseSnapshot): raise _Failure("REFERENCE_INVALID")
            triages = [by_id.get(x) for x in r.all_triage_ids]
            if any(not isinstance(x, MarketTriageDecision) for x in triages): raise _Failure("REFERENCE_INVALID")
            if len(set(r.all_triage_ids)) != len(r.all_triage_ids): raise _Failure("REFERENCE_INVALID")
            if isinstance(universe, AlphaUniverseSnapshot) and {x.market_id for x in triages} != {m.market_id for m in universe.markets}: raise _Failure("REFERENCE_INVALID")


def _load(connection: sqlite3.Connection) -> AlphaDiscoveryRegistrySnapshot:
    _verify_schema(connection)
    rows = connection.execute("SELECT sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash FROM discovery_registry_records ORDER BY sequence_number").fetchall()
    if len(rows) > MAX_DISCOVERY_REGISTRY_RECORDS: raise _Failure("LIMIT_EXCEEDED")
    entries = []; previous = None; total = 0
    for expected, row in enumerate(rows):
        sequence, kind, record_id, payload, payload_sha, stored_previous, stored_hash = row
        if sequence != expected or stored_previous != previous: raise _Failure("REGISTRY_INTEGRITY_INVALID")
        encoded = payload.encode(); total += len(encoded)
        if hashlib.sha256(encoded).hexdigest() != payload_sha or _entry_hash(sequence, kind, record_id, payload_sha, previous) != stored_hash: raise _Failure("REGISTRY_INTEGRITY_INVALID")
        record = _decode(kind, payload)
        if _serialize(record) != (kind, record_id, payload, payload_sha): raise _Failure("REGISTRY_INTEGRITY_INVALID")
        entries.append(AlphaDiscoveryRegistryEntry(sequence, kind, record_id, payload_sha, previous, stored_hash, record)); previous = stored_hash
    if total > MAX_DISCOVERY_STORE_PAYLOAD_BYTES: raise _Failure("LIMIT_EXCEEDED")
    result = AlphaDiscoveryRegistrySnapshot("alpha-discovery-registry-snapshot", "1.0.0", tuple(entries), len(entries), total, previous, True, True, True, True)
    _cross(result.entries)
    return result


def _remove_created(path: Path) -> None:
    try:
        if path.exists() and not path.is_symlink() and path.lstat().st_nlink == 1: path.unlink()
    except OSError: pass


def initialize_alpha_discovery_registry(path: object) -> AlphaDiscoveryRegistryResult:
    created = False; target = None
    try:
        target = _path(path, must_exist=False); existed = target.exists()
        if not existed:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd); created = True
        connection = _connect(target, "rwc")
        try:
            if existed: return _ok("REGISTRY_ALREADY_INITIALIZED", _load(connection))
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_CREATE_META); connection.execute(_CREATE_RECORDS); connection.execute(_CREATE_UPDATE); connection.execute(_CREATE_DELETE)
            connection.execute("INSERT INTO discovery_registry_meta VALUES(1,?,?)", (ALPHA_DISCOVERY_REGISTRY_FORMAT_ID, ALPHA_DISCOVERY_REGISTRY_SCHEMA_VERSION))
            connection.execute(f"PRAGMA application_id={ALPHA_DISCOVERY_REGISTRY_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={ALPHA_DISCOVERY_REGISTRY_SCHEMA_VERSION}")
            connection.execute("COMMIT")
            return _ok("REGISTRY_INITIALIZED", _load(connection))
        finally: connection.close()
    except _Failure as failure:
        if created and target is not None: _remove_created(target)
        return _reject(failure.code)
    except Exception:
        if created and target is not None: _remove_created(target)
        return _reject("INTERNAL_VALIDATION_FAILED")


def append_alpha_discovery_records(path: object, records: object) -> AlphaDiscoveryRegistryResult:
    try:
        target = _path(path, must_exist=True)
        if not isinstance(records, (list, tuple)): raise _Failure("FIELD_TYPE_INVALID")
        if not records: raise _Failure("FIELD_VALUE_INVALID")
        if len(records) > MAX_DISCOVERY_APPEND_BATCH: raise _Failure("LIMIT_EXCEEDED")
        by_id = {}
        for item in map(_serialize, records):
            prior = by_id.get(item[1])
            if prior is not None and prior != item: raise _Failure("REGISTRY_IDENTITY_CONFLICT")
            by_id[item[1]] = item
        connection = _connect(target, "rwc")
        try:
            connection.execute("BEGIN IMMEDIATE"); current = _load(connection); existing = {e.record_id:e for e in current.entries}
            new = []; idempotent = []
            for rid, item in by_id.items():
                found = existing.get(rid)
                if found:
                    if found.record_kind != item[0] or found.payload_sha256 != item[3]: raise _Failure("REGISTRY_IDENTITY_CONFLICT")
                    idempotent.append(rid)
                else: new.append(item)
            new.sort(key=lambda x: (_KIND_RANK[x[0]], x[1], x[3]))
            if current.total_rows + len(new) > MAX_DISCOVERY_REGISTRY_RECORDS or current.total_payload_bytes + sum(len(x[2].encode()) for x in new) > MAX_DISCOVERY_STORE_PAYLOAD_BYTES: raise _Failure("LIMIT_EXCEEDED")
            sequence = current.total_rows; previous = current.head_entry_hash; inserted = []
            for kind, rid, payload, sha in new:
                entry_hash = _entry_hash(sequence, kind, rid, sha, previous)
                connection.execute("INSERT INTO discovery_registry_records VALUES(?,?,?,?,?,?,?)", (sequence, kind, rid, payload, sha, previous, entry_hash))
                inserted.append(rid); previous = entry_hash; sequence += 1
            projected = _load(connection); connection.execute("COMMIT")
            return _ok("REGISTRY_APPEND_COMMITTED" if inserted else "REGISTRY_APPEND_IDEMPOTENT", projected, sorted(inserted), sorted(idempotent))
        except Exception:
            try: connection.execute("ROLLBACK")
            except sqlite3.Error: pass
            raise
        finally: connection.close()
    except _Failure as failure: return _reject(failure.code)
    except sqlite3.Error: return _reject("REGISTRY_SCHEMA_CONFLICT")
    except Exception: return _reject("INTERNAL_VALIDATION_FAILED")


def load_and_verify_alpha_discovery_registry(path: object) -> AlphaDiscoveryRegistryResult:
    try:
        target = _path(path, must_exist=True); connection = _connect(target, "ro")
        try: snapshot = _load(connection)
        finally: connection.close()
        return _ok("REGISTRY_LOADED_VERIFIED", snapshot)
    except _Failure as failure: return _reject(failure.code)
    except Exception: return _reject("INTERNAL_VALIDATION_FAILED")
