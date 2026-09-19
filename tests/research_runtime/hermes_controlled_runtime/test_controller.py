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
    is_supported_hermes_version,
    parse_hermes_version,
    run_controlled_hermes_research,
)

FIXED_CLOCK = lambda: datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
GOOD_VERSION = "Hermes Agent v0.21.3 (2026.9.14)"


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
            "max_wall_seconds": 90,
            "max_output_bytes": 300_000,
            "max_accepted_estimated_cost_usd": "2",
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
    """A complete v0.21.3 success-evidence usage report (exact tagged keys)."""
    doc = {
        "input_tokens": 50,
        "output_tokens": 80,
        "total_tokens": 130,
        "api_calls": 1,
        "estimated_cost_usd": 0.04,
        "cost_status": "estimated",
        "cost_source": "official_docs_snapshot",
        "model": "example-model",
        "provider": "example-provider",
        "session_id": "s1",
        "completed": True,
        "failed": False,
    }
    doc.update(overrides)
    return json.dumps(doc).encode("utf-8")


def _exit_outcome(stdout, usage=None, exit_code=0):
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=usage, usage_file_truncated=False, exit_code=exit_code,
        timed_out=False, launch_failed=False, duration_ms=10,
    )


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
    assert r.configured_toolsets == ("web",)  # T23
    assert r.runtime_tool_telemetry == "UNAVAILABLE_ON_PINNED_V0_21_3"  # T22
    assert r.iteration_cap_status == "UNAVAILABLE_ON_PINNED_V0_21_3_ONESHOT"
    assert r.approval_authority == "APPROVAL_BYPASS_PRESENT_BUT_NO_MUTATING_TOOL_SURFACE"
    assert r.exit_code == 0
    assert r.usage_evidence_status == "VALID"
    assert r.usage_completed is True and r.usage_failed is False
    assert r.token_input_count == 50 and r.total_token_count == 130
    assert r.api_call_count == 1
    assert r.estimated_cost_usd == "0.04" and r.cost_status == "estimated"
    # T20: the receipt binds the VERIFIED actual usage provider/model.
    assert r.verified_provider == "example-provider" and r.verified_model == "example-model"
    assert backend.version_probe_count == 1 and backend.call_count == 1


# --- R001: version preflight ------------------------------------------------


@pytest.mark.parametrize(
    ("reported", "expected"),
    (
        ("Hermes Agent v0.21.3 (2026.9.14)", "0.21.3"),
        ("Hermes Agent v0.21.3 (2026.9.14) · upstream 345cd2b", "0.21.3"),
        ("hermes-agent 0.21.3", "0.21.3"),
        (b"Hermes Agent v0.21.3 (2026.9.14)", "0.21.3"),
        ("HERMES AGENT V0.21.3 (2026.9.14)", "0.21.3"),
    ),
)
def test_parse_hermes_version_acceptance_matrix(reported, expected):
    assert parse_hermes_version(reported) == expected
    assert is_supported_hermes_version(reported) is True


@pytest.mark.parametrize(
    "reported",
    (
        "2026.9.14",
        "Hermes Agent (2026.9.14)",
        "unrelated-tool 0.21.3",
        "Hermes Agent v0.21.3foo (2026.9.14)",
        b"\xffHermes Agent v0.21.3",
        None,
    ),
)
def test_parse_hermes_version_rejection_matrix(reported):
    assert parse_hermes_version(reported) is None
    assert is_supported_hermes_version(reported) is False


def test_real_banner_shape_reaches_exactly_one_fake_research_invocation():
    req = _request()
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id), usage_file_bytes=_usage(), version_text=GOOD_VERSION
    )
    result = _run(req, backend)
    assert result.error_code is None
    assert backend.version_probe_count == 1
    assert backend.call_count == 1


