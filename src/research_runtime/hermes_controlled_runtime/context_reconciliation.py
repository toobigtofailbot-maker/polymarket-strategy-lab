"""Claim grounding, evidence precedence, contradiction and quality gates."""

from __future__ import annotations

import dataclasses
from typing import Mapping, Sequence

from .context_protocol import (
    BlindResearchArtifact,
    ContextCampaignScope,
    ContextResearchRevision,
    EvidenceVerificationRecord,
    RevealedContextSet,
)
from .models import ValidatedResearchDraft, canonical_json_bytes, content_address, sha256_hex
from .session_evidence import HermesSessionEvidence

EVIDENCE_PRECEDENCE = {
    "RAW_DIRECT": 4,
    "DETERMINISTIC_DERIVED": 3,
    "ALPHA_SUMMARY": 2,
    "HERMES_INFERENCE": 1,
}


@dataclasses.dataclass(frozen=True)
class ContextEvidenceItem:
    evidence_id: str
    content_sha256: str
    evidence_class: str
    subject_refs: tuple[str, ...]
    scope_sha256: str
    information_cutoff: str
    admissibility_status: str
    provenance_manifest_id: str | None
    dq_flags: tuple[str, ...]
    origin: str
    direction: str

    @property
    def precedence(self) -> int:
        return EVIDENCE_PRECEDENCE[self.evidence_class]


class ReconciliationError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def build_evidence_item(
    *, content_sha256: str, evidence_class: str, subject_refs: Sequence[str],
    scope_sha256: str, information_cutoff: str, admissibility_status: str,
    origin: str, direction: str, provenance_manifest_id: str | None = None,
    dq_flags: Sequence[str] = (),
) -> ContextEvidenceItem:
    if evidence_class not in EVIDENCE_PRECEDENCE or direction not in {"SUPPORTING", "CONTRADICTING"}:
        raise ReconciliationError("EVIDENCE_INVALID")
    fields = {
        "content_sha256": content_sha256, "evidence_class": evidence_class,
        "subject_refs": sorted(set(subject_refs)), "scope_sha256": scope_sha256,
        "information_cutoff": information_cutoff, "admissibility_status": admissibility_status,
        "provenance_manifest_id": provenance_manifest_id, "dq_flags": sorted(set(dq_flags)),
        "origin": origin, "direction": direction,
    }
    return ContextEvidenceItem(
        content_address("contextevidence:sha256:", fields), content_sha256, evidence_class,
        tuple(fields["subject_refs"]), scope_sha256, information_cutoff, admissibility_status,
        provenance_manifest_id, tuple(fields["dq_flags"]), origin, direction,
    )


