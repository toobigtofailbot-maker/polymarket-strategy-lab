"""Truthful v0.21.3 output handling: plain stdout response + usage-file report.

Pinned Hermes Agent v0.21.3 (tag v2026.9.14) does NOT emit a machine-readable
runtime tool-call event stream. Its one-shot output is the final research response
text on stdout; machine-readable usage/cost evidence comes from the ``--usage-file``
JSON report written into the ephemeral working directory.

This module bounds and sanitizes both surfaces. It never copies a raw usage payload
into canonical evidence and fails closed on malformed or oversized input.
"""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal, InvalidOperation
from typing import Mapping

# Final-response diagnostics.
RESPONSE_OK = "OK"
RESPONSE_EMPTY = "RESPONSE_EMPTY"
RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
RESPONSE_DECODE_ERROR = "RESPONSE_DECODE_ERROR"

# Usage-report diagnostics.
USAGE_OK = "OK"
USAGE_MISSING = "USAGE_MISSING"
USAGE_TOO_LARGE = "USAGE_TOO_LARGE"
USAGE_MALFORMED = "USAGE_MALFORMED"
# A syntactically valid object that fails the mandatory success-evidence contract
# (section 7 of the follow-up): missing/false completion, a set failure flag, or a
# missing/invalid required token/accounting/identity field.
USAGE_INCOMPLETE = "USAGE_INCOMPLETE"
USAGE_FAILED_FLAG = "USAGE_FAILED_FLAG"
USAGE_FIELD_INVALID = "USAGE_FIELD_INVALID"

# Cost-acceptance outcomes (section 9). Cost is POST-RUN accounting, not a pre-spend
# hard stop, so these gate acceptance of an already-completed run.
COST_ACCEPTED = "COST_ACCEPTED"
COST_EVIDENCE_UNAVAILABLE = "COST_EVIDENCE_UNAVAILABLE"
COST_ABOVE_THRESHOLD = "COST_ABOVE_THRESHOLD"

_MAX_USAGE_BYTES = 65_536
_MAX_LABEL = 128
_MAX_TOKEN = 1_000_000_000

# Exact tagged v0.21.3 cost vocabulary (agent/usage_pricing.py @ commit 345cd2b):
#   CostStatus = Literal["actual", "estimated", "included", "unknown"]
#   CostSource = Literal["provider_cost_api", "provider_generation_api",
#                        "provider_models_api", "official_docs_snapshot",
#                        "user_override", "custom_contract", "none"]
# Only a KNOWN priced/included status yields an acceptable, known cost. "unknown"
# (and any absent/out-of-vocabulary status) is treated as cost-unavailable.
KNOWN_COST_STATUSES = frozenset({"actual", "estimated", "included"})
COST_STATUS_UNKNOWN = "unknown"
COST_STATUS_VOCABULARY = frozenset({"actual", "estimated", "included", "unknown"})
COST_SOURCE_VOCABULARY = frozenset(
    {
        "provider_cost_api",
        "provider_generation_api",
        "provider_models_api",
        "official_docs_snapshot",
        "user_override",
        "custom_contract",
        "none",
    }
)

# Sanitized usage fields admitted into evidence. Only the first three token fields
# plus ``api_calls`` are mandatory success evidence; cache/reasoning tokens are
# optional accounting.
_USAGE_REQUIRED_INT_FIELDS = ("input_tokens", "output_tokens", "total_tokens", "api_calls")
_USAGE_OPTIONAL_INT_FIELDS = ("cache_read_tokens", "cache_write_tokens", "reasoning_tokens")
_USAGE_INT_FIELDS = _USAGE_REQUIRED_INT_FIELDS + _USAGE_OPTIONAL_INT_FIELDS
_USAGE_REQUIRED_STR_FIELDS = ("model", "provider", "session_id")
_USAGE_STR_FIELDS = _USAGE_REQUIRED_STR_FIELDS + ("service_tier", "cost_status", "cost_source")
_USAGE_BOOL_FIELDS = ("completed", "failed")


@dataclasses.dataclass(frozen=True)
class ResponseCapture:
    """Bounded final research response text captured from plain stdout."""

    diagnostic: str
    ok: bool
    final_text: str | None


@dataclasses.dataclass(frozen=True)
class UsageReport:
    """Sanitized usage/cost report parsed from the v0.21.3 ``--usage-file``."""

    diagnostic: str
    ok: bool
    input_tokens: int | None
    output_tokens: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    reasoning_tokens: int | None
    total_tokens: int | None
    api_calls: int | None
    estimated_cost_usd: str | None
    cost_status: str | None
    cost_source: str | None
    model: str | None
    provider: str | None
    session_id: str | None
    service_tier: str | None
    completed: bool | None
    failed: bool | None


def capture_final_response(stdout: str | bytes, *, max_bytes: int) -> ResponseCapture:
    """Bound and return the plain final research response text from stdout."""
    if isinstance(stdout, bytes):
        if len(stdout) > max_bytes:
            return ResponseCapture(RESPONSE_TOO_LARGE, False, None)
        try:
            text = stdout.decode("utf-8")
        except UnicodeError:
            return ResponseCapture(RESPONSE_DECODE_ERROR, False, None)
    elif isinstance(stdout, str):
        if len(stdout.encode("utf-8")) > max_bytes:
            return ResponseCapture(RESPONSE_TOO_LARGE, False, None)
        text = stdout
    else:
        return ResponseCapture(RESPONSE_DECODE_ERROR, False, None)

    if not text.strip():
        return ResponseCapture(RESPONSE_EMPTY, False, None)
    return ResponseCapture(RESPONSE_OK, True, text)


