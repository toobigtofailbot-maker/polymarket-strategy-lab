from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.data_layer.analytical_research import experiment_os as os_contract
from src.paper_trading import (
    PaperEngine,
    PaperMarketEvent,
    PaperRiskLimits,
    PaperStore,
    build_strategy_binding,
)
from src.research_runtime.executable_edge import (
    MarketTruthEvent,
    MarketTruthWindow,
    ResearchDecisionEvent,
    assess_executable_edge,
    build_execution_cost_model,
    build_research_decision_trace,
    identify_market_truth_window,
)
from tests.data_layer.analytical_research.test_experiment_os_lifecycle_evidence import (
    evidence_input,
    lifecycle,
)
from tests.data_layer.analytical_research.test_experiment_os_preregistration import (
    experiment_stack,
)


def edge_stack(mode: str = "AGGRESSIVE_TAKER", **model_overrides):
    values = dict(
        model_version="wp173-test/1",
        execution_mode=mode,
        fee_schedule_reference="local:fees:v1",
        fee_rate_bps="100",
        latency_ns=10,
        order_ttl_ns=50 if mode == "PASSIVE_MAKER" else None,
        size_grid=("4", "8"),
        queue_ahead_multiplier="1",
        markout_horizon_ns=0,
        net_edge_threshold="0.01",
        minimum_fill_ratio="0.5",
        minimum_capacity_quantity="4",
        max_data_age_ns=100,
    )
    values.update(model_overrides)
    model = build_execution_cost_model(**values)
    records = experiment_stack(cost_model_reference=model.cost_model_id)
    experiment = records[-1]
    receipts = lifecycle(experiment, 5)
    evidence = os_contract._build_run_evidence_receipt(
        experiment,
        records[3],
        records[4],
        records[7],
        receipts,
        (),
        evidence_input(records[4], "OUT_OF_SAMPLE"),
        allow_oos=True,
        prior_oos_release_count=0,
    ).record
    reference = "0.49" if mode == "PASSIVE_MAKER" else "0.5"
    trace = build_research_decision_trace(
        experiment,
        evidence,
        (
            ResearchDecisionEvent(
                "market:a", "asset:a", 100, "BUY", "ENTER", "4", reference, "0.9"
            ),
        ),
    )
    decision_book = MarketTruthEvent(
        "BOOK", 99, 100, (("0.49", "5"),), (("0.51", "5"), ("0.55", "5"))
    )
    book = MarketTruthEvent(
        "BOOK", 109, 110, (("0.49", "5"),), (("0.51", "5"), ("0.55", "5"))
    )
    events = [decision_book, book]
    if mode == "PASSIVE_MAKER":
        events.extend(
            (
                MarketTruthEvent(
                    "TRADE", 114, 115, side="SELL", price="0.49", size="5"
                ),
                MarketTruthEvent(
                    "TRADE", 119, 120, side="SELL", price="0.49", size="4"
                ),
            )
        )
    if model.markout_horizon_ns:
        target = 100 + model.latency_ns + model.markout_horizon_ns
        events.append(
            MarketTruthEvent(
                "BOOK",
                target - 1,
                target,
                (("0.44", "5"),),
                (("0.46", "5"),),
            )
        )
    provisional = MarketTruthWindow(
        "",
        "ext:wp173-test",
        "asset:a.POLYMARKET",
        "test/1",
        ("a" * 64 + ":0",),
        "NONE",
        True,
        100,
        events[-1].receive_time_ns,
        tuple(events),
        True,
        True,
    )
    window = replace(provisional, lineage_id=identify_market_truth_window(provisional))
    assessment = assess_executable_edge(experiment, evidence, trace, model, window)
    assert assessment.status == "EXECUTABLE_EDGE_PASS"
    binding = build_strategy_binding(
        assessment, model, strategy_label="wp173-test", created_time_ns=1
    )
    return model, experiment, evidence, trace, window, assessment, binding


def generous_limits(**overrides) -> PaperRiskLimits:
    values = dict(
        initial_cash="100",
        max_single_order_notional="100",
        max_per_market_gross_exposure="100",
        max_total_gross_exposure="100",
        max_open_orders=10,
        max_session_drawdown="100",
        max_utc_day_loss="100",
        minimum_free_cash_reserve="0",
        max_market_data_age_ns=100,
        max_position_quantity="100",
    )
    values.update(overrides)
    return PaperRiskLimits(**values)


def paper_book(receive: int, *, bid="0.49", ask="0.51", bid_size="20", ask_size="20"):
    return PaperMarketEvent(
        "BOOK",
        "market:a",
        "asset:a",
        receive - 1,
        receive,
        f"fixture:book:{receive}",
        ((bid, bid_size),),
        ((ask, ask_size),),
    )


def make_engine(path: Path, *, mode="AGGRESSIVE_TAKER", limits=None):
    model, _experiment, _evidence, _trace, _window, assessment, binding = edge_stack(
        mode
    )
    store = PaperStore(path, create=True)
    engine = PaperEngine.create(
        store,
        binding,
        limits or generous_limits(),
        assessment=assessment,
        cost_model=model,
        session_label="session-a",
        created_time_ns=1,
    )
    return store, engine
