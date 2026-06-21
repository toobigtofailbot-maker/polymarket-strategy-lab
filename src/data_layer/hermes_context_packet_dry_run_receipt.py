"""Build in-memory dry-run receipts for Hermes context packets.

This module is a deterministic local/offline/read-only receipt helper. It
accepts explicit in-memory inputs and returns an in-memory result. It does not
run Hermes, execute prompts, call models or providers, access a network, read
or write files, use credentials or private state, create a command-line
surface, or perform paper/live, order, risk, scheduler, dashboard, or bot-loop
work.

Stdlib-only. Local/offline/read-only. Added in WP101.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any


REQUIRED_PACKET_SAFETY_FLAGS: tuple[str, ...] = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_runtime_authority",
    "no_credential_authority",
    "no_paper_or_live_authority",
)

REQUIRED_PACKET_FIELDS: tuple[str, ...] = (
    "packet_id",
    "packet_type",
    "artifact_id",
    "artifact_type",
    "source_refs",
    "provenance_status",
    "staleness_status",
    "summary",
    "context_sections",
    "recommended_research_family",
    "recommended_next_review_step",
)

REQUIRED_READINESS_CHECKS: tuple[str, ...] = (
    "packet_validated",
    "source_refs_checked",
    "provenance_checked",
    "staleness_checked",
    "forbidden_authority_checked",
    "human_review_gate_checked",
    "no_prompt_execution_checked",
    "no_runtime_checked",
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

_SAFE_KEY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        *REQUIRED_PACKET_SAFETY_FLAGS,
        *REQUIRED_READINESS_CHECKS,
        "dry_run_only",
        "manual_review_required",
        "prompt_execution_performed",
        "hermes_runtime_used",
        "model_or_provider_called",
        "file_written",
        "network_used",
        "paper_or_live_authority",
        "execution_or_risk_authority",
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

_ALLOWED_REPO_TRUTH_REFS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "AI_CODING_AGENT_START_HERE.md",
        "CODEX_START_HERE.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "docs/deferred_items_log.md",
        "docs/status_entries/WP99.md",
        "docs/status_entries/WP100.md",
    }
)


@dataclass(frozen=True)
class HermesContextPacketDryRunReceiptResult:
    """Public result for deterministic context-packet receipt construction."""

    is_valid: bool
    receipt: dict[str, Any]
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


def _is_repo_truth_ref(value: str) -> bool:
    return value in _ALLOWED_REPO_TRUTH_REFS or value.startswith("docs/status_entries/")


def _validate_packet(
    packet: Mapping[str, object],
    errors: list[str],
    counter: list[int],
) -> dict[str, Any]:
    normalized_packet = _validate_and_normalize_value(packet, errors, counter, set())
    if not isinstance(normalized_packet, dict):
        errors.append(f"invalid_packet_{counter[0]:03d}")
        counter[0] += 1
        return {}

    for flag in REQUIRED_PACKET_SAFETY_FLAGS:
        if flag not in normalized_packet:
            errors.append(f"missing_safety_flag_{counter[0]:03d}")
            counter[0] += 1
        elif normalized_packet[flag] is not True:
            errors.append(f"invalid_safety_flag_{counter[0]:03d}")
            counter[0] += 1

    for field in REQUIRED_PACKET_FIELDS:
        if field not in normalized_packet:
            errors.append(f"missing_packet_field_{counter[0]:03d}")
            counter[0] += 1

    source_refs = normalized_packet.get("source_refs")
    if not isinstance(source_refs, tuple) or not source_refs:
        errors.append(f"invalid_packet_source_refs_{counter[0]:03d}")
        counter[0] += 1
    if not isinstance(normalized_packet.get("context_sections"), dict):
        errors.append(f"invalid_packet_context_{counter[0]:03d}")
        counter[0] += 1

    return normalized_packet


def _validate_readiness_checks(
    readiness_checks: Mapping[str, bool],
    errors: list[str],
    counter: list[int],
) -> dict[str, bool]:
    normalized_checks = _validate_and_normalize_value(
        readiness_checks, errors, counter, set()
    )
    if not isinstance(normalized_checks, dict):
        errors.append(f"invalid_readiness_checks_{counter[0]:03d}")
        counter[0] += 1
        return {}
    if set(normalized_checks) != set(REQUIRED_READINESS_CHECKS):
        errors.append(f"invalid_readiness_check_set_{counter[0]:03d}")
        counter[0] += 1
    for key in REQUIRED_READINESS_CHECKS:
        if normalized_checks.get(key) is not True:
            errors.append(f"invalid_readiness_check_{counter[0]:03d}")
            counter[0] += 1
    return {key: bool(normalized_checks.get(key)) for key in REQUIRED_READINESS_CHECKS}


def build_hermes_context_packet_dry_run_receipt(
    *,
    receipt_id: str,
    packet: Mapping[str, object],
    reviewer_id: str,
    dry_run_scope: str,
    checked_source_refs: Sequence[str],
    readiness_checks: Mapping[str, bool],
    stop_reasons: Sequence[str] | None = None,
    operator_notes: Sequence[str] | None = None,
    related_repo_truth_refs: Sequence[str] | None = None,
) -> HermesContextPacketDryRunReceiptResult:
    """Build one sanitized local dry-run receipt in memory.

    Invalid input fails closed with an empty receipt. Diagnostic strings are
    deterministic neutral codes and never include caller-provided content.
    """
    errors: list[str] = []
    counter = [0]

    normalized_receipt_id = _required_text(receipt_id, errors, counter)
    normalized_reviewer_id = _required_text(reviewer_id, errors, counter)
    normalized_scope = _required_text(dry_run_scope, errors, counter)

    normalized_packet = _validate_packet(packet, errors, counter)
    normalized_checked_refs = _required_string_sequence(
        checked_source_refs, errors, counter, allow_empty=False
    )
    normalized_related_refs = _optional_string_sequence(
        related_repo_truth_refs, errors, counter
    )
    normalized_stop_reasons = _optional_string_sequence(stop_reasons, errors, counter)
    normalized_operator_notes = _optional_string_sequence(
        operator_notes, errors, counter
    )
    normalized_readiness_checks = _validate_readiness_checks(
        readiness_checks, errors, counter
    )

    caller_content = {
        "receipt_id": normalized_receipt_id,
        "reviewer_id": normalized_reviewer_id,
        "dry_run_scope": normalized_scope,
        "checked_source_refs": normalized_checked_refs,
        "related_repo_truth_refs": normalized_related_refs,
        "stop_reasons": normalized_stop_reasons,
        "operator_notes": normalized_operator_notes,
    }
    _validate_and_normalize_value(caller_content, errors, counter, set())

    packet_source_refs = set(normalized_packet.get("source_refs", ()))
    related_refs = set(normalized_related_refs)
    for source_ref in normalized_checked_refs:
        if source_ref in packet_source_refs:
            continue
        if source_ref in related_refs or _is_repo_truth_ref(source_ref):
            continue
        errors.append(f"unverified_source_ref_{counter[0]:03d}")
        counter[0] += 1

    if normalized_stop_reasons:
        errors.append(f"stop_reasons_present_{counter[0]:03d}")
        counter[0] += 1

    if errors:
        return HermesContextPacketDryRunReceiptResult(
            is_valid=False,
            receipt={},
            errors=tuple(errors),
            warnings=(),
        )

    receipt: dict[str, Any] = {
        "receipt_id": normalized_receipt_id,
        "receipt_type": "HERMES_CONTEXT_PACKET_DRY_RUN_RECEIPT_V1",
        "receipt_status": "READY_FOR_MANUAL_REVIEW",
        "packet_id": normalized_packet["packet_id"],
        "packet_type": normalized_packet["packet_type"],
        "artifact_id": normalized_packet["artifact_id"],
        "artifact_type": normalized_packet["artifact_type"],
        "source_refs": normalized_packet["source_refs"],
        "checked_source_refs": normalized_checked_refs,
        "related_repo_truth_refs": normalized_related_refs,
        "reviewer_id": normalized_reviewer_id,
        "dry_run_scope": normalized_scope,
        "provenance_status": normalized_packet["provenance_status"],
        "staleness_status": normalized_packet["staleness_status"],
        "recommended_research_family": normalized_packet[
            "recommended_research_family"
        ],
        "recommended_next_review_step": normalized_packet[
            "recommended_next_review_step"
        ],
        "readiness_checks": normalized_readiness_checks,
        "operator_notes": normalized_operator_notes,
        "dry_run_only": True,
        "manual_review_required": True,
        "prompt_execution_performed": False,
        "hermes_runtime_used": False,
        "model_or_provider_called": False,
        "file_written": False,
        "network_used": False,
        "paper_or_live_authority": False,
        "execution_or_risk_authority": False,
    }
    return HermesContextPacketDryRunReceiptResult(
        is_valid=True,
        receipt=receipt,
        errors=(),
        warnings=(),
    )