def reconcile_context_research(
    *, campaign: ContextCampaignScope, blind_artifact: BlindResearchArtifact,
    reveal_set: RevealedContextSet, validated_draft: ValidatedResearchDraft,
    session_evidence: HermesSessionEvidence | None,
    context_output_contract_sha256: str, predecessor_state_record_id: str,
    predecessor_reconciliation_id: str | None = None, revision_ordinal: int = 0,
    project_evidence: Sequence[ContextEvidenceItem] = (),
) -> tuple[ContextResearchRevision, EvidenceVerificationRecord]:
    if (
        blind_artifact.campaign_id != campaign.campaign_id
        or reveal_set.campaign_id != campaign.campaign_id
        or reveal_set.blind_artifact_id != blind_artifact.blind_artifact_id
        or blind_artifact.context_output_contract_sha256 != context_output_contract_sha256
        or not validated_draft.context_claims
        or not validated_draft.falsification_checks_performed
    ):
        raise ReconciliationError("RECONCILIATION_BINDING_INVALID")
    observed = frozenset(session_evidence.observed_url_digests if session_evidence else ())
    unexpected = tuple(session_evidence.unexpected_tool_names if session_evidence else ())
    dispositions: list[dict[str, object]] = []
    falsification: list[dict[str, object]] = []
    unsupported = 0
    for claim in validated_draft.context_claims:
        qualifying: list[ContextEvidenceItem] = []
        for index in claim.source_reference_indices:
            reference = validated_draft.source_references[index]
            if reference.url_digest not in observed:
                continue
            qualifying.append(build_evidence_item(
                content_sha256=reference.url_digest, evidence_class="HERMES_INFERENCE",
                subject_refs=claim.subject_refs, scope_sha256=campaign.exact_scope_sha256,
                information_cutoff=campaign.information_cutoff, admissibility_status="ADMISSIBLE",
                origin="BLIND_WEB", direction=(
                    "CONTRADICTING" if claim.direction == "CONTRADICTING" else "SUPPORTING"
                ),
            ))
        for item in project_evidence:
            if (
                set(item.subject_refs).intersection(claim.subject_refs)
                and item.scope_sha256 == campaign.exact_scope_sha256
                and item.information_cutoff <= campaign.information_cutoff
                and item.admissibility_status == "ADMISSIBLE"
                and item.origin in {"REVEALED_ALPHA", "DETERMINISTIC_PROJECT_EVIDENCE"}
            ):
                qualifying.append(item)
        support = [item for item in qualifying if item.direction == "SUPPORTING"]
        contrary = [item for item in qualifying if item.direction == "CONTRADICTING"]
        strongest_support = max((item.precedence for item in support), default=0)
        strongest_contrary = max((item.precedence for item in contrary), default=0)
        if not support:
            disposition = "UNSUPPORTED"
            unsupported += 1
        elif strongest_contrary > strongest_support:
            disposition = "CONTRADICTED"
        elif strongest_contrary == strongest_support and strongest_contrary:
            disposition = "UNCERTAIN"
        else:
            disposition = "SUPPORTED"
        dispositions.append({
            "claim_id": claim.claim_id, "disposition": disposition,
            "supporting_evidence_ids": sorted(item.evidence_id for item in support),
            "contradicting_evidence_ids": sorted(item.evidence_id for item in contrary),
            "assumptions": list(claim.assumptions), "uncertainty_note": claim.uncertainty_note,
        })
        falsification.append({
            "claim_id": claim.claim_id, "challenged": True,
            "contrary_evidence_available": bool(contrary),
            "checks": list(validated_draft.falsification_checks_performed),
        })
    dispositions.sort(key=lambda item: str(item["claim_id"]))
    falsification.sort(key=lambda item: str(item["claim_id"]))
    claim_graph = {"claims": dispositions, "falsification": falsification}
    revision = ContextResearchRevision.create(
        campaign_id=campaign.campaign_id, blind_artifact_id=blind_artifact.blind_artifact_id,
        reveal_set_id=reveal_set.reveal_set_id,
        predecessor_reconciliation_id=predecessor_reconciliation_id,
        revision_ordinal=revision_ordinal,
        context_output_contract_sha256=context_output_contract_sha256,
        validated_draft_sha256=sha256_hex(canonical_json_bytes({
            "request_id": validated_draft.request_id,
            "summary": validated_draft.research_summary,
            "claims": [claim.identity_fields() for claim in validated_draft.context_claims],
        })),
        claim_graph_sha256=sha256_hex(canonical_json_bytes(claim_graph)),
    )
    failing_dispositions = {"UNSUPPORTED", "CONTRADICTED", "UNCERTAIN"}
    quality = "PASS"
    if unexpected:
        quality = "FAIL"
    elif any(item["disposition"] in failing_dispositions for item in dispositions):
        quality = "REVISION_REQUIRED"
    verification = EvidenceVerificationRecord.create(
        campaign_id=campaign.campaign_id, reconciliation_id=revision.revision_id,
        context_output_contract_sha256=context_output_contract_sha256,
        structural_validity="PASS", substantive_research_quality=quality,
        claim_dispositions=tuple(dispositions), falsification_results=tuple(falsification),
        unsupported_claim_count=unsupported, unexpected_tool_names=unexpected,
        predecessor_state_record_id=predecessor_state_record_id,
    )
    return revision, verification
