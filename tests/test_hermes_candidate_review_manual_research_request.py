from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer import hermes_candidate_review_manual_research_request as subject


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_SCORING_MODEL_CALL"
SCALARS = (
    "request_id", "source_wp_context", "source_briefing_packet_reference",
    "selected_candidate_reference", "research_question", "research_question_type",
    "research_scope", "known_uncertainties", "known_missing_data",
    "operator_research_instructions", "operator_review_instructions", "refusal_behavior",
    "failure_behavior", "created_by_operator_note", "non_authority_notice",
)
SEQUENCES = (
    "approved_source_references", "source_requirement_labels", "citation_requirement_labels",
    "evidence_requirement_labels", "required_response_sections", "falsification_checks_to_perform",
)
NOTICE = "; ".join((
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


def canonical() -> dict[str, object]:
    return {
        "request_id": "req-132", "source_wp_context": "WP132",
        "source_briefing_packet_reference": "briefing-public-1",
        "selected_candidate_reference": "candidate-public-1",
        "request_label": "REQUEST_READY_FOR_MANUAL_RESEARCH",
        "research_question": "What public evidence resolves the stated question?",
        "research_question_type": "resolution review",
        "approved_source_references": ["public-source-a", "public-source-b"],
        "source_requirement_labels": ["PRIMARY_SOURCE_REQUIRED", "SOURCE_DATE_REQUIRED"],
        "citation_requirement_labels": ["CITATION_REQUIRED_FOR_EACH_MATERIAL_CLAIM"],
        "evidence_requirement_labels": ["EVIDENCE_FOR_REQUIRED", "EVIDENCE_AGAINST_REQUIRED"],
        "required_response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "research_scope": "Review only the supplied public references.",
        "known_uncertainties": "Publication timing remains uncertain.",
        "known_missing_data": "One public update may be absent.",
        "falsification_checks_to_perform": ["Check whether the dated source conflicts."],
        "operator_research_instructions": "Manually inspect supplied references.",
        "operator_review_instructions": "Human checks citations and limitations.",
        "refusal_behavior": "Refuse unsafe or out-of-scope content.",
        "failure_behavior": "Return a neutral failure without findings.",
        "max_source_count": 10, "max_citation_count": 20, "max_output_words": 1000,
        "timeout_seconds": 60, "max_retry_count": 0, "human_review_required": True,
        "created_by_operator_note": "Explicit synthetic caller content.",
        "non_authority_notice": NOTICE,
        "safety_flags": {flag: True for flag in subject.REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS},
    }


def assert_neutral(result: object) -> None:
    assert result.is_valid is False
    assert result.research_request == {}
    assert result.warnings == ()
    assert result.request_label is None
    assert result.source_requirement_labels == result.citation_requirement_labels == ()
    assert result.evidence_requirement_labels == result.required_response_sections == ()
    assert result.safety_flags == {}
    assert TRAP not in repr(result)


def test_exact_public_surface_dataclass_and_stdlib_imports():
    expected_constants = {
        "ALLOWED_MANUAL_RESEARCH_REQUEST_LABELS", "ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS",
        "ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS", "ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS",
        "ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS", "REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS",
        "REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS",
    }
    assert {name for name in vars(subject) if name.isupper() and not name.startswith("_")} == expected_constants
    assert [f.name for f in fields(subject.HermesCandidateReviewManualResearchRequestResult)] == [
        "is_valid", "research_request", "errors", "warnings", "request_label",
        "source_requirement_labels", "citation_requirement_labels", "evidence_requirement_labels",
        "required_response_sections", "safety_flags",
    ]
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"__future__", "dataclasses", "typing"}
    public_functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}
    assert public_functions == {
        "validate_candidate_review_manual_research_request",
        "build_candidate_review_manual_research_request",
        "assert_candidate_review_manual_research_request",
    }


def test_valid_request_is_sanitized_immutable_and_order_preserving():
    data = canonical()
    original_sources = list(data["approved_source_references"])
    data["safety_flags"]["extra"] = True
    result = subject.build_candidate_review_manual_research_request(data)
    assert result.is_valid and result.errors == result.warnings == ()
    assert result.research_request["approved_source_references"] == original_sources
    assert result.source_requirement_labels == tuple(data["source_requirement_labels"])
    assert "extra" not in result.safety_flags
    result.research_request["approved_source_references"].append("new")
    assert data["approved_source_references"] == original_sources
    assert not any(k in result.research_request for k in ("priority", "fetched_evidence", "response"))


@pytest.mark.parametrize("label", subject.ALLOWED_MANUAL_RESEARCH_REQUEST_LABELS)
def test_every_request_label(label):
    data = canonical(); data["request_label"] = label
    assert subject.validate_candidate_review_manual_research_request(data).is_valid


@pytest.mark.parametrize("field,allowed", [
    ("source_requirement_labels", subject.ALLOWED_RESEARCH_SOURCE_REQUIREMENT_LABELS),
    ("citation_requirement_labels", subject.ALLOWED_RESEARCH_CITATION_REQUIREMENT_LABELS),
    ("evidence_requirement_labels", subject.ALLOWED_RESEARCH_EVIDENCE_REQUIREMENT_LABELS),
    ("required_response_sections", subject.ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS),
])
def test_every_allowed_label_family(field, allowed):
    for label in allowed:
        data = canonical(); data[field] = [label]
        assert subject.validate_candidate_review_manual_research_request(data).is_valid


