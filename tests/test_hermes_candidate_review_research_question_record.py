"""Focused tests for WP121 research question record validation."""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_research_question_record.py"


def _import_module():
    mod_name = "hermes_candidate_review_research_question_record"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _import_module()

ALLOWED_TYPES = _mod.ALLOWED_RESEARCH_QUESTION_TYPES
REQUIRED_FIELDS = _mod.REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS
REQUIRED_PREFLIGHT = _mod.REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS
REQUIRED_FLAGS = _mod.REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS
Result = _mod.HermesCandidateReviewResearchQuestionRecordResult
validate_record = _mod.validate_candidate_review_research_question_record
build_record = _mod.build_candidate_review_research_question_record
assert_record = _mod.assert_candidate_review_research_question_record


def _valid_safety_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_FLAGS}


def _valid_intake_basis() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_PREFLIGHT}


def _valid_notice() -> str:
    return (
        "Advisory-only manual local offline planning record. "
        "It is not a trade signal, not strategy promotion, not paper readiness, "
        "not live readiness, not execution authority, not risk authority, "
        "not order authority, not PR approval, not merge readiness, "
        "not credential permission, not account access, not private-state "
        "permission, not Hermes runtime authority, and not prompt runner authority."
    )


def _valid_record(question_type: str = "SOURCE_PROVENANCE_WEAKNESS") -> dict[str, Any]:
    return {
        "record_id": "rq-001",
        "source_wp_context": {
            "intake_wp": "WP118",
            "runbook_wp": "WP119",
            "contract_wp": "WP120",
        },
        "selected_candidate_reference": {
            "candidate_id": "candidate-001",
            "source_artifact": "reviewed-local-artifact-reference",
        },
        "intake_basis": _valid_intake_basis(),
        "research_question": "Which source references need manual provenance review?",
        "research_question_type": question_type,
        "evidence_references_to_check": ["source-reference-001"],
        "uncertainty_notes": ["Source provenance needs manual inspection."],
        "known_missing_data": ["Secondary reference not yet inspected."],
        "limitations": ["Planning record only."],
        "falsification_checks_to_perform": ["Check a conflicting reference manually."],
        "forbidden_interpretation_flags": {
            "not_a_signal": True,
            "not_authority": True,
        },
        "human_review_required": True,
        "next_manual_step": "Manually inspect the listed source references.",
        "created_by_operator_note": "Prepared by human operator for research planning.",
        "non_authority_notice": _valid_notice(),
        "safety_flags": _valid_safety_flags(),
    }


def _all_public_result_values(result: Result) -> list[object]:
    return [
        result.is_valid,
        result.record,
        result.errors,
        result.warnings,
        result.research_question_type,
        result.safety_flags,
    ]


def test_module_imports_with_stdlib_only_dependencies() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed = {"__future__", "dataclasses", "typing"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] in allowed


def test_valid_minimal_record_builds_successfully() -> None:
    result = build_record(_valid_record())
    assert result.is_valid is True
    assert result.record != {}
    assert result.errors == ()
    assert result.research_question_type == "SOURCE_PROVENANCE_WEAKNESS"


def test_valid_record_returns_sanitized_safety_flags() -> None:
    data = _valid_record()
    data["safety_flags"]["unexpected_flag"] = True
    result = build_record(data)
    assert result.is_valid is True
    assert result.safety_flags == {flag: True for flag in REQUIRED_FLAGS}
    assert result.record["safety_flags"] == result.safety_flags
    assert "unexpected_flag" not in result.safety_flags


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_all_required_fields_are_enforced(field: str) -> None:
    data = _valid_record()
    del data[field]
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "MISSING_REQUIRED_FIELD" in result.errors


@pytest.mark.parametrize("question_type", sorted(ALLOWED_TYPES))
def test_each_allowed_research_question_type_is_accepted(question_type: str) -> None:
    result = build_record(_valid_record(question_type))
    assert result.is_valid is True
    assert result.research_question_type == question_type


def test_unknown_research_question_type_is_rejected() -> None:
    data = _valid_record("UNKNOWN_TYPE")
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_RESEARCH_QUESTION_TYPE" in result.errors


def test_wallet_signal_uncertainty_exact_enum_is_allowed() -> None:
    result = build_record(_valid_record("WALLET_SIGNAL_UNCERTAINTY"))
    assert result.is_valid is True


