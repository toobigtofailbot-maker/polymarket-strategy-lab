"""Focused tests for WP123 human decision and follow-up task records."""

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
    / "hermes_candidate_review_human_decision_follow_up_record.py"
)
TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH"


def _import_module():
    mod_name = "hermes_candidate_review_human_decision_follow_up_record"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _import_module()

ALLOWED_DECISION_LABELS = _mod.ALLOWED_HUMAN_DECISION_LABELS
ALLOWED_TASK_LABELS = _mod.ALLOWED_FOLLOW_UP_TASK_LABELS
REQUIRED_DECISION_FIELDS = _mod.REQUIRED_HUMAN_DECISION_RECORD_FIELDS
REQUIRED_TASK_FIELDS = _mod.REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS
REQUIRED_SAFETY_FLAGS = _mod.REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS
DecisionResult = _mod.HermesCandidateReviewHumanDecisionRecordResult
TaskResult = _mod.HermesCandidateReviewFollowUpResearchTaskRecordResult
validate_decision = _mod.validate_candidate_review_human_decision_record
build_decision = _mod.build_candidate_review_human_decision_record
assert_decision = _mod.assert_candidate_review_human_decision_record
validate_task = _mod.validate_candidate_review_follow_up_research_task_record
build_task = _mod.build_candidate_review_follow_up_research_task_record
assert_task = _mod.assert_candidate_review_follow_up_research_task_record


def _valid_safety_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_SAFETY_FLAGS}


def _valid_notice() -> str:
    return (
        "Advisory only manual local offline record; human review required. "
        "It is not fact without source review, not a trade signal, not strategy "
        "promotion, not paper readiness, not live readiness, not execution "
        "authority, not risk authority, not order authority, not PR approval, "
        "not merge readiness, not credential permission, not account access, "
        "not private-state access, not Hermes runtime authority, not prompt "
        "runner authority, not storage/writer/export authority, and not "
        "automated task authority."
    )


def _valid_decision(
    decision_label: str = "NEEDS_MORE_EVIDENCE",
) -> dict[str, Any]:
    return {
        "decision_id": "decision-001",
        "source_wp_context": {"question_wp": "WP121", "receipt_wp": "WP122"},
        "source_research_question_record_reference": {
            "record_id": "research-question-001",
            "source_module": "hermes_candidate_review_research_question_record",
        },
        "source_advisory_output_validation_receipt_reference": {
            "receipt_id": "receipt-001",
            "source_module": "hermes_candidate_review_advisory_output_validation_receipt",
        },
        "decision_label": decision_label,
        "decision_basis": ["Reviewer needs one additional source check."],
        "accepted_findings": ["Source comparison was internally consistent."],
        "rejected_findings": ["One unsupported advisory claim was excluded."],
        "unresolved_questions": ["One source detail remains unresolved."],
        "evidence_references_relied_on": ["public-source-reference-001"],
        "uncertainty_notes": ["Uncertainty remains bounded to source freshness."],
        "limitations": ["Manual review covers only supplied references."],
        "falsification_checks_completed": ["Compared claim against source reference."],
        "follow_up_research_tasks": ["Manually recheck the source reference."],
        "human_review_required": True,
        "created_by_operator_note": "Operator recorded after manual source review.",
        "non_authority_notice": _valid_notice(),
        "safety_flags": _valid_safety_flags(),
    }


def _valid_task(
    task_label: str = "SOURCE_RECHECK_TASK",
) -> dict[str, Any]:
    return {
        "task_id": "task-001",
        "source_wp_context": {"decision_wp": "WP123"},
        "source_human_decision_reference": {"decision_id": "decision-001"},
        "task_label": task_label,
        "task_question": "Which cited source best supports the reviewed claim?",
        "evidence_to_check": ["public-source-reference-001"],
        "source_references_to_revisit": ["public-source-reference-002"],
        "missing_data_to_resolve": ["Publication timestamp for source reference."],
        "uncertainty_to_reduce": ["Whether source reference is current enough."],
        "falsification_check_to_perform": ["Compare claim against source text."],
        "blocking_reason": "Human source review is still incomplete.",
        "next_manual_step": "Open the source manually and record the finding.",
        "human_review_required": True,
        "created_by_operator_note": "Operator created a manual follow-up item.",
        "non_authority_notice": _valid_notice(),
        "safety_flags": _valid_safety_flags(),
    }


