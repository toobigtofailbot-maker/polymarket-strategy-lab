"""Local/offline/read-only human review label record validator.

Validates whether a human review label record dictionary has the required
fields, safe workflow state, safety flags, and no forbidden trading/performance
or automation fields.

Does not load label files, edit labels, automate labels, change scores, report
calibration metrics, or access the network. Stdlib-only. No file I/O.

Added in WP74.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


_ADVISORY_LABEL = (
    "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL — This validator checks human "
    "review label record structure for required fields and safe values only. "
    "It does not evaluate trading performance, profitability, signal quality, "
    "scoring weights, automated label logic, or execution behavior."
)

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "_notice",
    "_schema_version",
    "_status",
    "identity",
    "review",
    "safety",
)

EXPECTED_NOTICE: str = "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL"
EXPECTED_SCHEMA_VERSION: str = "HUMAN_REVIEW_LABEL_RECORD_V1"

REQUIRED_IDENTITY_FIELDS: tuple[str, ...] = (
    "market_id",
    "condition_id",
    "question",
    "snapshot_time_utc",
)

REQUIRED_REVIEW_FIELDS: tuple[str, ...] = (
    "review_time_utc",
    "reviewer_id_or_alias",
    "workflow_state",
    "human_review_usefulness_label",
    "confidence_level",
    "primary_reason",
    "secondary_reasons",
    "requires_followup_review",
    "review_notes",
)

ALLOWED_WORKFLOW_STATES: frozenset[str] = frozenset({
    "NOT_REVIEWED",
    "IN_REVIEW",
    "LABEL_APPLIED",
    "NEEDS_SECOND_REVIEW",
    "EXCLUDED_FROM_CALIBRATION",
})

FORBIDDEN_WORKFLOW_STATES: frozenset[str] = frozenset({
    "AUTO_LABELED_BY_LLM",
    "AUTO_LABELED",
    "LLM_LABELED",
})

ALLOWED_USEFULNESS_LABELS: frozenset[str] = frozenset({
    "USEFUL_RESEARCH_TARGET",
    "PARTIALLY_USEFUL_RESEARCH_TARGET",
    "NOT_USEFUL_DATA_TOO_WEAK",
    "NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS",
    "NOT_USEFUL_DUPLICATE_OR_OVERLAP",
    "NOT_REVIEWED",
    "REVIEW_BLOCKED_INSUFFICIENT_CONTEXT",
})

ALLOWED_CONFIDENCE_LEVELS: frozenset[str] = frozenset({
    "LOW",
    "MEDIUM",
    "HIGH",
    "NOT_APPLICABLE",
})

ALLOWED_PRIMARY_REASONS: frozenset[str] = frozenset({
    "SOURCE_CLARITY",
    "RESOLUTION_RULE_CLARITY",
    "DATA_COMPLETENESS",
    "MARKET_OVERLAP_CONTEXT",
    "QUEUE_BUCKET_RELEVANCE",
    "AMBIGUITY_TOO_HIGH",
    "SOURCE_MISSING",
    "OUTCOME_MAPPING_UNCLEAR",
    "DUPLICATE_OR_OVERLAP",
    "NOT_ENOUGH_CONTEXT",
})

REQUIRED_SAFETY_FLAGS: tuple[str, ...] = (
    "manual_only",
    "not_automated",
    "no_trading_signal",
    "no_score_change",
    "no_execution",
)

FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset({
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
    "auto_label",
    "llm_label",
    "automated_label",
    "score_change",
    "execution",
})

FORBIDDEN_STRING_VALUES: frozenset[str] = frozenset({
    "AUTO_LABELED_BY_LLM",
    "TRADE_SIGNAL",
    "BUY",
    "SELL",
    "PROFITABLE",
})

_UTC_SUFFIX_RE = re.compile(r"Z$")


@dataclass(frozen=True)
class HumanReviewLabelValidationResult:
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
    """Recursively collect keys matching FORBIDDEN_KEY_NAMES.

    The top-level 'safety' section is excluded because required safety flags
    use safe prefixed names (e.g. no_execution, no_trading_signal) that would
    otherwise match forbidden key terms.
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_path = f"{path}.{k}" if path else k
            if path == "" and k == "safety":
                continue
            if k.lower() in FORBIDDEN_KEY_NAMES:
                found.append(full_path)
            found.extend(_collect_forbidden_keys(v, full_path))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            found.extend(_collect_forbidden_keys(item, f"{path}[{i}]"))
    return found


