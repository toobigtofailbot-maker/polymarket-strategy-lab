"""WP175N / S10-ALPHA-01 bounded append-only SQLite Alpha Factory registry.

Canonical, verified local persistence for validated Alpha Factory research records
(source references, opportunity candidates, hypothesis families, research
episodes). Append-only with a per-entry SHA-256 hash chain; caller batch order never
affects the committed bytes; a rejected batch never mutates the store.

This registry is SEPARATE from the WP170 experiment registry: a distinct
application id (1464877425), format id, schema, record kinds, and file. It has no
network surface, computes no economics, performs no qualification or prioritisation,
and holds no execution/strategy/paper/live/Gate-C authority. Only a validated
ResearchEpisode committed here becomes canonical Alpha research memory.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Mapping

from .alpha_factory import (
    ALPHA_ERROR_CODES,
    MAX_ALPHA_RECORD_PAYLOAD_BYTES,
    HypothesisFamily,
    OpportunityCandidate,
    ResearchEpisode,
    ResearchSourceReference,
    _canonical_bytes,
    _digest,
    _Failure,
    _validate_public_record,
    record_from_mapping,
    record_to_mapping,
)

ALPHA_REGISTRY_FORMAT_ID = "s10-alpha-factory-registry"
ALPHA_REGISTRY_SCHEMA_VERSION = 1
ALPHA_REGISTRY_APPLICATION_ID = 1464877425

MAX_ALPHA_APPEND_BATCH = 128
MAX_ALPHA_REGISTRY_RECORDS = 50_000
MAX_ALPHA_STORE_PAYLOAD_BYTES = 268_435_456

ALPHA_REGISTRY_STATUSES = (
    "REGISTRY_INITIALIZED",
    "REGISTRY_ALREADY_INITIALIZED",
    "REGISTRY_APPEND_COMMITTED",
    "REGISTRY_APPEND_IDEMPOTENT",
    "REGISTRY_LOADED_VERIFIED",
    "REGISTRY_REJECTED",
)

ALPHA_REGISTRY_ERROR_CODES = (
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "REGISTRY_SCHEMA_CONFLICT",
    "REGISTRY_INTEGRITY_TAMPER",
    "REGISTRY_IDENTITY_CONFLICT",
    "REFERENCE_INVALID",
    "NOVELTY_DUPLICATE",
    "MECHANISM_CONFLICT",
    "LINEAGE_INVALID",
    "LINEAGE_CYCLE",
    "REOPEN_INVALID",
    "RESULT_EVIDENCE_INVALID",
    "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED",
)

# Canonical kind rank (append-order rule 1). Rank drives projected-history order.
RECORD_KIND_TYPES = (
    ("RESEARCH_SOURCE_REFERENCE", ResearchSourceReference, "source_reference_id"),
    ("OPPORTUNITY_CANDIDATE", OpportunityCandidate, "candidate_id"),
    ("HYPOTHESIS_FAMILY", HypothesisFamily, "hypothesis_family_id"),
    ("RESEARCH_EPISODE", ResearchEpisode, "research_episode_id"),
)
_TYPE_INFO = {rtype: (kind, id_field) for kind, rtype, id_field in RECORD_KIND_TYPES}
_KIND_INFO = {kind: (rtype, id_field) for kind, rtype, id_field in RECORD_KIND_TYPES}
_KIND_RANK = {kind: index for index, (kind, _t, _f) in enumerate(RECORD_KIND_TYPES)}

_CREATE_META = """CREATE TABLE alpha_registry_meta (
    singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),
    format_id TEXT NOT NULL CHECK (format_id = 's10-alpha-factory-registry'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
)"""
_KIND_CHECK = ", ".join(f"'{kind}'" for kind in _KIND_INFO)
_CREATE_RECORDS = f"""CREATE TABLE alpha_registry_records (
    sequence_number INTEGER PRIMARY KEY NOT NULL CHECK (sequence_number >= 0),
    record_kind TEXT NOT NULL CHECK (record_kind IN ({_KIND_CHECK})),
    record_id TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    previous_entry_hash TEXT,
    entry_hash TEXT NOT NULL UNIQUE
)"""
_CREATE_NO_UPDATE = """CREATE TRIGGER alpha_registry_records_no_update
BEFORE UPDATE ON alpha_registry_records
BEGIN
    SELECT RAISE(ABORT, 'append-only');
