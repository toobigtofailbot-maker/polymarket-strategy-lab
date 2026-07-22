from __future__ import annotations

import ast
import copy
import dataclasses
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from src.data_layer import hermes_candidate_review_assisted_research_local_dry_run_harness as subject
from src.data_layer import hermes_candidate_review_manual_research_response as wp133


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "hermes_candidate_review_assisted_research_local_dry_run_harness.py"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "hermes_candidate_review_assisted_research_gold_cases.json"
OPERATOR_NOTE = ROOT / "docs" / "hermes_candidate_review_assisted_research_local_dry_run_harness_operator_note.md"
TRAP = "NEVER_ECHO_PRIVATE_KEY_BUY_ORDER_PROVIDER_MODEL_SOURCE_FETCHED_RAW_OUTPUT"
DEFAULT_RESPONSE = object()
WP133_NOTICE = "; ".join((
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


def selected_case() -> dict[str, Any]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    matches = [case for case in fixture["cases"] if case["case_id"] == "GC-P01-COMPLETE-SUPPORTED"]
    assert len(matches) == 1
    return matches[0]


def valid_input() -> dict[str, Any]:
    return {
        "experiment_id": "WP145-LOCAL-DRY-RUN-001",
        "configuration_version": "WP145-LOCAL-OFFLINE-V1",
        "case_bundle": selected_case(),
        "permission_profile": {
            flag: True for flag in subject.REQUIRED_ASSISTED_RESEARCH_LOCAL_PERMISSION_FLAGS
        },
        "budget_profile": dict(subject.ASSISTED_RESEARCH_LOCAL_SINGLE_RUN_BUDGET),
        "output_policy": dict(subject.ASSISTED_RESEARCH_LOCAL_OUTPUT_POLICY),
        "human_review_required": True,
        "non_authority_notice": subject.ASSISTED_RESEARCH_LOCAL_NON_AUTHORITY_NOTICE,
    }


def valid_response() -> dict[str, Any]:
    return {
        "response_id": "response-wp145-local-001",
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
        "non_authority_notice": WP133_NOTICE,
        "safety_flags": {flag: True for flag in wp133.REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS},
    }


def valid_review() -> dict[str, Any]:
    return {
        "reviewer_outcome": "ACCEPTABLE_FOR_BOUNDED_DRY_RUN_EVIDENCE",
        "human_review_complete": True,
        "human_review_required": True,
        "reviewer_note": "Human checked the bounded synthetic draft and recorded this acknowledgement.",
    }


def run(
    *,
    data: dict[str, Any] | None = None,
    response: object = DEFAULT_RESPONSE,
    review: dict[str, Any] | None = None,
) -> subject.AssistedResearchLocalDryRunResult:
    return subject.run_assisted_research_local_no_network_dry_run(
        dry_run_input=valid_input() if data is None else data,
        fake_adapter_output=(
            valid_response() if response is DEFAULT_RESPONSE else response
        ),  # type: ignore[arg-type]
        human_review_acknowledgement=valid_review() if review is None else review,
    )


def recursive_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return recursive_text({field.name: getattr(value, field.name) for field in dataclasses.fields(value)})
    if isinstance(value, dict) or hasattr(value, "items"):
        return " ".join(
            recursive_text(item)
            for pair in value.items()  # type: ignore[union-attr]
            for item in pair
        )
    if isinstance(value, (list, tuple)):
        return " ".join(recursive_text(item) for item in value)
    return str(value)


def assert_failed_closed(result: subject.AssistedResearchLocalDryRunResult, trap: str | None = None) -> None:
    assert result.valid is False
    assert result.terminal_state == "STOPPED_FAILED_CLOSED"
    assert result.state_trace[-2:] == ("TEARDOWN_COMPLETE", "STOPPED_FAILED_CLOSED")
    assert result.teardown_complete is True
    assert result.network_used is result.credential_used is result.hermes_used is False
    assert result.provider_call_used is result.persistent_output_created is False
    assert result.downstream_record_created is False
    assert result.external_callable_invoked is False
    assert result.errors and result.warnings == ()
    if trap:
        assert trap not in recursive_text(result)
        assert trap not in repr(result)


def test_exact_public_surface_state_model_and_frozen_result() -> None:
    assert subject.ASSISTED_RESEARCH_LOCAL_DRY_RUN_STATES == (
        "NOT_STARTED", "PREFLIGHT", "CASE_LOADED", "INPUT_VALIDATED",
        "PERMISSIONS_VALIDATED", "BUDGET_VALIDATED", "SESSION_ENVELOPE_BUILT",
        "EPHEMERAL_SESSION_READY", "PROVIDER_INVOCATION_PENDING",
        "UNTRUSTED_OUTPUT_CAPTURED", "DETERMINISTIC_VALIDATION_COMPLETE",
        "RUBRIC_EVALUATION_COMPLETE", "HUMAN_REVIEW_COMPLETE",
        "SANITIZED_EVIDENCE_COMPLETE", "TEARDOWN_COMPLETE", "COMPLETED",
        "STOPPED_FAILED_CLOSED",
    )
    assert subject.ASSISTED_RESEARCH_LOCAL_DRY_RUN_POSTURE == (
        "Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE",
        "Dry-run case count: 1", "Dry-run case ID: GC-P01-COMPLETE-SUPPORTED",
        "Network: FORBIDDEN", "Credentials: FORBIDDEN",
        "Hermes installation/invocation: FORBIDDEN", "Provider/model call: FORBIDDEN",
        "Stable raw input/output persistence: FORBIDDEN",
        "Temporary filesystem: PYTEST_TMP_PATH_ONLY", "Output: SANITIZED_EVIDENCE_ONLY",
        "Deterministic WP133 validation: MANDATORY",
        "Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED",
        "Automatic downstream records: FORBIDDEN",
        "Paper/live/execution authority: FORBIDDEN", "WP146 requires separate approval",
    )
    public_functions = {
        node.name for node in ast.parse(MODULE_PATH.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert public_functions == {
        "validate_assisted_research_local_dry_run_input",
        "build_assisted_research_local_session_envelope",
        "run_assisted_research_local_no_network_dry_run",
        "assert_valid_assisted_research_local_dry_run_result",
    }
    assert subject.AssistedResearchLocalDryRunResult.__dataclass_params__.frozen
    assert isinstance(subject.ASSISTED_RESEARCH_LOCAL_SINGLE_RUN_BUDGET, MappingProxyType)
    assert isinstance(subject.ASSISTED_RESEARCH_LOCAL_OUTPUT_POLICY, MappingProxyType)


def test_valid_input_and_immutable_sanitized_envelope() -> None:
    data = valid_input()
    before = copy.deepcopy(data)
    assert subject.validate_assisted_research_local_dry_run_input(data) == ()
    envelope = subject.build_assisted_research_local_session_envelope(data)
    assert data == before
    assert tuple(envelope) == subject._ENVELOPE_FIELDS
    assert envelope["case_id"] == "GC-P01-COMPLETE-SUPPORTED"
    assert envelope["wp133_required_fields"] == wp133.REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS
    forbidden = {"credential", "endpoint", "path", "provider", "model", "prompt", "raw_output"}
    assert not (set(envelope) & forbidden)
    with pytest.raises(TypeError, match="IMMUTABLE_SESSION_ENVELOPE"):
        envelope["case_id"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError, match="IMMUTABLE_SESSION_ENVELOPE"):
        envelope["budget_limits"]["max_total_calls"] = 2  # type: ignore[index]


def test_positive_run_uses_precomputed_response_and_returns_only_sanitized_evidence() -> None:
    data = valid_input()
    before = copy.deepcopy(data)
    response = valid_response()
    response_before = copy.deepcopy(response)
    result = run(data=data, response=response)
    assert result.valid is True
    assert result.state_trace == subject.ASSISTED_RESEARCH_LOCAL_DRY_RUN_STATES[:-1]
    assert result.terminal_state == "COMPLETED"
    assert response == response_before
    assert data == before and result.input_unchanged is True
    assert result.deterministic_validation_passed is True
    assert result.rubric_evaluation_complete is True
    assert result.human_review_complete is result.teardown_complete is True
    assert result.precomputed_fake_response_only is True
    assert result.external_callable_invoked is False
    assert not any((
        result.network_used, result.credential_used, result.hermes_used,
        result.provider_call_used, result.persistent_output_created,
        result.downstream_record_created,
    ))
    assert result.errors == result.warnings == ()
    assert result.sanitized_evidence["adapter_kind"] == "TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE"
    assert result.sanitized_evidence["adapter_call_count"] == 0
    assert result.sanitized_evidence["external_callable_invoked"] is False
    assert tuple(result.sanitized_evidence["hard_gate_results"]) == subject._HARD_GATE_IDS
    assert all(result.sanitized_evidence["hard_gate_results"].values())
    forbidden = {
        "raw_input", "raw_output", "raw_adapter_output", "prompt", "envelope",
        "source_excerpt", "credential", "path", "recommendation", "probability",
        "ranking", "trading_data", "downstream_record", "persistent_output",
    }
    assert not (set(result.sanitized_evidence) & forbidden)
    with pytest.raises(TypeError, match="IMMUTABLE_SESSION_ENVELOPE"):
        result.sanitized_evidence["stop_reason"] = "changed"  # type: ignore[index]
    assert subject.assert_valid_assisted_research_local_dry_run_result(result) is result


def test_repeated_runs_with_same_precomputed_response_are_deterministic() -> None:
    response = valid_response()
    first = run(response=response)
    second = run(response=response)
    assert first == second


@pytest.mark.parametrize("mutation", ["missing_case", "case_not_mapping", "unknown_wrapper", "false_review"])
def test_wrapper_and_case_failures_fail_closed(mutation: str) -> None:
    data = valid_input()
    if mutation == "missing_case":
        del data["case_bundle"]
    elif mutation == "case_not_mapping":
        data["case_bundle"] = []
    elif mutation == "unknown_wrapper":
        data["state_trace"] = ["COMPLETED"]
    else:
        data["human_review_required"] = False
    result = run(data=data)
    assert_failed_closed(result)


@pytest.mark.parametrize("mode", ["wrong_id", "unknown_field", "unsafe_content", "false_gate"])
def test_case_contract_failures_fail_closed_without_echo(mode: str) -> None:
    data = valid_input()
    case = data["case_bundle"]
    if mode == "wrong_id":
        case["case_id"] = "GC-P02-CONFLICTING-SOURCES"
    elif mode == "unknown_field":
        case["metadata"] = TRAP
    elif mode == "unsafe_content":
        case["synthetic_question"] = TRAP
    else:
        case["expected_hard_gate_results"]["NO_INPUT_MUTATION"] = False
    result = run(data=data)
    assert_failed_closed(result, TRAP if mode in {"unknown_field", "unsafe_content"} else None)


@pytest.mark.parametrize("unsafe", [
    "https://real.example/source",
    "api key material",
    "OpenAI configuration",
    "person@example.com",
    "wallet account details",
    "powershell command",
    "buy this outcome",
])
def test_url_secret_provider_person_command_and_trading_content_is_rejected(unsafe: str) -> None:
    data = valid_input()
    data["case_bundle"]["synthetic_question"] = unsafe
    result = run(data=data)
    assert_failed_closed(result, unsafe)


@pytest.mark.parametrize("flag", subject.REQUIRED_ASSISTED_RESEARCH_LOCAL_PERMISSION_FLAGS)
def test_every_permission_flag_must_be_exact_true(flag: str) -> None:
    data = valid_input()
    data["permission_profile"][flag] = False
    result = run(data=data)
    assert_failed_closed(result)
    assert result.errors == ("INVALID_PERMISSION_PROFILE",)


@pytest.mark.parametrize("field,value", [
    ("max_cases", 2), ("max_primary_calls", 2), ("max_retries", 1),
    ("max_total_calls", 2), ("max_input_tokens", 50_001),
    ("max_output_tokens", 8_001), ("max_request_seconds", 181),
    ("max_case_run_seconds", 301), ("max_concurrency", 2),
    ("max_total_cost_usd", 1), ("max_total_calls", True),
])
def test_every_budget_or_cost_violation_fails_closed(field: str, value: object) -> None:
    data = valid_input()
    data["budget_profile"][field] = value
    result = run(data=data)
    assert_failed_closed(result)
    assert result.errors == ("INVALID_BUDGET_PROFILE",)


def test_output_policy_unknown_or_authority_true_fails_closed() -> None:
    for mutate in ("unknown", "authority", "truthy_integer"):
        data = valid_input()
        if mutate == "unknown":
            data["output_policy"]["raw_output"] = True
        elif mutate == "authority":
            data["output_policy"]["paper_live_execution_authority"] = True
        else:
            data["output_policy"]["sanitized_evidence_only"] = 1
        assert_failed_closed(run(data=data))


def test_public_runner_rejects_callable_without_invoking_external_code() -> None:
    class SideEffectCallable:
        calls = 0

        def __call__(self) -> dict[str, Any]:
            self.calls += 1
            return valid_response()

    candidate = SideEffectCallable()
    result = run(response=candidate)
    assert_failed_closed(result)
    assert result.errors == ("INVALID_PRECOMPUTED_FAKE_RESPONSE",)
    assert result.external_callable_invoked is False
    assert candidate.calls == 0


def test_non_plain_or_non_mapping_precomputed_response_fails_closed() -> None:
    for output in (None, "text", [], (), 7):
        result = run(response=output)
        assert_failed_closed(result)
        assert result.errors == ("INVALID_PRECOMPUTED_FAKE_RESPONSE",)


@pytest.mark.parametrize("mode", ["missing", "unknown", "unsafe", "source_claim", "unsupported_citation"])
def test_wp133_and_output_safety_failures_are_neutral(mode: str) -> None:
    response = valid_response()
    if mode == "missing":
        del response["response_id"]
    elif mode == "unknown":
        response["state_trace"] = ["COMPLETED"]
    elif mode == "unsafe":
        response["response_id"] = TRAP
    elif mode == "source_claim":
        response["source_summary"] = "The source was fetched and verified. " + TRAP
    else:
        response["cited_source_references"] = ["Synthetic unknown label"]
    result = run(response=response)
    assert_failed_closed(result, TRAP if mode in {"unsafe", "source_claim"} else None)
    assert result.deterministic_validation_passed is False


NON_SUCCESS_RESPONSE_LABELS = sorted(
    wp133.ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS
    - {"RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW"}
)


@pytest.mark.parametrize("response_label", NON_SUCCESS_RESPONSE_LABELS)
def test_every_non_success_wp133_label_fails_closed(response_label: str) -> None:
    response = valid_response()
    response["response_label"] = response_label
    result = run(response=response)
    assert_failed_closed(result)
    assert result.errors == ("POSITIVE_CASE_EXPECTED_OUTCOME_NOT_MET",)


@pytest.mark.parametrize("missing_label", ["REQUIRED_SECTIONS_PRESENT", "HUMAN_REVIEW_PENDING"])
def test_missing_required_positive_completion_label_fails_closed(missing_label: str) -> None:
    response = valid_response()
    response["completion_labels"].remove(missing_label)
    replacement = next(
        label for label in sorted(wp133.ALLOWED_RESEARCH_COMPLETION_LABELS)
        if label not in response["completion_labels"] and label != missing_label
    )
    response["completion_labels"].append(replacement)
    result = run(response=response)
    assert_failed_closed(result)
    assert result.errors == ("POSITIVE_CASE_EXPECTED_OUTCOME_NOT_MET",)


def test_expected_outcome_mismatch_fails_closed() -> None:
    data = valid_input()
    data["case_bundle"]["expected_outcome_label"] = "REFUSAL_OR_DEFER_EXPECTED"
    result = run(data=data)
    assert_failed_closed(result)
    assert result.errors == ("POSITIVE_CASE_EXPECTED_OUTCOME_NOT_MET",)


@pytest.mark.parametrize(
    "field_name",
    subject._WP133_FREE_TEXT_SCALAR_FIELDS + subject._WP133_FREE_TEXT_SEQUENCE_FIELDS,
)
@pytest.mark.parametrize("phrase", subject._FORBIDDEN_SOURCE_ACCESS_CLAIMS)
def test_recursive_source_access_claim_scan_covers_every_text_surface(
    field_name: str,
    phrase: str,
) -> None:
    response = valid_response()
    if field_name in subject._WP133_FREE_TEXT_SEQUENCE_FIELDS:
        response[field_name] = [phrase]
    else:
        response[field_name] = phrase
    result = run(response=response)
    assert_failed_closed(result)
    assert phrase not in recursive_text(result)
    assert phrase not in repr(result)


@pytest.mark.parametrize(
    "field_name",
    subject._WP133_FREE_TEXT_SCALAR_FIELDS + subject._WP133_FREE_TEXT_SEQUENCE_FIELDS,
)
def test_wp145_scan_itself_rejects_each_scalar_and_sequence_surface(field_name: str) -> None:
    phrase = "source was accessed"
    response = valid_response()
    if field_name == "non_authority_notice":
        response[field_name] = f"{response[field_name]}; {phrase}"
    elif field_name in subject._WP133_FREE_TEXT_SEQUENCE_FIELDS:
        response[field_name] = [phrase]
    else:
        response[field_name] = phrase
    result = run(response=response)
    assert_failed_closed(result)
    assert result.errors == ("FORBIDDEN_SOURCE_ACCESS_CLAIM",)
    assert phrase not in recursive_text(result)


@pytest.mark.parametrize("extra_key", [
    "downstream_record", "automatic_wp122_record", "automatic_wp123_record",
    "persistent_output", "raw_output", "provider_result", "recommendation", "probability",
])
def test_forbidden_authority_downstream_and_persistence_keys_fail_closed(extra_key: str) -> None:
    response = valid_response()
    response[extra_key] = TRAP
    result = run(response=response)
    assert_failed_closed(result, TRAP)


@pytest.mark.parametrize("mode", ["missing", "false_complete", "false_required", "unknown_outcome", "extra", "claim", "rejected"])
def test_human_review_failures_fail_closed(mode: str) -> None:
    review = valid_review()
    if mode == "missing":
        del review["reviewer_note"]
    elif mode == "false_complete":
        review["human_review_complete"] = False
    elif mode == "false_required":
        review["human_review_required"] = False
    elif mode == "unknown_outcome":
        review["reviewer_outcome"] = "AUTO_APPROVED"
    elif mode == "extra":
        review["state_trace"] = ["COMPLETED"]
    elif mode == "claim":
        review["reviewer_note"] = "Sources verified " + TRAP
    else:
        review["reviewer_outcome"] = "REJECTED_UNSAFE_OR_INCOMPLETE"
    result = run(review=review)
    assert_failed_closed(result, TRAP if mode == "claim" else None)
    assert result.deterministic_validation_passed is True
    assert result.rubric_evaluation_complete is False
    assert result.human_review_complete is False


def test_one_false_derived_hard_gate_blocks_success(monkeypatch: pytest.MonkeyPatch) -> None:
    original = subject._evaluate_wp142_hard_gates

    def false_gate(**kwargs: object) -> dict[str, bool]:
        gates = dict(original(**kwargs))  # type: ignore[arg-type]
        gates["NO_UNAPPROVED_PERSISTENCE"] = False
        return gates

    monkeypatch.setattr(subject, "_evaluate_wp142_hard_gates", false_gate)
    result = run()
    assert_failed_closed(result)
    assert result.errors == ("HARD_GATE_EVALUATION_FAILED",)


def test_all_ten_hard_gates_are_explicitly_derived_without_blanket_true_initialization() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "{gate: True for gate in _HARD_GATE_IDS}" not in source
    tree = ast.parse(source)
    evaluator = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_evaluate_wp142_hard_gates"
    )
    gate_dict = next(
        node.args[0]
        for node in ast.walk(evaluator)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_ImmutableMapping"
        and node.args
        and isinstance(node.args[0], ast.Dict)
    )
    keys = tuple(key.value for key in gate_dict.keys if isinstance(key, ast.Constant))
    assert keys == subject._HARD_GATE_IDS
    assert all(not (isinstance(value, ast.Constant) and value.value is True) for value in gate_dict.values)


def test_assert_helper_rejects_failure_with_neutral_exception() -> None:
    failed = run(data={})
    with pytest.raises(ValueError, match="^INVALID_ASSISTED_RESEARCH_LOCAL_DRY_RUN_RESULT$") as exc:
        subject.assert_valid_assisted_research_local_dry_run_result(failed)
    assert TRAP not in str(exc.value)


def test_result_field_coverage_and_full_invalid_output_scan() -> None:
    expected_fields = {
        "valid", "experiment_id", "case_id", "state_trace", "terminal_state",
        "deterministic_validation_passed", "rubric_evaluation_complete",
        "human_review_complete", "teardown_complete", "input_unchanged",
        "precomputed_fake_response_only", "external_callable_invoked",
        "network_used", "credential_used", "hermes_used",
        "provider_call_used", "persistent_output_created", "downstream_record_created",
        "sanitized_evidence", "errors", "warnings",
    }
    assert {field.name for field in dataclasses.fields(subject.AssistedResearchLocalDryRunResult)} == expected_fields
    response = valid_response()
    response["source_summary"] = TRAP
    result = run(response=response)
    assert set(dataclasses.asdict(result)) == expected_fields
    assert TRAP not in recursive_text(result)


def test_ast_boundary_has_only_stdlib_and_exact_wp133_import_and_no_io() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert set(imports) == {
        "__future__", "copy", "collections.abc", "dataclasses", "types", "typing",
        "src.data_layer.hermes_candidate_review_manual_research_response",
    }
    assert not any(isinstance(node, (ast.AsyncFunctionDef, ast.While)) for node in ast.walk(tree))
    forbidden_call_names = {
        "open", "write", "read", "read_text", "write_text", "run", "Popen",
        "system", "urlopen", "request", "connect", "sleep", "uuid4", "random",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_call_names
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_call_names
    forbidden_import_roots = {
        "os", "pathlib", "socket", "subprocess", "urllib", "requests", "httpx",
        "aiohttp", "asyncio", "random", "uuid", "sqlite3", "shelve", "pickle",
    }
    assert not ({name.split(".")[0] for name in imports} & forbidden_import_roots)
    assert "Callable" not in source
    runner = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_assisted_research_local_no_network_dry_run"
    )
    assert [argument.arg for argument in runner.args.kwonlyargs] == [
        "dry_run_input", "fake_adapter_output", "human_review_acknowledgement",
    ]
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"dry_run_input", "fake_adapter_output", "human_review_acknowledgement"}
        for node in ast.walk(runner)
    )


def test_source_does_not_load_fixture_or_define_reusable_fake_adapter() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    class_names = {node.name.casefold() for node in tree.body if isinstance(node, ast.ClassDef)}
    assert not any("adapter" in name or "provider" in name for name in class_names)
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "pathlib" for node in ast.walk(tree))
    source_files = list((ROOT / "src" / "data_layer").glob("*assisted_research_local_dry_run_harness*.py"))
    assert source_files == [MODULE_PATH]


