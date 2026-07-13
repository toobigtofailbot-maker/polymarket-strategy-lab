import ast
import copy
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_research_request import (
    ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS,
    ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS,
    ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS as REQUEST_SECTION_LABELS,
    ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS,
    REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS,
    REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS,
    assert_candidate_review_manual_research_request,
    build_candidate_review_manual_research_request,
    validate_candidate_review_manual_research_request,
)
from src.data_layer.hermes_candidate_review_manual_research_response import (
    ALLOWED_RESEARCH_COMPLETION_LABELS,
    ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS as RESPONSE_SECTION_LABELS,
    ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS,
    REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS,
    REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS,
    assert_candidate_review_manual_research_response,
    build_candidate_review_manual_research_response,
    validate_candidate_review_manual_research_response,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_SCORING_MODEL_CALL"


def _request_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS}


def _response_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}


def _request_notice() -> str:
    return "; ".join((
        "advisory only", "manual", "local", "offline", "read only", "human review required",
        "explicit caller content only", "request contract only", "not prompt generation",
        "not prompt execution", "not model or provider", "not Hermes", "not tool selection",
        "not tool invocation", "not network or API", "not source fetching", "not market data ingestion",
        "not discovery automation", "not automated selection", "not scoring or ranking",
        "not priority calculation", "not recommendation", "not factual conclusion",
        "not advisory finding generation", "not execution", "not credentials", "not paper or live",
        "not strategy promotion", "not PR approval", "not storage or writer", "not export or report",
        "not CLI", "not scheduler or background task",
    ))


def _response_notice() -> str:
    return "; ".join((
        "advisory only", "manual", "local", "offline", "read only", "human review required",
        "explicit caller content only", "response contract only", "not prompt generation",
        "not prompt execution", "not model or provider", "not Hermes", "not tool selection",
        "not tool invocation", "not network or API", "not source fetching",
        "not source verification", "not citation verification", "not market data ingestion",
        "not discovery automation", "not automated selection", "not scoring or ranking",
        "not priority calculation", "not recommendation", "not probability estimation",
        "not factual correctness", "not factual conclusion", "not strategy", "not execution",
        "not risk", "not credentials", "not paper or live", "not strategy promotion",
        "not PR approval", "not storage or writer", "not export or report", "not CLI",
        "not scheduler or background task",
    ))


def _request() -> dict[str, object]:
    return {
        "request_id": "synthetic-request-135",
        "source_wp_context": "WP135 synthetic request exercise",
        "source_briefing_packet_reference": "synthetic-briefing-reference-135",
        "selected_candidate_reference": "synthetic-candidate-reference-135",
        "request_label": "REQUEST_READY_FOR_MANUAL_RESEARCH",
        "research_question": "What synthetic public condition resolves this exercise?",
        "research_question_type": "synthetic resolution review",
        "approved_source_references": ["synthetic-source-reference-a", "synthetic-source-reference-b"],
        "source_requirement_labels": ["PRIMARY_SOURCE_REQUIRED", "SOURCE_DATE_REQUIRED"],
        "citation_requirement_labels": ["CITATION_REQUIRED_FOR_EACH_MATERIAL_CLAIM"],
        "evidence_requirement_labels": ["EVIDENCE_FOR_REQUIRED", "EVIDENCE_AGAINST_REQUIRED"],
        "required_response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "research_scope": "Review only supplied synthetic references.",
        "known_uncertainties": "A synthetic publication date remains uncertain.",
        "known_missing_data": "One synthetic bulletin is absent.",
        "falsification_checks_to_perform": ["Compare the synthetic condition wording."],
        "operator_research_instructions": "Manually inspect only synthetic references.",
        "operator_review_instructions": "A human checks the synthetic record.",
        "refusal_behavior": "Refuse unsafe or out-of-scope content.",
        "failure_behavior": "Return neutral failure without findings.",
        "max_source_count": 2,
        "max_citation_count": 4,
        "max_output_words": 500,
        "timeout_seconds": 60,
        "max_retry_count": 0,
        "human_review_required": True,
        "created_by_operator_note": "Explicit synthetic caller request fixture.",
        "non_authority_notice": _request_notice(),
        "safety_flags": _request_flags(),
    }


