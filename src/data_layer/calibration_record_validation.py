"""Local/offline/read-only calibration record schema validator.

Validates whether a calibration record dictionary has the required
research-usefulness fields and no forbidden trading/performance fields.

Does not fetch resolved outcomes, generate reports, compute trading metrics,
or write any files. Stdlib-only. No network access.

Added in WP67.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


_ADVISORY_LABEL = (
    "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT — This validator checks calibration "
    "record structure for research-usefulness requirements only. It does not "
    "evaluate trading performance, profitability, or signal quality."
)

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "_notice",
    "_schema_version",
    "_status",
    "identity",
    "snapshot_metadata",
    "research_queue_state",
    "resolved_outcome",
    "human_review",
    "calibration_validity",
)

REQUIRED_IDENTITY_FIELDS: tuple[str, ...] = (
    "market_id",
    "condition_id",
    "question",
    "category",
)

REQUIRED_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "snapshot_time_utc",
    "local_capture_time_utc",
    "snapshot_offset_from_resolution",
)

ALLOWED_SNAPSHOT_OFFSETS: frozenset[str] = frozenset(
    {"T-30d", "T-7d", "T-24h", "T-6h", "T-1h", "T-15m"}
)

REQUIRED_RESEARCH_QUEUE_FIELDS: tuple[str, ...] = (
    "research_queue_bucket",
    "research_review_priority",
    "research_priority_score",
    "quality_status",
    "source_metadata_available",
    "manual_source_review_required",
    "resolution_ambiguity_manual_review_required",
    "microstructure_quality_summary",
    "cross_market_candidate_count",
)

ALLOWED_RESEARCH_QUEUE_BUCKETS: frozenset[str] = frozenset(
    {
        "REVIEW_FIRST",
        "MANUAL_SOURCE_REVIEW_REQUIRED",
        "REVIEW_LATER",
        "DATA_QUALITY_BLOCKED",
        "DEPRIORITIZED",
    }
)

REQUIRED_RESOLVED_OUTCOME_FIELDS: tuple[str, ...] = (
    "resolved_outcome",
    "resolution_status",
    "resolution_time_utc",
    "resolution_source_url_or_reference",
    "resolution_source_type",
    "resolution_rule_text_snapshot_available",
    "resolution_dispute_or_ambiguity_flag",
    "final_market_status",
    "outcome_token_mapping_verified",
)

ALLOWED_RESOLUTION_STATUSES: frozenset[str] = frozenset(
    {"RESOLVED", "VOID", "CANCELLED", "DISPUTED", "PENDING"}
)

ALLOWED_RESOLUTION_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "OFFICIAL_WEBSITE",
        "NEWS_ARTICLE",
        "PLATFORM_ANNOUNCEMENT",
        "MANUAL_REVIEW",
        "UNKNOWN",
    }
)

REQUIRED_HUMAN_REVIEW_FIELDS: tuple[str, ...] = ("human_review_usefulness_label",)

ALLOWED_HUMAN_REVIEW_USEFULNESS_LABELS: frozenset[str] = frozenset(
    {
        "USEFUL_RESEARCH_TARGET",
        "PARTIALLY_USEFUL_RESEARCH_TARGET",
        "NOT_USEFUL_DATA_TOO_WEAK",
        "NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS",
        "NOT_USEFUL_DUPLICATE_OR_OVERLAP",
        "NOT_REVIEWED",
    }
)

REQUIRED_CALIBRATION_VALIDITY_FIELDS: tuple[str, ...] = (
    "record_complete",
    "missing_required_fields",
    "excluded_from_calibration",
    "exclusion_reason",
)

FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        "pnl",
        "profit",
        "roi",
        "expected_return",
        "win_rate",
        "sharpe",
        "trade_signal",
        "buy",
        "sell",
        "position_size",
        "entry",
        "exit",
        "fill_probability",
        "slippage",
        "edge",
        "alpha",
        "opportunity",
        "arbitrage",
    }
)

_UTC_SUFFIX_RE = re.compile(r"Z$")


@dataclass(frozen=True)
class CalibrationRecordValidationResult:
    is_valid: bool
    missing_required_fields: tuple[str, ...]
    invalid_fields: tuple[str, ...]
    warnings: tuple[str, ...]
    advisory_label: str


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_utc_timestamp(value: object) -> bool:
    return isinstance(value, str) and bool(value) and bool(_UTC_SUFFIX_RE.search(value))


def _collect_forbidden_keys(obj: object, path: str = "") -> list[str]:
    """Recursively collect keys matching FORBIDDEN_KEY_NAMES."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_KEY_NAMES:
                found.append(f"{path}.{k}" if path else k)
            found.extend(_collect_forbidden_keys(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            found.extend(_collect_forbidden_keys(item, f"{path}[{i}]"))
    return found


def validate_calibration_record(
    record: Mapping[str, object],
) -> CalibrationRecordValidationResult:
    """Validate a calibration record dict for structural completeness.

    Returns a CalibrationRecordValidationResult. Does not raise on invalid
    records. Does not compute trading or performance metrics.
    """
    missing: list[str] = []
    invalid: list[str] = []
    warnings: list[str] = []

    # Top-level sections
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section not in record:
            missing.append(section)

    # Forbidden key scan (key-name checks only, no semantic NLP)
    for fkey in _collect_forbidden_keys(dict(record)):
        invalid.append(fkey)
        warnings.append(
            f"Forbidden trading/performance key found: '{fkey}'. "
            "Calibration records must not contain trading or performance fields."
        )

    # identity
    identity = record.get("identity")
    if isinstance(identity, dict):
        for field in REQUIRED_IDENTITY_FIELDS:
            if field not in identity:
                missing.append(f"identity.{field}")
            elif not _is_nonempty_string(identity[field]):
                invalid.append(f"identity.{field}")
    elif "identity" in record:
        invalid.append("identity")

    # snapshot_metadata
    snapshot = record.get("snapshot_metadata")
    if isinstance(snapshot, dict):
        for field in REQUIRED_SNAPSHOT_FIELDS:
            if field not in snapshot:
                missing.append(f"snapshot_metadata.{field}")
        for ts_field in ("snapshot_time_utc", "local_capture_time_utc"):
            if ts_field in snapshot and not _is_utc_timestamp(snapshot[ts_field]):
                invalid.append(f"snapshot_metadata.{ts_field}")
        offset = snapshot.get("snapshot_offset_from_resolution")
        if offset is not None and offset not in ALLOWED_SNAPSHOT_OFFSETS:
            invalid.append("snapshot_metadata.snapshot_offset_from_resolution")
    elif "snapshot_metadata" in record:
        invalid.append("snapshot_metadata")

    # Determine exclusion before validating research_priority_score
    cal_val = record.get("calibration_validity")
    excluded = (
        isinstance(cal_val, dict) and bool(cal_val.get("excluded_from_calibration", False))
    )

    # research_queue_state
    rqs = record.get("research_queue_state")
    if isinstance(rqs, dict):
        for field in REQUIRED_RESEARCH_QUEUE_FIELDS:
            if field not in rqs:
                missing.append(f"research_queue_state.{field}")
        bucket = rqs.get("research_queue_bucket")
        if bucket is not None and bucket not in ALLOWED_RESEARCH_QUEUE_BUCKETS:
            invalid.append("research_queue_state.research_queue_bucket")
        # research_priority_score: None allowed only when excluded
        if "research_priority_score" in rqs:
            score = rqs["research_priority_score"]
            if score is None:
                if not excluded:
                    invalid.append("research_queue_state.research_priority_score")
                    warnings.append(
                        "research_priority_score is None but record is not excluded from calibration."
                    )
            elif not isinstance(score, (int, float)) or not (0 <= score <= 1):
                invalid.append("research_queue_state.research_priority_score")
        # cross_market_candidate_count: non-negative int
        if "cross_market_candidate_count" in rqs:
            count = rqs["cross_market_candidate_count"]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                invalid.append("research_queue_state.cross_market_candidate_count")
        # boolean fields
        for bool_field in (
            "source_metadata_available",
            "manual_source_review_required",
            "resolution_ambiguity_manual_review_required",
        ):
            if bool_field in rqs and not isinstance(rqs[bool_field], bool):
                invalid.append(f"research_queue_state.{bool_field}")
    elif "research_queue_state" in record:
        invalid.append("research_queue_state")

    # resolved_outcome
    ro = record.get("resolved_outcome")
    if isinstance(ro, dict):
        for field in REQUIRED_RESOLVED_OUTCOME_FIELDS:
            if field not in ro:
                missing.append(f"resolved_outcome.{field}")
        rs = ro.get("resolution_status")
        if rs is not None and rs not in ALLOWED_RESOLUTION_STATUSES:
            invalid.append("resolved_outcome.resolution_status")
        rst = ro.get("resolution_source_type")
        if rst is not None and rst not in ALLOWED_RESOLUTION_SOURCE_TYPES:
            invalid.append("resolved_outcome.resolution_source_type")
        for bool_field in (
            "resolution_rule_text_snapshot_available",
            "resolution_dispute_or_ambiguity_flag",
        ):
            if bool_field in ro and not isinstance(ro[bool_field], bool):
                invalid.append(f"resolved_outcome.{bool_field}")
        if "outcome_token_mapping_verified" in ro:
            otmv = ro["outcome_token_mapping_verified"]
            if not isinstance(otmv, bool):
                invalid.append("resolved_outcome.outcome_token_mapping_verified")
            elif not otmv:
                warnings.append(
                    "outcome_token_mapping_verified is False. "
                    "Record may have unverified token mapping; review before use in calibration."
                )
    elif "resolved_outcome" in record:
        invalid.append("resolved_outcome")

    # human_review
    hr = record.get("human_review")
    if isinstance(hr, dict):
        for field in REQUIRED_HUMAN_REVIEW_FIELDS:
            if field not in hr:
                missing.append(f"human_review.{field}")
        label = hr.get("human_review_usefulness_label")
        if label is not None and label not in ALLOWED_HUMAN_REVIEW_USEFULNESS_LABELS:
            invalid.append("human_review.human_review_usefulness_label")
    elif "human_review" in record:
        invalid.append("human_review")

    # calibration_validity
    if isinstance(cal_val, dict):
        for field in REQUIRED_CALIBRATION_VALIDITY_FIELDS:
            if field not in cal_val:
                missing.append(f"calibration_validity.{field}")
        if "excluded_from_calibration" in cal_val and not isinstance(
            cal_val["excluded_from_calibration"], bool
        ):
            invalid.append("calibration_validity.excluded_from_calibration")
        if "missing_required_fields" in cal_val and not isinstance(
            cal_val["missing_required_fields"], list
        ):
            invalid.append("calibration_validity.missing_required_fields")
        if "record_complete" in cal_val and not isinstance(cal_val["record_complete"], bool):
            invalid.append("calibration_validity.record_complete")
    elif "calibration_validity" in record:
        invalid.append("calibration_validity")

    is_valid = not missing and not invalid

    return CalibrationRecordValidationResult(
        is_valid=is_valid,
        missing_required_fields=tuple(missing),
        invalid_fields=tuple(invalid),
        warnings=tuple(warnings),
        advisory_label=_ADVISORY_LABEL,
    )
