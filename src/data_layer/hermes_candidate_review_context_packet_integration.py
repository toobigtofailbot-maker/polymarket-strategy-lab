"""Build sanitized in-memory candidate-review context packets for Hermes manual research.

This module is a deterministic local/offline/read-only candidate-review-to-context-packet
adapter. It accepts explicit in-memory candidate-review report data and returns a WP100
context packet build result. It does not run Hermes, execute prompts, call models or
providers, access a network, read or write files, use credentials or private state, create
a command-line surface, or perform paper/live, order, risk, scheduler, dashboard, or
bot-loop work.

Stdlib-only plus one approved internal import from
src.data_layer.hermes_context_packet_exporter (WP100). Local/offline/read-only.
Added in WP103.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.data_layer.hermes_context_packet_exporter import (
    HermesContextPacketBuildResult,
    build_hermes_context_packet,
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
        "mnemonic",
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
    "account data",
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
    "live approved",
    "merge ready",
    "model call",
    "network call",
    "override risk",
    "paper approved",
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
)

_PACKET_TYPE = "CANDIDATE_REVIEW_CONTEXT_PACKET_V1"
_ARTIFACT_TYPE = "candidate_review_advisory_report"
_RESEARCH_FAMILY = "candidate_review_manual_research"
_DETERMINISTIC_OWNER = "candidate_review_context_packet_adapter"
_SUMMARY = (
    "Candidate review context packet for Hermes manual research review. "
    "Advisory-only. Human review required."
)


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


def _required_text(value: object, errors: list[str], counter: list[int]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing_required_field_{counter[0]:03d}")
        counter[0] += 1
        return ""
    stripped = value.strip()
    if _is_raw_mapping_key(stripped):
        errors.append(f"unsafe_raw_key_{counter[0]:03d}")
        counter[0] += 1
    elif _is_unsafe_text(stripped):
        errors.append(f"unsafe_value_{counter[0]:03d}")
        counter[0] += 1
    return stripped


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
    items: list[str] = []
    has_invalid = False
    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"invalid_required_field_{counter[0]:03d}")
            counter[0] += 1
            has_invalid = True
        else:
            stripped = item.strip()
            if _is_raw_mapping_key(stripped):
                errors.append(f"unsafe_raw_key_{counter[0]:03d}")
                counter[0] += 1
            elif _is_unsafe_text(stripped):
                errors.append(f"unsafe_value_{counter[0]:03d}")
                counter[0] += 1
            items.append(stripped)
    if not allow_empty and not items and not has_invalid:
        errors.append(f"missing_required_field_{counter[0]:03d}")
        counter[0] += 1
    return tuple(items)


def _optional_string_sequence(
    value: Sequence[str] | None,
    errors: list[str],
    counter: list[int],
) -> tuple[str, ...]:
    if value is None:
        return ()
    return _required_string_sequence(value, errors, counter, allow_empty=True)


def _optional_text(value: str | None, errors: list[str], counter: list[int]) -> str:
    if value is None:
        return ""
    return _required_text(value, errors, counter)


def build_candidate_review_hermes_context_packet(
    *,
    packet_id: str,
    report_identity: str,
    source_refs: Sequence[str],
    advisory_notice: str,
    human_review_required: bool,
    review_status: str,
    provenance_status: str,
    staleness_status: str,
    recommended_next_review_step: str,
    data_quality_warnings: Sequence[str] | None = None,
    known_missing_data: Sequence[str] | None = None,
    key_findings: Sequence[str] | None = None,
    limitations: Sequence[str] | None = None,
    rejection_reasons: Sequence[str] | None = None,
    report_reference: str | None = None,
    uncertainty_notes: Sequence[str] | None = None,
    assumptions: Sequence[str] | None = None,
    falsification_checks: Sequence[str] | None = None,
    related_repo_truth_refs: Sequence[str] | None = None,
) -> HermesContextPacketBuildResult:
    """Build one sanitized, advisory-only candidate-review Hermes context packet.

    Accepts explicit in-memory candidate-review report data only. Invalid
    input fails closed with an empty packet. Diagnostic strings are
    deterministic neutral codes and never include caller-provided content.

    Does not run Hermes, execute prompts, call models or providers, access
    networks, read or write files, use credentials or private state, create a
    CLI, or perform paper/live, order, risk, scheduler, dashboard, or
    bot-loop work. Added in WP103.
    """
    errors: list[str] = []
    counter = [0]

    if human_review_required is not True:
        errors.append(f"missing_human_review_required_{counter[0]:03d}")
        counter[0] += 1

    validated_packet_id = _required_text(packet_id, errors, counter)
    validated_report_identity = _required_text(report_identity, errors, counter)
    validated_advisory_notice = _required_text(advisory_notice, errors, counter)
    validated_review_status = _required_text(review_status, errors, counter)
    validated_provenance_status = _required_text(provenance_status, errors, counter)
    validated_staleness_status = _required_text(staleness_status, errors, counter)
    validated_next_review_step = _required_text(
        recommended_next_review_step, errors, counter
    )

    validated_source_refs = _required_string_sequence(
        source_refs, errors, counter, allow_empty=False
    )
    validated_data_quality_warnings = _optional_string_sequence(
        data_quality_warnings, errors, counter
    )
    validated_known_missing_data = _optional_string_sequence(
        known_missing_data, errors, counter
    )
    validated_key_findings = _optional_string_sequence(key_findings, errors, counter)
    validated_limitations = _optional_string_sequence(limitations, errors, counter)
    validated_rejection_reasons = _optional_string_sequence(
        rejection_reasons, errors, counter
    )
    validated_report_reference = _optional_text(report_reference, errors, counter)
    validated_uncertainty_notes = _optional_string_sequence(
        uncertainty_notes, errors, counter
    )
    validated_assumptions = _optional_string_sequence(assumptions, errors, counter)
    validated_falsification_checks = _optional_string_sequence(
        falsification_checks, errors, counter
    )
    validated_related_refs = _optional_string_sequence(
        related_repo_truth_refs, errors, counter
    )

    if errors:
        return HermesContextPacketBuildResult(
            is_valid=False,
            packet={},
            errors=tuple(errors),
            warnings=(),
        )

    context_sections: dict[str, object] = {
        "candidate_review_identity": validated_report_identity,
        "review_status": validated_review_status,
        "advisory_notice": validated_advisory_notice,
    }
    if validated_key_findings:
        context_sections["key_findings"] = list(validated_key_findings)
    if validated_limitations:
        context_sections["limitations"] = list(validated_limitations)
    if validated_rejection_reasons:
        context_sections["rejection_reasons"] = list(validated_rejection_reasons)
    if validated_report_reference:
        context_sections["report_reference"] = validated_report_reference

    return build_hermes_context_packet(
        packet_id=validated_packet_id,
        packet_type=_PACKET_TYPE,
        artifact_id=validated_report_identity,
        artifact_type=_ARTIFACT_TYPE,
        source_refs=list(validated_source_refs),
        provenance_status=validated_provenance_status,
        staleness_status=validated_staleness_status,
        data_quality_warnings=list(validated_data_quality_warnings),
        known_missing_data=list(validated_known_missing_data),
        summary=_SUMMARY,
        context_sections=context_sections,
        recommended_prompt_family=_RESEARCH_FAMILY,
        recommended_next_review_step=validated_next_review_step,
        deterministic_owner=_DETERMINISTIC_OWNER,
        uncertainty_notes=list(validated_uncertainty_notes) if validated_uncertainty_notes else None,
        assumptions=list(validated_assumptions) if validated_assumptions else None,
        falsification_checks=list(validated_falsification_checks) if validated_falsification_checks else None,
        operator_notes=None,
        validator_requirements_reference=None,
        related_repo_truth_refs=list(validated_related_refs) if validated_related_refs else None,
    )
