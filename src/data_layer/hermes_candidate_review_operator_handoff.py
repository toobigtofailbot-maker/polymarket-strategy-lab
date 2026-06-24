"""In-memory operator handoff object for Hermes candidate-review research.

Implements the WP105 operator handoff contract. Accepts explicit
caller-supplied in-memory mappings, validates required conceptual groups,
safety flags, decision labels, source-review checklist, and evidence fields.
Rejects forbidden content, raw/free-form metadata, and unsafe inputs.
Returns a deterministic in-memory result. Fails closed with an empty handoff
and neutral diagnostics for invalid input. Never echoes unsafe caller-provided
input in errors, warnings, or rejection reasons.

Stdlib-only. No file I/O. No network. No subprocess. No CLI. No credentials.
No paper/live/execution/risk/scheduler/dashboard/bot-loop/runtime/Hermes
behavior. Local/offline/read-only. Added in WP106.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# Allowed decision labels
# ---------------------------------------------------------------------------

ALLOWED_HANDOFF_DECISION_LABELS: frozenset[str] = frozenset({
    "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW",
    "REJECT_FOR_INSUFFICIENT_EVIDENCE",
    "REJECT_FOR_STALE_OR_MISSING_DATA",
    "REJECT_FOR_RESOLUTION_AMBIGUITY",
    "REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT",
    "NEEDS_SOURCE_RECHECK",
    "NEEDS_DETERMINISTIC_VALIDATION",
    "DEFER_PENDING_MORE_CONTEXT",
})

_REJECTION_OR_DEFER_LABELS: frozenset[str] = frozenset({
    "REJECT_FOR_INSUFFICIENT_EVIDENCE",
    "REJECT_FOR_STALE_OR_MISSING_DATA",
    "REJECT_FOR_RESOLUTION_AMBIGUITY",
    "REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT",
    "NEEDS_SOURCE_RECHECK",
    "NEEDS_DETERMINISTIC_VALIDATION",
    "DEFER_PENDING_MORE_CONTEXT",
})

# ---------------------------------------------------------------------------
# Required top-level conceptual groups
# ---------------------------------------------------------------------------

REQUIRED_HANDOFF_GROUPS: tuple[str, ...] = (
    "handoff_identity",
    "source_chain_summary",
    "packet_stage_summary",
    "receipt_stage_summary",
    "operator_review_stage_summary",
    "source_review_checklist",
    "evidence_and_provenance",
    "staleness_and_missing_data",
    "uncertainty_and_limitations",
    "falsification_checks",
    "human_decision_record",
    "next_research_step",
    "safety_flags",
    "rejection_reasons",
)

# ---------------------------------------------------------------------------
# Required safety flags — all must be present and exactly True
# ---------------------------------------------------------------------------

REQUIRED_HANDOFF_SAFETY_FLAGS: tuple[str, ...] = (
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
)

# Keys exempt from key-content scanning (they are safety boundaries, not data)
_SAFETY_KEY_EXCEPTIONS: frozenset[str] = frozenset({
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
    "rejection_reasons",
    "source_review_checklist",
})

# ---------------------------------------------------------------------------
# Required source-review checklist keys — all must be boolean True for valid
# handoff unless the decision label is a rejection/defer label with neutral stop
# ---------------------------------------------------------------------------

_REQUIRED_CHECKLIST_KEYS: tuple[str, ...] = (
    "source_references_present",
    "source_references_manually_inspectable",
    "provenance_status_explicit",
    "staleness_status_explicit",
    "known_missing_data_explicit",
    "uncertainty_notes_explicit",
    "limitations_explicit",
    "falsification_checks_explicit",
    "next_research_step_explicit",
    "human_decision_record_explicit",
)

# ---------------------------------------------------------------------------
# Raw/free-form metadata keys — rejected at any nesting depth
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Forbidden content terms — matched against normalized keys and string values
# at any nesting depth
# ---------------------------------------------------------------------------

_FORBIDDEN_TERMS: tuple[str, ...] = (
    # Trading/execution
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
    # Scoring/readiness
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
    # PR/authority
    "approve pr",
    "approve pull request",
    "merge ready",
    "risk override",
    "strategy promotion",
    # Credentials/private state
    "credential",
    "private key",
    "api key",
    "secret",
    "passphrase",
    "wallet",
    "account endpoint",
    "private endpoint",
    # Runtime/model/prompt
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

# Key names that are forbidden in caller-supplied data-bearing mappings
_FORBIDDEN_KEY_TERMS: frozenset[str] = frozenset({
    "buy",
    "sell",
    "order",
    "trade",
    "execute",
    "execution",
    "position",
    "position_size",
    "entry",
    "exit",
    "stop_loss",
    "take_profit",
    "expected_return",
    "alpha",
    "fair_value",
    "confidence_to_trade",
    "trade_ready",
    "tradable",
    "tradability",
    "live_ready",
    "paper_ready",
    "approve_pr",
    "merge_ready",
    "risk_override",
    "strategy_promotion",
    "credential",
    "private_key",
    "api_key",
    "secret",
    "passphrase",
    "wallet",
    "provider",
})


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HermesCandidateReviewOperatorHandoffResult:
    """Result of building and validating a Hermes candidate-review operator handoff.

    Advisory only. Does not authorize execution, credential access, paper/live
    trading, strategy promotion, PR approval, runtime behavior, scheduler or
    bot-loop behavior, file/network behavior, or prompt execution.
    Human review is required before any action.

    Added in WP106.
    """

    is_valid: bool
    handoff: dict[str, Any]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    safety_flags: dict[str, bool]
    decision_label: str | None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").replace("-", " ")


def _scan_forbidden(
    value: object,
    errors: list[str],
    checked: list[int] | None = None,
    is_key_scan: bool = False,
) -> None:
    """Recursively scan keys and string values for forbidden content.

    Error codes are neutral and never echo caller-provided content.
    """
    if checked is None:
        checked = [0]
    if isinstance(value, dict):
        for k, v in value.items():
            k_str = str(k)
            if k_str not in _SAFETY_KEY_EXCEPTIONS:
                norm_k = _normalize(k_str)
                for term in _FORBIDDEN_TERMS:
                    if term in norm_k:
                        errors.append("FORBIDDEN_CONTENT")
                        checked[0] += 1
                        if checked[0] >= 20:
                            return
                        break
            _scan_forbidden(v, errors, checked)
            if checked[0] >= 20:
                return
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_forbidden(item, errors, checked)
            if checked[0] >= 20:
                return
    elif isinstance(value, str):
        norm_v = _normalize(value)
        for term in _FORBIDDEN_TERMS:
            if term in norm_v:
                errors.append("FORBIDDEN_CONTENT")
                checked[0] += 1
                if checked[0] >= 20:
                    return
                break


def _scan_raw_metadata(value: object, errors: list[str], depth: int = 0) -> None:
    """Recursively scan for raw/free-form metadata keys."""
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


def _invalid_result(errors: tuple[str, ...]) -> HermesCandidateReviewOperatorHandoffResult:
    return HermesCandidateReviewOperatorHandoffResult(
        is_valid=False,
        handoff={},
        errors=errors,
        warnings=(),
        safety_flags={},
        decision_label=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_candidate_review_operator_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewOperatorHandoffResult:
    """Validate a caller-supplied in-memory candidate-review operator handoff.

    Validates required conceptual groups, safety flags, decision label,
    source-review checklist, and data-bearing fields. Rejects forbidden content,
    raw/free-form metadata, and unsafe inputs. Fails closed with an empty handoff
    and neutral error codes for invalid input. Never echoes unsafe caller content.

    This function is advisory validation only. It does not run Hermes, execute
    prompts, call models or providers, access networks, read or write files,
    use credentials or private state, create a CLI, or perform paper/live,
    order, risk, scheduler, dashboard, or bot-loop work. Added in WP106.
    """
    errors: list[str] = []

    # --- Raw metadata scan ---
    _scan_raw_metadata(handoff_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Forbidden content scan (full recursive) ---
    _scan_forbidden(handoff_data, errors)
    if errors:
        return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Required groups check ---
    for group in REQUIRED_HANDOFF_GROUPS:
        if group not in handoff_data:
            errors.append("MISSING_REQUIRED_GROUP")
            return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Safety flags ---
    safety_flags_raw = handoff_data.get("safety_flags")
    if not isinstance(safety_flags_raw, Mapping):
        errors.append("INVALID_SAFETY_FLAG")
        return _invalid_result(tuple(errors))

    for flag in REQUIRED_HANDOFF_SAFETY_FLAGS:
        if safety_flags_raw.get(flag) is not True:
            errors.append("INVALID_SAFETY_FLAG")
            return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Decision label ---
    human_decision = handoff_data.get("human_decision_record")
    if not isinstance(human_decision, Mapping):
        errors.append("INVALID_DECISION_LABEL")
        return _invalid_result(tuple(errors))

    decision_label = human_decision.get("decision_label")
    if decision_label not in ALLOWED_HANDOFF_DECISION_LABELS:
        errors.append("INVALID_DECISION_LABEL")
        return _invalid_result(tuple(errors))

    # --- Source-review checklist ---
    checklist = handoff_data.get("source_review_checklist")
    if not isinstance(checklist, Mapping):
        errors.append("INVALID_SOURCE_REVIEW_CHECKLIST")
        return _invalid_result(tuple(errors))

    for key in _REQUIRED_CHECKLIST_KEYS:
        if key not in checklist:
            errors.append("INVALID_SOURCE_REVIEW_CHECKLIST")
            return _invalid_result(tuple(dict.fromkeys(errors)))

    # For ACCEPT decision, all checklist keys must be True.
    # For rejection/defer labels, false checklist values are allowed
    # if the label provides a neutral stop reason.
    if decision_label not in _REJECTION_OR_DEFER_LABELS:
        for key in _REQUIRED_CHECKLIST_KEYS:
            if checklist.get(key) is not True:
                errors.append("INVALID_SOURCE_REVIEW_CHECKLIST")
                return _invalid_result(tuple(dict.fromkeys(errors)))

    # --- Build sanitized handoff ---
    sanitized_flags = {flag: True for flag in REQUIRED_HANDOFF_SAFETY_FLAGS}
    sanitized: dict[str, Any] = {}
    for group in REQUIRED_HANDOFF_GROUPS:
        group_value = handoff_data[group]
        if group == "safety_flags":
            sanitized[group] = sanitized_flags
        else:
            sanitized[group] = group_value

    return HermesCandidateReviewOperatorHandoffResult(
        is_valid=True,
        handoff=sanitized,
        errors=(),
        warnings=(),
        safety_flags=sanitized_flags,
        decision_label=str(decision_label),
    )


def build_candidate_review_operator_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewOperatorHandoffResult:
    """Build and validate a candidate-review operator handoff from caller data.

    Alias for validate_candidate_review_operator_handoff. Provides a consistent
    build_* naming convention matching other WP99-WP104 modules.

    Advisory only. No file I/O, network, CLI, credentials, paper/live,
    execution/risk, scheduler, dashboard, bot-loop, runtime, Hermes, or prompt
    execution. Added in WP106.
    """
    return validate_candidate_review_operator_handoff(handoff_data)


def assert_candidate_review_operator_handoff(
    handoff_data: Mapping[str, Any],
) -> HermesCandidateReviewOperatorHandoffResult:
    """Assert that handoff_data produces a valid handoff; raise on failure.

    Raises ValueError with a neutral error code message if the handoff is
    invalid. Never echoes unsafe caller input in the exception message.

    Advisory only. No file I/O, network, CLI, credentials, paper/live,
    execution/risk, scheduler, dashboard, bot-loop, runtime, Hermes, or prompt
    execution. Added in WP106.
    """
    result = validate_candidate_review_operator_handoff(handoff_data)
    if not result.is_valid:
        raise ValueError(
            "INVALID_CANDIDATE_REVIEW_OPERATOR_HANDOFF: "
            + ", ".join(result.errors or ("UNKNOWN_VALIDATION_ERROR",))
        )
    return result
