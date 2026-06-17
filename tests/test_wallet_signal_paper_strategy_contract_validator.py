"""Focused tests for WP84 wallet-signal paper strategy contract validator.

Requirement-to-test mapping (WP84 Section 12):
  valid example passes               -> test_valid_contract_record_passes
  missing sections fail              -> test_missing_required_sections_fail
  safety flags all true              -> test_safety_flags_required_true
  forbidden statuses fail            -> test_forbidden_statuses_fail
  recursive key/value scan           -> test_forbidden_terms_rejected_recursively
  raw metadata rejected              -> test_raw_metadata_like_mappings_rejected
  source reference required          -> test_source_report_reference_required
  copyability context required       -> test_copyability_delay_context_required
  suspicious precedence              -> test_suspicious_flow_precedence
  safety precedence                  -> test_safety_flag_failure_precedence
  insufficient context precedence    -> test_insufficient_context_precedence
  neutral error wording              -> test_errors_and_warnings_use_neutral_wording
  frozen dataclass                   -> test_validator_result_is_frozen
  no network/file writes             -> test_validator_has_no_network_or_file_io
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest

from src.data_layer.wallet_signal_paper_strategy_contract_validator import (
    ALLOWED_ELIGIBILITY_STATUSES,
    FORBIDDEN_ELIGIBILITY_STATUSES,
    REQUIRED_SAFETY_FLAGS,
    REQUIRED_TOP_LEVEL_SECTIONS,
    VALID_STATUS,
    INVALID_STATUS,
    VALIDATOR_ADVISORY_LABEL,
    ContractValidationResult,
    validate_wallet_signal_paper_strategy_contract_record,
)

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SRC = (
    ROOT
    / "src"
    / "data_layer"
    / "wallet_signal_paper_strategy_contract_validator.py"
)


# ---------------------------------------------------------------------------
# Minimal valid record builder
# ---------------------------------------------------------------------------


def _build_valid_record() -> dict[str, Any]:
    """Build a minimal valid contract record for testing.

    All gates pass: source reference present, all safety flags true,
    no suspicious flow, copyability context present, no insufficient
    context warnings. Eligibility status is
    RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN.
    """
    return {
        "contract_identity": {
            "contract_id": "EXAMPLE-WP84-TEST-001",
            "contract_type": "WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_V1",
            "contract_created_at": "PLACEHOLDER_TIMESTAMP",
            "wp_version": "WP84",
            "advisory_only_notice": (
                "Advisory research record only. Not a strategy instruction."
            ),
            "design_example_only": True,
        },
        "source_report_reference": {
            "wallet_intelligence_report_id": "PLACEHOLDER_REPORT_001",
            "wallet_signal_profile_ids": ["PLACEHOLDER_PROFILE_001"],
            "copyability_delay_evaluation_ids": ["PLACEHOLDER_DELAY_EVAL_001"],
            "research_queue_annotation_ids": ["PLACEHOLDER_ANNOTATION_001"],
            "human_review_label_ids": ["PLACEHOLDER_LABEL_001"],
            "local_fixture_set_id": "PLACEHOLDER_FIXTURE_SET_001",
            "source_reference_advisory": (
                "Local placeholder IDs only. No real wallet addresses used."
            ),
        },
        "source_signal_context": {
            "wallet_id_placeholder": "wallet_placeholder_001",
            "market_id_placeholder": "market_placeholder_001",
            "condition_id_placeholder": "condition_placeholder_001",
            "signal_category_label": "WATCH_ONLY_ADVISORY_LABEL",
            "profitability_advisory_label": "ADVISORY_RESEARCH_LABEL_ONLY",
            "specialization_advisory_label": "ADVISORY_RESEARCH_LABEL_ONLY",
            "copyability_advisory_label": "RESEARCH_PROMISING_ADVISORY_ONLY",
            "advisory_only_notice": (
                "Signal context is advisory only. Not a recommendation."
            ),
        },
        "copyability_delay_context": {
            "copyability_delay_evaluation_id": "PLACEHOLDER_DELAY_EVAL_001",
            "delay_window_label": "PLACEHOLDER_DELAY_WINDOW",
            "copyability_advisory_status": "RESEARCH_PROMISING",
            "advisory_only_notice": (
                "RESEARCH_PROMISING is advisory only. Not an approval."
            ),
        },
        "eligibility_review": {
            "eligibility_status": "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN",
            "eligibility_gate_results": {
                "source_report_reference_present": True,
                "safety_flags_all_pass": True,
                "no_suspicious_flow_block": True,
                "copyability_context_present": True,
                "no_insufficient_context_warnings": True,
            },
            "advisory_only_notice": (
                "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN is advisory only."
            ),
        },
        "suspicious_flow_review": {
            "suspicious_flow_detected": False,
            "suspicious_flow_records": [],
            "advisory_only_notice": "No suspicious flow detected in this record.",
        },
        "insufficient_context_review": {
            "insufficient_context_warnings": [],
            "context_completeness_label": "SUFFICIENT_FOR_ADVISORY_REVIEW",
            "advisory_only_notice": "Context completeness is advisory only.",
        },
        "human_review": {
            "human_review_required": True,
            "human_review_label_ids": ["PLACEHOLDER_LABEL_001"],
            "human_review_advisory_note": (
                "Human review required before any future paper design review."
            ),
            "advisory_only_notice": "Human review required at all eligibility levels.",
        },
        "deferred_items": {
            "paper_strategy_implementation": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "paper_order_model": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "paper_portfolio_ledger": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "paper_fill_model": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "paper_pnl_computation": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "network_wallet_ingestion": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "real_wallet_monitoring": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "passive_following_scope": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "live_access_capability": (
                "Forbidden. Not authorized by this advisory contract."
            ),
            "credential_access": (
                "Forbidden. Not authorized by this advisory contract."
            ),
            "scheduler_or_loop": (
                "Deferred. Not authorized by this advisory contract."
            ),
            "dashboard_capability": (
                "Deferred. Not authorized by this advisory contract."
            ),
        },
        "safety": {
            "manual_research_only": True,
            "not_automated_copy_trading": True,
            "no_live_execution": True,
            "no_order_placement": True,
            "no_position_sizing": True,
            "no_risk_override": True,
            "no_parameter_auto_change": True,
            "no_paper_engine_created": True,
            "no_account_action": True,
        },
        "warnings": {
            "not_a_strategy_instruction": (
                "This record is not a strategy instruction."
            ),
            "not_an_allocation_record": (
                "This record is not an allocation record."
            ),
            "not_an_order_record": "This record is not an order record.",
            "research_queue_advisory_only": (
                "This record is advisory research queue only."
            ),
        },
        "advisory_notice": (
            "WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_V1 records are advisory "
            "research queue records only."
        ),
    }


# ---------------------------------------------------------------------------
# test_valid_contract_record_passes (Req: valid example passes)
# ---------------------------------------------------------------------------


def test_valid_contract_record_passes() -> None:
    record = _build_valid_record()
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is True, f"Expected valid, got errors: {result.errors}"
    assert result.status == VALID_STATUS
    assert result.errors == ()
    assert result.advisory_label == VALIDATOR_ADVISORY_LABEL


def test_valid_record_advisory_label_is_correct() -> None:
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    assert result.advisory_label == (
        "ADVISORY_ONLY_WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT_VALIDATION"
    )


def test_valid_record_normalized_record_present() -> None:
    record = _build_valid_record()
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert isinstance(result.normalized_record, dict)
    assert "contract_identity" in result.normalized_record


# ---------------------------------------------------------------------------
# test_missing_required_sections_fail (Req: missing sections fail)
# ---------------------------------------------------------------------------


def test_missing_required_sections_fail() -> None:
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        record = _build_valid_record()
        del record[section]
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid when section '{section}' is missing"
        )
        assert result.status == INVALID_STATUS
        assert any(section in e for e in result.errors), (
            f"Error for missing section '{section}' not found in {result.errors}"
        )


def test_empty_record_fails_all_required_sections() -> None:
    result = validate_wallet_signal_paper_strategy_contract_record({})
    assert result.is_valid is False
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        assert any(section in e for e in result.errors), (
            f"Error for missing section '{section}' not found"
        )


# ---------------------------------------------------------------------------
# test_safety_flags_required_true (Req: safety flags all true)
# ---------------------------------------------------------------------------


def test_safety_flags_required_true() -> None:
    for flag in REQUIRED_SAFETY_FLAGS:
        record = _build_valid_record()
        record["safety"][flag] = False
        # Since a safety flag fails, eligibility status must also change
        record["eligibility_review"]["eligibility_status"] = (
            "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
        )
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid when safety flag '{flag}' is False"
        )
        assert any(flag in e for e in result.errors), (
            f"Error for flag '{flag}' not found in {result.errors}"
        )


def test_missing_safety_flag_fails() -> None:
    for flag in REQUIRED_SAFETY_FLAGS:
        record = _build_valid_record()
        del record["safety"][flag]
        record["eligibility_review"]["eligibility_status"] = (
            "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
        )
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid when safety flag '{flag}' is missing"
        )
        assert any(flag in e for e in result.errors)


def test_safety_section_not_mapping_fails() -> None:
    record = _build_valid_record()
    record["safety"] = "all true"  # type: ignore[assignment]
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("safety" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# test_forbidden_statuses_fail (Req: forbidden statuses fail)
# ---------------------------------------------------------------------------


def test_forbidden_statuses_fail() -> None:
    for status in FORBIDDEN_ELIGIBILITY_STATUSES:
        record = _build_valid_record()
        record["eligibility_review"]["eligibility_status"] = status
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid for forbidden status '{status}'"
        )
        assert any("forbidden" in e.lower() or status in e for e in result.errors), (
            f"Error for forbidden status '{status}' not found in {result.errors}"
        )


def test_unknown_eligibility_status_fails() -> None:
    record = _build_valid_record()
    record["eligibility_review"]["eligibility_status"] = "UNKNOWN_STATUS_XYZ"
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("unknown" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# test_forbidden_terms_rejected_recursively (Req: recursive key/value scan)
# ---------------------------------------------------------------------------


# Reviewer-trap records from WP84 Section 7
_REVIEWER_TRAP_RECORDS: list[tuple[str, dict[str, Any]]] = [
    (
        "expected_return",
        {"expected_return": "12%"},
    ),
    (
        "position_size",
        {"position_size": "25 USDC"},
    ),
    (
        "buy_signal",
        {"buy_signal": "YES"},
    ),
    (
        "execution_ready",
        {"execution_ready": True},
    ),
    (
        "paper_trading_candidate",
        {"paper_trading_candidate": True},
    ),
    (
        "strategy_signal",
        {"strategy_signal": "wallet followed"},
    ),
    (
        "source_metadata_with_expected_return",
        {"source_metadata": {"expected_return": "buy recommendation"}},
    ),
    (
        "metadata_nested_position_size",
        {"metadata": {"safe_outer": {"position_size": "25"}}},
    ),
]


@pytest.mark.parametrize("label,injection", _REVIEWER_TRAP_RECORDS)
def test_reviewer_trap_record_fails(
    label: str,
    injection: dict[str, Any],
) -> None:
    """Reviewer-trap: records with forbidden terms must fail before a correct
    implementation would accept them."""
    record = _build_valid_record()
    record.update(injection)
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False, (
        f"Reviewer trap '{label}': expected invalid, got valid"
    )


def test_forbidden_terms_rejected_recursively() -> None:
    """Forbidden terms must be rejected at arbitrary nesting depth."""
    record = _build_valid_record()
    record["source_signal_context"] = {
        "nested_level_1": {
            "nested_level_2": {
                "nested_level_3": "expected return on this signal is 15%"
            }
        },
        "advisory_only_notice": "Advisory only.",
    }
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("boundary violation" in e for e in result.errors)


def test_forbidden_term_in_list_value_rejected() -> None:
    record = _build_valid_record()
    record["source_signal_context"]["signal_category_label"] = (
        "WATCH_ONLY_ADVISORY_LABEL"
    )
    record["human_review"]["human_review_label_ids"] = [
        "expected_return_signal_001"
    ]
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("boundary violation" in e for e in result.errors)


def test_forbidden_term_in_nested_dict_key_rejected() -> None:
    record = _build_valid_record()
    record["eligibility_review"]["eligibility_gate_results"] = {
        "expected_return_gate": True,
    }
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("boundary violation" in e for e in result.errors)


def test_forbidden_terms_buy_sell_in_values_rejected() -> None:
    for term_val in ("buy this signal", "sell this signal"):
        record = _build_valid_record()
        record["advisory_notice"] = term_val
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid for advisory_notice value '{term_val}'"
        )


def test_forbidden_terms_live_signal_in_values_rejected() -> None:
    record = _build_valid_record()
    record["advisory_notice"] = "live signal present"
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("boundary violation" in e for e in result.errors)


def test_forbidden_terms_pnl_target_in_key_rejected() -> None:
    record = _build_valid_record()
    record["pnl_target"] = "5%"
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("boundary violation" in e for e in result.errors)


def test_safety_flag_exception_keys_not_rejected() -> None:
    """Safety flag exception keys must not trigger forbidden term rejection."""
    record = _build_valid_record()
    # The safety section has not_automated_copy_trading, no_live_execution, etc.
    # These should NOT cause forbidden term errors.
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is True, (
        f"Safety flag exception keys caused unexpected errors: {result.errors}"
    )


# ---------------------------------------------------------------------------
# test_raw_metadata_like_mappings_rejected (Req: raw metadata rejected)
# ---------------------------------------------------------------------------


def test_raw_metadata_like_mappings_rejected() -> None:
    """Raw metadata-like keys must be rejected at any nesting depth."""
    raw_keys = [
        "metadata",
        "source_metadata",
        "raw_metadata",
        "extra",
        "context",
        "notes",
        "custom_fields",
    ]
    for key in raw_keys:
        record = _build_valid_record()
        record[key] = {"some_advisory_field": "advisory value"}
        result = validate_wallet_signal_paper_strategy_contract_record(record)
        assert result.is_valid is False, (
            f"Expected invalid for raw metadata key '{key}'"
        )
        assert any(key in e for e in result.errors), (
            f"Error for raw metadata key '{key}' not found in {result.errors}"
        )


def test_nested_raw_metadata_key_rejected() -> None:
    """Raw metadata keys nested inside valid sections must also be rejected."""
    record = _build_valid_record()
    record["source_signal_context"]["context"] = {"something": "advisory"}
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("context" in e for e in result.errors)


def test_deeply_nested_metadata_key_rejected() -> None:
    record = _build_valid_record()
    record["copyability_delay_context"] = {
        "copyability_delay_evaluation_id": "PLACEHOLDER_DELAY_EVAL_001",
        "delay_window_label": "PLACEHOLDER_DELAY_WINDOW",
        "copyability_advisory_status": "RESEARCH_PROMISING",
        "advisory_only_notice": "Advisory only.",
        "outer": {
            "inner": {
                "metadata": {"unsafe_field": "unsafe_value"},
            }
        },
    }
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("metadata" in e for e in result.errors)


# ---------------------------------------------------------------------------
# test_source_report_reference_required (Req: source reference required)
# ---------------------------------------------------------------------------


def test_source_report_reference_required() -> None:
    record = _build_valid_record()
    del record["source_report_reference"]
    # Status must now be NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("source_report_reference" in e for e in result.errors)


def test_empty_source_report_reference_triggers_precedence() -> None:
    record = _build_valid_record()
    record["source_report_reference"] = {}
    # Empty mapping → source ref missing → precedence requires NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
    # Record still states RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN → mismatch error
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False


def test_source_report_reference_present_allows_progress_to_next_gate() -> None:
    """With source ref present, the validator proceeds to evaluate other gates."""
    record = _build_valid_record()
    # source_report_reference is present → gate 1 passes
    # all safety flags true → gate 2 passes
    # no suspicious flow → gate 3 passes
    # copyability present → gate 4 passes
    # no ic warnings → gate 5 passes
    # expected: RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# test_copyability_delay_context_required (Req: copyability context required)
# ---------------------------------------------------------------------------


def test_copyability_delay_context_required() -> None:
    record = _build_valid_record()
    del record["copyability_delay_context"]
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("copyability_delay_context" in e for e in result.errors)


def test_empty_copyability_delay_context_triggers_precedence() -> None:
    """Empty copyability context triggers NOT_ELIGIBLE_INSUFFICIENT_CONTEXT
    precedence. If the stated status does not match, a mismatch error fires."""
    record = _build_valid_record()
    record["copyability_delay_context"] = {}
    # Status NOT updated — still RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN
    # but precedence requires NOT_ELIGIBLE_INSUFFICIENT_CONTEXT → mismatch
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("NOT_ELIGIBLE_INSUFFICIENT_CONTEXT" in e for e in result.errors)


# ---------------------------------------------------------------------------
# test_suspicious_flow_precedence (Req: suspicious precedence)
# Precedence trap: suspicious flow present + otherwise eligible →
# NOT_ELIGIBLE_SUSPICIOUS_FLOW
# ---------------------------------------------------------------------------


def test_suspicious_flow_precedence() -> None:
    record = _build_valid_record()
    record["suspicious_flow_review"]["suspicious_flow_detected"] = True
    # Record still states RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN → mismatch
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("NOT_ELIGIBLE_SUSPICIOUS_FLOW" in e for e in result.errors)


def test_suspicious_flow_with_correct_status_passes_flow_gate() -> None:
    record = _build_valid_record()
    record["suspicious_flow_review"]["suspicious_flow_detected"] = True
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_SUSPICIOUS_FLOW"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is True, (
        f"Expected valid when suspicious flow correctly mapped: {result.errors}"
    )


def test_suspicious_flow_records_list_triggers_precedence() -> None:
    record = _build_valid_record()
    record["suspicious_flow_review"]["suspicious_flow_records"] = [
        {"observation": "anomalous pattern detected"}
    ]
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False


# ---------------------------------------------------------------------------
# test_safety_flag_failure_precedence (Req: safety precedence)
# Precedence trap: safety flag false + otherwise eligible →
# NOT_ELIGIBLE_SAFETY_FLAG_FAILURE
# ---------------------------------------------------------------------------


def test_safety_flag_failure_precedence() -> None:
    record = _build_valid_record()
    record["safety"]["manual_research_only"] = False
    # Record still states RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN → mismatch
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    # The error must mention the safety flag failure
    assert any(
        "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE" in e or "manual_research_only" in e
        for e in result.errors
    )


def test_safety_flag_failure_with_correct_status_passes_safety_gate() -> None:
    record = _build_valid_record()
    record["safety"]["no_risk_override"] = False
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    # The flag error must still appear even if the status is correct
    assert any("no_risk_override" in e for e in result.errors)


def test_safety_flag_false_overrides_suspicious_flow_precedence() -> None:
    """Safety flag failure takes precedence over suspicious flow (gate 2 < gate 3)."""
    record = _build_valid_record()
    record["safety"]["no_account_action"] = False
    record["suspicious_flow_review"]["suspicious_flow_detected"] = True
    # Expected: NOT_ELIGIBLE_SAFETY_FLAG_FAILURE (gate 2 fires before gate 3)
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_SUSPICIOUS_FLOW"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    # The status mismatch error fires because gate 2 sets NOT_ELIGIBLE_SAFETY_FLAG_FAILURE
    assert any("NOT_ELIGIBLE_SAFETY_FLAG_FAILURE" in e for e in result.errors)


# ---------------------------------------------------------------------------
# test_insufficient_context_precedence (Req: insufficient context precedence)
# Precedence trap: insufficient context warning present + otherwise eligible →
# HUMAN_REVIEW_REQUIRED
# ---------------------------------------------------------------------------


def test_insufficient_context_precedence() -> None:
    record = _build_valid_record()
    record["insufficient_context_review"]["insufficient_context_warnings"] = [
        "Source fixture data is incomplete."
    ]
    # Record still states RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN → mismatch
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("HUMAN_REVIEW_REQUIRED" in e for e in result.errors)


def test_insufficient_context_with_correct_status_passes() -> None:
    record = _build_valid_record()
    record["insufficient_context_review"]["insufficient_context_warnings"] = [
        "Fixture data is partial."
    ]
    record["eligibility_review"]["eligibility_status"] = "HUMAN_REVIEW_REQUIRED"
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is True, (
        f"Expected valid with HUMAN_REVIEW_REQUIRED status: {result.errors}"
    )


def test_missing_source_ref_takes_precedence_over_safety_flag_failure() -> None:
    """Missing source report reference (gate 1) takes precedence over safety flag
    failure (gate 2)."""
    record = _build_valid_record()
    del record["source_report_reference"]
    record["safety"]["manual_research_only"] = False
    # Expected: NOT_ELIGIBLE_INSUFFICIENT_CONTEXT (gate 1 fires before gate 2)
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    # Still fails because of safety flag error, but the precedence status matches gate 1
    assert any("source_report_reference" in e for e in result.errors)


# ---------------------------------------------------------------------------
# test_errors_and_warnings_use_neutral_wording (Req: neutral error wording)
# ---------------------------------------------------------------------------

_TRADE_LIKE_TERMS = (
    "buy", "sell", "profit", "loss", "pnl", "order ready", "execution ready",
    "live signal", "expected return", "position size",
)


def test_errors_and_warnings_use_neutral_wording() -> None:
    """Error and warning strings from the validator must not contain
    trade-like or execution-like language."""
    record = _build_valid_record()
    # Force some errors by removing required sections
    del record["source_report_reference"]
    del record["safety"]
    record["eligibility_review"]["eligibility_status"] = "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE"
    result = validate_wallet_signal_paper_strategy_contract_record(record)

    all_output = list(result.errors) + list(result.warnings)
    for msg in all_output:
        for term in _TRADE_LIKE_TERMS:
            assert term not in msg.lower(), (
                f"Trade-like term '{term}' found in error/warning output: '{msg}'"
            )


def test_error_messages_are_strings() -> None:
    record = _build_valid_record()
    del record["source_report_reference"]
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    for e in result.errors:
        assert isinstance(e, str), f"Error must be a string, got {type(e)}"
    for w in result.warnings:
        assert isinstance(w, str), f"Warning must be a string, got {type(w)}"


# ---------------------------------------------------------------------------
# test_validator_result_is_frozen (Req: frozen dataclass)
# ---------------------------------------------------------------------------


def test_validator_result_is_frozen() -> None:
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    assert isinstance(result, ContractValidationResult)
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]


def test_validator_result_errors_is_tuple() -> None:
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    assert isinstance(result.errors, tuple)
    assert isinstance(result.warnings, tuple)


def test_validator_result_status_is_string() -> None:
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    assert isinstance(result.status, str)
    assert result.status in (VALID_STATUS, INVALID_STATUS)


def test_validator_result_advisory_label_never_forbidden() -> None:
    """The advisory_label must never be a forbidden output term."""
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    forbidden_labels = (
        "TRADE_READY", "COPY_READY", "LIVE_READY", "ORDER_READY",
        "EXECUTION_READY", "BUY_SIGNAL", "SELL_SIGNAL", "AUTO_APPROVED",
    )
    for label in forbidden_labels:
        assert label not in result.advisory_label, (
            f"Forbidden label term '{label}' found in advisory_label: "
            f"'{result.advisory_label}'"
        )


# ---------------------------------------------------------------------------
# test_validator_has_no_network_or_file_io (Req: no network/file writes)
# ---------------------------------------------------------------------------


def test_validator_has_no_network_or_file_io() -> None:
    """The validator source must not import any network or file I/O modules."""
    source = VALIDATOR_SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_imports = {
        "urllib", "urllib2", "urllib3", "requests", "httpx", "aiohttp",
        "socket", "ssl", "ftplib", "smtplib", "imaplib", "poplib",
        "subprocess", "os.system", "shutil",
        "open",  # checked separately below
    }

    # Collect all import names
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])

    network_imports = imported & {
        "urllib", "urllib2", "urllib3", "requests", "httpx",
        "aiohttp", "socket", "ssl", "ftplib", "smtplib", "imaplib",
        "poplib", "subprocess",
    }
    assert not network_imports, (
        f"Validator imports network/subprocess modules: {network_imports}"
    )

    # Check for open() or file write calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                assert False, "Validator must not use open() for file I/O"
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in ("write", "writelines", "unlink", "rmdir")
            ):
                assert False, (
                    f"Validator must not use file write method: {node.func.attr}"
                )


def test_validator_does_not_import_non_stdlib() -> None:
    """The validator must use only stdlib imports."""
    source = VALIDATOR_SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    stdlib_allowed = {
        "__future__", "dataclasses", "typing",
        "collections", "functools", "itertools",
        "re", "json", "math", "copy",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    # Allow src imports but flag third-party packages
    unknown = imported - stdlib_allowed - {"src"}
    # Modules starting with _ are internal to the file
    unknown = {m for m in unknown if not m.startswith("_")}
    assert not unknown, (
        f"Validator imports modules beyond stdlib allowlist: {unknown}"
    )


# ---------------------------------------------------------------------------
# human_review_required must always be true
# ---------------------------------------------------------------------------


def test_human_review_required_must_be_true() -> None:
    record = _build_valid_record()
    record["human_review"]["human_review_required"] = False
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("human_review_required" in e for e in result.errors)


def test_human_review_required_missing_fails() -> None:
    record = _build_valid_record()
    del record["human_review"]["human_review_required"]
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("human_review_required" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Output surface safety tests (Issue F/G follow-up)
# Verify that invalid records never echo forbidden terms, unsafe keys, or
# unsafe values in their errors — and that normalized_record is empty.
# ---------------------------------------------------------------------------

_ALL_FORBIDDEN_SUBSTRINGS = (
    "buy", "sell", "trade", "trading", "execute", "execution",
    "order ready", "execution ready", "entry", "exit",
    "position size", "position sizing", "expected return", "profit target",
    "stop loss", "take profit", "live signal", "auto copy",
    "automatic copy", "copy signal", "wallet copy instruction",
    "pnl target", "paper trading candidate", "strategy signal",
)

# These safety flag names are contract-defined exception keys; they contain
# forbidden-term substrings by design and must be stripped before scanning
# error messages for leaked user-provided unsafe content.
_SAFETY_FLAG_EXCEPTION_STRINGS = (
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
)

_OUTPUT_TRAP_RECORDS: list[tuple[str, dict[object, object]]] = [
    ("buy_signal key", {"buy_signal": "YES"}),
    ("expected_return key", {"expected_return": "12%"}),
    ("position_size key", {"position_size": "25 USDC"}),
    ("execution_ready key", {"execution_ready": True}),
    ("paper_trading_candidate key", {"paper_trading_candidate": True}),
    ("strategy_signal key", {"strategy_signal": "wallet followed"}),
    (
        "nested source_metadata with forbidden value",
        {"source_metadata": {"expected_return": "buy recommendation"}},
    ),
    (
        "nested metadata with position_size key",
        {"metadata": {"safe_outer": {"position_size": "25"}}},
    ),
]


def _errors_contain_forbidden_term(errors: tuple[str, ...]) -> str | None:
    for msg in errors:
        # Strip known-safe exception key names before scanning — they are
        # contract-defined vocabulary, not echoed user-provided content.
        sanitized = msg
        for exc in _SAFETY_FLAG_EXCEPTION_STRINGS:
            sanitized = sanitized.replace(exc, "")
        sanitized_norm = sanitized.lower().replace("_", " ").replace("-", " ")
        for term in _ALL_FORBIDDEN_SUBSTRINGS:
            if term in sanitized_norm:
                return f"term '{term}' in error '{msg}'"
    return None


@pytest.mark.parametrize("label,extra", _OUTPUT_TRAP_RECORDS)
def test_reviewer_trap_error_messages_do_not_echo_forbidden_terms(
    label: str, extra: dict[object, object]
) -> None:
    """Error messages for trap records must not echo forbidden terms or unsafe keys."""
    record: dict[str, object] = {**extra}
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False, f"Expected invalid for trap record: {label}"
    leaked = _errors_contain_forbidden_term(result.errors)
    assert leaked is None, (
        f"Trap record '{label}': output leakage detected — {leaked}"
    )


@pytest.mark.parametrize("label,extra", _OUTPUT_TRAP_RECORDS)
def test_reviewer_trap_invalid_normalized_record_is_empty(
    label: str, extra: dict[object, object]
) -> None:
    """Invalid records must return an empty normalized_record."""
    record: dict[str, object] = {**extra}
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False, f"Expected invalid for trap record: {label}"
    assert result.normalized_record == {}, (
        f"Trap record '{label}': normalized_record must be empty for invalid records, "
        f"got {result.normalized_record!r}"
    )


def test_valid_record_normalized_record_is_populated() -> None:
    """Valid records must return a non-empty normalized_record."""
    result = validate_wallet_signal_paper_strategy_contract_record(
        _build_valid_record()
    )
    assert result.is_valid is True
    assert result.normalized_record != {}


def test_output_surface_has_no_forbidden_terms_for_buy_signal_input() -> None:
    """Full output surface scan for {'buy_signal': 'YES'} input."""
    result = validate_wallet_signal_paper_strategy_contract_record(
        {"buy_signal": "YES"}
    )
    assert result.is_valid is False
    leaked = _errors_contain_forbidden_term(result.errors)
    assert leaked is None, f"Output leakage in errors: {leaked}"
    assert result.normalized_record == {}


def test_output_surface_has_no_forbidden_terms_for_expected_return_input() -> None:
    """Full output surface scan for {'expected_return': '12%'} input."""
    result = validate_wallet_signal_paper_strategy_contract_record(
        {"expected_return": "12%"}
    )
    assert result.is_valid is False
    leaked = _errors_contain_forbidden_term(result.errors)
    assert leaked is None, f"Output leakage in errors: {leaked}"
    assert result.normalized_record == {}


def test_output_surface_has_no_forbidden_terms_for_nested_position_size_input() -> None:
    """Full output surface scan for nested position_size in metadata input."""
    result = validate_wallet_signal_paper_strategy_contract_record(
        {"metadata": {"safe_outer": {"position_size": "25"}}}
    )
    assert result.is_valid is False
    leaked = _errors_contain_forbidden_term(result.errors)
    assert leaked is None, f"Output leakage in errors: {leaked}"
    assert result.normalized_record == {}


# ---------------------------------------------------------------------------
# Deferred items section validation
# ---------------------------------------------------------------------------


def test_deferred_items_section_must_be_present() -> None:
    record = _build_valid_record()
    del record["deferred_items"]
    record["eligibility_review"]["eligibility_status"] = (
        "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT"
    )
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("deferred_items" in e for e in result.errors)


# ---------------------------------------------------------------------------
# advisory_notice must be present
# ---------------------------------------------------------------------------


def test_advisory_notice_must_be_present() -> None:
    record = _build_valid_record()
    del record["advisory_notice"]
    result = validate_wallet_signal_paper_strategy_contract_record(record)
    assert result.is_valid is False
    assert any("advisory_notice" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_validator_is_idempotent() -> None:
    record = _build_valid_record()
    r1 = validate_wallet_signal_paper_strategy_contract_record(record)
    r2 = validate_wallet_signal_paper_strategy_contract_record(record)
    assert r1.is_valid == r2.is_valid
    assert r1.status == r2.status
    assert r1.errors == r2.errors
    assert r1.advisory_label == r2.advisory_label
