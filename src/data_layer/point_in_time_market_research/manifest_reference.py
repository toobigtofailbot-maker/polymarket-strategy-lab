"""Bounded in-memory manifest chain and dataset snapshot reference validator.

This module is local, offline, stdlib-only, deterministic, and in-memory. It
realizes the append-only local manifest and deterministic dataset snapshot
reference contract
(``docs/append_only_local_manifest_and_dataset_snapshot_reference_contract.md``)
as a validation and identity-derivation layer over immutable frozen objects.

It builds and validates:

1. ``DatasetSnapshotReference`` — a logical, tamper-evident reference to an
   already-valid research batch or as-of query result;
2. ``ManifestEntry`` — one append-only, hash-linked state-transition record;
3. a complete linear manifest chain over immutable entries.

It never reads or writes files, opens sockets, spawns subprocesses, touches the
environment, persists state, selects a strategy, computes an expected return, or
authorizes paper/live behavior. It has no execution authority. Review conflicts
never gain ordinary authority, and every reference and entry fixes
``advisory_only=True`` and ``no_execution_authority=True``.

Builder responsibility versus chain responsibility:

- ``build_dataset_snapshot_reference`` and ``build_manifest_entry`` validate one
  object's local structure, closed vocabularies, bounds, safety posture, and
  self-derived identity from an explicit caller mapping. They never reason about
  other entries or references.
- ``validate_manifest_chain`` re-derives and revalidates every supplied entry
  and reference, enforces the single-manifest hash-linked append chain, resolves
  each subject reference against the supplied registry, enforces the
  register/supersede/invalidate state machine, and binds human-review posture.

All results fail closed: an invalid result carries only a fixed status, an
ordered tuple of bounded closed error codes, an empty warning tuple, null object
fields, empty safe tuples, and the fixed advisory / no-execution booleans. No
raw caller value, exception text, path, or environment value is ever echoed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import re

from .as_of_query import SUPPORTED_CUTOFF_MODES, SUPPORTED_RESULT_VIEWS
from .records import canonical_json_bytes, sha256_hex


# ── Locked labels and posture (WP160) ────────────────────────────────────────

MANIFEST_REFERENCE_LABEL = (
    "APPEND_ONLY_LOCAL_MANIFEST_AND_DATASET_SNAPSHOT_REFERENCE_VALIDATION"
)
MANIFEST_REFERENCE_POSTURE = (
    "BOUNDED_LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION"
)

DATASET_REFERENCE_SCHEMA_ID = "point-in-time-dataset-snapshot-reference"
DATASET_REFERENCE_SCHEMA_VERSION = "1.0.0"
MANIFEST_ENTRY_SCHEMA_ID = "point-in-time-local-manifest-entry"
MANIFEST_ENTRY_SCHEMA_VERSION = "1.0.0"


# ── Closed vocabularies (canonically ordered) ────────────────────────────────

DATASET_DERIVATION_MODES = (
    "VALIDATED_RECORD_BATCH",
    "AS_OF_QUERY_RESULT",
)
MANIFEST_ENTRY_KINDS = (
    "REGISTER_DATASET_SNAPSHOT_REFERENCE",
    "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
    "INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
)
REFERENCE_STATES = (
    "ACTIVE_REFERENCE",
    "SUPERSEDED_REFERENCE",
    "INVALIDATED_REFERENCE",
)
MANIFEST_REASON_CODES = (
    "INITIAL_REGISTRATION",
    "SOURCE_SUPERSEDED",
    "REFERENCE_INVALIDATED",
)
MANIFEST_REFERENCE_VALIDATION_STATUSES = (
    "REFERENCE_VALID",
    "REFERENCE_REJECTED_CONTRACT",
    "REFERENCE_UNSUPPORTED_SCHEMA",
    "ENTRY_VALID",
    "ENTRY_REJECTED_CONTRACT",
    "ENTRY_UNSUPPORTED_SCHEMA",
    "CHAIN_VALID",
    "CHAIN_REJECTED",
)
MANIFEST_REFERENCE_ERROR_CODES = (
    "SCHEMA_UNSUPPORTED",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "ID_DERIVATION_MISMATCH",
    "REFERENCE_MODE_MISMATCH",
    "REVIEW_CONFLICT_AUTHORITY_FORBIDDEN",
    "MANIFEST_SEQUENCE_INVALID",
    "MANIFEST_PREVIOUS_ENTRY_UNKNOWN",
    "MANIFEST_CHAIN_MISMATCH",
    "MANIFEST_SUPERSEDES_INVALID",
    "MANIFEST_CYCLE",
    "MANIFEST_ID_COLLISION_OR_MISMATCH",
    "DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",
    "SAFETY_POSTURE_INVALID",
)

# Schema version 1.0.0 defines no warning codes; every result reports an empty
# warning tuple.
_ERROR_ORDER = {code: index for index, code in enumerate(MANIFEST_REFERENCE_ERROR_CODES)}

_DERIVATION_MODES = frozenset(DATASET_DERIVATION_MODES)
_ENTRY_KINDS = frozenset(MANIFEST_ENTRY_KINDS)
_REFERENCE_STATES = frozenset(REFERENCE_STATES)
_REASON_CODES = frozenset(MANIFEST_REASON_CODES)
_CUTOFF_MODES = frozenset(SUPPORTED_CUTOFF_MODES)
_RESULT_VIEWS = frozenset(SUPPORTED_RESULT_VIEWS)

# Per-kind consistency: kind -> (reference_state, reason_code).
_KIND_STATE = {
    "REGISTER_DATASET_SNAPSHOT_REFERENCE": "ACTIVE_REFERENCE",
    "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE": "SUPERSEDED_REFERENCE",
    "INVALIDATE_DATASET_SNAPSHOT_REFERENCE": "INVALIDATED_REFERENCE",
}
_KIND_REASON = {
    "REGISTER_DATASET_SNAPSHOT_REFERENCE": "INITIAL_REGISTRATION",
    "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE": "SOURCE_SUPERSEDED",
    "INVALIDATE_DATASET_SNAPSHOT_REFERENCE": "REFERENCE_INVALIDATED",
}


# ── Bounds (WP160 Section 11) ─────────────────────────────────────────────────

_MAX_STR = 256
_MAX_RECORD_IDS = 256
_MAX_ENTRIES = 256
_MAX_REFERENCES = 256

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECORD_VERSION_ID_RE = re.compile(r"^record:sha256:[0-9a-f]{64}$")
_DATASET_REFERENCE_ID_RE = re.compile(r"^datasetref:sha256:[0-9a-f]{64}$")
_MANIFEST_ENTRY_ID_RE = re.compile(r"^manifestentry:sha256:[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?P<fraction>\.[0-9]{1,})?(?P<zone>Z|\+00:00)$"
)

_DATASET_REFERENCE_ID_PREFIX = "datasetref:sha256:"
_MANIFEST_ENTRY_ID_PREFIX = "manifestentry:sha256:"

_QUERY_FIELDS = (
    "query_spec_sha256",
    "query_result_sha256",
    "cutoff_mode",
    "cutoff_time",
    "result_view",
    "query_engine_version",
)

_REFERENCE_FIELDS = (
    "schema_id",
    "schema_version",
    "dataset_snapshot_reference_id",
    "derivation_mode",
    "validated_batch_sha256",
    "ordinary_record_version_ids",
    "review_conflict_record_version_ids",
    "query_spec_sha256",
    "query_result_sha256",
    "cutoff_mode",
    "cutoff_time",
    "result_view",
    "query_engine_version",
    "validator_version",
    "parameter_set_id",
    "created_from_manifest_entry_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)
_REFERENCE_FIELD_SET = frozenset(_REFERENCE_FIELDS)

_ENTRY_FIELDS = (
    "schema_id",
    "schema_version",
    "manifest_entry_id",
    "manifest_id",
    "sequence_number",
    "previous_manifest_entry_id",
    "entry_kind",
    "dataset_snapshot_reference_id",
    "supersedes_manifest_entry_id",
    "reference_state",
    "reason_code",
    "effective_time",
    "parameter_set_id",
    "human_review_required",
    "advisory_only",
    "no_execution_authority",
)
_ENTRY_FIELD_SET = frozenset(_ENTRY_FIELDS)


# ── Immutable public dataclasses ─────────────────────────────────────────────


@dataclass(frozen=True)
class DatasetSnapshotReference:
    schema_id: str
    schema_version: str
    dataset_snapshot_reference_id: str
    derivation_mode: str
    validated_batch_sha256: str
    ordinary_record_version_ids: tuple[str, ...]
    review_conflict_record_version_ids: tuple[str, ...]
    query_spec_sha256: str | None
    query_result_sha256: str | None
    cutoff_mode: str | None
    cutoff_time: str | None
    result_view: str | None
    query_engine_version: str | None
    validator_version: str
    parameter_set_id: str
    created_from_manifest_entry_id: None
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class ManifestEntry:
    schema_id: str
    schema_version: str
    manifest_entry_id: str
    manifest_id: str
    sequence_number: int
    previous_manifest_entry_id: str | None
    entry_kind: str
    dataset_snapshot_reference_id: str
    supersedes_manifest_entry_id: str | None
    reference_state: str
    reason_code: str
    effective_time: str
    parameter_set_id: str
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class DatasetSnapshotReferenceBuildResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    reference: DatasetSnapshotReference | None


@dataclass(frozen=True)
class ManifestEntryBuildResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    entry: ManifestEntry | None


@dataclass(frozen=True)
class ManifestChainValidationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    manifest_id: str | None
    ordered_entry_ids: tuple[str, ...]
    head_manifest_entry_id: str | None
    active_reference_ids: tuple[str, ...]
    superseded_reference_ids: tuple[str, ...]
    invalidated_reference_ids: tuple[str, ...]
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


# ── Deterministic helpers ────────────────────────────────────────────────────


def _ordered(codes: Sequence[str]) -> tuple[str, ...]:
    """Return unique codes in the locked precedence order (first-seen tie-break)."""

    first: dict[str, int] = {}
    for occurrence, code in enumerate(codes):
        first.setdefault(code, occurrence)
    return tuple(
        sorted(first, key=lambda code: (_ERROR_ORDER.get(code, len(_ERROR_ORDER)), first[code]))
    )


def _check_vocabulary(
    value: object, vocabulary: frozenset[str], errors: list[str]
) -> bool:
    """Type-gate a caller closed-vocabulary value before any set membership.

    A non-string value is ``FIELD_TYPE_INVALID`` and a string outside the
    closed vocabulary is ``FIELD_VALUE_INVALID``. Membership is only tested once
    the value is proven to be a hashable string, so an unhashable ``list``/
    ``dict`` can never raise ``TypeError`` from a frozenset membership test.
    """

    if not isinstance(value, str):
        errors.append("FIELD_TYPE_INVALID")
        return False
    if value not in vocabulary:
        errors.append("FIELD_VALUE_INVALID")
        return False
    return True


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _bounded_str(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= _MAX_STR


def _valid_opaque_id(value: object) -> bool:
    return (
        _bounded_str(value)
        and value == value.strip()  # type: ignore[union-attr]
        and _OPAQUE_ID_RE.fullmatch(value) is not None  # type: ignore[arg-type]
    )


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _valid_record_version_id(value: object) -> bool:
    return isinstance(value, str) and _RECORD_VERSION_ID_RE.fullmatch(value) is not None


def _valid_dataset_reference_id(value: object) -> bool:
    return isinstance(value, str) and _DATASET_REFERENCE_ID_RE.fullmatch(value) is not None


def _valid_manifest_entry_id(value: object) -> bool:
    return isinstance(value, str) and _MANIFEST_ENTRY_ID_RE.fullmatch(value) is not None


def _valid_utc(value: object) -> bool:
    if not isinstance(value, str):
        return False
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        return False
    fraction = match.group("fraction")
    if fraction is not None and len(fraction) - 1 > 6:
        return False
    canonical = value[:-6] + "Z" if value.endswith("+00:00") else value
    try:
        datetime.fromisoformat(canonical.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _digest(prefix: str, preimage: Mapping[str, object]) -> str | None:
    """Return the locked-prefixed SHA-256 identity, or ``None`` if unencodable.

    All values reaching this helper are already validated, so the bounded
    canonical encoder should never raise; the guard keeps the layer fail-closed.
    """

    try:
        return prefix + sha256_hex(canonical_json_bytes(preimage))
    except (ValueError, TypeError):
        return None


# ── Result constructors ──────────────────────────────────────────────────────


def _rejected_reference(codes: Sequence[str]) -> DatasetSnapshotReferenceBuildResult:
    ordered = _ordered(codes)
    status = (
        "REFERENCE_UNSUPPORTED_SCHEMA"
        if "SCHEMA_UNSUPPORTED" in ordered
        else "REFERENCE_REJECTED_CONTRACT"
    )
    return DatasetSnapshotReferenceBuildResult(
        is_valid=False,
        status=status,
        error_codes=ordered,
        warning_codes=(),
        reference=None,
    )


def _rejected_entry(codes: Sequence[str]) -> ManifestEntryBuildResult:
    ordered = _ordered(codes)
    status = (
        "ENTRY_UNSUPPORTED_SCHEMA"
        if "SCHEMA_UNSUPPORTED" in ordered
        else "ENTRY_REJECTED_CONTRACT"
    )
    return ManifestEntryBuildResult(
        is_valid=False,
        status=status,
        error_codes=ordered,
        warning_codes=(),
        entry=None,
    )


def _rejected_chain(codes: Sequence[str]) -> ManifestChainValidationResult:
    return ManifestChainValidationResult(
        is_valid=False,
        status="CHAIN_REJECTED",
        error_codes=_ordered(codes),
        warning_codes=(),
        manifest_id=None,
        ordered_entry_ids=(),
        head_manifest_entry_id=None,
        active_reference_ids=(),
        superseded_reference_ids=(),
        invalidated_reference_ids=(),
        human_review_required=True,
        advisory_only=True,
        no_execution_authority=True,
    )


# ── Dataset snapshot reference builder (WP160 Section 12) ─────────────────────


def build_dataset_snapshot_reference(
    input_mapping: object,
) -> DatasetSnapshotReferenceBuildResult:
    """Build one immutable dataset snapshot reference or fail closed.

    Validates local structure, closed vocabularies, bounds, mode-conditional
    query fields, record-version tuples, reserved-null backlink, safety posture,
    and the recomputed self identity from an explicit caller mapping. The
    caller-provided ``dataset_snapshot_reference_id`` is never trusted; it is
    recomputed from the canonical preimage and compared.
    """

    if not isinstance(input_mapping, Mapping):
        return _rejected_reference(("FIELD_TYPE_INVALID",))

    keys = set(input_mapping.keys())
    structural: list[str] = []
    if keys - _REFERENCE_FIELD_SET:
        structural.append("FIELD_VALUE_INVALID")
    if _REFERENCE_FIELD_SET - keys:
        structural.append("FIELD_MISSING")
    if structural:
        return _rejected_reference(structural)

    # Schema takes precedence over all field-value checks.
    if (
        input_mapping["schema_id"] != DATASET_REFERENCE_SCHEMA_ID
        or input_mapping["schema_version"] != DATASET_REFERENCE_SCHEMA_VERSION
    ):
        return _rejected_reference(("SCHEMA_UNSUPPORTED",))

    errors: list[str] = []

    derivation_mode = input_mapping["derivation_mode"]
    _check_vocabulary(derivation_mode, _DERIVATION_MODES, errors)

    validated_batch_sha256 = input_mapping["validated_batch_sha256"]
    if not _valid_sha256(validated_batch_sha256):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(validated_batch_sha256, str)
            else "FIELD_VALUE_INVALID"
        )

    ordinary_raw = input_mapping["ordinary_record_version_ids"]
    review_raw = input_mapping["review_conflict_record_version_ids"]
    ordinary = _validate_record_id_tuple(ordinary_raw, errors)
    review = _validate_record_id_tuple(review_raw, errors)
    if ordinary is not None and review is not None:
        if len(ordinary) + len(review) > _MAX_RECORD_IDS:
            errors.append("FIELD_VALUE_INVALID")
        overlap = set(ordinary) & set(review)
        if overlap:
            errors.append("REVIEW_CONFLICT_AUTHORITY_FORBIDDEN")
        else:
            if len(set(ordinary)) != len(ordinary) or len(set(review)) != len(review):
                errors.append("FIELD_VALUE_INVALID")

    validator_version = input_mapping["validator_version"]
    if not _bounded_str(validator_version):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(validator_version, str)
            else "FIELD_VALUE_INVALID"
        )

    parameter_set_id = input_mapping["parameter_set_id"]
    if not _valid_opaque_id(parameter_set_id):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(parameter_set_id, str)
            else "FIELD_VALUE_INVALID"
        )

    # Reserved backlink: present and null in schema 1.0.0.
    if input_mapping["created_from_manifest_entry_id"] is not None:
        errors.append("FIELD_VALUE_INVALID")

    _validate_reference_mode(input_mapping, derivation_mode, errors)

    # Derived human-review posture and fixed safety flags.
    human_review = input_mapping["human_review_required"]
    derived_review = bool(review) if review is not None else None
    if not _is_bool(human_review):
        errors.append("FIELD_TYPE_INVALID")
    elif derived_review is not None and human_review is not derived_review:
        errors.append("FIELD_VALUE_INVALID")

    if input_mapping["advisory_only"] is not True or (
        input_mapping["no_execution_authority"] is not True
    ):
        errors.append("SAFETY_POSTURE_INVALID")

    if errors:
        return _rejected_reference(errors)

    ordinary_tuple = tuple(ordinary)  # type: ignore[arg-type]
    review_tuple = tuple(review)  # type: ignore[arg-type]
    canonical_review = bool(review_tuple)

    preimage = {
        "schema_id": DATASET_REFERENCE_SCHEMA_ID,
        "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
        "derivation_mode": derivation_mode,
        "validated_batch_sha256": validated_batch_sha256,
        "ordinary_record_version_ids": list(ordinary_tuple),
        "review_conflict_record_version_ids": list(review_tuple),
        "query_spec_sha256": input_mapping["query_spec_sha256"],
        "query_result_sha256": input_mapping["query_result_sha256"],
        "cutoff_mode": input_mapping["cutoff_mode"],
        "cutoff_time": input_mapping["cutoff_time"],
        "result_view": input_mapping["result_view"],
        "query_engine_version": input_mapping["query_engine_version"],
        "validator_version": validator_version,
        "parameter_set_id": parameter_set_id,
        "human_review_required": canonical_review,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    reference_id = _digest(_DATASET_REFERENCE_ID_PREFIX, preimage)
    if reference_id is None:
        return _rejected_reference(("FIELD_VALUE_INVALID",))
    if input_mapping["dataset_snapshot_reference_id"] != reference_id:
        return _rejected_reference(("ID_DERIVATION_MISMATCH",))

    reference = DatasetSnapshotReference(
        schema_id=DATASET_REFERENCE_SCHEMA_ID,
        schema_version=DATASET_REFERENCE_SCHEMA_VERSION,
        dataset_snapshot_reference_id=reference_id,
        derivation_mode=str(derivation_mode),
        validated_batch_sha256=str(validated_batch_sha256),
        ordinary_record_version_ids=ordinary_tuple,
        review_conflict_record_version_ids=review_tuple,
        query_spec_sha256=input_mapping["query_spec_sha256"],
        query_result_sha256=input_mapping["query_result_sha256"],
        cutoff_mode=input_mapping["cutoff_mode"],
        cutoff_time=input_mapping["cutoff_time"],
        result_view=input_mapping["result_view"],
        query_engine_version=input_mapping["query_engine_version"],
        validator_version=str(validator_version),
        parameter_set_id=str(parameter_set_id),
        created_from_manifest_entry_id=None,
        human_review_required=canonical_review,
        advisory_only=True,
        no_execution_authority=True,
    )
    return DatasetSnapshotReferenceBuildResult(
        is_valid=True,
        status="REFERENCE_VALID",
        error_codes=(),
        warning_codes=(),
        reference=reference,
    )


def _validate_record_id_tuple(value: object, errors: list[str]) -> list[str] | None:
    """Validate a record-version ID sequence into an ordered list, or ``None``."""

    if not isinstance(value, (list, tuple)):
        errors.append("FIELD_TYPE_INVALID")
        return None
    if len(value) > _MAX_RECORD_IDS:
        errors.append("FIELD_VALUE_INVALID")
    out: list[str] = []
    shape_ok = True
    for item in value:
        if not isinstance(item, str):
            errors.append("FIELD_TYPE_INVALID")
            shape_ok = False
        elif not _valid_record_version_id(item):
            errors.append("FIELD_VALUE_INVALID")
            shape_ok = False
        else:
            out.append(item)
    if not shape_ok:
        return None
    return out


def _validate_reference_mode(
    input_mapping: Mapping[str, object], derivation_mode: object, errors: list[str]
) -> None:
    """Enforce the mode-conditional query-field null/non-null combination."""

    if not isinstance(derivation_mode, str) or derivation_mode not in _DERIVATION_MODES:
        return
    query_values = {field: input_mapping[field] for field in _QUERY_FIELDS}
    if derivation_mode == "VALIDATED_RECORD_BATCH":
        if any(value is not None for value in query_values.values()):
            errors.append("REFERENCE_MODE_MISMATCH")
        return
    # AS_OF_QUERY_RESULT: all six query fields present and non-null.
    if any(value is None for value in query_values.values()):
        errors.append("REFERENCE_MODE_MISMATCH")
        return
    if not _valid_sha256(query_values["query_spec_sha256"]):
        errors.append("FIELD_VALUE_INVALID")
    if not _valid_sha256(query_values["query_result_sha256"]):
        errors.append("FIELD_VALUE_INVALID")
    _check_vocabulary(query_values["cutoff_mode"], _CUTOFF_MODES, errors)
    _check_vocabulary(query_values["result_view"], _RESULT_VIEWS, errors)
    if not _valid_utc(query_values["cutoff_time"]):
        errors.append("FIELD_VALUE_INVALID")
    if not _bounded_str(query_values["query_engine_version"]):
        errors.append("FIELD_VALUE_INVALID")


# ── Manifest entry builder (WP160 Section 13) ────────────────────────────────


def build_manifest_entry(input_mapping: object) -> ManifestEntryBuildResult:
    """Build one immutable manifest entry or fail closed.

    Validates one entry's local structure, closed vocabularies, bounds,
    per-kind field consistency, sequence/previous nullness, safety posture, and
    the recomputed self identity. Cross-entry semantics (link resolution,
    subject state, human-review binding) belong only to ``validate_manifest_chain``.
    """

    if not isinstance(input_mapping, Mapping):
        return _rejected_entry(("FIELD_TYPE_INVALID",))

    keys = set(input_mapping.keys())
    structural: list[str] = []
    if keys - _ENTRY_FIELD_SET:
        structural.append("FIELD_VALUE_INVALID")
    if _ENTRY_FIELD_SET - keys:
        structural.append("FIELD_MISSING")
    if structural:
        return _rejected_entry(structural)

    if (
        input_mapping["schema_id"] != MANIFEST_ENTRY_SCHEMA_ID
        or input_mapping["schema_version"] != MANIFEST_ENTRY_SCHEMA_VERSION
    ):
        return _rejected_entry(("SCHEMA_UNSUPPORTED",))

    errors: list[str] = []

    manifest_id = input_mapping["manifest_id"]
    if not _valid_opaque_id(manifest_id):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(manifest_id, str)
            else "FIELD_VALUE_INVALID"
        )

    sequence_number = input_mapping["sequence_number"]
    seq_ok = (
        isinstance(sequence_number, int)
        and not isinstance(sequence_number, bool)
        and 0 <= sequence_number < _MAX_ENTRIES
    )
    if not seq_ok:
        errors.append("MANIFEST_SEQUENCE_INVALID")

    previous = input_mapping["previous_manifest_entry_id"]
    if previous is not None and not _valid_manifest_entry_id(previous):
        errors.append(
            "FIELD_TYPE_INVALID" if not isinstance(previous, str) else "FIELD_VALUE_INVALID"
        )
    elif seq_ok:
        if sequence_number == 0 and previous is not None:
            errors.append("MANIFEST_SEQUENCE_INVALID")
        if sequence_number > 0 and previous is None:
            errors.append("MANIFEST_SEQUENCE_INVALID")

    entry_kind = input_mapping["entry_kind"]
    entry_kind_ok = _check_vocabulary(entry_kind, _ENTRY_KINDS, errors)

    dataset_reference_id = input_mapping["dataset_snapshot_reference_id"]
    if not _valid_dataset_reference_id(dataset_reference_id):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(dataset_reference_id, str)
            else "FIELD_VALUE_INVALID"
        )

    supersedes = input_mapping["supersedes_manifest_entry_id"]
    _validate_supersedes_shape(entry_kind, supersedes, errors)

    reference_state = input_mapping["reference_state"]
    if not _check_vocabulary(reference_state, _REFERENCE_STATES, errors):
        pass
    elif entry_kind_ok and reference_state != _KIND_STATE[entry_kind]:
        errors.append("FIELD_VALUE_INVALID")

    reason_code = input_mapping["reason_code"]
    if not _check_vocabulary(reason_code, _REASON_CODES, errors):
        pass
    elif entry_kind_ok and reason_code != _KIND_REASON[entry_kind]:
        errors.append("FIELD_VALUE_INVALID")

    effective_time = input_mapping["effective_time"]
    if not _valid_utc(effective_time):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(effective_time, str)
            else "FIELD_VALUE_INVALID"
        )

    parameter_set_id = input_mapping["parameter_set_id"]
    if not _valid_opaque_id(parameter_set_id):
        errors.append(
            "FIELD_TYPE_INVALID"
            if not isinstance(parameter_set_id, str)
            else "FIELD_VALUE_INVALID"
        )

    human_review = input_mapping["human_review_required"]
    if not _is_bool(human_review):
        errors.append("FIELD_TYPE_INVALID")
    elif entry_kind == "INVALIDATE_DATASET_SNAPSHOT_REFERENCE" and human_review is not True:
        errors.append("FIELD_VALUE_INVALID")

    if input_mapping["advisory_only"] is not True or (
        input_mapping["no_execution_authority"] is not True
    ):
        errors.append("SAFETY_POSTURE_INVALID")

    if errors:
        return _rejected_entry(errors)

    preimage = {
        "schema_id": MANIFEST_ENTRY_SCHEMA_ID,
        "schema_version": MANIFEST_ENTRY_SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "sequence_number": sequence_number,
        "previous_manifest_entry_id": previous,
        "entry_kind": entry_kind,
        "dataset_snapshot_reference_id": dataset_reference_id,
        "supersedes_manifest_entry_id": supersedes,
        "reference_state": reference_state,
        "reason_code": reason_code,
        "effective_time": effective_time,
        "parameter_set_id": parameter_set_id,
        "human_review_required": human_review,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    entry_id = _digest(_MANIFEST_ENTRY_ID_PREFIX, preimage)
    if entry_id is None:
        return _rejected_entry(("FIELD_VALUE_INVALID",))
    if input_mapping["manifest_entry_id"] != entry_id:
        return _rejected_entry(("ID_DERIVATION_MISMATCH",))

    entry = ManifestEntry(
        schema_id=MANIFEST_ENTRY_SCHEMA_ID,
        schema_version=MANIFEST_ENTRY_SCHEMA_VERSION,
        manifest_entry_id=entry_id,
        manifest_id=str(manifest_id),
        sequence_number=int(sequence_number),
        previous_manifest_entry_id=previous,
        entry_kind=str(entry_kind),
        dataset_snapshot_reference_id=str(dataset_reference_id),
        supersedes_manifest_entry_id=supersedes,
        reference_state=str(reference_state),
        reason_code=str(reason_code),
        effective_time=str(effective_time),
        parameter_set_id=str(parameter_set_id),
        human_review_required=bool(human_review),
        advisory_only=True,
        no_execution_authority=True,
    )
    return ManifestEntryBuildResult(
        is_valid=True,
        status="ENTRY_VALID",
        error_codes=(),
        warning_codes=(),
        entry=entry,
    )


def _validate_supersedes_shape(
    entry_kind: object, supersedes: object, errors: list[str]
) -> None:
    """Enforce per-kind supersedes nullness / shape (local structure only)."""

    # Tuple membership compares with ``==`` (never hashes ``entry_kind``), so an
    # unhashable caller value can never raise ``TypeError`` here.
    if entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE":
        if supersedes is not None:
            errors.append("MANIFEST_SUPERSEDES_INVALID")
    elif entry_kind in (
        "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE",
        "INVALIDATE_DATASET_SNAPSHOT_REFERENCE",
    ):
        if supersedes is None or not _valid_manifest_entry_id(supersedes):
            errors.append("MANIFEST_SUPERSEDES_INVALID")
    # Unknown kind: the entry_kind vocabulary error is reported separately.


# ── Complete manifest chain validator (WP160 Section 14) ─────────────────────


def validate_manifest_chain(
    entries: Sequence[ManifestEntry],
    *,
    dataset_references: Sequence[DatasetSnapshotReference],
) -> ManifestChainValidationResult:
    """Validate a complete linear manifest chain over immutable objects.

    Re-derives and revalidates every supplied entry and reference, enforces the
    single-manifest hash-linked append chain, resolves each subject reference
    against the supplied registry, applies the register/supersede/invalidate
    state machine, and binds human-review posture. Neither input sequence nor
    any supplied object is mutated, and no raw caller data is returned.
    """

    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        return _rejected_chain(("FIELD_TYPE_INVALID",))
    if isinstance(dataset_references, (str, bytes)) or not isinstance(
        dataset_references, Sequence
    ):
        return _rejected_chain(("FIELD_TYPE_INVALID",))

    entry_tuple = tuple(entries)
    reference_tuple = tuple(dataset_references)

    if len(entry_tuple) > _MAX_ENTRIES:
        return _rejected_chain(("MANIFEST_SEQUENCE_INVALID",))
    if len(reference_tuple) > _MAX_REFERENCES:
        return _rejected_chain(("DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH",))
    if not entry_tuple:
        return _rejected_chain(("MANIFEST_SEQUENCE_INVALID",))

    if any(not isinstance(entry, ManifestEntry) for entry in entry_tuple):
        return _rejected_chain(("FIELD_TYPE_INVALID",))
    if any(
        not isinstance(reference, DatasetSnapshotReference)
        for reference in reference_tuple
    ):
        return _rejected_chain(("FIELD_TYPE_INVALID",))

    errors: list[str] = []

    # Dataset reference registry: recompute-and-revalidate; unique identities.
    registry: dict[str, DatasetSnapshotReference] = {}
    for reference in reference_tuple:
        if not _reference_is_self_consistent(reference):
            errors.append("DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH")
            continue
        if reference.dataset_snapshot_reference_id in registry:
            errors.append("DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH")
            continue
        registry[reference.dataset_snapshot_reference_id] = reference

    # Entry integrity: recompute-and-revalidate; unique identities/sequences.
    id_to_index: dict[str, int] = {}
    seen_sequences: set[int] = set()
    for index, entry in enumerate(entry_tuple):
        if not _entry_is_self_consistent(entry):
            errors.append("MANIFEST_ID_COLLISION_OR_MISMATCH")
            continue
        if entry.manifest_entry_id in id_to_index:
            errors.append("MANIFEST_ID_COLLISION_OR_MISMATCH")
        else:
            id_to_index[entry.manifest_entry_id] = index
        if entry.sequence_number in seen_sequences:
            errors.append("MANIFEST_SEQUENCE_INVALID")
        else:
            seen_sequences.add(entry.sequence_number)

    # Integrity boundary: reject before any cross-entry set/dict/state-machine
    # operation once a non-self-consistent reference or entry is present. Every
    # object surviving to this point rebuilt identically through the public
    # builders, so all its fields are normalized, correctly typed, and hashable;
    # a malformed direct dataclass (e.g. an unhashable field value) can never
    # reach — and therefore never raise from — the operations below.
    if errors:
        return _rejected_chain(errors)

    # One manifest per chain.
    manifest_ids = {entry.manifest_id for entry in entry_tuple}
    if len(manifest_ids) != 1:
        errors.append("MANIFEST_CHAIN_MISMATCH")

    # Input order is authoritative: sequence values must equal 0..len-1.
    for index, entry in enumerate(entry_tuple):
        if entry.sequence_number != index:
            errors.append("MANIFEST_SEQUENCE_INVALID")
            break

    # Hash-linked previous-ID resolution.
    used_previous: set[str] = set()
    for index, entry in enumerate(entry_tuple):
        previous = entry.previous_manifest_entry_id
        if index == 0:
            if previous is not None:
                errors.append("MANIFEST_SEQUENCE_INVALID")
            continue
        if previous is None:
            errors.append("MANIFEST_SEQUENCE_INVALID")
            continue
        if previous == entry.manifest_entry_id:
            errors.append("MANIFEST_CYCLE")
            continue
        if previous not in id_to_index:
            errors.append("MANIFEST_PREVIOUS_ENTRY_UNKNOWN")
            continue
        target_index = id_to_index[previous]
        if target_index >= index:
            errors.append("MANIFEST_CYCLE")
            continue
        if previous in used_previous:
            errors.append("MANIFEST_CYCLE")
            continue
        used_previous.add(previous)
        if entry_tuple[target_index].manifest_id != entry.manifest_id:
            errors.append("MANIFEST_CHAIN_MISMATCH")
        elif target_index != index - 1:
            errors.append("MANIFEST_CHAIN_MISMATCH")

    # Subject registry existence and the register/supersede/invalidate machine.
    _validate_subject_state(entry_tuple, registry, id_to_index, errors)

    if errors:
        return _rejected_chain(errors)

    return _valid_chain_result(entry_tuple, registry)


def _validate_subject_state(
    entry_tuple: tuple[ManifestEntry, ...],
    registry: Mapping[str, DatasetSnapshotReference],
    id_to_index: Mapping[str, int],
    errors: list[str],
) -> None:
    """Apply subject-existence, transition, and human-review-binding rules."""

    # subject id -> current state; and the currently-effective entry id.
    state: dict[str, str] = {}
    effective_entry: dict[str, str] = {}
    for index, entry in enumerate(entry_tuple):
        subject = entry.dataset_snapshot_reference_id
        if subject not in registry:
            errors.append("DATASET_REFERENCE_ID_COLLISION_OR_MISMATCH")
        reference = registry.get(subject)

        if entry.entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE":
            if subject in state:
                # Duplicate registration or reactivation of a known subject.
                errors.append("MANIFEST_SUPERSEDES_INVALID")
            else:
                state[subject] = "ACTIVE_REFERENCE"
                effective_entry[subject] = entry.manifest_entry_id
            if reference is not None and (
                entry.human_review_required is not reference.human_review_required
            ):
                errors.append("FIELD_VALUE_INVALID")
            continue

        # SUPERSEDE / INVALIDATE transitions.
        target = entry.supersedes_manifest_entry_id
        target_index = id_to_index.get(target) if isinstance(target, str) else None
        if (
            target is None
            or target_index is None
            or target_index >= index
            or entry_tuple[target_index].dataset_snapshot_reference_id != subject
            or subject not in state
            or state.get(subject) != "ACTIVE_REFERENCE"
            or effective_entry.get(subject) != target
        ):
            errors.append("MANIFEST_SUPERSEDES_INVALID")
        else:
            state[subject] = _KIND_STATE[entry.entry_kind]
            effective_entry[subject] = entry.manifest_entry_id

        if entry.entry_kind == "SUPERSEDE_DATASET_SNAPSHOT_REFERENCE":
            if reference is not None and (
                entry.human_review_required is not reference.human_review_required
            ):
                errors.append("FIELD_VALUE_INVALID")


def _valid_chain_result(
    entry_tuple: tuple[ManifestEntry, ...],
    registry: Mapping[str, DatasetSnapshotReference],
) -> ManifestChainValidationResult:
    """Assemble the bounded valid chain result in first-registration order."""

    manifest_id = entry_tuple[0].manifest_id
    ordered_entry_ids = tuple(entry.manifest_entry_id for entry in entry_tuple)
    head = ordered_entry_ids[-1]

    # Final subject state in first-registration order.
    registration_order: list[str] = []
    final_state: dict[str, str] = {}
    for entry in entry_tuple:
        subject = entry.dataset_snapshot_reference_id
        if entry.entry_kind == "REGISTER_DATASET_SNAPSHOT_REFERENCE":
            registration_order.append(subject)
            final_state[subject] = "ACTIVE_REFERENCE"
        else:
            final_state[subject] = _KIND_STATE[entry.entry_kind]

    active = tuple(
        subject for subject in registration_order
        if final_state[subject] == "ACTIVE_REFERENCE"
    )
    superseded = tuple(
        subject for subject in registration_order
        if final_state[subject] == "SUPERSEDED_REFERENCE"
    )
    invalidated = tuple(
        subject for subject in registration_order
        if final_state[subject] == "INVALIDATED_REFERENCE"
    )

    # Review posture aggregates every valid supplied registry reference (whether
    # or not a manifest entry references it) and every manifest entry.
    human_review = any(
        entry.human_review_required for entry in entry_tuple
    ) or any(
        reference.human_review_required for reference in registry.values()
    )

    return ManifestChainValidationResult(
        is_valid=True,
        status="CHAIN_VALID",
        error_codes=(),
        warning_codes=(),
        manifest_id=manifest_id,
        ordered_entry_ids=ordered_entry_ids,
        head_manifest_entry_id=head,
        active_reference_ids=active,
        superseded_reference_ids=superseded,
        invalidated_reference_ids=invalidated,
        human_review_required=bool(human_review),
        advisory_only=True,
        no_execution_authority=True,
    )


def _reference_is_self_consistent(reference: DatasetSnapshotReference) -> bool:
    """Return whether a reference rebuilds identically through the public builder."""

    result = build_dataset_snapshot_reference(_reference_to_mapping(reference))
    return result.is_valid and result.reference == reference


def _entry_is_self_consistent(entry: ManifestEntry) -> bool:
    """Return whether an entry rebuilds identically through the public builder."""

    result = build_manifest_entry(_entry_to_mapping(entry))
    return result.is_valid and result.entry == entry


def _reference_to_mapping(reference: DatasetSnapshotReference) -> dict[str, object]:
    return {
        "schema_id": reference.schema_id,
        "schema_version": reference.schema_version,
        "dataset_snapshot_reference_id": reference.dataset_snapshot_reference_id,
        "derivation_mode": reference.derivation_mode,
        "validated_batch_sha256": reference.validated_batch_sha256,
        "ordinary_record_version_ids": list(reference.ordinary_record_version_ids),
        "review_conflict_record_version_ids": list(
            reference.review_conflict_record_version_ids
        ),
        "query_spec_sha256": reference.query_spec_sha256,
        "query_result_sha256": reference.query_result_sha256,
        "cutoff_mode": reference.cutoff_mode,
        "cutoff_time": reference.cutoff_time,
        "result_view": reference.result_view,
        "query_engine_version": reference.query_engine_version,
        "validator_version": reference.validator_version,
        "parameter_set_id": reference.parameter_set_id,
        "created_from_manifest_entry_id": reference.created_from_manifest_entry_id,
        "human_review_required": reference.human_review_required,
        "advisory_only": reference.advisory_only,
        "no_execution_authority": reference.no_execution_authority,
    }


def _entry_to_mapping(entry: ManifestEntry) -> dict[str, object]:
    return {
        "schema_id": entry.schema_id,
        "schema_version": entry.schema_version,
        "manifest_entry_id": entry.manifest_entry_id,
        "manifest_id": entry.manifest_id,
        "sequence_number": entry.sequence_number,
        "previous_manifest_entry_id": entry.previous_manifest_entry_id,
        "entry_kind": entry.entry_kind,
        "dataset_snapshot_reference_id": entry.dataset_snapshot_reference_id,
        "supersedes_manifest_entry_id": entry.supersedes_manifest_entry_id,
        "reference_state": entry.reference_state,
        "reason_code": entry.reason_code,
        "effective_time": entry.effective_time,
        "parameter_set_id": entry.parameter_set_id,
        "human_review_required": entry.human_review_required,
        "advisory_only": entry.advisory_only,
        "no_execution_authority": entry.no_execution_authority,
    }
