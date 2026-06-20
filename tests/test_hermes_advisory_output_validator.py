"""Focused tests for WP99 Hermes advisory output validator.

Trap-test coverage per WP99 Section 17 requirement-to-test mapping:

  A. Required-field failures
  B. Forbidden action phrases (all 29 trap phrases from WP99)
  C. Recursive scan (nested dict/list, warnings, limitations, examples)
  D. Raw metadata keys rejected (recursive)
  E. No unsafe echo in any result surface
  F. Valid path (minimal valid output passes, normalized_output populated)
  G. Source-level boundary (no network/runtime/file-write imports)
  H. Status/doc trap (status fragment wording checks)
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import re
from pathlib import Path
from typing import Any

import pytest

from src.data_layer.hermes_advisory_output_validator import (
    ADVISORY_LABEL,
    ALLOWED_CONFIDENCE_LEVELS,
    INVALID_STATUS,
    REQUIRED_BOOLEAN_SAFETY_FIELDS,
    REQUIRED_TEXT_FIELDS,
    REQUIRED_TOP_LEVEL_FIELDS,
    VALID_STATUS,
    HermesAdvisoryOutputValidationResult,
    validate_hermes_advisory_output,
)

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SRC = ROOT / "src" / "data_layer" / "hermes_advisory_output_validator.py"


# ---------------------------------------------------------------------------
# Minimal valid advisory output builder
# ---------------------------------------------------------------------------

def _build_valid_output() -> dict[str, Any]:
    """Return a minimal valid Hermes advisory output for testing.

    All required boolean safety fields are True. All required text/list
    fields are present and non-empty. Confidence level is LOW. No
    forbidden terms appear in any key or value.
    """
    return {
        # Boolean safety fields
        "advisory_only": True,
        "human_review_required": True,
        "no_execution_authority": True,
        "no_risk_override": True,
        "no_credential_request": True,
        "no_order_or_cancel_or_sign_or_submit": True,
        "no_paper_live_decision": True,
        "no_strategy_promotion_approval": True,
        "no_pr_approval_or_merge_readiness_claim": True,
        # Text / list fields
        "evidence_summary": (
            "Research hypothesis based on available public data. "
            "No private or authenticated data sources were used."
        ),
        "source_refs": ["docs/hermes_research_brain_execution_plan.md"],
        "provenance_status": "MANUAL_RESEARCH_ONLY",
        "staleness_status": "CURRENT_AT_TIME_OF_RESEARCH",
        "confidence_level": "LOW",
        "uncertainty_notes": (
            "Significant uncertainty remains. Human verification required "
            "before any consideration of future research steps."
        ),
        "assumptions": [
            "Public data only.",
            "No authenticated endpoint access was used.",
        ],
        "falsification_path": (
            "This hypothesis would be falsified by contrary public "
            "resolution data or deterministic repo-truth checks."
        ),
        "deterministic_validation_handoff": (
            "Human reviewer to validate against current repo-truth docs "
            "and deterministic-core outputs before any downstream use."
        ),
        "rejected_interpretations": [
            "Rejected: no direct market authority is implied by this output.",
            "Rejected: no automated reproduction of this analysis is authorized.",
        ],
        "forbidden_action_statement": (
            "This output is advisory only. Human review is required before "
            "any action. No execution, allocation, risk modification, "
            "credential access, strategy advancement, scheduler instruction, "
            "authenticated endpoint access, PR endorsement, or merge "
            "authorization is granted."
        ),
        "next_human_review_step": (
            "Review the evidence summary and validate against current "
            "repo-truth docs before any further consideration."
        ),
    }


# ---------------------------------------------------------------------------
# F. Valid path
# ---------------------------------------------------------------------------

def test_valid_minimal_output_passes() -> None:
    result = validate_hermes_advisory_output(_build_valid_output())
    assert result.is_valid is True
    assert result.status == VALID_STATUS
    assert result.errors == ()
    assert result.advisory_label == ADVISORY_LABEL


def test_valid_output_normalized_output_populated() -> None:
    output = _build_valid_output()
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is True
    assert result.normalized_output != {}
    assert dict(result.normalized_output) == output


def test_valid_output_all_boolean_safety_fields_true() -> None:
    output = _build_valid_output()
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is True
    for field in REQUIRED_BOOLEAN_SAFETY_FIELDS:
        assert output[field] is True


def test_confidence_level_allowlist_low() -> None:
    output = _build_valid_output()
    output["confidence_level"] = "LOW"
    assert validate_hermes_advisory_output(output).is_valid is True


def test_confidence_level_allowlist_medium() -> None:
    output = _build_valid_output()
    output["confidence_level"] = "MEDIUM"
    assert validate_hermes_advisory_output(output).is_valid is True


def test_confidence_level_allowlist_high() -> None:
    output = _build_valid_output()
    output["confidence_level"] = "HIGH"
    assert validate_hermes_advisory_output(output).is_valid is True


def test_result_is_frozen_dataclass() -> None:
    result = validate_hermes_advisory_output(_build_valid_output())
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
        result.is_valid = False  # type: ignore[misc]


def test_result_advisory_label_constant() -> None:
    result = validate_hermes_advisory_output(_build_valid_output())
    assert result.advisory_label == ADVISORY_LABEL
    assert result.advisory_label == "ADVISORY_ONLY_HERMES_OUTPUT_VALIDATION"


# ---------------------------------------------------------------------------
# A. Required-field failures
# ---------------------------------------------------------------------------

def test_missing_advisory_only_fails() -> None:
    output = _build_valid_output()
    del output["advisory_only"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert result.status == INVALID_STATUS
    assert any("advisory_only" in e for e in result.errors)


def test_advisory_only_false_fails() -> None:
    output = _build_valid_output()
    output["advisory_only"] = False
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("advisory_only" in e for e in result.errors)


def test_missing_human_review_required_fails() -> None:
    output = _build_valid_output()
    del output["human_review_required"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("human_review_required" in e for e in result.errors)


def test_human_review_required_false_fails() -> None:
    output = _build_valid_output()
    output["human_review_required"] = False
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("human_review_required" in e for e in result.errors)


def test_missing_no_execution_authority_fails() -> None:
    output = _build_valid_output()
    del output["no_execution_authority"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("no_execution_authority" in e for e in result.errors)


def test_missing_forbidden_action_statement_fails() -> None:
    output = _build_valid_output()
    del output["forbidden_action_statement"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("forbidden_action_statement" in e for e in result.errors)


def test_missing_deterministic_validation_handoff_fails() -> None:
    output = _build_valid_output()
    del output["deterministic_validation_handoff"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("deterministic_validation_handoff" in e for e in result.errors)


@pytest.mark.parametrize("field", REQUIRED_BOOLEAN_SAFETY_FIELDS)
def test_each_boolean_safety_field_missing_fails(field: str) -> None:
    output = _build_valid_output()
    del output[field]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any(field in e for e in result.errors)


@pytest.mark.parametrize("field", REQUIRED_BOOLEAN_SAFETY_FIELDS)
def test_each_boolean_safety_field_false_fails(field: str) -> None:
    output = _build_valid_output()
    output[field] = False
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any(field in e for e in result.errors)


@pytest.mark.parametrize("field", REQUIRED_TEXT_FIELDS)
def test_each_required_text_field_missing_fails(field: str) -> None:
    output = _build_valid_output()
    del output[field]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any(field in e for e in result.errors)


@pytest.mark.parametrize("field", [
    "evidence_summary",
    "provenance_status",
    "staleness_status",
    "confidence_level",
    "uncertainty_notes",
    "falsification_path",
    "deterministic_validation_handoff",
    "forbidden_action_statement",
    "next_human_review_step",
])
def test_empty_string_text_field_fails(field: str) -> None:
    output = _build_valid_output()
    output[field] = ""
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any(field in e for e in result.errors)


def test_empty_source_refs_list_fails() -> None:
    output = _build_valid_output()
    output["source_refs"] = []
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_empty_assumptions_list_fails() -> None:
    output = _build_valid_output()
    output["assumptions"] = []
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_empty_rejected_interpretations_list_fails() -> None:
    output = _build_valid_output()
    output["rejected_interpretations"] = []
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_unknown_confidence_level_fails() -> None:
    output = _build_valid_output()
    output["confidence_level"] = "VERY_HIGH"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert any("confidence_level" in e for e in result.errors)


def test_invalid_normalized_output_is_empty() -> None:
    output = _build_valid_output()
    del output["advisory_only"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert result.normalized_output == {}


# ---------------------------------------------------------------------------
# B. Forbidden action phrases — all 29 trap test phrases from WP99 Sec 17
# ---------------------------------------------------------------------------

_FORBIDDEN_PHRASES: list[tuple[str, str]] = [
    ("buy_yes_now", "buy YES now"),
    ("sell_this_market", "sell this market"),
    ("hold_position", "hold position"),
    ("enter_at", "enter at 0.42"),
    ("exit_at", "exit at 0.65"),
    ("position_size", "position_size"),
    ("allocate_pct", "allocate 10%"),
    ("limit_price", "limit_price"),
    ("stop_loss", "stop_loss"),
    ("take_profit", "take_profit"),
    ("place_order", "place order"),
    ("cancel_order", "cancel order"),
    ("sign_transaction", "sign transaction"),
    ("submit_order", "submit order"),
    ("override_risk", "override risk"),
    ("live_ready", "live ready"),
    ("paper_execution_approved", "paper execution approved"),
    ("promote_strategy", "promote strategy"),
    ("update_config", "update config"),
    ("start_scheduler", "start scheduler"),
    ("run_bot_loop", "run bot loop"),
    ("request_api_key", "request API key"),
    ("use_private_endpoint", "use private endpoint"),
    ("fetch_account_balance", "fetch account balance"),
    ("approve_pr", "approve PR"),
    ("merge_ready", "merge-ready"),
    ("final_decision", "final decision"),
    ("run_hermes_automatically", "run Hermes automatically"),
    ("set_provider", "set provider"),
]


@pytest.mark.parametrize("label,phrase", _FORBIDDEN_PHRASES)
def test_forbidden_phrase_in_top_level_string_value_fails(label: str, phrase: str) -> None:
    output = _build_valid_output()
    output["evidence_summary"] = phrase
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False, f"Expected {label!r} ({phrase!r}) to be rejected"


@pytest.mark.parametrize("label,phrase", _FORBIDDEN_PHRASES)
def test_forbidden_phrase_in_uncertainty_notes_fails(label: str, phrase: str) -> None:
    output = _build_valid_output()
    output["uncertainty_notes"] = phrase
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False, f"Expected {label!r} ({phrase!r}) to be rejected"


@pytest.mark.parametrize("label,phrase", _FORBIDDEN_PHRASES)
def test_forbidden_phrase_in_falsification_path_fails(label: str, phrase: str) -> None:
    output = _build_valid_output()
    output["falsification_path"] = phrase
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False, f"Expected {label!r} ({phrase!r}) to be rejected"


# ---------------------------------------------------------------------------
# C. Recursive scan
# ---------------------------------------------------------------------------

def test_forbidden_phrase_in_nested_dict_value_fails() -> None:
    output = _build_valid_output()
    output["analysis"] = {"recommendation": "buy YES now"}
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_nested_dict_key_fails() -> None:
    output = _build_valid_output()
    output["position_size"] = "research note"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_inside_list_fails() -> None:
    output = _build_valid_output()
    output["source_refs"] = ["legitimate ref", "place order at 0.42"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_nested_list_inside_dict_fails() -> None:
    output = _build_valid_output()
    output["analysis"] = {"warnings": ["override risk parameters"]}
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_warning_style_field_fails() -> None:
    output = _build_valid_output()
    output["data_quality_warnings"] = ["stop loss not configured"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_limitation_style_field_fails() -> None:
    output = _build_valid_output()
    output["limitations"] = "This analysis recommends to limit price entry at 0.45"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_advisory_notice_field_fails() -> None:
    output = _build_valid_output()
    output["advisory_notice"] = "run Hermes automatically each morning"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_example_field_fails() -> None:
    output = _build_valid_output()
    output["examples"] = "Example: place order when price crosses 0.5"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_markdown_like_string_fails() -> None:
    output = _build_valid_output()
    output["analysis"] = (
        "## Research Note\n\n"
        "Based on signals, **submit order** at next opportunity."
    )
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_phrase_in_deeply_nested_value_fails() -> None:
    output = _build_valid_output()
    output["analysis"] = {
        "section_a": {
            "subsection": {
                "note": "approve PR for live deployment"
            }
        }
    }
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


# ---------------------------------------------------------------------------
# D. Raw metadata keys rejected
# ---------------------------------------------------------------------------

def test_metadata_key_rejected() -> None:
    output = _build_valid_output()
    output["metadata"] = {"source": "hermes_run_1"}
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_source_metadata_key_rejected() -> None:
    output = _build_valid_output()
    output["source_metadata"] = {"run_id": "abc123"}
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_raw_metadata_key_rejected() -> None:
    output = _build_valid_output()
    output["raw_metadata"] = "some raw data"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_raw_response_key_rejected() -> None:
    output = _build_valid_output()
    output["raw_response"] = "model generated text"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_model_response_key_rejected() -> None:
    output = _build_valid_output()
    output["model_response"] = "generated content"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_prompt_key_rejected() -> None:
    output = _build_valid_output()
    output["prompt"] = "User: analyze this market..."
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_completion_key_rejected() -> None:
    output = _build_valid_output()
    output["completion"] = "Assistant: here is my analysis..."
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_extra_key_rejected() -> None:
    output = _build_valid_output()
    output["extra"] = {"key": "value"}
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_nested_raw_metadata_key_rejected() -> None:
    output = _build_valid_output()
    output["analysis"] = {
        "hypothesis": "Market edge detected",
        "metadata": {"source": "model_output"},
    }
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_nested_prompt_key_in_list_dict_rejected() -> None:
    output = _build_valid_output()
    output["analysis_steps"] = [{"prompt": "analyze this"}]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


# ---------------------------------------------------------------------------
# E. No unsafe echo
# ---------------------------------------------------------------------------

def _all_result_strings(result: HermesAdvisoryOutputValidationResult) -> list[str]:
    """Collect all string content from all public result fields."""
    parts: list[str] = [
        result.status,
        result.advisory_label,
    ]
    parts.extend(result.errors)
    parts.extend(result.warnings)
    if isinstance(result.normalized_output, dict):
        parts.extend(_collect_strings(result.normalized_output))
    return parts


def _collect_strings(obj: object) -> list[str]:
    parts: list[str] = []
    if isinstance(obj, str):
        parts.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            parts.append(str(k))
            parts.extend(_collect_strings(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            parts.extend(_collect_strings(item))
    return parts


def test_invalid_errors_do_not_echo_forbidden_phrase() -> None:
    output = _build_valid_output()
    output["evidence_summary"] = "buy YES now"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    combined = " ".join(_all_result_strings(result)).lower()
    assert "buy yes now" not in combined


def test_invalid_errors_do_not_echo_raw_forbidden_value() -> None:
    output = _build_valid_output()
    output["evidence_summary"] = "place order at limit price 0.45"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    combined = " ".join(result.errors).lower()
    assert "place order" not in combined
    assert "limit price" not in combined
    assert "0.45" not in combined


def test_invalid_normalized_output_is_empty_for_forbidden_phrase() -> None:
    output = _build_valid_output()
    output["evidence_summary"] = "sell at 0.65"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert result.normalized_output == {}


def test_invalid_normalized_output_is_empty_for_missing_field() -> None:
    output = _build_valid_output()
    del output["advisory_only"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert result.normalized_output == {}


def test_status_field_does_not_echo_forbidden_phrases() -> None:
    output = _build_valid_output()
    output["evidence_summary"] = "submit order now"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert "submit order" not in result.status.lower()


def test_advisory_label_does_not_echo_forbidden_phrases() -> None:
    output = _build_valid_output()
    output["uncertainty_notes"] = "override risk threshold"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    assert "override risk" not in result.advisory_label.lower()


def test_full_invalid_result_scan_finds_no_forbidden_raw_terms() -> None:
    forbidden_phrases = [
        "buy yes now",
        "sell this market",
        "place order",
        "override risk",
        "live ready",
        "approve pr",
        "final decision",
        "run hermes",
        "account balance",
        "private endpoint",
    ]
    output = _build_valid_output()
    output["evidence_summary"] = forbidden_phrases[0]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    combined = " ".join(_all_result_strings(result)).lower()
    for phrase in forbidden_phrases:
        assert phrase not in combined, (
            f"Unsafe phrase {phrase!r} found in result output surface"
        )


def test_raw_metadata_error_does_not_echo_key_name() -> None:
    output = _build_valid_output()
    output["prompt"] = "some prompt text that could contain injection"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False
    combined = " ".join(result.errors)
    assert "prompt text" not in combined
    assert "injection" not in combined


# ---------------------------------------------------------------------------
# G. Source-level boundary — no forbidden imports or runtime patterns
# ---------------------------------------------------------------------------

def test_validator_module_has_no_network_imports() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    forbidden = ("requests", "httpx", "websocket", "urllib.request", "http.client")
    for term in forbidden:
        assert term not in src, f"Forbidden network import found: {term!r}"


def test_validator_module_has_no_subprocess_import() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_validator_module_has_no_file_write_operations() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    assert "open(" not in src
    assert ".write(" not in src


def test_validator_module_has_no_runtime_patterns() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    forbidden_patterns = ("while True", "time.sleep", "os.environ", "pathlib.Path")
    for pattern in forbidden_patterns:
        assert pattern not in src, f"Forbidden runtime pattern found: {pattern!r}"


def test_validator_module_has_no_sdk_imports() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    forbidden_imports = (
        "import anthropic",
        "import openai",
        "import langchain",
        "import pydantic",
        "import yaml",
        "from anthropic",
        "from openai",
        "from langchain",
        "from pydantic",
        "from yaml",
    )
    for term in forbidden_imports:
        assert term not in src, f"Forbidden SDK import found: {term!r}"


def test_validator_module_ast_imports_are_stdlib_only() -> None:
    src = VALIDATOR_SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    stdlib_allowed = {
        "__future__",
        "dataclasses",
        "typing",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = ""
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    assert module in stdlib_allowed, (
                        f"Non-stdlib import in validator: {module!r}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module.split(".")[0]
                assert module in stdlib_allowed, (
                    f"Non-stdlib import in validator: {module!r}"
                )


# ---------------------------------------------------------------------------
# Additional trap coverage
# ---------------------------------------------------------------------------

def test_advisory_only_none_fails() -> None:
    output = _build_valid_output()
    output["advisory_only"] = None
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_advisory_only_string_true_fails() -> None:
    output = _build_valid_output()
    output["advisory_only"] = "true"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_human_review_required_none_fails() -> None:
    output = _build_valid_output()
    output["human_review_required"] = None
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_whitespace_only_text_field_fails() -> None:
    output = _build_valid_output()
    output["evidence_summary"] = "   "
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_confidence_level_lowercase_fails() -> None:
    output = _build_valid_output()
    output["confidence_level"] = "low"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_confidence_level_empty_string_fails() -> None:
    output = _build_valid_output()
    output["confidence_level"] = ""
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_empty_mapping_fails() -> None:
    result = validate_hermes_advisory_output({})
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert result.normalized_output == {}


def test_all_required_top_level_fields_are_documented() -> None:
    expected_bool = set(REQUIRED_BOOLEAN_SAFETY_FIELDS)
    expected_text = set(REQUIRED_TEXT_FIELDS)
    assert expected_bool.isdisjoint(expected_text), (
        "Boolean and text field sets must not overlap"
    )
    combined = set(REQUIRED_TOP_LEVEL_FIELDS)
    assert combined == expected_bool | expected_text


def test_result_dataclass_has_all_required_fields() -> None:
    result = validate_hermes_advisory_output(_build_valid_output())
    assert hasattr(result, "is_valid")
    assert hasattr(result, "status")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert hasattr(result, "normalized_output")
    assert hasattr(result, "advisory_label")


def test_errors_and_warnings_are_tuples() -> None:
    result = validate_hermes_advisory_output(_build_valid_output())
    assert isinstance(result.errors, tuple)
    assert isinstance(result.warnings, tuple)


def test_forbidden_phrase_in_rejected_interpretations_fails() -> None:
    output = _build_valid_output()
    output["rejected_interpretations"] = ["Recommended: buy YES tokens at 0.42"]
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_forbidden_key_in_top_level_position_size_fails() -> None:
    output = _build_valid_output()
    output["position_sizing"] = "1000 USDC"
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is False


def test_safety_key_exception_names_not_rejected_as_keys() -> None:
    output = _build_valid_output()
    result = validate_hermes_advisory_output(output)
    assert result.is_valid is True, (
        f"Safety key exception names should not be rejected as keys: {result.errors}"
    )


def test_allowed_confidence_levels_constant() -> None:
    assert "LOW" in ALLOWED_CONFIDENCE_LEVELS
    assert "MEDIUM" in ALLOWED_CONFIDENCE_LEVELS
    assert "HIGH" in ALLOWED_CONFIDENCE_LEVELS
    assert len(ALLOWED_CONFIDENCE_LEVELS) == 3


# ---------------------------------------------------------------------------
# H. Status/doc trap (deferred to test_project_status_docs.py for WP99)
# ---------------------------------------------------------------------------

def test_wp99_status_entry_exists() -> None:
    status_entry = ROOT / "docs" / "status_entries" / "WP99.md"
    assert status_entry.is_file(), "docs/status_entries/WP99.md must exist"


def test_wp99_status_entry_not_tbd() -> None:
    status_entry = ROOT / "docs" / "status_entries" / "WP99.md"
    text = status_entry.read_text(encoding="utf-8")
    assert "Merge commit: TBD after merge" not in text
    assert "PR: TBD" not in text


def test_wp99_status_entry_stable_wording() -> None:
    status_entry = ROOT / "docs" / "status_entries" / "WP99.md"
    text = status_entry.read_text(encoding="utf-8")
    assert "stable and non-self-referential" in text
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "Current live PR head: see GitHub PR metadata and PR body" in text


def test_wp99_status_entry_no_fixed_live_sha() -> None:
    status_entry = ROOT / "docs" / "status_entries" / "WP99.md"
    text = status_entry.read_text(encoding="utf-8")
    fixed_live_head = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_live_head.search(text) is None
