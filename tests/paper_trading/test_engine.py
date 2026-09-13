from decimal import Decimal

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperMarketEvent,
    PaperStore,
    PaperTradingError,
    build_paper_intent,
)
from src.research_runtime.executable_edge.evaluator import _aggressive, _passive

from conftest import edge_stack, generous_limits, make_engine, paper_book


def _intent(binding, *, decision=100, quantity="4", side="BUY", reference=None):
    return build_paper_intent(
        binding,
        market_id="market:a",
        asset_id="asset:a",
        side=side,
        quantity=quantity,
        order_style=binding.execution_mode,
        reference_price=reference
        or ("0.49" if binding.execution_mode == "PASSIVE_MAKER" else "0.5"),
        decision_time_ns=decision,
    )


def test_order_lifecycle_idempotency_partial_fill_cancel_and_expiry(tmp_path) -> None:
    store, engine = make_engine(tmp_path / "aggressive.sqlite3")
    engine.process_market_event(paper_book(100, ask_size="2"))
    intent = _intent(engine.state.binding, quantity="4")
    opened = engine.submit(intent)
    assert opened.status == "OPEN"
    assert engine.submit(intent) == opened
    engine.process_market_event(paper_book(110, ask_size="2"))
    final = next(
        order for order in engine.state.orders if order.intent_id == intent.intent_id
    )
    assert final.status == "CANCELLED" and final.filled_quantity == "2"
    types = [event.event_type for event in store.events()]
    assert types.index("RISK_DECIDED") < types.index("ORDER_OPENED")
    assert "PAPER_FILL" in types
    assert types.index("PAPER_FILL") < types.index("ORDER_CANCELLED")
    assert types[-1] == "FILL_MARKOUT"
    store.close()

    store, engine = make_engine(tmp_path / "passive.sqlite3", mode="PASSIVE_MAKER")
    engine.process_market_event(paper_book(100))
    first = engine.submit(_intent(engine.state.binding))
    engine.process_market_event(paper_book(110, bid_size="5"))
    assert (
        next(
            order for order in engine.state.orders if order.order_id == first.order_id
        ).filled_quantity
        == "0"
    )
    engine.advance_time(161)
    assert (
        next(
            order for order in engine.state.orders if order.order_id == first.order_id
        ).status
        == "EXPIRED"
    )
    second = engine.submit(_intent(engine.state.binding, decision=200))
    assert second.status == "OPEN"
    assert engine.cancel(second.order_id, 201).status == "CANCELLED"
    store.close()


def test_one_order_replay_matches_wp172_fill_and_fee_semantics(tmp_path) -> None:
    model, _exp, _ev, trace, window, assessment, binding = edge_stack()
    store, engine = make_engine(tmp_path / "aggressive.sqlite3")
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(binding))
    arrival = PaperMarketEvent(
        "BOOK",
        "market:a",
        "asset:a",
        109,
        110,
        "wp172:arrival",
        (("0.49", "5"),),
        (("0.51", "5"), ("0.55", "5")),
    )
    engine.process_market_event(arrival)
    paper_order = engine.state.orders[0]
    wp172 = _aggressive(trace.events[0], window, model, Decimal("4"))
    assert wp172 is not None
    assert paper_order.filled_quantity == assessment.filled_quantity == str(wp172[0])
    assert (
        Decimal(paper_order.fill_notional) / Decimal(paper_order.filled_quantity)
        == wp172[2]
    )
    assert paper_order.fee_paid == assessment.fee_cost
    paper_fill = engine.state.fills[0]
    assert paper_fill.spread_cost == assessment.spread_cost == str(wp172[3])
    assert Decimal(paper_fill.latency_cost) == Decimal(assessment.latency_cost) == wp172[4]
    assert (
        paper_fill.depth_slippage_cost
        == assessment.depth_slippage_cost
        and Decimal(paper_fill.depth_slippage_cost) == wp172[5]
    )
    assert (
        engine.state.markouts[0].adverse_selection_cost
        == assessment.adverse_selection_cost
    )
    store.close()

    model, _exp, _ev, trace, window, assessment, binding = edge_stack("PASSIVE_MAKER")
    store, engine = make_engine(tmp_path / "passive.sqlite3", mode="PASSIVE_MAKER")
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(binding))
    engine.process_market_event(paper_book(110, bid_size="5", ask_size="5"))
    assert engine.state.fills == ()
    engine.process_market_event(
        PaperMarketEvent(
            "TRADE",
            "market:a",
            "asset:a",
            114,
            115,
            "wp172:trade:1",
            side="SELL",
            price="0.49",
            size="5",
        )
    )
    assert engine.state.fills == ()
    engine.process_market_event(
        PaperMarketEvent(
            "TRADE",
            "market:a",
            "asset:a",
            119,
            120,
            "wp172:trade:2",
            side="SELL",
            price="0.49",
            size="4",
        )
    )
    paper_order = engine.state.orders[0]
    wp172 = _passive(trace.events[0], window, model, Decimal("4"))
    assert wp172 is not None
    assert paper_order.filled_quantity == assessment.filled_quantity == str(wp172[0])
    assert paper_order.fee_paid == assessment.fee_cost
    assert engine.state.fills[0].spread_cost == assessment.spread_cost == "0"
    assert (
        engine.state.fills[0].depth_slippage_cost
        == assessment.depth_slippage_cost
        == "0"
    )
    assert engine.state.fills[0].latency_cost == assessment.latency_cost == "0"
    store.close()