def _response() -> dict[str, object]:
    return {
        "response_id": "synthetic-response-135",
        "source_wp_context": "WP135 synthetic response exercise",
        "source_request_reference": "synthetic-request-135",
        "source_briefing_packet_reference": "synthetic-briefing-reference-135",
        "selected_candidate_reference": "synthetic-candidate-reference-135",
        "response_label": "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "research_question": "What synthetic public condition resolves this exercise?",
        "research_question_type": "synthetic resolution review",
        "question_restatement": "Inspect the synthetic public condition.",
        "source_summary": "Caller recorded synthetic source material.",
        "resolution_rule_analysis": "Caller recorded synthetic condition details.",
        "evidence_for": ["Synthetic item A supports the condition."],
        "evidence_against": ["Synthetic item B disputes the condition."],
        "source_conflicts": ["Synthetic items use different dates."],
        "uncertainties": ["A synthetic update remains unavailable."],
        "known_missing_data": ["A synthetic bulletin is absent."],
        "falsification_checks_performed": ["Compared the synthetic condition wording."],
        "limitations": ["Only synthetic material was considered."],
        "what_would_change_the_conclusion": ["A contrary synthetic bulletin."],
        "operator_review_notes": "Human inspection remains required.",
        "cited_source_references": ["synthetic-source-reference-a", "synthetic-source-reference-b"],
        "source_assessment_labels": ["PRIMARY_SOURCE_REVIEWED"],
        "completion_labels": ["REQUIRED_SECTIONS_PRESENT"],
        "response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "operator_next_manual_step": "Perform human inspection.",
        "reviewer_acknowledgement": "Human inspection remains pending.",
        "human_review_required": True,
        "created_by_operator_note": "Explicit synthetic caller response fixture.",
        "non_authority_notice": _response_notice(),
        "safety_flags": _response_flags(),
    }


