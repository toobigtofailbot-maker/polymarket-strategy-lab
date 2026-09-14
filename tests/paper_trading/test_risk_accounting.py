from dataclasses import replace
from decimal import Decimal

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperMarketEvent,
    PaperOrder,
    PaperStore,
    build_paper_intent,
    mark_account,
)
from src.paper_trading.accounting import (
    PaperAccount,
    PaperPosition,
    free_position,
    reserve,
)
from src.paper_trading.risk import evaluate_risk

from tests.paper_trading.conftest import edge_stack, generous_limits, make_engine, paper_book


def _intent(binding, **overrides):
    values = dict(
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity="2",
        order_style=binding.execution_mode,
        reference_price="0.5",
        decision_time_ns=101,
    )
    values.update(overrides)
    return build_paper_intent(binding, **values)


def _open_order(intent, *, side="BUY", quantity="1", reference_price="0.5"):
    return PaperOrder(
        order_id="paperorder:sha256:" + ("a" if side == "BUY" else "b") * 64,
        intent_id=intent.intent_id,
        market_id="market:a",
        asset_id="asset:a",
        side=side,
        order_style="PASSIVE_MAKER",
        quantity=quantity,
        reference_price=reference_price,
        filled_quantity="0",
        fill_notional="0",
        fee_paid="0",
        status="OPEN",
        created_time_ns=100,
        arrival_time_ns=110,
        expiry_time_ns=160,
        reserved_cash="0" if side == "SELL" else quantity,
        reserved_quantity=quantity if side == "SELL" else "0",
        queue_ahead=None,
        risk_decision_id="paperrisk:sha256:" + "c" * 64,
    )


def _at_cap_risk_inputs(
    binding, *, intent, orders=(), reserved="0", held_quantity="10"
):
    return dict(
        intent=intent,
        limits=generous_limits(
            max_per_market_gross_exposure="5",
            max_total_gross_exposure="5",
        ),
        account=PaperAccount(
            "100",
            "96",
            "0",
            (
                PaperPosition(
                    "market:a",
                    "asset:a",
                    held_quantity,
                    str(Decimal(held_quantity) * Decimal("0.4")),
                    "0",
                ),
            ),
            (("asset:a", reserved),) if reserved != "0" else (),
            "0",
        ),
        orders=orders,
        marks={"asset:a": "0.5"},
        control_state="RUNNING",
        reconciliation_blocked=False,
        resolution_pending=set(),
        last_market_receive_ns=100,
        decided_time_ns=intent.decision_time_ns,
    )


def test_spot_accounting_reservations_cost_basis_and_equity_identity(tmp_path) -> None:
    store, engine = make_engine(tmp_path / "paper.sqlite3")
    engine.process_market_event(paper_book(100))
    buy = engine.submit(_intent(engine.state.binding))
    assert buy.reserved_cash == "2.02"
    assert (
        engine.state.account.cash == "100" and engine.summary()["free_cash"] == "97.98"
    )
    engine.process_market_event(paper_book(111))
    position = engine.state.account.positions[0]
    assert position.quantity == "2" and position.cost_basis == "1.0302"
    assert engine.summary()["equity"] == "99.9698"
    sell = engine.submit(
        _intent(
            engine.state.binding,
            side="SELL",
            quantity="1",
            reference_price="0.49",
            decision_time_ns=111,
        )
    )
    assert sell.reserved_quantity == "1"
    engine.process_market_event(paper_book(122))
    position = engine.state.account.positions[0]
    assert position.quantity == "1" and position.cost_basis == "0.5151"
    assert engine.state.account.realized_pnl == "-0.03"
    marked = mark_account(engine.state.account, dict(engine.state.marks))
    assert Decimal(marked["equity"]) == (
        Decimal(engine.state.account.cash) + Decimal(position.quantity) * Decimal("0.5")
    )
    store.close()


