"""WP175H controller lifecycle traps for the pinned v0.21.3 contract.

R001 wrong Hermes version rejected at preflight (no research call).
R004 exactly one permitted web toolset.       R011 one transport retry only.
R005 broader toolset/policy cannot be built.   R012 schema failure not retried.
R010 timeout -> sanitized receipt.             R013 unsafe output rejected.
R015 no raw stderr/env/usage payload in receipt.
R018 deterministic receipt identity.           R023 CODE_COMPLETE vs RUNTIME_ACTIVATED.
Plus: static tool enforcement, cost-cap fail-closed, no fabricated telemetry.
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

FIXED_CLOCK = lambda: datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
GOOD_VERSION = "hermes-agent 0.21.3"


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


def _usage(**overrides) -> bytes:
    doc = {
        "input_tokens": 50,
        "output_tokens": 80,
        "total_tokens": 130,
        "estimated_cost_usd": "0.04",
        "model": "example-model",
        "provider": "example-provider",
        "session_id": "s1",
    }
    doc.update(overrides)
    return json.dumps(doc).encode("utf-8")


def _stdout(request_id, **overrides) -> bytes:
    return json.dumps(_draft(request_id, **overrides)).encode("utf-8")


def _success_outcome(stdout, usage=None):
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=usage, usage_file_truncated=False, exit_code=0, timed_out=False,
        launch_failed=False, duration_ms=10,
    )


def _timeout_outcome():
    return HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=None, timed_out=True,
        launch_failed=False, duration_ms=1000,
    )


def _run(req, backend, **kw):
    return run_controlled_hermes_research(req, backend, clock=FIXED_CLOCK, **kw)


# --- success ----------------------------------------------------------------


def test_success_produces_validated_receipt():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    result = _run(req, backend)
    r = result.receipt
    assert result.error_code is None
    assert r.terminal_status == "RESEARCH_DRAFT_VALIDATED"
    assert r.output_schema_valid is True and r.safety_validation_status == "PASS"
    assert r.human_review_required is True
    assert r.no_execution_authority and r.no_live_authority and r.no_credential_authority
    assert r.no_risk_authority and r.no_paper_authority
    assert r.hermes_version == "0.21.3"
    assert r.configured_toolsets == ("web",)
    assert r.runtime_tool_telemetry == "UNAVAILABLE_ON_PINNED_V0_21_3"
    assert r.token_input_count == 50 and r.total_token_count == 130
    assert r.estimated_cost_usd == "0.04"
    assert backend.version_probe_count == 1 and backend.call_count == 1


# --- R001: version preflight ------------------------------------------------


def test_r001_wrong_hermes_version_rejected_before_research_call():
    req = _request()
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id), usage_file_bytes=_usage(), version_text="hermes-agent 0.20.0"
    )
    result = _run(req, backend)
    assert result.error_code == "BACKEND_VERSION_MISMATCH"
    assert result.receipt.terminal_status == "VERSION_MISMATCH"
    assert result.validated_draft is None
    # No research invocation happened; only the version preflight ran.
    assert backend.version_probe_count == 1
    assert backend.call_count == 0


def test_version_preflight_timeout_is_version_mismatch():
    req = _request()
    backend = FakeHermesBackend(
        [_success_outcome(_stdout(req.request_id), _usage())], version_timed_out=True
    )
    result = _run(req, backend)
    assert result.receipt.terminal_status == "VERSION_MISMATCH"
    assert backend.call_count == 0


# --- R004 / R005: toolset isolation -----------------------------------------


def test_r004_controller_argv_has_no_unsupported_flags_and_one_web_toolset():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    _run(req, backend)
    argv = backend.recorded_argv[0]
    assert "--input-file" not in argv and "--format" not in argv and "stream-json" not in argv
    assert argv.count("--toolsets") == 1
    assert argv[argv.index("--toolsets") + 1] == "web"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"allowed_toolsets": ("web", "terminal")},
        {"tool_enforcement": "DYNAMIC"},
        {"output_mode": "STREAM_JSON"},
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
    result = _run(req, backend)
    assert result.error_code == "BACKEND_TIMEOUT"
    assert result.receipt.terminal_status == "TIMEOUT"
    assert result.receipt.timed_out is True
    assert result.receipt.budget_status == "TIMEOUT_CAP_REACHED"


# --- R011 / R012: retry policy ----------------------------------------------


def test_r011_one_transport_retry_then_success():
    req = _request()
    backend = FakeHermesBackend([_timeout_outcome(), _success_outcome(_stdout(req.request_id), _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "RESEARCH_DRAFT_VALIDATED"
    assert backend.call_count == 2 and result.receipt.transport_attempt_count == 2


def test_r011_no_second_transport_retry():
    req = _request()
    backend = FakeHermesBackend(
        [_timeout_outcome(), _timeout_outcome(), _success_outcome(_stdout(req.request_id), _usage())]
    )
    result = _run(req, backend)
    assert result.receipt.terminal_status == "TIMEOUT"
    assert backend.call_count == 2


def test_r012_schema_failure_is_not_retried():
    req = _request()
    bad = _draft(req.request_id)
    del bad["confidence_label"]
    backend = FakeHermesBackend([_success_outcome(json.dumps(bad).encode(), _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "OUTPUT_SCHEMA_INVALID"
    assert backend.call_count == 1


# --- R013: unsafe output -----------------------------------------------------


def test_r013_unsafe_output_is_safety_failure_not_retried():
    req = _request()
    unsafe = _stdout(req.request_id, research_summary="Recommendation: place an order to buy YES.")
    backend = FakeHermesBackend([_success_outcome(unsafe, _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "SAFETY_VALIDATION_FAILED"
    assert result.receipt.safety_validation_status == "FAILED"
    assert backend.call_count == 1


# --- cost cap ---------------------------------------------------------------


def test_cost_above_cap_fails_closed():
    req = _request()  # cap is USD 2
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id), usage_file_bytes=_usage(estimated_cost_usd="9.99")
    )
    result = _run(req, backend)
    assert result.receipt.terminal_status == "BUDGET_EXCEEDED"
    assert result.receipt.budget_status == "COST_CAP_EXCEEDED"
    assert result.validated_draft is None


# --- R015: receipt sanitation ------------------------------------------------


def test_r015_receipt_has_no_raw_stderr_env_or_usage_payload():
    req = _request()
    secret = "ghp_SECRETSECRETSECRETSECRETSECRET0123"
    # A secret in an unknown usage field must never surface in the receipt.
    usage = _usage(**{"unknown_secret_field": secret})
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=usage)
    result = _run(req, backend)
    serialized = json.dumps(result.receipt.identity_fields())
    assert secret not in serialized
    assert "stderr" not in serialized.replace("stderr_truncated", "")
    assert not hasattr(result.receipt, "tool_call_counts")
    assert not hasattr(result.receipt, "raw_stdout")
    for ref in result.receipt.source_references:
        assert len(ref.url_digest) == 64


# --- R018: deterministic identity -------------------------------------------


def test_r018_deterministic_fake_transcript_yields_exact_receipt_id():
    req = _request()
    stdout, usage = _stdout(req.request_id), _usage()
    r1 = _run(req, FakeHermesBackend.from_transcript(stdout, usage_file_bytes=usage))
    r2 = _run(req, FakeHermesBackend.from_transcript(stdout, usage_file_bytes=usage))
    assert r1.receipt.receipt_id == r2.receipt.receipt_id
    assert r1.receipt.receipt_id.startswith("hermesresearchreceipt:sha256:")


# --- R023: activation split --------------------------------------------------


def test_r023_default_activation_is_code_complete_not_runtime_activated():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    result = _run(req, backend)
    assert result.receipt.activation_state == ACTIVATION_CODE_COMPLETE


def test_activation_run_complete_is_explicit_only():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    result = _run(req, backend, activation_state=ACTIVATION_RUN_COMPLETE)
    assert result.receipt.activation_state == ACTIVATION_RUN_COMPLETE


# --- transport failure ------------------------------------------------------


def test_launch_failure_yields_transport_receipt():
    req = _request()
    launch_fail = HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=None, timed_out=False,
        launch_failed=True, duration_ms=None,
    )
    backend = FakeHermesBackend([launch_fail, launch_fail])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "TRANSPORT_FAILURE"
    assert result.receipt.budget_status == "TRANSPORT_FAILED"
    assert backend.call_count == 2


def test_empty_response_stdout_fails_closed():
    req = _request()
    backend = FakeHermesBackend([_success_outcome(b"   ", _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "RESPONSE_CAPTURE_FAILED"


def test_default_policy_id_is_stable():
    assert DEFAULT_HERMES_INVOCATION_POLICY.policy_id.startswith("hermesinvocationpolicy:sha256:")
    assert HermesInvocationPolicy().policy_id == DEFAULT_HERMES_INVOCATION_POLICY.policy_id


def test_r020_no_imports_from_execution_paper_or_private_account_surfaces():
    """The runtime package imports no trading/paper/private-account surface."""
    import ast
    from pathlib import Path

    package = (
        Path(__file__).resolve().parents[3]
        / "src" / "research_runtime" / "hermes_controlled_runtime"
    )
    forbidden = (
        "execution_gateway", "paper_trading", "oms", "risk_engine",
        "py_clob_client", "polymarket", "requests", "httpx", "websockets",
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
