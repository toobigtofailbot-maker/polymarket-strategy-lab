"""Bounded deterministic WP156/WP157 → WP160 → WP161 dataset persistence handoff.

This module is local, offline, stdlib-only, deterministic, and import-safe. It
bridges the already-merged point-in-time research layers into one durable
dataset-lineage handoff:

1. a WP156 validated record batch, or
2. a WP157 as-of query result,

is re-computed from the caller's records/spec, projected into a WP160
``DatasetSnapshotReference``, registered as a WP160 ``REGISTER`` ``ManifestEntry``
at the verified append-chain head, and persisted transactionally through the
WP161 SQLite manifest store.

It never trusts a caller-supplied batch result, query result, dataset reference,
manifest entry, sequence number, previous-entry ID, or store snapshot: the
authoritative upstream computation is always re-run from the caller's records or
spec. It talks to persistence ONLY through the WP161 public functions.

It never imports SQLite, opens a socket, spawns a subprocess, touches the
environment, reads a clock, discovers a path, issues SQL, initializes or migrates
a store, persists raw record payloads, selects a strategy, computes an expected
return, or authorizes paper/live behavior. It has no execution authority. Every
result fixes ``advisory_only=True`` and ``no_execution_authority=True``.

All results fail closed: a rejected result carries only a fixed status, an
ordered tuple of bounded closed adapter error codes, closed upstream/store error
codes, an empty warning tuple, null object fields, ``human_review_required=False``,
and the fixed safety booleans. No caller record, spec, path, payload, object
repr, exception text, filesystem detail, SQL, or environment value is ever
echoed. Only ordinary ``Exception`` is ever contained; ``BaseException`` escapes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .as_of_query import PointInTimeQuerySpec, query_point_in_time_record_set
from .manifest_reference import (
    DATASET_REFERENCE_SCHEMA_ID,
    DATASET_REFERENCE_SCHEMA_VERSION,
    DATASET_REFERENCE_SCHEMA_VERSION_LINEAGE,
    MANIFEST_ENTRY_SCHEMA_ID,
    MANIFEST_ENTRY_SCHEMA_VERSION,
    DatasetSnapshotReference,
    ManifestEntry,
    build_dataset_snapshot_reference,
    build_manifest_entry,
)
from .manifest_store import append_manifest_store_batch, load_and_verify_manifest_store
from .records import (
    MarketObservationRecord,
    PointInTimeEnvelope,
    ResolutionRuleSnapshotRecord,
    SourceSnapshotRecord,
    canonical_json_bytes,
    sha256_hex,
    validate_record_batch,
)


# ── Locked labels, posture, statuses, and error precedence (WP162) ───────────

DATASET_PERSISTENCE_ADAPTER_LABEL = (
    "POINT_IN_TIME_RESEARCH_DATASET_PERSISTENCE_ADAPTER"
)
DATASET_PERSISTENCE_ADAPTER_POSTURE = (
    "BOUNDED_DETERMINISTIC_WP156_WP157_TO_WP160_WP161_HANDOFF"
)

DATASET_PERSISTENCE_ADAPTER_STATUSES = (
    "ADAPTER_PERSISTED",
    "ADAPTER_ALREADY_PERSISTED",
    "ADAPTER_REJECTED",
)

DATASET_PERSISTENCE_ADAPTER_ERROR_CODES = (
    "ADAPTER_INPUT_INVALID",
    "ADAPTER_BATCH_INVALID",
    "ADAPTER_QUERY_INVALID",
    "ADAPTER_PARAMETER_SET_MISMATCH",
    "ADAPTER_VALIDATOR_VERSION_MISMATCH",
    "ADAPTER_REFERENCE_BUILD_FAILED",
    "ADAPTER_STORE_LOAD_FAILED",
    "ADAPTER_MANIFEST_ID_MISMATCH",
    "ADAPTER_REGISTRATION_CONFLICT",
    "ADAPTER_STORE_STATE_INVALID",
    "ADAPTER_ENTRY_BUILD_FAILED",
    "ADAPTER_STORE_APPEND_FAILED",
    # WP166 lineage-delta external-parent-context adapter codes.
    "ADAPTER_PARENT_CONTEXT_INVALID",
    "ADAPTER_PARENT_CONTEXT_UNREGISTERED",
    "ADAPTER_PARENT_CONTEXT_HEAD_CHANGED",
)

# Schema 1 defines no adapter warning codes; ``warning_codes`` is always empty.
_ERROR_ORDER = {
    code: index for index, code in enumerate(DATASET_PERSISTENCE_ADAPTER_ERROR_CODES)
}

_RECORD_TYPES = (
    MarketObservationRecord,
    SourceSnapshotRecord,
    ResolutionRuleSnapshotRecord,
)

_MAX_SCALAR = 256

_DATASET_REFERENCE_ID_PREFIX = "datasetref:sha256:"
_MANIFEST_ENTRY_ID_PREFIX = "manifestentry:sha256:"

_REGISTER_KIND = "REGISTER_DATASET_SNAPSHOT_REFERENCE"


# ── Public immutable result ──────────────────────────────────────────────────


@dataclass(frozen=True)
class DatasetPersistenceAdapterResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    upstream_error_codes: tuple[str, ...]
    store_error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    dataset_reference: DatasetSnapshotReference | None
    manifest_entry: ManifestEntry | None
    store_status: str | None
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


# ── Result constructors ──────────────────────────────────────────────────────


def _order(codes: tuple[str, ...]) -> tuple[str, ...]:
    """Return unique adapter codes in the locked precedence order."""

    return tuple(sorted(set(codes), key=lambda code: _ERROR_ORDER.get(code, len(_ERROR_ORDER))))


def _rejected(
    codes: tuple[str, ...],
    *,
    upstream: tuple[str, ...] = (),
    store: tuple[str, ...] = (),
) -> DatasetPersistenceAdapterResult:
    """Return one bounded, echo-free rejected adapter result."""

    return DatasetPersistenceAdapterResult(
        is_valid=False,
        status="ADAPTER_REJECTED",
        error_codes=_order(codes),
        upstream_error_codes=tuple(upstream),
        store_error_codes=tuple(store),
        warning_codes=(),
        dataset_reference=None,
        manifest_entry=None,
        store_status=None,
        human_review_required=False,
        advisory_only=True,
        no_execution_authority=True,
    )


def _persisted(
    status: str,
    reference: DatasetSnapshotReference,
    entry: ManifestEntry,
    store_status: str,
) -> DatasetPersistenceAdapterResult:
    """Return the valid success result for a persisted or already-persisted subject."""

    return DatasetPersistenceAdapterResult(
        is_valid=True,
        status=status,
        error_codes=(),
        upstream_error_codes=(),
        store_error_codes=(),
        warning_codes=(),
        dataset_reference=reference,
        manifest_entry=entry,
        store_status=store_status,
        human_review_required=reference.human_review_required,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Bounded hostile-runtime-object input boundary ────────────────────────────


def _copy_records(records: object) -> tuple[object, ...] | None:
    """Accept only an exact built-in ``list``/``tuple`` and copy to a tuple.

    List/tuple subclasses, strings, bytes, mappings, sets, generators, iterators,
    arbitrary iterables, and ``None`` are rejected without being iterated, so a
    hostile subclass or single-use iterator is never consumed.
    """

    if type(records) not in (list, tuple):
        return None
    return tuple(records)


def _records_are_bounded(records_tuple: tuple[object, ...]) -> bool:
    """Require each element to be an exact WP156 record with an exact envelope.

    This is only the hostile-runtime-object boundary; it does not weaken or
    replace the authoritative WP156/WP157 validation that runs afterward.
    """

    for record in records_tuple:
        if type(record) not in _RECORD_TYPES:
            return False
        envelope = getattr(record, "envelope", None)
        if type(envelope) is not PointInTimeEnvelope:
            return False
        if (
            type(envelope.record_version_id) is not str
            or type(envelope.validator_version) is not str
            or type(envelope.parameter_set_id) is not str
        ):
            return False
    return True


def _valid_scalar(value: object) -> bool:
    """Bounded exact-``str`` primitive check (WP160 owns the full grammar)."""

    return (
        type(value) is str
        and 0 < len(value) <= _MAX_SCALAR
        and value == value.strip()
    )


# ── Local deterministic identity derivation (WP160 is the final authority) ────


def _reference_id(preimage: dict[str, object]) -> str:
    return _DATASET_REFERENCE_ID_PREFIX + sha256_hex(canonical_json_bytes(preimage))


def _entry_id(preimage: dict[str, object]) -> str:
    return _MANIFEST_ENTRY_ID_PREFIX + sha256_hex(canonical_json_bytes(preimage))


def _build_reference(
    *,
    derivation_mode: str,
    validated_batch_sha256: str,
    ordinary_ids: tuple[str, ...],
    review_ids: tuple[str, ...],
    query_spec_sha256: str | None,
    query_result_sha256: str | None,
    cutoff_mode: str | None,
    cutoff_time: str | None,
    result_view: str | None,
    query_engine_version: str | None,
    validator_version: str,
    parameter_set_id: str,
) -> DatasetSnapshotReference | None:
    """Derive the WP160 reference preimage/identity and rebuild through WP160.

    The preimage is exactly the WP158/WP160 identity mapping (excluding the
    reference ID and the reserved null backlink). The recomputed identity is
    handed to the public builder, which remains the sole authority.
    """

    try:
        human_review_required = bool(review_ids)
        preimage: dict[str, object] = {
            "schema_id": DATASET_REFERENCE_SCHEMA_ID,
            "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
            "derivation_mode": derivation_mode,
            "validated_batch_sha256": validated_batch_sha256,
            "ordinary_record_version_ids": list(ordinary_ids),
            "review_conflict_record_version_ids": list(review_ids),
            "query_spec_sha256": query_spec_sha256,
            "query_result_sha256": query_result_sha256,
            "cutoff_mode": cutoff_mode,
            "cutoff_time": cutoff_time,
            "result_view": result_view,
            "query_engine_version": query_engine_version,
            "validator_version": validator_version,
            "parameter_set_id": parameter_set_id,
            "human_review_required": human_review_required,
            "advisory_only": True,
            "no_execution_authority": True,
        }
        reference_id = _reference_id(preimage)
        mapping = dict(preimage)
        mapping["dataset_snapshot_reference_id"] = reference_id
        mapping["created_from_manifest_entry_id"] = None
        result = build_dataset_snapshot_reference(mapping)
    except Exception:
        return None
    if not result.is_valid or result.reference is None:
        return None
    if result.reference.dataset_snapshot_reference_id != reference_id:
        return None
    return result.reference


def _build_register_entry(
    *,
    manifest_id: str,
    sequence_number: int,
    previous_manifest_entry_id: str | None,
    dataset_snapshot_reference_id: str,
    effective_time: str,
    parameter_set_id: str,
    human_review_required: bool,
) -> ManifestEntry | None:
    """Derive the WP160 REGISTER-entry preimage/identity and rebuild through WP160."""

    try:
        preimage: dict[str, object] = {
            "schema_id": MANIFEST_ENTRY_SCHEMA_ID,
            "schema_version": MANIFEST_ENTRY_SCHEMA_VERSION,
            "manifest_id": manifest_id,
            "sequence_number": sequence_number,
            "previous_manifest_entry_id": previous_manifest_entry_id,
            "entry_kind": _REGISTER_KIND,
            "dataset_snapshot_reference_id": dataset_snapshot_reference_id,
            "supersedes_manifest_entry_id": None,
            "reference_state": "ACTIVE_REFERENCE",
            "reason_code": "INITIAL_REGISTRATION",
            "effective_time": effective_time,
            "parameter_set_id": parameter_set_id,
            "human_review_required": human_review_required,
            "advisory_only": True,
            "no_execution_authority": True,
        }
        entry_id = _entry_id(preimage)
        mapping = dict(preimage)
        mapping["manifest_entry_id"] = entry_id
        result = build_manifest_entry(mapping)
    except Exception:
        return None
    if not result.is_valid or result.entry is None:
        return None
    if result.entry.manifest_entry_id != entry_id:
        return None
    return result.entry


# ── Verified-store registration handoff (shared by both adapters) ─────────────


def _register_reference(
    path: object,
    reference: DatasetSnapshotReference,
    *,
    manifest_id: str,
    effective_time: str,
    expected_created_from: str | None = None,
) -> DatasetPersistenceAdapterResult:
    """Register one already-built reference at the verified append-chain head.

    The store must already exist and verify; this adapter never initializes,
    repairs, or migrates a store. Sequence/previous-head are derived from the
    verified snapshot, never accepted from the caller.

    When ``expected_created_from`` is supplied (a WP166 v2 lineage-delta
    registration whose reference identity binds the prior head), the head the new
    entry will link to must equal it exactly; a head change between the coordinator's
    pre-read and this append fails closed with ``ADAPTER_PARENT_CONTEXT_HEAD_CHANGED``
    rather than silently retargeting the backlink.
    """

    try:
        loaded = load_and_verify_manifest_store(path)
    except Exception:
        return _rejected(("ADAPTER_STORE_LOAD_FAILED",))
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        return _rejected(
            ("ADAPTER_STORE_LOAD_FAILED",), store=tuple(loaded.error_codes)
        )

    snapshot = loaded.snapshot
    entries = snapshot.manifest_entries
    references = snapshot.dataset_references

    # Manifest-ID rule: genesis adopts the caller ID; an existing chain must
    # match exactly. A conflicting caller ID is never inferred or replaced.
    if entries and manifest_id != entries[0].manifest_id:
        return _rejected(("ADAPTER_MANIFEST_ID_MISMATCH",))

    subject_id = reference.dataset_snapshot_reference_id
    existing_reference = next(
        (
            candidate
            for candidate in references
            if candidate.dataset_snapshot_reference_id == subject_id
        ),
        None,
    )
    if existing_reference is not None:
        if existing_reference != reference:
            return _rejected(("ADAPTER_STORE_STATE_INVALID",))
        register_entries = [
            entry
            for entry in entries
            if entry.dataset_snapshot_reference_id == subject_id
            and entry.entry_kind == _REGISTER_KIND
        ]
        if len(register_entries) > 1:
            return _rejected(("ADAPTER_STORE_STATE_INVALID",))
        if len(register_entries) == 1:
            entry = register_entries[0]
            if (
                entry.manifest_id == manifest_id
                and entry.parameter_set_id == reference.parameter_set_id
                and entry.human_review_required == reference.human_review_required
                and entry.effective_time == effective_time
            ):
                return _persisted(
                    "ADAPTER_ALREADY_PERSISTED",
                    existing_reference,
                    entry,
                    "STORE_LOADED_VERIFIED",
                )
            return _rejected(("ADAPTER_REGISTRATION_CONFLICT",))
        # Reference persisted but not registered: register it now (below).

    if entries:
        sequence_number = len(entries)
        previous_manifest_entry_id: str | None = entries[-1].manifest_entry_id
    else:
        sequence_number = 0
        previous_manifest_entry_id = None

    # WP166: fail closed if the head moved since the reference's backlink was
    # fixed. This runs only after the idempotent already-persisted short-circuit.
    if (
        expected_created_from is not None
        and previous_manifest_entry_id != expected_created_from
    ):
        return _rejected(("ADAPTER_PARENT_CONTEXT_HEAD_CHANGED",))

    entry = _build_register_entry(
        manifest_id=manifest_id,
        sequence_number=sequence_number,
        previous_manifest_entry_id=previous_manifest_entry_id,
        dataset_snapshot_reference_id=subject_id,
        effective_time=effective_time,
        parameter_set_id=reference.parameter_set_id,
        human_review_required=reference.human_review_required,
    )
    if entry is None:
        return _rejected(("ADAPTER_ENTRY_BUILD_FAILED",))

    try:
        appended = append_manifest_store_batch(
            path,
            dataset_references=(reference,),
            manifest_entries=(entry,),
        )
    except Exception:
        return _rejected(("ADAPTER_STORE_APPEND_FAILED",))
    if (
        not appended.is_valid
        or appended.status not in ("STORE_APPEND_COMMITTED", "STORE_APPEND_IDEMPOTENT")
        or appended.snapshot is None
    ):
        return _rejected(
            ("ADAPTER_STORE_APPEND_FAILED",), store=tuple(appended.error_codes)
        )

    final = appended.snapshot
    if reference not in final.dataset_references or entry not in final.manifest_entries:
        return _rejected(("ADAPTER_STORE_APPEND_FAILED",))
    if final.chain_validation is None or not final.chain_validation.is_valid:
        return _rejected(("ADAPTER_STORE_APPEND_FAILED",))

    return _persisted("ADAPTER_PERSISTED", reference, entry, appended.status)


# ── Public adapter: WP156 validated record batch → registration ──────────────


def persist_validated_record_batch_snapshot(
    path: object,
    records: object,
    *,
    manifest_id: object,
    effective_time: object,
    parameter_set_id: object,
    validator_version: object,
) -> DatasetPersistenceAdapterResult:
    """Persist a WP156 validated record batch as a registered dataset reference."""

    records_tuple = _copy_records(records)
    if records_tuple is None or not _records_are_bounded(records_tuple):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if not (
        _valid_scalar(manifest_id)
        and _valid_scalar(effective_time)
        and _valid_scalar(parameter_set_id)
        and _valid_scalar(validator_version)
    ):
        return _rejected(("ADAPTER_INPUT_INVALID",))

    try:
        batch = validate_record_batch(records_tuple)
    except Exception:
        return _rejected(("ADAPTER_BATCH_INVALID",))
    if batch.is_valid is not True:
        return _rejected(
            ("ADAPTER_BATCH_INVALID",), upstream=tuple(batch.error_codes)
        )
    if not batch.accepted_record_version_ids:
        return _rejected(("ADAPTER_BATCH_INVALID",))

    for record in records_tuple:
        if record.envelope.parameter_set_id != parameter_set_id:
            return _rejected(("ADAPTER_PARAMETER_SET_MISMATCH",))
    for record in records_tuple:
        if record.envelope.validator_version != validator_version:
            return _rejected(("ADAPTER_VALIDATOR_VERSION_MISMATCH",))

    reference = _build_reference(
        derivation_mode="VALIDATED_RECORD_BATCH",
        validated_batch_sha256=batch.canonical_batch_sha256,
        ordinary_ids=tuple(batch.accepted_record_version_ids),
        review_ids=(),
        query_spec_sha256=None,
        query_result_sha256=None,
        cutoff_mode=None,
        cutoff_time=None,
        result_view=None,
        query_engine_version=None,
        validator_version=validator_version,
        parameter_set_id=parameter_set_id,
    )
    if reference is None:
        return _rejected(("ADAPTER_REFERENCE_BUILD_FAILED",))

    return _register_reference(
        path, reference, manifest_id=manifest_id, effective_time=effective_time
    )


# ── Public adapter: WP157 as-of query result → registration ──────────────────


def persist_as_of_query_snapshot(
    path: object,
    records: object,
    spec: object,
    *,
    manifest_id: object,
    effective_time: object,
    validator_version: object,
) -> DatasetPersistenceAdapterResult:
    """Persist a WP157 as-of query result as a registered dataset reference."""

    records_tuple = _copy_records(records)
    if records_tuple is None or not _records_are_bounded(records_tuple):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if not (
        _valid_scalar(manifest_id)
        and _valid_scalar(effective_time)
        and _valid_scalar(validator_version)
    ):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if type(spec) is not PointInTimeQuerySpec:
        return _rejected(("ADAPTER_INPUT_INVALID",))

    try:
        result = query_point_in_time_record_set(records_tuple, spec)
    except Exception:
        return _rejected(("ADAPTER_QUERY_INVALID",))
    if result.is_valid is not True:
        return _rejected(
            ("ADAPTER_QUERY_INVALID",), upstream=tuple(result.error_codes)
        )
    receipt = result.receipt
    if receipt is None:
        return _rejected(("ADAPTER_QUERY_INVALID",))
    if receipt.advisory_only is not True or receipt.no_execution_authority is not True:
        return _rejected(("ADAPTER_QUERY_INVALID",))

    parameter_set_id = receipt.parameter_set_id
    if receipt.parameter_set_id != spec.parameter_set_id:
        return _rejected(("ADAPTER_PARAMETER_SET_MISMATCH",))
    for record in records_tuple:
        if record.envelope.parameter_set_id != parameter_set_id:
            return _rejected(("ADAPTER_PARAMETER_SET_MISMATCH",))
    for record in records_tuple:
        if record.envelope.validator_version != validator_version:
            return _rejected(("ADAPTER_VALIDATOR_VERSION_MISMATCH",))

    view = receipt.result_view
    if view == "AUTHORITATIVE_CURRENT_STATE":
        ordinary_ids = tuple(receipt.authoritative_record_version_ids)
    elif view in ("VISIBLE_HISTORY", "ENTITY_TIMELINE"):
        # ENTITY_TIMELINE history is the complete ordinary timeline view; the
        # authoritative terminal tuple is a subset and must not be duplicated
        # in the single WP158 ordinary-ID tuple.
        ordinary_ids = tuple(receipt.history_record_version_ids)
    else:
        return _rejected(("ADAPTER_QUERY_INVALID",))

    reference = _build_reference(
        derivation_mode="AS_OF_QUERY_RESULT",
        validated_batch_sha256=receipt.validated_batch_sha256,
        ordinary_ids=ordinary_ids,
        review_ids=tuple(receipt.review_conflict_record_version_ids),
        query_spec_sha256=receipt.query_spec_sha256,
        query_result_sha256=receipt.result_sha256,
        cutoff_mode=receipt.cutoff_mode,
        cutoff_time=receipt.cutoff_time,
        result_view=receipt.result_view,
        query_engine_version=receipt.query_engine_version,
        validator_version=validator_version,
        parameter_set_id=parameter_set_id,
    )
    if reference is None:
        return _rejected(("ADAPTER_REFERENCE_BUILD_FAILED",))

    return _register_reference(
        path, reference, manifest_id=manifest_id, effective_time=effective_time
    )


# ── WP166 lineage-delta reference (v2) identity derivation ────────────────────


def _build_lineage_delta_reference(
    *,
    validated_batch_sha256: str,
    ordinary_ids: tuple[str, ...],
    external_parent_ids: tuple[str, ...],
    created_from_manifest_entry_id: str,
    validator_version: str,
    parameter_set_id: str,
) -> DatasetSnapshotReference | None:
    """Derive the WP160 v2 lineage-delta reference preimage/identity and rebuild.

    The preimage is the schema-2.0.0 identity mapping including the sorted external
    direct-parent set and the prior-head backlink. The recomputed identity is handed
    to the public builder, which remains the sole authority.
    """

    try:
        preimage: dict[str, object] = {
            "schema_id": DATASET_REFERENCE_SCHEMA_ID,
            "schema_version": DATASET_REFERENCE_SCHEMA_VERSION_LINEAGE,
            "derivation_mode": "LINEAGE_DELTA_RECORD_BATCH",
            "validated_batch_sha256": validated_batch_sha256,
            "ordinary_record_version_ids": list(ordinary_ids),
            "review_conflict_record_version_ids": [],
            "query_spec_sha256": None,
            "query_result_sha256": None,
            "cutoff_mode": None,
            "cutoff_time": None,
            "result_view": None,
            "query_engine_version": None,
            "validator_version": validator_version,
            "parameter_set_id": parameter_set_id,
            "human_review_required": False,
            "advisory_only": True,
            "no_execution_authority": True,
            "external_parent_record_version_ids": list(external_parent_ids),
            "created_from_manifest_entry_id": created_from_manifest_entry_id,
        }
        reference_id = _reference_id(preimage)
        mapping = dict(preimage)
        mapping["dataset_snapshot_reference_id"] = reference_id
        result = build_dataset_snapshot_reference(mapping)
    except Exception:
        return None
    if not result.is_valid or result.reference is None:
        return None
    if result.reference.dataset_snapshot_reference_id != reference_id:
        return None
    return result.reference


# ── Public adapter: WP166 lineage-delta current-record batch → registration ───


def persist_lineage_delta_record_batch_snapshot(
    path: object,
    records: object,
    parent_records: object,
    *,
    manifest_id: object,
    effective_time: object,
    parameter_set_id: object,
    validator_version: object,
) -> DatasetPersistenceAdapterResult:
    """Persist ONLY the current records as a v2 lineage-delta dataset reference.

    The current records' direct external lineage parents are supplied as actual
    immutable record objects. The supplied parent id set must be exactly the set of
    current lineage-parent ids not present among the current records, every supplied
    parent must already be authorized by an earlier registered reference in the
    verified chain, and the current records are validated against the actual parent
    objects. Only the current records are registered as the v2 reference's ordinary
    ids; the external direct parents and the prior manifest head are bound into its
    identity. A nonempty valid existing chain is required, and a head change between
    pre-read and append fails closed. Behavior of the WP156/WP157 adapters is
    unchanged.
    """

    current_tuple = _copy_records(records)
    if current_tuple is None or not _records_are_bounded(current_tuple):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    parent_tuple = _copy_records(parent_records)
    if parent_tuple is None or not _records_are_bounded(parent_tuple):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if not (1 <= len(current_tuple) <= _MAX_SCALAR):
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if len(parent_tuple) > _MAX_SCALAR:
        return _rejected(("ADAPTER_INPUT_INVALID",))
    if not (
        _valid_scalar(manifest_id)
        and _valid_scalar(effective_time)
        and _valid_scalar(parameter_set_id)
        and _valid_scalar(validator_version)
    ):
        return _rejected(("ADAPTER_INPUT_INVALID",))

    # Provenance binds BOTH the current records and the actual parent records.
    for record in current_tuple + parent_tuple:
        if record.envelope.parameter_set_id != parameter_set_id:
            return _rejected(("ADAPTER_PARAMETER_SET_MISMATCH",))
    for record in current_tuple + parent_tuple:
        if record.envelope.validator_version != validator_version:
            return _rejected(("ADAPTER_VALIDATOR_VERSION_MISMATCH",))

    # Current ids must be unique among themselves; the required external parents
    # are exactly the current lineage-parent ids that are not current records.
    current_ids = tuple(record.envelope.record_version_id for record in current_tuple)
    current_id_set = set(current_ids)
    if len(current_id_set) != len(current_ids):
        return _rejected(("ADAPTER_BATCH_INVALID",))
    required_external: set[str] = set()
    for record in current_tuple:
        for parent_id in record.envelope.lineage_parent_ids:
            if parent_id not in current_id_set:
                required_external.add(parent_id)
    supplied_ids = [record.envelope.record_version_id for record in parent_tuple]
    supplied_set = set(supplied_ids)
    if len(supplied_set) != len(supplied_ids):
        return _rejected(("ADAPTER_PARENT_CONTEXT_INVALID",))
    if supplied_set != required_external:
        # A missing or unused-extra parent object.
        return _rejected(("ADAPTER_PARENT_CONTEXT_INVALID",))

    # Load and fully verify the existing (nonempty) chain BEFORE any registration.
    try:
        loaded = load_and_verify_manifest_store(path)
    except Exception:
        return _rejected(("ADAPTER_STORE_LOAD_FAILED",))
    if (
        not loaded.is_valid
        or loaded.status != "STORE_LOADED_VERIFIED"
        or loaded.snapshot is None
    ):
        return _rejected(
            ("ADAPTER_STORE_LOAD_FAILED",), store=tuple(loaded.error_codes)
        )
    snapshot = loaded.snapshot
    entries = snapshot.manifest_entries
    references = snapshot.dataset_references
    if not entries:
        return _rejected(("ADAPTER_STORE_STATE_INVALID",))
    if manifest_id != entries[0].manifest_id:
        return _rejected(("ADAPTER_MANIFEST_ID_MISMATCH",))
    chain = snapshot.chain_validation
    if (
        chain is None
        or not chain.is_valid
        or chain.head_manifest_entry_id is None
    ):
        return _rejected(("ADAPTER_STORE_STATE_INVALID",))
    head = chain.head_manifest_entry_id

    # Every supplied parent must already be authorized by an earlier registered
    # reference (the union of every registered reference's ordinary ids).
    registered_union: set[str] = set()
    for reference in references:
        registered_union.update(reference.ordinary_record_version_ids)
    if not supplied_set <= registered_union:
        return _rejected(("ADAPTER_PARENT_CONTEXT_UNREGISTERED",))

    # Validate the current records against the ACTUAL direct external parents.
    try:
        batch = validate_record_batch(
            current_tuple, known_parent_records=parent_tuple
        )
    except Exception:
        return _rejected(("ADAPTER_BATCH_INVALID",))
    if batch.is_valid is not True or batch.quarantined_record_version_ids:
        return _rejected(
            ("ADAPTER_BATCH_INVALID",), upstream=tuple(batch.error_codes)
        )
    accepted = tuple(batch.accepted_record_version_ids)
    if set(accepted) != current_id_set or len(accepted) != len(current_ids):
        return _rejected(("ADAPTER_BATCH_INVALID",))

    reference = _build_lineage_delta_reference(
        validated_batch_sha256=batch.canonical_batch_sha256,
        ordinary_ids=accepted,
        external_parent_ids=tuple(sorted(supplied_set)),
        created_from_manifest_entry_id=head,
        validator_version=validator_version,
        parameter_set_id=parameter_set_id,
    )
    if reference is None:
        return _rejected(("ADAPTER_REFERENCE_BUILD_FAILED",))

    return _register_reference(
        path,
        reference,
        manifest_id=manifest_id,
        effective_time=effective_time,
        expected_created_from=head,
    )
