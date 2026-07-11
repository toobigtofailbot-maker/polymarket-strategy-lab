import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_manual_queue_selection_handoff import *


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING_AUTO_SELECT"
NOTICE = (
    "Advisory only; manual; local; offline; human review required; explicit human selection only; "
    "not automated selection; not scoring or ranking; not priority calculation; not discovery automation; "
    "not market data ingestion; not research-question generation; not execution; not runtime; not credentials; "
    "not paper or live; not prompt execution; not file or network; not strategy promotion; not PR approval; "
    "not storage or writer; not export or report."
)


def flags():
    return {name: True for name in REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS}


def selection():
    return {
        "selection_id": "selection-128", "source_wp_context": "WP128 manual review",
        "source_queue_reference": "queue reference", "selected_candidate_reference": "candidate reference",
        "selection_label": "SELECT_FOR_MANUAL_RESEARCH_QUESTION_DRAFT",
        "selection_reason_labels": ["HUMAN_SELECTED_FOR_DEEPER_RESEARCH"],
        "human_selection_basis": "Operator inspected the supplied evidence references",
        "evidence_references_reviewed": ["public source reference"],
        "uncertainty_notes": "Outcome wording remains uncertain", "known_missing_data": "No recent source update",
        "limitations": "Manual review is bounded", "duplicate_check_notes": "No matching question found",
        "operator_next_manual_step": "Draft a caller supplied question for human review",
        "human_review_required": True, "created_by_operator_note": "Recorded by operator",
        "non_authority_notice": NOTICE, "safety_flags": flags(),
    }


def handoff():
    return {
        "handoff_id": "handoff-128", "source_wp_context": "WP128 manual handoff",
        "source_selection_record_reference": "selection reference",
        "selected_candidate_reference": "candidate reference",
        "proposed_research_question": "Which public source resolves the outcome wording ambiguity?",
        "proposed_research_question_type": "RESOLUTION_RULE_AMBIGUITY",
        "evidence_references_to_check": ["public source reference"],
        "uncertainty_notes": "Outcome wording remains uncertain", "known_missing_data": "No recent source update",
        "limitations": "Question is caller supplied", "falsification_checks_to_perform": ["Check contrary source"],
        "operator_next_manual_step": "Review the proposed question manually", "human_review_required": True,
        "created_by_operator_note": "Recorded by operator", "non_authority_notice": NOTICE,
        "safety_flags": flags(),
    }


def test_stdlib_only_import_posture():
    path = Path("src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"__future__", "dataclasses", "typing"}
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)]


def test_valid_selection_and_handoff_are_bounded_and_sanitized():
    selected = build_candidate_review_manual_queue_selection_record(selection())
    handed = build_candidate_review_research_question_handoff(handoff())
    assert selected.is_valid and handed.is_valid
    assert set(selected.selection_record) == set(REQUIRED_MANUAL_QUEUE_SELECTION_RECORD_FIELDS)
    assert set(handed.handoff_record) == set(REQUIRED_RESEARCH_QUESTION_HANDOFF_FIELDS)
    assert selected.safety_flags == handed.safety_flags == flags()


@pytest.mark.parametrize("label", ALLOWED_MANUAL_QUEUE_SELECTION_LABELS)
def test_every_allowed_selection_label(label):
    data = selection(); data["selection_label"] = label
    assert validate_candidate_review_manual_queue_selection_record(data).is_valid


@pytest.mark.parametrize("reason", ALLOWED_MANUAL_QUEUE_SELECTION_REASON_LABELS)
def test_every_allowed_selection_reason(reason):
    data = selection(); data["selection_reason_labels"] = [reason]
    assert validate_candidate_review_manual_queue_selection_record(data).is_valid


@pytest.mark.parametrize("question_type", ALLOWED_RESEARCH_QUESTION_HANDOFF_TYPES)
def test_every_allowed_question_type(question_type):
    data = handoff(); data["proposed_research_question_type"] = question_type
    assert validate_candidate_review_research_question_handoff(data).is_valid