def test_positive_independent_request_response_linkage_and_empty_tmp_path(tmp_path: Path) -> None:
    request = _request()
    response = _response()
    request_before = copy.deepcopy(request)
    response_before = copy.deepcopy(response)

    request_validation = validate_candidate_review_manual_research_request(request)
    request_result = build_candidate_review_manual_research_request(request)
    response_validation = validate_candidate_review_manual_research_response(response)
    response_result = build_candidate_review_manual_research_response(response)

    assert request_validation.is_valid is request_result.is_valid is True
    assert response_validation.is_valid is response_result.is_valid is True
    assert request == request_before
    assert response == response_before
    assert set(request_result.research_request) == set(REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS)
    assert set(response_result.research_response) == set(REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS)
    assert request_result.errors == request_result.warnings == ()
    assert response_result.errors == response_result.warnings == ()
    assert request_result.research_request["human_review_required"] is True
    assert response_result.research_response["human_review_required"] is True
    assert request_result.safety_flags == _request_flags()
    assert response_result.safety_flags == _response_flags()

    assert request_result.research_request["request_id"] == response_result.research_response["source_request_reference"]
    assert request_result.research_request["source_briefing_packet_reference"] == response_result.research_response["source_briefing_packet_reference"]
    assert request_result.research_request["selected_candidate_reference"] == response_result.research_response["selected_candidate_reference"]
    assert request_result.research_request["research_question"] == response_result.research_response["research_question"]
    assert request_result.research_request["research_question_type"] == response_result.research_response["research_question_type"]
    assert request_result.research_request["required_response_sections"] == response_result.research_response["response_sections"]
    assert all(reference in request_result.research_request["approved_source_references"] for reference in response_result.research_response["cited_source_references"])
    assert request_result.research_request["human_review_required"] is response_result.research_response["human_review_required"] is True

    forbidden_outputs = {
        "chain", "session", "linkage_receipt", "recommendation", "probability_estimate",
        "score", "rank", "priority", "prompt", "model_output", "tool_output", "report",
        "export", "execution", "order", "risk_decision",
    }
    assert forbidden_outputs.isdisjoint(request_result.research_request)
    assert forbidden_outputs.isdisjoint(response_result.research_response)
    assert "chain" not in type(request_result).__name__.lower()
    assert "session" not in type(response_result).__name__.lower()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mismatch", [
    "request_reference", "briefing_reference", "candidate_reference", "research_question",
    "research_question_type", "response_sections", "cited_reference",
])
def test_independently_valid_records_can_be_linkage_inconsistent(
    mismatch: str, tmp_path: Path
) -> None:
    request = _request()
    response = _response()
    if mismatch == "request_reference":
        response["source_request_reference"] = "synthetic-request-other"
    elif mismatch == "briefing_reference":
        response["source_briefing_packet_reference"] = "synthetic-briefing-other"
    elif mismatch == "candidate_reference":
        response["selected_candidate_reference"] = "synthetic-candidate-other"
    elif mismatch == "research_question":
        response["research_question"] = "What alternate synthetic condition resolves this exercise?"
    elif mismatch == "research_question_type":
        response["research_question_type"] = "alternate synthetic resolution review"
    elif mismatch == "response_sections":
        response["response_sections"] = ["SOURCE_SUMMARY", "QUESTION_RESTATEMENT"]
    else:
        response["cited_source_references"] = ["synthetic-source-reference-outside"]

    request_result = validate_candidate_review_manual_research_request(request)
    response_result = validate_candidate_review_manual_research_response(response)
    assert request_result.is_valid is response_result.is_valid is True
    if mismatch == "request_reference":
        assert request_result.research_request["request_id"] != response_result.research_response["source_request_reference"]
    elif mismatch == "briefing_reference":
        assert request_result.research_request["source_briefing_packet_reference"] != response_result.research_response["source_briefing_packet_reference"]
    elif mismatch == "candidate_reference":
        assert request_result.research_request["selected_candidate_reference"] != response_result.research_response["selected_candidate_reference"]
    elif mismatch == "research_question":
        assert request_result.research_request["research_question"] != response_result.research_response["research_question"]
    elif mismatch == "research_question_type":
        assert request_result.research_request["research_question_type"] != response_result.research_response["research_question_type"]
    elif mismatch == "response_sections":
        assert request_result.research_request["required_response_sections"] != response_result.research_response["response_sections"]
    else:
        assert not all(reference in request_result.research_request["approved_source_references"] for reference in response_result.research_response["cited_source_references"])
    assert not hasattr(request_result, "chain")
    assert not hasattr(response_result, "session")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("invalid", [
    "missing_request_id", "bad_bounded_integer", "false_request_review",
    "unsafe_request_trap", "unknown_request_authority",
])
def test_invalid_request_records_fail_closed_without_response_generation(
    invalid: str, tmp_path: Path
) -> None:
    request = _request()
    if invalid == "missing_request_id":
        request.pop("request_id")
    elif invalid == "bad_bounded_integer":
        request["max_source_count"] = "2"
    elif invalid == "false_request_review":
        request["human_review_required"] = False
    elif invalid == "unsafe_request_trap":
        request["research_question"] = TRAP
    else:
        request["recommendation"] = "synthetic"
    result = validate_candidate_review_manual_research_request(request)
    assert result.is_valid is False
    assert result.research_request == {}
    assert result.warnings == ()
    assert TRAP not in repr(result)
    with pytest.raises(ValueError, match="^INVALID_MANUAL_RESEARCH_REQUEST$") as captured:
        assert_candidate_review_manual_research_request(request)
    assert TRAP not in str(captured.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("invalid", [
    "missing_response_id", "bad_sequence", "false_response_review",
    "unsafe_response_trap", "unknown_response_authority",
])
def test_invalid_response_records_fail_closed_without_request_generation(
    invalid: str, tmp_path: Path
) -> None:
    response = _response()
    if invalid == "missing_response_id":
        response.pop("response_id")
    elif invalid == "bad_sequence":
        response["response_sections"] = "QUESTION_RESTATEMENT"
    elif invalid == "false_response_review":
        response["human_review_required"] = False
    elif invalid == "unsafe_response_trap":
        response["research_question"] = TRAP
    else:
        response["probability_estimate"] = "synthetic"
    result = validate_candidate_review_manual_research_response(response)
    assert result.is_valid is False
    assert result.research_response == {}
    assert result.warnings == ()
    assert TRAP not in repr(result)
    with pytest.raises(ValueError, match="^INVALID_MANUAL_RESEARCH_RESPONSE$") as captured:
        assert_candidate_review_manual_research_response(response)
    assert TRAP not in str(captured.value)
    assert list(tmp_path.iterdir()) == []


def test_allowlist_values_are_existing_contract_constants() -> None:
    assert "PRIMARY_SOURCE_REQUIRED" in ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS
    assert "CITATION_REQUIRED_FOR_EACH_MATERIAL_CLAIM" in ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS
    assert "EVIDENCE_FOR_REQUIRED" in ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS
    assert "QUESTION_RESTATEMENT" in REQUEST_SECTION_LABELS
    assert "QUESTION_RESTATEMENT" in RESPONSE_SECTION_LABELS
    assert "PRIMARY_SOURCE_REVIEWED" in ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS
    assert "REQUIRED_SECTIONS_PRESENT" in ALLOWED_RESEARCH_COMPLETION_LABELS


def test_ast_reviewer_traps_enforce_independent_helper_free_linkage() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    helpers = {node.name for node in functions if not node.name.startswith("test_")}
    assert helpers == {
        "_request_flags", "_response_flags", "_request_notice", "_response_notice",
        "_request", "_response",
    }
    forbidden_helper_terms = (
        "adapter", "convert", "conversion", "bridge", "transfer", "map", "mapping",
        "chain", "session", "from_request", "to_response", "populate", "generate",
        "infer", "default",
    )
    assert not any(term in name.lower() for name in helpers for term in forbidden_helper_terms)
    request_function = next(node for node in functions if node.name == "_request")
    response_function = next(node for node in functions if node.name == "_response")
    assert request_function.args.args == []
    assert response_function.args.args == []
    response_names = {node.id for node in ast.walk(response_function) if isinstance(node, ast.Name)}
    assert not {"request", "request_result", "request_data"} & response_names

    imports_from = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    application = {node.module for node in imports_from if node.module and node.module.startswith("src.")}
    assert application == {
        "src.data_layer.hermes_candidate_review_manual_research_request",
        "src.data_layer.hermes_candidate_review_manual_research_response",
    }
    all_modules = application | {
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    }
    forbidden_modules = (
        "subprocess", "os", "socket", "http", "requests", "urllib", "time", "datetime",
        "uuid", "random", "database", "writer", "storage", "export", "cli",
    )
    assert not any(term in module.lower() for module in all_modules - application for term in forbidden_modules)
    assert not any(isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    forbidden_calls = {"open", "write", "writelines"}
    assert not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id in forbidden_calls for node in ast.walk(tree)
    )
    response_calls = [
        node for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "_response"
    ]
    assert response_calls and all(not node.args and not node.keywords for node in response_calls)