def test_nonzero_markout_reporting_matches_wp172(tmp_path) -> None:
    model, _exp, _ev, _trace, _window, assessment, binding = edge_stack(
        markout_horizon_ns=10
    )
    with PaperStore(tmp_path / "markout.sqlite3", create=True) as store:
        engine = PaperEngine.create(
            store,
            binding,
            generous_limits(),
            assessment=assessment,
            cost_model=model,
            session_label="markout",
            created_time_ns=1,
        )
        engine.process_market_event(paper_book(100))
        engine.submit(_intent(binding))
        engine.process_market_event(paper_book(110, ask_size="5"))
        assert engine.state.markouts == ()
        engine.process_market_event(
            paper_book(120, bid="0.44", ask="0.46", ask_size="5")
        )
        assert (
            engine.state.markouts[0].adverse_selection_cost
            == assessment.adverse_selection_cost
            == "0.2"
        )


def test_pause_and_kill_controls_fail_closed_and_kill_is_terminal(tmp_path) -> None:
    store, engine = make_engine(tmp_path / "controls.sqlite3")
    engine.process_market_event(paper_book(100))
    engine.pause(101)
    paused = engine.submit(_intent(engine.state.binding, decision=102, quantity="1"))
    assert paused.status == "REJECTED"
    assert engine.state.risk_decisions[-1].reason_codes == ("CONTROL_NOT_RUNNING",)
    engine.resume(103)
    opened = engine.submit(_intent(engine.state.binding, decision=104, quantity="1"))
    assert opened.status == "OPEN"
    engine.kill(105)
    assert engine.state.control_state == "KILLED"
    assert (
        next(
            item for item in engine.state.orders if item.order_id == opened.order_id
        ).status
        == "CANCELLED"
    )
    with pytest.raises(PaperTradingError, match="CONTROL_TRANSITION_INVALID"):
        engine.resume(106)
    denied = engine.submit(_intent(engine.state.binding, decision=107, quantity="2"))
    assert denied.status == "REJECTED"
    assert "CONTROL_NOT_RUNNING" in engine.state.risk_decisions[-1].reason_codes
    store.close()


def test_resolution_pending_and_deterministic_settlement(tmp_path) -> None:
    store, engine = make_engine(tmp_path / "paper.sqlite3")
    engine.process_market_event(paper_book(100))
    engine.submit(_intent(engine.state.binding, quantity="2"))
    engine.process_market_event(paper_book(110))
    engine.process_market_event(
        PaperMarketEvent(
            "RESOLUTION", "market:a", "asset:a", 119, 120, "resolution:ambiguous"
        )
    )
    assert "market:a" in engine.state.resolution_pending
    denied = engine.submit(_intent(engine.state.binding, decision=121, quantity="1"))
    assert denied.status == "REJECTED"
    engine.process_market_event(
        PaperMarketEvent(
            "RESOLUTION",
            "market:a",
            "asset:a",
            129,
            130,
            "resolution:winner",
            winner_asset_id="asset:a",
        )
    )
    assert engine.state.account.positions == ()
    assert engine.state.account.cash == "100.9698"
    store.close()