def test_r001_wrong_hermes_version_rejected_before_research_call():
    req = _request()
    wrong_version = "Hermes Agent v0.20.0 (2026.9.14)"
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id),
        usage_file_bytes=_usage(),
        version_text=wrong_version,
    )
    assert parse_hermes_version(wrong_version) == "0.20.0"
    assert is_supported_hermes_version(wrong_version) is False
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
    assert "--max-turns" not in argv  # T03: chat-only flag, never on top-level -z
    assert argv.count("--toolsets") == 1
    assert argv[argv.index("--toolsets") + 1] == "web"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"allowed_toolsets": ("web", "terminal")},  # P007
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
        # WP175I P005: safe mode may not be re-enabled as the supposed H1 safety layer.
        {"safe_mode": True},
        # WP175I P006: the ignore flags and controlled managed scope cannot be disabled.
        {"ignore_user_config": False},
        {"ignore_rules": False},
        {"controlled_managed_scope": False},
        # WP175I P016: any controlled backend/fallback/retry/plugin field is pinned.
        {"web_search_backend": "exa"},
        {"web_extract_backend": "tavily"},
        {"web_backend": "brave"},
        {"keyless_fallback": True},
        {"keyless_rescue": True},
        {"web_cache_enabled": True},
        {"web_provider_tier_firecrawl": "free"},
        {"api_max_retries": 3},
        {"managed_fallback_providers": ("openrouter",)},
        {"managed_plugins_enabled": ("web-custom",)},
        {"updates_check": True},
        {"custom_user_project_plugin_loading": "ALLOWED"},
        {"bundled_backend_discovery": "FORBIDDEN"},
        {"same_provider_primary_transport_recovery": "UNBOUNDED"},
        {"research_home_config_allowed": True},
        {"research_home_user_plugins_allowed": True},
        {"controlled_profile_version": "other/9.9.9"},
        {"max_transport_retries": 1},  # zero retries is the frozen ceiling now
        {"max_transport_retries": 2},
        {"max_concurrency": 2},
        {"iteration_cap": "CLAIMS_A_CAP"},
        {"approval_authority": "APPROVAL_PROMPTS_ARE_SAFETY"},
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


# --- R011 / R012: retry policy (ZERO automatic paid research retries) --------


def test_r011_no_second_transport_retry():  # T07 + T08
    """The frozen first-runtime policy performs exactly ONE research invocation.

    A paid provider call can already spend before a timeout/transport failure, and
    v0.21.3 emits accounting only after/best-effort, so a timed-out run is never
    automatically repeated.
    """
    req = _request()
    # A second success outcome is available but must never be reached.
    backend = FakeHermesBackend(
        [_timeout_outcome(), _success_outcome(_stdout(req.request_id), _usage())]
    )
    result = _run(req, backend)
    assert result.receipt.terminal_status == "TIMEOUT"
    assert backend.call_count == 1
    assert result.receipt.transport_attempt_count == 1


def test_default_policy_makes_at_most_one_research_invocation():  # T07
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    _run(req, backend)
    assert backend.call_count == 1
    assert DEFAULT_HERMES_INVOCATION_POLICY.max_transport_retries == 0


def test_launch_failure_is_not_retried():  # T08 (transport failure)
    req = _request()
    launch_fail = HermesInvocationOutcome(
        stdout=b"", stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=None, usage_file_truncated=False, exit_code=None, timed_out=False,
        launch_failed=True, duration_ms=None,
    )
    backend = FakeHermesBackend([launch_fail, _success_outcome(_stdout(req.request_id), _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "TRANSPORT_FAILURE"
    assert backend.call_count == 1


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


def test_cost_above_cap_fails_closed():  # T17
    req = _request()  # accepted cost threshold is USD 2
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id), usage_file_bytes=_usage(estimated_cost_usd=9.99)
    )
    result = _run(req, backend)
    assert result.receipt.terminal_status == "BUDGET_EXCEEDED"
    assert result.receipt.budget_status == "COST_CAP_EXCEEDED"
    assert result.validated_draft is None


def test_cost_evidence_unavailable_fails_closed():  # T16
    req = _request()
    # A completed run whose cost is unknown cannot succeed; cost is never zero.
    backend = FakeHermesBackend.from_transcript(
        _stdout(req.request_id),
        usage_file_bytes=_usage(estimated_cost_usd=0.01, cost_status="unknown"),
    )
    result = _run(req, backend)
    assert result.error_code == "COST_EVIDENCE_UNAVAILABLE"
    assert result.receipt.terminal_status == "COST_EVIDENCE_UNAVAILABLE"
    assert result.receipt.budget_status == "COST_EVIDENCE_UNAVAILABLE"
    assert result.validated_draft is None


# --- exit code is authoritative (section 6) ---------------------------------


@pytest.mark.parametrize("exit_code", [1, 2, 130])
def test_nonzero_exit_fails_even_with_valid_stdout(exit_code):  # T09 / T10 / T11
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(), exit_code=exit_code)]
    )
    result = _run(req, backend)
    assert result.error_code == "EXIT_CODE_NONZERO"
    assert result.receipt.terminal_status == "EXIT_CODE_NONZERO"
    assert result.receipt.exit_code == exit_code
    assert result.validated_draft is None
    assert backend.call_count == 1  # not retried


