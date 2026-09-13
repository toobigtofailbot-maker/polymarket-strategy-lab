from dataclasses import replace

from src.data_layer.analytical_research import experiment_os as os_contract
from src.research_runtime.executable_edge import (
    MarketTruthEvent,
    MarketTruthWindow,
    ResearchDecisionEvent,
    assess_executable_edge,
    build_execution_cost_model,
    build_research_decision_trace,
    identify_market_truth_window,
)
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import evidence_input, lifecycle
from tests.data_layer.analytical_research.test_experiment_os_preregistration import experiment_stack


def _model(**overrides):
    values = dict(
        model_version="test/1", execution_mode="AGGRESSIVE_TAKER",
        fee_schedule_reference="local:fees:v1", fee_rate_bps="100", latency_ns=10,
        order_ttl_ns=None, size_grid=("5", "8", "12"), queue_ahead_multiplier="1",
        markout_horizon_ns=20, net_edge_threshold="0.05", minimum_fill_ratio="0.8",
        minimum_capacity_quantity="8", max_data_age_ns=100,
    )
    values.update(overrides)
    return build_execution_cost_model(**values)


def _evidence(model):
    records = experiment_stack(cost_model_reference=model.cost_model_id)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment, records[3], records[4], records[7], receipts, (),
        evidence_input(records[4], "OUT_OF_SAMPLE"), allow_oos=True, prior_oos_release_count=0,
    ).record
    return experiment, evidence


def _window(*events, continuity=True):
    provisional = MarketTruthWindow(
        "", "ext:test", "asset:a.POLYMARKET", "test-conversion/1", ("a" * 64 + ":0",),
        "NONE" if continuity else "KNOWN_GAPS", continuity,
        min(e.receive_time_ns for e in events), max(e.receive_time_ns for e in events),
        tuple(events), True, True,
    )
    return replace(provisional, lineage_id=identify_market_truth_window(provisional))


def _book(receive, bid="0.48", ask="0.52", bid_size="20", ask_size="5"):
    return MarketTruthEvent("BOOK", receive - 1, receive, ((bid, bid_size),), ((ask, ask_size),))


def _assessment(model, window, quantity="8", reference="0.5", value="0.7"):
    experiment, evidence = _evidence(model)
    trace = build_research_decision_trace(experiment, evidence, (
        ResearchDecisionEvent("market:a", "asset:a", 100, "BUY", "ENTER", quantity, reference, value),
    ))
    return assess_executable_edge(experiment, evidence, trace, model, window)


def test_aggressive_depth_fee_latency_and_partial_fill() -> None:
    model = _model()
    events = (
        MarketTruthEvent("BOOK", 109, 110, (("0.48", "20"),), (("0.52", "5"), ("0.55", "5"))),
        _book(130, bid="0.47", ask="0.51", ask_size="20"),
    )
    passed = _assessment(model, _window(*events))
    assert passed.status == "EXECUTABLE_EDGE_PASS"
    assert passed.filled_quantity == "8" and passed.intended_quantity == "8"
    assert passed.depth_slippage_cost == "0.09"
    assert passed.fee_cost == "0.0425"
    partial = _assessment(_model(minimum_fill_ratio="0.9"), _window(*events), quantity="12")
    assert partial.filled_quantity == "10" and partial.fill_ratio == "0.8333333333333333333333333333"
    assert partial.status == "EXECUTABLE_EDGE_FAIL"


def test_positive_gross_edge_overwhelmed_by_cost_or_threshold_fails() -> None:
    result = _assessment(_model(net_edge_threshold="0.2"), _window(_book(110), _book(130)), value="0.53")
    assert result.gross_research_result > "0"
    assert result.status == "EXECUTABLE_EDGE_FAIL"
    assert not result.wp173_evaluation_eligible


def test_passive_queue_requires_subsequent_trade_flow_and_marks_out() -> None:
    model = _model(
        execution_mode="PASSIVE_MAKER", order_ttl_ns=50, size_grid=("4",),
        minimum_fill_ratio="1", minimum_capacity_quantity="4", net_edge_threshold="0.01",
    )
    base = _book(110, bid="0.49", ask="0.51", bid_size="5", ask_size="10")
    mark = _book(130, bid="0.49", ask="0.51", bid_size="5", ask_size="10")
    touch_only = _assessment(model, _window(base, mark), quantity="4", reference="0.49")
    assert touch_only.filled_quantity == "0" and touch_only.status == "EXECUTABLE_EDGE_FAIL"
    flow = (
        base,
        MarketTruthEvent("TRADE", 114, 115, side="SELL", price="0.49", size="4"),
        MarketTruthEvent("TRADE", 119, 120, side="SELL", price="0.49", size="5"),
        mark,
    )
    filled = _assessment(model, _window(*flow), quantity="4", reference="0.49")
    assert filled.filled_quantity == "4"
    assert filled.status == "EXECUTABLE_EDGE_PASS"


def test_capacity_and_net_threshold_classification() -> None:
    stale = _assessment(_model(max_data_age_ns=1), _window(_book(100), _book(101)))
    assert stale.status == "EXECUTABLE_EDGE_INCONCLUSIVE"
    gapped = _assessment(_model(), _window(_book(110), _book(130), continuity=False))
    assert gapped.status == "EXECUTABLE_EDGE_INCONCLUSIVE"
    capacity = _assessment(_model(minimum_capacity_quantity="12", minimum_fill_ratio="1"), _window(_book(110), _book(130)))
    assert capacity.status == "EXECUTABLE_EDGE_FAIL" and not capacity.capacity_pass


def test_future_event_cannot_change_a_completed_decision_assessment() -> None:
    model = _model(markout_horizon_ns=0)
    base = _window(_book(110))
    future = MarketTruthEvent("BOOK", 999, 1000, (("0.1", "100"),), (("0.9", "100"),))
    with_future = _window(_book(110), future)
    first = _assessment(model, base)
    second = _assessment(model, with_future)
    assert (
        first.status, first.gross_research_result, first.spread_cost,
        first.depth_slippage_cost, first.latency_cost, first.fee_cost,
        first.adverse_selection_cost, first.filled_quantity, first.net_result,
        first.capacity_quantity,
    ) == (
        second.status, second.gross_research_result, second.spread_cost,
        second.depth_slippage_cost, second.latency_cost, second.fee_cost,
        second.adverse_selection_cost, second.filled_quantity, second.net_result,
        second.capacity_quantity,
    )
