"""Bounded scalable one-page keyset public Polymarket capture (WP166).

This module performs a bounded, manual, one-page keyset capture that expands the
real public research corpus materially beyond the WP164/165 first 25 markets while
keeping full lineage integrity. Unlike WP165 (which re-registers the COMPLETE
cumulative <=256-record batch on every run), WP166 registers ONLY the current
page's records through the WP162 lineage-delta adapter and references its direct
lineage parents as an explicit external-parent set already committed by an earlier
manifest entry. This removes the cumulative-256 historical ceiling: physical
history may grow to the WP163 4096-record horizon while each capture's current and
direct-parent contexts each stay bounded <=256.

Before any network activity the module verifies:

* a valid, nonempty, bounded WP163 record store whose records are all supported
  WP164-shaped observations with only the three cross-run lineage classifications
  and the configured provenance;
* a valid WP161 mixed v1/v2 manifest chain whose registered ordinary-id union
  exactly equals the physical WP163 record-id set (baseline convergence).

It defaults to zero network activity. Real keyset use requires BOTH
``allow_network=True`` and ``allow_documented_unverified_keyset=True`` (a double
opt-in), because ``GET /markets/keyset`` is documented but not historically live
probed by this repo. Only in that double-opted-in path is the default client
constructed with ``allow_unverified_endpoints=True``, and only the explicitly
documented keyset call relies on that posture; the CLOB book endpoint remains
already repo-verified.

One invocation performs at most ONE keyset page request (<=100 markets) plus at
most ``order_books_limit`` (<=20) CLOB book reads, builds immutable WP156
observations, classifies each against the entire registered history's latest prior
record for the same entity, appends ONLY the current records through WP163, and
registers the current delta with its exact external direct parents through WP162.
The response ``next_cursor`` is returned to the operator for a later manual
invocation; there is no automatic cursor loop.

Like WP164/165 it has no scheduler, retry, sleep, backoff, credential,
authenticated, Data API, trading, or execution authority, and imports no direct
network library, credential/wallet module, or order/execution module. Every result
fails closed: an invalid result carries only a fixed status and bounded closed
error codes, never a path, URL, raw response, question text, source payload, record
repr, exception text, credential, or arbitrary cursor. Only ordinary ``Exception``
is ever contained; ``BaseException`` always escapes.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass

from ..polymarket.polling_policy import default_polling_policy, validate_polling_policy
from ..polymarket.public_client import PolymarketPublicClient
from .dataset_persistence_adapter import (
    DATASET_PERSISTENCE_ADAPTER_ERROR_CODES,
    DatasetPersistenceAdapterResult,
    persist_lineage_delta_record_batch_snapshot,
)
from .manifest_reference import DatasetSnapshotReference, ManifestEntry
from .manifest_store import load_and_verify_manifest_store
from .record_store import (
    POINT_IN_TIME_RECORD_STORE_ERROR_CODES,
    append_point_in_time_records,
    load_and_verify_point_in_time_record_store,
    materialize_dataset_snapshot_reference,
)
from .records import (
    MarketObservationRecord,
    build_market_observation,
    canonical_json_bytes,
    sha256_hex,
    validate_record_batch,
)
from .polymarket_public_population import (
    _CLOB_ENDPOINT_KEY,
    _CLOB_PAYLOAD_KEYS,
    _CLOB_SOURCE_ID,
    _GAMMA_PAYLOAD_KEYS,
    _GAMMA_SOURCE_ID,
    _PLATFORM_ID,
    _build_gamma_record,
    _build_guard,
    _build_order_book_record,
    _capture_time,
    _consult_guard,
    _get_order_book,
    _normalize_order_book,
    _parse_markets,
    _select_tokens,
)


# ── Locked labels, posture, statuses, and error precedence (WP166) ────────────

POLYMARKET_SCALED_POPULATION_LABEL = (
    "POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION"
)
POLYMARKET_SCALED_POPULATION_POSTURE = (
    "MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY"
)

POLYMARKET_SCALED_POPULATION_STATUSES = (
    "SCALED_DRY_RUN",
    "SCALED_PERSISTED_AND_REGISTERED",
    "SCALED_RECORDS_PERSISTED_REGISTRATION_FAILED",
    "SCALED_RECOVERED_REGISTRATION",
    "SCALED_ALREADY_REGISTERED",
    "SCALED_REJECTED",
)

POLYMARKET_SCALED_POPULATION_ERROR_CODES = (
    "SCALED_INPUT_INVALID",
    "SCALED_RECORD_STORE_INVALID",
    "SCALED_MANIFEST_STORE_INVALID",
    "SCALED_BASELINE_UNREGISTERED",
    "SCALED_BASELINE_REFERENCE_INVALID",
    "SCALED_PROVENANCE_MISMATCH",
    "SCALED_CAPACITY_EXCEEDED",
    "SCALED_KEYSET_OPT_IN_REQUIRED",
    "SCALED_POLICY_INVALID",
    "SCALED_GUARD_DENIED",
    "SCALED_FETCH_FAILED",
    "SCALED_RESPONSE_INVALID",
    "SCALED_IDENTITY_DRIFT",
    "SCALED_BUILD_FAILED",
    "SCALED_BATCH_INVALID",
    "SCALED_RECORD_APPEND_FAILED",
    "SCALED_REGISTRATION_FAILED",
    "SCALED_RECOVERY_INVALID",
    "SCALED_UNEXPECTED_ERROR",
)

_ERROR_ORDER = {
    code: index for index, code in enumerate(POLYMARKET_SCALED_POPULATION_ERROR_CODES)
}

# Bounds. The keyset page is <=100 markets; optional books <=20; the physical
# record store may grow to the WP163 4096-record horizon.
_MAX_PAGE_LIMIT = 100
_MAX_ORDER_BOOKS_LIMIT = 20
_MAX_SCALAR = 256
_MAX_CURSOR = 2048
_MAX_STORE_RECORDS = 4_096
_MAX_MANIFEST_ROWS = 256
_MAX_CURRENT_PAGE = 256
# One page: at most 100 Gamma markets + 20 books = 120 direct current records.
_MAX_ORPHAN_RECORDS = _MAX_PAGE_LIMIT + _MAX_ORDER_BOOKS_LIMIT

_GAMMA_KEYSET_ENDPOINT_KEY = "gamma_markets_keyset"
_GAMMA_KIND = "MARKET_METADATA"
_CLOB_KIND = "ORDER_BOOK"

_ALLOWED_CLASSIFICATIONS = frozenset(
    {"PRIMARY_ASSERTION", "EXACT_DUPLICATE", "SOURCE_REVISION"}
)

# The exact WP163 materialization mode each derivation mode must reproduce when a
# registered reference is materialized against the physical record store. A
# self-consistent reference with a wrong batch hash / ordinary-id order fails these.
_EXPECTED_MATERIALIZATION_MODE = {
    "VALIDATED_RECORD_BATCH": "VALIDATED_BATCH_RECOMPUTED",
    "LINEAGE_DELTA_RECORD_BATCH": "LINEAGE_DELTA_PARENT_CONTEXT_RECOMPUTED",
    "AS_OF_QUERY_RESULT": "AS_OF_REFERENCE_IDS_RESOLVED",
}

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

# Map the closed WP164 helper reject codes onto the closed WP166 vocabulary. Only
# closed enum members are ever translated; no free text is copied across.
_WP164_CODE_MAP = {
    "POPULATION_POLICY_INVALID": "SCALED_POLICY_INVALID",
    "POPULATION_GUARD_DENIED": "SCALED_GUARD_DENIED",
    "POPULATION_FETCH_FAILED": "SCALED_FETCH_FAILED",
    "POPULATION_RESPONSE_INVALID": "SCALED_RESPONSE_INVALID",
    "POPULATION_BUILD_FAILED": "SCALED_BUILD_FAILED",
    "POPULATION_UNEXPECTED_ERROR": "SCALED_UNEXPECTED_ERROR",
}


# ── Public immutable config and result ────────────────────────────────────────


@dataclass(frozen=True)
class PolymarketScaledPopulationConfig:
    manifest_id: str
    parameter_set_id: str
    normalizer_version: str
    validator_version: str
    page_limit: int = 100
    after_cursor: str | None = None
    order_books_limit: int = 0
    allow_network: bool = False
    allow_documented_unverified_keyset: bool = False


@dataclass(frozen=True)
class PolymarketScaledPopulationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record_store_error_codes: tuple[str, ...]
    registration_error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    prior_registered_unique_record_count: int
    new_record_count: int
    primary_assertion_count: int
    exact_duplicate_count: int
    source_revision_count: int
    page_market_count: int
    page_book_count: int
    after_cursor: str | None
    next_cursor: str | None
    snapshot_id: str | None
    captured_at_utc: str | None
    dataset_snapshot_reference_id: str | None
    manifest_entry_id: str | None
    record_store_status: str | None
    registration_status: str | None
    network_used: bool
    recovery_required: bool
    advisory_only: bool
    no_execution_authority: bool


# ── Internal control-flow rejection ───────────────────────────────────────────


class _ScaledReject(Exception):
    """Carry only a closed WP166 error code out of a bounded helper.

    ``recovery`` is set only for a strict-superset baseline that is provably one
    genuine failed scaled page; every other rejection is not recoverable.
    """

    def __init__(self, code: str, *, recovery: bool = False):
        self.code = code
        self.recovery = recovery


class _AppendFailure(Exception):
    def __init__(self, store_error_codes: tuple[str, ...]):
        self.store_error_codes = store_error_codes


def _order(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, len(_ERROR_ORDER)))
    )


def _result(
    *,
    is_valid: bool,
    status: str,
    error_codes: tuple[str, ...] = (),
    record_store_error_codes: tuple[str, ...] = (),
    registration_error_codes: tuple[str, ...] = (),
    prior_registered_unique_record_count: int = 0,
    new_record_count: int = 0,
    primary_assertion_count: int = 0,
    exact_duplicate_count: int = 0,
    source_revision_count: int = 0,
    page_market_count: int = 0,
    page_book_count: int = 0,
    after_cursor: str | None = None,
    next_cursor: str | None = None,
    snapshot_id: str | None = None,
    captured_at_utc: str | None = None,
    dataset_snapshot_reference_id: str | None = None,
    manifest_entry_id: str | None = None,
    record_store_status: str | None = None,
    registration_status: str | None = None,
    network_used: bool = False,
    recovery_required: bool = False,
) -> PolymarketScaledPopulationResult:
    return PolymarketScaledPopulationResult(
        is_valid=is_valid,
        status=status,
        error_codes=_order(error_codes),
        record_store_error_codes=tuple(record_store_error_codes),
        registration_error_codes=tuple(registration_error_codes),
        warning_codes=(),
        prior_registered_unique_record_count=prior_registered_unique_record_count,
        new_record_count=new_record_count,
        primary_assertion_count=primary_assertion_count,
        exact_duplicate_count=exact_duplicate_count,
        source_revision_count=source_revision_count,
        page_market_count=page_market_count,
        page_book_count=page_book_count,
        after_cursor=after_cursor,
        next_cursor=next_cursor,
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
        dataset_snapshot_reference_id=dataset_snapshot_reference_id,
        manifest_entry_id=manifest_entry_id,
        record_store_status=record_store_status,
        registration_status=registration_status,
        network_used=network_used,
        recovery_required=recovery_required,
        advisory_only=True,
        no_execution_authority=True,
    )


def _rejected(code: str) -> PolymarketScaledPopulationResult:
    return _result(is_valid=False, status="SCALED_REJECTED", error_codes=(code,))


# ── Config / public input boundary ────────────────────────────────────────────


def _valid_scalar(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= _MAX_SCALAR and value == value.strip()


def _valid_cursor(value: object) -> bool:
    """A bounded opaque cursor: a stripped control-free str of 1..2048 chars."""

    return (
        type(value) is str
        and 0 < len(value) <= _MAX_CURSOR
        and value == value.strip()
        and _CONTROL_RE.search(value) is None
    )


def _validate_config(config: object) -> None:
    if type(config) is not PolymarketScaledPopulationConfig:
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if (
        type(config.allow_network) is not bool
        or type(config.allow_documented_unverified_keyset) is not bool
    ):
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if type(config.page_limit) is not int or type(config.page_limit) is bool:
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if not (1 <= config.page_limit <= _MAX_PAGE_LIMIT):
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if (
        type(config.order_books_limit) is not int
        or type(config.order_books_limit) is bool
    ):
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if not (0 <= config.order_books_limit <= _MAX_ORDER_BOOKS_LIMIT):
        raise _ScaledReject("SCALED_INPUT_INVALID")
    if config.after_cursor is not None and not _valid_cursor(config.after_cursor):
        raise _ScaledReject("SCALED_INPUT_INVALID")
    for value in (
        config.manifest_id,
        config.parameter_set_id,
        config.normalizer_version,
        config.validator_version,
    ):
        if not _valid_scalar(value):
            raise _ScaledReject("SCALED_INPUT_INVALID")


# ── WP166 deterministic run identity (Section 13) ─────────────────────────────


def _content_id(prefix: str, preimage: dict) -> str:
    return prefix + sha256_hex(canonical_json_bytes(preimage))


def _run_identities(
    *,
    captured_at_utc: str,
    gamma_payload_hashes: list[str],
    clob_payload_hashes: list[str],
    config: PolymarketScaledPopulationConfig,
) -> tuple[str, str]:
    """Derive the deterministic WP166 snapshot/batch identities for one page.

    The preimage commits the WP166 label, the single captured time, ``after_cursor``
    and ``page_limit`` (so the page position is bound into the immutable identity),
    the ordered Gamma/CLOB payload hashes, and the config provenance. ``next_cursor``
    is NEVER part of the immutable record identity. Response order never controls
    the identity.
    """

    base = {
        "label": POLYMARKET_SCALED_POPULATION_LABEL,
        "captured_at_utc": captured_at_utc,
        "after_cursor": config.after_cursor,
        "page_limit": config.page_limit,
        "gamma_payload_sha256_ordered": list(gamma_payload_hashes),
        "clob_payload_sha256_ordered": list(clob_payload_hashes),
        "parameter_set_id": config.parameter_set_id,
        "normalizer_version": config.normalizer_version,
        "validator_version": config.validator_version,
    }
    snapshot_id = _content_id(
        "snapshot:sha256:", dict(base, identity_kind="snapshot_id")
    )
    ingestion_batch_id = _content_id(
        "ingest:sha256:", dict(base, identity_kind="ingestion_batch_id")
    )
    return snapshot_id, ingestion_batch_id


# ── Entity identity, chronology, and drift (Section 14) ───────────────────────


def _entity_identity(record: MarketObservationRecord) -> tuple[object, ...]:
    return (
        "MARKET_OBSERVATION",
        record.platform_id,
        record.event_id,
        record.market_id,
        record.token_id,
        record.source_id,
        record.observation_kind,
    )


def _parse_utc(value: object) -> datetime.datetime:
    """Parse a WP156 UTC timestamp to an aware UTC datetime, or fail closed.

    Latest-prior selection uses true timestamp chronology, never lexical string
    order; a malformed timestamp fails closed with no lexical fallback.
    """

    if type(value) is not str:
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    if parsed.tzinfo is None:
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    return parsed.astimezone(datetime.UTC)


def _time_key(
    record: MarketObservationRecord,
) -> tuple[datetime.datetime, datetime.datetime, str]:
    envelope = record.envelope
    return (
        _parse_utc(envelope.ingestion_time),
        _parse_utc(envelope.observed_time),
        envelope.record_version_id,
    )


def _prior_indexes(prior_records: tuple[MarketObservationRecord, ...]):
    """Build the latest-prior entity index plus the identity-drift lookups."""

    latest_by_identity: dict[tuple[object, ...], MarketObservationRecord] = {}
    market_events: dict[tuple[str, str, str], set[str]] = {}
    token_markets: dict[str, set[str]] = {}
    for record in prior_records:
        identity = _entity_identity(record)
        current = latest_by_identity.get(identity)
        if current is None or _time_key(record) > _time_key(current):
            latest_by_identity[identity] = record
        market_events.setdefault(
            (record.market_id, record.source_id, record.observation_kind), set()
        ).add(record.event_id)
        if record.source_id == _CLOB_SOURCE_ID and record.token_id is not None:
            token_markets.setdefault(record.token_id, set()).add(record.market_id)
    return latest_by_identity, market_events, token_markets


def _require_no_identity_drift(
    candidate: MarketObservationRecord,
    market_events: dict[tuple[str, str, str], set[str]],
    token_markets: dict[str, set[str]],
) -> None:
    key = (candidate.market_id, candidate.source_id, candidate.observation_kind)
    seen_events = market_events.get(key)
    if seen_events is not None and candidate.event_id not in seen_events:
        raise _ScaledReject("SCALED_IDENTITY_DRIFT")
    if candidate.source_id == _CLOB_SOURCE_ID and candidate.token_id is not None:
        seen_markets = token_markets.get(candidate.token_id)
        if seen_markets is not None and candidate.market_id not in seen_markets:
            raise _ScaledReject("SCALED_IDENTITY_DRIFT")


def _rebuild_with_lineage(
    candidate: MarketObservationRecord,
    *,
    classification: str,
    parents: tuple[str, ...],
    supersedes: str | None,
) -> MarketObservationRecord:
    """Rebuild a FINAL record from a PRIMARY_ASSERTION candidate through the public
    builder, replacing only classification, lineage parents, and supersedes."""

    envelope = candidate.envelope
    input_record = {
        "schema_id": envelope.schema_id,
        "schema_version": envelope.schema_version,
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": candidate.observation_kind,
        "platform_id": candidate.platform_id,
        "event_id": candidate.event_id,
        "market_id": candidate.market_id,
        "token_id": candidate.token_id,
        "source_id": candidate.source_id,
        "source_assertion_id": candidate.source_assertion_id,
        "source_snapshot_id": envelope.source_snapshot_id,
        "snapshot_id": envelope.snapshot_id,
        "ingestion_batch_id": envelope.ingestion_batch_id,
        "event_time": envelope.event_time,
        "observed_time": envelope.observed_time,
        "ingestion_time": envelope.ingestion_time,
        "lifecycle_state": "NORMALIZED_ACCEPTED",
        "classification": classification,
        "lineage_parent_ids": list(parents),
        "supersedes_record_version_id": supersedes,
        "normalizer_version": envelope.normalizer_version,
        "validator_version": envelope.validator_version,
        "parameter_set_id": envelope.parameter_set_id,
        "human_review_required": envelope.human_review_required,
        "canonical_payload": json.loads(candidate.canonical_payload_json),
    }
    try:
        built = build_market_observation(input_record)
    except Exception:
        raise _ScaledReject("SCALED_BUILD_FAILED")
    if (
        not built.is_valid
        or built.record is None
        or type(built.record) is not MarketObservationRecord
    ):
        raise _ScaledReject("SCALED_BUILD_FAILED")
    return built.record


def _classify_page_records(
    prior_records: tuple[MarketObservationRecord, ...],
    candidates: list[MarketObservationRecord],
) -> tuple[
    list[MarketObservationRecord],
    dict[str, MarketObservationRecord],
    int,
    int,
    int,
]:
    """Classify each page candidate against the entire history's latest prior.

    Returns ``(new_records, external_parents_by_id, primary, exact_duplicate,
    source_revision)``. Every non-primary record's direct lineage parent is a prior
    record that lives outside this page, so ``external_parents_by_id`` is exactly
    the direct external-parent object set of the current delta.
    """

    latest_by_identity, market_events, token_markets = _prior_indexes(prior_records)
    new_records: list[MarketObservationRecord] = []
    external_parents: dict[str, MarketObservationRecord] = {}
    primary = exact_duplicate = source_revision = 0
    for candidate in candidates:
        _require_no_identity_drift(candidate, market_events, token_markets)
        prior = latest_by_identity.get(_entity_identity(candidate))
        if prior is None:
            new_records.append(candidate)
            primary += 1
            continue
        parent_id = prior.envelope.record_version_id
        external_parents[parent_id] = prior
        if (
            candidate.envelope.canonical_payload_sha256
            == prior.envelope.canonical_payload_sha256
        ):
            new_records.append(
                _rebuild_with_lineage(
                    candidate,
                    classification="EXACT_DUPLICATE",
                    parents=(parent_id,),
                    supersedes=None,
                )
            )
            exact_duplicate += 1
        else:
            new_records.append(
                _rebuild_with_lineage(
                    candidate,
                    classification="SOURCE_REVISION",
                    parents=(parent_id,),
                    supersedes=parent_id,
                )
            )
            source_revision += 1
    return new_records, external_parents, primary, exact_duplicate, source_revision


# ── Store precondition and baseline convergence (Sections 14, 15) ─────────────


def _load_verified_store_records(
    record_store_path: object,
) -> tuple[MarketObservationRecord, ...]:
    try:
        loaded = load_and_verify_point_in_time_record_store(record_store_path)
    except Exception:
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    return loaded.snapshot.records


def _require_supported_store(
    records: tuple[MarketObservationRecord, ...],
    config: PolymarketScaledPopulationConfig,
) -> None:
    if not records:
        raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
    if len(records) > _MAX_STORE_RECORDS:
        raise _ScaledReject("SCALED_CAPACITY_EXCEEDED")
    for record in records:
        if type(record) is not MarketObservationRecord:
            raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        if record.platform_id != _PLATFORM_ID:
            raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        if record.source_id == _GAMMA_SOURCE_ID:
            if record.observation_kind != _GAMMA_KIND:
                raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        elif record.source_id == _CLOB_SOURCE_ID:
            if record.observation_kind != _CLOB_KIND:
                raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        else:
            raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        if record.envelope.classification not in _ALLOWED_CLASSIFICATIONS:
            raise _ScaledReject("SCALED_RECORD_STORE_INVALID")
        if (
            record.envelope.parameter_set_id != config.parameter_set_id
            or record.envelope.normalizer_version != config.normalizer_version
            or record.envelope.validator_version != config.validator_version
        ):
            raise _ScaledReject("SCALED_PROVENANCE_MISMATCH")


def _load_verified_chain(manifest_store_path: object):
    """Load and verify the WP161 mixed v1/v2 chain snapshot or fail closed."""

    try:
        loaded = load_and_verify_manifest_store(manifest_store_path)
    except Exception:
        raise _ScaledReject("SCALED_MANIFEST_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _ScaledReject("SCALED_MANIFEST_STORE_INVALID")
    snapshot = loaded.snapshot
    if not snapshot.manifest_entries:
        raise _ScaledReject("SCALED_MANIFEST_STORE_INVALID")
    if snapshot.chain_validation is None or not snapshot.chain_validation.is_valid:
        raise _ScaledReject("SCALED_MANIFEST_STORE_INVALID")
    return snapshot


def _registered_union(snapshot, config: PolymarketScaledPopulationConfig) -> tuple[
    set[str], str
]:
    """Return ``(registered_ordinary_id_union, head_manifest_entry_id)``.

    Binds the whole chain's shared manifest_id to ``config.manifest_id`` and unions
    the ordinary record ids of every reference registered by a REGISTER entry.
    """

    entries = snapshot.manifest_entries
    if any(entry.manifest_id != config.manifest_id for entry in entries):
        raise _ScaledReject("SCALED_PROVENANCE_MISMATCH")
    references = {
        reference.dataset_snapshot_reference_id: reference
        for reference in snapshot.dataset_references
    }
    union: set[str] = set()
    for entry in entries:
        if entry.entry_kind != "REGISTER_DATASET_SNAPSHOT_REFERENCE":
            continue
        reference = references.get(entry.dataset_snapshot_reference_id)
        if reference is None:
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
        if (
            reference.validator_version != config.validator_version
            or reference.parameter_set_id != config.parameter_set_id
        ):
            raise _ScaledReject("SCALED_PROVENANCE_MISMATCH")
        for record_id in reference.ordinary_record_version_ids:
            union.add(record_id)
    head = snapshot.chain_validation.head_manifest_entry_id
    if type(head) is not str:
        raise _ScaledReject("SCALED_MANIFEST_STORE_INVALID")
    return union, head


def _prove_registered_baseline_materialization(
    record_store_path: object,
    snapshot,
    config: PolymarketScaledPopulationConfig,
) -> None:
    """Materialize every registered reference against the actual WP163 store.

    Exact physical id-set equality alone does not prove a registered reference is a
    genuine record-store materialization: a self-consistent reference (valid self
    id, structurally rebuilt through the verified chain) can still carry a wrong
    ``validated_batch_sha256`` or ordinary-id order. Before any registered ordinary
    id is trusted as lineage authority — in capture pre-network AND in offline
    recovery — every ``REGISTER`` reference must materialize against the actual store
    through the public materializer with the exact ordinary records in reference
    order and the derivation mode's exact verification mode. The materializer
    resolves only the referenced ids, so this holds even against a strict-superset
    physical store. Manifest ancestry authority remains the already-verified
    WP160/WP161 chain and is never duplicated or claimed by the record-store-only
    materializer. Any failure fails closed with ``SCALED_BASELINE_REFERENCE_INVALID``.
    """

    references = {
        reference.dataset_snapshot_reference_id: reference
        for reference in snapshot.dataset_references
    }
    seen: set[str] = set()
    for entry in snapshot.manifest_entries:
        if entry.entry_kind != "REGISTER_DATASET_SNAPSHOT_REFERENCE":
            continue
        subject = entry.dataset_snapshot_reference_id
        reference = references.get(subject)
        # Each registered subject must resolve exactly once.
        if reference is None or subject in seen:
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
        seen.add(subject)
        expected_mode = _EXPECTED_MATERIALIZATION_MODE.get(reference.derivation_mode)
        if expected_mode is None:
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
        try:
            materialization = materialize_dataset_snapshot_reference(
                record_store_path, reference
            )
        except Exception:
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
        if (
            not materialization.is_valid
            or materialization.status != "DATASET_REFERENCE_MATERIALIZED"
            or materialization.verification_mode != expected_mode
        ):
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
        materialized_ids = tuple(
            record.envelope.record_version_id
            for record in materialization.ordinary_records
        )
        if materialized_ids != tuple(reference.ordinary_record_version_ids):
            raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")


def _orphan_suffix_plausible(
    orphan_records: tuple[MarketObservationRecord, ...],
) -> bool:
    """Config-independent single-page shape gate for the recovery advisory.

    The definitive genuine-page proof (which binds ``config.after_cursor`` and
    ``config.page_limit`` into the run identity) belongs to the offline recovery
    path, whose config matches the page that produced the orphans. A new capture's
    config generally differs, so the coordinator only checks a config-independent
    shape here: 1..120 records sharing exactly one snapshot/batch/observed==ingestion
    time with at least one Gamma record.
    """

    count = len(orphan_records)
    if not (1 <= count <= _MAX_ORPHAN_RECORDS):
        return False
    snapshot_ids = {o.envelope.snapshot_id for o in orphan_records}
    batch_ids = {o.envelope.ingestion_batch_id for o in orphan_records}
    observed = {o.envelope.observed_time for o in orphan_records}
    ingestion = {o.envelope.ingestion_time for o in orphan_records}
    if (
        len(snapshot_ids) != 1
        or len(batch_ids) != 1
        or len(observed) != 1
        or len(ingestion) != 1
    ):
        return False
    if next(iter(observed)) != next(iter(ingestion)):
        return False
    return any(o.source_id == _GAMMA_SOURCE_ID for o in orphan_records)


def _prove_baseline_convergence(
    store_records: tuple[MarketObservationRecord, ...],
    registered_union: set[str],
) -> None:
    """Require the physical record-id set to EXACTLY equal the registered union.

    A registered id missing from the store is a corrupt baseline. A physical strict
    superset is an unregistered orphan page: the coordinator blocks any new network
    and advises recovery when the suffix has a plausible single-page shape. The
    definitive genuine-page proof is performed by the offline recovery path.
    """

    store_ids = {record.envelope.record_version_id for record in store_records}
    if not registered_union <= store_ids:
        raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")
    if store_ids == registered_union:
        return
    orphan_records = tuple(
        record
        for record in store_records
        if record.envelope.record_version_id not in registered_union
    )
    raise _ScaledReject(
        "SCALED_BASELINE_UNREGISTERED",
        recovery=_orphan_suffix_plausible(orphan_records),
    )


# ── Policy authority and bounded limits (Section 15) ──────────────────────────


def _call_helper(fn, *args, default_code: str, **kwargs):
    """Run a reused WP164 helper and translate any closed reject to a WP166 code."""

    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - contained; BaseException still escapes
        code = getattr(exc, "code", None)
        mapped = _WP164_CODE_MAP.get(code) if isinstance(code, str) else None
        raise _ScaledReject(mapped or default_code)


def _bounded_limits(config: PolymarketScaledPopulationConfig) -> tuple[int, int]:
    try:
        policy = default_polling_policy()
        validation = validate_polling_policy(policy)
    except Exception:
        raise _ScaledReject("SCALED_POLICY_INVALID")
    if not validation.passed:
        raise _ScaledReject("SCALED_POLICY_INVALID")
    keyset_policy = policy.endpoints.get(_GAMMA_KEYSET_ENDPOINT_KEY)
    clob_policy = policy.endpoints.get(_CLOB_ENDPOINT_KEY)
    if keyset_policy is None or clob_policy is None:
        raise _ScaledReject("SCALED_POLICY_INVALID")
    bounded_markets = min(config.page_limit, keyset_policy.max_markets_per_run)
    bounded_books = min(config.order_books_limit, clob_policy.max_tokens_per_run)
    return bounded_markets, bounded_books


def _require_capacity(
    existing: int, snapshot, config: PolymarketScaledPopulationConfig
) -> None:
    """Enforce the WP163/WP161/current-page capacity gates BEFORE any network."""

    if existing + config.page_limit + config.order_books_limit > _MAX_STORE_RECORDS:
        raise _ScaledReject("SCALED_CAPACITY_EXCEEDED")
    if (
        len(snapshot.manifest_entries) >= _MAX_MANIFEST_ROWS
        or len(snapshot.dataset_references) >= _MAX_MANIFEST_ROWS
    ):
        raise _ScaledReject("SCALED_CAPACITY_EXCEEDED")
    if config.page_limit + config.order_books_limit > _MAX_CURRENT_PAGE:
        raise _ScaledReject("SCALED_CAPACITY_EXCEEDED")


# ── Guarded one-page keyset capture and response boundary (Section 12) ────────


def _require_get_2xx(result: object) -> None:
    request_info = getattr(result, "request_info", None)
    if request_info is None:
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    if getattr(request_info, "method", None) != "GET":
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    status_code = getattr(request_info, "status_code", None)
    if type(status_code) is not int or not (200 <= status_code < 300):
        raise _ScaledReject("SCALED_RESPONSE_INVALID")


def _fetch_keyset_page(
    client: PolymarketPublicClient,
    bounded_markets: int,
    after_cursor: str | None,
) -> tuple[list[dict], str | None]:
    """Fetch exactly ONE keyset page and enforce the response boundary.

    Returns ``(markets, next_cursor)`` where ``markets`` is a built-in list of
    1..bounded_markets built-in dicts and ``next_cursor`` is a validated bounded
    cursor string or ``None``. No second page is ever fetched.
    """

    try:
        result = client.get_markets_keyset(
            limit=bounded_markets, after_cursor=after_cursor
        )
    except _ScaledReject:
        raise
    except Exception:
        raise _ScaledReject("SCALED_FETCH_FAILED")
    _require_get_2xx(result)
    data = getattr(result, "data", None)
    if type(data) is not dict:
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    markets = data.get("markets")
    if type(markets) is not list:
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    if not (1 <= len(markets) <= bounded_markets):
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    for item in markets:
        if type(item) is not dict:
            raise _ScaledReject("SCALED_RESPONSE_INVALID")
    next_cursor = data.get("next_cursor")
    if next_cursor is not None and not _valid_cursor(next_cursor):
        raise _ScaledReject("SCALED_RESPONSE_INVALID")
    return markets, next_cursor


def _capture_page(
    config: PolymarketScaledPopulationConfig,
    *,
    client: object | None,
    guard: object | None,
    now_provider: object | None,
    utcnow_provider: object | None,
    bounded_markets: int,
    bounded_books: int,
    network_used: list[bool],
) -> tuple[list[MarketObservationRecord], str, str, int, int, str | None]:
    """Perform the ONE keyset GET plus optional book reads and build candidates.

    Returns ``(candidates, snapshot_id, captured_at_utc, page_market_count,
    page_book_count, next_cursor)``. ``network_used[0]`` is set to True only once
    the keyset GET is actually attempted. A single failed/denied book aborts the
    whole page before any persistence.
    """

    rate_guard = _build_guard(guard)
    utc_now = (
        (lambda: datetime.datetime.now(datetime.UTC))
        if utcnow_provider is None
        else utcnow_provider
    )

    active_client = client
    if active_client is None:
        # Only the double-opted-in path reaches here, so the keyset endpoint's
        # documented-but-unverified posture is explicitly permitted.
        try:
            active_client = PolymarketPublicClient(allow_unverified_endpoints=True)
        except Exception:
            raise _ScaledReject("SCALED_FETCH_FAILED")

    _call_helper(
        _consult_guard,
        rate_guard,
        _GAMMA_KEYSET_ENDPOINT_KEY,
        now_provider,
        default_code="SCALED_GUARD_DENIED",
    )
    network_used[0] = True
    markets, next_cursor = _fetch_keyset_page(
        active_client, bounded_markets, config.after_cursor
    )
    parsed_markets = _call_helper(
        _parse_markets, markets, default_code="SCALED_RESPONSE_INVALID"
    )
    selected_tokens, token_to_market = _call_helper(
        _select_tokens,
        parsed_markets,
        bounded_books,
        default_code="SCALED_RESPONSE_INVALID",
    )

    raw_books: list[tuple[dict, str, dict]] = []
    for raw_token in selected_tokens:
        _call_helper(
            _consult_guard,
            rate_guard,
            _CLOB_ENDPOINT_KEY,
            now_provider,
            default_code="SCALED_GUARD_DENIED",
        )
        parent = token_to_market[raw_token]
        raw_book = _call_helper(
            _get_order_book,
            active_client,
            raw_token,
            default_code="SCALED_FETCH_FAILED",
        )
        payload = _call_helper(
            _normalize_order_book,
            raw_book,
            raw_token,
            default_code="SCALED_RESPONSE_INVALID",
        )
        raw_books.append((parent, raw_token, payload))

    captured_at_utc = _call_helper(
        _capture_time, utc_now, default_code="SCALED_UNEXPECTED_ERROR"
    )

    gamma_sorted = sorted(parsed_markets, key=lambda entry: entry[0])
    book_sorted = sorted(
        raw_books,
        key=lambda item: (item[0]["market_id"], "token:polymarket:" + item[1]),
    )
    gamma_payload_hashes = [
        sha256_hex(canonical_json_bytes(normalized["payload"]))
        for _market_id, _raw_gamma_id, normalized in gamma_sorted
    ]
    clob_payload_hashes = [
        sha256_hex(canonical_json_bytes(payload)) for _parent, _token, payload in book_sorted
    ]
    snapshot_id, ingestion_batch_id = _run_identities(
        captured_at_utc=captured_at_utc,
        gamma_payload_hashes=gamma_payload_hashes,
        clob_payload_hashes=clob_payload_hashes,
        config=config,
    )

    gamma_records = [
        _call_helper(
            _build_gamma_record,
            normalized,
            default_code="SCALED_BUILD_FAILED",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=captured_at_utc,
            config=config,
        )
        for _market_id, _raw_gamma_id, normalized in parsed_markets
    ]
    book_records = [
        _call_helper(
            _build_order_book_record,
            parent,
            raw_token,
            payload,
            default_code="SCALED_BUILD_FAILED",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=captured_at_utc,
            config=config,
        )
        for parent, raw_token, payload in raw_books
    ]

    gamma_records.sort(key=lambda record: record.market_id)
    book_records.sort(key=lambda record: (record.market_id, record.token_id or ""))
    candidates = gamma_records + book_records
    return (
        candidates,
        snapshot_id,
        captured_at_utc,
        len(gamma_records),
        len(book_records),
        next_cursor,
    )


# ── Current-batch validation, append, and registration (Section 16) ───────────


def _validate_current(
    current_records: tuple[MarketObservationRecord, ...],
    parent_records: tuple[MarketObservationRecord, ...],
) -> tuple[tuple[str, ...], str]:
    """Validate the current page against the actual external direct parents.

    Returns ``(accepted_record_version_ids, canonical_batch_sha256)``.
    """

    if not current_records or len(current_records) > _MAX_CURRENT_PAGE:
        raise _ScaledReject("SCALED_BATCH_INVALID")
    if len(parent_records) > _MAX_CURRENT_PAGE:
        raise _ScaledReject("SCALED_BATCH_INVALID")
    try:
        batch = validate_record_batch(
            current_records, known_parent_records=parent_records
        )
    except Exception:
        raise _ScaledReject("SCALED_BATCH_INVALID")
    if batch.is_valid is not True or batch.quarantined_record_version_ids:
        raise _ScaledReject("SCALED_BATCH_INVALID")
    accepted = tuple(batch.accepted_record_version_ids)
    current_ids = {record.envelope.record_version_id for record in current_records}
    if set(accepted) != current_ids or len(accepted) != len(current_records):
        raise _ScaledReject("SCALED_BATCH_INVALID")
    return accepted, batch.canonical_batch_sha256


def _append_new_records(
    record_store_path: object,
    new_records: tuple[MarketObservationRecord, ...],
) -> tuple[str, tuple[str, ...]]:
    try:
        appended = append_point_in_time_records(record_store_path, new_records)
    except Exception:
        raise _AppendFailure(())
    expected = {record.envelope.record_version_id for record in new_records}
    if (
        not appended.is_valid
        or appended.status != "RECORD_STORE_APPEND_COMMITTED"
        or appended.snapshot is None
        or set(appended.inserted_record_version_ids) != expected
    ):
        raise _AppendFailure(_closed_store_codes(appended.error_codes))
    return appended.status, tuple(sorted(expected))


_ADAPTER_ERROR_CODES = frozenset(DATASET_PERSISTENCE_ADAPTER_ERROR_CODES)
_STORE_ERROR_CODES = frozenset(POINT_IN_TIME_RECORD_STORE_ERROR_CODES)


def _closed_adapter_codes(value: object) -> tuple[str, ...]:
    try:
        return tuple(
            code for code in value if type(code) is str and code in _ADAPTER_ERROR_CODES
        )
    except Exception:
        return ()


def _closed_store_codes(value: object) -> tuple[str, ...]:
    try:
        return tuple(
            code for code in value if type(code) is str and code in _STORE_ERROR_CODES
        )
    except Exception:
        return ()


def _reference_entry_proven(
    reference: DatasetSnapshotReference,
    entry: ManifestEntry,
    config: PolymarketScaledPopulationConfig,
    *,
    effective_time: str,
    expected_accepted_ids: tuple[str, ...],
    expected_external_ids: tuple[str, ...],
    expected_batch_hash: str,
    expected_head: str,
) -> bool:
    """Prove a typed adapter success actually represents THIS current delta."""

    return bool(
        reference.derivation_mode == "LINEAGE_DELTA_RECORD_BATCH"
        and tuple(reference.ordinary_record_version_ids) == expected_accepted_ids
        and reference.review_conflict_record_version_ids == ()
        and tuple(reference.external_parent_record_version_ids) == expected_external_ids
        and reference.validated_batch_sha256 == expected_batch_hash
        and reference.created_from_manifest_entry_id == expected_head
        and reference.validator_version == config.validator_version
        and reference.parameter_set_id == config.parameter_set_id
        and reference.advisory_only is True
        and reference.no_execution_authority is True
        and entry.manifest_id == config.manifest_id
        and entry.dataset_snapshot_reference_id
        == reference.dataset_snapshot_reference_id
        and entry.entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE"
        and entry.reference_state == "ACTIVE_REFERENCE"
        and entry.reason_code == "INITIAL_REGISTRATION"
        and entry.previous_manifest_entry_id == expected_head
        and entry.effective_time == effective_time
        and entry.parameter_set_id == config.parameter_set_id
        and entry.advisory_only is True
        and entry.no_execution_authority is True
    )


def _prove_convergence(
    record_store_path: object,
    manifest_store_path: object,
    reference: DatasetSnapshotReference,
    entry: ManifestEntry,
    config: PolymarketScaledPopulationConfig,
    *,
    expected_accepted_ids: tuple[str, ...],
) -> bool:
    """Independently reload WP161 and WP163 and prove EXACT convergence.

    A typed adapter success plus a subset check is not convergence. This reloads
    both stores and requires: the returned reference and entry persist in a valid
    reloaded chain; the returned entry is the reloaded chain head (no silent
    post-registration head drift); the physical record-id set EXACTLY equals the
    ordinary-id union registered by the reloaded chain (no extra unregistered
    record); every newly-registered current id is present; and every registered
    reference still materializes against the reloaded physical store.
    """

    manifest_loaded = load_and_verify_manifest_store(manifest_store_path)
    if (
        not manifest_loaded.is_valid
        or manifest_loaded.status != "STORE_LOADED_VERIFIED"
        or manifest_loaded.snapshot is None
    ):
        return False
    manifest_snapshot = manifest_loaded.snapshot
    chain = manifest_snapshot.chain_validation
    if not (
        reference in manifest_snapshot.dataset_references
        and entry in manifest_snapshot.manifest_entries
        and chain is not None
        and chain.is_valid
    ):
        return False
    # The returned registration entry must be the reloaded chain head.
    if chain.head_manifest_entry_id != entry.manifest_entry_id:
        return False
    record_loaded = load_and_verify_point_in_time_record_store(record_store_path)
    if (
        not record_loaded.is_valid
        or record_loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or record_loaded.snapshot is None
    ):
        return False
    store_ids = {
        record.envelope.record_version_id
        for record in record_loaded.snapshot.records
    }
    try:
        registered_union, _reloaded_head = _registered_union(manifest_snapshot, config)
    except _ScaledReject:
        return False
    # Exact convergence: physical ids == registered ordinary-id union (not subset),
    # and the newly-registered current ids are present.
    if store_ids != registered_union:
        return False
    if not set(expected_accepted_ids) <= store_ids:
        return False
    # The union is materialized, not merely an id-set: every registered reference
    # must materialize against the reloaded physical store.
    try:
        _prove_registered_baseline_materialization(
            record_store_path, manifest_snapshot, config
        )
    except _ScaledReject:
        return False
    return True


def _safe_register_delta(
    manifest_store_path: object,
    record_store_path: object,
    current_records: tuple[MarketObservationRecord, ...],
    parent_records: tuple[MarketObservationRecord, ...],
    config: PolymarketScaledPopulationConfig,
    *,
    effective_time: str,
    expected_accepted_ids: tuple[str, ...],
    expected_external_ids: tuple[str, ...],
    expected_batch_hash: str,
    expected_head: str,
) -> tuple[bool, str | None, str | None, str | None, tuple[str, ...]]:
    """Register the current delta and extract only trusted scalars.

    Returns ``(ok, status, dataset_snapshot_reference_id, manifest_entry_id,
    closed_codes)``. A claimed success is accepted only after proving the returned
    v2 reference/entry represent exactly this current delta (accepted ids, external
    parent ids, batch hash, prior-head backlink, REGISTER/ACTIVE/INITIAL posture,
    config identity) AND an independent WP161/WP163 reload converges. ``BaseException``
    is never caught and no repr/exception text is exposed.
    """

    try:
        registration = persist_lineage_delta_record_batch_snapshot(
            manifest_store_path,
            current_records,
            parent_records,
            manifest_id=config.manifest_id,
            effective_time=effective_time,
            parameter_set_id=config.parameter_set_id,
            validator_version=config.validator_version,
        )
        if type(registration) is not DatasetPersistenceAdapterResult:
            return False, None, None, None, ()
        if (
            registration.is_valid is True
            and type(registration.status) is str
            and registration.status
            in ("ADAPTER_PERSISTED", "ADAPTER_ALREADY_PERSISTED")
        ):
            reference = registration.dataset_reference
            entry = registration.manifest_entry
            if (
                type(reference) is not DatasetSnapshotReference
                or type(entry) is not ManifestEntry
            ):
                return False, None, None, None, ()
            if not _reference_entry_proven(
                reference,
                entry,
                config,
                effective_time=effective_time,
                expected_accepted_ids=expected_accepted_ids,
                expected_external_ids=expected_external_ids,
                expected_batch_hash=expected_batch_hash,
                expected_head=expected_head,
            ):
                return False, None, None, None, ()
            if not _prove_convergence(
                record_store_path,
                manifest_store_path,
                reference,
                entry,
                config,
                expected_accepted_ids=expected_accepted_ids,
            ):
                return False, None, None, None, ()
            reference_id = reference.dataset_snapshot_reference_id
            entry_id = entry.manifest_entry_id
            if type(reference_id) is not str or type(entry_id) is not str:
                return False, None, None, None, ()
            return True, registration.status, reference_id, entry_id, ()
        return False, None, None, None, _closed_adapter_codes(registration.error_codes)
    except Exception:
        return False, None, None, None, ()


# ── Public coordinator ────────────────────────────────────────────────────────


def capture_scaled_polymarket_public_page(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
    *,
    client: object | None = None,
    guard: object | None = None,
    now_provider: object | None = None,
    utcnow_provider: object | None = None,
) -> PolymarketScaledPopulationResult:
    """Perform one bounded, manual, one-page keyset lineage-delta capture.

    With the default ``allow_network=False`` this makes zero network calls and
    returns a valid dry-run result after fully verifying both stores, the baseline
    convergence, the policy, and the worst-case capacity. Real keyset use requires
    the double opt-in; a lone ``allow_network=True`` is rejected before any client
    construction. Every invalid result is bounded and echo-free.
    """

    try:
        try:
            _validate_config(config)
        except _ScaledReject as reject:
            return _rejected(reject.code)
        assert isinstance(config, PolymarketScaledPopulationConfig)

        try:
            store_records = _load_verified_store_records(record_store_path)
            _require_supported_store(store_records, config)
            snapshot = _load_verified_chain(manifest_store_path)
            registered_union, baseline_head = _registered_union(snapshot, config)
            # Prove the registered baseline FIRST: every registered reference must
            # materialize against the actual store before its ordinary ids are
            # trusted. Only then is the physical superset tested for a recoverable
            # orphan page, so a failed baseline never grants recovery authority.
            _prove_registered_baseline_materialization(
                record_store_path, snapshot, config
            )
            _prove_baseline_convergence(store_records, registered_union)
            _require_capacity(len(store_records), snapshot, config)
        except _ScaledReject as reject:
            return _result(
                is_valid=False,
                status="SCALED_REJECTED",
                error_codes=(reject.code,),
                after_cursor=config.after_cursor,
                recovery_required=reject.recovery,
            )

        prior_count = len(registered_union)

        if not config.allow_network:
            return _result(
                is_valid=True,
                status="SCALED_DRY_RUN",
                prior_registered_unique_record_count=prior_count,
                record_store_status="RECORD_STORE_LOADED_VERIFIED",
                after_cursor=config.after_cursor,
                network_used=False,
            )

        # Double opt-in: real keyset use requires BOTH flags true. A lone
        # allow_network is rejected before any client construction or GET.
        if not config.allow_documented_unverified_keyset:
            return _result(
                is_valid=False,
                status="SCALED_REJECTED",
                error_codes=("SCALED_KEYSET_OPT_IN_REQUIRED",),
                prior_registered_unique_record_count=prior_count,
                after_cursor=config.after_cursor,
                network_used=False,
            )

        return _run_page_capture(
            record_store_path,
            manifest_store_path,
            config,
            store_records=store_records,
            baseline_head=baseline_head,
            prior_count=prior_count,
            client=client,
            guard=guard,
            now_provider=now_provider,
            utcnow_provider=utcnow_provider,
        )
    except Exception:
        return _result(
            is_valid=False,
            status="SCALED_REJECTED",
            error_codes=("SCALED_UNEXPECTED_ERROR",),
        )


def _run_page_capture(
    record_store_path: object,
    manifest_store_path: object,
    config: PolymarketScaledPopulationConfig,
    *,
    store_records: tuple[MarketObservationRecord, ...],
    baseline_head: str,
    prior_count: int,
    client: object | None,
    guard: object | None,
    now_provider: object | None,
    utcnow_provider: object | None,
) -> PolymarketScaledPopulationResult:
    bounded_markets, bounded_books = _bounded_limits(config)
    network_used = [False]

    try:
        (
            candidates,
            snapshot_id,
            captured_at_utc,
            page_market_count,
            page_book_count,
            next_cursor,
        ) = _capture_page(
            config,
            client=client,
            guard=guard,
            now_provider=now_provider,
            utcnow_provider=utcnow_provider,
            bounded_markets=bounded_markets,
            bounded_books=bounded_books,
            network_used=network_used,
        )
        (
            new_records,
            external_parents,
            primary,
            exact_dup,
            source_rev,
        ) = _classify_page_records(store_records, candidates)
        current_tuple = tuple(new_records)
        parent_tuple = tuple(external_parents.values())
        expected_external_ids = tuple(sorted(external_parents))
        expected_accepted_ids, expected_batch_hash = _validate_current(
            current_tuple, parent_tuple
        )
    except _ScaledReject as reject:
        return _result(
            is_valid=False,
            status="SCALED_REJECTED",
            error_codes=(reject.code,),
            prior_registered_unique_record_count=prior_count,
            after_cursor=config.after_cursor,
            network_used=network_used[0],
        )

    counts = dict(
        prior_registered_unique_record_count=prior_count,
        new_record_count=len(current_tuple),
        primary_assertion_count=primary,
        exact_duplicate_count=exact_dup,
        source_revision_count=source_rev,
        page_market_count=page_market_count,
        page_book_count=page_book_count,
        after_cursor=config.after_cursor,
        next_cursor=next_cursor,
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
    )

    # ── Current records appended first (locked), then delta registration. ─────
    try:
        record_store_status, _inserted = _append_new_records(
            record_store_path, current_tuple
        )
    except _AppendFailure as failure:
        return _result(
            is_valid=False,
            status="SCALED_REJECTED",
            error_codes=("SCALED_RECORD_APPEND_FAILED",),
            record_store_error_codes=failure.store_error_codes,
            network_used=True,
            **counts,
        )

    (
        ok,
        registration_status,
        dataset_reference_id,
        manifest_entry_id,
        registration_error_codes,
    ) = _safe_register_delta(
        manifest_store_path,
        record_store_path,
        current_tuple,
        parent_tuple,
        config,
        effective_time=captured_at_utc,
        expected_accepted_ids=expected_accepted_ids,
        expected_external_ids=expected_external_ids,
        expected_batch_hash=expected_batch_hash,
        expected_head=baseline_head,
    )
    if not ok:
        # Current records committed (fail-safe ordering); immutable WP163 records
        # are never deleted. The validated next_cursor is preserved for the
        # operator. Offline recovery re-registers the delta with no fetch.
        return _result(
            is_valid=False,
            status="SCALED_RECORDS_PERSISTED_REGISTRATION_FAILED",
            error_codes=("SCALED_REGISTRATION_FAILED",),
            registration_error_codes=registration_error_codes,
            record_store_status=record_store_status,
            registration_status=None,
            network_used=True,
            recovery_required=True,
            **counts,
        )

    status = (
        "SCALED_PERSISTED_AND_REGISTERED"
        if registration_status == "ADAPTER_PERSISTED"
        else "SCALED_ALREADY_REGISTERED"
    )
    return _result(
        is_valid=True,
        status=status,
        record_store_status=record_store_status,
        registration_status=registration_status,
        dataset_snapshot_reference_id=dataset_reference_id,
        manifest_entry_id=manifest_entry_id,
        network_used=True,
        recovery_required=False,
        **counts,
    )


# ── Offline registration recovery (Section 17) ────────────────────────────────


def recover_scaled_polymarket_public_registration(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
) -> PolymarketScaledPopulationResult:
    """Re-register exactly one committed-but-unregistered scaled page offline.

    This performs ZERO network activity, constructs no client, and never writes
    records. It verifies both stores and the registered ordinary-id union. When the
    store already converges it is a valid ``SCALED_ALREADY_REGISTERED`` no-op. When
    the store strictly extends the registered union by exactly one genuine scaled
    page (1..120 records reconstructed object-for-object from the registered prior
    state, with every direct external parent already registered), it re-registers
    that delta through WP162. A forged, multi-page, drifted, or after_cursor-mismatched
    orphan set fails closed.
    """

    try:
        try:
            _validate_config(config)
        except _ScaledReject as reject:
            return _rejected(reject.code)
        assert isinstance(config, PolymarketScaledPopulationConfig)

        try:
            store_records = _load_verified_store_records(record_store_path)
            _require_supported_store(store_records, config)
            snapshot = _load_verified_chain(manifest_store_path)
            registered_union, baseline_head = _registered_union(snapshot, config)
            # Prove the registered baseline materializes FIRST — in both the
            # converged no-op and the strict-superset recovery cases — before any
            # orphan is interpreted as a recoverable page.
            _prove_registered_baseline_materialization(
                record_store_path, snapshot, config
            )
            store_ids = {r.envelope.record_version_id for r in store_records}
            if not registered_union <= store_ids:
                raise _ScaledReject("SCALED_BASELINE_REFERENCE_INVALID")

            registered_records = tuple(
                r for r in store_records if r.envelope.record_version_id in registered_union
            )
            orphan_records = tuple(
                r
                for r in store_records
                if r.envelope.record_version_id not in registered_union
            )

            if store_ids == registered_union:
                return _result(
                    is_valid=True,
                    status="SCALED_ALREADY_REGISTERED",
                    prior_registered_unique_record_count=len(registered_union),
                    record_store_status="RECORD_STORE_LOADED_VERIFIED",
                    after_cursor=config.after_cursor,
                    network_used=False,
                    recovery_required=False,
                )

            (
                captured_at_utc,
                snapshot_id,
                parent_records,
                primary,
                exact_dup,
                source_rev,
            ) = _prove_orphan_page(registered_records, orphan_records, config)
            current_tuple = orphan_records
            parent_tuple = tuple(parent_records)
            expected_external_ids = tuple(
                sorted(p.envelope.record_version_id for p in parent_tuple)
            )
            expected_accepted_ids, expected_batch_hash = _validate_current(
                current_tuple, parent_tuple
            )
        except _ScaledReject as reject:
            return _result(
                is_valid=False,
                status="SCALED_REJECTED",
                error_codes=(reject.code,),
                after_cursor=config.after_cursor,
            )

        (
            ok,
            registration_status,
            dataset_reference_id,
            manifest_entry_id,
            registration_error_codes,
        ) = _safe_register_delta(
            manifest_store_path,
            record_store_path,
            current_tuple,
            parent_tuple,
            config,
            effective_time=captured_at_utc,
            expected_accepted_ids=expected_accepted_ids,
            expected_external_ids=expected_external_ids,
            expected_batch_hash=expected_batch_hash,
            expected_head=baseline_head,
        )
        counts = dict(
            prior_registered_unique_record_count=len(registered_union),
            new_record_count=len(orphan_records),
            primary_assertion_count=primary,
            exact_duplicate_count=exact_dup,
            source_revision_count=source_rev,
            snapshot_id=snapshot_id,
            captured_at_utc=captured_at_utc,
            after_cursor=config.after_cursor,
            record_store_status="RECORD_STORE_LOADED_VERIFIED",
        )
        if not ok:
            return _result(
                is_valid=False,
                status="SCALED_REJECTED",
                error_codes=("SCALED_REGISTRATION_FAILED",),
                registration_error_codes=registration_error_codes,
                network_used=False,
                recovery_required=True,
                **counts,
            )

        status = (
            "SCALED_RECOVERED_REGISTRATION"
            if registration_status == "ADAPTER_PERSISTED"
            else "SCALED_ALREADY_REGISTERED"
        )
        return _result(
            is_valid=True,
            status=status,
            registration_status=registration_status,
            dataset_snapshot_reference_id=dataset_reference_id,
            manifest_entry_id=manifest_entry_id,
            network_used=False,
            recovery_required=False,
            **counts,
        )
    except Exception:
        return _result(
            is_valid=False,
            status="SCALED_REJECTED",
            error_codes=("SCALED_UNEXPECTED_ERROR",),
        )


def _parse_payload(canonical_payload_json: object) -> dict:
    if type(canonical_payload_json) is not str:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    try:
        payload = json.loads(canonical_payload_json)
    except Exception:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    if type(payload) is not dict:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    return payload


def _orphan_to_candidate(
    orphan: MarketObservationRecord,
    *,
    snapshot_id: str,
    ingestion_batch_id: str,
    config: PolymarketScaledPopulationConfig,
) -> MarketObservationRecord:
    """Rebuild the PRIMARY_ASSERTION candidate the page would have built for an orphan."""

    payload = _parse_payload(orphan.canonical_payload_json)
    observed = orphan.envelope.observed_time
    if orphan.source_id == _GAMMA_SOURCE_ID and orphan.observation_kind == _GAMMA_KIND:
        if frozenset(payload) != _GAMMA_PAYLOAD_KEYS:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        prefix = "market:polymarket:"
        if orphan.token_id is not None or not orphan.market_id.startswith(prefix):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        raw_gamma_id = orphan.market_id[len(prefix):]
        if not raw_gamma_id:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        condition_id = payload["condition_id"]
        condition_norm = (
            condition_id.strip()
            if isinstance(condition_id, str) and condition_id
            else ""
        )
        expected_event = (
            "event:polymarket:" + condition_norm
            if condition_norm
            else "event:polymarket:market-" + raw_gamma_id
        )
        if orphan.event_id != expected_event:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        normalized = {
            "market_id": orphan.market_id,
            "event_id": orphan.event_id,
            "payload": payload,
        }
        return _call_helper(
            _build_gamma_record,
            normalized,
            default_code="SCALED_RECOVERY_INVALID",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=observed,
            config=config,
        )
    if orphan.source_id == _CLOB_SOURCE_ID and orphan.observation_kind == _CLOB_KIND:
        if frozenset(payload) != _CLOB_PAYLOAD_KEYS:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        prefix = "token:polymarket:"
        if orphan.token_id is None or not orphan.token_id.startswith(prefix):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        raw_token = orphan.token_id[len(prefix):]
        if not raw_token:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        parent = {"market_id": orphan.market_id, "event_id": orphan.event_id}
        return _call_helper(
            _build_order_book_record,
            parent,
            raw_token,
            payload,
            default_code="SCALED_RECOVERY_INVALID",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=observed,
            config=config,
        )
    raise _ScaledReject("SCALED_RECOVERY_INVALID")


def _prove_orphan_page(
    registered_records: tuple[MarketObservationRecord, ...],
    orphan_records: tuple[MarketObservationRecord, ...],
    config: PolymarketScaledPopulationConfig,
) -> tuple[str, str, list[MarketObservationRecord], int, int, int]:
    """Prove the orphan suffix is exactly one genuine scaled page.

    Returns ``(captured_at_utc, snapshot_id, external_parent_records, primary,
    exact_duplicate, source_revision)``. Requires: 1..120 orphans sharing exactly one
    snapshot/batch/observed==ingestion time; a config-bounded Gamma/book shape whose
    books reproduce the same-run deterministic token selection; a WP166 run identity
    recomputed from the orphan payload hashes with ``config.after_cursor`` and
    ``config.page_limit`` matching the stored identity; every orphan reconstructing
    object-for-object from the registered prior state; and every direct external
    parent existing as an already-registered record.
    """

    count = len(orphan_records)
    if not (1 <= count <= _MAX_ORPHAN_RECORDS):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")

    snapshot_ids: set[str] = set()
    batch_ids: set[str] = set()
    observed_times: set[str] = set()
    ingestion_times: set[str] = set()
    for orphan in orphan_records:
        envelope = orphan.envelope
        snapshot_ids.add(envelope.snapshot_id)
        batch_ids.add(envelope.ingestion_batch_id)
        observed_times.add(envelope.observed_time)
        ingestion_times.add(envelope.ingestion_time)
    if (
        len(snapshot_ids) != 1
        or len(batch_ids) != 1
        or len(observed_times) != 1
        or len(ingestion_times) != 1
    ):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    captured_at_utc = next(iter(observed_times))
    if captured_at_utc != next(iter(ingestion_times)):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    stored_snapshot_id = next(iter(snapshot_ids))
    stored_batch_id = next(iter(batch_ids))

    gamma_orphans = sorted(
        (o for o in orphan_records if o.source_id == _GAMMA_SOURCE_ID),
        key=lambda record: record.market_id,
    )
    clob_orphans = sorted(
        (o for o in orphan_records if o.source_id == _CLOB_SOURCE_ID),
        key=lambda record: (record.market_id, record.token_id or ""),
    )

    bounded_markets, bounded_books = _bounded_limits(config)
    gamma_count = len(gamma_orphans)
    clob_count = len(clob_orphans)
    if not (1 <= gamma_count <= bounded_markets):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    if clob_count > bounded_books:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    if bounded_books == 0 and clob_count != 0:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")

    parsed_markets: list[tuple[str, str, dict]] = []
    market_prefix = "market:polymarket:"
    for gamma in gamma_orphans:
        payload = _parse_payload(gamma.canonical_payload_json)
        if frozenset(payload) != _GAMMA_PAYLOAD_KEYS:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        if not gamma.market_id.startswith(market_prefix):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        raw_gamma_id = gamma.market_id[len(market_prefix):]
        raw_token_ids = payload["token_ids"]
        if type(raw_token_ids) is not list or any(
            type(token) is not str for token in raw_token_ids
        ):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        parsed_markets.append(
            (
                gamma.market_id,
                raw_gamma_id,
                {
                    "market_id": gamma.market_id,
                    "event_id": gamma.event_id,
                    "raw_token_ids": list(raw_token_ids),
                    "payload": payload,
                },
            )
        )
    parsed_markets.sort(key=lambda entry: entry[0])

    selected_tokens, token_to_market = _call_helper(
        _select_tokens,
        parsed_markets,
        bounded_books,
        default_code="SCALED_RECOVERY_INVALID",
    )
    token_prefix = "token:polymarket:"
    orphan_book_tokens: list[str] = []
    for book in clob_orphans:
        if book.token_id is None or not book.token_id.startswith(token_prefix):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
        orphan_book_tokens.append(book.token_id[len(token_prefix):])
    if len(orphan_book_tokens) != len(set(orphan_book_tokens)):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    if sorted(orphan_book_tokens) != sorted(selected_tokens):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    for book in clob_orphans:
        owner = token_to_market.get(book.token_id[len(token_prefix):])
        if (
            owner is None
            or book.market_id != owner["market_id"]
            or book.event_id != owner["event_id"]
        ):
            raise _ScaledReject("SCALED_RECOVERY_INVALID")

    gamma_hashes = [sha256_hex(o.canonical_payload_json) for o in gamma_orphans]
    clob_hashes = [sha256_hex(o.canonical_payload_json) for o in clob_orphans]
    recomputed_snapshot_id, recomputed_batch_id = _run_identities(
        captured_at_utc=captured_at_utc,
        gamma_payload_hashes=gamma_hashes,
        clob_payload_hashes=clob_hashes,
        config=config,
    )
    if (
        recomputed_snapshot_id != stored_snapshot_id
        or recomputed_batch_id != stored_batch_id
    ):
        raise _ScaledReject("SCALED_RECOVERY_INVALID")

    ordered_orphans = list(gamma_orphans) + list(clob_orphans)
    candidates = [
        _orphan_to_candidate(
            orphan,
            snapshot_id=stored_snapshot_id,
            ingestion_batch_id=stored_batch_id,
            config=config,
        )
        for orphan in ordered_orphans
    ]
    reconstructed, external_parents, primary, exact_dup, source_rev = (
        _classify_page_records(registered_records, candidates)
    )
    expected = {r.envelope.record_version_id: r for r in reconstructed}
    actual = {r.envelope.record_version_id: r for r in orphan_records}
    if expected != actual:
        raise _ScaledReject("SCALED_RECOVERY_INVALID")
    registered_ids = {
        r.envelope.record_version_id for r in registered_records
    }
    for parent_id in external_parents:
        if parent_id not in registered_ids:
            raise _ScaledReject("SCALED_RECOVERY_INVALID")
    return (
        captured_at_utc,
        stored_snapshot_id,
        list(external_parents.values()),
        primary,
        exact_dup,
        source_rev,
    )
