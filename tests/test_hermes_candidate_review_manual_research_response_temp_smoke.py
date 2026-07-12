import ast
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_research_response import (
    ALLOWED_RESEARCH_COMPLETION_LABELS,
    ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS,
    ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS,
    REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS,
    REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS,
    assert_candidate_review_manual_research_response,
    build_candidate_review_manual_research_response,
    validate_candidate_review_manual_research_response,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MNEMONIC_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_SCORING_MODEL_CALL_PROBABILITY_ESTIMATE"
SCALARS = (
    "response_id", "source_wp_context", "source_request_reference", "source_briefing_packet_reference",
    "selected_candidate_reference", "research_question", "research_question_type", "question_restatement",
    "source_summary", "resolution_rule_analysis", "operator_review_notes", "operator_next_manual_step",
    "reviewer_acknowledgement", "created_by_operator_note", "non_authority_notice",
)
SEQUENCES = (
    "evidence_for", "evidence_against", "source_conflicts", "uncertainties", "known_missing_data",
    "falsification_checks_performed", "limitations", "what_would_change_the_conclusion",
    "cited_source_references", "source_assessment_labels", "completion_labels", "response_sections",
)


def _safety_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}


def _notice() -> str:
    return "; ".join((
        "advisory only", "manual", "local", "offline", "read only", "human review required",
        "explicit caller content only", "response contract only", "not prompt generation",
        "not prompt execution", "not model or provider", "not Hermes", "not tool selection",
        "not tool invocation", "not network or API", "not source fetching", "not source verification",
        "not citation verification", "not market data ingestion", "not discovery automation",
        "not automated selection", "not scoring or ranking", "not priority calculation",
        "not recommendation", "not probability estimation", "not factual correctness",
        "not factual conclusion", "not strategy", "not execution", "not risk", "not credentials",
        "not paper or live", "not strategy promotion", "not PR approval", "not storage or writer",
        "not export or report", "not CLI", "not scheduler or background task",
    ))


def _record() -> dict[str, object]:
    return {
        "response_id": "synthetic-response-134", "source_wp_context": "WP134 synthetic exercise",
        "source_request_reference": "synthetic-request-reference", "source_briefing_packet_reference": "synthetic-briefing-reference",
        "selected_candidate_reference": "synthetic-candidate-reference", "response_label": "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "research_question": "What synthetic public condition would resolve this exercise?", "research_question_type": "synthetic resolution rules",
        "question_restatement": "Inspect the synthetic condition.", "source_summary": "Caller recorded synthetic source text.",
        "resolution_rule_analysis": "Caller recorded synthetic rule analysis.", "evidence_for": ["Synthetic item A supports the condition."],
        "evidence_against": ["Synthetic item B disputes the condition."], "source_conflicts": ["Synthetic items use different dates."],
        "uncertainties": ["A synthetic update remains unavailable."], "known_missing_data": ["A synthetic bulletin is absent."],
        "falsification_checks_performed": ["Compared synthetic rule wording."], "limitations": ["Only synthetic material was considered."],
        "what_would_change_the_conclusion": ["A contrary synthetic bulletin."], "operator_review_notes": "Human inspection remains required.",
        "cited_source_references": ["synthetic-source-reference-a"], "source_assessment_labels": ["PRIMARY_SOURCE_REVIEWED"],
        "completion_labels": ["REQUIRED_SECTIONS_PRESENT"], "response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "operator_next_manual_step": "Perform human inspection.", "reviewer_acknowledgement": "Human inspection remains pending.",
        "human_review_required": True, "created_by_operator_note": "Explicit synthetic caller fixture.",
        "non_authority_notice": _notice(), "safety_flags": _safety_flags(),
    }


def test_positive_manual_response_is_sanitized_in_memory_and_tmp_empty(tmp_path: Path) -> None:
    record = _record()
    result = build_candidate_review_manual_research_response(record)
    assert result.is_valid and not result.errors and not result.warnings
    assert set(result.research_response) == set(REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS)
    assert result.research_response["evidence_for"] == record["evidence_for"]
    assert result.response_label == record["response_label"]
    assert result.source_assessment_labels == tuple(record["source_assessment_labels"])
    assert result.completion_labels == tuple(record["completion_labels"])
    assert result.response_sections == tuple(record["response_sections"])
    assert result.safety_flags == _safety_flags()
    assert result.research_response["human_review_required"] is True
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field", REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS)
def test_missing_fields_fail_neutrally(field: str) -> None:
    record = _record(); record.pop(field)
    result = validate_candidate_review_manual_research_response(record)
    assert not result.is_valid and result.research_response == {} and TRAP not in repr(result)