def _decision_values(result: DecisionResult) -> list[object]:
    return [
        result.is_valid,
        result.decision_record,
        result.errors,
        result.warnings,
        result.decision_label,
        result.safety_flags,
    ]


def _task_values(result: TaskResult) -> list[object]:
    return [
        result.is_valid,
        result.follow_up_task_record,
        result.errors,
        result.warnings,
        result.task_label,
        result.safety_flags,
    ]


def _all_public_text(values: list[object]) -> str:
    return " ".join(repr(value) for value in values)


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


def test_valid_decision_record_is_accepted() -> None:
    result = build_decision(_valid_decision())
    assert result.is_valid is True
    assert result.decision_record != {}
    assert result.errors == ()
    assert result.warnings == ()
    assert result.decision_label == "NEEDS_MORE_EVIDENCE"


def test_valid_follow_up_task_record_is_accepted() -> None:
    result = build_task(_valid_task())
    assert result.is_valid is True
    assert result.follow_up_task_record != {}
    assert result.errors == ()
    assert result.warnings == ()
    assert result.task_label == "SOURCE_RECHECK_TASK"


@pytest.mark.parametrize("decision_label", sorted(ALLOWED_DECISION_LABELS))
def test_each_allowed_decision_label_is_accepted(decision_label: str) -> None:
    result = build_decision(_valid_decision(decision_label))
    assert result.is_valid is True
    assert result.decision_label == decision_label


@pytest.mark.parametrize("task_label", sorted(ALLOWED_TASK_LABELS))
def test_each_allowed_follow_up_task_label_is_accepted(task_label: str) -> None:
    result = build_task(_valid_task(task_label))
    assert result.is_valid is True
    assert result.task_label == task_label


def test_unknown_decision_label_is_rejected() -> None:
    result = build_decision(_valid_decision("UNKNOWN_DECISION_LABEL"))
    assert result.is_valid is False
    assert result.decision_record == {}
    assert result.errors == ("INVALID_DECISION_LABEL",)


def test_unknown_task_label_is_rejected() -> None:
    result = build_task(_valid_task("UNKNOWN_TASK_LABEL"))
    assert result.is_valid is False
    assert result.follow_up_task_record == {}
    assert result.errors == ("INVALID_TASK_LABEL",)


@pytest.mark.parametrize("field", REQUIRED_DECISION_FIELDS)
def test_every_required_decision_field_is_enforced(field: str) -> None:
    data = _valid_decision()
    del data[field]
    result = build_decision(data)
    assert result.is_valid is False
    assert result.decision_record == {}
    assert "MISSING_REQUIRED_FIELD" in result.errors


@pytest.mark.parametrize("field", REQUIRED_TASK_FIELDS)
def test_every_required_follow_up_task_field_is_enforced(field: str) -> None:
    data = _valid_task()
    del data[field]
    result = build_task(data)
    assert result.is_valid is False
    assert result.follow_up_task_record == {}
    assert "MISSING_REQUIRED_FIELD" in result.errors


def test_null_required_value_is_rejected() -> None:
    decision = _valid_decision()
    decision["decision_id"] = None
    assert build_decision(decision).errors == ("INVALID_REQUIRED_FIELD",)
    task = _valid_task()
    task["task_id"] = None
    assert build_task(task).errors == ("INVALID_REQUIRED_FIELD",)


def test_unsupported_input_shape_is_rejected() -> None:
    assert build_decision(["not-a-mapping"]).errors == ("UNSUPPORTED_INPUT_SHAPE",)
    assert build_task(["not-a-mapping"]).errors == ("UNSUPPORTED_INPUT_SHAPE",)


