"""Local/offline/read-only validator for wallet-signal paper strategy contract records.

Validates in-memory candidate records against the WP83 paper-strategy contract.

This module is advisory validation only.

It does not:
- create paper strategy records or paper strategy implementations;
- fetch wallet data from any network or API source;
- monitor real wallets;
- copy wallets;
- compute dollar PnL, expected return, or position size;
- produce buy/sell/trade/execute/position-sizing/live-signal instructions;
- place orders, cancel orders, size positions, or override risk;
- write files;
- access credentials or authentication clients;
- invoke an LLM, AI agent, scheduler, dashboard, or bot loop;
- run paper or live trading.

Stdlib-only. No network access. No credentials. No file writes.

Added in WP84.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# ---------------------------------------------------------------------------
# Advisory label and status constants
# ---------------------------------------------------------------------------

VALIDATOR_ADVISORY_LABEL = (
    "ADVISORY_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_VALIDATION"
)

VALID_STATUS = "VALID_CONTRACT_RECORD"
INVALID_STATUS = "INVALID_CONTRACT_RECORD"

# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "contract_identity",
    "source_report_reference",
    "source_signal_context",
    "copyability_delay_context",
    "eligibility_review",
    "suspicious_flow_review",
    "insufficient_context_review",
    "human_review",
    "deferred_items",
    "safety",
    "warnings",
    "advisory_notice",
)

# ---------------------------------------------------------------------------
# Eligibility statuses
# ---------------------------------------------------------------------------

ALLOWED_ELIGIBILITY_STATUSES: frozenset[str] = frozenset({
    "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT",
    "NOT_ELIGIBLE_SUSPICIOUS_FLOW",
    "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE",
    "HUMAN_REVIEW_REQUIRED",
    "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN",
})

FORBIDDEN_ELIGIBILITY_STATUSES: frozenset[str] = frozenset({
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "EXECUTION_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "AUTO_APPROVED",
})

# ---------------------------------------------------------------------------
# Required safety flags — all must be present and true
# ---------------------------------------------------------------------------

REQUIRED_SAFETY_FLAGS: tuple[str, ...] = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
    "no_paper_engine_created",
    "no_account_action",
)

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
})

# ---------------------------------------------------------------------------
# Safety-flag key exceptions — these exact key names are permitted even
# though they contain substrings of forbidden terms
# ---------------------------------------------------------------------------

_SAFETY_FLAG_EXCEPTION_KEYS: frozenset[str] = frozenset({
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
})

# ---------------------------------------------------------------------------
# Forbidden term substrings — matched against normalized (lowercase,
# underscores/hyphens → spaces) keys and string values
# ---------------------------------------------------------------------------

_FORBIDDEN_TERM_SUBSTRINGS: tuple[str, ...] = (
    "buy",
    "sell",
    "trade",
    "trading",
    "execute",
    "execution",
    "order ready",
    "execution ready",
    "entry",
    "exit",
    "position size",
    "position sizing",
    "expected return",
    "profit target",
    "stop loss",
    "take profit",
    "live signal",
    "auto copy",
    "automatic copy",
    "copy signal",
    "wallet copy instruction",
    "pnl target",
    "paper trading candidate",
    "strategy signal",
)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractValidationResult:
    """Result of validating a wallet-signal paper strategy contract record.

    This dataclass is advisory only. It does not authorize implementation,
    allocation, order placement, live account action, or any account activity.
    Human review is required before any use of these validation results.

    Added in WP84.
    """

    is_valid: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    normalized_record: Mapping[str, object]
    advisory_label: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").replace("-", " ")


def _scan_forbidden_terms(
    value: object,
    path: str,
    errors: list[str],
) -> None:
    """Recursively scan for forbidden output terms in keys and string values.

    Keys in _SAFETY_FLAG_EXCEPTION_KEYS are exempt from key scanning.
    All string values are scanned without exception.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            current_path = f"{path}.{k}" if path else k
            if k not in _SAFETY_FLAG_EXCEPTION_KEYS:
                norm_k = _normalize(str(k))
                for term in _FORBIDDEN_TERM_SUBSTRINGS:
                    if term in norm_k:
                        errors.append(
                            f"Forbidden term '{term}' found in key at path '{current_path}'"
                        )
                        break
            _scan_forbidden_terms(v, current_path, errors)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_forbidden_terms(item, f"{path}[{i}]", errors)
    elif isinstance(value, str):
        norm_v = _normalize(value)
        for term in _FORBIDDEN_TERM_SUBSTRINGS:
            if term in norm_v:
                errors.append(
                    f"Forbidden term '{term}' found in value at path '{path}'"
                )
                break


