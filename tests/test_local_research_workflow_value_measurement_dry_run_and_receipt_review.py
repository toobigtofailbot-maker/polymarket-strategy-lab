"""Focused WP153 regression: one project-authorized synthetic dry run.

This test reproduces the exact WP153 dry run through the public WP152 package
surface only (no private monkeypatches), independently validates its event and
receipt surfaces, proves deterministic byte-equal replay, and reconciles the
recorded canonical SHA-256 evidence against the committed WP153 document and
status fragment. The second replay is deterministic regression evidence only,
not a second accepted project run.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from src.data_layer.local_research_value_measurement import (
    CORPUS_ID,
    CORPUS_VERSION,
    METRIC_REGISTRY_VERSION,
    NON_AUTHORITY_NOTICE,
    REQUIRED_REPEATS,
    RUN_CONTRACT_VERSION,
    STAGE_MAP_VERSION,
    load_and_validate_corpus,
    run_measurement,
    validate_event_stream,
    validate_operator_actions,
    validate_run_request,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/local_research_workflow_value_measurement_v1.json"
REVIEW_DOC = (
    ROOT
    / "docs/local_research_workflow_value_measurement_dry_run_and_receipt_review.md"
)
STATUS_FRAGMENT = ROOT / "docs/status_entries/WP153.md"

RUN_ID = "WP153-DRY-RUN-001"
OPERATOR_RUN_LABEL = "WP152_SYNTHETIC_VALIDATION"

EVENT_STREAM_SHA256 = (
    "31eca5ee6b7881029585f494de0740f04fd068ac9625b4cd8b387b41a87f3135"
)
RECEIPT_SHA256 = (
    "5a60772bec6c582a83a1e36bfeaa60de4a7aff7840f8ec9b7f33ad9f17234750"
)
PUBLIC_RESULT_SHA256 = (
    "f95101f9ed82ca32cc458f2133b8cb0c34e2adfccf0619b349c993fafcc8b514"
)

VALUE_FIELDS = (
    "numerator",
    "denominator",
    "count",
    "duration_ns",
    "boolean_result",
    "set_coverage",
    "repeatability_result",
    "rubric_score",
)

FORBIDDEN_POSITIVE_VARIANTS = (
    "buy now",
    "sell now",
    "trade signal",
    "place order",
    "submit order",
    "execute order",
    "approve strategy",
    "promote strategy",
    "position size",
    "expected return",
    "profit target",
    "paper ready",
    "live ready",
    "wallet balance",
    "account balance",
    "provider response",
    "model response",
    "hermes command",
    "background worker",
    "persistent report",
)

_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)
_ABS_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/[A-Za-z])")


def _corpus() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _request(corpus: dict) -> dict:
    return {
        "run_contract_version": RUN_CONTRACT_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "stage_map_version": STAGE_MAP_VERSION,
        "run_id": RUN_ID,
        "operator_run_label": OPERATOR_RUN_LABEL,
        "case_selection": [case["case_id"] for case in corpus["cases"]],
        "repeat_index": REQUIRED_REPEATS,
        "temporary_output_mode": "IN_MEMORY_ONLY",
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


def _canonical_sha256(value: object) -> str:
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canonical_text(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _run() -> dict:
    corpus = _corpus()
    request = _request(corpus)
    actions = _actions(corpus, request)
    return run_measurement(request, corpus, actions)


def test_request_fixture_and_actions_validate() -> None:
    corpus = _corpus()
    request = _request(corpus)
    actions = _actions(corpus, request)
    assert load_and_validate_corpus(corpus)["is_valid"] is True
    assert validate_run_request(request)["is_valid"] is True
    assert (
        validate_operator_actions(
            actions,
            run_id=request["run_id"],
            selected_cases=request["case_selection"],
            corpus_cases=corpus["cases"],
        )["is_valid"]
        is True
    )


def test_dry_run_public_result_fields_are_exact() -> None:
    result = _run()
    assert result["is_valid"] is True
    assert result["run_status"] == "RUN_VALID_MEASUREMENT_COMPLETE"
    assert result["errors"] == ()
    receipt = result["receipt"]
    assert receipt["run_id"] == RUN_ID
    assert receipt["receipt_id"] == f"{RUN_ID}_RECEIPT"
    assert receipt["case_count"] == 14
    assert receipt["repeat_count"] == 3
    assert receipt["event_count"] == len(result["events"]) == 392
    assert len(receipt["metric_results"]) == 39
    assert (
        receipt["human_review_status"]
        == "ACCEPT_MEASUREMENT_RECEIPT_FOR_RESEARCH_MEMORY_ONLY"
    )
    assert receipt["hard_failures"] == ()
    assert receipt["temporary_output_status"] == "IN_MEMORY_ONLY"


def test_independent_event_and_receipt_validation_pass() -> None:
    corpus = _corpus()
    request = _request(corpus)
    actions = _actions(corpus, request)
    result = run_measurement(request, corpus, actions)

    event_validation = validate_event_stream(
        result["events"],
        run_id=request["run_id"],
        selected_cases=request["case_selection"],
        expected_operator_actions=actions,
    )
    assert event_validation["is_valid"] is True
    assert event_validation["run_status"] == "RUN_VALID_MEASUREMENT_COMPLETE"
    assert event_validation["errors"] == ()

    from src.data_layer.local_research_value_measurement import validate_receipt

    receipt_validation = validate_receipt(
        result["receipt"],
        expected_run_id=request["run_id"],
        expected_case_count=len(request["case_selection"]),
        expected_event_count=len(result["events"]),
        expected_operator_action_count=len(actions),
        expected_metric_results=copy.deepcopy(result["receipt"]["metric_results"]),
        expected_case_ids=tuple(request["case_selection"]),
        expected_operator_actions=actions,
    )
    assert receipt_validation["is_valid"] is True
    assert receipt_validation["errors"] == ()


def test_inputs_remain_unchanged_by_the_run() -> None:
    corpus = _corpus()
    request = _request(corpus)
    actions = _actions(corpus, request)
    corpus_before = copy.deepcopy(corpus)
    request_before = copy.deepcopy(request)
    actions_before = copy.deepcopy(actions)
    run_measurement(request, corpus, actions)
    assert corpus == corpus_before
    assert request == request_before
    assert actions == actions_before


def test_metric_split_is_exactly_39_22_17_with_empty_wave2_values() -> None:
    metric_results = _run()["receipt"]["metric_results"]
    assert len(metric_results) == 39
    wave1_valid = [
        m for m in metric_results if m["measurement_status"] == "MEASURED_VALID"
    ]
    wave2_blocked = [
        m for m in metric_results if m["measurement_status"] == "BLOCKED_WAVE_2"
    ]
    assert len(wave1_valid) == 22
    assert len(wave2_blocked) == 17
    assert all(m["wave"] == "WAVE_1" for m in wave1_valid)
    assert all(m["wave"] == "WAVE_2" for m in wave2_blocked)
    for m in wave2_blocked:
        assert m["failure_codes"] == ("BLOCKED_WAVE_2",)
        assert all(m[field] is None for field in VALUE_FIELDS)
    populated_wave2 = sum(
        any(m[field] is not None for field in VALUE_FIELDS)
        for m in metric_results
        if m["wave"] == "WAVE_2"
    )
    assert populated_wave2 == 0


def test_repeatability_and_safety_gates_and_action_counts() -> None:
    receipt = _run()["receipt"]
    assert len(receipt["repeatability_results"]) == 14
    assert all(state == "PASS" for _, state in receipt["repeatability_results"])
    assert len(receipt["safety_flags"]) == 12
    assert all(value is True for _, value in receipt["safety_flags"])
    action_counts = dict(receipt["operator_action_counts"])
    assert action_counts["ACKNOWLEDGE"] == 14
    assert all(
        action_counts[name] == 0
        for name in (
            "NO_ACTION",
            "REQUEST_CORRECTION",
            "RETRY_CASE",
            "DEFER_CASE",
            "ABORT_RUN",
        )
    )


def test_canonical_hashes_match_the_recorded_evidence() -> None:
    result = _run()
    assert _canonical_sha256(result["events"]) == EVENT_STREAM_SHA256
    assert _canonical_sha256(result["receipt"]) == RECEIPT_SHA256
    assert _canonical_sha256(result) == PUBLIC_RESULT_SHA256


def test_recorded_hashes_appear_in_committed_doc_and_status_fragment() -> None:
    doc = REVIEW_DOC.read_text(encoding="utf-8")
    status = STATUS_FRAGMENT.read_text(encoding="utf-8")
    for digest in (EVENT_STREAM_SHA256, RECEIPT_SHA256, PUBLIC_RESULT_SHA256):
        assert digest in doc
        assert digest in status


def test_second_replay_is_byte_equal_regression_evidence_only() -> None:
    first = _run()
    second = _run()
    assert _canonical_sha256(first["events"]) == _canonical_sha256(second["events"])
    assert _canonical_sha256(first["receipt"]) == _canonical_sha256(second["receipt"])
    assert _canonical_sha256(first) == _canonical_sha256(second)
    assert _canonical_sha256(second["events"]) == EVENT_STREAM_SHA256
    assert _canonical_sha256(second["receipt"]) == RECEIPT_SHA256
    assert _canonical_sha256(second) == PUBLIC_RESULT_SHA256


def test_no_time_random_environment_or_path_value_appears() -> None:
    text = _canonical_text(_run())
    assert not _TIMESTAMP.search(text)
    assert not _UUID.search(text)
    assert not _ABS_PATH.search(text)


def test_no_forbidden_positive_capability_appears() -> None:
    text = _canonical_text(_run()).lower()
    for variant in FORBIDDEN_POSITIVE_VARIANTS:
        assert variant not in text


def test_dry_run_creates_no_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _run()
    assert result["is_valid"] is True
    assert result["receipt"]["temporary_output_status"] == "IN_MEMORY_ONLY"
    assert list(tmp_path.iterdir()) == []