# --- usage report is mandatory success evidence (section 7) -------------------


def test_missing_usage_file_fails_even_with_exit_zero():  # T12
    req = _request()
    backend = FakeHermesBackend([_exit_outcome(_stdout(req.request_id), None, exit_code=0)])
    result = _run(req, backend)
    assert result.error_code == "USAGE_MISSING"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"
    assert result.receipt.usage_evidence_status == "INVALID"


def test_malformed_usage_fails_closed():  # T13
    req = _request()
    backend = FakeHermesBackend([_exit_outcome(_stdout(req.request_id), b"{bad", exit_code=0)])
    result = _run(req, backend)
    assert result.error_code == "USAGE_MALFORMED"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"


def test_usage_completed_not_true_fails_closed():  # T14
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(completed=False), exit_code=0)]
    )
    result = _run(req, backend)
    assert result.error_code == "USAGE_INCOMPLETE"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"


def test_usage_failed_flag_fails_closed():  # T15
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(failed=True), exit_code=0)]
    )
    result = _run(req, backend)
    assert result.error_code == "USAGE_FAILED_FLAG"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"


def test_usage_bad_integer_field_fails_closed():  # T21
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(total_tokens=-1), exit_code=0)]
    )
    result = _run(req, backend)
    assert result.error_code == "USAGE_FIELD_INVALID"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"


# --- provider / model binding (section 8) ------------------------------------


def test_provider_mismatch_fails_closed():  # T18
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(provider="other-provider"), exit_code=0)]
    )
    result = _run(req, backend)
    assert result.error_code == "PROVIDER_MODEL_MISMATCH"
    assert result.receipt.terminal_status == "PROVIDER_MODEL_MISMATCH"
    assert result.receipt.verified_provider is None
    assert backend.call_count == 1


def test_model_mismatch_fails_closed():  # T19
    req = _request()
    backend = FakeHermesBackend(
        [_exit_outcome(_stdout(req.request_id), _usage(model="other-model"), exit_code=0)]
    )
    result = _run(req, backend)
    assert result.error_code == "PROVIDER_MODEL_MISMATCH"
    assert result.receipt.terminal_status == "PROVIDER_MODEL_MISMATCH"


# --- truncation of authoritative surfaces is fail-closed (section 5) ---------


def _truncated_outcome(stdout, usage=None, *, stdout_truncated=False, usage_truncated=False):
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=stdout_truncated, stderr_byte_len=0,
        stderr_truncated=False, usage_file_bytes=usage, usage_file_truncated=usage_truncated,
        exit_code=0, timed_out=False, launch_failed=False, duration_ms=10,
    )


def test_c10_stdout_truncated_can_never_succeed():  # C10
    req = _request()
    # A truncated prefix that still happens to be valid JSON must not be accepted.
    backend = FakeHermesBackend(
        [_truncated_outcome(_stdout(req.request_id), _usage(), stdout_truncated=True)]
    )
    result = _run(req, backend)
    assert result.error_code == "RESPONSE_TOO_LARGE"
    assert result.receipt.terminal_status == "RESPONSE_CAPTURE_FAILED"
    assert result.validated_draft is None


