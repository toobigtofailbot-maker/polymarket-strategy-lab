"""WP169 bounded append-only local SQLite market-truth archive.

Import-safe, standard-library-only (sqlite3), offline, no import-time side
effects. The store owns exact append-only evidence tables plus a derived
checkpoint cache rebuilt from an append-only history hash chain. It never
deletes, truncates, replaces, or migrates an existing file, and paths never
appear in receipts, exceptions, identities, or any diagnostic surface.
"""

from __future__ import annotations

import dataclasses
import functools
import json
import os
import pathlib
import sqlite3
import threading
from collections.abc import Mapping, Sequence

from .market_truth import (
    AcquisitionLimits,
    AcquisitionReceipt,
    Checkpoint,
    MarketTruthError,
    NormalizedObservation,
    RawEnvelope,
    SOURCE_KINDS,
    CHECKPOINT_STATES,
    ERROR_PRECEDENCE,
    GAP_REASONS,
    GAP_STATES,
    OBSERVATION_STATUSES,
    RECEIPT_STATUSES,
    SESSION_STATES,
    STOP_REASONS,
    canonical_json_bytes,
    compute_checkpoint_sha256,
    compute_observation_id,
    compute_occurrence_id,
    compute_raw_id,
    is_rfc3339_micros,
    order_error_codes,
    sha256_hex,
)

_ERROR_CODE_SET = frozenset(ERROR_PRECEDENCE)

APPLICATION_ID = 1_347_242_297
USER_VERSION = 1

# WP175E additive read-only evidence-query bound. A native-continuity request whose
# exact (asset, receive-time interval) selects more than this many durable rows is
# rejected closed (INPUT_INVALID): the caller must narrow the interval. This is a
# query bound only; it never changes the schema, append semantics, or stored bytes.
MAX_EVIDENCE_READ_ROWS = 200_000


@dataclasses.dataclass(frozen=True)
class SessionEventRecord:
    """Immutable durable WP169 session-transition evidence row (WP175E read surface)."""

    sequence: int
    session_id: str
    state: str
    received_at: str


@dataclasses.dataclass(frozen=True)
class GapEventRecord:
    """Immutable durable WP169 gap-transition evidence row (WP175E read surface)."""

    sequence: int
    asset_id: str
    state: str
    reason: str
    received_at: str


@dataclasses.dataclass(frozen=True)
class AcceptedObservationRecord:
    """Verified accepted observation plus its durable append/session provenance."""

    archive_sequence: int
    session_id: str
    observation: NormalizedObservation

_TABLES = {
    "raw_occurrences": (
        "CREATE TABLE raw_occurrences ("
        "archive_sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "occurrence_id TEXT NOT NULL UNIQUE,"
        "raw_id TEXT NOT NULL,"
        "source_kind TEXT NOT NULL,"
        "source_id TEXT NOT NULL,"
        "source_cursor TEXT NOT NULL,"
        "received_at TEXT NOT NULL,"
        "media_type TEXT NOT NULL,"
        "byte_length INTEGER NOT NULL,"
        "raw_sha256 TEXT NOT NULL,"
        "raw_bytes BLOB NOT NULL)"
    ),
    "normalized_occurrences": (
        "CREATE TABLE normalized_occurrences ("
        "archive_sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "observation_id TEXT NOT NULL,"
        "occurrence_id TEXT NOT NULL,"
        "raw_id TEXT NOT NULL,"
        "source_kind TEXT NOT NULL,"
        "event_kind TEXT NOT NULL,"
        "event_id TEXT,"
        "market_id TEXT,"
        "asset_id TEXT,"
        "event_time TEXT,"
        "received_at TEXT NOT NULL,"
        "canonical_payload_json TEXT NOT NULL,"
        "canonical_payload_sha256 TEXT NOT NULL,"
        "status TEXT NOT NULL,"
        "error_codes_json TEXT NOT NULL,"
        "book_ready INTEGER NOT NULL,"
        "provenance_json TEXT NOT NULL,"
        "UNIQUE(observation_id, occurrence_id))"
    ),
    "session_events": (
        "CREATE TABLE session_events ("
        "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id TEXT NOT NULL,"
        "state TEXT NOT NULL,"
        "received_at TEXT NOT NULL)"
    ),
    "gap_events": (
        "CREATE TABLE gap_events ("
        "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "asset_id TEXT NOT NULL,"
        "state TEXT NOT NULL,"
        "reason TEXT NOT NULL,"
        "received_at TEXT NOT NULL)"
    ),
    "checkpoint_history": (
        "CREATE TABLE checkpoint_history ("
        "history_sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "checkpoint_key TEXT NOT NULL,"
        "sequence INTEGER NOT NULL,"
        "state TEXT NOT NULL,"
        "value_json TEXT NOT NULL,"
        "value_sha256 TEXT NOT NULL,"
        "previous_sha256 TEXT)"
    ),
    "chain_finality_events": (
        "CREATE TABLE chain_finality_events ("
        "sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
        "source_log_id TEXT NOT NULL,"
        "block_hash TEXT NOT NULL,"
        "finality_state TEXT NOT NULL,"
        "received_at TEXT NOT NULL)"
    ),
    "checkpoint_current": (
        "CREATE TABLE checkpoint_current ("
        "checkpoint_key TEXT PRIMARY KEY,"
        "history_sequence INTEGER NOT NULL,"
        "sequence INTEGER NOT NULL,"
        "state TEXT NOT NULL,"
        "value_json TEXT NOT NULL,"
        "value_sha256 TEXT NOT NULL,"
        "previous_sha256 TEXT)"
    ),
}

_INDEXES = {
    "idx_normalized_status": (
        "CREATE INDEX idx_normalized_status ON normalized_occurrences(status)"
    ),
    "idx_checkpoint_history_key": (
        "CREATE INDEX idx_checkpoint_history_key "
        "ON checkpoint_history(checkpoint_key, history_sequence)"
    ),
    "idx_chain_finality_log": (
        "CREATE INDEX idx_chain_finality_log "
        "ON chain_finality_events(source_log_id)"
    ),
}


import re as _re

# Frozen source_cursor grammars. The occurrence sequence is the trailing frame/attempt
# integer, which must equal the occurrence_sequence used to build the occurrence_id.
_WS_CURSOR_RE = _re.compile(r"^ws:[^:]+:frame:(\d+)$")
_HTTP_CURSOR_RE = _re.compile(r"^http:[^:]+:offset:\d+:attempt:(\d+)$")
_RPC_CURSOR_RE = _re.compile(r"^rpc:[^:]+:blocks:\d+-\d+:attempt:(\d+)$")

