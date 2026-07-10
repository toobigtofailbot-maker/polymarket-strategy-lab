"""Safe in-memory Hermes candidate-review manual research session packages.

WP124 combines explicit caller-supplied research workflow records in memory.
It is deterministic, stdlib-only, local/offline, read-only, and side-effect
free. It performs no file I/O, network access, persistence, prompt execution,
automation, runtime integration, or trading behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_MANUAL_RESEARCH_SESSION_LABELS: frozenset[str] = frozenset({
    "SESSION_READY_FOR_MANUAL_REVIEW_MEMORY",
    "SESSION_REJECTED_FOR_INVALID_RESEARCH_QUESTION",
    "SESSION_REJECTED_FOR_INVALID_ADVISORY_RECEIPT",
    "SESSION_REJECTED_FOR_INVALID_HUMAN_DECISION",
    "SESSION_REJECTED_FOR_INVALID_FOLLOW_UP_TASK",
    "SESSION_NEEDS_MORE_EVIDENCE",
    "SESSION_NEEDS_SOURCE_RECHECK",
    "SESSION_NEEDS_FALSIFICATION_CHECK",
    "SESSION_DEFERRED_PENDING_MORE_CONTEXT",
    "SESSION_REJECTED_FOR_UNSAFE_OR_FORBIDDEN_CONTENT",
})

REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS: tuple[str, ...] = (
    "session_id",
    "source_wp_context",
    "research_question_record",
    "advisory_output_validation_receipt",
    "human_decision_record",
    "follow_up_research_task_records",
    "session_label",
    "session_summary",
    "source_references_summary",
    "evidence_gap_summary",
    "uncertainty_summary",
    "limitations_summary",
    "falsification_summary",
    "operator_next_manual_step",
    "human_review_required",
    "non_authority_notice",
    "safety_flags",
)

REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS: tuple[str, ...] = (
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
    "no_export_or_report_authority",
)

_RAW_METADATA_KEYS: frozenset[str] = frozenset({
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata",
    "raw_input", "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw",
    "custom", "extras", "metadata", "freeform", "extra", "context", "custom_fields",
    "raw_response", "model_response", "prompt", "completion", "raw", "free_form",
    "arbitrary",
})

_FORBIDDEN_TERMS: tuple[str, ...] = (
    "buy", "sell", "hold", "short", "trade", "trading", "order", "execute",
    "execution", "entry", "exit", "stop loss", "take profit", "position size",
    "allocation", "expected return", "fair value", "alpha", "edge",
    "confidence to trade", "trade ready", "tradable", "tradability", "paper ready",
    "live ready", "deployment ready", "strategy promotion", "strategy promoted",
    "approve pr", "pr approval", "merge ready", "risk override", "execution authority",
    "implementation approval", "credential", "private key", "api key", "secret",
    "passphrase", "wallet key", "account endpoint", "private endpoint", "account state",
    "order state", "paper state", "live state", "runtime logs", "prompt runner",
    "prompt execution", "model call", "provider", "hermes runtime", "scheduler",
    "bot loop", "daemon", "network poller", "dashboard", "automated task", "auto task",
    "background task", "file writer", "storage path", "parser", "loader",
    "report writer", "exporter", "cli command",
)

_KEY_EXCEPTIONS: frozenset[str] = frozenset({
    "session_label", "non_authority_notice", "safety_flags",
    *ALLOWED_MANUAL_RESEARCH_SESSION_LABELS,
    *REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS,
})

_NON_AUTHORITY_REQUIRED_FRAGMENTS: tuple[str, ...] = (
    "advisory only", "manual", "local", "offline", "human review required",
    "not fact without source review", "not a trade signal", "not strategy promotion",
    "not paper readiness", "not live readiness", "not execution", "not risk",
    "not order authority", "not pr approval", "not merge readiness",
    "not credential permission", "not account access", "not private-state access",
    "not hermes runtime", "not prompt runner", "not storage/writer/export authority",
    "not automated task authority", "not report/export authority",
)

_PERMISSION_PHRASES: tuple[str, ...] = (
    "authorizes", "authorized to", "grants", "permission to", "approved for",
    "may execute", "can execute", "paper ready", "live ready", "deployment ready",
    "merge ready", "approve pr", "pr approved", "trade ready", "strategy promoted",
    "automated task",
)


@dataclass(frozen=True)
class HermesCandidateReviewManualResearchSessionPackageResult:
    """Validation result for an in-memory manual research session package."""

    is_valid: bool
    session_package: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    session_label: str | None
    safety_flags: dict[str, bool]


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _scan_raw_metadata(value: object, errors: list[str], depth: int = 0) -> None:
    if depth > 20:
        errors.append("UNSUPPORTED_NESTING_DEPTH")
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
            if key_text not in _KEY_EXCEPTIONS:
                normalized_key = _normalize(key_text)
                if any(term in normalized_key for term in _FORBIDDEN_TERMS):
                    errors.append("FORBIDDEN_CONTENT")
                    return
            if key_text == "non_authority_notice":
                continue
            _scan_forbidden(child, errors, key_text)
            if errors:
                return
    elif isinstance(value, (list, tuple)):
        for child in value:
            _scan_forbidden(child, errors, parent_key)
            if errors:
                return
    elif isinstance(value, str) and value not in ALLOWED_MANUAL_RESEARCH_SESSION_LABELS:
        normalized = _normalize(value)
        if any(term in normalized for term in _FORBIDDEN_TERMS):
            errors.append("FORBIDDEN_CONTENT")


def _invalid(errors: tuple[str, ...]) -> HermesCandidateReviewManualResearchSessionPackageResult:
    return HermesCandidateReviewManualResearchSessionPackageResult(
        False, {}, errors, (), None, {}
    )


def _validate_notice(value: object, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append("INVALID_NON_AUTHORITY_NOTICE")
        return
    normalized = _normalize(value)
    for phrase in _PERMISSION_PHRASES:
        if phrase in normalized and not (
            phrase == "automated task" and "not automated task" in normalized
        ):
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return
    if any(_normalize(fragment) not in normalized for fragment in _NON_AUTHORITY_REQUIRED_FRAGMENTS):
        errors.append("INVALID_NON_AUTHORITY_NOTICE")


def validate_candidate_review_manual_research_session_package(
    session_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchSessionPackageResult:
    """Validate and sanitize an explicit in-memory manual session mapping."""
    if not isinstance(session_data, Mapping):
        return _invalid(("UNSUPPORTED_INPUT_SHAPE",))

    errors: list[str] = []
    _scan_raw_metadata(session_data, errors)
    if not errors:
        _scan_forbidden(session_data, errors)
    if errors:
        return _invalid(tuple(dict.fromkeys(errors)))

    for field in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS:
        if field not in session_data:
            return _invalid(("MISSING_REQUIRED_FIELD",))
        value = session_data[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            return _invalid(("INVALID_REQUIRED_FIELD",))

    if not isinstance(session_data["research_question_record"], Mapping):
        return _invalid(("INVALID_NESTED_RECORD_SHAPE",))
    if not isinstance(session_data["advisory_output_validation_receipt"], Mapping):
        return _invalid(("INVALID_NESTED_RECORD_SHAPE",))
    if not isinstance(session_data["human_decision_record"], Mapping):
        return _invalid(("INVALID_NESTED_RECORD_SHAPE",))
    tasks = session_data["follow_up_research_task_records"]
    if not isinstance(tasks, (list, tuple)) or any(not isinstance(item, Mapping) for item in tasks):
        return _invalid(("INVALID_NESTED_RECORD_SHAPE",))

    label = session_data["session_label"]
    if label not in ALLOWED_MANUAL_RESEARCH_SESSION_LABELS:
        return _invalid(("INVALID_SESSION_LABEL",))
    if session_data["human_review_required"] is not True:
        return _invalid(("HUMAN_REVIEW_REQUIRED",))

    flags = session_data["safety_flags"]
    if not isinstance(flags, Mapping) or any(
        flags.get(flag) is not True
        for flag in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS
    ):
        return _invalid(("INVALID_SAFETY_FLAG",))

    _validate_notice(session_data["non_authority_notice"], errors)
    if errors:
        return _invalid(tuple(dict.fromkeys(errors)))

    sanitized_flags = {
        flag: True for flag in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS
    }
    package = {
        field: sanitized_flags if field == "safety_flags" else session_data[field]
        for field in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS
    }
    return HermesCandidateReviewManualResearchSessionPackageResult(
        True, package, (), (), str(label), sanitized_flags
    )


def build_candidate_review_manual_research_session_package(
    session_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchSessionPackageResult:
    """Build by applying the same fail-closed package validation contract."""
    return validate_candidate_review_manual_research_session_package(session_data)


def assert_candidate_review_manual_research_session_package(
    session_data: Mapping[str, Any],
) -> HermesCandidateReviewManualResearchSessionPackageResult:
    """Return a valid result or raise a neutral error without caller content."""
    result = validate_candidate_review_manual_research_session_package(session_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_MANUAL_RESEARCH_SESSION_PACKAGE: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result
