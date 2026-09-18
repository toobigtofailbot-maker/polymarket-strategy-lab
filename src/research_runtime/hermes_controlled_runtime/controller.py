"""Deterministic controller for one bounded, one-shot Hermes research session.

The controller owns the full lifecycle against the pinned Hermes v0.21.3 contract:

  validated ``HermesResearchRunRequest``
  -> bounded no-network version preflight (``hermes --version`` == 0.21.3)
  -> frozen ``HermesInvocationPolicy`` + compact ``-z`` research envelope
  -> exactly one backend invocation (with at most one transport retry)
  -> bounded plain-stdout final response capture + bounded ``--usage-file`` parse
  -> static exact-toolset enforcement (v0.21.3 emits no runtime tool telemetry)
  -> authoritative untrusted-draft schema + safety validation
  -> per-run cost-cap enforcement
  -> sanitized ``HermesResearchRunReceipt`` + mandatory human review flag

It never retries on content/schema/safety failure, never auto-tops-up budget,
never falls back to another provider, and always fails closed with a sanitized
receipt that echoes no raw payload, stderr, environment, secret, or path.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Mapping

from .models import (
    HermesResearchError,
    HermesResearchRunReceipt,
    HermesResearchRunRequest,
    SanitizedSourceReference,
    RECEIPT_SCHEMA_VERSION,
    ValidatedResearchDraft,
    build_research_run_request,
    derive_receipt_id,
    validate_research_draft,
)
from .policy import (
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
)
from .response_capture import (
    RESPONSE_OK,
    capture_final_response,
    cost_within_cap,
    parse_usage_report,
)
from .runner import HermesInvocationBackend

ACTIVATION_CODE_COMPLETE = "CODE_COMPLETE_NOT_REMOTE_ACTIVATED"
ACTIVATION_RUN_COMPLETE = "CONTROLLED_RESEARCH_RUN_COMPLETE"

# Terminal statuses (closed vocabulary).
_STATUS_SUCCESS = "RESEARCH_DRAFT_VALIDATED"
_STATUS_TRANSPORT = "TRANSPORT_FAILURE"
_STATUS_TIMEOUT = "TIMEOUT"
_STATUS_VERSION = "VERSION_MISMATCH"
_STATUS_RESPONSE = "RESPONSE_CAPTURE_FAILED"
_STATUS_OUTPUT_SCHEMA = "OUTPUT_SCHEMA_INVALID"
_STATUS_SAFETY = "SAFETY_VALIDATION_FAILED"
_STATUS_BUDGET = "BUDGET_EXCEEDED"

_SAFETY_PASS = "PASS"
_SAFETY_FAILED = "FAILED"
_SAFETY_NOT_REACHED = "NOT_REACHED"

_BUDGET_WITHIN = "WITHIN_CAPS"
_BUDGET_TIMEOUT = "TIMEOUT_CAP_REACHED"
_BUDGET_TRANSPORT = "TRANSPORT_FAILED"
_BUDGET_OUTPUT = "OUTPUT_CAP_REACHED"
_BUDGET_COST = "COST_CAP_EXCEEDED"
_BUDGET_NOT_REACHED = "NOT_REACHED"

_MAX_STDERR_BYTES = 65_536
_MAX_USAGE_BYTES = 65_536
_VERSION_PROBE_MAX_BYTES = 4_096
_VERSION_PROBE_MAX_SECONDS = 15


@dataclasses.dataclass(frozen=True)
class HermesControlledRunResult:
    """Immutable controller result. A receipt is always produced (fail-closed)."""

    receipt: HermesResearchRunReceipt
    validated_draft: ValidatedResearchDraft | None
    error_code: str | None
    request_id: str
    policy_id: str


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
) -> HermesControlledRunResult:
    """Execute one controlled research run and return a sanitized result."""
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

    # --- Version preflight (R001): no provider/network research call is made. ---
    probe = backend.probe_version(
        version_argv=build_version_argv(executable_path),
        max_output_bytes=_VERSION_PROBE_MAX_BYTES,
        max_wall_seconds=_VERSION_PROBE_MAX_SECONDS,
    )
    reported_semver = parse_hermes_version(probe.version_text)
    if not probe.launched or probe.timed_out or not is_supported_hermes_version(
        probe.version_text
    ):
        builder.end_utc = _utc_iso(clock())
        return builder.failure(
            _STATUS_VERSION, "BACKEND_VERSION_MISMATCH", budget=_BUDGET_NOT_REACHED,
            reported_semver=reported_semver,
        )

    envelope = build_research_envelope(request)
    prompt_text = envelope.to_prompt_string()
    argv = build_hermes_argv(executable_path, request, prompt_text, policy, USAGE_FILE_NAME)

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
        )
        if not outcome.transport_retry_eligible:
            break

    assert outcome is not None
    builder.transport_attempt_count = transport_attempts
    builder.end_utc = _utc_iso(clock())
    builder.reported_semver = reported_semver
    st = outcome.stdout_truncated
    se = outcome.stderr_truncated

    if outcome.launch_failed:
        return builder.failure(_STATUS_TRANSPORT, "TRANSPORT_FAILURE", budget=_BUDGET_TRANSPORT,
                               stdout_truncated=st, stderr_truncated=se)
    if outcome.timed_out:
        return builder.failure(_STATUS_TIMEOUT, "BACKEND_TIMEOUT", budget=_BUDGET_TIMEOUT,
                               stdout_truncated=st, stderr_truncated=se)

    response = capture_final_response(outcome.stdout, max_bytes=request.max_output_bytes)
    usage = parse_usage_report(outcome.usage_file_bytes, max_bytes=_MAX_USAGE_BYTES)
    builder.usage = usage

    if response.diagnostic != RESPONSE_OK or response.final_text is None:
        budget = _BUDGET_OUTPUT if "TOO_LARGE" in response.diagnostic else _BUDGET_WITHIN
        return builder.failure(_STATUS_RESPONSE, response.diagnostic, budget=budget,
                               stdout_truncated=st, stderr_truncated=se)

    # Authoritative untrusted-draft validation. No retry on any failure (R012).
    try:
        draft = validate_research_draft(
            response.final_text,
            expected_request_id=request.request_id,
            max_sources=request.max_sources,
        )
    except HermesResearchError as exc:
        if exc.code == "DRAFT_UNSAFE_CONTENT":
            return builder.failure(_STATUS_SAFETY, exc.code, budget=_BUDGET_WITHIN,
                                   safety=_SAFETY_FAILED, output_schema_valid=False,
                                   stdout_truncated=st, stderr_truncated=se)
        return builder.failure(_STATUS_OUTPUT_SCHEMA, exc.code, budget=_BUDGET_WITHIN,
                               output_schema_valid=False, stdout_truncated=st, stderr_truncated=se)

    # Cost cap: reported estimated cost above the per-run cap fails closed.
    if not cost_within_cap(usage, request.max_estimated_cost_usd):
        return builder.failure(_STATUS_BUDGET, "COST_CAP_EXCEEDED", budget=_BUDGET_COST,
                               output_schema_valid=True, safety=_SAFETY_PASS,
                               stdout_truncated=st, stderr_truncated=se)

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
    usage: object = None

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
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            terminal_status=terminal_status,
            transport_attempt_count=self.transport_attempt_count,
            timed_out=terminal_status == _STATUS_TIMEOUT,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            configured_toolsets=self.policy.allowed_toolsets,
            tool_enforcement=self.policy.tool_enforcement,
            runtime_tool_telemetry=RUNTIME_TOOL_TELEMETRY,
            source_url_count=source_url_count,
            source_references=source_references,
            output_schema_valid=output_schema_valid,
            safety_validation_status=safety,
            token_input_count=getattr(usage, "input_tokens", None),
            token_output_count=getattr(usage, "output_tokens", None),
            total_token_count=getattr(usage, "total_tokens", None),
            estimated_cost_usd=getattr(usage, "estimated_cost_usd", None),
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
        )


def expected_hermes_contract() -> dict[str, str]:
    """Return the pinned external contract summary for status/PR evidence."""
    return {
        "hermes_release": HERMES_EXPECTED_SEMVER,
        "hermes_expected_semver": HERMES_EXPECTED_SEMVER,
    }