# Frozen source-domain grammar (raw trust boundary): the only accepted source_id namespaces,
# endpoint tokens, and RPC methods; lowercase UUID4 session ids; canonical (nonpadded)
# cursor integers.
_WS_SOURCE_ID = "polymarket:market-ws"
_HTTP_SOURCE_PREFIX = {
    "DATA": "polymarket:data-api:",
    "GAMMA": "polymarket:gamma:",
    "CLOB": "polymarket:clob:",
}
_POLYGON_SOURCE_PREFIX = "polygon:137:drpc:"
_ENDPOINT_TOKENS = frozenset({
    "trades", "activity", "positions", "holders", "markets",
    "market-by-id", "book", "fee-rate", "clob-market-info",
})
_RPC_METHODS = frozenset({"eth_chainId", "eth_blockNumber", "eth_getLogs", "eth_getBlockByNumber"})
_UUID4_STR = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_CANON_INT = r"(?:0|[1-9][0-9]*)"
_WS_CURSOR_STRICT = _re.compile(rf"^ws:({_UUID4_STR}):frame:{_CANON_INT}$")
_HTTP_CURSOR_STRICT = _re.compile(rf"^http:([^:]+):offset:{_CANON_INT}:attempt:{_CANON_INT}$")
_RPC_CURSOR_STRICT = _re.compile(
    rf"^rpc:([^:]+):blocks:{_CANON_INT}-{_CANON_INT}:attempt:{_CANON_INT}$"
)
# Provenance key schemas per source kind (byte-exact canonical provenance is also enforced).
_PROVENANCE_KEYS = {
    "WS": {"normalizer_version", "frame_event_type", "child_index", "event_hash"},
    "DATA": {"normalizer_version", "endpoint", "child_index"},
    "GAMMA": {"normalizer_version", "endpoint", "child_index"},
    "CLOB": {"normalizer_version", "endpoint", "child_index"},
    "POLYGON": {"normalizer_version", "chain_id", "exchange_address", "child_index"},
}


def _validate_source_domain(raw: RawEnvelope) -> None:
    """Enforce the frozen source_id/source_cursor coherence for a raw envelope, or raise
    STORE_CONFLICT. A self-consistent forged source domain must not be accepted."""
    sk, sid, cur = raw.source_kind, raw.source_id, raw.source_cursor
    if sk == "WS":
        match = _WS_CURSOR_STRICT.fullmatch(cur)
        if sid != _WS_SOURCE_ID or match is None:
            raise MarketTruthError("STORE_CONFLICT")
    elif sk in _HTTP_SOURCE_PREFIX:
        prefix = _HTTP_SOURCE_PREFIX[sk]
        match = _HTTP_CURSOR_STRICT.fullmatch(cur)
        if not sid.startswith(prefix) or match is None:
            raise MarketTruthError("STORE_CONFLICT")
        endpoint = sid[len(prefix):]
        if endpoint not in _ENDPOINT_TOKENS or match.group(1) != endpoint:
            raise MarketTruthError("STORE_CONFLICT")
    elif sk == "POLYGON":
        match = _RPC_CURSOR_STRICT.fullmatch(cur)
        if not sid.startswith(_POLYGON_SOURCE_PREFIX) or match is None:
            raise MarketTruthError("STORE_CONFLICT")
        method = sid[len(_POLYGON_SOURCE_PREFIX):]
        if method not in _RPC_METHODS or match.group(1) != method:
            raise MarketTruthError("STORE_CONFLICT")
    else:
        raise MarketTruthError("STORE_CONFLICT")


_SHA256_HEX = r"[0-9a-f]{64}"
_RAW_ID_RE = _re.compile(rf"^markettruth:raw:sha256:{_SHA256_HEX}$")
_OCCURRENCE_ID_RE = _re.compile(rf"^markettruth:occurrence:sha256:{_SHA256_HEX}$")
_OBSERVATION_ID_RE = _re.compile(rf"^markettruth:observation:sha256:{_SHA256_HEX}$")
_HASH_0X64_RE = _re.compile(rf"^0x{_SHA256_HEX}$")


def _is_nonneg_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_checkpoint_value(checkpoint_key: str, value: Mapping[str, object], code: str) -> None:
    """Validate a checkpoint value against its exact frozen schema (chosen by key), raising
    ``code`` (INPUT_INVALID on write, STORE_CONFLICT on persisted-history load) on mismatch.

    Schemas: http={endpoint,next_offset,last_raw_id}; ws={asset_ids,last_occurrence_id,
    book_states}; chain={chain_id,last_verified_block,last_verified_block_hash}.
    """
    if not isinstance(value, dict):
        raise MarketTruthError(code)
    keys = set(value)
    if checkpoint_key.startswith("http:"):
        if keys != {"endpoint", "next_offset", "last_raw_id"}:
            raise MarketTruthError(code)
        last_raw_id = value["last_raw_id"]
        if (
            value["endpoint"] not in _ENDPOINT_TOKENS
            or not _is_nonneg_int(value["next_offset"])
            or not (last_raw_id is None or (isinstance(last_raw_id, str) and _RAW_ID_RE.fullmatch(last_raw_id)))
        ):
            raise MarketTruthError(code)
    elif checkpoint_key.startswith("ws:"):
        if keys != {"asset_ids", "last_occurrence_id", "book_states"}:
            raise MarketTruthError(code)
        asset_ids = value["asset_ids"]
        last_occurrence_id = value["last_occurrence_id"]
        book_states = value["book_states"]
        if (
            not (isinstance(asset_ids, list) and all(isinstance(a, str) for a in asset_ids))
            or not (last_occurrence_id is None or (isinstance(last_occurrence_id, str) and _OCCURRENCE_ID_RE.fullmatch(last_occurrence_id)))
            or not (isinstance(book_states, dict) and set(book_states) == {"assets"} and isinstance(book_states["assets"], dict))
        ):
            raise MarketTruthError(code)
    elif checkpoint_key == "chain:137:order-filled-v2":
        if keys != {"chain_id", "last_verified_block", "last_verified_block_hash"}:
            raise MarketTruthError(code)
        block = value["last_verified_block"]
        block_hash = value["last_verified_block_hash"]
        both_null = block is None and block_hash is None
        canonical_pair = _is_nonneg_int(block) and isinstance(block_hash, str) and _HASH_0X64_RE.fullmatch(block_hash) is not None
        if value["chain_id"] != 137 or not (both_null or canonical_pair):
            raise MarketTruthError(code)
    else:
        raise MarketTruthError(code)


def _normalize_ddl(sql: object) -> str | None:
    """Whitespace-normalize a CREATE statement for exact-schema comparison, or None."""
    if not isinstance(sql, str):
        return None
    return " ".join(sql.split())


def _cursor_occurrence_sequence(cursor: str) -> int | None:
    for pattern in (_WS_CURSOR_RE, _HTTP_CURSOR_RE, _RPC_CURSOR_RE):
        match = pattern.fullmatch(cursor)
        if match is not None:
            return int(match.group(1))
    return None


