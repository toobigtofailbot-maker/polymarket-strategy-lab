"""Immutable deterministic contracts for the WP173 simulated-paper boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from collections.abc import Mapping, Sequence

from src.research_runtime.executable_edge import (
    ExecutableEdgeAssessment,
    ExecutionCostModel,
    validate_assessment,
    validate_execution_cost_model,
)


SCHEMA_VERSION = "1.0.0"
PAPER_APPLICATION_ID = 1_347_242_301
PAPER_USER_VERSION = 1
ORDER_STATES = (
    "PENDING_RISK",
    "REJECTED",
    "OPEN",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELLED",
    "EXPIRED",
)
CONTROL_STATES = ("RUNNING", "PAUSED", "KILLED", "RECONCILIATION_BLOCKED")
ORDER_STYLES = ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")
SIDES = ("BUY", "SELL")
RISK_RESULTS = ("ALLOW", "DENY")
RISK_REASON_CODES = (
    "RECONCILIATION_BLOCKED",
    "CONTROL_NOT_RUNNING",
    "RESOLUTION_PENDING",
    "MARKET_DATA_UNAVAILABLE",
    "MARKET_DATA_STALE",
    "MAX_OPEN_ORDERS",
    "MAX_SINGLE_ORDER_NOTIONAL",
    "INSUFFICIENT_FREE_CASH",
    "MINIMUM_FREE_CASH_RESERVE",
    "INSUFFICIENT_FREE_POSITION",
    "MAX_POSITION_QUANTITY",
    "MAX_PER_MARKET_GROSS_EXPOSURE",
    "MAX_TOTAL_GROSS_EXPOSURE",
    "MAX_SESSION_DRAWDOWN",
    "MAX_UTC_DAY_LOSS",
)

_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*:sha256:[0-9a-f]{64}$")
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,127}$")


class PaperTradingError(ValueError):
    """Closed paper failure; messages are stable codes and never echo caller input."""


def canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise PaperTradingError("FIELD_VALUE_INVALID") from None


def content_id(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def decimal_value(value: object, *, nonnegative: bool = False) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise PaperTradingError("FIELD_VALUE_INVALID")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise PaperTradingError("FIELD_VALUE_INVALID") from None
    if not parsed.is_finite() or (nonnegative and parsed < 0):
        raise PaperTradingError("FIELD_VALUE_INVALID")
    return parsed


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise PaperTradingError("FIELD_VALUE_INVALID")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _text(value: object, *, label: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise PaperTradingError("FIELD_VALUE_INVALID")
    if label and _LABEL_RE.fullmatch(value) is None:
        raise PaperTradingError("FIELD_VALUE_INVALID")
    return value


def _time(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PaperTradingError("FIELD_VALUE_INVALID")
    return value


@dataclass(frozen=True)
class PaperStrategyBinding:
    schema_version: str
    binding_id: str
    assessment_id: str
    cost_model_id: str
    decision_trace_id: str
    market_data_lineage_id: str
    experiment_id: str
    first_look_evidence_id: str
    strategy_label: str
    created_time_ns: int
    execution_mode: str
    fee_rate_bps: str
    maker_rebate_bps: str
    latency_ns: int
    order_ttl_ns: int | None
    queue_ahead_multiplier: str
    markout_horizon_ns: int
    max_data_age_ns: int
    simulated_paper_only: bool


@dataclass(frozen=True)
class ResearchPaperStrategyBinding:
    schema_version: str
    binding_id: str
    binding_kind: str
    candidate_id: str
    hypothesis_family_id: str | None
    research_episode_id: str | None
    strategy_spec_id: str
    strategy_version: str
    strategy_code_identity: str
    subject_refs: tuple[str, ...]
    scope_id: str
    allowed_market_ids: tuple[str, ...]
    market_data_lineage_id: str
    decision_time_start_ns: int
    decision_time_end_ns: int
    execution_mode: str
    fee_rate_bps: str
    maker_rebate_bps: str
    latency_ns: int
    order_ttl_ns: int | None
    queue_ahead_multiplier: str
    markout_horizon_ns: int
    max_data_age_ns: int
    reserved_evidence_policy: str
    reserved_evidence_refs: tuple[str, ...]
    admitted_scope_refs: tuple[str, ...]
    created_time_ns: int
    research_paper_only: bool
    simulated_paper_only: bool
    qualification_claim: bool
    executable_edge_claim: bool
    wp173_qualified_evaluation_eligible: bool
    gate_c_eligible: bool
    live_promotion_eligible: bool
    real_capital_usd: str


PaperBinding = PaperStrategyBinding | ResearchPaperStrategyBinding


def _binding_preimage(binding: PaperStrategyBinding) -> dict[str, object]:
    value = asdict(binding)
    value.pop("binding_id")
    value.pop("simulated_paper_only")
    return value


def build_strategy_binding(
    assessment: ExecutableEdgeAssessment,
    cost_model: ExecutionCostModel,
    *,
    strategy_label: str,
    created_time_ns: int,
) -> PaperStrategyBinding:
    try:
        validate_assessment(assessment)
        validate_execution_cost_model(cost_model)
    except Exception:
        raise PaperTradingError("WP172_BINDING_INVALID") from None
    if (
        assessment.status != "EXECUTABLE_EDGE_PASS"
        or not assessment.wp173_evaluation_eligible
        or assessment.cost_model_id != cost_model.cost_model_id
        or cost_model.fee_rate_bps is None
    ):
        raise PaperTradingError("WP172_BINDING_INVALID")
    _text(strategy_label, label=True)
    _time(created_time_ns)
    provisional = PaperStrategyBinding(
        SCHEMA_VERSION,
        "",
        assessment.assessment_id,
        cost_model.cost_model_id,
        assessment.decision_trace_id,
        assessment.market_data_lineage_id,
        assessment.experiment_id,
        assessment.first_look_evidence_id,
        strategy_label,
        created_time_ns,
        cost_model.execution_mode,
        cost_model.fee_rate_bps,
        cost_model.maker_rebate_bps,
        cost_model.latency_ns,
        cost_model.order_ttl_ns,
        cost_model.queue_ahead_multiplier,
        cost_model.markout_horizon_ns,
        cost_model.max_data_age_ns,
        True,
    )
    return replace(
        provisional,
        binding_id=content_id("paperbinding:sha256:", _binding_preimage(provisional)),
    )


def validate_strategy_binding(binding: object) -> None:
    if type(binding) is not PaperStrategyBinding:
        raise PaperTradingError("WP172_BINDING_INVALID")
    _text(binding.strategy_label, label=True)
    _time(binding.created_time_ns)
    for identity in (
        binding.binding_id,
        binding.assessment_id,
        binding.cost_model_id,
        binding.decision_trace_id,
        binding.market_data_lineage_id,
        binding.experiment_id,
        binding.first_look_evidence_id,
    ):
        if _ID_RE.fullmatch(identity) is None:
            raise PaperTradingError("WP172_BINDING_INVALID")
    if (
        binding.schema_version != SCHEMA_VERSION
        or binding.execution_mode not in ORDER_STYLES
        or binding.order_ttl_ns is not None
        and (not isinstance(binding.order_ttl_ns, int) or binding.order_ttl_ns <= 0)
        or binding.execution_mode == "PASSIVE_MAKER"
        and binding.order_ttl_ns is None
        or not isinstance(binding.latency_ns, int)
        or binding.latency_ns < 0
        or not isinstance(binding.max_data_age_ns, int)
        or binding.max_data_age_ns < 0
        or decimal_value(binding.fee_rate_bps, nonnegative=True) < 0
        or decimal_value(binding.maker_rebate_bps, nonnegative=True) < 0
        or decimal_value(binding.queue_ahead_multiplier, nonnegative=True) < 1
        or not isinstance(binding.markout_horizon_ns, int)
        or binding.markout_horizon_ns < 0
        or not binding.simulated_paper_only
        or binding.binding_id
        != content_id("paperbinding:sha256:", _binding_preimage(binding))
    ):
        raise PaperTradingError("WP172_BINDING_INVALID")


def _research_binding_preimage(
    binding: ResearchPaperStrategyBinding,
) -> dict[str, object]:
    value = asdict(binding)
    value.pop("binding_id")
    for key in (
        "research_paper_only",
        "simulated_paper_only",
        "qualification_claim",
        "executable_edge_claim",
        "wp173_qualified_evaluation_eligible",
        "gate_c_eligible",
        "live_promotion_eligible",
        "real_capital_usd",
    ):
        value.pop(key)
    return value


def _ordered_unique_text(values: object, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise PaperTradingError("RESEARCH_BINDING_INVALID")
    try:
        result = tuple(_text(value) for value in values)
    except PaperTradingError:
        raise PaperTradingError("RESEARCH_BINDING_INVALID") from None
    if (not allow_empty and not result) or len(result) != len(set(result)):
        raise PaperTradingError("RESEARCH_BINDING_INVALID")
    return tuple(sorted(result))


def build_research_strategy_binding(
    *,
    candidate_id: str,
    hypothesis_family_id: str | None,
    research_episode_id: str | None,
    strategy_spec_id: str,
    strategy_version: str,
    strategy_code_identity: str,
    subject_refs: Sequence[str],
    scope_id: str,
    allowed_market_ids: Sequence[str],
    market_data_lineage_id: str,
    decision_time_start_ns: int,
    decision_time_end_ns: int,
    execution_mode: str,
    fee_rate_bps: str,
    maker_rebate_bps: str,
    latency_ns: int,
    order_ttl_ns: int | None,
    queue_ahead_multiplier: str,
    markout_horizon_ns: int,
    max_data_age_ns: int,
    reserved_evidence_policy: str,
    reserved_evidence_refs: Sequence[str],
    admitted_scope_refs: Sequence[str],
    created_time_ns: int,
) -> ResearchPaperStrategyBinding:
    provisional = ResearchPaperStrategyBinding(
        SCHEMA_VERSION,
        "",
        "RESEARCH_PAPER",
        candidate_id,
        hypothesis_family_id,
        research_episode_id,
        strategy_spec_id,
        strategy_version,
        strategy_code_identity,
        tuple(subject_refs),
        scope_id,
        tuple(allowed_market_ids),
        market_data_lineage_id,
        decision_time_start_ns,
        decision_time_end_ns,
        execution_mode,
        fee_rate_bps,
        maker_rebate_bps,
        latency_ns,
        order_ttl_ns,
        queue_ahead_multiplier,
        markout_horizon_ns,
        max_data_age_ns,
        reserved_evidence_policy,
        tuple(reserved_evidence_refs),
        tuple(admitted_scope_refs),
        created_time_ns,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        "0",
    )
    provisional = replace(
        provisional,
        subject_refs=_ordered_unique_text(provisional.subject_refs),
        allowed_market_ids=_ordered_unique_text(provisional.allowed_market_ids),
        reserved_evidence_refs=_ordered_unique_text(
            provisional.reserved_evidence_refs, allow_empty=True
        ),
        admitted_scope_refs=_ordered_unique_text(
            provisional.admitted_scope_refs, allow_empty=True
        ),
    )
    provisional = replace(
        provisional,
        binding_id=content_id(
            "researchpaperbinding:sha256:", _research_binding_preimage(provisional)
        ),
    )
    validate_research_strategy_binding(provisional)
    return provisional


def validate_research_strategy_binding(binding: object) -> None:
    if type(binding) is not ResearchPaperStrategyBinding:
        raise PaperTradingError("RESEARCH_BINDING_INVALID")
    identities = (
        binding.candidate_id,
        binding.strategy_spec_id,
        binding.strategy_code_identity,
        binding.scope_id,
        binding.market_data_lineage_id,
    )
    if any(_ID_RE.fullmatch(identity) is None for identity in identities):
        raise PaperTradingError("RESEARCH_BINDING_INVALID")
    for optional in (binding.hypothesis_family_id, binding.research_episode_id):
        if optional is not None and _ID_RE.fullmatch(optional) is None:
            raise PaperTradingError("RESEARCH_BINDING_INVALID")
    _text(binding.strategy_version, label=True)
    subjects = _ordered_unique_text(binding.subject_refs)
    markets = _ordered_unique_text(binding.allowed_market_ids)
    reserved = _ordered_unique_text(binding.reserved_evidence_refs, allow_empty=True)
    admitted = _ordered_unique_text(binding.admitted_scope_refs, allow_empty=True)
    if any(_ID_RE.fullmatch(item) is None for item in reserved + admitted):
        raise PaperTradingError("RESEARCH_BINDING_INVALID")
    for value in (
        binding.created_time_ns,
        binding.decision_time_start_ns,
        binding.decision_time_end_ns,
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise PaperTradingError("RESEARCH_BINDING_INVALID")
    if (
        binding.schema_version != SCHEMA_VERSION
        or binding.binding_kind != "RESEARCH_PAPER"
        or binding.subject_refs != subjects
        or binding.allowed_market_ids != markets
        or binding.reserved_evidence_refs != reserved
        or binding.admitted_scope_refs != admitted
        or binding.reserved_evidence_policy != "NON_CONFIRMATORY_RESEARCH_PAPER"
        or bool(reserved)
        or bool(admitted)
        or binding.decision_time_start_ns >= binding.decision_time_end_ns
        or binding.execution_mode not in ORDER_STYLES
        or binding.order_ttl_ns is not None
        and (not isinstance(binding.order_ttl_ns, int) or binding.order_ttl_ns <= 0)
        or binding.execution_mode == "PASSIVE_MAKER" and binding.order_ttl_ns is None
        or not isinstance(binding.latency_ns, int)
        or isinstance(binding.latency_ns, bool)
        or binding.latency_ns < 0
        or not isinstance(binding.max_data_age_ns, int)
        or isinstance(binding.max_data_age_ns, bool)
        or binding.max_data_age_ns < 0
        or not isinstance(binding.markout_horizon_ns, int)
        or isinstance(binding.markout_horizon_ns, bool)
        or binding.markout_horizon_ns < 0
        or decimal_value(binding.fee_rate_bps, nonnegative=True) < 0
        or decimal_value(binding.maker_rebate_bps, nonnegative=True) < 0
        or decimal_value(binding.queue_ahead_multiplier, nonnegative=True) < 1
        or not binding.research_paper_only
        or not binding.simulated_paper_only
        or binding.qualification_claim
        or binding.executable_edge_claim
        or binding.wp173_qualified_evaluation_eligible
        or binding.gate_c_eligible
        or binding.live_promotion_eligible
        or binding.real_capital_usd != "0"
        or binding.binding_id
        != content_id(
            "researchpaperbinding:sha256:", _research_binding_preimage(binding)
        )
    ):
        raise PaperTradingError("RESEARCH_BINDING_INVALID")


def validate_paper_binding(binding: object) -> None:
    if type(binding) is PaperStrategyBinding:
        validate_strategy_binding(binding)
    elif type(binding) is ResearchPaperStrategyBinding:
        validate_research_strategy_binding(binding)
    else:
        raise PaperTradingError("BINDING_KIND_INVALID")


@dataclass(frozen=True)
class PaperIntent:
    schema_version: str
    intent_id: str
    binding_id: str
    market_id: str
    asset_id: str
    side: str
    quantity: str
    order_style: str
    reference_price: str
    decision_time_ns: int
    ttl_ns: int | None
    simulated_paper_only: bool


def _intent_preimage(intent: PaperIntent) -> dict[str, object]:
    value = asdict(intent)
    value.pop("intent_id")
    value.pop("simulated_paper_only")
    return value


def build_paper_intent(
    binding: PaperBinding,
    *,
    market_id: str,
    asset_id: str,
    side: str,
    quantity: str,
    order_style: str,
    reference_price: str,
    decision_time_ns: int,
) -> PaperIntent:
    validate_paper_binding(binding)
    _text(market_id)
    _text(asset_id)
    if side not in SIDES or order_style != binding.execution_mode:
        raise PaperTradingError("INTENT_INVALID")
    if decimal_value(quantity, nonnegative=True) <= 0:
        raise PaperTradingError("INTENT_INVALID")
    price = decimal_value(reference_price, nonnegative=True)
    if price > 1:
        raise PaperTradingError("INTENT_INVALID")
    _time(decision_time_ns)
    if type(binding) is ResearchPaperStrategyBinding and (
        market_id not in binding.allowed_market_ids
        or not binding.decision_time_start_ns
        <= decision_time_ns
        < binding.decision_time_end_ns
    ):
        raise PaperTradingError("INTENT_INVALID")
    provisional = PaperIntent(
        SCHEMA_VERSION,
        "",
        binding.binding_id,
        market_id,
        asset_id,
        side,
        quantity,
        order_style,
        reference_price,
        decision_time_ns,
        binding.order_ttl_ns if order_style == "PASSIVE_MAKER" else None,
        True,
    )
    return replace(
        provisional,
        intent_id=content_id("paperintent:sha256:", _intent_preimage(provisional)),
    )


def validate_paper_intent(intent: object, binding: PaperBinding) -> None:
    if type(intent) is not PaperIntent:
        raise PaperTradingError("INTENT_INVALID")
    validate_paper_binding(binding)
    if (
        intent.schema_version != SCHEMA_VERSION
        or intent.binding_id != binding.binding_id
        or intent.side not in SIDES
        or intent.order_style != binding.execution_mode
        or intent.ttl_ns
        != (binding.order_ttl_ns if intent.order_style == "PASSIVE_MAKER" else None)
        or intent.intent_id
        != content_id("paperintent:sha256:", _intent_preimage(intent))
        or not intent.simulated_paper_only
    ):
        raise PaperTradingError("INTENT_INVALID")
    _text(intent.market_id)
    _text(intent.asset_id)
    _time(intent.decision_time_ns)
    if type(binding) is ResearchPaperStrategyBinding and (
        intent.market_id not in binding.allowed_market_ids
        or not binding.decision_time_start_ns
        <= intent.decision_time_ns
        < binding.decision_time_end_ns
    ):
        raise PaperTradingError("INTENT_INVALID")
    if decimal_value(intent.quantity, nonnegative=True) <= 0:
        raise PaperTradingError("INTENT_INVALID")
    if decimal_value(intent.reference_price, nonnegative=True) > 1:
        raise PaperTradingError("INTENT_INVALID")


@dataclass(frozen=True)
class PaperRiskLimits:
    initial_cash: str
    max_single_order_notional: str
    max_per_market_gross_exposure: str
    max_total_gross_exposure: str
    max_open_orders: int
    max_session_drawdown: str
    max_utc_day_loss: str
    minimum_free_cash_reserve: str
    max_market_data_age_ns: int
    max_position_quantity: str | None = None


def validate_risk_limits(limits: object) -> None:
    if type(limits) is not PaperRiskLimits:
        raise PaperTradingError("RISK_LIMITS_INVALID")
    for name in (
        "initial_cash",
        "max_single_order_notional",
        "max_per_market_gross_exposure",
        "max_total_gross_exposure",
        "max_session_drawdown",
        "max_utc_day_loss",
        "minimum_free_cash_reserve",
    ):
        decimal_value(getattr(limits, name), nonnegative=True)
    if (
        decimal_value(limits.initial_cash) <= 0
        or decimal_value(limits.minimum_free_cash_reserve)
        > decimal_value(limits.initial_cash)
        or not isinstance(limits.max_open_orders, int)
        or isinstance(limits.max_open_orders, bool)
        or limits.max_open_orders < 1
        or not isinstance(limits.max_market_data_age_ns, int)
        or limits.max_market_data_age_ns < 0
    ):
        raise PaperTradingError("RISK_LIMITS_INVALID")
    if (
        limits.max_position_quantity is not None
        and decimal_value(limits.max_position_quantity, nonnegative=True) <= 0
    ):
        raise PaperTradingError("RISK_LIMITS_INVALID")


@dataclass(frozen=True)
class PaperRiskDecision:
    decision_id: str
    intent_id: str
    result: str
    reason_codes: tuple[str, ...]
    decided_time_ns: int
    limits_hash: str


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    intent_id: str
    market_id: str
    asset_id: str
    side: str
    order_style: str
    quantity: str
    reference_price: str
    filled_quantity: str
    fill_notional: str
    fee_paid: str
    status: str
    created_time_ns: int
    arrival_time_ns: int
    expiry_time_ns: int | None
    reserved_cash: str
    reserved_quantity: str
    queue_ahead: str | None
    risk_decision_id: str | None
    arrival_mid: str | None = None
    markout_mid: str | None = None
    markout_lineage: str | None = None
    markout_observed_receive_time_ns: int | None = None
    markout_status: str = "PENDING"
    passive_fill_eligible: bool | None = None


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    fill_sequence: int
    market_id: str
    asset_id: str
    side: str
    quantity: str
    price: str
    fee: str
    spread_cost: str
    depth_slippage_cost: str
    latency_cost: str
    event_time_ns: int
    receive_time_ns: int
    market_truth_lineage: str
    fill_kind: str = "SIMULATED_PAPER_FILL"


@dataclass(frozen=True)
class PaperMarkout:
    markout_id: str
    fill_id: str
    target_time_ns: int
    observed_receive_time_ns: int
    adverse_selection_cost: str | None
    market_truth_lineage: str | None
    status: str


def validate_risk_decision(decision: object) -> None:
    if type(decision) is not PaperRiskDecision:
        raise PaperTradingError("RISK_DECISION_INVALID")
    if (
        decision.decision_id
        != content_id(
            "paperrisk:sha256:",
            {
                "intent_id": decision.intent_id,
                "result": decision.result,
                "reason_codes": list(decision.reason_codes),
                "decided_time_ns": decision.decided_time_ns,
                "limits_hash": decision.limits_hash,
            },
        )
        or _ID_RE.fullmatch(decision.intent_id) is None
        or decision.result not in RISK_RESULTS
        or decision.reason_codes
        != tuple(code for code in RISK_REASON_CODES if code in decision.reason_codes)
        or len(set(decision.reason_codes)) != len(decision.reason_codes)
        or any(code not in RISK_REASON_CODES for code in decision.reason_codes)
        or (decision.result == "ALLOW") != (not decision.reason_codes)
        or _ID_RE.fullmatch(decision.limits_hash) is None
    ):
        raise PaperTradingError("RISK_DECISION_INVALID")
    _time(decision.decided_time_ns)


def validate_order(order: object) -> None:
    if type(order) is not PaperOrder:
        raise PaperTradingError("ORDER_INVALID")
    quantity = decimal_value(order.quantity, nonnegative=True)
    filled = decimal_value(order.filled_quantity, nonnegative=True)
    if (
        _ID_RE.fullmatch(order.order_id) is None
        or order.order_id
        != content_id("paperorder:sha256:", {"intent_id": order.intent_id})
        or _ID_RE.fullmatch(order.intent_id) is None
        or order.side not in SIDES
        or order.order_style not in ORDER_STYLES
        or order.status not in ORDER_STATES
        or quantity <= 0
        or filled > quantity
        or decimal_value(order.reference_price, nonnegative=True) > 1
        or decimal_value(order.fill_notional, nonnegative=True) < 0
        or decimal_value(order.reserved_cash, nonnegative=True) < 0
        or decimal_value(order.reserved_quantity, nonnegative=True) < 0
        or (
            order.queue_ahead is not None
            and decimal_value(order.queue_ahead, nonnegative=True) < 0
        )
        or order.arrival_time_ns < order.created_time_ns
        or (order.expiry_time_ns is not None and order.expiry_time_ns <= order.arrival_time_ns)
        or order.status != "PENDING_RISK" and order.risk_decision_id is None
        or order.risk_decision_id is not None
        and _ID_RE.fullmatch(order.risk_decision_id) is None
        or order.arrival_mid is not None
        and decimal_value(order.arrival_mid, nonnegative=True) > 1
        or order.markout_mid is not None
        and decimal_value(order.markout_mid, nonnegative=True) > 1
        or order.markout_status
        not in {"PENDING", "AVAILABLE", "MARKET_DATA_UNAVAILABLE"}
        or (order.markout_status == "AVAILABLE") != (order.markout_mid is not None)
        or order.markout_status == "PENDING"
        and order.markout_observed_receive_time_ns is not None
        or order.passive_fill_eligible is not None
        and not isinstance(order.passive_fill_eligible, bool)
        or order.order_style == "AGGRESSIVE_TAKER"
        and order.passive_fill_eligible is not None
    ):
        raise PaperTradingError("ORDER_INVALID")
    decimal_value(order.fee_paid)
    _text(order.market_id)
    _text(order.asset_id)
    _time(order.created_time_ns)
    _time(order.arrival_time_ns)
    if order.markout_lineage is not None:
        _text(order.markout_lineage)
    if order.markout_observed_receive_time_ns is not None:
        _time(order.markout_observed_receive_time_ns)


def _fill_identity_preimage(fill: PaperFill) -> dict[str, object]:
    return {
        "order_id": fill.order_id,
        "fill_sequence": fill.fill_sequence,
        "quantity": fill.quantity,
        "price": fill.price,
        "fee": fill.fee,
        "spread_cost": fill.spread_cost,
        "depth_slippage_cost": fill.depth_slippage_cost,
        "latency_cost": fill.latency_cost,
        "receive_time_ns": fill.receive_time_ns,
        "market_truth_lineage": fill.market_truth_lineage,
    }


def validate_fill(fill: object) -> None:
    if type(fill) is not PaperFill:
        raise PaperTradingError("FILL_INVALID")
    if (
        fill.fill_id != content_id("paperfill:sha256:", _fill_identity_preimage(fill))
        or _ID_RE.fullmatch(fill.order_id) is None
        or not isinstance(fill.fill_sequence, int)
        or isinstance(fill.fill_sequence, bool)
        or fill.fill_sequence < 1
        or fill.side not in SIDES
        or decimal_value(fill.quantity, nonnegative=True) <= 0
        or decimal_value(fill.price, nonnegative=True) > 1
        or decimal_value(fill.spread_cost, nonnegative=True) < 0
        or decimal_value(fill.depth_slippage_cost, nonnegative=True) < 0
        or fill.fill_kind != "SIMULATED_PAPER_FILL"
    ):
        raise PaperTradingError("FILL_INVALID")
    decimal_value(fill.fee)
    decimal_value(fill.latency_cost)
    _text(fill.market_id)
    _text(fill.asset_id)
    _text(fill.market_truth_lineage)
    _time(fill.event_time_ns)
    _time(fill.receive_time_ns)


def validate_markout(markout: object) -> None:
    if type(markout) is not PaperMarkout:
        raise PaperTradingError("MARKOUT_INVALID")
    data = {
        "fill_id": markout.fill_id,
        "target_time_ns": markout.target_time_ns,
        "observed_receive_time_ns": markout.observed_receive_time_ns,
        "adverse_selection_cost": markout.adverse_selection_cost,
        "market_truth_lineage": markout.market_truth_lineage,
        "status": markout.status,
    }
    if (
        markout.markout_id != content_id("papermarkout:sha256:", data)
        or _ID_RE.fullmatch(markout.fill_id) is None
        or markout.status not in {"AVAILABLE", "MARKET_DATA_UNAVAILABLE"}
        or (markout.status == "AVAILABLE")
        != (markout.adverse_selection_cost is not None)
    ):
        raise PaperTradingError("MARKOUT_INVALID")
    if markout.adverse_selection_cost is not None:
        decimal_value(markout.adverse_selection_cost, nonnegative=True)
    if markout.market_truth_lineage is not None:
        _text(markout.market_truth_lineage)
    _time(markout.target_time_ns)
    _time(markout.observed_receive_time_ns)


@dataclass(frozen=True)
class PaperMarketEvent:
    kind: str
    market_id: str
    asset_id: str | None
    event_time_ns: int
    receive_time_ns: int
    lineage: str
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    side: str | None = None
    price: str | None = None
    size: str | None = None
    winner_asset_id: str | None = None


def validate_market_event(event: object) -> None:
    if type(event) is not PaperMarketEvent or event.kind not in {
        "BOOK",
        "TRADE",
        "GAP_OPEN",
        "GAP_HEALED",
        "RESOLUTION",
    }:
        raise PaperTradingError("MARKET_EVENT_INVALID")
    _text(event.market_id)
    _text(event.lineage)
    _time(event.event_time_ns)
    _time(event.receive_time_ns)
    if event.asset_id is not None:
        _text(event.asset_id)
    if event.kind == "BOOK":
        if (
            event.asset_id is None
            or event.side is not None
            or event.price is not None
            or event.size is not None
        ):
            raise PaperTradingError("MARKET_EVENT_INVALID")
        try:
            bids = tuple(
                (decimal_value(p, nonnegative=True), decimal_value(q, nonnegative=True))
                for p, q in event.bids
            )
            asks = tuple(
                (decimal_value(p, nonnegative=True), decimal_value(q, nonnegative=True))
                for p, q in event.asks
            )
        except (TypeError, ValueError):
            raise PaperTradingError("MARKET_EVENT_INVALID") from None
        if (
            not bids
            or not asks
            or any(p > 1 or q <= 0 for p, q in bids + asks)
            or bids != tuple(sorted(bids, reverse=True))
            or asks != tuple(sorted(asks))
            or bids[0][0] >= asks[0][0]
        ):
            raise PaperTradingError("MARKET_EVENT_INVALID")
    elif event.kind == "TRADE":
        if (
            event.asset_id is None
            or event.side not in SIDES
            or event.price is None
            or event.size is None
        ):
            raise PaperTradingError("MARKET_EVENT_INVALID")
        if (
            decimal_value(event.price, nonnegative=True) > 1
            or decimal_value(event.size, nonnegative=True) <= 0
        ):
            raise PaperTradingError("MARKET_EVENT_INVALID")


def dataclass_from_mapping(cls: type, value: Mapping[str, object]):
    try:
        data = dict(value)
        if cls is PaperRiskDecision:
            data["reason_codes"] = tuple(data["reason_codes"])
        elif cls is PaperMarketEvent:
            data["bids"] = tuple(tuple(level) for level in data.get("bids", ()))
            data["asks"] = tuple(tuple(level) for level in data.get("asks", ()))
        elif cls is ResearchPaperStrategyBinding:
            for name in (
                "subject_refs",
                "allowed_market_ids",
                "reserved_evidence_refs",
                "admitted_scope_refs",
            ):
                data[name] = tuple(data[name])
        return cls(**data)
    except (KeyError, TypeError, ValueError):
        raise PaperTradingError("SERIALIZATION_INVALID") from None


def canonical_mapping(record: object) -> dict[str, object]:
    if not hasattr(record, "__dataclass_fields__"):
        raise PaperTradingError("SERIALIZATION_INVALID")
    return asdict(record)