@pytest.mark.parametrize("field", SCALARS)
@pytest.mark.parametrize("bad", [1, True, {}, [], {"nested_response": "unsafe"}])
def test_scalar_wrong_shapes_fail_neutrally(field: str, bad: object) -> None:
    record = _record(); record[field] = bad
    result = validate_candidate_review_manual_research_response(record)
    assert not result.is_valid and result.research_response == {}


@pytest.mark.parametrize("field", SEQUENCES)
@pytest.mark.parametrize("bad", [[], "scalar", {}, [{"nested": "unsafe"}]])
def test_sequence_wrong_shapes_fail_neutrally(field: str, bad: object) -> None:
    record = _record(); record[field] = bad
    result = validate_candidate_review_manual_research_response(record)
    assert not result.is_valid and result.research_response == {}


@pytest.mark.parametrize("field,value", [
    ("response_label", "UNKNOWN"), ("source_assessment_labels", ["UNKNOWN"]),
    ("completion_labels", ["UNKNOWN"]), ("response_sections", ["UNKNOWN"]),
    ("source_assessment_labels", ["PRIMARY_SOURCE_REVIEWED", "PRIMARY_SOURCE_REVIEWED"]),
])
def test_label_failures_are_neutral(field: str, value: object) -> None:
    record = _record(); record[field] = value
    assert not validate_candidate_review_manual_research_response(record).is_valid


def test_allowlist_values_are_the_merged_constants() -> None:
    assert "PRIMARY_SOURCE_REVIEWED" in ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS
    assert "REQUIRED_SECTIONS_PRESENT" in ALLOWED_RESEARCH_COMPLETION_LABELS
    assert "QUESTION_RESTATEMENT" in ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS


def test_flag_precedence_and_sanitization() -> None:
    flag = REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS[0]
    for bad in (False, 1, "true", None):
        record = _record(); record["safety_flags"][flag] = bad
        assert not validate_candidate_review_manual_research_response(record).is_valid
    record = _record(); record["safety_flags"].pop(flag)
    assert not validate_candidate_review_manual_research_response(record).is_valid
    record = _record(); record["safety_flags"]["safe_extra_boundary"] = True
    result = validate_candidate_review_manual_research_response(record)
    assert result.is_valid and "safe_extra_boundary" not in result.safety_flags
    record = _record(); record["safety_flags"]["execution"] = True
    assert not validate_candidate_review_manual_research_response(record).is_valid


@pytest.mark.parametrize("surface", ["research_question", "evidence_for", "cited_source_references", "non_authority_notice", "safety_flags"])
def test_unsafe_content_never_echoes(surface: str) -> None:
    record = _record()
    if surface in ("evidence_for", "cited_source_references"):
        record[surface] = [TRAP]
    elif surface == "safety_flags":
        record[surface][TRAP] = True
    else:
        record[surface] = TRAP
    result = validate_candidate_review_manual_research_response(record)
    assert not result.is_valid and result.research_response == {} and TRAP not in repr(result)
    with pytest.raises(ValueError) as captured:
        assert_candidate_review_manual_research_response(record)
    assert str(captured.value) == "INVALID_MANUAL_RESEARCH_RESPONSE" and TRAP not in str(captured.value)


@pytest.mark.parametrize("field", ["recommendation", "probability_estimate", "score", "rank", "priority", "prompt", "model_output", "tool_plan", "execution", "order"])
def test_unknown_authority_fields_fail_closed(field: str) -> None:
    record = _record(); record[field] = "unsafe"
    assert not validate_candidate_review_manual_research_response(record).is_valid


def test_ast_reviewer_traps_enforce_exact_bounded_surface() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    helpers = {node.name for node in functions if not node.name.startswith("test_")}
    assert helpers == {"_safety_flags", "_notice", "_record"}
    forbidden_names = ("adapter", "convert", "conversion", "bridge", "transfer", "map", "from_wp130", "from_wp132", "request_to_response", "briefing_to_response", "generate", "infer", "default", "prompt", "model", "provider", "hermes", "write", "export", "storage", "cli")
    assert not any(term in name.lower() for name in helpers for term in forbidden_names)
    imports_from = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    application = {node.module for node in imports_from if node.module and node.module.startswith("src.")}
    assert application == {"src.data_layer.hermes_candidate_review_manual_research_response"}
    imported = {alias.name for node in imports_from if node.module in application for alias in node.names}
    assert imported == {
        "ALLOWED_RESEARCH_COMPLETION_LABELS", "ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS",
        "ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS", "REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS", "assert_candidate_review_manual_research_response",
        "build_candidate_review_manual_research_response", "validate_candidate_review_manual_research_response",
    }
    all_modules = application | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    forbidden_modules = ("subprocess", "os", "socket", "http", "requests", "urllib", "time", "datetime", "uuid", "random", "database", "writer", "storage", "export", "cli")
    assert not any(term in module.lower() for module in all_modules - application for term in forbidden_modules)
