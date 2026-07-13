import ast
import copy
from pathlib import Path

import pytest

from src.data_layer.hermes_candidate_review_advisory_output_validation_receipt import (
    REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS,
    REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS,
    REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS,
    assert_candidate_review_advisory_output_validation_receipt,
    build_candidate_review_advisory_output_validation_receipt,
    validate_candidate_review_advisory_output_validation_receipt,
)
from src.data_layer.hermes_candidate_review_manual_research_request import (
    REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS,
    REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS,
    assert_candidate_review_manual_research_request,
    build_candidate_review_manual_research_request,
    validate_candidate_review_manual_research_request,
)
from src.data_layer.hermes_candidate_review_manual_research_response import (
    REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS,
    REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS,
    assert_candidate_review_manual_research_response,
    build_candidate_review_manual_research_response,
    validate_candidate_review_manual_research_response,
)
from src.data_layer.hermes_candidate_review_research_question_record import (
    REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS,
    REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS,
    REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS,
    assert_candidate_review_research_question_record,
    build_candidate_review_research_question_record,
    validate_candidate_review_research_question_record,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_MODEL_CALL_PROBABILITY_ESTIMATE"


def _question_preflight_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS}


def _question_safety_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS}


def _question_notice() -> str:
    return (
        "Advisory-only manual local offline planning record. It is not a trade signal, "
        "not strategy promotion, not paper readiness, not live readiness, not execution "
        "authority, not risk authority, not order authority, not PR approval, not merge "
        "readiness, not credential permission, not account access, not private-state "
        "permission, not Hermes runtime authority, and not prompt runner authority."
    )


def _question_record() -> dict[str, object]:
    return {
        "record_id": "synthetic-question-record-137",
        "source_wp_context": {"intake_wp": "WP118", "contract_wp": "WP120"},
        "selected_candidate_reference": "synthetic-candidate-reference-137",
        "intake_basis": _question_preflight_flags(),
        "research_question": "Which synthetic source reference requires provenance review?",
        "research_question_type": "SOURCE_PROVENANCE_WEAKNESS",
        "evidence_references_to_check": ["synthetic-source-reference-a", "synthetic-source-reference-b"],
        "uncertainty_notes": ["Synthetic provenance remains uncertain."],
        "known_missing_data": ["One synthetic publication date is absent."],
        "limitations": ["Synthetic caller content only."],
        "falsification_checks_to_perform": ["Compare the supplied synthetic references."],
        "forbidden_interpretation_flags": {"not_a_signal": True, "not_authority": True},
        "human_review_required": True,
        "next_manual_step": "Manually inspect the supplied synthetic references.",
        "created_by_operator_note": "Explicit synthetic caller question fixture.",
        "non_authority_notice": _question_notice(),
        "safety_flags": _question_safety_flags(),
    }


def _request_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS}


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


def _request() -> dict[str, object]:
    return {
        "request_id": "synthetic-request-137",
        "source_wp_context": "WP137 synthetic request exercise",
        "source_briefing_packet_reference": "synthetic-briefing-reference-137",
        "selected_candidate_reference": "synthetic-candidate-reference-137",
        "request_label": "REQUEST_READY_FOR_MANUAL_RESEARCH",
        "research_question": "Which synthetic source reference requires provenance review?",
        "research_question_type": "SOURCE_PROVENANCE_WEAKNESS",
        "approved_source_references": ["synthetic-source-reference-a", "synthetic-source-reference-b"],
        "source_requirement_labels": ["PRIMARY_SOURCE_REQUIRED", "SOURCE_PROVENANCE_REQUIRED"],
        "citation_requirement_labels": ["CITATION_REQUIRED_FOR_EACH_MATERIAL_CLAIM"],
        "evidence_requirement_labels": ["EVIDENCE_FOR_REQUIRED", "EVIDENCE_AGAINST_REQUIRED"],
        "required_response_sections": ["QUESTION_RESTATEMENT", "SOURCE_SUMMARY"],
        "research_scope": "Review only supplied synthetic references.",
        "known_uncertainties": "Synthetic provenance remains uncertain.",
        "known_missing_data": "One synthetic publication date is absent.",
        "falsification_checks_to_perform": ["Compare the supplied synthetic references."],
        "operator_research_instructions": "Manually inspect only synthetic references.",
        "operator_review_instructions": "A human checks the synthetic record.",
        "refusal_behavior": "Refuse unsafe or out-of-scope content.",
        "failure_behavior": "Return neutral failure without findings.",
        "max_source_count": 2, "max_citation_count": 4, "max_output_words": 500,
        "timeout_seconds": 60, "max_retry_count": 0,
        "human_review_required": True,
        "created_by_operator_note": "Explicit synthetic caller request fixture.",
        "non_authority_notice": _request_notice(),
        "safety_flags": _request_flags(),
    }


