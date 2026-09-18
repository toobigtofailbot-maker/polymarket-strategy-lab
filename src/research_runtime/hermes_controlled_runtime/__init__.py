"""Controlled Hermes research runtime core (WP175H / S10-HERMES-01).

A narrow, reusable, dormant-by-default primitive that wraps one bounded, one-shot,
web-only EXTERNAL Hermes research session in a deterministic control plane:

    validated request -> frozen invocation policy + compact envelope
    -> one ephemeral one-shot Hermes session (fake/local in tests)
    -> bounded stream-json audit capture -> untrusted final research draft
    -> authoritative repo-side schema/safety validation
    -> sanitized research-run receipt -> mandatory human/deterministic review.

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
    QUERY_FILE_NAME,
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
    MAX_ESTIMATED_COST_USD_ABSOLUTE,
    MAX_OUTPUT_BYTES_ABSOLUTE,
    MAX_SOURCES_ABSOLUTE,
    MAX_TURNS_ABSOLUTE,
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
    DEFAULT_HERMES_INVOCATION_POLICY,
    HERMES_EXPECTED_VERSION,
    HERMES_RELEASE,
    HERMES_RELEASE_COMMIT,
    HERMES_RELEASE_TAG,
    HermesInvocationPolicy,
    HermesResearchEnvelope,
    PolicyBroadeningError,
    build_hermes_argv,
    build_research_envelope,
    is_supported_hermes_version,
)
from .runner import (
    ExternalHermesCliBackend,
    FakeHermesBackend,
    HermesInvocationBackend,
    HermesInvocationOutcome,
)
from .stream_json import (
    StreamJsonAuditResult,
    parse_stream_json,
    tool_calls_within_allowed,
)

__all__ = (
    # controller
    "run_controlled_hermes_research",
    "HermesControlledRunResult",
    "QUERY_FILE_NAME",
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
    "MAX_TURNS_ABSOLUTE",
    "MAX_WALL_SECONDS_ABSOLUTE",
    "MAX_OUTPUT_BYTES_ABSOLUTE",
    "MAX_SOURCES_ABSOLUTE",
    "MAX_ESTIMATED_COST_USD_ABSOLUTE",
    # policy
    "HermesInvocationPolicy",
    "DEFAULT_HERMES_INVOCATION_POLICY",
    "HermesResearchEnvelope",
    "PolicyBroadeningError",
    "build_hermes_argv",
    "build_research_envelope",
    "is_supported_hermes_version",
    "ALLOWED_TOOLSETS",
    "ALLOWED_WEB_TOOLS",
    "HERMES_RELEASE",
    "HERMES_RELEASE_TAG",
    "HERMES_RELEASE_COMMIT",
    "HERMES_EXPECTED_VERSION",
    # runner
    "HermesInvocationBackend",
    "HermesInvocationOutcome",
    "FakeHermesBackend",
    "ExternalHermesCliBackend",
    # stream_json
    "StreamJsonAuditResult",
    "parse_stream_json",
    "tool_calls_within_allowed",
)