@pytest.mark.parametrize("unsafe", [
    "wallet key data",
    "account state details",
    "private endpoint sample",
])
def test_free_form_wallet_account_private_state_data_is_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["selected_candidate_reference"]["unsafe_note"] = unsafe
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_human_review_required_must_be_true() -> None:
    data = _valid_record()
    data["human_review_required"] = False
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "HUMAN_REVIEW_REQUIRED" in result.errors


@pytest.mark.parametrize("flag", REQUIRED_FLAGS)
def test_required_safety_flags_must_be_present_and_true(flag: str) -> None:
    data = _valid_record()
    del data["safety_flags"][flag]
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_SAFETY_FLAG" in result.errors

    data = _valid_record()
    data["safety_flags"][flag] = False
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


@pytest.mark.parametrize("flag", REQUIRED_PREFLIGHT)
def test_required_preflight_flags_must_be_present_and_true(flag: str) -> None:
    data = _valid_record()
    del data["intake_basis"][flag]
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_PREFLIGHT_FLAG" in result.errors

    data = _valid_record()
    data["intake_basis"][flag] = False
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_PREFLIGHT_FLAG" in result.errors


def test_non_authority_notice_is_required() -> None:
    data = _valid_record()
    data["non_authority_notice"] = ""
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_NON_AUTHORITY_NOTICE" in result.errors


def test_non_authority_notice_cannot_grant_permission() -> None:
    data = _valid_record()
    data["non_authority_notice"] = (
        "Advisory manual local offline note that grants paper/live/execution "
        "readiness and PR approval permission."
    )
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_NON_AUTHORITY_NOTICE" in result.errors


@pytest.mark.parametrize("unsafe", [
    "buy",
    "sell",
    "hold",
    "short",
    "trade",
    "trading",
    "order",
    "execute",
    "execution",
    "entry",
    "exit",
    "stop loss",
    "take profit",
])
def test_forbidden_trade_action_variants_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["uncertainty_notes"].append(f"hidden {unsafe} request")
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "expected return",
    "fair value as trade instruction",
    "alpha as trade instruction",
    "edge as trade instruction",
    "confidence to trade",
    "trade ready",
    "tradable",
    "tradability",
])
def test_forbidden_score_laundering_variants_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["limitations"].append(unsafe)
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", ["position size", "allocation"])
def test_forbidden_position_size_allocation_variants_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["falsification_checks_to_perform"].append(unsafe)
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


@pytest.mark.parametrize("unsafe", ["approve PR", "PR approval", "merge ready"])
def test_forbidden_pr_approval_merge_readiness_variants_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["created_by_operator_note"] = unsafe
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


@pytest.mark.parametrize("unsafe", [
    "credential",
    "private key",
    "API key",
    "secret",
    "passphrase",
    "account endpoint",
    "private endpoint",
    "wallet key",
    "account state",
    "order state",
    "paper state",
    "live state",
    "runtime logs",
])
def test_forbidden_credential_private_runtime_terms_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["evidence_references_to_check"].append(unsafe)
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


@pytest.mark.parametrize("unsafe", [
    "prompt runner",
    "prompt execution",
    "model call",
    "provider",
    "Hermes runtime",
])
def test_forbidden_prompt_model_provider_runtime_terms_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["next_manual_step"] = unsafe
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


@pytest.mark.parametrize("unsafe", ["scheduler", "bot loop", "dashboard"])
def test_forbidden_scheduler_bot_loop_dashboard_terms_are_rejected(unsafe: str) -> None:
    data = _valid_record()
    data["research_question"] = f"Should this use {unsafe}?"
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


@pytest.mark.parametrize("raw_key", [
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
])
def test_raw_free_form_metadata_keys_are_rejected_recursively(raw_key: str) -> None:
    data = _valid_record()
    data["selected_candidate_reference"]["nested"] = {raw_key: "some text"}
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "RAW_METADATA_NOT_ALLOWED" in result.errors


def test_nested_forbidden_keys_are_rejected_recursively() -> None:
    data = _valid_record()
    data["selected_candidate_reference"]["nested"] = {"buy": "hidden key"}
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


def test_nested_forbidden_values_are_rejected_recursively() -> None:
    data = _valid_record()
    data["selected_candidate_reference"]["nested"] = {"note": ["file writer"]}
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}


