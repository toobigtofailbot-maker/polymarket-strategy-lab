"""In-memory artifact builder for Hermes candidate-review handoff manual export.

Implements the WP107 contract. Accepts a valid WP106 handoff result, validates
required conceptual groups, safety flags, decision label, forbidden content,
and raw-metadata keys, then returns a deterministic in-memory artifact
dictionary. Fails closed with neutral errors for invalid input. Never echoes
unsafe caller-provided input in errors, warnings, or artifact output.

Stdlib-only plus approved WP106 internal import. No file I/O. No network.
No subprocess. No CLI. No credentials. No paper/live/execution/risk/scheduler/
dashboard/bot-loop/runtime/Hermes behavior. Local/offline/read-only/in-memory
only. Added in WP108.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.data_layer.hermes_candidate_review_operator_handoff import (
    ALLOWED_HANDOFF_DECISION_LABELS,
    HermesCandidateReviewOperatorHandoffResult,
    REQUIRED_HANDOFF_GROUPS as _WP106_REQUIRED_GROUPS,
    REQUIRED_HANDOFF_SAFETY_FLAGS,
)


# ---------------------------------------------------------------------------
# Required output artifact conceptual groups (WP107 Section 5)
# ---------------------------------------------------------------------------

REQUIRED_ARTIFACT_GROUPS: tuple[str, ...] = (
    "artifact_identity",
    "source_handoff_identity",
    "chain_stage_summary",
    "manual_review_summary",
    "evidence_and_provenance_summary",
    "staleness_and_missing_data_summary",
    "uncertainty_and_limitations_summary",
    "falsification_summary",
    "human_decision_record_summary",
    "next_manual_research_step",
    "safety_flags",
    "forbidden_scope_notice",
)

# ---------------------------------------------------------------------------
# Required artifact safety flags (WP107 Section 6) — all must be True
# ---------------------------------------------------------------------------

REQUIRED_ARTIFACT_SAFETY_FLAGS: tuple[str, ...] = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_runtime_authority",
    "no_credential_authority",
    "no_paper_or_live_authority",
    "no_prompt_execution",
    "no_file_or_network_beyond_explicit_local_manual_export",
    "no_strategy_promotion_authority",
    "no_pr_approval_authority",
    "no_trade_signal",
    "no_position_sizing",
    "no_expected_return",
)

# ---------------------------------------------------------------------------
# Forbidden content terms — matched against normalized caller-supplied input
# ---------------------------------------------------------------------------

_FORBIDDEN_TERMS: tuple[str, ...] = (
    "buy",
    "sell",
    "order",
    "trade",
    "trading",
    "execute",
    "execution",
    "position",
    "position size",
    "entry",
    "exit",
    "stop loss",
    "take profit",
    "expected return",
    "edge",
    "alpha",
    "fair value",
    "confidence to trade",
    "trade ready",
    "tradable",
    "tradability",
    "live ready",
    "paper ready",
    "deployment ready",
    "approve pr",
    "approve pull request",
    "merge ready",
    "risk override",
    "strategy promotion",
    "credential",
    "private key",
    "api key",
    "secret",
    "passphrase",
    "wallet",
    "account endpoint",
    "private endpoint",
    "provider",
    "model call",
    "prompt execution",
    "prompt runner",
    "hermes runtime",
    "scheduler",
    "bot loop",
    "daemon",
    "network poller",
    "file writer",
    "report writer",
    "exporter",
)

# Raw/free-form metadata key patterns — rejected at any nesting depth
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

# Keys that represent safety-boundary notices or authority flag names.
# These key names contain forbidden-term substrings by design (they name
# what is NOT authorized). They must not be scanned as data-bearing content.
_BOUNDARY_KEY_EXCEPTIONS: frozenset[str] = frozenset({
    # Required boundary notice field in artifact output
    "forbidden_scope_notice",
    # WP106 safety flag key names (contain forbidden term substrings by design)
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_runtime_authority",
    "no_credential_authority",
    "no_paper_or_live_authority",
    "no_prompt_execution",
    "no_file_or_network",
    "no_strategy_promotion_authority",
    "no_pr_approval_authority",
    # WP107/WP108 artifact safety flag key names
    "no_file_or_network_beyond_explicit_local_manual_export",
    "no_trade_signal",
    "no_position_sizing",
    "no_expected_return",
    # WP106 keys whose values are boundary codes, not recommendations
    "rejection_reasons",
    "source_review_checklist",
})

# Chain stages included in every artifact (builder-controlled, not caller data)
_CHAIN_STAGES: tuple[str, ...] = (
    "WP103_candidate_review_context_packet",
    "WP101_dry_run_receipt",
    "WP102_manual_operator_review",
    "WP104_manual_chain_smoke",
    "WP105_operator_handoff_contract",
    "WP106_in_memory_handoff_object",
)

# Forbidden scope notice text (builder-controlled boundary notice, not data)
_FORBIDDEN_SCOPE_NOTICE: str = (
    "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED: "
    "This artifact is not a trade signal, not a trade recommendation, "
    "not a position-sizing guidance, not an expected-return estimate, "
    "not a paper or live readiness statement, not a strategy promotion, "
    "not a risk authorization, not a PR approval, "
    "not a Hermes runtime instruction, not an execution authority, "
    "not a credential access permission, and not an automated instruction. "
    "It requires human review before any use. "
    "Any next research step cited is a manual research suggestion only."
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateReviewManualExportArtifactResult:
    """Result of building a Hermes candidate-review handoff manual export artifact.

    Advisory only. Does not authorize execution, credential access, paper/live,
    strategy promotion, PR approval, runtime, scheduler, bot-loop, file/network,
    or prompt execution. Human review is required. Added in WP108.
    """

    is_valid: bool
    artifact: dict[str, Any]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").replace("-", " ")


def _scan_forbidden_string(value: str, errors: list[str], counter: list[int]) -> None:
    norm = _normalize(value)
    for term in _FORBIDDEN_TERMS:
        if term in norm:
            errors.append("FORBIDDEN_CONTENT_DETECTED")
            counter[0] += 1
            if counter[0] >= 20:
                return
            break


def _scan_forbidden(value: object, errors: list[str], counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    if counter[0] >= 20:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k) in _BOUNDARY_KEY_EXCEPTIONS:
                continue
            _scan_forbidden_string(str(k), errors, counter)
            if counter[0] >= 20:
                return
            _scan_forbidden(v, errors, counter)
            if counter[0] >= 20:
                return
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_forbidden(item, errors, counter)
            if counter[0] >= 20:
                return
    elif isinstance(value, str):
        _scan_forbidden_string(value, errors, counter)


def _scan_raw_metadata(value: object, errors: list[str], depth: int = 0) -> None:
    if depth > 10:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _RAW_METADATA_KEYS:
                errors.append("RAW_METADATA_NOT_ALLOWED")
            _scan_raw_metadata(v, errors, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_raw_metadata(item, errors, depth + 1)


def _invalid_result(errors: tuple[str, ...]) -> CandidateReviewManualExportArtifactResult:
    return CandidateReviewManualExportArtifactResult(
        is_valid=False,
        artifact={},
        errors=errors,
        warnings=(),
    )


def _safe_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _safe_list_count(value: object) -> int:
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def _safe_bool(value: object) -> bool:
    return value is True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_candidate_review_manual_export_artifact(
    *,
    artifact_id: str,
    handoff_result: object,
    generated_by: str = "hermes_candidate_review_handoff_manual_export_artifact_v1",
    contract_version: str = "WP108.v1",
    operator_role: str = "human_operator",
    manual_review_notice: str | None = None,
) -> CandidateReviewManualExportArtifactResult:
    """Build a deterministic in-memory manual export artifact from a valid WP106 handoff.

    Validates caller inputs, confirms the handoff result is a valid WP106 result,
    checks required conceptual groups, safety flags, decision label, forbidden
    content, and raw-metadata keys. Returns a deterministic in-memory artifact
    dictionary with the 12 required conceptual groups from the WP107 contract.
    Fails closed with neutral error codes for invalid input. Never echoes unsafe
    caller-provided content.

    This function is advisory only. It does not run Hermes, execute prompts,
    call models or providers, access networks, read or write files, use
    credentials or private state, create a CLI, or perform paper/live, order,
    risk, scheduler, dashboard, or bot-loop work. Added in WP108.
    """
    errors: list[str] = []

    # --- artifact_id validation ---
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        errors.append("INVALID_ARTIFACT_ID")
        return _invalid_result(tuple(errors))

    # --- Caller string input forbidden scan ---
    for caller_field in (artifact_id, generated_by, contract_version, operator_role):
        if not isinstance(caller_field, str):
            errors.append("INVALID_ARTIFACT_ID")
            return _invalid_result(tuple(errors))
        _scan_forbidden_string(caller_field, errors, [0])
        if errors:
            return _invalid_result(tuple(dict.fromkeys(errors)))

    if manual_review_notice is not None:
        if not isinstance(manual_review_notice, str):
            errors.append("INVALID_HANDOFF_INPUT")
            return _invalid_result(tuple(errors))
        _scan_forbidden_string(manual_review_notice, errors, [0])
        if errors:
            return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- handoff_result type check (duck-typed to handle importlib path variants) ---
    expected_class_name = "HermesCandidateReviewOperatorHandoffResult"
    actual_class_name = type(handoff_result).__name__
    required_attrs = ("is_valid", "handoff", "errors", "warnings", "safety_flags", "decision_label")
    if actual_class_name != expected_class_name or not all(
        hasattr(handoff_result, attr) for attr in required_attrs
    ):
        errors.append("UNSUPPORTED_INPUT_SHAPE")
        return _invalid_result(tuple(errors))

    # --- handoff_result validity ---
    if handoff_result.is_valid is not True:
        errors.append("SOURCE_HANDOFF_NOT_VALID")
        return _invalid_result(tuple(errors))

    handoff: dict[str, Any] = handoff_result.handoff
    if not handoff:
        errors.append("SOURCE_HANDOFF_NOT_VALID")
        return _invalid_result(tuple(errors))

    # --- WP106 required groups present ---
    for group in _WP106_REQUIRED_GROUPS:
        if group not in handoff:
            errors.append("MISSING_REQUIRED_GROUP")
            return _invalid_result(tuple(errors))

    # --- WP106 safety flags present and True ---
    handoff_flags = handoff.get("safety_flags", {})
    for flag in REQUIRED_HANDOFF_SAFETY_FLAGS:
        if handoff_flags.get(flag) is not True:
            errors.append("MISSING_REQUIRED_SAFETY_FLAG")
            return _invalid_result(tuple(errors))

    # --- Decision label ---
    human_decision = handoff.get("human_decision_record", {})
    decision_label = human_decision.get("decision_label")
    if decision_label not in ALLOWED_HANDOFF_DECISION_LABELS:
        errors.append("INVALID_DECISION_LABEL")
        return _invalid_result(tuple(errors))

    # --- Raw metadata scan on handoff data ---
    _scan_raw_metadata(handoff, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Forbidden content scan on handoff data ---
    _scan_forbidden(handoff, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Build artifact ---
    handoff_identity = handoff.get("handoff_identity", {})

    artifact_identity: dict[str, Any] = {
        "artifact_id": artifact_id,
        "contract_version": contract_version,
        "generated_by": generated_by,
        "source_wp": "WP108",
        "source_contract": "WP107",
        "deterministic_owner": "deterministic_core",
        "artifact_type": "candidate_review_manual_export_artifact",
        "in_memory_only": True,
    }

    source_handoff_identity: dict[str, Any] = {
        "handoff_id": _safe_str(handoff_identity.get("handoff_id")),
        "chain_identifier": _safe_str(handoff_identity.get("chain_identifier")),
        "contract_version": _safe_str(handoff_identity.get("contract_version")),
        "generated_by": _safe_str(handoff_identity.get("generated_by")),
    }

    chain_stage_summary: dict[str, Any] = {
        "stages": list(_CHAIN_STAGES),
        "stage_count": len(_CHAIN_STAGES),
    }

    manual_review_summary: dict[str, Any] = {
        "decision_label": str(decision_label),
        "handoff_is_valid": True,
    }

    evidence = handoff.get("evidence_and_provenance", {})
    evidence_and_provenance_summary: dict[str, Any] = {
        "provenance_status": _safe_str(evidence.get("provenance_status")),
        "source_reference_count": _safe_list_count(evidence.get("source_references")),
        "artifact_references_count": _safe_list_count(evidence.get("artifact_references")),
        "evidence_summary_present": bool(evidence.get("evidence_summary")),
    }

    staleness = handoff.get("staleness_and_missing_data", {})
    staleness_and_missing_data_summary: dict[str, Any] = {
        "staleness_status": _safe_str(staleness.get("staleness_status")),
        "known_missing_data_count": _safe_list_count(staleness.get("known_missing_data")),
        "data_quality_warning_count": _safe_list_count(staleness.get("data_quality_warnings")),
        "coverage_limit_count": _safe_list_count(staleness.get("coverage_limits")),
    }

    uncertainty = handoff.get("uncertainty_and_limitations", {})
    uncertainty_and_limitations_summary: dict[str, Any] = {
        "uncertainty_notes_count": _safe_list_count(uncertainty.get("uncertainty_notes")),
        "assumptions_count": _safe_list_count(uncertainty.get("assumptions")),
        "limitations_count": _safe_list_count(uncertainty.get("limitations")),
        "boundary_notes_count": _safe_list_count(uncertainty.get("boundary_notes")),
    }

    falsification = handoff.get("falsification_checks", {})
    falsification_summary: dict[str, Any] = {
        "checks_count": _safe_list_count(falsification.get("checks")),
    }

    timestamp_note = _safe_str(human_decision.get("timestamp_note"))
    rationale = human_decision.get("rationale", "")
    rationale_length = len(str(rationale)) if rationale else 0
    human_decision_record_summary: dict[str, Any] = {
        "decision_label": str(decision_label),
        "operator_role": operator_role,
        "timestamp_note": timestamp_note,
        "rationale_length_chars": rationale_length,
    }

    next_step = handoff.get("next_research_step", {})
    next_manual_research_step: dict[str, Any] = {
        "step_type": _safe_str(next_step.get("step_type")),
        "has_step_description": bool(next_step.get("step_description")),
    }

    artifact_safety_flags: dict[str, bool] = {
        flag: True for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS
    }

    artifact: dict[str, Any] = {
        "artifact_identity": artifact_identity,
        "source_handoff_identity": source_handoff_identity,
        "chain_stage_summary": chain_stage_summary,
        "manual_review_summary": manual_review_summary,
        "evidence_and_provenance_summary": evidence_and_provenance_summary,
        "staleness_and_missing_data_summary": staleness_and_missing_data_summary,
        "uncertainty_and_limitations_summary": uncertainty_and_limitations_summary,
        "falsification_summary": falsification_summary,
        "human_decision_record_summary": human_decision_record_summary,
        "next_manual_research_step": next_manual_research_step,
        "safety_flags": artifact_safety_flags,
        "forbidden_scope_notice": _FORBIDDEN_SCOPE_NOTICE,
    }

    return CandidateReviewManualExportArtifactResult(
        is_valid=True,
        artifact=artifact,
        errors=(),
        warnings=(),
    )
