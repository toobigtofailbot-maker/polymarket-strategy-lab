"""Local/offline/read-only schema validation for WP55 resolution ambiguity label records.

stdlib-only; no network; no file writes; no CLI; no export/report writer;
no parser; no scorer integration; no feature extraction; no dependency changes.
Advisory-only research-data-quality metadata validation.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping


# ── Module identity ───────────────────────────────────────────────────────────

MODULE_VERSION = "wp56-v1"

# ── Advisory label ────────────────────────────────────────────────────────────

ADVISORY_LABEL = "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"

# ── Allowed enum values ───────────────────────────────────────────────────────

ALLOWED_AMBIGUITY_CATEGORIES: frozenset[str] = frozenset(
    {
        "missing_resolution_source",
        "unclear_source_hierarchy",
        "cutoff_time_ambiguity",
        "timezone_ambiguity",
        "title_rules_mismatch",
        "entity_definition_ambiguity",
        "event_definition_ambiguity",
        "measurement_definition_ambiguity",
        "outcome_mapping_ambiguity",
        "source_conflict",
        "finality_or_revision_ambiguity",
        "duplicate_or_overlap_risk",
        "insufficient_local_evidence",
        "other_manual_review_issue",
    }
)

ALLOWED_REVIEW_STATUSES: frozenset[str] = frozenset(
    {
        "NOT_REVIEWED",
        "REVIEWED_CLEAR",
        "REVIEWED_LOW_AMBIGUITY",
        "REVIEWED_MEDIUM_AMBIGUITY",
        "REVIEWED_HIGH_AMBIGUITY",
        "INSUFFICIENT_LOCAL_EVIDENCE",
    }
)

ALLOWED_SEVERITY_VALUES: frozenset[str] = frozenset(
    {"NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"}
)

ALLOWED_CONFIDENCE_VALUES: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH"})

# ── Required fields ───────────────────────────────────────────────────────────

REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "label_id",
    "market_id",
    "question_snapshot",
    "resolution_text_snapshot",
    "review_status",
    "ambiguity_categories",
    "ambiguity_severity",
    "reviewer_confidence",
    "manual_review_required",
    "reviewed_at_utc",
    "reviewer_id_or_role",
    "source_artifact_refs",
    "evidence_notes",
    "limitations",
    "advisory_label",
    "forbidden_use_notice",
)

# ── Forbidden field names (trade-like semantics) ──────────────────────────────

FORBIDDEN_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "tradability_score",
        "alpha_score",
        "edge_score",
        "opportunity_score",
        "trade_score",
        "execution_confidence",
        "expected_return",
        "fill_probability",
        "order_size",
        "slippage_score",
        "entry",
        "exit",
        "position_size",
        "leverage",
    }
)

# ── Forbidden non-signal phrases required in forbidden_use_notice ─────────────
# Each phrase must appear in the forbidden_use_notice field.

FORBIDDEN_USE_REQUIRED_PHRASES: tuple[str, ...] = (
    "not a trading signal",
    "not expected return",
    "not position sizing",
    "not execution instruction",
)

# ── Forbidden source artifact prefixes / substrings ──────────────────────────

_FORBIDDEN_REF_SUBSTRINGS: tuple[str, ...] = (
    "http://",
    "https://",
    "api.",
    "wallet",
    "private_key",
    "credential",
    "secret",
)


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResolutionAmbiguityLabelValidationIssue:
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ResolutionAmbiguityLabelValidationResult:
    is_valid: bool
    errors: tuple[ResolutionAmbiguityLabelValidationIssue, ...]
    warnings: tuple[ResolutionAmbiguityLabelValidationIssue, ...]


# ── Internal helpers ──────────────────────────────────────────────────────────


def _err(
    field: str,
    code: str,
    message: str,
    errors: list[ResolutionAmbiguityLabelValidationIssue],
) -> None:
    errors.append(ResolutionAmbiguityLabelValidationIssue(field, code, message))


def _warn(
    field: str,
    code: str,
    message: str,
    warnings: list[ResolutionAmbiguityLabelValidationIssue],
) -> None:
    warnings.append(ResolutionAmbiguityLabelValidationIssue(field, code, message))


def _check_iso8601(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


# ── Public validation ─────────────────────────────────────────────────────────


def validate_resolution_ambiguity_label(
    label: Mapping[str, Any],
) -> ResolutionAmbiguityLabelValidationResult:
    """Validate a single resolution ambiguity label record.

    Returns a ResolutionAmbiguityLabelValidationResult with is_valid=True only
    if there are zero errors. Warnings are informational and do not affect is_valid.
    """
    errors: list[ResolutionAmbiguityLabelValidationIssue] = []
    warnings: list[ResolutionAmbiguityLabelValidationIssue] = []

    present_fields = set(label.keys())

    # ── 8.1 Required fields and unknown extra fields ───────────────────────────
    for field in REQUIRED_FIELDS:
        if field not in present_fields:
            _err(field, "MISSING_REQUIRED_FIELD", f"Required field '{field}' is missing.", errors)

    extra_fields = present_fields - set(REQUIRED_FIELDS)
    for field in sorted(extra_fields):
        if field in FORBIDDEN_FIELD_NAMES:
            _err(
                field,
                "FORBIDDEN_FIELD",
                f"Field '{field}' is a forbidden trade-like field name.",
                errors,
            )
        else:
            _err(
                field,
                "UNKNOWN_EXTRA_FIELD",
                f"Field '{field}' is not in the required schema and must be removed.",
                errors,
            )

    # ── Empty critical identifiers ─────────────────────────────────────────────
    for crit in ("label_id", "market_id"):
        val = label.get(crit)
        if crit in present_fields and (not isinstance(val, str) or not val.strip()):
            _err(crit, "EMPTY_CRITICAL_IDENTIFIER", f"'{crit}' must be a non-empty string.", errors)

    # ── 8.2 Allowed enum values ────────────────────────────────────────────────
    review_status = label.get("review_status")
    if "review_status" in present_fields:
        if review_status not in ALLOWED_REVIEW_STATUSES:
            _err(
                "review_status",
                "INVALID_REVIEW_STATUS",
                f"'review_status' value '{review_status}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_REVIEW_STATUSES)}",
                errors,
            )

    ambiguity_severity = label.get("ambiguity_severity")
    if "ambiguity_severity" in present_fields:
        if ambiguity_severity not in ALLOWED_SEVERITY_VALUES:
            _err(
                "ambiguity_severity",
                "INVALID_AMBIGUITY_SEVERITY",
                f"'ambiguity_severity' value '{ambiguity_severity}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_SEVERITY_VALUES)}",
                errors,
            )

    reviewer_confidence = label.get("reviewer_confidence")
    if "reviewer_confidence" in present_fields:
        if reviewer_confidence not in ALLOWED_CONFIDENCE_VALUES:
            _err(
                "reviewer_confidence",
                "INVALID_REVIEWER_CONFIDENCE",
                f"'reviewer_confidence' value '{reviewer_confidence}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_CONFIDENCE_VALUES)}",
                errors,
            )

    ambiguity_categories = label.get("ambiguity_categories")
    if "ambiguity_categories" in present_fields:
        if not isinstance(ambiguity_categories, list):
            _err(
                "ambiguity_categories",
                "INVALID_AMBIGUITY_CATEGORIES_TYPE",
                "'ambiguity_categories' must be an array.",
                errors,
            )
        else:
            for cat in ambiguity_categories:
                if cat not in ALLOWED_AMBIGUITY_CATEGORIES:
                    _err(
                        "ambiguity_categories",
                        "INVALID_AMBIGUITY_CATEGORY",
                        f"Unknown ambiguity category: '{cat}'. "
                        f"Allowed: {sorted(ALLOWED_AMBIGUITY_CATEGORIES)}",
                        errors,
                    )

    # ── 8.3 Manual review gate ─────────────────────────────────────────────────
    manual_review_required = label.get("manual_review_required")
    if "manual_review_required" in present_fields and "review_status" in present_fields:
        if review_status == "REVIEWED_CLEAR":
            # manual_review_required may be false; ambiguity_categories should be empty;
            # ambiguity_severity should be NONE.
            if isinstance(ambiguity_categories, list) and len(ambiguity_categories) > 0:
                _err(
                    "ambiguity_categories",
                    "REVIEWED_CLEAR_WITH_CATEGORIES",
                    "When 'review_status' is 'REVIEWED_CLEAR', 'ambiguity_categories' should be empty.",
                    errors,
                )
            if ambiguity_severity is not None and ambiguity_severity != "NONE":
                _err(
                    "ambiguity_severity",
                    "REVIEWED_CLEAR_WITH_NON_NONE_SEVERITY",
                    "When 'review_status' is 'REVIEWED_CLEAR', 'ambiguity_severity' should be 'NONE'.",
                    errors,
                )
        elif review_status in ALLOWED_REVIEW_STATUSES:
            # For all other valid statuses, manual_review_required must be true.
            if manual_review_required is not True:
                _err(
                    "manual_review_required",
                    "MANUAL_REVIEW_REQUIRED_MUST_BE_TRUE",
                    f"'manual_review_required' must be true when 'review_status' is '{review_status}'.",
                    errors,
                )

        if review_status == "INSUFFICIENT_LOCAL_EVIDENCE":
            if ambiguity_severity != "UNKNOWN":
                _err(
                    "ambiguity_severity",
                    "INSUFFICIENT_EVIDENCE_SEVERITY_MUST_BE_UNKNOWN",
                    "When 'review_status' is 'INSUFFICIENT_LOCAL_EVIDENCE', "
                    "'ambiguity_severity' must be 'UNKNOWN'.",
                    errors,
                )
            if reviewer_confidence != "LOW":
                _err(
                    "reviewer_confidence",
                    "INSUFFICIENT_EVIDENCE_CONFIDENCE_MUST_BE_LOW",
                    "When 'review_status' is 'INSUFFICIENT_LOCAL_EVIDENCE', "
                    "'reviewer_confidence' must be 'LOW'.",
                    errors,
                )

    # ── 8.4 Advisory label and forbidden-use notice ────────────────────────────
    advisory_label = label.get("advisory_label")
    if "advisory_label" in present_fields:
        if advisory_label != ADVISORY_LABEL:
            _err(
                "advisory_label",
                "WRONG_ADVISORY_LABEL",
                f"'advisory_label' must be exactly '{ADVISORY_LABEL}'. "
                f"Got: '{advisory_label}'",
                errors,
            )

    forbidden_use_notice = label.get("forbidden_use_notice")
    if "forbidden_use_notice" in present_fields:
        if not isinstance(forbidden_use_notice, str) or not forbidden_use_notice.strip():
            _err(
                "forbidden_use_notice",
                "MISSING_FORBIDDEN_USE_NOTICE",
                "'forbidden_use_notice' must be a non-empty string.",
                errors,
            )
        else:
            notice_lower = forbidden_use_notice.lower()
            for phrase in FORBIDDEN_USE_REQUIRED_PHRASES:
                if phrase not in notice_lower:
                    _err(
                        "forbidden_use_notice",
                        "MISSING_REQUIRED_NON_SIGNAL_PHRASE",
                        f"'forbidden_use_notice' must include the phrase: '{phrase}'.",
                        errors,
                    )

    # ── 8.5 Source artifact references ─────────────────────────────────────────
    source_artifact_refs = label.get("source_artifact_refs")
    if "source_artifact_refs" in present_fields:
        if not isinstance(source_artifact_refs, list) or len(source_artifact_refs) == 0:
            _err(
                "source_artifact_refs",
                "EMPTY_SOURCE_ARTIFACT_REFS",
                "'source_artifact_refs' must be a non-empty array of strings.",
                errors,
            )
        else:
            for ref in source_artifact_refs:
                if not isinstance(ref, str):
                    _err(
                        "source_artifact_refs",
                        "NON_STRING_SOURCE_REF",
                        f"Each source artifact ref must be a string. Got: {type(ref).__name__}",
                        errors,
                    )
                    continue
                ref_lower = ref.lower()
                for forbidden in _FORBIDDEN_REF_SUBSTRINGS:
                    if forbidden in ref_lower:
                        _err(
                            "source_artifact_refs",
                            "FORBIDDEN_SOURCE_REF",
                            f"Source artifact ref '{ref}' contains forbidden substring "
                            f"'{forbidden}'. Only local/offline references are allowed.",
                            errors,
                        )
                        break

    # ── 8.6 other_manual_review_issue requires evidence_notes ─────────────────
    if isinstance(ambiguity_categories, list) and "other_manual_review_issue" in ambiguity_categories:
        evidence_notes = label.get("evidence_notes")
        if not isinstance(evidence_notes, str) or not evidence_notes.strip():
            _err(
                "evidence_notes",
                "OTHER_CATEGORY_REQUIRES_EVIDENCE_NOTES",
                "When 'other_manual_review_issue' is in 'ambiguity_categories', "
                "'evidence_notes' must be a non-empty string.",
                errors,
            )

    # ── 8.7 Timestamp ──────────────────────────────────────────────────────────
    reviewed_at_utc = label.get("reviewed_at_utc")
    if "reviewed_at_utc" in present_fields:
        if not _check_iso8601(reviewed_at_utc):
            _err(
                "reviewed_at_utc",
                "UNPARSEABLE_TIMESTAMP",
                f"'reviewed_at_utc' value '{reviewed_at_utc}' is not a parseable ISO-8601 timestamp.",
                errors,
            )

    return ResolutionAmbiguityLabelValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_resolution_ambiguity_labels(
    labels: Iterable[Mapping[str, Any]],
) -> list[ResolutionAmbiguityLabelValidationResult]:
    """Validate a collection of resolution ambiguity label records.

    Returns one ResolutionAmbiguityLabelValidationResult per input label.
    Does not raise; errors are captured in each result.
    """
    return [validate_resolution_ambiguity_label(label) for label in labels]


def load_resolution_ambiguity_label_records(path: pathlib.Path) -> list[dict]:
    """Read label records from a local JSON array or JSONL file.

    Read-only. Does not write files or create directories.
    Does not call network. Does not infer labels.
    Returns raw records without validation or feature extraction.
    Raises ValueError for unsupported extension or parse errors.
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array in {path}, got {type(data).__name__}"
            )
        return data
    elif suffix in (".jsonl", ".ndjson"):
        records: list[dict] = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {lineno} of {path}: {exc}"
                ) from exc
            if not isinstance(obj, dict):
                raise ValueError(
                    f"Expected a JSON object on line {lineno} of {path}, "
                    f"got {type(obj).__name__}"
                )
            records.append(obj)
        return records
    else:
        raise ValueError(
            f"Unsupported file extension '{suffix}' for {path}. "
            "Expected .json or .jsonl"
        )
