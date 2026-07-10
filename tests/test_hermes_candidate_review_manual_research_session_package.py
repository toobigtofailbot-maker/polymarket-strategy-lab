from __future__ import annotations

import dataclasses
import importlib
import sys
from copy import deepcopy

import pytest

from src.data_layer.hermes_candidate_review_manual_research_session_package import (
    ALLOWED_MANUAL_RESEARCH_SESSION_LABELS,
    REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS,
    REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS,
    HermesCandidateReviewManualResearchSessionPackageResult,
    assert_candidate_review_manual_research_session_package,
    build_candidate_review_manual_research_session_package,
    validate_candidate_review_manual_research_session_package,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH"


def notice() -> str:
    return (
        "Advisory only; manual, local, offline; human review required; not fact without source review; "
        "not a trade signal; not strategy promotion; not paper readiness; not live readiness; "
        "not execution; not risk; not order authority; not PR approval; not merge readiness; "
        "not credential permission; not account access; not private-state access; not Hermes runtime; "
        "not prompt runner; not storage/writer/export authority; not automated task authority; "
        "not report/export authority."
    )


def valid_session() -> dict[str, object]:
    return {
        "session_id": "session-124",
        "source_wp_context": "WP121 through WP123 validated in-memory record chain",
        "research_question_record": {"record_id": "question-1", "summary": "Resolution-source review"},
        "advisory_output_validation_receipt": {"receipt_id": "receipt-1", "summary": "Claims require source review"},
        "human_decision_record": {"decision_id": "decision-1", "summary": "More evidence needed"},
        "follow_up_research_task_records": [{"task_id": "task-1", "summary": "Recheck cited sources manually"}],
        "session_label": "SESSION_READY_FOR_MANUAL_REVIEW_MEMORY",
        "session_summary": "Manual candidate research session assembled in memory",
        "source_references_summary": "Public resolution references reviewed by a human",
        "evidence_gap_summary": "One source date remains to be checked",
        "uncertainty_summary": "Outcome wording remains ambiguous",
        "limitations_summary": "The material remains advisory and human reviewed",
        "falsification_summary": "A conflicting source would reject the claim",
        "operator_next_manual_step": "Recheck the cited resolution source manually",
        "human_review_required": True,
        "non_authority_notice": notice(),
        "safety_flags": {flag: True for flag in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS},
    }


def public_text(result: HermesCandidateReviewManualResearchSessionPackageResult) -> str:
    return repr((result.session_package, result.errors, result.warnings, result.session_label, result.safety_flags))


def test_module_imports_stdlib_only(monkeypatch: pytest.MonkeyPatch) -> None:
    before = set(sys.modules)
    module = importlib.reload(sys.modules[validate_candidate_review_manual_research_session_package.__module__])
    added_roots = {name.split(".")[0] for name in set(sys.modules) - before}
    assert module.__name__.endswith("manual_research_session_package")
    assert not ({"requests", "httpx", "pandas", "pydantic"} & added_roots)


def test_valid_session_and_exact_output_surfaces() -> None:
    result = validate_candidate_review_manual_research_session_package(valid_session())
    assert result.is_valid
    assert set(result.session_package) == set(REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS)
    assert set(result.safety_flags) == set(REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS)
    assert result.errors == result.warnings == ()


@pytest.mark.parametrize("label", sorted(ALLOWED_MANUAL_RESEARCH_SESSION_LABELS))
def test_all_allowed_labels(label: str) -> None:
    data = valid_session()
    data["session_label"] = label
    assert validate_candidate_review_manual_research_session_package(data).is_valid


@pytest.mark.parametrize("field", REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_FIELDS)
def test_missing_required_fields(field: str) -> None:
    data = valid_session()
    del data[field]
    assert validate_candidate_review_manual_research_session_package(data).errors == ("MISSING_REQUIRED_FIELD",)


@pytest.mark.parametrize("field", [
    "session_id", "source_wp_context", "session_summary", "source_references_summary",
    "evidence_gap_summary", "uncertainty_summary", "limitations_summary",
    "falsification_summary", "operator_next_manual_step", "non_authority_notice",
])
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_null_or_blank_scalar_fields(field: str, bad: object) -> None:
    data = valid_session()
    data[field] = bad
    assert not validate_candidate_review_manual_research_session_package(data).is_valid


@pytest.mark.parametrize("bad", [None, "text", [], 1])
def test_unsupported_top_level_shapes(bad: object) -> None:
    result = validate_candidate_review_manual_research_session_package(bad)  # type: ignore[arg-type]
    assert result.errors == ("UNSUPPORTED_INPUT_SHAPE",)


@pytest.mark.parametrize("field,bad", [
    ("research_question_record", []),
    ("advisory_output_validation_receipt", "receipt"),
    ("human_decision_record", None),
    ("follow_up_research_task_records", {}),
    ("follow_up_research_task_records", ["task"]),
])
def test_invalid_nested_shapes(field: str, bad: object) -> None:
    data = valid_session()
    data[field] = bad
    assert not validate_candidate_review_manual_research_session_package(data).is_valid


def test_unknown_label_and_human_review_exact_true() -> None:
    data = valid_session(); data["session_label"] = "UNKNOWN"
    assert validate_candidate_review_manual_research_session_package(data).errors == ("INVALID_SESSION_LABEL",)
    data = valid_session(); data["human_review_required"] = 1
    assert validate_candidate_review_manual_research_session_package(data).errors == ("HUMAN_REVIEW_REQUIRED",)


@pytest.mark.parametrize("mutation", ["missing", "false", "truthy"])
def test_required_safety_flags(mutation: str) -> None:
    data = valid_session(); flags = dict(data["safety_flags"])  # type: ignore[arg-type]
    flag = REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS[0]
    if mutation == "missing": del flags[flag]
    elif mutation == "false": flags[flag] = False
    else: flags[flag] = 1
    data["safety_flags"] = flags
    assert validate_candidate_review_manual_research_session_package(data).errors == ("INVALID_SAFETY_FLAG",)


def test_extra_safety_flags_are_sanitized() -> None:
    data = valid_session(); data["safety_flags"]["benign_extra"] = True  # type: ignore[index]
    result = validate_candidate_review_manual_research_session_package(data)
    assert result.is_valid
    assert set(result.safety_flags) == set(REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS)


@pytest.mark.parametrize("bad_notice", ["", notice() + " This grants permission to proceed."])
def test_notice_missing_or_permission_granting(bad_notice: str) -> None:
    data = valid_session(); data["non_authority_notice"] = bad_notice
    assert not validate_candidate_review_manual_research_session_package(data).is_valid


def test_build_assert_and_dataclass_contract() -> None:
    validated = validate_candidate_review_manual_research_session_package(valid_session())
    assert build_candidate_review_manual_research_session_package(valid_session()) == validated
    assert assert_candidate_review_manual_research_session_package(valid_session()) == validated
    assert [field.name for field in dataclasses.fields(HermesCandidateReviewManualResearchSessionPackageResult)] == [
        "is_valid", "session_package", "errors", "warnings", "session_label", "safety_flags"
    ]


@pytest.mark.parametrize("unsafe", [
    "buy now", "expected return estimate", "strategy promotion", "approve PR",
    "private key", "account state", "paper ready", "runtime logs", "prompt runner",
    "model call", "Hermes runtime", "scheduler", "dashboard", "bot loop",
    "automated task", "parser", "loader", "file writer", "storage path", "exporter",
    "CLI command",
])
def test_forbidden_values_rejected_recursively(unsafe: str) -> None:
    data = valid_session(); data["research_question_record"] = {"safe": {"value": unsafe}}
    assert validate_candidate_review_manual_research_session_package(data).errors == ("FORBIDDEN_CONTENT",)


@pytest.mark.parametrize("target", [
    "research_question_record", "advisory_output_validation_receipt",
    "human_decision_record", "follow_up_research_task_records", "safety_flags",
])
def test_trap_hidden_in_every_nested_surface_fails_closed(target: str) -> None:
    data = valid_session()
    if target == "follow_up_research_task_records": data[target] = [{"safe": TRAP}]
    else: data[target] = {"safe": TRAP}
    result = validate_candidate_review_manual_research_session_package(data)
    assert not result.is_valid and result.session_package == {} and result.warnings == ()
    assert result.session_label is None and result.safety_flags == {}
    assert TRAP not in public_text(result)


@pytest.mark.parametrize("key", ["raw_metadata", "metadata", "custom_fields", "raw_response", "prompt", "free_form"])
def test_raw_metadata_keys_rejected_recursively(key: str) -> None:
    data = valid_session(); data["human_decision_record"] = {"safe": {key: "benign"}}
    assert validate_candidate_review_manual_research_session_package(data).errors == ("RAW_METADATA_NOT_ALLOWED",)


def test_forbidden_nested_key_and_neutral_assert_error() -> None:
    data = valid_session(); data["follow_up_research_task_records"] = [{"storage_path": TRAP}]
    result = validate_candidate_review_manual_research_session_package(data)
    assert public_text(result).find(TRAP) == -1
    with pytest.raises(ValueError) as exc:
        assert_candidate_review_manual_research_session_package(data)
    assert TRAP not in str(exc.value)
    assert "INVALID_CANDIDATE_REVIEW_MANUAL_RESEARCH_SESSION_PACKAGE" in str(exc.value)


def test_input_is_not_mutated() -> None:
    data = valid_session(); original = deepcopy(data)
    validate_candidate_review_manual_research_session_package(data)
    assert data == original