def test_every_paper_risk_limit_denies_before_open() -> None:
    *_, binding = edge_stack()
    intent = _intent(binding)
    account = PaperAccount(
        "100",
        "100",
        "0",
        (PaperPosition("market:a", "asset:a", "2", "2", "0"),),
        (),
        "0",
    )
    base = dict(
        intent=intent,
        limits=generous_limits(),
        account=account,
        orders=(),
        marks={"asset:a": "0.5"},
        control_state="RUNNING",
        reconciliation_blocked=False,
        resolution_pending=set(),
        last_market_receive_ns=100,
        decided_time_ns=101,
    )
    cases = (
        ({"reconciliation_blocked": True}, "RECONCILIATION_BLOCKED"),
        ({"control_state": "PAUSED"}, "CONTROL_NOT_RUNNING"),
        ({"resolution_pending": {"market:a"}}, "RESOLUTION_PENDING"),
        ({"marks": {}, "last_market_receive_ns": None}, "MARKET_DATA_UNAVAILABLE"),
        ({"decided_time_ns": 1000}, "MARKET_DATA_STALE"),
        (
            {
                "limits": generous_limits(max_open_orders=1),
                "orders": (
                    replace(
                        __import__(
                            "src.paper_trading.models", fromlist=["PaperOrder"]
                        ).PaperOrder(
                            "paperorder:sha256:" + "a" * 64,
                            "paperintent:sha256:" + "b" * 64,
                            "market:b",
                            "asset:b",
                            "BUY",
                            "AGGRESSIVE_TAKER",
                            "1",
                            "0.5",
                            "0",
                            "0",
                            "0",
                            "OPEN",
                            1,
                            1,
                            None,
                            "1",
                            "0",
                            None,
                            "paperrisk:sha256:" + "c" * 64,
                        ),
                        status="OPEN",
                    ),
                ),
            },
            "MAX_OPEN_ORDERS",
        ),
            (
                {"limits": generous_limits(max_single_order_notional="1.5")},
                "MAX_SINGLE_ORDER_NOTIONAL",
            ),
        ({"account": replace(account, cash="1")}, "INSUFFICIENT_FREE_CASH"),
        (
            {"limits": generous_limits(minimum_free_cash_reserve="99")},
            "MINIMUM_FREE_CASH_RESERVE",
        ),
        (
            {"intent": _intent(binding, side="SELL", quantity="3")},
            "INSUFFICIENT_FREE_POSITION",
        ),
        (
            {"limits": generous_limits(max_position_quantity="3")},
            "MAX_POSITION_QUANTITY",
        ),
        (
            {"limits": generous_limits(max_per_market_gross_exposure="1")},
            "MAX_PER_MARKET_GROSS_EXPOSURE",
        ),
        (
            {"limits": generous_limits(max_total_gross_exposure="1")},
            "MAX_TOTAL_GROSS_EXPOSURE",
        ),
        (
            {
                "limits": generous_limits(max_session_drawdown="1"),
                "marks": {"asset:a": "0"},
                "account": replace(account, cash="98"),
            },
            "MAX_SESSION_DRAWDOWN",
        ),
        (
                {
                    "limits": generous_limits(max_utc_day_loss="1"),
                    "account": replace(
                        account,
                        realized_pnl="-1",
                        daily_realized_pnl=(("0", "-1"),),
                    ),
                },
            "MAX_UTC_DAY_LOSS",
        ),
    )
    for override, expected in cases:
        decision = evaluate_risk(**{**base, **override})
        assert decision.result == "DENY" and expected in decision.reason_codes


def test_reservations_prevent_oversubscription_and_risk_precedes_open(tmp_path) -> None:
    store, engine = make_engine(
        tmp_path / "paper.sqlite3", limits=generous_limits(initial_cash="5")
    )
    engine.process_market_event(paper_book(100))
    assert engine.submit(_intent(engine.state.binding, quantity="4")).status == "OPEN"
    second = engine.submit(
        _intent(engine.state.binding, quantity="2", decision_time_ns=102)
    )
    assert second.status == "REJECTED"
    assert "INSUFFICIENT_FREE_CASH" in engine.state.risk_decisions[-1].reason_codes
    types = [event.event_type for event in store.events()]
    assert types.index("RISK_DECIDED") < types.index("ORDER_OPENED")
    store.close()