@pytest.mark.parametrize("flag", REQUIRED_SAFETY_FLAGS)
def test_all_required_safety_flags_must_be_present_and_true(flag: str) -> None:
    decision = _valid_decision()
    del decision["safety_flags"][flag]
    assert build_decision(decision).errors == ("INVALID_SAFETY_FLAG",)
    decision = _valid_decision()
    decision["safety_flags"][flag] = False
    assert build_decision(decision).errors == ("INVALID_SAFETY_FLAG",)

    task = _valid_task()
    del task["safety_flags"][flag]
    assert build_task(task).errors == ("INVALID_SAFETY_FLAG",)
    task = _valid_task()
    task["safety_flags"][flag] = False
    assert build_task(task).errors == ("INVALID_SAFETY_FLAG",)


def test_valid_outputs_sanitize_safety_flags_to_exact_required_flags_only() -> None:
    decision = _valid_decision()
    decision["safety_flags"]["unexpected_extra"] = True
    decision_result = build_decision(decision)
    assert decision_result.is_valid is True
    assert decision_result.safety_flags == _valid_safety_flags()
    assert decision_result.decision_record["safety_flags"] == _valid_safety_flags()

    task = _valid_task()
    task["safety_flags"]["unexpected_extra"] = True
    task_result = build_task(task)
    assert task_result.is_valid is True
    assert task_result.safety_flags == _valid_safety_flags()
    assert task_result.follow_up_task_record["safety_flags"] == _valid_safety_flags()


def test_human_review_required_must_be_exactly_true() -> None:
    decision = _valid_decision()
    decision["human_review_required"] = False
    assert build_decision(decision).errors == ("HUMAN_REVIEW_REQUIRED",)
    task = _valid_task()
    task["human_review_required"] = "true"
    assert build_task(task).errors == ("HUMAN_REVIEW_REQUIRED",)


def test_non_authority_notice_is_required() -> None:
    decision = _valid_decision()
    decision["non_authority_notice"] = ""
    assert build_decision(decision).errors == ("INVALID_REQUIRED_FIELD",)
    task = _valid_task()
    task["non_authority_notice"] = ""
    assert build_task(task).errors == ("INVALID_REQUIRED_FIELD",)