def test_forbidden_interpretation_flags_cannot_hide_unsafe_content() -> None:
    data = _valid_record()
    data["forbidden_interpretation_flags"]["nested"] = {"note": "buy"}
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_safety_flags_cannot_hide_extra_unsafe_content() -> None:
    data = _valid_record()
    data["safety_flags"]["extra_note"] = "private key"
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_invalid_results_never_echo_unsafe_caller_content() -> None:
    unsafe = "buy sell expected return fair value merge ready private key prompt runner dashboard storage path file writer"
    data = _valid_record()
    data["selected_candidate_reference"]["nested"] = {"note": unsafe}
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    public_values = _all_public_result_values(result)
    for value in public_values:
        assert unsafe not in repr(value)
        assert "private key" not in repr(value).lower()
        assert "file writer" not in repr(value).lower()


def test_assert_helper_raises_neutral_error_only() -> None:
    data = _valid_record()
    data["research_question"] = "buy now with private key"
    with pytest.raises(ValueError) as exc_info:
        assert_record(data)
    message = str(exc_info.value)
    assert "INVALID_CANDIDATE_REVIEW_RESEARCH_QUESTION_RECORD" in message
    assert "FORBIDDEN_CONTENT" in message
    assert "buy now" not in message
    assert "private key" not in message.lower()


def test_build_is_alias_for_validate_behavior() -> None:
    data = _valid_record()
    assert build_record(data) == validate_record(data)


def test_result_dataclass_field_coverage() -> None:
    assert dataclasses.is_dataclass(Result)
    result = build_record(_valid_record())
    assert {f.name for f in dataclasses.fields(Result)} == {
        "is_valid",
        "record",
        "errors",
        "warnings",
        "research_question_type",
        "safety_flags",
    }
    assert len(_all_public_result_values(result)) == len(dataclasses.fields(Result))


def test_module_contains_no_file_io_network_subprocess_cli_env_or_dependency_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "argparse",
        "click",
        "dotenv",
        "http",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "typer",
        "urllib",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_import_roots
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden_import_roots

    forbidden_call_names = {"open"}
    forbidden_attr_roots = {"os", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_call_names
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert node.value.id not in forbidden_attr_roots
            assert node.attr not in {"read", "write", "read_text", "write_text", "write_bytes"}
    assert "if __name__" not in source
    assert "output_path" not in inspect.signature(build_record).parameters


def test_exact_changed_file_inventory_excludes_protected_paths() -> None:
    status = (ROOT / "docs" / "status_entries" / "WP121.md").read_text(encoding="utf-8")
    inventory = status.split("Changed files (16):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "tests/test_hermes_candidate_review_research_question_record.py",
        "docs/status_entries/WP121.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_research_question_record_contract_docs.py",
        "tests/test_architecture_boundaries.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
        "tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py",
        "tests/test_hermes_candidate_review_research_workflow_runbook_docs.py",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
        "tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py",
    ):
        assert path in inventory
    for forbidden in ("tools/", ".github/workflows/", "local_data/", "requirements.txt", "pyproject.toml"):
        assert forbidden not in inventory


def test_project_status_records_wp121_wp122_merged_or_later_review_target() -> None:
    text = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    current_phase = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP122" in current_phase or "WP122" in merged_line
    assert "WP120" in merged_line
    assert "WP121" in merged_line
    assert "WP122" in merged_line
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text


def test_repo_truth_index_registers_new_module_tests_and_status() -> None:
    text = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        "tests/test_hermes_candidate_review_research_question_record.py",
        "docs/status_entries/WP121.md",
    ):
        assert path in text


def test_reviewer_trap_unsafe_strings_in_nested_keys_and_values_fail_closed() -> None:
    unsafe_terms = [
        "buy",
        "sell",
        "expected return",
        "fair value",
        "merge ready",
        "private key",
        "prompt runner",
        "dashboard",
        "storage path",
        "file writer",
    ]
    for term in unsafe_terms:
        data = _valid_record()
        data["selected_candidate_reference"]["nested"] = {term: "safe text"}
        result = build_record(data)
        assert result.is_valid is False
        assert result.record == {}

        data = _valid_record()
        data["selected_candidate_reference"]["nested"] = {"note": term}
        result = build_record(data)
        assert result.is_valid is False
        assert result.record == {}
        assert all(term not in error.lower() for error in result.errors)


def test_one_false_safety_flag_invalidates_record() -> None:
    data = _valid_record()
    data["safety_flags"]["no_runtime_authority"] = False
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


def test_one_false_preflight_flag_invalidates_record() -> None:
    data = _valid_record()
    data["intake_basis"]["source_provenance_explicit"] = False
    result = build_record(data)
    assert result.is_valid is False
    assert result.record == {}
    assert "INVALID_PREFLIGHT_FLAG" in result.errors
