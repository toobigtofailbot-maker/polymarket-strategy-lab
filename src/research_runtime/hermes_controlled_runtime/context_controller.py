"""Deterministic, non-looping orchestration for blind-first context campaigns."""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Mapping, Sequence

from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    ResearchProvenanceManifest,
)

from .context_broker import build_revealed_context_set
from .context_protocol import (
    BlindResearchArtifact,
    ContextCampaignScope,
    ContextCampaignStateRecord,
    ContextTerminalDisposition,
    EvidenceVerificationRecord,
    RevealedContextSet,
)
from .context_reconciliation import ContextEvidenceItem, reconcile_context_research
from .context_store import ContextArtifactStore
from .controller import HermesControlledRunResult, run_controlled_hermes_research
from .models import (
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
    ValidatedResearchDraft,
    build_context_research_draft_output_schema,
    build_research_run_request,
    canonical_json_bytes,
    sha256_hex,
)
from .policy import (
    DEFAULT_HERMES_INVOCATION_POLICY,
    HermesInvocationPolicy,
    build_research_envelope,
)
from .runner import HermesInvocationBackend


@dataclasses.dataclass(frozen=True)
class BlindPhaseResult:
    run_result: HermesControlledRunResult
    scope_state: ContextCampaignStateRecord
    research_state: ContextCampaignStateRecord
    blind_artifact: BlindResearchArtifact | None
    blind_frozen_state: ContextCampaignStateRecord | None


@dataclasses.dataclass(frozen=True)
class RevealPhaseResult:
    reveal_set: RevealedContextSet
    context_revealed_state: ContextCampaignStateRecord


@dataclasses.dataclass(frozen=True)
class VerificationPhaseResult:
    verification: EvidenceVerificationRecord
    terminal_disposition: ContextTerminalDisposition | None
    final_state: ContextCampaignStateRecord


def _context_request(campaign: ContextCampaignScope):
    scope = {
        "campaign_id": campaign.campaign_id,
        "scope_key": campaign.scope_key,
        "exact_scope_json": campaign.exact_scope_json,
        "exact_scope_sha256": campaign.exact_scope_sha256,
        "information_cutoff": campaign.information_cutoff,
        "subject_refs": list(campaign.subject_refs),
        "alpha_context_present": False,
    }
    return build_research_run_request({
        "schema_version": REQUEST_SCHEMA_VERSION,
        "research_question": campaign.research_question,
        "research_objective": "Blind public research within the frozen campaign scope and cutoff.",
        "research_category": "general_public",
        "public_market_context": canonical_json_bytes(scope).decode("utf-8"),
        "allowed_research_scope": list(campaign.allowed_public_research_classes),
        "required_source_types": ["official", "reference"],
        "max_sources": 20,
        "provider_label": campaign.requested_provider_label,
        "model_label": campaign.requested_model_label,
        "max_wall_seconds": 300,
        "max_output_bytes": 1_000_000,
        "max_accepted_estimated_cost_usd": Decimal("5"),
        "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    })


def run_blind_phase(
    *, campaign: ContextCampaignScope, store: ContextArtifactStore,
    backend: HermesInvocationBackend, executable_path: str = "hermes",
    policy: HermesInvocationPolicy = DEFAULT_HERMES_INVOCATION_POLICY,
    hermes_home: str | None = None,
) -> BlindPhaseResult:
    """Run exactly one caller-authorized blind invocation; accepts no Alpha input."""
    if campaign.policy_id != policy.policy_id:
        raise ValueError("CONTEXT_POLICY_MISMATCH")
    store.append(campaign)
    scope_state = ContextCampaignStateRecord.create(campaign_id=campaign.campaign_id, state="SCOPE_FROZEN")
    store.append(scope_state)
    research_state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="BLIND_RESEARCH", predecessor=scope_state,
    )
    store.append(research_state)
    request = _context_request(campaign)
    schema = build_context_research_draft_output_schema(
        expected_request_id=request.request_id, max_sources=request.max_sources,
        allowed_subject_refs=campaign.subject_refs,
    )
    contract_digest = sha256_hex(canonical_json_bytes(schema))
    context_request_id = sha256_hex(canonical_json_bytes({
        "request_id": request.request_id, "campaign_id": campaign.campaign_id,
        "context_output_contract_sha256": contract_digest,
    }))
    run = run_controlled_hermes_research(
        request, backend, executable_path=executable_path, policy=policy,
        hermes_home=hermes_home, context_mode=True,
        allowed_subject_refs=campaign.subject_refs,
    )
    if run.validated_draft is None:
        return BlindPhaseResult(run, scope_state, research_state, None, None)
    draft = run.validated_draft
    draft_fields = {
        "request_id": draft.request_id, "research_summary": draft.research_summary,
        "confidence_label": draft.confidence_label,
        "source_references": [dataclasses.asdict(item) for item in draft.source_references],
        "falsification_checks_performed": list(draft.falsification_checks_performed),
        "context_claims": [claim.identity_fields() for claim in draft.context_claims],
    }
    envelope = build_research_envelope(
        request, context_mode=True, allowed_subject_refs=campaign.subject_refs,
    )
    blind = BlindResearchArtifact.create(
        campaign=campaign, blind_request_id=context_request_id,
        prompt_envelope_sha256=envelope.envelope_digest,
        context_output_contract_sha256=contract_digest,
        validated_draft_sha256=sha256_hex(canonical_json_bytes(draft_fields)),
        source_reference_digests=[item.url_digest for item in draft.source_references],
        context_claims_sha256=sha256_hex(canonical_json_bytes({
            "context_claims": [claim.identity_fields() for claim in draft.context_claims]
        })),
        session_evidence_id=(run.session_evidence.session_evidence_id if run.session_evidence else None),
        predecessor_state_record_id=research_state.state_record_id,
    )
    # The durable append is the information barrier; state advances only afterwards.
    store.append(blind)
    frozen = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="BLIND_FROZEN", predecessor=research_state,
        caused_by_artifact_id=blind.blind_artifact_id,
    )
    store.append(frozen)
    return BlindPhaseResult(run, scope_state, research_state, blind, frozen)