def _validate_output_path(path: str | pathlib.Path) -> pathlib.Path:
    if isinstance(path, str) and path == ":memory:":
        raise MarketTruthError("STORE_CONFLICT")
    if not isinstance(path, (str, pathlib.Path)):
        raise MarketTruthError("STORE_CONFLICT")
    resolved = pathlib.Path(path)
    if resolved.suffix != ".sqlite3":
        raise MarketTruthError("STORE_CONFLICT")
    parent = resolved.parent
    if not parent.exists() or not parent.is_dir():
        raise MarketTruthError("STORE_CONFLICT")
    # No symlink at the file or any existing parent.
    probe = resolved
    checked: set[str] = set()
    while True:
        text = str(probe)
        if text in checked:
            break
        checked.add(text)
        if probe.exists() or probe.is_symlink():
            if probe.is_symlink():
                raise MarketTruthError("STORE_CONFLICT")
        if probe == probe.parent:
            break
        probe = probe.parent
    if resolved.exists():
        if resolved.is_dir() or not resolved.is_file():
            raise MarketTruthError("STORE_CONFLICT")
        try:
            stat = resolved.stat()
        except OSError:
            raise MarketTruthError("STORE_CONFLICT")
        if getattr(stat, "st_nlink", 1) > 1:
            raise MarketTruthError("STORE_CONFLICT")
    return resolved


