"""S10-CC-RESEARCH-01/02 read-only Control Center research projections.

Pure, bounded projection adapter for the local Control Center. It reads canonical
state only through four verified loaders:

* ``load_strategy_lifecycle_store`` -> verified ``StrategyLifecycleSnapshot``;
* ``load_hermes_strategy_manager_store`` -> verified Hermes strategy-manager history;
* ``load_and_verify_alpha_factory_registry`` -> verified Alpha Factory research memory;
* ``load_and_verify_alpha_discovery_registry`` -> verified Alpha Discovery evidence.

It never opens a store itself, never appends or initializes, never fabricates a
snapshot, never invokes Hermes and never performs network or file writes. A Hermes
assessment is a canonical SOFT strategy judgment: the derived context status
(CURRENT / STALE_CONTEXT / TARGET_MISSING) is display-only and is never approval,
portfolio authority, execution feasibility, Gate-C eligibility or live permission.

Alpha research memory and Alpha Discovery priority are research records only. A
RESEARCH_SUPPORTIVE episode is never qualification, executable edge or trading
authority; a discovery lane is research allocation, never trade priority. The only
Discovery -> Alpha relationship resolved here is the triage record's stored
``matched_*`` ids, and only against an Alpha snapshot whose head equals the bound
head exactly. Alpha records are never joined to StrategyLifecycle or Hermes records.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, TypeVar

from src.data_layer.analytical_research.alpha_discovery import (
    AlphaDiscoveryPolicy,
    AlphaResearchQueueSnapshot,
    AlphaUniverseSnapshot,
    MarketTriageDecision,
    MaterialChangeEvent,
)
from src.data_layer.analytical_research.alpha_discovery_registry import (
    AlphaDiscoveryRegistrySnapshot,
    load_and_verify_alpha_discovery_registry,
)
from src.data_layer.analytical_research.alpha_factory import (
    HypothesisFamily,
    OpportunityCandidate,
    ResearchEpisode,
    ResearchSourceReference,
)
from src.data_layer.analytical_research.alpha_factory_registry import (
    AlphaFactoryRegistrySnapshot,
    load_and_verify_alpha_factory_registry,
)
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
ALPHA_CANDIDATE_ID_RE = re.compile(r"^alphacandidate:sha256:[0-9a-f]{64}$")
ALPHA_EPISODE_ID_RE = re.compile(r"^alphaepisode:sha256:[0-9a-f]{64}$")
ALPHA_TRIAGE_ID_RE = re.compile(r"^alphatriage:sha256:[0-9a-f]{64}$")
ALPHA_RESOLUTION_STATUSES = ("NOT_BOUND", "UNAVAILABLE", "HEAD_MISMATCH", "RESOLVED")
DISCOVERY_LANES = (
    ("core", "core_triage_ids"),
    ("exploration", "exploration_triage_ids"),
    ("audit", "audit_triage_ids"),
    ("deferred", "deferred_triage_ids"),
    ("skipped_ineligible", "skipped_ineligible_triage_ids"),
    ("skipped_capacity", "skipped_capacity_triage_ids"),
)
_ALPHA_AUTHORITY_FLAGS = (
    "advisory_only",
    "no_execution_authority",
    "no_strategy_authority",
    "no_qualification_authority",
)
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


# ---------------------------------------------------------------------------
# S10-CC-RESEARCH-02: Alpha Factory research memory (verified loader only)
# ---------------------------------------------------------------------------


def load_alpha_factory(path: Path | None) -> AlphaFactoryRegistrySnapshot:
    if path is None:
        raise _unavailable()

    def action() -> AlphaFactoryRegistrySnapshot:
        result = load_and_verify_alpha_factory_registry(path)
        if not result.is_valid or not isinstance(result.snapshot, AlphaFactoryRegistrySnapshot):
            raise _unavailable()
        return result.snapshot

    return _guarded(action)


def load_alpha_discovery(path: Path | None) -> AlphaDiscoveryRegistrySnapshot:
    if path is None:
        raise _unavailable()

    def action() -> AlphaDiscoveryRegistrySnapshot:
        result = load_and_verify_alpha_discovery_registry(path)
        if not result.is_valid or not isinstance(result.snapshot, AlphaDiscoveryRegistrySnapshot):
            raise _unavailable()
        return result.snapshot

    return _guarded(action)


class _AlphaIndex:
    """Same-snapshot lookup tables; insertion order is canonical registry order."""

    def __init__(self, snapshot: AlphaFactoryRegistrySnapshot):
        self.snapshot = snapshot
        self.sequence: dict[str, int] = {}
        self.sources: dict[str, ResearchSourceReference] = {}
        self.candidates: dict[str, OpportunityCandidate] = {}
        self.families: dict[str, HypothesisFamily] = {}
        self.episodes: dict[str, ResearchEpisode] = {}
        tables: tuple[tuple[type, dict[str, Any]], ...] = (
            (ResearchSourceReference, self.sources),
            (OpportunityCandidate, self.candidates),
            (HypothesisFamily, self.families),
            (ResearchEpisode, self.episodes),
        )
        for entry in snapshot.entries:
            for record_type, table in tables:
                if isinstance(entry.record, record_type):
                    table[entry.record_id] = entry.record
                    break
            else:
                raise _unavailable()
            self.sequence[entry.record_id] = entry.sequence_number

    def episodes_of(self, candidate_id: str) -> list[ResearchEpisode]:
        return [item for item in self.episodes.values() if item.candidate_id == candidate_id]


def _alpha_index(path: Path | None) -> _AlphaIndex:
    snapshot = load_alpha_factory(path)
    return _guarded(lambda: _AlphaIndex(snapshot))


def _optional_alpha_index(path: Path | None) -> _AlphaIndex | None:
    """Alpha memory is never a prerequisite for viewing Discovery evidence."""
    try:
        return _alpha_index(path)
    except ResearchProjectionError:
        return None


def _resolve(table: dict[str, _T], record_id: str) -> _T:
    record = table.get(record_id)
    if record is None:
        # Impossible inside one verified snapshot: fail closed.
        raise _unavailable()
    return record


def _alpha_flags(record: object) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for name in _ALPHA_AUTHORITY_FLAGS:
        if hasattr(record, name):
            if getattr(record, name) is not True:
                raise _unavailable()
            flags[name] = True
    return flags


def _research_leaf_ids(episodes: list[ResearchEpisode]) -> set[str]:
    """Research leaves per exact (candidate, family) lineage; several may coexist."""
    referenced: set[tuple[str, str, str]] = set()
    for episode in episodes:
        for ref in (episode.predecessor_episode_id, episode.reopened_episode_id):
            if ref is not None:
                referenced.add((episode.candidate_id, episode.hypothesis_family_id, ref))
    return {
        episode.research_episode_id
        for episode in episodes
        if (episode.candidate_id, episode.hypothesis_family_id, episode.research_episode_id)
        not in referenced
    }


def _source_reference(source: ResearchSourceReference) -> dict[str, Any]:
    if source.public_research_only is not True:
        raise _unavailable()
    return {
        "source_reference_id": source.source_reference_id,
        "source_kind": source.source_kind,
        "source_class": source.source_class,
        "source_locator": source.source_locator,
        "title": source.title,
        "observed_at": source.observed_at,
        "content_sha256": source.content_sha256,
        "provenance": source.provenance,
        "public_research_only": True,
        **_alpha_flags(source),
    }


def _candidate_summary(index: _AlphaIndex, candidate: OpportunityCandidate) -> dict[str, Any]:
    episodes = index.episodes_of(candidate.candidate_id)
    return {
        "sequence_number": index.sequence[candidate.candidate_id],
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "title": candidate.title,
        "research_question": candidate.research_question,
        "subject_refs": list(candidate.subject_refs),
        "evidence_lanes": list(candidate.evidence_lanes),
        "is_multi_lane": len(candidate.evidence_lanes) >= 2,
        "scope_key": candidate.scope_key,
        "mechanism_hint": candidate.mechanism_hint,
        "novelty_fingerprint": candidate.novelty_fingerprint,
        "human_review_required": candidate.human_review_required,
        "family_count": len({episode.hypothesis_family_id for episode in episodes}),
        "episode_count": len(episodes),
        "leaf_episode_count": len(_research_leaf_ids(episodes)),
    }


def _candidate_record(candidate: OpportunityCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "title": candidate.title,
        "research_question": candidate.research_question,
        "thesis": candidate.thesis,
        "subject_refs": list(candidate.subject_refs),
        "evidence_lanes": list(candidate.evidence_lanes),
        "is_multi_lane": len(candidate.evidence_lanes) >= 2,
        "scope_key": candidate.scope_key,
        "mechanism_hint": candidate.mechanism_hint,
        "novelty_dimensions_json": candidate.novelty_dimensions_json,
        "novelty_fingerprint": candidate.novelty_fingerprint,
        "discovery_provenance": candidate.discovery_provenance,
        "human_review_required": candidate.human_review_required,
        **_alpha_flags(candidate),
    }


def _family_record(
    index: _AlphaIndex, family: HypothesisFamily, episodes: list[ResearchEpisode]
) -> dict[str, Any]:
    lineage = [item for item in episodes if item.hypothesis_family_id == family.hypothesis_family_id]
    leaves = _research_leaf_ids(lineage)
    return {
        "sequence_number": index.sequence[family.hypothesis_family_id],
        "hypothesis_family_id": family.hypothesis_family_id,
        "family_version": family.family_version,
        "family_name": family.family_name,
        "mechanism_key": family.mechanism_key,
        "mechanism_dimensions_json": family.mechanism_dimensions_json,
        "mechanism_fingerprint": family.mechanism_fingerprint,
        "falsifiable_theme": family.falsifiable_theme,
        "predecessor_family_id": family.predecessor_family_id,
        "creation_provenance": family.creation_provenance,
        "human_review_required": family.human_review_required,
        **_alpha_flags(family),
        "episode_count": len(lineage),
        "leaf_episode_ids": [
            item.research_episode_id for item in lineage if item.research_episode_id in leaves
        ],
    }


def _episode_summary(index: _AlphaIndex, episode: ResearchEpisode) -> dict[str, Any]:
    return {
        "sequence_number": index.sequence[episode.research_episode_id],
        "research_episode_id": episode.research_episode_id,
        "hypothesis_family_id": episode.hypothesis_family_id,
        "predecessor_episode_id": episode.predecessor_episode_id,
        "reopened_episode_id": episode.reopened_episode_id,
        "result_state": episode.result_state,
        "confidence_label": episode.confidence_label,
        "evidence_lanes": list(episode.evidence_lanes),
        "research_as_of": episode.research_as_of,
        "producer_type": episode.producer_type,
        "human_review_required": episode.human_review_required,
    }


def alpha_memory_summary(path: Path | None) -> dict[str, Any]:
    index = _alpha_index(path)

    def action() -> dict[str, Any]:
        snapshot = index.snapshot
        return {
            "head_entry_hash": snapshot.head_entry_hash,
            "total_rows": snapshot.total_rows,
            "total_payload_bytes": snapshot.total_payload_bytes,
            "record_counts": {
                "research_source_references": len(index.sources),
                "opportunity_candidates": len(index.candidates),
                "hypothesis_families": len(index.families),
                "research_episodes": len(index.episodes),
            },
            **_alpha_flags(snapshot),
        }

    return _guarded(action)


def alpha_candidate_list(path: Path | None, limit: int) -> list[dict[str, Any]]:
    index = _alpha_index(path)

    def action() -> list[dict[str, Any]]:
        # Registry sequence is canonical append order, not a timestamp.
        ordered = sorted(
            index.candidates.values(),
            key=lambda item: (-index.sequence[item.candidate_id], item.candidate_id),
        )
        return [_candidate_summary(index, item) for item in ordered[:limit]]

    return _guarded(action)


def alpha_candidate_detail(path: Path | None, candidate_id: str) -> dict[str, Any]:
    index = _alpha_index(path)
    candidate = index.candidates.get(candidate_id)
    if candidate is None:
        raise ResearchProjectionError("NOT_FOUND")

    def action() -> dict[str, Any]:
        episodes = index.episodes_of(candidate_id)
        leaves = _research_leaf_ids(episodes)
        family_ids = sorted(
            {item.hypothesis_family_id for item in episodes},
            key=lambda family_id: (index.sequence[family_id], family_id),
        )
        families = [
            _family_record(index, _resolve(index.families, family_id), episodes)
            for family_id in family_ids
        ]
        source_ids = sorted(
            {source_id for item in episodes for source_id in item.source_reference_ids},
            key=lambda source_id: (index.sequence.get(source_id, -1), source_id),
        )
        evidence_refs: list[str] = []
        for item in episodes:
            for ref in item.deterministic_evidence_refs:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
        return {
            "candidate": _candidate_record(candidate),
            "hypothesis_families": families,
            "research_episodes": [_episode_summary(index, item) for item in episodes],
            "source_references": [
                _source_reference(_resolve(index.sources, source_id)) for source_id in source_ids
            ],
            "deterministic_evidence_refs": evidence_refs,
            "lineage_summary": {
                "family_count": len(families),
                "episode_count": len(episodes),
                "leaf_episode_count": len(leaves),
                "leaf_episode_ids": [
                    item.research_episode_id for item in episodes if item.research_episode_id in leaves
                ],
            },
        }

    return _guarded(action)


def alpha_episode_detail(path: Path | None, research_episode_id: str) -> dict[str, Any]:
    index = _alpha_index(path)
    episode = index.episodes.get(research_episode_id)
    if episode is None:
        raise ResearchProjectionError("NOT_FOUND")

    def action() -> dict[str, Any]:
        return {
            "research_episode_id": episode.research_episode_id,
            "episode_version": episode.episode_version,
            "candidate_id": episode.candidate_id,
            "hypothesis_family_id": episode.hypothesis_family_id,
            "predecessor_episode_id": episode.predecessor_episode_id,
            "reopened_episode_id": episode.reopened_episode_id,
            "result_state": episode.result_state,
            "confidence_label": episode.confidence_label,
            "evidence_lanes": list(episode.evidence_lanes),
            "is_multi_lane": len(episode.evidence_lanes) >= 2,
            "exact_scope_json": episode.exact_scope_json,
            "evidence_regime_json": episode.evidence_regime_json,
            "research_question": episode.research_question,
            "thesis": episode.thesis,
            "tested_assumptions": list(episode.tested_assumptions),
            "evidence_for": list(episode.evidence_for),
            "evidence_against": list(episode.evidence_against),
            "uncertainties": list(episode.uncertainties),
            "known_missing_data": list(episode.known_missing_data),
            "falsification_checks_performed": list(episode.falsification_checks_performed),
            "limitations": list(episode.limitations),
            "what_would_change_the_conclusion": list(episode.what_would_change_the_conclusion),
            "suggested_next_research_steps": list(episode.suggested_next_research_steps),
            "source_reference_ids": list(episode.source_reference_ids),
            "source_references": [
                _source_reference(_resolve(index.sources, source_id))
                for source_id in episode.source_reference_ids
            ],
            "deterministic_evidence_refs": list(episode.deterministic_evidence_refs),
            "material_change_basis": list(episode.material_change_basis),
            "producer_type": episode.producer_type,
            "producer_version": episode.producer_version,
            "producer_receipt_ref": episode.producer_receipt_ref,
            "research_as_of": episode.research_as_of,
            "creation_provenance": episode.creation_provenance,
            "human_review_required": episode.human_review_required,
            **_alpha_flags(episode),
        }

    return _guarded(action)


# ---------------------------------------------------------------------------
# S10-CC-RESEARCH-02: Alpha Discovery evidence (verified loader only)
# ---------------------------------------------------------------------------


class _DiscoveryIndex:
    """Same-snapshot record lookup; every cross reference resolves from one snapshot."""

    def __init__(self, snapshot: AlphaDiscoveryRegistrySnapshot):
        self.snapshot = snapshot
        self.records: dict[str, object] = {}
        for entry in snapshot.entries:
            self.records[entry.record_id] = entry.record

    def get(self, record_id: str, record_type: type[_T]) -> _T:
        record = self.records.get(record_id)
        if not isinstance(record, record_type):
            raise _unavailable()
        return record


def _discovery_index(path: Path | None) -> _DiscoveryIndex:
    snapshot = load_alpha_discovery(path)
    return _guarded(lambda: _DiscoveryIndex(snapshot))


def _triage_summary(triage: MarketTriageDecision) -> dict[str, Any]:
    return {
        "market_triage_decision_id": triage.market_triage_decision_id,
        "market_id": triage.market_id,
        "event_id": triage.event_id,
        "category": triage.category,
        "eligibility": triage.eligibility,
        "priority_class": triage.priority_class,
        "reopen_disposition": triage.reopen_disposition,
        "readiness": triage.readiness,
        "reason_codes": list(triage.reason_codes),
        "material_change_event_id": triage.material_change_event_id,
        "newly_observed_locally": triage.newly_observed_locally,
        "final_disposition": triage.final_disposition,
        "selected_lane": triage.selected_lane,
        "analysis_temporal_mode": triage.analysis_temporal_mode,
        "alpha_memory_temporal_posture": triage.alpha_memory_temporal_posture,
        "alpha_registry_head_entry_hash": triage.alpha_registry_head_entry_hash,
        "matched_candidate_ids": list(triage.matched_candidate_ids),
        "matched_hypothesis_family_ids": list(triage.matched_hypothesis_family_ids),
        "matched_research_episode_ids": list(triage.matched_research_episode_ids),
        "coverage": [
            {"research_archetype": archetype, "coverage_state": state}
            for archetype, state in triage.coverage
        ],
    }


def _triage_detail(triage: MarketTriageDecision) -> dict[str, Any]:
    detail = _triage_summary(triage)
    detail.update(
        {
            "policy_id": triage.policy_id,
            "universe_id": triage.universe_id,
            "comparison_prior_universe_id": triage.comparison_prior_universe_id,
            "capture_requests": [
                {
                    "request_type": request.request_type,
                    "market_id": request.market_id,
                    "token_id": request.token_id,
                    "universe_id": request.universe_id,
                    "policy_id": request.policy_id,
                    "comparison_prior_universe_id": request.comparison_prior_universe_id,
                    "reason_code": request.reason_code,
                    "priority_class": request.priority_class,
                    "pre_allocation_semantic_key": request.pre_allocation_semantic_key,
                }
                for request in triage.capture_requests
            ],
            "audit_digest": triage.audit_digest,
            "audit_eligible_pool_size": triage.audit_eligible_pool_size,
            "audit_selection_fraction_numerator": triage.audit_selection_fraction_numerator,
            "audit_selection_fraction_denominator": triage.audit_selection_fraction_denominator,
            "historical_alpha_memory_available": triage.historical_alpha_memory_available,
            "historical_selection_replay_valid": triage.historical_selection_replay_valid,
            "historical_replay_valid_for_alpha_memory": triage.historical_replay_valid_for_alpha_memory,
            **_alpha_flags(triage),
        }
    )
    return detail


def _policy_summary(policy: AlphaDiscoveryPolicy) -> dict[str, Any]:
    # audit_seed is deliberately omitted from the presentation DTO.
    return {
        "alpha_discovery_policy_id": policy.alpha_discovery_policy_id,
        "policy_version": policy.policy_version,
        "eligible_market_statuses": list(policy.eligible_market_statuses),
        "metadata_freshness_seconds": policy.metadata_freshness_seconds,
        "order_book_freshness_seconds": policy.order_book_freshness_seconds,
        "resolution_rule_freshness_seconds": policy.resolution_rule_freshness_seconds,
        "queue_capacity": policy.queue_capacity,
        "exploration_slots": policy.exploration_slots,
        "audit_slots": policy.audit_slots,
        "max_per_category": policy.max_per_category,
        "research_archetype_taxonomy_version": policy.research_archetype_taxonomy_version,
    }


def _universe_summary(universe: AlphaUniverseSnapshot) -> dict[str, Any]:
    return {
        "alpha_universe_snapshot_id": universe.alpha_universe_snapshot_id,
        "as_of": universe.as_of,
        "cutoff_mode": universe.cutoff_mode,
        "query_engine_version": universe.query_engine_version,
        "query_parameter_set_id": universe.query_parameter_set_id,
        "coverage_scope": universe.coverage_scope,
        "external_universe_completeness": universe.external_universe_completeness,
        "market_count": len(universe.markets),
    }


def _queue_summary(queue: AlphaResearchQueueSnapshot) -> dict[str, Any]:
    return {
        "alpha_research_queue_snapshot_id": queue.alpha_research_queue_snapshot_id,
        "policy_id": queue.policy_id,
        "universe_id": queue.universe_id,
        "comparison_prior_universe_id": queue.comparison_prior_universe_id,
        "analysis_temporal_mode": queue.analysis_temporal_mode,
        "alpha_memory_temporal_posture": queue.alpha_memory_temporal_posture,
        "alpha_registry_head_entry_hash": queue.alpha_registry_head_entry_hash,
        "historical_alpha_memory_available": queue.historical_alpha_memory_available,
        "historical_selection_replay_valid": queue.historical_selection_replay_valid,
        "queue_capacity": queue.queue_capacity,
        "configured_exploration_slots": queue.configured_exploration_slots,
        "configured_audit_slots": queue.configured_audit_slots,
        "exploration_selected_count": queue.exploration_selected_count,
        "audit_selected_count": queue.audit_selected_count,
        "unused_exploration_slots": queue.unused_exploration_slots,
        "unused_audit_slots": queue.unused_audit_slots,
        "unused_capacity_reason_codes": list(queue.unused_capacity_reason_codes),
        "max_per_category": queue.max_per_category,
        "prior_only_market_ids": list(queue.prior_only_market_ids),
        **_alpha_flags(queue),
    }


def alpha_discovery_queue(path: Path | None) -> dict[str, Any]:
    index = _discovery_index(path)
    queues = [
        entry for entry in index.snapshot.entries
        if isinstance(entry.record, AlphaResearchQueueSnapshot)
    ]
    if not queues:
        raise ResearchProjectionError("NOT_FOUND")

    def action() -> dict[str, Any]:
        # Latest recorded queue = greatest registry sequence; never a wall clock.
        latest = max(queues, key=lambda entry: entry.sequence_number)
        queue = latest.record
        return {
            "discovery_registry_head_entry_hash": index.snapshot.head_entry_hash,
            "queue_sequence_number": latest.sequence_number,
            "queue": _queue_summary(queue),
            "policy": _policy_summary(index.get(queue.policy_id, AlphaDiscoveryPolicy)),
            "universe": _universe_summary(index.get(queue.universe_id, AlphaUniverseSnapshot)),
            "lanes": {
                lane: [
                    _triage_summary(index.get(triage_id, MarketTriageDecision))
                    for triage_id in getattr(queue, field)
                ]
                for lane, field in DISCOVERY_LANES
            },
        }

    return _guarded(action)


def _universe_market(universe: AlphaUniverseSnapshot, market_id: str) -> dict[str, Any]:
    market = next((item for item in universe.markets if item.market_id == market_id), None)
    if market is None:
        raise _unavailable()
    return {
        "market_id": market.market_id,
        "event_id": market.event_id,
        "market_status": market.market_status,
        "condition_id": market.condition_id,
        "token_ids": list(market.token_ids),
        "outcome_labels": list(market.outcome_labels),
        "resolution_date": market.resolution_date,
        "category": market.category,
        "question_text": market.question_text,
        "metadata_record_version_id": market.metadata_record_version_id,
        "metadata_observed_time": market.metadata_observed_time,
        "metadata_freshness": market.metadata_freshness,
        "data_gap_codes": list(market.data_gap_codes),
        "resolution_rule_count": len(market.rules),
        "order_book_count": len(market.books),
    }


def _material_change(change: MaterialChangeEvent) -> dict[str, Any]:
    return {
        "material_change_event_id": change.material_change_event_id,
        "prior_universe_id": change.prior_universe_id,
        "current_universe_id": change.current_universe_id,
        "market_id": change.market_id,
        "hard_change_classes": list(change.hard_change_classes),
        "soft_change_classes": list(change.soft_change_classes),
        "review_only_change_classes": list(change.review_only_change_classes),
        "affected_token_ids": [
            {"change_class": change_class, "token_ids": list(token_ids)}
            for change_class, token_ids in change.affected_token_ids
        ],
        "affected_resolution_source_ids": list(change.affected_resolution_source_ids),
        "before_record_version_ids": list(change.before_record_version_ids),
        "after_record_version_ids": list(change.after_record_version_ids),
        "comparison_diagnostics": list(change.comparison_diagnostics),
        "reopen_material": change.reopen_material,
        **_alpha_flags(change),
    }


def _alpha_memory_resolution(
    triage: MarketTriageDecision, alpha_path: Path | None
) -> dict[str, Any]:
    """Exact-head, matched_*-only Alpha memory resolution for one triage record."""
    bound = triage.alpha_registry_head_entry_hash

    def outcome(status: str, candidates=(), families=(), episodes=()) -> dict[str, Any]:
        return {
            "status": status,
            "bound_alpha_registry_head_entry_hash": bound,
            "candidates": list(candidates),
            "hypothesis_families": list(families),
            "research_episodes": list(episodes),
        }

    if bound is None:
        return outcome("NOT_BOUND")
    index = _optional_alpha_index(alpha_path)
    if index is None:
        return outcome("UNAVAILABLE")
    if index.snapshot.head_entry_hash != bound:
        # Never resolve ids against a snapshot the triage was not bound to.
        return outcome("HEAD_MISMATCH")
    candidates = [
        _candidate_summary(index, _resolve(index.candidates, candidate_id))
        for candidate_id in triage.matched_candidate_ids
    ]
    families = []
    for family_id in triage.matched_hypothesis_family_ids:
        family = _resolve(index.families, family_id)
        families.append(
            {
                "sequence_number": index.sequence[family_id],
                "hypothesis_family_id": family.hypothesis_family_id,
                "family_name": family.family_name,
                "mechanism_key": family.mechanism_key,
                "falsifiable_theme": family.falsifiable_theme,
            }
        )
    episodes = [
        _episode_summary(index, _resolve(index.episodes, episode_id))
        for episode_id in triage.matched_research_episode_ids
    ]
    return outcome("RESOLVED", candidates, families, episodes)


def alpha_triage_detail(
    discovery_path: Path | None, alpha_path: Path | None, market_triage_decision_id: str
) -> dict[str, Any]:
    index = _discovery_index(discovery_path)
    triage = index.records.get(market_triage_decision_id)
    if not isinstance(triage, MarketTriageDecision):
        raise ResearchProjectionError("NOT_FOUND")

    def action() -> dict[str, Any]:
        universe = index.get(triage.universe_id, AlphaUniverseSnapshot)
        change = None
        if triage.material_change_event_id is not None:
            change = _material_change(
                index.get(triage.material_change_event_id, MaterialChangeEvent)
            )
        return {
            "triage": _triage_detail(triage),
            "universe_market": _universe_market(universe, triage.market_id),
            "material_change": change,
            "alpha_memory_resolution": _alpha_memory_resolution(triage, alpha_path),
        }

    return _guarded(action)