def test_operator_note_has_exact_title_headings_and_locked_posture() -> None:
    text = OPERATOR_NOTE.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# Hermes Candidate-Review Assisted Research Local Dry-Run Harness Operator Note"
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Purpose", "## Position After WP144", "## What WP145 Implements",
        "## What WP145 Does Not Implement", "## Exact One-Case Dry Run",
        "## State Machine", "## Precomputed Fake-Response Boundary", "## Deterministic Validation",
        "## Human Review", "## Sanitized Evidence", "## Teardown",
        "## Failure Behavior", "## Test-Only Temp Boundary",
        "## Forbidden Interpretations", "## Future WP146 Boundary",
        "## Non-Authority Statement",
    ]
    for statement in (
        "Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON",
        "Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE",
        "Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE",
        "Dry-run case count: 1", "Dry-run case ID: GC-P01-COMPLETE-SUPPORTED",
        "Network: FORBIDDEN", "Credentials: FORBIDDEN",
        "Hermes installation/invocation: FORBIDDEN", "Provider/model call: FORBIDDEN",
        "Stable raw input/output persistence: FORBIDDEN",
        "Temporary filesystem: PYTEST_TMP_PATH_ONLY", "Output: SANITIZED_EVIDENCE_ONLY",
        "Deterministic WP133 validation: MANDATORY",
        "Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED",
        "Automatic downstream records: FORBIDDEN",
        "Paper/live/execution authority: FORBIDDEN", "WP146 requires separate approval",
    ):
        assert statement in text
