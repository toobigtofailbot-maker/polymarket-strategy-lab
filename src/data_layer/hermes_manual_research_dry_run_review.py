"""Build in-memory manual research dry-run operator review records.

This module is a deterministic local/offline/read-only operator-review helper.
It accepts explicit in-memory inputs including a WP101 dry-run receipt and
returns an in-memory result. It does not run Hermes, execute prompts, call
models or providers, access a network, read or write files, use credentials
or private state, create a command-line surface, or perform paper/live, order,
risk, scheduler, dashboard, or bot-loop work.

Stdlib-only. Local/offline/read-only. Added in WP102.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any


REQUIRED_SOURCE_REVIEW_CHECKS: tuple[str, ...] = (
    "receipt_reviewed",
    "source_refs_compared",
    "operator_runbook_compared",
    "research_family_allowed",
    "human_review_gate_checked",
    "no_prompt_execution_checked",
    "no_runtime_checked",
    "no_file_network_checked",
    "no_paper_live_checked",
    "no_execution_risk_checked",
)

_RECEIPT_REQUIRED_TYPE = "HERMES_CONTEXT_PACKET_DRY_RUN_RECEIPT_V1"
_RECEIPT_REQUIRED_STATUS = "READY_FOR_MANUAL_REVIEW"

_RECEIPT_REQUIRED_TRUE_FLAGS: tuple[str, ...] = (
    "dry_run_only",
    "manual_review_required",
)

_RECEIPT_REQUIRED_FALSE_FLAGS: tuple[str, ...] = (
    "prompt_execution_performed",
    "hermes_runtime_used",
    "model_or_provider_called",
    "file_written",
    "network_used",
    "paper_or_live_authority",
    "execution_or_risk_authority",
)

_REQUIRED_RECEIPT_IDENTITY_FIELDS: tuple[str, ...] = (
    "receipt_id",
    "packet_id",
    "packet_type",
)

_REQUIRED_RECEIPT_SOURCE_REF_FIELDS: tuple[str, ...] = (
    "source_refs",
    "checked_source_refs",
)

# Keys that contain forbidden-term substrings but are explicitly allowed
# because they are approved safety-flag names or required structural keys.
_SAFE_KEY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        # WP101 receipt field names
        "receipt_id",
        "receipt_type",
        "receipt_status",
        "packet_id",
        "packet_type",
        "artifact_id",
        "artifact_type",
        "source_refs",
        "checked_source_refs",
        "related_repo_truth_refs",
        "reviewer_id",
        "dry_run_scope",
        "provenance_status",
        "staleness_status",
        "recommended_research_family",
        "recommended_next_review_step",
        "readiness_checks",
        "operator_notes",
        # WP101 receipt safety flags
        "dry_run_only",
        "manual_review_required",
        "prompt_execution_performed",
        "hermes_runtime_used",
        "model_or_provider_called",
        "file_written",
        "network_used",
        "paper_or_live_authority",
        "execution_or_risk_authority",
        # WP101 readiness check names
        "packet_validated",
        "source_refs_checked",
        "provenance_checked",
        "staleness_checked",
        "forbidden_authority_checked",
        "human_review_gate_checked",
        "no_prompt_execution_checked",
        "no_runtime_checked",
        # WP100 packet safety flag names
        "advisory_only",
        "human_review_required",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "forbidden_use_notice",
        # WP102 review output field names
        "review_id",
        "review_type",
        "review_status",
        "operator_id",
        "selected_research_family",
        "selected_operator_runbook_ref",
        "source_review_checks",
        # WP102 review output safety flags
        "credential_or_account_authority",
        # WP102 source review check names (those with forbidden-term substrings)
        "no_file_network_checked",
        "no_paper_live_checked",
        "no_execution_risk_checked",
        # Additional common receipt/packet field keys
        "receipt_reviewed",
        "source_refs_compared",
        "operator_runbook_compared",
        "research_family_allowed",
    }
)

_RAW_MAPPING_KEY_TERMS: frozenset[str] = frozenset(
    {
        "metadata",
        "raw metadata",
        "source metadata",
        "raw response",
        "model response",
        "raw prompt",
        "prompt",
        "freeform",
        "free form",
        "raw payload",
        "raw payloads",
        "completion",
    }
)

_FORBIDDEN_SINGLE_WORDS: frozenset[str] = frozenset(
    {
        "account",
        "alpha",
        "buy",
        "credential",
        "daemon",
        "edge",
        "entry",
        "execute",
        "execution",
        "exit",
        "live",
        "mnemo" "nic",
        "opportunity",
        "order",
        "passphrase",
        "position",
        "runtime",
        "scheduler",
        "secret",
        "sell",
        "signal",
        "token",
        "trade",
    }
)

_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "api key",
    "approve pr",
    "bot loop",
    "bypass risk",
    "cancel order",
    "expected return",
    "fair value",
    "file write",
    "free form",
    "freeform",
    "kill switch override",
    "merge ready",
    "model call",
    "place order",
    "position size",
    "private key",
    "prompt runner",
    "provider config",
    "raw metadata",
    "raw payload",
    "raw prompt",
    "raw response",
    "risk override",
    "run prompt",
    "stop loss",
    "take profit",
    "trade signal",
    "wallet balance",
    "wallet private",
    "network call",
    "override risk",
    "paper approved",
    "live approved",
)


@dataclass(frozen=True)
class HermesManualResearchDryRunReviewResult:
    """Public result for deterministic operator review record construction."""

    is_valid: bool
    review: dict[str, Any]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _normalize_text(value: str) -> str:
    normalized = value.casefold().replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


def _word_tokens(value: str) -> frozenset[str]:
    cleaned = "".join(character if character.isalnum() else " " for character in value)
    return frozenset(cleaned.split())


def _is_unsafe_text(value: str) -> bool:
    normalized = _normalize_text(value)
    tokens = _word_tokens(normalized)
    return bool(tokens & _FORBIDDEN_SINGLE_WORDS) or any(
        phrase in normalized for phrase in _FORBIDDEN_PHRASES
    )


def _is_raw_mapping_key(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in _RAW_MAPPING_KEY_TERMS or normalized.startswith("raw ")


def _validate_and_normalize_value(
    value: object,
    errors: list[str],
    counter: list[int],
    active_container_ids: set[int],
    *,
    value_is_mapping_key: bool = False,
) -> object:
    if isinstance(value, str):
        stripped = value.strip()
        if value_is_mapping_key and stripped in _SAFE_KEY_EXCEPTIONS:
            return stripped
        if _is_raw_mapping_key(stripped):
            errors.append(f"unsafe_raw_key_{counter[0]:03d}")
            counter[0] += 1
        elif _is_unsafe_text(stripped):
            errors.append(f"unsafe_text_{counter[0]:03d}")
            counter[0] += 1
        return stripped

    if value is None or isinstance(value, (bool, int)):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            errors.append(f"unsupported_value_{counter[0]:03d}")
            counter[0] += 1
        return value

    if isinstance(value, Mapping):
        container_id = id(value)
        if container_id in active_container_ids:
            errors.append(f"unsupported_structure_{counter[0]:03d}")
            counter[0] += 1
            return {}
        active_container_ids.add(container_id)
        normalized_items: list[tuple[str, object]] = []
        normalized_keys: set[str] = set()
        for key, nested_value in value.items():
            if not isinstance(key, str):
                errors.append(f"invalid_key_type_{counter[0]:03d}")
                counter[0] += 1
                continue
            normalized_key = _validate_and_normalize_value(
                key,
                errors,
                counter,
                active_container_ids,
                value_is_mapping_key=True,
            )
            assert isinstance(normalized_key, str)
            if not normalized_key:
                errors.append(f"invalid_key_{counter[0]:03d}")
                counter[0] += 1
            elif normalized_key in normalized_keys:
                errors.append(f"conflicting_key_{counter[0]:03d}")
                counter[0] += 1
            normalized_keys.add(normalized_key)
            normalized_items.append(
                (
                    normalized_key,
                    _validate_and_normalize_value(
                        nested_value, errors, counter, active_container_ids
                    ),
                )
            )
        active_container_ids.remove(container_id)
        return dict(sorted(normalized_items, key=lambda item: item[0]))

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        container_id = id(value)
        if container_id in active_container_ids:
            errors.append(f"unsupported_structure_{counter[0]:03d}")
            counter[0] += 1
            return ()
        active_container_ids.add(container_id)
        normalized = tuple(
            _validate_and_normalize_value(item, errors, counter, active_container_ids)
            for item in value
        )
        active_container_ids.remove(container_id)
        return normalized

    errors.append(f"unsupported_value_{counter[0]:03d}")
    counter[0] += 1
    return None


def _required_text(value: object, errors: list[str], counter: list[int]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing_required_field_{counter[0]:03d}")
        counter[0] += 1
        return ""
    return value.strip()


def _required_string_sequence(
    value: object,
    errors: list[str],
    counter: list[int],
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        errors.append(f"invalid_required_field_{counter[0]:03d}")
        counter[0] += 1
        return ()
    normalized = tuple(item.strip() for item in value if isinstance(item, str))
    if len(normalized) != len(value) or any(not item for item in normalized):
        errors.append(f"invalid_required_field_{counter[0]:03d}")
        counter[0] += 1
    if not allow_empty and not normalized:
        errors.append(f"missing_required_field_{counter[0]:03d}")
        counter[0] += 1
    return normalized


def _optional_string_sequence(
    value: Sequence[str] | None,
    errors: list[str],
    counter: list[int],
) -> tuple[str, ...]:
    if value is None:
        return ()
    return _required_string_sequence(value, errors, counter, allow_empty=True)


def _validate_receipt(
    receipt: Mapping[str, object],
    errors: list[str],
    counter: list[int],
) -> dict[str, Any]:
    normalized_receipt = _validate_and_normalize_value(receipt, errors, counter, set())
    if not isinstance(normalized_receipt, dict):
        errors.append(f"invalid_receipt_{counter[0]:03d}")
        counter[0] += 1
        return {}

    receipt_type = normalized_receipt.get("receipt_type")
    if receipt_type != _RECEIPT_REQUIRED_TYPE:
        errors.append(f"invalid_receipt_type_{counter[0]:03d}")
        counter[0] += 1

    receipt_status = normalized_receipt.get("receipt_status")
    if receipt_status != _RECEIPT_REQUIRED_STATUS:
        errors.append(f"invalid_receipt_status_{counter[0]:03d}")
        counter[0] += 1

    for flag in _RECEIPT_REQUIRED_TRUE_FLAGS:
        if normalized_receipt.get(flag) is not True:
            errors.append(f"invalid_receipt_safety_flag_{counter[0]:03d}")
            counter[0] += 1

    for flag in _RECEIPT_REQUIRED_FALSE_FLAGS:
        if normalized_receipt.get(flag) is not False:
            errors.append(f"invalid_receipt_safety_flag_{counter[0]:03d}")
            counter[0] += 1

    for field in _REQUIRED_RECEIPT_IDENTITY_FIELDS:
        field_value = normalized_receipt.get(field)
        if not isinstance(field_value, str) or not field_value.strip():
            errors.append(f"missing_receipt_identity_field_{counter[0]:03d}")
            counter[0] += 1

    for field in _REQUIRED_RECEIPT_SOURCE_REF_FIELDS:
        field_value = normalized_receipt.get(field)
        if not isinstance(field_value, (list, tuple)) or not field_value:
            errors.append(f"missing_receipt_source_ref_{counter[0]:03d}")
            counter[0] += 1

    return normalized_receipt


def _validate_source_review_checks(
    source_review_checks: Mapping[str, bool],
    errors: list[str],
    counter: list[int],
) -> dict[str, bool]:
    normalized_checks = _validate_and_normalize_value(
        source_review_checks, errors, counter, set()
    )
    if not isinstance(normalized_checks, dict):
        errors.append(f"invalid_source_review_checks_{counter[0]:03d}")
        counter[0] += 1
        return {}
    if set(normalized_checks) != set(REQUIRED_SOURCE_REVIEW_CHECKS):
        errors.append(f"invalid_source_review_check_set_{counter[0]:03d}")
        counter[0] += 1
    for key in REQUIRED_SOURCE_REVIEW_CHECKS:
        if normalized_checks.get(key) is not True:
            errors.append(f"invalid_source_review_check_{counter[0]:03d}")
            counter[0] += 1
    return {key: bool(normalized_checks.get(key)) for key in REQUIRED_SOURCE_REVIEW_CHECKS}


def build_hermes_manual_research_dry_run_review(
    *,
    review_id: str,
    dry_run_receipt: Mapping[str, object],
    operator_id: str,
    selected_research_family: str,
    selected_operator_runbook_ref: str,
    source_review_checks: Mapping[str, bool],
    stop_reasons: Sequence[str] | None = None,
    operator_notes: Sequence[str] | None = None,
    related_repo_truth_refs: Sequence[str] | None = None,
) -> HermesManualResearchDryRunReviewResult:
    """Build one sanitized local manual operator-review record in memory.

    Invalid input fails closed with an empty review. Diagnostic strings are
    deterministic neutral codes and never include caller-provided content.
    """
    errors: list[str] = []
    counter = [0]

    normalized_review_id = _required_text(review_id, errors, counter)
    normalized_operator_id = _required_text(operator_id, errors, counter)
    normalized_research_family = _required_text(
        selected_research_family, errors, counter
    )
    normalized_runbook_ref = _required_text(
        selected_operator_runbook_ref, errors, counter
    )

    normalized_receipt = _validate_receipt(dry_run_receipt, errors, counter)
    normalized_source_review_checks = _validate_source_review_checks(
        source_review_checks, errors, counter
    )

    normalized_stop_reasons = _optional_string_sequence(stop_reasons, errors, counter)
    normalized_operator_notes = _optional_string_sequence(
        operator_notes, errors, counter
    )
    normalized_related_refs = _optional_string_sequence(
        related_repo_truth_refs, errors, counter
    )

    caller_text_content: dict[str, object] = {
        "review_id": normalized_review_id,
        "operator_id": normalized_operator_id,
        "selected_research_family": normalized_research_family,
        "selected_operator_runbook_ref": normalized_runbook_ref,
        "operator_notes": normalized_operator_notes,
        "related_repo_truth_refs": normalized_related_refs,
        "stop_reasons": normalized_stop_reasons,
    }
    _validate_and_normalize_value(caller_text_content, errors, counter, set())

    if normalized_stop_reasons:
        errors.append(f"stop_reasons_present_{counter[0]:03d}")
        counter[0] += 1

    if errors:
        return HermesManualResearchDryRunReviewResult(
            is_valid=False,
            review={},
            errors=tuple(errors),
            warnings=(),
        )

    review: dict[str, Any] = {
        "review_id": normalized_review_id,
        "review_type": "HERMES_MANUAL_RESEARCH_DRY_RUN_OPERATOR_REVIEW_V1",
        "review_status": "READY_FOR_MANUAL_RESEARCH_REVIEW",
        "receipt_id": normalized_receipt["receipt_id"],
        "receipt_type": normalized_receipt["receipt_type"],
        "packet_id": normalized_receipt["packet_id"],
        "packet_type": normalized_receipt["packet_type"],
        "operator_id": normalized_operator_id,
        "selected_research_family": normalized_research_family,
        "selected_operator_runbook_ref": normalized_runbook_ref,
        "source_review_checks": normalized_source_review_checks,
        "related_repo_truth_refs": normalized_related_refs,
        "operator_notes": normalized_operator_notes,
        "advisory_only": True,
        "manual_review_required": True,
        "dry_run_only": True,
        "prompt_execution_performed": False,
        "hermes_runtime_used": False,
        "model_or_provider_called": False,
        "file_written": False,
        "network_used": False,
        "paper_or_live_authority": False,
        "execution_or_risk_authority": False,
        "credential_or_account_authority": False,
    }
    return HermesManualResearchDryRunReviewResult(
        is_valid=True,
        review=review,
        errors=(),
        warnings=(),
    )
