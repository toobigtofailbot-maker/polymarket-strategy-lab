"""Pure deterministic evaluation: ExecutionIntent + PublicExecutionVenueSnapshot -> assessment.

No network, filesystem, clock or environment access. The caller supplies
``evaluated_at_ns``. The result is a current-public mechanics assessment only: it is
not a profitability, strategy-merit, account-capacity, Gate-C or order decision.
"""

from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
)

from .models import (
    _PENDING_ID,
    ExecutionFeasibilityAssessment,
    ExecutionFeasibilityError,
    ExecutionIntent,
    PublicExecutionVenueSnapshot,
    decimal_text,
    derive_status,
    order_diagnostics,
    validate_execution_intent,
    validate_public_venue_snapshot,
)

MAX_SUPPORTED_FEE_EXPONENT = 8
FEE_QUANTUM = Decimal("0.00001")
RATIO_QUANTUM = Decimal("1E-18")
# Exact arithmetic: any rounding raises instead of silently losing precision.
_EXACT = Context(prec=4_000, traps=[Inexact, InvalidOperation, DivisionByZero, Overflow])
_CEILING = Context(prec=200, rounding=ROUND_CEILING, traps=[InvalidOperation, DivisionByZero])
_FLOOR = Context(prec=200, rounding=ROUND_FLOOR, traps=[InvalidOperation, DivisionByZero])

_ZERO = Decimal(0)
_ONE = Decimal(1)


