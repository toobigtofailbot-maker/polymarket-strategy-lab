import ast
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_research_briefing_packet import (
    ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS,
    REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS,
    REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS,
    assert_candidate_review_manual_research_briefing_packet,
    build_candidate_review_manual_research_briefing_packet,
    validate_candidate_review_manual_research_briefing_packet,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING_MODEL_CALL"
SCALAR_FIELDS = (
    "briefing_id", "source_wp_context", "source_research_question_record_reference",
    "selected_candidate_reference", "research_question", "research_question_type",
    "resolution_rule_context", "evidence_gap_summary", "uncertainty_summary",
    "known_missing_data", "limitations", "operator_research_instructions",
    "operator_next_manual_step", "created_by_operator_note", "non_authority_notice",
)
SEQUENCE_FIELDS = (
    "source_references_to_inspect", "falsification_checks_to_perform",
    "required_response_sections",
)


def _safety_flags():
    return {name: True for name in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS}


def _notice():
    return (
        "Advisory only; manual; local; offline; read only; human review required; explicit caller content only; "
        "not prompt generation; not prompt execution; not model or provider call; not Hermes runtime; "
        "not network or API; not market data ingestion; not discovery automation; not automated selection; "
        "not scoring or ranking; not priority calculation; not recommendation; not factual conclusion; "
        "not advisory finding generation; not execution; not credentials; not paper or live; "
        "not strategy promotion; not PR approval; not storage or writer; not export or report; not CLI; "
        "not scheduler or background task."
    )


def _valid_packet():
    return {
        "briefing_id": "synthetic-briefing-131",
        "source_wp_context": "Synthetic WP131 manual briefing exercise",
        "source_research_question_record_reference": "synthetic-question-record-reference",
        "selected_candidate_reference": "synthetic-candidate-reference",
        "briefing_label": "BRIEFING_READY_FOR_MANUAL_RESEARCH",
        "research_question": "Which synthetic public source resolves the stated outcome ambiguity?",
        "research_question_type": "RESOLUTION_RULE_AMBIGUITY",
        "source_references_to_inspect": ["synthetic-public-source-a", "synthetic-public-source-b"],
        "resolution_rule_context": "Synthetic outcome wording requires manual inspection",
        "evidence_gap_summary": "A synthetic primary reference is absent",
        "uncertainty_summary": "Synthetic source applicability remains uncertain",
        "known_missing_data": "A synthetic publication timestamp is absent",
        "limitations": "Synthetic fixture only and no factual conclusion",
        "falsification_checks_to_perform": ["Inspect synthetic contrary source", "Compare synthetic wording"],
        "required_response_sections": sorted(ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS),
        "operator_research_instructions": "Inspect only the named synthetic sources manually",
        "operator_next_manual_step": "Record human observations outside this smoke",
        "human_review_required": True,
        "created_by_operator_note": "Prepared manually for a synthetic smoke",
        "non_authority_notice": _notice(),
        "safety_flags": _safety_flags(),
    }


def test_positive_manual_packet_smoke_is_in_memory_only(tmp_path) -> None:
    packet = _valid_packet()
    question = packet["research_question"]
    references = list(packet["source_references_to_inspect"])
    checks = list(packet["falsification_checks_to_perform"])
    sections = list(packet["required_response_sections"])
    result = build_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is True
    assert set(result.briefing_packet) == set(REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS)
    assert all(isinstance(result.briefing_packet[field], str) for field in SCALAR_FIELDS)
    assert all(
        isinstance(result.briefing_packet[field], (list, tuple))
        and all(isinstance(item, str) and item.strip() for item in result.briefing_packet[field])
        for field in SEQUENCE_FIELDS
    )
    assert result.briefing_packet["research_question"] == question
    assert result.briefing_packet["source_references_to_inspect"] == references
    assert result.briefing_packet["falsification_checks_to_perform"] == checks
    assert result.briefing_packet["required_response_sections"] == sections
    assert result.safety_flags == _safety_flags()
    assert result.briefing_packet["safety_flags"] == _safety_flags()
    assert result.briefing_packet["human_review_required"] is True
    forbidden = {"response", "generated_response", "prompt", "conclusion", "finding", "recommendation", "score", "rank", "priority"}
    assert forbidden.isdisjoint(result.briefing_packet)
    assert list(tmp_path.iterdir()) == []


def test_missing_question_fails_closed_without_generation(tmp_path) -> None:
    packet = _valid_packet()
    del packet["research_question"]
    result = validate_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is False
    assert result.briefing_packet == {} and result.safety_flags == {}
    assert result.required_response_sections == () and result.briefing_label is None
    assert result.errors == ("MISSING_REQUIRED_FIELD",) and result.warnings == ()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field", ("research_question", "research_question_type", "operator_research_instructions", "resolution_rule_context", "non_authority_notice"))
@pytest.mark.parametrize("value", (7, True, {}, [], dict(response="safe text")))
def test_representative_scalar_wrong_shapes_fail_closed(field, value) -> None:
    packet = _valid_packet()
    packet[field] = value
    result = validate_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is False and result.briefing_packet == {}
    assert result.safety_flags == {} and result.required_response_sections == ()


@pytest.mark.parametrize("field", SEQUENCE_FIELDS)
@pytest.mark.parametrize("value", ([], "scalar text", {"nested": "text"}, ["safe text", {"nested": "text"}]))
def test_every_sequence_wrong_shape_fails_closed(field, value) -> None:
    packet = _valid_packet()
    packet[field] = value
    result = validate_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is False and result.briefing_packet == {}
    assert result.safety_flags == {} and result.required_response_sections == ()


@pytest.mark.parametrize("field", ("research_question", "source_references_to_inspect", "operator_research_instructions", "non_authority_notice"))
def test_unsafe_trap_fails_closed_without_echo(field) -> None:
    packet = _valid_packet()
    packet[field] = [TRAP] if field == "source_references_to_inspect" else TRAP
    result = validate_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is False and result.briefing_packet == {}
    assert TRAP not in repr(result)


@pytest.mark.parametrize("field", ("generated_response", "recommendation", "score", "rank", "priority", "prompt", "model_output"))
def test_unknown_authority_fields_fail_closed(field) -> None:
    packet = _valid_packet()
    packet[field] = "synthetic extra"
    result = validate_candidate_review_manual_research_briefing_packet(packet)
    assert result.is_valid is False and result.briefing_packet == {}
    assert result.safety_flags == {} and result.required_response_sections == ()


def test_assert_helper_raises_exact_neutral_error_without_echo() -> None:
    packet = _valid_packet()
    packet["research_question"] = TRAP
    with pytest.raises(ValueError) as captured:
        assert_candidate_review_manual_research_briefing_packet(packet)
    assert str(captured.value) == "INVALID_MANUAL_RESEARCH_BRIEFING_PACKET"
    assert TRAP not in str(captured.value)


def test_ast_reviewer_traps_enforce_exact_bounded_surface() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    helpers = {node.name for node in functions if not node.name.startswith("test_")}
    assert helpers == {"_safety_flags", "_notice", "_valid_packet"}
    forbidden_terms = (
        "adapter", "convert", "conversion", "bridge", "transfer", "map", "mapping",
        "from_wp121", "from_wp128", "from_wp129", "prompt", "response", "conclusion",
        "model", "provider", "hermes", "write", "export", "storage", "cli",
    )
    assert not any(term in name.lower() for name in helpers for term in forbidden_terms)
    imports_from = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    modules = {node.module for node in imports_from}
    assert modules == {"pathlib", "src.data_layer.hermes_candidate_review_manual_research_briefing_packet"}
    assert not any("research_question_record" in module or "manual_queue_selection" in module for module in modules)
    imported_application_names = {
        alias.name for node in imports_from
        if node.module == "src.data_layer.hermes_candidate_review_manual_research_briefing_packet"
        for alias in node.names
    }
    assert imported_application_names == {
        "ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS", "REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS",
        "REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS",
        "assert_candidate_review_manual_research_briefing_packet",
        "build_candidate_review_manual_research_briefing_packet",
        "validate_candidate_review_manual_research_briefing_packet",
    }
    forbidden_modules = ("subprocess", "os", "socket", "http", "requests", "urllib", "model", "provider", "hermes", "writer", "storage", "export", "cli")
    all_modules = modules | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    non_application_modules = all_modules - {"src.data_layer.hermes_candidate_review_manual_research_briefing_packet"}
    assert not any(term in module.lower() for module in non_application_modules for term in forbidden_modules)
    forbidden_keys = {"response", "generated_response", "prompt", "conclusion", "finding", "recommendation", "score", "rank", "priority"}
    for function in functions:
        for dictionary in (node for node in ast.walk(function) if isinstance(node, ast.Dict)):
            keys = {key.value for key in dictionary.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            assert forbidden_keys.isdisjoint(keys)
