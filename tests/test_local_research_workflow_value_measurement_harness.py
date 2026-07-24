from __future__ import annotations

import ast
import builtins
import copy
import importlib
import json
from pathlib import Path

import pytest

import src.data_layer.local_research_value_measurement.harness as harness
from src.data_layer.local_research_value_measurement import (
    ALLOWED_EVENT_TYPES,
    ALLOWED_OPERATOR_ACTIONS,
    ALLOWED_RUN_STATUSES,
    CORPUS_ID,
    CORPUS_VERSION,
    EVENT_CONTRACT_VERSION,
    METRIC_REGISTRY,
    METRIC_REGISTRY_VERSION,
    NON_AUTHORITY_NOTICE,
    RECEIPT_CONTRACT_VERSION,
    REQUIRED_REPEATS,
    RUN_CONTRACT_VERSION,
    SAFETY_GATES,
    STAGE_MAP,
    STAGE_MAP_VERSION,
    load_and_validate_corpus,
    run_measurement,
    validate_event_stream,
    validate_operator_actions,
    validate_receipt,
    validate_run_request,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/local_research_workflow_value_measurement_v1.json"
CONTRACT = ROOT / "docs/local_research_workflow_value_measurement_harness_contract.md"
SOURCE = (
    ROOT
    / "src/data_layer/local_research_value_measurement/harness.py"
)


def _corpus() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _request(
    *,
    case_selection: list[str] | None = None,
    output_mode: str = "IN_MEMORY_ONLY",
) -> dict:
    return {
        "run_contract_version": RUN_CONTRACT_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "stage_map_version": STAGE_MAP_VERSION,
        "run_id": "WP152-SYNTHETIC-RUN",
        "operator_run_label": "WP152_SYNTHETIC_VALIDATION",
        "case_selection": case_selection
        or [f"LVM-{index:03d}" for index in range(1, 15)],
        "repeat_index": REQUIRED_REPEATS,
        "temporary_output_mode": output_mode,
        "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }


def _actions(corpus: dict, request: dict) -> list[dict]:
    selected = set(request["case_selection"])
    return [
        {
            "action_id": f"{case['case_id']}-ACK",
            "run_id": request["run_id"],
            "case_id": case["case_id"],
            "stage_id": case["stage_ids"][-1],
            "action_type": "ACKNOWLEDGE",
            "reason_code": "REVIEW_COMPLETE",
            "correction_target": "NONE",
            "reviewer_acknowledgement": True,
            "human_review_required": True,
            "non_authority_notice": NON_AUTHORITY_NOTICE,
        }
        for case in corpus["cases"]
        if case["case_id"] in selected
    ]


def _valid_run(
    *,
    corpus: dict | None = None,
    request: dict | None = None,
) -> dict:
    corpus = corpus or _corpus()
    request = request or _request()
    return run_measurement(request, corpus, _actions(corpus, request))


def _metric(result: dict, metric_id: str) -> dict:
    return next(
        item for item in result["receipt"]["metric_results"] if item["metric_id"] == metric_id
    )


def _recursive_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(
            [_recursive_text(key) for key in value]
            + [_recursive_text(item) for item in value.values()]
        )
    if isinstance(value, (list, tuple)):
        return " ".join(_recursive_text(item) for item in value)
    return str(value)


def _contract_table_rows(text: str, heading: str, next_heading: str) -> list[list[str]]:
    section = text.split(heading, 1)[1].split(next_heading, 1)[0]
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("|---")
    ][1:]


def test_registry_is_exact_wp151_order_and_39_22_17_split() -> None:
    rows = _contract_table_rows(
        CONTRACT.read_text(encoding="utf-8"),
        "## Canonical Metric Registry",
        "## Metric-To-Stage Applicability Map",
    )
    assert [tuple(row) for row in rows] == [tuple(record) for record in METRIC_REGISTRY]
    assert len(METRIC_REGISTRY) == 39
    assert sum(record.wave == "WAVE_1" for record in METRIC_REGISTRY) == 22
    assert sum(record.wave == "WAVE_2" for record in METRIC_REGISTRY) == 17
    assert all(
        record.measurement_type
        in {
            "COUNT",
            "RATE",
            "BOOLEAN_COVERAGE",
            "SET_COVERAGE",
            "REPEATABILITY_EQUALITY",
        }
        for record in METRIC_REGISTRY
        if record.wave == "WAVE_1"
    )
    assert all(
        record.measurement_type == "NOT_IMPLEMENTABLE_YET"
        for record in METRIC_REGISTRY
        if record.wave == "WAVE_2"
    )


def test_stage_map_is_exact_wp151_order_and_complete_wave1_coverage() -> None:
    rows = _contract_table_rows(
        CONTRACT.read_text(encoding="utf-8"),
        "## Metric-To-Stage Applicability Map",
        "## Corpus Contract",
    )
    assert [tuple(row) for row in rows] == [tuple(record) for record in STAGE_MAP]
    assert [record.stage_id for record in STAGE_MAP] == [
        f"LRW-{index:02d}" for index in range(1, 21)
    ]
    stage_text = " ".join(record.applicable_metric_ids for record in STAGE_MAP)
    assert all(
        record.metric_id in stage_text for record in METRIC_REGISTRY if record.wave == "WAVE_1"
    )
    assert "paper stage" not in stage_text.lower()


def test_fixed_corpus_identity_order_shape_and_immutability() -> None:
    corpus = _corpus()
    before = copy.deepcopy(corpus)
    result = load_and_validate_corpus(corpus)
    assert result["is_valid"] is True
    assert result["errors"] == ()
    assert corpus == before
    assert result["normalized"] is not corpus
    assert result["normalized"]["corpus_id"] == CORPUS_ID
    assert result["normalized"]["corpus_version"] == CORPUS_VERSION
    assert len(result["normalized"]["cases"]) == 14
    assert [case["case_id"] for case in result["normalized"]["cases"]] == [
        f"LVM-{index:03d}" for index in range(1, 15)
    ]
    assert len({case["family"] for case in result["normalized"]["cases"]}) == 14
    rows = _contract_table_rows(
        CONTRACT.read_text(encoding="utf-8"),
        "## Corpus Contract",
        "## Run Contract",
    )
    fixture_rows = [
        [
            case["case_id"],
            case["family"],
            "; ".join(case["stage_ids"]),
            "; ".join(case["metric_ids"]),
            case["input_artifact_shape"],
            case["expected_validation_state"],
            case["expected_metric_events"],
            case["negative_mutation_family"],
            case["human_review"],
        ]
        for case in corpus["cases"]
    ]
    assert fixture_rows == rows
    corpus["cases"][0]["observations"]["market_ids"].append("CALLER-MUTATION")
    assert "CALLER-MUTATION" not in _recursive_text(result["normalized"])


def test_contract_vocabularies_are_exact() -> None:
    assert EVENT_CONTRACT_VERSION == "local-research-value-event-v1.0"
    assert RECEIPT_CONTRACT_VERSION == "local-research-value-receipt-v1.0"
    assert len(ALLOWED_EVENT_TYPES) == 13
    assert len(ALLOWED_RUN_STATUSES) == 9
    assert len(SAFETY_GATES) == 12
    assert REQUIRED_REPEATS == 3
    assert ALLOWED_OPERATOR_ACTIONS == (
        "NO_ACTION",
        "ACKNOWLEDGE",
        "REQUEST_CORRECTION",
        "RETRY_CASE",
        "DEFER_CASE",
        "ABORT_RUN",
    )


def test_complete_run_is_deterministic_and_measures_only_wave1() -> None:
    corpus = _corpus()
    request = _request()
    before_corpus = copy.deepcopy(corpus)
    before_request = copy.deepcopy(request)
    actions = _actions(corpus, request)
    before_actions = copy.deepcopy(actions)
    first = run_measurement(request, corpus, actions)
    second = run_measurement(request, corpus, actions)
    assert first == second
    assert first["is_valid"] is True
    assert first["run_status"] == "RUN_VALID_MEASUREMENT_COMPLETE"
    assert first["errors"] == ()
    assert corpus == before_corpus
    assert request == before_request
    assert actions == before_actions
    receipt = first["receipt"]
    assert receipt["case_count"] == 14
    assert receipt["repeat_count"] == 3
    assert receipt["event_count"] == len(first["events"]) == 392
    assert receipt["human_review_status"] == "HUMAN_REVIEW_COMPLETE_NOT_ACCEPTED"
    assert receipt["temporary_output_status"] == "IN_MEMORY_ONLY"
    assert sum(
        item["measurement_status"] == "MEASURED_VALID"
        for item in receipt["metric_results"]
    ) == 22
    assert sum(
        item["measurement_status"] == "BLOCKED_WAVE_2"
        for item in receipt["metric_results"]
    ) == 17
    assert all(value is True for _, value in receipt["safety_flags"])


def test_exact_count_rate_set_and_repeatability_formulas() -> None:
    result = _valid_run()
    assert _metric(result, "RV-THR-01")["count"] == 3
    assert _metric(result, "RV-THR-02")["count"] == 2
    assert _metric(result, "RV-THR-06")["count"] == 3
    assert (
        _metric(result, "RV-REJ-04")["numerator"],
        _metric(result, "RV-REJ-04")["denominator"],
    ) == (4, 4)
    assert (
        _metric(result, "RV-REJ-05")["numerator"],
        _metric(result, "RV-REJ-05")["denominator"],
    ) == (3, 3)
    assert (
        _metric(result, "RV-REJ-06")["numerator"],
        _metric(result, "RV-REJ-06")["denominator"],
    ) == (2, 2)
    assert (
        _metric(result, "RV-REJ-07")["numerator"],
        _metric(result, "RV-REJ-07")["denominator"],
    ) == (4, 6)
    assert _metric(result, "RV-REJ-02")["set_coverage"] == "4/4"
    assert _metric(result, "RV-REP-06")["repeatability_result"] == "PASS"
    boolean_results = [
        item
        for item in result["receipt"]["metric_results"]
        if item["measurement_type"] == "BOOLEAN_COVERAGE"
    ]
    assert boolean_results and all(item["boolean_result"] is True for item in boolean_results)


def test_metric_results_populate_only_type_relevant_value_fields() -> None:
    fields_by_type = {
        "COUNT": {"count"},
        "RATE": {"numerator", "denominator"},
        "BOOLEAN_COVERAGE": {"boolean_result"},
        "SET_COVERAGE": {"set_coverage"},
        "REPEATABILITY_EQUALITY": {"repeatability_result"},
        "NOT_IMPLEMENTABLE_YET": set(),
    }
    value_fields = {
        "numerator",
        "denominator",
        "count",
        "duration_ns",
        "boolean_result",
        "set_coverage",
        "repeatability_result",
        "rubric_score",
    }
    for result in _valid_run()["receipt"]["metric_results"]:
        populated = {field for field in value_fields if result[field] is not None}
        assert populated == fields_by_type[result["measurement_type"]]


def test_wave2_is_always_blocked_with_empty_value_fields() -> None:
    value_fields = (
        "numerator",
        "denominator",
        "count",
        "duration_ns",
        "boolean_result",
        "set_coverage",
        "repeatability_result",
        "rubric_score",
    )
    blocked = [
        item
        for item in _valid_run()["receipt"]["metric_results"]
        if item["wave"] == "WAVE_2"
    ]
    assert len(blocked) == 17
    assert all(item["measurement_status"] == "BLOCKED_WAVE_2" for item in blocked)
    assert all(all(item[field] is None for field in value_fields) for item in blocked)


def test_exact_event_fields_sequences_references_and_terminal_state() -> None:
    result = _valid_run()
    events = result["events"]
    assert [event["event_sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["event_type"] == "RUN_STARTED"
    assert events[-1]["event_type"] == "RUN_COMPLETED"
    assert events[-1]["validation_state"] == "RUN_VALID_MEASUREMENT_COMPLETE"
    assert all(
        tuple(event.keys()) == harness.REQUIRED_EVENT_FIELDS for event in events
    )
    assert all(event["monotonic_elapsed_ns"] >= 0 for event in events)
    assert all("/" not in event["input_reference"] for event in events)
    validation = validate_event_stream(
        events,
        run_id=_request()["run_id"],
        selected_cases=_request()["case_selection"],
    )
    assert validation["is_valid"] is True


def test_receipt_exact_fields_and_reconciliation() -> None:
    corpus = _corpus()
    request = _request()
    actions = _actions(corpus, request)
    result = run_measurement(request, corpus, actions)
    receipt = result["receipt"]
    assert tuple(receipt.keys()) == harness.REQUIRED_RECEIPT_FIELDS
    assert all(
        tuple(metric.keys()) == harness.REQUIRED_METRIC_RESULT_FIELDS
        for metric in receipt["metric_results"]
    )
    validation = validate_receipt(
        receipt,
        expected_run_id=request["run_id"],
        expected_case_count=14,
        expected_event_count=len(result["events"]),
        expected_operator_action_count=len(actions),
    )
    assert validation["is_valid"] is True


def test_public_dict_results_have_exact_field_coverage() -> None:
    request_result = validate_run_request(_request())
    corpus_result = load_and_validate_corpus(_corpus())
    run_result = _valid_run()
    assert tuple(request_result.keys()) == harness.VALIDATION_RESULT_FIELDS
    assert tuple(corpus_result.keys()) == harness.VALIDATION_RESULT_FIELDS
    assert tuple(run_result.keys()) == harness.RUN_RESULT_FIELDS


@pytest.mark.parametrize(
    ("field", "value", "status", "error"),
    [
        ("run_contract_version", "wrong", "RUN_FAILED_INPUT_CONTRACT", "RUN_VERSION_MISMATCH"),
        ("corpus_id", "wrong", "RUN_FAILED_CORPUS_VERSION", "CORPUS_ID_MISMATCH"),
        ("corpus_version", "2.0", "RUN_FAILED_CORPUS_VERSION", "CORPUS_VERSION_MISMATCH"),
        (
            "metric_registry_version",
            "wrong",
            "RUN_FAILED_METRIC_REGISTRY",
            "METRIC_REGISTRY_VERSION_MISMATCH",
        ),
        ("stage_map_version", "wrong", "RUN_FAILED_STAGE_MAP", "STAGE_MAP_VERSION_MISMATCH"),
        ("repeat_index", 2, "RUN_FAILED_INPUT_CONTRACT", "REPEAT_COUNT_MUST_EQUAL_THREE"),
        ("temporary_output_mode", "PERSISTENT", "RUN_FAILED_INPUT_CONTRACT", "INVALID_OUTPUT_MODE"),
        ("human_review_required", False, "RUN_FAILED_VALIDATION", "HUMAN_REVIEW_REQUIRED"),
    ],
)
def test_run_contract_fails_closed(
    field: str, value: object, status: str, error: str
) -> None:
    request = _request()
    request[field] = value
    result = validate_run_request(request)
    assert result == {
        "is_valid": False,
        "run_status": status,
        "errors": (error,),
        "normalized": {},
    }


def test_run_contract_rejects_missing_extra_duplicate_unknown_and_unordered_cases() -> None:
    assert validate_run_request(None)["errors"] == ("UNSUPPORTED_INPUT_SHAPE",)
    missing = _request()
    missing.pop("run_id")
    assert validate_run_request(missing)["errors"] == ("RUN_FIELDS_MISMATCH",)
    extra = _request()
    extra["unrestricted_note"] = "safe-looking text"
    assert validate_run_request(extra)["errors"] == ("RUN_FIELDS_MISMATCH",)
    duplicate = _request(case_selection=["LVM-001", "LVM-001"])
    assert validate_run_request(duplicate)["errors"] == ("INVALID_CASE_SELECTION",)
    unknown = _request(case_selection=["LVM-999"])
    assert validate_run_request(unknown)["errors"] == ("INVALID_CASE_SELECTION",)
    unordered = _request(case_selection=["LVM-002", "LVM-001"])
    assert validate_run_request(unordered)["errors"] == ("INVALID_CASE_SELECTION",)
    null_id = _request()
    null_id["run_id"] = None
    assert validate_run_request(null_id)["errors"] == ("INVALID_RUN_ID",)
    wrong_type = _request()
    wrong_type["case_selection"] = "LVM-001"
    assert validate_run_request(wrong_type)["errors"] == ("INVALID_CASE_SELECTION",)
    empty = _request()
    empty["case_selection"] = []
    assert validate_run_request(empty)["errors"] == ("INVALID_CASE_SELECTION",)


def test_corpus_mutations_fail_closed_with_exact_statuses() -> None:
    duplicate = _corpus()
    duplicate["cases"][1]["case_id"] = "LVM-001"
    assert load_and_validate_corpus(duplicate)["run_status"] == "RUN_FAILED_CORPUS_VERSION"
    unknown_stage = _corpus()
    unknown_stage["cases"][0]["stage_ids"][0] = "LRW-99"
    assert load_and_validate_corpus(unknown_stage)["run_status"] == "RUN_FAILED_STAGE_MAP"
    missing_stage = _corpus()
    missing_stage["cases"][0]["stage_ids"].pop()
    assert load_and_validate_corpus(missing_stage)["errors"] == ("CASE_STAGE_MAP_MISMATCH",)
    unknown_metric = _corpus()
    unknown_metric["cases"][0]["metric_ids"][0] = "RV-UNKNOWN"
    assert load_and_validate_corpus(unknown_metric)["run_status"] == "RUN_FAILED_METRIC_REGISTRY"
    missing_metric = _corpus()
    missing_metric["cases"][0]["metric_ids"].pop()
    assert load_and_validate_corpus(missing_metric)["errors"] == (
        "CASE_METRIC_COVERAGE_MISMATCH",
    )
    renamed_family = _corpus()
    renamed_family["cases"][0]["family"] = "renamed family"
    assert load_and_validate_corpus(renamed_family)["errors"] == (
        "CORPUS_CASE_METADATA_MISMATCH",
    )


@pytest.mark.parametrize(
    ("text", "expected_error"),
    [
        ("https://outside.invalid", "SAFETY_GATE_NO_NETWORK"),
        ("api key sample", "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA"),
        ("provider output", "SAFETY_GATE_NO_PROVIDER_OR_MODEL_CALL"),
        ("hermes runtime", "SAFETY_GATE_NO_HERMES_RUNTIME"),
        ("account state", "SAFETY_GATE_NO_PAPER_OR_LIVE_STATE"),
        ("strategy signal", "SAFETY_GATE_NO_ORDER_OR_SIGNAL_CREATION"),
        ("buy recommendation", "SAFETY_GATE_NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT"),
        ("TRADE-READY", "SAFETY_GATE_NO_PROFITABILITY_OR_RECOMMENDATION_OUTPUT"),
        ("paper state", "SAFETY_GATE_NO_PAPER_OR_LIVE_STATE"),
        ("create order", "SAFETY_GATE_NO_ORDER_OR_SIGNAL_CREATION"),
        ("database writer", "SAFETY_GATE_NO_UNAPPROVED_PERSISTENCE"),
        ("background task", "SAFETY_GATE_NO_SCHEDULER_OR_BACKGROUND_TASK"),
        ("C:\\private\\record.json", "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA"),
        ("2026-07-24T12:30:00Z", "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA"),
        (
            "123e4567-e89b-12d3-a456-426614174000",
            "SAFETY_GATE_NO_RAW_PRIVATE_OR_SECRET_DATA",
        ),
    ],
)
def test_safety_gates_take_precedence_and_never_echo_input(
    text: str, expected_error: str
) -> None:
    corpus = _corpus()
    corpus["cases"][0]["observations"]["normalized_output_shape"].append(text)
    result = run_measurement(_request(), corpus, _actions(_corpus(), _request()))
    assert result["is_valid"] is False
    assert result["run_status"] == "RUN_FAILED_VALIDATION"
    assert result["errors"] == (expected_error,)
    assert result["events"] == ()
    assert result["receipt"] == {}
    assert text not in _recursive_text(result)


def test_operator_action_contract_orphan_cross_case_unknown_note_retry_and_abort() -> None:
    corpus = _corpus()
    request = _request()
    actions = _actions(corpus, request)
    valid = validate_operator_actions(
        actions,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )
    assert valid["is_valid"] is True

    orphan = copy.deepcopy(actions)
    orphan[0]["case_id"] = "LVM-999"
    assert validate_operator_actions(
        orphan,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("ORPHAN_OR_CROSS_CASE_ACTION",)

    cross_stage = copy.deepcopy(actions)
    cross_stage[0]["stage_id"] = "LRW-20"
    assert validate_operator_actions(
        cross_stage,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("CROSS_CASE_STAGE_ACTION",)

    unknown = copy.deepcopy(actions)
    unknown[0]["action_type"] = "APPROVE"
    assert validate_operator_actions(
        unknown,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("UNKNOWN_OPERATOR_ACTION",)

    note = copy.deepcopy(actions)
    note[0]["unrestricted_note"] = "not allowed"
    assert validate_operator_actions(
        note,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("ACTION_FIELDS_MISMATCH",)

    wrong_transition = copy.deepcopy(actions)
    wrong_transition[0]["reason_code"] = "NO_REASON"
    assert validate_operator_actions(
        wrong_transition,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("INVALID_ACTION_TRANSITION",)

    retry = copy.deepcopy(actions[0])
    retry.update(
        {
            "action_id": "LVM-001-RETRY-A",
            "action_type": "RETRY_CASE",
            "reason_code": "CASE_RETRY_REQUIRED",
            "correction_target": "CASE_VALIDATION",
            "reviewer_acknowledgement": False,
        }
    )
    retry_two = copy.deepcopy(retry)
    retry_two["action_id"] = "LVM-001-RETRY-B"
    assert validate_operator_actions(
        [retry, retry_two],
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        corpus_cases=corpus["cases"],
    )["errors"] == ("UNBOUNDED_RETRY",)

    abort = copy.deepcopy(actions[0])
    abort.update(
        {
            "action_id": "LVM-001-ABORT",
            "action_type": "ABORT_RUN",
            "reason_code": "RUN_ABORT_REQUESTED",
            "correction_target": "NONE",
            "reviewer_acknowledgement": False,
        }
    )
    result = run_measurement(request, corpus, [abort])
    assert result["run_status"] == "RUN_ABORTED_BY_OPERATOR"
    assert result["receipt"] == {}


def test_event_mutations_missing_duplicate_out_of_order_negative_and_unknown() -> None:
    result = _valid_run()
    request = _request()

    missing = list(copy.deepcopy(result["events"]))
    missing.pop(2)
    assert validate_event_stream(
        missing, run_id=request["run_id"], selected_cases=request["case_selection"]
    )["errors"] == ("NONCONTIGUOUS_EVENT_SEQUENCE",)

    missing_renumbered = list(copy.deepcopy(result["events"]))
    missing_renumbered.pop(2)
    for index, event in enumerate(missing_renumbered, 1):
        event["event_sequence"] = index
        event["monotonic_elapsed_ns"] = index * 10
    assert validate_event_stream(
        missing_renumbered,
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
    )["errors"] == ("ORPHAN_STAGE_COMPLETION",)

    duplicate = list(copy.deepcopy(result["events"]))
    duplicate.insert(2, copy.deepcopy(duplicate[1]))
    assert validate_event_stream(
        duplicate, run_id=request["run_id"], selected_cases=request["case_selection"]
    )["errors"] == ("NONCONTIGUOUS_EVENT_SEQUENCE",)

    out_of_order = list(copy.deepcopy(result["events"]))
    out_of_order[2]["monotonic_elapsed_ns"] = 0
    assert validate_event_stream(
        out_of_order, run_id=request["run_id"], selected_cases=request["case_selection"]
    )["errors"] == ("OUT_OF_ORDER_DURATION",)

    negative = list(copy.deepcopy(result["events"]))
    negative[2]["monotonic_elapsed_ns"] = -1
    assert validate_event_stream(
        negative, run_id=request["run_id"], selected_cases=request["case_selection"]
    )["errors"] == ("NEGATIVE_OR_INVALID_DURATION",)

    unknown = list(copy.deepcopy(result["events"]))
    unknown[2]["event_type"] = "UNKNOWN"
    assert validate_event_stream(
        unknown, run_id=request["run_id"], selected_cases=request["case_selection"]
    )["errors"] == ("UNKNOWN_EVENT_TYPE",)


def test_receipt_rejects_missing_extra_fields_zero_denominator_and_reconciliation() -> None:
    result = _valid_run()
    receipt = copy.deepcopy(result["receipt"])
    kwargs = {
        "expected_run_id": _request()["run_id"],
        "expected_case_count": 14,
        "expected_event_count": len(result["events"]),
        "expected_operator_action_count": 14,
    }

    missing = copy.deepcopy(receipt)
    missing.pop("event_count")
    assert validate_receipt(missing, **kwargs)["errors"] == ("RECEIPT_FIELDS_MISMATCH",)

    extra = copy.deepcopy(receipt)
    extra["raw_input"] = "not echoed"
    validation = validate_receipt(extra, **kwargs)
    assert validation["errors"] == ("RECEIPT_FIELDS_MISMATCH",)
    assert "not echoed" not in _recursive_text(validation)

    zero = copy.deepcopy(receipt)
    rate = next(item for item in zero["metric_results"] if item["measurement_type"] == "RATE")
    rate["denominator"] = 0
    assert validate_receipt(zero, **kwargs)["errors"] == ("ZERO_DENOMINATOR",)

    count_mismatch = copy.deepcopy(receipt)
    count_mismatch["event_count"] += 1
    assert validate_receipt(count_mismatch, **kwargs)["errors"] == (
        "RECEIPT_RECONCILIATION_FAILED",
    )


def test_wave2_false_measurement_fails_registry_and_safety_gate() -> None:
    result = _valid_run()
    receipt = copy.deepcopy(result["receipt"])
    wave2 = next(item for item in receipt["metric_results"] if item["wave"] == "WAVE_2")
    wave2["measurement_status"] = "MEASURED_VALID"
    wave2["count"] = 1
    validation = validate_receipt(
        receipt,
        expected_run_id=_request()["run_id"],
        expected_case_count=14,
        expected_event_count=len(result["events"]),
        expected_operator_action_count=14,
    )
    assert validation["run_status"] == "RUN_FAILED_METRIC_REGISTRY"
    assert validation["errors"] == (
        "WAVE_2_FALSE_MEASUREMENT",
        "SAFETY_GATE_NO_WAVE_2_FALSE_MEASUREMENT",
    )


def test_partial_selection_is_not_a_valid_complete_measurement() -> None:
    corpus = _corpus()
    request = _request(case_selection=["LVM-001"])
    result = run_measurement(request, corpus, _actions(corpus, request))
    assert result["is_valid"] is False
    assert result["run_status"] == "RUN_FAILED_VALIDATION"
    assert result["receipt"]
    assert result["events"][-1]["event_type"] == "RUN_FAILED"
    wave1 = [
        item for item in result["receipt"]["metric_results"] if item["wave"] == "WAVE_1"
    ]
    assert all(
        item["measurement_status"] == "INSUFFICIENT_CASE_COVERAGE" for item in wave1
    )


def test_missing_human_review_fails_run() -> None:
    result = run_measurement(_request(), _corpus(), ())
    assert result == {
        "is_valid": False,
        "run_status": "RUN_FAILED_VALIDATION",
        "errors": ("HUMAN_REVIEW_REQUIRED",),
        "events": (),
        "receipt": {},
    }


def test_repeatability_mismatch_fails_without_partial_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    original = harness._execute_case

    def mismatching_execute(case: dict, repeat_index: int) -> dict:
        result = original(case, repeat_index)
        if case["case_id"] == "LVM-013" and repeat_index == 2:
            result["normalized_output_shape"] = ("MISMATCH",)
        return result

    monkeypatch.setattr(harness, "_execute_case", mismatching_execute)
    result = _valid_run()
    assert result == {
        "is_valid": False,
        "run_status": "RUN_FAILED_REPEATABILITY",
        "errors": ("REPEATABILITY_MISMATCH",),
        "events": (),
        "receipt": {},
    }


def test_pytest_temporary_mode_writes_nothing_and_leaves_tmp_path_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    request = _request(output_mode="PYTEST_TMP_PATH_ONLY")
    result = _valid_run(request=request)
    assert result["is_valid"] is True
    assert result["receipt"]["temporary_output_status"] == "PYTEST_TMP_PATH_ONLY"
    assert list(tmp_path.iterdir()) == []


def test_invalid_input_no_echo_scans_complete_public_result() -> None:
    marker = "UNSAFE-MARKER-NEVER-ECHO"
    invalid = _request()
    invalid["unrestricted_note"] = marker
    result = run_measurement(invalid, _corpus(), ())
    assert result["is_valid"] is False
    assert result["receipt"] == {}
    assert marker not in _recursive_text(result)


def test_source_has_only_stdlib_imports_and_no_protected_integration_imports() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports <= {
        "__future__",
        "copy",
        "hashlib",
        "json",
        "re",
        "collections",
        "typing",
    }
    forbidden = {
        "socket",
        "http",
        "urllib",
        "requests",
        "subprocess",
        "os",
        "environ",
        "provider",
        "hermes",
        "paper_trading",
        "execution_gateway",
        "risk_engine",
        "scheduler",
        "sqlite3",
        "pathlib",
    }
    assert imports.isdisjoint(forbidden)


def test_import_has_no_file_io_or_other_import_time_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_open(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"unexpected import-time file access: {args!r} {kwargs!r}")

    monkeypatch.setattr(builtins, "open", fail_open)
    reloaded = importlib.reload(harness)
    assert len(reloaded.METRIC_REGISTRY) == 39
    assert len(reloaded.STAGE_MAP) == 20


def test_registry_and_stage_constants_are_immutable_tuples() -> None:
    assert isinstance(METRIC_REGISTRY, tuple)
    assert isinstance(STAGE_MAP, tuple)
    with pytest.raises(AttributeError):
        METRIC_REGISTRY[0].metric_id = "RENAMED"
    with pytest.raises(TypeError):
        METRIC_REGISTRY[0] = METRIC_REGISTRY[1]