def test_non_authority_notice_cannot_grant_permission() -> None:
    decision = _valid_decision()
    decision["non_authority_notice"] = (
        "Advisory manual local offline note that grants permission to execute "
        "and says paper ready, live ready, merge ready, PR approved, and automated task."
    )
    assert build_decision(decision).errors == ("INVALID_NON_AUTHORITY_NOTICE",)

    task = _valid_task()
    task["non_authority_notice"] = "This notice authorizes deployment ready work."
    assert build_task(task).errors == ("INVALID_NON_AUTHORITY_NOTICE",)


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
def test_trade_action_variants_are_rejected(unsafe: str) -> None:
    decision = _valid_decision()
    decision["decision_basis"].append(f"hidden {unsafe} language")
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["task_question"] = f"Should this become {unsafe} language?"
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


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
def test_score_edge_laundering_variants_are_rejected(unsafe: str) -> None:
    decision = _valid_decision()
    decision["accepted_findings"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["evidence_to_check"].append(unsafe)
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


@pytest.mark.parametrize("unsafe", [
    "strategy promotion",
    "strategy promoted",
    "approve PR",
    "PR approval",
    "merge ready",
    "risk override",
    "execution authority",
    "implementation approval",
])
def test_readiness_authority_variants_are_rejected(unsafe: str) -> None:
    decision = _valid_decision()
    decision["rejected_findings"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["missing_data_to_resolve"].append(unsafe)
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


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
def test_credential_private_account_order_paper_live_runtime_variants_are_rejected(
    unsafe: str,
) -> None:
    decision = _valid_decision()
    decision["unresolved_questions"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["source_references_to_revisit"].append(unsafe)
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


@pytest.mark.parametrize("unsafe", [
    "prompt runner",
    "prompt execution",
    "model call",
    "provider",
    "Hermes runtime",
])
def test_prompt_model_provider_hermes_runtime_variants_are_rejected(unsafe: str) -> None:
    decision = _valid_decision()
    decision["evidence_references_relied_on"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["uncertainty_to_reduce"].append(unsafe)
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


@pytest.mark.parametrize("unsafe", [
    "scheduler",
    "bot loop",
    "daemon",
    "network poller",
    "dashboard",
    "automated task",
    "auto task",
    "background task",
])
def test_scheduler_dashboard_bot_loop_automation_variants_are_rejected(
    unsafe: str,
) -> None:
    decision = _valid_decision()
    decision["follow_up_research_tasks"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["next_manual_step"] = unsafe
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


@pytest.mark.parametrize("unsafe", [
    "file writer",
    "storage path",
    "parser",
    "loader",
    "report writer",
    "exporter",
    "CLI command",
])
def test_parser_loader_writer_storage_export_cli_variants_are_rejected(
    unsafe: str,
) -> None:
    decision = _valid_decision()
    decision["limitations"].append(unsafe)
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["falsification_check_to_perform"].append(unsafe)
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


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
    decision = _valid_decision()
    decision["source_wp_context"]["nested"] = {raw_key: "safe text"}
    assert build_decision(decision).errors == ("RAW_METADATA_NOT_ALLOWED",)
    task = _valid_task()
    task["source_human_decision_reference"]["nested"] = {raw_key: "safe text"}
    assert build_task(task).errors == ("RAW_METADATA_NOT_ALLOWED",)


def test_nested_forbidden_keys_are_rejected_recursively() -> None:
    decision = _valid_decision()
    decision["source_wp_context"]["nested"] = {"storage_path": "hidden key"}
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["source_human_decision_reference"]["nested"] = {"private_key": "hidden key"}
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


def test_nested_forbidden_values_are_rejected_recursively() -> None:
    decision = _valid_decision()
    decision["source_wp_context"]["nested"] = {"note": ["file writer"]}
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["source_human_decision_reference"]["nested"] = {"note": ["prompt runner"]}
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


def test_safety_flags_cannot_hide_unsafe_extra_content() -> None:
    decision = _valid_decision()
    decision["safety_flags"]["extra_note"] = "private key"
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["safety_flags"]["automated_task"] = True
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


def test_forbidden_interpretation_flags_cannot_hide_unsafe_content() -> None:
    decision = _valid_decision()
    decision["forbidden_interpretation_flags"] = {"note": "buy"}
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["forbidden_interpretation_flags"] = {"note": "storage path"}
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


def test_decision_basis_cannot_hide_trade_readiness_authority_language() -> None:
    decision = _valid_decision()
    decision["decision_basis"].append("This is trade ready and merge ready.")
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)


def test_follow_up_research_tasks_cannot_hide_automation_storage_export_runtime_language() -> None:
    decision = _valid_decision()
    decision["follow_up_research_tasks"].append("Create automated task with storage path.")
    assert build_decision(decision).errors == ("FORBIDDEN_CONTENT",)
    task = _valid_task()
    task["next_manual_step"] = "Use report writer through Hermes runtime."
    assert build_task(task).errors == ("FORBIDDEN_CONTENT",)


def test_invalid_results_never_echo_unsafe_content() -> None:
    decision = _valid_decision()
    decision["source_wp_context"]["trap"] = TRAP
    decision_result = build_decision(decision)
    assert decision_result.is_valid is False
    for surface in _decision_values(decision_result):
        assert TRAP not in repr(surface)
    assert TRAP not in str(decision_result)

    task = _valid_task()
    task["source_human_decision_reference"]["trap"] = TRAP
    task_result = build_task(task)
    assert task_result.is_valid is False
    for surface in _task_values(task_result):
        assert TRAP not in repr(surface)
    assert TRAP not in str(task_result)


def test_assert_helpers_raise_neutral_errors_only() -> None:
    decision = _valid_decision()
    decision["decision_basis"].append(TRAP)
    with pytest.raises(ValueError) as decision_exc:
        assert_decision(decision)
    decision_message = str(decision_exc.value)
    assert "INVALID_CANDIDATE_REVIEW_HUMAN_DECISION_RECORD" in decision_message
    assert "FORBIDDEN_CONTENT" in decision_message
    assert TRAP not in decision_message

    task = _valid_task()
    task["task_question"] = TRAP
    with pytest.raises(ValueError) as task_exc:
        assert_task(task)
    task_message = str(task_exc.value)
    assert "INVALID_CANDIDATE_REVIEW_FOLLOW_UP_RESEARCH_TASK_RECORD" in task_message
    assert "FORBIDDEN_CONTENT" in task_message
    assert TRAP not in task_message


def test_result_dataclass_field_coverage() -> None:
    assert dataclasses.is_dataclass(DecisionResult)
    assert dataclasses.is_dataclass(TaskResult)
    assert {f.name for f in dataclasses.fields(DecisionResult)} == {
        "is_valid",
        "decision_record",
        "errors",
        "warnings",
        "decision_label",
        "safety_flags",
    }
    assert {f.name for f in dataclasses.fields(TaskResult)} == {
        "is_valid",
        "follow_up_task_record",
        "errors",
        "warnings",
        "task_label",
        "safety_flags",
    }
    assert len(_decision_values(build_decision(_valid_decision()))) == len(
        dataclasses.fields(DecisionResult)
    )
    assert len(_task_values(build_task(_valid_task()))) == len(
        dataclasses.fields(TaskResult)
    )


def test_build_aliases_validate_behavior() -> None:
    decision = _valid_decision()
    assert build_decision(decision) == validate_decision(decision)
    task = _valid_task()
    assert build_task(task) == validate_task(task)


def test_assert_helpers_return_result_for_valid_input() -> None:
    assert assert_decision(_valid_decision()).is_valid is True
    assert assert_task(_valid_task()).is_valid is True


def test_no_file_network_subprocess_env_dependency_imports_or_calls() -> None:
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
    forbidden_attr_roots = {"os", "subprocess", "socket", "requests"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_call_names
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert node.value.id not in forbidden_attr_roots
            assert node.attr not in {"read", "write", "read_text", "write_text", "write_bytes"}
    assert "if __name__" not in source
    assert "output_path" not in inspect.signature(build_decision).parameters
    assert "output_path" not in inspect.signature(build_task).parameters


def test_module_docstring_records_boundary_exclusions() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for phrase in (
        "No file I/O",
        "No network",
        "No CLI",
        "No storage",
        "No Hermes runtime",
        "No prompt execution",
        "No credentials",
        "paper/live/execution/risk/order",
    ):
        assert phrase in source


def test_public_result_surfaces_are_fail_closed_for_invalid_inputs() -> None:
    decision = build_decision({"decision_id": TRAP})
    assert decision.is_valid is False
    assert decision.decision_record == {}
    assert decision.warnings == ()
    assert decision.decision_label is None
    assert decision.safety_flags == {}
    assert TRAP not in _all_public_text(_decision_values(decision))

    task = build_task({"task_id": TRAP})
    assert task.is_valid is False
    assert task.follow_up_task_record == {}
    assert task.warnings == ()
    assert task.task_label is None
    assert task.safety_flags == {}
    assert TRAP not in _all_public_text(_task_values(task))


def test_project_status_records_wp122_merged_and_wp123_current_review_target() -> None:
    text = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    current_phase = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP123" in current_phase
    assert "WP122" in merged_line
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_REVIEW_TARGET" in text


def test_repo_truth_index_registers_wp123_surfaces() -> None:
    text = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    for path in (
        "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
        "tests/test_hermes_candidate_review_human_decision_follow_up_record.py",
        "docs/status_entries/WP123.md",
    ):
        assert path in text
