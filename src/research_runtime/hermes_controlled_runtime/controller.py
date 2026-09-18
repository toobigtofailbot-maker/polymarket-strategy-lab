"""Deterministic controller for one bounded, one-shot Hermes research session.

The controller owns the full lifecycle:

  validated ``HermesResearchRunRequest``
  -> frozen ``HermesInvocationPolicy`` + compact research envelope
  -> exactly one backend invocation (with at most one transport retry)
  -> bounded stream-json audit parse
  -> exact Hermes version + tool-isolation gate
  -> authoritative untrusted-draft schema + safety validation
  -> sanitized ``HermesResearchRunReceipt`` + mandatory human review flag

It never retries on content/schema/safety failure, never auto-tops-up budget,
never falls back to another provider, and always fails closed with a sanitized
receipt that echoes no raw payload, stderr, environment, secret, or path.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
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
    sha256_hex,
    validate_research_draft,
)
from .policy import (
    DEFAULT_HERMES_INVOCATION_POLICY,
    HERMES_EXPECTED_VERSION,
    HERMES_RELEASE,
    HermesInvocationPolicy,
    build_hermes_argv,
    build_research_envelope,
    is_supported_hermes_version,
)
from .runner import HermesInvocationBackend
from .stream_json import STREAM_OK, parse_stream_json, tool_calls_within_allowed

QUERY_FILE_NAME = "research_query.json"

ACTIVATION_CODE_COMPLETE = "CODE_COMPLETE_NOT_REMOTE_ACTIVATED"
ACTIVATION_RUN_COMPLETE = "CONTROLLED_RESEARCH_RUN_COMPLETE"

# Terminal statuses (closed vocabulary).
_STATUS_SUCCESS = "RESEARCH_DRAFT_VALIDATED"
_STATUS_TRANSPORT = "TRANSPORT_FAILURE"
_STATUS_TIMEOUT = "TIMEOUT"
_STATUS_VERSION = "VERSION_MISMATCH"
_STATUS_STREAM = "STREAM_PARSE_FAILED"
_STATUS_HERMES_ERROR = "HERMES_ERROR"
_STATUS_TOOL_ISOLATION = "TOOL_ISOLATION_VIOLATION"
_STATUS_OUTPUT_SCHEMA = "OUTPUT_SCHEMA_INVALID"
_STATUS_SAFETY = "SAFETY_VALIDATION_FAILED"

_SAFETY_PASS = "PASS"
_SAFETY_FAILED = "FAILED"
_SAFETY_NOT_REACHED = "NOT_REACHED"

_BUDGET_WITHIN = "WITHIN_CAPS"
_BUDGET_TIMEOUT = "TIMEOUT_CAP_REACHED"
_BUDGET_TRANSPORT = "TRANSPORT_FAILED"
_BUDGET_OUTPUT = "OUTPUT_CAP_REACHED"


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

    envelope = build_research_envelope(request)
    argv = build_hermes_argv(executable_path, request, QUERY_FILE_NAME, policy)
    query_bytes = envelope.to_query_bytes()

    max_stderr_bytes = 65_536
    outcome = None
    transport_attempts = 0
    # Exactly one invocation plus at most ``policy.max_transport_retries`` retries.
    max_invocations = 1 + policy.max_transport_retries
    while transport_attempts < max_invocations:
        transport_attempts += 1
        outcome = backend.invoke(
            argv=argv,
            query_bytes=query_bytes,
            query_file_name=QUERY_FILE_NAME,
            max_stdout_bytes=request.max_output_bytes,
            max_stderr_bytes=max_stderr_bytes,
            max_wall_seconds=request.max_wall_seconds,
        )
        if not outcome.transport_retry_eligible:
            break

    assert outcome is not None
    end = clock()

    builder = _ReceiptBuilder(
        request=request,
        policy=policy,
        start_utc=_utc_iso(start),
        end_utc=_utc_iso(end),
        transport_attempt_count=transport_attempts,
        activation_state=activation_state,
    )

    # --- Transport-level terminal outcomes (fail closed, no parse) ---
    if outcome.launch_failed:
        return builder.failure(
            _STATUS_TRANSPORT, "TRANSPORT_FAILURE", budget=_BUDGET_TRANSPORT,
            stdout_truncated=outcome.stdout_truncated, stderr_truncated=outcome.stderr_truncated,
        )
    if outcome.timed_out:
        return builder.failure(
            _STATUS_TIMEOUT, "BACKEND_TIMEOUT", budget=_BUDGET_TIMEOUT,
            stdout_truncated=outcome.stdout_truncated, stderr_truncated=outcome.stderr_truncated,
        )

    audit = parse_stream_json(outcome.stdout, max_bytes=request.max_output_bytes)
    stdout_truncated = outcome.stdout_truncated
    stderr_truncated = outcome.stderr_truncated

    if audit.diagnostic != STREAM_OK:
        budget = _BUDGET_OUTPUT if "TOO_LARGE" in audit.diagnostic else _BUDGET_WITHIN
        return builder.failure(
            _STATUS_STREAM, audit.diagnostic, budget=budget, audit=audit,
            stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
        )

    # Exact pinned Hermes version gate (R001).
    if not is_supported_hermes_version(audit.reported_version):
        return builder.failure(
            _STATUS_VERSION, "BACKEND_VERSION_MISMATCH", budget=_BUDGET_WITHIN, audit=audit,
            stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
        )

    # Tool isolation gate (R004/R005): only permitted ``web`` tools may appear.
    if not tool_calls_within_allowed(audit):
        return builder.failure(
            _STATUS_TOOL_ISOLATION, "TOOL_ISOLATION_VIOLATION", budget=_BUDGET_WITHIN,
            audit=audit, stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
        )

    if not audit.ok or audit.final_text is None:
        return builder.failure(
            _STATUS_HERMES_ERROR, "HERMES_ERROR", budget=_BUDGET_WITHIN, audit=audit,
            stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
        )

    # Authoritative untrusted-draft validation. No retry on any failure (R012).
    try:
        draft = validate_research_draft(
            audit.final_text,
            expected_request_id=request.request_id,
            max_sources=request.max_sources,
        )
    except HermesResearchError as exc:
        if exc.code == "DRAFT_UNSAFE_CONTENT":
            return builder.failure(
                _STATUS_SAFETY, exc.code, budget=_BUDGET_WITHIN, audit=audit,
                safety=_SAFETY_FAILED, output_schema_valid=False,
                stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
            )
        return builder.failure(
            _STATUS_OUTPUT_SCHEMA, exc.code, budget=_BUDGET_WITHIN, audit=audit,
            output_schema_valid=False,
            stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
        )

    receipt = builder.build(
        terminal_status=_STATUS_SUCCESS,
        audit=audit,
        output_schema_valid=True,
        safety=_SAFETY_PASS,
        budget=_BUDGET_WITHIN,
        source_references=draft.source_references,
        source_url_count=len(draft.source_urls),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
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

    def _provider(self, audit_provider: str | None) -> str:
        return audit_provider or self.request.provider_label

    def _model(self, audit_model: str | None) -> str:
        return audit_model or self.request.model_label

    def build(
        self,
        *,
        terminal_status: str,
        audit,
        output_schema_valid: bool,
        safety: str,
        budget: str,
        source_references: tuple[SanitizedSourceReference, ...],
        source_url_count: int,
        stdout_truncated: bool,
        stderr_truncated: bool,
    ) -> HermesResearchRunReceipt:
        reported_version = getattr(audit, "reported_version", None)
        hermes_version = reported_version if reported_version else HERMES_RELEASE
        tool_counts = tuple(getattr(audit, "tool_call_counts", ()) or ())
        partial = HermesResearchRunReceipt(
            receipt_id="",
            schema_version=RECEIPT_SCHEMA_VERSION,
            request_id=self.request.request_id,
            policy_id=self.policy.policy_id,
            hermes_version=hermes_version,
            provider_label=self._provider(getattr(audit, "reported_provider", None)),
            model_label=self._model(getattr(audit, "reported_model", None)),
            start_utc=self.start_utc,
            end_utc=self.end_utc,
            terminal_status=terminal_status,
            transport_attempt_count=self.transport_attempt_count,
            timed_out=terminal_status == _STATUS_TIMEOUT,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            tool_call_counts=tool_counts,
            source_url_count=source_url_count,
            source_references=source_references,
            output_schema_valid=output_schema_valid,
            safety_validation_status=safety,
            token_input_count=getattr(audit, "input_tokens", None),
            token_output_count=getattr(audit, "output_tokens", None),
            estimated_cost_usd=getattr(audit, "estimated_cost_usd", None),
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
        audit=None,
        safety: str = _SAFETY_NOT_REACHED,
        output_schema_valid: bool = False,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
    ) -> HermesControlledRunResult:
        source_refs: tuple[SanitizedSourceReference, ...] = ()
        source_url_count = 0
        if audit is not None:
            source_url_count = len(getattr(audit, "source_urls", ()) or ())
            source_refs = tuple(
                SanitizedSourceReference(url_digest=sha256_hex(url.encode("utf-8")), source_class="other_public")
                for url in (getattr(audit, "source_urls", ()) or ())
            )
        receipt = self.build(
            terminal_status=terminal_status,
            audit=audit if audit is not None else _EMPTY_AUDIT,
            output_schema_valid=output_schema_valid,
            safety=safety,
            budget=budget,
            source_references=source_refs,
            source_url_count=source_url_count,
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


class _EmptyAudit:
    reported_version = None
    reported_provider = None
    reported_model = None
    tool_call_counts: tuple[tuple[str, int], ...] = ()
    input_tokens = None
    output_tokens = None
    estimated_cost_usd = None
    source_urls: tuple[str, ...] = ()


_EMPTY_AUDIT = _EmptyAudit()


def expected_hermes_contract() -> dict[str, str]:
    """Return the pinned external contract summary for status/PR evidence."""
    return {
        "hermes_release": HERMES_RELEASE,
        "hermes_expected_version": HERMES_EXPECTED_VERSION,
    }