def _collect_forbidden_values(obj: object, path: str = "") -> list[str]:
    """Recursively collect string values matching FORBIDDEN_STRING_VALUES."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_path = f"{path}.{k}" if path else k
            found.extend(_collect_forbidden_values(v, full_path))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            found.extend(_collect_forbidden_values(item, f"{path}[{i}]"))
    elif isinstance(obj, str) and obj in FORBIDDEN_STRING_VALUES:
        found.append(f"{path}={obj}")
    return found


def validate_human_review_label_record(
    record: Mapping[str, object],
) -> HumanReviewLabelValidationResult:
    """Validate a human review label record dict for structural completeness.

    Returns a HumanReviewLabelValidationResult. Does not raise on invalid
    records. Does not load files, write files, compute trading metrics,
    or access the network.
    """
    missing: list[str] = []
    invalid: list[str] = []
    warnings: list[str] = []

    # Top-level sections
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section not in record:
            missing.append(section)

    # _notice expected value
    notice = record.get("_notice")
    if notice is not None and notice != EXPECTED_NOTICE:
        invalid.append("_notice")

    # _schema_version expected value
    schema_version = record.get("_schema_version")
    if schema_version is not None and schema_version != EXPECTED_SCHEMA_VERSION:
        invalid.append("_schema_version")

    # Forbidden key scan (safety section excluded)
    for fkey in _collect_forbidden_keys(dict(record)):
        if fkey not in invalid:
            invalid.append(fkey)
        warnings.append(
            f"Forbidden trading/performance/automation key found: '{fkey}'. "
            "Human review label records must not contain trading, performance, "
            "or automation fields."
        )

    # Forbidden string value scan
    for fval in _collect_forbidden_values(dict(record)):
        warnings.append(
            f"Forbidden automation/trading value found: '{fval}'. "
            "Human review label records must not contain automation or trading values."
        )

    # identity section
    identity = record.get("identity")
    if isinstance(identity, dict):
        for field in REQUIRED_IDENTITY_FIELDS:
            if field not in identity:
                missing.append(f"identity.{field}")
            elif field.endswith("_utc"):
                if not _is_utc_timestamp(identity[field]):
                    invalid.append(f"identity.{field}")
            elif not _is_nonempty_string(identity[field]):
                invalid.append(f"identity.{field}")
    elif "identity" in record:
        invalid.append("identity")

    # review section
    review = record.get("review")
    if isinstance(review, dict):
        for field in REQUIRED_REVIEW_FIELDS:
            if field not in review:
                missing.append(f"review.{field}")

        # workflow_state enum check
        wf_state = review.get("workflow_state")
        if wf_state is not None:
            if wf_state in FORBIDDEN_WORKFLOW_STATES:
                invalid.append("review.workflow_state")
                warnings.append(
                    f"Forbidden workflow state '{wf_state}': automated labeling "
                    "is not authorized. Only manual workflow states are allowed."
                )
            elif wf_state not in ALLOWED_WORKFLOW_STATES:
                invalid.append("review.workflow_state")

        # human_review_usefulness_label enum check
        label = review.get("human_review_usefulness_label")
        if label is not None and label not in ALLOWED_USEFULNESS_LABELS:
            invalid.append("review.human_review_usefulness_label")

        # confidence_level enum check
        confidence = review.get("confidence_level")
        if confidence is not None and confidence not in ALLOWED_CONFIDENCE_LEVELS:
            invalid.append("review.confidence_level")

        # primary_reason enum check (all workflow states)
        primary_reason = review.get("primary_reason")
        if primary_reason is not None and primary_reason not in ALLOWED_PRIMARY_REASONS:
            invalid.append("review.primary_reason")

        # secondary_reasons: must be a list of allowed reason strings
        sec_reasons = review.get("secondary_reasons")
        if "secondary_reasons" in review:
            if not isinstance(sec_reasons, list):
                invalid.append("review.secondary_reasons")
            else:
                for sr in sec_reasons:
                    if sr not in ALLOWED_PRIMARY_REASONS:
                        invalid.append("review.secondary_reasons")
                        break

        # requires_followup_review: must be bool
        rfr = review.get("requires_followup_review")
        if "requires_followup_review" in review and not isinstance(rfr, bool):
            invalid.append("review.requires_followup_review")

        # review_notes: must be a string
        notes = review.get("review_notes")
        if "review_notes" in review and not isinstance(notes, str):
            invalid.append("review.review_notes")

        # review_time_utc: non-empty string ending with Z
        if "review_time_utc" in review:
            rtv = review["review_time_utc"]
            if not _is_utc_timestamp(rtv):
                invalid.append("review.review_time_utc")

        # reviewer_id_or_alias: non-empty string
        if "reviewer_id_or_alias" in review:
            if not _is_nonempty_string(review["reviewer_id_or_alias"]):
                invalid.append("review.reviewer_id_or_alias")

        # Cross-field rules
        if wf_state is not None and label is not None:
            # LABEL_APPLIED: label must not be NOT_REVIEWED
            if wf_state == "LABEL_APPLIED" and label == "NOT_REVIEWED":
                if "review.human_review_usefulness_label" not in invalid:
                    invalid.append("review.human_review_usefulness_label")
                warnings.append(
                    "Cross-field rule: workflow_state is LABEL_APPLIED but "
                    "human_review_usefulness_label is NOT_REVIEWED. "
                    "A completed review must have a non-NOT_REVIEWED label."
                )
            # NOT_REVIEWED workflow: label should be NOT_REVIEWED (warning, not invalid)
            if wf_state == "NOT_REVIEWED" and label != "NOT_REVIEWED":
                warnings.append(
                    f"Cross-field rule: workflow_state is NOT_REVIEWED but "
                    f"human_review_usefulness_label is '{label}'. "
                    "Expected NOT_REVIEWED label when workflow state is NOT_REVIEWED."
                )

        # LABEL_APPLIED: confidence must not be NOT_APPLICABLE
        if wf_state == "LABEL_APPLIED" and confidence is not None:
            if confidence == "NOT_APPLICABLE":
                if "review.confidence_level" not in invalid:
                    invalid.append("review.confidence_level")
                warnings.append(
                    "Cross-field rule: workflow_state is LABEL_APPLIED but "
                    "confidence_level is NOT_APPLICABLE. "
                    "A completed review must have an explicit confidence level."
                )

        # NEEDS_SECOND_REVIEW: requires_followup_review should be True (warning)
        if wf_state == "NEEDS_SECOND_REVIEW" and rfr is False:
            warnings.append(
                "Cross-field rule: workflow_state is NEEDS_SECOND_REVIEW but "
                "requires_followup_review is False. "
                "Expected requires_followup_review=True when second review is needed."
            )

    elif "review" in record:
        invalid.append("review")

    # safety section
    safety = record.get("safety")
    if isinstance(safety, dict):
        for flag in REQUIRED_SAFETY_FLAGS:
            if flag not in safety:
                missing.append(f"safety.{flag}")
            elif safety[flag] is not True:
                invalid.append(f"safety.{flag}")
    elif "safety" in record:
        invalid.append("safety")

    is_valid = not missing and not invalid

    return HumanReviewLabelValidationResult(
        is_valid=is_valid,
        missing_required_fields=tuple(missing),
        invalid_fields=tuple(invalid),
        warnings=tuple(warnings),
        advisory_label=_ADVISORY_LABEL,
    )
