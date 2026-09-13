from dataclasses import FrozenInstanceError, replace

import pytest

from src.research_runtime.executable_edge import (
    ExecutableEdgeError,
    ResearchDecisionEvent,
    build_execution_cost_model,
    build_research_decision_trace,
    validate_execution_cost_model,
    validate_research_decision_trace,
)
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import (
    evidence_input,
    lifecycle,
)
from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack
from src.data_layer.analytical_research import experiment_os as os_contract


def _model(**overrides):
    values = dict(
        model_version="wp172-test/1.0.0", execution_mode="AGGRESSIVE_TAKER",
        fee_schedule_reference="local:test-fees:v1", fee_rate_bps="100",
        latency_ns=10, order_ttl_ns=None, size_grid=("4", "8"),
        queue_ahead_multiplier="1", markout_horizon_ns=20,
        net_edge_threshold="0.05", minimum_fill_ratio="0.8",
        minimum_capacity_quantity="4", max_data_age_ns=100,
    )
    values.update(overrides)
    return build_execution_cost_model(**values)


def _experiment_evidence(cost_model_id):
    records = experiment_stack(cost_model_reference=cost_model_id)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment, records[3], records[4], records[7], receipts, (),
        evidence_input(records[4], "OUT_OF_SAMPLE"), allow_oos=True,
        prior_oos_release_count=0,
    ).record
    return experiment, evidence


def test_trace_is_ordered_content_addressed_and_future_independent() -> None:
    model = _model()
    experiment, evidence = _experiment_evidence(model.cost_model_id)
    events = (
        ResearchDecisionEvent("market:a", "asset:a", 100, "BUY", "ENTER", "4", "0.5", "0.7"),
        ResearchDecisionEvent("market:a", "asset:a", 200, "SELL", "EXIT", "4", "0.6", "0.4"),
    )
    first = build_research_decision_trace(experiment, evidence, events)
    second = build_research_decision_trace(experiment, evidence, events)
    assert first == second
    assert first.trace_id.startswith("decisiontrace:sha256:")
    assert all(not hasattr(first, name) for name in ("account_id", "order_id"))
    validate_research_decision_trace(first)
    with pytest.raises(ExecutableEdgeError):
        build_research_decision_trace(experiment, evidence, tuple(reversed(events)))
    with pytest.raises(ExecutableEdgeError):
        validate_research_decision_trace(replace(first, trace_id="decisiontrace:sha256:" + "0" * 64))
    with pytest.raises(FrozenInstanceError):
        first.trace_id = "changed"  # type: ignore[misc]


def test_cost_model_is_explicit_exact_and_unknown_fee_is_preserved() -> None:
    first = _model()
    assert first == _model()
    assert first.maker_rebate_bps == "0"
    assert _model(fee_rate_bps=None).fee_rate_bps is None
    assert _model(latency_ns=11).cost_model_id != first.cost_model_id
    validate_execution_cost_model(first)
    with pytest.raises(ExecutableEdgeError):
        _model(maker_rebate_bps="1")
    with pytest.raises(ExecutableEdgeError):
        _model(size_grid=("8", "4"))
    with pytest.raises(ExecutableEdgeError):
        _model(fee_rate_bps="0.0e0")
