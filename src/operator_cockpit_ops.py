"""S10-CC-OPS-01 read-only Control Center portfolio-operations projection.

Pure, bounded projection over canonical StrategyLifecycle portfolio authority. It reads
lifecycle state only through ``load_strategy_lifecycle_store`` (a valid, non-null
verified ``StrategyLifecycleSnapshot``) and evaluates capacity only through the canonical
``evaluate_portfolio_capacity(snapshot, evaluated_at_ns)``, called exactly once per
projection with the caller's single backend evaluation time.

It never opens a store itself, never appends or initializes, never re-validates records,
never computes capacity on its own and never performs network, subprocess or file writes.
Budget reservations are policy/reservation state only: they are not actual account
exposure, orders, fills or PnL, and nothing projected here implies Gate-C eligibility,
host or network currentness, execution readiness or live authority. Paper and gateway
state are composed by the frontend from their existing read-only APIs; they are never
read or merged here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.strategy_lifecycle import (
    RISK_BANDS,
    PortfolioAuthorityPolicy,
    PortfolioCapacityResult,
    StrategyLifecycleSnapshot,
    StrategyRestrictionReceipt,
    StrategyRiskAllocation,
    evaluate_portfolio_capacity,
    load_strategy_lifecycle_store,
)


POLICY_LIMIT_FIELDS = (
    "global_capital_at_risk_max_usd",
    "global_gross_exposure_max_usd",
    "global_daily_loss_max_usd",
    "global_drawdown_max_usd",
    "global_cumulative_loss_max_usd",
    "exploratory_pool_max_usd",
    "validated_pool_max_usd",
    "mature_pool_max_usd",
    "max_exploratory_per_strategy_usd",
    "max_validated_per_strategy_usd",
    "max_mature_per_strategy_usd",
    "max_per_market_usd",
    "max_order_notional_usd",
    "max_active_strategies",
    "max_active_markets",
    "max_simultaneous_open_orders",
    "max_mutations_per_minute",
)
NON_AUTHORITY = {
    "budget_reservation_only": True,
    "actual_account_exposure_not_measured": True,
    "orders_not_measured": True,
    "fills_not_measured": True,
    "pnl_not_measured": True,
    "gate_c_not_implied": True,
    "execution_not_implied": True,
    "live_not_implied": True,
}


class OpsProjectionError(Exception):
    """Closed, payload-free projection failure: always SOURCE_UNAVAILABLE."""

    def __init__(self) -> None:
        super().__init__("SOURCE_UNAVAILABLE")
        self.code = "SOURCE_UNAVAILABLE"


def _load(path: Path) -> StrategyLifecycleSnapshot:
    result = load_strategy_lifecycle_store(path)
    if not result.is_valid or not isinstance(result.snapshot, StrategyLifecycleSnapshot):
        raise OpsProjectionError()
    return result.snapshot


def _policy(policy: PortfolioAuthorityPolicy) -> dict[str, Any]:
    return {
        "policy_id": policy.policy_id,
        "predecessor_policy_id": policy.predecessor_policy_id,
        "policy_label": policy.policy_label,
        "venue_scope": list(policy.venue_scope),
        "account_scope_ref": policy.account_scope_ref,
        "effective_from_ns": policy.effective_from_ns,
        "expires_at_ns": policy.expires_at_ns,
        "limits": {name: getattr(policy, name) for name in POLICY_LIMIT_FIELDS},
        "allowed_order_styles": list(policy.allowed_order_styles),
        "created_time_ns": policy.created_time_ns,
    }


def _capacity(capacity: PortfolioCapacityResult) -> dict[str, Any]:
    return {
        "status": capacity.status,
        "reason_codes": list(capacity.reason_codes),
        "evaluated_at_ns": capacity.at_time_ns,
        "policy_id": capacity.policy_id,
        "reserved_budget_usd": {
            "exploratory": capacity.exploratory_active_usd,
            "validated": capacity.validated_active_usd,
            "mature": capacity.mature_active_usd,
            "total": capacity.total_active_usd,
        },
        "active_real_risk_strategy_count": capacity.active_real_risk_strategy_count,
    }


def _restriction(receipt: StrategyRestrictionReceipt) -> dict[str, Any]:
    return {
        "restriction_receipt_id": receipt.restriction_receipt_id,
        "restriction_key": receipt.restriction_key,
        "restriction_kind": receipt.restriction_kind,
        "max_active_budget_usd": receipt.max_active_budget_usd,
        "created_time_ns": receipt.created_time_ns,
    }


def _reservation(
    snapshot: StrategyLifecycleSnapshot,
    capacity: PortfolioCapacityResult,
    strategy_version_id: str,
    allocation: StrategyRiskAllocation,
    evaluated_at_ns: int,
) -> dict[str, Any]:
    version = snapshot.version_by_id(strategy_version_id)
    if version is None:
        # Impossible in a verified snapshot: fail closed.
        raise OpsProjectionError()
    result = capacity.strategy_result(strategy_version_id)
    return {
        "allocation_id": allocation.allocation_id,
        "strategy_version_id": strategy_version_id,
        "strategy_label": version.strategy_label,
        "policy_id": allocation.policy_id,
        "risk_band": allocation.risk_band,
        "active_budget_usd": allocation.active_budget_usd,
        "allocation_basis": allocation.allocation_basis,
        "valid_from_ns": allocation.valid_from_ns,
        "valid_until_ns": allocation.valid_until_ns,
        "active_at_evaluation": allocation.is_active_at(evaluated_at_ns),
        "health_state": snapshot.health_of(strategy_version_id),
        "capacity_status": result.status if result is not None else None,
        "capacity_reason_codes": list(result.reason_codes) if result is not None else [],
        "active_restrictions": [
            _restriction(item) for item in snapshot.restrictions_of(strategy_version_id)
        ],
    }


def _reservation_order(item: dict[str, Any]) -> tuple[int, int, str, str]:
    band = item["risk_band"]
    return (
        0 if item["active_at_evaluation"] else 1,
        RISK_BANDS.index(band) if band in RISK_BANDS else len(RISK_BANDS),
        item["strategy_label"],
        item["strategy_version_id"],
    )


def _project(path: Path, evaluated_at_ns: int) -> dict[str, Any]:
    snapshot = _load(path)
    capacity = evaluate_portfolio_capacity(snapshot, evaluated_at_ns)
    if not isinstance(capacity, PortfolioCapacityResult):
        raise OpsProjectionError()
    active_policy = None
    if snapshot.active_policy_id is not None:
        policy = snapshot.policy_by_id(snapshot.active_policy_id)
        if policy is None:
            raise OpsProjectionError()
        active_policy = _policy(policy)
    reservations = [
        _reservation(snapshot, capacity, version_id, allocation, evaluated_at_ns)
        for version_id, allocation in snapshot.current_allocation_by_strategy_version
    ]
    reservations.sort(key=_reservation_order)
    return {
        "read_only": True,
        "evaluated_at_ns": evaluated_at_ns,
        "lifecycle_store_head_entry_hash": snapshot.store_head_entry_hash,
        "active_policy": active_policy,
        "capacity": _capacity(capacity),
        "strategy_reservations": reservations,
        "non_authority": dict(NON_AUTHORITY),
    }


def portfolio_projection(lifecycle_path: Path | None, evaluated_at_ns: int) -> dict[str, Any]:
    """Verified portfolio policy, budget reservations and canonical capacity at one time."""
    if (
        lifecycle_path is None
        or isinstance(evaluated_at_ns, bool)
        or not isinstance(evaluated_at_ns, int)
        or evaluated_at_ns < 0
    ):
        raise OpsProjectionError()
    try:
        return _project(lifecycle_path, evaluated_at_ns)
    except OpsProjectionError:
        raise
    except Exception:
        raise OpsProjectionError() from None
