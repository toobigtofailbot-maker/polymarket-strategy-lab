import ast
import copy
import dataclasses
import inspect
from pathlib import Path

import pytest

from src.data_layer import hermes_candidate_review_manual_research_response as module


NOTICE_FRAGMENTS = (
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
)
SCALARS = (
    "response_id", "source_wp_context", "source_request_reference",
    "source_briefing_packet_reference", "selected_candidate_reference",
    "research_question", "research_question_type", "question_restatement", "source_summary",
    "resolution_rule_analysis", "operator_review_notes", "operator_next_manual_step",
    "reviewer_acknowledgement", "created_by_operator_note", "non_authority_notice",
)
SEQUENCES = (
    "evidence_for", "evidence_against", "source_conflicts", "uncertainties",
    "known_missing_data", "falsification_checks_performed", "limitations",
    "what_would_change_the_conclusion", "cited_source_references",
    "source_assessment_labels", "completion_labels", "response_sections",
)


def valid_response():
    data = {field: "safe text" for field in SCALARS}
    data.update({
        "response_id": "response-133", "source_wp_context": "WP133",
        "source_request_reference": "request-132",
        "source_briefing_packet_reference": "briefing-130",
        "selected_candidate_reference": "candidate-reference",
        "response_label": "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "research_question": "What public evidence resolves this event?",
        "research_question_type": "resolution rules",
        "question_restatement": "Review the public evidence for the event.",
        "source_summary": "The caller recorded public source material.",
        "resolution_rule_analysis": "The caller recorded rule details.",
        "evidence_for": ["Public source A supports the stated condition."],
        "evidence_against": ["Public source B disputes the stated condition."],
        "source_conflicts": ["The public sources use different dates."],
        "uncertainties": ["The final public update is pending."],
        "known_missing_data": ["A later public bulletin is unavailable."],
        "falsification_checks_performed": ["Compared the public rule text."],
        "limitations": ["Only the cited public material was reviewed."],
        "what_would_change_the_conclusion": ["A contrary official bulletin."],
        "operator_review_notes": "A human reviewer must inspect the record.",
        "cited_source_references": ["https://example.invalid/public-a"],
        "source_assessment_labels": ["PRIMARY_SOURCE_REVIEWED"],
        "completion_labels": ["REQUIRED_SECTIONS_PRESENT"],
        "response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "operator_next_manual_step": "Human review of the cited public material.",
        "reviewer_acknowledgement": "Human review remains pending.",
        "human_review_required": True,
        "created_by_operator_note": "Explicitly entered by the operator.",
        "non_authority_notice": "; ".join(NOTICE_FRAGMENTS),
        "safety_flags": {flag: True for flag in module.REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS},
    })
    return data


def assert_neutral(result, trap=None):
    assert result.is_valid is False
    assert result.research_response == {}
    assert result.warnings == ()
    assert result.response_label is None
    assert result.source_assessment_labels == ()
    assert result.completion_labels == ()
    assert result.response_sections == ()
    assert result.safety_flags == {}
    if trap:
        assert trap not in repr(result)


def test_exact_public_surface_and_frozen_result():
    constants = {name for name in vars(module) if name.isupper() and not name.startswith("_")}
    assert constants == {
        "ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS",
        "ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS",
        "ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS",
        "ALLOWED_RESEARCH_COMPLETION_LABELS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS",
        "REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS",
    }
    functions = {name for name, value in vars(module).items()
                 if inspect.isfunction(value) and value.__module__ == module.__name__
                 and not name.startswith("_")}
    assert functions == {
        "validate_candidate_review_manual_research_response",
        "build_candidate_review_manual_research_response",
        "assert_candidate_review_manual_research_response",
    }
    assert [field.name for field in dataclasses.fields(
        module.HermesCandidateReviewManualResearchResponseResult)] == [
        "is_valid", "research_response", "errors", "warnings", "response_label",
        "source_assessment_labels", "completion_labels", "response_sections", "safety_flags",
    ]
    assert module.HermesCandidateReviewManualResearchResponseResult.__dataclass_params__.frozen


def test_ast_imports_and_helpers_are_exact_and_side_effect_free():
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append((node.module, tuple(alias.name for alias in node.names)))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
    assert imports == [
        ("__future__", ("annotations",)), ("dataclasses", ("dataclass",)),
        ("typing", ("Any", "Mapping")),
    ]
    assert set(functions) == {
        "_normalize", "_scan", "_copy", "_valid_notice", "_invalid",
        "validate_candidate_review_manual_research_response",
        "build_candidate_review_manual_research_response",
        "assert_candidate_review_manual_research_response",
    }
    lowered = source.lower()
    assert "manual_research_request" not in lowered
    assert "manual_research_briefing_packet" not in lowered
    for token in ("open(", "write(", "datetime", "uuid", "random", "subprocess", "requests"):
        assert token not in lowered