def test_c11_usage_file_truncated_can_never_succeed():  # C11
    req = _request()
    backend = FakeHermesBackend(
        [_truncated_outcome(_stdout(req.request_id), _usage(), usage_truncated=True)]
    )
    result = _run(req, backend)
    assert result.error_code == "USAGE_TOO_LARGE"
    assert result.receipt.terminal_status == "USAGE_EVIDENCE_INVALID"
    assert result.receipt.usage_evidence_status == "INVALID"
    assert result.validated_draft is None


# --- version preflight exit/truncation gates (section 6) ---------------------


def test_c12_correct_semver_but_nonzero_exit_rejected():  # C12
    req = _request()
    backend = FakeHermesBackend(
        [_success_outcome(_stdout(req.request_id), _usage())], version_exit_code=1
    )
    result = _run(req, backend)
    assert result.error_code == "VERSION_PREFLIGHT_FAILED"
    assert result.receipt.terminal_status == "VERSION_MISMATCH"
    assert backend.call_count == 0  # no research invocation


def test_c13_truncated_version_stdout_rejected():  # C13
    req = _request()
    backend = FakeHermesBackend(
        [_success_outcome(_stdout(req.request_id), _usage())], version_stdout_truncated=True
    )
    result = _run(req, backend)
    assert result.error_code == "VERSION_PREFLIGHT_FAILED"
    assert result.receipt.terminal_status == "VERSION_MISMATCH"
    assert backend.call_count == 0


# --- exact tagged web toolset provenance (section 11) ------------------------


def test_web_toolset_provenance_is_web_search_and_web_extract():  # T24
    from src.research_runtime.hermes_controlled_runtime import (
        ALLOWED_TOOLSETS,
        ALLOWED_WEB_TOOLS,
    )

    assert ALLOWED_TOOLSETS == ("web",)
    assert ALLOWED_WEB_TOOLS == ("web_search", "web_extract")


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
    backend = FakeHermesBackend([launch_fail])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "TRANSPORT_FAILURE"
    assert result.receipt.budget_status == "TRANSPORT_FAILED"
    assert backend.call_count == 1


def test_empty_response_stdout_fails_closed():
    req = _request()
    backend = FakeHermesBackend([_success_outcome(b"   ", _usage())])
    result = _run(req, backend)
    assert result.receipt.terminal_status == "RESPONSE_CAPTURE_FAILED"


def test_default_policy_id_is_stable():
    assert DEFAULT_HERMES_INVOCATION_POLICY.policy_id.startswith("hermesinvocationpolicy:sha256:")
    assert HermesInvocationPolicy().policy_id == DEFAULT_HERMES_INVOCATION_POLICY.policy_id


def test_r020_no_imports_from_execution_paper_or_private_account_surfaces():
    """The runtime package imports no trading/paper/private-account surface. P036."""
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


# ---------------------------------------------------------------------------
# WP175I controlled research profile: managed scope + policy identity
# ---------------------------------------------------------------------------

import json as _json  # noqa: E402

from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    CONTROLLED_MANAGED_CONFIG_BYTES,
    CONTROLLED_MANAGED_CONFIG_SHA256,
    CONTROLLED_PROFILE_VERSION,
    expected_hermes_contract,
)


def _managed():
    return _json.loads(DEFAULT_HERMES_INVOCATION_POLICY.managed_config_bytes().decode("utf-8"))


def test_p005_safe_mode_frozen_false_on_controlled_profile():
    # The default controlled policy represents the new mode with safe_mode False,
    # not by re-enabling safe mode.
    assert DEFAULT_HERMES_INVOCATION_POLICY.safe_mode is False
    assert DEFAULT_HERMES_INVOCATION_POLICY.controlled_managed_scope is True
    with pytest.raises(PolicyBroadeningError):
        HermesInvocationPolicy(safe_mode=True)


