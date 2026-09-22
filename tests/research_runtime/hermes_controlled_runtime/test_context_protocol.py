"""S10-HERMES-CTX-01 protocol/store identity and immutability oracles."""

import dataclasses

import pytest

from src.research_runtime.hermes_controlled_runtime import (
    BlindResearchArtifact,
    ContextArtifactStore,
    ContextCampaignScope,
    ContextCampaignStateRecord,
    ContextResearchRevision,
    ContextStoreError,
    DEFAULT_HERMES_INVOCATION_POLICY,
)


def campaign(**overrides):
    values = dict(
        research_question="What public evidence bears on the frozen subject?",
        subject_refs=("subject:one",), scope_key="scope-one",
        exact_scope_json={"market": "one"}, information_cutoff="2026-01-01T00:00:00Z",
        allowed_public_research_classes=("public_web",),
        requested_provider_label="provider", requested_model_label="model",
        policy_id=DEFAULT_HERMES_INVOCATION_POLICY.policy_id,
        base_repo_code_identity="7495427820c892497e9c195a8b130c2d32102c67",
    )
    values.update(overrides)
    return ContextCampaignScope.create(**values)


def blind(c, predecessor):
    return BlindResearchArtifact.create(
        campaign=c, blind_request_id="request", prompt_envelope_sha256="1" * 64,
        context_output_contract_sha256="2" * 64, validated_draft_sha256="3" * 64,
        source_reference_digests=("4" * 64,), context_claims_sha256="5" * 64,
        session_evidence_id=None, predecessor_state_record_id=predecessor,
    )


def test_campaign_and_state_identities_are_stable_and_material():
    first = campaign()
    assert first == campaign()
    assert first.campaign_id != campaign(information_cutoff="2026-01-02T00:00:00Z").campaign_id
    scope = ContextCampaignStateRecord.create(campaign_id=first.campaign_id, state="SCOPE_FROZEN")
    research = ContextCampaignStateRecord.create(
        campaign_id=first.campaign_id, state="BLIND_RESEARCH", predecessor=scope
    )
    assert research == ContextCampaignStateRecord.create(
        campaign_id=first.campaign_id, state="BLIND_RESEARCH", predecessor=scope
    )
    with pytest.raises(Exception, match="STATE_TRANSITION_INVALID"):
        ContextCampaignStateRecord.create(
            campaign_id=first.campaign_id, state="CONTEXT_REVEALED", predecessor=scope
        )


def test_revision_transition_requires_explicit_artifact():
    c = campaign()
    evidence = ContextCampaignStateRecord("x", "v", c.campaign_id, "EVIDENCE_VERIFY", None, None, 0)
    required = ContextCampaignStateRecord.create(
        campaign_id=c.campaign_id, state="REVISION_REQUIRED", predecessor=evidence,
        caused_by_artifact_id="verification",
    )
    with pytest.raises(Exception, match="REVISION_ARTIFACT_REQUIRED"):
        ContextCampaignStateRecord.create(
            campaign_id=c.campaign_id, state="RECONCILIATION", predecessor=required
        )


def test_store_is_idempotent_append_only_and_detects_tamper(tmp_path):
    c = campaign()
    store = ContextArtifactStore(tmp_path / "context")
    assert store.append(c) == c.campaign_id
    assert store.append(c) == c.campaign_id
    payload = store.load(c.campaign_id, c.campaign_id)
    assert payload["campaign_id"] == c.campaign_id
    target = next((tmp_path / "context").rglob("*.json"))
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ContextStoreError, match="ARTIFACT_TAMPERED"):
        store.load(c.campaign_id, c.campaign_id)


def test_blind_artifact_is_immutable_and_material_inputs_change_id(tmp_path):
    c = campaign()
    store = ContextArtifactStore(tmp_path / "context")
    scope = ContextCampaignStateRecord.create(campaign_id=c.campaign_id, state="SCOPE_FROZEN")
    research = ContextCampaignStateRecord.create(
        campaign_id=c.campaign_id, state="BLIND_RESEARCH", predecessor=scope
    )
    original = blind(c, research.state_record_id)
    store.append(original)
    changed = dataclasses.replace(original, validated_draft_sha256="9" * 64)
    assert changed.blind_artifact_id == original.blind_artifact_id
    with pytest.raises(ContextStoreError, match="ARTIFACT_IDENTITY_CONFLICT"):
        store.append(changed)
    recreated = BlindResearchArtifact.create(
        campaign=c, blind_request_id="request", prompt_envelope_sha256="1" * 64,
        context_output_contract_sha256="2" * 64, validated_draft_sha256="9" * 64,
        source_reference_digests=("4" * 64,), context_claims_sha256="5" * 64,
        session_evidence_id=None, predecessor_state_record_id=research.state_record_id,
    )
    assert recreated.blind_artifact_id != original.blind_artifact_id


def test_revision_is_append_only_and_predecessor_is_identity_material(tmp_path):
    c = campaign()
    store = ContextArtifactStore(tmp_path / "context")
    common = dict(
        campaign_id=c.campaign_id, blind_artifact_id="blind", reveal_set_id="reveal",
        revision_ordinal=1, context_output_contract_sha256="1" * 64,
        validated_draft_sha256="2" * 64, claim_graph_sha256="3" * 64,
    )
    first = ContextResearchRevision.create(predecessor_reconciliation_id="prior-a", **common)
    second = ContextResearchRevision.create(predecessor_reconciliation_id="prior-b", **common)
    assert first.revision_id != second.revision_id
    before = dataclasses.asdict(first)
    store.append(first); store.append(second)
    assert dataclasses.asdict(first) == before
