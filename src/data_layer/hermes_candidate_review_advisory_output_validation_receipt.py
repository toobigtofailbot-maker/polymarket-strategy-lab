"""In-memory Hermes candidate-review advisory output validation receipt.

Implements WP122 as a deterministic local/offline/advisory-only validation
receipt layer. Accepts explicit caller-supplied in-memory mappings, validates
required receipt fields, review checks, safety flags, human review, receipt
label, and non-authority notice. Rejects forbidden content and raw/free-form
metadata recursively. Fails closed with an empty receipt and neutral diagnostics
for invalid input.

Stdlib-only. No file I/O. No network. No subprocess. No CLI. No credentials.
No parser, loader, writer, storage path, paper/live/execution/risk/order,
scheduler/dashboard/bot-loop/runtime/Hermes prompt-runner behavior. Added in
WP122.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_RECEIPT_LABELS: frozenset[str] = frozenset({
    "ADVISORY_OUTPUT_ACCEPTED_FOR_HUMAN_REVIEW",
    "ADVISORY_OUTPUT_REJECTED_FOR_UNSUPPORTED_CLAIMS",
    "ADVISORY_OUTPUT_REJECTED_FOR_SOURCE_GAPS",
    "ADVISORY_OUTPUT_REJECTED_FOR_UNCERTAINTY_OR_LIMITATION_GAPS",
    "ADVISORY_OUTPUT_REJECTED_FOR_FORBIDDEN_AUTHORITY",
    "ADVISORY_OUTPUT_REJECTED_FOR_RAW_MODEL_OUTPUT",
    "ADVISORY_OUTPUT_REJECTED_FOR_UNSAFE_CONTENT",
    "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE",
    "ADVISORY_OUTPUT_NEEDS_FALSIFICATION_CHECK",
    "ADVISORY_OUTPUT_DEFERRED_TO_FUTURE_APPROVED_WP",
})

REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS: tuple[str, ...] = (
    "receipt_id",
    "source_wp_context",
    "source_research_question_record_reference",
    "advisory_output_reference",
    "receipt_label",
    "source_references_checked",
    "unsupported_claims",
    "uncertainty_review",
    "limitations_review",
    "missing_data_review",
    "falsification_review",
    "human_review_notes",
    "follow_up_research_tasks",
    "forbidden_interpretation_flags",
    "human_review_required",
    "non_authority_notice",
    "safety_flags",
)

REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS: tuple[str, ...] = (
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
)

REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS: tuple[str, ...] = (
    "source_references_checked",
    "unsupported_claims_identified",
    "uncertainty_review_explicit",
    "limitations_review_explicit",
    "missing_data_review_explicit",
    "falsification_review_explicit",
    "no_raw_model_output_treated_as_fact",
    "no_trading_readiness_approval_language",
    "no_credentials_private_account_order_paper_live_runtime_data",
    "human_review_required",
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
    "file writer",
    "storage path",
    "parser",
    "loader",
    "report writer",
    "exporter",
    "cli command",
)

_BOUNDARY_KEY_EXCEPTIONS: frozenset[str] = frozenset({
    "advisory_output_reference",
    "forbidden_interpretation_flags",
    "non_authority_notice",
    "receipt_label",
    "safety_flags",
    *ALLOWED_RECEIPT_LABELS,
    *REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS,
    *REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS,
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
    "not account",
    "not private-state access",
    "not hermes runtime",
    "not prompt runner",
    "not storage/writer/export authority",
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
)


@dataclass(frozen=True)
class HermesCandidateReviewAdvisoryOutputValidationReceiptResult:
    """Validation result for a candidate-review advisory output receipt."""

    is_valid: bool
    receipt: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    receipt_label: str | None
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
        if value in ALLOWED_RECEIPT_LABELS:
            return
        normalized_value = _normalize(value)
        for term in _FORBIDDEN_TERMS:
            if term in normalized_value:
                errors.append("FORBIDDEN_CONTENT")
                return


def _invalid_result(
    errors: tuple[str, ...],
) -> HermesCandidateReviewAdvisoryOutputValidationReceiptResult:
    return HermesCandidateReviewAdvisoryOutputValidationReceiptResult(
        is_valid=False,
        receipt={},
        errors=errors,
        warnings=(),
        receipt_label=None,
        safety_flags={},
    )


def _validate_required_fields(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    for field in REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS:
        if field not in receipt_data:
            errors.append("MISSING_REQUIRED_FIELD")
            return


def _validate_safety_flags(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    safety_flags = receipt_data.get("safety_flags")
    if not isinstance(safety_flags, Mapping):
        errors.append("INVALID_SAFETY_FLAG")
        return
    for flag in REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS:
        if safety_flags.get(flag) is not True:
            errors.append("INVALID_SAFETY_FLAG")
            return


def _validate_review_flags(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    safety_flags = receipt_data.get("safety_flags")
    if not isinstance(safety_flags, Mapping):
        errors.append("INVALID_REVIEW_FLAG")
        return
    for flag in REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS:
        if safety_flags.get(flag) is not True:
            errors.append("INVALID_REVIEW_FLAG")
            return


def _validate_receipt_label(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    receipt_label = receipt_data.get("receipt_label")
    if receipt_label not in ALLOWED_RECEIPT_LABELS:
        errors.append("INVALID_RECEIPT_LABEL")


def _validate_human_review(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    if receipt_data.get("human_review_required") is not True:
        errors.append("HUMAN_REVIEW_REQUIRED")


def _validate_non_authority_notice(receipt_data: Mapping[str, Any], errors: list[str]) -> None:
    notice = receipt_data.get("non_authority_notice")
    if not isinstance(notice, str) or not notice.strip():
        errors.append("INVALID_NON_AUTHORITY_NOTICE")
        return
    normalized = _normalize(notice)
    for phrase in _NON_AUTHORITY_PERMISSION_PHRASES:
        if phrase in normalized:
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return
    for fragment in _NON_AUTHORITY_REQUIRED_FRAGMENTS:
        if _normalize(fragment) not in normalized:
            errors.append("INVALID_NON_AUTHORITY_NOTICE")
            return


def validate_candidate_review_advisory_output_validation_receipt(
    receipt_data: Mapping[str, Any],
) -> HermesCandidateReviewAdvisoryOutputValidationReceiptResult:
    """Validate an in-memory candidate-review advisory output receipt."""
    if not isinstance(receipt_data, Mapping):
        return _invalid_result(("UNSUPPORTED_INPUT_SHAPE",))

    errors: list[str] = []

    _scan_raw_metadata(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _scan_forbidden(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_required_fields(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_safety_flags(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_review_flags(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_receipt_label(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_human_review(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    _validate_non_authority_notice(receipt_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    sanitized_flags = {
        flag: True for flag in REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS
    }
    sanitized_receipt: dict[str, Any] = {}
    for field in REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS:
        if field == "safety_flags":
            sanitized_receipt[field] = sanitized_flags
        else:
            sanitized_receipt[field] = receipt_data[field]

    receipt_label = str(receipt_data["receipt_label"])
    return HermesCandidateReviewAdvisoryOutputValidationReceiptResult(
        is_valid=True,
        receipt=sanitized_receipt,
        errors=(),
        warnings=(),
        receipt_label=receipt_label,
        safety_flags=sanitized_flags,
    )


def build_candidate_review_advisory_output_validation_receipt(
    receipt_data: Mapping[str, Any],
) -> HermesCandidateReviewAdvisoryOutputValidationReceiptResult:
    """Build and validate an advisory output receipt from caller data."""
    return validate_candidate_review_advisory_output_validation_receipt(receipt_data)


def assert_candidate_review_advisory_output_validation_receipt(
    receipt_data: Mapping[str, Any],
) -> HermesCandidateReviewAdvisoryOutputValidationReceiptResult:
    """Assert that receipt_data produces a valid advisory output receipt."""
    result = validate_candidate_review_advisory_output_validation_receipt(receipt_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_ADVISORY_OUTPUT_VALIDATION_RECEIPT: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result
