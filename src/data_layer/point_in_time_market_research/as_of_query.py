"""Bounded in-memory point-in-time record-set reconstruction and as-of query.

This module is local, offline, stdlib-only, deterministic, and in-memory. It
consumes already-built WP156 public record objects and produces immutable
deterministic query results with an exact receipt and SHA-256 result hash.

It never reads files, fetches data, persists state, selects a strategy,
computes expected return, or authorizes paper/live behavior. It has no
execution authority. Conflicts never enter authoritative results.

The deterministic sequence is:

1. validate the query spec;
2. validate the record batch (WP156 ``validate_record_batch``);
3. reject the query if record integrity is invalid;
4. apply ingestion-time visibility (default authoritative research mode);
5. optionally apply the diagnostic observed-time bound (ingestion-bounded);
6. apply entity / family / kind filters;
7. apply event-time windows only to already-visible records;
8. apply visible supersession / correction / revision / retraction state;
9. exclude conflict, quarantine, invalid, and retracted authoritative states;
10. return immutable records / IDs plus an exact query receipt.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
import re

from .records import (
    SUPPORTED_OBSERVATION_KINDS,
    SUPPORTED_RECORD_FAMILIES,
    MarketObservationRecord,
    PointInTimeRecord,
    ResolutionRuleSnapshotRecord,
    SourceSnapshotRecord,
    canonical_json_bytes,
    revalidate_review_conflict_record,
    sha256_hex,
    validate_record_batch,
)


# ── Locked labels and posture (WP157 Section 4) ──────────────────────────────

AS_OF_QUERY_LABEL = "POINT_IN_TIME_RECORD_SET_RECONSTRUCTION"
AS_OF_QUERY_POSTURE = "BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION"
QUERY_ENGINE_VERSION = "point-in-time-as-of-query@1.0.0"

SUPPORTED_CUTOFF_MODES = (
    "AS_OF_INGESTION_TIME",
    "AS_OF_OBSERVED_TIME_DIAGNOSTIC",
)
SUPPORTED_RESULT_VIEWS = (
    "AUTHORITATIVE_CURRENT_STATE",
    "VISIBLE_HISTORY",
    "ENTITY_TIMELINE",
)
QUERY_STATUSES = (
    "QUERY_VALID",
    "QUERY_VALID_WITH_WARNINGS",
    "QUERY_EMPTY",
    "QUERY_REJECTED_SPEC",
    "QUERY_REJECTED_RECORD_BATCH",
    "QUERY_CONFLICT_REQUIRES_REVIEW",
)
EXCLUSION_REASONS = (
    "AFTER_INGESTION_CUTOFF",
    "AFTER_OBSERVED_CUTOFF",
    "BEFORE_EVENT_WINDOW",
    "AFTER_EVENT_WINDOW",
    "EVENT_TIME_MISSING",
    "SUPERSEDED_AT_CUTOFF",
    "RETRACTED_AT_CUTOFF",
    "CONFLICT_REQUIRES_REVIEW",
    "INVALID_RECORD_BATCH",
    "ENTITY_FILTER_MISMATCH",
    "RECORD_FAMILY_FILTER_MISMATCH",
    "OBSERVATION_KIND_FILTER_MISMATCH",
)

ERROR_CODES = (
    # Query spec.
    "QUERY_SPEC_TYPE_INVALID",
    "QUERY_ID_INVALID",
    "CUTOFF_MODE_UNSUPPORTED",
    "CUTOFF_TIME_INVALID",
    "RESULT_VIEW_UNSUPPORTED",
    "FILTER_TYPE_INVALID",
    "FILTER_VALUE_INVALID",
    "FILTER_DUPLICATE",
    "FILTER_ORDER_INVALID",
    "FILTER_LIMIT_EXCEEDED",
    "ENTITY_TIMELINE_FILTER_REQUIRED",
    "EVENT_WINDOW_INVALID",
    "EVENT_WINDOW_ORDER_INVALID",
    "RETRACTED_HISTORY_INCOMPATIBLE_WITH_CURRENT_STATE",
    "PARAMETER_SET_ID_INVALID",
    # Batch / state.
    "RECORD_BATCH_INVALID",
    "VISIBLE_CHILD_PARENT_NOT_VISIBLE",
    "VISIBLE_SUPERSEDES_PARENT_UNKNOWN",
    "VISIBLE_LINEAGE_CYCLE",
    "STATE_ENTITY_MISMATCH",
    "CONFLICT_NOT_AUTHORIZED_FOR_REVIEW",
    "RESULT_LIMIT_EXCEEDED",
    "RESULT_ACCOUNTING_MISMATCH",
    "RESULT_HASH_MISMATCH",
)
WARNING_CODES = (
    "OBSERVED_TIME_DIAGNOSTIC_MODE",
    "EMPTY_RESULT",
    "EVENT_TIME_MISSING_INCLUDED",
    "CONFLICTS_EXCLUDED_FROM_AUTHORITY",
    "RETRACTED_HISTORY_INCLUDED",
    "LATE_ARRIVAL_VISIBLE",
    "SEMANTIC_DUPLICATE_HISTORY_ONLY",
)

_CUTOFF_MODES = frozenset(SUPPORTED_CUTOFF_MODES)
_RESULT_VIEWS = frozenset(SUPPORTED_RESULT_VIEWS)
_FAMILIES = frozenset(SUPPORTED_RECORD_FAMILIES)
_KINDS = frozenset(SUPPORTED_OBSERVATION_KINDS)
_ERROR_ORDER = {code: index for index, code in enumerate(ERROR_CODES)}
_WARNING_ORDER = {code: index for index, code in enumerate(WARNING_CODES)}
_EXCLUSION_ORDER = {reason: index for index, reason in enumerate(EXCLUSION_REASONS)}
_FAMILY_ORDER = {family: index for index, family in enumerate(SUPPORTED_RECORD_FAMILIES)}

# Bounds (WP157 Section 21). Input records inherit the WP156 batch cap.
_MAX_ID = 256
_MAX_QUERY_ID = 256
_MAX_FILTER_VALUES_PER_FIELD = 128
_MAX_TOTAL_FILTER_VALUES = 512
_MAX_RESULT_RECORDS = 256
_MAX_INPUT_RECORDS = 256

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?P<fraction>\.[0-9]{1,})?(?P<zone>Z|\+00:00)$"
)

_FILTER_FIELDS = (
    "record_families",
    "observation_kinds",
    "platform_ids",
    "event_ids",
    "market_ids",
    "token_ids",
    "source_ids",
    "resolution_source_ids",
)
_ENTITY_TIMELINE_FILTER_FIELDS = (
    "event_ids",
    "market_ids",
    "token_ids",
    "source_ids",
    "resolution_source_ids",
)
# Canonical filter precedence for primary exclusion-reason assignment.
_FILTER_PRECEDENCE = (
    ("record_families", "RECORD_FAMILY_FILTER_MISMATCH"),
    ("observation_kinds", "OBSERVATION_KIND_FILTER_MISMATCH"),
    ("platform_ids", "ENTITY_FILTER_MISMATCH"),
    ("event_ids", "ENTITY_FILTER_MISMATCH"),
    ("market_ids", "ENTITY_FILTER_MISMATCH"),
    ("token_ids", "ENTITY_FILTER_MISMATCH"),
    ("source_ids", "ENTITY_FILTER_MISMATCH"),
    ("resolution_source_ids", "ENTITY_FILTER_MISMATCH"),
)


# ── Immutable query spec (WP157 Section 5) ───────────────────────────────────


@dataclass(frozen=True)
class EventTimeWindow:
    start_inclusive: str | None
    end_exclusive: str | None
    include_missing_event_time: bool


@dataclass(frozen=True)
class PointInTimeQuerySpec:
    query_id: str
    cutoff_mode: str
    cutoff_time: str
    result_view: str
    record_families: tuple[str, ...]
    observation_kinds: tuple[str, ...]
    platform_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    market_ids: tuple[str, ...]
    token_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    resolution_source_ids: tuple[str, ...]
    event_time_window: EventTimeWindow | None
    include_conflicts_for_review: bool
    include_retracted_history: bool
    parameter_set_id: str


@dataclass(frozen=True)
class PointInTimeQueryReceipt:
    query_id: str
    query_spec_sha256: str
    validated_batch_sha256: str
    cutoff_mode: str
    cutoff_time: str
    event_window_start_inclusive: str | None
    event_window_end_exclusive: str | None
    result_view: str
    input_record_count: int
    validated_unique_record_count: int
    visible_record_count_before_state_application: int
    authoritative_result_count: int
    history_result_count: int
    review_conflict_count: int
    excluded_count: int
    exclusion_counts: tuple[tuple[str, int], ...]
    authoritative_record_version_ids: tuple[str, ...]
    history_record_version_ids: tuple[str, ...]
    review_conflict_record_version_ids: tuple[str, ...]
    result_sha256: str
    query_engine_version: str
    parameter_set_id: str
    advisory_only: bool
    no_execution_authority: bool


@dataclass(frozen=True)
class PointInTimeRecordSetResult:
    is_valid: bool
    status: str
    error_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    authoritative_records: tuple[PointInTimeRecord, ...]
    history_records: tuple[PointInTimeRecord, ...]
    review_conflict_records: tuple[PointInTimeRecord, ...]
    receipt: PointInTimeQueryReceipt | None


@dataclass(frozen=True)
class SyntheticAsOfQueryCase:
    case_id: str
    record_case_ids: tuple[str, ...]
    query_spec: PointInTimeQuerySpec
    expected_valid: bool
    expected_status: str
    expected_error_codes: tuple[str, ...]
    expected_warning_codes: tuple[str, ...]
    expected_authoritative_ids: tuple[str, ...]
    expected_history_ids: tuple[str, ...]
    expected_review_conflict_ids: tuple[str, ...]
    expected_result_sha256: str
    safety_notice: str


# ── Deterministic helpers ────────────────────────────────────────────────────


def _ordered_unique(codes: Sequence[str], order: dict[str, int]) -> tuple[str, ...]:
    first: dict[str, int] = {}
    for occurrence, code in enumerate(codes):
        first.setdefault(code, occurrence)
    return tuple(
        sorted(first, key=lambda code: (order.get(code, len(order)), first[code]))
    )


def _valid_opaque_id(value: object, max_len: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= max_len
        and value == value.strip()
        and _ID_RE.fullmatch(value) is not None
    )


def _normalize_utc(value: object) -> str | None:
    """Return canonical ``Z``-form UTC timestamp using the exact WP156 rules."""

    if not isinstance(value, str):
        return None
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        return None
    fraction = match.group("fraction")
    if fraction is not None and len(fraction) - 1 > 6:
        return None
    canonical = value[:-6] + "Z" if value.endswith("+00:00") else value
    try:
        datetime.fromisoformat(canonical.replace("Z", "+00:00"))
    except ValueError:
        return None
    return canonical


def _to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ── Query-spec canonicalization and hash (WP157 Section 7) ───────────────────


def _spec_mapping(spec: PointInTimeQuerySpec) -> dict[str, object]:
    window: object = None
    if spec.event_time_window is not None:
        window = {
            "start_inclusive": spec.event_time_window.start_inclusive,
            "end_exclusive": spec.event_time_window.end_exclusive,
            "include_missing_event_time": bool(
                spec.event_time_window.include_missing_event_time
            ),
        }
    return {
        "query_id": spec.query_id,
        "cutoff_mode": spec.cutoff_mode,
        "cutoff_time": spec.cutoff_time,
        "result_view": spec.result_view,
        "record_families": list(spec.record_families),
        "observation_kinds": list(spec.observation_kinds),
        "platform_ids": list(spec.platform_ids),
        "event_ids": list(spec.event_ids),
        "market_ids": list(spec.market_ids),
        "token_ids": list(spec.token_ids),
        "source_ids": list(spec.source_ids),
        "resolution_source_ids": list(spec.resolution_source_ids),
        "event_time_window": window,
        "include_conflicts_for_review": bool(spec.include_conflicts_for_review),
        "include_retracted_history": bool(spec.include_retracted_history),
        "parameter_set_id": spec.parameter_set_id,
    }


def query_spec_sha256(spec: PointInTimeQuerySpec) -> str:
    """Return the deterministic SHA-256 of the canonical query-spec mapping."""

    return sha256_hex(canonical_json_bytes(_spec_mapping(spec)))


def _validate_filter_tuple(
    value: object,
    errors: list[str],
    *,
    allowed: frozenset[str] | None = None,
) -> None:
    if not isinstance(value, tuple):
        errors.append("FILTER_TYPE_INVALID")
        return
    if len(value) > _MAX_FILTER_VALUES_PER_FIELD:
        errors.append("FILTER_LIMIT_EXCEEDED")
    for item in value:
        if not _valid_opaque_id(item, _MAX_ID):
            errors.append("FILTER_VALUE_INVALID")
        elif allowed is not None and item not in allowed:
            errors.append("FILTER_VALUE_INVALID")
    if len(set(value)) != len(value):
        errors.append("FILTER_DUPLICATE")
    if list(value) != sorted(value):
        errors.append("FILTER_ORDER_INVALID")


def _validate_spec(spec: object) -> tuple[str, ...]:
    if type(spec) is not PointInTimeQuerySpec:
        return ("QUERY_SPEC_TYPE_INVALID",)
    errors: list[str] = []
    if not _valid_opaque_id(spec.query_id, _MAX_QUERY_ID):
        errors.append("QUERY_ID_INVALID")
    if not _valid_opaque_id(spec.parameter_set_id, _MAX_ID):
        errors.append("PARAMETER_SET_ID_INVALID")
    if spec.cutoff_mode not in _CUTOFF_MODES:
        errors.append("CUTOFF_MODE_UNSUPPORTED")
    if _normalize_utc(spec.cutoff_time) is None or spec.cutoff_time != _normalize_utc(
        spec.cutoff_time
    ):
        errors.append("CUTOFF_TIME_INVALID")
    if spec.result_view not in _RESULT_VIEWS:
        errors.append("RESULT_VIEW_UNSUPPORTED")

    total_filter_values = 0
    for field in _FILTER_FIELDS:
        value = getattr(spec, field)
        allowed: frozenset[str] | None = None
        if field == "record_families":
            allowed = _FAMILIES
        elif field == "observation_kinds":
            allowed = _KINDS
        _validate_filter_tuple(value, errors, allowed=allowed)
        if isinstance(value, tuple):
            total_filter_values += len(value)
    if total_filter_values > _MAX_TOTAL_FILTER_VALUES:
        errors.append("FILTER_LIMIT_EXCEEDED")

    if not isinstance(spec.include_conflicts_for_review, bool) or not isinstance(
        spec.include_retracted_history, bool
    ):
        errors.append("QUERY_SPEC_TYPE_INVALID")

    window = spec.event_time_window
    if window is not None:
        if type(window) is not EventTimeWindow:
            errors.append("EVENT_WINDOW_INVALID")
        else:
            start = window.start_inclusive
            end = window.end_exclusive
            start_ok = start is None or (
                _normalize_utc(start) is not None and start == _normalize_utc(start)
            )
            end_ok = end is None or (
                _normalize_utc(end) is not None and end == _normalize_utc(end)
            )
            if not start_ok or not end_ok:
                errors.append("EVENT_WINDOW_INVALID")
            if start is None and end is None:
                errors.append("EVENT_WINDOW_INVALID")
            if not isinstance(window.include_missing_event_time, bool):
                errors.append("EVENT_WINDOW_INVALID")
            if (
                start_ok
                and end_ok
                and start is not None
                and end is not None
                and not _to_dt(start) < _to_dt(end)
            ):
                errors.append("EVENT_WINDOW_ORDER_INVALID")

    if spec.result_view == "ENTITY_TIMELINE" and not any(
        isinstance(getattr(spec, field), tuple) and getattr(spec, field)
        for field in _ENTITY_TIMELINE_FILTER_FIELDS
    ):
        errors.append("ENTITY_TIMELINE_FILTER_REQUIRED")

    if (
        spec.result_view == "AUTHORITATIVE_CURRENT_STATE"
        and spec.include_retracted_history is True
    ):
        errors.append("RETRACTED_HISTORY_INCOMPATIBLE_WITH_CURRENT_STATE")

    return _ordered_unique(errors, _ERROR_ORDER)


# ── Record dimension extraction and filters (WP157 Section 10) ───────────────


def _record_dimensions(record: PointInTimeRecord) -> dict[str, str]:
    if isinstance(record, MarketObservationRecord):
        dims = {
            "record_families": "MARKET_OBSERVATION",
            "observation_kinds": record.observation_kind,
            "platform_ids": record.platform_id,
            "event_ids": record.event_id,
            "market_ids": record.market_id,
            "source_ids": record.source_id,
        }
        if record.token_id is not None:
            dims["token_ids"] = record.token_id
        return dims
    if isinstance(record, SourceSnapshotRecord):
        return {
            "record_families": "SOURCE_SNAPSHOT",
            "source_ids": record.source_id,
        }
    return {
        "record_families": "RESOLUTION_RULE_SNAPSHOT",
        "platform_ids": record.platform_id,
        "event_ids": record.event_id,
        "market_ids": record.market_id,
        "resolution_source_ids": record.resolution_source_id,
    }


def _filter_exclusion_reason(
    record: PointInTimeRecord, spec: PointInTimeQuerySpec
) -> str | None:
    dims = _record_dimensions(record)
    for field, reason in _FILTER_PRECEDENCE:
        selected = getattr(spec, field)
        if not selected:
            continue
        value = dims.get(field)
        if value is None or value not in selected:
            return reason
    return None


# ── Entity key and ordering (WP157 Sections 12, 14) ──────────────────────────


def _entity_key(record: PointInTimeRecord) -> tuple[str, ...]:
    envelope = record.envelope
    if isinstance(record, MarketObservationRecord):
        return (
            "MARKET_OBSERVATION",
            record.observation_kind,
            record.platform_id,
            record.event_id,
            record.market_id,
            record.token_id if record.token_id is not None else "\x00NULL",
            record.source_id,
            envelope.observation_id or "\x00NULL",
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


def _canonical_sort_key(record: PointInTimeRecord) -> tuple[object, ...]:
    envelope = record.envelope
    event_time = envelope.event_time
    return (
        _to_dt(envelope.ingestion_time),
        _to_dt(envelope.observed_time),
        1 if event_time is None else 0,
        event_time if event_time is not None else "",
        _FAMILY_ORDER.get(envelope.record_family, len(_FAMILY_ORDER)),
        envelope.record_version_id,
    )


def _authoritative_sort_key(record: PointInTimeRecord) -> tuple[object, ...]:
    envelope = record.envelope
    return (
        _entity_key(record),
        _to_dt(envelope.ingestion_time),
        envelope.record_version_id,
    )


# ── Result hash (WP157 Section 16) ───────────────────────────────────────────


def _result_sha256(
    *,
    spec: PointInTimeQuerySpec,
    query_spec_hash: str,
    validated_batch_hash: str,
    authoritative_ids: tuple[str, ...],
    history_ids: tuple[str, ...],
    review_ids: tuple[str, ...],
    exclusion_counts: tuple[tuple[str, int], ...],
) -> str:
    window = spec.event_time_window
    preimage = {
        "query_spec_sha256": query_spec_hash,
        "validated_batch_sha256": validated_batch_hash,
        "cutoff_mode": spec.cutoff_mode,
        "cutoff_time": spec.cutoff_time,
        "event_window_start_inclusive": window.start_inclusive if window else None,
        "event_window_end_exclusive": window.end_exclusive if window else None,
        "event_window_include_missing": (
            bool(window.include_missing_event_time) if window else None
        ),
        "result_view": spec.result_view,
        "authoritative_record_version_ids": list(authoritative_ids),
        "history_record_version_ids": list(history_ids),
        "review_conflict_record_version_ids": list(review_ids),
        "exclusion_counts": [[reason, count] for reason, count in exclusion_counts],
        "query_engine_version": QUERY_ENGINE_VERSION,
        "parameter_set_id": spec.parameter_set_id,
        "advisory_only": True,
        "no_execution_authority": True,
    }
    return sha256_hex(canonical_json_bytes(preimage))


def _rejected_result(
    status: str, error_codes: tuple[str, ...]
) -> PointInTimeRecordSetResult:
    return PointInTimeRecordSetResult(
        is_valid=False,
        status=status,
        error_codes=error_codes,
        warning_codes=(),
        authoritative_records=(),
        history_records=(),
        review_conflict_records=(),
        receipt=None,
    )


# ── Visibility (WP157 Section 9) ─────────────────────────────────────────────


def _visibility_exclusion(
    record: PointInTimeRecord, cutoff: datetime, diagnostic: bool
) -> str | None:
    envelope = record.envelope
    if _to_dt(envelope.ingestion_time) > cutoff:
        return "AFTER_INGESTION_CUTOFF"
    if diagnostic and _to_dt(envelope.observed_time) > cutoff:
        return "AFTER_OBSERVED_CUTOFF"
    return None


def _event_window_exclusion(
    record: PointInTimeRecord, window: EventTimeWindow | None
) -> str | None:
    if window is None:
        return None
    event_time = record.envelope.event_time
    if event_time is None:
        return None if window.include_missing_event_time else "EVENT_TIME_MISSING"
    moment = _to_dt(event_time)
    if window.start_inclusive is not None and moment < _to_dt(window.start_inclusive):
        return "BEFORE_EVENT_WINDOW"
    if window.end_exclusive is not None and moment >= _to_dt(window.end_exclusive):
        return "AFTER_EVENT_WINDOW"
    return None


# ── Public query entry point ─────────────────────────────────────────────────


def query_point_in_time_record_set(
    records: Sequence[PointInTimeRecord],
    spec: PointInTimeQuerySpec,
) -> PointInTimeRecordSetResult:
    """Reconstruct an as-of record set from valid WP156 records and one spec."""

    spec_errors = _validate_spec(spec)
    if spec_errors:
        return _rejected_result("QUERY_REJECTED_SPEC", spec_errors)

    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        return _rejected_result(
            "QUERY_REJECTED_RECORD_BATCH", ("RECORD_BATCH_INVALID",)
        )
    if len(records) > _MAX_INPUT_RECORDS:
        return _rejected_result(
            "QUERY_REJECTED_RECORD_BATCH", ("RECORD_BATCH_INVALID",)
        )

    # Partition conflicts (never authoritative) from authoritative candidates.
    conflict_candidates: list[PointInTimeRecord] = []
    authoritative_candidates: list[PointInTimeRecord] = []
    for candidate in records:
        envelope = getattr(candidate, "envelope", None)
        classification = getattr(envelope, "classification", None)
        if classification == "CONFLICT":
            conflict_candidates.append(candidate)
        else:
            authoritative_candidates.append(candidate)

    batch = validate_record_batch(authoritative_candidates)
    if not batch.is_valid:
        return _rejected_result(
            "QUERY_REJECTED_RECORD_BATCH", ("RECORD_BATCH_INVALID",)
        )

    # Structurally validate every conflict record through the WP156 review-only
    # handoff. Any invalid conflict fails the whole query closed.
    for conflict in conflict_candidates:
        if revalidate_review_conflict_record(conflict):
            return _rejected_result(
                "QUERY_REJECTED_RECORD_BATCH",
                ("RECORD_BATCH_INVALID", "CONFLICT_NOT_AUTHORIZED_FOR_REVIEW"),
            )

    # Deduplicate unique records by committed record-version identity.
    accepted_ids = set(batch.accepted_record_version_ids)
    unique_authoritative: dict[str, PointInTimeRecord] = {}
    for record in authoritative_candidates:
        record_id = record.envelope.record_version_id
        if record_id in accepted_ids and record_id not in unique_authoritative:
            unique_authoritative[record_id] = record
    unique_conflicts: dict[str, PointInTimeRecord] = {}
    for conflict in conflict_candidates:
        conflict_id = conflict.envelope.record_version_id
        if conflict_id not in unique_conflicts:
            unique_conflicts[conflict_id] = conflict

    cutoff = _to_dt(spec.cutoff_time)
    diagnostic = spec.cutoff_mode == "AS_OF_OBSERVED_TIME_DIAGNOSTIC"
    window = spec.event_time_window

    exclusion_counts = {reason: 0 for reason in EXCLUSION_REASONS}
    warnings: list[str] = []
    if diagnostic:
        warnings.append("OBSERVED_TIME_DIAGNOSTIC_MODE")

    def _passes_pipeline(record: PointInTimeRecord) -> str | None:
        reason = _visibility_exclusion(record, cutoff, diagnostic)
        if reason is not None:
            return reason
        reason = _filter_exclusion_reason(record, spec)
        if reason is not None:
            return reason
        return _event_window_exclusion(record, window)

    # Authoritative-candidate pipeline.
    visible: list[PointInTimeRecord] = []
    for record in unique_authoritative.values():
        reason = _passes_pipeline(record)
        if reason is not None:
            exclusion_counts[reason] += 1
            continue
        if window is not None and record.envelope.event_time is None:
            warnings.append("EVENT_TIME_MISSING_INCLUDED")
        visible.append(record)

    visible_before_state = len(visible)

    # Conflict pipeline (review-only; never authoritative).
    review_conflicts: list[PointInTimeRecord] = []
    for record in unique_conflicts.values():
        reason = _passes_pipeline(record)
        if reason is not None:
            exclusion_counts[reason] += 1
            continue
        if spec.include_conflicts_for_review:
            review_conflicts.append(record)
        else:
            exclusion_counts["CONFLICT_REQUIRES_REVIEW"] += 1
    if exclusion_counts["CONFLICT_REQUIRES_REVIEW"] > 0:
        warnings.append("CONFLICTS_EXCLUDED_FROM_AUTHORITY")

    # State application over the visible authoritative candidates.
    visible_ids = {record.envelope.record_version_id for record in visible}
    superseded_ids: set[str] = set()
    retraction_targets: set[str] = set()
    for record in visible:
        envelope = record.envelope
        target = envelope.supersedes_record_version_id
        if target is not None and envelope.classification in {
            "SOURCE_REVISION",
            "PROJECT_CORRECTION",
            "SOURCE_RETRACTION",
        }:
            superseded_ids.add(target)
            if envelope.classification == "SOURCE_RETRACTION":
                retraction_targets.add(target)

    terminal: list[PointInTimeRecord] = []
    history_state_excluded: list[tuple[PointInTimeRecord, str]] = []
    for record in visible:
        envelope = record.envelope
        record_id = envelope.record_version_id
        classification = envelope.classification
        is_retraction = classification == "SOURCE_RETRACTION"
        is_retracted_target = record_id in retraction_targets
        if is_retraction or is_retracted_target:
            history_state_excluded.append((record, "RETRACTED_AT_CUTOFF"))
            continue
        if record_id in superseded_ids:
            history_state_excluded.append((record, "SUPERSEDED_AT_CUTOFF"))
            continue
        if classification in {"EXACT_DUPLICATE", "SEMANTIC_DUPLICATE"}:
            if classification == "SEMANTIC_DUPLICATE":
                warnings.append("SEMANTIC_DUPLICATE_HISTORY_ONLY")
            history_state_excluded.append((record, "SUPERSEDED_AT_CUTOFF"))
            continue
        if classification == "LATE_ARRIVAL":
            warnings.append("LATE_ARRIVAL_VISIBLE")
        terminal.append(record)

    terminal.sort(key=_authoritative_sort_key)

    # Assemble per-view result tuples.
    view = spec.result_view
    include_retracted = spec.include_retracted_history

    if view == "AUTHORITATIVE_CURRENT_STATE":
        authoritative_records = tuple(terminal)
        history_records: tuple[PointInTimeRecord, ...] = ()
        for record, reason in history_state_excluded:
            exclusion_counts[reason] += 1
    else:
        # VISIBLE_HISTORY and ENTITY_TIMELINE keep visible records in history.
        history_pool: list[PointInTimeRecord] = []
        for record in visible:
            envelope = record.envelope
            record_id = envelope.record_version_id
            is_retraction = envelope.classification == "SOURCE_RETRACTION"
            is_retracted_target = record_id in retraction_targets
            if (is_retraction or is_retracted_target) and not include_retracted:
                exclusion_counts["RETRACTED_AT_CUTOFF"] += 1
                continue
            if (is_retraction or is_retracted_target) and include_retracted:
                warnings.append("RETRACTED_HISTORY_INCLUDED")
            history_pool.append(record)
        history_pool.sort(key=_canonical_sort_key)
        history_records = tuple(history_pool)
        if view == "ENTITY_TIMELINE":
            authoritative_records = tuple(terminal)
        else:
            authoritative_records = ()

    review_conflicts.sort(key=_canonical_sort_key)
    review_records = tuple(review_conflicts)

    # Bounded result guard.
    if (
        len(authoritative_records) > _MAX_RESULT_RECORDS
        or len(history_records) > _MAX_RESULT_RECORDS
        or len(review_records) > _MAX_RESULT_RECORDS
    ):
        return _rejected_result(
            "QUERY_REJECTED_RECORD_BATCH", ("RESULT_LIMIT_EXCEEDED",)
        )

    excluded_count = sum(exclusion_counts.values())
    ordered_exclusion_counts = tuple(
        (reason, exclusion_counts[reason]) for reason in EXCLUSION_REASONS
    )

    validated_unique = len(unique_authoritative) + len(unique_conflicts)
    primary_result_count = (
        len(authoritative_records)
        if view == "AUTHORITATIVE_CURRENT_STATE"
        else len(history_records)
    )
    accounting_ok = (
        primary_result_count + len(review_records) + excluded_count == validated_unique
    )

    authoritative_ids = tuple(
        record.envelope.record_version_id for record in authoritative_records
    )
    history_ids = tuple(
        record.envelope.record_version_id for record in history_records
    )
    review_ids = tuple(
        record.envelope.record_version_id for record in review_records
    )

    query_hash = query_spec_sha256(spec)
    result_hash = _result_sha256(
        spec=spec,
        query_spec_hash=query_hash,
        validated_batch_hash=batch.canonical_batch_sha256,
        authoritative_ids=authoritative_ids,
        history_ids=history_ids,
        review_ids=review_ids,
        exclusion_counts=ordered_exclusion_counts,
    )

    # Determine status.
    result_is_empty = (
        not authoritative_records and not history_records and not review_records
    )
    if result_is_empty:
        warnings.append("EMPTY_RESULT")

    ordered_warnings = _ordered_unique(warnings, _WARNING_ORDER)
    error_codes: list[str] = []
    if not accounting_ok:
        error_codes.append("RESULT_ACCOUNTING_MISMATCH")

    if error_codes:
        return _rejected_result(
            "QUERY_REJECTED_RECORD_BATCH",
            _ordered_unique(error_codes, _ERROR_ORDER),
        )

    if review_records:
        status = "QUERY_CONFLICT_REQUIRES_REVIEW"
    elif result_is_empty:
        status = "QUERY_EMPTY"
    elif ordered_warnings:
        status = "QUERY_VALID_WITH_WARNINGS"
    else:
        status = "QUERY_VALID"

    receipt = PointInTimeQueryReceipt(
        query_id=spec.query_id,
        query_spec_sha256=query_hash,
        validated_batch_sha256=batch.canonical_batch_sha256,
        cutoff_mode=spec.cutoff_mode,
        cutoff_time=spec.cutoff_time,
        event_window_start_inclusive=window.start_inclusive if window else None,
        event_window_end_exclusive=window.end_exclusive if window else None,
        result_view=view,
        input_record_count=len(records),
        validated_unique_record_count=validated_unique,
        visible_record_count_before_state_application=visible_before_state,
        authoritative_result_count=len(authoritative_records),
        history_result_count=len(history_records),
        review_conflict_count=len(review_records),
        excluded_count=excluded_count,
        exclusion_counts=ordered_exclusion_counts,
        authoritative_record_version_ids=authoritative_ids,
        history_record_version_ids=history_ids,
        review_conflict_record_version_ids=review_ids,
        result_sha256=result_hash,
        query_engine_version=QUERY_ENGINE_VERSION,
        parameter_set_id=spec.parameter_set_id,
        advisory_only=True,
        no_execution_authority=True,
    )
    return PointInTimeRecordSetResult(
        is_valid=True,
        status=status,
        error_codes=(),
        warning_codes=ordered_warnings,
        authoritative_records=authoritative_records,
        history_records=history_records,
        review_conflict_records=review_records,
        receipt=receipt,
    )


# ── Synthetic corpus loaders (WP157 Section 18) ──────────────────────────────


def get_synthetic_as_of_query_cases() -> tuple[SyntheticAsOfQueryCase, ...]:
    """Return the exact ordered immutable 24-case synthetic as-of query corpus."""

    from .as_of_synthetic_cases import build_synthetic_as_of_query_cases

    return build_synthetic_as_of_query_cases()


def load_synthetic_as_of_query_case(case_id: str) -> SyntheticAsOfQueryCase:
    """Return a fresh immutable synthetic as-of query case by exact case id."""

    for case in get_synthetic_as_of_query_cases():
        if case.case_id == case_id:
            return case
    raise KeyError("SYNTHETIC_AS_OF_QUERY_CASE_NOT_FOUND")
