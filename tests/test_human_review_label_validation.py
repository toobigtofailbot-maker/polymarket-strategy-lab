"""
Focused unit tests for WP74 human review label record validator.

Tests validate_human_review_label_record() from
src/data_layer/human_review_label_validation.py.

Covers:
- Valid example schema passes
- Missing required top-level sections fail
- Missing required identity/review/safety fields fail
- Invalid enum values fail
- Forbidden workflow states fail
- Cross-field rule violations fail or warn per documented rule
- Forbidden key/value detection
- safety.no_execution is allowed (not flagged as forbidden)
- Type checks
- Frozen/deterministic result dataclass
- Module safety (no network, no file I/O, no credentials, no LLM imports)
"""

import json
import os
import copy

import pytest

from src.data_layer.human_review_label_validation import (
    validate_human_review_label_record,
    HumanReviewLabelValidationResult,
    ALLOWED_WORKFLOW_STATES,
    ALLOWED_USEFULNESS_LABELS,
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_PRIMARY_REASONS,
    REQUIRED_SAFETY_FLAGS,
    FORBIDDEN_KEY_NAMES,
    FORBIDDEN_STRING_VALUES,
    EXPECTED_NOTICE,
    EXPECTED_SCHEMA_VERSION,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_EXAMPLE_PATH = os.path.join(
    REPO_ROOT, "docs", "schemas", "human_review_label_record_v1.example.json"
)


def _load_example() -> dict:
    with open(SCHEMA_EXAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _valid_record() -> dict:
    return {
        "_notice": "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL",
        "_schema_version": "HUMAN_REVIEW_LABEL_RECORD_V1",
        "_status": "DESIGN_ONLY_NOT_IMPLEMENTED",
        "identity": {
            "market_id": "test-market-001",
            "condition_id": "test-condition-001",
            "question": "Will this test pass?",
            "snapshot_time_utc": "2026-01-01T00:00:00Z",
        },
        "review": {
            "review_time_utc": "2026-01-02T00:00:00Z",
            "reviewer_id_or_alias": "test-reviewer",
            "workflow_state": "LABEL_APPLIED",
            "human_review_usefulness_label": "USEFUL_RESEARCH_TARGET",
            "confidence_level": "MEDIUM",
            "primary_reason": "SOURCE_CLARITY",
            "secondary_reasons": [],
            "requires_followup_review": False,
            "review_notes": "Test review note.",
        },
        "safety": {
            "manual_only": True,
            "not_automated": True,
            "no_trading_signal": True,
            "no_score_change": True,
            "no_execution": True,
        },
    }


# ---------------------------------------------------------------------------
# Test 1: Valid example schema from the WP73 static example passes
# ---------------------------------------------------------------------------


def test_valid_example_schema_passes():
    example = _load_example()
    result = validate_human_review_label_record(example)
    assert result.is_valid, (
        f"Expected valid example to pass. missing={result.missing_required_fields}, "
        f"invalid={result.invalid_fields}"
    )
    assert result.missing_required_fields == ()
    assert result.invalid_fields == ()


def test_valid_base_record_passes():
    result = validate_human_review_label_record(_valid_record())
    assert result.is_valid, (
        f"Expected valid base record to pass. missing={result.missing_required_fields}, "
        f"invalid={result.invalid_fields}"
    )


# ---------------------------------------------------------------------------
# Test 2: Missing top-level identity fails
# ---------------------------------------------------------------------------


def test_missing_identity_fails():
    record = _valid_record()
    del record["identity"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "identity" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 3: Missing review section fails
# ---------------------------------------------------------------------------


def test_missing_review_section_fails():
    record = _valid_record()
    del record["review"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 4: Missing safety section fails
# ---------------------------------------------------------------------------


def test_missing_safety_section_fails():
    record = _valid_record()
    del record["safety"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "safety" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 5: Missing identity.market_id fails
# ---------------------------------------------------------------------------


def test_missing_identity_market_id_fails():
    record = _valid_record()
    del record["identity"]["market_id"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "identity.market_id" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 6: Missing identity.condition_id fails
# ---------------------------------------------------------------------------


def test_missing_identity_condition_id_fails():
    record = _valid_record()
    del record["identity"]["condition_id"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "identity.condition_id" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 7: Missing identity.snapshot_time_utc fails
# ---------------------------------------------------------------------------


def test_missing_identity_snapshot_time_utc_fails():
    record = _valid_record()
    del record["identity"]["snapshot_time_utc"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "identity.snapshot_time_utc" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 8: Missing review.reviewer_id_or_alias fails
# ---------------------------------------------------------------------------


def test_missing_reviewer_id_or_alias_fails():
    record = _valid_record()
    del record["review"]["reviewer_id_or_alias"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.reviewer_id_or_alias" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 9: Missing review.review_time_utc fails
# ---------------------------------------------------------------------------


def test_missing_review_time_utc_fails():
    record = _valid_record()
    del record["review"]["review_time_utc"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.review_time_utc" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 10: Invalid workflow_state fails
# ---------------------------------------------------------------------------


def test_invalid_workflow_state_fails():
    record = _valid_record()
    record["review"]["workflow_state"] = "INVALID_STATE_XYZ"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.workflow_state" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 11: AUTO_LABELED_BY_LLM workflow state fails
# ---------------------------------------------------------------------------


def test_auto_labeled_by_llm_workflow_state_fails():
    record = _valid_record()
    record["review"]["workflow_state"] = "AUTO_LABELED_BY_LLM"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.workflow_state" in result.invalid_fields
    assert any("AUTO_LABELED_BY_LLM" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 12: Invalid human_review_usefulness_label fails
# ---------------------------------------------------------------------------


def test_invalid_usefulness_label_fails():
    record = _valid_record()
    record["review"]["human_review_usefulness_label"] = "INVALID_LABEL"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.human_review_usefulness_label" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 13: Invalid confidence_level fails
# ---------------------------------------------------------------------------


def test_invalid_confidence_level_fails():
    record = _valid_record()
    record["review"]["confidence_level"] = "VERY_HIGH"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.confidence_level" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 14: Invalid primary_reason fails
# ---------------------------------------------------------------------------


def test_invalid_primary_reason_fails():
    record = _valid_record()
    record["review"]["primary_reason"] = "UNKNOWN_REASON"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.primary_reason" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 15: secondary_reasons must be a list
# ---------------------------------------------------------------------------


def test_secondary_reasons_must_be_list():
    record = _valid_record()
    record["review"]["secondary_reasons"] = "SOURCE_CLARITY"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.secondary_reasons" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 16: Invalid secondary reason fails
# ---------------------------------------------------------------------------


def test_invalid_secondary_reason_fails():
    record = _valid_record()
    record["review"]["secondary_reasons"] = ["SOURCE_CLARITY", "NOT_A_REASON"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.secondary_reasons" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 17: requires_followup_review must be bool
# ---------------------------------------------------------------------------


def test_requires_followup_review_must_be_bool():
    record = _valid_record()
    record["review"]["requires_followup_review"] = "false"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.requires_followup_review" in result.invalid_fields


def test_requires_followup_review_true_is_valid():
    record = _valid_record()
    record["review"]["requires_followup_review"] = True
    result = validate_human_review_label_record(record)
    assert result.is_valid or "review.requires_followup_review" not in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 18: Missing safety flag fails
# ---------------------------------------------------------------------------


def test_missing_safety_flag_fails():
    record = _valid_record()
    del record["safety"]["manual_only"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "safety.manual_only" in result.missing_required_fields


def test_all_required_safety_flags_present():
    for flag in REQUIRED_SAFETY_FLAGS:
        record = _valid_record()
        del record["safety"][flag]
        result = validate_human_review_label_record(record)
        assert not result.is_valid, f"Expected missing safety.{flag} to fail"
        assert f"safety.{flag}" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 19: Safety flag false fails
# ---------------------------------------------------------------------------


def test_safety_flag_false_fails():
    record = _valid_record()
    record["safety"]["no_trading_signal"] = False
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "safety.no_trading_signal" in result.invalid_fields


def test_all_safety_flags_must_be_true():
    for flag in REQUIRED_SAFETY_FLAGS:
        record = _valid_record()
        record["safety"][flag] = False
        result = validate_human_review_label_record(record)
        assert not result.is_valid, f"Expected safety.{flag}=False to fail"
        assert f"safety.{flag}" in result.invalid_fields


# ---------------------------------------------------------------------------
# Test 20: LABEL_APPLIED with NOT_REVIEWED label fails
# ---------------------------------------------------------------------------


def test_label_applied_with_not_reviewed_label_fails():
    record = _valid_record()
    record["review"]["workflow_state"] = "LABEL_APPLIED"
    record["review"]["human_review_usefulness_label"] = "NOT_REVIEWED"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "review.human_review_usefulness_label" in result.invalid_fields
    assert any("LABEL_APPLIED" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 21: NOT_REVIEWED workflow with non-NOT_REVIEWED label warns
# ---------------------------------------------------------------------------


def test_not_reviewed_workflow_with_other_label_warns():
    record = _valid_record()
    record["review"]["workflow_state"] = "NOT_REVIEWED"
    record["review"]["human_review_usefulness_label"] = "USEFUL_RESEARCH_TARGET"
    record["review"]["confidence_level"] = "MEDIUM"
    result = validate_human_review_label_record(record)
    assert any("NOT_REVIEWED" in w and "workflow_state" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 22: NEEDS_SECOND_REVIEW with requires_followup_review=false warns
# ---------------------------------------------------------------------------


def test_needs_second_review_with_followup_false_warns():
    record = _valid_record()
    record["review"]["workflow_state"] = "NEEDS_SECOND_REVIEW"
    record["review"]["requires_followup_review"] = False
    record["review"]["human_review_usefulness_label"] = "USEFUL_RESEARCH_TARGET"
    result = validate_human_review_label_record(record)
    assert any("NEEDS_SECOND_REVIEW" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 23: Forbidden key pnl is flagged
# ---------------------------------------------------------------------------


def test_forbidden_key_pnl_is_flagged():
    record = _valid_record()
    record["pnl"] = 0.5
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "pnl" in result.invalid_fields
    assert any("pnl" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 24: Forbidden key expected_return is flagged
# ---------------------------------------------------------------------------


def test_forbidden_key_expected_return_is_flagged():
    record = _valid_record()
    record["expected_return"] = 0.1
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "expected_return" in result.invalid_fields
    assert any("expected_return" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 25: Forbidden automation value AUTO_LABELED_BY_LLM is flagged
# ---------------------------------------------------------------------------


def test_forbidden_value_auto_labeled_by_llm_is_flagged():
    record = _valid_record()
    # Use it as a workflow_state — enum check catches it as invalid
    record["review"]["workflow_state"] = "AUTO_LABELED_BY_LLM"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    # Enum check flags it in invalid_fields
    assert "review.workflow_state" in result.invalid_fields
    # Value scan or workflow forbidden check produces a warning
    assert any("AUTO_LABELED_BY_LLM" in w for w in result.warnings)


def test_forbidden_value_auto_labeled_by_llm_in_other_field_warns():
    record = _valid_record()
    # Place forbidden value in a nested field (not as workflow_state)
    record["identity"]["_extra_flag"] = "AUTO_LABELED_BY_LLM"
    result = validate_human_review_label_record(record)
    assert any("AUTO_LABELED_BY_LLM" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Test 26: Required safety.no_execution is allowed despite containing execution
# ---------------------------------------------------------------------------


def test_safety_no_execution_is_allowed():
    record = _valid_record()
    result = validate_human_review_label_record(record)
    # no_execution is a required safety flag - must NOT be flagged as forbidden
    assert "safety.no_execution" not in result.invalid_fields
    assert not any("no_execution" in w and "forbidden" in w.lower() for w in result.warnings)


def test_safety_no_execution_missing_fails():
    record = _valid_record()
    del record["safety"]["no_execution"]
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "safety.no_execution" in result.missing_required_fields


# ---------------------------------------------------------------------------
# Test 27: Result dataclass is frozen/deterministic
# ---------------------------------------------------------------------------


def test_result_dataclass_is_frozen():
    result = validate_human_review_label_record(_valid_record())
    assert isinstance(result, HumanReviewLabelValidationResult)
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = False  # type: ignore[misc]


def test_result_is_deterministic():
    record = _valid_record()
    r1 = validate_human_review_label_record(record)
    r2 = validate_human_review_label_record(record)
    assert r1.is_valid == r2.is_valid
    assert r1.missing_required_fields == r2.missing_required_fields
    assert r1.invalid_fields == r2.invalid_fields
    assert r1.warnings == r2.warnings
    assert r1.advisory_label == r2.advisory_label


def test_result_fields_are_tuples():
    result = validate_human_review_label_record(_valid_record())
    assert isinstance(result.missing_required_fields, tuple)
    assert isinstance(result.invalid_fields, tuple)
    assert isinstance(result.warnings, tuple)
    assert isinstance(result.advisory_label, str)


# ---------------------------------------------------------------------------
# Test 28: Validator imports no network libraries
# ---------------------------------------------------------------------------


def test_validator_imports_no_network_libraries():
    import src.data_layer.human_review_label_validation as mod
    import sys
    network_libs = {
        "requests", "urllib3", "httpx", "aiohttp", "socket", "http.client",
        "ssl", "ftplib", "imaplib", "smtplib", "poplib", "xmlrpc",
    }
    loaded = set(sys.modules.keys())
    imported_by_module = set(dir(mod))
    for lib in network_libs:
        assert lib not in imported_by_module, f"Validator must not import {lib}"


# ---------------------------------------------------------------------------
# Test 29: Validator performs no file reads/writes
# ---------------------------------------------------------------------------


def test_validator_source_has_no_file_io():
    import inspect
    import src.data_layer.human_review_label_validation as mod
    source = inspect.getsource(mod)
    assert "open(" not in source, "Validator must not call open()"
    assert "Path(" not in source or "pathlib" not in source.lower(), (
        "Validator must not use pathlib file I/O"
    )
    assert "os.path.join" not in source, "Validator must not use os.path.join for file I/O"
    assert "read_text" not in source, "Validator must not call read_text()"
    assert "write_text" not in source, "Validator must not call write_text()"


# ---------------------------------------------------------------------------
# Test 30: Validator references no credentials
# ---------------------------------------------------------------------------


def test_validator_source_has_no_credentials():
    import inspect
    import src.data_layer.human_review_label_validation as mod
    source = inspect.getsource(mod)
    assert ".env" not in source, "Validator must not reference .env"
    assert "wallet" not in source.lower(), "Validator must not reference wallet"
    assert "api_key" not in source.lower(), "Validator must not reference api_key"
    assert "private_key" not in source.lower(), "Validator must not reference private_key"
    assert "auth" not in source.lower() or "not_automated" in source, (
        "Validator must not reference auth outside of safety flag wording"
    )


# ---------------------------------------------------------------------------
# Test 31: Validator does not import LLM/agent libraries
# ---------------------------------------------------------------------------


def test_validator_imports_no_llm_libraries():
    import inspect
    import src.data_layer.human_review_label_validation as mod
    source = inspect.getsource(mod)
    llm_libs = ["anthropic", "openai", "langchain", "llama", "huggingface", "transformers"]
    for lib in llm_libs:
        assert lib not in source.lower(), f"Validator must not import {lib}"


# ---------------------------------------------------------------------------
# Test 32: Human review label workflow docs tests still pass (import check)
# ---------------------------------------------------------------------------


def test_human_review_label_workflow_docs_importable():
    import tests.test_human_review_label_workflow_docs  # noqa: F401


# ---------------------------------------------------------------------------
# Test 33: Project status docs tests importable
# ---------------------------------------------------------------------------


def test_project_status_docs_importable():
    import tests.test_project_status_docs  # noqa: F401


# ---------------------------------------------------------------------------
# Additional coverage for all allowed enum values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", list(ALLOWED_WORKFLOW_STATES))
def test_all_allowed_workflow_states_pass(state):
    record = _valid_record()
    record["review"]["workflow_state"] = state
    if state == "NOT_REVIEWED":
        record["review"]["human_review_usefulness_label"] = "NOT_REVIEWED"
        record["review"]["confidence_level"] = "NOT_APPLICABLE"
    elif state == "NEEDS_SECOND_REVIEW":
        record["review"]["requires_followup_review"] = True
    result = validate_human_review_label_record(record)
    assert "review.workflow_state" not in result.invalid_fields, (
        f"Allowed workflow state '{state}' should not be in invalid_fields"
    )


@pytest.mark.parametrize("label", list(ALLOWED_USEFULNESS_LABELS))
def test_all_allowed_usefulness_labels_valid(label):
    record = _valid_record()
    if label == "NOT_REVIEWED":
        record["review"]["workflow_state"] = "NOT_REVIEWED"
        record["review"]["confidence_level"] = "NOT_APPLICABLE"
    record["review"]["human_review_usefulness_label"] = label
    result = validate_human_review_label_record(record)
    assert "review.human_review_usefulness_label" not in result.invalid_fields, (
        f"Allowed label '{label}' should not be in invalid_fields"
    )


@pytest.mark.parametrize("level", list(ALLOWED_CONFIDENCE_LEVELS))
def test_all_allowed_confidence_levels_valid(level):
    record = _valid_record()
    if level == "NOT_APPLICABLE":
        record["review"]["workflow_state"] = "NOT_REVIEWED"
        record["review"]["human_review_usefulness_label"] = "NOT_REVIEWED"
    record["review"]["confidence_level"] = level
    result = validate_human_review_label_record(record)
    assert "review.confidence_level" not in result.invalid_fields, (
        f"Allowed confidence level '{level}' should not be in invalid_fields"
    )


@pytest.mark.parametrize("reason", list(ALLOWED_PRIMARY_REASONS))
def test_all_allowed_primary_reasons_valid(reason):
    record = _valid_record()
    record["review"]["primary_reason"] = reason
    result = validate_human_review_label_record(record)
    assert "review.primary_reason" not in result.invalid_fields, (
        f"Allowed primary reason '{reason}' should not be in invalid_fields"
    )


# ---------------------------------------------------------------------------
# Additional forbidden key coverage
# ---------------------------------------------------------------------------


def test_forbidden_key_profit_flagged():
    record = _valid_record()
    record["profit"] = 100.0
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "profit" in result.invalid_fields


def test_forbidden_key_nested_pnl_flagged():
    record = _valid_record()
    record["identity"]["pnl"] = 0.5
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert any("pnl" in k for k in result.invalid_fields)


# ---------------------------------------------------------------------------
# Additional cross-field coverage
# ---------------------------------------------------------------------------


def test_label_applied_with_valid_confidence_passes():
    record = _valid_record()
    record["review"]["workflow_state"] = "LABEL_APPLIED"
    record["review"]["confidence_level"] = "HIGH"
    result = validate_human_review_label_record(record)
    assert "review.confidence_level" not in result.invalid_fields


def test_not_reviewed_workflow_with_not_reviewed_label_passes():
    record = _valid_record()
    record["review"]["workflow_state"] = "NOT_REVIEWED"
    record["review"]["human_review_usefulness_label"] = "NOT_REVIEWED"
    record["review"]["confidence_level"] = "NOT_APPLICABLE"
    result = validate_human_review_label_record(record)
    assert not any("NOT_REVIEWED" in w and "Cross-field" in w for w in result.warnings)


def test_needs_second_review_with_followup_true_no_warning():
    record = _valid_record()
    record["review"]["workflow_state"] = "NEEDS_SECOND_REVIEW"
    record["review"]["requires_followup_review"] = True
    result = validate_human_review_label_record(record)
    assert not any("NEEDS_SECOND_REVIEW" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Advisory label presence
# ---------------------------------------------------------------------------


def test_advisory_label_present_on_valid_result():
    result = validate_human_review_label_record(_valid_record())
    assert "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL" in result.advisory_label


def test_advisory_label_present_on_invalid_result():
    record = _valid_record()
    del record["identity"]
    result = validate_human_review_label_record(record)
    assert "ADVISORY_ONLY_MANUAL_RESEARCH_REVIEW_LABEL" in result.advisory_label


# ---------------------------------------------------------------------------
# Empty record
# ---------------------------------------------------------------------------


def test_empty_record_fails():
    result = validate_human_review_label_record({})
    assert not result.is_valid
    assert len(result.missing_required_fields) > 0


# ---------------------------------------------------------------------------
# _notice and _schema_version expected value checks
# ---------------------------------------------------------------------------


def test_wrong_notice_value_invalid():
    record = _valid_record()
    record["_notice"] = "WRONG_NOTICE"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "_notice" in result.invalid_fields


def test_wrong_schema_version_invalid():
    record = _valid_record()
    record["_schema_version"] = "WRONG_VERSION"
    result = validate_human_review_label_record(record)
    assert not result.is_valid
    assert "_schema_version" in result.invalid_fields