def test_open_aggressive_orders_count_conservatively_toward_aggregate_caps() -> None:
    *_, binding = edge_stack()
    first_intent = _intent(binding, quantity="4")
    open_order = PaperOrder(
        "paperorder:sha256:" + "a" * 64,
        first_intent.intent_id,
        "market:a", "asset:a", "BUY", "AGGRESSIVE_TAKER", "4", "0.1",
        "0", "0", "0", "OPEN", 100, 110, None, "4.04", "0", None,
        "paperrisk:sha256:" + "b" * 64,
    )
    account = PaperAccount("100", "100", "4.04", (), (), "0")
    common = dict(
        intent=_intent(binding, quantity="2", decision_time_ns=102),
        limits=generous_limits(
            max_per_market_gross_exposure="5", max_total_gross_exposure="5",
            max_position_quantity="5",
        ),
        account=account,
        orders=(open_order,),
        marks={"asset:a": "0.5"},
        control_state="RUNNING", reconciliation_blocked=False,
        resolution_pending=set(), last_market_receive_ns=100, decided_time_ns=102,
        conservative_buy_reserve="2.02",
    )
    reasons = evaluate_risk(**common).reason_codes
    assert "MAX_PER_MARKET_GROSS_EXPOSURE" in reasons
    assert "MAX_TOTAL_GROSS_EXPOSURE" in reasons
    assert "MAX_POSITION_QUANTITY" in reasons


@pytest.mark.parametrize(
    ("held_quantity", "limit_overrides", "reason"),
    (
        (
            "10",
            {
                "max_per_market_gross_exposure": "5",
                "max_total_gross_exposure": "100",
            },
            "MAX_PER_MARKET_GROSS_EXPOSURE",
        ),
        (
            "12",
            {
                "max_per_market_gross_exposure": "5",
                "max_total_gross_exposure": "100",
            },
            "MAX_PER_MARKET_GROSS_EXPOSURE",
        ),
        (
            "10",
            {
                "max_per_market_gross_exposure": "100",
                "max_total_gross_exposure": "5",
            },
            "MAX_TOTAL_GROSS_EXPOSURE",
        ),
        (
            "12",
            {
                "max_per_market_gross_exposure": "100",
                "max_total_gross_exposure": "5",
            },
            "MAX_TOTAL_GROSS_EXPOSURE",
        ),
    ),
)
def test_owned_sell_at_or_above_gross_cap_is_not_exposure_increasing(
    held_quantity, limit_overrides, reason
) -> None:
    *_, binding = edge_stack("PASSIVE_MAKER")
    intent = _intent(
        binding,
        side="SELL",
        quantity="1",
        reference_price="0.5",
    )
    inputs = _at_cap_risk_inputs(
        binding, intent=intent, held_quantity=held_quantity
    )
    inputs["limits"] = generous_limits(**limit_overrides)

    decision = evaluate_risk(**inputs)

    assert decision.result == "ALLOW"
    assert reason not in decision.reason_codes


def test_open_sell_reservation_prevents_overselling_without_adding_gross() -> None:
    *_, binding = edge_stack("PASSIVE_MAKER")
    first_intent = _intent(
        binding, side="SELL", quantity="6", reference_price="0.5"
    )
    first_inputs = _at_cap_risk_inputs(binding, intent=first_intent)
    first_decision = evaluate_risk(**first_inputs)
    assert first_decision.result == "ALLOW"

    first_order = _open_order(first_intent, side="SELL", quantity="6")
    reserved_account = reserve(first_inputs["account"], first_order)
    second_intent = _intent(
        binding,
        side="SELL",
        quantity="5",
        reference_price="0.5",
        decision_time_ns=102,
    )
    second = evaluate_risk(
        **{
            **first_inputs,
            "intent": second_intent,
            "account": reserved_account,
            "orders": (first_order,),
            "decided_time_ns": 102,
        }
    )

    assert second.result == "DENY"
    assert "INSUFFICIENT_FREE_POSITION" in second.reason_codes
    assert "MAX_PER_MARKET_GROSS_EXPOSURE" not in second.reason_codes
    assert "MAX_TOTAL_GROSS_EXPOSURE" not in second.reason_codes
    assert free_position(reserved_account, "asset:a") == Decimal("4")