class MarketTruthStore:
    """Bounded append-only local SQLite market-truth archive."""

    def __init__(
        self, path: str | pathlib.Path, limits: AcquisitionLimits | None = None
    ) -> None:
        self._path = _validate_output_path(path)
        self._limits = limits or AcquisitionLimits()
        self._connection: sqlite3.Connection | None = None
        # The manual foreground runtime shares one store across the event-loop thread
        # (WebSocket) and to_thread workers (HTTP/RPC cadences); serialize all access.
        self._lock = threading.RLock()

    # -- lifecycle -------------------------------------------------------
    def initialize(self) -> None:
        if self._connection is not None:
            return
        existed = self._path.exists()
        if not existed:
            # Create the missing file exclusively (O_EXCL): this fails closed on a
            # concurrent create and refuses to follow a symlink placed at the path after
            # construction-time validation. A zero-byte file is a fresh empty database.
            try:
                fd = os.open(
                    str(self._path), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600
                )
                os.close(fd)
            except FileExistsError:
                existed = True  # lost the create race; verify the existing file instead
            except OSError:
                raise MarketTruthError("STORE_CONFLICT")
        connection = sqlite3.connect(
            str(self._path), isolation_level=None, check_same_thread=False
        )
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            if existed:
                self._verify_existing(connection)
            else:
                self._create_schema(connection)
        except MarketTruthError:
            connection.close()
            raise
        self._connection = connection

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN")
        try:
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={USER_VERSION}")
            for statement in _TABLES.values():
                connection.execute(statement)
            for statement in _INDEXES.values():
                connection.execute(statement)
            connection.execute("COMMIT")
        except sqlite3.DatabaseError:
            connection.execute("ROLLBACK")
            raise MarketTruthError("STORE_CONFLICT")

    def _verify_existing(self, connection: sqlite3.Connection) -> None:
        try:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.DatabaseError:
            raise MarketTruthError("STORE_CONFLICT")
        if application_id != APPLICATION_ID or user_version != USER_VERSION:
            raise MarketTruthError("STORE_CONFLICT")
        if integrity != "ok":
            raise MarketTruthError("STORE_CONFLICT")
        # Every exact table/index must exist with the exact certified DDL. A name-only
        # check would accept a file with a table of the right name but wrong columns; the
        # stored CREATE text is compared (whitespace-normalized) against the certified DDL.
        table_sql = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for name, ddl in _TABLES.items():
            if _normalize_ddl(table_sql.get(name)) != _normalize_ddl(ddl):
                raise MarketTruthError("STORE_CONFLICT")
        index_sql = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        for name, ddl in _INDEXES.items():
            if _normalize_ddl(index_sql.get(name)) != _normalize_ddl(ddl):
                raise MarketTruthError("STORE_CONFLICT")

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @classmethod
    def _read_raw_occurrences(
        cls, path: str | pathlib.Path, occurrence_ids: Sequence[str],
        limits: AcquisitionLimits | None = None,
    ) -> tuple[RawEnvelope, ...]:
        """Cold, read-only, bounded lookup with the frozen schema/domain/ID checks."""
        active = limits or AcquisitionLimits()
        if (not isinstance(occurrence_ids, Sequence)
                or not 1 <= len(occurrence_ids) <= 2 * (active.max_retries + 1)
                or any(not isinstance(key, str) or len(key) > 128 for key in occurrence_ids)
                or len(set(occurrence_ids)) != len(occurrence_ids)):
            raise MarketTruthError("STORE_CONFLICT")
        store = cls(path, active)
        if not store._path.is_file():
            raise MarketTruthError("STORE_CONFLICT")
        connection = None
        try:
            connection = sqlite3.connect(store._path.resolve().as_uri() + "?mode=ro", uri=True)
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            store._verify_existing(connection)
            if (store._row_count(connection) > active.max_store_rows
                    or store._store_bytes(connection) > active.max_store_bytes):
                raise MarketTruthError("STORE_CONFLICT")
            result = []
            fields = tuple(field.name for field in dataclasses.fields(RawEnvelope))
            for key in occurrence_ids:
                row = connection.execute(
                    "SELECT " + ",".join(fields) + " FROM raw_occurrences "
                    "WHERE occurrence_id=? AND typeof(raw_bytes)='blob' "
                    "AND length(raw_bytes)<=?", (key, active.max_response_bytes),
                ).fetchone()
                if row is None:
                    raise MarketTruthError("STORE_CONFLICT")
                raw = RawEnvelope(**dict(zip(fields, row)))
                store._validate_raw(raw)
                result.append(raw)
            return tuple(result)
        except (sqlite3.Error, OSError, TypeError, ValueError, OverflowError):
            raise MarketTruthError("STORE_CONFLICT") from None
        finally:
            if connection is not None:
                connection.close()

    def __enter__(self) -> "MarketTruthStore":
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _require(self) -> sqlite3.Connection:
        if self._connection is None:
            raise MarketTruthError("STORE_NOT_INITIALIZED")
        return self._connection

    # -- accounting ------------------------------------------------------
    def _row_count(self, connection: sqlite3.Connection) -> int:
        raw = connection.execute("SELECT COUNT(*) FROM raw_occurrences").fetchone()[0]
        norm = connection.execute(
            "SELECT COUNT(*) FROM normalized_occurrences"
        ).fetchone()[0]
        return int(raw) + int(norm)

    def _store_bytes(self, connection: sqlite3.Connection) -> int:
        raw = connection.execute(
            "SELECT COALESCE(SUM(byte_length),0) FROM raw_occurrences"
        ).fetchone()[0]
        # Measure UTF-8 byte length (CAST ... AS BLOB) to match append's projection, which
        # uses len(canonical_payload_json.encode("utf-8")); LENGTH() alone counts code
        # points and would diverge for non-ASCII payloads.
        norm = connection.execute(
            "SELECT COALESCE(SUM(LENGTH(CAST(canonical_payload_json AS BLOB))),0) "
            "FROM normalized_occurrences"
        ).fetchone()[0]
        return int(raw) + int(norm)

    def _checkpoint_sequence(self, connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(history_sequence),0) FROM checkpoint_history"
        ).fetchone()
        return int(row[0])

    def _counts(self, connection: sqlite3.Connection) -> tuple[int, int, int, int]:
        raw = connection.execute("SELECT COUNT(*) FROM raw_occurrences").fetchone()[0]
        accepted = connection.execute(
            "SELECT COUNT(*) FROM normalized_occurrences WHERE status='ACCEPTED'"
        ).fetchone()[0]
        not_accepted = connection.execute(
            "SELECT COUNT(*) FROM normalized_occurrences WHERE status!='ACCEPTED'"
        ).fetchone()[0]
        opened = connection.execute(
            "SELECT COUNT(*) FROM gap_events WHERE state='OPEN'"
        ).fetchone()[0]
        healed = connection.execute(
            "SELECT COUNT(*) FROM gap_events WHERE state='HEALED'"
        ).fetchone()[0]
        # Currently-open gaps = OPEN events not yet balanced by a HEALED transition.
        open_gaps = max(0, int(opened) - int(healed))
        return int(raw), int(accepted), int(not_accepted), int(open_gaps)

    def receipt(
        self,
        status: str = "OK",
        error_codes: Sequence[str] = (),
        stop_reason: str = "NONE",
    ) -> AcquisitionReceipt:
        # Closed public vocabularies: an out-of-vocabulary status/stop_reason/error code is
        # INPUT_INVALID, never emitted on a receipt.
        if status not in RECEIPT_STATUSES or stop_reason not in STOP_REASONS:
            raise MarketTruthError("INPUT_INVALID")
        if any(code not in _ERROR_CODE_SET for code in error_codes):
            raise MarketTruthError("INPUT_INVALID")
        connection = self._require()
        raw, accepted, not_accepted, open_gaps = self._counts(connection)
        return AcquisitionReceipt(
            status=status,
            error_codes=tuple(error_codes),
            raw_count=raw,
            normalized_count=accepted,
            quarantined_count=not_accepted,
            gap_count=open_gaps,
            checkpoint_sequence=self._checkpoint_sequence(connection),
            store_bytes=self._store_bytes(connection),
            stop_reason=stop_reason,
        )

    # -- validation ------------------------------------------------------
    def _validate_raw(self, raw: RawEnvelope) -> None:
        if raw.source_kind not in SOURCE_KINDS:
            raise MarketTruthError("STORE_CONFLICT")
        # Source-domain trust boundary: exact media type, canonical receive time, active byte
        # bound, and source_id/source_cursor coherence -- a self-consistent forged source
        # domain (correct hashes/ids but wrong namespace/cursor) must still fail closed.
        if raw.media_type != "application/json":
            raise MarketTruthError("STORE_CONFLICT")
        if not is_rfc3339_micros(raw.received_at):
            raise MarketTruthError("STORE_CONFLICT")
        _validate_source_domain(raw)
        if not isinstance(raw.raw_bytes, (bytes, bytearray)):
            raise MarketTruthError("STORE_CONFLICT")
        payload = bytes(raw.raw_bytes)
        if len(payload) != raw.byte_length:
            raise MarketTruthError("STORE_CONFLICT")
        if raw.byte_length > self._limits.max_response_bytes:
            raise MarketTruthError("STORE_CONFLICT")
        if sha256_hex(payload) != raw.raw_sha256:
            raise MarketTruthError("STORE_CONFLICT")
        expected_raw_id = compute_raw_id(
            source_kind=raw.source_kind,
            source_id=raw.source_id,
            media_type=raw.media_type,
            raw_sha256=raw.raw_sha256,
            byte_length=raw.byte_length,
        )
        if expected_raw_id != raw.raw_id:
            raise MarketTruthError("STORE_CONFLICT")
        # Revalidate occurrence_id exactly. The occurrence sequence is not stored on the
        # envelope, so derive it from the frozen source_cursor grammar and recompute.
        sequence = _cursor_occurrence_sequence(raw.source_cursor)
        if sequence is None:
            raise MarketTruthError("STORE_CONFLICT")
        expected_occurrence = compute_occurrence_id(
            raw_id=raw.raw_id,
            received_at=raw.received_at,
            source_id=raw.source_id,
            source_cursor=raw.source_cursor,
            occurrence_sequence=sequence,
        )
        if expected_occurrence != raw.occurrence_id:
            raise MarketTruthError("STORE_CONFLICT")

    def _validate_child(self, raw: RawEnvelope, obs: NormalizedObservation) -> None:
        # Linkage.
        if obs.occurrence_id != raw.occurrence_id or obs.raw_id != raw.raw_id:
            raise MarketTruthError("STORE_CONFLICT")
        if obs.received_at != raw.received_at:
            raise MarketTruthError("STORE_CONFLICT")
        if obs.source_kind != raw.source_kind:
            raise MarketTruthError("STORE_CONFLICT")
        if obs.status not in OBSERVATION_STATUSES:
            raise MarketTruthError("STORE_CONFLICT")
        # Payload: byte-for-byte canonical JSON, matching digest, bounded size.
        payload_sha = sha256_hex(obs.canonical_payload_json.encode("utf-8"))
        if payload_sha != obs.canonical_payload_sha256:
            raise MarketTruthError("STORE_CONFLICT")
        try:
            payload_obj = json.loads(obs.canonical_payload_json)
            provenance_obj = json.loads(obs.provenance_json)
        except ValueError:
            raise MarketTruthError("STORE_CONFLICT")
        try:
            canonical_payload = canonical_json_bytes(
                payload_obj, max_bytes=self._limits.max_record_bytes
            ).decode("utf-8")
            canonical_provenance = canonical_json_bytes(provenance_obj).decode("utf-8")
        except MarketTruthError:
            raise MarketTruthError("STORE_CONFLICT")
        if canonical_payload != obs.canonical_payload_json:
            raise MarketTruthError("STORE_CONFLICT")
        # Provenance: byte-for-byte canonical, exact key schema per source kind, and (HTTP)
        # endpoint coherence with the raw source_id.
        if canonical_provenance != obs.provenance_json:
            raise MarketTruthError("STORE_CONFLICT")
        if not isinstance(provenance_obj, dict) or set(provenance_obj) != _PROVENANCE_KEYS.get(
            obs.source_kind, frozenset()
        ):
            raise MarketTruthError("STORE_CONFLICT")
        if obs.source_kind in _HTTP_SOURCE_PREFIX:
            endpoint = raw.source_id[len(_HTTP_SOURCE_PREFIX[obs.source_kind]):]
            if provenance_obj.get("endpoint") != endpoint:
                raise MarketTruthError("STORE_CONFLICT")
        # Error/status/book_ready consistency: closed, ordered, deduped error codes; an
        # ACCEPTED observation carries no errors; book_ready implies ACCEPTED.
        if any(code not in _ERROR_CODE_SET for code in obs.error_codes):
            raise MarketTruthError("STORE_CONFLICT")
        if order_error_codes(obs.error_codes) != tuple(obs.error_codes):
            raise MarketTruthError("STORE_CONFLICT")
        if obs.status == "ACCEPTED" and obs.error_codes:
            raise MarketTruthError("STORE_CONFLICT")
        if not isinstance(obs.book_ready, bool):
            raise MarketTruthError("STORE_CONFLICT")
        if obs.book_ready and obs.status != "ACCEPTED":
            raise MarketTruthError("STORE_CONFLICT")
        # Non-null event_time must be canonical RFC3339 micros.
        if obs.event_time is not None and not is_rfc3339_micros(obs.event_time):
            raise MarketTruthError("STORE_CONFLICT")
        source_content_id = obs.raw_id
        # POLYGON identity: an ACCEPTED order_filled binds to its stable source_log_id, but a
        # QUARANTINED malformed log keeps raw_id as its source_content_id (matching the
        # decoder). Overriding for a quarantined log would make the recomputed observation_id
        # mismatch and wrongly reject a valid quarantined child (dropping raw evidence).
        if obs.source_kind == "POLYGON" and obs.status == "ACCEPTED":
            payload = json.loads(obs.canonical_payload_json)
            log_id = payload.get("source_log_id")
            if isinstance(log_id, str):
                source_content_id = log_id
        expected = compute_observation_id(
            source_content_id=source_content_id,
            source_kind=obs.source_kind,
            event_kind=obs.event_kind,
            event_id=obs.event_id,
            market_id=obs.market_id,
            asset_id=obs.asset_id,
            event_time=obs.event_time,
            canonical_payload_sha256=obs.canonical_payload_sha256,
            status=obs.status,
            error_codes=obs.error_codes,
            book_ready=obs.book_ready,
            provenance_json=obs.provenance_json,
        )
        if expected != obs.observation_id:
            raise MarketTruthError("STORE_CONFLICT")

    # -- append ----------------------------------------------------------
    def append(
        self,
        raw: RawEnvelope,
        observations: Sequence[NormalizedObservation] = (),
    ) -> AcquisitionReceipt:
        connection = self._require()
        try:
            self._validate_raw(raw)
        except MarketTruthError as error:
            return self.receipt("FAILED", error.error_codes, "NONE")

        # Raw occurrence committed alone first.
        existing = connection.execute(
            "SELECT raw_id, raw_sha256 FROM raw_occurrences WHERE occurrence_id=?",
            (raw.occurrence_id,),
        ).fetchone()

        # Store-limit accounting counts ONLY rows/bytes that will actually be newly
        # stored: an idempotent re-append of an already-committed raw occurrence and of
        # already-present normalized children adds nothing, so it must not be rejected at
        # the store limit (nor systematically double-count the raw on the archive-then-
        # normalize two-call pattern used by every HTTP/RPC/discovery page).
        new_rows = 0
        new_bytes = 0
        if existing is None:
            new_rows += 1
            new_bytes += raw.byte_length
        for obs in observations:
            present_row = connection.execute(
                "SELECT 1 FROM normalized_occurrences"
                " WHERE observation_id=? AND occurrence_id=? LIMIT 1",
                (obs.observation_id, obs.occurrence_id),
            ).fetchone()
            if present_row is None:
                new_rows += 1
                new_bytes += len(obs.canonical_payload_json.encode("utf-8"))
        projected_rows = self._row_count(connection) + new_rows
        projected_bytes = self._store_bytes(connection) + new_bytes
        # Frozen terminal mapping: a store row/byte bound is FAILED/STORE_LIMIT_EXCEEDED with
        # stop_reason STORE_LIMIT (globally, not just on the WebSocket surface), so callers
        # that propagate this receipt report the exact terminal.
        if projected_rows > self._limits.max_store_rows:
            return self.receipt("FAILED", ("STORE_LIMIT_EXCEEDED",), "STORE_LIMIT")
        if projected_bytes > self._limits.max_store_bytes:
            return self.receipt("FAILED", ("STORE_LIMIT_EXCEEDED",), "STORE_LIMIT")

        if existing is None:
            connection.execute("BEGIN")
            try:
                connection.execute(
                    "INSERT INTO raw_occurrences"
                    "(occurrence_id, raw_id, source_kind, source_id, source_cursor,"
                    " received_at, media_type, byte_length, raw_sha256, raw_bytes)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        raw.occurrence_id,
                        raw.raw_id,
                        raw.source_kind,
                        raw.source_id,
                        raw.source_cursor,
                        raw.received_at,
                        raw.media_type,
                        raw.byte_length,
                        raw.raw_sha256,
                        sqlite3.Binary(raw.raw_bytes),
                    ),
                )
                connection.execute("COMMIT")
            except sqlite3.DatabaseError:
                connection.execute("ROLLBACK")
                return self.receipt("FAILED", ("STORE_CONFLICT",), "NONE")
        elif existing[0] != raw.raw_id or existing[1] != raw.raw_sha256:
            return self.receipt("FAILED", ("STORE_CONFLICT",), "NONE")

        if not observations:
            return self.receipt("OK", (), "NONE")

        # Children validated then committed all-or-nothing.
        try:
            for obs in observations:
                self._validate_child(raw, obs)
        except MarketTruthError as error:
            return self.receipt("FAILED", error.error_codes, "NONE")

        connection.execute("BEGIN")
        try:
            for obs in observations:
                present = connection.execute(
                    "SELECT canonical_payload_sha256, status FROM normalized_occurrences"
                    " WHERE observation_id=? AND occurrence_id=?",
                    (obs.observation_id, obs.occurrence_id),
                ).fetchone()
                if present is not None:
                    if present[0] != obs.canonical_payload_sha256 or present[1] != obs.status:
                        raise sqlite3.IntegrityError("child conflict")
                    continue
                connection.execute(
                    "INSERT INTO normalized_occurrences"
                    "(observation_id, occurrence_id, raw_id, source_kind, event_kind,"
                    " event_id, market_id, asset_id, event_time, received_at,"
                    " canonical_payload_json, canonical_payload_sha256, status,"
                    " error_codes_json, book_ready, provenance_json)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        obs.observation_id,
                        obs.occurrence_id,
                        obs.raw_id,
                        obs.source_kind,
                        obs.event_kind,
                        obs.event_id,
                        obs.market_id,
                        obs.asset_id,
                        obs.event_time,
                        obs.received_at,
                        obs.canonical_payload_json,
                        obs.canonical_payload_sha256,
                        obs.status,
                        json.dumps(list(obs.error_codes)),
                        1 if obs.book_ready else 0,
                        obs.provenance_json,
                    ),
                )
            connection.execute("COMMIT")
        except sqlite3.DatabaseError:
            connection.execute("ROLLBACK")
            return self.receipt("FAILED", ("STORE_CONFLICT",), "NONE")
        return self.receipt("OK", (), "NONE")

    # -- session / gap ---------------------------------------------------
    def mark_session(self, session_id: str, state: str, received_at: str) -> None:
        connection = self._require()
        if state not in SESSION_STATES:
            raise MarketTruthError("INPUT_INVALID")
        connection.execute(
            "INSERT INTO session_events(session_id, state, received_at) VALUES(?,?,?)",
            (session_id, state, received_at),
        )

    def mark_gap(self, asset_id: str, state: str, reason: str, received_at: str) -> None:
        connection = self._require()
        if state not in GAP_STATES or reason not in GAP_REASONS:
            raise MarketTruthError("INPUT_INVALID")
        connection.execute(
            "INSERT INTO gap_events(asset_id, state, reason, received_at) VALUES(?,?,?,?)",
            (asset_id, state, reason, received_at),
        )

    def _checkpoint_history_values(self, checkpoint_key: str) -> tuple[dict[str, object], ...]:
        """Parsed value dicts for a checkpoint key in append-only history order (internal;
        used for deep-reorg rollback over prior verified points)."""
        connection = self._require()
        rows = connection.execute(
            "SELECT value_json FROM checkpoint_history WHERE checkpoint_key=?"
            " ORDER BY history_sequence ASC",
            (checkpoint_key,),
        ).fetchall()
        out: list[dict[str, object]] = []
        for (value_json,) in rows:
            try:
                parsed = json.loads(value_json)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
        return tuple(out)

    # -- checkpoints -----------------------------------------------------
    def write_checkpoint(
        self, checkpoint_key: str, value: Mapping[str, object], state: str
    ) -> Checkpoint:
        connection = self._require()
        if state not in CHECKPOINT_STATES:
            raise MarketTruthError("INPUT_INVALID")
        # Exact frozen value schema per checkpoint kind; an out-of-schema caller write is
        # INPUT_INVALID before anything is persisted.
        _validate_checkpoint_value(checkpoint_key, value, "INPUT_INVALID")
        value_json = canonical_json_bytes(value).decode("utf-8")
        prior = connection.execute(
            "SELECT sequence, value_sha256 FROM checkpoint_history"
            " WHERE checkpoint_key=? ORDER BY history_sequence DESC LIMIT 1",
            (checkpoint_key,),
        ).fetchone()
        if prior is None:
            sequence = 1
            previous_sha256: str | None = None
        else:
            sequence = int(prior[0]) + 1
            previous_sha256 = prior[1]
        value_sha256 = compute_checkpoint_sha256(
            checkpoint_key=checkpoint_key,
            sequence=sequence,
            state=state,
            value_json=value_json,
            previous_sha256=previous_sha256,
        )
        connection.execute("BEGIN")
        try:
            cursor = connection.execute(
                "INSERT INTO checkpoint_history"
                "(checkpoint_key, sequence, state, value_json, value_sha256, previous_sha256)"
                " VALUES(?,?,?,?,?,?)",
                (checkpoint_key, sequence, state, value_json, value_sha256, previous_sha256),
            )
            history_sequence = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO checkpoint_current"
                "(checkpoint_key, history_sequence, sequence, state, value_json,"
                " value_sha256, previous_sha256) VALUES(?,?,?,?,?,?,?)"
                " ON CONFLICT(checkpoint_key) DO UPDATE SET"
                " history_sequence=excluded.history_sequence,"
                " sequence=excluded.sequence, state=excluded.state,"
                " value_json=excluded.value_json, value_sha256=excluded.value_sha256,"
                " previous_sha256=excluded.previous_sha256",
                (
                    checkpoint_key,
                    history_sequence,
                    sequence,
                    state,
                    value_json,
                    value_sha256,
                    previous_sha256,
                ),
            )
            connection.execute("COMMIT")
        except sqlite3.DatabaseError:
            connection.execute("ROLLBACK")
            raise MarketTruthError("STORE_CONFLICT")
        return Checkpoint(
            sequence=sequence,
            history_sequence=history_sequence,
            checkpoint_key=checkpoint_key,
            value_json=value_json,
            value_sha256=value_sha256,
            previous_sha256=previous_sha256,
            state=state,
        )

    def load_checkpoint(self, checkpoint_key: str) -> Checkpoint | None:
        connection = self._require()
        rows = connection.execute(
            "SELECT history_sequence, sequence, state, value_json, value_sha256,"
            " previous_sha256 FROM checkpoint_history WHERE checkpoint_key=?"
            " ORDER BY history_sequence ASC",
            (checkpoint_key,),
        ).fetchall()
        if not rows:
            return None
        previous: str | None = None
        latest: Checkpoint | None = None
        for history_sequence, sequence, state, value_json, value_sha256, prev in rows:
            expected = compute_checkpoint_sha256(
                checkpoint_key=checkpoint_key,
                sequence=int(sequence),
                state=state,
                value_json=value_json,
                previous_sha256=previous,
            )
            if prev != previous or expected != value_sha256:
                raise MarketTruthError("STORE_CONFLICT")
            # Persisted history must also match the exact frozen value schema for its kind;
            # a tampered/foreign value fails closed with STORE_CONFLICT.
            if state not in CHECKPOINT_STATES:
                raise MarketTruthError("STORE_CONFLICT")
            try:
                loaded_value = json.loads(value_json)
            except ValueError:
                raise MarketTruthError("STORE_CONFLICT")
            _validate_checkpoint_value(checkpoint_key, loaded_value, "STORE_CONFLICT")
            previous = value_sha256
            latest = Checkpoint(
                sequence=int(sequence),
                history_sequence=int(history_sequence),
                checkpoint_key=checkpoint_key,
                value_json=value_json,
                value_sha256=value_sha256,
                previous_sha256=prev,
                state=state,
            )
        return latest

    def _append_finality(
        self, source_log_id: str, block_hash: str, finality_state: str, received_at: str
    ) -> None:
        connection = self._require()
        if finality_state not in ("PENDING", "CONFIRMED", "REORG_INVALIDATED"):
            raise MarketTruthError("INPUT_INVALID")
        connection.execute(
            "INSERT INTO chain_finality_events"
            "(source_log_id, block_hash, finality_state, received_at) VALUES(?,?,?,?)",
            (source_log_id, block_hash, finality_state, received_at),
        )

    # -- reads -----------------------------------------------------------
    def _has_observation(self, observation_id: str) -> bool:
        connection = self._require()
        row = connection.execute(
            "SELECT 1 FROM normalized_occurrences WHERE observation_id=? LIMIT 1",
            (observation_id,),
        ).fetchone()
        return row is not None

    def _latest_finality_states(
        self, connection: sqlite3.Connection
    ) -> dict[str, str]:
        """Latest append-only finality-event state per source_log_id."""
        rows = connection.execute(
            "SELECT source_log_id, finality_state FROM chain_finality_events"
            " ORDER BY sequence ASC"
        ).fetchall()
        latest: dict[str, str] = {}
        for source_log_id, state in rows:
            latest[source_log_id] = state
        return latest

    def _latest_pending_order_filled(self) -> tuple[dict[str, object], ...]:
        """Return the newest normalized order_filled payload per source_log_id whose
        latest normalized finality is PENDING AND whose latest append-only finality
        event is not REORG_INVALIDATED. A reorg-invalidated log is no longer active
        pending, so it never re-triggers the same stale hash mismatch."""
        connection = self._require()
        rows = connection.execute(
            "SELECT canonical_payload_json FROM normalized_occurrences"
            " WHERE event_kind='order_filled' ORDER BY archive_sequence ASC"
        ).fetchall()
        latest: dict[str, dict[str, object]] = {}
        for (payload_json,) in rows:
            payload = json.loads(payload_json)
            log_id = payload.get("source_log_id")
            if isinstance(log_id, str):
                latest[log_id] = payload
        finality = self._latest_finality_states(connection)
        return tuple(
            payload
            for log_id, payload in latest.items()
            if payload.get("finality_state") == "PENDING"
            and finality.get(log_id) != "REORG_INVALIDATED"
        )

    def _latest_order_filled(self) -> tuple[dict[str, object], ...]:
        """Return the newest normalized order_filled payload per source_log_id."""
        connection = self._require()
        rows = connection.execute(
            "SELECT canonical_payload_json FROM normalized_occurrences"
            " WHERE event_kind='order_filled' ORDER BY archive_sequence ASC"
        ).fetchall()
        latest: dict[str, dict[str, object]] = {}
        for (payload_json,) in rows:
            payload = json.loads(payload_json)
            log_id = payload.get("source_log_id")
            if isinstance(log_id, str):
                latest[log_id] = payload
        return tuple(latest.values())

    def iter_normalized(
        self, *, after_sequence: int = 0, limit: int = 1000
    ) -> tuple[NormalizedObservation, ...]:
        connection = self._require()
        if not isinstance(after_sequence, int) or after_sequence < 0:
            raise MarketTruthError("INPUT_INVALID")
        if not isinstance(limit, int) or limit < 1:
            raise MarketTruthError("INPUT_INVALID")
        rows = connection.execute(
            "SELECT observation_id, occurrence_id, raw_id, source_kind, event_kind,"
            " event_id, market_id, asset_id, event_time, received_at,"
            " canonical_payload_json, canonical_payload_sha256, status, error_codes_json,"
            " book_ready, provenance_json FROM normalized_occurrences"
            " WHERE archive_sequence>? ORDER BY archive_sequence ASC LIMIT ?",
            (after_sequence, limit),
        ).fetchall()
        result: list[NormalizedObservation] = []
        for row in rows:
            result.append(
                NormalizedObservation(
                    observation_id=row[0],
                    occurrence_id=row[1],
                    raw_id=row[2],
                    source_kind=row[3],
                    event_kind=row[4],
                    event_id=row[5],
                    market_id=row[6],
                    asset_id=row[7],
                    event_time=row[8],
                    received_at=row[9],
                    canonical_payload_json=row[10],
                    canonical_payload_sha256=row[11],
                    status=row[12],
                    error_codes=tuple(json.loads(row[13])),
                    book_ready=bool(row[14]),
                    provenance_json=row[15],
                )
            )
        return tuple(result)

    # -- WP175E additive read-only native-continuity evidence surface ----
    #
    # These queries never write, migrate, or repair the database. They read the
    # already-verified append-only tables through the normal initialized connection,
    # preserve durable append order, enforce a bounded result count, fail closed on
    # malformed persisted evidence with a closed code, and never expose a path.
    def _validate_read_bounds(self, upto_received_at: str, limit: int) -> None:
        if not is_rfc3339_micros(upto_received_at):
            raise MarketTruthError("INPUT_INVALID")
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise MarketTruthError("INPUT_INVALID")
        if not 1 <= limit <= MAX_EVIDENCE_READ_ROWS:
            raise MarketTruthError("INPUT_INVALID")

    def _read_accepted_asset_observations(
        self,
        *,
        asset_id: str,
        start_received_at: str,
        end_received_at: str,
        limit: int = 4096,
    ) -> tuple[AcceptedObservationRecord, ...]:
        """Return verified ACCEPTED WS observations for one exact asset whose
        receive time lies in the inclusive interval, in durable append order.

        Canonical output order is the durable ``archive_sequence`` append order (the
        genuine WP169 knowability order), applied by an explicit ORDER BY so it never
        depends on physical row-retrieval order. A request selecting more than
        ``limit`` rows is rejected closed; ``limit`` itself is bounded.
        """
        connection = self._require()
        if not isinstance(asset_id, str) or not asset_id:
            raise MarketTruthError("INPUT_INVALID")
        self._validate_read_bounds(start_received_at, limit)
        if not is_rfc3339_micros(end_received_at) or start_received_at > end_received_at:
            raise MarketTruthError("INPUT_INVALID")
        predicate = (
            " FROM normalized_occurrences WHERE asset_id=? AND status='ACCEPTED'"
            " AND source_kind='WS'"
            " AND received_at>=? AND received_at<=?"
        )
        params = (asset_id, start_received_at, end_received_at)
        count = connection.execute("SELECT COUNT(*)" + predicate, params).fetchone()[0]
        if int(count) > limit:
            raise MarketTruthError("INPUT_INVALID")
        rows = connection.execute(
            "SELECT n.archive_sequence, n.observation_id, n.occurrence_id, n.raw_id,"
            " n.source_kind, n.event_kind, n.event_id, n.market_id, n.asset_id,"
            " n.event_time, n.received_at, n.canonical_payload_json,"
            " n.canonical_payload_sha256, n.status, n.error_codes_json, n.book_ready,"
            " n.provenance_json, r.source_id, r.source_cursor, r.media_type,"
            " r.raw_bytes, r.byte_length, r.raw_sha256"
            " FROM normalized_occurrences AS n"
            " JOIN raw_occurrences AS r ON r.occurrence_id=n.occurrence_id"
            " WHERE n.asset_id=? AND n.status='ACCEPTED' AND n.source_kind='WS'"
            " AND n.received_at>=? AND n.received_at<=?"
            " ORDER BY n.archive_sequence ASC",
            params,
        ).fetchall()
        if len(rows) != int(count):
            raise MarketTruthError("STORE_CONFLICT")
        result: list[AcceptedObservationRecord] = []
        previous_sequence = 0
        previous_received_at: str | None = None
        for row in rows:
            if (
                not isinstance(row[0], int)
                or isinstance(row[0], bool)
                or row[0] <= previous_sequence
                or row[13] != "ACCEPTED"
                or row[8] != asset_id
                or row[4] != "WS"
                or not is_rfc3339_micros(row[10])
                or (row[9] is not None and not is_rfc3339_micros(row[9]))
                or (previous_received_at is not None and row[10] < previous_received_at)
            ):
                raise MarketTruthError("STORE_CONFLICT")
            try:
                decoded_errors = json.loads(row[14])
            except (TypeError, ValueError):
                raise MarketTruthError("STORE_CONFLICT")
            if not isinstance(decoded_errors, list) or any(
                not isinstance(code, str) for code in decoded_errors
            ):
                raise MarketTruthError("STORE_CONFLICT")
            error_codes = tuple(decoded_errors)
            if error_codes:
                raise MarketTruthError("STORE_CONFLICT")
            if not isinstance(row[15], int) or isinstance(row[15], bool) or row[15] not in (0, 1):
                raise MarketTruthError("STORE_CONFLICT")
            try:
                raw = RawEnvelope(
                    raw_id=row[3],
                    occurrence_id=row[2],
                    source_kind=row[4],
                    source_id=row[17],
                    source_cursor=row[18],
                    received_at=row[10],
                    media_type=row[19],
                    raw_bytes=bytes(row[20]),
                    byte_length=row[21],
                    raw_sha256=row[22],
                )
                observation = NormalizedObservation(
                    observation_id=row[1],
                    occurrence_id=row[2],
                    raw_id=row[3],
                    source_kind=row[4],
                    event_kind=row[5],
                    event_id=row[6],
                    market_id=row[7],
                    asset_id=row[8],
                    event_time=row[9],
                    received_at=row[10],
                    canonical_payload_json=row[11],
                    canonical_payload_sha256=row[12],
                    status=row[13],
                    error_codes=error_codes,
                    book_ready=bool(row[15]),
                    provenance_json=row[16],
                )
            except (TypeError, ValueError, OverflowError):
                raise MarketTruthError("STORE_CONFLICT") from None
            try:
                self._validate_raw(raw)
                self._validate_child(raw, observation)
            except MarketTruthError:
                raise MarketTruthError("STORE_CONFLICT") from None
            cursor_match = _WS_CURSOR_STRICT.fullmatch(raw.source_cursor)
            if cursor_match is None:
                raise MarketTruthError("STORE_CONFLICT")
            result.append(
                AcceptedObservationRecord(
                    archive_sequence=row[0],
                    session_id=cursor_match.group(1),
                    observation=observation,
                )
            )
            previous_sequence = row[0]
            previous_received_at = row[10]
        return tuple(result)

    def _read_session_events(
        self, *, upto_received_at: str, limit: int = 4096
    ) -> tuple[SessionEventRecord, ...]:
        """Return every durable session-transition event received at or before the
        bound, in append (sequence) order, so a caller can reconstruct the exact
        session epoch active at an interval start and any transition inside it."""
        connection = self._require()
        self._validate_read_bounds(upto_received_at, limit)
        count = connection.execute(
            "SELECT COUNT(*) FROM session_events WHERE received_at<=?",
            (upto_received_at,),
        ).fetchone()[0]
        if int(count) > limit:
            raise MarketTruthError("INPUT_INVALID")
        rows = connection.execute(
            "SELECT sequence, session_id, state, received_at FROM session_events"
            " WHERE received_at<=? ORDER BY sequence ASC",
            (upto_received_at,),
        ).fetchall()
        result: list[SessionEventRecord] = []
        previous_sequence = 0
        previous_received_at: str | None = None
        for sequence, session_id, state, received_at in rows:
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence <= previous_sequence
                or state not in SESSION_STATES
                or not is_rfc3339_micros(received_at)
                or (previous_received_at is not None and received_at < previous_received_at)
            ):
                raise MarketTruthError("STORE_CONFLICT")
            if not isinstance(session_id, str) or not session_id:
                raise MarketTruthError("STORE_CONFLICT")
            result.append(
                SessionEventRecord(
                    sequence=int(sequence),
                    session_id=session_id,
                    state=state,
                    received_at=received_at,
                )
            )
            previous_sequence = sequence
            previous_received_at = received_at
        return tuple(result)

    def _read_gap_events(
        self, *, asset_id: str, upto_received_at: str, limit: int = 4096
    ) -> tuple[GapEventRecord, ...]:
        """Return every durable gap-transition event for one exact asset received at
        or before the bound, in append (sequence) order, so a caller can determine
        whether a gap was already OPEN at an interval start or opened inside it."""
        connection = self._require()
        if not isinstance(asset_id, str) or not asset_id:
            raise MarketTruthError("INPUT_INVALID")
        self._validate_read_bounds(upto_received_at, limit)
        count = connection.execute(
            "SELECT COUNT(*) FROM gap_events WHERE asset_id=? AND received_at<=?",
            (asset_id, upto_received_at),
        ).fetchone()[0]
        if int(count) > limit:
            raise MarketTruthError("INPUT_INVALID")
        rows = connection.execute(
            "SELECT sequence, asset_id, state, reason, received_at FROM gap_events"
            " WHERE asset_id=? AND received_at<=? ORDER BY sequence ASC",
            (asset_id, upto_received_at),
        ).fetchall()
        result: list[GapEventRecord] = []
        previous_sequence = 0
        previous_received_at: str | None = None
        for sequence, row_asset_id, state, reason, received_at in rows:
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence <= previous_sequence
                or state not in GAP_STATES
                or reason not in GAP_REASONS
                or not is_rfc3339_micros(received_at)
                or row_asset_id != asset_id
                or (previous_received_at is not None and received_at < previous_received_at)
            ):
                raise MarketTruthError("STORE_CONFLICT")
            result.append(
                GapEventRecord(
                    sequence=int(sequence),
                    asset_id=row_asset_id,
                    state=state,
                    reason=reason,
                    received_at=received_at,
                )
            )
            previous_sequence = sequence
            previous_received_at = received_at
        return tuple(result)


