"""Local/offline/read-only validator for Hermes advisory output objects.

Validates in-memory Python mappings that represent a manually prepared
Hermes advisory output against WP97/WP98 advisory-output requirements.

This module is advisory validation only.

It does not:
- run Hermes or call any model or provider;
- execute prompts or create a prompt runner;
- export, report, or write any files;
- fetch data from any network or API source;
- access credentials, authenticated clients, or private endpoints;
- read account data, wallet data, or order lifecycle state;
- create paper or live trading behavior;
- place orders, cancel orders, sign transactions, or submit orders;
- override risk, approve strategies, approve PRs, or claim merge readiness;
- activate a scheduler, bot loop, dashboard, or runtime daemon;
- read environment variables or subprocess state.

Stdlib-only. No network access. No credentials. No file writes.
No external schema system (no Pydantic, no JSON Schema, no YAML).

Added in WP99.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


# ---------------------------------------------------------------------------
# Advisory label and status constants
# ---------------------------------------------------------------------------

ADVISORY_LABEL = "ADVISORY_ONLY_HERMES_OUTPUT_VALIDATION"
VALID_STATUS = "VALID_HERMES_ADVISORY_OUTPUT"
INVALID_STATUS = "INVALID_HERMES_ADVISORY_OUTPUT"


# ---------------------------------------------------------------------------
# Required boolean safety fields — all must be present and exactly True
# ---------------------------------------------------------------------------

REQUIRED_BOOLEAN_SAFETY_FIELDS: tuple[str, ...] = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_risk_override",
    "no_credential_request",
    "no_order_or_cancel_or_sign_or_submit",
    "no_paper_live_decision",
    "no_strategy_promotion_approval",
    "no_pr_approval_or_merge_readiness_claim",
)

# ---------------------------------------------------------------------------
# Required text/list fields — must be present and non-empty
# ---------------------------------------------------------------------------

REQUIRED_TEXT_FIELDS: tuple[str, ...] = (
    "evidence_summary",
    "source_refs",
    "provenance_status",
    "staleness_status",
    "confidence_level",
    "uncertainty_notes",
    "assumptions",
    "falsification_path",
    "deterministic_validation_handoff",
    "rejected_interpretations",
    "forbidden_action_statement",
    "next_human_review_step",
)

# All required top-level fields (boolean + text/list)
REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    *REQUIRED_BOOLEAN_SAFETY_FIELDS,
    *REQUIRED_TEXT_FIELDS,
)

# ---------------------------------------------------------------------------
# Allowed confidence levels
# ---------------------------------------------------------------------------

ALLOWED_CONFIDENCE_LEVELS: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH"})


# ---------------------------------------------------------------------------
# Raw/free-form metadata keys — rejected at any nesting depth
# ---------------------------------------------------------------------------

_RAW_METADATA_KEYS: frozenset[str] = frozenset({
    "metadata",
    "source_metadata",
    "raw_metadata",
    "extra",
    "context",
    "notes",
    "custom_fields",
    "raw_response",
    "model_response",
    "prompt",
    "completion",
})


# ---------------------------------------------------------------------------
# Safety key exceptions — these exact key names are exempt from key scanning
# even though they contain substrings of forbidden terms
# ---------------------------------------------------------------------------

_SAFETY_KEY_EXCEPTION_KEYS: frozenset[str] = frozenset({
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_risk_override",
    "no_credential_request",
    "no_order_or_cancel_or_sign_or_submit",
    "no_paper_live_decision",
    "no_strategy_promotion_approval",
    "no_pr_approval_or_merge_readiness_claim",
    "forbidden_action_statement",
})


# ---------------------------------------------------------------------------
# Forbidden term substrings — matched against normalized (lowercase,
# underscores/hyphens → spaces) keys and string values.
#
# Terms are chosen to match instruction/authority language while avoiding
# false positives on standard denial/advisory text.
# ---------------------------------------------------------------------------

_FORBIDDEN_TERM_SUBSTRINGS: tuple[str, ...] = (
    # Direct trade instruction forms
    "buy yes",
    "buy no",
    "buy at",
    "buy now",
    "sell this",
    "sell at",
    "sell now",
    # Position control as instruction
    "hold position",
    "enter at",
    "exit at",
    # Sizing and allocation as instruction
    "position size",
    "position sizing",
    "allocate",
    # Price parameters as order instruction
    "limit price",
    "stop loss",
    "take profit",
    # Order lifecycle instruction
    "place order",
    "cancel order",
    "sign transaction",
    "submit order",
    # Risk and live authority
    "override risk",
    "live ready",
    "paper execution",
    # Strategy and config control
    "promote strategy",
    "update config",
    # Scheduler / bot control
    "start scheduler",
    "bot loop",
    # Credential and account authority
    "request api key",
    "private endpoint",
    "account balance",
    # PR and merge authority
    "approve pr",
    "merge ready",
    # Decision and runtime authority
    "final decision",
    "run hermes",
    "set provider",
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HermesAdvisoryOutputValidationResult:
    """Result of validating a Hermes advisory output mapping.

    This dataclass is advisory only. It does not authorize execution,
    allocation, risk modification, credential access, strategy advancement,
    scheduler instruction, PR endorsement, or merge authorization.
    Human review is required before any action.

    Added in WP99.
    """

    is_valid: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    normalized_output: Mapping[str, object]
    advisory_label: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").replace("-", " ")


def _is_nonempty(value: object) -> bool:
    """Return True if value is a non-empty string, list, or tuple."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return False