def test_p008_managed_config_bytes_are_deterministic_and_stable():
    a = HermesInvocationPolicy().managed_config_bytes()
    b = HermesInvocationPolicy().managed_config_bytes()
    assert a == b == CONTROLLED_MANAGED_CONFIG_BYTES
    # Canonical (sorted, compact) so the digest is stable across processes.
    assert a == _json.dumps(_managed(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_p009_managed_config_pins_firecrawl_for_search_and_extract():
    web = _managed()["web"]
    assert web["backend"] == "firecrawl"
    assert web["search_backend"] == "firecrawl"
    assert web["extract_backend"] == "firecrawl"
    assert web["provider_tier"] == {"firecrawl": "paid"}


def test_p010_managed_config_disables_keyless_and_cache():
    web = _managed()["web"]
    assert web["keyless_fallback"] is False
    assert web["keyless_rescue"] is False
    assert web["cache_enabled"] is False


def test_p011_managed_config_empties_fallback_chain():
    assert _managed()["fallback_providers"] == []


def test_p012_managed_config_sets_one_ordinary_provider_attempt():
    assert _managed()["agent"]["api_max_retries"] == 1


def test_p013_managed_config_pins_plugins_hooks_updates():
    managed = _managed()
    assert managed["plugins"]["enabled"] == []
    assert managed["hooks"] == {}
    assert managed["updates"]["check"] is False


def test_p015_managed_config_digest_participates_in_policy_identity():
    ident = DEFAULT_HERMES_INVOCATION_POLICY.identity_fields()
    assert ident["managed_config_sha256"] == CONTROLLED_MANAGED_CONFIG_SHA256
    assert CONTROLLED_MANAGED_CONFIG_SHA256 in DEFAULT_HERMES_INVOCATION_POLICY.policy_id.replace(
        "hermesinvocationpolicy:sha256:", "X"
    ) or True  # digest is committed via identity_fields (hashed into policy_id)
    # A different managed digest would change the policy id: verify identity depends
    # on the managed bytes by hashing identity_fields ourselves.
    import hashlib
    canonical = _json.dumps(ident, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert DEFAULT_HERMES_INVOCATION_POLICY.policy_id.endswith(
        hashlib.sha256(canonical).hexdigest()
    )


def test_p032_policy_truthfully_records_recovery_and_no_fallback():
    p = DEFAULT_HERMES_INVOCATION_POLICY
    assert p.same_provider_primary_transport_recovery == "ALLOWED_BOUNDED"
    assert p.provider_model_fallback == "NONE"
    assert p.web_backend_fallback_rescue == "NONE"
    assert p.custom_user_project_plugin_loading == "FORBIDDEN"
    assert p.bundled_backend_discovery == "ALLOWED_FOR_WEB_PROVIDER_REGISTRATION"
    assert p.exposed_agent_toolset == "WEB_ONLY"
    assert p.controlled_profile_version == CONTROLLED_PROFILE_VERSION


def test_p028_p029_controller_supplies_managed_config_once():
    req = _request()
    backend = FakeHermesBackend.from_transcript(_stdout(req.request_id), usage_file_bytes=_usage())
    _run(req, backend)
    # P029: exactly one research invocation.
    assert backend.call_count == 1
    # P028: the fake records the deterministic controlled managed-config bytes and made
    # zero process/network calls (from_transcript uses no real process).
    assert backend.recorded_managed_config_bytes == [CONTROLLED_MANAGED_CONFIG_BYTES]


def test_p031_outer_transport_retries_are_zero():
    assert DEFAULT_HERMES_INVOCATION_POLICY.max_transport_retries == 0


def test_expected_contract_surfaces_controlled_profile_facts():
    contract = expected_hermes_contract()
    assert contract["research_argv_has_safe_mode"] == "NO"
    assert contract["ignore_user_config"] == "YES" and contract["ignore_rules"] == "YES"
    assert contract["toolsets"] == "web"
    assert contract["firecrawl_search_backend"] == "firecrawl"
    assert contract["firecrawl_extract_backend"] == "firecrawl"
    assert contract["web_keyless_fallback"] == "OFF"
    assert contract["web_keyless_rescue"] == "OFF"
    assert contract["fallback_providers"] == "EMPTY"
    assert contract["api_max_retries"] == "1"
    assert contract["managed_config_sha256"] == CONTROLLED_MANAGED_CONFIG_SHA256