def _sane_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 0 <= value <= _MAX_TOKEN:
        return value
    return None


def _sane_str(value: object) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= _MAX_LABEL:
        return value
    return None


def _sane_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _sane_cost(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dec = Decimal(text)
        except InvalidOperation:
            return None
        return text if dec >= 0 else None
    return None


def _empty_usage(diagnostic: str) -> UsageReport:
    return UsageReport(
        diagnostic=diagnostic,
        ok=False,
        input_tokens=None,
        output_tokens=None,
        cache_read_tokens=None,
        cache_write_tokens=None,
        reasoning_tokens=None,
        total_tokens=None,
        api_calls=None,
        estimated_cost_usd=None,
        cost_status=None,
        cost_source=None,
        model=None,
        provider=None,
        session_id=None,
        service_tier=None,
        completed=None,
        failed=None,
    )


def parse_usage_report(
    usage_bytes: bytes | None, *, max_bytes: int = _MAX_USAGE_BYTES
) -> UsageReport:
    """Strictly parse the bounded v0.21.3 ``--usage-file`` JSON object, fail-closed.

    ``ok`` is True only when the object is mandatory success evidence (section 7):
    ``completed`` is exactly ``True``, ``failed`` is exactly ``False``, and the
    required token/accounting integers (``input_tokens``, ``output_tokens``,
    ``total_tokens``, ``api_calls``) and identity labels (``model``, ``provider``,
    ``session_id``) are present and valid. A syntactically valid object that is not
    success evidence returns ``ok=False`` with a specific diagnostic while still
    exposing whatever fields sanitized cleanly, so a failure receipt can preserve
    safely-available accounting. Cost *acceptability* is a separate gate
    (:func:`cost_acceptance`); a valid usage object may still lack a known cost.
    """
    if usage_bytes is None:
        return _empty_usage(USAGE_MISSING)
    if not isinstance(usage_bytes, (bytes, bytearray)):
        return _empty_usage(USAGE_MALFORMED)
    if len(usage_bytes) > max_bytes:
        return _empty_usage(USAGE_TOO_LARGE)
    try:
        document = json.loads(bytes(usage_bytes).decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        return _empty_usage(USAGE_MALFORMED)
    if not isinstance(document, Mapping):
        return _empty_usage(USAGE_MALFORMED)

    ints = {field: _sane_int(document.get(field)) for field in _USAGE_INT_FIELDS}
    strs = {field: _sane_str(document.get(field)) for field in _USAGE_STR_FIELDS}
    bools = {field: _sane_bool(document.get(field)) for field in _USAGE_BOOL_FIELDS}
    cost = _sane_cost(document.get("estimated_cost_usd"))

    # Determine mandatory success-evidence validity without echoing raw content.
    diagnostic = _success_evidence_diagnostic(ints, strs, bools)

    return UsageReport(
        diagnostic=diagnostic,
        ok=diagnostic == USAGE_OK,
        input_tokens=ints["input_tokens"],
        output_tokens=ints["output_tokens"],
        cache_read_tokens=ints["cache_read_tokens"],
        cache_write_tokens=ints["cache_write_tokens"],
        reasoning_tokens=ints["reasoning_tokens"],
        total_tokens=ints["total_tokens"],
        api_calls=ints["api_calls"],
        estimated_cost_usd=cost,
        cost_status=strs["cost_status"],
        cost_source=strs["cost_source"],
        model=strs["model"],
        provider=strs["provider"],
        session_id=strs["session_id"],
        service_tier=strs["service_tier"],
        completed=bools["completed"],
        failed=bools["failed"],
    )


def _success_evidence_diagnostic(
    ints: Mapping[str, int | None],
    strs: Mapping[str, str | None],
    bools: Mapping[str, bool | None],
) -> str:
    """First failing mandatory success-evidence check, or ``USAGE_OK``."""
    if bools["completed"] is not True:
        return USAGE_INCOMPLETE
    if bools["failed"] is not False:
        return USAGE_FAILED_FLAG
    for field in _USAGE_REQUIRED_INT_FIELDS:
        if ints[field] is None:
            return USAGE_FIELD_INVALID
    for field in _USAGE_REQUIRED_STR_FIELDS:
        if strs[field] is None:
            return USAGE_FIELD_INVALID
    return USAGE_OK


def cost_acceptance(usage: UsageReport, cap: Decimal) -> str:
    """POST-RUN cost-acceptance outcome (section 9); fail-closed on unknown cost.

    Returns ``COST_EVIDENCE_UNAVAILABLE`` when the reported estimated cost is
    missing/invalid or ``cost_status`` is missing/``unknown``/out-of-vocabulary
    (never treating a missing cost as zero), ``COST_ABOVE_THRESHOLD`` when a known
    cost exceeds the accepted per-run threshold, and ``COST_ACCEPTED`` only when a
    known, finite, in-threshold cost is present.
    """
    if usage.estimated_cost_usd is None:
        return COST_EVIDENCE_UNAVAILABLE
    if usage.cost_status not in KNOWN_COST_STATUSES:
        return COST_EVIDENCE_UNAVAILABLE
    try:
        amount = Decimal(usage.estimated_cost_usd)
    except InvalidOperation:
        return COST_EVIDENCE_UNAVAILABLE
    if amount < 0:
        return COST_EVIDENCE_UNAVAILABLE
    if amount > cap:
        return COST_ABOVE_THRESHOLD
    return COST_ACCEPTED
