"""Focused tests for WP122 advisory output validation receipt validation."""

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
MODULE_PATH = (
    ROOT
    / "src"
    / "data_layer"
    / "hermes_candidate_review_advisory_output_validation_receipt.py"
)


def _import_module():
    mod_name = "hermes_candidate_review_advisory_output_validation_receipt"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _import_module()

ALLOWED_LABELS = _mod.ALLOWED_RECEIPT_LABELS
REQUIRED_FIELDS = _mod.REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS
REQUIRED_SAFETY_FLAGS = _mod.REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS
REQUIRED_REVIEW_FLAGS = _mod.REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS
Result = _mod.HermesCandidateReviewAdvisoryOutputValidationReceiptResult
validate_receipt = _mod.validate_candidate_review_advisory_output_validation_receipt
build_receipt = _mod.build_candidate_review_advisory_output_validation_receipt
assert_receipt = _mod.assert_candidate_review_advisory_output_validation_receipt


def _valid_safety_flags() -> dict[str, bool]:
    flags = {flag: True for flag in REQUIRED_SAFETY_FLAGS}
    flags.update({flag: True for flag in REQUIRED_REVIEW_FLAGS})
    return flags


def _valid_notice() -> str:
    return (
        "Advisory only manual local offline receipt; human review required. "
        "It is not fact without source review, not a trade signal, not strategy "
        "promotion, not paper readiness, not live readiness, not execution "
        "authority, not risk authority, not order authority, not PR approval, "
        "not merge readiness, not credential permission, not account access, "
        "not private-state access, not Hermes runtime authority, not prompt "
        "runner authority, and not storage/writer/export authority."
    )


def _valid_receipt(
    receipt_label: str = "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE",
) -> dict[str, Any]:
    return {
        "receipt_id": "aovr-001",
        "source_wp_context": {
            "research_question_wp": "WP121",
            "receipt_wp": "WP122",
        },
        "source_research_question_record_reference": {
            "record_id": "rq-001",
            "source_module": "hermes_candidate_review_research_question_record",
        },
        "advisory_output_reference": {
            "artifact_id": "advisory-output-001",
            "operator_reference": "manual-reviewed-reference",
        },
        "receipt_label": receipt_label,
        "source_references_checked": ["source-reference-001"],
        "unsupported_claims": ["No unsupported claims accepted."],
        "uncertainty_review": ["Uncertainty explicitly reviewed."],
        "limitations_review": ["Limitations explicitly reviewed."],
        "missing_data_review": ["Missing data explicitly reviewed."],
        "falsification_review": ["Falsification checks explicitly reviewed."],
        "human_review_notes": ["Human reviewer performed source review."],
        "follow_up_research_tasks": ["Manually inspect one additional source."],
        "forbidden_interpretation_flags": {
            "not_a_signal": True,
            "not_authority": True,
        },
        "human_review_required": True,
        "non_authority_notice": _valid_notice(),
        "safety_flags": _valid_safety_flags(),
    }


