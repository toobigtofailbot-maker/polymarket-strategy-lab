from dataclasses import replace
from decimal import Decimal

from src.paper_trading import build_paper_intent, mark_account
from src.paper_trading.accounting import PaperAccount, PaperPosition
from src.paper_trading.risk import evaluate_risk

from conftest import edge_stack, generous_limits, make_engine, paper_book


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