def _scan_raw_metadata_keys(
    value: object,
    path: str,
    errors: list[str],
) -> None:
    """Recursively reject raw/free-form metadata keys at any nesting depth."""
    if isinstance(value, dict):
        for k, v in value.items():
            current_path = f"{path}.{k}" if path else k
            if k in _RAW_METADATA_KEYS:
                errors.append(
                    f"Raw metadata-like key '{k}' found at path '{current_path}' — "
                    f"raw metadata pass-through is not permitted in contract records"
                )
            _scan_raw_metadata_keys(v, current_path, errors)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_raw_metadata_keys(item, f"{path}[{i}]", errors)


def _check_safety_flags(
    safety: object,
) -> list[str]:
    """Return error strings for missing or non-true safety flags."""
    flag_errors: list[str] = []
    if not isinstance(safety, dict):
        flag_errors.append("safety section must be a mapping")
        return flag_errors
    for flag in REQUIRED_SAFETY_FLAGS:
        if flag not in safety:
            flag_errors.append(f"Required safety flag missing: {flag}")
        elif safety[flag] is not True:
            flag_errors.append(
                f"Required safety flag must be true: {flag}"
            )
    return flag_errors


def _suspicious_flow_detected(suspicious_section: object) -> bool:
    if not isinstance(suspicious_section, dict):
        return False
    if suspicious_section.get("suspicious_flow_detected") is True:
        return True
    records = suspicious_section.get("suspicious_flow_records", [])
    if isinstance(records, (list, tuple)) and len(records) > 0:
        return True
    return False


def _has_insufficient_context_warnings(ic_section: object) -> bool:
    if not isinstance(ic_section, dict):
        return False
    warnings = ic_section.get("insufficient_context_warnings", [])
    return isinstance(warnings, (list, tuple)) and len(warnings) > 0


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------


