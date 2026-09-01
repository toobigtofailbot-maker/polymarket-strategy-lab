"""Bounded point-in-time market research record validation.

This package is local, offline, stdlib-only, deterministic, and in-memory.
It validates explicit caller mappings and has no file, network, credential,
scheduler, strategy, paper, order, risk, or execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime
import hashlib
import json
import re
from typing import Callable, TypeAlias


FOUNDATION_LABEL = "POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT"
IMPLEMENTATION_POSTURE = "LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION"
SUPPORTED_SCHEMA_ID = "point-in-time-market-research-record"
SUPPORTED_SCHEMA_VERSION = "1.0.0"

SUPPORTED_RECORD_FAMILIES = (
    "MARKET_OBSERVATION",
    "SOURCE_SNAPSHOT",
    "RESOLUTION_RULE_SNAPSHOT",
)
SUPPORTED_OBSERVATION_KINDS = (
    "MARKET_METADATA",
    "ORDER_BOOK",
    "PUBLIC_TRADE",
)
LIFECYCLE_STATES = (
    "RAW_CAPTURED",
    "NORMALIZED_ACCEPTED",
    "QUARANTINED",
    "SUPERSEDED",
    "RETRACTED_BY_SOURCE",
    "INVALIDATED_BY_CONTRACT",
)
RECORD_CLASSIFICATIONS = (
    "PRIMARY_ASSERTION",
    "EXACT_DUPLICATE",
    "SEMANTIC_DUPLICATE",
    "LATE_ARRIVAL",
    "SOURCE_REVISION",
    "PROJECT_CORRECTION",
    "SOURCE_RETRACTION",
    "CONFLICT",
)
VALIDATION_STATUSES = (
    "VALID",
    "VALID_WITH_WARNINGS",
    "QUARANTINED",
    "REJECTED_CONTRACT",
    "UNSUPPORTED_SCHEMA",
    "CONFLICT_REQUIRES_REVIEW",
)

_FAMILIES = frozenset(SUPPORTED_RECORD_FAMILIES)
_KINDS = frozenset(SUPPORTED_OBSERVATION_KINDS)
_LIFECYCLES = frozenset(LIFECYCLE_STATES)
_CLASSIFICATIONS = frozenset(RECORD_CLASSIFICATIONS)

SOURCE_TYPES = (
    "POLYMARKET_PUBLIC_API",
    "POLYMARKET_PUBLIC_DOCUMENTATION",
    "SANITIZED_SYNTHETIC_SOURCE",
)
ACCESS_CLASSIFICATIONS = ("PUBLIC", "SANITIZED_SYNTHETIC")
AMBIGUITY_LABELS = (
    "NONE_IDENTIFIED",
    "SOURCE_AMBIGUOUS",
    "TIMING_AMBIGUOUS",
    "OUTCOME_DEFINITION_AMBIGUOUS",
    "EDGE_CASE_AMBIGUOUS",
    "CONFLICTING_SOURCE_TEXT",
    "HUMAN_REVIEW_REQUIRED",
)
SOURCE_HIERARCHY_RANKS = (
    "PRIMARY_RESOLUTION_SOURCE",
    "SECONDARY_OFFICIAL_SOURCE",
    "SUPPORTING_PUBLIC_SOURCE",
    "UNRESOLVED_SOURCE_RANK",
)
HUMAN_REVIEW_STATES = (
    "NOT_REVIEWED",
    "REVIEW_REQUIRED",
    "REVIEWED_ACKNOWLEDGED",
    "REVIEWED_CONFLICT_UNRESOLVED",
)
SIDE_OBSERVED_VALUES = (
    "BUY_OBSERVED",
    "SELL_OBSERVED",
    "UNKNOWN_OBSERVED",
)

ERROR_CODES = (
    "SCHEMA_ID_MISMATCH",
    "SCHEMA_VERSION_UNSUPPORTED",
    "RECORD_FAMILY_UNSUPPORTED",
    "OBSERVATION_KIND_UNSUPPORTED",
    "UNKNOWN_FIELD",
    "REQUIRED_FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "ID_EMPTY",
    "ID_TOO_LONG",
    "ID_NOT_NAMESPACED",
    "ID_CHARACTERS_INVALID",
    "ID_DERIVATION_MISMATCH",
    "IDENTITY_CONFLICT",
    "TIMESTAMP_MISSING",
    "TIMESTAMP_FORMAT_INVALID",
    "TIMESTAMP_NOT_UTC",
    "TIMESTAMP_PRECISION_UNSUPPORTED",
    "INGESTION_BEFORE_OBSERVED",
    "EVENT_TIME_REQUIRED",
    "PAYLOAD_TYPE_UNSUPPORTED",
    "PAYLOAD_FLOAT_FORBIDDEN",
    "PAYLOAD_DEPTH_EXCEEDED",
    "PAYLOAD_NODE_LIMIT_EXCEEDED",
    "PAYLOAD_SIZE_EXCEEDED",
    "PAYLOAD_KEY_LIMIT_EXCEEDED",
    "PAYLOAD_SEQUENCE_LIMIT_EXCEEDED",
    "PAYLOAD_STRING_LIMIT_EXCEEDED",
    "SECRET_LIKE_KEY_REJECTED",
    "AUTHORITY_LIKE_KEY_REJECTED",
    "DECIMAL_STRING_INVALID",
    "SHA256_FORMAT_INVALID",
    "LINEAGE_PARENT_DUPLICATE",
    "LINEAGE_SELF_PARENT",
    "LINEAGE_PARENT_UNKNOWN",
    "LINEAGE_CYCLE",
    "SUPERSEDES_REQUIRED",
    "SUPERSEDES_NOT_IN_LINEAGE",
    "SUPERSEDES_PARENT_UNKNOWN",
    "CORRECTION_VISIBILITY_VIOLATION",
    "CLASSIFICATION_LIFECYCLE_MISMATCH",
    "EXACT_DUPLICATE_CONTENT_MISMATCH",
    "SEMANTIC_DUPLICATE_IDENTITY_MISMATCH",
    "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH",
    "CONFLICT_REQUIRES_HUMAN_REVIEW",
    "SOURCE_TYPE_UNSUPPORTED",
    "ACCESS_CLASSIFICATION_FORBIDDEN",
    "AMBIGUITY_LABEL_UNSUPPORTED",
    "SOURCE_HIERARCHY_RANK_UNSUPPORTED",
    "HUMAN_REVIEW_STATE_UNSUPPORTED",
    "RECORD_BATCH_LIMIT_EXCEEDED",
)
WARNING_CODES = (
    "EVENT_TIME_AFTER_INGESTION",
    "EVENT_TIME_MISSING_ALLOWED",
    "LATE_ARRIVAL_DECLARED",
    "SOURCE_REVISION_DECLARED",
    "PROJECT_CORRECTION_DECLARED",
    "SOURCE_RETRACTION_DECLARED",
    "SEMANTIC_DUPLICATE_DECLARED",
    "CONFLICT_DECLARED",
)
_ERROR_ORDER = {code: index for index, code in enumerate(ERROR_CODES)}
_WARNING_ORDER = {code: index for index, code in enumerate(WARNING_CODES)}

_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "secret_key",
        "private_key",
        "seed_phrase",
        "mne" + "monic",
        "passphrase",
        "auth_token",
        "access_token",
        "bearer_token",
        "authorization",
        "cookie",
        "set_cookie",
        "authenticated_headers",
    }
)
_AUTHORITY_KEYS = frozenset(
    {
        "place_" + "order",
        "cancel_" + "order",
        "submit_" + "order",
        "sign_transaction",
        "position_size",
        "expected_return",
        "trade_signal",
        "live_signal",
        "paper_order",
        "risk_override",
        "execute",
        "auto_trade",
        "auto_copy",
        "scheduler_command",
        "credential_request",
    }
)

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECORD_VERSION_ID_RE = re.compile(r"^record:sha256:[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_TIMESTAMP_RE = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]{1,})?(?P<zone>Z|\+00:00)$"
)
_ABSOLUTE_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")

_MAX_DEPTH = 8
_MAX_NODES = 1_024
_MAX_KEYS = 128
_MAX_ITEMS = 256
_MAX_STRING = 4_096
_MAX_PAYLOAD_BYTES = 65_536
_MAX_ID = 256
_MAX_BATCH = 256


@dataclass(frozen=True)
class PointInTimeEnvelope:
    schema_id: str
    schema_version: str
    record_family: str
    record_version_id: str
    observation_id: str | None
    snapshot_id: str
    source_snapshot_id: str | None
    resolution_rule_snapshot_id: str | None
    ingestion_batch_id: str
    event_time: str | None
    observed_time: str
    ingestion_time: str
    lifecycle_state: str
    classification: str
    supersedes_record_version_id: str | None
    lineage_parent_ids: tuple[str, ...]
    canonical_payload_sha256: str
    source_content_sha256: str | None
    normalizer_version: str
    validator_version: str
    parameter_set_id: str
    human_review_required: bool
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class MarketObservationRecord:
    envelope: PointInTimeEnvelope
    observation_kind: str
    platform_id: str
    event_id: str
    market_id: str
    token_id: str | None
    source_id: str
    source_assertion_id: str
    canonical_payload_json: str


@dataclass(frozen=True)
class SourceSnapshotRecord:
    envelope: PointInTimeEnvelope
    source_id: str
    source_type: str
    source_reference: str
    media_type: str
    raw_content_sha256: str
    byte_length: int
    retrieval_method: str
    retrieval_version: str
    upstream_revision: str | None
    prior_source_snapshot_id: str | None
    access_classification: str
    canonical_payload_json: str


@dataclass(frozen=True)
class ResolutionRuleSnapshotRecord:
    envelope: PointInTimeEnvelope
    platform_id: str
    event_id: str
    market_id: str
    resolution_source_id: str
    source_snapshot_id: str
    rule_content_sha256: str
    source_declared_effective_time: str | None
    ambiguity_labels: tuple[str, ...]
    source_hierarchy_rank: str
    human_review_state: str
    canonical_payload_json: str


PointInTimeRecord: TypeAlias = (
    MarketObservationRecord | SourceSnapshotRecord | ResolutionRuleSnapshotRecord
)


@dataclass(frozen=True)
class QuarantineDescriptor:
    quarantine_id: str
    schema_id: str | None
    schema_version: str | None
    record_family: str | None
    source_id: str | None
    observed_time: str | None
    ingestion_time: str | None
    input_fingerprint_sha256: str
    failure_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    operator_review_required: bool
    safe_diagnostics_only: bool


@dataclass(frozen=True)
class PointInTimeBuildResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    record: PointInTimeRecord | None
    quarantine: QuarantineDescriptor | None


@dataclass(frozen=True)
class PointInTimeBatchValidationResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    accepted_record_version_ids: tuple[str, ...]
    exact_duplicate_record_version_ids: tuple[str, ...]
    quarantined_record_version_ids: tuple[str, ...]
    canonical_batch_sha256: str


def _ordered_unique(codes: Sequence[str], order: Mapping[str, int]) -> tuple[str, ...]:
    first: dict[str, int] = {}
    for occurrence, code in enumerate(codes):
        first.setdefault(code, occurrence)
    return tuple(
        sorted(first, key=lambda code: (order.get(code, len(order)), first[code]))
    )


def _error(code: str) -> ValueError:
    return ValueError(code)


def canonical_json_bytes(value: object) -> bytes:
    """Return bounded deterministic UTF-8 JSON or raise a stable ValueError."""

    node_count = 0

    def normalize(current: object, depth: int) -> object:
        nonlocal node_count
        node_count += 1
        if node_count > _MAX_NODES:
            raise _error("PAYLOAD_NODE_LIMIT_EXCEEDED")
        if depth > _MAX_DEPTH:
            raise _error("PAYLOAD_DEPTH_EXCEEDED")
        if current is None or isinstance(current, bool):
            return current
        if isinstance(current, int):
            return current
        if isinstance(current, float):
            raise _error("PAYLOAD_FLOAT_FORBIDDEN")
        if isinstance(current, str):
            if len(current) > _MAX_STRING:
                raise _error("PAYLOAD_STRING_LIMIT_EXCEEDED")
            return current
        if isinstance(current, Mapping):
            if len(current) > _MAX_KEYS:
                raise _error("PAYLOAD_KEY_LIMIT_EXCEEDED")
            normalized_mapping: dict[str, object] = {}
            for key in sorted(current.keys(), key=lambda item: item if isinstance(item, str) else ""):
                if not isinstance(key, str):
                    raise _error("PAYLOAD_TYPE_UNSUPPORTED")
                if len(key) > _MAX_STRING:
                    raise _error("PAYLOAD_STRING_LIMIT_EXCEEDED")
                normalized_mapping[key] = normalize(current[key], depth + 1)
            return normalized_mapping
        if isinstance(current, (list, tuple)):
            if len(current) > _MAX_ITEMS:
                raise _error("PAYLOAD_SEQUENCE_LIMIT_EXCEEDED")
            return [normalize(item, depth + 1) for item in current]
        raise _error("PAYLOAD_TYPE_UNSUPPORTED")

    normalized = normalize(value, 0)
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (OverflowError, ValueError):
        raise _error("PAYLOAD_SIZE_EXCEEDED") from None
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        raise _error("PAYLOAD_SIZE_EXCEEDED")
    return encoded


def sha256_hex(data: bytes | str) -> str:
    """Return the lowercase SHA-256 digest of bytes or UTF-8 text."""

    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, bytes):
        raise TypeError("SHA256_INPUT_TYPE_INVALID")
    return hashlib.sha256(data).hexdigest()


def _make_quarantine(
    input_record: object,
    errors: Sequence[str],
    warnings: Sequence[str],
) -> QuarantineDescriptor | None:
    if not isinstance(input_record, Mapping):
        return None
    type_names: dict[str, str] = {}
    for key, value in input_record.items():
        if isinstance(key, str) and len(key) <= _MAX_STRING:
            type_names[key] = type(value).__name__
    safe = {
        "top_level_types": type_names,
    }
    try:
        fingerprint = sha256_hex(canonical_json_bytes(safe))
    except ValueError:
        fingerprint = sha256_hex(b"BOUNDED_STRUCTURAL_FINGERPRINT_UNAVAILABLE")
    ordered_errors = _ordered_unique(errors, _ERROR_ORDER)
    ordered_warnings = _ordered_unique(warnings, _WARNING_ORDER)
    quarantine_preimage = {
        "input_fingerprint_sha256": fingerprint,
        "failure_codes": ordered_errors,
        "warning_codes": ordered_warnings,
    }
    quarantine_id = "quarantine:sha256:" + sha256_hex(
        canonical_json_bytes(quarantine_preimage)
    )
    return QuarantineDescriptor(
        quarantine_id=quarantine_id,
        schema_id=None,
        schema_version=None,
        record_family=None,
        source_id=None,
        observed_time=None,
        ingestion_time=None,
        input_fingerprint_sha256=fingerprint,
        failure_codes=ordered_errors,
        warning_codes=ordered_warnings,
        operator_review_required=True,
        safe_diagnostics_only=True,
    )


def _invalid_result(
    input_record: object,
    errors: Sequence[str],
    warnings: Sequence[str] = (),
    *,
    status: str | None = None,
) -> PointInTimeBuildResult:
    ordered_errors = _ordered_unique(errors, _ERROR_ORDER)
    ordered_warnings = _ordered_unique(warnings, _WARNING_ORDER)
    if status is None:
        if any(
            code
            in {
                "SCHEMA_ID_MISMATCH",
                "SCHEMA_VERSION_UNSUPPORTED",
                "RECORD_FAMILY_UNSUPPORTED",
            }
            for code in ordered_errors
        ):
            status = "UNSUPPORTED_SCHEMA"
        elif "CONFLICT_REQUIRES_HUMAN_REVIEW" in ordered_errors:
            status = "CONFLICT_REQUIRES_REVIEW"
        elif any(
            code
            in {
                "SECRET_LIKE_KEY_REJECTED",
                "AUTHORITY_LIKE_KEY_REJECTED",
                "PAYLOAD_FLOAT_FORBIDDEN",
            }
            for code in ordered_errors
        ):
            status = "QUARANTINED"
        else:
            status = "REJECTED_CONTRACT"
    return PointInTimeBuildResult(
        is_valid=False,
        status=status,
        error_codes=ordered_errors,
        warning_codes=ordered_warnings,
        record=None,
        quarantine=_make_quarantine(input_record, ordered_errors, ordered_warnings),
    )


def _valid_result(
    record: PointInTimeRecord, warnings: Sequence[str]
) -> PointInTimeBuildResult:
    ordered = _ordered_unique(warnings, _WARNING_ORDER)
    return PointInTimeBuildResult(
        is_valid=True,
        status="VALID_WITH_WARNINGS" if ordered else "VALID",
        error_codes=(),
        warning_codes=ordered,
        record=record,
        quarantine=None,
    )


def _validate_fields(
    record: object,
    allowed: frozenset[str],
    required: frozenset[str],
) -> tuple[list[str], Mapping[str, object] | None]:
    if not isinstance(record, Mapping):
        return ["FIELD_TYPE_INVALID"], None
    errors: list[str] = []
    if any(not isinstance(key, str) or key not in allowed for key in record):
        errors.append("UNKNOWN_FIELD")
    if any(key not in record for key in required):
        errors.append("REQUIRED_FIELD_MISSING")
    return errors, record


def _validate_schema(
    record: Mapping[str, object], expected_family: str, errors: list[str]
) -> None:
    if record.get("schema_id") != SUPPORTED_SCHEMA_ID:
        errors.append("SCHEMA_ID_MISMATCH")
    if record.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_UNSUPPORTED")
    family = record.get("record_family")
    if family not in _FAMILIES or family != expected_family:
        errors.append("RECORD_FAMILY_UNSUPPORTED")


def _validate_id(
    value: object,
    errors: list[str],
    *,
    namespaced: bool = False,
    nullable: bool = False,
) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        errors.append("FIELD_TYPE_INVALID")
        return None
    if not value:
        errors.append("ID_EMPTY")
        return None
    if len(value) > _MAX_ID:
        errors.append("ID_TOO_LONG")
        return None
    if value != value.strip() or not _ID_RE.fullmatch(value):
        errors.append("ID_CHARACTERS_INVALID")
        return None
    if namespaced and ":" not in value:
        errors.append("ID_NOT_NAMESPACED")
        return None
    return value


def _validate_text(
    value: object, errors: list[str], *, nullable: bool = False
) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or len(value) > _MAX_STRING:
        errors.append("FIELD_TYPE_INVALID")
        return None
    return value


def _validate_sha(value: object, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        errors.append("SHA256_FORMAT_INVALID")
        return None
    return value


def _normalize_timestamp(
    value: object,
    errors: list[str],
    *,
    required: bool,
) -> tuple[str | None, datetime | None]:
    if value is None:
        if required:
            errors.append("TIMESTAMP_MISSING")
        return None, None
    if not isinstance(value, str):
        errors.append("TIMESTAMP_FORMAT_INVALID")
        return None, None
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        if re.search(r"[+-][0-9]{2}:[0-9]{2}$", value) and not value.endswith(
            "+00:00"
        ):
            errors.append("TIMESTAMP_NOT_UTC")
        elif re.search(r"\.[0-9]{7,}(?:Z|\+00:00)$", value):
            errors.append("TIMESTAMP_PRECISION_UNSUPPORTED")
        else:
            errors.append("TIMESTAMP_FORMAT_INVALID")
        return None, None
    fraction = match.group("fraction")
    if fraction is not None and len(fraction) - 1 > 6:
        errors.append("TIMESTAMP_PRECISION_UNSUPPORTED")
        return None, None
    canonical = value[:-6] + "Z" if value.endswith("+00:00") else value
    try:
        parsed = datetime.fromisoformat(canonical.replace("Z", "+00:00"))
    except ValueError:
        errors.append("TIMESTAMP_FORMAT_INVALID")
        return None, None
    return canonical, parsed


def _validate_times(
    record: Mapping[str, object],
    errors: list[str],
    warnings: list[str],
    *,
    event_required: bool,
) -> tuple[str | None, str | None, str | None]:
    event_time, event_dt = _normalize_timestamp(
        record.get("event_time"), errors, required=event_required
    )
    if event_required and record.get("event_time") is None:
        errors.append("EVENT_TIME_REQUIRED")
    observed_time, observed_dt = _normalize_timestamp(
        record.get("observed_time"), errors, required=True
    )
    ingestion_time, ingestion_dt = _normalize_timestamp(
        record.get("ingestion_time"), errors, required=True
    )
    if observed_dt is not None and ingestion_dt is not None:
        if ingestion_dt < observed_dt:
            errors.append("INGESTION_BEFORE_OBSERVED")
    if event_dt is not None and ingestion_dt is not None and event_dt > ingestion_dt:
        warnings.append("EVENT_TIME_AFTER_INGESTION")
    if event_time is None and not event_required and record.get("event_time") is None:
        warnings.append("EVENT_TIME_MISSING_ALLOWED")
    return event_time, observed_time, ingestion_time


def _validate_payload_tree(value: object, errors: list[str]) -> bytes | None:
    if not isinstance(value, Mapping):
        errors.append("PAYLOAD_TYPE_UNSUPPORTED")
        return None

    def scan(current: object) -> None:
        if isinstance(current, Mapping):
            for key, nested in current.items():
                if isinstance(key, str):
                    normalized = key.lower().replace("-", "_")
                    if normalized in _SECRET_KEYS:
                        errors.append("SECRET_LIKE_KEY_REJECTED")
                    if normalized in _AUTHORITY_KEYS:
                        errors.append("AUTHORITY_LIKE_KEY_REJECTED")
                scan(nested)
        elif isinstance(current, (list, tuple)):
            for nested in current:
                scan(nested)
        elif isinstance(current, str) and _ABSOLUTE_PATH_RE.match(current):
            errors.append("PAYLOAD_TYPE_UNSUPPORTED")

    scan(value)
    try:
        return canonical_json_bytes(value)
    except ValueError as exc:
        code = str(exc)
        errors.append(code if code in _ERROR_ORDER else "PAYLOAD_TYPE_UNSUPPORTED")
        return None


def _validate_decimal(value: object, errors: list[str]) -> bool:
    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value):
        errors.append("DECIMAL_STRING_INVALID")
        return False
    return True


def _validate_lineage(
    record: Mapping[str, object], errors: list[str]
) -> tuple[tuple[str, ...], str | None]:
    raw_parents = record.get("lineage_parent_ids")
    parents: list[str] = []
    if not isinstance(raw_parents, (list, tuple)):
        errors.append("FIELD_TYPE_INVALID")
    else:
        for parent in raw_parents:
            validated = _validate_id(parent, errors)
            if validated is not None:
                parents.append(validated)
    if len(set(parents)) != len(parents):
        errors.append("LINEAGE_PARENT_DUPLICATE")
    supersedes = _validate_id(
        record.get("supersedes_record_version_id"),
        errors,
        nullable=True,
    )
    classification = record.get("classification")
    if classification == "PRIMARY_ASSERTION" and supersedes is not None:
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if classification in {
        "SOURCE_REVISION",
        "PROJECT_CORRECTION",
        "SOURCE_RETRACTION",
    } and supersedes is None:
        errors.append("SUPERSEDES_REQUIRED")
    if supersedes is not None and parents.count(supersedes) != 1:
        errors.append("SUPERSEDES_NOT_IN_LINEAGE")
    return tuple(parents), supersedes


def _validate_lifecycle(
    record: Mapping[str, object],
    errors: list[str],
    warnings: list[str],
    *,
    allow_review_conflict: bool = False,
) -> None:
    lifecycle = record.get("lifecycle_state")
    classification = record.get("classification")
    human_review = record.get("human_review_required")
    if lifecycle not in _LIFECYCLES or classification not in _CLASSIFICATIONS:
        errors.append("FIELD_TYPE_INVALID")
        return
    if not isinstance(human_review, bool):
        errors.append("FIELD_TYPE_INVALID")
        return
    if lifecycle in {"QUARANTINED", "INVALIDATED_BY_CONTRACT"}:
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if classification == "SOURCE_RETRACTION" and lifecycle != "RETRACTED_BY_SOURCE":
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if classification != "SOURCE_RETRACTION" and lifecycle == "RETRACTED_BY_SOURCE":
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if classification == "CONFLICT":
        warnings.append("CONFLICT_DECLARED")
        # A conflict record always fails the standard builders and
        # validate_record_batch. Only the additive WP157 review-only handoff
        # (allow_review_conflict=True) tolerates a human-reviewed conflict as a
        # structurally valid record; it never becomes authoritative downstream.
        if human_review is not True or not allow_review_conflict:
            errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
    if lifecycle in {"QUARANTINED", "INVALIDATED_BY_CONTRACT"} and human_review is not True:
        errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
    warning_by_classification = {
        "LATE_ARRIVAL": "LATE_ARRIVAL_DECLARED",
        "SOURCE_REVISION": "SOURCE_REVISION_DECLARED",
        "PROJECT_CORRECTION": "PROJECT_CORRECTION_DECLARED",
        "SOURCE_RETRACTION": "SOURCE_RETRACTION_DECLARED",
        "SEMANTIC_DUPLICATE": "SEMANTIC_DUPLICATE_DECLARED",
    }
    if classification in warning_by_classification:
        warnings.append(warning_by_classification[classification])


_COMMON_REQUIRED = frozenset(
    {
        "schema_id",
        "schema_version",
        "record_family",
        "snapshot_id",
        "ingestion_batch_id",
        "event_time",
        "observed_time",
        "ingestion_time",
        "lifecycle_state",
        "classification",
        "lineage_parent_ids",
        "supersedes_record_version_id",
        "normalizer_version",
        "validator_version",
        "parameter_set_id",
        "human_review_required",
        "canonical_payload",
    }
)
_EXPECTED_FIELDS = frozenset(
    {
        "record_version_id",
        "canonical_payload_sha256",
    }
)


def _common_values(
    record: Mapping[str, object],
    errors: list[str],
    warnings: list[str],
    *,
    event_required: bool,
    allow_review_conflict: bool = False,
) -> dict[str, object]:
    snapshot_id = _validate_id(record.get("snapshot_id"), errors)
    ingestion_batch_id = _validate_id(record.get("ingestion_batch_id"), errors)
    normalizer_version = _validate_id(record.get("normalizer_version"), errors)
    validator_version = _validate_id(record.get("validator_version"), errors)
    parameter_set_id = _validate_id(record.get("parameter_set_id"), errors)
    event_time, observed_time, ingestion_time = _validate_times(
        record, errors, warnings, event_required=event_required
    )
    parents, supersedes = _validate_lineage(record, errors)
    _validate_lifecycle(
        record, errors, warnings, allow_review_conflict=allow_review_conflict
    )
    payload_bytes = _validate_payload_tree(record.get("canonical_payload"), errors)
    payload_hash = sha256_hex(payload_bytes) if payload_bytes is not None else None
    expected_payload_hash = record.get("canonical_payload_sha256")
    if expected_payload_hash is not None and expected_payload_hash != payload_hash:
        errors.append("ID_DERIVATION_MISMATCH")
    return {
        "snapshot_id": snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "normalizer_version": normalizer_version,
        "validator_version": validator_version,
        "parameter_set_id": parameter_set_id,
        "event_time": event_time,
        "observed_time": observed_time,
        "ingestion_time": ingestion_time,
        "parents": parents,
        "supersedes": supersedes,
        "payload_bytes": payload_bytes,
        "payload_hash": payload_hash,
    }


def _market_record_specific_metadata(
    *,
    observation_kind: object,
    platform_id: object,
    event_id: object,
    market_id: object,
    token_id: object,
    source_id: object,
    source_assertion_id: object,
) -> dict[str, object]:
    return {
        "observation_kind": observation_kind,
        "platform_id": platform_id,
        "event_id": event_id,
        "market_id": market_id,
        "token_id": token_id,
        "source_id": source_id,
        "source_assertion_id": source_assertion_id,
    }


def _source_record_specific_metadata(
    *,
    source_id: object,
    source_type: object,
    source_reference: object,
    media_type: object,
    raw_content_sha256: object,
    byte_length: object,
    retrieval_method: object,
    retrieval_version: object,
    upstream_revision: object,
    prior_source_snapshot_id: object,
    access_classification: object,
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_reference": source_reference,
        "media_type": media_type,
        "raw_content_sha256": raw_content_sha256,
        "byte_length": byte_length,
        "retrieval_method": retrieval_method,
        "retrieval_version": retrieval_version,
        "upstream_revision": upstream_revision,
        "prior_source_snapshot_id": prior_source_snapshot_id,
        "access_classification": access_classification,
    }


def _rule_record_specific_metadata(
    *,
    platform_id: object,
    event_id: object,
    market_id: object,
    resolution_source_id: object,
    source_snapshot_id: object,
    rule_content_sha256: object,
    source_declared_effective_time: object,
    ambiguity_labels: object,
    source_hierarchy_rank: object,
    human_review_state: object,
) -> dict[str, object]:
    return {
        "platform_id": platform_id,
        "event_id": event_id,
        "market_id": market_id,
        "resolution_source_id": resolution_source_id,
        "source_snapshot_id": source_snapshot_id,
        "rule_content_sha256": rule_content_sha256,
        "source_declared_effective_time": source_declared_effective_time,
        "ambiguity_labels": ambiguity_labels,
        "source_hierarchy_rank": source_hierarchy_rank,
        "human_review_state": human_review_state,
    }


def _record_specific_metadata_sha256(metadata: Mapping[str, object]) -> str:
    return sha256_hex(canonical_json_bytes(metadata))


def _record_version_preimage(
    *,
    record_family: str,
    record_specific_metadata_sha256: str,
    canonical_payload_sha256: str,
    observation_id: str | None,
    snapshot_id: str,
    source_snapshot_id: str | None,
    resolution_rule_snapshot_id: str | None,
    ingestion_batch_id: str,
    observed_time: str,
    ingestion_time: str,
    event_time: str | None,
    lineage_parent_ids: tuple[str, ...],
    supersedes_record_version_id: str | None,
    lifecycle_state: str,
    classification: str,
    normalizer_version: str,
    validator_version: str,
    parameter_set_id: str,
    source_content_sha256: str | None,
    human_review_required: bool,
    advisory_only: bool,
    no_execution_authority: bool,
) -> dict[str, object]:
    return {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": record_family,
        "record_specific_metadata_sha256": record_specific_metadata_sha256,
        "canonical_payload_sha256": canonical_payload_sha256,
        "observation_id": observation_id,
        "snapshot_id": snapshot_id,
        "source_snapshot_id": source_snapshot_id,
        "resolution_rule_snapshot_id": resolution_rule_snapshot_id,
        "ingestion_batch_id": ingestion_batch_id,
        "observed_time": observed_time,
        "ingestion_time": ingestion_time,
        "event_time": event_time,
        "lineage_parent_ids": lineage_parent_ids,
        "supersedes_record_version_id": supersedes_record_version_id,
        "lifecycle_state": lifecycle_state,
        "classification": classification,
        "normalizer_version": normalizer_version,
        "validator_version": validator_version,
        "parameter_set_id": parameter_set_id,
        "source_content_sha256": source_content_sha256,
        "human_review_required": human_review_required,
        "advisory_only": advisory_only,
        "no_execution_authority": no_execution_authority,
    }


def _make_envelope(
    record: Mapping[str, object],
    common: Mapping[str, object],
    *,
    record_family: str,
    observation_id: str | None,
    source_snapshot_id: str | None,
    resolution_rule_snapshot_id: str | None,
    source_content_sha256: str | None,
    record_specific_metadata: Mapping[str, object],
) -> PointInTimeEnvelope:
    preimage = _record_version_preimage(
        record_family=record_family,
        record_specific_metadata_sha256=_record_specific_metadata_sha256(
            record_specific_metadata
        ),
        canonical_payload_sha256=str(common["payload_hash"]),
        observation_id=observation_id,
        snapshot_id=str(common["snapshot_id"]),
        source_snapshot_id=source_snapshot_id,
        resolution_rule_snapshot_id=resolution_rule_snapshot_id,
        ingestion_batch_id=str(common["ingestion_batch_id"]),
        observed_time=str(common["observed_time"]),
        ingestion_time=str(common["ingestion_time"]),
        event_time=common["event_time"] if isinstance(common["event_time"], str) else None,
        lineage_parent_ids=common["parents"],  # type: ignore[arg-type]
        supersedes_record_version_id=(
            common["supersedes"] if isinstance(common["supersedes"], str) else None
        ),
        lifecycle_state=str(record["lifecycle_state"]),
        classification=str(record["classification"]),
        normalizer_version=str(common["normalizer_version"]),
        validator_version=str(common["validator_version"]),
        parameter_set_id=str(common["parameter_set_id"]),
        source_content_sha256=source_content_sha256,
        human_review_required=bool(record["human_review_required"]),
        advisory_only=True,
        no_execution_authority=True,
    )
    version_id = "record:sha256:" + sha256_hex(canonical_json_bytes(preimage))
    return PointInTimeEnvelope(
        schema_id=SUPPORTED_SCHEMA_ID,
        schema_version=SUPPORTED_SCHEMA_VERSION,
        record_family=record_family,
        record_version_id=version_id,
        observation_id=observation_id,
        snapshot_id=str(common["snapshot_id"]),
        source_snapshot_id=source_snapshot_id,
        resolution_rule_snapshot_id=resolution_rule_snapshot_id,
        ingestion_batch_id=str(common["ingestion_batch_id"]),
        event_time=common["event_time"] if isinstance(common["event_time"], str) else None,
        observed_time=str(common["observed_time"]),
        ingestion_time=str(common["ingestion_time"]),
        lifecycle_state=str(record["lifecycle_state"]),
        classification=str(record["classification"]),
        supersedes_record_version_id=(
            common["supersedes"] if isinstance(common["supersedes"], str) else None
        ),
        lineage_parent_ids=common["parents"],  # type: ignore[arg-type]
        canonical_payload_sha256=str(common["payload_hash"]),
        source_content_sha256=source_content_sha256,
        normalizer_version=str(common["normalizer_version"]),
        validator_version=str(common["validator_version"]),
        parameter_set_id=str(common["parameter_set_id"]),
        human_review_required=bool(record["human_review_required"]),
        advisory_only=True,
        no_execution_authority=True,
    )


def _check_expected_ids(
    record: Mapping[str, object],
    errors: list[str],
    envelope: PointInTimeEnvelope,
    family_id_name: str,
    family_id: str | None,
) -> None:
    expected_version = record.get("record_version_id")
    if expected_version is not None and expected_version != envelope.record_version_id:
        errors.append("ID_DERIVATION_MISMATCH")
    expected_family_id = record.get(family_id_name)
    if expected_family_id is not None and expected_family_id != family_id:
        errors.append("ID_DERIVATION_MISMATCH")


_MARKET_REQUIRED = _COMMON_REQUIRED | frozenset(
    {
        "observation_kind",
        "platform_id",
        "event_id",
        "market_id",
        "token_id",
        "source_id",
        "source_assertion_id",
        "source_snapshot_id",
    }
)
_MARKET_ALLOWED = _MARKET_REQUIRED | _EXPECTED_FIELDS | frozenset({"observation_id"})


def build_market_observation(
    input_record: Mapping[str, object],
) -> PointInTimeBuildResult:
    """Build one immutable validated market observation or fail closed.

    Public builders always reject ``CONFLICT`` input. Review-only conflict
    tolerance exists exclusively on the private handoff path and is never
    reachable through this signature.
    """

    return _build_market_observation(input_record)


def _build_market_observation(
    input_record: Mapping[str, object],
    *,
    allow_review_conflict: bool = False,
) -> PointInTimeBuildResult:
    """Internal market-observation builder for the review-only conflict handoff."""

    errors, record = _validate_fields(
        input_record, frozenset(_MARKET_ALLOWED), frozenset(_MARKET_REQUIRED)
    )
    if record is None:
        return _invalid_result(input_record, errors)
    warnings: list[str] = []
    _validate_schema(record, "MARKET_OBSERVATION", errors)
    kind = record.get("observation_kind")
    if kind not in _KINDS:
        errors.append("OBSERVATION_KIND_UNSUPPORTED")
    platform_id = _validate_id(record.get("platform_id"), errors, namespaced=True)
    event_id = _validate_id(record.get("event_id"), errors, namespaced=True)
    market_id = _validate_id(record.get("market_id"), errors, namespaced=True)
    source_id = _validate_id(record.get("source_id"), errors, namespaced=True)
    source_assertion_id = _validate_id(record.get("source_assertion_id"), errors)
    source_snapshot_id = _validate_id(record.get("source_snapshot_id"), errors)
    token_id = _validate_id(
        record.get("token_id"),
        errors,
        namespaced=True,
        nullable=kind == "MARKET_METADATA",
    )
    if kind in {"ORDER_BOOK", "PUBLIC_TRADE"} and record.get("token_id") is None:
        errors.append("REQUIRED_FIELD_MISSING")
    common = _common_values(
        record,
        errors,
        warnings,
        event_required=kind == "PUBLIC_TRADE",
        allow_review_conflict=allow_review_conflict,
    )
    payload = record.get("canonical_payload")
    if isinstance(payload, Mapping):
        if kind == "MARKET_METADATA":
            if any(
                key not in payload
                for key in ("question_text", "market_status", "outcome_labels")
            ):
                errors.append("REQUIRED_FIELD_MISSING")
            if not isinstance(payload.get("question_text"), str) or not isinstance(
                payload.get("market_status"), str
            ):
                errors.append("FIELD_TYPE_INVALID")
            outcomes = payload.get("outcome_labels")
            if not isinstance(outcomes, (list, tuple)) or not outcomes or any(
                not isinstance(item, str) for item in outcomes
            ):
                errors.append("FIELD_TYPE_INVALID")
        elif kind == "ORDER_BOOK":
            if any(
                key not in payload
                for key in ("bids", "asks", "tick_size", "minimum_order_size")
            ):
                errors.append("REQUIRED_FIELD_MISSING")
            _validate_decimal(payload.get("tick_size"), errors)
            _validate_decimal(payload.get("minimum_order_size"), errors)
            for side in ("bids", "asks"):
                levels = payload.get(side)
                if not isinstance(levels, (list, tuple)):
                    errors.append("FIELD_TYPE_INVALID")
                    continue
                for level in levels:
                    if not isinstance(level, Mapping) or set(level) != {"price", "size"}:
                        errors.append("FIELD_TYPE_INVALID")
                        continue
                    _validate_decimal(level.get("price"), errors)
                    _validate_decimal(level.get("size"), errors)
        elif kind == "PUBLIC_TRADE":
            if any(
                key not in payload
                for key in ("price", "size", "side_observed", "transaction_reference")
            ):
                errors.append("REQUIRED_FIELD_MISSING")
            _validate_decimal(payload.get("price"), errors)
            _validate_decimal(payload.get("size"), errors)
            if payload.get("side_observed") not in SIDE_OBSERVED_VALUES:
                errors.append("FIELD_TYPE_INVALID")
            if not isinstance(payload.get("transaction_reference"), str):
                errors.append("FIELD_TYPE_INVALID")
    if errors:
        return _invalid_result(record, errors, warnings)
    observation_preimage = {
        "schema_id": SUPPORTED_SCHEMA_ID,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "record_family": "MARKET_OBSERVATION",
        "observation_kind": kind,
        "platform_id": platform_id,
        "event_id": event_id,
        "market_id": market_id,
        "token_id": token_id,
        "source_id": source_id,
        "source_snapshot_id": source_snapshot_id,
        "source_assertion_id": source_assertion_id,
    }
    observation_id = "obs:sha256:" + sha256_hex(
        canonical_json_bytes(observation_preimage)
    )
    record_specific_metadata = _market_record_specific_metadata(
        observation_kind=kind,
        platform_id=platform_id,
        event_id=event_id,
        market_id=market_id,
        token_id=token_id,
        source_id=source_id,
        source_assertion_id=source_assertion_id,
    )
    envelope = _make_envelope(
        record,
        common,
        record_family="MARKET_OBSERVATION",
        observation_id=observation_id,
        source_snapshot_id=source_snapshot_id,
        resolution_rule_snapshot_id=None,
        source_content_sha256=None,
        record_specific_metadata=record_specific_metadata,
    )
    _check_expected_ids(record, errors, envelope, "observation_id", observation_id)
    if envelope.record_version_id in envelope.lineage_parent_ids:
        errors.append("LINEAGE_SELF_PARENT")
    if errors:
        return _invalid_result(record, errors, warnings)
    built = MarketObservationRecord(
        envelope=envelope,
        observation_kind=str(kind),
        platform_id=str(platform_id),
        event_id=str(event_id),
        market_id=str(market_id),
        token_id=token_id,
        source_id=str(source_id),
        source_assertion_id=str(source_assertion_id),
        canonical_payload_json=bytes(common["payload_bytes"]).decode("utf-8"),
    )
    return _valid_result(built, warnings)


_SOURCE_REQUIRED = _COMMON_REQUIRED | frozenset(
    {
        "source_id",
        "source_type",
        "source_reference",
        "media_type",
        "raw_content_sha256",
        "byte_length",
        "retrieval_method",
        "retrieval_version",
        "upstream_revision",
        "prior_source_snapshot_id",
        "access_classification",
    }
)
_SOURCE_ALLOWED = _SOURCE_REQUIRED | _EXPECTED_FIELDS | frozenset(
    {"source_snapshot_id"}
)


def build_source_snapshot(
    input_record: Mapping[str, object],
) -> PointInTimeBuildResult:
    """Build one immutable source snapshot metadata record or fail closed.

    Public builders always reject ``CONFLICT`` input. Review-only conflict
    tolerance exists exclusively on the private handoff path.
    """

    return _build_source_snapshot(input_record)


def _build_source_snapshot(
    input_record: Mapping[str, object],
    *,
    allow_review_conflict: bool = False,
) -> PointInTimeBuildResult:
    """Internal source-snapshot builder for the review-only conflict handoff."""

    errors, record = _validate_fields(
        input_record, frozenset(_SOURCE_ALLOWED), frozenset(_SOURCE_REQUIRED)
    )
    if record is None:
        return _invalid_result(input_record, errors)
    warnings: list[str] = []
    _validate_schema(record, "SOURCE_SNAPSHOT", errors)
    source_id = _validate_id(record.get("source_id"), errors, namespaced=True)
    source_type = record.get("source_type")
    if source_type not in SOURCE_TYPES:
        errors.append("SOURCE_TYPE_UNSUPPORTED")
    access = record.get("access_classification")
    if access not in ACCESS_CLASSIFICATIONS:
        errors.append("ACCESS_CLASSIFICATION_FORBIDDEN")
    source_reference = _validate_text(record.get("source_reference"), errors)
    if isinstance(source_reference, str) and _ABSOLUTE_PATH_RE.match(source_reference):
        errors.append("FIELD_TYPE_INVALID")
    media_type = _validate_text(record.get("media_type"), errors)
    raw_hash = _validate_sha(record.get("raw_content_sha256"), errors)
    byte_length = record.get("byte_length")
    if isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length < 0:
        errors.append("FIELD_TYPE_INVALID")
    retrieval_method = _validate_text(record.get("retrieval_method"), errors)
    retrieval_version = _validate_id(record.get("retrieval_version"), errors)
    upstream_revision = _validate_text(
        record.get("upstream_revision"), errors, nullable=True
    )
    prior_source_snapshot_id = _validate_id(
        record.get("prior_source_snapshot_id"), errors, nullable=True
    )
    common = _common_values(
        record,
        errors,
        warnings,
        event_required=False,
        allow_review_conflict=allow_review_conflict,
    )
    if record.get("lifecycle_state") != "RAW_CAPTURED" and record.get(
        "classification"
    ) == "PRIMARY_ASSERTION":
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if errors:
        return _invalid_result(record, errors, warnings)
    source_preimage = {
        "source_id": source_id,
        "observed_time": common["observed_time"],
        "raw_content_sha256": raw_hash,
        "byte_length": byte_length,
        "media_type": media_type,
    }
    source_snapshot_id = "srcsnap:sha256:" + sha256_hex(
        canonical_json_bytes(source_preimage)
    )
    record_specific_metadata = _source_record_specific_metadata(
        source_id=source_id,
        source_type=source_type,
        source_reference=source_reference,
        media_type=media_type,
        raw_content_sha256=raw_hash,
        byte_length=byte_length,
        retrieval_method=retrieval_method,
        retrieval_version=retrieval_version,
        upstream_revision=upstream_revision,
        prior_source_snapshot_id=prior_source_snapshot_id,
        access_classification=access,
    )
    envelope = _make_envelope(
        record,
        common,
        record_family="SOURCE_SNAPSHOT",
        observation_id=None,
        source_snapshot_id=source_snapshot_id,
        resolution_rule_snapshot_id=None,
        source_content_sha256=raw_hash,
        record_specific_metadata=record_specific_metadata,
    )
    _check_expected_ids(
        record, errors, envelope, "source_snapshot_id", source_snapshot_id
    )
    if envelope.record_version_id in envelope.lineage_parent_ids:
        errors.append("LINEAGE_SELF_PARENT")
    if errors:
        return _invalid_result(record, errors, warnings)
    built = SourceSnapshotRecord(
        envelope=envelope,
        source_id=str(source_id),
        source_type=str(source_type),
        source_reference=str(source_reference),
        media_type=str(media_type),
        raw_content_sha256=str(raw_hash),
        byte_length=int(byte_length),
        retrieval_method=str(retrieval_method),
        retrieval_version=str(retrieval_version),
        upstream_revision=upstream_revision,
        prior_source_snapshot_id=prior_source_snapshot_id,
        access_classification=str(access),
        canonical_payload_json=bytes(common["payload_bytes"]).decode("utf-8"),
    )
    return _valid_result(built, warnings)


_RULE_REQUIRED = _COMMON_REQUIRED | frozenset(
    {
        "platform_id",
        "event_id",
        "market_id",
        "resolution_source_id",
        "source_snapshot_id",
        "rule_content_sha256",
        "source_declared_effective_time",
        "ambiguity_labels",
        "source_hierarchy_rank",
        "human_review_state",
    }
)
_RULE_ALLOWED = _RULE_REQUIRED | _EXPECTED_FIELDS | frozenset(
    {"resolution_rule_snapshot_id"}
)


def build_resolution_rule_snapshot(
    input_record: Mapping[str, object],
) -> PointInTimeBuildResult:
    """Build one immutable resolution-rule snapshot or fail closed.

    Public builders always reject ``CONFLICT`` input. Review-only conflict
    tolerance exists exclusively on the private handoff path.
    """

    return _build_resolution_rule_snapshot(input_record)


def _build_resolution_rule_snapshot(
    input_record: Mapping[str, object],
    *,
    allow_review_conflict: bool = False,
) -> PointInTimeBuildResult:
    """Internal resolution-rule builder for the review-only conflict handoff."""

    errors, record = _validate_fields(
        input_record, frozenset(_RULE_ALLOWED), frozenset(_RULE_REQUIRED)
    )
    if record is None:
        return _invalid_result(input_record, errors)
    warnings: list[str] = []
    _validate_schema(record, "RESOLUTION_RULE_SNAPSHOT", errors)
    platform_id = _validate_id(record.get("platform_id"), errors, namespaced=True)
    event_id = _validate_id(record.get("event_id"), errors, namespaced=True)
    market_id = _validate_id(record.get("market_id"), errors, namespaced=True)
    resolution_source_id = _validate_id(
        record.get("resolution_source_id"), errors, namespaced=True
    )
    source_snapshot_id = _validate_id(record.get("source_snapshot_id"), errors)
    rule_hash = _validate_sha(record.get("rule_content_sha256"), errors)
    effective_time, _ = _normalize_timestamp(
        record.get("source_declared_effective_time"), errors, required=False
    )
    raw_labels = record.get("ambiguity_labels")
    labels: tuple[str, ...] = ()
    if not isinstance(raw_labels, (list, tuple)) or not raw_labels:
        errors.append("FIELD_TYPE_INVALID")
    else:
        labels = tuple(raw_labels) if all(isinstance(item, str) for item in raw_labels) else ()
        if not labels:
            errors.append("FIELD_TYPE_INVALID")
        if len(set(labels)) != len(labels) or any(
            item not in AMBIGUITY_LABELS for item in labels
        ):
            errors.append("AMBIGUITY_LABEL_UNSUPPORTED")
        if "NONE_IDENTIFIED" in labels and len(labels) != 1:
            errors.append("AMBIGUITY_LABEL_UNSUPPORTED")
    rank = record.get("source_hierarchy_rank")
    if rank not in SOURCE_HIERARCHY_RANKS:
        errors.append("SOURCE_HIERARCHY_RANK_UNSUPPORTED")
    review_state = record.get("human_review_state")
    if review_state not in HUMAN_REVIEW_STATES:
        errors.append("HUMAN_REVIEW_STATE_UNSUPPORTED")
    labels_are_supported = bool(labels) and all(
        item in AMBIGUITY_LABELS for item in labels
    )
    if labels_are_supported and labels != ("NONE_IDENTIFIED",) and record.get(
        "human_review_required"
    ) is not True:
        errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
    conflicting = "CONFLICTING_SOURCE_TEXT" in labels
    if conflicting and (
        record.get("classification") != "CONFLICT"
        or record.get("human_review_required") is not True
    ):
        errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
    common = _common_values(
        record,
        errors,
        warnings,
        event_required=False,
        allow_review_conflict=allow_review_conflict,
    )
    if errors:
        return _invalid_result(record, errors, warnings)
    rule_preimage = {
        "event_id": event_id,
        "market_id": market_id,
        "resolution_source_id": resolution_source_id,
        "source_snapshot_id": source_snapshot_id,
        "rule_content_sha256": rule_hash,
    }
    rule_snapshot_id = "rulesnap:sha256:" + sha256_hex(
        canonical_json_bytes(rule_preimage)
    )
    record_specific_metadata = _rule_record_specific_metadata(
        platform_id=platform_id,
        event_id=event_id,
        market_id=market_id,
        resolution_source_id=resolution_source_id,
        source_snapshot_id=source_snapshot_id,
        rule_content_sha256=rule_hash,
        source_declared_effective_time=effective_time,
        ambiguity_labels=labels,
        source_hierarchy_rank=rank,
        human_review_state=review_state,
    )
    envelope = _make_envelope(
        record,
        common,
        record_family="RESOLUTION_RULE_SNAPSHOT",
        observation_id=None,
        source_snapshot_id=source_snapshot_id,
        resolution_rule_snapshot_id=rule_snapshot_id,
        source_content_sha256=rule_hash,
        record_specific_metadata=record_specific_metadata,
    )
    _check_expected_ids(
        record,
        errors,
        envelope,
        "resolution_rule_snapshot_id",
        rule_snapshot_id,
    )
    if envelope.record_version_id in envelope.lineage_parent_ids:
        errors.append("LINEAGE_SELF_PARENT")
    if errors:
        return _invalid_result(record, errors, warnings)
    built = ResolutionRuleSnapshotRecord(
        envelope=envelope,
        platform_id=str(platform_id),
        event_id=str(event_id),
        market_id=str(market_id),
        resolution_source_id=str(resolution_source_id),
        source_snapshot_id=str(source_snapshot_id),
        rule_content_sha256=str(rule_hash),
        source_declared_effective_time=effective_time,
        ambiguity_labels=labels,
        source_hierarchy_rank=str(rank),
        human_review_state=str(review_state),
        canonical_payload_json=bytes(common["payload_bytes"]).decode("utf-8"),
    )
    return _valid_result(built, warnings)


def _entity_identity(record: PointInTimeRecord) -> tuple[object, ...]:
    if isinstance(record, MarketObservationRecord):
        return (
            "MARKET_OBSERVATION",
            record.platform_id,
            record.event_id,
            record.market_id,
            record.token_id,
            record.source_id,
            record.observation_kind,
        )
    if isinstance(record, SourceSnapshotRecord):
        return ("SOURCE_SNAPSHOT", record.source_id)
    return (
        "RESOLUTION_RULE_SNAPSHOT",
        record.platform_id,
        record.event_id,
        record.market_id,
        record.resolution_source_id,
    )


def _record_specific_metadata(record: PointInTimeRecord) -> dict[str, object]:
    if isinstance(record, MarketObservationRecord):
        return _market_record_specific_metadata(
            observation_kind=record.observation_kind,
            platform_id=record.platform_id,
            event_id=record.event_id,
            market_id=record.market_id,
            token_id=record.token_id,
            source_id=record.source_id,
            source_assertion_id=record.source_assertion_id,
        )
    if isinstance(record, SourceSnapshotRecord):
        return _source_record_specific_metadata(
            source_id=record.source_id,
            source_type=record.source_type,
            source_reference=record.source_reference,
            media_type=record.media_type,
            raw_content_sha256=record.raw_content_sha256,
            byte_length=record.byte_length,
            retrieval_method=record.retrieval_method,
            retrieval_version=record.retrieval_version,
            upstream_revision=record.upstream_revision,
            prior_source_snapshot_id=record.prior_source_snapshot_id,
            access_classification=record.access_classification,
        )
    return _rule_record_specific_metadata(
        platform_id=record.platform_id,
        event_id=record.event_id,
        market_id=record.market_id,
        resolution_source_id=record.resolution_source_id,
        source_snapshot_id=record.source_snapshot_id,
        rule_content_sha256=record.rule_content_sha256,
        source_declared_effective_time=record.source_declared_effective_time,
        ambiguity_labels=record.ambiguity_labels,
        source_hierarchy_rank=record.source_hierarchy_rank,
        human_review_state=record.human_review_state,
    )


def _recomputed_record_version_id(record: PointInTimeRecord) -> str:
    envelope = record.envelope
    preimage = _record_version_preimage(
        record_family=envelope.record_family,
        record_specific_metadata_sha256=_record_specific_metadata_sha256(
            _record_specific_metadata(record)
        ),
        canonical_payload_sha256=envelope.canonical_payload_sha256,
        observation_id=envelope.observation_id,
        snapshot_id=envelope.snapshot_id,
        source_snapshot_id=envelope.source_snapshot_id,
        resolution_rule_snapshot_id=envelope.resolution_rule_snapshot_id,
        ingestion_batch_id=envelope.ingestion_batch_id,
        observed_time=envelope.observed_time,
        ingestion_time=envelope.ingestion_time,
        event_time=envelope.event_time,
        lineage_parent_ids=envelope.lineage_parent_ids,
        supersedes_record_version_id=envelope.supersedes_record_version_id,
        lifecycle_state=envelope.lifecycle_state,
        classification=envelope.classification,
        normalizer_version=envelope.normalizer_version,
        validator_version=envelope.validator_version,
        parameter_set_id=envelope.parameter_set_id,
        source_content_sha256=envelope.source_content_sha256,
        human_review_required=envelope.human_review_required,
        advisory_only=envelope.advisory_only,
        no_execution_authority=envelope.no_execution_authority,
    )
    return "record:sha256:" + sha256_hex(canonical_json_bytes(preimage))


def _record_fingerprint(record: PointInTimeRecord) -> str:
    envelope = record.envelope
    material: dict[str, object] = {
        field.name: getattr(envelope, field.name) for field in fields(PointInTimeEnvelope)
    }
    material["record_type"] = type(record).__name__
    material["canonical_payload_json"] = record.canonical_payload_json
    for field in fields(type(record)):
        if field.name not in {"envelope", "canonical_payload_json"}:
            material[field.name] = getattr(record, field.name)
    return sha256_hex(canonical_json_bytes(material))


def _canonical_time_value(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _payload_matches_envelope(record: PointInTimeRecord) -> bool:
    try:
        decoded = json.loads(record.canonical_payload_json)
        canonical = canonical_json_bytes(decoded)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    return (
        canonical.decode("utf-8") == record.canonical_payload_json
        and sha256_hex(canonical) == record.envelope.canonical_payload_sha256
    )


def _derived_family_ids_match(record: PointInTimeRecord) -> bool:
    envelope = record.envelope
    if isinstance(record, MarketObservationRecord):
        preimage = {
            "schema_id": SUPPORTED_SCHEMA_ID,
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "record_family": "MARKET_OBSERVATION",
            "observation_kind": record.observation_kind,
            "platform_id": record.platform_id,
            "event_id": record.event_id,
            "market_id": record.market_id,
            "token_id": record.token_id,
            "source_id": record.source_id,
            "source_snapshot_id": envelope.source_snapshot_id,
            "source_assertion_id": record.source_assertion_id,
        }
        expected = "obs:sha256:" + sha256_hex(canonical_json_bytes(preimage))
        return (
            envelope.record_family == "MARKET_OBSERVATION"
            and envelope.observation_id == expected
            and envelope.resolution_rule_snapshot_id is None
        )
    if isinstance(record, SourceSnapshotRecord):
        preimage = {
            "source_id": record.source_id,
            "observed_time": envelope.observed_time,
            "raw_content_sha256": record.raw_content_sha256,
            "byte_length": record.byte_length,
            "media_type": record.media_type,
        }
        expected = "srcsnap:sha256:" + sha256_hex(canonical_json_bytes(preimage))
        return (
            envelope.record_family == "SOURCE_SNAPSHOT"
            and envelope.observation_id is None
            and envelope.source_snapshot_id == expected
            and envelope.resolution_rule_snapshot_id is None
            and envelope.source_content_sha256 == record.raw_content_sha256
        )
    preimage = {
        "event_id": record.event_id,
        "market_id": record.market_id,
        "resolution_source_id": record.resolution_source_id,
        "source_snapshot_id": record.source_snapshot_id,
        "rule_content_sha256": record.rule_content_sha256,
    }
    expected = "rulesnap:sha256:" + sha256_hex(canonical_json_bytes(preimage))
    return (
        envelope.record_family == "RESOLUTION_RULE_SNAPSHOT"
        and envelope.observation_id is None
        and envelope.source_snapshot_id == record.source_snapshot_id
        and envelope.resolution_rule_snapshot_id == expected
        and envelope.source_content_sha256 == record.rule_content_sha256
    )


def _public_record_builder_input(
    record: PointInTimeRecord,
) -> tuple[dict[str, object], Callable[[Mapping[str, object]], PointInTimeBuildResult]]:
    envelope = record.envelope
    decoded_payload = json.loads(record.canonical_payload_json)
    common: dict[str, object] = {
        "schema_id": envelope.schema_id,
        "schema_version": envelope.schema_version,
        "record_family": envelope.record_family,
        "record_version_id": envelope.record_version_id,
        "snapshot_id": envelope.snapshot_id,
        "ingestion_batch_id": envelope.ingestion_batch_id,
        "event_time": envelope.event_time,
        "observed_time": envelope.observed_time,
        "ingestion_time": envelope.ingestion_time,
        "lifecycle_state": envelope.lifecycle_state,
        "classification": envelope.classification,
        "lineage_parent_ids": envelope.lineage_parent_ids,
        "supersedes_record_version_id": envelope.supersedes_record_version_id,
        "normalizer_version": envelope.normalizer_version,
        "validator_version": envelope.validator_version,
        "parameter_set_id": envelope.parameter_set_id,
        "human_review_required": envelope.human_review_required,
        "canonical_payload": decoded_payload,
        "canonical_payload_sha256": envelope.canonical_payload_sha256,
    }
    if isinstance(record, MarketObservationRecord):
        common.update(
            {
                "observation_id": envelope.observation_id,
                "observation_kind": record.observation_kind,
                "platform_id": record.platform_id,
                "event_id": record.event_id,
                "market_id": record.market_id,
                "token_id": record.token_id,
                "source_id": record.source_id,
                "source_assertion_id": record.source_assertion_id,
                "source_snapshot_id": envelope.source_snapshot_id,
            }
        )
        return common, _build_market_observation
    if isinstance(record, SourceSnapshotRecord):
        common.update(
            {
                "source_snapshot_id": envelope.source_snapshot_id,
                "source_id": record.source_id,
                "source_type": record.source_type,
                "source_reference": record.source_reference,
                "media_type": record.media_type,
                "raw_content_sha256": record.raw_content_sha256,
                "byte_length": record.byte_length,
                "retrieval_method": record.retrieval_method,
                "retrieval_version": record.retrieval_version,
                "upstream_revision": record.upstream_revision,
                "prior_source_snapshot_id": record.prior_source_snapshot_id,
                "access_classification": record.access_classification,
            }
        )
        return common, _build_source_snapshot
    common.update(
        {
            "resolution_rule_snapshot_id": envelope.resolution_rule_snapshot_id,
            "platform_id": record.platform_id,
            "event_id": record.event_id,
            "market_id": record.market_id,
            "resolution_source_id": record.resolution_source_id,
            "source_snapshot_id": record.source_snapshot_id,
            "rule_content_sha256": record.rule_content_sha256,
            "source_declared_effective_time": record.source_declared_effective_time,
            "ambiguity_labels": record.ambiguity_labels,
            "source_hierarchy_rank": record.source_hierarchy_rank,
            "human_review_state": record.human_review_state,
        }
    )
    return common, _build_resolution_rule_snapshot


def _revalidate_public_record(record: PointInTimeRecord) -> tuple[str, ...]:
    if type(record.envelope) is not PointInTimeEnvelope:
        return ("FIELD_TYPE_INVALID", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    try:
        builder_input, builder = _public_record_builder_input(record)
        rebuilt = builder(builder_input)
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
        return (
            "PAYLOAD_TYPE_UNSUPPORTED",
            "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH",
        )
    errors = list(rebuilt.error_codes)
    if not rebuilt.is_valid or rebuilt.record is None or rebuilt.record != record:
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    return _ordered_unique(errors, _ERROR_ORDER)


def _validate_external_parent_record(
    candidate: object, errors: list[str]
) -> str | None:
    """Fully revalidate one supplied external-parent record object, or fail.

    Mirrors the per-record integrity gate ``validate_record_batch`` applies to a
    current record: exact WP156 ordinary record class, exact ``PointInTimeEnvelope``,
    namespaced ``record:sha256:`` id grammar, complete public revalidation,
    recomputed record-version identity, payload/envelope agreement, and
    family-derived id agreement. A ``CONFLICT`` parent never carries authority and
    is rejected. Returns the proven ``record_version_id`` or ``None`` (codes are
    appended to ``errors``). Ancestors are never required recursively; the caller's
    manifest authority proves the parent itself was previously committed.
    """

    allowed_types = (
        MarketObservationRecord,
        SourceSnapshotRecord,
        ResolutionRuleSnapshotRecord,
    )
    if type(candidate) not in allowed_types:
        errors.append("FIELD_TYPE_INVALID")
        return None
    if type(candidate.envelope) is not PointInTimeEnvelope:
        errors.extend(
            ("FIELD_TYPE_INVALID", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
        )
        return None
    record_id = candidate.envelope.record_version_id
    if _validate_id(record_id, errors) is None:
        return None
    if _RECORD_VERSION_ID_RE.fullmatch(record_id) is None:
        errors.extend(
            ("ID_DERIVATION_MISMATCH", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
        )
        return None
    if candidate.envelope.classification == "CONFLICT":
        errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
        return None
    record_errors = _revalidate_public_record(candidate)
    if record_errors:
        errors.extend(record_errors)
        return None
    try:
        recomputed = _recomputed_record_version_id(candidate)
    except (TypeError, ValueError):
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
        return None
    if (
        recomputed != record_id
        or not _payload_matches_envelope(candidate)
        or not _derived_family_ids_match(candidate)
    ):
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
        return None
    return record_id


def validate_record_batch(
    records: Sequence[PointInTimeRecord],
    *,
    known_parent_record_ids: Sequence[str] = (),
    known_parent_records: Sequence[PointInTimeRecord] = (),
) -> PointInTimeBatchValidationResult:
    """Validate a finite in-memory record set without reconstructing as-of state.

    ``known_parent_record_ids`` remains the legacy existence-only authority: it
    proves a referenced parent id exists elsewhere but cannot compare a current
    record against the parent's semantics.

    ``known_parent_records`` (WP166) additionally supplies the actual immutable
    external-parent record objects. Each is fully revalidated, and every current
    record whose relevant lineage parent is external is checked against the actual
    parent object with the SAME entity/content/time semantics used when the parent
    is inside the batch. When ``known_parent_records`` is non-empty the canonical
    batch material additionally commits the sorted external-parent id set; when it
    is empty the legacy batch material and hash are byte-for-byte unchanged.
    ``accepted_record_version_ids`` always names only the current records.
    """

    errors: list[str] = []
    warnings: list[str] = []
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        errors.append("FIELD_TYPE_INVALID")
        records = ()
    if len(records) > _MAX_BATCH:
        errors.append("RECORD_BATCH_LIMIT_EXCEEDED")
    known_external: set[str] = set()
    if isinstance(known_parent_record_ids, (str, bytes)) or not isinstance(
        known_parent_record_ids, Sequence
    ):
        errors.append("FIELD_TYPE_INVALID")
    else:
        for parent in known_parent_record_ids:
            validated = _validate_id(parent, errors)
            if validated is not None:
                known_external.add(validated)

    # WP166 external-parent record objects: fully revalidated, bounded, unique.
    external_parent_map: dict[str, PointInTimeRecord] = {}
    external_parents_supplied = False
    if isinstance(known_parent_records, (str, bytes)) or not isinstance(
        known_parent_records, Sequence
    ):
        errors.append("FIELD_TYPE_INVALID")
    else:
        external_parents_supplied = len(known_parent_records) > 0
        if len(known_parent_records) > _MAX_BATCH:
            errors.append("RECORD_BATCH_LIMIT_EXCEEDED")
        for parent_candidate in list(known_parent_records)[:_MAX_BATCH]:
            parent_id = _validate_external_parent_record(parent_candidate, errors)
            if parent_id is None:
                continue
            if parent_id in external_parent_map:
                errors.append("LINEAGE_PARENT_DUPLICATE")
                continue
            external_parent_map[parent_id] = parent_candidate
    known_external |= set(external_parent_map)

    exact_duplicates: list[str] = []
    unique: dict[str, PointInTimeRecord] = {}
    fingerprints: dict[str, str] = {}
    rejected_ids: set[str] = set()
    diagnostic_graph: dict[str, tuple[str, ...]] = {}
    allowed_types = (
        MarketObservationRecord,
        SourceSnapshotRecord,
        ResolutionRuleSnapshotRecord,
    )
    for candidate in records[:_MAX_BATCH]:
        if type(candidate) not in allowed_types:
            errors.append("FIELD_TYPE_INVALID")
            continue
        record = candidate
        if type(record.envelope) is not PointInTimeEnvelope:
            errors.extend(
                ("FIELD_TYPE_INVALID", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
            )
            continue
        record_id = record.envelope.record_version_id
        if _validate_id(record_id, errors) is None:
            continue
        envelope = record.envelope
        if isinstance(envelope.lineage_parent_ids, tuple) and all(
            isinstance(parent, str) for parent in envelope.lineage_parent_ids
        ):
            diagnostic_graph[record_id] = envelope.lineage_parent_ids
        if _RECORD_VERSION_ID_RE.fullmatch(record_id) is None:
            errors.extend(
                ("ID_DERIVATION_MISMATCH", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
            )
            continue
        record_errors = _revalidate_public_record(record)
        if record_errors:
            errors.extend(record_errors)
            rejected_ids.add(record_id)
            continue
        try:
            fingerprint = _record_fingerprint(record)
            recomputed = _recomputed_record_version_id(record)
        except (TypeError, ValueError):
            errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
            continue
        if (
            recomputed != record_id
            or not _payload_matches_envelope(record)
            or not _derived_family_ids_match(record)
        ):
            errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
            rejected_ids.add(record_id)
            continue
        if record_id in unique:
            if fingerprints[record_id] == fingerprint:
                exact_duplicates.append(record_id)
            else:
                errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
                rejected_ids.add(record_id)
            continue
        unique[record_id] = record
        fingerprints[record_id] = fingerprint

    for rejected_id in rejected_ids:
        unique.pop(rejected_id, None)
        fingerprints.pop(rejected_id, None)
    exact_duplicates = [
        record_id for record_id in exact_duplicates if record_id not in rejected_ids
    ]

    diagnostic_available = set(diagnostic_graph) | known_external
    for record_id, parents in diagnostic_graph.items():
        if len(set(parents)) != len(parents):
            errors.append("LINEAGE_PARENT_DUPLICATE")
        if record_id in parents:
            errors.append("LINEAGE_SELF_PARENT")
        if any(parent not in diagnostic_available for parent in parents):
            errors.append("LINEAGE_PARENT_UNKNOWN")

    diagnostic_visiting: set[str] = set()
    diagnostic_visited: set[str] = set()

    def visit_diagnostic(record_id: str) -> None:
        if record_id in diagnostic_visiting:
            errors.append("LINEAGE_CYCLE")
            return
        if record_id in diagnostic_visited:
            return
        diagnostic_visiting.add(record_id)
        for parent_id in diagnostic_graph.get(record_id, ()):
            if parent_id in diagnostic_graph:
                visit_diagnostic(parent_id)
        diagnostic_visiting.remove(record_id)
        diagnostic_visited.add(record_id)

    for record_id in sorted(diagnostic_graph):
        visit_diagnostic(record_id)

    available = set(unique) | known_external
    graph: dict[str, tuple[str, ...]] = {}
    quarantined: list[str] = sorted(rejected_ids)
    for record_id, record in unique.items():
        envelope = record.envelope
        parents = envelope.lineage_parent_ids
        if envelope.event_time is None:
            warnings.append("EVENT_TIME_MISSING_ALLOWED")
        elif _canonical_time_value(envelope.event_time) > _canonical_time_value(
            envelope.ingestion_time
        ):
            warnings.append("EVENT_TIME_AFTER_INGESTION")
        classification_warning = {
            "LATE_ARRIVAL": "LATE_ARRIVAL_DECLARED",
            "SOURCE_REVISION": "SOURCE_REVISION_DECLARED",
            "PROJECT_CORRECTION": "PROJECT_CORRECTION_DECLARED",
            "SOURCE_RETRACTION": "SOURCE_RETRACTION_DECLARED",
            "SEMANTIC_DUPLICATE": "SEMANTIC_DUPLICATE_DECLARED",
        }.get(envelope.classification)
        if classification_warning is not None:
            warnings.append(classification_warning)
        graph[record_id] = tuple(parent for parent in parents if parent in unique)
        if len(set(parents)) != len(parents):
            errors.append("LINEAGE_PARENT_DUPLICATE")
        if record_id in parents:
            errors.append("LINEAGE_SELF_PARENT")
        if any(parent not in available for parent in parents):
            errors.append("LINEAGE_PARENT_UNKNOWN")
        supersedes = envelope.supersedes_record_version_id
        if supersedes is not None:
            if supersedes not in parents:
                errors.append("SUPERSEDES_NOT_IN_LINEAGE")
            if supersedes not in available:
                errors.append("SUPERSEDES_PARENT_UNKNOWN")
        if envelope.classification in {
            "SOURCE_REVISION",
            "PROJECT_CORRECTION",
            "SOURCE_RETRACTION",
        } and supersedes is None:
            errors.append("SUPERSEDES_REQUIRED")
        if envelope.classification == "CONFLICT":
            quarantined.append(record_id)
            warnings.append("CONFLICT_DECLARED")
            if not envelope.human_review_required:
                errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")

        reference_id = supersedes
        if reference_id is None and envelope.classification in {
            "EXACT_DUPLICATE",
            "SEMANTIC_DUPLICATE",
        }:
            reference_id = parents[0] if parents else None
        parent = unique.get(reference_id) if reference_id is not None else None
        if parent is None and reference_id is not None:
            # WP166: the relevant parent is external; run the same semantics
            # against the actual supplied immutable parent object.
            parent = external_parent_map.get(reference_id)
        if parent is not None:
            if envelope.classification in {
                "SOURCE_REVISION",
                "PROJECT_CORRECTION",
                "SOURCE_RETRACTION",
            }:
                if _entity_identity(record) != _entity_identity(parent):
                    errors.append("IDENTITY_CONFLICT")
                if _canonical_time_value(
                    envelope.ingestion_time
                ) < _canonical_time_value(parent.envelope.ingestion_time):
                    errors.append("CORRECTION_VISIBILITY_VIOLATION")
            if envelope.classification == "EXACT_DUPLICATE":
                if (
                    envelope.canonical_payload_sha256
                    != parent.envelope.canonical_payload_sha256
                    or _entity_identity(record) != _entity_identity(parent)
                ):
                    errors.append("EXACT_DUPLICATE_CONTENT_MISMATCH")
            if envelope.classification == "SEMANTIC_DUPLICATE":
                if (
                    envelope.observation_id != parent.envelope.observation_id
                    or _entity_identity(record) != _entity_identity(parent)
                ):
                    errors.append("SEMANTIC_DUPLICATE_IDENTITY_MISMATCH")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(record_id: str) -> None:
        if record_id in visiting:
            errors.append("LINEAGE_CYCLE")
            return
        if record_id in visited:
            return
        visiting.add(record_id)
        for parent_id in graph.get(record_id, ()):
            visit(parent_id)
        visiting.remove(record_id)
        visited.add(record_id)

    for record_id in sorted(graph):
        visit(record_id)

    accepted_records = [
        record for record_id, record in unique.items() if record_id not in quarantined
    ]
    accepted_records.sort(
        key=lambda record: (
            _canonical_time_value(record.envelope.ingestion_time),
            _canonical_time_value(record.envelope.observed_time),
            record.envelope.event_time is not None,
            (
                _canonical_time_value(record.envelope.event_time)
                if record.envelope.event_time is not None
                else _canonical_time_value("0001-01-01T00:00:00Z")
            ),
            record.envelope.record_version_id,
        )
    )
    accepted_ids = tuple(
        record.envelope.record_version_id for record in accepted_records
    )
    ordered_errors = _ordered_unique(errors, _ERROR_ORDER)
    ordered_warnings = _ordered_unique(warnings, _WARNING_ORDER)
    batch_material = {
        "accepted_record_version_ids": accepted_ids,
        "exact_duplicate_record_version_ids": tuple(exact_duplicates),
        "quarantined_record_version_ids": tuple(sorted(quarantined)),
        "error_codes": ordered_errors,
        "warning_codes": ordered_warnings,
    }
    if external_parents_supplied:
        # Only present when external parent objects were supplied, so a legacy
        # call with no external parents keeps its byte-for-byte identical hash.
        batch_material["external_parent_record_version_ids"] = tuple(
            sorted(external_parent_map)
        )
    batch_hash = sha256_hex(canonical_json_bytes(batch_material))
    is_valid = not ordered_errors and not quarantined
    if is_valid:
        status = "VALID_WITH_WARNINGS" if ordered_warnings else "VALID"
    elif quarantined and not ordered_errors:
        status = "CONFLICT_REQUIRES_REVIEW"
    else:
        status = "REJECTED_CONTRACT"
    return PointInTimeBatchValidationResult(
        is_valid=is_valid,
        status=status,
        error_codes=ordered_errors,
        warning_codes=ordered_warnings,
        accepted_record_version_ids=accepted_ids,
        exact_duplicate_record_version_ids=tuple(exact_duplicates),
        quarantined_record_version_ids=tuple(sorted(quarantined)),
        canonical_batch_sha256=batch_hash,
    )


# ---------------------------------------------------------------------------
# WP157 review-only conflict handoff (additive; standard builders and
# validate_record_batch are unchanged and continue to reject conflicts).
#
# A CONFLICT record can never be authoritative and is never accepted by
# validate_record_batch. These two additive surfaces expose a *structurally
# valid* conflict record — one that satisfies every WP156 integrity rule except
# the human-review gate — so the separately approved WP157 as-of query layer can
# list conflict identities in a review-only result field. Neither surface
# weakens any fail-closed guarantee: a conflict record is admitted only when its
# classification is CONFLICT, human_review_required is True, and it reproduces
# its committed record-version identity exactly.
# ---------------------------------------------------------------------------


def build_review_conflict_record(
    input_record: Mapping[str, object],
) -> PointInTimeBuildResult:
    """Build one structurally valid review-only CONFLICT record or fail closed.

    Identical to the family builders except that a ``CONFLICT`` classification
    with ``human_review_required`` True is treated as structurally valid for
    review-only handoff. The record is never authoritative. Non-conflict input
    fails closed; the standard builders remain the only authoritative path.
    """

    if not isinstance(input_record, Mapping):
        return _invalid_result(input_record, ["FIELD_TYPE_INVALID"])
    if input_record.get("classification") != "CONFLICT":
        return _invalid_result(input_record, ["CLASSIFICATION_LIFECYCLE_MISMATCH"])
    family = input_record.get("record_family")
    if family == "MARKET_OBSERVATION":
        return _build_market_observation(input_record, allow_review_conflict=True)
    if family == "SOURCE_SNAPSHOT":
        return _build_source_snapshot(input_record, allow_review_conflict=True)
    if family == "RESOLUTION_RULE_SNAPSHOT":
        return _build_resolution_rule_snapshot(input_record, allow_review_conflict=True)
    return _invalid_result(input_record, ["RECORD_FAMILY_UNSUPPORTED"])


def revalidate_review_conflict_record(record: PointInTimeRecord) -> tuple[str, ...]:
    """Return ``()`` when ``record`` is a structurally valid review-only conflict.

    Mirrors the per-record integrity checks applied by ``validate_record_batch``
    but tolerates the human-reviewed conflict gate. Returns ordered WP156 error
    codes otherwise. The record is required to be a CONFLICT classification with
    ``human_review_required`` True and to reproduce its committed
    ``record_version_id`` exactly. This surface never returns the record itself
    for authoritative use.
    """

    if type(record) not in (
        MarketObservationRecord,
        SourceSnapshotRecord,
        ResolutionRuleSnapshotRecord,
    ):
        return ("FIELD_TYPE_INVALID",)
    if type(record.envelope) is not PointInTimeEnvelope:
        return ("FIELD_TYPE_INVALID", "RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    envelope = record.envelope
    errors: list[str] = []
    if envelope.classification != "CONFLICT":
        errors.append("CLASSIFICATION_LIFECYCLE_MISMATCH")
    if envelope.human_review_required is not True:
        errors.append("CONFLICT_REQUIRES_HUMAN_REVIEW")
    record_id = envelope.record_version_id
    if _validate_id(record_id, errors) is None:
        return _ordered_unique(errors, _ERROR_ORDER)
    if _RECORD_VERSION_ID_RE.fullmatch(record_id) is None:
        errors.append("ID_DERIVATION_MISMATCH")
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    try:
        builder_input, builder = _public_record_builder_input(record)
        rebuilt = builder(builder_input, allow_review_conflict=True)
    except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
        errors.append("PAYLOAD_TYPE_UNSUPPORTED")
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
        return _ordered_unique(errors, _ERROR_ORDER)
    if not rebuilt.is_valid or rebuilt.record is None or rebuilt.record != record:
        errors.extend(rebuilt.error_codes)
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    try:
        recomputed = _recomputed_record_version_id(record)
    except (TypeError, ValueError):
        recomputed = None
    if (
        recomputed != record_id
        or not _payload_matches_envelope(record)
        or not _derived_family_ids_match(record)
    ):
        errors.append("RECORD_VERSION_HASH_COLLISION_OR_MISMATCH")
    return _ordered_unique(errors, _ERROR_ORDER)
