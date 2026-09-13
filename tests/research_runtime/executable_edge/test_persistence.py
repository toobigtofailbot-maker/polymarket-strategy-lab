from dataclasses import replace

import pytest

from src.data_layer.analytical_research import experiment_os as os_contract
from src.research_runtime.executable_edge import (
    ExecutableEdgeError, MarketTruthEvent, MarketTruthWindow, ResearchDecisionEvent,
    assess_executable_edge, build_execution_cost_model, build_research_decision_trace,
    deserialize_assessment, identify_market_truth_window, serialize_assessment, write_assessment,
)
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import evidence_input, lifecycle
from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack


def _assessment():
    model = build_execution_cost_model(
        model_version="persist/1", execution_mode="AGGRESSIVE_TAKER",
        fee_schedule_reference="local:fees:v1", fee_rate_bps="1", latency_ns=0,
        order_ttl_ns=None, size_grid=("1",), queue_ahead_multiplier="1",
        markout_horizon_ns=0, net_edge_threshold="0.01", minimum_fill_ratio="1",
        minimum_capacity_quantity="1", max_data_age_ns=100,
    )
    records = experiment_stack(cost_model_reference=model.cost_model_id)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment, records[3], records[4], records[7], receipts, (),
        evidence_input(records[4], "OUT_OF_SAMPLE"), allow_oos=True, prior_oos_release_count=0,
    ).record
    trace = build_research_decision_trace(experiment, evidence, (
        ResearchDecisionEvent("market:a", "asset:a", 100, "BUY", "ENTER", "1", "0.5", "0.7"),
    ))
    book = MarketTruthEvent("BOOK", 99, 100, (("0.49", "2"),), (("0.51", "2"),))
    provisional = MarketTruthWindow("", "ext:test", "asset:a.POLYMARKET", "test-conversion/1", ("c" * 64 + ":0",), "NONE", True, 100, 100, (book,), True, True)
    window = replace(provisional, lineage_id=identify_market_truth_window(provisional))
    return assess_executable_edge(experiment, evidence, trace, model, window)


def test_persistence_is_deterministic_tamper_evident_and_no_overwrite(tmp_path) -> None:
    assessment = _assessment()
    payload = serialize_assessment(assessment)
    assert deserialize_assessment(payload) == assessment
    output = tmp_path / "local_data"
    output.mkdir()
    path = output / "assessment.json"
    assert write_assessment(path, assessment) == "ASSESSMENT_WRITTEN"
    assert write_assessment(path, assessment) == "ASSESSMENT_WRITE_IDEMPOTENT"
    before = path.read_bytes()
    other = _assessment()
    from src.research_runtime.executable_edge.models import identify_assessment
    other = replace(other, diagnostic_codes=("DIFFERENT_VALID_EVIDENCE",))
    other = replace(other, assessment_id=identify_assessment(other))
    with pytest.raises(ExecutableEdgeError):
        write_assessment(path, other)
    assert path.read_bytes() == before
    tampered = payload.replace(b"EXECUTABLE_EDGE_PASS", b"EXECUTABLE_EDGE_FAIL")
    with pytest.raises(ExecutableEdgeError):
        deserialize_assessment(tampered)


def test_output_path_is_explicit_and_no_implicit_default(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ExecutableEdgeError):
        write_assessment("assessment.json", _assessment())
    outside = tmp_path / "assessment.json"
    with pytest.raises(ExecutableEdgeError):
        write_assessment(outside, _assessment())
