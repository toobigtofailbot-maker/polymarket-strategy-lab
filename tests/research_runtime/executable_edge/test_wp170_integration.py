from dataclasses import replace

import pytest

from src.data_layer.analytical_research import experiment_os as os_contract
from src.research_runtime.executable_edge import (
    ExecutableEdgeError, MarketTruthEvent, MarketTruthWindow, ResearchDecisionEvent, assess_executable_edge,
    build_execution_cost_model, build_research_decision_trace, identify_market_truth_window,
)
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import evidence_input, lifecycle
from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack


def _model(fee="10"):
    return build_execution_cost_model(
        model_version="integration/1", execution_mode="AGGRESSIVE_TAKER",
        fee_schedule_reference="local:fees:v1", fee_rate_bps=fee, latency_ns=0,
        order_ttl_ns=None, size_grid=("1",), queue_ahead_multiplier="1",
        markout_horizon_ns=0, net_edge_threshold="0.01", minimum_fill_ratio="1",
        minimum_capacity_quantity="1", max_data_age_ns=100,
    )


def _records(model, cost_reference=True, ordinal=1):
    records = experiment_stack(cost_model_reference=model.cost_model_id if cost_reference else None)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment, records[3], records[4], records[7], receipts, (),
        evidence_input(records[4], "OUT_OF_SAMPLE"), allow_oos=True,
        prior_oos_release_count=ordinal - 1,
    ).record
    return experiment, evidence


def _window():
    event = MarketTruthEvent("BOOK", 99, 100, (("0.49", "2"),), (("0.51", "2"),))
    provisional = MarketTruthWindow("", "ext:test", "asset:a.POLYMARKET", "test-conversion/1", ("b" * 64 + ":0",), "NONE", True, 100, 100, (event,), True, True)
    return replace(provisional, lineage_id=identify_market_truth_window(provisional))


def _assess(model, experiment, evidence):
    trace = build_research_decision_trace(experiment, evidence, (
        ResearchDecisionEvent("market:a", "asset:a", 100, "BUY", "ENTER", "1", "0.5", "0.7"),
    ))
    return assess_executable_edge(experiment, evidence, trace, model, _window())


def test_first_look_cost_binding_controls_eligibility() -> None:
    model = _model()
    experiment, evidence = _records(model)
    result = _assess(model, experiment, evidence)
    assert result.status == "EXECUTABLE_EDGE_PASS" and result.wp173_evaluation_eligible
    assert result.experiment_id == experiment.experiment_id
    assert result.first_look_evidence_id == evidence.run_evidence_receipt_id
    null_experiment, null_evidence = _records(model, cost_reference=False)
    assert _assess(model, null_experiment, null_evidence).status == "DIAGNOSTIC_ONLY"


def test_reused_null_mismatch_and_unknown_fee_never_promote() -> None:
    model = _model()
    experiment, reused = _records(model, ordinal=2)
    assert reused.result_status == "OOS_REUSED_DIAGNOSTIC"
    assert _assess(model, experiment, reused).status == "DIAGNOSTIC_ONLY"
    other = _model(fee="11")
    first_experiment, first_evidence = _records(model)
    assert _assess(other, first_experiment, first_evidence).status == "DIAGNOSTIC_ONLY"
    unknown = _model(fee=None)
    unknown_experiment, evidence = _records(unknown)
    result = _assess(unknown, unknown_experiment, evidence)
    assert result.status == "EXECUTABLE_EDGE_INCONCLUSIVE"
    assert result.fee_cost is None and result.net_result is None


def test_tampered_wp170_record_is_rejected_not_diagnosed() -> None:
    model = _model()
    experiment, evidence = _records(model)
    trace = build_research_decision_trace(experiment, evidence, (
        ResearchDecisionEvent("market:a", "asset:a", 100, "BUY", "ENTER", "1", "0.5", "0.7"),
    ))
    with pytest.raises(ExecutableEdgeError, match="WP170_EVIDENCE_INVALID"):
        assess_executable_edge(
            replace(experiment, cost_model_reference=None), evidence, trace, model, _window()
        )