def validate_wallet_signal_paper_strategy_contract_record(
    record: Mapping[str, object],
) -> ContractValidationResult:
    """Validate an in-memory wallet-signal paper strategy contract record.

    Checks the record against the WP83 paper-strategy contract rules:
    - all required sections are present;
    - no raw/free-form metadata keys appear at any nesting depth;
    - no forbidden output terms appear in keys or string values;
    - all required safety flags are present and true;
    - the eligibility status is from the allowed set and not from the
      forbidden set;
    - the stated eligibility status matches the status required by the
      blocking-gate precedence rules;
    - human_review_required is true.

    This function is local/offline/read-only and pure. It does not fetch
    data, write files, access credentials, or produce trade-like output.

    Returns a ContractValidationResult. is_valid is True only when all
    rules pass. The advisory_label is always
    ADVISORY_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_VALIDATION.

    Added in WP84.
    """
    errors: list[str] = []
    warnings_out: list[str] = []

    # --- Rule 1: Missing required top-level sections ----------------------
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section not in record:
            errors.append(f"Required section missing: {section}")

    # --- Rule 11: Missing source_report_reference (precedence gate 1) ----
    source_ref = record.get("source_report_reference")
    source_ref_missing = not source_ref

    # --- Rules 4 & 5: Safety flags (precedence gate 2) -------------------
    safety_flag_errors = _check_safety_flags(record.get("safety", {}))

    # --- Rule 13: Suspicious flow (precedence gate 3) --------------------
    flow_detected = _suspicious_flow_detected(
        record.get("suspicious_flow_review", {})
    )

    # --- Rule 12: Missing copyability_delay_context (precedence gate 4) --
    copyability_missing = not record.get("copyability_delay_context")

    # --- Rule 15: Insufficient context warnings (precedence gate 5) ------
    has_ic_warnings = _has_insufficient_context_warnings(
        record.get("insufficient_context_review", {})
    )

    # --- Derive expected eligibility status from precedence rules ---------
    if source_ref_missing:
        expected_status = "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    elif safety_flag_errors:
        expected_status = "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
    elif flow_detected:
        expected_status = "NOT_ELIGIBLE_SUSPICIOUS_FLOW"
    elif copyability_missing:
        expected_status = "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    elif has_ic_warnings:
        expected_status = "HUMAN_REVIEW_REQUIRED"
    else:
        expected_status = "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN"

    # Collect safety flag errors
    errors.extend(safety_flag_errors)

    # --- Rules 2 & 3: Unknown or forbidden eligibility statuses ----------
    eligibility_review = record.get("eligibility_review", {})
    stated_status: object = None
    if isinstance(eligibility_review, dict):
        stated_status = eligibility_review.get("eligibility_status")

    if stated_status is not None:
        if stated_status in FORBIDDEN_ELIGIBILITY_STATUSES:
            errors.append(
                f"Forbidden eligibility status present: {stated_status}"
            )
        elif stated_status not in ALLOWED_ELIGIBILITY_STATUSES:
            errors.append(
                f"Unknown eligibility status: {stated_status}"
            )
        elif stated_status != expected_status:
            errors.append(
                f"Eligibility status mismatch: record states '{stated_status}' "
                f"but blocking-gate precedence requires '{expected_status}'"
            )
    elif isinstance(eligibility_review, dict):
        errors.append(
            "eligibility_review section must contain eligibility_status"
        )

    # --- Rule 14: suspicious flow status must map to correct value --------
    # (covered by precedence check above — if flow detected and stated status
    # is not NOT_ELIGIBLE_SUSPICIOUS_FLOW, the mismatch error fires)

    # --- human_review_required must be true in all cases ------------------
    human_review = record.get("human_review", {})
    if isinstance(human_review, dict):
        if human_review.get("human_review_required") is not True:
            errors.append(
                "human_review.human_review_required must be true"
            )
    elif "human_review" in record:
        errors.append("human_review section must be a mapping")

    # --- Rule 6: Raw/free-form metadata keys (recursive) -----------------
    _scan_raw_metadata_keys(record, "", errors)

    # --- Rule 8: Forbidden output terms in keys or string values ---------
    # (Rules 9 & 10 are covered here — deferred item keys and advisory
    # notices are included in the recursive scan)
    _scan_forbidden_terms(record, "", errors)

    # --- Rule 7: Non-placeholder identifiers in design examples ----------
    contract_identity = record.get("contract_identity", {})
    is_design_example = (
        isinstance(contract_identity, dict)
        and contract_identity.get("design_example_only") is True
    )
    if is_design_example:
        source_signal = record.get("source_signal_context", {})
        if isinstance(source_signal, dict):
            for id_field in (
                "wallet_id_placeholder",
                "market_id_placeholder",
                "condition_id_placeholder",
            ):
                val = source_signal.get(id_field, "")
                if isinstance(val, str) and val and "0x" in val.lower():
                    warnings_out.append(
                        f"Design example field '{id_field}' may contain a real "
                        f"identifier — placeholder values are required in design examples"
                    )

    is_valid = len(errors) == 0

    return ContractValidationResult(
        is_valid=is_valid,
        status=VALID_STATUS if is_valid else INVALID_STATUS,
        errors=tuple(errors),
        warnings=tuple(warnings_out),
        normalized_record=dict(record),
        advisory_label=VALIDATOR_ADVISORY_LABEL,
    )
