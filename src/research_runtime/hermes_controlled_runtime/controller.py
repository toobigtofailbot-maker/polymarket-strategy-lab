"""Deterministic controller for one bounded, one-shot Hermes research session.

The controller owns the full lifecycle against the pinned Hermes v0.21.3 contract:

  validated ``HermesResearchRunRequest``
  -> bounded no-network version preflight (``hermes --version`` == 0.21.3)
  -> frozen ``HermesInvocationPolicy`` + compact ``-z`` research envelope
  -> exactly one backend invocation (ZERO automatic paid research retries)
  -> authoritative process-exit-code gate (only exit 0 may proceed)
  -> bounded plain-stdout final response capture + bounded ``--usage-file`` parse
  -> mandatory valid usage-file success evidence (completed/failed/tokens/labels)
  -> static exact-toolset enforcement (v0.21.3 emits no runtime tool telemetry)
  -> authoritative untrusted-draft schema + safety validation
  -> verified provider/model binding (usage == request)
  -> POST-RUN cost-acceptance gate (unknown cost fails closed; over-threshold fails)
  -> sanitized ``HermesResearchRunReceipt`` + mandatory human review flag

It performs no automatic paid research retry (a paid provider call can spend before
a timeout/transport failure and v0.21.3 emits accounting only after/best-effort), it
never retries on exit-code/usage/content/schema/safety/cost failure, never auto-tops-
up budget, never falls back to another provider, and always fails closed with a
sanitized receipt that echoes no raw payload, stderr, environment, secret, or path.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Callable, Mapping

from .models import (
    DRAFT_DIAGNOSTICS_NOT_REACHED,
    DraftStructureDiagnostics,
    HermesResearchError,
    HermesResearchRunReceipt,
    HermesResearchRunRequest,
    ITERATION_CAP_STATUS,
    SanitizedSourceReference,
    RECEIPT_SCHEMA_VERSION,
    ValidatedResearchDraft,
    build_research_run_request,
    derive_receipt_id,
    inspect_research_draft_structure,
    sha256_hex,
    validate_research_draft,
)
from .policy import (
    APPROVAL_AUTHORITY,
    DEFAULT_HERMES_INVOCATION_POLICY,
    HERMES_EXPECTED_SEMVER,
    HermesInvocationPolicy,
    RUNTIME_TOOL_TELEMETRY,
    USAGE_FILE_NAME,
    build_hermes_argv,
    build_research_envelope,
    build_version_argv,
    is_supported_hermes_version,
    parse_hermes_version,
    validate_executable_path,
)
from .response_capture import (
    COST_ABOVE_THRESHOLD,
    COST_ACCEPTED,
    COST_EVIDENCE_UNAVAILABLE,
    RESPONSE_OK,
    UsageReport,
    capture_final_response,
    cost_acceptance,
    parse_usage_report,
)
from .runner import HermesInvocationBackend, STDERR_STATUS_EMPTY
from .session_evidence import HermesSessionEvidence, collect_hermes_session_evidence

ACTIVATION_CODE_COMPLETE = "CODE_COMPLETE_NOT_REMOTE_ACTIVATED"
ACTIVATION_RUN_COMPLETE = "CONTROLLED_RESEARCH_RUN_COMPLETE"

# Terminal statuses (closed vocabulary).
_STATUS_SUCCESS = "RESEARCH_DRAFT_VALIDATED"
_STATUS_TRANSPORT = "TRANSPORT_FAILURE"
_STATUS_TIMEOUT = "TIMEOUT"
_STATUS_VERSION = "VERSION_MISMATCH"
_STATUS_EXIT = "EXIT_CODE_NONZERO"
_STATUS_RESPONSE = "RESPONSE_CAPTURE_FAILED"
_STATUS_USAGE = "USAGE_EVIDENCE_INVALID"
_STATUS_OUTPUT_SCHEMA = "OUTPUT_SCHEMA_INVALID"
_STATUS_SAFETY = "SAFETY_VALIDATION_FAILED"
_STATUS_PROVIDER_MODEL = "PROVIDER_MODEL_MISMATCH"
_STATUS_COST_UNAVAILABLE = "COST_EVIDENCE_UNAVAILABLE"
_STATUS_BUDGET = "BUDGET_EXCEEDED"
# WP175L: a startup/profile-init preflight failure. Terminal and pre-research; it is
# NOT a research invocation and leaves transport_attempt_count = 0 (no H1 slot spent).
_STATUS_STARTUP = "STARTUP_PREFLIGHT_FAILED"

_SAFETY_PASS = "PASS"
_SAFETY_FAILED = "FAILED"
_SAFETY_NOT_REACHED = "NOT_REACHED"

_USAGE_VALID = "VALID"
_USAGE_INVALID = "INVALID"
_USAGE_NOT_REACHED = "NOT_REACHED"

_BUDGET_WITHIN = "WITHIN_CAPS"
_BUDGET_TIMEOUT = "TIMEOUT_CAP_REACHED"
_BUDGET_TRANSPORT = "TRANSPORT_FAILED"
_BUDGET_OUTPUT = "OUTPUT_CAP_REACHED"
_BUDGET_COST = "COST_CAP_EXCEEDED"
_BUDGET_COST_UNAVAILABLE = "COST_EVIDENCE_UNAVAILABLE"
_BUDGET_USAGE_INVALID = "USAGE_EVIDENCE_INVALID"
_BUDGET_NOT_REACHED = "NOT_REACHED"

_MAX_STDERR_BYTES = 65_536
_MAX_USAGE_BYTES = 65_536
_VERSION_PROBE_MAX_BYTES = 4_096
_VERSION_PROBE_MAX_SECONDS = 15
# WP175L startup/profile-init preflight bounds. ``hermes --help`` prints a few KB of
# help text and exits; the output is discarded (only launch/exit/timeout matter).
_STARTUP_PROBE_MAX_BYTES = 16_384
_STARTUP_PROBE_MAX_SECONDS = 20


def build_startup_argv(executable_path: str) -> tuple[str, str]:
    """Build the argv for the bounded OFFLINE startup/profile-init preflight (WP175L).

    ``hermes --help`` exercises the pinned ``_apply_profile_override()`` ->
    ``get_default_hermes_root()`` -> ``_get_platform_default_hermes_home()`` path that
    the ``--version`` fast path skips, then argparse prints help and exits before any
    agent/research/provider/Firecrawl work. argv only; the executable path is validated
    with the same guard as every other Hermes argv (no shell, no metacharacters).
    """
    return (validate_executable_path(executable_path), "--help")


@dataclasses.dataclass(frozen=True)
class HermesControlledRunResult:
    """Immutable controller result. A receipt is always produced (fail-closed)."""

    receipt: HermesResearchRunReceipt
    validated_draft: ValidatedResearchDraft | None
    error_code: str | None
    request_id: str
    policy_id: str
    session_evidence: HermesSessionEvidence | None = None


def _utc_iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_controlled_hermes_research(
    request: HermesResearchRunRequest | Mapping[str, object],
    backend: HermesInvocationBackend,
    *,
    executable_path: str = "hermes",
    policy: HermesInvocationPolicy = DEFAULT_HERMES_INVOCATION_POLICY,
    clock: Callable[[], datetime] | None = None,
    activation_state: str = ACTIVATION_CODE_COMPLETE,
    hermes_home: str | None = None,
    context_mode: bool = False,
    allowed_subject_refs: tuple[str, ...] | None = None,
    strategy_mode: bool = False,
    strategy_parameter_names: tuple[str, ...] | None = None,
) -> HermesControlledRunResult:
    """Execute one controlled research run and return a sanitized result.

    ``strategy_mode`` (S10-HERMES-STRAT-01, default off) selects the strategy-assessment
    output contract; it requires ``strategy_parameter_names`` and is mutually exclusive
    with ``context_mode``. Both conditions fail closed before any probe or invocation.
    """
    if context_mode and strategy_mode:
        raise HermesResearchError("STRATEGY_MODE_INVALID")
    if strategy_mode and strategy_parameter_names is None:
        raise HermesResearchError("STRATEGY_MODE_INVALID")
    if isinstance(request, Mapping):
        request = build_research_run_request(request)
    elif not isinstance(request, HermesResearchRunRequest):
        raise HermesResearchError("REQUEST_SCHEMA_INVALID")
    if activation_state not in (ACTIVATION_CODE_COMPLETE, ACTIVATION_RUN_COMPLETE):
        activation_state = ACTIVATION_CODE_COMPLETE

    clock = clock or (lambda: datetime.now(timezone.utc))
    start = clock()
    builder = _ReceiptBuilder(
        request=request,
        policy=policy,
        start_utc=_utc_iso(start),
        end_utc=_utc_iso(start),
        transport_attempt_count=0,
        activation_state=activation_state,
    )

    # --- Version preflight (R001): isolated, update-check-disabled probe; no
    # provider/research call is made. The probe runs in a throwaway HERMES_HOME whose
    # config disables the passive update check, so it makes no network access. The
    # probe must launch, not time out, exit 0, not truncate its version stdout, and
    # report exactly 0.21.3; otherwise no research invocation happens. ---
    probe = backend.probe_version(
        version_argv=build_version_argv(executable_path),
        max_output_bytes=_VERSION_PROBE_MAX_BYTES,
        max_wall_seconds=_VERSION_PROBE_MAX_SECONDS,
    )
    reported_semver = parse_hermes_version(probe.version_text)
    preflight_broken = (
        not probe.launched
        or probe.timed_out
        or probe.exit_code != 0
        or probe.stdout_truncated
    )
    if preflight_broken or not is_supported_hermes_version(probe.version_text):
        # A clean-but-wrong reported version is a version mismatch; a launch/timeout/
        # nonzero-exit/truncated-stdout probe is a preflight failure. Both are terminal
        # VERSION_MISMATCH with no research invocation.
        error_code = "VERSION_PREFLIGHT_FAILED" if preflight_broken else "BACKEND_VERSION_MISMATCH"
        builder.end_utc = _utc_iso(clock())
        return builder.failure(
            _STATUS_VERSION, error_code, budget=_BUDGET_NOT_REACHED,
            reported_semver=reported_semver,
        )

    # --- Startup/profile-init preflight (R00x, WP175L): the ``--version`` fast path
    # never exercises Hermes profile/default-home resolution, so a version-clean binary
    # can still fail at startup (H1 #2: ``RuntimeError: Could not determine home
    # directory.``). This SECOND preflight runs ``hermes --help`` -- which the pinned
    # tagged CLI resolves through ``_apply_profile_override()`` BEFORE argparse exits --
    # in the SAME sanitized runtime envelope and a throwaway HERMES_HOME. It is offline:
    # no provider, model, Firecrawl, or research call. A launch failure, timeout, or
    # nonzero exit is terminal STARTUP_PREFLIGHT_FAILED with NO research invocation, so
    # transport_attempt_count stays 0 and no future H1 research slot is consumed. ---
    startup = backend.probe_startup(
        startup_argv=build_startup_argv(executable_path),
        max_output_bytes=_STARTUP_PROBE_MAX_BYTES,
        max_wall_seconds=_STARTUP_PROBE_MAX_SECONDS,
    )
    if not startup.launched or startup.timed_out or startup.exit_code != 0:
        builder.end_utc = _utc_iso(clock())
        return builder.failure(
            _STATUS_STARTUP, "STARTUP_PREFLIGHT_FAILED", budget=_BUDGET_NOT_REACHED,
            reported_semver=reported_semver,
        )

    if context_mode and not allowed_subject_refs:
        raise HermesResearchError("CONTEXT_CLAIM_INVALID")
    strategy_kwargs: dict[str, object] = {}
    if strategy_mode:
        strategy_kwargs = {
            "strategy_mode": True, "strategy_parameter_names": strategy_parameter_names,
        }
    envelope = build_research_envelope(
        request, context_mode=context_mode, allowed_subject_refs=allowed_subject_refs,
        **strategy_kwargs,  # type: ignore[arg-type]
    )
    prompt_text = envelope.to_prompt_string()
    argv = build_hermes_argv(executable_path, request, prompt_text, policy, USAGE_FILE_NAME)
    # WP175M: bind the exact canonical prompt bytes and the machine-generated draft
    # output contract into the receipt evidence. Set once the envelope exists; the
    # pre-research (version/startup preflight) paths leave these as deterministic None.
    builder.prompt_envelope_sha256 = envelope.envelope_digest
    builder.draft_output_contract_sha256 = envelope.draft_output_contract_digest
    # WP175I: the deterministic non-secret controlled managed-scope config bytes are
    # frozen by the policy and handed to the backend, which writes them into an
    # ephemeral HERMES_MANAGED_DIR/config.yaml for the child. The controller neither
    # writes the config to disk nor sets any environment variable.
    managed_config_bytes = policy.managed_config_bytes()

    outcome = None
    transport_attempts = 0
    max_invocations = 1 + policy.max_transport_retries
    while transport_attempts < max_invocations:
        transport_attempts += 1
        outcome = backend.invoke(
            argv=argv,
            usage_file_name=USAGE_FILE_NAME,
            max_stdout_bytes=request.max_output_bytes,
            max_stderr_bytes=_MAX_STDERR_BYTES,
            max_usage_bytes=_MAX_USAGE_BYTES,
            max_wall_seconds=request.max_wall_seconds,
            hermes_home=hermes_home,
            managed_config_bytes=managed_config_bytes,
        )
        if not outcome.transport_retry_eligible:
            break

    assert outcome is not None
    builder.transport_attempt_count = transport_attempts
    builder.end_utc = _utc_iso(clock())
    builder.reported_semver = reported_semver
    builder.exit_code = outcome.exit_code
    # WP175K: preserve the sanitized failure evidence for EVERY research-child path
    # (transport failure, timeout, exit-code, truncation, downstream gates). This is
    # evidence only; it never changes terminal status, error code, or retry.
    builder.stderr_captured_byte_len = outcome.stderr_byte_len
    builder.stderr_sanitization_status = outcome.stderr_sanitization_status
    builder.stderr_excerpt = outcome.stderr_excerpt
    builder.stderr_excerpt_truncated = outcome.stderr_excerpt_truncated
    builder.stderr_redaction_applied = outcome.stderr_redaction_applied
    builder.usage_file_present = outcome.usage_file_bytes is not None
    builder.usage_file_truncated = outcome.usage_file_truncated
    st = outcome.stdout_truncated
    se = outcome.stderr_truncated

    if outcome.launch_failed:
        return builder.failure(_STATUS_TRANSPORT, "TRANSPORT_FAILURE", budget=_BUDGET_TRANSPORT,
                               stdout_truncated=st, stderr_truncated=se)
    if outcome.timed_out:
        return builder.failure(_STATUS_TIMEOUT, "BACKEND_TIMEOUT", budget=_BUDGET_TIMEOUT,
                               stdout_truncated=st, stderr_truncated=se)

    # Process exit code is authoritative (section 6): only exit_code == 0 may proceed
    # toward success. Any other code fails closed even with syntactically valid stdout;
    # usage accounting is still preserved if safely available. No retry.
    usage = parse_usage_report(outcome.usage_file_bytes, max_bytes=_MAX_USAGE_BYTES)
    builder.usage = usage
    if outcome.exit_code != 0:
        return builder.failure(_STATUS_EXIT, "EXIT_CODE_NONZERO", budget=_BUDGET_NOT_REACHED,
                               stdout_truncated=st, stderr_truncated=se)

    # Truncation of either authoritative surface is fail-closed BEFORE parsing
    # (section 5): a truncated prefix can be syntactically valid but is not the real
    # output, so it must never yield a successful receipt.
    if outcome.stdout_truncated:
        return builder.failure(_STATUS_RESPONSE, "RESPONSE_TOO_LARGE", budget=_BUDGET_OUTPUT,
                               stdout_truncated=st, stderr_truncated=se)
    if outcome.usage_file_truncated:
        builder.usage_evidence_status = _USAGE_INVALID
        return builder.failure(_STATUS_USAGE, "USAGE_TOO_LARGE", budget=_BUDGET_USAGE_INVALID,
                               stdout_truncated=st, stderr_truncated=se)

    response = capture_final_response(outcome.stdout, max_bytes=request.max_output_bytes)
    if response.diagnostic != RESPONSE_OK or response.final_text is None:
        budget = _BUDGET_OUTPUT if "TOO_LARGE" in response.diagnostic else _BUDGET_WITHIN
        return builder.failure(_STATUS_RESPONSE, response.diagnostic, budget=budget,
                               stdout_truncated=st, stderr_truncated=se)

    # A valid usage report is mandatory success evidence (section 7). A missing,
    # malformed, incomplete, failed, or field-invalid usage report fails closed even
    # when Hermes exited 0 and stdout is syntactically valid. No retry.
    if not usage.ok:
        builder.usage_evidence_status = _USAGE_INVALID
        return builder.failure(_STATUS_USAGE, usage.diagnostic, budget=_BUDGET_USAGE_INVALID,
                               stdout_truncated=st, stderr_truncated=se)
    builder.usage_evidence_status = _USAGE_VALID

    # WP175M (section 10): with valid usage, preserve the ACTUAL provider/model evidence
    # BEFORE draft validation so a downstream schema failure still records them (H1 #3
    # kept them null because validation ran first). This does not change failure
    # precedence: the provider/model MISMATCH terminal gate still runs after schema
    # validation below. The sanitized session-id digest anchors future read-only
    # forensics; the raw session id is never retained in the receipt.
    builder.verified_provider = usage.provider
    builder.verified_model = usage.model
    if usage.session_id:
        builder.usage_session_id_digest = sha256_hex(usage.session_id.encode("utf-8"))
        if hermes_home is not None:
            builder.session_evidence = collect_hermes_session_evidence(
                hermes_home, session_id=usage.session_id,
                configured_backend=policy.web_backend,
            )

    # WP175M (section 8): sanitized structural diagnostics for the untrusted draft. Only
    # static canonical field-name tokens and fixed statuses are retained -- never a
    # rejected value, research text, URL, or arbitrary model-supplied key.
    diagnostics = inspect_research_draft_structure(response.final_text)
    builder.set_draft_diagnostics(diagnostics)

    # Authoritative untrusted-draft validation. No retry on any failure (R012).
    try:
        draft = validate_research_draft(
            response.final_text,
            expected_request_id=request.request_id,
            max_sources=request.max_sources,
            context_mode=context_mode,
            allowed_subject_refs=allowed_subject_refs,
            **strategy_kwargs,  # type: ignore[arg-type]
        )
    except HermesResearchError as exc:
        if exc.code == "DRAFT_UNSAFE_CONTENT":
            return builder.failure(_STATUS_SAFETY, exc.code, budget=_BUDGET_WITHIN,
                                   safety=_SAFETY_FAILED, output_schema_valid=False,
                                   stdout_truncated=st, stderr_truncated=se)
        return builder.failure(_STATUS_OUTPUT_SCHEMA, exc.code, budget=_BUDGET_WITHIN,
                               output_schema_valid=False, stdout_truncated=st, stderr_truncated=se)

    # Provider/model binding (section 8): the VERIFIED actual usage provider/model
    # must equal the frozen request labels. Mismatch fails closed with no retry.
    if usage.provider != request.provider_label or usage.model != request.model_label:
        return builder.failure(_STATUS_PROVIDER_MODEL, "PROVIDER_MODEL_MISMATCH",
                               budget=_BUDGET_WITHIN, output_schema_valid=True,
                               safety=_SAFETY_PASS, stdout_truncated=st, stderr_truncated=se)

    # POST-RUN cost acceptance (section 9): a run cannot succeed without a known,
    # acceptable cost. Missing/unknown cost is COST_EVIDENCE_UNAVAILABLE (never zero);
    # a known cost above the accepted threshold is BUDGET_EXCEEDED.
    acceptance = cost_acceptance(usage, request.max_accepted_estimated_cost_usd)
    if acceptance == COST_EVIDENCE_UNAVAILABLE:
        return builder.failure(_STATUS_COST_UNAVAILABLE, "COST_EVIDENCE_UNAVAILABLE",
                               budget=_BUDGET_COST_UNAVAILABLE, output_schema_valid=True,
                               safety=_SAFETY_PASS, stdout_truncated=st, stderr_truncated=se)
    if acceptance == COST_ABOVE_THRESHOLD:
        return builder.failure(_STATUS_BUDGET, "COST_CAP_EXCEEDED", budget=_BUDGET_COST,
                               output_schema_valid=True, safety=_SAFETY_PASS,
                               stdout_truncated=st, stderr_truncated=se)
    assert acceptance == COST_ACCEPTED

    # Success binds the VERIFIED actual usage provider/model, not merely the caller's
    # requested labels (which are equal here by the binding check above).
    builder.verified_provider = usage.provider
    builder.verified_model = usage.model
    receipt = builder.build(
        terminal_status=_STATUS_SUCCESS,
        output_schema_valid=True,
        safety=_SAFETY_PASS,
        budget=_BUDGET_WITHIN,
        source_references=draft.source_references,
        source_url_count=len(draft.source_urls),
        stdout_truncated=st,
        stderr_truncated=se,
    )
    return HermesControlledRunResult(
        receipt=receipt,
        validated_draft=draft,
        error_code=None,
        request_id=request.request_id,
        policy_id=policy.policy_id,
        session_evidence=builder.session_evidence,
    )


@dataclasses.dataclass
class _ReceiptBuilder:
    request: HermesResearchRunRequest
    policy: HermesInvocationPolicy
    start_utc: str
    end_utc: str
    transport_attempt_count: int
    activation_state: str
    reported_semver: str | None = None
    usage: UsageReport | None = None
    exit_code: int | None = None
    verified_provider: str | None = None
    verified_model: str | None = None
    usage_evidence_status: str = _USAGE_NOT_REACHED
    # WP175K sanitized failure evidence. Defaults are the no-child / preflight shape;
    # they are overwritten from the invocation outcome for any research-child path.
    stderr_captured_byte_len: int = 0
    stderr_sanitization_status: str = STDERR_STATUS_EMPTY
    stderr_excerpt: str | None = None
    stderr_excerpt_truncated: bool = False
    stderr_redaction_applied: bool = False
    usage_file_present: bool = False
    usage_file_truncated: bool = False
    # WP175M sanitized additive evidence (receipt schema 1.3.0). Defaults are the
    # deterministic pre-research / no-draft shape; they are overwritten once the
    # envelope is built and once a draft is inspected.
    prompt_envelope_sha256: str | None = None
    draft_output_contract_sha256: str | None = None
    draft_diagnostics_status: str = DRAFT_DIAGNOSTICS_NOT_REACHED
    draft_present_required_fields: tuple[str, ...] = ()
    draft_missing_required_fields: tuple[str, ...] = ()
    draft_first_missing_field: str | None = None
    usage_session_id_digest: str | None = None
    session_evidence: HermesSessionEvidence | None = None

    def set_draft_diagnostics(self, diagnostics: DraftStructureDiagnostics) -> None:
        self.draft_diagnostics_status = diagnostics.status
        self.draft_present_required_fields = diagnostics.present_required_fields
        self.draft_missing_required_fields = diagnostics.missing_required_fields
        self.draft_first_missing_field = diagnostics.first_missing_field

    def build(
        self,
        *,
        terminal_status: str,
        output_schema_valid: bool,
        safety: str,
        budget: str,
        source_references: tuple[SanitizedSourceReference, ...],
        source_url_count: int,
        stdout_truncated: bool,
        stderr_truncated: bool,
    ) -> HermesResearchRunReceipt:
        usage = self.usage
        hermes_version = self.reported_semver or HERMES_EXPECTED_SEMVER
        partial = HermesResearchRunReceipt(
            receipt_id="",
            schema_version=RECEIPT_SCHEMA_VERSION,
            request_id=self.request.request_id,
            policy_id=self.policy.policy_id,
            hermes_version=hermes_version,
            provider_label=self.request.provider_label,
            model_label=self.request.model_label,
            verified_provider=self.verified_provider,
            verified_model=self.verified_model,
            iteration_cap_status=ITERATION_CAP_STATUS,
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            terminal_status=terminal_status,
            exit_code=self.exit_code,
            transport_attempt_count=self.transport_attempt_count,
            timed_out=terminal_status == _STATUS_TIMEOUT,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stderr_captured_byte_len=self.stderr_captured_byte_len,
            stderr_sanitization_status=self.stderr_sanitization_status,
            stderr_excerpt=self.stderr_excerpt,
            stderr_excerpt_truncated=self.stderr_excerpt_truncated,
            stderr_redaction_applied=self.stderr_redaction_applied,
            usage_file_present=self.usage_file_present,
            usage_file_truncated=self.usage_file_truncated,
            configured_toolsets=self.policy.allowed_toolsets,
            tool_enforcement=self.policy.tool_enforcement,
            runtime_tool_telemetry=RUNTIME_TOOL_TELEMETRY,
            approval_authority=APPROVAL_AUTHORITY,
            source_url_count=source_url_count,
            source_references=source_references,
            output_schema_valid=output_schema_valid,
            safety_validation_status=safety,
            prompt_envelope_sha256=self.prompt_envelope_sha256,
            draft_output_contract_sha256=self.draft_output_contract_sha256,
            draft_diagnostics_status=self.draft_diagnostics_status,
            draft_present_required_fields=self.draft_present_required_fields,
            draft_missing_required_fields=self.draft_missing_required_fields,
            draft_first_missing_field=self.draft_first_missing_field,
            usage_session_id_digest=self.usage_session_id_digest,
            usage_evidence_status=self.usage_evidence_status,
            usage_completed=getattr(usage, "completed", None),
            usage_failed=getattr(usage, "failed", None),
            token_input_count=getattr(usage, "input_tokens", None),
            token_output_count=getattr(usage, "output_tokens", None),
            total_token_count=getattr(usage, "total_tokens", None),
            api_call_count=getattr(usage, "api_calls", None),
            estimated_cost_usd=getattr(usage, "estimated_cost_usd", None),
            cost_status=getattr(usage, "cost_status", None),
            cost_source=getattr(usage, "cost_source", None),
            budget_status=budget,
            human_review_required=True,
            no_execution_authority=True,
            no_live_authority=True,
            no_credential_authority=True,
            no_risk_authority=True,
            no_paper_authority=True,
            activation_state=self.activation_state,
        )
        receipt_id = derive_receipt_id(partial)
        return dataclasses.replace(partial, receipt_id=receipt_id)

    def failure(
        self,
        terminal_status: str,
        error_code: str,
        *,
        budget: str,
        safety: str = _SAFETY_NOT_REACHED,
        output_schema_valid: bool = False,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
        reported_semver: str | None = None,
    ) -> HermesControlledRunResult:
        if reported_semver is not None:
            self.reported_semver = reported_semver
        receipt = self.build(
            terminal_status=terminal_status,
            output_schema_valid=output_schema_valid,
            safety=safety,
            budget=budget,
            source_references=(),
            source_url_count=0,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
        return HermesControlledRunResult(
            receipt=receipt,
            validated_draft=None,
            error_code=error_code,
            request_id=self.request.request_id,
            policy_id=self.policy.policy_id,
            session_evidence=self.session_evidence,
        )


def expected_hermes_contract(
    policy: HermesInvocationPolicy = DEFAULT_HERMES_INVOCATION_POLICY,
) -> dict[str, str]:
    """Return the pinned external contract + controlled-profile summary for evidence."""
    return {
        "hermes_release": HERMES_EXPECTED_SEMVER,
        "hermes_expected_semver": HERMES_EXPECTED_SEMVER,
        "research_argv_has_safe_mode": "NO",
        "ignore_user_config": "YES",
        "ignore_rules": "YES",
        "toolsets": ",".join(policy.allowed_toolsets),
        "managed_scope_mode": policy.managed_scope_mode,
        "controlled_profile_version": policy.controlled_profile_version,
        "managed_config_sha256": policy.managed_config_sha256,
        "firecrawl_search_backend": policy.web_search_backend,
        "firecrawl_extract_backend": policy.web_extract_backend,
        "web_keyless_fallback": "OFF" if not policy.keyless_fallback else "ON",
        "web_keyless_rescue": "OFF" if not policy.keyless_rescue else "ON",
        "web_cache": "OFF" if not policy.web_cache_enabled else "ON",
        "fallback_providers": "EMPTY" if not policy.managed_fallback_providers else "NONEMPTY",
        "api_max_retries": str(policy.api_max_retries),
        "same_provider_primary_transport_recovery": policy.same_provider_primary_transport_recovery,
        "custom_user_project_plugin_loading": policy.custom_user_project_plugin_loading,
        "bundled_backend_discovery": policy.bundled_backend_discovery,
        "policy_id": policy.policy_id,
    }
