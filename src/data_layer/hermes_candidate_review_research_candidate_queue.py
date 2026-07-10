"""Deterministic in-memory candidate-review research queue contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

ALLOWED_RESEARCH_CANDIDATE_QUEUE_ITEM_LABELS = frozenset({
    "CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW", "CANDIDATE_NEEDS_SOURCE_RECHECK",
    "CANDIDATE_NEEDS_RESOLUTION_RULE_REVIEW", "CANDIDATE_NEEDS_EVIDENCE_GAP_REVIEW",
    "CANDIDATE_NEEDS_CROSS_MARKET_CONTEXT_REVIEW", "CANDIDATE_NEEDS_WALLET_SIGNAL_CONTEXT_REVIEW",
    "CANDIDATE_NEEDS_MICROSTRUCTURE_CONTEXT_REVIEW", "CANDIDATE_NEEDS_STALE_OR_MISSING_DATA_REVIEW",
    "CANDIDATE_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT", "CANDIDATE_DEFERRED_PENDING_MORE_CONTEXT",
})
ALLOWED_RESEARCH_CANDIDATE_QUEUE_REASON_LABELS = frozenset({
    "RESOLUTION_RULE_AMBIGUITY", "EVIDENCE_QUALITY_GAP", "SOURCE_CONFLICT",
    "WALLET_SIGNAL_UNCERTAINTY", "CROSS_MARKET_INCONSISTENCY",
    "MARKET_STRUCTURE_MICROSTRUCTURE_CONCERN", "STALE_OR_MISSING_DATA_RISK",
    "OPERATOR_UNCERTAINTY_REQUIRING_DEEPER_RESEARCH", "SOURCE_PROVENANCE_WEAKNESS",
    "FALSIFICATION_CHECK_NEED",
})
ALLOWED_RESEARCH_CANDIDATE_QUEUE_LABELS = frozenset({
    "QUEUE_READY_FOR_MANUAL_RESEARCH_REVIEW", "QUEUE_NEEDS_MORE_EVIDENCE",
    "QUEUE_NEEDS_SOURCE_RECHECK", "QUEUE_DEFERRED_PENDING_MORE_CONTEXT",
    "QUEUE_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
})
REQUIRED_RESEARCH_CANDIDATE_QUEUE_ITEM_FIELDS = (
    "candidate_id", "source_wp_context", "candidate_reference", "candidate_label",
    "candidate_reason_labels", "candidate_summary", "evidence_references_to_check",
    "resolution_rule_notes", "source_quality_notes", "uncertainty_notes", "known_missing_data",
    "limitations", "falsification_checks_to_perform", "operator_next_manual_step",
    "human_review_required", "non_authority_notice", "safety_flags",
)
REQUIRED_RESEARCH_CANDIDATE_QUEUE_PACKAGE_FIELDS = (
    "queue_id", "source_wp_context", "queue_label", "candidate_items", "queue_summary",
    "operator_next_manual_step", "human_review_required", "non_authority_notice", "safety_flags",
)
REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS = (
    "advisory_only", "manual_only", "local_only", "offline_only", "human_review_required",
    "no_execution_authority", "no_runtime_authority", "no_credential_authority",
    "no_paper_or_live_authority", "no_prompt_execution", "no_file_or_network",
    "no_strategy_promotion_authority", "no_pr_approval_authority", "no_storage_or_writer_authority",
    "no_advisory_output_as_fact", "no_automated_task_authority", "no_export_or_report_authority",
    "no_discovery_automation_authority", "no_market_data_ingestion_authority",
    "no_scoring_or_ranking_authority",
)
_RAW_KEYS = frozenset({"raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata", "metadata", "custom_fields", "raw_response", "prompt", "completion", "raw", "free_form", "extras"})
_FORBIDDEN = (
    "buy", "sell", "hold", "short", "trade", "trading", "order", "execute", "execution",
    "position size", "allocation", "expected return", "fair value", "alpha", "edge", "confidence to trade",
    "paper ready", "live ready", "deployment ready", "trade ready", "strategy promotion", "pr approval",
    "merge ready", "risk override", "implementation approval", "credential", "private key", "api key", "secret",
    "passphrase", "wallet key", "account endpoint", "private endpoint", "account state", "order state", "paper state",
    "live state", "runtime logs", "prompt runner", "prompt execution", "model call", "provider", "hermes runtime",
    "scheduler", "bot loop", "daemon", "network poller", "dashboard", "automated task", "background task",
    "parser", "loader", "file writer", "storage path", "report writer", "exporter", "cli command",
    "market data ingestion", "discovery automation", "scoring", "ranking",
)
_NOTICE_FRAGMENTS = ("advisory only", "manual", "local", "offline", "human review required", "not execution", "not runtime", "not credential", "not paper or live", "not prompt execution", "not file or network", "not strategy promotion", "not pr approval", "not storage or writer", "not automated task", "not export or report", "not discovery automation", "not market data ingestion", "not scoring or ranking")
_PERMISSION = ("authorizes", "authorized to", "grants permission", "permission to", "approved for", "may execute", "can execute", "merge ready", "trade ready")
_EXCEPTIONS = frozenset((*ALLOWED_RESEARCH_CANDIDATE_QUEUE_ITEM_LABELS, *ALLOWED_RESEARCH_CANDIDATE_QUEUE_REASON_LABELS, *ALLOWED_RESEARCH_CANDIDATE_QUEUE_LABELS, *REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS, "non_authority_notice", "safety_flags"))

@dataclass(frozen=True)
class HermesCandidateReviewResearchCandidateQueueItemResult:
    is_valid: bool
    candidate_item: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    candidate_label: str | None
    candidate_reason_labels: tuple[str, ...]
    safety_flags: dict[str, bool]

@dataclass(frozen=True)
class HermesCandidateReviewResearchCandidateQueuePackageResult:
    is_valid: bool
    queue_package: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    queue_label: str | None
    safety_flags: dict[str, bool]

def _norm(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())

def _scan(value: object, depth: int = 0) -> str | None:
    if depth > 20: return "UNSUPPORTED_NESTING_DEPTH"
    if isinstance(value, Mapping):
        for key, child in value.items():
            text = str(key)
            if text.lower() in _RAW_KEYS: return "RAW_METADATA_NOT_ALLOWED"
            if text not in _EXCEPTIONS and any(term in _norm(text) for term in _FORBIDDEN): return "FORBIDDEN_CONTENT"
            if text != "non_authority_notice":
                error = _scan(child, depth + 1)
                if error: return error
    elif isinstance(value, (list, tuple)):
        for child in value:
            error = _scan(child, depth + 1)
            if error: return error
    elif isinstance(value, str) and value not in _EXCEPTIONS and any(term in _norm(value) for term in _FORBIDDEN):
        return "FORBIDDEN_CONTENT"
    return None

def _common(data: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    error = _scan(data)
    if error: return error
    for field in fields:
        if field not in data: return "MISSING_REQUIRED_FIELD"
        value = data[field]
        if value is None or (isinstance(value, str) and not value.strip()): return "INVALID_REQUIRED_FIELD"
    if data["human_review_required"] is not True: return "HUMAN_REVIEW_REQUIRED"
    flags = data["safety_flags"]
    if not isinstance(flags, Mapping) or any(flags.get(flag) is not True for flag in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS): return "INVALID_SAFETY_FLAG"
    notice = data["non_authority_notice"]
    if not isinstance(notice, str) or not notice.strip(): return "INVALID_NON_AUTHORITY_NOTICE"
    normalized = _norm(notice)
    if any(phrase in normalized for phrase in _PERMISSION) or any(_norm(part) not in normalized for part in _NOTICE_FRAGMENTS): return "INVALID_NON_AUTHORITY_NOTICE"
    return None

def _bad_item(error: str) -> HermesCandidateReviewResearchCandidateQueueItemResult:
    return HermesCandidateReviewResearchCandidateQueueItemResult(False, {}, (error,), (), None, (), {})

def validate_candidate_review_research_candidate_queue_item(item_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueueItemResult:
    if not isinstance(item_data, Mapping): return _bad_item("UNSUPPORTED_INPUT_SHAPE")
    error = _common(item_data, REQUIRED_RESEARCH_CANDIDATE_QUEUE_ITEM_FIELDS)
    if error: return _bad_item(error)
    label, reasons = item_data["candidate_label"], item_data["candidate_reason_labels"]
    if label not in ALLOWED_RESEARCH_CANDIDATE_QUEUE_ITEM_LABELS: return _bad_item("INVALID_CANDIDATE_LABEL")
    if not isinstance(reasons, (list, tuple)) or not reasons or any(reason not in ALLOWED_RESEARCH_CANDIDATE_QUEUE_REASON_LABELS for reason in reasons): return _bad_item("INVALID_CANDIDATE_REASON_LABEL")
    flags = {flag: True for flag in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS}
    output = {field: flags if field == "safety_flags" else item_data[field] for field in REQUIRED_RESEARCH_CANDIDATE_QUEUE_ITEM_FIELDS}
    return HermesCandidateReviewResearchCandidateQueueItemResult(True, output, (), (), str(label), tuple(reasons), flags)

def build_candidate_review_research_candidate_queue_item(item_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueueItemResult:
    return validate_candidate_review_research_candidate_queue_item(item_data)

def assert_candidate_review_research_candidate_queue_item(item_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueueItemResult:
    result = validate_candidate_review_research_candidate_queue_item(item_data)
    if not result.is_valid: raise ValueError("INVALID_RESEARCH_CANDIDATE_QUEUE_ITEM: " + ", ".join(result.errors))
    return result

def _bad_package(error: str) -> HermesCandidateReviewResearchCandidateQueuePackageResult:
    return HermesCandidateReviewResearchCandidateQueuePackageResult(False, {}, (error,), (), None, {})

def validate_candidate_review_research_candidate_queue_package(queue_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueuePackageResult:
    if not isinstance(queue_data, Mapping): return _bad_package("UNSUPPORTED_INPUT_SHAPE")
    error = _common(queue_data, REQUIRED_RESEARCH_CANDIDATE_QUEUE_PACKAGE_FIELDS)
    if error: return _bad_package(error)
    label, items = queue_data["queue_label"], queue_data["candidate_items"]
    if label not in ALLOWED_RESEARCH_CANDIDATE_QUEUE_LABELS: return _bad_package("INVALID_QUEUE_LABEL")
    if not isinstance(items, (list, tuple)) or not items: return _bad_package("EMPTY_OR_INVALID_CANDIDATE_QUEUE")
    validated = []
    for item in items:
        if not isinstance(item, Mapping): return _bad_package("INVALID_CANDIDATE_ITEM_SHAPE")
        result = validate_candidate_review_research_candidate_queue_item(item)
        if not result.is_valid: return _bad_package("INVALID_CANDIDATE_ITEM")
        validated.append(result.candidate_item)
    flags = {flag: True for flag in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS}
    output = {field: (validated if field == "candidate_items" else flags if field == "safety_flags" else queue_data[field]) for field in REQUIRED_RESEARCH_CANDIDATE_QUEUE_PACKAGE_FIELDS}
    return HermesCandidateReviewResearchCandidateQueuePackageResult(True, output, (), (), str(label), flags)

def build_candidate_review_research_candidate_queue_package(queue_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueuePackageResult:
    return validate_candidate_review_research_candidate_queue_package(queue_data)

def assert_candidate_review_research_candidate_queue_package(queue_data: Mapping[str, Any]) -> HermesCandidateReviewResearchCandidateQueuePackageResult:
    result = validate_candidate_review_research_candidate_queue_package(queue_data)
    if not result.is_valid: raise ValueError("INVALID_RESEARCH_CANDIDATE_QUEUE_PACKAGE: " + ", ".join(result.errors))
    return result
