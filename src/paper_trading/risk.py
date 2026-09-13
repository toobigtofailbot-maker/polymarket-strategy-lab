"""Non-overridable deterministic pre-order paper-risk decisions."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

from .accounting import (
    PaperAccount,
    free_cash,
    free_position,
    mark_account,
    position_map,
    utc_day_key,
)
from .models import (
    PaperIntent,
    PaperOrder,
    PaperRiskDecision,
    PaperRiskLimits,
    RISK_REASON_CODES,
    content_id,
    decimal_value,
    validate_risk_limits,
)


def limits_hash(limits: PaperRiskLimits) -> str:
    validate_risk_limits(limits)
    return content_id("paperlimits:sha256:", asdict(limits))


def _open(orders: tuple[PaperOrder, ...]) -> tuple[PaperOrder, ...]:
    return tuple(
        order for order in orders if order.status in {"OPEN", "PARTIALLY_FILLED"}
    )


def evaluate_risk(
    *,
    intent: PaperIntent,
    limits: PaperRiskLimits,
    account: PaperAccount,
    orders: tuple[PaperOrder, ...],
    marks: dict[str, str],
    control_state: str,
    reconciliation_blocked: bool,
    resolution_pending: set[str],
    last_market_receive_ns: int | None,
    decided_time_ns: int,
    conservative_buy_reserve: str | None = None,
) -> PaperRiskDecision:
    """Evaluate every frozen cap before opening; callers cannot override the result."""
    validate_risk_limits(limits)
    reasons: list[str] = []
    quantity = decimal_value(intent.quantity, nonnegative=True)
    reference = decimal_value(intent.reference_price, nonnegative=True)
    intended_notional = (
        quantity if intent.order_style == "AGGRESSIVE_TAKER" else quantity * reference
    )
    open_orders = _open(orders)
    if reconciliation_blocked:
        reasons.append("RECONCILIATION_BLOCKED")
    if control_state != "RUNNING":
        reasons.append("CONTROL_NOT_RUNNING")
    if intent.market_id in resolution_pending:
        reasons.append("RESOLUTION_PENDING")
    mark = marks.get(intent.asset_id)
    if mark is None or last_market_receive_ns is None:
        reasons.append("MARKET_DATA_UNAVAILABLE")
    elif decided_time_ns < last_market_receive_ns or (
        decided_time_ns - last_market_receive_ns > limits.max_market_data_age_ns
    ):
        reasons.append("MARKET_DATA_STALE")
    if len(open_orders) >= limits.max_open_orders:
        reasons.append("MAX_OPEN_ORDERS")
    if intended_notional > Decimal(limits.max_single_order_notional):
        reasons.append("MAX_SINGLE_ORDER_NOTIONAL")
    if intent.side == "BUY":
        reserve = (
            Decimal(conservative_buy_reserve)
            if conservative_buy_reserve is not None
            else quantity
        )
        if free_cash(account) < reserve:
            reasons.append("INSUFFICIENT_FREE_CASH")
        if free_cash(account) - reserve < Decimal(limits.minimum_free_cash_reserve):
            reasons.append("MINIMUM_FREE_CASH_RESERVE")
    elif free_position(account, intent.asset_id) < quantity:
        reasons.append("INSUFFICIENT_FREE_POSITION")
    positions = position_map(account)
    held = (
        Decimal(positions[intent.asset_id].quantity)
        if intent.asset_id in positions
        else Decimal(0)
    )
    pending_buy_quantity = sum(
        (
            Decimal(order.quantity) - Decimal(order.filled_quantity)
            for order in open_orders
            if order.side == "BUY" and order.asset_id == intent.asset_id
        ),
        Decimal(0),
    )
    projected_quantity = held + pending_buy_quantity + (
        quantity if intent.side == "BUY" else Decimal(0)
    )
    if limits.max_position_quantity is not None and projected_quantity > Decimal(
        limits.max_position_quantity
    ):
        reasons.append("MAX_POSITION_QUANTITY")

    def exposure(order: PaperOrder) -> Decimal:
        remaining = Decimal(order.quantity) - Decimal(order.filled_quantity)
        unit_value = (
            Decimal(1)
            if order.order_style == "AGGRESSIVE_TAKER"
            else Decimal(order.reference_price)
        )
        return remaining * unit_value

    market_open = sum(
        exposure(order) for order in open_orders if order.market_id == intent.market_id
    )
    total_open = sum((exposure(order) for order in open_orders), Decimal(0))
    position_market = sum(
        Decimal(position.quantity) * Decimal(marks.get(position.asset_id, "0"))
        for position in account.positions
        if position.market_id == intent.market_id
    )
    position_total = sum(
        (
            Decimal(position.quantity) * Decimal(marks.get(position.asset_id, "0"))
            for position in account.positions
        ),
        Decimal(0),
    )
    if position_market + market_open + intended_notional > Decimal(
        limits.max_per_market_gross_exposure
    ):
        reasons.append("MAX_PER_MARKET_GROSS_EXPOSURE")
    if position_total + total_open + intended_notional > Decimal(
        limits.max_total_gross_exposure
    ):
        reasons.append("MAX_TOTAL_GROSS_EXPOSURE")
    marked = mark_account(account, marks)
    if marked["equity"] is None:
        if "MARKET_DATA_UNAVAILABLE" not in reasons:
            reasons.append("MARKET_DATA_UNAVAILABLE")
    else:
        drawdown = max(
            Decimal(0), Decimal(account.initial_cash) - Decimal(marked["equity"])
        )
        if drawdown >= Decimal(limits.max_session_drawdown):
            reasons.append("MAX_SESSION_DRAWDOWN")
    daily = dict(account.daily_realized_pnl)
    day_realized = Decimal(daily.get(utc_day_key(decided_time_ns), "0"))
    if max(Decimal(0), -day_realized) >= Decimal(limits.max_utc_day_loss):
        reasons.append("MAX_UTC_DAY_LOSS")
    ordered = tuple(code for code in RISK_REASON_CODES if code in reasons)
    result = "DENY" if ordered else "ALLOW"
    preimage = {
        "intent_id": intent.intent_id,
        "result": result,
        "reason_codes": list(ordered),
        "decided_time_ns": decided_time_ns,
        "limits_hash": limits_hash(limits),
    }
    return PaperRiskDecision(
        content_id("paperrisk:sha256:", preimage),
        intent.intent_id,
        result,
        ordered,
        decided_time_ns,
        preimage["limits_hash"],
    )
