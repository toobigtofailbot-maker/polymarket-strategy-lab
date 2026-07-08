"""In-memory Hermes candidate-review human decision and follow-up records.

Implements WP123 as a deterministic local/offline/advisory-only record layer.
Accepts explicit caller-supplied in-memory mappings for human decision records
and manual follow-up research task records. Validates required fields, labels,
safety flags, human review, non-authority notices, raw/free-form metadata, and
forbidden boundary content. Invalid input fails closed with empty public record
outputs and neutral diagnostics.

Stdlib-only. No file I/O. No network. No subprocess. No CLI. No storage.
No Hermes runtime. No prompt execution. No credentials. No parser, loader, writer,
report/export pipeline, paper/live/execution/risk/order,
scheduler/dashboard/bot-loop/runtime behavior. Added in WP123.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_HUMAN_DECISION_LABELS: frozenset[str] = frozenset({
    "ACCEPT_FOR_RESEARCH_MEMORY_ONLY",
    "REJECT_FOR_INSUFFICIENT_EVIDENCE",
    "REJECT_FOR_UNSUPPORTED_CLAIMS",
    "REJECT_FOR_RESOLUTION_AMBIGUITY",
    "REJECT_FOR_STALE_OR_MISSING_DATA",
    "REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT",
    "NEEDS_MORE_EVIDENCE",
    "NEEDS_SOURCE_RECHECK",
    "NEEDS_FALSIFICATION_CHECK",
    "DEFER_PENDING_MORE_CONTEXT",
})

ALLOWED_FOLLOW_UP_TASK_LABELS: frozenset[str] = frozenset({
    "SOURCE_RECHECK_TASK",
    "EVIDENCE_GAP_TASK",
    "MISSING_DATA_TASK",
    "UNCERTAINTY_REDUCTION_TASK",
    "FALSIFICATION_CHECK_TASK",
    "RESOLUTION_RULE_REVIEW_TASK",
    "CROSS_MARKET_CONTEXT_TASK",
    "WALLET_SIGNAL_CONTEXT_TASK",
    "MICROSTRUCTURE_CONTEXT_TASK",
    "OPERATOR_REVIEW_TASK",
})

REQUIRED_HUMAN_DECISION_RECORD_FIELDS: tuple[str, ...] = (
    "decision_id",
    "source_wp_context",
    "source_research_question_record_reference",
    "source_advisory_output_validation_receipt_reference",
    "decision_label",
    "decision_basis",
    "accepted_findings",
    "rejected_findings",
    "unresolved_questions",
    "evidence_references_relied_on",
    "uncertainty_notes",
    "limitations",
    "falsification_checks_completed",
    "follow_up_research_tasks",
    "human_review_required",
    "created_by_operator_note",
    "non_authority_notice",
    "safety_flags",
)

REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS: tuple[str, ...] = (
    "task_id",
    "source_wp_context",
    "source_human_decision_reference",
    "task_label",
    "task_question",
    "evidence_to_check",
    "source_references_to_revisit",
    "missing_data_to_resolve",
    "uncertainty_to_reduce",
    "falsification_check_to_perform",
    "blocking_reason",
    "next_manual_step",
    "human_review_required",
    "created_by_operator_note",
    "non_authority_notice",
    "safety_flags",
)

REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS: tuple[str, ...] = (
    "advisory_only",
    "manual_only",
    "local_only",
    "offline_only",
    "human_review_required",
    "no_execution_authority",
    "no_runtime_authority",
    "no_credential_authority",
    "no_paper_or_live_authority",
    "no_prompt_execution",
    "no_file_or_network",
    "no_strategy_promotion_authority",
    "no_pr_approval_authority",
    "no_storage_or_writer_authority",
    "no_advisory_output_as_fact",
    "no_automated_task_authority",
)

_RAW_METADATA_KEYS: frozenset[str] = frozenset({
    "raw_metadata",
    "free_form_metadata",
    "caller_metadata",
    "arbitrary_metadata",
    "raw_input",
    "untrusted_input",
    "notes_raw",
    "warnings_raw",
    "reason_text_raw",
    "custom",
    "extras",
    "metadata",
    "freeform",
    "extra",
    "context",
    "custom_fields",
    "raw_response",
    "model_response",
    "prompt",
    "completion",
    "raw",
    "free_form",
    "arbitrary",
})

_FORBIDDEN_TERMS: tuple[str, ...] = (
    "buy",
    "sell",
    "hold",
    "short",
    "trade",
    "trading",
    "order",
    "execute",
    "execution",
    "entry",
    "exit",
    "stop loss",
    "take profit",
    "position size",
    "allocation",
    "expected return",
    "fair value",
    "alpha",
    "edge",
    "confidence to trade",
    "trade ready",
    "tradable",
    "tradability",
    "paper ready",
    "live ready",
    "deployment ready",
    "strategy promotion",
    "strategy promoted",
    "approve pr",
    "pr approval",
    "merge ready",
    "risk override",
    "execution authority",
    "implementation approval",
    "credential",
    "private key",
    "api key",
    "secret",
    "passphrase",
    "wallet key",
    "account endpoint",
    "private endpoint",
    "account state",
    "order state",
    "paper state",
    "live state",
    "runtime logs",
    "prompt runner",
    "prompt execution",
    "model call",
    "provider",
    "hermes runtime",
    "scheduler",
    "bot loop",
    "daemon",
    "network poller",
    "dashboard",
    "automated task",
    "auto task",
    "background task",
    "file writer",
    "storage path",
    "parser",
    "loader",
    "report writer",
    "exporter",
    "cli command",
)

_BOUNDARY_KEY_EXCEPTIONS: frozenset[str] = frozenset({
    "decision_label",
    "task_label",
    "non_authority_notice",
    "safety_flags",
    *ALLOWED_HUMAN_DECISION_LABELS,
    *ALLOWED_FOLLOW_UP_TASK_LABELS,
    *REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS,
})

_BOUNDARY_VALUE_EXEMPT_KEYS: frozenset[str] = frozenset({
    "non_authority_notice",
})

_NON_AUTHORITY_REQUIRED_FRAGMENTS: tuple[str, ...] = (
    "advisory only",
    "manual",
    "local",
    "offline",
    "human review required",
    "not fact without source review",
    "not a trade signal",
    "not strategy promotion",
    "not paper readiness",
    "not live readiness",
    "not execution",
    "not risk",
    "not order authority",
    "not pr approval",
    "not merge readiness",
    "not credential permission",
    "not account access",
    "not private-state access",
    "not hermes runtime",
    "not prompt runner",
    "not storage/writer/export authority",
    "not automated task authority",
)

_NON_AUTHORITY_PERMISSION_PHRASES: tuple[str, ...] = (
    "authorizes",
    "authorized to",
    "grants",
    "permission to",
    "approved for",
    "may execute",
    "can execute",
    "paper ready",
    "live ready",
    "deployment ready",
    "merge ready",
    "approve pr",
    "pr approved",
    "trade ready",
    "strategy promoted",
    "automated task",
)


@dataclass(frozen=True)
class HermesCandidateReviewHumanDecisionRecordResult:
    """Validation result for a candidate-review human decision record."""

    is_valid: bool
    decision_record: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    decision_label: str | None
    safety_flags: dict[str, bool]


@dataclass(frozen=True)
class HermesCandidateReviewFollowUpResearchTaskRecordResult:
    """Validation result for a candidate-review follow-up research task record."""

    is_valid: bool
    follow_up_task_record: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    task_label: str | None
    safety_flags: dict[str, bool]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _scan_raw_metadata(value: object, errors: list[str], depth: int = 0) -> None:
    if depth > 20:
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in _RAW_METADATA_KEYS:
                errors.append("RAW_METADATA_NOT_ALLOWED")
                return
            _scan_raw_metadata(child, errors, depth + 1)
            if errors:
                return
    elif isinstance(value, (list, tuple)):
        for child in value:
            _scan_raw_metadata(child, errors, depth + 1)
            if errors:
                return


def _scan_forbidden(value: object, errors: list[str], parent_key: str | None = None) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text not in _BOUNDARY_KEY_EXCEPTIONS:
                normalized_key = _normalize(key_text)
                for term in _FORBIDDEN_TERMS:
                    if term in normalized_key:
                        errors.append("FORBIDDEN_CONTENT")
                        return
            if key_text in _BOUNDARY_VALUE_EXEMPT_KEYS:
                continue
            _scan_forbidden(child, errors, key_text)
            if errors:
                return
    elif isinstance(value, (list, tuple)):
        for child in value:
            _scan_forbidden(child, errors, parent_key)
            if errors:
                return
    elif isinstance(value, str):
        if value in ALLOWED_HUMAN_DECISION_LABELS or value in ALLOWED_FOLLOW_UP_TASK_LABELS:
            return
        normalized_value = _normalize(value)
        for term in _FORBIDDEN_TERMS:
            if term in normalized_value:
                errors.append("FORBIDDEN_CONTENT")
                return


def _invalid_decision_result(
    errors: tuple[str, ...],
) -> HermesCandidateReviewHumanDecisionRecordResult:
    return HermesCandidateReviewHumanDecisionRecordResult(
        is_valid=False,
        decision_record={},
        errors=errors,
        warnings=(),
        decision_label=None,
        safety_flags={},
    )


def _invalid_task_result(
    errors: tuple[str, ...],
) -> HermesCandidateReviewFollowUpResearchTaskRecordResult:
    return HermesCandidateReviewFollowUpResearchTaskRecordResult(
        is_valid=False,
        follow_up_task_record={},
        errors=errors,
        warnings=(),
        task_label=None,
        safety_flags={},
    )


def _validate_required_fields(
    record_data: Mapping[str, Any],
    required_fields: tuple[str, ...],
    errors: list[str],
) -> None:
    for field in required_fields:
        if field not in record_data:
            errors.append("MISSING_REQUIRED_FIELD")
            return
        value = record_data[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append("INVALID_REQUIRED_FIELD")
            return


def _validate_safety_flags(record_data: Mapping[str, Any], errors: list[str]) -> None:
    safety_flags = record_data.get("safety_flags")
    if not isinstance(safety_flags, Mapping):
        errors.append("INVALID_SAFETY_FLAG")
        return
    for flag in REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS:
        if safety_flags.get(flag) is not True:
            errors.append("INVALID_SAFETY_FLAG")
            return


def _validate_human_review(record_data: Mapping[str, Any], errors: list[str]) -> None:
    if record_data.get("human_review_required") is not True:
        errors.append("HUMAN_REVIEW_REQUIRED")


def _validate_non_authority_notice(record_data: Mapping[str, Any], errors: list[str]) -> None:
    notice = record_data.get("non_authority_notice")
    if not isinstance(notice, str) or not notice.strip():
        errors.append("INVALID_NON_AUTHORITY_NOTICE")
        return
    normalized = _normalize(notice)
    for phrase in _NON_AUTHORITY_PERMISSION_PHRASES:
        if phrase not in normalized:
            continue
        if phrase == "automated task" and "not automated task" in normalized:
            continue
        errors.append("INVALID_NON_AUTHORITY_NOTICE")
        return
    for fragment in _NON_AUTHORITY_REQUIRED_FRAGMENTS:
        if _normalize(fragment) not in normalized:
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return


def _sanitized_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS}


def validate_candidate_review_human_decision_record(
    decision_data: Mapping[str, Any],
) -> HermesCandidateReviewHumanDecisionRecordResult:
    """Validate an in-memory candidate-review human decision record."""
    if not isinstance(decision_data, Mapping):
        return _invalid_decision_result(("UNSUPPORTED_INPUT_SHAPE",))

    errors: list[str] = []

    _scan_raw_metadata(decision_data, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    _scan_forbidden(decision_data, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    _validate_required_fields(decision_data, REQUIRED_HUMAN_DECISION_RECORD_FIELDS, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    _validate_safety_flags(decision_data, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    decision_label = decision_data.get("decision_label")
    if decision_label not in ALLOWED_HUMAN_DECISION_LABELS:
        return _invalid_decision_result(("INVALID_DECISION_LABEL",))

    _validate_human_review(decision_data, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    _validate_non_authority_notice(decision_data, errors)
    if errors:
        return _invalid_decision_result(tuple(dict.fromkeys(errors)))

    sanitized_flags = _sanitized_flags()
    sanitized_record: dict[str, Any] = {}
    for field in REQUIRED_HUMAN_DECISION_RECORD_FIELDS:
        if field == "safety_flags":
            sanitized_record[field] = sanitized_flags
        else:
            sanitized_record[field] = decision_data[field]

    return HermesCandidateReviewHumanDecisionRecordResult(
        is_valid=True,
        decision_record=sanitized_record,
        errors=(),
        warnings=(),
        decision_label=str(decision_label),
        safety_flags=sanitized_flags,
    )


def build_candidate_review_human_decision_record(
    decision_data: Mapping[str, Any],
) -> HermesCandidateReviewHumanDecisionRecordResult:
    """Build and validate a human decision record from caller data."""
    return validate_candidate_review_human_decision_record(decision_data)


def assert_candidate_review_human_decision_record(
    decision_data: Mapping[str, Any],
) -> HermesCandidateReviewHumanDecisionRecordResult:
    """Assert that decision_data produces a valid human decision record."""
    result = validate_candidate_review_human_decision_record(decision_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_HUMAN_DECISION_RECORD: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result


def validate_candidate_review_follow_up_research_task_record(
    task_data: Mapping[str, Any],
) -> HermesCandidateReviewFollowUpResearchTaskRecordResult:
    """Validate an in-memory candidate-review follow-up research task record."""
    if not isinstance(task_data, Mapping):
        return _invalid_task_result(("UNSUPPORTED_INPUT_SHAPE",))

    errors: list[str] = []

    _scan_raw_metadata(task_data, errors)
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    _scan_forbidden(task_data, errors)
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    _validate_required_fields(
        task_data, REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS, errors
    )
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    _validate_safety_flags(task_data, errors)
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    task_label = task_data.get("task_label")
    if task_label not in ALLOWED_FOLLOW_UP_TASK_LABELS:
        return _invalid_task_result(("INVALID_TASK_LABEL",))

    _validate_human_review(task_data, errors)
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    _validate_non_authority_notice(task_data, errors)
    if errors:
        return _invalid_task_result(tuple(dict.fromkeys(errors)))

    sanitized_flags = _sanitized_flags()
    sanitized_record: dict[str, Any] = {}
    for field in REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS:
        if field == "safety_flags":
            sanitized_record[field] = sanitized_flags
        else:
            sanitized_record[field] = task_data[field]

    return HermesCandidateReviewFollowUpResearchTaskRecordResult(
        is_valid=True,
        follow_up_task_record=sanitized_record,
        errors=(),
        warnings=(),
        task_label=str(task_label),
        safety_flags=sanitized_flags,
    )


def build_candidate_review_follow_up_research_task_record(
    task_data: Mapping[str, Any],
) -> HermesCandidateReviewFollowUpResearchTaskRecordResult:
    """Build and validate a follow-up research task record from caller data."""
    return validate_candidate_review_follow_up_research_task_record(task_data)


def assert_candidate_review_follow_up_research_task_record(
    task_data: Mapping[str, Any],
) -> HermesCandidateReviewFollowUpResearchTaskRecordResult:
    """Assert that task_data produces a valid follow-up research task record."""
    result = validate_candidate_review_follow_up_research_task_record(task_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_FOLLOW_UP_RESEARCH_TASK_RECORD: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result