def test_unknown_and_empty_labels_fail_closed():
    data = selection(); data["selection_label"] = "UNKNOWN"
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_SELECTION_LABEL",)
    data = selection(); data["selection_reason_labels"] = []
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_SELECTION_REASON_LABEL",)
    data = handoff(); data["proposed_research_question_type"] = "UNKNOWN"
    assert validate_candidate_review_research_question_handoff(data).errors == ("INVALID_RESEARCH_QUESTION_TYPE",)


def test_malformed_label_reason_type_and_question_text_fail_closed():
    data = selection(); data["selection_label"] = []
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_SELECTION_LABEL",)
    data = selection(); data["selection_reason_labels"] = [{}]
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_SELECTION_REASON_LABEL",)
    data = handoff(); data["proposed_research_question_type"] = []
    assert validate_candidate_review_research_question_handoff(data).errors == ("INVALID_RESEARCH_QUESTION_TYPE",)
    data = handoff(); data["proposed_research_question"] = 7
    assert validate_candidate_review_research_question_handoff(data).errors == ("INVALID_REQUIRED_FIELD",)


@pytest.mark.parametrize("field", REQUIRED_MANUAL_QUEUE_SELECTION_RECORD_FIELDS)
def test_every_selection_field_required(field):
    data = selection(); del data[field]
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("MISSING_REQUIRED_FIELD",)


@pytest.mark.parametrize("field", REQUIRED_RESEARCH_QUESTION_HANDOFF_FIELDS)
def test_every_handoff_field_required(field):
    data = handoff(); del data[field]
    assert validate_candidate_review_research_question_handoff(data).errors == ("MISSING_REQUIRED_FIELD",)


@pytest.mark.parametrize("factory,validator,field", [
    (selection, validate_candidate_review_manual_queue_selection_record, "selection_id"),
    (handoff, validate_candidate_review_research_question_handoff, "proposed_research_question"),
])
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_null_and_blank_required_scalars(factory, validator, field, bad):
    data = factory(); data[field] = bad
    assert validator(data).errors == ("INVALID_REQUIRED_FIELD",)


@pytest.mark.parametrize("bad", [None, [], "text", 7])
def test_unsupported_top_level_shapes(bad):
    assert validate_candidate_review_manual_queue_selection_record(bad).errors == ("UNSUPPORTED_INPUT_SHAPE",)
    assert validate_candidate_review_research_question_handoff(bad).errors == ("UNSUPPORTED_INPUT_SHAPE",)


@pytest.mark.parametrize("bad", [False, 1, "true"])
def test_exact_human_review_boolean(bad):
    data = selection(); data["human_review_required"] = bad
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("HUMAN_REVIEW_REQUIRED",)


@pytest.mark.parametrize("bad", [False, 1, "true"])
def test_each_safety_flag_requires_exact_true(bad):
    for name in REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS:
        data = selection(); data["safety_flags"][name] = bad
        assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_SAFETY_FLAG",)


def test_missing_flag_and_extra_flag_behavior():
    data = selection(); del data["safety_flags"][REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS[0]]
    assert not validate_candidate_review_manual_queue_selection_record(data).is_valid
    data = selection(); data["safety_flags"]["benign_extra_flag"] = True
    result = validate_candidate_review_manual_queue_selection_record(data)
    assert result.is_valid and result.safety_flags == flags() and result.selection_record["safety_flags"] == flags()


def test_notice_requirements_and_permission_grants():
    data = selection(); data["non_authority_notice"] = "Advisory only"
    assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_NON_AUTHORITY_NOTICE",)
    for phrase in ("authorizes", "permission to", "approved for", "automatically selected", "recommended candidate"):
        data = selection(); data["non_authority_notice"] = NOTICE + " " + phrase
        assert validate_candidate_review_manual_queue_selection_record(data).errors == ("INVALID_NON_AUTHORITY_NOTICE",)


