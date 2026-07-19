from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from src.data_layer import hermes_candidate_review_assisted_research_local_dry_run_harness as harness
from src.data_layer import hermes_candidate_review_manual_research_response as wp133


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "hermes_candidate_review_assisted_research_gold_cases.json"
TRAP = "TEMP_SMOKE_NEVER_ECHO_PRIVATE_KEY_BUY_ORDER_PROVIDER_MODEL_RAW_OUTPUT"
NOTICE = "; ".join((
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


def load_one_case() -> tuple[dict[str, Any], bytes]:
    before = FIXTURE.read_bytes()
    fixture = json.loads(before.decode("utf-8"))
    selected = [case for case in fixture["cases"] if case["case_id"] == "GC-P01-COMPLETE-SUPPORTED"]
    assert len(selected) == 1
    return selected[0], before


def dry_run_input(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": "WP145-TEMP-SMOKE-001",
        "configuration_version": "WP145-LOCAL-OFFLINE-V1",
        "case_bundle": case,
        "permission_profile": {
            flag: True for flag in harness.REQUIRED_ASSISTED_RESEARCH_LOCAL_PERMISSION_FLAGS
        },
        "budget_profile": dict(harness.ASSISTED_RESEARCH_LOCAL_SINGLE_RUN_BUDGET),
        "output_policy": dict(harness.ASSISTED_RESEARCH_LOCAL_OUTPUT_POLICY),
        "human_review_required": True,
        "non_authority_notice": harness.ASSISTED_RESEARCH_LOCAL_NON_AUTHORITY_NOTICE,
    }


def response() -> dict[str, Any]:
    return {
        "response_id": "response-wp145-temp-smoke",
        "source_wp_context": "WP145",
        "source_request_reference": "synthetic-request-P01",
        "source_briefing_packet_reference": "synthetic-briefing-P01",
        "selected_candidate_reference": "synthetic-case-P01",
        "response_label": "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "research_question": "What conclusion is supported by the supplied synthetic excerpts?",
        "research_question_type": "synthetic supplied excerpt review",
        "question_restatement": "Assess only the supplied invented excerpts.",
        "source_summary": "Two supplied synthetic labels state the same bounded condition.",
        "resolution_rule_analysis": "The invented labels align on the stated condition.",
        "evidence_for": ["Both supplied invented labels support the stated condition."],
        "evidence_against": ["No contrary invented excerpt was supplied."],
        "source_conflicts": ["No conflict appears within the supplied invented excerpts."],
        "uncertainties": ["The exercise cannot establish real world truth."],
        "known_missing_data": ["No external material was supplied or considered."],
        "falsification_checks_performed": ["Compared the two supplied invented labels."],
        "limitations": ["Only the supplied synthetic content was considered."],
        "what_would_change_the_conclusion": ["A contrary supplied synthetic excerpt."],
        "operator_review_notes": "Human review remains required for this bounded draft.",
        "cited_source_references": ["Synthetic primary label P01-A", "Synthetic secondary label P01-B"],
        "source_assessment_labels": ["PRIMARY_SOURCE_REVIEWED"],
        "completion_labels": ["REQUIRED_SECTIONS_PRESENT", "HUMAN_REVIEW_PENDING"],
        "response_sections": [
            "QUESTION_RESTATEMENT", "SOURCE_SUMMARY", "EVIDENCE_FOR", "EVIDENCE_AGAINST",
            "UNCERTAINTIES", "LIMITATIONS", "OPERATOR_REVIEW_NOTES",
        ],
        "operator_next_manual_step": "Human checks the bounded synthetic draft.",
        "reviewer_acknowledgement": "Human review remains pending.",
        "human_review_required": True,
        "created_by_operator_note": "Explicit synthetic test adapter content.",
        "non_authority_notice": NOTICE,
        "safety_flags": {flag: True for flag in wp133.REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS},
    }


def review() -> dict[str, Any]:
    return {
        "reviewer_outcome": "ACCEPTABLE_FOR_BOUNDED_DRY_RUN_EVIDENCE",
        "human_review_complete": True,
        "human_review_required": True,
        "reviewer_note": "Human checked the bounded synthetic draft and recorded this acknowledgement.",
    }


class OneCallAdapter:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls = 0

    def __call__(self, envelope: object) -> object:
        self.calls += 1
        assert self.calls == 1
        assert set(envelope) == set(harness._ENVELOPE_FIELDS)  # type: ignore[arg-type]
        return copy.deepcopy(self.output)


def assert_failed(result: harness.AssistedResearchLocalDryRunResult, tmp_path: Path, before: bytes) -> None:
    assert result.valid is False
    assert result.state_trace[-2:] == ("TEARDOWN_COMPLETE", "STOPPED_FAILED_CLOSED")
    assert result.teardown_complete is True
    assert not list(tmp_path.iterdir())
    assert FIXTURE.read_bytes() == before
    assert not any((
        result.network_used, result.credential_used, result.hermes_used,
        result.provider_call_used, result.persistent_output_created,
        result.downstream_record_created,
    ))


def test_exact_one_case_local_no_network_temp_smoke(tmp_path: Path) -> None:
    case, fixture_before = load_one_case()
    data = dry_run_input(case)
    data_before = copy.deepcopy(data)
    adapter = OneCallAdapter(response())
    result = harness.run_assisted_research_local_no_network_dry_run(
        dry_run_input=data,
        fake_adapter=adapter,
        human_review_acknowledgement=review(),
    )
    assert result.valid is True
    assert result.case_id == "GC-P01-COMPLETE-SUPPORTED"
    assert result.state_trace == harness.ASSISTED_RESEARCH_LOCAL_DRY_RUN_STATES[:-1]
    assert result.terminal_state == "COMPLETED"
    assert adapter.calls == 1
    assert result.input_unchanged is True and data == data_before
    assert result.deterministic_validation_passed is True
    assert result.rubric_evaluation_complete is True
    assert result.human_review_complete is result.teardown_complete is True
    assert result.fake_adapter_only is True
    assert not any((
        result.network_used, result.credential_used, result.hermes_used,
        result.provider_call_used, result.persistent_output_created,
        result.downstream_record_created,
    ))
    assert result.errors == result.warnings == ()
    assert set(result.sanitized_evidence) == {
        "experiment_id", "case_id", "configuration_version", "fixture_pack_version",
        "rubric_version", "adapter_kind", "adapter_call_count",
        "deterministic_validation", "hard_gate_results", "bounded_test_evaluation",
        "reviewer_outcome", "stop_reason", "teardown_result",
    }
    assert all(result.sanitized_evidence["hard_gate_results"].values())
    assert not list(tmp_path.iterdir())
    assert FIXTURE.read_bytes() == fixture_before


def test_adapter_exception_temp_smoke_fails_closed(tmp_path: Path) -> None:
    case, fixture_before = load_one_case()

    class ExplodingAdapter:
        calls = 0

        def __call__(self, envelope: object) -> object:
            self.calls += 1
            raise RuntimeError(TRAP)

    adapter = ExplodingAdapter()
    result = harness.run_assisted_research_local_no_network_dry_run(
        dry_run_input=dry_run_input(case),
        fake_adapter=adapter,
        human_review_acknowledgement=review(),
    )
    assert_failed(result, tmp_path, fixture_before)
    assert adapter.calls == 1
    assert TRAP not in repr(result)


def test_invalid_output_temp_smoke_fails_closed(tmp_path: Path) -> None:
    case, fixture_before = load_one_case()
    output = response()
    del output["response_id"]
    adapter = OneCallAdapter(output)
    result = harness.run_assisted_research_local_no_network_dry_run(
        dry_run_input=dry_run_input(case),
        fake_adapter=adapter,
        human_review_acknowledgement=review(),
    )
    assert_failed(result, tmp_path, fixture_before)
    assert adapter.calls == 1


def test_unsafe_no_echo_temp_smoke_fails_closed(tmp_path: Path) -> None:
    case, fixture_before = load_one_case()
    output = response()
    output["source_summary"] = TRAP
    adapter = OneCallAdapter(output)
    result = harness.run_assisted_research_local_no_network_dry_run(
        dry_run_input=dry_run_input(case),
        fake_adapter=adapter,
        human_review_acknowledgement=review(),
    )
    assert_failed(result, tmp_path, fixture_before)
    assert adapter.calls == 1
    assert TRAP not in repr(result)


def test_failed_review_temp_smoke_fails_closed(tmp_path: Path) -> None:
    case, fixture_before = load_one_case()
    acknowledgement = review()
    acknowledgement["human_review_complete"] = False
    adapter = OneCallAdapter(response())
    result = harness.run_assisted_research_local_no_network_dry_run(
        dry_run_input=dry_run_input(case),
        fake_adapter=adapter,
        human_review_acknowledgement=acknowledgement,
    )
    assert_failed(result, tmp_path, fixture_before)
    assert adapter.calls == 1
    assert result.deterministic_validation_passed is True
    assert result.rubric_evaluation_complete is True
    assert result.human_review_complete is False