def _scan_forbidden_terms(
    value: object,
    path: str,
    errors: list[str],
    _counter: list[int] | None = None,
) -> None:
    """Recursively scan for forbidden output terms in keys and string values.

    Keys in _SAFETY_KEY_EXCEPTION_KEYS are exempt from key scanning.
    All string values are scanned without exception.
    Error messages use neutral deterministic codes — caller-provided keys,
    values, and paths are never echoed back into output.
    """
    if _counter is None:
        _counter = [0]
    if isinstance(value, dict):
        for k, v in value.items():
            current_path = f"{path}.{k}" if path else k
            if k not in _SAFETY_KEY_EXCEPTION_KEYS:
                norm_k = _normalize(str(k))
                for term in _FORBIDDEN_TERM_SUBSTRINGS:
                    if term in norm_k:
                        errors.append(
                            f"Advisory output boundary violation in key: "
                            f"unsafe_key_{_counter[0]:03d}"
                        )
                        _counter[0] += 1
                        break
            _scan_forbidden_terms(v, current_path, errors, _counter)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_forbidden_terms(item, f"{path}[{i}]", errors, _counter)
    elif isinstance(value, str):
        norm_v = _normalize(value)
        for term in _FORBIDDEN_TERM_SUBSTRINGS:
            if term in norm_v:
                errors.append(
                    f"Advisory output boundary violation in value: "
                    f"unsafe_value_{_counter[0]:03d}"
                )
                _counter[0] += 1
                break


def _scan_raw_metadata_keys(
    value: object,
    path: str,
    errors: list[str],
    _counter: list[int] | None = None,
) -> None:
    """Recursively reject raw/free-form metadata keys at any nesting depth."""
    if _counter is None:
        _counter = [0]
    if isinstance(value, dict):
        for k, v in value.items():
            current_path = f"{path}.{k}" if path else k
            if k in _RAW_METADATA_KEYS:
                errors.append(
                    f"Raw metadata-like key rejected at advisory output boundary: "
                    f"unsafe_raw_key_{_counter[0]:03d}"
                )
                _counter[0] += 1
            _scan_raw_metadata_keys(v, current_path, errors, _counter)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_raw_metadata_keys(item, f"{path}[{i}]", errors, _counter)


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------


def validate_hermes_advisory_output(
    output: Mapping[str, object],
) -> HermesAdvisoryOutputValidationResult:
    """Validate an in-memory Hermes advisory output mapping.

    Enforces WP97/WP98 advisory-output requirements:
    - all required boolean safety fields are present and exactly True;
    - all required text/list fields are present and non-empty;
    - confidence_level is LOW, MEDIUM, or HIGH;
    - no forbidden output categories appear in keys or values recursively;
    - no raw/free-form metadata keys appear at any nesting depth;
    - invalid outputs return empty normalized_output;
    - error messages do not echo unsafe raw input.

    This function is local/offline/read-only and pure. It does not fetch
    data, write files, access credentials, or produce trade-like output.

    Returns a HermesAdvisoryOutputValidationResult. is_valid is True only
    when all rules pass. The advisory_label is always
    ADVISORY_ONLY_HERMES_OUTPUT_VALIDATION.

    Added in WP99.
    """
    errors: list[str] = []
    warnings_out: list[str] = []

    # --- Rule 1: Required boolean safety fields must be present and True --
    for field in REQUIRED_BOOLEAN_SAFETY_FIELDS:
        if field not in output:
            errors.append(f"Required safety field missing: {field}")
        elif output[field] is not True:
            errors.append(f"Required safety field must be exactly True: {field}")

    # --- Rule 2: Required text/list fields must be present and non-empty --
    for field in REQUIRED_TEXT_FIELDS:
        if field not in output:
            errors.append(f"Required field missing: {field}")
        elif not _is_nonempty(output[field]):
            errors.append(f"Required field must be non-empty: {field}")

    # --- Rule 3: Confidence level must be in allowlist --------------------
    confidence = output.get("confidence_level")
    if isinstance(confidence, str) and confidence.strip():
        if confidence not in ALLOWED_CONFIDENCE_LEVELS:
            errors.append("confidence_level must be LOW, MEDIUM, or HIGH")

    # --- Rule 4: Raw/free-form metadata keys (recursive) -----------------
    _scan_raw_metadata_keys(output, "", errors)

    # --- Rule 5: Forbidden output terms in keys or string values ---------
    _scan_forbidden_terms(output, "", errors)

    is_valid = len(errors) == 0

    return HermesAdvisoryOutputValidationResult(
        is_valid=is_valid,
        status=VALID_STATUS if is_valid else INVALID_STATUS,
        errors=tuple(errors),
        warnings=tuple(warnings_out),
        normalized_output=dict(output) if is_valid else {},
        advisory_label=ADVISORY_LABEL,
    )