def _locked(method):
    """Serialize a store method behind the instance re-entrant lock.

    functools.wraps preserves __wrapped__ so the exact frozen method signature remains
    introspectable via inspect.signature despite the lock wrapper.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


for _name in (
    "append",
    "write_checkpoint",
    "load_checkpoint",
    "mark_session",
    "mark_gap",
    "_append_finality",
    "iter_normalized",
    "_read_accepted_asset_observations",
    "_read_session_events",
    "_read_gap_events",
    "_has_observation",
    "_latest_pending_order_filled",
    "_latest_order_filled",
    "_checkpoint_history_values",
    "receipt",
):
    setattr(MarketTruthStore, _name, _locked(getattr(MarketTruthStore, _name)))


def read_accepted_asset_observations(
    store: MarketTruthStore,
    *,
    asset_id: str,
    start_received_at: str,
    end_received_at: str,
    limit: int = 4096,
) -> tuple[AcceptedObservationRecord, ...]:
    """Read one bounded immutable accepted-WS evidence interval."""
    if type(store) is not MarketTruthStore:
        raise MarketTruthError("INPUT_INVALID")
    return store._read_accepted_asset_observations(
        asset_id=asset_id,
        start_received_at=start_received_at,
        end_received_at=end_received_at,
        limit=limit,
    )


def read_session_events(
    store: MarketTruthStore, *, upto_received_at: str, limit: int = 4096
) -> tuple[SessionEventRecord, ...]:
    """Read bounded durable session-transition evidence in canonical order."""
    if type(store) is not MarketTruthStore:
        raise MarketTruthError("INPUT_INVALID")
    return store._read_session_events(
        upto_received_at=upto_received_at,
        limit=limit,
    )


def read_gap_events(
    store: MarketTruthStore,
    *,
    asset_id: str,
    upto_received_at: str,
    limit: int = 4096,
) -> tuple[GapEventRecord, ...]:
    """Read bounded durable exact-asset gap evidence in canonical order."""
    if type(store) is not MarketTruthStore:
        raise MarketTruthError("INPUT_INVALID")
    return store._read_gap_events(
        asset_id=asset_id,
        upto_received_at=upto_received_at,
        limit=limit,
    )