def test_valid_response_preserves_content_order_and_input():
    data = valid_response()
    data["evidence_for"] = ["first public fact", "second public fact"]
    before = copy.deepcopy(data)
    result = module.validate_candidate_review_manual_research_response(data)
    assert result.is_valid
    assert data == before
    assert result.research_response.keys() == dict.fromkeys(
        module.REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS).keys()
    assert result.research_response["evidence_for"] == ["first public fact", "second public fact"]
    assert result.errors == result.warnings == ()
    assert result.safety_flags == {flag: True for flag in module.REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}


@pytest.mark.parametrize("label", module.ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS)
def test_each_response_label(label):
    data = valid_response(); data["response_label"] = label
    assert module.validate_candidate_review_manual_research_response(data).is_valid


@pytest.mark.parametrize("field,allowed", [
    ("source_assessment_labels", module.ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS),
    ("completion_labels", module.ALLOWED_RESEARCH_COMPLETION_LABELS),
    ("response_sections", module.ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS),
])
def test_each_allowed_sequence_label(field, allowed):
    for label in allowed:
        data = valid_response(); data[field] = [label]
        assert module.validate_candidate_review_manual_research_response(data).is_valid


@pytest.mark.parametrize("field", module.REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS)
def test_every_missing_field_fails_closed(field):
    data = valid_response(); del data[field]
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("field", SCALARS)
@pytest.mark.parametrize("bad", [None, "", "  ", 1, 1.2, True, b"x", {}, [], (), set()])
def test_scalar_shape_matrix(field, bad):
    data = valid_response(); data[field] = bad
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("field", SEQUENCES)
@pytest.mark.parametrize("bad", [None, "text", [], (), {}, [""], [1], [True], [b"x"], [["x"]], [{"prompt": "x"}]])
def test_sequence_shape_matrix(field, bad):
    data = valid_response(); data[field] = bad
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("field", ["source_assessment_labels", "completion_labels", "response_sections"])
def test_unknown_and_duplicate_labels(field):
    data = valid_response(); data[field] = ["UNKNOWN_LABEL"]
    assert_neutral(module.validate_candidate_review_manual_research_response(data))
    data = valid_response(); data[field] = [data[field][0], data[field][0]]
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_human_review_is_exact_true(value):
    data = valid_response(); data["human_review_required"] = value
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("flag", module.REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS)
@pytest.mark.parametrize("mode", ["missing", "false", "integer", "string"])
def test_every_safety_flag_is_exact_true(flag, mode):
    data = valid_response()
    if mode == "missing": del data["safety_flags"][flag]
    else: data["safety_flags"][flag] = {"false": False, "integer": 1, "string": "true"}[mode]
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


def test_safe_extra_flag_removed_and_unsafe_extra_rejected():
    data = valid_response(); data["safety_flags"]["safe_extra"] = True
    result = module.validate_candidate_review_manual_research_response(data)
    assert result.is_valid and "safe_extra" not in result.safety_flags
    trap = "NEVER_ECHO_BUY_PRIVATE_KEY_MNEMONIC_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_SCORING_MODEL_CALL_PROBABILITY_ESTIMATE"
    data = valid_response(); data["safety_flags"]["extra"] = trap
    result = module.validate_candidate_review_manual_research_response(data)
    assert_neutral(result, trap)
    with pytest.raises(ValueError, match="^INVALID_MANUAL_RESEARCH_RESPONSE$") as exc:
        module.assert_candidate_review_manual_research_response(data)
    assert trap not in str(exc.value)


@pytest.mark.parametrize("permission", [
    "authorizes", "approved for", "may execute", "citations are verified",
    "factually correct", "recommended action",
])
def test_notice_permission_and_remainder_rejected(permission):
    data = valid_response(); data["non_authority_notice"] += "; " + permission
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("fragment", NOTICE_FRAGMENTS)
def test_notice_requires_every_fragment(fragment):
    data = valid_response(); data["non_authority_notice"] = "; ".join(
        item for item in NOTICE_FRAGMENTS if item != fragment)
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("field,value", [
    ("evidence_for", ["buy this outcome"]),
    ("source_request_reference", "private-key material"),
    ("operator_review_notes", "merge-ready"),
    ("source_summary", "generated response"),
    ("limitations", ["storage_path available"]),
])
def test_forbidden_variants_fail_closed(field, value):
    data = valid_response(); data[field] = value
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("key", [
    "raw_metadata", "free-form-metadata", "caller metadata", "generated_response",
    "model-response", "tool_plan", "response_payload",
])
def test_recursive_raw_metadata_keys_rejected(key):
    data = valid_response(); data["safety_flags"][key] = "safe text"
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


@pytest.mark.parametrize("key", ["recommendation", "probability_estimate", "model_output"])
def test_unknown_authority_fields_rejected(key):
    data = valid_response(); data[key] = "safe text"
    assert_neutral(module.validate_candidate_review_manual_research_response(data))


def test_build_and_assert_delegate_to_exact_contract():
    data = valid_response()
    assert module.build_candidate_review_manual_research_response(data).is_valid
    assert module.assert_candidate_review_manual_research_response(data).is_valid