def _d(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def _text(value: Decimal | None) -> str | None:
    return None if value is None else decimal_text(value)


def _market_dimension(snapshot: PublicExecutionVenueSnapshot, diags: set[str]) -> str:
    if snapshot.gamma_source_state != "AVAILABLE":
        return "UNKNOWN"
    checks = (
        (snapshot.active, True, "MARKET_INACTIVE"),
        (snapshot.closed, False, "MARKET_CLOSED"),
        (snapshot.accepting_orders, True, "MARKET_NOT_ACCEPTING_ORDERS"),
        (snapshot.enable_order_book, True, "ORDER_BOOK_DISABLED"),
    )
    failed = [code for value, good, code in checks if value is not None and value is not good]
    diags.update(failed)
    if failed:
        return "FAIL"
    if any(value is None for value, _good, _code in checks):
        return "UNKNOWN"
    return "PASS"


def _identity_dimension(snapshot: PublicExecutionVenueSnapshot, diags: set[str]) -> str:
    if (snapshot.gamma_neg_risk is not None and snapshot.book_neg_risk is not None
            and snapshot.gamma_neg_risk != snapshot.book_neg_risk):
        diags.add("NEG_RISK_SOURCE_CONFLICT")
        return "UNKNOWN"
    if snapshot.gamma_source_state != "AVAILABLE" or snapshot.clob_source_state != "AVAILABLE":
        return "UNKNOWN"
    return "PASS"


def _freshness_dimension(
    intent: ExecutionIntent, snapshot: PublicExecutionVenueSnapshot, diags: set[str]
) -> str:
    if snapshot.clob_source_state != "AVAILABLE":
        return "UNKNOWN"
    book_ns = snapshot.book_timestamp_ns
    if book_ns > snapshot.acquisition_completed_ns:  # type: ignore[operator]
        diags.add("BOOK_TIMESTAMP_INVALID")
        return "UNKNOWN"
    if snapshot.acquisition_completed_ns - book_ns > intent.max_public_data_age_ns:  # type: ignore[operator]
        diags.add("BOOK_STALE")
        return "UNKNOWN"
    return "PASS"


def _tick_dimension(
    price: Decimal, snapshot: PublicExecutionVenueSnapshot, diags: set[str]
) -> str:
    gamma_tick, book_tick = _d(snapshot.gamma_tick_size), _d(snapshot.book_tick_size)
    if gamma_tick is None or book_tick is None:
        return "UNKNOWN"
    if gamma_tick != book_tick:
        diags.add("TICK_SOURCE_CONFLICT")
        return "UNKNOWN"
    if _EXACT.remainder(price, gamma_tick) != 0:
        diags.add("PRICE_OFF_TICK")
        return "FAIL"
    return "PASS"


def _minimum_order(
    notional: Decimal, snapshot: PublicExecutionVenueSnapshot, diags: set[str]
) -> tuple[str, Decimal | None]:
    gamma_min = _d(snapshot.gamma_min_order_notional_usd)
    book_min = _d(snapshot.book_min_order_size_raw)
    if gamma_min is None or book_min is None:
        return "UNKNOWN", None
    if gamma_min != book_min:
        diags.add("MIN_ORDER_SOURCE_CONFLICT")
        return "UNKNOWN", None
    if notional < gamma_min:
        diags.add("MINIMUM_ORDER_NOTIONAL_NOT_MET")
        return "FAIL", gamma_min
    return "PASS", gamma_min


def _sweep(
    levels: tuple[tuple[str, str], ...], price_ok, requested: Decimal
) -> tuple[list[tuple[Decimal, Decimal]], Decimal, Decimal]:
    """Consume visible levels in best-first order within the exact price bound."""

    fills: list[tuple[Decimal, Decimal]] = []
    remaining = requested
    total_depth = _ZERO
    bound_depth = _ZERO
    for price_text, size_text in levels:
        price, size = Decimal(price_text), Decimal(size_text)
        total_depth = _EXACT.add(total_depth, size)
        if not price_ok(price):
            continue
        bound_depth = _EXACT.add(bound_depth, size)
        if remaining > 0:
            take = min(remaining, size)
            fills.append((price, take))
            remaining = _EXACT.subtract(remaining, take)
    return fills, total_depth, bound_depth


def _taker_fee(fills, rate: Decimal, exponent: int) -> Decimal:
    total = _ZERO
    for price, take in fills:
        variance = _EXACT.multiply(price, _EXACT.subtract(_ONE, price))
        factor = _EXACT.power(variance, exponent) if exponent else _ONE
        total = _EXACT.add(total, _EXACT.multiply(_EXACT.multiply(take, rate), factor))
    return total


def _fee(
    intent: ExecutionIntent,
    snapshot: PublicExecutionVenueSnapshot,
    fills,
    diags: set[str],
) -> tuple[str, str, Decimal | None, Decimal | None]:
    """Return (fee_dimension, fee_exactness, theoretical_unrounded, conservative_bound)."""

    enabled = snapshot.fees_enabled
    if enabled is None:
        diags.add("FEE_CONFIG_UNKNOWN")
        return "UNKNOWN", "UNKNOWN", None, None
    if enabled is False:
        return "PASS", "EXACT_ZERO_NO_FEES", _ZERO, _ZERO
    if snapshot.fee_taker_only is not True:
        diags.add("FEE_CONFIG_UNKNOWN")
        return "UNKNOWN", "UNKNOWN", None, None
    if intent.execution_style == "PASSIVE_MAKER":
        return "PASS", "EXACT_ZERO_MAKER", _ZERO, _ZERO
    rate, exponent = _d(snapshot.fee_rate), _d(snapshot.fee_exponent)
    if rate is None or exponent is None:
        diags.add("FEE_CONFIG_UNKNOWN")
        return "UNKNOWN", "UNKNOWN", None, None
    if exponent != exponent.to_integral_value() or exponent > MAX_SUPPORTED_FEE_EXPONENT:
        diags.add("FEE_EXPONENT_UNSUPPORTED")
        return "UNKNOWN", "UNKNOWN", None, None
    if fills is None:
        return "PASS", "UNKNOWN", None, None
    unrounded = _taker_fee(fills, rate, int(exponent))
    bound = unrounded.quantize(FEE_QUANTUM, rounding=ROUND_CEILING)
    return "PASS", "CONSERVATIVE_5DP_UPPER_BOUND", unrounded, bound


def assess_execution_feasibility(
    intent: ExecutionIntent,
    venue_snapshot: PublicExecutionVenueSnapshot,
    *,
    evaluated_at_ns: int,
) -> ExecutionFeasibilityAssessment:
    """Deterministically evaluate one exact intent against one public venue snapshot."""

    validate_execution_intent(intent)
    snapshot = validate_public_venue_snapshot(venue_snapshot)
    if isinstance(evaluated_at_ns, bool) or not isinstance(evaluated_at_ns, int):
        raise ExecutionFeasibilityError("FIELD_TYPE_INVALID")
    if evaluated_at_ns < snapshot.acquisition_completed_ns or evaluated_at_ns > 2**63 - 1:
        raise ExecutionFeasibilityError("FIELD_VALUE_INVALID")
    if (intent.gamma_market_id, intent.condition_id, intent.token_id) != (
        snapshot.gamma_market_id,
        snapshot.condition_id,
        snapshot.token_id,
    ):
        raise ExecutionFeasibilityError("IDENTITY_DERIVATION_MISMATCH")

    diags: set[str] = set(snapshot.diagnostic_codes)
    diags.update(("CLIENT_LATENCY_UNKNOWN", "ADVERSE_SELECTION_UNKNOWN"))
    aggressive = intent.execution_style == "AGGRESSIVE_TAKER"
    buy = intent.side == "BUY"
    requested = Decimal(intent.requested_shares)
    price_limit = Decimal(intent.price_limit)
    notional = _EXACT.multiply(requested, price_limit)

    dims = {
        "market_dimension": _market_dimension(snapshot, diags),
        "identity_dimension": _identity_dimension(snapshot, diags),
        "freshness_dimension": _freshness_dimension(intent, snapshot, diags),
        "tick_dimension": _tick_dimension(price_limit, snapshot, diags),
    }
    dims["minimum_order_dimension"], minimum = _minimum_order(notional, snapshot, diags)
    book_usable = dims["freshness_dimension"] == "PASS"
    dims["book_dimension"] = "PASS" if book_usable else "UNKNOWN"

    best_bid = _d(snapshot.bids[0][0]) if book_usable and snapshot.bids else None
    best_ask = _d(snapshot.asks[0][0]) if book_usable and snapshot.asks else None
    spread = _EXACT.subtract(best_ask, best_bid) if best_bid is not None and best_ask is not None else None
    metrics: dict[str, Decimal | None] = {
        "visible_fill_shares": None, "fill_ratio": None, "weighted_execution_price": None,
        "slippage_per_share": None, "slippage_cost_usd": None,
        "visible_depth_capacity_shares": None, "price_bound_capacity_shares": None,
    }
    fills = None
    if not book_usable:
        dims["fill_dimension"] = "UNKNOWN"
    elif aggressive:
        if buy:
            fills, depth, bound = _sweep(snapshot.asks, lambda p: p <= price_limit, requested)
        else:
            fills, depth, bound = _sweep(snapshot.bids, lambda p: p >= price_limit, requested)
        filled = _ZERO
        notional_filled = _ZERO
        for price, take in fills:
            filled = _EXACT.add(filled, take)
            notional_filled = _EXACT.add(notional_filled, _EXACT.multiply(price, take))
        metrics.update(
            visible_fill_shares=filled,
            fill_ratio=_FLOOR.divide(filled, requested).quantize(RATIO_QUANTUM, rounding=ROUND_FLOOR),
            visible_depth_capacity_shares=depth,
            price_bound_capacity_shares=bound,
        )
        if filled > 0:
            # Division-derived VWAP is quantized conservatively (BUY up, SELL down).
            if buy:
                vwap = _CEILING.divide(notional_filled, filled).quantize(RATIO_QUANTUM, rounding=ROUND_CEILING)
                per_share = _EXACT.subtract(vwap, best_ask)
            else:
                vwap = _FLOOR.divide(notional_filled, filled).quantize(RATIO_QUANTUM, rounding=ROUND_FLOOR)
                per_share = _EXACT.subtract(best_bid, vwap)
            if per_share < 0:
                raise ExecutionFeasibilityError("INTERNAL_VALIDATION_FAILED")
            metrics.update(
                weighted_execution_price=vwap,
                slippage_per_share=per_share,
                slippage_cost_usd=_EXACT.multiply(per_share, filled),
            )
        if filled == 0:
            diags.add("NO_VISIBLE_OPPOSING_LIQUIDITY")
        if intent.order_type == "FOK":
            if filled < requested:
                diags.add("FOK_INSUFFICIENT_VISIBLE_DEPTH")
                dims["fill_dimension"] = "FAIL"
            else:
                dims["fill_dimension"] = "PASS"
        elif filled == 0:
            dims["fill_dimension"] = "FAIL"
        elif filled < requested:
            diags.add("FAK_PARTIAL_VISIBLE_FILL")
            dims["fill_dimension"] = "LIMITED"
        else:
            dims["fill_dimension"] = "PASS"
    else:
        crosses = (best_ask is not None and price_limit >= best_ask) if buy else (
            best_bid is not None and price_limit <= best_bid
        )
        if crosses:
            diags.add("POST_ONLY_WOULD_CROSS")
            dims["fill_dimension"] = "FAIL"
        else:
            dims["fill_dimension"] = "PASS"

    fee_dimension, fee_exactness, fee_unrounded, fee_bound = _fee(intent, snapshot, fills, diags)
    dims["fee_dimension"] = fee_dimension

    if not aggressive:
        dims["delay_dimension"] = "NOT_APPLICABLE"
        diags.add("PASSIVE_FILL_UNKNOWN")
    elif snapshot.seconds_delay is None:
        dims["delay_dimension"] = "UNKNOWN"
    elif snapshot.seconds_delay > 0:
        diags.add("MARKETABLE_ORDER_DELAY")
        dims["delay_dimension"] = "LIMITED"
    else:
        dims["delay_dimension"] = "PASS"

    return ExecutionFeasibilityAssessment(
        execution_feasibility_assessment_id=_PENDING_ID,  # type: ignore[arg-type]
        strategy_version_id=intent.strategy_version_id,
        execution_rule_sha256=intent.execution_rule_sha256,
        execution_intent_id=intent.execution_intent_id,
        venue_snapshot_id=snapshot.venue_snapshot_id,
        information_cutoff_ns=intent.information_cutoff_ns,
        evaluated_at_ns=evaluated_at_ns,
        status=derive_status(dims),
        **dims,
        best_bid=_text(best_bid),
        best_ask=_text(best_ask),
        spread=_text(spread),
        requested_shares=intent.requested_shares,
        **{name: _text(value) for name, value in metrics.items()},
        minimum_order_notional_usd=_text(minimum),
        intent_notional_at_price_limit_usd=decimal_text(notional),
        fee_exactness=fee_exactness,
        theoretical_fee_unrounded_usd=_text(fee_unrounded),
        fee_upper_bound_usd=_text(fee_bound),
        maker_rebate_rate=snapshot.fee_rebate_rate,
        expected_maker_rebate_usd=None,
        seconds_delay=snapshot.seconds_delay,
        client_latency_state="UNKNOWN",
        client_latency_ns=None,
        passive_fill_state="NOT_APPLICABLE" if aggressive else "UNKNOWN",
        passive_fill_probability=None,
        adverse_selection_state="UNKNOWN",
        adverse_selection_cost=None,
        diagnostic_codes=order_diagnostics(diags),
    )


def validate_execution_feasibility_assessment(
    assessment: object,
    *,
    intent: ExecutionIntent | None = None,
    venue_snapshot: PublicExecutionVenueSnapshot | None = None,
) -> ExecutionFeasibilityAssessment:
    """Exact-type and round-trip validation; with both inputs, full re-evaluation equality."""

    if type(assessment) is not ExecutionFeasibilityAssessment:
        raise ExecutionFeasibilityError("FIELD_TYPE_INVALID")
    if ExecutionFeasibilityAssessment.from_mapping(assessment.to_mapping()) != assessment:
        raise ExecutionFeasibilityError("INTERNAL_VALIDATION_FAILED")
    if (intent is None) != (venue_snapshot is None):
        raise ExecutionFeasibilityError("FIELD_MISSING")
    if intent is not None:
        expected = assess_execution_feasibility(
            intent, venue_snapshot, evaluated_at_ns=assessment.evaluated_at_ns  # type: ignore[arg-type]
        )
        if expected != assessment:
            raise ExecutionFeasibilityError("IDENTITY_DERIVATION_MISMATCH")
    return assessment
