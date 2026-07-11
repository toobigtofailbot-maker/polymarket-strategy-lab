"""Bounded manual research briefing packet validation and construction.

WP130 organizes explicit caller-supplied content in memory only.  It does not
generate prompts, questions, research responses, findings, or recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_RESEARCH_BRIEFING_PACKET_LABELS = frozenset({
    "BRIEFING_READY_FOR_MANUAL_RESEARCH",
    "BRIEFING_NEEDS_SOURCE_RECHECK",
    "BRIEFING_NEEDS_RESOLUTION_RULE_REVIEW",
    "BRIEFING_NEEDS_MORE_EVIDENCE",
    "BRIEFING_NEEDS_FALSIFICATION_REVIEW",
    "BRIEFING_DEFERRED_PENDING_CONTEXT",
    "BRIEFING_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
})
ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS = frozenset({
    "QUESTION_RESTATEMENT", "SOURCE_SUMMARY", "RESOLUTION_RULE_ANALYSIS",
    "EVIDENCE_FOR", "EVIDENCE_AGAINST", "SOURCE_CONFLICTS", "UNCERTAINTIES",
    "MISSING_DATA", "FALSIFICATION_CHECKS", "LIMITATIONS",
    "WHAT_WOULD_CHANGE_THE_CONCLUSION", "OPERATOR_REVIEW_NOTES",
})
REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS = (
    "briefing_id", "source_wp_context", "source_research_question_record_reference",
    "selected_candidate_reference", "briefing_label", "research_question",
    "research_question_type", "source_references_to_inspect", "resolution_rule_context",
    "evidence_gap_summary", "uncertainty_summary", "known_missing_data", "limitations",
    "falsification_checks_to_perform", "required_response_sections",
    "operator_research_instructions", "operator_next_manual_step", "human_review_required",
    "created_by_operator_note", "non_authority_notice", "safety_flags",
)
REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS = (
    "advisory_only", "manual_only", "local_only", "offline_only", "read_only",
    "human_review_required", "explicit_caller_content_only", "no_prompt_generation",
    "no_prompt_execution", "no_model_or_provider_call", "no_hermes_runtime",
    "no_network_or_api", "no_market_data_ingestion", "no_discovery_automation",
    "no_automated_selection", "no_scoring_or_ranking_authority",
    "no_priority_calculation_authority", "no_recommendation_authority",
    "no_factual_conclusion_authority", "no_advisory_finding_generation",
    "no_execution_authority", "no_credential_authority", "no_paper_or_live_authority",
    "no_strategy_promotion_authority", "no_pr_approval_authority",
    "no_storage_or_writer_authority", "no_export_or_report_authority", "no_cli_authority",
    "no_scheduler_or_background_authority",
)

_REQUIRED_SCALAR_FIELDS = (
    "briefing_id", "source_wp_context", "source_research_question_record_reference",
    "selected_candidate_reference", "research_question", "research_question_type",
    "resolution_rule_context", "evidence_gap_summary", "uncertainty_summary",
    "known_missing_data", "limitations", "operator_research_instructions",
    "operator_next_manual_step", "created_by_operator_note", "non_authority_notice",
)
_REQUIRED_SEQUENCE_FIELDS = (
    "source_references_to_inspect", "falsification_checks_to_perform",
    "required_response_sections",
)

_RAW_KEYS = frozenset({
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata", "raw_input",
    "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw", "custom", "extras",
    "metadata", "freeform", "extra", "context", "custom_fields", "raw_response",
    "model_response", "prompt", "completion", "raw", "free_form", "arbitrary",
})
_FORBIDDEN_TERMS = (
    "buy", "sell", "hold", "short", "trade", "trading", "order", "execute", "execution",
    "entry", "exit", "stop loss", "take profit", "position size", "allocation",
    "expected return", "fair value", "alpha", "edge", "confidence to trade", "tradable",
    "trade ready", "paper ready", "live ready", "deployment ready", "strategy promotion",
    "approve pr", "pr approval", "merge ready", "risk override", "implementation approval",
    "research priority approved", "recommended candidate", "credential", "private key",
    "api key", "secret", "passphrase", "wallet key", "account endpoint", "private endpoint",
    "account state", "order state", "paper state", "live state", "runtime logs",
    "prompt runner", "prompt execution", "prompt generated", "generated prompt", "model call",
    "provider call", "hermes runtime", "automatic research response", "generated conclusion",
    "advisory finding generated", "automated selection", "automatic selection", "auto select",
    "scheduler", "bot loop", "daemon", "network poller", "dashboard", "automated task",
    "background task", "discovery automation", "market data ingestion", "scoring", "ranking",
    "priority score", "priority calculation", "recommendation engine", "parser", "loader",
    "file writer", "storage path", "database write", "report writer", "exporter", "cli command",
)
_NOTICE_FRAGMENTS = (
    "advisory only", "manual", "local", "offline", "read only", "human review required",
    "explicit caller content only", "not prompt generation", "not prompt execution",
    "not model or provider call", "not hermes runtime", "not network or api",
    "not market data ingestion", "not discovery automation", "not automated selection",
    "not scoring or ranking", "not priority calculation", "not recommendation",
    "not factual conclusion", "not advisory finding generation", "not execution",
    "not credentials", "not paper or live", "not strategy promotion", "not pr approval",
    "not storage or writer", "not export or report", "not cli",
    "not scheduler or background task",
)
_PERMISSION_PHRASES = (
    "authorizes", "authorized to", "grants permission", "permission to", "approved for",
    "may execute", "can execute", "merge ready", "trade ready", "priority approved",
    "automatically selected", "recommended candidate", "generated by model",
    "prompt ready for execution",
)
_EXACT_EXCEPTIONS = frozenset({
    *ALLOWED_RESEARCH_BRIEFING_PACKET_LABELS,
    *ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS,
    *REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS,
    "non_authority_notice", "safety_flags",
})


@dataclass(frozen=True)
class HermesCandidateReviewManualResearchBriefingPacketResult:
    is_valid: bool
    briefing_packet: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    briefing_label: str | None
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
            if key_text not in _EXACT_EXCEPTIONS:
                normalized = _normalize(key_text)
                if any(term in normalized for term in _FORBIDDEN_TERMS):
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
    elif isinstance(value, str) and value not in _EXACT_EXCEPTIONS:
        normalized = _normalize(value)
        if any(term in normalized for term in _FORBIDDEN_TERMS):
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
    if any(fragment not in notice for fragment in fragments):
        return False
    if any(phrase in notice for phrase in _PERMISSION_PHRASES):
        return False
    remainder = notice
    for fragment in sorted(fragments, key=len, reverse=True):
        remainder = remainder.replace(fragment, " ")
    remainder = _normalize(remainder)
    return not any(term in remainder for term in _FORBIDDEN_TERMS)


def _invalid(error: str) -> HermesCandidateReviewManualResearchBriefingPacketResult:
    return HermesCandidateReviewManualResearchBriefingPacketResult(
        False, {}, (error,), (), None, (), {}
    )


def validate_candidate_review_manual_research_briefing_packet(
    packet_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchBriefingPacketResult:
    if not isinstance(packet_data, Mapping):
        return _invalid("UNSUPPORTED_INPUT_SHAPE")
    if any(key not in REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS for key in packet_data):
        return _invalid("UNKNOWN_FIELD")
    for field in REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS:
        if field not in packet_data:
            return _invalid("MISSING_REQUIRED_FIELD")
    if any(
        not isinstance(packet_data[field], str) or not packet_data[field].strip()
        for field in _REQUIRED_SCALAR_FIELDS
    ):
        return _invalid("INVALID_REQUIRED_FIELD")
    if any(
        not isinstance(packet_data[field], (list, tuple))
        or not packet_data[field]
        or any(not isinstance(item, str) or not item.strip() for item in packet_data[field])
        for field in _REQUIRED_SEQUENCE_FIELDS
    ):
        return _invalid("INVALID_REQUIRED_FIELD")
    error = _scan(packet_data)
    if error:
        return _invalid(error)
    for field in REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS:
        value = packet_data[field]
        if value is None:
            return _invalid("INVALID_REQUIRED_FIELD")
    label = packet_data["briefing_label"]
    if not isinstance(label, str) or label not in ALLOWED_RESEARCH_BRIEFING_PACKET_LABELS:
        return _invalid("INVALID_BRIEFING_LABEL")
    sections = packet_data["required_response_sections"]
    if not isinstance(sections, (list, tuple)) or not sections:
        return _invalid("INVALID_REQUIRED_RESPONSE_SECTIONS")
    if any(not isinstance(section, str) or section not in ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS
           for section in sections):
        return _invalid("INVALID_REQUIRED_RESPONSE_SECTION_LABEL")
    if len(set(sections)) != len(sections):
        return _invalid("DUPLICATE_REQUIRED_RESPONSE_SECTION_LABEL")
    if packet_data["human_review_required"] is not True:
        return _invalid("HUMAN_REVIEW_REQUIRED")
    flags = packet_data["safety_flags"]
    if not isinstance(flags, Mapping) or any(
        flags.get(flag) is not True for flag in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS
    ):
        return _invalid("INVALID_SAFETY_FLAG")
    if not _valid_notice(packet_data["non_authority_notice"]):
        return _invalid("INVALID_NON_AUTHORITY_NOTICE")
    clean_flags = {flag: True for flag in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS}
    packet = {
        field: clean_flags if field == "safety_flags" else _copy(packet_data[field])
        for field in REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS
    }
    return HermesCandidateReviewManualResearchBriefingPacketResult(
        True, packet, (), (), label, tuple(sections), clean_flags
    )


def build_candidate_review_manual_research_briefing_packet(
    packet_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchBriefingPacketResult:
    return validate_candidate_review_manual_research_briefing_packet(packet_data)


def assert_candidate_review_manual_research_briefing_packet(
    packet_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchBriefingPacketResult:
    result = validate_candidate_review_manual_research_briefing_packet(packet_data)
    if not result.is_valid:
        raise ValueError("INVALID_MANUAL_RESEARCH_BRIEFING_PACKET")
    return result
