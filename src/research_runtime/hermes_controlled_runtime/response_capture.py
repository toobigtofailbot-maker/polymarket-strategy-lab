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

_MAX_USAGE_BYTES = 65_536
_MAX_LABEL = 128
_MAX_TOKEN = 1_000_000_000

# The only usage fields admitted into sanitized evidence (section 8 of the follow-up).
_USAGE_INT_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
    "api_calls",
)
_USAGE_STR_FIELDS = ("model", "provider", "session_id", "service_tier")
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
    """Strictly parse a bounded sanitized JSON usage object. Fails closed."""
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

    return UsageReport(
        diagnostic=USAGE_OK,
        ok=True,
        input_tokens=ints["input_tokens"],
        output_tokens=ints["output_tokens"],
        cache_read_tokens=ints["cache_read_tokens"],
        cache_write_tokens=ints["cache_write_tokens"],
        reasoning_tokens=ints["reasoning_tokens"],
        total_tokens=ints["total_tokens"],
        api_calls=ints["api_calls"],
        estimated_cost_usd=cost,
        model=strs["model"],
        provider=strs["provider"],
        session_id=strs["session_id"],
        service_tier=strs["service_tier"],
        completed=bools["completed"],
        failed=bools["failed"],
    )


def cost_within_cap(usage: UsageReport, cap: Decimal) -> bool:
    """True unless the reported estimated cost exceeds the per-run cap."""
    if usage.estimated_cost_usd is None:
        return True
    try:
        return Decimal(usage.estimated_cost_usd) <= cap
    except InvalidOperation:
        return False