def _response_flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}


def _response_notice() -> str:
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


def _response() -> dict[str, object]:
    return {
        "response_id": "synthetic-response-137",
        "source_wp_context": "WP137 synthetic response exercise",
        "source_request_reference": "synthetic-request-137",
        "source_briefing_packet_reference": "synthetic-briefing-reference-137",
        "selected_candidate_reference": "synthetic-candidate-reference-137",
        "response_label": "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "research_question": "Which synthetic source reference requires provenance review?",
        "research_question_type": "SOURCE_PROVENANCE_WEAKNESS",
        "question_restatement": "Inspect the supplied synthetic references.",
        "source_summary": "Caller recorded synthetic source material.",
        "resolution_rule_analysis": "Caller recorded synthetic provenance details.",
        "evidence_for": ["Synthetic item A supports the recorded provenance."],
        "evidence_against": ["Synthetic item B disputes the recorded provenance."],
        "source_conflicts": ["Synthetic items use different publication dates."],
        "uncertainties": ["A synthetic update remains unavailable."],
        "known_missing_data": ["One synthetic publication date is absent."],
        "falsification_checks_performed": ["Compared the supplied synthetic references."],
        "limitations": ["Only synthetic caller content was considered."],
        "what_would_change_the_conclusion": ["A contrary synthetic publication record."],
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


def _receipt_flags() -> dict[str, bool]:
    return {flag: True for flag in (*REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS, *REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS)}


def _receipt_notice() -> str:
    return (
        "Advisory only manual local offline receipt; human review required. It is not fact without "
        "source review, not a trade signal, not strategy promotion, not paper readiness, not live "
        "readiness, not execution authority, not risk authority, not order authority, not PR approval, "
        "not merge readiness, not credential permission, not account access, not private-state access, "
        "not Hermes runtime authority, not prompt runner authority, and not storage/writer/export authority."
    )


def _receipt() -> dict[str, object]:
    return {
        "receipt_id": "synthetic-receipt-137",
        "source_wp_context": {"research_question_wp": "WP121", "receipt_wp": "WP122"},
        "source_research_question_record_reference": {
            "record_id": "synthetic-question-record-137",
            "source_module": "hermes_candidate_review_research_question_record",
        },
        "advisory_output_reference": {
            "artifact_id": "synthetic-response-137",
            "operator_reference": "manual-synthetic-response-reference-137",
        },
        "receipt_label": "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE",
        "source_references_checked": ["synthetic-source-reference-a", "synthetic-source-reference-b"],
        "unsupported_claims": ["No unsupported claims accepted."],
        "uncertainty_review": ["Uncertainty evidence reviewed separately."],
        "limitations_review": ["Limitation evidence reviewed separately."],
        "missing_data_review": ["Missing-data evidence reviewed separately."],
        "falsification_review": ["Falsification evidence reviewed separately."],
        "human_review_notes": ["Human reviewer performed synthetic source review."],
        "follow_up_research_tasks": ["Manually inspect one additional synthetic source."],
        "forbidden_interpretation_flags": {"not_a_signal": True, "not_authority": True},
        "human_review_required": True,
        "non_authority_notice": _receipt_notice(),
        "safety_flags": _receipt_flags(),
    }


def test_positive_four_record_manual_lineage_and_empty_tmp_path(tmp_path: Path) -> None:
    question, request, response, receipt = _question_record(), _request(), _response(), _receipt()
    before = copy.deepcopy((question, request, response, receipt))

    validations = (
        validate_candidate_review_research_question_record(question),
        validate_candidate_review_manual_research_request(request),
        validate_candidate_review_manual_research_response(response),
        validate_candidate_review_advisory_output_validation_receipt(receipt),
    )
    results = (
        build_candidate_review_research_question_record(question),
        build_candidate_review_manual_research_request(request),
        build_candidate_review_manual_research_response(response),
        build_candidate_review_advisory_output_validation_receipt(receipt),
    )
    assert all(item.is_valid for item in (*validations, *results))
    assert (question, request, response, receipt) == before
    q, req, res, rec = results
    assert set(q.record) == set(REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS)
    assert set(req.research_request) == set(REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS)
    assert set(res.research_response) == set(REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS)
    assert set(rec.receipt) == set(REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS)
    assert all(item.errors == item.warnings == () for item in results)
    assert q.safety_flags == _question_safety_flags()
    assert req.safety_flags == _request_flags()
    assert res.safety_flags == _response_flags()
    assert rec.safety_flags == {flag: True for flag in REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS}
    assert receipt["safety_flags"] == _receipt_flags()

    qr, rr, rs, rc = q.record, req.research_request, res.research_response, rec.receipt
    assert qr["record_id"] == rc["source_research_question_record_reference"]["record_id"]
    assert qr["selected_candidate_reference"] == rr["selected_candidate_reference"]
    assert qr["selected_candidate_reference"] == rs["selected_candidate_reference"]
    assert qr["research_question"] == rr["research_question"]
    assert qr["research_question"] == rs["research_question"]
    assert qr["research_question_type"] == rr["research_question_type"]
    assert qr["research_question_type"] == rs["research_question_type"]
    assert rr["request_id"] == rs["source_request_reference"]
    assert rr["source_briefing_packet_reference"] == rs["source_briefing_packet_reference"]
    assert rr["required_response_sections"] == rs["response_sections"]
    assert all(source in rr["approved_source_references"] for source in rs["cited_source_references"])
    assert rs["response_id"] == rc["advisory_output_reference"]["artifact_id"]
    assert rs["cited_source_references"] == rc["source_references_checked"]
    assert all(item["human_review_required"] is True for item in (qr, rr, rs, rc))
    assert rs["uncertainties"] != rc["uncertainty_review"]
    assert rs["limitations"] != rc["limitations_review"]
    assert rs["known_missing_data"] != rc["missing_data_review"]
    assert rs["falsification_checks_performed"] != rc["falsification_review"]
    forbidden_keys = {"chain", "session", "linkage", "authority_output", "generated_record"}
    assert all(not (forbidden_keys & set(item)) for item in (qr, rr, rs, rc))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("case", [
    "question_record_reference", "question_to_request_candidate", "question_to_response_candidate",
    "question_to_request_text", "question_to_response_text", "question_to_request_type",
    "question_to_response_type", "request_reference", "briefing_reference", "response_sections",
    "cited_reference_outside_request", "response_receipt_artifact", "receipt_checked_sources",
])
def test_contract_valid_records_can_be_lineage_inconsistent(case: str, tmp_path: Path) -> None:
    question, request, response, receipt = _question_record(), _request(), _response(), _receipt()
    if case == "question_record_reference": receipt["source_research_question_record_reference"]["record_id"] = "synthetic-question-record-other"
    elif case == "question_to_request_candidate": request["selected_candidate_reference"] = "synthetic-candidate-other"
    elif case == "question_to_response_candidate": response["selected_candidate_reference"] = "synthetic-candidate-other"
    elif case == "question_to_request_text": request["research_question"] = "Which synthetic reference has a different provenance record?"
    elif case == "question_to_response_text": response["research_question"] = "Which synthetic reference has a different provenance record?"
    elif case == "question_to_request_type": request["research_question_type"] = "EVIDENCE_QUALITY_GAP"
    elif case == "question_to_response_type": response["research_question_type"] = "EVIDENCE_QUALITY_GAP"
    elif case == "request_reference": response["source_request_reference"] = "synthetic-request-other"
    elif case == "briefing_reference": response["source_briefing_packet_reference"] = "synthetic-briefing-other"
    elif case == "response_sections": response["response_sections"] = ["QUESTION_RESTATEMENT"]
    elif case == "cited_reference_outside_request":
        response["cited_source_references"] = ["synthetic-source-reference-c"]
        receipt["source_references_checked"] = ["synthetic-source-reference-c"]
    elif case == "response_receipt_artifact": receipt["advisory_output_reference"]["artifact_id"] = "synthetic-response-other"
    elif case == "receipt_checked_sources": receipt["source_references_checked"] = ["synthetic-source-reference-c"]

    q = validate_candidate_review_research_question_record(question)
    req = validate_candidate_review_manual_research_request(request)
    res = validate_candidate_review_manual_research_response(response)
    rec = validate_candidate_review_advisory_output_validation_receipt(receipt)
    assert all(item.is_valid for item in (q, req, res, rec))
    checks = [
        q.record["record_id"] == rec.receipt["source_research_question_record_reference"]["record_id"],
        q.record["selected_candidate_reference"] == req.research_request["selected_candidate_reference"],
        q.record["selected_candidate_reference"] == res.research_response["selected_candidate_reference"],
        q.record["research_question"] == req.research_request["research_question"],
        q.record["research_question"] == res.research_response["research_question"],
        q.record["research_question_type"] == req.research_request["research_question_type"],
        q.record["research_question_type"] == res.research_response["research_question_type"],
        req.research_request["request_id"] == res.research_response["source_request_reference"],
        req.research_request["source_briefing_packet_reference"] == res.research_response["source_briefing_packet_reference"],
        req.research_request["required_response_sections"] == res.research_response["response_sections"],
        all(source in req.research_request["approved_source_references"] for source in res.research_response["cited_source_references"]),
        res.research_response["response_id"] == rec.receipt["advisory_output_reference"]["artifact_id"],
        res.research_response["cited_source_references"] == rec.receipt["source_references_checked"],
    ]
    assert checks.count(False) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("record_name", ["question", "request", "response", "receipt"])
def test_each_contract_rejects_false_human_review(record_name: str, tmp_path: Path) -> None:
    records = {"question": _question_record(), "request": _request(), "response": _response(), "receipt": _receipt()}
    records[record_name]["human_review_required"] = False
    validators = {
        "question": validate_candidate_review_research_question_record,
        "request": validate_candidate_review_manual_research_request,
        "response": validate_candidate_review_manual_research_response,
        "receipt": validate_candidate_review_advisory_output_validation_receipt,
    }
    result = validators[record_name](records[record_name])
    assert result.is_valid is False
    assert getattr(result, {"question": "record", "request": "research_request", "response": "research_response", "receipt": "receipt"}[record_name]) == {}
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("record_name,field", [
    ("question", "research_question"), ("request", "research_question"),
    ("response", "research_question"), ("receipt", "human_review_notes"),
])
def test_each_contract_rejects_unsafe_content_without_echo(record_name: str, field: str, tmp_path: Path) -> None:
    records = {"question": _question_record(), "request": _request(), "response": _response(), "receipt": _receipt()}
    records[record_name][field] = [TRAP] if record_name == "receipt" else TRAP
    validators = {
        "question": validate_candidate_review_research_question_record,
        "request": validate_candidate_review_manual_research_request,
        "response": validate_candidate_review_manual_research_response,
        "receipt": validate_candidate_review_advisory_output_validation_receipt,
    }
    assertions = {
        "question": assert_candidate_review_research_question_record,
        "request": assert_candidate_review_manual_research_request,
        "response": assert_candidate_review_manual_research_response,
        "receipt": assert_candidate_review_advisory_output_validation_receipt,
    }
    result = validators[record_name](records[record_name])
    assert result.is_valid is False and TRAP not in repr(result)
    with pytest.raises(ValueError) as exc:
        assertions[record_name](records[record_name])
    assert TRAP not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_ast_reviewer_guard_proves_fixture_independence_and_no_side_effects() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    helper_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_")}
    expected = {
        "_question_preflight_flags", "_question_safety_flags", "_question_notice", "_question_record",
        "_request_flags", "_request_notice", "_request", "_response_flags", "_response_notice",
        "_response", "_receipt_flags", "_receipt_notice", "_receipt",
    }
    assert helper_names == expected
    fixtures = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"_question_record", "_request", "_response", "_receipt"}}
    assert all(not node.args.args and not node.args.kwonlyargs for node in fixtures.values())
    for name, node in fixtures.items():
        other_fixtures = set(fixtures) - {name}
        assert not (other_fixtures & {child.id for child in ast.walk(node) if isinstance(child, ast.Name)})
    app_modules = {node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src.")}
    assert app_modules == {
        "src.data_layer.hermes_candidate_review_research_question_record",
        "src.data_layer.hermes_candidate_review_manual_research_request",
        "src.data_layer.hermes_candidate_review_manual_research_response",
        "src.data_layer.hermes_candidate_review_advisory_output_validation_receipt",
    }
    forbidden_name_parts = ("adapter", "convert", "bridge", "transfer", "map", "chain", "session", "linkage", "populate", "generate", "infer", "default", "repair", "serialize", "write", "export")
    assert all(not any(part in name.lower() for part in forbidden_name_parts) for name in helper_names)
    assert not any(isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    forbidden_imports = {"subprocess", "os", "socket", "http", "requests", "urllib", "time", "datetime", "uuid", "random", "database", "writer", "storage", "export", "cli"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not (imports & forbidden_imports)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not any(isinstance(call.func, ast.Name) and call.func.id in {"open", "write"} for call in calls)
    assert not any(isinstance(call.func, ast.Name) and call.func.id in fixtures and (call.args or call.keywords) for call in calls)
