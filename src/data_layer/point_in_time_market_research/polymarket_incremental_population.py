"""Bounded incremental/repeated public Polymarket point-in-time capture (WP165).

This module performs the FIRST safe REPEATED real/public Polymarket capture after
the WP164 initial seed. It captures into an already-populated and already-registered
WP163 record store and commits deterministic cross-run lineage while keeping the
complete cumulative dataset inside one registered WP160 dataset snapshot reference.

Architecture decision (WP162-D004 remains open): WP165 never passes uncommitted
external ``known_parent_record_ids`` through WP162. Instead every cross-run parent
is a record already committed in the same WP163 store, so the cumulative validated
batch (prior registered records + new lineage records) is registered as one WP160
reference. This bounds the cumulative total to <=256 records because the WP156 and
WP162 batch validation is capped at 256; the scalable external-parent/reference
schema extension is a separately gated successor (``WP165-D001``).

Before any network activity the module verifies:

* a valid, nonempty, bounded WP163 record store whose records are all supported
  WP164-shaped observations with only the three cross-run lineage classifications;
* a valid WP161 manifest chain whose latest registered ``VALIDATED_RECORD_BATCH``
  reference exactly matches the currently registered portion of the record store,
  proven by set convergence, a re-run ``validate_record_batch`` whose accepted ids
  and batch hash match the reference, and a successful materialization.

It defaults to zero network activity. When ``allow_network=True`` it reuses the
existing WP164 bounded GET-only Gamma/CLOB capture boundary under the unchanged
``RateLimitGuard``, creates one immutable observation per selected capture, compares
each to the latest prior record for the same WP156 entity, and classifies
deterministically into ``PRIMARY_ASSERTION`` (entity never seen),
``EXACT_DUPLICATE`` (identical canonical payload as latest prior, parent set, no
supersedes), or ``SOURCE_REVISION`` (changed canonical payload, parent set and
supersedes the latest prior). The complete cumulative record set is validated
through WP156, ONLY the new records are appended through WP163, and the COMPLETE
cumulative dataset is registered through the unchanged WP162/WP161 path.

Like WP164 it has no scheduler, retry, sleep, backoff, credential, authenticated,
keyset/pagination, Data API, trading, or execution authority. It imports no direct
network library, credential/wallet module, or order/execution module. Every result
fails closed: an invalid result carries only a fixed status and bounded closed error
codes, never a path, URL, raw response, question text, source payload, record repr,
exception text, or credential. Only ordinary ``Exception`` is ever contained;
``BaseException`` always escapes.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass

from .dataset_persistence_adapter import (
    DATASET_PERSISTENCE_ADAPTER_ERROR_CODES,
    DatasetPersistenceAdapterResult,
    persist_validated_record_batch_snapshot,
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
    PolymarketPublicPopulationConfig,
    _PLATFORM_ID,
    _GAMMA_SOURCE_ID,
    _CLOB_SOURCE_ID,
    _GAMMA_ENDPOINT_KEY,
    _CLOB_ENDPOINT_KEY,
    _bounded_limits,
    _build_guard,
    _consult_guard,
    _get_markets,
    _parse_markets,
    _select_tokens,
    _get_order_book,
    _normalize_order_book,
    _capture_time,
    _build_gamma_record,
    _build_order_book_record,
)
from ..polymarket.public_client import PolymarketPublicClient


# ── Locked labels, posture, statuses, and error precedence (WP165) ────────────

POLYMARKET_INCREMENTAL_POPULATION_LABEL = (
    "POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION"
)
POLYMARKET_INCREMENTAL_POPULATION_POSTURE = (
    "MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY"
)

POLYMARKET_INCREMENTAL_POPULATION_STATUSES = (
    "INCREMENTAL_DRY_RUN",
    "INCREMENTAL_PERSISTED_AND_REGISTERED",
    "INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED",
    "INCREMENTAL_RECOVERED_REGISTRATION",
    "INCREMENTAL_ALREADY_REGISTERED",
    "INCREMENTAL_REJECTED",
)

POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES = (
    "INCREMENTAL_INPUT_INVALID",
    "INCREMENTAL_RECORD_STORE_INVALID",
    "INCREMENTAL_MANIFEST_STORE_INVALID",
    "INCREMENTAL_BASELINE_UNREGISTERED",
    "INCREMENTAL_BASELINE_REFERENCE_INVALID",
    "INCREMENTAL_PROVENANCE_MISMATCH",
    "INCREMENTAL_CAPACITY_EXCEEDED",
    "INCREMENTAL_POLICY_INVALID",
    "INCREMENTAL_GUARD_DENIED",
    "INCREMENTAL_FETCH_FAILED",
    "INCREMENTAL_RESPONSE_INVALID",
    "INCREMENTAL_IDENTITY_DRIFT",
    "INCREMENTAL_BUILD_FAILED",
    "INCREMENTAL_BATCH_INVALID",
    "INCREMENTAL_RECORD_APPEND_FAILED",
    "INCREMENTAL_REGISTRATION_FAILED",
    "INCREMENTAL_RECOVERY_INVALID",
    "INCREMENTAL_UNEXPECTED_ERROR",
)

_ERROR_ORDER = {
    code: index
    for index, code in enumerate(POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES)
}

# Bounds. The authoritative cumulative cap is 256 (the WP156/WP162 batch cap); the
# per-run capture bounds mirror the WP164 config field grammar and policy maxima.
_MAX_MARKETS_LIMIT = 25
_MAX_ORDER_BOOKS_LIMIT = 20
_MAX_SCALAR = 256
_MAX_CUMULATIVE = 256
_MAX_ORPHAN_RECORDS = 45

# Supported source/observation-kind pairs for this bounded package.
_GAMMA_KIND = "MARKET_METADATA"
_CLOB_KIND = "ORDER_BOOK"

# The only lineage classifications WP165 ever reads or writes.
_ALLOWED_CLASSIFICATIONS = frozenset(
    {"PRIMARY_ASSERTION", "EXACT_DUPLICATE", "SOURCE_REVISION"}
)

# Exact WP164 canonical payload key sets, re-proved during offline recovery so a
# forged orphan record cannot claim a genuine WP165 lineage identity.
_GAMMA_PAYLOAD_KEYS = frozenset(
    {
        "question_text",
        "market_status",
        "outcome_labels",
        "condition_id",
        "token_ids",
        "resolution_date",
        "category",
        "raw_field_names",
    }
)
_CLOB_PAYLOAD_KEYS = frozenset(
    {
        "bids",
        "asks",
        "tick_size",
        "minimum_order_size",
        "clob_timestamp",
        "book_hash",
        "last_trade_price",
        "raw_field_names",
    }
)

# Map the closed WP164 helper reject codes onto the closed WP165 vocabulary. Only
# closed enum members are ever translated; no free text is copied across.
_WP164_CODE_MAP = {
    "POPULATION_POLICY_INVALID": "INCREMENTAL_POLICY_INVALID",
    "POPULATION_GUARD_DENIED": "INCREMENTAL_GUARD_DENIED",
    "POPULATION_FETCH_FAILED": "INCREMENTAL_FETCH_FAILED",
    "POPULATION_RESPONSE_INVALID": "INCREMENTAL_RESPONSE_INVALID",
    "POPULATION_BUILD_FAILED": "INCREMENTAL_BUILD_FAILED",
    "POPULATION_UNEXPECTED_ERROR": "INCREMENTAL_UNEXPECTED_ERROR",
}


# ── Public immutable result ───────────────────────────────────────────────────


@dataclass(frozen=True)
class PolymarketIncrementalPopulationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    record_store_error_codes: tuple[str, ...]
    registration_error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    prior_registered_record_count: int
    new_record_count: int
    cumulative_record_count: int
    primary_assertion_count: int
    exact_duplicate_count: int
    source_revision_count: int
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


class _IncrementalReject(Exception):
    """Carry only a closed WP165 error code out of a bounded helper.

    ``recovery`` is set only for a strict-superset baseline that is provably one
    genuine failed incremental run; every other rejection is not recoverable.
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
    prior_registered_record_count: int = 0,
    new_record_count: int = 0,
    cumulative_record_count: int = 0,
    primary_assertion_count: int = 0,
    exact_duplicate_count: int = 0,
    source_revision_count: int = 0,
    snapshot_id: str | None = None,
    captured_at_utc: str | None = None,
    dataset_snapshot_reference_id: str | None = None,
    manifest_entry_id: str | None = None,
    record_store_status: str | None = None,
    registration_status: str | None = None,
    network_used: bool = False,
    recovery_required: bool = False,
) -> PolymarketIncrementalPopulationResult:
    return PolymarketIncrementalPopulationResult(
        is_valid=is_valid,
        status=status,
        error_codes=_order(error_codes),
        record_store_error_codes=tuple(record_store_error_codes),
        registration_error_codes=tuple(registration_error_codes),
        warning_codes=(),
        prior_registered_record_count=prior_registered_record_count,
        new_record_count=new_record_count,
        cumulative_record_count=cumulative_record_count,
        primary_assertion_count=primary_assertion_count,
        exact_duplicate_count=exact_duplicate_count,
        source_revision_count=source_revision_count,
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


def _rejected(code: str) -> PolymarketIncrementalPopulationResult:
    return _result(is_valid=False, status="INCREMENTAL_REJECTED", error_codes=(code,))


# ── Config / public input boundary ────────────────────────────────────────────


def _valid_scalar(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= _MAX_SCALAR and value == value.strip()


def _validate_config(config: object) -> None:
    """Require the exact WP164 config type and mirror its scalar/int/bool grammar."""

    if type(config) is not PolymarketPublicPopulationConfig:
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    if type(config.allow_network) is not bool:
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    if type(config.markets_limit) is not int or type(config.markets_limit) is bool:
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    if not (0 <= config.markets_limit <= _MAX_MARKETS_LIMIT):
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    if (
        type(config.order_books_limit) is not int
        or type(config.order_books_limit) is bool
    ):
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    if not (0 <= config.order_books_limit <= _MAX_ORDER_BOOKS_LIMIT):
        raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")
    for value in (
        config.manifest_id,
        config.parameter_set_id,
        config.normalizer_version,
        config.validator_version,
    ):
        if not _valid_scalar(value):
            raise _IncrementalReject("INCREMENTAL_INPUT_INVALID")


# ── Content addressing and WP165 run identity ─────────────────────────────────


def _content_id(prefix: str, preimage: dict) -> str:
    return prefix + sha256_hex(canonical_json_bytes(preimage))


def _run_identities(
    *,
    captured_at_utc: str,
    gamma_payload_hashes: list[str],
    clob_payload_hashes: list[str],
    config: PolymarketPublicPopulationConfig,
) -> tuple[str, str]:
    """Derive the deterministic WP165 snapshot/batch identities for one capture.

    The preimage commits the WP165 label (never the WP164 seed label), the single
    captured time, the ordered Gamma/CLOB payload hashes, and the config identity.
    Response order never controls the identity.
    """

    base = {
        "label": POLYMARKET_INCREMENTAL_POPULATION_LABEL,
        "captured_at_utc": captured_at_utc,
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


# ── Store precondition and baseline convergence (Sections 8, 14) ──────────────


def _entity_identity(record: MarketObservationRecord) -> tuple[object, ...]:
    """The exact WP156 market-observation entity identity used for lineage."""

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
    """Parse a WP156 UTC timestamp (optional 1..6 fractional digits) to an aware
    UTC datetime.

    Latest-prior selection must use true timestamp chronology, not lexical string
    order: ``12:00:00Z`` and ``12:00:00.500000Z`` sort chronologically but not
    lexically. A malformed timestamp fails closed; there is never a lexical
    fallback.
    """

    if type(value) is not str:
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    if parsed.tzinfo is None:
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    return parsed.astimezone(datetime.UTC)


def _time_key(
    record: MarketObservationRecord,
) -> tuple[datetime.datetime, datetime.datetime, str]:
    # Parsed ingestion datetime, then parsed observed datetime, then the
    # content-addressed record_version_id as a deterministic tie-break.
    envelope = record.envelope
    return (
        _parse_utc(envelope.ingestion_time),
        _parse_utc(envelope.observed_time),
        envelope.record_version_id,
    )


def _load_verified_store_records(
    record_store_path: object,
) -> tuple[MarketObservationRecord, ...]:
    try:
        loaded = load_and_verify_point_in_time_record_store(record_store_path)
    except Exception:
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "RECORD_STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    return loaded.snapshot.records


def _require_supported_store(
    records: tuple[MarketObservationRecord, ...],
    config: PolymarketPublicPopulationConfig,
) -> None:
    if not records:
        raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
    if len(records) > _MAX_CUMULATIVE:
        raise _IncrementalReject("INCREMENTAL_CAPACITY_EXCEEDED")
    for record in records:
        if type(record) is not MarketObservationRecord:
            raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        if record.platform_id != _PLATFORM_ID:
            raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        if record.source_id == _GAMMA_SOURCE_ID:
            if record.observation_kind != _GAMMA_KIND:
                raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        elif record.source_id == _CLOB_SOURCE_ID:
            if record.observation_kind != _CLOB_KIND:
                raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        else:
            raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        if record.envelope.classification not in _ALLOWED_CLASSIFICATIONS:
            raise _IncrementalReject("INCREMENTAL_RECORD_STORE_INVALID")
        if (
            record.envelope.parameter_set_id != config.parameter_set_id
            or record.envelope.normalizer_version != config.normalizer_version
            or record.envelope.validator_version != config.validator_version
        ):
            raise _IncrementalReject("INCREMENTAL_PROVENANCE_MISMATCH")


def _latest_registered_reference(
    manifest_store_path: object,
    config: PolymarketPublicPopulationConfig,
) -> DatasetSnapshotReference:
    """Return the latest registered VALIDATED_RECORD_BATCH reference or fail closed."""

    try:
        loaded = load_and_verify_manifest_store(manifest_store_path)
    except Exception:
        raise _IncrementalReject("INCREMENTAL_MANIFEST_STORE_INVALID")
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        raise _IncrementalReject("INCREMENTAL_MANIFEST_STORE_INVALID")
    snapshot = loaded.snapshot
    entries = snapshot.manifest_entries
    if not entries:
        raise _IncrementalReject("INCREMENTAL_MANIFEST_STORE_INVALID")
    if snapshot.chain_validation is None or not snapshot.chain_validation.is_valid:
        raise _IncrementalReject("INCREMENTAL_MANIFEST_STORE_INVALID")

    # Bind the verified chain's manifest_id to config.manifest_id BEFORE any
    # network. A mismatch would otherwise fetch and append records first and only
    # then be rejected by WP162 as ADAPTER_MANIFEST_ID_MISMATCH, needlessly
    # creating orphan/recovery state. The whole chain shares one manifest_id.
    if any(entry.manifest_id != config.manifest_id for entry in entries):
        raise _IncrementalReject("INCREMENTAL_PROVENANCE_MISMATCH")

    latest = max(entries, key=lambda entry: entry.sequence_number)
    if (
        latest.entry_kind != "REGISTER_DATASET_SNAPSHOT_REFERENCE"
        or latest.reference_state != "ACTIVE_REFERENCE"
        or latest.reason_code != "INITIAL_REGISTRATION"
        or latest.supersedes_manifest_entry_id is not None
    ):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")

    matching = [
        reference
        for reference in snapshot.dataset_references
        if reference.dataset_snapshot_reference_id
        == latest.dataset_snapshot_reference_id
    ]
    if len(matching) != 1:
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    reference = matching[0]
    if reference.derivation_mode != "VALIDATED_RECORD_BATCH":
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    if reference.review_conflict_record_version_ids:
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    if (
        reference.validator_version != config.validator_version
        or reference.parameter_set_id != config.parameter_set_id
    ):
        raise _IncrementalReject("INCREMENTAL_PROVENANCE_MISMATCH")
    return reference


def _prove_registered_reference_materialization(
    record_store_path: object,
    all_store_records: tuple[MarketObservationRecord, ...],
    reference: DatasetSnapshotReference,
) -> tuple[MarketObservationRecord, ...]:
    """Prove a registered reference against ONLY its registered record subset.

    This holds even when the physical WP163 store is a strict superset (an
    unregistered orphan suffix is present): a WP160 reference can be internally
    self-consistent yet not be a genuine record-store materialization, so before
    its records are ever trusted as authoritative lineage parents the reference
    must recompute exactly against the actual store. Returns the proven registered
    record tuple or fails closed with ``INCREMENTAL_BASELINE_REFERENCE_INVALID``.
    """

    ordinary_ids = reference.ordinary_record_version_ids
    if len(set(ordinary_ids)) != len(ordinary_ids):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    by_id = {r.envelope.record_version_id: r for r in all_store_records}
    registered: list[MarketObservationRecord] = []
    for record_id in ordinary_ids:
        record = by_id.get(record_id)
        if record is None:
            raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
        registered.append(record)
    if len(registered) != len(ordinary_ids):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")

    try:
        batch = validate_record_batch(tuple(registered))
    except Exception:
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    if (
        batch.is_valid is not True
        or batch.quarantined_record_version_ids
        or batch.accepted_record_version_ids != reference.ordinary_record_version_ids
        or batch.canonical_batch_sha256 != reference.validated_batch_sha256
    ):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")

    # Materialize against the actual physical store even when it holds a superset.
    try:
        materialization = materialize_dataset_snapshot_reference(
            record_store_path, reference
        )
    except Exception:
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    if (
        not materialization.is_valid
        or materialization.verification_mode != "VALIDATED_BATCH_RECOMPUTED"
    ):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")
    return tuple(registered)


def _prove_baseline_convergence(
    record_store_path: object,
    records: tuple[MarketObservationRecord, ...],
    reference: DatasetSnapshotReference,
    config: PolymarketPublicPopulationConfig,
) -> tuple[MarketObservationRecord, ...]:
    """Prove the latest registered reference against the store (superset-aware).

    The registered reference is ALWAYS proven first (validate + materialize against
    the physical store). A converged store returns; a strict-superset store then
    evaluates the orphan suffix to decide ``recovery_required`` — but only after the
    registered baseline itself is proven. Returns the proven registered record tuple.
    """

    store_ids = {record.envelope.record_version_id for record in records}
    registered_ids = set(reference.ordinary_record_version_ids)
    if len(registered_ids) != len(reference.ordinary_record_version_ids):
        raise _IncrementalReject("INCREMENTAL_BASELINE_REFERENCE_INVALID")

    # Prove the registered reference FIRST. Success guarantees every referenced id
    # exists in the store, so registered_ids is a subset of store_ids.
    registered_records = _prove_registered_reference_materialization(
        record_store_path, records, reference
    )

    if store_ids == registered_ids:
        return registered_records

    # Strict superset: an unregistered suffix is present. It is recoverable ONLY
    # when that suffix is provably exactly one genuine failed WP165 incremental
    # run; an arbitrary WP156-looking record, a forged run, or two distinct orphan
    # batches is blocked before any network with recovery_required=False.
    orphan_records = tuple(
        r for r in records if r.envelope.record_version_id not in registered_ids
    )
    try:
        _prove_orphan_run(registered_records, orphan_records, config)
    except _IncrementalReject:
        raise _IncrementalReject("INCREMENTAL_BASELINE_UNREGISTERED", recovery=False)
    raise _IncrementalReject("INCREMENTAL_BASELINE_UNREGISTERED", recovery=True)


# ── Guarded reuse of the WP164 GET-only capture boundary ──────────────────────


def _call_wp164(fn, *args, default_code: str, **kwargs):
    """Run a reused WP164 helper and translate any closed reject to a WP165 code.

    ``BaseException`` always escapes. The WP164 reject's closed ``.code`` (if any)
    is mapped through ``_WP164_CODE_MAP`` — only closed enum members translate, and
    no free text is copied — otherwise ``default_code`` is used.
    """

    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - contained; BaseException still escapes
        code = getattr(exc, "code", None)
        mapped = _WP164_CODE_MAP.get(code) if isinstance(code, str) else None
        raise _IncrementalReject(mapped or default_code)


def _capture_candidates(
    config: PolymarketPublicPopulationConfig,
    *,
    client: object | None,
    guard: object | None,
    now_provider: object | None,
    utcnow_provider: object | None,
    bounded_markets: int,
    bounded_books: int,
    network_used: list[bool],
) -> tuple[list[MarketObservationRecord], str, str]:
    """Perform the WP164 GET-only reads and build PRIMARY_ASSERTION candidates.

    Returns ``(ordered_candidates, snapshot_id, captured_at_utc)``. Sets
    ``network_used[0]`` to ``True`` only once the Gamma GET is actually attempted.
    """

    rate_guard = _build_guard(guard)
    utc_now = (
        (lambda: datetime.datetime.now(datetime.UTC))
        if utcnow_provider is None
        else utcnow_provider
    )

    active_client = client
    if active_client is None:
        try:
            active_client = PolymarketPublicClient(allow_unverified_endpoints=False)
        except Exception:
            raise _IncrementalReject("INCREMENTAL_FETCH_FAILED")

    _call_wp164(
        _consult_guard,
        rate_guard,
        _GAMMA_ENDPOINT_KEY,
        now_provider,
        default_code="INCREMENTAL_GUARD_DENIED",
    )
    network_used[0] = True
    raw_markets = _call_wp164(
        _get_markets,
        active_client,
        bounded_markets,
        default_code="INCREMENTAL_FETCH_FAILED",
    )
    parsed_markets = _call_wp164(
        _parse_markets, raw_markets, default_code="INCREMENTAL_RESPONSE_INVALID"
    )
    selected_tokens, token_to_market = _call_wp164(
        _select_tokens,
        parsed_markets,
        bounded_books,
        default_code="INCREMENTAL_RESPONSE_INVALID",
    )

    raw_books: list[tuple[dict, str, dict]] = []
    for raw_token in selected_tokens:
        _call_wp164(
            _consult_guard,
            rate_guard,
            _CLOB_ENDPOINT_KEY,
            now_provider,
            default_code="INCREMENTAL_GUARD_DENIED",
        )
        parent = token_to_market[raw_token]
        raw_book = _call_wp164(
            _get_order_book,
            active_client,
            raw_token,
            default_code="INCREMENTAL_FETCH_FAILED",
        )
        payload = _call_wp164(
            _normalize_order_book,
            raw_book,
            raw_token,
            default_code="INCREMENTAL_RESPONSE_INVALID",
        )
        raw_books.append((parent, raw_token, payload))

    captured_at_utc = _call_wp164(
        _capture_time, utc_now, default_code="INCREMENTAL_UNEXPECTED_ERROR"
    )

    # Deterministic WP164 record order for hashing and identity derivation.
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
        sha256_hex(canonical_json_bytes(payload))
        for _parent, _token, payload in book_sorted
    ]
    snapshot_id, ingestion_batch_id = _run_identities(
        captured_at_utc=captured_at_utc,
        gamma_payload_hashes=gamma_payload_hashes,
        clob_payload_hashes=clob_payload_hashes,
        config=config,
    )

    gamma_records = [
        _call_wp164(
            _build_gamma_record,
            normalized,
            default_code="INCREMENTAL_BUILD_FAILED",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=captured_at_utc,
            config=config,
        )
        for _market_id, _raw_gamma_id, normalized in parsed_markets
    ]
    book_records = [
        _call_wp164(
            _build_order_book_record,
            parent,
            raw_token,
            payload,
            default_code="INCREMENTAL_BUILD_FAILED",
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
    return candidates, snapshot_id, captured_at_utc


# ── Deterministic cross-run lineage classification (Sections 12, 13) ──────────


def _rebuild_with_lineage(
    candidate: MarketObservationRecord,
    *,
    classification: str,
    parents: tuple[str, ...],
    supersedes: str | None,
) -> MarketObservationRecord:
    """Rebuild a FINAL record from a PRIMARY_ASSERTION candidate through the public
    builder, replacing only classification, lineage parents, and supersedes.

    Every other field — schema, entity, source ids, run identities, times, payload,
    and provenance versions — is taken from the candidate. A dataclass is never
    mutated.
    """

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
        raise _IncrementalReject("INCREMENTAL_BUILD_FAILED")
    if (
        not built.is_valid
        or built.record is None
        or type(built.record) is not MarketObservationRecord
    ):
        raise _IncrementalReject("INCREMENTAL_BUILD_FAILED")
    return built.record


def _prior_indexes(prior_records: tuple[MarketObservationRecord, ...]):
    """Build the latest-prior entity index plus the identity-drift lookups."""

    latest_by_identity: dict[tuple[object, ...], MarketObservationRecord] = {}
    # (market_id, source_id, observation_kind) -> set of event_ids ever seen.
    market_events: dict[tuple[str, str, str], set[str]] = {}
    # book token_id -> set of market_ids ever seen for that token.
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
        # Same market/source/kind previously seen under a different event id.
        raise _IncrementalReject("INCREMENTAL_IDENTITY_DRIFT")
    if candidate.source_id == _CLOB_SOURCE_ID and candidate.token_id is not None:
        seen_markets = token_markets.get(candidate.token_id)
        if seen_markets is not None and candidate.market_id not in seen_markets:
            # The same raw token was previously associated with another market.
            raise _IncrementalReject("INCREMENTAL_IDENTITY_DRIFT")


def _classify_new_records(
    prior_records: tuple[MarketObservationRecord, ...],
    candidates: list[MarketObservationRecord],
) -> tuple[list[MarketObservationRecord], int, int, int]:
    """Classify every candidate against the latest prior and rebuild final records.

    Returns ``(new_records, primary, exact_duplicate, source_revision)``.
    """

    latest_by_identity, market_events, token_markets = _prior_indexes(prior_records)
    new_records: list[MarketObservationRecord] = []
    primary = exact_duplicate = source_revision = 0
    for candidate in candidates:
        _require_no_identity_drift(candidate, market_events, token_markets)
        prior = latest_by_identity.get(_entity_identity(candidate))
        if prior is None:
            new_records.append(candidate)
            primary += 1
            continue
        parent_id = prior.envelope.record_version_id
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
    return new_records, primary, exact_duplicate, source_revision


# ── Cumulative validation, append, and registration (Sections 14, 15) ─────────


def _validate_cumulative(
    cumulative_records: tuple[MarketObservationRecord, ...],
    new_ids: set[str],
) -> tuple[tuple[str, ...], str]:
    """Validate the complete cumulative batch and return the trusted registration
    expectations ``(accepted_record_version_ids, canonical_batch_sha256)``."""

    if not cumulative_records or len(cumulative_records) > _MAX_CUMULATIVE:
        raise _IncrementalReject("INCREMENTAL_BATCH_INVALID")
    try:
        batch = validate_record_batch(cumulative_records)
    except Exception:
        raise _IncrementalReject("INCREMENTAL_BATCH_INVALID")
    if batch.is_valid is not True or batch.quarantined_record_version_ids:
        raise _IncrementalReject("INCREMENTAL_BATCH_INVALID")
    accepted = set(batch.accepted_record_version_ids)
    if len(batch.accepted_record_version_ids) != len(cumulative_records):
        raise _IncrementalReject("INCREMENTAL_BATCH_INVALID")
    if not new_ids <= accepted:
        raise _IncrementalReject("INCREMENTAL_BATCH_INVALID")
    return (
        tuple(batch.accepted_record_version_ids),
        batch.canonical_batch_sha256,
    )


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
    """Keep only exact members of the closed WP162 adapter vocabulary."""

    try:
        return tuple(
            code for code in value if type(code) is str and code in _ADAPTER_ERROR_CODES
        )
    except Exception:
        return ()


def _closed_store_codes(value: object) -> tuple[str, ...]:
    """Keep only exact members of the closed WP163 record-store vocabulary."""

    try:
        return tuple(
            code for code in value if type(code) is str and code in _STORE_ERROR_CODES
        )
    except Exception:
        return ()


def _reference_entry_proven(
    reference: DatasetSnapshotReference,
    entry: ManifestEntry,
    config: PolymarketPublicPopulationConfig,
    *,
    effective_time: str,
    expected_accepted_ids: tuple[str, ...],
    expected_batch_hash: str,
) -> bool:
    """Prove a typed adapter success actually represents THIS cumulative batch.

    A genuine ``DatasetSnapshotReference``/``ManifestEntry`` pair could still name
    an unrelated dataset; require every field to match the cumulative batch, the
    config identity, the effective time, and the fixed safety posture.
    """

    return bool(
        reference.derivation_mode == "VALIDATED_RECORD_BATCH"
        and tuple(reference.ordinary_record_version_ids) == expected_accepted_ids
        and reference.review_conflict_record_version_ids == ()
        and reference.validated_batch_sha256 == expected_batch_hash
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
        and entry.effective_time == effective_time
        and entry.parameter_set_id == config.parameter_set_id
        and entry.advisory_only is True
        and entry.no_execution_authority is True
    )


def _manifest_persisted(
    manifest_store_path: object,
    reference: DatasetSnapshotReference,
    entry: ManifestEntry,
) -> bool:
    """Independently reload WP161 and require the exact reference and entry to be
    durably persisted in a valid chain (defeats a claimed success that never
    actually wrote the cumulative registration)."""

    loaded = load_and_verify_manifest_store(manifest_store_path)
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        return False
    snapshot = loaded.snapshot
    return bool(
        reference in snapshot.dataset_references
        and entry in snapshot.manifest_entries
        and snapshot.chain_validation is not None
        and snapshot.chain_validation.is_valid
    )


def _safe_register(
    manifest_store_path: object,
    records: tuple[MarketObservationRecord, ...],
    config: PolymarketPublicPopulationConfig,
    *,
    effective_time: str,
    expected_accepted_ids: tuple[str, ...],
    expected_batch_hash: str,
) -> tuple[bool, str | None, str | None, str | None, tuple[str, ...]]:
    """Register the cumulative validated batch and extract only trusted scalars.

    The adapter call AND the full inspection of its returned object are one ordinary
    ``Exception`` boundary. A claimed success is accepted only after proving the
    returned reference/entry represent exactly this cumulative batch (accepted ids,
    batch hash, config identity, effective time, REGISTER/ACTIVE/INITIAL posture)
    AND an independent WP161 reload shows the exact reference and entry durably
    persisted in a valid chain. Only already-validated immutable scalars leave this
    function — the raw registration object never escapes. Returns
    ``(ok, status, dataset_snapshot_reference_id, manifest_entry_id, closed_codes)``.
    ``BaseException`` is never caught and no repr/exception text is exposed.
    """

    try:
        registration = persist_validated_record_batch_snapshot(
            manifest_store_path,
            records,
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
                expected_batch_hash=expected_batch_hash,
            ):
                return False, None, None, None, ()
            if not _manifest_persisted(manifest_store_path, reference, entry):
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


def capture_incremental_polymarket_public_data(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
    *,
    client: object | None = None,
    guard: object | None = None,
    now_provider: object | None = None,
    utcnow_provider: object | None = None,
) -> PolymarketIncrementalPopulationResult:
    """Perform one bounded incremental cumulative-lineage public capture.

    With the default ``allow_network=False`` this makes zero network calls and
    returns a valid dry-run result after fully verifying the store, the manifest
    baseline convergence, the policy, and worst-case capacity. Every invalid result
    is bounded and echo-free.
    """

    try:
        try:
            _validate_config(config)
        except _IncrementalReject as reject:
            return _rejected(reject.code)
        assert isinstance(config, PolymarketPublicPopulationConfig)

        try:
            prior_records = _load_verified_store_records(record_store_path)
            _require_supported_store(prior_records, config)
            reference = _latest_registered_reference(manifest_store_path, config)
            _prove_baseline_convergence(
                record_store_path, prior_records, reference, config
            )
            bounded_markets, bounded_books = _bounded_limits_wp165(config)
            _require_capacity(len(prior_records), bounded_markets, bounded_books)
        except _IncrementalReject as reject:
            return _result(
                is_valid=False,
                status="INCREMENTAL_REJECTED",
                error_codes=(reject.code,),
                recovery_required=reject.recovery,
            )

        prior_count = len(prior_records)

        if not config.allow_network:
            return _result(
                is_valid=True,
                status="INCREMENTAL_DRY_RUN",
                prior_registered_record_count=prior_count,
                new_record_count=0,
                cumulative_record_count=prior_count,
                record_store_status="RECORD_STORE_LOADED_VERIFIED",
                network_used=False,
                recovery_required=False,
            )

        return _run_network_capture(
            record_store_path,
            manifest_store_path,
            config,
            prior_records=prior_records,
            client=client,
            guard=guard,
            now_provider=now_provider,
            utcnow_provider=utcnow_provider,
            bounded_markets=bounded_markets,
            bounded_books=bounded_books,
        )
    except Exception:
        return _result(
            is_valid=False,
            status="INCREMENTAL_REJECTED",
            error_codes=("INCREMENTAL_UNEXPECTED_ERROR",),
        )


def _bounded_limits_wp165(config: PolymarketPublicPopulationConfig) -> tuple[int, int]:
    return _call_wp164(
        _bounded_limits, config, default_code="INCREMENTAL_POLICY_INVALID"
    )


def _require_capacity(existing: int, bounded_markets: int, bounded_books: int) -> None:
    if existing + bounded_markets + bounded_books > _MAX_CUMULATIVE:
        raise _IncrementalReject("INCREMENTAL_CAPACITY_EXCEEDED")


def _run_network_capture(
    record_store_path: object,
    manifest_store_path: object,
    config: PolymarketPublicPopulationConfig,
    *,
    prior_records: tuple[MarketObservationRecord, ...],
    client: object | None,
    guard: object | None,
    now_provider: object | None,
    utcnow_provider: object | None,
    bounded_markets: int,
    bounded_books: int,
) -> PolymarketIncrementalPopulationResult:
    prior_count = len(prior_records)
    network_used = [False]

    if bounded_markets <= 0:
        # An incremental network capture must fetch at least one market; no GET.
        return _result(
            is_valid=False,
            status="INCREMENTAL_REJECTED",
            error_codes=("INCREMENTAL_INPUT_INVALID",),
            prior_registered_record_count=prior_count,
            cumulative_record_count=prior_count,
            network_used=False,
        )

    try:
        candidates, snapshot_id, captured_at_utc = _capture_candidates(
            config,
            client=client,
            guard=guard,
            now_provider=now_provider,
            utcnow_provider=utcnow_provider,
            bounded_markets=bounded_markets,
            bounded_books=bounded_books,
            network_used=network_used,
        )
        new_records, primary, exact_dup, source_rev = _classify_new_records(
            prior_records, candidates
        )
        cumulative_records = tuple(prior_records) + tuple(new_records)
        new_ids = {record.envelope.record_version_id for record in new_records}
        expected_accepted_ids, expected_batch_hash = _validate_cumulative(
            cumulative_records, new_ids
        )
    except _IncrementalReject as reject:
        return _result(
            is_valid=False,
            status="INCREMENTAL_REJECTED",
            error_codes=(reject.code,),
            prior_registered_record_count=prior_count,
            cumulative_record_count=prior_count,
            network_used=network_used[0],
        )

    new_count = len(new_records)
    cumulative_count = len(cumulative_records)
    counts = dict(
        prior_registered_record_count=prior_count,
        new_record_count=new_count,
        cumulative_record_count=cumulative_count,
        primary_assertion_count=primary,
        exact_duplicate_count=exact_dup,
        source_revision_count=source_rev,
        snapshot_id=snapshot_id,
        captured_at_utc=captured_at_utc,
    )

    # ── New records appended first (locked), then cumulative registration. ─────
    try:
        record_store_status, _inserted = _append_new_records(
            record_store_path, tuple(new_records)
        )
    except _AppendFailure as failure:
        return _result(
            is_valid=False,
            status="INCREMENTAL_REJECTED",
            error_codes=("INCREMENTAL_RECORD_APPEND_FAILED",),
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
    ) = _safe_register(
        manifest_store_path,
        cumulative_records,
        config,
        effective_time=captured_at_utc,
        expected_accepted_ids=expected_accepted_ids,
        expected_batch_hash=expected_batch_hash,
    )
    if not ok:
        # New records committed (fail-safe ordering); the immutable WP163 records
        # are never deleted. EVERY registration failure mode after a committed
        # append reports the recoverable partial status. Offline recovery
        # re-registers the complete cumulative store with no fetch.
        return _result(
            is_valid=False,
            status="INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED",
            error_codes=("INCREMENTAL_REGISTRATION_FAILED",),
            registration_error_codes=registration_error_codes,
            record_store_status=record_store_status,
            registration_status=None,
            network_used=True,
            recovery_required=True,
            **counts,
        )

    status = (
        "INCREMENTAL_PERSISTED_AND_REGISTERED"
        if registration_status == "ADAPTER_PERSISTED"
        else "INCREMENTAL_ALREADY_REGISTERED"
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


# ── Offline registration recovery (Section 16) ────────────────────────────────


def recover_incremental_polymarket_public_registration(
    record_store_path: object,
    manifest_store_path: object,
    config: object,
) -> PolymarketIncrementalPopulationResult:
    """Re-register exactly one committed-but-unregistered incremental run offline.

    This performs ZERO network activity, constructs no client, and never writes
    records. It verifies both stores and the latest registered cumulative
    reference. When the store already converges with the reference it is a valid
    ``INCREMENTAL_ALREADY_REGISTERED`` no-op. When the store strictly extends the
    reference by exactly one genuine WP165 orphan run (1..45 records reconstructed
    object-for-object from the registered prior state), it re-validates the complete
    store and re-registers it through WP162. A forged, multi-batch, drifted, or
    mismatched orphan set fails closed.
    """

    try:
        try:
            _validate_config(config)
        except _IncrementalReject as reject:
            return _rejected(reject.code)
        assert isinstance(config, PolymarketPublicPopulationConfig)

        try:
            store_records = _load_verified_store_records(record_store_path)
            _require_supported_store(store_records, config)
            reference = _latest_registered_reference(manifest_store_path, config)
            registered_ids = set(reference.ordinary_record_version_ids)
            store_ids = {r.envelope.record_version_id for r in store_records}

            # Prove the registered baseline reference against the store FIRST, in
            # both the converged and the strict-superset cases, before any of its
            # records are trusted as authoritative lineage parents.
            registered_records = _prove_registered_reference_materialization(
                record_store_path, store_records, reference
            )

            if store_ids == registered_ids:
                return _result(
                    is_valid=True,
                    status="INCREMENTAL_ALREADY_REGISTERED",
                    prior_registered_record_count=len(registered_ids),
                    new_record_count=0,
                    cumulative_record_count=len(store_records),
                    record_store_status="RECORD_STORE_LOADED_VERIFIED",
                    network_used=False,
                    recovery_required=False,
                )

            if not registered_ids < store_ids:
                raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")

            orphan_records = tuple(
                r for r in store_records if r.envelope.record_version_id not in registered_ids
            )
            captured_at_utc, snapshot_id, primary, exact_dup, source_rev = (
                _prove_orphan_run(registered_records, orphan_records, config)
            )
            cumulative_records = tuple(store_records)
            expected_accepted_ids, expected_batch_hash = _validate_cumulative(
                cumulative_records, store_ids
            )
        except _IncrementalReject as reject:
            return _result(
                is_valid=False,
                status="INCREMENTAL_REJECTED",
                error_codes=(reject.code,),
            )

        (
            ok,
            registration_status,
            dataset_reference_id,
            manifest_entry_id,
            registration_error_codes,
        ) = _safe_register(
            manifest_store_path,
            cumulative_records,
            config,
            effective_time=captured_at_utc,
            expected_accepted_ids=expected_accepted_ids,
            expected_batch_hash=expected_batch_hash,
        )
        counts = dict(
            prior_registered_record_count=len(registered_ids),
            new_record_count=len(orphan_records),
            cumulative_record_count=len(store_records),
            primary_assertion_count=primary,
            exact_duplicate_count=exact_dup,
            source_revision_count=source_rev,
            snapshot_id=snapshot_id,
            captured_at_utc=captured_at_utc,
            record_store_status="RECORD_STORE_LOADED_VERIFIED",
        )
        if not ok:
            return _result(
                is_valid=False,
                status="INCREMENTAL_REJECTED",
                error_codes=("INCREMENTAL_REGISTRATION_FAILED",),
                registration_error_codes=registration_error_codes,
                network_used=False,
                recovery_required=True,
                **counts,
            )

        status = (
            "INCREMENTAL_RECOVERED_REGISTRATION"
            if registration_status == "ADAPTER_PERSISTED"
            else "INCREMENTAL_ALREADY_REGISTERED"
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
            status="INCREMENTAL_REJECTED",
            error_codes=("INCREMENTAL_UNEXPECTED_ERROR",),
        )


def _parse_payload(canonical_payload_json: object) -> dict:
    if type(canonical_payload_json) is not str:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    try:
        payload = json.loads(canonical_payload_json)
    except Exception:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    if type(payload) is not dict:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    return payload


def _orphan_to_candidate(
    orphan: MarketObservationRecord,
    *,
    snapshot_id: str,
    ingestion_batch_id: str,
    config: PolymarketPublicPopulationConfig,
) -> MarketObservationRecord:
    """Rebuild the PRIMARY_ASSERTION candidate WP165 would have built for an orphan.

    Source-snapshot/assertion ids and (for Gamma) the event id are re-derived from
    the payload, so a forged orphan whose ids do not match its payload can never
    reconstruct into an equal final record.
    """

    payload = _parse_payload(orphan.canonical_payload_json)
    observed = orphan.envelope.observed_time
    if orphan.source_id == _GAMMA_SOURCE_ID and orphan.observation_kind == _GAMMA_KIND:
        if frozenset(payload) != _GAMMA_PAYLOAD_KEYS:
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        prefix = "market:polymarket:"
        if orphan.token_id is not None or not orphan.market_id.startswith(prefix):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        raw_gamma_id = orphan.market_id[len(prefix):]
        if not raw_gamma_id:
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
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
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        normalized = {
            "market_id": orphan.market_id,
            "event_id": orphan.event_id,
            "payload": payload,
        }
        return _call_wp164(
            _build_gamma_record,
            normalized,
            default_code="INCREMENTAL_RECOVERY_INVALID",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=observed,
            config=config,
        )
    if orphan.source_id == _CLOB_SOURCE_ID and orphan.observation_kind == _CLOB_KIND:
        if frozenset(payload) != _CLOB_PAYLOAD_KEYS:
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        prefix = "token:polymarket:"
        if orphan.token_id is None or not orphan.token_id.startswith(prefix):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        raw_token = orphan.token_id[len(prefix):]
        if not raw_token:
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        parent = {"market_id": orphan.market_id, "event_id": orphan.event_id}
        return _call_wp164(
            _build_order_book_record,
            parent,
            raw_token,
            payload,
            default_code="INCREMENTAL_RECOVERY_INVALID",
            snapshot_id=snapshot_id,
            ingestion_batch_id=ingestion_batch_id,
            captured_at_utc=observed,
            config=config,
        )
    raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")


def _prove_orphan_run(
    registered_records: tuple[MarketObservationRecord, ...],
    orphan_records: tuple[MarketObservationRecord, ...],
    config: PolymarketPublicPopulationConfig,
) -> tuple[str, str, int, int, int]:
    """Prove the orphan suffix is exactly one genuine WP165 incremental run.

    Returns ``(captured_at_utc, snapshot_id, primary, exact_duplicate,
    source_revision)``. Requires: 1..45 orphans, all supported observations sharing
    exactly one snapshot/batch/observed==ingestion time; a WP165 run identity
    recomputed from the orphan payload hashes matching that single snapshot/batch;
    and that reconstructing every orphan from the registered prior state through the
    exact WP165 lineage yields object-for-object equality.
    """

    count = len(orphan_records)
    if not (1 <= count <= _MAX_ORPHAN_RECORDS):
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")

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
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    captured_at_utc = next(iter(observed_times))
    if captured_at_utc != next(iter(ingestion_times)):
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
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

    # Prove the orphan run is a shape the config-bounded capture path could
    # actually produce: a real WP165 run fetches at most ``bounded_markets`` Gamma
    # markets (always >=1) and derives its books ONLY from the same run's Gamma
    # response via the deterministic ``_select_tokens`` selection.
    bounded_markets, bounded_books = _bounded_limits_wp165(config)
    gamma_count = len(gamma_orphans)
    clob_count = len(clob_orphans)
    if not (1 <= gamma_count <= bounded_markets):
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    if clob_count > bounded_books:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    if bounded_books == 0 and clob_count != 0:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")

    parsed_markets: list[tuple[str, str, dict]] = []
    market_prefix = "market:polymarket:"
    for gamma in gamma_orphans:
        payload = _parse_payload(gamma.canonical_payload_json)
        if frozenset(payload) != _GAMMA_PAYLOAD_KEYS:
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        if not gamma.market_id.startswith(market_prefix):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        raw_gamma_id = gamma.market_id[len(market_prefix):]
        raw_token_ids = payload["token_ids"]
        if type(raw_token_ids) is not list or any(
            type(token) is not str for token in raw_token_ids
        ):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
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

    # Reproduce the deterministic bounded token selection (and its same-market
    # de-duplication and cross-market-ambiguity rejection). The CLOB orphans must be
    # exactly the selected tokens, each parented to its same-run Gamma owner.
    selected_tokens, token_to_market = _call_wp164(
        _select_tokens,
        parsed_markets,
        bounded_books,
        default_code="INCREMENTAL_RECOVERY_INVALID",
    )
    token_prefix = "token:polymarket:"
    orphan_book_tokens: list[str] = []
    for book in clob_orphans:
        if book.token_id is None or not book.token_id.startswith(token_prefix):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
        orphan_book_tokens.append(book.token_id[len(token_prefix):])
    if len(orphan_book_tokens) != len(set(orphan_book_tokens)):
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    if sorted(orphan_book_tokens) != sorted(selected_tokens):
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    for book in clob_orphans:
        owner = token_to_market.get(book.token_id[len(token_prefix):])
        if (
            owner is None
            or book.market_id != owner["market_id"]
            or book.event_id != owner["event_id"]
        ):
            raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")

    # Recompute the WP165 run identity from only the orphan payload hashes in the
    # deterministic WP164 record order and require an exact match.
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
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")

    # Reconstruct the candidate for every orphan, then re-run the exact WP165
    # lineage classification against the registered prior state and require the
    # reconstructed finals to equal the stored orphans object-for-object.
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
    reconstructed, primary, exact_dup, source_rev = _classify_new_records(
        registered_records, candidates
    )
    expected = {r.envelope.record_version_id: r for r in reconstructed}
    actual = {r.envelope.record_version_id: r for r in orphan_records}
    if expected != actual:
        raise _IncrementalReject("INCREMENTAL_RECOVERY_INVALID")
    return captured_at_utc, stored_snapshot_id, primary, exact_dup, source_rev
