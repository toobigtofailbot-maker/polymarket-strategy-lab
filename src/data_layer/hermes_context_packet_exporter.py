"""Build sanitized in-memory context packets for manual Hermes research.

This module is a deterministic packet-builder foundation only. It accepts
explicit in-memory summaries and returns an in-memory result. It does not run
Hermes, execute prompts, call models or providers, access a network, read or
write files, use credentials or private state, create a command-line surface,
or perform paper/live, order, risk, scheduler, dashboard, or bot-loop work.

Stdlib-only. Local/offline/read-only. Added in WP100.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any


FORBIDDEN_USE_NOTICE = (
    "Research context only. Human review is required. "
    "This packet grants no operational or control authority."
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
        "hold",
        "live",
        "mnemo" "nic",
        "opportunity",
        "order",
        "passphrase",
        "position",
        "prompt",
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
    "authenticated endpoint",
    "bot loop",
    "bypass risk",
    "cancel order",
    "expected return",
    "fair value",
    "free form",
    "freeform",
    "kill switch override",
    "merge ready",
    "model call",
    "place order",
    "position size",
    "private endpoint",
    "private key",
    "provider config",
    "raw metadata",
    "raw payload",
    "raw prompt",
    "raw response",
    "risk override",
    "run prompt",
    "stop loss",
    "take profit",
    "wallet balance",
    "wallet private",
    "override risk",
)


@dataclass(frozen=True)
class HermesContextPacketBuildResult:
    """Public result for deterministic context-packet construction."""

    is_valid: bool
    packet: dict[str, Any]
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
) -> object:
    """Recursively validate and deterministically normalize one input value."""
    if isinstance(value, str):
        if _is_unsafe_text(value):
            errors.append(f"unsafe_value_{counter[0]:03d}")
            counter[0] += 1
        return value.strip()

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
            normalized_key = key.strip()
            if not normalized_key:
                errors.append(f"invalid_key_{counter[0]:03d}")
                counter[0] += 1
            elif normalized_key in normalized_keys:
                errors.append(f"conflicting_key_{counter[0]:03d}")
                counter[0] += 1
            normalized_keys.add(normalized_key)
            if _is_raw_mapping_key(normalized_key):
                errors.append(f"unsafe_raw_key_{counter[0]:03d}")
                counter[0] += 1
            elif _is_unsafe_text(normalized_key):
                errors.append(f"unsafe_key_{counter[0]:03d}")
                counter[0] += 1
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


def _required_text(
    value: object,
    errors: list[str],
    counter: list[int],
) -> str:
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
    warnings: list[str],
    counter: list[int],
    warning_counter: list[int],
) -> tuple[str, ...]:
    if value is None:
        warnings.append(f"optional_field_omitted_{warning_counter[0]:03d}")
        warning_counter[0] += 1
        return ()
    return _required_string_sequence(value, errors, counter, allow_empty=True)


def build_hermes_context_packet(
    *,
    packet_id: str,
    packet_type: str,
    artifact_id: str,
    artifact_type: str,
    source_refs: Sequence[str],
    provenance_status: str,
    staleness_status: str,
    data_quality_warnings: Sequence[str],
    known_missing_data: Sequence[str],
    summary: str,
    context_sections: Mapping[str, object],
    recommended_prompt_family: str,
    recommended_next_review_step: str,
    deterministic_owner: str,
    uncertainty_notes: Sequence[str] | None = None,
    assumptions: Sequence[str] | None = None,
    falsification_checks: Sequence[str] | None = None,
    operator_notes: Sequence[str] | None = None,
    validator_requirements_reference: str | None = None,
    related_repo_truth_refs: Sequence[str] | None = None,
) -> HermesContextPacketBuildResult:
    """Build one sanitized, advisory-only Hermes context packet in memory.

    Invalid input fails closed with an empty packet. Diagnostic strings are
    deterministic neutral codes and never include caller-provided content.
    """
    errors: list[str] = []
    warnings: list[str] = []
    counter = [0]
    warning_counter = [0]

    required_text_values = {
        "packet_id": _required_text(packet_id, errors, counter),
        "packet_type": _required_text(packet_type, errors, counter),
        "artifact_id": _required_text(artifact_id, errors, counter),
        "artifact_type": _required_text(artifact_type, errors, counter),
        "provenance_status": _required_text(provenance_status, errors, counter),
        "staleness_status": _required_text(staleness_status, errors, counter),
        "summary": _required_text(summary, errors, counter),
        "recommended_research_family": _required_text(
            recommended_prompt_family, errors, counter
        ),
        "recommended_next_review_step": _required_text(
            recommended_next_review_step, errors, counter
        ),
        "deterministic_owner": _required_text(deterministic_owner, errors, counter),
    }
    required_sequences = {
        "source_refs": _required_string_sequence(
            source_refs, errors, counter, allow_empty=False
        ),
        "data_quality_warnings": _required_string_sequence(
            data_quality_warnings, errors, counter, allow_empty=True
        ),
        "known_missing_data": _required_string_sequence(
            known_missing_data, errors, counter, allow_empty=True
        ),
    }

    if not isinstance(context_sections, Mapping) or not context_sections:
        errors.append(f"missing_required_field_{counter[0]:03d}")
        counter[0] += 1
        normalized_context: object = {}
    else:
        normalized_context = context_sections

    optional_sequences = {
        "uncertainty_notes": _optional_string_sequence(
            uncertainty_notes, errors, warnings, counter, warning_counter
        ),
        "assumptions": _optional_string_sequence(
            assumptions, errors, warnings, counter, warning_counter
        ),
        "falsification_checks": _optional_string_sequence(
            falsification_checks, errors, warnings, counter, warning_counter
        ),
        "operator_notes": _optional_string_sequence(
            operator_notes, errors, warnings, counter, warning_counter
        ),
        "related_repo_truth_refs": _optional_string_sequence(
            related_repo_truth_refs, errors, warnings, counter, warning_counter
        ),
    }

    caller_content: dict[str, object] = {
        **required_text_values,
        **required_sequences,
        "context_sections": normalized_context,
        **optional_sequences,
    }
    if validator_requirements_reference is None:
        warnings.append(f"optional_field_omitted_{warning_counter[0]:03d}")
        warning_counter[0] += 1
    else:
        caller_content["validator_requirements_reference"] = _required_text(
            validator_requirements_reference, errors, counter
        )

    normalized_caller_content = _validate_and_normalize_value(
        caller_content, errors, counter, set()
    )

    if errors:
        return HermesContextPacketBuildResult(
            is_valid=False,
            packet={},
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    assert isinstance(normalized_caller_content, dict)
    packet: dict[str, Any] = {
        **normalized_caller_content,
        "advisory_only": True,
        "human_review_required": True,
        "forbidden_use_notice": FORBIDDEN_USE_NOTICE,
        "no_execution_authority": True,
        "no_runtime_authority": True,
        "no_credential_authority": True,
        "no_paper_or_live_authority": True,
    }
    return HermesContextPacketBuildResult(
        is_valid=True,
        packet=packet,
        errors=(),
        warnings=tuple(warnings),
    )