def run_reveal_phase(
    *, campaign: ContextCampaignScope, blind: BlindResearchArtifact,
    blind_frozen_state: ContextCampaignStateRecord, store: ContextArtifactStore,
    registry_path: object, candidate_record_ids: Sequence[str],
    provenance_manifests: Mapping[str, ResearchProvenanceManifest],
    observability_evidence: Mapping[str, ObservabilityEvidence],
) -> RevealPhaseResult:
    eligibility_state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="REVEAL_ELIGIBILITY",
        predecessor=blind_frozen_state, caused_by_artifact_id=blind.blind_artifact_id,
    )
    store.append(eligibility_state)
    eligibility, reveal = build_revealed_context_set(
        campaign=campaign, blind_artifact=blind, blind_frozen_state=blind_frozen_state,
        store=store, registry_path=registry_path, candidate_record_ids=candidate_record_ids,
        provenance_manifests=provenance_manifests, observability_evidence=observability_evidence,
    )
    store.append(eligibility)
    store.append(reveal)
    revealed_state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="CONTEXT_REVEALED",
        predecessor=eligibility_state, caused_by_artifact_id=reveal.reveal_set_id,
    )
    store.append(revealed_state)
    return RevealPhaseResult(reveal, revealed_state)


def verify_reconciliation(
    *, campaign: ContextCampaignScope, blind: BlindResearchArtifact,
    reveal_result: RevealPhaseResult, validated_revision: ValidatedResearchDraft,
    session_evidence, store: ContextArtifactStore,
    project_evidence: Sequence[ContextEvidenceItem] = (),
    predecessor_reconciliation_id: str | None = None, revision_ordinal: int = 0,
    revision_required_state: ContextCampaignStateRecord | None = None,
) -> VerificationPhaseResult:
    predecessor_state = reveal_result.context_revealed_state
    if revision_ordinal:
        if (
            revision_required_state is None or revision_required_state.state != "REVISION_REQUIRED"
            or revision_required_state.campaign_id != campaign.campaign_id
            or not predecessor_reconciliation_id
        ):
            raise ValueError("REVISION_ARTIFACT_REQUIRED")
        predecessor_state = revision_required_state
    reconciliation_state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="RECONCILIATION",
        predecessor=predecessor_state,
        caused_by_artifact_id=(predecessor_reconciliation_id if revision_ordinal else reveal_result.reveal_set.reveal_set_id),
        revision_ordinal=revision_ordinal,
    )
    store.append(reconciliation_state)
    revision, verification = reconcile_context_research(
        campaign=campaign, blind_artifact=blind, reveal_set=reveal_result.reveal_set,
        validated_draft=validated_revision, session_evidence=session_evidence,
        context_output_contract_sha256=blind.context_output_contract_sha256,
        predecessor_state_record_id=reconciliation_state.state_record_id,
        predecessor_reconciliation_id=predecessor_reconciliation_id,
        revision_ordinal=revision_ordinal, project_evidence=project_evidence,
    )
    store.append(revision)
    evidence_state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state="EVIDENCE_VERIFY",
        predecessor=reconciliation_state, caused_by_artifact_id=revision.revision_id,
        revision_ordinal=revision_ordinal,
    )
    store.append(evidence_state)
    store.append(verification)
    quality = verification.substantive_research_quality
    next_state = "TERMINAL_ACCEPTED" if quality == "PASS" else (
        "TERMINAL_FAILED" if quality == "FAIL" else "REVISION_REQUIRED"
    )
    state = ContextCampaignStateRecord.create(
        campaign_id=campaign.campaign_id, state=next_state, predecessor=evidence_state,
        caused_by_artifact_id=verification.verification_id, revision_ordinal=revision_ordinal,
    )
    store.append(state)
    disposition = None
    if next_state in {"TERMINAL_ACCEPTED", "TERMINAL_FAILED"}:
        disposition = ContextTerminalDisposition.create(
            campaign_id=campaign.campaign_id, verification_id=verification.verification_id,
            terminal_state=next_state,
            context_output_contract_sha256=blind.context_output_contract_sha256,
            predecessor_state_record_id=state.state_record_id,
        )
        store.append(disposition)
    return VerificationPhaseResult(verification, disposition, state)
