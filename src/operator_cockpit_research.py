"""S10-CC-RESEARCH-01 read-only StrategyLifecycle + Hermes research projection.

Pure, bounded projection adapter for the local Control Center. It reads canonical
state only through the two verified loaders:

* ``load_strategy_lifecycle_store`` -> verified ``StrategyLifecycleSnapshot``;
* ``load_hermes_strategy_manager_store`` -> verified Hermes strategy-manager history.

It never opens a store itself, never appends or initializes, never fabricates a
snapshot, never invokes Hermes and never performs network or file writes. A Hermes
assessment is a canonical SOFT strategy judgment: the derived context status
(CURRENT / STALE_CONTEXT / TARGET_MISSING) is display-only and is never approval,
portfolio authority, execution feasibility, Gate-C eligibility or live permission.
No Alpha Factory lineage is read or inferred here (S10-CC-RESEARCH-02).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, TypeVar

from src.research_runtime.hermes_controlled_runtime.strategy_manager import (
    HermesStrategyAssessment,
    HermesStrategyManagerStoreSnapshot,
    HermesStrategyRunRecord,
    load_hermes_strategy_manager_store,
    strategy_lifecycle_context_fingerprint,
)
from src.strategy_lifecycle import (
    StrategyLifecycleSnapshot,
    StrategyRestrictionReceipt,
    StrategyRiskAllocation,
    StrategyVersion,
    load_strategy_lifecycle_store,
)
from src.strategy_lifecycle.models import parse_adaptive_bounds, parse_strategy_spec


STRATEGY_VERSION_ID_RE = re.compile(r"^strategyversion:sha256:[0-9a-f]{64}$")
ASSESSMENT_ID_RE = re.compile(r"^hermesstrategyassessment:sha256:[0-9a-f]{64}$")
CONTEXT_STATUSES = ("CURRENT", "STALE_CONTEXT", "TARGET_MISSING")
MAX_LINEAGE_DEPTH = 1_024
_NON_AUTHORITY_FLAGS = (
    "canonical_soft_strategy_decision",
    "no_credential_authority",
    "no_portfolio_policy_authority",
    "no_hard_risk_override",
    "no_paper_execution_authority",
    "no_order_authority",
    "no_execution_authority",
    "no_live_authority",
)

_T = TypeVar("_T")


class ResearchProjectionError(Exception):
    """Closed, payload-free projection failure (SOURCE_UNAVAILABLE or NOT_FOUND)."""

    def __init__(self, code: str):
        if code not in ("SOURCE_UNAVAILABLE", "NOT_FOUND"):
            code = "SOURCE_UNAVAILABLE"
        super().__init__(code)
        self.code = code


def _unavailable() -> ResearchProjectionError:
    return ResearchProjectionError("SOURCE_UNAVAILABLE")


def _guarded(action: Callable[[], _T]) -> _T:
    """Map every non-closed failure (loader, tamper, parse, internal) to SOURCE_UNAVAILABLE."""
    try:
        return action()
    except ResearchProjectionError:
        raise
    except Exception:
        raise _unavailable() from None


# ---------------------------------------------------------------------------
# Verified source loading
# ---------------------------------------------------------------------------


def load_lifecycle(path: Path | None) -> StrategyLifecycleSnapshot:
    if path is None:
        raise _unavailable()

    def action() -> StrategyLifecycleSnapshot:
        result = load_strategy_lifecycle_store(path)
        if not result.is_valid or not isinstance(result.snapshot, StrategyLifecycleSnapshot):
            raise _unavailable()
        return result.snapshot

    return _guarded(action)


def load_hermes(path: Path | None) -> HermesStrategyManagerStoreSnapshot:
    if path is None:
        raise _unavailable()

    def action() -> HermesStrategyManagerStoreSnapshot:
        snapshot = load_hermes_strategy_manager_store(path)
        if not isinstance(snapshot, HermesStrategyManagerStoreSnapshot):
            raise _unavailable()
        return snapshot

    return _guarded(action)


def _optional_hermes(path: Path | None) -> HermesStrategyManagerStoreSnapshot | None:
    """Hermes is never a prerequisite for viewing canonical lifecycle state."""
    try:
        return load_hermes(path)
    except ResearchProjectionError:
        return None


# ---------------------------------------------------------------------------
# Shared projections
# ---------------------------------------------------------------------------


def context_status(
    lifecycle: StrategyLifecycleSnapshot, assessment: HermesStrategyAssessment
) -> str:
    """Display-only currentness of a soft assessment against current lifecycle context."""
    if lifecycle.version_by_id(assessment.strategy_version_id) is None:
        return "TARGET_MISSING"
    current = strategy_lifecycle_context_fingerprint(lifecycle, assessment.strategy_version_id)
    if assessment.strategy_lifecycle_context_sha256 == current:
        return "CURRENT"
    return "STALE_CONTEXT"


def _allocation(allocation: StrategyRiskAllocation | None) -> dict[str, Any] | None:
    if allocation is None:
        return None
    return {
        "allocation_id": allocation.allocation_id,
        "policy_id": allocation.policy_id,
        "risk_band": allocation.risk_band,
        "active_budget_usd": allocation.active_budget_usd,
        "allocation_basis": allocation.allocation_basis,
        "valid_from_ns": allocation.valid_from_ns,
        "valid_until_ns": allocation.valid_until_ns,
    }


def _restriction(receipt: StrategyRestrictionReceipt) -> dict[str, Any]:
    return {
        "restriction_receipt_id": receipt.restriction_receipt_id,
        "restriction_key": receipt.restriction_key,
        "restriction_kind": receipt.restriction_kind,
        "max_active_budget_usd": receipt.max_active_budget_usd,
        "created_time_ns": receipt.created_time_ns,
    }


def _assessment_by_id(
    hermes: HermesStrategyManagerStoreSnapshot, assessment_id: str
) -> HermesStrategyAssessment | None:
    for assessment in hermes.assessments:
        if assessment.assessment_id == assessment_id:
            return assessment
    return None


def _run_by_id(
    hermes: HermesStrategyManagerStoreSnapshot, run_record_id: str
) -> HermesStrategyRunRecord:
    for run in hermes.run_records:
        if run.run_record_id == run_record_id:
            return run
    # Impossible in a verified snapshot: fail closed.
    raise _unavailable()


def _latest_compact(
    lifecycle: StrategyLifecycleSnapshot,
    hermes: HermesStrategyManagerStoreSnapshot | None,
    strategy_version_id: str,
) -> dict[str, Any] | None:
    if hermes is None:
        return None
    latest_id = hermes.latest_assessment_id(strategy_version_id)
    if latest_id is None:
        return None
    assessment = _assessment_by_id(hermes, latest_id)
    if assessment is None:
        raise _unavailable()
    return {
        "assessment_id": assessment.assessment_id,
        "information_cutoff": assessment.information_cutoff,
        "confidence_label": assessment.confidence_label,
        "lifecycle_action": assessment.lifecycle_action,
        "recommended_health_state": assessment.recommended_health_state,
        "risk_direction": assessment.risk_direction,
        "target_risk_band": assessment.target_risk_band,
        "context_status": context_status(lifecycle, assessment),
    }


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


def _strategy_summary(
    lifecycle: StrategyLifecycleSnapshot,
    hermes: HermesStrategyManagerStoreSnapshot | None,
    version: StrategyVersion,
) -> dict[str, Any]:
    sid = version.strategy_version_id
    return {
        "strategy_version_id": sid,
        "strategy_family_id": version.strategy_family_id,
        "parent_strategy_version_id": version.parent_strategy_version_id,
        "strategy_label": version.strategy_label,
        "evidence_posture": version.evidence_posture,
        "adaptation_class": version.adaptation_class,
        "created_time_ns": version.created_time_ns,
        "current_health_state": lifecycle.health_of(sid),
        "current_allocation": _allocation(lifecycle.allocation_of(sid)),
        "active_restriction_count": len(lifecycle.restrictions_of(sid)),
        "evidence_ref_count": len(version.evidence_refs),
        "latest_hermes_assessment": _latest_compact(lifecycle, hermes, sid),
    }


def _lineage(lifecycle: StrategyLifecycleSnapshot, version: StrategyVersion) -> list[str]:
    """Exact parent ids root -> target within one family; bounded, fails closed."""
    chain = [version.strategy_version_id]
    seen = {version.strategy_version_id}
    current = version
    bound = min(MAX_LINEAGE_DEPTH, len(lifecycle.strategy_versions))
    while current.parent_strategy_version_id is not None:
        parent_id = current.parent_strategy_version_id
        if parent_id in seen or len(chain) >= bound:
            raise _unavailable()
        parent = lifecycle.version_by_id(parent_id)
        if parent is None or parent.strategy_family_id != version.strategy_family_id:
            raise _unavailable()
        chain.append(parent_id)
        seen.add(parent_id)
        current = parent
    chain.reverse()
    return chain


def strategy_list(
    lifecycle_path: Path | None, hermes_path: Path | None, limit: int
) -> list[dict[str, Any]]:
    lifecycle = load_lifecycle(lifecycle_path)
    hermes = _optional_hermes(hermes_path)

    def action() -> list[dict[str, Any]]:
        ordered = sorted(
            lifecycle.strategy_versions,
            key=lambda version: (-version.created_time_ns, version.strategy_version_id),
        )
        return [_strategy_summary(lifecycle, hermes, version) for version in ordered[:limit]]

    return _guarded(action)


def strategy_detail(
    lifecycle_path: Path | None, hermes_path: Path | None, strategy_version_id: str
) -> dict[str, Any]:
    lifecycle = load_lifecycle(lifecycle_path)
    version = lifecycle.version_by_id(strategy_version_id)
    if version is None:
        raise ResearchProjectionError("NOT_FOUND")
    hermes = _optional_hermes(hermes_path)

    def action() -> dict[str, Any]:
        sid = version.strategy_version_id
        family = next(
            (
                item
                for item in lifecycle.families
                if item.strategy_family_id == version.strategy_family_id
            ),
            None,
        )
        if family is None:
            raise _unavailable()
        spec = parse_strategy_spec(version.strategy_spec_json)
        bounds = parse_adaptive_bounds(version.adaptive_bounds_json, spec)
        return {
            "strategy_version_id": sid,
            "strategy_family_id": version.strategy_family_id,
            "parent_strategy_version_id": version.parent_strategy_version_id,
            "strategy_label": version.strategy_label,
            "evidence_posture": version.evidence_posture,
            "adaptation_class": version.adaptation_class,
            "strategy_code_identity": version.strategy_code_identity,
            "created_time_ns": version.created_time_ns,
            "creation_provenance": version.creation_provenance,
            "evidence_refs": list(version.evidence_refs),
            "family": {
                "strategy_family_id": family.strategy_family_id,
                "family_key": family.family_key,
                "family_label": family.family_label,
            },
            "lineage_strategy_version_ids": _lineage(lifecycle, version),
            "strategy_definition": {
                "thesis": spec["thesis"],
                "universe": spec["universe"],
                "entry_rule": spec["entry_rule"],
                "exit_rule": spec["exit_rule"],
                "execution_rule": spec["execution_rule"],
                "parameters": spec["parameters"],
            },
            "adaptive_bounds": bounds,
            "current_state": {
                "health_state": lifecycle.health_of(sid),
                "active_policy_id": lifecycle.active_policy_id,
                "allocation": _allocation(lifecycle.allocation_of(sid)),
                "active_restrictions": [
                    _restriction(receipt) for receipt in lifecycle.restrictions_of(sid)
                ],
                "strategy_lifecycle_context_sha256": strategy_lifecycle_context_fingerprint(
                    lifecycle, sid
                ),
            },
            "latest_hermes_assessment": _latest_compact(lifecycle, hermes, sid),
        }

    return _guarded(action)


# ---------------------------------------------------------------------------
# Hermes soft assessments
# ---------------------------------------------------------------------------


def _assessment_item(
    lifecycle: StrategyLifecycleSnapshot, assessment: HermesStrategyAssessment
) -> dict[str, Any]:
    return {
        "assessment_id": assessment.assessment_id,
        "strategy_version_id": assessment.strategy_version_id,
        "strategy_family_id": assessment.strategy_family_id,
        "predecessor_assessment_id": assessment.predecessor_assessment_id,
        "information_cutoff": assessment.information_cutoff,
        "decision_time_ns": assessment.decision_time_ns,
        "trigger": assessment.trigger,
        "confidence_label": assessment.confidence_label,
        "assessment_summary": assessment.assessment_summary,
        "lifecycle_action": assessment.lifecycle_action,
        "recommended_health_state": assessment.recommended_health_state,
        "risk_direction": assessment.risk_direction,
        "target_risk_band": assessment.target_risk_band,
        "context_status": context_status(lifecycle, assessment),
        "canonical_soft_strategy_decision": assessment.canonical_soft_strategy_decision is True,
    }


def assessment_list(
    lifecycle_path: Path | None, hermes_path: Path | None, limit: int
) -> list[dict[str, Any]]:
    # Context status needs the current lifecycle snapshot; both sources are required.
    hermes = load_hermes(hermes_path)
    lifecycle = load_lifecycle(lifecycle_path)

    def action() -> list[dict[str, Any]]:
        ordered = sorted(
            hermes.assessments,
            key=lambda item: (-item.decision_time_ns, item.assessment_id),
        )
        return [_assessment_item(lifecycle, item) for item in ordered[:limit]]

    return _guarded(action)


def assessment_detail(
    lifecycle_path: Path | None, hermes_path: Path | None, assessment_id: str
) -> dict[str, Any]:
    hermes = load_hermes(hermes_path)
    lifecycle = load_lifecycle(lifecycle_path)
    assessment = _assessment_by_id(hermes, assessment_id)
    if assessment is None:
        raise ResearchProjectionError("NOT_FOUND")

    def action() -> dict[str, Any]:
        run = _run_by_id(hermes, assessment.run_record_id)
        item = _assessment_item(lifecycle, assessment)
        item.update(
            {
                "run_record_id": assessment.run_record_id,
                "runtime_request_id": assessment.runtime_request_id,
                "runtime_receipt_id": assessment.runtime_receipt_id,
                "subject_refs": list(assessment.subject_refs),
                "input_evidence_refs": list(assessment.input_evidence_refs),
                "evidence_for": list(assessment.evidence_for),
                "evidence_against": list(assessment.evidence_against),
                "uncertainties": list(assessment.uncertainties),
                "known_missing_data": list(assessment.known_missing_data),
                "falsification_checks_performed": list(
                    assessment.falsification_checks_performed
                ),
                "limitations": list(assessment.limitations),
                "what_would_change_the_conclusion": list(
                    assessment.what_would_change_the_conclusion
                ),
                "suggested_next_research_steps": list(
                    assessment.suggested_next_research_steps
                ),
                "adaptation_recommendation": assessment.adaptation_recommendation(),
                "strategy_lifecycle_context_sha256": assessment.strategy_lifecycle_context_sha256,
                "lifecycle_store_head_entry_hash": assessment.lifecycle_store_head_entry_hash,
                "active_policy_id": assessment.active_policy_id,
                "run": {
                    "provider_label": run.provider_label,
                    "model_label": run.model_label,
                    "hermes_version": run.hermes_version,
                    "terminal_status": run.terminal_status,
                    "start_utc": run.start_utc,
                    "end_utc": run.end_utc,
                    "estimated_cost_usd": run.estimated_cost_usd,
                    "cost_status": run.cost_status,
                    "cost_source": run.cost_source,
                },
                "non_authority": {
                    flag: getattr(assessment, flag) is True for flag in _NON_AUTHORITY_FLAGS
                },
            }
        )
        if not all(item["non_authority"].values()):
            raise _unavailable()
        return item

    return _guarded(action)
