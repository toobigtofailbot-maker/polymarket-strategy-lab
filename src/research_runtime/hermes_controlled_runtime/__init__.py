"""Controlled Hermes research runtime core (WP175H / S10-HERMES-01).

A narrow, reusable, dormant-by-default primitive that wraps one bounded, one-shot,
web-only EXTERNAL Hermes research session in a deterministic control plane, pinned
to the Hermes Agent v0.21.3 tagged contract:

    validated request -> bounded version preflight -> frozen invocation policy +
    compact ``-z`` envelope -> one ephemeral one-shot Hermes session (fake/local in
    tests) -> bounded plain-stdout response + ``--usage-file`` capture -> untrusted
    final research draft -> authoritative repo-side schema/safety validation ->
    sanitized research-run receipt -> mandatory human/deterministic review.

This package has NO trading, paper, execution, live, credential, scheduler, or
merge authority. It creates no opportunity candidate, probability thesis, strategy
family, or trade recommendation. The first real provider-backed run is separately
gated as S10-GATE-H1; code-complete is not runtime-activated.
"""

from __future__ import annotations

from .controller import (
    ACTIVATION_CODE_COMPLETE,
    ACTIVATION_RUN_COMPLETE,
    HermesControlledRunResult,
    expected_hermes_contract,
    run_controlled_hermes_research,
)
from .models import (
    CONFIDENCE_LABELS,
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
    HermesResearchError,
    HermesResearchRunReceipt,
    HermesResearchRunRequest,
    ITERATION_CAP_STATUS,
    MAX_ACCEPTED_ESTIMATED_COST_USD_ABSOLUTE,
    MAX_OUTPUT_BYTES_ABSOLUTE,
    MAX_SOURCES_ABSOLUTE,
    MAX_TRANSPORT_RETRIES_ABSOLUTE,
    MAX_WALL_SECONDS_ABSOLUTE,
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION,
    SanitizedSourceReference,
    ValidatedResearchDraft,
    build_research_run_request,
    derive_receipt_id,
    validate_research_draft,
)
from .policy import (
    ALLOWED_TOOLSETS,
    ALLOWED_WEB_TOOLS,
    APPROVAL_AUTHORITY,
    DEFAULT_HERMES_INVOCATION_POLICY,
    HERMES_EXPECTED_SEMVER,
    HERMES_RELEASE,
    HERMES_RELEASE_COMMIT,
    HERMES_RELEASE_TAG,
    ITERATION_CAP,
    MAX_COMMAND_LINE_CHARS,
    MAX_PROMPT_BYTES,
    RUNTIME_TOOL_TELEMETRY,
    TOOL_ENFORCEMENT,
    USAGE_FILE_NAME,
    HermesInvocationPolicy,
    HermesResearchEnvelope,
    PolicyBroadeningError,
    build_hermes_argv,
    build_research_envelope,
    build_version_argv,
    is_supported_hermes_version,
    parse_hermes_version,
)
from .response_capture import (
    COST_ABOVE_THRESHOLD,
    COST_ACCEPTED,
    COST_EVIDENCE_UNAVAILABLE,
    COST_SOURCE_VOCABULARY,
    COST_STATUS_VOCABULARY,
    KNOWN_COST_STATUSES,
    PRICED_COST_SOURCES,
    ResponseCapture,
    UsageReport,
    capture_final_response,
    cost_acceptance,
    parse_usage_report,
)
from .runner import (
    ExternalHermesCliBackend,
    FakeHermesBackend,
    HermesInvocationBackend,
    HermesInvocationOutcome,
    HermesVersionProbe,
    is_safe_research_home,
)

__all__ = (
    # controller
    "run_controlled_hermes_research",
    "HermesControlledRunResult",
    "ACTIVATION_CODE_COMPLETE",
    "ACTIVATION_RUN_COMPLETE",
    "expected_hermes_contract",
    # models
    "HermesResearchRunRequest",
    "HermesResearchRunReceipt",
    "HermesResearchError",
    "SanitizedSourceReference",
    "ValidatedResearchDraft",
    "build_research_run_request",
    "derive_receipt_id",
    "validate_research_draft",
    "REQUEST_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "DRAFT_SCHEMA_VERSION",
    "DRAFT_AUTHORITY_FLAGS",
    "CONFIDENCE_LABELS",
    "NON_AUTHORITY_NOTICE",
    "ITERATION_CAP_STATUS",
    "MAX_WALL_SECONDS_ABSOLUTE",
    "MAX_OUTPUT_BYTES_ABSOLUTE",
    "MAX_SOURCES_ABSOLUTE",
    "MAX_ACCEPTED_ESTIMATED_COST_USD_ABSOLUTE",
    "MAX_TRANSPORT_RETRIES_ABSOLUTE",
    # policy
    "HermesInvocationPolicy",
    "DEFAULT_HERMES_INVOCATION_POLICY",
    "HermesResearchEnvelope",
    "PolicyBroadeningError",
    "build_hermes_argv",
    "build_version_argv",
    "build_research_envelope",
    "is_supported_hermes_version",
    "parse_hermes_version",
    "ALLOWED_TOOLSETS",
    "ALLOWED_WEB_TOOLS",
    "APPROVAL_AUTHORITY",
    "ITERATION_CAP",
    "TOOL_ENFORCEMENT",
    "RUNTIME_TOOL_TELEMETRY",
    "USAGE_FILE_NAME",
    "MAX_PROMPT_BYTES",
    "MAX_COMMAND_LINE_CHARS",
    "HERMES_RELEASE",
    "HERMES_RELEASE_TAG",
    "HERMES_RELEASE_COMMIT",
    "HERMES_EXPECTED_SEMVER",
    # response capture
    "ResponseCapture",
    "UsageReport",
    "capture_final_response",
    "parse_usage_report",
    "cost_acceptance",
    "COST_ACCEPTED",
    "COST_ABOVE_THRESHOLD",
    "COST_EVIDENCE_UNAVAILABLE",
    "KNOWN_COST_STATUSES",
    "COST_STATUS_VOCABULARY",
    "COST_SOURCE_VOCABULARY",
    "PRICED_COST_SOURCES",
    # runner
    "HermesInvocationBackend",
    "HermesInvocationOutcome",
    "HermesVersionProbe",
    "FakeHermesBackend",
    "ExternalHermesCliBackend",
    "is_safe_research_home",
)
