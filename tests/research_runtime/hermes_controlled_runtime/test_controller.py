"""WP175H controller lifecycle traps.

R001 wrong Hermes version rejected.        R011 one transport retry only.
R004 exactly one permitted web toolset.    R012 schema failure not retried.
R005 broader toolset cannot be requested.  R013 unsafe output rejected.
R010 timeout -> sanitized receipt.         R015 no raw stderr/env/payload in receipt.
R018 deterministic receipt identity.       R023 CODE_COMPLETE vs RUNTIME_ACTIVATED.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.research_runtime.hermes_controlled_runtime import (
    ACTIVATION_CODE_COMPLETE,
    ACTIVATION_RUN_COMPLETE,
    DEFAULT_HERMES_INVOCATION_POLICY,
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
    FakeHermesBackend,
    HermesInvocationOutcome,
    HermesInvocationPolicy,
    NON_AUTHORITY_NOTICE,
    PolicyBroadeningError,
    REQUEST_SCHEMA_VERSION,
    build_research_run_request,
    run_controlled_hermes_research,
)

FIXED_CLOCK = lambda: datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)


def _request():
    return build_research_run_request(
        {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "research_question": "Will the public event resolve YES by the deadline?",
            "research_objective": "Assess public evidence for and against the outcome.",
            "research_category": "event_outcome",
            "public_market_context": "A Polymarket public market on a future event.",
            "allowed_research_scope": ["public_web", "public_news"],
            "required_source_types": ["news", "official"],
            "max_sources": 8,
            "provider_label": "example-provider",
            "model_label": "example-model",
            "max_turns": 15,
            "max_wall_seconds": 90,
            "max_output_bytes": 300_000,
            "max_estimated_cost_usd": "2",
            "human_review_required": True,
            "non_authority_notice": NON_AUTHORITY_NOTICE,
        }
    )


def _draft(request_id: str, **overrides) -> dict:
    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
        "research_summary": "A balanced public-evidence summary.",
        "evidence_for": ["report A"],
        "evidence_against": ["report B"],
        "uncertainties": ["timing"],
        "known_missing_data": ["no official confirmation"],
        "falsification_checks_performed": ["searched disconfirming sources"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["official announcement"],
        "suggested_next_research_steps": ["monitor official channel"],
        "source_references": [
            {"url": "https://example.com/a", "title": "A", "source_class": "news"}
        ],
        "confidence_label": "moderate",
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    draft.update(overrides)
    return draft


def _transcript(request_id, *, version="hermes-agent 0.21.3", tools=("web_search",),
                draft=None, extra_events=None, subtype="success"):
    events = [
        {"type": "session", "session_id": "s1", "provider": "example-provider",
         "model": "example-model", "version": version},
    ]
    for tool in tools:
        events.append({"type": "tool_call", "tool": tool})
    for event in (extra_events or []):
        events.append(event)
    result_text = json.dumps(draft if draft is not None else _draft(request_id))
    events.append({
        "type": "result", "subtype": subtype, "result": result_text,
        "usage": {"input_tokens": 50, "output_tokens": 80},
        "total_cost_usd": "0.04", "duration_ms": 1200,
    })
    return ("\n".join(json.dumps(e) for e in events)).encode("utf-8")


def _success_outcome(stdout, *, stderr_byte_len=0):
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=stderr_byte_len,
        stderr_truncated=False, exit_code=0, timed_out=False, launch_failed=False,
        duration_ms=10,
    )


def _timeout_outcome():
    return HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        exit_code=None, timed_out=True, launch_failed=False, duration_ms=1000,
    )


# --- success ----------------------------------------------------------------


def test_success_produces_validated_receipt():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_transcript(req.request_id))
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    r = result.receipt
    assert result.error_code is None
    assert r.terminal_status == "RESEARCH_DRAFT_VALIDATED"
    assert r.output_schema_valid is True
    assert r.safety_validation_status == "PASS"
    assert r.human_review_required is True
    assert r.no_execution_authority and r.no_live_authority and r.no_credential_authority
    assert r.no_risk_authority and r.no_paper_authority
    assert r.hermes_version == "hermes-agent 0.21.3"
    assert backend.call_count == 1


# --- R001: wrong version -----------------------------------------------------


def test_r001_wrong_hermes_version_rejected():
    req = _request()
    backend = FakeHermesBackend.from_transcript(
        _transcript(req.request_id, version="hermes-agent 0.20.0")
    )
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.error_code == "BACKEND_VERSION_MISMATCH"
    assert result.receipt.terminal_status == "VERSION_MISMATCH"
    assert result.validated_draft is None


# --- R004 / R005: toolset isolation -----------------------------------------


def test_r004_controller_argv_has_exactly_one_web_toolset():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_transcript(req.request_id))
    run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    argv = backend.recorded_argv[0]
    assert argv.count("--toolsets") == 1
    assert argv[argv.index("--toolsets") + 1] == "web"


def test_forbidden_tool_in_transcript_is_isolation_violation():
    req = _request()
    backend = FakeHermesBackend.from_transcript(
        _transcript(req.request_id, tools=("web_search", "terminal"))
    )
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "TOOL_ISOLATION_VIOLATION"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"allowed_toolsets": ("web", "terminal")},
        {"shell": True},
        {"repo_mount": True},
        {"mcp": True},
        {"plugins": True},
        {"cron": True},
        {"delegation": True},
        {"file_tools": True},
        {"automatic_retry_on_schema_failure": True},
        {"safe_mode": False},
        {"max_transport_retries": 2},
        {"max_concurrency": 2},
    ],
)
def test_r005_policy_cannot_be_broadened(kwargs):
    with pytest.raises(PolicyBroadeningError):
        HermesInvocationPolicy(**kwargs)


# --- R010: timeout ----------------------------------------------------------


def test_r010_timeout_yields_sanitized_receipt():
    req = _request()
    backend = FakeHermesBackend([_timeout_outcome(), _timeout_outcome()])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.error_code == "BACKEND_TIMEOUT"
    assert result.receipt.terminal_status == "TIMEOUT"
    assert result.receipt.timed_out is True
    assert result.receipt.budget_status == "TIMEOUT_CAP_REACHED"


# --- R011 / R012: retry policy ----------------------------------------------


def test_r011_one_transport_retry_then_success():
    req = _request()
    backend = FakeHermesBackend([_timeout_outcome(), _success_outcome(_transcript(req.request_id))])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "RESEARCH_DRAFT_VALIDATED"
    assert backend.call_count == 2
    assert result.receipt.transport_attempt_count == 2


def test_r011_no_second_transport_retry():
    req = _request()
    backend = FakeHermesBackend([_timeout_outcome(), _timeout_outcome(), _success_outcome(_transcript(req.request_id))])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "TIMEOUT"
    assert backend.call_count == 2  # exactly one retry, no third attempt


def test_r012_schema_failure_is_not_retried():
    req = _request()
    bad_draft = _draft(req.request_id)
    del bad_draft["confidence_label"]
    backend = FakeHermesBackend([_success_outcome(_transcript(req.request_id, draft=bad_draft))])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "OUTPUT_SCHEMA_INVALID"
    assert backend.call_count == 1


# --- R013: unsafe output -----------------------------------------------------


def test_r013_unsafe_output_is_safety_failure_not_retried():
    req = _request()
    unsafe = _draft(req.request_id, research_summary="Recommendation: place an order to buy YES.")
    backend = FakeHermesBackend([_success_outcome(_transcript(req.request_id, draft=unsafe))])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "SAFETY_VALIDATION_FAILED"
    assert result.receipt.safety_validation_status == "FAILED"
    assert backend.call_count == 1


# --- R015: receipt sanitation ------------------------------------------------


def test_r015_receipt_has_no_raw_stderr_env_or_payload():
    req = _request()
    secret = "ghp_SECRETSECRETSECRETSECRETSECRET0123"
    # A poison secret in an ignored/unknown stream event must never surface.
    backend = FakeHermesBackend.from_transcript(
        _transcript(req.request_id, extra_events=[{"type": "debug", "leak": secret}]),
    )
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    serialized = json.dumps(result.receipt.identity_fields())
    assert secret not in serialized
    assert "stderr" not in serialized.replace("stderr_truncated", "")
    assert not hasattr(result.receipt, "raw_stdout")
    # Source references are digests, not raw URLs beyond the validated draft.
    for ref in result.receipt.source_references:
        assert len(ref.url_digest) == 64


# --- R018: deterministic identity -------------------------------------------


def test_r018_deterministic_fake_transcript_yields_exact_receipt_id():
    req = _request()
    transcript = _transcript(req.request_id)
    r1 = run_controlled_hermes_research(req, FakeHermesBackend.from_transcript(transcript), clock=FIXED_CLOCK)
    r2 = run_controlled_hermes_research(req, FakeHermesBackend.from_transcript(transcript), clock=FIXED_CLOCK)
    assert r1.receipt.receipt_id == r2.receipt.receipt_id
    assert r1.receipt.receipt_id.startswith("hermesresearchreceipt:sha256:")


# --- R023: activation split --------------------------------------------------


def test_r023_default_activation_is_code_complete_not_runtime_activated():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_transcript(req.request_id))
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.activation_state == ACTIVATION_CODE_COMPLETE


def test_activation_run_complete_is_explicit_only():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_transcript(req.request_id))
    result = run_controlled_hermes_research(
        req, backend, clock=FIXED_CLOCK, activation_state=ACTIVATION_RUN_COMPLETE
    )
    assert result.receipt.activation_state == ACTIVATION_RUN_COMPLETE


# --- transport / hermes error ------------------------------------------------


def test_launch_failure_yields_transport_receipt():
    req = _request()
    launch_fail = HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        exit_code=None, timed_out=False, launch_failed=True, duration_ms=None,
    )
    backend = FakeHermesBackend([launch_fail, launch_fail])
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status == "TRANSPORT_FAILURE"
    assert result.receipt.budget_status == "TRANSPORT_FAILED"
    assert backend.call_count == 2


def test_hermes_error_subtype_is_terminal():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_transcript(req.request_id, subtype="error"))
    result = run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK)
    assert result.receipt.terminal_status in {"HERMES_ERROR", "VERSION_MISMATCH"}


def test_default_policy_id_is_stable():
    assert DEFAULT_HERMES_INVOCATION_POLICY.policy_id.startswith(
        "hermesinvocationpolicy:sha256:"
    )
    assert HermesInvocationPolicy().policy_id == DEFAULT_HERMES_INVOCATION_POLICY.policy_id


def test_r020_no_imports_from_execution_paper_or_private_account_surfaces():
    """The runtime package imports no trading/paper/private-account surface."""
    import ast
    from pathlib import Path

    package = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "research_runtime"
        / "hermes_controlled_runtime"
    )
    forbidden = (
        "execution_gateway",
        "paper_trading",
        "oms",
        "risk_engine",
        "py_clob_client",
        "polymarket",
        "requests",
        "httpx",
        "websockets",
    )
    offenders: list[str] = []
    for module_path in sorted(package.glob("*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                if any(bad in name for bad in forbidden):
                    offenders.append(f"{module_path.name}:{name}")
    assert offenders == [], offenders