END"""
_CREATE_NO_DELETE = """CREATE TRIGGER alpha_registry_records_no_delete
BEFORE DELETE ON alpha_registry_records
BEGIN
    SELECT RAISE(ABORT, 'append-only');
END"""

_SNAPSHOT_SCHEMA_ID = "alpha-factory-registry-snapshot"
_SNAPSHOT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class AlphaFactoryRegistryEntry:
    sequence_number: int
    record_kind: str
    record_id: str
    payload_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    record: object


@dataclass(frozen=True)
class AlphaFactoryRegistrySnapshot:
    schema_id: str
    schema_version: str
    entries: tuple[AlphaFactoryRegistryEntry, ...]
    total_rows: int
    total_payload_bytes: int
    head_entry_hash: str | None
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


@dataclass(frozen=True)
class AlphaFactoryRegistryResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    snapshot: AlphaFactoryRegistrySnapshot | None
    inserted_record_ids: tuple[str, ...]
    idempotent_record_ids: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool
    no_strategy_authority: bool
    no_qualification_authority: bool


class _StoreFailure(Exception):
    def __init__(self, code: str):
        self.code = code


# Deterministic, exhaustive mapping from every Alpha-model error code to the closed
# public registry error vocabulary. Any Alpha-model validation failure surfaced during
# append is translated here so no model-internal code ever leaks to a public result.
_ALPHA_TO_REGISTRY_ERROR = {
    "SCHEMA_UNSUPPORTED": "FIELD_VALUE_INVALID",
    "FIELD_MISSING": "FIELD_VALUE_INVALID",
    "FIELD_TYPE_INVALID": "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID": "FIELD_VALUE_INVALID",
    "FORBIDDEN_CONTENT": "FIELD_VALUE_INVALID",
    "IDENTITY_DERIVATION_MISMATCH": "REGISTRY_IDENTITY_CONFLICT",
    "REFERENCE_INVALID": "REFERENCE_INVALID",
    "LANE_INVALID": "FIELD_VALUE_INVALID",
    "RESULT_STATE_INVALID": "FIELD_VALUE_INVALID",
    "NOVELTY_DUPLICATE": "NOVELTY_DUPLICATE",
    "MECHANISM_CONFLICT": "MECHANISM_CONFLICT",
    "LINEAGE_INVALID": "LINEAGE_INVALID",
    "LINEAGE_CYCLE": "LINEAGE_CYCLE",
    "REOPEN_INVALID": "REOPEN_INVALID",
    "RESULT_EVIDENCE_INVALID": "RESULT_EVIDENCE_INVALID",
    "LIMIT_EXCEEDED": "LIMIT_EXCEEDED",
    "INTERNAL_VALIDATION_FAILED": "INTERNAL_VALIDATION_FAILED",
}
_REGISTRY_ERROR_SET = frozenset(ALPHA_REGISTRY_ERROR_CODES)


def _map_alpha_error(code: str) -> str:
    """Translate an Alpha-model error code to a closed registry code, fail-closed."""
    return _ALPHA_TO_REGISTRY_ERROR.get(code, "INTERNAL_VALIDATION_FAILED")


def _reject(code: str) -> AlphaFactoryRegistryResult:
    # Final public closure: an out-of-vocabulary code can never reach a public result.
    if code not in _REGISTRY_ERROR_SET:
        code = "INTERNAL_VALIDATION_FAILED"
    return AlphaFactoryRegistryResult(
        False, "REGISTRY_REJECTED", (code,), None, (), (), True, True, True, True
    )


def _success(
    status: str, snapshot: AlphaFactoryRegistrySnapshot,
    inserted: tuple[str, ...] = (), idempotent: tuple[str, ...] = (),
) -> AlphaFactoryRegistryResult:
    return AlphaFactoryRegistryResult(
        True, status, (), snapshot, inserted, idempotent, True, True, True, True
    )


def _path(path: object, *, must_exist: bool) -> Path:
    try:
        if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
            raise _StoreFailure("FIELD_TYPE_INVALID")
        raw = os.fspath(path)
        if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
            raise _StoreFailure("FIELD_VALUE_INVALID")
        candidate = Path(raw).absolute()
        if candidate.suffix != ".sqlite3" or candidate.parent.is_symlink() or candidate.is_symlink():
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if not candidate.parent.exists() or not candidate.parent.is_dir():
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if candidate.exists():
            stat = candidate.lstat()
            if not candidate.is_file() or stat.st_nlink != 1:
                raise _StoreFailure("FIELD_VALUE_INVALID")
        elif must_exist:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        return candidate
    except _StoreFailure:
        raise
    except Exception:
        raise _StoreFailure("FIELD_VALUE_INVALID") from None


def _uri(path: Path, mode: str) -> str:
    return f"{path.as_uri()}?mode={mode}"


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    try:
        return sqlite3.connect(_uri(path, mode), uri=True, isolation_level=None, timeout=0.0)
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _configure(connection: sqlite3.Connection, *, writable: bool) -> None:
    try:
        if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if writable:
            connection.execute("PRAGMA synchronous=FULL")
        if connection.execute("PRAGMA synchronous").fetchone() != (2,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
    except _StoreFailure:
        raise
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _norm_sql(value: str) -> str:
    return " ".join(value.split())


def _verify_schema(connection: sqlite3.Connection) -> None:
    try:
        if connection.execute("PRAGMA application_id").fetchone() != (ALPHA_REGISTRY_APPLICATION_ID,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("PRAGMA user_version").fetchone() != (ALPHA_REGISTRY_SCHEMA_VERSION,):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        objects = connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        expected = [
            ("table", "alpha_registry_meta", _CREATE_META),
            ("table", "alpha_registry_records", _CREATE_RECORDS),
            ("trigger", "alpha_registry_records_no_delete", _CREATE_NO_DELETE),
            ("trigger", "alpha_registry_records_no_update", _CREATE_NO_UPDATE),
        ]
        if [(t, n, _norm_sql(s)) for t, n, s in objects] != [(t, n, _norm_sql(s)) for t, n, s in expected]:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute(
            "SELECT singleton,format_id,schema_version FROM alpha_registry_meta"
        ).fetchall() != [(1, ALPHA_REGISTRY_FORMAT_ID, ALPHA_REGISTRY_SCHEMA_VERSION)]:
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        indexes = connection.execute("PRAGMA index_list(alpha_registry_records)").fetchall()
        signatures = []
        for row in indexes:
            columns = tuple(
                item[2]
                for item in connection.execute(
                    "SELECT * FROM pragma_index_info(?)", (row[1],)
                ).fetchall()
            )
            signatures.append((row[3], columns))
        if sorted(signatures, key=lambda item: item[1]) != sorted(
            [("u", ("record_id",)), ("u", ("entry_hash",))], key=lambda item: item[1]
        ):
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall():
            raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
    except _StoreFailure:
        raise
    except sqlite3.Error:
        raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _decode(kind: str, payload: str) -> object:
    try:
        value = json.loads(
            payload, object_pairs_hook=_strict_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        record_type, _id_field = _KIND_INFO[kind]
        return record_from_mapping(record_type, value)
    except (KeyError, TypeError, ValueError, UnicodeError, _Failure):
        raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER") from None


def _serialize(record: object) -> tuple[str, str, str, str]:
    try:
        _validate_public_record(record)
        if type(record) not in _TYPE_INFO:
            raise _StoreFailure("FIELD_TYPE_INVALID")
        kind, id_field = _TYPE_INFO[type(record)]
        record_id = getattr(record, id_field)
        raw = _canonical_bytes(record_to_mapping(record))
        if len(raw) > MAX_ALPHA_RECORD_PAYLOAD_BYTES:
            raise _StoreFailure("LIMIT_EXCEEDED")
        return kind, record_id, raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
    except _StoreFailure:
        raise
    except _Failure as failure:
        raise _StoreFailure(_map_alpha_error(failure.code)) from None
    except Exception:
        raise _StoreFailure("INTERNAL_VALIDATION_FAILED") from None


def _entry_hash(sequence: int, kind: str, record_id: str, payload_sha: str, previous: str | None) -> str:
    return _digest("alpha_registry_entry", "alpharegistryentry:sha256:", {
        "sequence_number": sequence, "record_kind": kind, "record_id": record_id,
        "payload_sha256": payload_sha, "previous_entry_hash": previous,
    })


def _verify_cross_record_invariants(snapshot: AlphaFactoryRegistrySnapshot) -> None:
    sources: set[str] = set()
    candidates: dict[str, OpportunityCandidate] = {}
    novelty_by_fp: dict[str, str] = {}
    families: dict[str, HypothesisFamily] = {}
    mechanism_by_fp: dict[str, str] = {}
    episodes: dict[str, ResearchEpisode] = {}
    for entry in snapshot.entries:
        record = entry.record
        try:
            _validate_public_record(record)
            if isinstance(record, ResearchSourceReference):
                sources.add(record.source_reference_id)
            elif isinstance(record, OpportunityCandidate):
                claimed = novelty_by_fp.get(record.novelty_fingerprint)
                if claimed is not None and claimed != record.candidate_id:
                    raise _StoreFailure("NOVELTY_DUPLICATE")
                novelty_by_fp[record.novelty_fingerprint] = record.candidate_id
                candidates[record.candidate_id] = record
            elif isinstance(record, HypothesisFamily):
                claimed = mechanism_by_fp.get(record.mechanism_fingerprint)
                if claimed is not None and claimed != record.hypothesis_family_id:
                    raise _StoreFailure("MECHANISM_CONFLICT")
                mechanism_by_fp[record.mechanism_fingerprint] = record.hypothesis_family_id
                predecessor = record.predecessor_family_id
                if predecessor is not None:
                    if predecessor == record.hypothesis_family_id:
                        raise _StoreFailure("LINEAGE_INVALID")
                    if predecessor not in families:
                        raise _StoreFailure("LINEAGE_INVALID")
                families[record.hypothesis_family_id] = record
            elif isinstance(record, ResearchEpisode):
                if record.candidate_id not in candidates:
                    raise _StoreFailure("REFERENCE_INVALID")
                if record.hypothesis_family_id not in families:
                    raise _StoreFailure("REFERENCE_INVALID")
                for source_id in record.source_reference_ids:
                    if source_id not in sources:
                        raise _StoreFailure("REFERENCE_INVALID")
                predecessor = record.predecessor_episode_id
                if predecessor is not None:
                    prior = episodes.get(predecessor)
                    if prior is None:
                        raise _StoreFailure("LINEAGE_INVALID")
                    if prior.candidate_id != record.candidate_id or prior.hypothesis_family_id != record.hypothesis_family_id:
                        raise _StoreFailure("LINEAGE_INVALID")
                reopened = record.reopened_episode_id
                if record.result_state == "REOPEN_TRIGGERED":
                    if reopened is None:
                        raise _StoreFailure("REOPEN_INVALID")
                    target = episodes.get(reopened)
                    if target is None:
                        raise _StoreFailure("REOPEN_INVALID")
                    if target.candidate_id != record.candidate_id or target.hypothesis_family_id != record.hypothesis_family_id:
                        raise _StoreFailure("REOPEN_INVALID")
                    if target.result_state in {"RESEARCH_SUPPORTIVE", "REOPEN_TRIGGERED"}:
                        raise _StoreFailure("REOPEN_INVALID")
                elif reopened is not None:
                    raise _StoreFailure("REOPEN_INVALID")
                episodes[record.research_episode_id] = record
        except _StoreFailure:
            raise
        except _Failure:
            # Reached only for persisted/projected records; any semantic failure here
            # means persisted corruption, surfaced as tamper (never a model code leak).
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER") from None
        except Exception:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER") from None


def _load(connection: sqlite3.Connection) -> AlphaFactoryRegistrySnapshot:
    _verify_schema(connection)
    rows = connection.execute(
        "SELECT sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash FROM alpha_registry_records ORDER BY sequence_number"
    ).fetchall()
    if len(rows) > MAX_ALPHA_REGISTRY_RECORDS:
        raise _StoreFailure("LIMIT_EXCEEDED")
    entries: list[AlphaFactoryRegistryEntry] = []
    total_bytes = 0
    previous = None
    for expected_sequence, row in enumerate(rows):
        sequence, kind, record_id, payload, payload_sha, prior_hash, entry_hash = row
        if sequence != expected_sequence or kind not in _KIND_INFO or prior_hash != previous:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        if not all(isinstance(value, str) for value in (kind, record_id, payload, payload_sha, entry_hash)):
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        raw = payload.encode("utf-8")
        total_bytes += len(raw)
        if len(raw) > MAX_ALPHA_RECORD_PAYLOAD_BYTES or total_bytes > MAX_ALPHA_STORE_PAYLOAD_BYTES:
            raise _StoreFailure("LIMIT_EXCEEDED")
        if hashlib.sha256(raw).hexdigest() != payload_sha or _entry_hash(sequence, kind, record_id, payload_sha, prior_hash) != entry_hash:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        record = _decode(kind, payload)
        if getattr(record, _KIND_INFO[kind][1]) != record_id:
            raise _StoreFailure("REGISTRY_INTEGRITY_TAMPER")
        entries.append(
            AlphaFactoryRegistryEntry(sequence, kind, record_id, payload_sha, prior_hash, entry_hash, record)
        )
        previous = entry_hash
    snapshot = AlphaFactoryRegistrySnapshot(
        _SNAPSHOT_SCHEMA_ID, _SNAPSHOT_SCHEMA_VERSION, tuple(entries),
        len(entries), total_bytes, previous, True, True, True, True,
    )
    _verify_cross_record_invariants(snapshot)
    return snapshot


def _remove_created(path: Path) -> None:
    try:
        if path.exists() and path.is_file() and not path.is_symlink() and path.lstat().st_nlink == 1:
            path.unlink()
    except OSError:
        pass


def initialize_alpha_factory_registry(path: object) -> AlphaFactoryRegistryResult:
    created = False
    target: Path | None = None
    try:
        target = _path(path, must_exist=False)
        existed = target.exists()
        if not existed:
            try:
                descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except OSError:
                raise _StoreFailure("REGISTRY_SCHEMA_CONFLICT") from None
            else:
                os.close(descriptor)
                created = True
        connection = _connect(target, "rwc")
        try:
            _configure(connection, writable=True)
            if existed:
                snapshot = _load(connection)
                return _success("REGISTRY_ALREADY_INITIALIZED", snapshot)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_CREATE_META)
            # DDL is built solely from the closed module-owned RECORD_KIND_TYPES
            # vocabulary; no caller or persisted value is interpolated.
            connection.execute(_CREATE_RECORDS)  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query, python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            connection.execute(_CREATE_NO_UPDATE)
            connection.execute(_CREATE_NO_DELETE)
            connection.execute(
                "INSERT INTO alpha_registry_meta VALUES (1,?,?)",
                (ALPHA_REGISTRY_FORMAT_ID, ALPHA_REGISTRY_SCHEMA_VERSION),
            )
            connection.execute(f"PRAGMA application_id={ALPHA_REGISTRY_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={ALPHA_REGISTRY_SCHEMA_VERSION}")
            connection.execute("COMMIT")
            snapshot = _load(connection)
            return _success("REGISTRY_INITIALIZED", snapshot)
        finally:
            connection.close()
    except _StoreFailure as failure:
        if created and target is not None:
            _remove_created(target)
        return _reject(failure.code)
    except Exception:
        if created and target is not None:
            _remove_created(target)
        return _reject("INTERNAL_VALIDATION_FAILED")


def _predecessor_depth(
    record_id: str, new_ids: frozenset[str], decoded: Mapping[str, object],
    links: tuple[str, ...],
) -> int:
    """Longest same-batch dependency chain length above ``record_id``.

    Follows each link field to a parent that is also new in this batch; a repeated
    node on the active path is a dependency cycle. Cross-batch/existing parents (not
    in ``new_ids``) terminate the walk. Deterministic and bounded by the batch size.
    """

    def longest(node_id: str, on_path: frozenset[str]) -> int:
        if node_id in on_path:
            raise _StoreFailure("LINEAGE_CYCLE")
        record = decoded[node_id]
        best = 0
        for link in links:
            parent_id = getattr(record, link)
            if parent_id in new_ids:
                best = max(best, 1 + longest(parent_id, on_path | {node_id}))
        return best

    return longest(record_id, frozenset())


def _new_item_sort_key(
    item: tuple[str, str, str, str],
    decoded_by_id: Mapping[str, object],
    new_family_ids: frozenset[str],
    new_episode_ids: frozenset[str],
) -> tuple[object, ...]:
    kind, record_id, _payload, payload_sha = item
    if kind == "HYPOTHESIS_FAMILY":
        depth = _predecessor_depth(record_id, new_family_ids, decoded_by_id, ("predecessor_family_id",))
        return (_KIND_RANK[kind], depth, record_id, payload_sha)
    if kind == "RESEARCH_EPISODE":
        depth = _predecessor_depth(
            record_id, new_episode_ids, decoded_by_id,
            ("predecessor_episode_id", "reopened_episode_id"),
        )
        return (_KIND_RANK[kind], depth, record_id, payload_sha)
    return (_KIND_RANK[kind], record_id, payload_sha)


def append_alpha_factory_records(path: object, records: object) -> AlphaFactoryRegistryResult:
    try:
        target = _path(path, must_exist=True)
        if not isinstance(records, (list, tuple)):
            raise _StoreFailure("FIELD_TYPE_INVALID")
        if not records:
            raise _StoreFailure("FIELD_VALUE_INVALID")
        if len(records) > MAX_ALPHA_APPEND_BATCH:
            raise _StoreFailure("LIMIT_EXCEEDED")
        serialized = [_serialize(record) for record in records]
        by_id: dict[str, tuple[str, str, str, str]] = {}
        duplicate_ids: set[str] = set()
        for item in serialized:
            _kind, record_id, _payload, _sha = item
            prior = by_id.get(record_id)
            if prior is not None and prior != item:
                raise _StoreFailure("REGISTRY_IDENTITY_CONFLICT")
            if prior == item:
                duplicate_ids.add(record_id)
            by_id[record_id] = item
        connection = _connect(target, "rwc")
        try:
            _configure(connection, writable=True)
            connection.execute("BEGIN IMMEDIATE")
            current = _load(connection)
            existing = {entry.record_id: entry for entry in current.entries}
            new_items: list[tuple[str, str, str, str]] = []
            idempotent = set(duplicate_ids)
            for record_id, item in by_id.items():
                kind, _record_id, _payload, payload_sha = item
                found = existing.get(record_id)
                if found is not None:
                    if found.record_kind != kind or found.payload_sha256 != payload_sha:
                        raise _StoreFailure("REGISTRY_IDENTITY_CONFLICT")
                    idempotent.add(record_id)
                else:
                    new_items.append(item)
            decoded_by_id = {
                record_id: _decode(item[0], item[2]) for record_id, item in by_id.items()
            }
            new_family_ids = frozenset(
                record_id for kind, record_id, _p, _s in new_items if kind == "HYPOTHESIS_FAMILY"
            )
            new_episode_ids = frozenset(
                record_id for kind, record_id, _p, _s in new_items if kind == "RESEARCH_EPISODE"
            )
            new_items.sort(
                key=lambda item: _new_item_sort_key(
                    item, decoded_by_id, new_family_ids, new_episode_ids
                )
            )
            projected_rows = current.total_rows + len(new_items)
            projected_bytes = current.total_payload_bytes + sum(
                len(item[2].encode("utf-8")) for item in new_items
            )
            if projected_rows > MAX_ALPHA_REGISTRY_RECORDS or projected_bytes > MAX_ALPHA_STORE_PAYLOAD_BYTES:
                raise _StoreFailure("LIMIT_EXCEEDED")
            sequence = current.total_rows
            previous = current.head_entry_hash
            inserted: list[str] = []
            for kind, record_id, payload, payload_sha in new_items:
                entry_hash = _entry_hash(sequence, kind, record_id, payload_sha, previous)
                connection.execute(
                    "INSERT INTO alpha_registry_records(sequence_number,record_kind,record_id,payload_json,payload_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",
                    (sequence, kind, record_id, payload, payload_sha, previous, entry_hash),
                )
                inserted.append(record_id)
                previous = entry_hash
                sequence += 1
            projected = _load(connection)
            connection.execute("COMMIT")
            status = "REGISTRY_APPEND_COMMITTED" if inserted else "REGISTRY_APPEND_IDEMPOTENT"
            return _success(status, projected, tuple(sorted(inserted)), tuple(sorted(idempotent)))
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()
    except _StoreFailure as failure:
        return _reject(failure.code)
    except sqlite3.Error:
        return _reject("REGISTRY_SCHEMA_CONFLICT")
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")


def load_and_verify_alpha_factory_registry(path: object) -> AlphaFactoryRegistryResult:
    try:
        target = _path(path, must_exist=True)
        connection = _connect(target, "ro")
        try:
            _configure(connection, writable=False)
            snapshot = _load(connection)
        finally:
            connection.close()
        return _success("REGISTRY_LOADED_VERIFIED", snapshot)
    except _StoreFailure as failure:
        return _reject(failure.code)
    except Exception:
        return _reject("INTERNAL_VALIDATION_FAILED")
