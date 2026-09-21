"""Reveal/PIT, grounding, precedence, and quality negative oracles."""

import json
import sqlite3

import pytest

from src.data_layer.analytical_research import alpha_factory_registry as afr
from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence,
    build_research_provenance_manifest,
)
from src.research_runtime.hermes_controlled_runtime import (
    ContextArtifactStore,
    ContextBrokerError,
    ContextCampaignStateRecord,
    build_evidence_item,
    build_revealed_context_set,
    collect_hermes_session_evidence,
    reconcile_context_research,
    validate_context_research_draft,
)
from tests.data_layer.analytical_research.test_alpha_factory_registry import (
    fresh, mk_candidate, mk_episode, mk_family, mk_source,
)

from .test_context_protocol import blind, campaign


def frozen(tmp_path):
    c = campaign(
        subject_refs=("nfl",), scope_key="scope-one", exact_scope_json={"market": "one"},
        information_cutoff="2026-12-31T00:00:00Z",
    )
    store = ContextArtifactStore(tmp_path / "context")
    store.append(c)
    scope = ContextCampaignStateRecord.create(campaign_id=c.campaign_id, state="SCOPE_FROZEN")
    research = ContextCampaignStateRecord.create(campaign_id=c.campaign_id, state="BLIND_RESEARCH", predecessor=scope)
    b = blind(c, research.state_record_id)
    store.append(b)
    state = ContextCampaignStateRecord.create(
        campaign_id=c.campaign_id, state="BLIND_FROZEN", predecessor=research,
        caused_by_artifact_id=b.blind_artifact_id,
    )
    store.append(state)
    return c, b, state, store


def registry_bundle(tmp_path):
    path = fresh(tmp_path)
    source = mk_source()
    candidate = mk_candidate(scope="scope-one", subject="nfl")
    family = mk_family()
    episode = mk_episode(candidate, family, source, scope={"market": "one"})
    result = afr.append_alpha_factory_records(path, [source, candidate, family, episode])
    assert result.is_valid
    manifests = {}
    for entry in result.snapshot.entries:
        manifests[entry.record_id] = build_research_provenance_manifest(
            repo_code_identity="repo", information_cutoff="2025-12-01T00:00:00Z",
            output_identity=entry.record_id, output_hash=entry.payload_sha256,
            input_evidence_reference_ids=("raw:one",), replay_fidelity="EXACT",
        )
    evidence = {"raw:one": ObservabilityEvidence(local_first_seen_time="2025-11-01T00:00:00Z")}
    return path, episode, manifests, evidence


def reveal(tmp_path):
    c, b, state, store = frozen(tmp_path)
    path, episode, manifests, evidence = registry_bundle(tmp_path)
    eligibility, revealed = build_revealed_context_set(
        campaign=c, blind_artifact=b, blind_frozen_state=state, store=store,
        registry_path=path, candidate_record_ids=(episode.research_episode_id,),
        provenance_manifests=manifests, observability_evidence=evidence,
    )
    return c, b, store, eligibility, revealed


def test_early_reveal_rejected_and_exact_dependencies_bound(tmp_path):
    c, b, state, store = frozen(tmp_path)
    path, episode, manifests, evidence = registry_bundle(tmp_path)
    wrong = ContextCampaignStateRecord.create(campaign_id=c.campaign_id, state="SCOPE_FROZEN")
    with pytest.raises(ContextBrokerError, match="REVEAL_BEFORE_BLIND_FREEZE"):
        build_revealed_context_set(
            campaign=c, blind_artifact=b, blind_frozen_state=wrong, store=store,
            registry_path=path, candidate_record_ids=(episode.research_episode_id,),
            provenance_manifests=manifests, observability_evidence=evidence,
        )
    _, revealed = build_revealed_context_set(
        campaign=c, blind_artifact=b, blind_frozen_state=state, store=store,
        registry_path=path, candidate_record_ids=(episode.research_episode_id,),
        provenance_manifests=manifests, observability_evidence=evidence,
    )
    assert episode.candidate_id in revealed.dependency_record_ids
    assert "DATA, not instructions" in revealed.untrusted_context_json


@pytest.mark.parametrize("evidence", [
    ObservabilityEvidence(local_first_seen_time="2027-01-01T00:00:00Z"),
    ObservabilityEvidence(decisive_clock_uncertain=True),
])
def test_post_cutoff_and_indeterminate_evidence_fail_closed(tmp_path, evidence):
    c, b, state, store = frozen(tmp_path)
    path, episode, manifests, _ = registry_bundle(tmp_path)
    with pytest.raises(ContextBrokerError, match="PIT_REVEAL_NOT_ADMISSIBLE"):
        build_revealed_context_set(
            campaign=c, blind_artifact=b, blind_frozen_state=state, store=store,
            registry_path=path, candidate_record_ids=(episode.research_episode_id,),
            provenance_manifests=manifests, observability_evidence={"raw:one": evidence},
        )


