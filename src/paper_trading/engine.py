"""Deterministic simulated order lifecycle, fills, controls, and resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from collections.abc import Mapping, Sequence

from src.research_runtime.executable_edge import (
    ExecutableEdgeAssessment,
    ExecutionCostModel,
)

from .accounting import (
    PaperAccount,
    account_from_mapping,
    account_to_mapping,
    apply_fill,
    mark_account,
    new_account,
    release,
    reserve,
    settle_position,
    validate_account,
)
from .models import (
    CONTROL_STATES,
    PaperFill,
    PaperIntent,
    PaperMarkout,
    PaperMarketEvent,
    PaperOrder,
    PaperRiskDecision,
    PaperRiskLimits,
    PaperBinding,
    PaperStrategyBinding,
    ResearchPaperStrategyBinding,
    PaperTradingError,
    build_strategy_binding,
    content_id,
    dataclass_from_mapping,
    decimal_text,
    validate_market_event,
    validate_fill,
    validate_markout,
    validate_order,
    validate_paper_intent,
    validate_risk_decision,
    validate_risk_limits,
    validate_paper_binding,
    validate_research_strategy_binding,
    validate_strategy_binding,
)
from .risk import evaluate_risk, limits_hash
from .store import JournalEvent, JournalMutation, PaperStore, StoreHead, mutation


_ACTIVE = {"OPEN", "PARTIALLY_FILLED"}


@dataclass(frozen=True)
class BookSnapshot:
    market_id: str
    asset_id: str
    event_time_ns: int
    receive_time_ns: int
    lineage: str
    bids: tuple[tuple[str, str], ...]
    asks: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PaperState:
    session_id: str
    binding: PaperBinding
    limits: PaperRiskLimits
    control_state: str
    account: PaperAccount
    orders: tuple[PaperOrder, ...]
    fills: tuple[PaperFill, ...]
    markouts: tuple[PaperMarkout, ...]
    risk_decisions: tuple[PaperRiskDecision, ...]
    marks: tuple[tuple[str, str], ...]
    mark_times: tuple[tuple[str, int], ...]
    books: tuple[BookSnapshot, ...]
    gapped_assets: tuple[str, ...]
    resolution_pending: tuple[str, ...]
    last_market_receive_ns: int | None


def state_to_mapping(state: PaperState) -> dict[str, object]:
    binding = asdict(state.binding)
    if type(state.binding) is ResearchPaperStrategyBinding:
        for name in (
            "subject_refs",
            "allowed_market_ids",
            "reserved_evidence_refs",
            "admitted_scope_refs",
        ):
            binding[name] = list(binding[name])
    return {
        "session_id": state.session_id,
        "binding": binding,
        "limits": asdict(state.limits),
        "control_state": state.control_state,
        "account": account_to_mapping(state.account),
        "orders": [asdict(item) for item in state.orders],
        "fills": [asdict(item) for item in state.fills],
        "markouts": [asdict(item) for item in state.markouts],
        "risk_decisions": [
            {**asdict(item), "reason_codes": list(item.reason_codes)}
            for item in state.risk_decisions
        ],
        "marks": [list(item) for item in state.marks],
        "mark_times": [list(item) for item in state.mark_times],
        "books": [
            {
                **asdict(item),
                "bids": [list(level) for level in item.bids],
                "asks": [list(level) for level in item.asks],
            }
            for item in state.books
        ],
        "gapped_assets": list(state.gapped_assets),
        "resolution_pending": list(state.resolution_pending),
        "last_market_receive_ns": state.last_market_receive_ns,
    }


def state_from_mapping(value: Mapping[str, object]) -> PaperState:
    try:
        raw_binding = value["binding"]
    except (KeyError, TypeError):
        raise PaperTradingError("SERIALIZATION_INVALID") from None
    if (
        isinstance(raw_binding, Mapping)
        and "binding_kind" in raw_binding
        and raw_binding.get("binding_kind") != "RESEARCH_PAPER"
    ):
        raise PaperTradingError("BINDING_KIND_INVALID")
    try:
        if not isinstance(raw_binding, Mapping):
            raise PaperTradingError("SERIALIZATION_INVALID")
        if "binding_kind" not in raw_binding:
            binding = dataclass_from_mapping(PaperStrategyBinding, raw_binding)
        elif raw_binding.get("binding_kind") == "RESEARCH_PAPER":
            binding = dataclass_from_mapping(ResearchPaperStrategyBinding, raw_binding)
        limits = dataclass_from_mapping(PaperRiskLimits, value["limits"])
        account = account_from_mapping(value["account"])
        orders = tuple(
            dataclass_from_mapping(PaperOrder, item) for item in value["orders"]
        )
        fills = tuple(
            dataclass_from_mapping(PaperFill, item) for item in value["fills"]
        )
        markouts = tuple(
            dataclass_from_mapping(PaperMarkout, item) for item in value["markouts"]
        )
        decisions = tuple(
            dataclass_from_mapping(PaperRiskDecision, item)
            for item in value["risk_decisions"]
        )
        books = tuple(
            BookSnapshot(
                item["market_id"],
                item["asset_id"],
                item["event_time_ns"],
                item["receive_time_ns"],
                item["lineage"],
                tuple(tuple(level) for level in item["bids"]),
                tuple(tuple(level) for level in item["asks"]),
            )
            for item in value["books"]
        )
        state = PaperState(
            value["session_id"],
            binding,
            limits,
            value["control_state"],
            account,
            orders,
            fills,
            markouts,
            decisions,
            tuple(tuple(item) for item in value["marks"]),
            tuple((item[0], item[1]) for item in value["mark_times"]),
            books,
            tuple(value["gapped_assets"]),
            tuple(value["resolution_pending"]),
            value["last_market_receive_ns"],
        )
    except (KeyError, TypeError, ValueError):
        raise PaperTradingError("SERIALIZATION_INVALID") from None
    validate_paper_binding(state.binding)
    validate_risk_limits(state.limits)
    if state.control_state not in CONTROL_STATES:
        raise PaperTradingError("SERIALIZATION_INVALID")
    _validate_state_relationships(state)
    return state


def _validate_state_relationships(state: PaperState) -> None:
    validate_account(state.account)
    if Decimal(state.account.initial_cash) != Decimal(state.limits.initial_cash):
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    expected_limits_hash = limits_hash(state.limits)
    orders = {item.order_id: item for item in state.orders}
    if len(orders) != len(state.orders):
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    decisions = {item.decision_id: item for item in state.risk_decisions}
    if len(decisions) != len(state.risk_decisions):
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    for decision in state.risk_decisions:
        validate_risk_decision(decision)
        if decision.limits_hash != expected_limits_hash:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
    for order in state.orders:
        validate_order(order)
        if order.risk_decision_id is not None:
            decision = decisions.get(order.risk_decision_id)
            if decision is None or decision.intent_id != order.intent_id:
                raise PaperTradingError("RECONCILIATION_BLOCKED")
    fill_groups: dict[str, list[PaperFill]] = {}
    for fill in state.fills:
        validate_fill(fill)
        if fill.order_id not in orders:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        fill_groups.setdefault(fill.order_id, []).append(fill)
    for order_id, order in orders.items():
        fills = fill_groups.get(order_id, [])
        fills.sort(key=lambda item: item.fill_sequence)
        if [item.fill_sequence for item in fills] != list(range(1, len(fills) + 1)):
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        filled = Decimal(order.filled_quantity)
        quantity = Decimal(order.quantity)
        if (
            order.status == "FILLED"
            and filled != quantity
            or order.status == "PARTIALLY_FILLED"
            and not Decimal(0) < filled < quantity
            or order.status in {"PENDING_RISK", "REJECTED", "OPEN"}
            and filled != 0
            or order.status in {"REJECTED", "FILLED", "CANCELLED", "EXPIRED"}
            and (Decimal(order.reserved_cash) != 0 or Decimal(order.reserved_quantity) != 0)
        ):
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        if order.risk_decision_id is not None:
            decision = decisions[order.risk_decision_id]
            if (order.status == "REJECTED") != (decision.result == "DENY"):
                raise PaperTradingError("RECONCILIATION_BLOCKED")
        if (
            sum((Decimal(item.quantity) for item in fills), Decimal(0))
            != Decimal(order.filled_quantity)
            or sum(
                (
                    Decimal(item.quantity) * Decimal(item.price)
                    for item in fills
                ),
                Decimal(0),
            )
            != Decimal(order.fill_notional)
            or sum((Decimal(item.fee) for item in fills), Decimal(0))
            != Decimal(order.fee_paid)
        ):
            raise PaperTradingError("RECONCILIATION_BLOCKED")
    markout_fills: set[str] = set()
    for markout in state.markouts:
        validate_markout(markout)
        if markout.fill_id not in {item.fill_id for item in state.fills}:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        if markout.fill_id in markout_fills:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        markout_fills.add(markout.fill_id)
    active = [item for item in state.orders if item.status in _ACTIVE]
    if sum((Decimal(item.reserved_cash) for item in active), Decimal(0)) != Decimal(
        state.account.reserved_cash
    ):
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    expected_positions: dict[str, Decimal] = {}
    for order in active:
        if order.side == "SELL":
            expected_positions[order.asset_id] = expected_positions.get(
                order.asset_id, Decimal(0)
            ) + Decimal(order.reserved_quantity)
    actual_positions = {
        asset: Decimal(quantity)
        for asset, quantity in state.account.reserved_positions
    }
    if expected_positions != actual_positions:
        raise PaperTradingError("RECONCILIATION_BLOCKED")


def _with_order(state: PaperState, order: PaperOrder) -> PaperState:
    values = {item.order_id: item for item in state.orders}
    values[order.order_id] = order
    return replace(
        state, orders=tuple(sorted(values.values(), key=lambda item: item.order_id))
    )


def _event(
    event_type: str,
    event_time_ns: int,
    data: Mapping[str, object],
    state: PaperState,
) -> JournalMutation:
    return mutation(event_type, event_time_ns, data, state_to_mapping(state))


def _pending_order(state: PaperState, intent: PaperIntent) -> PaperOrder:
    quantity = Decimal(intent.quantity)
    fee_bps = Decimal(state.binding.fee_rate_bps)
    reserve_cash = (
        quantity * (Decimal(1) + fee_bps / Decimal(10_000))
        if intent.side == "BUY"
        else Decimal(0)
    )
    return PaperOrder(
        _order_id(intent.intent_id), intent.intent_id, intent.market_id,
        intent.asset_id, intent.side, intent.order_style, intent.quantity,
        intent.reference_price, "0", "0", "0", "PENDING_RISK",
        intent.decision_time_ns,
        intent.decision_time_ns + state.binding.latency_ns,
        (intent.decision_time_ns + state.binding.latency_ns + intent.ttl_ns)
        if intent.ttl_ns is not None else None,
        decimal_text(reserve_cash), intent.quantity if intent.side == "SELL" else "0",
        None, None,
    )


def _risk_decision(
    state: PaperState, intent: PaperIntent, order: PaperOrder
) -> PaperRiskDecision:
    marks = valid_marks(state)
    current_book = next(
        (book for book in state.books if book.asset_id == intent.asset_id), None
    )
    if current_book is None or current_book.market_id != intent.market_id:
        marks.pop(intent.asset_id, None)
    return evaluate_risk(
        intent=intent,
        limits=state.limits,
        account=state.account,
        orders=tuple(item for item in state.orders if item.order_id != order.order_id),
        marks=marks,
        control_state=state.control_state,
        reconciliation_blocked=False,
        resolution_pending=set(state.resolution_pending),
        last_market_receive_ns=dict(state.mark_times).get(intent.asset_id),
        decided_time_ns=intent.decision_time_ns,
        conservative_buy_reserve=order.reserved_cash if intent.side == "BUY" else None,
    )


def _record_fill(state: PaperState, fill: PaperFill) -> PaperState:
    order = next(
        (item for item in state.orders if item.order_id == fill.order_id), None
    )
    if order is None or order.status not in _ACTIVE:
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    quantity = Decimal(fill.quantity)
    prior_remaining = Decimal(order.quantity) - Decimal(order.filled_quantity)
    if quantity > prior_remaining:
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    new_filled = Decimal(order.filled_quantity) + quantity
    new_notional = Decimal(order.fill_notional) + quantity * Decimal(fill.price)
    remaining_ratio = (Decimal(order.quantity) - new_filled) / prior_remaining
    new_reserved_cash = (
        Decimal(order.reserved_cash) * remaining_ratio
        if order.side == "BUY"
        else Decimal(0)
    )
    new_reserved_quantity = (
        Decimal(order.reserved_quantity) - quantity
        if order.side == "SELL"
        else Decimal(0)
    )
    updated = replace(
        order,
        filled_quantity=decimal_text(new_filled),
        fill_notional=decimal_text(new_notional),
        fee_paid=decimal_text(Decimal(order.fee_paid) + Decimal(fill.fee)),
        status=("FILLED" if new_filled == Decimal(order.quantity) else "PARTIALLY_FILLED"),
        reserved_cash=decimal_text(new_reserved_cash),
        reserved_quantity=decimal_text(new_reserved_quantity),
    )
    account = apply_fill(state.account, order, updated, fill)
    return replace(
        _with_order(state, updated),
        account=account,
        fills=state.fills + (fill,),
    )


def _replay_market_event(state: PaperState, event: PaperMarketEvent) -> PaperState:
    validate_market_event(event)
    if state.last_market_receive_ns is not None and event.receive_time_ns < state.last_market_receive_ns:
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    marks = dict(state.marks)
    mark_times = dict(state.mark_times)
    books = {item.asset_id: item for item in state.books}
    gaps = set(state.gapped_assets)
    pending = set(state.resolution_pending)
    if event.kind == "BOOK":
        prior = books.get(event.asset_id)
        if prior is not None and prior.market_id != event.market_id:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        snapshot = BookSnapshot(
            event.market_id,
            event.asset_id,
            event.event_time_ns,
            event.receive_time_ns,
            event.lineage,
            event.bids,
            event.asks,
        )
        books[event.asset_id] = snapshot
        if event.asset_id not in gaps:
            marks[event.asset_id] = decimal_text(_mid(snapshot))
            mark_times[event.asset_id] = event.receive_time_ns
    elif event.kind == "GAP_OPEN" and event.asset_id:
        gaps.add(event.asset_id)
        marks.pop(event.asset_id, None)
        mark_times.pop(event.asset_id, None)
    elif event.kind == "GAP_HEALED" and event.asset_id:
        gaps.discard(event.asset_id)
    elif event.kind == "RESOLUTION":
        if event.winner_asset_id is None:
            pending.add(event.market_id)
        else:
            pending.discard(event.market_id)
    return replace(
        state,
        marks=tuple(sorted(marks.items())),
        mark_times=tuple(sorted(mark_times.items())),
        books=tuple(sorted(books.values(), key=lambda item: item.asset_id)),
        gapped_assets=tuple(sorted(gaps)),
        resolution_pending=tuple(sorted(pending)),
        last_market_receive_ns=event.receive_time_ns,
    )


def _replay_mutation(state: PaperState, event: JournalEvent) -> PaperState:
    data = event.data
    if event.event_type == "MARKET_EVENT":
        return _replay_market_event(
            state, dataclass_from_mapping(PaperMarketEvent, data)
        )
    if event.event_type == "ORDER_PENDING_RISK":
        return _with_order(
            state, dataclass_from_mapping(PaperOrder, data["order"])
        )
    if event.event_type == "RISK_DECIDED":
        decision = dataclass_from_mapping(PaperRiskDecision, data)
        return replace(state, risk_decisions=state.risk_decisions + (decision,))
    if event.event_type in {"ORDER_REJECTED", "ORDER_OPENED"}:
        order = next(item for item in state.orders if item.order_id == data["order_id"])
        updated = replace(
            order,
            status="REJECTED" if event.event_type == "ORDER_REJECTED" else "OPEN",
            risk_decision_id=data["risk_decision_id"],
            reserved_cash="0" if event.event_type == "ORDER_REJECTED" else order.reserved_cash,
            reserved_quantity="0" if event.event_type == "ORDER_REJECTED" else order.reserved_quantity,
        )
        result = _with_order(state, updated)
        return result if event.event_type == "ORDER_REJECTED" else replace(
            result, account=reserve(state.account, updated)
        )
    if event.event_type in {"ORDER_CANCELLED", "ORDER_EXPIRED"}:
        order = next(item for item in state.orders if item.order_id == data["order_id"])
        result = _with_order(
            state,
            replace(
                order,
                status="CANCELLED" if event.event_type == "ORDER_CANCELLED" else "EXPIRED",
                reserved_cash="0",
                reserved_quantity="0",
            ),
        )
        return replace(result, account=release(state.account, order))
    if event.event_type == "ORDER_ARRIVAL_REFERENCE":
        order = next(item for item in state.orders if item.order_id == data["order_id"])
        return _with_order(state, replace(order, arrival_mid=data["arrival_mid"]))
    if event.event_type == "ORDER_MARKOUT_REFERENCE":
        order = next(item for item in state.orders if item.order_id == data["order_id"])
        return _with_order(
            state,
            replace(
                order,
                markout_mid=data["markout_mid"],
                markout_lineage=data["market_truth_lineage"],
                markout_observed_receive_time_ns=event.event_time_ns,
                markout_status=data["status"],
            ),
        )
    if event.event_type in {"ORDER_QUEUE_INITIALIZED", "ORDER_QUEUE_UPDATED"}:
        order = next(item for item in state.orders if item.order_id == data["order_id"])
        return _with_order(
            state,
            replace(
                order,
                queue_ahead=data["queue_ahead"],
                passive_fill_eligible=data.get(
                    "passive_fill_eligible", order.passive_fill_eligible
                ),
            ),
        )
    if event.event_type == "PAPER_FILL":
        return _record_fill(state, dataclass_from_mapping(PaperFill, data))
    if event.event_type == "FILL_MARKOUT":
        markout = dataclass_from_mapping(PaperMarkout, data)
        return replace(state, markouts=state.markouts + (markout,))
    if event.event_type == "POSITION_SETTLED":
        return replace(
            state,
            account=settle_position(
                state.account,
                data["asset_id"],
                Decimal(data["payoff"]),
                event.event_time_ns,
            ),
        )
    if event.event_type == "CONTROL_CHANGED":
        return replace(state, control_state=data["to"])
    raise PaperTradingError("RECONCILIATION_BLOCKED")


def _replay_journal(events: tuple[JournalEvent, ...]) -> PaperState:
    if not events or events[0].event_type != "SESSION_INITIALIZED":
        raise PaperTradingError("RECONCILIATION_BLOCKED")
    for event in events:
        if event.event_id != content_id(
            "paperevent:sha256:",
            {
                "event_type": event.event_type,
                "event_time_ns": event.event_time_ns,
                "data": event.data,
            },
        ):
            raise PaperTradingError("RECONCILIATION_BLOCKED")
    state = state_from_mapping(events[0].state_after)
    pending_intents: dict[str, PaperIntent] = {}
    for event in events[1:]:
        if event.event_type == "ORDER_PENDING_RISK":
            intent = dataclass_from_mapping(PaperIntent, event.data["intent"])
            validate_paper_intent(intent, state.binding)
            recorded_order = dataclass_from_mapping(PaperOrder, event.data["order"])
            if recorded_order != _pending_order(state, intent):
                raise PaperTradingError("RECONCILIATION_BLOCKED")
            pending_intents[intent.intent_id] = intent
        if event.event_type == "RISK_DECIDED":
            recorded_decision = dataclass_from_mapping(PaperRiskDecision, event.data)
            intent = pending_intents.get(recorded_decision.intent_id)
            if intent is None:
                raise PaperTradingError("RECONCILIATION_BLOCKED")
            order = next(
                item for item in state.orders if item.intent_id == intent.intent_id
            )
            if recorded_decision != _risk_decision(state, intent, order):
                raise PaperTradingError("RECONCILIATION_BLOCKED")
        expected = _replay_mutation(state, event)
        recorded = state_from_mapping(event.state_after)
        if expected != recorded:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        state = recorded
    return state


def _order_id(intent_id: str) -> str:
    return content_id("paperorder:sha256:", {"intent_id": intent_id})


def _mid(book: BookSnapshot) -> Decimal:
    return (Decimal(book.bids[0][0]) + Decimal(book.asks[0][0])) / 2


def _signed(side: str, later: Decimal, earlier: Decimal) -> Decimal:
    return later - earlier if side == "BUY" else earlier - later


def valid_marks(state: PaperState) -> dict[str, str]:
    if state.last_market_receive_ns is None:
        return {}
    times = dict(state.mark_times)
    gapped = set(state.gapped_assets)
    return {
        asset: mark
        for asset, mark in state.marks
        if asset not in gapped
        and asset in times
        and 0 <= state.last_market_receive_ns - times[asset]
        <= state.binding.max_data_age_ns
    }


class PaperEngine:
    def __init__(
        self, store: PaperStore, state: PaperState, expected_head: StoreHead
    ) -> None:
        self.store = store
        self.state = state
        self.expected_head = expected_head

    @classmethod
    def create(
        cls,
        store: PaperStore,
        binding: PaperStrategyBinding,
        limits: PaperRiskLimits,
        *,
        assessment: ExecutableEdgeAssessment,
        cost_model: ExecutionCostModel,
        session_label: str,
        created_time_ns: int,
    ) -> "PaperEngine":
        expected_binding = build_strategy_binding(
            assessment,
            cost_model,
            strategy_label=binding.strategy_label,
            created_time_ns=binding.created_time_ns,
        )
        if expected_binding != binding:
            raise PaperTradingError("WP172_BINDING_INVALID")
        validate_risk_limits(limits)
        if store.load_state() is not None:
            raise PaperTradingError("SESSION_ALREADY_EXISTS")
        session_id = content_id(
            "papersession:sha256:",
            {
                "binding_id": binding.binding_id,
                "limits": asdict(limits),
                "session_label": session_label,
                "created_time_ns": created_time_ns,
            },
        )
        state = PaperState(
            session_id,
            binding,
            limits,
            "RUNNING",
            new_account(limits.initial_cash),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            None,
        )
        event = _event(
            "SESSION_INITIALIZED",
            created_time_ns,
            {
                "session_id": session_id,
                "binding_id": binding.binding_id,
                "limits": asdict(limits),
                "simulated_paper_only": True,
            },
            state,
        )
        head = store.commit((event,), state_to_mapping(state), expected_head=None)
        return cls(store, state, head)

    @classmethod
    def create_research(
        cls,
        store: PaperStore,
        binding: ResearchPaperStrategyBinding,
        limits: PaperRiskLimits,
        *,
        session_label: str,
        created_time_ns: int,
    ) -> "PaperEngine":
        validate_research_strategy_binding(binding)
        validate_risk_limits(limits)
        if not isinstance(session_label, str) or not session_label:
            raise PaperTradingError("FIELD_VALUE_INVALID")
        if (
            not isinstance(created_time_ns, int)
            or isinstance(created_time_ns, bool)
            or created_time_ns < 0
        ):
            raise PaperTradingError("FIELD_VALUE_INVALID")
        if store.load_state() is not None:
            raise PaperTradingError("SESSION_ALREADY_EXISTS")
        session_id = content_id(
            "papersession:sha256:",
            {
                "binding_id": binding.binding_id,
                "binding_kind": binding.binding_kind,
                "limits": asdict(limits),
                "session_label": session_label,
                "created_time_ns": created_time_ns,
            },
        )
        state = PaperState(
            session_id,
            binding,
            limits,
            "RUNNING",
            new_account(limits.initial_cash),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            None,
        )
        event = _event(
            "SESSION_INITIALIZED",
            created_time_ns,
            {
                "session_id": session_id,
                "binding_id": binding.binding_id,
                "binding_kind": "RESEARCH_PAPER",
                "research_paper_only": True,
                "simulated_paper_only": True,
                "qualification_claim": False,
                "gate_c_eligible": False,
                "limits": asdict(limits),
            },
            state,
        )
        head = store.commit((event,), state_to_mapping(state), expected_head=None)
        return cls(store, state, head)

    @classmethod
    def open(cls, store: PaperStore) -> "PaperEngine":
        raw, events, head = store.recovery_snapshot()
        if raw is None:
            raise PaperTradingError("SESSION_NOT_INITIALIZED")
        if head is None:
            raise PaperTradingError("RECONCILIATION_BLOCKED")
        try:
            state = _replay_journal(events)
        except (IndexError, KeyError, StopIteration, TypeError, PaperTradingError):
            store.reconciliation_blocked = True
            try:
                state = replace(
                    state_from_mapping(raw), control_state="RECONCILIATION_BLOCKED"
                )
            except PaperTradingError:
                raise PaperTradingError("RECONCILIATION_BLOCKED") from None
            return cls(store, state, head)
        if store.reconciliation_blocked:
            state = replace(state, control_state="RECONCILIATION_BLOCKED")
        else:
            if state_to_mapping(state) != raw:
                store.reconciliation_blocked = True
                state = replace(state, control_state="RECONCILIATION_BLOCKED")
        return cls(store, state, head)

    def check_store_head(self) -> None:
        if self.store.current_head() != self.expected_head:
            self.state = replace(
                self.state, control_state="RECONCILIATION_BLOCKED"
            )
            raise PaperTradingError("STALE_PAPER_STATE")

    def _commit(self, events: Sequence[JournalMutation], state: PaperState) -> None:
        try:
            head = self.store.commit(
                events, state_to_mapping(state), expected_head=self.expected_head
            )
        except PaperTradingError as exc:
            if str(exc) == "STALE_PAPER_STATE":
                self.state = replace(
                    self.state, control_state="RECONCILIATION_BLOCKED"
                )
            raise
        self.expected_head = head
        self.state = state

    def _control(self, target: str, event_time_ns: int) -> None:
        current = self.state.control_state
        if target == "RUNNING" and current != "PAUSED":
            raise PaperTradingError("CONTROL_TRANSITION_INVALID")
        if target == "PAUSED" and current != "RUNNING":
            raise PaperTradingError("CONTROL_TRANSITION_INVALID")
        if current in {"KILLED", "RECONCILIATION_BLOCKED"}:
            raise PaperTradingError("CONTROL_TRANSITION_INVALID")
        state = replace(self.state, control_state=target)
        self._commit(
            (
                _event(
                    "CONTROL_CHANGED",
                    event_time_ns,
                    {
                        "from": current,
                        "to": target,
                    },
                    state,
                ),
            ),
            state,
        )

    def pause(self, event_time_ns: int) -> None:
        self._control("PAUSED", event_time_ns)

    def resume(self, event_time_ns: int) -> None:
        self._control("RUNNING", event_time_ns)

    def kill(self, event_time_ns: int) -> None:
        if self.state.control_state in {"KILLED", "RECONCILIATION_BLOCKED"}:
            raise PaperTradingError("CONTROL_TRANSITION_INVALID")
        state = self.state
        events: list[JournalMutation] = []
        for order in state.orders:
            if order.status in _ACTIVE:
                account = release(state.account, order)
                cancelled = replace(
                    order, status="CANCELLED", reserved_cash="0", reserved_quantity="0"
                )
                state = replace(_with_order(state, cancelled), account=account)
                events.append(
                    _event(
                        "ORDER_CANCELLED",
                        event_time_ns,
                        {
                            "order_id": order.order_id,
                            "reason": "SESSION_KILLED",
                        },
                        state,
                    )
                )
        state = replace(state, control_state="KILLED")
        events.append(
            _event(
                "CONTROL_CHANGED",
                event_time_ns,
                {
                    "from": self.state.control_state,
                    "to": "KILLED",
                },
                state,
            )
        )
        self._commit(events, state)

    def submit(self, intent: PaperIntent) -> PaperOrder:
        validate_paper_intent(intent, self.state.binding)
        for existing in self.state.orders:
            if existing.intent_id == intent.intent_id:
                return existing
        order = _pending_order(self.state, intent)
        state = _with_order(self.state, order)
        events = [
            _event(
                "ORDER_PENDING_RISK",
                intent.decision_time_ns,
                {
                    "order": asdict(order),
                    "intent": asdict(intent),
                },
                state,
            )
        ]
        decision = _risk_decision(state, intent, order)
        state = replace(state, risk_decisions=state.risk_decisions + (decision,))
        events.append(
            _event("RISK_DECIDED", intent.decision_time_ns, asdict(decision), state)
        )
        if decision.result == "DENY":
            order = replace(
                order,
                status="REJECTED",
                risk_decision_id=decision.decision_id,
                reserved_cash="0",
                reserved_quantity="0",
            )
            state = _with_order(state, order)
            events.append(
                _event(
                    "ORDER_REJECTED",
                    intent.decision_time_ns,
                    {
                        "order_id": order.order_id,
                        "risk_decision_id": decision.decision_id,
                    },
                    state,
                )
            )
        else:
            order = replace(order, status="OPEN", risk_decision_id=decision.decision_id)
            account = reserve(state.account, order)
            state = replace(_with_order(state, order), account=account)
            events.append(
                _event(
                    "ORDER_OPENED",
                    intent.decision_time_ns,
                    {
                        "order_id": order.order_id,
                        "risk_decision_id": decision.decision_id,
                    },
                    state,
                )
            )
        self._commit(events, state)
        if (
            order.status == "OPEN"
            and self.state.last_market_receive_ns is not None
            and order.arrival_time_ns <= self.state.last_market_receive_ns
        ):
            self.advance_time(self.state.last_market_receive_ns)
            return next(
                item for item in self.state.orders if item.order_id == order.order_id
            )
        return order

    def cancel(self, order_id: str, event_time_ns: int) -> PaperOrder:
        order = next(
            (item for item in self.state.orders if item.order_id == order_id), None
        )
        if order is None:
            raise PaperTradingError("ORDER_NOT_FOUND")
        if order.status not in _ACTIVE:
            raise PaperTradingError("ORDER_TERMINAL")
        account = release(self.state.account, order)
        order = replace(
            order, status="CANCELLED", reserved_cash="0", reserved_quantity="0"
        )
        state = replace(_with_order(self.state, order), account=account)
        self._commit(
            (
                _event(
                    "ORDER_CANCELLED",
                    event_time_ns,
                    {
                        "order_id": order_id,
                        "reason": "MANUAL_PAPER_CANCEL",
                    },
                    state,
                ),
            ),
            state,
        )
        return order

    def _expire(
        self, state: PaperState, order: PaperOrder, time_ns: int
    ) -> tuple[PaperState, JournalMutation]:
        account = release(state.account, order)
        expired = replace(
            order, status="EXPIRED", reserved_cash="0", reserved_quantity="0"
        )
        state = replace(_with_order(state, expired), account=account)
        return state, _event(
            "ORDER_EXPIRED", time_ns, {"order_id": order.order_id}, state
        )

    def _apply_one_fill(
        self,
        state: PaperState,
        order: PaperOrder,
        quantity: Decimal,
        price: Decimal,
        market_event: PaperMarketEvent,
        arrival_book: BookSnapshot,
    ) -> tuple[PaperState, list[JournalMutation]]:
        if quantity <= 0:
            return state, []
        prior_remaining = Decimal(order.quantity) - Decimal(order.filled_quantity)
        quantity = min(quantity, prior_remaining)
        effective_bps = Decimal(state.binding.fee_rate_bps)
        if order.order_style == "PASSIVE_MAKER":
            effective_bps -= Decimal(state.binding.maker_rebate_bps)
        fee = quantity * price * effective_bps / Decimal(10_000)
        if order.order_style == "AGGRESSIVE_TAKER":
            arrival_mid = _mid(arrival_book)
            levels = arrival_book.asks if order.side == "BUY" else arrival_book.bids
            best = Decimal(levels[0][0])
            spread = abs(best - arrival_mid) * quantity
            latency = _signed(
                order.side,
                arrival_mid,
                Decimal(order.reference_price),
            ) * quantity
            slippage = _signed(order.side, price, best) * quantity
        else:
            spread = latency = slippage = Decimal(0)
        fill_sequence = 1 + sum(item.order_id == order.order_id for item in state.fills)
        fill_data = {
            "order_id": order.order_id,
            "fill_sequence": fill_sequence,
            "quantity": decimal_text(quantity),
            "price": decimal_text(price),
            "fee": decimal_text(fee),
            "spread_cost": decimal_text(spread),
            "depth_slippage_cost": decimal_text(slippage),
            "latency_cost": decimal_text(latency),
            "receive_time_ns": market_event.receive_time_ns,
            "market_truth_lineage": market_event.lineage,
        }
        fill = PaperFill(
            content_id("paperfill:sha256:", fill_data),
            order.order_id,
            fill_sequence,
            order.market_id,
            order.asset_id,
            order.side,
            decimal_text(quantity),
            decimal_text(price),
            decimal_text(fee),
            decimal_text(spread),
            decimal_text(slippage),
            decimal_text(latency),
            market_event.event_time_ns,
            market_event.receive_time_ns,
            market_event.lineage,
        )
        state = _record_fill(state, fill)
        return state, [
            _event("PAPER_FILL", market_event.receive_time_ns, asdict(fill), state)
        ]

    def _finalize_markouts(
        self, state: PaperState
    ) -> tuple[PaperState, list[JournalMutation]]:
        existing = {item.fill_id for item in state.markouts}
        orders = {item.order_id: item for item in state.orders}
        added: list[PaperMarkout] = []
        events: list[JournalMutation] = []
        for fill in state.fills:
            if fill.fill_id in existing:
                continue
            order = orders[fill.order_id]
            target = order.arrival_time_ns + state.binding.markout_horizon_ns
            if order.markout_status == "PENDING" or order.arrival_mid is None:
                continue
            if order.markout_status == "AVAILABLE":
                assert order.markout_mid is not None
                adverse = max(
                    Decimal(0),
                    -_signed(
                        fill.side,
                        Decimal(order.markout_mid),
                        Decimal(order.arrival_mid),
                    ),
                ) * Decimal(fill.quantity)
                cost = decimal_text(adverse)
                lineage = order.markout_lineage
                status = "AVAILABLE"
            else:
                cost = None
                lineage = order.markout_lineage
                status = "MARKET_DATA_UNAVAILABLE"
            observed = order.markout_observed_receive_time_ns
            assert observed is not None
            data = {
                "fill_id": fill.fill_id,
                "target_time_ns": target,
                "observed_receive_time_ns": observed,
                "adverse_selection_cost": cost,
                "market_truth_lineage": lineage,
                "status": status,
            }
            markout = PaperMarkout(
                content_id("papermarkout:sha256:", data),
                fill.fill_id,
                target,
                observed,
                cost,
                lineage,
                status,
            )
            added.append(markout)
            candidate = replace(state, markouts=state.markouts + tuple(added))
            events.append(
                _event("FILL_MARKOUT", observed, asdict(markout), candidate)
            )
        if added:
            state = replace(state, markouts=state.markouts + tuple(added))
        return state, events

    def process_market_event(self, market_event: PaperMarketEvent) -> None:
        validate_market_event(market_event)
        if (
            self.state.last_market_receive_ns is not None
            and market_event.receive_time_ns < self.state.last_market_receive_ns
        ):
            raise PaperTradingError("MARKET_EVENT_ORDER_INVALID")
        existing_book = next(
            (book for book in self.state.books if book.asset_id == market_event.asset_id),
            None,
        )
        if (
            market_event.kind == "BOOK"
            and existing_book is not None
            and existing_book.market_id != market_event.market_id
        ):
            raise PaperTradingError("MARKET_EVENT_INVALID")
        state = replace(self.state, last_market_receive_ns=market_event.receive_time_ns)
        marks = dict(state.marks)
        mark_times = dict(state.mark_times)
        prior_books = {item.asset_id: item for item in state.books}
        books = dict(prior_books)
        gaps = set(state.gapped_assets)
        pending = set(state.resolution_pending)
        if market_event.kind == "BOOK":
            bid = Decimal(market_event.bids[0][0])
            ask = Decimal(market_event.asks[0][0])
            snapshot = BookSnapshot(
                market_event.market_id,
                market_event.asset_id,
                market_event.event_time_ns,
                market_event.receive_time_ns,
                market_event.lineage,
                market_event.bids,
                market_event.asks,
            )
            books[market_event.asset_id] = snapshot
            if market_event.asset_id not in gaps:
                marks[market_event.asset_id] = decimal_text((bid + ask) / 2)
                mark_times[market_event.asset_id] = market_event.receive_time_ns
        elif market_event.kind == "GAP_OPEN" and market_event.asset_id:
            gaps.add(market_event.asset_id)
            marks.pop(market_event.asset_id, None)
            mark_times.pop(market_event.asset_id, None)
        elif market_event.kind == "GAP_HEALED" and market_event.asset_id:
            gaps.discard(market_event.asset_id)
        elif market_event.kind == "RESOLUTION":
            if market_event.winner_asset_id is None:
                pending.add(market_event.market_id)
            else:
                pending.discard(market_event.market_id)
        state = replace(
            state,
            marks=tuple(sorted(marks.items())),
            mark_times=tuple(sorted(mark_times.items())),
            books=tuple(sorted(books.values(), key=lambda item: item.asset_id)),
            gapped_assets=tuple(sorted(gaps)),
            resolution_pending=tuple(sorted(pending)),
        )
        events: list[JournalMutation] = [
            _event(
                "MARKET_EVENT",
                market_event.receive_time_ns,
                asdict(market_event),
                state,
            )
        ]
        for order in tuple(state.orders):
            target = order.arrival_time_ns + state.binding.markout_horizon_ns
            if order.markout_status != "PENDING" or market_event.receive_time_ns < target:
                continue
            reference = books.get(order.asset_id)
            if reference is not None and reference.receive_time_ns > target:
                reference = prior_books.get(order.asset_id)
            available = (
                reference is not None
                and reference.receive_time_ns <= target
                and target - reference.receive_time_ns
                <= state.binding.max_data_age_ns
                and order.asset_id not in gaps
            )
            updated = replace(
                order,
                markout_mid=decimal_text(_mid(reference)) if available else None,
                markout_lineage=reference.lineage if reference is not None else None,
                markout_observed_receive_time_ns=market_event.receive_time_ns,
                markout_status="AVAILABLE" if available else "MARKET_DATA_UNAVAILABLE",
            )
            state = _with_order(state, updated)
            events.append(
                _event(
                    "ORDER_MARKOUT_REFERENCE",
                    market_event.receive_time_ns,
                    {
                        "order_id": order.order_id,
                        "target_time_ns": target,
                        "status": updated.markout_status,
                        "markout_mid": updated.markout_mid,
                        "market_truth_lineage": updated.markout_lineage,
                    },
                    state,
                )
            )
        if market_event.kind == "RESOLUTION":
            for order in tuple(state.orders):
                if (
                    order.market_id == market_event.market_id
                    and order.status in _ACTIVE
                ):
                    account = release(state.account, order)
                    order = replace(
                        order,
                        status="CANCELLED",
                        reserved_cash="0",
                        reserved_quantity="0",
                    )
                    state = replace(_with_order(state, order), account=account)
                    events.append(
                        _event(
                            "ORDER_CANCELLED",
                            market_event.receive_time_ns,
                            {
                                "order_id": order.order_id,
                                "reason": "MARKET_RESOLUTION",
                            },
                            state,
                        )
                    )
            if market_event.winner_asset_id is not None:
                for position in tuple(state.account.positions):
                    if position.market_id == market_event.market_id:
                        payoff = (
                            Decimal(1)
                            if position.asset_id == market_event.winner_asset_id
                            else Decimal(0)
                        )
                        state = replace(
                            state,
                            account=settle_position(
                                state.account,
                                position.asset_id,
                                payoff,
                                market_event.receive_time_ns,
                            ),
                        )
                        events.append(
                            _event(
                                "POSITION_SETTLED",
                                market_event.receive_time_ns,
                                {
                                    "market_id": market_event.market_id,
                                    "asset_id": position.asset_id,
                                    "payoff": decimal_text(payoff),
                                },
                                state,
                            )
                        )
            self._commit(events, state)
            return

        for order in tuple(state.orders):
            if (
                order.status not in _ACTIVE
                or order.asset_id != market_event.asset_id
                or order.market_id != market_event.market_id
            ):
                continue
            order = next(item for item in state.orders if item.order_id == order.order_id)
            if (
                order.expiry_time_ns is not None
                and market_event.receive_time_ns > order.expiry_time_ns
            ):
                state, expired_event = self._expire(
                    state, order, market_event.receive_time_ns
                )
                events.append(expired_event)
                continue
            if (
                order.asset_id in gaps
                or market_event.receive_time_ns < order.arrival_time_ns
            ):
                continue
            arrival_book = books.get(order.asset_id)
            if (
                arrival_book is not None
                and arrival_book.receive_time_ns > order.arrival_time_ns
            ):
                arrival_book = prior_books.get(order.asset_id)
            if (
                arrival_book is None
                or arrival_book.market_id != order.market_id
                or arrival_book.receive_time_ns > order.arrival_time_ns
                or order.arrival_time_ns - arrival_book.receive_time_ns
                > state.binding.max_data_age_ns
            ):
                account = release(state.account, order)
                closed = replace(
                    order,
                    status="CANCELLED",
                    reserved_cash="0",
                    reserved_quantity="0",
                )
                state = replace(_with_order(state, closed), account=account)
                events.append(
                    _event(
                        "ORDER_CANCELLED",
                        market_event.receive_time_ns,
                        {
                            "order_id": order.order_id,
                            "reason": "MARKET_STATE_UNAVAILABLE",
                        },
                        state,
                    )
                )
                continue
            if order.arrival_mid is None:
                order = replace(order, arrival_mid=decimal_text(_mid(arrival_book)))
                state = _with_order(state, order)
                events.append(
                    _event(
                        "ORDER_ARRIVAL_REFERENCE",
                        order.arrival_time_ns,
                        {
                            "order_id": order.order_id,
                            "market_truth_lineage": arrival_book.lineage,
                            "arrival_mid": order.arrival_mid,
                        },
                        state,
                    )
                )
            fill_event = PaperMarketEvent(
                "BOOK",
                arrival_book.market_id,
                arrival_book.asset_id,
                arrival_book.event_time_ns,
                order.arrival_time_ns,
                arrival_book.lineage,
                arrival_book.bids,
                arrival_book.asks,
            )
            if order.order_style == "AGGRESSIVE_TAKER":
                remaining = Decimal(order.quantity) - Decimal(order.filled_quantity)
                levels = arrival_book.asks if order.side == "BUY" else arrival_book.bids
                filled = Decimal(0)
                notional = Decimal(0)
                for price_text, size_text in levels:
                    take = min(remaining - filled, Decimal(size_text))
                    if take > 0:
                        filled += take
                        notional += take * Decimal(price_text)
                    if filled == remaining:
                        break
                average = notional / filled if filled else Decimal(0)
                state, fill_events = self._apply_one_fill(
                    state, order, filled, average, fill_event, arrival_book
                )
                events.extend(fill_events)
                current = next(
                    item for item in state.orders if item.order_id == order.order_id
                )
                if current.status != "FILLED":
                    account = release(state.account, current)
                    current = replace(
                        current,
                        status="CANCELLED",
                        reserved_cash="0",
                        reserved_quantity="0",
                    )
                    state = replace(_with_order(state, current), account=account)
                    events.append(
                        _event(
                            "ORDER_CANCELLED",
                            market_event.receive_time_ns,
                            {
                                "order_id": current.order_id,
                                "reason": "AGGRESSIVE_DEPTH_EXHAUSTED",
                            },
                            state,
                        )
                    )
            elif order.order_style == "PASSIVE_MAKER":
                current = next(
                    item for item in state.orders if item.order_id == order.order_id
                )
                if current.queue_ahead is None:
                    own = (
                        arrival_book.bids if order.side == "BUY" else arrival_book.asks
                    )
                    visible = sum(
                        Decimal(size)
                        for price, size in own
                        if Decimal(price) == Decimal(order.reference_price)
                    )
                    queue = visible * Decimal(state.binding.queue_ahead_multiplier)
                    current = replace(
                        current,
                        queue_ahead=decimal_text(queue),
                        passive_fill_eligible=visible > 0,
                    )
                    state = _with_order(state, current)
                    events.append(
                        _event(
                            "ORDER_QUEUE_INITIALIZED",
                            order.arrival_time_ns,
                            {
                                "order_id": current.order_id,
                                "queue_ahead": current.queue_ahead,
                                "passive_fill_eligible": current.passive_fill_eligible,
                            },
                            state,
                        )
                    )
                current = next(
                    item for item in state.orders if item.order_id == order.order_id
                )
                if (
                    current.queue_ahead is not None
                    and current.passive_fill_eligible
                    and market_event.kind == "TRADE"
                ):
                    trade_price = Decimal(market_event.price or "0")
                    eligible = (
                        order.side == "BUY"
                        and market_event.side == "SELL"
                        and trade_price <= Decimal(order.reference_price)
                    ) or (
                        order.side == "SELL"
                        and market_event.side == "BUY"
                        and trade_price >= Decimal(order.reference_price)
                    )
                    if eligible:
                        flow = Decimal(market_event.size or "0")
                        queue = Decimal(current.queue_ahead)
                        consumed = min(queue, flow)
                        fill_quantity = max(Decimal(0), flow - consumed)
                        current = replace(
                            current, queue_ahead=decimal_text(queue - consumed)
                        )
                        state = _with_order(state, current)
                        events.append(
                            _event(
                                "ORDER_QUEUE_UPDATED",
                                market_event.receive_time_ns,
                                {
                                    "order_id": current.order_id,
                                    "queue_ahead": current.queue_ahead,
                                },
                                state,
                            )
                        )
                        state, fill_events = self._apply_one_fill(
                            state,
                            current,
                            fill_quantity,
                            Decimal(order.reference_price),
                            market_event,
                            arrival_book,
                        )
                        events.extend(fill_events)
        state, markout_events = self._finalize_markouts(state)
        events.extend(markout_events)
        self._commit(events, state)

    def advance_time(self, time_ns: int) -> None:
        if not isinstance(time_ns, int) or isinstance(time_ns, bool) or time_ns < 0:
            raise PaperTradingError("FIELD_VALUE_INVALID")
        state = self.state
        events: list[JournalMutation] = []
        for order in tuple(state.orders):
            order = next(item for item in state.orders if item.order_id == order.order_id)
            if (
                order.status in _ACTIVE
                and order.order_style == "AGGRESSIVE_TAKER"
                and order.arrival_time_ns <= time_ns
            ):
                book = {item.asset_id: item for item in state.books}.get(order.asset_id)
                if (
                    book is None
                    or book.receive_time_ns > order.arrival_time_ns
                    or order.arrival_time_ns - book.receive_time_ns
                    > state.binding.max_data_age_ns
                    or order.asset_id in state.gapped_assets
                ):
                    account = release(state.account, order)
                    cancelled = replace(
                        order,
                        status="CANCELLED",
                        reserved_cash="0",
                        reserved_quantity="0",
                    )
                    state = replace(
                        _with_order(state, cancelled), account=account
                    )
                    events.append(
                        _event(
                            "ORDER_CANCELLED",
                            order.arrival_time_ns,
                            {
                                "order_id": order.order_id,
                                "reason": "MARKET_STATE_UNAVAILABLE",
                            },
                            state,
                        )
                    )
                    continue
                if order.arrival_mid is None:
                    order = replace(order, arrival_mid=decimal_text(_mid(book)))
                    state = _with_order(state, order)
                    events.append(
                        _event(
                            "ORDER_ARRIVAL_REFERENCE",
                            order.arrival_time_ns,
                            {
                                "order_id": order.order_id,
                                "market_truth_lineage": book.lineage,
                                "arrival_mid": order.arrival_mid,
                            },
                            state,
                        )
                    )
                target = order.arrival_time_ns + state.binding.markout_horizon_ns
                if order.markout_status == "PENDING" and target <= time_ns:
                    available = (
                        book.receive_time_ns <= target
                        and target - book.receive_time_ns
                        <= state.binding.max_data_age_ns
                    )
                    order = replace(
                        order,
                        markout_mid=decimal_text(_mid(book)) if available else None,
                        markout_lineage=book.lineage,
                        markout_observed_receive_time_ns=time_ns,
                        markout_status=(
                            "AVAILABLE" if available else "MARKET_DATA_UNAVAILABLE"
                        ),
                    )
                    state = _with_order(state, order)
                    events.append(
                        _event(
                            "ORDER_MARKOUT_REFERENCE",
                            time_ns,
                            {
                                "order_id": order.order_id,
                                "target_time_ns": target,
                                "status": order.markout_status,
                                "markout_mid": order.markout_mid,
                                "market_truth_lineage": order.markout_lineage,
                            },
                            state,
                        )
                    )
                levels = book.asks if order.side == "BUY" else book.bids
                remaining = Decimal(order.quantity) - Decimal(order.filled_quantity)
                filled = notional = Decimal(0)
                for price_text, size_text in levels:
                    take = min(remaining - filled, Decimal(size_text))
                    if take > 0:
                        filled += take
                        notional += take * Decimal(price_text)
                    if filled == remaining:
                        break
                average = notional / filled if filled else Decimal(0)
                fill_event = PaperMarketEvent(
                    "BOOK",
                    book.market_id,
                    book.asset_id,
                    book.event_time_ns,
                    order.arrival_time_ns,
                    book.lineage,
                    book.bids,
                    book.asks,
                )
                state, fill_events = self._apply_one_fill(
                    state, order, filled, average, fill_event, book
                )
                events.extend(fill_events)
                current = next(
                    item for item in state.orders if item.order_id == order.order_id
                )
                if current.status != "FILLED":
                    account = release(state.account, current)
                    current = replace(
                        current,
                        status="CANCELLED",
                        reserved_cash="0",
                        reserved_quantity="0",
                    )
                    state = replace(
                        _with_order(state, current), account=account
                    )
                    events.append(
                        _event(
                            "ORDER_CANCELLED",
                            order.arrival_time_ns,
                            {
                                "order_id": current.order_id,
                                "reason": "AGGRESSIVE_DEPTH_EXHAUSTED",
                            },
                            state,
                        )
                    )
                continue
            if (
                order.status in _ACTIVE
                and order.expiry_time_ns is not None
                and time_ns > order.expiry_time_ns
            ):
                state, item = self._expire(state, order, time_ns)
                events.append(item)
        state, markout_events = self._finalize_markouts(state)
        events.extend(markout_events)
        if events:
            self._commit(events, state)

    def summary(self) -> dict[str, object]:
        marks = valid_marks(self.state)
        marked = mark_account(self.state.account, marks)
        return {
            "session_id": self.state.session_id,
            "control_state": self.state.control_state,
            "reconciliation_state": "BLOCKED"
            if self.store.reconciliation_blocked
            else "OK",
            "cash": self.state.account.cash,
            "free_cash": decimal_text(
                Decimal(self.state.account.cash)
                - Decimal(self.state.account.reserved_cash)
            ),
            "reserved_cash": self.state.account.reserved_cash,
            "equity": marked["equity"],
            "realized_pnl": self.state.account.realized_pnl,
            "unrealized_pnl": marked["unrealized_pnl"],
            "open_order_count": sum(
                order.status in _ACTIVE for order in self.state.orders
            ),
            "fill_count": len(self.state.fills),
            "markout_count": len(self.state.markouts),
            "last_market_receive_ns": self.state.last_market_receive_ns,
            "binding_kind": (
                "RESEARCH_PAPER"
                if type(self.state.binding) is ResearchPaperStrategyBinding
                else "QUALIFIED_PAPER"
            ),
            "research_paper_only": type(self.state.binding) is ResearchPaperStrategyBinding,
            "simulated_paper_only": True,
        }
