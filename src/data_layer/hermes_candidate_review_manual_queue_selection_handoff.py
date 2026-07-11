"""Manual candidate-queue selection and research-question handoff contracts.

WP128 provides deterministic, in-memory validation/build/assert helpers for
explicit caller-supplied mappings.  It has no selection, ranking, question
generation, persistence, network, runtime, prompt, or trading authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_MANUAL_QUEUE_SELECTION_LABELS = frozenset({
    "SELECT_FOR_MANUAL_RESEARCH_QUESTION_DRAFT",
    "DEFER_PENDING_MORE_EVIDENCE",
    "DEFER_PENDING_SOURCE_RECHECK",
    "DEFER_PENDING_RESOLUTION_RULE_REVIEW",
    "REJECT_FOR_INSUFFICIENT_EVIDENCE",
    "REJECT_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
    "REJECT_FOR_DUPLICATE_RESEARCH_QUESTION",
    "RETURN_TO_MANUAL_QUEUE_REVIEW",
})
ALLOWED_MANUAL_QUEUE_SELECTION_REASON_LABELS = frozenset({
    "HUMAN_SELECTED_FOR_DEEPER_RESEARCH",
    "EVIDENCE_GAP_REQUIRES_RESEARCH",
    "SOURCE_CONFLICT_REQUIRES_RESEARCH",
    "RESOLUTION_AMBIGUITY_REQUIRES_RESEARCH",
    "SOURCE_PROVENANCE_REQUIRES_RESEARCH",
    "FALSIFICATION_CHECK_REQUIRES_RESEARCH",
    "CROSS_MARKET_CONTEXT_REQUIRES_RESEARCH",
    "WALLET_SIGNAL_CONTEXT_REQUIRES_RESEARCH",
    "MICROSTRUCTURE_CONTEXT_REQUIRES_RESEARCH",
    "STALE_OR_MISSING_DATA_REQUIRES_RESEARCH",
    "DUPLICATE_OR_ALREADY_COVERED",
    "INSUFFICIENT_CONTEXT_TO_SELECT",
})
ALLOWED_RESEARCH_QUESTION_HANDOFF_TYPES = frozenset({
    "RESOLUTION_RULE_AMBIGUITY",
    "EVIDENCE_QUALITY_GAP",
    "SOURCE_CONFLICT",
    "WALLET_SIGNAL_UNCERTAINTY",
    "CROSS_MARKET_INCONSISTENCY",
    "MARKET_STRUCTURE_MICROSTRUCTURE_CONCERN",
    "STALE_OR_MISSING_DATA_RISK",
    "OPERATOR_UNCERTAINTY_REQUIRING_DEEPER_RESEARCH",
    "SOURCE_PROVENANCE_WEAKNESS",
    "FALSIFICATION_CHECK_NEED",
})
REQUIRED_MANUAL_QUEUE_SELECTION_RECORD_FIELDS = (
    "selection_id", "source_wp_context", "source_queue_reference",
    "selected_candidate_reference", "selection_label", "selection_reason_labels",
    "human_selection_basis", "evidence_references_reviewed", "uncertainty_notes",
    "known_missing_data", "limitations", "duplicate_check_notes",
    "operator_next_manual_step", "human_review_required", "created_by_operator_note",
    "non_authority_notice", "safety_flags",
)
REQUIRED_RESEARCH_QUESTION_HANDOFF_FIELDS = (
    "handoff_id", "source_wp_context", "source_selection_record_reference",
    "selected_candidate_reference", "proposed_research_question",
    "proposed_research_question_type", "evidence_references_to_check",
    "uncertainty_notes", "known_missing_data", "limitations",
    "falsification_checks_to_perform", "operator_next_manual_step",
    "human_review_required", "created_by_operator_note", "non_authority_notice",
    "safety_flags",
)
REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS = (
    "advisory_only", "manual_only", "local_only", "offline_only",
    "human_review_required", "explicit_human_selection_only",
    "no_automated_selection", "no_scoring_or_ranking_authority",
    "no_priority_calculation_authority", "no_discovery_automation_authority",
    "no_market_data_ingestion_authority", "no_execution_authority",
    "no_runtime_authority", "no_credential_authority", "no_paper_or_live_authority",
    "no_prompt_execution", "no_file_or_network", "no_strategy_promotion_authority",
    "no_pr_approval_authority", "no_storage_or_writer_authority",
    "no_export_or_report_authority", "no_research_question_generation_authority",
)

_RAW_KEYS = frozenset({
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata",
    "raw_input", "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw",
    "custom", "extras", "metadata", "freeform", "extra", "context", "custom_fields",
    "raw_response", "model_response", "prompt", "completion", "raw", "free_form",
    "arbitrary",
})
_FORBIDDEN_TERMS = (
    "buy", "sell", "hold", "short", "trade", "trading", "order", "execute",
    "execution", "entry", "exit", "stop loss", "take profit", "position size",
    "allocation", "expected return", "fair value", "alpha", "edge",
    "confidence to trade", "tradable", "tradability", "trade ready", "paper ready",
    "live ready", "deployment ready", "strategy promotion", "strategy promoted",
    "approve pr", "pr approval", "merge ready", "risk override",
    "implementation approval", "execution authority", "research priority approved",
    "priority approved", "recommended candidate", "credential", "private key",
    "api key", "secret", "passphrase", "wallet key", "account endpoint",
    "private endpoint", "account state", "order state", "paper state", "live state",
    "runtime logs", "prompt runner", "prompt execution", "model call", "provider",
    "hermes runtime", "automated selection", "automatic selection", "auto select",
    "scheduler", "bot loop", "daemon", "network poller", "dashboard",
    "automated task", "background task", "discovery automation",
    "market data ingestion", "score", "scoring", "rank", "ranking", "priority score",
    "priority calculation", "recommendation engine", "parser", "loader", "file writer",
    "storage path", "report writer", "exporter", "cli command",
)
_NOTICE_FRAGMENTS = (
    "advisory only", "manual", "local", "offline", "human review required",
    "explicit human selection only", "not automated selection", "not scoring or ranking",
    "not priority calculation", "not discovery automation", "not market data ingestion",
    "not research question generation", "not execution", "not runtime",
    "not credentials", "not paper or live", "not prompt execution",
    "not file or network", "not strategy promotion", "not pr approval",
    "not storage or writer", "not export or report",
)
_PERMISSION_PHRASES = (
    "authorizes", "authorized to", "grants permission", "permission to", "approved for",
    "may execute", "can execute", "merge ready", "trade ready", "priority approved",
    "automatically selected", "recommended candidate",
)
_EXACT_EXCEPTIONS = frozenset({
    *ALLOWED_MANUAL_QUEUE_SELECTION_LABELS,
    *ALLOWED_MANUAL_QUEUE_SELECTION_REASON_LABELS,
    *ALLOWED_RESEARCH_QUESTION_HANDOFF_TYPES,
    *REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS,
    "non_authority_notice", "safety_flags",
})


@dataclass(frozen=True)
class HermesCandidateReviewManualQueueSelectionRecordResult:
    is_valid: bool
    selection_record: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    selection_label: str | None
    selection_reason_labels: tuple[str, ...]
    safety_flags: dict[str, bool]


@dataclass(frozen=True)
class HermesCandidateReviewResearchQuestionHandoffResult:
    is_valid: bool
    handoff_record: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    research_question_type: str | None
    safety_flags: dict[str, bool]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _scan(value: object, depth: int = 0, parent_key: str | None = None) -> str | None:
    if depth > 20:
        return "UNSUPPORTED_NESTING_DEPTH"
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _RAW_KEYS:
                return "RAW_METADATA_NOT_ALLOWED"
            if key_text not in _EXACT_EXCEPTIONS:
                normalized_key = _normalize(key_text)
                if any(term in normalized_key for term in _FORBIDDEN_TERMS):
                    return "FORBIDDEN_CONTENT"
            if key_text != "non_authority_notice":
                error = _scan(child, depth + 1, key_text)
                if error:
                    return error
    elif isinstance(value, (list, tuple)):
        for child in value:
            error = _scan(child, depth + 1, parent_key)
            if error:
                return error
    elif isinstance(value, str) and value not in _EXACT_EXCEPTIONS:
        normalized_value = _normalize(value)
        if any(term in normalized_value for term in _FORBIDDEN_TERMS):
            return "FORBIDDEN_CONTENT"
    return None


def _copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _copy_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_copy_value(child) for child in value]
    if isinstance(value, tuple):
        return tuple(_copy_value(child) for child in value)
    return value


def _validate_non_authority_notice(value: object) -> bool:
    """Allow required negations while rejecting forbidden notice remainder."""
    if not isinstance(value, str) or not value.strip():
        return False
    normalized_notice = _normalize(value)
    normalized_fragments = tuple(_normalize(fragment) for fragment in _NOTICE_FRAGMENTS)
    if any(fragment not in normalized_notice for fragment in normalized_fragments):
        return False
    if any(phrase in normalized_notice for phrase in _PERMISSION_PHRASES):
        return False

    remainder = normalized_notice
    for fragment in sorted(normalized_fragments, key=len, reverse=True):
        remainder = remainder.replace(fragment, " ")
    remainder = _normalize(remainder)
    return not any(term in remainder for term in _FORBIDDEN_TERMS)


def _common(data: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    error = _scan(data)
    if error:
        return error
    for field in fields:
        if field not in data:
            return "MISSING_REQUIRED_FIELD"
        value = data[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            return "INVALID_REQUIRED_FIELD"
    if data["human_review_required"] is not True:
        return "HUMAN_REVIEW_REQUIRED"
    flags = data["safety_flags"]
    if not isinstance(flags, Mapping):
        return "INVALID_SAFETY_FLAG"
    if any(flags.get(flag) is not True for flag in REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS):
        return "INVALID_SAFETY_FLAG"
    if not _validate_non_authority_notice(data["non_authority_notice"]):
        return "INVALID_NON_AUTHORITY_NOTICE"
    return None


def _invalid_selection(error: str) -> HermesCandidateReviewManualQueueSelectionRecordResult:
    return HermesCandidateReviewManualQueueSelectionRecordResult(False, {}, (error,), (), None, (), {})


def validate_candidate_review_manual_queue_selection_record(
    selection_data: Mapping[str, Any],
) -> HermesCandidateReviewManualQueueSelectionRecordResult:
    if not isinstance(selection_data, Mapping):
        return _invalid_selection("UNSUPPORTED_INPUT_SHAPE")
    error = _common(selection_data, REQUIRED_MANUAL_QUEUE_SELECTION_RECORD_FIELDS)
    if error:
        return _invalid_selection(error)
    label = selection_data["selection_label"]
    reasons = selection_data["selection_reason_labels"]
    if not isinstance(label, str) or label not in ALLOWED_MANUAL_QUEUE_SELECTION_LABELS:
        return _invalid_selection("INVALID_SELECTION_LABEL")
    if not isinstance(reasons, (list, tuple)) or not reasons:
        return _invalid_selection("INVALID_SELECTION_REASON_LABEL")
    if any(
        not isinstance(reason, str) or reason not in ALLOWED_MANUAL_QUEUE_SELECTION_REASON_LABELS
        for reason in reasons
    ):
        return _invalid_selection("INVALID_SELECTION_REASON_LABEL")
    flags = {flag: True for flag in REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS}
    record = {
        field: flags if field == "safety_flags" else _copy_value(selection_data[field])
        for field in REQUIRED_MANUAL_QUEUE_SELECTION_RECORD_FIELDS
    }
    return HermesCandidateReviewManualQueueSelectionRecordResult(
        True, record, (), (), str(label), tuple(reasons), flags
    )


def build_candidate_review_manual_queue_selection_record(
    selection_data: Mapping[str, Any],
) -> HermesCandidateReviewManualQueueSelectionRecordResult:
    return validate_candidate_review_manual_queue_selection_record(selection_data)


def assert_candidate_review_manual_queue_selection_record(
    selection_data: Mapping[str, Any],
) -> HermesCandidateReviewManualQueueSelectionRecordResult:
    result = validate_candidate_review_manual_queue_selection_record(selection_data)
    if not result.is_valid:
        raise ValueError("INVALID_MANUAL_QUEUE_SELECTION_RECORD")
    return result


def _invalid_handoff(error: str) -> HermesCandidateReviewResearchQuestionHandoffResult:
    return HermesCandidateReviewResearchQuestionHandoffResult(False, {}, (error,), (), None, {})


def validate_candidate_review_research_question_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionHandoffResult:
    if not isinstance(handoff_data, Mapping):
        return _invalid_handoff("UNSUPPORTED_INPUT_SHAPE")
    error = _common(handoff_data, REQUIRED_RESEARCH_QUESTION_HANDOFF_FIELDS)
    if error:
        return _invalid_handoff(error)
    question_type = handoff_data["proposed_research_question_type"]
    if not isinstance(handoff_data["proposed_research_question"], str):
        return _invalid_handoff("INVALID_REQUIRED_FIELD")
    if not isinstance(question_type, str) or question_type not in ALLOWED_RESEARCH_QUESTION_HANDOFF_TYPES:
        return _invalid_handoff("INVALID_RESEARCH_QUESTION_TYPE")
    flags = {flag: True for flag in REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS}
    record = {
        field: flags if field == "safety_flags" else _copy_value(handoff_data[field])
        for field in REQUIRED_RESEARCH_QUESTION_HANDOFF_FIELDS
    }
    return HermesCandidateReviewResearchQuestionHandoffResult(
        True, record, (), (), str(question_type), flags
    )


def build_candidate_review_research_question_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionHandoffResult:
    return validate_candidate_review_research_question_handoff(handoff_data)


def assert_candidate_review_research_question_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionHandoffResult:
    result = validate_candidate_review_research_question_handoff(handoff_data)
    if not result.is_valid:
        raise ValueError("INVALID_RESEARCH_QUESTION_HANDOFF")
    return result
