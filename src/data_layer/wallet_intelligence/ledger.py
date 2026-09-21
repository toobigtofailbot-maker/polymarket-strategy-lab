"""Local append-only wallet evidence ledger (S10-WALLET-01).

A deterministic, local, stdlib-only SQLite registry for immutable wallet evidence
records. It is NOT Alpha Factory, WP170, paper, or live execution storage. It has
a unique application_id, a frozen schema, UPDATE/DELETE protection, per-entry hash
chaining in a caller-order-independent canonical order, reference integrity,
exact-duplicate idempotency, same-id/different-payload conflict detection, atomic
batch append, and complete semantic verified load. It performs no migration, no
background writing, and no network or execution work.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3

from ..point_in_time_market_research.records import sha256_hex
from ..point_in_time_market_research.research_provenance import (
    RawEvidenceReference,
    ResearchProvenanceManifest,
    build_pit_timestamps,
    build_raw_evidence_reference,
    build_research_provenance_manifest,
)
from . import contracts as C
from .contracts import wallet_canonical_json_bytes
from .contracts import (
    FeedAcquisitionReceipt,
    WalletAccountIdentityEvidence,
    WalletContractError,
    WalletEventObservation,
    WalletEvidenceEvent,
    WalletFeedPageEvidence,
    WalletIngestRunReceipt,
    WalletProvenanceExtension,
    WalletReconciliationLink,
    map_internal_failure_to_public,
)


WALLET_EVIDENCE_LEDGER_LABEL = "PUBLIC_WALLET_EVIDENCE_APPEND_ONLY_LEDGER"
WALLET_EVIDENCE_LEDGER_POSTURE = "BOUNDED_LOCAL_SQLITE_APPEND_ONLY_VERIFIED_READ"
WALLET_EVIDENCE_LEDGER_FORMAT_ID = "wallet-evidence-ledger"
# Unique SQLite application_id ("WAL1"), distinct from other project registries
# (e.g. the Alpha Factory registry). Proven distinct by test.
WALLET_EVIDENCE_LEDGER_APPLICATION_ID = 0x57414C31  # 1463991857
WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION = 1

WALLET_EVIDENCE_LEDGER_STATUSES = (
    "LEDGER_INITIALIZED",
    "LEDGER_ALREADY_INITIALIZED",
    "LEDGER_APPEND_COMMITTED",
    "LEDGER_APPEND_IDEMPOTENT",
    "LEDGER_LOADED_VERIFIED",
    "LEDGER_REJECTED",
)

_MAX_ROWS = 20_000
_MAX_PAYLOAD_BYTES = 4_194_304
_GENESIS_HASH = "0" * 64

# Record-kind tie-break ranks (12.2).
_KIND_RANK = {
    C.RECORD_KIND_RAW_EVIDENCE_REFERENCE: 10,
    C.RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE: 20,
    C.RECORD_KIND_WALLET_EVIDENCE_EVENT: 30,
    C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE: 40,
    C.RECORD_KIND_WALLET_EVENT_OBSERVATION: 50,
    C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT: 60,
    C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST: 70,
    C.RECORD_KIND_WALLET_PROVENANCE_EXTENSION: 80,
    C.RECORD_KIND_WALLET_RECONCILIATION_LINK: 90,
}

# Run-key carrier invariants (10.6 / 12.1).
_MUST_CARRY_RUN_KEY = frozenset(
    {
        C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE,
        C.RECORD_KIND_WALLET_EVENT_OBSERVATION,
        C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT,
    }
)
_MUST_NOT_CARRY_RUN_KEY = frozenset(
    {
        C.RECORD_KIND_RAW_EVIDENCE_REFERENCE,
        C.RECORD_KIND_WALLET_EVIDENCE_EVENT,
        C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST,
    }
)

_CREATE_META = """CREATE TABLE ledger_meta (
    singleton INTEGER PRIMARY KEY NOT NULL CHECK (singleton = 1),
    format_id TEXT NOT NULL CHECK (format_id = 'wallet-evidence-ledger'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
)"""

_CREATE_ENTRIES = """CREATE TABLE ledger_entries (
    sequence_number INTEGER PRIMARY KEY NOT NULL CHECK (sequence_number >= 0),
    record_id TEXT NOT NULL UNIQUE,
    record_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
)"""

# Append-only enforcement: reject UPDATE and DELETE at the storage layer.
_CREATE_NO_UPDATE = """CREATE TRIGGER ledger_entries_no_update
BEFORE UPDATE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'ledger_entries is append-only');
END"""
_CREATE_NO_DELETE = """CREATE TRIGGER ledger_entries_no_delete
BEFORE DELETE ON ledger_entries
BEGIN
    SELECT RAISE(ABORT, 'ledger_entries is append-only');