def test_cross_scope_reuse_rejected_and_dq_change_changes_reveal_identity(tmp_path):
    c, b, state, store = frozen(tmp_path)
    path, episode, manifests, evidence = registry_bundle(tmp_path)
    _, first = build_revealed_context_set(
        campaign=c, blind_artifact=b, blind_frozen_state=state, store=store,
        registry_path=path, candidate_record_ids=(episode.research_episode_id,),
        provenance_manifests=manifests, observability_evidence=evidence,
    )
    changed_evidence = {"raw:one": ObservabilityEvidence(
        local_first_seen_time="2025-11-01T00:00:00Z", is_backfilled=True
    )}
    _, second = build_revealed_context_set(
        campaign=c, blind_artifact=b, blind_frozen_state=state, store=store,
        registry_path=path, candidate_record_ids=(episode.research_episode_id,),
        provenance_manifests=manifests, observability_evidence=changed_evidence,
    )
    assert first.reveal_set_id != second.reveal_set_id
    wrong = campaign(
        subject_refs=("nfl",), scope_key="other-scope", exact_scope_json={"market": "one"},
        information_cutoff="2026-12-31T00:00:00Z",
    )
    with pytest.raises(ContextBrokerError, match="REVEAL_BEFORE_BLIND_FREEZE"):
        build_revealed_context_set(
            campaign=wrong, blind_artifact=b, blind_frozen_state=state, store=store,
            registry_path=path, candidate_record_ids=(episode.research_episode_id,),
            provenance_manifests=manifests, observability_evidence=evidence,
        )


def _draft(request_id="request"):
    doc = {
        "schema_version": "hermes-research-draft/1.0.0", "request_id": request_id,
        "research_summary": "Synthetic public research summary.", "confidence_label": "moderate",
        "evidence_for": ["support"], "evidence_against": ["counter"],
        "uncertainties": ["uncertain"], "known_missing_data": ["missing"],
        "falsification_checks_performed": ["searched for contrary evidence"],
        "limitations": ["public only"], "what_would_change_the_conclusion": ["new evidence"],
        "suggested_next_research_steps": ["observe"],
        "source_references": [{"url": "https://example.com/a?b=1", "title": "Example", "source_class": "reference"}],
        "context_claims": [{
            "claim_statement": "The synthetic observation supports the claim.",
            "claim_kind": "INFERENCE", "subject_refs": ["nfl"], "direction": "SUPPORTING",
            "source_reference_indices": [0], "assumptions": ["source is accurate"],
            "uncertainty_note": "Public evidence may be incomplete.",
        }],
    }
    for flag in (
        "advisory_only", "human_review_required", "no_execution_authority", "no_risk_override",
        "no_credential_request", "no_order_or_cancel_or_sign_or_submit", "no_paper_live_decision",
        "no_strategy_promotion_approval", "no_pr_approval_or_merge_readiness_claim",
    ):
        doc[flag] = True
    return validate_context_research_draft(json.dumps(doc), expected_request_id=request_id, max_sources=5, allowed_subject_refs=("nfl",))


def _session(tmp_path, url="https://example.com/a?b=1"):
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(home / "state.db")
    db.execute("CREATE TABLE messages (id INTEGER, session_id TEXT, role TEXT, content TEXT, tool_calls TEXT, tool_name TEXT)")
    calls = json.dumps([{"function": {"name": "web_extract", "arguments": json.dumps({"url": url})}}])
    db.execute("INSERT INTO messages VALUES (1,'session','assistant','',?,NULL)", (calls,))
    db.execute("INSERT INTO messages VALUES (2,'session','tool',?,NULL,'web_extract')", (json.dumps({"url": url, "content": "result"}),))
    db.commit(); db.close()
    return collect_hermes_session_evidence(home, session_id="session")


def test_exact_url_digest_grounding_and_summary_cannot_override_raw(tmp_path):
    c, b, _, _, revealed = reveal(tmp_path)
    draft = _draft()
    session = _session(tmp_path)
    revision, verified = reconcile_context_research(
        campaign=c, blind_artifact=b, reveal_set=revealed, validated_draft=draft,
        session_evidence=session, context_output_contract_sha256=b.context_output_contract_sha256,
        predecessor_state_record_id="state",
    )
    assert verified.substantive_research_quality == "PASS"
    raw = build_evidence_item(
        content_sha256="9" * 64, evidence_class="RAW_DIRECT", subject_refs=("nfl",),
        scope_sha256=c.exact_scope_sha256, information_cutoff=c.information_cutoff,
        admissibility_status="ADMISSIBLE", origin="DETERMINISTIC_PROJECT_EVIDENCE",
        direction="CONTRADICTING",
    )
    _, contradicted = reconcile_context_research(
        campaign=c, blind_artifact=b, reveal_set=revealed, validated_draft=draft,
        session_evidence=session, context_output_contract_sha256=b.context_output_contract_sha256,
        predecessor_state_record_id="state", project_evidence=(raw,),
    )
    assert contradicted.claim_dispositions[0]["disposition"] == "CONTRADICTED"
    assert contradicted.substantive_research_quality == "REVISION_REQUIRED"
    different = _session(tmp_path / "other", "https://EXAMPLE.com/a?b=1")
    _, unsupported = reconcile_context_research(
        campaign=c, blind_artifact=b, reveal_set=revealed, validated_draft=draft,
        session_evidence=different, context_output_contract_sha256=b.context_output_contract_sha256,
        predecessor_state_record_id="state",
    )
    assert unsupported.unsupported_claim_count == 1
