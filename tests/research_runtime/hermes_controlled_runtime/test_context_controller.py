"""Blind orchestration, no-retry, policy-invariance, and phase-path oracles."""

import json

from src.research_runtime.hermes_controlled_runtime import (
    ContextArtifactStore,
    DEFAULT_HERMES_INVOCATION_POLICY,
    FakeHermesBackend,
    HermesInvocationOutcome,
    run_blind_phase,
)
from src.research_runtime.hermes_controlled_runtime.context_controller import _context_request
from tests.research_runtime.hermes_controlled_runtime.test_controller import _usage

from .test_context_protocol import campaign


def context_stdout(request_id):
    doc = {
        "schema_version": "hermes-research-draft/1.0.0", "request_id": request_id,
        "research_summary": "Balanced synthetic public evidence.", "confidence_label": "moderate",
        "evidence_for": ["support"], "evidence_against": ["counter"],
        "uncertainties": ["uncertain"], "known_missing_data": ["missing"],
        "falsification_checks_performed": ["searched for contrary evidence"],
        "limitations": ["public only"], "what_would_change_the_conclusion": ["new source"],
        "suggested_next_research_steps": ["observe"],
        "source_references": [{"url": "https://example.com/a", "title": "A", "source_class": "reference"}],
        "context_claims": [{
            "claim_statement": "Synthetic evidence supports the scoped claim.",
            "claim_kind": "INFERENCE", "subject_refs": ["subject:one"],
            "direction": "SUPPORTING", "source_reference_indices": [0],
            "assumptions": ["the public source is accurate"],
            "uncertainty_note": "The public record may be incomplete.",
        }],
    }
    for flag in (
        "advisory_only", "human_review_required", "no_execution_authority", "no_risk_override",
        "no_credential_request", "no_order_or_cancel_or_sign_or_submit", "no_paper_live_decision",
        "no_strategy_promotion_approval", "no_pr_approval_or_merge_readiness_claim",
    ):
        doc[flag] = True
    return json.dumps(doc).encode()


def backend_for(c):
    request = _context_request(c)
    return FakeHermesBackend.from_transcript(
        context_stdout(request.request_id), usage_file_bytes=_usage(),
    )


def test_blind_phase_is_prior_independent_and_freezes_only_after_append(tmp_path, monkeypatch):
    c = campaign(requested_provider_label="example-provider", requested_model_label="example-model")
    def explode(*args, **kwargs):
        raise AssertionError("Alpha loader crossed blind barrier")
    monkeypatch.setattr(
        "src.research_runtime.hermes_controlled_runtime.context_broker.load_and_verify_alpha_factory_registry",
        explode,
    )
    first_backend = backend_for(c)
    second_backend = backend_for(c)
    first = run_blind_phase(
        campaign=c, store=ContextArtifactStore(tmp_path / "one"), backend=first_backend,
    )
    second = run_blind_phase(
        campaign=c, store=ContextArtifactStore(tmp_path / "two"), backend=second_backend,
    )
    assert first_backend.call_count == second_backend.call_count == 1
    assert first.blind_artifact == second.blind_artifact
    assert first.blind_frozen_state.state == "BLIND_FROZEN"
    assert first.blind_artifact.alpha_context_present is False
    assert first.blind_artifact.reveal_set_id is None


def test_failure_never_consumes_queued_second_outcome(tmp_path):
    c = campaign(requested_provider_label="example-provider", requested_model_label="example-model")
    fail = HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=None,
        timed_out=True, launch_failed=False, duration_ms=1,
    )
    success = HermesInvocationOutcome(
        stdout=context_stdout(_context_request(c).request_id), stdout_truncated=False,
        stderr_byte_len=0, stderr_truncated=False, usage_file_bytes=_usage(),
        usage_file_truncated=False, exit_code=0, timed_out=False, launch_failed=False,
        duration_ms=1,
    )
    backend = FakeHermesBackend([fail, success])
    result = run_blind_phase(
        campaign=c, store=ContextArtifactStore(tmp_path / "context"), backend=backend,
    )
    assert backend.call_count == 1
    assert result.blind_artifact is None


def test_managed_policy_memory_auxiliary_and_lazy_install_pins_are_closed():
    policy = DEFAULT_HERMES_INVOCATION_POLICY
    config = policy.managed_config_mapping()
    assert config["memory"] == {"memory_enabled": False, "user_profile_enabled": False, "provider": ""}
    assert config["compression"] == {"enabled": False}
    assert config["auxiliary"]["transient_retries"] == 0
    assert config["security"] == {"allow_lazy_installs": False, "allow_private_urls": False}
    assert config["browser"] == {"allow_private_urls": False}
