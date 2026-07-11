import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_research_briefing_packet import *


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING_MODEL_CALL"
NOTICE = (
    "Advisory only; manual; local; offline; read only; human review required; explicit caller content only; "
    "not prompt generation; not prompt execution; not model or provider call; not Hermes runtime; "
    "not network or API; not market data ingestion; not discovery automation; not automated selection; "
    "not scoring or ranking; not priority calculation; not recommendation; not factual conclusion; "
    "not advisory finding generation; not execution; not credentials; not paper or live; "
    "not strategy promotion; not PR approval; not storage or writer; not export or report; not CLI; "
    "not scheduler or background task."
)


def safety_flags():
    return {name: True for name in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS}


def packet():
    return {
        "briefing_id": "briefing-130", "source_wp_context": "WP130 manual briefing",
        "source_research_question_record_reference": "question record reference",
        "selected_candidate_reference": "candidate reference",
        "briefing_label": "BRIEFING_READY_FOR_MANUAL_RESEARCH",
        "research_question": "Which public source resolves the stated outcome ambiguity?",
        "research_question_type": "RESOLUTION_RULE_AMBIGUITY",
        "source_references_to_inspect": ["public resolution source"],
        "resolution_rule_context": "Outcome wording remains ambiguous",
        "evidence_gap_summary": "A primary source is missing",
        "uncertainty_summary": "The applicable source is uncertain",
        "known_missing_data": "No recent public update", "limitations": "Manual review is bounded",
        "falsification_checks_to_perform": ["Check a contrary public source"],
        "required_response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "operator_research_instructions": "Inspect the named public sources manually",
        "operator_next_manual_step": "Record human review observations",
        "human_review_required": True, "created_by_operator_note": "Recorded by operator",
        "non_authority_notice": NOTICE, "safety_flags": safety_flags(),
    }


def invalid(data):
    result = validate_candidate_review_manual_research_briefing_packet(data)
    assert not result.is_valid
    assert result.briefing_packet == {} and result.warnings == ()
    assert result.briefing_label is None and result.required_response_sections == ()
    assert result.safety_flags == {}
    assert TRAP not in repr(result)
    return result


