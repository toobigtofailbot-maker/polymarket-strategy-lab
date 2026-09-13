"""Conservative exact-arithmetic fill and cost evaluation for WP172."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from src.data_layer.analytical_research import PreregisteredExperiment, RunEvidenceReceipt
from src.data_layer.analytical_research.experiment_os import record_to_mapping

from .market_truth import MarketTruthEvent, MarketTruthWindow, validate_market_truth_window
from .models import (
    ASSESSMENT_SCHEMA_ID,
    SCHEMA_VERSION,
    ExecutableEdgeAssessment,
    ExecutableEdgeError,
    ExecutionCostModel,
    ResearchDecisionEvent,
    ResearchDecisionTrace,
    authoritative_first_look,
    decimal_text,
    identify_assessment,
    validate_execution_cost_model,
    validate_research_decision_trace,
)


def _book_at(events: tuple[MarketTruthEvent, ...], receive_ns: int) -> MarketTruthEvent | None:
    books = [event for event in events if event.kind == "BOOK" and event.receive_time_ns <= receive_ns]
    return books[-1] if books else None


def _mid(book: MarketTruthEvent) -> Decimal | None:
    if not book.bids or not book.asks:
        return None
    best_bid = Decimal(book.bids[0][0])
    best_ask = Decimal(book.asks[0][0])
    if best_bid >= best_ask:
        return None
    return (best_bid + best_ask) / 2


def _signed(side: str, later: Decimal, earlier: Decimal) -> Decimal:
    return later - earlier if side == "BUY" else earlier - later


def _sweep(levels: tuple[tuple[str, str], ...], quantity: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    remaining = quantity
    filled = Decimal(0)
    notional = Decimal(0)
    for price_text, size_text in levels:
        take = min(remaining, Decimal(size_text))
        if take > 0:
            filled += take
            notional += take * Decimal(price_text)
            remaining -= take
        if remaining == 0:
            break
    average = notional / filled if filled else Decimal(0)
    return filled, notional, average


def _aggressive(
    event: ResearchDecisionEvent, window: MarketTruthWindow, model: ExecutionCostModel,
    quantity: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal] | None:
    arrival = event.decision_time_ns + model.latency_ns
    book = _book_at(window.events, arrival)
    if book is None or arrival - book.receive_time_ns > model.max_data_age_ns:
        return None
    mid = _mid(book)
    if mid is None:
        return None
    levels = book.asks if event.side == "BUY" else book.bids
    filled, notional, average = _sweep(levels, quantity)
    best = Decimal(levels[0][0]) if levels else mid
    reference = Decimal(event.decision_reference_price)
    spread = abs(best - mid) * filled
    latency = _signed(event.side, mid, reference) * filled
    slippage = _signed(event.side, average, best) * filled if filled else Decimal(0)
    return filled, notional, average, spread, latency, slippage


def _passive(
    event: ResearchDecisionEvent, window: MarketTruthWindow, model: ExecutionCostModel,
    quantity: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal] | None:
    arrival = event.decision_time_ns + model.latency_ns
    expiry = arrival + int(model.order_ttl_ns or 0)
    book = _book_at(window.events, arrival)
    if book is None or arrival - book.receive_time_ns > model.max_data_age_ns:
        return None
    mid = _mid(book)
    if mid is None:
        return None
    limit = Decimal(event.decision_reference_price)
    levels = book.bids if event.side == "BUY" else book.asks
    visible = sum(Decimal(size) for price, size in levels if Decimal(price) == limit)
    if visible <= 0:
        return (Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    queue = visible * Decimal(model.queue_ahead_multiplier)
    eligible_flow = Decimal(0)
    for trade in window.events:
        if trade.kind != "TRADE" or not arrival <= trade.receive_time_ns <= expiry:
            continue
        price = Decimal(trade.price or "0")
        consumes = (
            event.side == "BUY" and trade.side == "SELL" and price <= limit
        ) or (
            event.side == "SELL" and trade.side == "BUY" and price >= limit
        )
        if consumes:
            eligible_flow += Decimal(trade.size or "0")
    filled = min(quantity, max(Decimal(0), eligible_flow - queue))
    notional = filled * limit
    # The passive limit is the trace's frozen reference; gross edge is already measured
    # from that price, so charging/crediting spread again would double count it.
    return filled, notional, limit if filled else Decimal(0), Decimal(0), Decimal(0), Decimal(0)


def _markout_cost(
    event: ResearchDecisionEvent, window: MarketTruthWindow, model: ExecutionCostModel,
    filled: Decimal,
) -> Decimal | None:
    if not filled or model.markout_horizon_ns == 0:
        return Decimal(0)
    target = event.decision_time_ns + model.latency_ns + model.markout_horizon_ns
    later = _book_at(window.events, target)
    if later is None or target - later.receive_time_ns > model.max_data_age_ns:
        return None
    later_mid = _mid(later)
    arrival_book = _book_at(window.events, event.decision_time_ns + model.latency_ns)
    arrival_mid = _mid(arrival_book) if arrival_book else None
    if later_mid is None or arrival_mid is None:
        return None
    return max(Decimal(0), -_signed(event.side, later_mid, arrival_mid)) * filled


def _fillable_quantity(event: ResearchDecisionEvent, window: MarketTruthWindow, model: ExecutionCostModel) -> Decimal | None:
    maximum = Decimal(0)
    for size in model.size_grid:
        quantity = Decimal(size)
        result = (_aggressive if model.execution_mode == "AGGRESSIVE_TAKER" else _passive)(
            event, window, model, quantity
        )
        if result is None:
            return None
        filled = result[0]
        if filled / quantity >= Decimal(model.minimum_fill_ratio):
            maximum = quantity
    return maximum


def assess_executable_edge(
    experiment: PreregisteredExperiment,
    evidence: RunEvidenceReceipt,
    trace: ResearchDecisionTrace,
    cost_model: ExecutionCostModel,
    market_truth: MarketTruthWindow,
) -> ExecutableEdgeAssessment:
    try:
        record_to_mapping(experiment)
        record_to_mapping(evidence)
    except Exception as exc:
        raise ExecutableEdgeError("WP170_EVIDENCE_INVALID") from exc
    validate_research_decision_trace(trace)
    validate_execution_cost_model(cost_model)
    validate_market_truth_window(market_truth)
    if trace.experiment_id != experiment.experiment_id or trace.first_look_evidence_id != evidence.run_evidence_receipt_id:
        raise ExecutableEdgeError("WP170_EVIDENCE_INVALID")

    diagnostics: list[str] = []
    cost_bound = experiment.cost_model_reference == cost_model.cost_model_id
    first_look = authoritative_first_look(experiment, evidence)
    if not cost_bound:
        diagnostics.append("COST_MODEL_REFERENCE_MISMATCH")
    if not first_look:
        diagnostics.append("FIRST_LOOK_OOS_NOT_AUTHORITATIVE")
    if not market_truth.continuity_complete:
        diagnostics.append("MARKET_DATA_CONTINUITY_INCOMPLETE")
    if cost_model.fee_rate_bps is None:
        diagnostics.append("FEE_REGIME_UNKNOWN")

    gross = spread = slippage = latency = adverse = intended = filled = notional = Decimal(0)
    capacity = None
    temporal_inconclusive = False
    for decision in trace.events:
        quantity = Decimal(decision.intended_quantity)
        intended += quantity
        result = (_aggressive if cost_model.execution_mode == "AGGRESSIVE_TAKER" else _passive)(
            decision, market_truth, cost_model, quantity
        )
        if result is None:
            temporal_inconclusive = True
            continue
        event_filled, event_notional, _average, event_spread, event_latency, event_slippage = result
        markout = _markout_cost(decision, market_truth, cost_model, event_filled)
        event_capacity = _fillable_quantity(decision, market_truth, cost_model)
        if markout is None or event_capacity is None:
            temporal_inconclusive = True
            continue
        filled += event_filled
        notional += event_notional
        spread += event_spread
        latency += event_latency
        slippage += event_slippage
        adverse += markout
        value = Decimal(decision.estimated_value)
        reference = Decimal(decision.decision_reference_price)
        gross += _signed(decision.side, value, reference) * event_filled
        capacity = event_capacity if capacity is None else min(capacity, event_capacity)
    if temporal_inconclusive:
        diagnostics.append("MARKET_DATA_WINDOW_UNAVAILABLE")
    capacity = capacity or Decimal(0)
    fill_ratio = filled / intended if intended else Decimal(0)
    capacity_pass = capacity >= Decimal(cost_model.minimum_capacity_quantity)

    fee: Decimal | None = None
    net: Decimal | None = None
    net_edge: Decimal | None = None
    if cost_model.fee_rate_bps is not None:
        effective_bps = Decimal(cost_model.fee_rate_bps)
        if cost_model.execution_mode == "PASSIVE_MAKER":
            effective_bps -= Decimal(cost_model.maker_rebate_bps)
        fee = notional * effective_bps / Decimal(10_000)
        net = gross - spread - slippage - latency - fee - adverse
        net_edge = net / filled if filled else Decimal(0)

    if not cost_bound or not first_look:
        status = "DIAGNOSTIC_ONLY"
    elif not market_truth.continuity_complete or temporal_inconclusive or fee is None:
        status = "EXECUTABLE_EDGE_INCONCLUSIVE"
    elif (
        fill_ratio < Decimal(cost_model.minimum_fill_ratio)
        or not capacity_pass
        or net_edge is None
        or net_edge < Decimal(cost_model.net_edge_threshold)
    ):
        status = "EXECUTABLE_EDGE_FAIL"
    else:
        status = "EXECUTABLE_EDGE_PASS"

    provisional = ExecutableEdgeAssessment(
        ASSESSMENT_SCHEMA_ID, SCHEMA_VERSION, "", experiment.experiment_id,
        evidence.run_evidence_receipt_id, trace.trace_id, cost_model.cost_model_id,
        market_truth.lineage_id, status, status == "EXECUTABLE_EDGE_PASS",
        decimal_text(gross), decimal_text(spread), decimal_text(slippage),
        decimal_text(latency), None if fee is None else decimal_text(fee),
        decimal_text(adverse), decimal_text(filled), decimal_text(intended),
        decimal_text(fill_ratio), None if net is None else decimal_text(net),
        None if net_edge is None else decimal_text(net_edge), decimal_text(capacity),
        capacity_pass,
        (
            "LOCAL_OFFLINE_RESEARCH_ONLY",
            "WP168_RECEIVE_TIME_PRIMARY_MARKET_TRUTH",
            "NO_NAUTILUS_DEFAULT_FILL_PROOF",
            f"EXECUTION_MODE_{cost_model.execution_mode}",
        ),
        tuple(diagnostics), True, True,
    )
    return replace(provisional, assessment_id=identify_assessment(provisional))