def _all_public_result_values(result: Result) -> list[object]:
    return [
        result.is_valid,
        result.receipt,
        result.errors,
        result.warnings,
        result.receipt_label,
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


def test_valid_minimal_receipt_builds_successfully() -> None:
    result = build_receipt(_valid_receipt())
    assert result.is_valid is True
    assert result.receipt != {}
    assert result.errors == ()
    assert result.warnings == ()
    assert result.receipt_label == "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE"


@pytest.mark.parametrize("receipt_label", sorted(ALLOWED_LABELS))
def test_each_allowed_receipt_label_is_accepted(receipt_label: str) -> None:
    result = build_receipt(_valid_receipt(receipt_label))
    assert result.is_valid is True
    assert result.receipt_label == receipt_label


def test_sanitized_safety_flags_are_exact_required_safety_flags_only() -> None:
    data = _valid_receipt()
    data["safety_flags"]["unexpected_flag"] = True
    data["safety_flags"]["unsupported_claims_identified"] = True
    result = build_receipt(data)
    assert result.is_valid is True
    assert result.safety_flags == {flag: True for flag in REQUIRED_SAFETY_FLAGS}
    assert result.receipt["safety_flags"] == result.safety_flags
    assert "unexpected_flag" not in result.safety_flags
    assert "unsupported_claims_identified" not in result.safety_flags


def test_build_is_alias_for_validate_behavior() -> None:
    data = _valid_receipt()
    assert build_receipt(data) == validate_receipt(data)


def test_assert_helper_returns_result_for_valid_input() -> None:
    result = assert_receipt(_valid_receipt())
    assert result.is_valid is True
    assert result.receipt_label == "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE"


def test_result_dataclass_field_coverage() -> None:
    assert dataclasses.is_dataclass(Result)
    result = build_receipt(_valid_receipt())
    assert {f.name for f in dataclasses.fields(Result)} == {
        "is_valid",
        "receipt",
        "errors",
        "warnings",
        "receipt_label",
        "safety_flags",
    }
    assert len(_all_public_result_values(result)) == len(dataclasses.fields(Result))


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_all_required_fields_are_enforced(field: str) -> None:
    data = _valid_receipt()
    del data[field]
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "MISSING_REQUIRED_FIELD" in result.errors


@pytest.mark.parametrize("flag", REQUIRED_SAFETY_FLAGS)
def test_required_safety_flags_must_be_present_and_true(flag: str) -> None:
    data = _valid_receipt()
    del data["safety_flags"][flag]
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "INVALID_SAFETY_FLAG" in result.errors

    data = _valid_receipt()
    data["safety_flags"][flag] = False
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "INVALID_SAFETY_FLAG" in result.errors


@pytest.mark.parametrize("flag", REQUIRED_REVIEW_FLAGS)
def test_required_review_flags_must_be_present_and_true(flag: str) -> None:
    expected_error = (
        "INVALID_SAFETY_FLAG"
        if flag in REQUIRED_SAFETY_FLAGS
        else "INVALID_REVIEW_FLAG"
    )
    data = _valid_receipt()
    del data["safety_flags"][flag]
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert expected_error in result.errors

    data = _valid_receipt()
    data["safety_flags"][flag] = False
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert expected_error in result.errors


def test_human_review_required_must_be_exactly_true() -> None:
    data = _valid_receipt()
    data["human_review_required"] = False
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "HUMAN_REVIEW_REQUIRED" in result.errors


def test_unknown_receipt_label_is_rejected() -> None:
    data = _valid_receipt("UNKNOWN_RECEIPT_LABEL")
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "INVALID_RECEIPT_LABEL" in result.errors


def test_non_authority_notice_is_required() -> None:
    data = _valid_receipt()
    data["non_authority_notice"] = ""
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "INVALID_NON_AUTHORITY_NOTICE" in result.errors


def test_non_authority_notice_cannot_grant_permission() -> None:
    data = _valid_receipt()
    data["non_authority_notice"] = (
        "Advisory manual local offline note that grants permission to execute "
        "and says paper ready, live ready, merge ready, and PR approved."
    )
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
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
    "position size",
    "allocation",
])
def test_forbidden_trade_action_variants_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["human_review_notes"].append(f"hidden {unsafe} request")
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "expected return",
    "fair value",
    "alpha",
    "edge",
    "confidence to trade",
    "trade ready",
    "tradable",
    "tradability",
    "paper ready",
    "live ready",
    "deployment ready",
])
def test_forbidden_score_laundering_variants_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["unsupported_claims"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "strategy promotion",
    "approve PR",
    "PR approval",
    "merge ready",
    "risk override",
    "execution authority",
    "implementation approval",
])
def test_forbidden_authority_variants_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["limitations_review"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "credential",
    "private key",
    "API key",
    "secret",
    "passphrase",
    "wallet key",
    "account endpoint",
    "private endpoint",
    "account state",
    "order state",
    "paper state",
    "live state",
    "runtime logs",
])
def test_forbidden_credential_private_runtime_terms_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["source_references_checked"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "prompt runner",
    "prompt execution",
    "model call",
    "provider",
    "Hermes runtime",
])
def test_forbidden_prompt_model_provider_runtime_terms_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["missing_data_review"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", ["scheduler", "bot loop", "daemon", "network poller", "dashboard"])
def test_forbidden_scheduler_bot_loop_dashboard_terms_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["falsification_review"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


@pytest.mark.parametrize("unsafe", [
    "file writer",
    "storage path",
    "parser",
    "loader",
    "report writer",
    "exporter",
    "CLI command",
])
def test_forbidden_parser_loader_writer_storage_export_cli_terms_are_rejected(unsafe: str) -> None:
    data = _valid_receipt()
    data["follow_up_research_tasks"].append(unsafe)
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_nested_forbidden_keys_are_rejected_recursively() -> None:
    data = _valid_receipt()
    data["advisory_output_reference"]["nested"] = {"buy": "hidden key"}
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_nested_forbidden_values_are_rejected_recursively() -> None:
    data = _valid_receipt()
    data["advisory_output_reference"]["nested"] = {"note": ["file writer"]}
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_forbidden_interpretation_flags_cannot_hide_unsafe_content() -> None:
    data = _valid_receipt()
    data["forbidden_interpretation_flags"]["nested"] = {"note": "buy"}
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_safety_flags_cannot_hide_extra_unsafe_content() -> None:
    data = _valid_receipt()
    data["safety_flags"]["extra_note"] = "private key"
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_unsupported_claims_cannot_include_trading_readiness_authority_wording() -> None:
    data = _valid_receipt()
    data["unsupported_claims"].append("This is trade ready and merge ready.")
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


def test_follow_up_research_tasks_cannot_include_implementation_execution_order_wording() -> None:
    data = _valid_receipt()
    data["follow_up_research_tasks"].append("Implementation approval to execute order.")
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "FORBIDDEN_CONTENT" in result.errors


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
    data = _valid_receipt()
    data["advisory_output_reference"]["nested"] = {raw_key: "some text"}
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    assert "RAW_METADATA_NOT_ALLOWED" in result.errors


def test_invalid_results_never_echo_unsafe_caller_content() -> None:
    unsafe = "buy sell expected return fair value merge ready private key prompt runner dashboard storage path file writer"
    data = _valid_receipt()
    data["advisory_output_reference"]["nested"] = {"note": unsafe}
    result = build_receipt(data)
    assert result.is_valid is False
    assert result.receipt == {}
    for value in _all_public_result_values(result):
        assert unsafe not in repr(value)
        assert "private key" not in repr(value).lower()
        assert "file writer" not in repr(value).lower()


def test_assert_helper_raises_neutral_error_only() -> None:
    data = _valid_receipt()
    data["human_review_notes"] = ["buy now with private key"]
    with pytest.raises(ValueError) as exc_info:
        assert_receipt(data)
    message = str(exc_info.value)
    assert "INVALID_CANDIDATE_REVIEW_ADVISORY_OUTPUT_VALIDATION_RECEIPT" in message
    assert "FORBIDDEN_CONTENT" in message
    assert "buy now" not in message
    assert "private key" not in message.lower()


def test_errors_are_neutral_codes_only_for_precedence_cases() -> None:
    cases = [
        (["not-a-mapping"], "UNSUPPORTED_INPUT_SHAPE"),
        ({**_valid_receipt(), "raw_metadata": "buy"}, "RAW_METADATA_NOT_ALLOWED"),
        ({**_valid_receipt(), "receipt_label": "buy"}, "FORBIDDEN_CONTENT"),
    ]
    for payload, code in cases:
        result = build_receipt(payload)
        assert result.is_valid is False
        assert result.receipt == {}
        assert result.errors == (code,)
        assert all(error.isupper() and " " not in error for error in result.errors)


def test_validation_precedence_table_stops_at_first_safety_category() -> None:
    result = build_receipt(["not-a-mapping"])
    assert result.errors == ("UNSUPPORTED_INPUT_SHAPE",)

    data = _valid_receipt()
    data["raw_metadata"] = "buy"
    result = build_receipt(data)
    assert result.errors == ("RAW_METADATA_NOT_ALLOWED",)

    data = _valid_receipt()
    data["source_references_checked"].append("buy")
    del data["receipt_id"]
    result = build_receipt(data)
    assert result.errors == ("FORBIDDEN_CONTENT",)

    data = _valid_receipt()
    del data["receipt_id"]
    del data["safety_flags"]["advisory_only"]
    result = build_receipt(data)
    assert result.errors == ("MISSING_REQUIRED_FIELD",)

    data = _valid_receipt()
    del data["safety_flags"]["advisory_only"]
    data["safety_flags"]["source_references_checked"] = False
    result = build_receipt(data)
    assert result.errors == ("INVALID_SAFETY_FLAG",)

    data = _valid_receipt()
    data["safety_flags"]["source_references_checked"] = False
    data["receipt_label"] = "UNKNOWN_RECEIPT_LABEL"
    result = build_receipt(data)
    assert result.errors == ("INVALID_REVIEW_FLAG",)

    data = _valid_receipt()
    data["receipt_label"] = "UNKNOWN_RECEIPT_LABEL"
    data["human_review_required"] = False
    result = build_receipt(data)
    assert result.errors == ("INVALID_RECEIPT_LABEL",)

    data = _valid_receipt()
    data["human_review_required"] = False
    data["non_authority_notice"] = ""
    result = build_receipt(data)
    assert result.errors == ("HUMAN_REVIEW_REQUIRED",)


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
    assert "output_path" not in inspect.signature(build_receipt).parameters


def test_project_status_records_wp121_merged_and_wp122_current_review_target() -> None:
    text = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    current_phase = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP122" in current_phase
    assert "WP121" in merged_line
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_REVIEW_TARGET" in text


def test_project_status_preserves_protected_boundary_statuses() -> None:
    text = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
    ):
        assert phrase in text


def test_repo_truth_index_registers_new_module_tests_and_status() -> None:
    text = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        "tests/test_hermes_candidate_review_advisory_output_validation_receipt.py",
        "docs/status_entries/WP122.md",
    ):
        assert path in text
