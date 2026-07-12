"""Deterministic in-memory contract for a manual research response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS = frozenset({
    "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
    "RESPONSE_INCOMPLETE_MISSING_SOURCES",
    "RESPONSE_INCOMPLETE_MISSING_CITATIONS",
    "RESPONSE_INCOMPLETE_EVIDENCE_CONFLICT",
    "RESPONSE_INCOMPLETE_MISSING_DATA",
    "RESPONSE_INCOMPLETE_FALSIFICATION_PENDING",
    "RESPONSE_REJECTED_UNSAFE_OR_FORBIDDEN_CONTENT",
    "RESPONSE_DEFERRED_PENDING_OPERATOR_ACTION",
})
ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS = frozenset({
    "QUESTION_RESTATEMENT", "SOURCE_SUMMARY", "RESOLUTION_RULE_ANALYSIS",
    "EVIDENCE_FOR", "EVIDENCE_AGAINST", "SOURCE_CONFLICTS", "UNCERTAINTIES",
    "MISSING_DATA", "FALSIFICATION_CHECKS", "LIMITATIONS",
    "WHAT_WOULD_CHANGE_THE_CONCLUSION", "OPERATOR_REVIEW_NOTES",
})
ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS = frozenset({
    "PRIMARY_SOURCE_REVIEWED", "OFFICIAL_SOURCE_REVIEWED",
    "SECONDARY_SOURCE_REVIEWED_WITH_DISCLOSURE", "SOURCE_DATE_RECORDED",
    "SOURCE_PROVENANCE_RECORDED", "SOURCE_FRESHNESS_RECORDED",
    "CONFLICTING_SOURCE_RECORDED", "SOURCE_UNAVAILABLE_RECORDED",
    "SOURCE_ACCESS_FAILURE_RECORDED", "UNCITED_MATERIAL_CLAIM_RECORDED",
})
ALLOWED_RESEARCH_COMPLETION_LABELS = frozenset({
    "REQUIRED_SECTIONS_PRESENT", "MATERIAL_CLAIMS_CITATION_STATUS_RECORDED",
    "EVIDENCE_FOR_RECORDED", "EVIDENCE_AGAINST_RECORDED",
    "UNCERTAINTIES_RECORDED", "MISSING_DATA_RECORDED",
    "FALSIFICATION_STATUS_RECORDED", "LIMITATIONS_RECORDED",
    "HUMAN_REVIEW_PENDING",
})
REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS = (
    "response_id", "source_wp_context", "source_request_reference",
    "source_briefing_packet_reference", "selected_candidate_reference",
    "response_label", "research_question", "research_question_type",
    "question_restatement", "source_summary", "resolution_rule_analysis",
    "evidence_for", "evidence_against", "source_conflicts", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "operator_review_notes",
    "cited_source_references", "source_assessment_labels", "completion_labels",
    "response_sections", "operator_next_manual_step", "reviewer_acknowledgement",
    "human_review_required", "created_by_operator_note", "non_authority_notice",
    "safety_flags",
)
REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS = (
    "advisory_only", "manual_only", "local_only", "offline_only", "read_only",
    "human_review_required", "explicit_caller_content_only", "response_contract_only",
    "no_prompt_generation", "no_prompt_execution", "no_model_or_provider_call",
    "no_hermes_runtime", "no_tool_selection", "no_tool_invocation",
    "no_network_or_api", "no_source_fetching", "no_source_verification_authority",
    "no_citation_verification_authority", "no_market_data_ingestion",
    "no_discovery_automation", "no_automated_selection",
    "no_scoring_or_ranking_authority", "no_priority_calculation_authority",
    "no_recommendation_authority", "no_probability_estimation_authority",
    "no_factual_correctness_authority", "no_factual_conclusion_authority",
    "no_strategy_authority", "no_execution_authority", "no_risk_authority",
    "no_credential_authority", "no_paper_or_live_authority",
    "no_strategy_promotion_authority", "no_pr_approval_authority",
    "no_storage_or_writer_authority", "no_export_or_report_authority",
    "no_cli_authority", "no_scheduler_or_background_authority",
)

_SCALARS = (
    "response_id", "source_wp_context", "source_request_reference",
    "source_briefing_packet_reference", "selected_candidate_reference",
    "research_question", "research_question_type", "question_restatement",
    "source_summary", "resolution_rule_analysis", "operator_review_notes",
    "operator_next_manual_step", "reviewer_acknowledgement",
    "created_by_operator_note", "non_authority_notice",
)
_SEQUENCES = (
    "evidence_for", "evidence_against", "source_conflicts", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "cited_source_references",
    "source_assessment_labels", "completion_labels", "response_sections",
)
_LABEL_FIELDS = {
    "source_assessment_labels": ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS,
    "completion_labels": ALLOWED_RESEARCH_COMPLETION_LABELS,
    "response_sections": ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS,
}
_RAW_KEYS = frozenset({
    "raw metadata", "free form metadata", "caller metadata", "arbitrary metadata",
    "raw input", "untrusted input", "raw response", "generated response",
    "model response", "provider response", "hermes response", "completion", "prompt",
    "prompt text", "system prompt", "tool plan", "tool call", "tool output", "custom",
    "extras", "metadata", "freeform", "extra", "context", "custom fields", "raw",
    "free form", "arbitrary", "payload", "response payload",
})
_FORBIDDEN = (
    "buy", "sell", "hold", "short", "long position", "trade", "trading", "order",
    "execute", "execution", "entry", "exit", "stop loss", "take profit",
    "position size", "allocation", "bet", "wager", "expected return", "expected value",
    "fair value", "alpha", "edge", "probability estimate", "fair probability",
    "model probability", "confidence to trade", "profit target", "profitable", "roi",
    "pnl forecast", "tradable", "trade ready", "execution ready", "paper ready",
    "live ready", "deployment ready", "strategy ready", "implementation ready",
    "strategy promotion", "approve pr", "pr approval", "merge ready", "risk override",
    "implementation approval", "research priority approved", "recommended candidate",
    "recommendation", "copy signal", "strategy signal", "credential", "private key",
    "api key", "secret", "passphrase", "mnemo" + "nic", "seed phrase", "wallet key",
    "account endpoint", "private endpoint", "account state", "order state", "paper state",
    "live state", "runtime logs", "prompt runner", "prompt execution", "generated prompt",
    "prompt ready", "model call", "provider call", "hermes runtime", "tool selection",
    "tool invocation", "tool call", "browsing session", "search execution",
    "generated response", "generated conclusion", "automatic research response",
    "advisory finding generated", "automated selection", "automatic selection",
    "auto select", "scheduler", "bot loop", "daemon", "network poller", "dashboard",
    "automated task", "background task", "discovery automation", "market data ingestion",
    "scoring", "ranking", "priority score", "priority calculation",
    "recommendation engine", "parser", "loader", "file writer", "storage path",
    "database write", "report writer", "exporter", "cli command",
)
_NOTICE_FRAGMENTS = (
    "advisory only", "manual", "local", "offline", "read only", "human review required",
    "explicit caller content only", "response contract only", "not prompt generation",
    "not prompt execution", "not model or provider", "not hermes", "not tool selection",
    "not tool invocation", "not network or api", "not source fetching",
    "not source verification", "not citation verification", "not market data ingestion",
    "not discovery automation", "not automated selection", "not scoring or ranking",
    "not priority calculation", "not recommendation", "not probability estimation",
    "not factual correctness", "not factual conclusion", "not strategy", "not execution",
    "not risk", "not credentials", "not paper or live", "not strategy promotion",
    "not pr approval", "not storage or writer", "not export or report", "not cli",
    "not scheduler or background task",
)
_PERMISSION = (
    "authorizes", "authorized to", "grants permission", "permission to", "approved for",
    "may execute", "can execute", "merge ready", "trade ready", "priority approved",
    "automatically selected", "generated by model", "prompt ready for execution",
    "tools may be invoked", "sources may be fetched", "citations are verified",
    "sources are verified", "factually correct", "approved conclusion", "recommended action",
)
_EXCEPTIONS = frozenset({
    *ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS,
    *ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS,
    *ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS,
    *ALLOWED_RESEARCH_COMPLETION_LABELS,
    *REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS,
    *REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS,
})


@dataclass(frozen=True)
class HermesCandidateReviewManualResearchResponseResult:
    is_valid: bool
    research_response: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    response_label: str | None
    source_assessment_labels: tuple[str, ...]
    completion_labels: tuple[str, ...]
    response_sections: tuple[str, ...]
    safety_flags: dict[str, bool]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _scan(value: object, depth: int = 0) -> str | None:
    if depth > 20:
        return "UNSUPPORTED_NESTING_DEPTH"
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            normalized_key = _normalize(key_text)
            if normalized_key in _RAW_KEYS:
                return "RAW_METADATA_NOT_ALLOWED"
            if key_text not in _EXCEPTIONS and any(term in normalized_key for term in _FORBIDDEN):
                return "FORBIDDEN_CONTENT"
            if key_text != "non_authority_notice":
                error = _scan(child, depth + 1)
                if error:
                    return error
    elif isinstance(value, (list, tuple)):
        for child in value:
            error = _scan(child, depth + 1)
            if error:
                return error
    elif isinstance(value, str) and value not in _EXCEPTIONS:
        if any(term in _normalize(value) for term in _FORBIDDEN):
            return "FORBIDDEN_CONTENT"
    return None


def _copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _copy(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_copy(child) for child in value]
    if isinstance(value, tuple):
        return tuple(_copy(child) for child in value)
    return value


def _valid_notice(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    notice = _normalize(value)
    fragments = tuple(_normalize(fragment) for fragment in _NOTICE_FRAGMENTS)
    for fragment in fragments:
        fragment_surface = notice
        for other in sorted(
            (item for item in fragments if item != fragment and fragment in item),
            key=len,
            reverse=True,
        ):
            fragment_surface = fragment_surface.replace(other, " ")
        if fragment not in fragment_surface:
            return False
    if any(phrase in notice for phrase in _PERMISSION):
        return False
    remainder = notice
    for fragment in sorted(fragments, key=len, reverse=True):
        remainder = remainder.replace(fragment, " ")
    return not any(term in _normalize(remainder) for term in _FORBIDDEN)


def _invalid(error: str) -> HermesCandidateReviewManualResearchResponseResult:
    return HermesCandidateReviewManualResearchResponseResult(
        False, {}, (error,), (), None, (), (), (), {}
    )


def validate_candidate_review_manual_research_response(
    response_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchResponseResult:
    if not isinstance(response_data, Mapping):
        return _invalid("UNSUPPORTED_INPUT_SHAPE")
    if any(key not in REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS for key in response_data):
        return _invalid("UNKNOWN_FIELD")
    if any(field not in response_data for field in REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS):
        return _invalid("MISSING_REQUIRED_FIELD")
    if any(not isinstance(response_data[field], str) or not response_data[field].strip()
           for field in _SCALARS):
        return _invalid("INVALID_REQUIRED_FIELD")
    for field in _SEQUENCES:
        value = response_data[field]
        if (not isinstance(value, (list, tuple)) or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)):
            return _invalid("INVALID_REQUIRED_FIELD")
    error = _scan(response_data)
    if error:
        return _invalid(error)
    label = response_data["response_label"]
    if not isinstance(label, str) or label not in ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS:
        return _invalid("INVALID_RESPONSE_LABEL")
    for field, allowed in _LABEL_FIELDS.items():
        values = response_data[field]
        if any(item not in allowed for item in values):
            return _invalid("INVALID_LABEL")
        if len(set(values)) != len(values):
            return _invalid("DUPLICATE_LABEL")
    if response_data["human_review_required"] is not True:
        return _invalid("HUMAN_REVIEW_REQUIRED")
    flags = response_data["safety_flags"]
    if not isinstance(flags, Mapping) or any(
        flags.get(flag) is not True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS
    ):
        return _invalid("INVALID_SAFETY_FLAG")
    if not _valid_notice(response_data["non_authority_notice"]):
        return _invalid("INVALID_NON_AUTHORITY_NOTICE")
    clean_flags = {flag: True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}
    result = {
        field: clean_flags if field == "safety_flags" else _copy(response_data[field])
        for field in REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS
    }
    return HermesCandidateReviewManualResearchResponseResult(
        True, result, (), (), label, tuple(response_data["source_assessment_labels"]),
        tuple(response_data["completion_labels"]), tuple(response_data["response_sections"]),
        clean_flags,
    )


def build_candidate_review_manual_research_response(
    response_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchResponseResult:
    return validate_candidate_review_manual_research_response(response_data)


def assert_candidate_review_manual_research_response(
    response_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchResponseResult:
    result = validate_candidate_review_manual_research_response(response_data)
    if not result.is_valid:
        raise ValueError("INVALID_MANUAL_RESEARCH_RESPONSE")
    return result