def test_unfilled_sell_never_nets_held_gross_to_create_buy_capacity() -> None:
    *_, binding = edge_stack("PASSIVE_MAKER")
    sell_intent = _intent(
        binding, side="SELL", quantity="2", reference_price="0.5"
    )
    sell_order = _open_order(sell_intent, side="SELL", quantity="2")
    buy_intent = _intent(
        binding,
        side="BUY",
        quantity="1",
        reference_price="0.5",
        decision_time_ns=102,
    )
    inputs = _at_cap_risk_inputs(
        binding, intent=buy_intent, orders=(sell_order,), reserved="2"
    )

    decision = evaluate_risk(**inputs)

    assert decision.result == "DENY"
    assert "MAX_PER_MARKET_GROSS_EXPOSURE" in decision.reason_codes
    assert "MAX_TOTAL_GROSS_EXPOSURE" in decision.reason_codes


def test_reduce_only_sell_risk_decision_replays_identically_after_restart(
    tmp_path,
) -> None:
    path = tmp_path / "reduce-only-replay.sqlite3"
    limits = generous_limits(
        max_per_market_gross_exposure="5",
        max_total_gross_exposure="5",
    )
    store, engine = make_engine(path, mode="PASSIVE_MAKER", limits=limits)
    engine.process_market_event(paper_book(100, bid="0.39", ask="0.41"))
    buy = engine.submit(
        _intent(
            engine.state.binding,
            quantity="10",
            reference_price="0.39",
            decision_time_ns=101,
        )
    )
    assert buy.status == "OPEN"
    engine.process_market_event(
        paper_book(111, bid="0.39", ask="0.41", bid_size="5")
    )
    for receive, size in ((115, "5"), (120, "10")):
        engine.process_market_event(
            PaperMarketEvent(
                "TRADE",
                "market:a",
                "asset:a",
                receive - 1,
                receive,
                f"fixture:trade:{receive}",
                side="SELL",
                price="0.39",
                size=size,
            )
        )
    engine.process_market_event(paper_book(130, bid="0.59", ask="0.61"))
    assert engine.state.account.positions[0].quantity == "10"
    sell = engine.submit(
        _intent(
            engine.state.binding,
            side="SELL",
            quantity="2",
            reference_price="0.61",
            decision_time_ns=131,
        )
    )
    assert sell.status == "OPEN"
    assert engine.state.risk_decisions[-1].result == "ALLOW"
    expected_state = engine.state
    expected_decision = engine.state.risk_decisions[-1]
    store.close()

    with PaperStore(path) as reopened:
        recovered = PaperEngine.open(reopened)
        assert recovered.state == expected_state
        assert recovered.state.risk_decisions[-1] == expected_decision
        assert recovered.state.account.reserved_positions == (("asset:a", "2"),)


def test_utc_day_loss_resets_by_day_without_erasing_session_loss() -> None:
    *_, binding = edge_stack()
    intent = _intent(binding)
    account = PaperAccount(
        "100",
        "100",
        "0",
        (),
        (),
        "-2",
        (("0", "-2"),),
    )
    common = dict(
        intent=intent,
        limits=generous_limits(max_utc_day_loss="1"),
        account=account,
        orders=(),
        marks={"asset:a": "0.5"},
        control_state="RUNNING",
        reconciliation_blocked=False,
        resolution_pending=set(),
        last_market_receive_ns=100,
    )
    assert "MAX_UTC_DAY_LOSS" in evaluate_risk(
        **common, decided_time_ns=101
    ).reason_codes
    next_day = {
        **common,
        "decided_time_ns": 86_400_000_000_101,
        "last_market_receive_ns": 86_400_000_000_100,
    }
    assert "MAX_UTC_DAY_LOSS" not in evaluate_risk(**next_day).reason_codes
