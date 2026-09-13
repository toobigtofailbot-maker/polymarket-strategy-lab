"""Immutable content-addressed records for WP172 executable-edge research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from collections.abc import Sequence

from src.data_layer.analytical_research import PreregisteredExperiment, RunEvidenceReceipt
from src.data_layer.analytical_research.experiment_os import record_to_mapping

SCHEMA_VERSION = "1.0.0"
TRACE_SCHEMA_ID = "polymarket-research-decision-trace"
COST_MODEL_SCHEMA_ID = "polymarket-execution-cost-model"
ASSESSMENT_SCHEMA_ID = "polymarket-executable-edge-assessment"

EXECUTION_MODES = ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")
ASSESSMENT_STATUSES = (
    "EXECUTABLE_EDGE_PASS",
    "EXECUTABLE_EDGE_FAIL",
    "EXECUTABLE_EDGE_INCONCLUSIVE",
    "DIAGNOSTIC_ONLY",
)
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*:sha256:[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class ExecutableEdgeError(ValueError):
    """Closed failure: the message is a stable code and never echoes input."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _id(prefix: str, preimage: object) -> str:
    return prefix + hashlib.sha256(canonical_bytes(preimage)).hexdigest()


def decimal_value(value: object, *, nonnegative: bool = False) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise ExecutableEdgeError("FIELD_VALUE_INVALID")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ExecutableEdgeError("FIELD_VALUE_INVALID") from exc
    if not result.is_finite() or (nonnegative and result < 0):
        raise ExecutableEdgeError("FIELD_VALUE_INVALID")
    return result


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ExecutableEdgeError("FIELD_VALUE_INVALID")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _text(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ExecutableEdgeError("FIELD_VALUE_INVALID")
    return value


def _nonnegative_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ExecutableEdgeError("FIELD_VALUE_INVALID")
    return value


def _validate_wp170(experiment: object, evidence: object) -> tuple[PreregisteredExperiment, RunEvidenceReceipt]:
    if not isinstance(experiment, PreregisteredExperiment) or not isinstance(evidence, RunEvidenceReceipt):
        raise ExecutableEdgeError("WP170_EVIDENCE_INVALID")
    try:
        record_to_mapping(experiment)
        record_to_mapping(evidence)
    except Exception as exc:
        raise ExecutableEdgeError("WP170_EVIDENCE_INVALID") from exc
    if evidence.experiment_id != experiment.experiment_id:
        raise ExecutableEdgeError("WP170_EVIDENCE_INVALID")
    return experiment, evidence


def authoritative_first_look(experiment: object, evidence: object) -> bool:
    try:
        exp, receipt = _validate_wp170(experiment, evidence)
    except ExecutableEdgeError:
        return False
    return bool(
        receipt.experiment_id == exp.experiment_id
        and receipt.evaluated_role == "OUT_OF_SAMPLE"
        and receipt.oos_exposure_ordinal == 1
        and receipt.result_status == "OOS_CRITERIA_MET_UNCOSTED"
        and receipt.uncertainty_state == "NONE"
        and receipt.candidate_criterion_met
        and receipt.baseline_criterion_met
    )


@dataclass(frozen=True)
class ResearchDecisionEvent:
    market_id: str
    asset_id: str
    decision_time_ns: int
    side: str
    action: str
    intended_quantity: str
    decision_reference_price: str
    estimated_value: str


@dataclass(frozen=True)
class ResearchDecisionTrace:
    schema_id: str
    schema_version: str
    trace_id: str
    experiment_id: str
    first_look_evidence_id: str
    events: tuple[ResearchDecisionEvent, ...]
    advisory_only: bool
    no_execution_authority: bool


def _event_mapping(event: ResearchDecisionEvent) -> dict[str, object]:
    return asdict(event)


def build_research_decision_trace(
    experiment: object, evidence: object, events: Sequence[ResearchDecisionEvent]
) -> ResearchDecisionTrace:
    exp, receipt = _validate_wp170(experiment, evidence)
    if not events or len(events) > 4096:
        raise ExecutableEdgeError("DECISION_TRACE_INVALID")
    normalized: list[ResearchDecisionEvent] = []
    previous_key: tuple[int, str, str] | None = None
    for event in events:
        if type(event) is not ResearchDecisionEvent:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        _text(event.market_id)
        _text(event.asset_id)
        _nonnegative_int(event.decision_time_ns)
        if event.side not in {"BUY", "SELL"} or event.action not in {"ENTER", "EXIT"}:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        if decimal_value(event.intended_quantity, nonnegative=True) <= 0:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        for price in (event.decision_reference_price, event.estimated_value):
            parsed = decimal_value(price, nonnegative=True)
            if parsed > 1:
                raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        key = (event.decision_time_ns, event.market_id, event.asset_id)
        if previous_key is not None and key <= previous_key:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        previous_key = key
        normalized.append(event)
    preimage = {
        "schema_id": TRACE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "experiment_id": exp.experiment_id,
        "first_look_evidence_id": receipt.run_evidence_receipt_id,
        "events": [_event_mapping(event) for event in normalized],
    }
    return ResearchDecisionTrace(
        TRACE_SCHEMA_ID,
        SCHEMA_VERSION,
        _id("decisiontrace:sha256:", preimage),
        exp.experiment_id,
        receipt.run_evidence_receipt_id,
        tuple(normalized),
        True,
        True,
    )


def validate_research_decision_trace(trace: object) -> None:
    if type(trace) is not ResearchDecisionTrace:
        raise ExecutableEdgeError("DECISION_TRACE_INVALID")
    pseudo_experiment = trace.experiment_id
    preimage = {
        "schema_id": trace.schema_id,
        "schema_version": trace.schema_version,
        "experiment_id": pseudo_experiment,
        "first_look_evidence_id": trace.first_look_evidence_id,
        "events": [_event_mapping(event) for event in trace.events],
    }
    if (
        trace.schema_id != TRACE_SCHEMA_ID
        or trace.schema_version != SCHEMA_VERSION
        or not _ID_RE.fullmatch(trace.trace_id)
        or trace.trace_id != _id("decisiontrace:sha256:", preimage)
        or not trace.advisory_only
        or not trace.no_execution_authority
    ):
        raise ExecutableEdgeError("DECISION_TRACE_INVALID")
    # Reuse the same closed event checks without requiring WP170 objects.
    if not trace.events:
        raise ExecutableEdgeError("DECISION_TRACE_INVALID")
    prior: tuple[int, str, str] | None = None
    for event in trace.events:
        _text(event.market_id)
        _text(event.asset_id)
        _nonnegative_int(event.decision_time_ns)
        if event.side not in {"BUY", "SELL"} or event.action not in {"ENTER", "EXIT"}:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        if decimal_value(event.intended_quantity, nonnegative=True) <= 0:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        for value in (event.decision_reference_price, event.estimated_value):
            if decimal_value(value, nonnegative=True) > 1:
                raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        key = (event.decision_time_ns, event.market_id, event.asset_id)
        if prior is not None and key <= prior:
            raise ExecutableEdgeError("DECISION_TRACE_INVALID")
        prior = key


@dataclass(frozen=True)
class ExecutionCostModel:
    schema_id: str
    schema_version: str
    cost_model_id: str
    model_version: str
    execution_mode: str
    fee_schedule_reference: str
    fee_rate_bps: str | None
    maker_rebate_bps: str
    maker_rebate_evidence_reference: str | None
    latency_ns: int
    order_ttl_ns: int | None
    size_grid: tuple[str, ...]
    queue_ahead_multiplier: str
    markout_horizon_ns: int
    net_edge_threshold: str
    minimum_fill_ratio: str
    minimum_capacity_quantity: str
    max_data_age_ns: int
    advisory_only: bool
    no_execution_authority: bool


def _cost_preimage(model: ExecutionCostModel) -> dict[str, object]:
    value = asdict(model)
    value.pop("cost_model_id")
    value.pop("advisory_only")
    value.pop("no_execution_authority")
    value["size_grid"] = list(model.size_grid)
    return value


def build_execution_cost_model(
    *, model_version: str, execution_mode: str, fee_schedule_reference: str,
    fee_rate_bps: str | None, latency_ns: int, order_ttl_ns: int | None,
    size_grid: Sequence[str], queue_ahead_multiplier: str,
    markout_horizon_ns: int, net_edge_threshold: str, minimum_fill_ratio: str,
    minimum_capacity_quantity: str, max_data_age_ns: int,
    maker_rebate_bps: str = "0", maker_rebate_evidence_reference: str | None = None,
) -> ExecutionCostModel:
    if execution_mode not in EXECUTION_MODES:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    _text(model_version)
    _text(fee_schedule_reference)
    if fee_rate_bps is not None:
        decimal_value(fee_rate_bps, nonnegative=True)
    rebate = decimal_value(maker_rebate_bps, nonnegative=True)
    if rebate and not maker_rebate_evidence_reference:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    if maker_rebate_evidence_reference is not None:
        _text(maker_rebate_evidence_reference)
    _nonnegative_int(latency_ns)
    _nonnegative_int(markout_horizon_ns)
    _nonnegative_int(max_data_age_ns)
    if order_ttl_ns is not None:
        _nonnegative_int(order_ttl_ns)
    if execution_mode == "PASSIVE_MAKER" and (order_ttl_ns is None or order_ttl_ns <= 0):
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    if not isinstance(size_grid, Sequence) or isinstance(size_grid, (str, bytes)) or not size_grid:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    grid = tuple(size_grid)
    parsed_grid = tuple(decimal_value(item, nonnegative=True) for item in grid)
    if any(item <= 0 for item in parsed_grid) or tuple(sorted(parsed_grid)) != parsed_grid or len(set(parsed_grid)) != len(parsed_grid):
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    if decimal_value(queue_ahead_multiplier, nonnegative=True) < 1:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    decimal_value(net_edge_threshold)
    fill = decimal_value(minimum_fill_ratio, nonnegative=True)
    if fill > 1:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    capacity = decimal_value(minimum_capacity_quantity, nonnegative=True)
    if capacity <= 0 or capacity not in parsed_grid:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    provisional = ExecutionCostModel(
        COST_MODEL_SCHEMA_ID, SCHEMA_VERSION, "", model_version, execution_mode,
        fee_schedule_reference, fee_rate_bps, maker_rebate_bps,
        maker_rebate_evidence_reference, latency_ns, order_ttl_ns, grid,
        queue_ahead_multiplier, markout_horizon_ns, net_edge_threshold,
        minimum_fill_ratio, minimum_capacity_quantity, max_data_age_ns, True, True,
    )
    return ExecutionCostModel(
        **{**asdict(provisional), "cost_model_id": _id("costmodel:sha256:", _cost_preimage(provisional)), "size_grid": grid}
    )


def validate_execution_cost_model(model: object) -> None:
    if type(model) is not ExecutionCostModel:
        raise ExecutableEdgeError("COST_MODEL_INVALID")
    rebuilt = build_execution_cost_model(
        model_version=model.model_version, execution_mode=model.execution_mode,
        fee_schedule_reference=model.fee_schedule_reference, fee_rate_bps=model.fee_rate_bps,
        maker_rebate_bps=model.maker_rebate_bps,
        maker_rebate_evidence_reference=model.maker_rebate_evidence_reference,
        latency_ns=model.latency_ns, order_ttl_ns=model.order_ttl_ns,
        size_grid=model.size_grid, queue_ahead_multiplier=model.queue_ahead_multiplier,
        markout_horizon_ns=model.markout_horizon_ns, net_edge_threshold=model.net_edge_threshold,
        minimum_fill_ratio=model.minimum_fill_ratio,
        minimum_capacity_quantity=model.minimum_capacity_quantity,
        max_data_age_ns=model.max_data_age_ns,
    )
    if rebuilt != model:
        raise ExecutableEdgeError("COST_MODEL_INVALID")


@dataclass(frozen=True)
class ExecutableEdgeAssessment:
    schema_id: str
    schema_version: str
    assessment_id: str
    experiment_id: str
    first_look_evidence_id: str
    decision_trace_id: str
    cost_model_id: str
    market_data_lineage_id: str
    status: str
    wp173_evaluation_eligible: bool
    gross_research_result: str
    spread_cost: str
    depth_slippage_cost: str
    latency_cost: str
    fee_cost: str | None
    adverse_selection_cost: str
    filled_quantity: str
    intended_quantity: str
    fill_ratio: str
    net_result: str | None
    net_edge_per_filled_unit: str | None
    capacity_quantity: str
    capacity_pass: bool
    assumptions: tuple[str, ...]
    diagnostic_codes: tuple[str, ...]
    advisory_only: bool
    no_execution_authority: bool


def assessment_preimage(assessment: ExecutableEdgeAssessment) -> dict[str, object]:
    value = asdict(assessment)
    value.pop("assessment_id")
    value.pop("advisory_only")
    value.pop("no_execution_authority")
    value["assumptions"] = list(assessment.assumptions)
    value["diagnostic_codes"] = list(assessment.diagnostic_codes)
    return value


def identify_assessment(assessment: ExecutableEdgeAssessment) -> str:
    return _id("edgeassessment:sha256:", assessment_preimage(assessment))


def validate_assessment(assessment: object) -> None:
    if type(assessment) is not ExecutableEdgeAssessment:
        raise ExecutableEdgeError("ASSESSMENT_INVALID")
    if set(asdict(assessment)) != {field.name for field in fields(ExecutableEdgeAssessment)}:
        raise ExecutableEdgeError("ASSESSMENT_INVALID")
    if (
        assessment.schema_id != ASSESSMENT_SCHEMA_ID
        or assessment.schema_version != SCHEMA_VERSION
        or assessment.status not in ASSESSMENT_STATUSES
        or assessment.wp173_evaluation_eligible != (assessment.status == "EXECUTABLE_EDGE_PASS")
        or assessment.assessment_id != identify_assessment(assessment)
        or not assessment.advisory_only
        or not assessment.no_execution_authority
    ):
        raise ExecutableEdgeError("ASSESSMENT_INVALID")
    for name in (
        "gross_research_result", "spread_cost", "depth_slippage_cost", "latency_cost",
        "adverse_selection_cost", "filled_quantity", "intended_quantity", "fill_ratio",
        "capacity_quantity",
    ):
        decimal_value(getattr(assessment, name))
    for name in ("fee_cost", "net_result", "net_edge_per_filled_unit"):
        value = getattr(assessment, name)
        if value is not None:
            decimal_value(value)