@pytest.mark.parametrize("term", [
    "buy", "stop loss", "fair value", "merge ready", "private key", "provider",
    "automated selection", "market data ingestion", "priority score", "rank", "score",
    "parser", "loader", "file writer", "storage path", "exporter", "CLI command",
])
def test_recursive_forbidden_families_and_reviewer_traps(term):
    data = selection(); data["selected_candidate_reference"] = {"nested": term}
    result = validate_candidate_review_manual_queue_selection_record(data)
    assert not result.is_valid and result.selection_record == {} and term not in repr(result)


@pytest.mark.parametrize("key", [
    "raw_metadata", "free_form_metadata", "caller_metadata", "arbitrary_metadata", "raw_input",
    "untrusted_input", "notes_raw", "warnings_raw", "reason_text_raw", "custom", "extras",
    "metadata", "freeform", "extra", "context", "custom_fields", "raw_response",
    "model_response", "prompt", "completion", "raw", "free_form", "arbitrary",
])
def test_recursive_raw_free_form_metadata_rejected(key):
    data = handoff(); data["limitations"] = {"nested": {key: "benign value"}}
    assert validate_candidate_review_research_question_handoff(data).errors == ("RAW_METADATA_NOT_ALLOWED",)


def test_unsafe_keys_and_safety_flag_keys_rejected_without_echo():
    for target in ("selected_candidate_reference", "safety_flags"):
        data = selection()
        if target == "selected_candidate_reference":
            data[target] = {"priority_score": TRAP}
        else:
            data[target]["priority_score"] = TRAP
        result = validate_candidate_review_manual_queue_selection_record(data)
        assert not result.is_valid and TRAP not in repr(result)


def test_caller_question_preserved_and_never_generated():
    question = "Which cited public source most directly resolves the stated ambiguity?"
    data = handoff(); data["proposed_research_question"] = question
    result = validate_candidate_review_research_question_handoff(data)
    assert result.is_valid and result.handoff_record["proposed_research_question"] == question
    del data["proposed_research_question"]
    invalid = validate_candidate_review_research_question_handoff(data)
    assert not invalid.is_valid and invalid.handoff_record == {}


def test_invalid_outputs_and_assertions_are_neutral():
    data = selection(); data["selected_candidate_reference"] = TRAP
    result = validate_candidate_review_manual_queue_selection_record(data)
    assert result == HermesCandidateReviewManualQueueSelectionRecordResult(False, {}, ("FORBIDDEN_CONTENT",), (), None, (), {})
    with pytest.raises(ValueError, match="^INVALID_MANUAL_QUEUE_SELECTION_RECORD$") as exc:
        assert_candidate_review_manual_queue_selection_record(data)
    assert TRAP not in str(exc.value)
    bad = handoff(); bad["proposed_research_question"] = TRAP
    result = validate_candidate_review_research_question_handoff(bad)
    assert result == HermesCandidateReviewResearchQuestionHandoffResult(False, {}, ("FORBIDDEN_CONTENT",), (), None, {})
    with pytest.raises(ValueError, match="^INVALID_RESEARCH_QUESTION_HANDOFF$") as exc:
        assert_candidate_review_research_question_handoff(bad)
    assert TRAP not in str(exc.value)


def test_inputs_unchanged_and_outputs_do_not_use_array_order_as_priority():
    data = selection(); data["selection_reason_labels"] = list(ALLOWED_MANUAL_QUEUE_SELECTION_REASON_LABELS)[:3]
    original = deepcopy(data)
    result = build_candidate_review_manual_queue_selection_record(data)
    assert data == original and result.selection_reason_labels == tuple(data["selection_reason_labels"])
    assert "priority" not in result.selection_record


def test_exact_dataclass_fields():
    assert tuple(field.name for field in fields(HermesCandidateReviewManualQueueSelectionRecordResult)) == (
        "is_valid", "selection_record", "errors", "warnings", "selection_label",
        "selection_reason_labels", "safety_flags",
    )
    assert tuple(field.name for field in fields(HermesCandidateReviewResearchQuestionHandoffResult)) == (
        "is_valid", "handoff_record", "errors", "warnings", "research_question_type", "safety_flags",
    )