def test_stdlib_only_import_posture_and_no_prior_workflow_import():
    path = Path("src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"__future__", "dataclasses", "typing"}
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    assert not any("hermes_candidate_review" in name for name in imports)


def test_valid_packet_is_bounded_sanitized_and_preserves_question():
    data = packet(); data["safety_flags"]["extra_safe_flag"] = True
    result = build_candidate_review_manual_research_briefing_packet(data)
    assert result.is_valid
    assert set(result.briefing_packet) == set(REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS)
    assert result.safety_flags == safety_flags()
    assert result.briefing_packet["safety_flags"] == safety_flags()
    assert result.briefing_packet["research_question"] == data["research_question"]
    assert result.required_response_sections == tuple(data["required_response_sections"])
    assert not any(key in result.briefing_packet for key in ("response", "prompt", "conclusion"))


@pytest.mark.parametrize("label", ALLOWED_RESEARCH_BRIEFING_PACKET_LABELS)
def test_every_allowed_briefing_label(label):
    data = packet(); data["briefing_label"] = label
    assert validate_candidate_review_manual_research_briefing_packet(data).is_valid


@pytest.mark.parametrize("section", ALLOWED_REQUIRED_RESPONSE_SECTION_LABELS)
def test_every_allowed_response_section_label(section):
    data = packet(); data["required_response_sections"] = [section]
    result = validate_candidate_review_manual_research_briefing_packet(data)
    assert result.is_valid and result.required_response_sections == (section,)


def test_unknown_labels_empty_and_duplicate_sections_rejected():
    data = packet(); data["briefing_label"] = "UNKNOWN"; invalid(data)
    data = packet(); data["required_response_sections"] = ["UNKNOWN"]; invalid(data)
    data = packet(); data["required_response_sections"] = []; invalid(data)
    data = packet(); data["required_response_sections"] *= 2; invalid(data)


@pytest.mark.parametrize("field", REQUIRED_RESEARCH_BRIEFING_PACKET_FIELDS)
def test_every_required_field_enforced(field):
    data = packet(); del data[field]; invalid(data)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_null_and_blank_scalar_fields_rejected(value):
    data = packet(); data["briefing_id"] = value; invalid(data)


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


@pytest.mark.parametrize("field", SCALAR_FIELDS)
@pytest.mark.parametrize("value", [
    7, 1.5, True, False, [], (), {}, ["text"], {"a": "b"}, b"text",
])
def test_every_scalar_field_rejects_non_string_shapes(field, value):
    data = packet(); data[field] = value
    assert invalid(data).errors == ("INVALID_REQUIRED_FIELD",)


@pytest.mark.parametrize("field", SEQUENCE_FIELDS)
@pytest.mark.parametrize("value", [
    [], (), "single string", 7, {}, [" "], [7], [True], [{}], [["nested"]],
    ["safe", {}],
])
def test_every_sequence_field_rejects_invalid_shapes_and_elements(field, value):
    data = packet(); data[field] = value
    assert invalid(data).errors == ("INVALID_REQUIRED_FIELD",)


@pytest.mark.parametrize("field", SEQUENCE_FIELDS)
@pytest.mark.parametrize("container", [list, tuple])
def test_every_sequence_field_accepts_nonempty_string_list_or_tuple(field, container):
    data = packet()
    values = ["QUESTION_RESTATEMENT"] if field == "required_response_sections" else ["safe text"]
    data[field] = container(values)
    result = validate_candidate_review_manual_research_briefing_packet(data)
    assert result.is_valid
    assert result.briefing_packet[field] == container(values)


@pytest.mark.parametrize("field", SCALAR_FIELDS)
@pytest.mark.parametrize("payload", [
    {"generated_response": "safe answer"}, {"response": "safe answer"},
    {"conclusion": "safe"}, {"finding": "safe"},
])
def test_nested_response_payloads_in_scalar_fields_fail_by_schema_shape(field, payload):
    data = packet(); data[field] = payload
    assert invalid(data).errors == ("INVALID_REQUIRED_FIELD",)


@pytest.mark.parametrize("value", [None, [], (), "packet", 7, True])
def test_unsupported_top_level_shapes_rejected(value):
    invalid(value)


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_human_review_must_be_exact_true(value):
    data = packet(); data["human_review_required"] = value; invalid(data)


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_each_safety_flag_false_or_truthy_rejected(value):
    for name in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS:
        data = packet(); data["safety_flags"][name] = value; invalid(data)


def test_each_missing_safety_flag_rejected():
    for name in REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS:
        data = packet(); del data["safety_flags"][name]; invalid(data)


def test_notice_policy_accepts_canonical_and_rejects_missing_permission_and_remainder():
    assert validate_candidate_review_manual_research_briefing_packet(packet()).is_valid
    data = packet(); data["non_authority_notice"] = NOTICE.replace("not prompt generation; ", ""); invalid(data)
    data = packet(); data["non_authority_notice"] = NOTICE + " Authorized to proceed."; invalid(data)
    data = packet(); data["non_authority_notice"] = NOTICE + " Buy after review."; invalid(data)


@pytest.mark.parametrize("unsafe", [
    "buy now", "expected return", "private key", "prompt runner", "provider call",
    "Hermes runtime", "automated selection", "market data ingestion", "scoring",
    "priority calculation", "parser", "loader", "file writer", "storage path",
    "exporter", "CLI command", "merge ready", "recommended candidate",
])
def test_forbidden_wording_families_rejected_recursively(unsafe):
    data = packet(); data["source_wp_context"] = {"nested": [unsafe]}; invalid(data)


@pytest.mark.parametrize("raw_key", [
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata", "raw_input",
    "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw", "custom", "extras",
    "metadata", "freeform", "extra", "context", "custom_fields", "raw_response",
    "model_response", "prompt", "completion", "raw", "free_form", "arbitrary",
])
def test_raw_free_form_metadata_rejected_recursively(raw_key):
    data = packet(); data["source_wp_context"] = {"nested": {raw_key: "safe text"}}; invalid(data)


@pytest.mark.parametrize("field", [
    "source_references_to_inspect", "operator_research_instructions", "safety_flags",
])
def test_unsafe_content_hidden_in_sensitive_surfaces_is_rejected(field):
    data = packet()
    data[field] = {"nested": TRAP} if field == "safety_flags" else [TRAP]
    invalid(data)


def test_missing_question_is_not_generated_and_unknown_authority_fields_rejected():
    data = packet(); del data["research_question"]; invalid(data)
    for name in ("recommendation", "score", "rank", "priority", "generated_response"):
        data = packet(); data[name] = "safe"; invalid(data)


def test_assert_is_neutral_and_trap_never_echoes():
    data = packet(); data["research_question"] = TRAP
    with pytest.raises(ValueError, match="^INVALID_MANUAL_RESEARCH_BRIEFING_PACKET$") as exc:
        assert_candidate_review_manual_research_briefing_packet(data)
    assert TRAP not in repr(exc.value)


def test_input_is_not_mutated_and_result_dataclass_fields_are_exact():
    data = packet(); before = deepcopy(data)
    validate_candidate_review_manual_research_briefing_packet(data)
    assert data == before
    assert [field.name for field in fields(HermesCandidateReviewManualResearchBriefingPacketResult)] == [
        "is_valid", "briefing_packet", "errors", "warnings", "briefing_label",
        "required_response_sections", "safety_flags",
    ]


def test_packet_order_and_section_labels_have_no_priority_or_generated_content():
    data = packet(); data["source_references_to_inspect"] = ["source z", "source a"]
    result = validate_candidate_review_manual_research_briefing_packet(data)
    assert result.is_valid
    assert result.briefing_packet["source_references_to_inspect"] == ["source z", "source a"]
    assert result.briefing_packet["required_response_sections"] == data["required_response_sections"]
    module = __import__(
        "src.data_layer.hermes_candidate_review_manual_research_briefing_packet", fromlist=["*"]
    )
    public = {name for name in dir(module) if not name.startswith("_")}
    assert not ({"store", "export", "main", "parse", "rank", "score", "recommend"} & public)