END"""


class _LedgerFailure(Exception):
    def __init__(self, internal_code: str) -> None:
        self.internal_code = internal_code
        super().__init__(internal_code)


@dataclass(frozen=True)
class WalletLedgerRecord:
    sequence_number: int
    record_id: str
    record_kind: str
    payload: dict
    payload_sha256: str
    prev_hash: str
    entry_hash: str


@dataclass(frozen=True)
class WalletLedgerSnapshot:
    entries: tuple[WalletLedgerRecord, ...]
    head_hash: str

    def record_ids(self) -> frozenset[str]:
        return frozenset(entry.record_id for entry in self.entries)


@dataclass(frozen=True)
class WalletLedgerResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    snapshot: WalletLedgerSnapshot | None
    inserted_record_ids: tuple[str, ...]
    idempotent_record_ids: tuple[str, ...]


def _rejected(internal_code: str) -> WalletLedgerResult:
    return WalletLedgerResult(
        is_valid=False,
        status="LEDGER_REJECTED",
        error_codes=(map_internal_failure_to_public(internal_code),),
        snapshot=None,
        inserted_record_ids=(),
        idempotent_record_ids=(),
    )


# ===========================================================================
# Record kind / id / serialization / reference model.
# ===========================================================================
def _record_kind(record: object) -> str:
    mapping = {
        RawEvidenceReference: C.RECORD_KIND_RAW_EVIDENCE_REFERENCE,
        ResearchProvenanceManifest: C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST,
        WalletAccountIdentityEvidence: C.RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE,
        WalletEvidenceEvent: C.RECORD_KIND_WALLET_EVIDENCE_EVENT,
        WalletFeedPageEvidence: C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE,
        WalletEventObservation: C.RECORD_KIND_WALLET_EVENT_OBSERVATION,
        WalletIngestRunReceipt: C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT,
        WalletProvenanceExtension: C.RECORD_KIND_WALLET_PROVENANCE_EXTENSION,
        WalletReconciliationLink: C.RECORD_KIND_WALLET_RECONCILIATION_LINK,
    }
    kind = mapping.get(type(record))
    if kind is None:
        raise _LedgerFailure("FIELD_TYPE")
    return kind


_ID_FIELD = {
    C.RECORD_KIND_RAW_EVIDENCE_REFERENCE: "raw_evidence_reference_id",
    C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST: "research_provenance_manifest_id",
    C.RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE: "wallet_account_identity_evidence_id",
    C.RECORD_KIND_WALLET_EVIDENCE_EVENT: "wallet_event_id",
    C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE: "wallet_feed_page_evidence_id",
    C.RECORD_KIND_WALLET_EVENT_OBSERVATION: "wallet_event_observation_id",
    C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT: "wallet_ingest_run_receipt_id",
    C.RECORD_KIND_WALLET_PROVENANCE_EXTENSION: "wallet_provenance_extension_id",
    C.RECORD_KIND_WALLET_RECONCILIATION_LINK: "wallet_reconciliation_link_id",
}


def _record_id(record: object, kind: str) -> str:
    return getattr(record, _ID_FIELD[kind])


def _serialize(record: object, kind: str) -> dict:
    """Full canonical payload dict (including the record id) for one record."""

    id_field = _ID_FIELD[kind]
    identity = getattr(record, id_field)
    if kind == C.RECORD_KIND_RAW_EVIDENCE_REFERENCE:
        body = record.logical_preimage()
        body["schema_id"] = record.schema_id
        body["schema_version"] = record.schema_version
    elif kind == C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST:
        body = record.logical_preimage()
    elif kind == C.RECORD_KIND_WALLET_EVIDENCE_EVENT:
        body = _full_event_dict(record)
    elif kind == C.RECORD_KIND_WALLET_EVENT_OBSERVATION:
        body = record.logical_preimage()
    elif kind == C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT:
        body = record.logical_preimage()
    else:
        body = record.logical_preimage()
    payload = {"record_kind": kind, id_field: identity}
    payload.update(body)
    return payload


def _full_event_dict(event: WalletEvidenceEvent) -> dict:
    return {
        "identity_schema_version": event.identity_schema_version,
        "identity_strength": event.identity_strength,
        "canonical_event_type": event.canonical_event_type,
        "canonical_wallet": event.canonical_wallet,
        "combo_state": event.combo_state,
        "source_system_family": event.source_system_family,
        "chain_id": event.chain_id,
        "condition_context": event.condition_context,
        "condition_value": event.condition_value,
        "token_context": event.token_context,
        "token_value": event.token_value,
        "side": event.side,
        "price": event.price,
        "size": event.size,
        "notional": event.notional,
        "event_time": event.event_time,
        "transaction_hash": event.transaction_hash,
        "log_index": event.log_index,
        "block_hash": event.block_hash,
        "source_contract_address": event.source_contract_address,
        "native_event_id": event.native_event_id,
        "economic_object_key": [list(p) for p in event.economic_object_key],
        "cost_basis_state": event.cost_basis_state,
        "identity_ambiguous": event.identity_ambiguous,
    }


def _run_key_of(record: object, kind: str) -> str | None:
    return getattr(record, "ingest_run_key", None)


def _references(record: object, kind: str) -> list[tuple[str, frozenset[str]]]:
    """Return required (referenced_id, allowed_kinds) pairs for a record."""

    refs: list[tuple[str, frozenset[str]]] = []
    if kind == C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE:
        refs.append(
            (record.raw_evidence_reference_id, frozenset({C.RECORD_KIND_RAW_EVIDENCE_REFERENCE}))
        )
    elif kind == C.RECORD_KIND_WALLET_EVENT_OBSERVATION:
        refs.append((record.wallet_event_id, frozenset({C.RECORD_KIND_WALLET_EVIDENCE_EVENT})))
        refs.append(
            (
                record.wallet_feed_page_evidence_id,
                frozenset({C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE}),
            )
        )
        if record.raw_evidence_reference_id is not None:
            refs.append(
                (
                    record.raw_evidence_reference_id,
                    frozenset({C.RECORD_KIND_RAW_EVIDENCE_REFERENCE}),
                )
            )
    elif kind == C.RECORD_KIND_WALLET_PROVENANCE_EXTENSION:
        refs.append(
            (
                record.research_provenance_manifest_id,
                frozenset({C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST}),
            )
        )
    elif kind == C.RECORD_KIND_WALLET_RECONCILIATION_LINK:
        for eid in record.event_ids:
            refs.append((eid, frozenset({C.RECORD_KIND_WALLET_EVIDENCE_EVENT})))
        for eid in (record.predecessor_event_id, record.successor_event_id):
            if eid is not None:
                refs.append((eid, frozenset({C.RECORD_KIND_WALLET_EVIDENCE_EVENT})))
    elif kind == C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT:
        for pid in record.all_page_evidence_ids:
            refs.append((pid, frozenset({C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE})))
        for oid in record.ordered_observation_ids:
            refs.append((oid, frozenset({C.RECORD_KIND_WALLET_EVENT_OBSERVATION})))
        for eid in record.ordered_event_ids:
            refs.append((eid, frozenset({C.RECORD_KIND_WALLET_EVIDENCE_EVENT})))
        for rid in record.referenced_raw_evidence_ids:
            refs.append((rid, frozenset({C.RECORD_KIND_RAW_EVIDENCE_REFERENCE})))
    return refs


# ===========================================================================
# Rebuild + semantic verified load (12.3).
# ===========================================================================
def _rebuild(kind: str, payload: dict):
    """Rebuild a record from its stored payload via the production builder, so a
    semantically invalid but hash-consistent payload fails verified load."""

    try:
        if kind == C.RECORD_KIND_RAW_EVIDENCE_REFERENCE:
            pit = build_pit_timestamps(**payload["pit"])
            return build_raw_evidence_reference(
                source_system=payload["source_system"],
                endpoint=payload["endpoint"],
                retrieval_method=payload["retrieval_method"],
                content_sha256=payload["content_sha256"],
                byte_length=payload["byte_length"],
                media_type=payload["media_type"],
                pit=pit,
                dq_flags=payload["dq_flags"],
                replay_fidelity=payload["replay_fidelity"],
                request_parameters=[tuple(p) for p in payload["request_parameters"]],
                cursor_anchor=payload["cursor_anchor"],
                api_version=payload["api_version"],
                raw_snapshot_ref=payload["raw_snapshot_ref"],
            )
        if kind == C.RECORD_KIND_RESEARCH_PROVENANCE_MANIFEST:
            return build_research_provenance_manifest(
                repo_code_identity=payload["repo_code_identity"],
                information_cutoff=payload["information_cutoff"],
                output_identity=payload["output_identity"],
                output_hash=payload["output_hash"],
                input_evidence_reference_ids=payload["input_evidence_reference_ids"],
                input_content_hashes=payload["input_content_hashes"],
                dataset_refs=payload["dataset_refs"],
                request_source_version_refs=payload["request_source_version_refs"],
                dq_flags=payload["dq_flags"],
                replay_fidelity=payload["replay_fidelity"],
                gap_summary=payload["gap_summary"],
            )
        if kind == C.RECORD_KIND_WALLET_ACCOUNT_IDENTITY_EVIDENCE:
            return C.build_wallet_account_identity_evidence(
                canonical_wallet=payload["canonical_wallet"],
                generic_account_role=payload["generic_account_role"],
                polymarket_wallet_type=payload["polymarket_wallet_type"],
                evidence_link_class=payload["evidence_link_class"],
                source_reference=payload["source_reference"],
                related_account=payload["related_account"],
                effective_start=payload["effective_start"],
                effective_end=payload["effective_end"],
            )
        if kind == C.RECORD_KIND_WALLET_EVIDENCE_EVENT:
            return C.build_wallet_evidence_event(
                identity_strength=payload["identity_strength"],
                canonical_event_type=payload["canonical_event_type"],
                canonical_wallet=payload["canonical_wallet"],
                combo_state=payload["combo_state"],
                source_system_family=payload["source_system_family"],
                chain_id=payload["chain_id"],
                condition_context=payload["condition_context"],
                condition_value=payload["condition_value"],
                token_context=payload["token_context"],
                token_value=payload["token_value"],
                side=payload["side"],
                price=payload["price"],
                size=payload["size"],
                notional=payload["notional"],
                event_time=payload["event_time"],
                transaction_hash=payload["transaction_hash"],
                log_index=payload["log_index"],
                block_hash=payload["block_hash"],
                source_contract_address=payload["source_contract_address"],
                native_event_id=payload["native_event_id"],
                economic_object_key=[tuple(p) for p in payload["economic_object_key"]],
                cost_basis_state=payload["cost_basis_state"],
                identity_ambiguous=payload["identity_ambiguous"],
            )
        if kind == C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE:
            return C.build_wallet_feed_page_evidence(
                raw_evidence_reference_id=payload["raw_evidence_reference_id"],
                ingest_run_key=payload["ingest_run_key"],
                feed_key=payload["feed_key"],
                canonical_request_identity=[tuple(p) for p in payload["canonical_request_identity"]],
                requested_page_size=payload["requested_page_size"],
                has_more=payload["has_more"],
                local_first_seen_time=payload["local_first_seen_time"],
                ingestion_time=payload["ingestion_time"],
                api_source_parser_version=payload["api_source_parser_version"],
                dq_flags=payload["dq_flags"],
                replay_fidelity=payload["replay_fidelity"],
                source_row_count=payload["source_row_count"],
                normalized_event_count=payload["normalized_event_count"],
                observation_count=payload["observation_count"],
                incoming_cursor=payload["incoming_cursor"],
                outgoing_cursor=payload["outgoing_cursor"],
                freshness_ref=payload["freshness_ref"],
            )
        if kind == C.RECORD_KIND_WALLET_EVENT_OBSERVATION:
            pit = build_pit_timestamps(**payload["pit"])
            return C.build_wallet_event_observation(
                wallet_event_id=payload["wallet_event_id"],
                wallet_feed_page_evidence_id=payload["wallet_feed_page_evidence_id"],
                ingest_run_key=payload["ingest_run_key"],
                source_system=payload["source_system"],
                endpoint=payload["endpoint"],
                source_activity_type=payload["source_activity_type"],
                pit=pit,
                dq_flags=payload["dq_flags"],
                replay_fidelity=payload["replay_fidelity"],
                raw_evidence_reference_id=payload["raw_evidence_reference_id"],
            )
        if kind == C.RECORD_KIND_WALLET_PROVENANCE_EXTENSION:
            return C.build_wallet_provenance_extension(
                research_provenance_manifest_id=payload["research_provenance_manifest_id"],
                chain_metadata=[tuple(p) for p in payload["chain_metadata"]],
                indexer_metadata=[tuple(p) for p in payload["indexer_metadata"]],
                source_metadata=[tuple(p) for p in payload["source_metadata"]],
                cursor_metadata=[tuple(p) for p in payload["cursor_metadata"]],
                first_seen_metadata=[tuple(p) for p in payload["first_seen_metadata"]],
                gap_metadata=[tuple(p) for p in payload["gap_metadata"]],
                reconciliation_metadata=[tuple(p) for p in payload["reconciliation_metadata"]],
                ingest_run_key=payload["ingest_run_key"],
            )
        if kind == C.RECORD_KIND_WALLET_RECONCILIATION_LINK:
            return C.build_wallet_reconciliation_link(
                reconciliation_state=payload["reconciliation_state"],
                relation_kind=payload["relation_kind"],
                event_ids=payload["event_ids"],
                predecessor_event_id=payload["predecessor_event_id"],
                successor_event_id=payload["successor_event_id"],
                finality_state=payload["finality_state"],
                notes=payload["notes"],
            )
        if kind == C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT:
            feed_receipts = tuple(_rebuild_feed_receipt(fr) for fr in payload["feed_receipts"])
            return C.build_wallet_ingest_run_receipt(
                ingest_run_key=payload["ingest_run_key"],
                canonical_wallet=payload["canonical_wallet"],
                run_started_at=payload["run_started_at"],
                run_ended_at=payload["run_ended_at"],
                feed_receipts=feed_receipts,
                collection_completion_state=payload["collection_completion_state"],
                collection_replay_fidelity=payload["collection_replay_fidelity"],
                all_page_evidence_ids=payload["all_page_evidence_ids"],
                referenced_raw_evidence_ids=payload["referenced_raw_evidence_ids"],
                freshness_refs=payload["freshness_refs"],
                aggregate_dq_flags=payload["aggregate_dq_flags"],
                aggregate_page_count=payload["aggregate_page_count"],
                aggregate_source_row_count=payload["aggregate_source_row_count"],
                aggregate_event_count=payload["aggregate_event_count"],
                aggregate_observation_count=payload["aggregate_observation_count"],
                ordered_event_ids=payload["ordered_event_ids"],
                ordered_observation_ids=payload["ordered_observation_ids"],
                schema_version=payload["schema_version"],
            )
    except (WalletContractError, KeyError, TypeError, ValueError):
        raise _LedgerFailure("LEDGER_TAMPER") from None
    raise _LedgerFailure("LEDGER_TAMPER")


def _rebuild_feed_receipt(data: dict) -> FeedAcquisitionReceipt:
    return C.build_feed_acquisition_receipt(
        feed_key=data["feed_key"],
        endpoint=data["endpoint"],
        source_contract_version=data["source_contract_version"],
        canonical_wallet=data["canonical_wallet"],
        time_filter_capability=data["time_filter_capability"],
        acquisition_scope=data["acquisition_scope"],
        requested_page_size=data["requested_page_size"],
        feed_completion_state=data["feed_completion_state"],
        feed_replay_fidelity=data["feed_replay_fidelity"],
        requested_start=data["requested_start"],
        requested_end=data["requested_end"],
        condition_scope=data["condition_scope"],
        frozen_filters=[tuple(p) for p in data["frozen_filters"]],
        page_count=data["page_count"],
        source_row_count=data["source_row_count"],
        page_evidence_ids=data["page_evidence_ids"],
        cursor_chain=[tuple(p) for p in data["cursor_chain"]],
        terminal_has_more=data["terminal_has_more"],
        feed_failure_codes=data["feed_failure_codes"],
        feed_dq_flags=data["feed_dq_flags"],
    )


# ===========================================================================
# Canonical topological ordering + hash chain (12.2).
# ===========================================================================
def _topological_order(records: list[tuple[str, str, object]]) -> list[tuple[str, str, object]]:
    """Order (record_id, kind, record) deterministically.

    Edge: referenced record -> referencing record, only among the batch (a
    reference to an already-persisted record imposes no intra-batch edge). Cycles
    reject. Ready nodes are chosen by the lexicographically smallest
    (kind_rank, record_id).
    """

    by_id = {rid: (rid, kind, rec) for rid, kind, rec in records}
    indegree: dict[str, int] = {rid: 0 for rid in by_id}
    dependents: dict[str, list[str]] = {rid: [] for rid in by_id}
    for rid, kind, rec in records:
        for ref_id, _ in _references(rec, kind):
            if ref_id in by_id and ref_id != rid:
                indegree[rid] += 1
                dependents[ref_id].append(rid)

    ready = sorted(
        (rid for rid, deg in indegree.items() if deg == 0),
        key=lambda r: (_KIND_RANK[by_id[r][1]], r),
    )
    ordered: list[tuple[str, str, object]] = []
    ready_set = list(ready)
    while ready_set:
        current = ready_set.pop(0)
        ordered.append(by_id[current])
        for dep in dependents[current]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                ready_set.append(dep)
        ready_set.sort(key=lambda r: (_KIND_RANK[by_id[r][1]], r))
    if len(ordered) != len(records):
        raise _LedgerFailure("REFERENCE_CYCLE")
    return ordered


def _entry_hash(prev_hash: str, kind: str, record_id: str, payload_sha256: str) -> str:
    return sha256_hex(f"{prev_hash}|{kind}|{record_id}|{payload_sha256}")


# ===========================================================================
# SQLite plumbing.
# ===========================================================================
def _normalize_path(path: object, *, must_exist: bool) -> Path:
    if isinstance(path, (bool, bytes)) or not isinstance(path, (str, os.PathLike)):
        raise _LedgerFailure("FIELD_VALUE")
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise _LedgerFailure("FIELD_VALUE")
    normalized = Path(raw).absolute()
    if normalized.is_symlink():
        raise _LedgerFailure("FIELD_VALUE")
    if must_exist:
        if not normalized.exists() or not normalized.is_file():
            raise _LedgerFailure("REFERENCE_MISSING")
    else:
        if normalized.exists() and not normalized.is_file():
            raise _LedgerFailure("FIELD_VALUE")
        if not normalized.parent.is_dir():
            raise _LedgerFailure("FIELD_VALUE")
    return normalized


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    try:
        return sqlite3.connect(
            f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None, timeout=0.0
        )
    except sqlite3.Error:
        raise _LedgerFailure("UNEXPECTED") from None


def _configure_writable(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() != "delete":
        raise _LedgerFailure("UNEXPECTED")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA foreign_keys=ON")


def _is_pristine(connection: sqlite3.Connection) -> bool:
    version = connection.execute("PRAGMA user_version").fetchone()
    app = connection.execute("PRAGMA application_id").fetchone()
    objects = connection.execute(
        "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return version == (0,) and app == (0,) and objects == []


def _verify_schema(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA application_id").fetchone() != (
        WALLET_EVIDENCE_LEDGER_APPLICATION_ID,
    ):
        raise _LedgerFailure("LEDGER_TAMPER")
    if connection.execute("PRAGMA user_version").fetchone() != (
        WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION,
    ):
        raise _LedgerFailure("LEDGER_TAMPER")
    objects = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    ).fetchall()
    if objects != [
        ("table", "ledger_entries"),
        ("table", "ledger_meta"),
        ("trigger", "ledger_entries_no_delete"),
        ("trigger", "ledger_entries_no_update"),
    ]:
        raise _LedgerFailure("LEDGER_TAMPER")
    if connection.execute(
        "SELECT singleton, format_id, schema_version FROM ledger_meta"
    ).fetchall() != [
        (1, WALLET_EVIDENCE_LEDGER_FORMAT_ID, WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION)
    ]:
        raise _LedgerFailure("LEDGER_TAMPER")


def _verify_integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise _LedgerFailure("LEDGER_TAMPER")


def _decode_payload(payload_json: object, payload_sha256: object) -> dict:
    import json

    if not isinstance(payload_json, str) or not isinstance(payload_sha256, str):
        raise _LedgerFailure("LEDGER_TAMPER")
    try:
        decoded = json.loads(payload_json)
    except (ValueError, TypeError):
        raise _LedgerFailure("LEDGER_TAMPER") from None
    if not isinstance(decoded, dict):
        raise _LedgerFailure("LEDGER_TAMPER")
    canonical = wallet_canonical_json_bytes(decoded)
    if canonical.decode("utf-8") != payload_json or sha256_hex(canonical) != payload_sha256:
        raise _LedgerFailure("LEDGER_TAMPER")
    return decoded


def _load_snapshot(connection: sqlite3.Connection) -> WalletLedgerSnapshot:
    _verify_schema(connection)
    _verify_integrity(connection)
    rows = connection.execute(
        "SELECT sequence_number, record_id, record_kind, payload_json, payload_sha256, "
        "prev_hash, entry_hash FROM ledger_entries ORDER BY sequence_number"
    ).fetchall()
    if len(rows) > _MAX_ROWS:
        raise _LedgerFailure("LIMIT")
    entries: list[WalletLedgerRecord] = []
    prev = _GENESIS_HASH
    for index, row in enumerate(rows):
        seq, record_id, kind, payload_json, payload_sha256, prev_hash, entry_hash = row
        if seq != index:
            raise _LedgerFailure("LEDGER_TAMPER")
        if kind not in _KIND_RANK:
            raise _LedgerFailure("LEDGER_TAMPER")
        payload = _decode_payload(payload_json, payload_sha256)
        if payload.get("record_kind") != kind:
            raise _LedgerFailure("LEDGER_TAMPER")
        if payload.get(_ID_FIELD[kind]) != record_id:
            raise _LedgerFailure("LEDGER_TAMPER")
        # Semantic revalidation: rebuild via the production builder and require an
        # exact match. A semantically invalid but hash-consistent payload fails.
        rebuilt = _rebuild(kind, payload)
        if _serialize(rebuilt, kind) != payload:
            raise _LedgerFailure("LEDGER_TAMPER")
        if getattr(rebuilt, _ID_FIELD[kind]) != record_id:
            raise _LedgerFailure("IDENTITY")
        expected_prev = _GENESIS_HASH if index == 0 else prev
        if prev_hash != expected_prev:
            raise _LedgerFailure("LEDGER_TAMPER")
        expected_entry = _entry_hash(prev_hash, kind, record_id, payload_sha256)
        if entry_hash != expected_entry:
            raise _LedgerFailure("LEDGER_TAMPER")
        entries.append(
            WalletLedgerRecord(
                sequence_number=seq,
                record_id=record_id,
                record_kind=kind,
                payload=payload,
                payload_sha256=payload_sha256,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
        )
        prev = entry_hash
    head = entries[-1].entry_hash if entries else _GENESIS_HASH
    return WalletLedgerSnapshot(entries=tuple(entries), head_hash=head)


def _load_path(path: Path) -> WalletLedgerResult:
    connection = None
    try:
        connection = _connect(path, "ro")
        snapshot = _load_snapshot(connection)
        return WalletLedgerResult(
            is_valid=True,
            status="LEDGER_LOADED_VERIFIED",
            error_codes=(),
            snapshot=snapshot,
            inserted_record_ids=(),
            idempotent_record_ids=(),
        )
    except _LedgerFailure as failure:
        return _rejected(failure.internal_code)
    except sqlite3.Error:
        return _rejected("LEDGER_TAMPER")
    except Exception:
        return _rejected("UNEXPECTED")
    finally:
        if connection is not None:
            connection.close()


def initialize_wallet_evidence_ledger(path: object) -> WalletLedgerResult:
    """Create the exact ledger schema or verify an existing compatible ledger."""

    try:
        normalized = _normalize_path(path, must_exist=False)
        existed = normalized.exists()
    except _LedgerFailure as failure:
        return _rejected(failure.internal_code)

    if existed:
        existing = _load_path(normalized)
        if existing.is_valid:
            return WalletLedgerResult(
                is_valid=True,
                status="LEDGER_ALREADY_INITIALIZED",
                error_codes=(),
                snapshot=existing.snapshot,
                inserted_record_ids=(),
                idempotent_record_ids=(),
            )
        return existing

    connection = None
    committed = False
    try:
        connection = _connect(normalized, "rwc")
        if not _is_pristine(connection):
            return _rejected("LEDGER_TAMPER")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(_CREATE_META)
        connection.execute(_CREATE_ENTRIES)
        connection.execute(_CREATE_NO_UPDATE)
        connection.execute(_CREATE_NO_DELETE)
        connection.execute(
            "INSERT INTO ledger_meta (singleton, format_id, schema_version) VALUES (?, ?, ?)",
            (1, WALLET_EVIDENCE_LEDGER_FORMAT_ID, WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION),
        )
        connection.execute(f"PRAGMA application_id={WALLET_EVIDENCE_LEDGER_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={WALLET_EVIDENCE_LEDGER_SCHEMA_VERSION}")
        connection.execute("COMMIT")
        committed = True
    except _LedgerFailure as failure:
        if connection is not None and connection.in_transaction:
            connection.execute("ROLLBACK")
        return _rejected(failure.internal_code)
    except sqlite3.Error:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("UNEXPECTED")
    finally:
        if connection is not None:
            connection.close()
        if not committed:
            try:
                if normalized.is_file() and not normalized.is_symlink():
                    normalized.unlink()
            except OSError:
                pass

    verified = _load_path(normalized)
    if not verified.is_valid:
        return verified
    return WalletLedgerResult(
        is_valid=True,
        status="LEDGER_INITIALIZED",
        error_codes=(),
        snapshot=verified.snapshot,
        inserted_record_ids=(),
        idempotent_record_ids=(),
    )


def load_and_verify_wallet_evidence_ledger(path: object) -> WalletLedgerResult:
    """Read one existing ledger read-only and fully verify identity, hash chain,
    and semantics."""

    try:
        normalized = _normalize_path(path, must_exist=True)
    except _LedgerFailure as failure:
        return _rejected(failure.internal_code)
    return _load_path(normalized)


# ===========================================================================
# Append.
# ===========================================================================
def _prepare_batch(records: Sequence[object]):
    prepared: list[tuple[str, str, object, dict, str]] = []
    seen_payload: dict[str, str] = {}
    for record in records:
        kind = _record_kind(record)
        record_id = _record_id(record, kind)
        if not isinstance(record_id, str) or not record_id:
            raise _LedgerFailure("IDENTITY")
        payload = _serialize(record, kind)
        payload_bytes = wallet_canonical_json_bytes(payload)
        if len(payload_bytes) > _MAX_PAYLOAD_BYTES:
            raise _LedgerFailure("LIMIT")
        digest = sha256_hex(payload_bytes)
        # Recompute identity independently: the record's stored id must match its
        # own content-address (defends against a hand-built inconsistent record).
        rebuilt = _rebuild(kind, payload)
        if getattr(rebuilt, _ID_FIELD[kind]) != record_id or _serialize(rebuilt, kind) != payload:
            raise _LedgerFailure("IDENTITY")
        # Run-key carrier invariants.
        run_key = _run_key_of(record, kind)
        if kind in _MUST_CARRY_RUN_KEY and not run_key:
            raise _LedgerFailure("FIELD_VALUE")
        if kind in _MUST_NOT_CARRY_RUN_KEY and run_key is not None:
            raise _LedgerFailure("FIELD_VALUE")
        prior = seen_payload.get(record_id)
        if prior is not None:
            if prior != digest:
                raise _LedgerFailure("LEDGER_IDENTITY")
            continue  # exact intra-batch duplicate
        seen_payload[record_id] = digest
        prepared.append((record_id, kind, record, payload, digest))
    return prepared


def _validate_references(
    prepared: list[tuple[str, str, object, dict, str]],
    existing: dict[str, tuple[str, str | None]],
) -> None:
    """existing: record_id -> (kind, run_key). Validate every required reference
    against persisted records plus the proposed batch (12.1)."""

    batch_index: dict[str, tuple[str, object]] = {
        rid: (kind, rec) for rid, kind, rec, _, _ in prepared
    }

    def resolve(ref_id: str) -> tuple[str, str | None] | None:
        if ref_id in batch_index:
            kind, rec = batch_index[ref_id]
            return kind, _run_key_of(rec, kind)
        if ref_id in existing:
            return existing[ref_id]
        return None

    for rid, kind, rec, _payload, _digest in prepared:
        run_key = _run_key_of(rec, kind)
        for ref_id, allowed in _references(rec, kind):
            if ref_id == rid:
                raise _LedgerFailure("REFERENCE_MISSING")  # no self-reference
            resolved = resolve(ref_id)
            if resolved is None:
                raise _LedgerFailure("REFERENCE_MISSING")
            ref_kind, ref_run_key = resolved
            if ref_kind not in allowed:
                raise _LedgerFailure("REFERENCE_WRONG_TYPE")
            # Terminal receipt: referenced page/observation must carry the same run.
            if kind == C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT and ref_kind in (
                C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE,
                C.RECORD_KIND_WALLET_EVENT_OBSERVATION,
            ):
                if ref_run_key != run_key:
                    raise _LedgerFailure("RECONCILIATION")

    _detect_supersession_cycle(prepared, existing)


def _detect_supersession_cycle(
    prepared: list[tuple[str, str, object, dict, str]],
    existing: dict[str, tuple[str, str | None]],
) -> None:
    # Build predecessor -> successor edges across all reconciliation links (batch
    # here; persisted links are already acyclic by prior validation).
    edges: dict[str, set[str]] = {}
    for _rid, kind, rec, _payload, _digest in prepared:
        if kind != C.RECORD_KIND_WALLET_RECONCILIATION_LINK:
            continue
        if rec.predecessor_event_id and rec.successor_event_id:
            if rec.predecessor_event_id == rec.successor_event_id:
                raise _LedgerFailure("RECONCILIATION")
            edges.setdefault(rec.predecessor_event_id, set()).add(rec.successor_event_id)
    color: dict[str, int] = {}

    def visit(node: str) -> None:
        color[node] = 1
        for nxt in edges.get(node, ()):  # gray
            if color.get(nxt) == 1:
                raise _LedgerFailure("REFERENCE_CYCLE")
            if color.get(nxt, 0) == 0:
                visit(nxt)
        color[node] = 2

    for node in list(edges):
        if color.get(node, 0) == 0:
            visit(node)


def append_wallet_evidence_records(
    path: object,
    records: Sequence[object] = (),
) -> WalletLedgerResult:
    """Atomically append a bounded batch of already-built immutable records.

    The stored order, sequence numbers, and head hash are computed in a caller-
    order-independent canonical order. A rejected batch leaves the ledger
    unchanged.
    """

    try:
        normalized = _normalize_path(path, must_exist=True)
    except _LedgerFailure as failure:
        return _rejected(failure.internal_code)

    if not records:
        return _load_status(normalized, "LEDGER_APPEND_IDEMPOTENT")

    connection = None
    inserted_ids: tuple[str, ...] = ()
    idempotent_ids: list[str] = []
    try:
        prepared = _prepare_batch(records)
        connection = _connect(normalized, "rw")
        _configure_writable(connection)
        connection.execute("BEGIN IMMEDIATE")
        snapshot = _load_snapshot(connection)
        existing_by_id: dict[str, tuple[str, str | None]] = {}
        existing_payload_digest: dict[str, str] = {}
        for entry in snapshot.entries:
            existing_by_id[entry.record_id] = (
                entry.record_kind,
                entry.payload.get("ingest_run_key"),
            )
            existing_payload_digest[entry.record_id] = entry.payload_sha256

        # Split prepared into brand-new vs idempotent-existing / conflict.
        new_records: list[tuple[str, str, object, dict, str]] = []
        for rid, kind, rec, payload, digest in prepared:
            if rid in existing_payload_digest:
                if existing_payload_digest[rid] != digest:
                    raise _LedgerFailure("LEDGER_IDENTITY")
                idempotent_ids.append(rid)
                continue
            new_records.append((rid, kind, rec, payload, digest))

        if not new_records:
            connection.execute("ROLLBACK")
            connection.close()
            connection = None
            return _load_status(normalized, "LEDGER_APPEND_IDEMPOTENT", idempotent_ids)

        _validate_references(new_records, existing_by_id)

        ordered = _topological_order([(rid, kind, rec) for rid, kind, rec, _, _ in new_records])
        payload_by_id = {rid: (payload, digest) for rid, _, _, payload, digest in new_records}

        total_after = len(snapshot.entries) + len(ordered)
        if total_after > _MAX_ROWS:
            raise _LedgerFailure("LIMIT")

        prev_hash = snapshot.head_hash
        seq = len(snapshot.entries)
        inserted: list[str] = []
        import json

        for rid, kind, _rec in ordered:
            payload, digest = payload_by_id[rid]
            payload_json = wallet_canonical_json_bytes(payload).decode("utf-8")
            entry_hash = _entry_hash(prev_hash, kind, rid, digest)
            connection.execute(
                "INSERT INTO ledger_entries (sequence_number, record_id, record_kind, "
                "payload_json, payload_sha256, prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (seq, rid, kind, payload_json, digest, prev_hash, entry_hash),
            )
            prev_hash = entry_hash
            seq += 1
            inserted.append(rid)
        connection.execute("COMMIT")
        inserted_ids = tuple(inserted)
    except _LedgerFailure as failure:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected(failure.internal_code)
    except sqlite3.Error:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("LEDGER_TAMPER")
    except Exception:
        if connection is not None and connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return _rejected("UNEXPECTED")
    finally:
        if connection is not None:
            connection.close()

    verified = _load_path(normalized)
    if not verified.is_valid:
        return verified
    return WalletLedgerResult(
        is_valid=True,
        status="LEDGER_APPEND_COMMITTED",
        error_codes=(),
        snapshot=verified.snapshot,
        inserted_record_ids=inserted_ids,
        idempotent_record_ids=tuple(sorted(idempotent_ids)),
    )


def _load_status(
    path: Path, status: str, idempotent_ids: Sequence[str] = ()
) -> WalletLedgerResult:
    verified = _load_path(path)
    if not verified.is_valid:
        return verified
    return WalletLedgerResult(
        is_valid=True,
        status=status,
        error_codes=(),
        snapshot=verified.snapshot,
        inserted_record_ids=(),
        idempotent_record_ids=tuple(sorted(idempotent_ids)),
    )


def query_records_by_ingest_run_key(
    snapshot: WalletLedgerSnapshot, ingest_run_key: str
) -> tuple[WalletLedgerRecord, ...]:
    """Return run-tagged records (page/observation/receipt) carrying the key."""

    return tuple(
        entry
        for entry in snapshot.entries
        if entry.payload.get("ingest_run_key") == ingest_run_key
    )
