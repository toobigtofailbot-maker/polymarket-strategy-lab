"""Deterministic in-memory contract for a manual research request.

This module only validates and copies explicit caller-supplied content.  It
does not generate or execute prompts, invoke tools, fetch sources, or produce
research findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_MANUAL_RESEARCH_REQUEST_LABELS = frozenset({
    "REQUEST_READY_FOR_MANUAL_RESEARCH", "REQUEST_NEEDS_SOURCE_RECHECK",
    "REQUEST_NEEDS_CITATION_REVIEW", "REQUEST_NEEDS_EVIDENCE_REVIEW",
    "REQUEST_NEEDS_SCOPE_REDUCTION", "REQUEST_DEFERRED_PENDING_CONTEXT",
    "REQUEST_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
})
ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS = frozenset({
    "PRIMARY_SOURCE_REQUIRED", "OFFICIAL_SOURCE_PREFERRED",
    "SECONDARY_SOURCE_ALLOWED_WITH_DISCLOSURE", "SOURCE_DATE_REQUIRED",
    "SOURCE_PROVENANCE_REQUIRED", "SOURCE_FRESHNESS_REQUIRED",
    "CONFLICTING_SOURCES_MUST_BE_DISCLOSED", "UNAVAILABLE_SOURCE_MUST_BE_REPORTED",
})
ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS = frozenset({
    "CITATION_REQUIRED_FOR_EACH_MATERIAL_CLAIM", "CITATION_MUST_IDENTIFY_SOURCE",
    "CITATION_MUST_PRESERVE_PUBLIC_REFERENCE", "UNCITED_MATERIAL_CLAIM_MUST_BE_FLAGGED",
    "SOURCE_CONFLICTS_MUST_BE_CITED", "SOURCE_ACCESS_FAILURE_MUST_BE_RECORDED",
})
ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS = frozenset({
    "EVIDENCE_FOR_REQUIRED", "EVIDENCE_AGAINST_REQUIRED", "UNCERTAINTIES_REQUIRED",
    "MISSING_DATA_REQUIRED", "FALSIFICATION_CHECKS_REQUIRED", "LIMITATIONS_REQUIRED",
    "WHAT_WOULD_CHANGE_THE_CONCLUSION_REQUIRED", "NO_UNSUPPORTED_FACTUAL_CLAIMS",
})
ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS = frozenset({
    "QUESTION_RESTATEMENT", "SOURCE_SUMMARY", "RESOLUTION_RULE_ANALYSIS", "EVIDENCE_FOR",
    "EVIDENCE_AGAINST", "SOURCE_CONFLICTS", "UNCERTAINTIES", "MISSING_DATA",
    "FALSIFICATION_CHECKS", "LIMITATIONS", "WHAT_WOULD_CHANGE_THE_CONCLUSION",
    "OPERATOR_REVIEW_NOTES",
})
REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS = (
    "request_id", "source_wp_context", "source_briefing_packet_reference",
    "selected_candidate_reference", "request_label", "research_question",
    "research_question_type", "approved_source_references", "source_requirement_labels",
    "citation_requirement_labels", "evidence_requirement_labels", "required_response_sections",
    "research_scope", "known_uncertainties", "known_missing_data",
    "falsification_checks_to_perform", "operator_research_instructions",
    "operator_review_instructions", "refusal_behavior", "failure_behavior",
    "max_source_count", "max_citation_count", "max_output_words", "timeout_seconds",
    "max_retry_count", "human_review_required", "created_by_operator_note",
    "non_authority_notice", "safety_flags",
)
REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS = (
    "advisory_only", "manual_only", "local_only", "offline_only", "read_only",
    "human_review_required", "explicit_caller_content_only", "request_contract_only",
    "no_prompt_generation", "no_prompt_execution", "no_model_or_provider_call",
    "no_hermes_runtime", "no_tool_selection", "no_tool_invocation", "no_network_or_api",
    "no_source_fetching", "no_market_data_ingestion", "no_discovery_automation",
    "no_automated_selection", "no_scoring_or_ranking_authority",
    "no_priority_calculation_authority", "no_recommendation_authority",
    "no_factual_conclusion_authority", "no_advisory_finding_generation",
    "no_execution_authority", "no_credential_authority", "no_paper_or_live_authority",
    "no_strategy_promotion_authority", "no_pr_approval_authority",
    "no_storage_or_writer_authority", "no_export_or_report_authority", "no_cli_authority",
    "no_scheduler_or_background_authority",
)

_SCALARS = (
    "request_id", "source_wp_context", "source_briefing_packet_reference",
    "selected_candidate_reference", "research_question", "research_question_type",
    "research_scope", "known_uncertainties", "known_missing_data",
    "operator_research_instructions", "operator_review_instructions", "refusal_behavior",
    "failure_behavior", "created_by_operator_note", "non_authority_notice",
)
_SEQUENCES = (
    "approved_source_references", "source_requirement_labels", "citation_requirement_labels",
    "evidence_requirement_labels", "required_response_sections", "falsification_checks_to_perform",
)
_LABEL_FIELDS = {
    "source_requirement_labels": ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS,
    "citation_requirement_labels": ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS,
    "evidence_requirement_labels": ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS,
    "required_response_sections": ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS,
}
_INTEGER_BOUNDS = {
    "max_source_count": (1, 50), "max_citation_count": (1, 100),
    "max_output_words": (100, 20_000), "timeout_seconds": (1, 3_600),
    "max_retry_count": (0, 5),
}
_RAW_KEYS = frozenset({
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata", "raw_input",
    "untrusted_input", "raw_response", "model_response", "prompt", "completion", "tool_plan",
    "tool_call", "provider_response", "hermes_response", "custom", "extras", "metadata",
    "freeform", "extra", "context", "custom_fields", "raw", "free_form", "arbitrary",
})
_FORBIDDEN = (
    "buy", "sell", "hold", "short", "trade", "trading", "order", "execute", "execution",
    "entry", "exit", "stop loss", "take profit", "position size", "allocation",
    "expected return", "fair value", "alpha", "edge", "confidence to trade", "tradable",
    "trade ready", "paper ready", "live ready", "deployment ready", "strategy promotion",
    "approve pr", "pr approval", "merge ready", "risk override", "implementation approval",
    "research priority approved", "recommended candidate", "credential", "private key", "api key",
    "secret", "passphrase", "wallet key", "account endpoint", "private endpoint", "account state",
    "order state", "paper state", "live state", "runtime logs", "prompt runner", "prompt execution",
    "generated prompt", "prompt ready", "model call", "provider call", "hermes runtime",
    "tool selection", "tool invocation", "tool call", "browsing session", "search execution",
    "automatic research response", "generated response", "generated conclusion",
    "advisory finding generated", "automated selection", "automatic selection", "auto select",
    "scheduler", "bot loop", "daemon", "network poller", "dashboard", "automated task",
    "background task", "discovery automation", "market data ingestion", "scoring", "ranking",
    "priority score", "priority calculation", "recommendation engine", "parser", "loader",
    "file writer", "storage path", "database write", "report writer", "exporter", "cli command",
)
_NOTICE_FRAGMENTS = (
    "advisory only", "manual", "local", "offline", "read only", "human review required",
    "explicit caller content only", "request contract only", "not prompt generation",
    "not prompt execution", "not model or provider", "not hermes", "not tool selection",
    "not tool invocation", "not network or api", "not source fetching", "not market data ingestion",
    "not discovery automation", "not automated selection", "not scoring or ranking",
    "not priority calculation", "not recommendation", "not factual conclusion",
    "not advisory finding generation", "not execution", "not credentials", "not paper or live",
    "not strategy promotion", "not pr approval", "not storage or writer", "not export or report",
    "not cli", "not scheduler or background task",
)
_PERMISSION = (
    "authorizes", "authorized to", "grants permission", "permission to", "approved for",
    "may execute", "can execute", "merge ready", "trade ready", "priority approved",
    "automatically selected", "generated by model", "prompt ready for execution",
    "tools may be invoked", "sources may be fetched",
)
_EXCEPTIONS = frozenset({
    *ALLOWED_MANUAL_RESEARCH_REQUEST_LABELS, *ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS,
    *ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS, *ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS,
    *ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS, *REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS,
})


@dataclass(frozen=True)
class HermesCandidateReviewManualResearchRequestResult:
    is_valid: bool
    research_request: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    request_label: str | None
    source_requirement_labels: tuple[str, ...]
    citation_requirement_labels: tuple[str, ...]
    evidence_requirement_labels: tuple[str, ...]
    required_response_sections: tuple[str, ...]
    safety_flags: dict[str, bool]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _scan(value: object, depth: int = 0) -> str | None:
    if depth > 20:
        return "UNSUPPORTED_NESTING_DEPTH"
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _RAW_KEYS:
                return "RAW_METADATA_NOT_ALLOWED"
            if key_text not in _EXCEPTIONS and any(term in _normalize(key_text) for term in _FORBIDDEN):
                return "FORBIDDEN_CONTENT"
            if key_text not in {"non_authority_notice", "safety_flags"}:
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
    if any(fragment not in notice for fragment in fragments) or any(p in notice for p in _PERMISSION):
        return False
    remainder = notice
    for fragment in sorted(fragments, key=len, reverse=True):
        remainder = remainder.replace(fragment, " ")
    return not any(term in _normalize(remainder) for term in _FORBIDDEN)


def _invalid(error: str) -> HermesCandidateReviewManualResearchRequestResult:
    return HermesCandidateReviewManualResearchRequestResult(
        False, {}, (error,), (), None, (), (), (), (), {}
    )


def validate_candidate_review_manual_research_request(
    request_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchRequestResult:
    if not isinstance(request_data, Mapping):
        return _invalid("UNSUPPORTED_INPUT_SHAPE")
    if any(key not in REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS for key in request_data):
        return _invalid("UNKNOWN_FIELD")
    if any(field not in request_data for field in REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS):
        return _invalid("MISSING_REQUIRED_FIELD")
    if any(not isinstance(request_data[field], str) or not request_data[field].strip() for field in _SCALARS):
        return _invalid("INVALID_REQUIRED_FIELD")
    for field in _SEQUENCES:
        value = request_data[field]
        if (not isinstance(value, (list, tuple)) or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)):
            return _invalid("INVALID_REQUIRED_FIELD")
    error = _scan(request_data)
    if error:
        return _invalid(error)
    label = request_data["request_label"]
    if not isinstance(label, str) or label not in ALLOWED_MANUAL_RESEARCH_REQUEST_LABELS:
        return _invalid("INVALID_REQUEST_LABEL")
    for field, allowed in _LABEL_FIELDS.items():
        values = request_data[field]
        if any(item not in allowed for item in values):
            return _invalid("INVALID_LABEL")
        if len(set(values)) != len(values):
            return _invalid("DUPLICATE_LABEL")
    for field, (minimum, maximum) in _INTEGER_BOUNDS.items():
        value = request_data[field]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            return _invalid("INVALID_BOUNDED_INTEGER")
    if request_data["human_review_required"] is not True:
        return _invalid("HUMAN_REVIEW_REQUIRED")
    flags = request_data["safety_flags"]
    if not isinstance(flags, Mapping) or any(
        flags.get(flag) is not True for flag in REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS
    ):
        return _invalid("INVALID_SAFETY_FLAG")
    if not _valid_notice(request_data["non_authority_notice"]):
        return _invalid("INVALID_NON_AUTHORITY_NOTICE")
    clean_flags = {flag: True for flag in REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS}
    result = {
        field: clean_flags if field == "safety_flags" else _copy(request_data[field])
        for field in REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS
    }
    return HermesCandidateReviewManualResearchRequestResult(
        True, result, (), (), label, tuple(request_data["source_requirement_labels"]),
        tuple(request_data["citation_requirement_labels"]),
        tuple(request_data["evidence_requirement_labels"]),
        tuple(request_data["required_response_sections"]), clean_flags,
    )


def build_candidate_review_manual_research_request(
    request_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchRequestResult:
    return validate_candidate_review_manual_research_request(request_data)


def assert_candidate_review_manual_research_request(
    request_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchRequestResult:
    result = validate_candidate_review_manual_research_request(request_data)
    if not result.is_valid:
        raise ValueError("INVALID_MANUAL_RESEARCH_REQUEST")
    return result
