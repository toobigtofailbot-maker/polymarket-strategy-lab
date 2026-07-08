"""In-memory Hermes candidate-review research question record validator.

Implements the WP120 research question record contract as a deterministic
local/offline/advisory-only build and validation layer. Accepts explicit
caller-supplied in-memory mappings, validates required fields, research
question type, preflight checks, safety flags, human review, and non-authority
notice. Rejects forbidden content and raw/free-form metadata recursively.
Fails closed with an empty record and neutral diagnostics for invalid input.

Stdlib-only. No file I/O. No network. No subprocess. No CLI. No credentials.
No parser, loader, writer, storage path, paper/live/execution/risk/order,
scheduler/dashboard/bot-loop/runtime/Hermes prompt-runner behavior. Added in
WP121.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_RESEARCH_QUESTION_TYPES: frozenset[str] = frozenset({
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

REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS: tuple[str, ...] = (
    "record_id",
    "source_wp_context",
    "selected_candidate_reference",
    "intake_basis",
    "research_question",
    "research_question_type",
    "evidence_references_to_check",
    "uncertainty_notes",
    "known_missing_data",
    "limitations",
    "falsification_checks_to_perform",
    "forbidden_interpretation_flags",
    "human_review_required",
    "next_manual_step",
    "created_by_operator_note",
    "non_authority_notice",
    "safety_flags",
)

REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS: tuple[str, ...] = (
    "upstream_intake_passed_wp118",
    "source_provenance_explicit",
    "evidence_references_manually_inspectable",
    "uncertainty_missing_data_limitations_explicit",
    "no_raw_model_or_hermes_output_treated_as_fact",
    "no_credentials_private_account_order_paper_live_runtime_data",
    "no_generated_artifact_commit",
    "no_trading_readiness_approval_language",
)

REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS: tuple[str, ...] = (
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
    "approve pr",
    "pr approval",
    "merge ready",
    "risk override",
    "credential",
    "private key",
    "api key",
    "secret",
    "passphrase",
    "account endpoint",
    "private endpoint",
    "wallet",
    "wallet key",
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
    "file writer",
    "storage path",
    "parser",
    "loader",
    "report writer",
    "exporter",
    "cli command",
)

_BOUNDARY_KEY_EXCEPTIONS: frozenset[str] = frozenset({
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
    "forbidden_interpretation_flags",
    "non_authority_notice",
    "safety_flags",
    *REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS,
})

_BOUNDARY_VALUE_EXEMPT_KEYS: frozenset[str] = frozenset({
    "non_authority_notice",
})

_NON_AUTHORITY_REQUIRED_FRAGMENTS: tuple[str, ...] = (
    "advisory",
    "manual",
    "local",
    "offline",
    "not a trade signal",
    "not strategy promotion",
    "not paper",
    "not live",
    "not execution",
    "not risk",
    "not order",
    "not pr approval",
    "not merge readiness",
    "not credential",
    "not account",
    "not private",
    "not hermes runtime",
    "not prompt runner",
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
)


@dataclass(frozen=True)
class HermesCandidateReviewResearchQuestionRecordResult:
    """Validation result for a candidate-review research question record."""

    is_valid: bool
    record: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    research_question_type: str | None
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
        if value in ALLOWED_RESEARCH_QUESTION_TYPES:
            return
        normalized_value = _normalize(value)
        for term in _FORBIDDEN_TERMS:
            if term in normalized_value:
                errors.append("FORBIDDEN_CONTENT")
                return


def _invalid_result(errors: tuple[str, ...]) -> HermesCandidateReviewResearchQuestionRecordResult:
    return HermesCandidateReviewResearchQuestionRecordResult(
        is_valid=False,
        record={},
        errors=errors,
        warnings=(),
        research_question_type=None,
        safety_flags={},
    )


def _validate_required_fields(record_data: Mapping[str, Any], errors: list[str]) -> None:
    for field in REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS:
        if field not in record_data:
            errors.append("MISSING_REQUIRED_FIELD")
            return


def _validate_safety_flags(record_data: Mapping[str, Any], errors: list[str]) -> None:
    safety_flags = record_data.get("safety_flags")
    if not isinstance(safety_flags, Mapping):
        errors.append("INVALID_SAFETY_FLAG")
        return
    for flag in REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS:
        if safety_flags.get(flag) is not True:
            errors.append("INVALID_SAFETY_FLAG")
            return


def _validate_preflight(record_data: Mapping[str, Any], errors: list[str]) -> None:
    intake_basis = record_data.get("intake_basis")
    if not isinstance(intake_basis, Mapping):
        errors.append("INVALID_PREFLIGHT_FLAG")
        return
    for flag in REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS:
        if intake_basis.get(flag) is not True:
            errors.append("INVALID_PREFLIGHT_FLAG")
            return


def _validate_research_question_type(record_data: Mapping[str, Any], errors: list[str]) -> None:
    question_type = record_data.get("research_question_type")
    if question_type not in ALLOWED_RESEARCH_QUESTION_TYPES:
        errors.append("INVALID_RESEARCH_QUESTION_TYPE")


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
        if phrase in normalized:
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return
    for fragment in _NON_AUTHORITY_REQUIRED_FRAGMENTS:
        if fragment not in normalized:
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return


def validate_candidate_review_research_question_record(
    record_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionRecordResult:
    """Validate an in-memory candidate-review research question record."""
    if not isinstance(record_data, Mapping):
        return _invalid_result(("UNSUPPORTED_INPUT_SHAPE",))

    errors: list[str] = []

    _scan_raw_metadata(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _scan_forbidden(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_required_fields(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_safety_flags(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_preflight(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_research_question_type(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_human_review(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_non_authority_notice(record_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    sanitized_flags = {
        flag: True for flag in REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS
    }
    sanitized_record: dict[str, Any] = {}
    for field in REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS:
        if field == "safety_flags":
            sanitized_record[field] = sanitized_flags
        else:
            sanitized_record[field] = record_data[field]

    question_type = str(record_data["research_question_type"])
    return HermesCandidateReviewResearchQuestionRecordResult(
        is_valid=True,
        record=sanitized_record,
        errors=(),
        warnings=(),
        research_question_type=question_type,
        safety_flags=sanitized_flags,
    )


def build_candidate_review_research_question_record(
    record_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionRecordResult:
    """Build and validate a research question record from caller data."""
    return validate_candidate_review_research_question_record(record_data)


def assert_candidate_review_research_question_record(
    record_data: Mapping[str, Any],
) -> HermesCandidateReviewResearchQuestionRecordResult:
    """Assert that record_data produces a valid research question record."""
    result = validate_candidate_review_research_question_record(record_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_RESEARCH_QUESTION_RECORD: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result
