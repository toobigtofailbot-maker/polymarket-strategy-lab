"""Immutable, fail-closed data models for the controlled Hermes research runtime.

This module owns the deterministic request model, the sanitized receipt model, and
the authoritative validator for the untrusted Hermes research draft (WP175H).

Design invariants (see docs/hermes_controlled_research_runtime_contract.md):
  * every public record is a frozen dataclass with a content-addressed identity;
  * validation is fail-closed and never echoes rejected request/output content,
    secrets, raw exception text, filesystem paths, or provider payloads;
  * numeric canonicality: monetary amounts are ``Decimal`` derived from strings or
    integers -- binary ``float`` inputs are rejected where identity depends on them;
  * Hermes output is untrusted bytes: the repository validator here is authoritative
    and never relies on Hermes-native structured output reliability.

No credential, environment value, wallet/account identifier, order identifier,
execution parameter, position size, or live-authorization field is accepted, stored,
transformed, logged, or echoed by any object in this module.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Mapping, Sequence

# ---------------------------------------------------------------------------
# Schema / identity constants
# ---------------------------------------------------------------------------

REQUEST_SCHEMA_VERSION = "hermes-research-run-request/1.1.0"
# WP175M: bumped 1.2.0 -> 1.3.0. The receipt gains sanitized additive evidence fields
# (prompt/contract digests, static draft-structure diagnostics, usage session-id
# digest); historical 1.2.0 H1 #3 receipts remain valid for that run and are not
# rewritten.
RECEIPT_SCHEMA_VERSION = "hermes-research-run-receipt/1.3.0"
DRAFT_SCHEMA_VERSION = "hermes-research-draft/1.0.0"

# WP175M: the canonical machine-generated draft output-contract identifier embedded in
# the prompt envelope's ``draft_output_schema``. It is NOT the draft payload schema
# version (that stays ``DRAFT_SCHEMA_VERSION``); it versions the JSON-schema-like
# contract shape produced by :func:`build_research_draft_output_schema`.
DRAFT_OUTPUT_CONTRACT_ID = "hermes-research-draft-output-contract/1.0.0"
CONTEXT_DRAFT_OUTPUT_CONTRACT_ID = "hermes-context-research-draft-output-contract/1.0.0"

REQUEST_IDENTITY_PREFIX = "hermesresearchrequest:sha256:"
RECEIPT_IDENTITY_PREFIX = "hermesresearchreceipt:sha256:"

NON_AUTHORITY_NOTICE = (
    "ADVISORY_RESEARCH_ONLY_NO_EXECUTION_NO_RISK_NO_CREDENTIAL_NO_ORDER_HUMAN_REVIEW_REQUIRED"
)

# ---------------------------------------------------------------------------
# Absolute repository maxima (section 12). Request caps must be <= these.
# ---------------------------------------------------------------------------

# Pinned Hermes v0.21.3 exposes NO iteration cap on the top-level ``-z`` one-shot
# path: ``--max-turns`` exists only on the ``chat`` subparser (exact tagged
# ``hermes_cli/_parser.py``, commit 345cd2b) and the ``-z`` implementation
# constructs the agent without a ``max_iterations`` override (exact tagged
# ``hermes_cli/oneshot.py``). WP175H therefore carries no ``max_turns`` request
# field or argv flag; the honest posture is recorded below and in the policy.
ITERATION_CAP_STATUS = "UNAVAILABLE_ON_PINNED_V0_21_3_ONESHOT"

MAX_WALL_SECONDS_ABSOLUTE = 300
MAX_OUTPUT_BYTES_ABSOLUTE = 1_000_000
MAX_SOURCES_ABSOLUTE = 30
MAX_ACCEPTED_ESTIMATED_COST_USD_ABSOLUTE = Decimal("5")
# First real controlled runtime performs ZERO automatic paid research retries: a
# provider call can spend before a timeout/transport failure and v0.21.3 emits
# accounting only best-effort/after the run, so no attempt is ever repeated.
MAX_TRANSPORT_RETRIES_ABSOLUTE = 0

# Bounded text / collection limits.
_MAX_SHORT_TEXT = 512
_MAX_LONG_TEXT = 4096
_MAX_LIST_ITEMS = 32
_MAX_LABEL = 128

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

RESEARCH_CATEGORIES = frozenset(
    {
        "market_mechanics",
        "event_outcome",
        "fundamental",
        "cross_market",
        "calibration",
        "general_public",
    }
)

ALLOWED_RESEARCH_SCOPE_TOKENS = frozenset(
    {"public_web", "public_news", "public_reference", "public_market_data"}
)

REQUIRED_SOURCE_TYPES = frozenset(
    {"news", "official", "reference", "public_market_data", "academic", "other_public"}
)

CONFIDENCE_LABELS = frozenset({"very_low", "low", "moderate", "high"})

SOURCE_CLASSES = frozenset(
    {"news", "official", "reference", "public_market_data", "academic", "other_public"}
)

# Draft authority flags that must all be present and exactly ``True``.
DRAFT_AUTHORITY_FLAGS = (
    "advisory_only",
    "human_review_required",
    "no_execution_authority",
    "no_risk_override",
    "no_credential_request",
    "no_order_or_cancel_or_sign_or_submit",
    "no_paper_live_decision",
    "no_strategy_promotion_approval",
    "no_pr_approval_or_merge_readiness_claim",
)

# Draft top-level required list fields. WP175M: promoted from the private
# ``_DRAFT_LIST_FIELDS`` to the public canonical collection so the prompt output-schema
# generator and the validator share ONE source of truth (STOP CONTRACT_VALIDATOR_DRIFT).
DRAFT_LIST_FIELDS = (
    "evidence_for",
    "evidence_against",
    "uncertainties",
    "known_missing_data",
    "falsification_checks_performed",
    "limitations",
    "what_would_change_the_conclusion",
    "suggested_next_research_steps",
)
# The one list field the validator rejects when empty (falsification discipline).
DRAFT_NON_EMPTY_LIST_FIELD = "falsification_checks_performed"

# Canonical ordered required top-level draft fields. The order is authoritative for the
# sanitized "first missing field" diagnostic: schema_version/request_id first, then the
# authority flags (``advisory_only`` first), then the substantive research fields. The
# validator and the generated output schema both derive their required set from this.
DRAFT_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "request_id",
    *DRAFT_AUTHORITY_FLAGS,
    "research_summary",
    "confidence_label",
    *DRAFT_LIST_FIELDS,
    "source_references",
)

# WP175M Finding G: canonical primitives shared EXACTLY by the validator and the
# generated output schema so the model-facing contract describes precisely the set the
# validator accepts (STOP CONTRACT_VALIDATOR_DRIFT).
#
# ``DRAFT_NON_WHITESPACE_PATTERN`` is a JSON-Schema search-style regex: ``\S`` matches
# iff the string contains at least one non-whitespace character, which is exactly the
# validator's ``value.strip()`` non-empty test for ``research_summary`` and source
# titles. ``DRAFT_SOURCE_URL_PATTERN`` reproduces the accepted set of the former
# case-insensitive HTTPS regex WITHOUT relying on a regex flag a schema consumer cannot
# see: only the ``https`` prefix has alphabetic case, so it is spelled with explicit
# character classes and the rest is unchanged.
DRAFT_NON_WHITESPACE_PATTERN = r"\S"
DRAFT_SOURCE_URL_PATTERN = r"^[hH][tT][tT][pP][sS]://[^\s/$.?#].[^\s]*$"

# Validator-aligned draft bounds (shared by the validator and the output-schema helper).
DRAFT_RESEARCH_SUMMARY_MAX_LEN = _MAX_LONG_TEXT * 4
DRAFT_LIST_MAX_ITEMS = _MAX_LIST_ITEMS
DRAFT_LIST_ITEM_MAX_LEN = _MAX_LONG_TEXT
DRAFT_SOURCE_TITLE_MAX_LEN = _MAX_SHORT_TEXT
DRAFT_SOURCE_URL_MAX_LEN = _MAX_SHORT_TEXT

# S10-HERMES-CTX-01 context-mode extension.  These constants are the single source
# of truth for both the model-facing contract and the authoritative validator.
CONTEXT_CLAIMS_FIELD = "context_claims"
CONTEXT_CLAIM_FIELDS = (
    "claim_statement",
    "claim_kind",
    "subject_refs",
    "direction",
    "source_reference_indices",
    "assumptions",
    "uncertainty_note",
)
CONTEXT_CLAIM_KINDS = ("HYPOTHESIS", "INFERENCE", "OBSERVATION")
CONTEXT_CLAIM_DIRECTIONS = ("CONTRADICTING", "MIXED", "SUPPORTING")
CONTEXT_CLAIM_MAX_ITEMS = 64
CONTEXT_CLAIM_TEXT_MAX_LEN = _MAX_LONG_TEXT
CONTEXT_CLAIM_SUBJECT_MAX_ITEMS = 32
CONTEXT_CLAIM_EVIDENCE_MAX_ITEMS = MAX_SOURCES_ABSOLUTE
CONTEXT_CLAIM_ASSUMPTION_MAX_ITEMS = 32
CONTEXT_REQUIRED_TOP_LEVEL_FIELDS = (*DRAFT_REQUIRED_TOP_LEVEL_FIELDS, CONTEXT_CLAIMS_FIELD)
CONTEXT_CLAIM_ID_PREFIX = "hermescontextclaim:sha256:"

# S10-HERMES-STRAT-01 strategy-mode extension (default OFF). These constants are the
# single source of truth for the strategy-mode output contract, the authoritative
# structural validator and the deterministic action/risk consistency rules. The raw
# model output stays untrusted: only the separately authorized strategy manager may
# convert a validated strategy-mode draft into a canonical soft strategy decision.
STRATEGY_DRAFT_OUTPUT_CONTRACT_ID = "hermes-strategy-assessment-draft-output-contract/1.0.0"
STRATEGY_ASSESSMENT_FIELD = "strategy_assessment"
STRATEGY_ASSESSMENT_FIELDS = (
    "lifecycle_action",
    "recommended_health_state",
    "risk_direction",
    "target_risk_band",
    "adaptation_recommendation",
)
STRATEGY_LIFECYCLE_ACTIONS = (
    "CONTINUE", "SCALE", "REDUCE", "ADAPT", "PAPER", "QUARANTINE", "RETIRE",
)
# STRAT-LIFE health vocabulary minus the derived-only ``NEW`` state.
STRATEGY_RECOMMENDED_HEALTH_STATES = ("HEALTHY", "WATCH", "DEGRADED", "QUARANTINED", "RETIRED")
STRATEGY_RISK_DIRECTIONS = ("UNCHANGED", "INCREASE", "DECREASE", "PAPER_ONLY", "ZERO")
# STRAT-LIFE risk-band vocabulary (``target_risk_band`` may also be null).
STRATEGY_TARGET_RISK_BANDS = ("PAPER", "EXPLORATORY_LIVE", "VALIDATED_LIVE", "MATURE_LIVE")
STRATEGY_ADAPTATION_FIELDS = ("kind", "summary", "parameter_updates")
STRATEGY_ADAPTATION_KINDS = ("PARAMETER_UPDATE", "MATERIAL_REDESIGN")
STRATEGY_ADAPTATION_SUMMARY_MAX_LEN = 1024
STRATEGY_PARAMETER_UPDATES_MAX_ITEMS = 64
STRATEGY_PARAMETER_VALUE_MAX_DEPTH = 8
STRATEGY_PARAMETER_NAME_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"
STRATEGY_REQUIRED_TOP_LEVEL_FIELDS = (*DRAFT_REQUIRED_TOP_LEVEL_FIELDS, STRATEGY_ASSESSMENT_FIELD)

# Obvious action/risk consistency rules (section 11.4). ``health`` None means any
# recommended health state; ``target_risk_band`` is ANY, NULL or an exact band;
# ``adaptation`` is REQUIRED (ADAPT) or NULL (every other action). The rules are
# embedded verbatim in the strategy-mode output contract and enforced by
# :func:`check_strategy_assessment_consistency`; no scoring/ranking rule exists.
STRATEGY_ACTION_CONSISTENCY_RULES: Mapping[str, Mapping[str, object]] = {
    "CONTINUE": {"risk_directions": ("UNCHANGED",), "health": None,
                 "target_risk_band": "ANY", "adaptation": "NULL"},
    "SCALE": {"risk_directions": ("INCREASE",), "health": ("HEALTHY", "WATCH", "DEGRADED"),
              "target_risk_band": "ANY", "adaptation": "NULL"},
    "REDUCE": {"risk_directions": ("DECREASE",), "health": None,
               "target_risk_band": "ANY", "adaptation": "NULL"},
    "ADAPT": {"risk_directions": ("UNCHANGED", "DECREASE", "PAPER_ONLY", "ZERO"), "health": None,
              "target_risk_band": "ANY", "adaptation": "REQUIRED"},
    "PAPER": {"risk_directions": ("PAPER_ONLY",), "health": None,
              "target_risk_band": "PAPER", "adaptation": "NULL"},
    "QUARANTINE": {"risk_directions": ("ZERO",), "health": ("QUARANTINED",),
                   "target_risk_band": "NULL", "adaptation": "NULL"},
    "RETIRE": {"risk_directions": ("ZERO",), "health": ("RETIRED",),
               "target_risk_band": "NULL", "adaptation": "NULL"},
}
# Adaptation-kind rules: PARAMETER_UPDATE needs a non-empty update map; a
# MATERIAL_REDESIGN carries an empty map (no child StrategyVersion is created here).
STRATEGY_ADAPTATION_KIND_RULES: Mapping[str, str] = {
    "PARAMETER_UPDATE": "NON_EMPTY_PARAMETER_UPDATES",
    "MATERIAL_REDESIGN": "EMPTY_PARAMETER_UPDATES",
}
_STRATEGY_PARAMETER_NAME_RE = re.compile(STRATEGY_PARAMETER_NAME_PATTERN)

# Deterministic sorted closed vocabularies for the generated output schema enums.
CONFIDENCE_LABELS_SORTED = tuple(sorted(CONFIDENCE_LABELS))
SOURCE_CLASSES_SORTED = tuple(sorted(SOURCE_CLASSES))

# Sanitized draft-structure diagnostic statuses (WP175M section 20).
DRAFT_DIAGNOSTICS_AVAILABLE = "AVAILABLE"
DRAFT_DIAGNOSTICS_UNAVAILABLE_INVALID = "UNAVAILABLE_INVALID_OUTPUT"
DRAFT_DIAGNOSTICS_NOT_REACHED = "NOT_REACHED"

# Compiled once from the shared pattern; reused by the validator (Finding G).
_DRAFT_NON_WHITESPACE_RE = re.compile(DRAFT_NON_WHITESPACE_PATTERN)

# ---------------------------------------------------------------------------
# Fail-closed error type
# ---------------------------------------------------------------------------

_ERROR_CODES = frozenset(
    {
        "REQUEST_SCHEMA_INVALID",
        "REQUEST_UNKNOWN_FIELD",
        "REQUEST_FIELD_MISSING",
        "REQUEST_FIELD_TYPE_INVALID",
        "REQUEST_FIELD_VALUE_INVALID",
        "REQUEST_NUMERIC_NONCANONICAL",
        "REQUEST_BOUND_EXCEEDED",
        "REQUEST_SECRET_DETECTED",
        "REQUEST_AUTHORITY_ESCALATION",
        "REQUEST_PATH_TRAVERSAL",
        "DRAFT_SCHEMA_INVALID",
        "DRAFT_FIELD_MISSING",
        "DRAFT_FIELD_TYPE_INVALID",
        "DRAFT_AUTHORITY_FLAG_INVALID",
        "DRAFT_SOURCE_INVALID",
        "DRAFT_UNSAFE_CONTENT",
        "CONTEXT_CLAIM_INVALID",
        "STRATEGY_ASSESSMENT_INVALID",
        "STRATEGY_MODE_INVALID",
        "RECEIPT_IDENTITY_INVALID",
    }
)


class HermesResearchError(Exception):
    """Sanitized closed-code error. Its ``str`` is only the code -- never content."""

    def __init__(self, code: str) -> None:
        if code not in _ERROR_CODES:
            code = "REQUEST_SCHEMA_INVALID"
        super().__init__(code)
        self.code = code


def _fail(code: str) -> "HermesResearchError":
    return HermesResearchError(code)


# ---------------------------------------------------------------------------
# Canonical serialization / identity helpers (shared by policy/controller)
# ---------------------------------------------------------------------------


def canonical_json_bytes(payload: Mapping[str, object]) -> bytes:
    """Deterministic canonical JSON encoding (sorted keys, no NaN, compact)."""
    return json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_address(prefix: str, payload: Mapping[str, object]) -> str:
    return prefix + sha256_hex(canonical_json_bytes(payload))


# ---------------------------------------------------------------------------
# Secret / authority-escalation scanning (never echoes matched content)
# ---------------------------------------------------------------------------

# Wallet / long-hex identifiers. Kept as a named member of ``_SECRET_PATTERNS`` so the
# public_market_context compatibility path (S10-HERMES-CTX-03) can reference it exactly.
_LONG_HEX_SECRET_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40,}\b")

# Credential / secret indicators. Matching fails closed WITHOUT echoing content.
_SECRET_PATTERNS = (
    re.compile(r"api[\s_-]?key", re.IGNORECASE),
    re.compile(r"secret[\s_-]?key", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"private[\s_-]?key", re.IGNORECASE),
    re.compile(r"\bbearer\s+[a-z0-9._~+/-]{8,}", re.IGNORECASE),
    re.compile(r"authorization\s*:", re.IGNORECASE),
    re.compile(r"\bsk-[a-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"\bghp_[a-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\baccess[\s_-]?token\b", re.IGNORECASE),
    _LONG_HEX_SECRET_PATTERN,  # wallet / long hex identifiers
)

# Exact, complete, repo-canonical PUBLIC Polymarket identifiers (S10-HERMES-CTX-03):
# Gamma market id, condition-backed event id (repository condition-id contract
# ``^0x[0-9a-f]{64}$``), Gamma-fallback event id, and CLOB token id. Case-sensitive and
# delimited on both sides by a closed set: start/end, whitespace, quotes, brackets,
# commas, ``=`` before and a JSON-escape backslash after. Wrong namespaces, other hex
# lengths, uppercase hex and any trailing token characters therefore never match.
_CANONICAL_PUBLIC_POLYMARKET_ID = re.compile(
    r"(?<![^\s\"'(\[{,=])"
    r"(?:market:polymarket:[1-9][0-9]*"
    r"|event:polymarket:0x[0-9a-f]{64}"
    r"|event:polymarket:market-[1-9][0-9]*"
    r"|token:polymarket:[1-9][0-9]*)"
    r"(?![^\s\"'\\)\]},])"
)
_CANONICAL_EVENT_NAMESPACE = "event:polymarket:"

# Attempts to grant trading / risk / credential / scheduler / file / shell authority.
_AUTHORITY_PATTERNS = (
    re.compile(r"place\s+(?:an?\s+)?order", re.IGNORECASE),
    re.compile(r"cancel\s+(?:an?\s+)?order", re.IGNORECASE),
    re.compile(r"submit\s+(?:an?\s+)?order", re.IGNORECASE),
    re.compile(r"sign\s+(?:the\s+)?transaction", re.IGNORECASE),
    re.compile(r"execute\s+(?:a\s+)?trade", re.IGNORECASE),
    re.compile(r"transfer\s+funds", re.IGNORECASE),
    re.compile(r"withdraw\s+funds", re.IGNORECASE),
    re.compile(r"override\s+risk", re.IGNORECASE),
    re.compile(r"disable\s+risk", re.IGNORECASE),
    re.compile(r"grant\s+credential", re.IGNORECASE),
    re.compile(r"enable\s+(?:the\s+)?scheduler", re.IGNORECASE),
    re.compile(r"run\s+(?:a\s+)?(?:shell|terminal)\s+command", re.IGNORECASE),
    re.compile(r"write\s+to\s+(?:the\s+)?(?:file|filesystem|disk)", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"activate\s+live", re.IGNORECASE),
    re.compile(r"authorize\s+(?:the\s+)?merge", re.IGNORECASE),
)

_PATH_TRAVERSAL = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")
_ABSOLUTE_PATH = re.compile(r"^(?:/|[a-zA-Z]:[\\/]|\\\\)")


def _scan_secret(text: str) -> None:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise _fail("REQUEST_SECRET_DETECTED")


def _scan_public_market_context_secret(text: str) -> None:
    """Secret scan for ``public_market_context`` only (S10-HERMES-CTX-03).

    The full scanner runs over a validation-only copy in which exact canonical public
    Polymarket identifiers are replaced by a space, and every rule other than the
    long-hex rule also runs over the original text, so masking can never hide a
    credential marker. The masked copy is never stored or hashed.

    Every occurrence of the canonical event namespace must begin an exact, delimited
    canonical event identifier; any malformed canonical-looking event id fails closed
    even where the generic long-hex rule would not flag it.
    """
    start = text.find(_CANONICAL_EVENT_NAMESPACE)
    while start != -1:
        if _CANONICAL_PUBLIC_POLYMARKET_ID.match(text, start) is None:
            raise _fail("REQUEST_SECRET_DETECTED")
        start = text.find(_CANONICAL_EVENT_NAMESPACE, start + 1)
    _scan_secret(_CANONICAL_PUBLIC_POLYMARKET_ID.sub(" ", text))
    for pattern in _SECRET_PATTERNS:
        if pattern is not _LONG_HEX_SECRET_PATTERN and pattern.search(text):
            raise _fail("REQUEST_SECRET_DETECTED")


def _scan_authority(text: str) -> None:
    for pattern in _AUTHORITY_PATTERNS:
        if pattern.search(text):
            raise _fail("REQUEST_AUTHORITY_ESCALATION")


def _scan_path(token: str) -> None:
    if _PATH_TRAVERSAL.search(token) or _ABSOLUTE_PATH.search(token):
        raise _fail("REQUEST_PATH_TRAVERSAL")


# ---------------------------------------------------------------------------
# Field validation primitives
# ---------------------------------------------------------------------------


def _require_str(value: object, *, max_len: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    if not allow_empty and not value.strip():
        raise _fail("REQUEST_FIELD_VALUE_INVALID")
    if len(value) > max_len:
        raise _fail("REQUEST_BOUND_EXCEEDED")
    _scan_secret(value)
    _scan_authority(value)
    return value


def _require_public_market_context(value: object, *, max_len: int) -> str:
    """``_require_str`` for ``public_market_context`` with the public-id-aware scan."""
    if not isinstance(value, str):
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    if not value.strip():
        raise _fail("REQUEST_FIELD_VALUE_INVALID")
    if len(value) > max_len:
        raise _fail("REQUEST_BOUND_EXCEEDED")
    _scan_public_market_context_secret(value)
    _scan_authority(value)
    return value


def _require_int(value: object, *, minimum: int, maximum: int) -> int:
    # bool is an int subclass; reject it explicitly for numeric canonicality.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    if value < minimum:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")
    if value > maximum:
        raise _fail("REQUEST_BOUND_EXCEEDED")
    return value


def _canonical_decimal(value: object, *, maximum: Decimal) -> Decimal:
    # Binary floats are rejected: monetary canonicality requires str/int/Decimal.
    if isinstance(value, bool):
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    if isinstance(value, float):
        raise _fail("REQUEST_NUMERIC_NONCANONICAL")
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, str):
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value.strip()):
            raise _fail("REQUEST_NUMERIC_NONCANONICAL")
        try:
            dec = Decimal(value.strip())
        except InvalidOperation:
            raise _fail("REQUEST_NUMERIC_NONCANONICAL")
    else:
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    if dec < 0:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")
    if dec > maximum:
        raise _fail("REQUEST_BOUND_EXCEEDED")
    return dec


def _require_token_tuple(
    value: object, *, vocabulary: frozenset[str], max_items: int, non_empty: bool = True
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise _fail("REQUEST_FIELD_TYPE_INVALID")
    items = list(value)
    if non_empty and not items:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")
    if len(items) > max_items:
        raise _fail("REQUEST_BOUND_EXCEEDED")
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            raise _fail("REQUEST_FIELD_TYPE_INVALID")
        if item not in vocabulary:
            raise _fail("REQUEST_FIELD_VALUE_INVALID")
        if item in seen:
            raise _fail("REQUEST_FIELD_VALUE_INVALID")
        seen.add(item)
        out.append(item)
    return tuple(out)


# ---------------------------------------------------------------------------
# HermesResearchRunRequest
# ---------------------------------------------------------------------------

_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "research_question",
        "research_objective",
        "research_category",
        "public_market_context",
        "allowed_research_scope",
        "required_source_types",
        "max_sources",
        "provider_label",
        "model_label",
        "max_wall_seconds",
        "max_output_bytes",
        "max_accepted_estimated_cost_usd",
        "human_review_required",
        "non_authority_notice",
    }
)


@dataclasses.dataclass(frozen=True)
class HermesResearchRunRequest:
    """Immutable, content-addressed controlled research request."""

    request_id: str
    schema_version: str
    research_question: str
    research_objective: str
    research_category: str
    public_market_context: str
    allowed_research_scope: tuple[str, ...]
    required_source_types: tuple[str, ...]
    max_sources: int
    provider_label: str
    model_label: str
    max_wall_seconds: int
    max_output_bytes: int
    max_accepted_estimated_cost_usd: Decimal
    human_review_required: bool
    non_authority_notice: str

    def public_fields(self) -> dict[str, object]:
        """Canonical public field mapping (excludes the derived identity)."""
        return {
            "schema_version": self.schema_version,
            "research_question": self.research_question,
            "research_objective": self.research_objective,
            "research_category": self.research_category,
            "public_market_context": self.public_market_context,
            "allowed_research_scope": list(self.allowed_research_scope),
            "required_source_types": list(self.required_source_types),
            "max_sources": self.max_sources,
            "provider_label": self.provider_label,
            "model_label": self.model_label,
            "max_wall_seconds": self.max_wall_seconds,
            "max_output_bytes": self.max_output_bytes,
            "max_accepted_estimated_cost_usd": format(
                self.max_accepted_estimated_cost_usd, "f"
            ),
            "human_review_required": self.human_review_required,
            "non_authority_notice": self.non_authority_notice,
        }


def build_research_run_request(fields: Mapping[str, object]) -> HermesResearchRunRequest:
    """Validate a request mapping and derive its content-addressed identity.

    Fails closed on unknown fields, wrong types, out-of-bound values, non-canonical
    numerics, path traversal, embedded secrets, and authority-escalation content.
    Never echoes rejected content.
    """
    if not isinstance(fields, Mapping):
        raise _fail("REQUEST_SCHEMA_INVALID")
    unknown = set(fields) - _REQUEST_FIELDS
    if unknown:
        raise _fail("REQUEST_UNKNOWN_FIELD")
    missing = _REQUEST_FIELDS - set(fields)
    if missing:
        raise _fail("REQUEST_FIELD_MISSING")

    schema_version = _require_str(fields["schema_version"], max_len=_MAX_LABEL)
    if schema_version != REQUEST_SCHEMA_VERSION:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")

    research_question = _require_str(fields["research_question"], max_len=_MAX_LONG_TEXT)
    research_objective = _require_str(fields["research_objective"], max_len=_MAX_LONG_TEXT)

    research_category = _require_str(fields["research_category"], max_len=_MAX_LABEL)
    if research_category not in RESEARCH_CATEGORIES:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")

    public_market_context = _require_public_market_context(
        fields["public_market_context"], max_len=_MAX_LONG_TEXT
    )

    allowed_research_scope = _require_token_tuple(
        fields["allowed_research_scope"],
        vocabulary=ALLOWED_RESEARCH_SCOPE_TOKENS,
        max_items=_MAX_LIST_ITEMS,
    )
    required_source_types = _require_token_tuple(
        fields["required_source_types"],
        vocabulary=REQUIRED_SOURCE_TYPES,
        max_items=_MAX_LIST_ITEMS,
    )

    max_sources = _require_int(fields["max_sources"], minimum=1, maximum=MAX_SOURCES_ABSOLUTE)
    max_wall_seconds = _require_int(
        fields["max_wall_seconds"], minimum=1, maximum=MAX_WALL_SECONDS_ABSOLUTE
    )
    max_output_bytes = _require_int(
        fields["max_output_bytes"], minimum=1, maximum=MAX_OUTPUT_BYTES_ABSOLUTE
    )
    max_accepted_estimated_cost_usd = _canonical_decimal(
        fields["max_accepted_estimated_cost_usd"],
        maximum=MAX_ACCEPTED_ESTIMATED_COST_USD_ABSOLUTE,
    )

    provider_label = _require_str(fields["provider_label"], max_len=_MAX_LABEL)
    model_label = _require_str(fields["model_label"], max_len=_MAX_LABEL)
    for label in (provider_label, model_label):
        _scan_path(label)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", label):
            raise _fail("REQUEST_FIELD_VALUE_INVALID")

    human_review_required = fields["human_review_required"]
    if human_review_required is not True:
        # This runtime never produces a request that waives human review.
        raise _fail("REQUEST_FIELD_VALUE_INVALID")

    non_authority_notice = _require_str(
        fields["non_authority_notice"], max_len=_MAX_SHORT_TEXT
    )
    if non_authority_notice != NON_AUTHORITY_NOTICE:
        raise _fail("REQUEST_FIELD_VALUE_INVALID")

    partial = HermesResearchRunRequest(
        request_id="",
        schema_version=schema_version,
        research_question=research_question,
        research_objective=research_objective,
        research_category=research_category,
        public_market_context=public_market_context,
        allowed_research_scope=allowed_research_scope,
        required_source_types=required_source_types,
        max_sources=max_sources,
        provider_label=provider_label,
        model_label=model_label,
        max_wall_seconds=max_wall_seconds,
        max_output_bytes=max_output_bytes,
        max_accepted_estimated_cost_usd=max_accepted_estimated_cost_usd,
        human_review_required=True,
        non_authority_notice=non_authority_notice,
    )
    request_id = content_address(REQUEST_IDENTITY_PREFIX, partial.public_fields())
    return dataclasses.replace(partial, request_id=request_id)


# ---------------------------------------------------------------------------
# Sanitized source reference + receipt
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SanitizedSourceReference:
    """Bounded, sanitized source reference derived from a validated draft."""

    url_digest: str
    source_class: str


@dataclasses.dataclass(frozen=True)
class HermesResearchRunReceipt:
    """Immutable sanitized research-run receipt (section 13).

    Contains no API key/token, auth header, environment dump, raw stderr, raw
    provider payload, home/repo path, private data, trading credential, or order/
    account state. Every authority flag is fixed False for execution/live/credential
    /risk/paper; ``human_review_required`` is fixed True.
    """

    receipt_id: str
    schema_version: str
    request_id: str
    policy_id: str
    hermes_version: str
    provider_label: str
    model_label: str
    verified_provider: str | None
    verified_model: str | None
    iteration_cap_status: str
    start_utc: str
    end_utc: str
    terminal_status: str
    exit_code: int | None
    transport_attempt_count: int
    timed_out: bool
    stdout_truncated: bool
    stderr_truncated: bool
    # WP175K sanitized failure evidence (additive, receipt schema 1.2.0). No raw
    # stderr is ever stored; ``stderr_excerpt`` is the only diagnostic text surface
    # and is bounded + secret/path-scrubbed by the runner. ``usage_file_present`` is
    # true iff Hermes wrote any usage-file bytes (a zero-byte existing file counts).
    stderr_captured_byte_len: int
    stderr_sanitization_status: str
    stderr_excerpt: str | None
    stderr_excerpt_truncated: bool
    stderr_redaction_applied: bool
    usage_file_present: bool
    usage_file_truncated: bool
    configured_toolsets: tuple[str, ...]
    tool_enforcement: str
    runtime_tool_telemetry: str
    approval_authority: str
    source_url_count: int
    source_references: tuple[SanitizedSourceReference, ...]
    output_schema_valid: bool
    safety_validation_status: str
    # WP175M sanitized additive evidence (receipt schema 1.3.0). ``prompt_envelope_sha256``
    # binds the exact canonical prompt bytes; ``draft_output_contract_sha256`` binds the
    # machine-generated output schema; the ``draft_*`` diagnostics use ONLY static
    # canonical field-name tokens and fixed statuses (never rejected values);
    # ``usage_session_id_digest`` is the SHA-256 of a valid usage report's session id
    # (raw session id is never retained) or ``None``.
    prompt_envelope_sha256: str | None
    draft_output_contract_sha256: str | None
    draft_diagnostics_status: str
    draft_present_required_fields: tuple[str, ...]
    draft_missing_required_fields: tuple[str, ...]
    draft_first_missing_field: str | None
    usage_session_id_digest: str | None
    usage_evidence_status: str
    usage_completed: bool | None
    usage_failed: bool | None
    token_input_count: int | None
    token_output_count: int | None
    total_token_count: int | None
    api_call_count: int | None
    estimated_cost_usd: str | None
    cost_status: str | None
    cost_source: str | None
    budget_status: str
    human_review_required: bool
    no_execution_authority: bool
    no_live_authority: bool
    no_credential_authority: bool
    no_risk_authority: bool
    no_paper_authority: bool
    activation_state: str

    def identity_fields(self) -> dict[str, object]:
        """Canonical field mapping used to derive ``receipt_id`` (excludes it)."""
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "policy_id": self.policy_id,
            "hermes_version": self.hermes_version,
            "provider_label": self.provider_label,
            "model_label": self.model_label,
            "verified_provider": self.verified_provider,
            "verified_model": self.verified_model,
            "iteration_cap_status": self.iteration_cap_status,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "terminal_status": self.terminal_status,
            "exit_code": self.exit_code,
            "transport_attempt_count": self.transport_attempt_count,
            "timed_out": self.timed_out,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "stderr_captured_byte_len": self.stderr_captured_byte_len,
            "stderr_sanitization_status": self.stderr_sanitization_status,
            "stderr_excerpt": self.stderr_excerpt,
            "stderr_excerpt_truncated": self.stderr_excerpt_truncated,
            "stderr_redaction_applied": self.stderr_redaction_applied,
            "usage_file_present": self.usage_file_present,
            "usage_file_truncated": self.usage_file_truncated,
            "configured_toolsets": list(self.configured_toolsets),
            "tool_enforcement": self.tool_enforcement,
            "runtime_tool_telemetry": self.runtime_tool_telemetry,
            "approval_authority": self.approval_authority,
            "source_url_count": self.source_url_count,
            "source_references": [
                {"url_digest": ref.url_digest, "source_class": ref.source_class}
                for ref in self.source_references
            ],
            "output_schema_valid": self.output_schema_valid,
            "safety_validation_status": self.safety_validation_status,
            "prompt_envelope_sha256": self.prompt_envelope_sha256,
            "draft_output_contract_sha256": self.draft_output_contract_sha256,
            "draft_diagnostics_status": self.draft_diagnostics_status,
            "draft_present_required_fields": list(self.draft_present_required_fields),
            "draft_missing_required_fields": list(self.draft_missing_required_fields),
            "draft_first_missing_field": self.draft_first_missing_field,
            "usage_session_id_digest": self.usage_session_id_digest,
            "usage_evidence_status": self.usage_evidence_status,
            "usage_completed": self.usage_completed,
            "usage_failed": self.usage_failed,
            "token_input_count": self.token_input_count,
            "token_output_count": self.token_output_count,
            "total_token_count": self.total_token_count,
            "api_call_count": self.api_call_count,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cost_status": self.cost_status,
            "cost_source": self.cost_source,
            "budget_status": self.budget_status,
            "human_review_required": self.human_review_required,
            "no_execution_authority": self.no_execution_authority,
            "no_live_authority": self.no_live_authority,
            "no_credential_authority": self.no_credential_authority,
            "no_risk_authority": self.no_risk_authority,
            "no_paper_authority": self.no_paper_authority,
            "activation_state": self.activation_state,
        }


def derive_receipt_id(receipt: HermesResearchRunReceipt) -> str:
    return content_address(RECEIPT_IDENTITY_PREFIX, receipt.identity_fields())


# ---------------------------------------------------------------------------
# Authoritative research-draft validator (untrusted Hermes output)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ValidatedResearchDraft:
    """Parsed + validated research draft with sanitized source references."""

    request_id: str
    research_summary: str
    confidence_label: str
    source_references: tuple[SanitizedSourceReference, ...]
    source_urls: tuple[str, ...]
    falsification_checks_performed: tuple[str, ...] = ()
    context_claims: tuple["ValidatedContextClaim", ...] = ()
    # S10-HERMES-STRAT-01: populated only in strategy mode (default None). The raw
    # draft remains untrusted; this is structural validation only.
    strategy_assessment: "ValidatedStrategyAssessmentDraft | None" = None


@dataclasses.dataclass(frozen=True)
class ValidatedStrategyAssessmentDraft:
    """Structurally validated strategy-mode output (S10-HERMES-STRAT-01).

    Carries the five strategy fields plus the eight research-quality lists of the
    authoritatively validated generic draft, in canonical field order. It grants no
    authority: action/risk consistency is checked separately by
    :func:`check_strategy_assessment_consistency`, and only the strategy manager may
    turn it into a canonical soft strategy decision.
    """

    lifecycle_action: str
    recommended_health_state: str
    risk_direction: str
    target_risk_band: str | None
    adaptation_kind: str | None
    adaptation_summary: str | None
    adaptation_parameter_updates_json: str | None
    research_lists: tuple[tuple[str, tuple[str, ...]], ...]

    def research_list(self, name: str) -> tuple[str, ...]:
        return dict(self.research_lists)[name]


@dataclasses.dataclass(frozen=True)
class ValidatedContextClaim:
    """Bounded, repo-identified context claim derived from untrusted model output."""

    claim_id: str
    claim_statement: str
    claim_kind: str
    subject_refs: tuple[str, ...]
    direction: str
    source_reference_indices: tuple[int, ...]
    assumptions: tuple[str, ...]
    uncertainty_note: str

    def identity_fields(self) -> dict[str, object]:
        return {
            "claim_statement": self.claim_statement,
            "claim_kind": self.claim_kind,
            "subject_refs": list(self.subject_refs),
            "direction": self.direction,
            "source_reference_indices": list(self.source_reference_indices),
            "assumptions": list(self.assumptions),
            "uncertainty_note": self.uncertainty_note,
        }


# Finding G: compiled from the SAME canonical pattern the generated schema embeds. The
# explicit ``[hH][tT]...`` prefix preserves the former ``re.IGNORECASE`` accepted set
# (only the ``https`` prefix has alphabetic case) without a flag a schema consumer sees.
_URL_RE = re.compile(DRAFT_SOURCE_URL_PATTERN)


def _draft_str(value: object, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise _fail("DRAFT_FIELD_TYPE_INVALID")
    if len(value) > max_len:
        raise _fail("DRAFT_SCHEMA_INVALID")
    return value


def validate_research_draft(
    raw: str | bytes, *, expected_request_id: str, max_sources: int,
    context_mode: bool = False, allowed_subject_refs: Sequence[str] | None = None,
    strategy_mode: bool = False, strategy_parameter_names: Sequence[str] | None = None,
) -> ValidatedResearchDraft:
    """Parse and validate the untrusted Hermes final research draft.

    Fails closed on invalid JSON/schema, missing/false authority flags, malformed
    or empty source references, and content asserting execution/trading authority.
    Never re-runs Hermes on failure and never echoes rejected payload bytes.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeError:
            raise _fail("DRAFT_SCHEMA_INVALID")
    if not isinstance(raw, str):
        raise _fail("DRAFT_SCHEMA_INVALID")
    try:
        document = json.loads(raw)
    except (ValueError, RecursionError):
        raise _fail("DRAFT_SCHEMA_INVALID")
    if not isinstance(document, dict):
        raise _fail("DRAFT_SCHEMA_INVALID")
    if context_mode and strategy_mode:
        raise _fail("STRATEGY_MODE_INVALID")
    if context_mode and set(document) != set(CONTEXT_REQUIRED_TOP_LEVEL_FIELDS):
        raise _fail("CONTEXT_CLAIM_INVALID")
    parameter_names: frozenset[str] = frozenset()
    if strategy_mode:
        parameter_names = _strategy_parameter_name_set(strategy_parameter_names)
        if set(document) - set(STRATEGY_REQUIRED_TOP_LEVEL_FIELDS) or (
            STRATEGY_ASSESSMENT_FIELD not in document
        ):
            raise _fail("STRATEGY_ASSESSMENT_INVALID")

    if document.get("schema_version") != DRAFT_SCHEMA_VERSION:
        raise _fail("DRAFT_SCHEMA_INVALID")
    if document.get("request_id") != expected_request_id:
        raise _fail("DRAFT_SCHEMA_INVALID")

    # All authority flags must be present and exactly True.
    for flag in DRAFT_AUTHORITY_FLAGS:
        if flag not in document:
            raise _fail("DRAFT_FIELD_MISSING")
        if document[flag] is not True:
            raise _fail("DRAFT_AUTHORITY_FLAG_INVALID")

    research_summary = document.get("research_summary")
    research_summary = _draft_str(research_summary, max_len=DRAFT_RESEARCH_SUMMARY_MAX_LEN)
    if not _DRAFT_NON_WHITESPACE_RE.search(research_summary):
        raise _fail("DRAFT_SCHEMA_INVALID")

    confidence_label = document.get("confidence_label")
    if confidence_label not in CONFIDENCE_LABELS:
        raise _fail("DRAFT_SCHEMA_INVALID")

    for list_field in DRAFT_LIST_FIELDS:
        if list_field not in document:
            raise _fail("DRAFT_FIELD_MISSING")
        value = document[list_field]
        if not isinstance(value, list) or len(value) > DRAFT_LIST_MAX_ITEMS:
            raise _fail("DRAFT_SCHEMA_INVALID")
        for item in value:
            _draft_str(item, max_len=DRAFT_LIST_ITEM_MAX_LEN)

    # Falsification discipline: the model must have attempted disconfirmation.
    if not document[DRAFT_NON_EMPTY_LIST_FIELD]:
        raise _fail("DRAFT_UNSAFE_CONTENT")

    # Unsafe-content gate: reject execution/trading authority claims in the summary.
    _scan_unsafe_draft(research_summary)

    refs, urls = _validate_source_references(document.get("source_references"), max_sources)
    claims: tuple[ValidatedContextClaim, ...] = ()
    if context_mode:
        claims = _validate_context_claims(
            document.get(CONTEXT_CLAIMS_FIELD),
            source_count=len(refs),
            allowed_subject_refs=allowed_subject_refs,
        )
    strategy: ValidatedStrategyAssessmentDraft | None = None
    if strategy_mode:
        strategy = _validate_strategy_assessment(
            document[STRATEGY_ASSESSMENT_FIELD],
            parameter_names=parameter_names,
            research_lists=tuple(
                (name, tuple(document[name])) for name in DRAFT_LIST_FIELDS
            ),
        )

    return ValidatedResearchDraft(
        request_id=expected_request_id,
        research_summary=research_summary,
        confidence_label=confidence_label,
        source_references=refs,
        source_urls=urls,
        falsification_checks_performed=tuple(document[DRAFT_NON_EMPTY_LIST_FIELD]),
        context_claims=claims,
        strategy_assessment=strategy,
    )


