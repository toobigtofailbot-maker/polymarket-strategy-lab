"""Deterministic, advisory-only evidence derived from verified WP173 paper stores."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from collections.abc import Sequence
import re

from src.paper_trading.accounting import mark_account
from src.paper_trading.engine import _replay_journal, state_to_mapping, valid_marks
from src.paper_trading.models import (
    PaperStrategyBinding,
    PaperTradingError,
    ResearchPaperStrategyBinding,
    canonical_json_bytes,
    content_id,
    decimal_text,
)
from src.paper_trading.store import PaperStore
from src.research_runtime.hermes_controlled_runtime.context_reconciliation import (
    ContextEvidenceItem,
    ReconciliationError,
    build_evidence_item,
)


SNAPSHOT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ResearchPaperPerformanceSnapshot:
    snapshot_id: str
    schema_version: str
    paper_session_id: str
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
    paper_store_event_sequence: int
    paper_store_event_head: str
    paper_store_state_hash: str
    observation_start_ns: int
    observation_end_ns: int
    information_cutoff_ns: int
    control_state: str
    reconciliation_state: str
    intent_count: int
    order_count: int
    fill_count: int
    closed_order_state_counts: tuple[tuple[str, int], ...]
    risk_allow_count: int
    risk_deny_count: int
    risk_reason_counts: tuple[tuple[str, int], ...]
    intended_quantity: str
    filled_quantity: str
    fill_ratio: str
    fee_total: str
    spread_cost_total: str
    depth_slippage_cost_total: str
    latency_cost_total: str
    adverse_selection_cost_total: str
    pending_markout_count: int
    cash: str
    reserved_cash: str
    equity: str | None
    realized_paper_pnl: str
    unrealized_paper_pnl: str | None
    gapped_asset_count: int
    resolution_pending_count: int
    research_paper_only: bool
    advisory_only: bool
    no_qualification_authority: bool
    no_execution_authority: bool
    no_live_authority: bool


def _sum(values: Sequence[str]) -> str:
    return decimal_text(sum((Decimal(value) for value in values), Decimal(0)))


def _snapshot_preimage(snapshot: ResearchPaperPerformanceSnapshot) -> dict[str, object]:
    value = asdict(snapshot)
    value.pop("snapshot_id")
    for key in (
        "research_paper_only",
        "advisory_only",
        "no_qualification_authority",
        "no_execution_authority",
        "no_live_authority",
    ):
        value.pop(key)
    return value


def _lineage(binding: object) -> tuple[str, str | None, str | None, str, str, str, tuple[str, ...], str, str]:
    if type(binding) is ResearchPaperStrategyBinding:
        return (
            binding.candidate_id,
            binding.hypothesis_family_id,
            binding.research_episode_id,
            binding.strategy_spec_id,
            binding.strategy_version,
            binding.strategy_code_identity,
            binding.subject_refs,
            binding.scope_id,
            "RESEARCH_PAPER",
        )
    if type(binding) is PaperStrategyBinding:
        return (
            binding.experiment_id,
            None,
            None,
            binding.cost_model_id,
            binding.strategy_label,
            binding.assessment_id,
            (binding.experiment_id, binding.market_data_lineage_id),
            binding.decision_trace_id,
            "QUALIFIED_PAPER",
        )
    raise PaperTradingError("SNAPSHOT_BINDING_INVALID")


def build_research_paper_performance_snapshot(
    store: PaperStore,
) -> ResearchPaperPerformanceSnapshot:
    if store.reconciliation_blocked:
        raise PaperTradingError("SNAPSHOT_RECONCILIATION_BLOCKED")
    raw, events, head = store.recovery_snapshot()
    if raw is None or head is None or not events:
        raise PaperTradingError("SNAPSHOT_STORE_INVALID")
    try:
        state = _replay_journal(events)
    except (IndexError, KeyError, StopIteration, TypeError, PaperTradingError):
        raise PaperTradingError("SNAPSHOT_RECONCILIATION_BLOCKED") from None
    if state.control_state == "RECONCILIATION_BLOCKED" or state_to_mapping(state) != raw:
        raise PaperTradingError("SNAPSHOT_RECONCILIATION_BLOCKED")
    lineage = _lineage(state.binding)
    state_counts = tuple(
        (name, sum(order.status == name for order in state.orders))
        for name in ("REJECTED", "FILLED", "CANCELLED", "EXPIRED")
    )
    reason_counts: dict[str, int] = {}
    for decision in state.risk_decisions:
        for reason in decision.reason_codes:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    intended = sum((Decimal(order.quantity) for order in state.orders), Decimal(0))
    filled = sum((Decimal(order.filled_quantity) for order in state.orders), Decimal(0))
    marked = mark_account(state.account, valid_marks(state))
    start = min(event.event_time_ns for event in events)
    end = max(event.event_time_ns for event in events)
    adverse = tuple(
        item.adverse_selection_cost
        for item in state.markouts
        if item.adverse_selection_cost is not None
    )
    provisional = ResearchPaperPerformanceSnapshot(
        "",
        SNAPSHOT_SCHEMA_VERSION,
        state.session_id,
        state.binding.binding_id,
        lineage[8],
        lineage[0],
        lineage[1],
        lineage[2],
        lineage[3],
        lineage[4],
        lineage[5],
        lineage[6],
        lineage[7],
        head.last_sequence,
        head.last_event_hash,
        head.state_hash,
        start,
        end,
        end,
        state.control_state,
        "HEALTHY",
        sum(event.event_type == "ORDER_PENDING_RISK" for event in events),
        len(state.orders),
        len(state.fills),
        state_counts,
        sum(item.result == "ALLOW" for item in state.risk_decisions),
        sum(item.result == "DENY" for item in state.risk_decisions),
        tuple(sorted(reason_counts.items())),
        decimal_text(intended),
        decimal_text(filled),
        decimal_text(filled / intended) if intended else "0",
        _sum(tuple(item.fee for item in state.fills)),
        _sum(tuple(item.spread_cost for item in state.fills)),
        _sum(tuple(item.depth_slippage_cost for item in state.fills)),
        _sum(tuple(item.latency_cost for item in state.fills)),
        _sum(adverse),
        sum(item.markout_status == "PENDING" for item in state.orders),
        state.account.cash,
        state.account.reserved_cash,
        marked["equity"],
        state.account.realized_pnl,
        marked["unrealized_pnl"],
        len(state.gapped_assets),
        len(state.resolution_pending),
        True,
        True,
        True,
        True,
        True,
    )
    return replace(
        provisional,
        snapshot_id=content_id(
            "researchpapersnapshot:sha256:", _snapshot_preimage(provisional)
        ),
    )


def snapshot_to_mapping(snapshot: ResearchPaperPerformanceSnapshot) -> dict[str, object]:
    if type(snapshot) is not ResearchPaperPerformanceSnapshot:
        raise PaperTradingError("SNAPSHOT_INVALID")
    expected = content_id("researchpapersnapshot:sha256:", _snapshot_preimage(snapshot))
    if (
        snapshot.schema_version != SNAPSHOT_SCHEMA_VERSION
        or snapshot.snapshot_id != expected
        or not snapshot.research_paper_only
        or not snapshot.advisory_only
        or not snapshot.no_qualification_authority
        or not snapshot.no_execution_authority
        or not snapshot.no_live_authority
    ):
        raise PaperTradingError("SNAPSHOT_INVALID")
    return asdict(snapshot)


def build_snapshot_context_evidence(
    snapshot: ResearchPaperPerformanceSnapshot,
    *,
    subject_refs: Sequence[str],
    scope_sha256: str,
    information_cutoff: str,
    admissibility_status: str,
    direction: str,
) -> ContextEvidenceItem:
    snapshot_to_mapping(snapshot)
    if (
        tuple(sorted(set(subject_refs))) != snapshot.subject_refs
        or re.fullmatch(r"[0-9a-f]{64}", scope_sha256) is None
        or not isinstance(information_cutoff, str)
        or not information_cutoff
        or admissibility_status not in {"ADMISSIBLE", "INADMISSIBLE"}
    ):
        raise ReconciliationError("EVIDENCE_INVALID")
    return build_evidence_item(
        content_sha256=snapshot.snapshot_id.rsplit(":", 1)[-1],
        evidence_class="DETERMINISTIC_DERIVED",
        subject_refs=subject_refs,
        scope_sha256=scope_sha256,
        information_cutoff=information_cutoff,
        admissibility_status=admissibility_status,
        origin="DETERMINISTIC_PROJECT_EVIDENCE",
        direction=direction,
    )


def snapshot_json_bytes(snapshot: ResearchPaperPerformanceSnapshot) -> bytes:
    return canonical_json_bytes(snapshot_to_mapping(snapshot))