@pytest.mark.parametrize("field", subject.REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS)
def test_every_required_field(field):
    data = canonical(); del data[field]
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("field", SCALARS)
@pytest.mark.parametrize("value", [None, 1, True, b"x", {}, [], (), set(), " "])
def test_scalar_wrong_shape_matrix(field, value):
    data = canonical(); data[field] = value
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("field", SEQUENCES)
@pytest.mark.parametrize("value", [None, "x", [], (), {}, {"x"}, [""], [1], [True], [{"generated_response": "safe"}]])
def test_sequence_wrong_shape_matrix(field, value):
    data = canonical(); data[field] = value
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("field,low,high", [
    ("max_source_count", 1, 50), ("max_citation_count", 1, 100),
    ("max_output_words", 100, 20_000), ("timeout_seconds", 1, 3_600),
    ("max_retry_count", 0, 5),
])
def test_integer_bounds_and_wrong_types(field, low, high):
    for value in (low, high):
        data = canonical(); data[field] = value
        assert subject.validate_candidate_review_manual_research_request(data).is_valid
    for value in (low - 1, high + 1, True, 1.0, str(low), {}, []):
        data = canonical(); data[field] = value
        assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_human_review_exact_true(value):
    data = canonical(); data["human_review_required"] = value
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


def test_safety_flags_missing_false_truthy_and_extra_sanitization():
    flag = subject.REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS[0]
    for value in (False, 1, "true"):
        data = canonical(); data["safety_flags"][flag] = value
        assert_neutral(subject.validate_candidate_review_manual_research_request(data))
    data = canonical(); del data["safety_flags"][flag]
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("mutation", ["missing", "permission", "remainder"])
def test_notice_cases(mutation):
    data = canonical()
    if mutation == "missing": data["non_authority_notice"] = NOTICE.replace("request contract only", "")
    if mutation == "permission": data["non_authority_notice"] = NOTICE + "; tools may be invoked"
    if mutation == "remainder": data["non_authority_notice"] = NOTICE + "; merge ready"
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("unsafe", [
    "buy", "private key", "merge ready", "prompt runner", "tool call", "storage path",
    "scoring", "model call", "scheduler", "generated response", "CLI command",
])
def test_recursive_forbidden_families(unsafe):
    data = canonical(); data["approved_source_references"] = [{"nested": unsafe}]
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


@pytest.mark.parametrize("raw_key", [
    "raw_metadata", "free_form_metadata", "caller_metadata", "raw_input", "model_response",
    "prompt", "completion", "tool_plan", "tool_call", "provider_response", "metadata", "context",
])
def test_recursive_raw_metadata(raw_key):
    data = canonical(); data["approved_source_references"] = [{raw_key: "safe"}]
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


def test_reviewer_traps_unknown_fields_missing_question_and_no_echo():
    traps = []
    data = canonical(); data["research_question"] = {"generated_prompt": "safe"}; traps.append(data)
    data = canonical(); data["operator_research_instructions"] = {"tool_call": {}}; traps.append(data)
    data = canonical(); data["approved_source_references"] = ["private key text"]; traps.append(data)
    data = canonical(); data["required_response_sections"] = [{"generated_response": {}}]; traps.append(data)
    data = canonical(); data["max_retry_count"] = True; traps.append(data)
    data = canonical(); data["timeout_seconds"] = "60"; traps.append(data)
    for extra in ("response", "model_output", "tool_call"):
        data = canonical(); data[extra] = TRAP; traps.append(data)
    data = canonical(); del data["research_question"]; traps.append(data)
    data = canonical(); data["request_id"] = TRAP; traps.append(data)
    for data in traps:
        result = subject.validate_candidate_review_manual_research_request(data)
        assert_neutral(result)
        with pytest.raises(ValueError, match="^INVALID_MANUAL_RESEARCH_REQUEST$") as exc:
            subject.assert_candidate_review_manual_research_request(data)
        assert TRAP not in repr(exc.value)


@pytest.mark.parametrize("field", [
    "source_requirement_labels", "citation_requirement_labels",
    "evidence_requirement_labels", "required_response_sections",
])
def test_unknown_empty_duplicate_labels(field):
    for value in ([], ["UNKNOWN_LABEL"]):
        data = canonical(); data[field] = value
        assert_neutral(subject.validate_candidate_review_manual_research_request(data))
    data = canonical(); data[field] = [data[field][0], data[field][0]]
    assert_neutral(subject.validate_candidate_review_manual_research_request(data))


def test_no_runtime_storage_export_cli_tool_or_io_authority():
    text = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert not any(isinstance(node, (ast.Import, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    forbidden_public = {"fetch", "browse", "execute", "run", "write", "store", "export", "cli", "schedule", "invoke"}
    public_names = {node.name.lower() for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert not public_names & forbidden_public