def validate_strategy_research_draft(
    raw: str | bytes, *, expected_request_id: str, max_sources: int,
    strategy_parameter_names: Sequence[str],
) -> ValidatedResearchDraft:
    """Validate the explicit strategy-mode contract without changing ordinary H1."""
    return validate_research_draft(
        raw,
        expected_request_id=expected_request_id,
        max_sources=max_sources,
        strategy_mode=True,
        strategy_parameter_names=strategy_parameter_names,
    )


def _strategy_parameter_name_set(names: Sequence[str] | None) -> frozenset[str]:
    if names is None or isinstance(names, (str, bytes)) or not isinstance(names, Sequence):
        raise _fail("STRATEGY_MODE_INVALID")
    if any(not isinstance(name, str) or not _STRATEGY_PARAMETER_NAME_RE.match(name) for name in names):
        raise _fail("STRATEGY_MODE_INVALID")
    out = frozenset(names)
    if len(out) != len(names):
        raise _fail("STRATEGY_MODE_INVALID")
    return out


def _strategy_json_value(value: object, depth: int) -> None:
    """Canonical JSON value domain: object/array/string/integer/boolean/null only.

    Binary floats (including NaN/Infinity, which ``json.loads`` yields as floats) and
    non-JSON types reject; depth is bounded.
    """
    if depth > STRATEGY_PARAMETER_VALUE_MAX_DEPTH:
        raise _fail("STRATEGY_ASSESSMENT_INVALID")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        if abs(value) > 2**63 - 1:
            raise _fail("STRATEGY_ASSESSMENT_INVALID")
        return
    if isinstance(value, list):
        for item in value:
            _strategy_json_value(item, depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _fail("STRATEGY_ASSESSMENT_INVALID")
            _strategy_json_value(item, depth + 1)
        return
    raise _fail("STRATEGY_ASSESSMENT_INVALID")


def _validate_strategy_assessment(
    value: object, *, parameter_names: frozenset[str],
    research_lists: tuple[tuple[str, tuple[str, ...]], ...],
) -> ValidatedStrategyAssessmentDraft:
    """Exact-shape structural validation of the untrusted ``strategy_assessment``."""
    if not isinstance(value, dict) or set(value) != set(STRATEGY_ASSESSMENT_FIELDS):
        raise _fail("STRATEGY_ASSESSMENT_INVALID")
    action = value["lifecycle_action"]
    health = value["recommended_health_state"]
    direction = value["risk_direction"]
    band = value["target_risk_band"]
    if (
        not isinstance(action, str) or action not in STRATEGY_LIFECYCLE_ACTIONS
        or not isinstance(health, str) or health not in STRATEGY_RECOMMENDED_HEALTH_STATES
        or not isinstance(direction, str) or direction not in STRATEGY_RISK_DIRECTIONS
        or (band is not None and (not isinstance(band, str) or band not in STRATEGY_TARGET_RISK_BANDS))
    ):
        raise _fail("STRATEGY_ASSESSMENT_INVALID")
    adaptation = value["adaptation_recommendation"]
    kind = summary = updates_json = None
    if adaptation is not None:
        if not isinstance(adaptation, dict) or set(adaptation) != set(STRATEGY_ADAPTATION_FIELDS):
            raise _fail("STRATEGY_ASSESSMENT_INVALID")
        kind = adaptation["kind"]
        if not isinstance(kind, str) or kind not in STRATEGY_ADAPTATION_KINDS:
            raise _fail("STRATEGY_ASSESSMENT_INVALID")
        summary = adaptation["summary"]
        if (
            not isinstance(summary, str)
            or not _DRAFT_NON_WHITESPACE_RE.search(summary)
            or len(summary) > STRATEGY_ADAPTATION_SUMMARY_MAX_LEN
        ):
            raise _fail("STRATEGY_ASSESSMENT_INVALID")
        try:
            _scan_unsafe_draft(summary)
        except HermesResearchError:
            raise _fail("STRATEGY_ASSESSMENT_INVALID") from None
        updates = adaptation["parameter_updates"]
        if not isinstance(updates, dict) or len(updates) > STRATEGY_PARAMETER_UPDATES_MAX_ITEMS:
            raise _fail("STRATEGY_ASSESSMENT_INVALID")
        for key, item in updates.items():
            if key not in parameter_names:
                raise _fail("STRATEGY_ASSESSMENT_INVALID")
            _strategy_json_value(item, 1)
        updates_json = json.dumps(
            updates, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    return ValidatedStrategyAssessmentDraft(
        lifecycle_action=action,
        recommended_health_state=health,
        risk_direction=direction,
        target_risk_band=band,
        adaptation_kind=kind,
        adaptation_summary=summary,
        adaptation_parameter_updates_json=updates_json,
        research_lists=research_lists,
    )


def check_strategy_assessment_consistency(draft: ValidatedStrategyAssessmentDraft) -> bool:
    """Deterministic obvious action/risk consistency (section 11.4) -- no scoring.

    Returns True iff the structurally valid draft satisfies
    :data:`STRATEGY_ACTION_CONSISTENCY_RULES` and :data:`STRATEGY_ADAPTATION_KIND_RULES`.
    """
    if not isinstance(draft, ValidatedStrategyAssessmentDraft):
        return False
    rule = STRATEGY_ACTION_CONSISTENCY_RULES.get(draft.lifecycle_action)
    if rule is None or draft.risk_direction not in rule["risk_directions"]:  # type: ignore[operator]
        return False
    allowed_health = rule["health"]
    if allowed_health is not None and draft.recommended_health_state not in allowed_health:  # type: ignore[operator]
        return False
    band_rule = rule["target_risk_band"]
    if band_rule == "NULL" and draft.target_risk_band is not None:
        return False
    if band_rule not in ("ANY", "NULL") and draft.target_risk_band != band_rule:
        return False
    if rule["adaptation"] == "NULL":
        return draft.adaptation_kind is None
    if draft.adaptation_kind is None or draft.adaptation_parameter_updates_json is None:
        return False
    empty = draft.adaptation_parameter_updates_json == "{}"
    kind_rule = STRATEGY_ADAPTATION_KIND_RULES[draft.adaptation_kind]
    return empty if kind_rule == "EMPTY_PARAMETER_UPDATES" else not empty


def validate_context_research_draft(
    raw: str | bytes, *, expected_request_id: str, max_sources: int,
    allowed_subject_refs: Sequence[str],
) -> ValidatedResearchDraft:
    """Validate the explicit context-mode contract without changing ordinary H1."""
    return validate_research_draft(
        raw,
        expected_request_id=expected_request_id,
        max_sources=max_sources,
        context_mode=True,
        allowed_subject_refs=allowed_subject_refs,
    )


def _context_text(value: object, *, allow_empty: bool = False) -> str:
    text = _draft_str(value, max_len=CONTEXT_CLAIM_TEXT_MAX_LEN)
    if not allow_empty and not text.strip():
        raise _fail("CONTEXT_CLAIM_INVALID")
    _scan_unsafe_draft(text)
    return text


def _context_text_tuple(value: object, *, maximum: int, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > maximum or (not allow_empty and not value):
        raise _fail("CONTEXT_CLAIM_INVALID")
    return tuple(_context_text(item) for item in value)


def _validate_context_claims(
    value: object, *, source_count: int, allowed_subject_refs: Sequence[str] | None,
) -> tuple[ValidatedContextClaim, ...]:
    if not isinstance(value, list) or not value or len(value) > CONTEXT_CLAIM_MAX_ITEMS:
        raise _fail("CONTEXT_CLAIM_INVALID")
    allowed = frozenset(allowed_subject_refs or ())
    if not allowed:
        raise _fail("CONTEXT_CLAIM_INVALID")
    claims: list[ValidatedContextClaim] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != set(CONTEXT_CLAIM_FIELDS):
            raise _fail("CONTEXT_CLAIM_INVALID")
        statement = _context_text(item["claim_statement"])
        kind = item["claim_kind"]
        direction = item["direction"]
        if kind not in CONTEXT_CLAIM_KINDS or direction not in CONTEXT_CLAIM_DIRECTIONS:
            raise _fail("CONTEXT_CLAIM_INVALID")
        subjects = _context_text_tuple(
            item["subject_refs"], maximum=CONTEXT_CLAIM_SUBJECT_MAX_ITEMS, allow_empty=False
        )
        if len(set(subjects)) != len(subjects) or not set(subjects).issubset(allowed):
            raise _fail("CONTEXT_CLAIM_INVALID")
        raw_indices = item["source_reference_indices"]
        if (
            not isinstance(raw_indices, list) or not raw_indices
            or len(raw_indices) > CONTEXT_CLAIM_EVIDENCE_MAX_ITEMS
            or any(isinstance(index, bool) or not isinstance(index, int) for index in raw_indices)
        ):
            raise _fail("CONTEXT_CLAIM_INVALID")
        indices = tuple(sorted(set(raw_indices)))
        if len(indices) != len(raw_indices) or any(index < 0 or index >= source_count for index in indices):
            raise _fail("CONTEXT_CLAIM_INVALID")
        assumptions = _context_text_tuple(
            item["assumptions"], maximum=CONTEXT_CLAIM_ASSUMPTION_MAX_ITEMS,
            allow_empty=kind == "OBSERVATION",
        )
        if kind != "OBSERVATION" and not assumptions:
            raise _fail("CONTEXT_CLAIM_INVALID")
        uncertainty = _context_text(item["uncertainty_note"])
        partial = ValidatedContextClaim(
            claim_id="", claim_statement=statement, claim_kind=kind,
            subject_refs=tuple(sorted(subjects)), direction=direction,
            source_reference_indices=indices, assumptions=assumptions,
            uncertainty_note=uncertainty,
        )
        claim_id = content_address(CONTEXT_CLAIM_ID_PREFIX, partial.identity_fields())
        if claim_id in seen:
            raise _fail("CONTEXT_CLAIM_INVALID")
        seen.add(claim_id)
        claims.append(dataclasses.replace(partial, claim_id=claim_id))
    return tuple(claims)


# Draft content that asserts trading / execution / promotion authority is unsafe.
_UNSAFE_DRAFT_PATTERNS = (
    re.compile(r"place\s+(?:an?\s+)?order", re.IGNORECASE),
    re.compile(r"submit\s+(?:an?\s+)?order", re.IGNORECASE),
    re.compile(r"execute\s+(?:this\s+|a\s+)?trade", re.IGNORECASE),
    re.compile(r"sign\s+(?:and\s+submit|the\s+transaction)", re.IGNORECASE),
    re.compile(r"go\s+live", re.IGNORECASE),
    re.compile(r"activate\s+live", re.IGNORECASE),
    re.compile(r"override\s+risk", re.IGNORECASE),
    re.compile(r"approve\s+(?:the\s+)?(?:merge|pull request|pr)\b", re.IGNORECASE),
    re.compile(r"promote\s+(?:this\s+)?strategy", re.IGNORECASE),
)


def _scan_unsafe_draft(text: str) -> None:
    for pattern in _UNSAFE_DRAFT_PATTERNS:
        if pattern.search(text):
            raise _fail("DRAFT_UNSAFE_CONTENT")


def _validate_source_references(
    value: object, max_sources: int
) -> tuple[tuple[SanitizedSourceReference, ...], tuple[str, ...]]:
    if not isinstance(value, list):
        raise _fail("DRAFT_SOURCE_INVALID")
    if not value:
        # Empty citation structure fails the required source-provenance check.
        raise _fail("DRAFT_SOURCE_INVALID")
    if len(value) > min(max_sources, MAX_SOURCES_ABSOLUTE):
        raise _fail("DRAFT_SOURCE_INVALID")
    refs: list[SanitizedSourceReference] = []
    urls: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            raise _fail("DRAFT_SOURCE_INVALID")
        url = item.get("url")
        title = item.get("title")
        source_class = item.get("source_class")
        if not isinstance(url, str) or not _URL_RE.match(url) or len(url) > DRAFT_SOURCE_URL_MAX_LEN:
            raise _fail("DRAFT_SOURCE_INVALID")
        if (
            not isinstance(title, str)
            or not _DRAFT_NON_WHITESPACE_RE.search(title)
            or len(title) > DRAFT_SOURCE_TITLE_MAX_LEN
        ):
            raise _fail("DRAFT_SOURCE_INVALID")
        if source_class not in SOURCE_CLASSES:
            raise _fail("DRAFT_SOURCE_INVALID")
        refs.append(
            SanitizedSourceReference(
                url_digest=sha256_hex(url.encode("utf-8")), source_class=source_class
            )
        )
        urls.append(url)
    return tuple(refs), tuple(urls)


# ---------------------------------------------------------------------------
# Canonical machine-generated draft output contract (WP175M section 5)
# ---------------------------------------------------------------------------


def build_research_draft_output_schema(
    *, expected_request_id: str, max_sources: int, context_mode: bool = False,
    allowed_subject_refs: Sequence[str] | None = None,
    strategy_mode: bool = False, strategy_parameter_names: Sequence[str] | None = None,
) -> dict[str, object]:
    """Deterministic JSON-schema-like draft output contract for the prompt envelope.

    Every constraint is derived from the SAME canonical constants the authoritative
    :func:`validate_research_draft` enforces (STOP CONTRACT_VALIDATOR_DRIFT): the
    ordered required top-level field set, the authority-flag ``const=True`` set, the
    confidence and source-class closed vocabularies, the validator-aligned length/
    cardinality bounds, and the exact draft schema version and request id embedded as
    constants. It invents no constraint the validator does not enforce. The output is a
    plain mapping of literals only -- it carries no repository path, credential, or
    private data -- and identical inputs yield byte-identical canonical serialization.
    """
    if not isinstance(expected_request_id, str) or not expected_request_id:
        raise _fail("DRAFT_SCHEMA_INVALID")
    if isinstance(max_sources, bool) or not isinstance(max_sources, int) or max_sources < 1:
        raise _fail("DRAFT_SCHEMA_INVALID")
    source_cap = min(max_sources, MAX_SOURCES_ABSOLUTE)
    if context_mode and strategy_mode:
        raise _fail("STRATEGY_MODE_INVALID")

    properties: dict[str, object] = {
        "schema_version": {"type": "string", "const": DRAFT_SCHEMA_VERSION},
        "request_id": {"type": "string", "const": expected_request_id},
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        properties[flag] = {"type": "boolean", "const": True}
    properties["research_summary"] = {
        "type": "string",
        "minLength": 1,
        "pattern": DRAFT_NON_WHITESPACE_PATTERN,
        "maxLength": DRAFT_RESEARCH_SUMMARY_MAX_LEN,
    }
    properties["confidence_label"] = {
        "type": "string",
        "enum": list(CONFIDENCE_LABELS_SORTED),
    }
    for field in DRAFT_LIST_FIELDS:
        field_schema: dict[str, object] = {
            "type": "array",
            "maxItems": DRAFT_LIST_MAX_ITEMS,
            "items": {"type": "string", "maxLength": DRAFT_LIST_ITEM_MAX_LEN},
        }
        if field == DRAFT_NON_EMPTY_LIST_FIELD:
            # The validator rejects an empty falsification list, so the contract
            # requires at least one entry.
            field_schema["minItems"] = 1
        properties[field] = field_schema
    properties["source_references"] = {
        "type": "array",
        "minItems": 1,
        "maxItems": source_cap,
        "items": {
            "type": "object",
            "required": ["url", "title", "source_class"],
            "properties": {
                "url": {
                    "type": "string",
                    "pattern": DRAFT_SOURCE_URL_PATTERN,
                    "maxLength": DRAFT_SOURCE_URL_MAX_LEN,
                },
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": DRAFT_NON_WHITESPACE_PATTERN,
                    "maxLength": DRAFT_SOURCE_TITLE_MAX_LEN,
                },
                "source_class": {"type": "string", "enum": list(SOURCE_CLASSES_SORTED)},
            },
        },
    }
    required = DRAFT_REQUIRED_TOP_LEVEL_FIELDS
    schema_id = DRAFT_OUTPUT_CONTRACT_ID
    if context_mode:
        allowed_subjects = tuple(sorted(set(allowed_subject_refs or ())))
        if not allowed_subjects or any(
            not isinstance(subject, str) or not subject.strip()
            or len(subject) > CONTEXT_CLAIM_TEXT_MAX_LEN
            for subject in allowed_subjects
        ):
            raise _fail("CONTEXT_CLAIM_INVALID")
        schema_id = CONTEXT_DRAFT_OUTPUT_CONTRACT_ID
        required = CONTEXT_REQUIRED_TOP_LEVEL_FIELDS
        properties[CONTEXT_CLAIMS_FIELD] = {
            "type": "array",
            "minItems": 1,
            "maxItems": CONTEXT_CLAIM_MAX_ITEMS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": list(CONTEXT_CLAIM_FIELDS),
                "properties": {
                    "claim_statement": {"type": "string", "minLength": 1, "pattern": DRAFT_NON_WHITESPACE_PATTERN, "maxLength": CONTEXT_CLAIM_TEXT_MAX_LEN},
                    "claim_kind": {"type": "string", "enum": list(CONTEXT_CLAIM_KINDS)},
                    "subject_refs": {"type": "array", "minItems": 1, "maxItems": CONTEXT_CLAIM_SUBJECT_MAX_ITEMS, "uniqueItems": True, "items": {"type": "string", "enum": list(allowed_subjects)}},
                    "direction": {"type": "string", "enum": list(CONTEXT_CLAIM_DIRECTIONS)},
                    "source_reference_indices": {"type": "array", "minItems": 1, "maxItems": CONTEXT_CLAIM_EVIDENCE_MAX_ITEMS, "uniqueItems": True, "items": {"type": "integer", "minimum": 0}},
                    "assumptions": {"type": "array", "maxItems": CONTEXT_CLAIM_ASSUMPTION_MAX_ITEMS, "items": {"type": "string", "minLength": 1, "pattern": DRAFT_NON_WHITESPACE_PATTERN, "maxLength": CONTEXT_CLAIM_TEXT_MAX_LEN}},
                    "uncertainty_note": {"type": "string", "minLength": 1, "pattern": DRAFT_NON_WHITESPACE_PATTERN, "maxLength": CONTEXT_CLAIM_TEXT_MAX_LEN},
                },
            },
        }
    if strategy_mode:
        parameter_names = sorted(_strategy_parameter_name_set(strategy_parameter_names))
        schema_id = STRATEGY_DRAFT_OUTPUT_CONTRACT_ID
        required = STRATEGY_REQUIRED_TOP_LEVEL_FIELDS
        properties[STRATEGY_ASSESSMENT_FIELD] = _strategy_assessment_schema(parameter_names)
    schema = {
        "type": "object",
        "schema_id": schema_id,
        "draft_schema_version": DRAFT_SCHEMA_VERSION,
        "required": list(required),
        "properties": properties,
    }
    if context_mode or strategy_mode:
        schema["additionalProperties"] = False
    if strategy_mode:
        schema["strategy_consistency_rules"] = {
            "lifecycle_actions": {
                action: {
                    "risk_directions": list(rule["risk_directions"]),  # type: ignore[arg-type]
                    "recommended_health_states": (
                        None if rule["health"] is None else list(rule["health"])  # type: ignore[arg-type]
                    ),
                    "target_risk_band": rule["target_risk_band"],
                    "adaptation_recommendation": rule["adaptation"],
                }
                for action, rule in STRATEGY_ACTION_CONSISTENCY_RULES.items()
            },
            "adaptation_kinds": dict(STRATEGY_ADAPTATION_KIND_RULES),
        }
    return schema


def _strategy_assessment_schema(parameter_names: Sequence[str]) -> dict[str, object]:
    """The ``strategy_assessment`` sub-contract, derived from the validator constants."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(STRATEGY_ASSESSMENT_FIELDS),
        "properties": {
            "lifecycle_action": {"type": "string", "enum": list(STRATEGY_LIFECYCLE_ACTIONS)},
            "recommended_health_state": {
                "type": "string", "enum": list(STRATEGY_RECOMMENDED_HEALTH_STATES),
            },
            "risk_direction": {"type": "string", "enum": list(STRATEGY_RISK_DIRECTIONS)},
            "target_risk_band": {
                "type": ["string", "null"], "enum": [*STRATEGY_TARGET_RISK_BANDS, None],
            },
            "adaptation_recommendation": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "required": list(STRATEGY_ADAPTATION_FIELDS),
                "properties": {
                    "kind": {"type": "string", "enum": list(STRATEGY_ADAPTATION_KINDS)},
                    "summary": {
                        "type": "string", "minLength": 1,
                        "pattern": DRAFT_NON_WHITESPACE_PATTERN,
                        "maxLength": STRATEGY_ADAPTATION_SUMMARY_MAX_LEN,
                    },
                    "parameter_updates": {
                        "type": "object",
                        "maxProperties": STRATEGY_PARAMETER_UPDATES_MAX_ITEMS,
                        "propertyNames": {"enum": list(parameter_names)},
                        "additionalProperties": {
                            "type": ["object", "array", "string", "integer", "boolean", "null"],
                        },
                    },
                },
            },
        },
    }


def build_strategy_research_draft_output_schema(
    *, expected_request_id: str, max_sources: int, strategy_parameter_names: Sequence[str]
) -> dict[str, object]:
    return build_research_draft_output_schema(
        expected_request_id=expected_request_id, max_sources=max_sources, strategy_mode=True,
        strategy_parameter_names=strategy_parameter_names,
    )


def build_context_research_draft_output_schema(
    *, expected_request_id: str, max_sources: int, allowed_subject_refs: Sequence[str]
) -> dict[str, object]:
    return build_research_draft_output_schema(
        expected_request_id=expected_request_id, max_sources=max_sources, context_mode=True,
        allowed_subject_refs=allowed_subject_refs,
    )


def research_draft_output_schema_digest(schema: Mapping[str, object]) -> str:
    """SHA-256 of the canonical serialization of a generated draft output schema."""
    return sha256_hex(canonical_json_bytes(schema))


# ---------------------------------------------------------------------------
# Sanitized draft-structure diagnostics (WP175M section 8)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DraftStructureDiagnostics:
    """Bounded, sanitized structural diagnostics for an untrusted draft.

    Only STATIC canonical field-name tokens from
    :data:`DRAFT_REQUIRED_TOP_LEVEL_FIELDS` and fixed status strings are ever retained.
    No rejected value, research text, URL, arbitrary model-supplied key, tool payload,
    or provider content is stored.
    """

    status: str
    present_required_fields: tuple[str, ...]
    missing_required_fields: tuple[str, ...]
    first_missing_field: str | None


def inspect_research_draft_structure(raw: str | bytes) -> DraftStructureDiagnostics:
    """Return sanitized present/missing canonical-field diagnostics for untrusted output.

    Parses the untrusted JSON but emits ONLY predefined canonical field-name tokens and
    fixed status values. Non-JSON, non-object, or undecodable input yields
    ``UNAVAILABLE_INVALID_OUTPUT`` (every canonical field reported missing). A parsed
    JSON object yields ``AVAILABLE`` with the canonical fields partitioned into present
    and missing by NAME PRESENCE only (never by value validity), and the first missing
    field in canonical order.
    """
    document: dict[str, object] | None = None
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeError:
            raw = None  # type: ignore[assignment]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, RecursionError):
            parsed = None
        if isinstance(parsed, dict):
            document = parsed
    if document is None:
        return DraftStructureDiagnostics(
            status=DRAFT_DIAGNOSTICS_UNAVAILABLE_INVALID,
            present_required_fields=(),
            missing_required_fields=DRAFT_REQUIRED_TOP_LEVEL_FIELDS,
            first_missing_field=DRAFT_REQUIRED_TOP_LEVEL_FIELDS[0],
        )
    present = tuple(f for f in DRAFT_REQUIRED_TOP_LEVEL_FIELDS if f in document)
    missing = tuple(f for f in DRAFT_REQUIRED_TOP_LEVEL_FIELDS if f not in document)
    return DraftStructureDiagnostics(
        status=DRAFT_DIAGNOSTICS_AVAILABLE,
        present_required_fields=present,
        missing_required_fields=missing,
        first_missing_field=missing[0] if missing else None,
    )
