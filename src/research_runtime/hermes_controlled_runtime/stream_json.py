"""Bounded, fail-closed parser for the pinned Hermes v0.21.3 stream-json surface.

The parser collects only the required audit facts from a newline-delimited JSON
event stream and never copies arbitrary raw tool payloads into canonical evidence.
Unknown event shapes do not crash into raw exception output: they are counted and
ignored with a neutral diagnostic. If the terminal result cannot be unambiguously
identified, parsing fails closed.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Mapping

# Closed diagnostic vocabulary. ``OK`` is the only success code.
STREAM_OK = "OK"
STREAM_OUTPUT_TOO_LARGE = "STREAM_JSON_OUTPUT_TOO_LARGE"
STREAM_NO_FINAL_RESULT = "STREAM_JSON_NO_FINAL_RESULT"
STREAM_AMBIGUOUS_RESULT = "STREAM_JSON_AMBIGUOUS_RESULT"
STREAM_MALFORMED = "STREAM_JSON_MALFORMED"
STREAM_EMPTY = "STREAM_JSON_EMPTY"

_TERMINAL_STATUS_SUCCESS = "SUCCESS"
_TERMINAL_STATUS_ERROR = "ERROR"

# Bounded caps that protect canonical evidence regardless of the request cap.
_MAX_EVENTS = 100_000
_MAX_FINAL_TEXT_BYTES = 1_000_000
_MAX_TOOL_NAME_LEN = 64
_MAX_SOURCE_URLS = 512
_MAX_URL_LEN = 2048
_ALLOWED_TOOL_NAMES = frozenset({"web_search", "web_extract"})


@dataclasses.dataclass(frozen=True)
class StreamJsonAuditResult:
    """Sanitized audit facts extracted from the stream-json transcript."""

    diagnostic: str
    ok: bool
    session_id: str | None
    terminal_status: str | None
    reported_provider: str | None
    reported_model: str | None
    reported_version: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: str | None
    duration_ms: int | None
    tool_call_counts: tuple[tuple[str, int], ...]
    source_urls: tuple[str, ...]
    final_text: str | None
    event_count: int
    unknown_event_count: int


def _neutral(diagnostic: str, event_count: int = 0, unknown: int = 0) -> StreamJsonAuditResult:
    return StreamJsonAuditResult(
        diagnostic=diagnostic,
        ok=False,
        session_id=None,
        terminal_status=None,
        reported_provider=None,
        reported_model=None,
        reported_version=None,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=None,
        duration_ms=None,
        tool_call_counts=(),
        source_urls=(),
        final_text=None,
        event_count=event_count,
        unknown_event_count=unknown,
    )


def _opt_str(value: object, *, max_len: int) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= max_len:
        return value
    return None


def _opt_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _opt_cost(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return str(value)
    if isinstance(value, str) and _looks_like_amount(value):
        return value
    return None


def _looks_like_amount(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    try:
        return float(stripped) >= 0  # inspection only; not stored as float
    except ValueError:
        return False


def _collect_urls(event: Mapping[str, object], sink: list[str]) -> None:
    """Collect bounded web source URLs surfaced by a tool/result event."""
    candidates: list[object] = []
    for key in ("urls", "sources", "source_urls"):
        value = event.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    for item in candidates:
        if len(sink) >= _MAX_SOURCE_URLS:
            return
        url: object = None
        if isinstance(item, str):
            url = item
        elif isinstance(item, Mapping):
            url = item.get("url")
        if (
            isinstance(url, str)
            and url.lower().startswith("https://")
            and len(url) <= _MAX_URL_LEN
            and url not in sink
        ):
            sink.append(url)


def parse_stream_json(raw: str | bytes, *, max_bytes: int) -> StreamJsonAuditResult:
    """Parse the bounded stream-json transcript into sanitized audit facts."""
    if isinstance(raw, bytes):
        if len(raw) > max_bytes:
            return _neutral(STREAM_OUTPUT_TOO_LARGE)
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            return _neutral(STREAM_MALFORMED)
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > max_bytes:
            return _neutral(STREAM_OUTPUT_TOO_LARGE)
        text = raw
    else:
        return _neutral(STREAM_MALFORMED)

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return _neutral(STREAM_EMPTY)
    if len(lines) > _MAX_EVENTS:
        return _neutral(STREAM_OUTPUT_TOO_LARGE)

    session_id: str | None = None
    reported_provider: str | None = None
    reported_model: str | None = None
    reported_version: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: str | None = None
    duration_ms: int | None = None
    tool_counts: dict[str, int] = {}
    urls: list[str] = []
    unknown = 0
    terminal_events: list[Mapping[str, object]] = []

    for line in lines:
        try:
            event = json.loads(line)
        except (ValueError, RecursionError):
            return _neutral(STREAM_MALFORMED, event_count=len(lines))
        if not isinstance(event, dict):
            unknown += 1
            continue
        etype = event.get("type")
        if etype == "session":
            session_id = _opt_str(event.get("session_id"), max_len=128) or session_id
            reported_provider = _opt_str(event.get("provider"), max_len=128) or reported_provider
            reported_model = _opt_str(event.get("model"), max_len=128) or reported_model
            reported_version = _opt_str(event.get("version"), max_len=64) or reported_version
        elif etype == "tool_call":
            name = event.get("tool")
            if isinstance(name, str) and 0 < len(name) <= _MAX_TOOL_NAME_LEN:
                tool_counts[name] = tool_counts.get(name, 0) + 1
            else:
                unknown += 1
        elif etype == "tool_result":
            _collect_urls(event, urls)
        elif etype == "result":
            terminal_events.append(event)
        else:
            unknown += 1

    if not terminal_events:
        return _neutral(STREAM_NO_FINAL_RESULT, event_count=len(lines), unknown=unknown)
    if len(terminal_events) > 1:
        return _neutral(STREAM_AMBIGUOUS_RESULT, event_count=len(lines), unknown=unknown)

    result = terminal_events[0]
    subtype = result.get("subtype")
    if subtype == "success":
        terminal_status = _TERMINAL_STATUS_SUCCESS
    elif subtype == "error":
        terminal_status = _TERMINAL_STATUS_ERROR
    else:
        return _neutral(STREAM_NO_FINAL_RESULT, event_count=len(lines), unknown=unknown)

    final_text = result.get("result")
    if terminal_status == _TERMINAL_STATUS_SUCCESS:
        if not isinstance(final_text, str) or not final_text.strip():
            return _neutral(STREAM_NO_FINAL_RESULT, event_count=len(lines), unknown=unknown)
        if len(final_text.encode("utf-8")) > _MAX_FINAL_TEXT_BYTES:
            return _neutral(STREAM_OUTPUT_TOO_LARGE, event_count=len(lines), unknown=unknown)
    else:
        final_text = None

    usage = result.get("usage")
    if isinstance(usage, Mapping):
        input_tokens = _opt_int(usage.get("input_tokens"))
        output_tokens = _opt_int(usage.get("output_tokens"))
    estimated_cost = _opt_cost(result.get("total_cost_usd"))
    duration_ms = _opt_int(result.get("duration_ms"))
    reported_provider = _opt_str(result.get("provider"), max_len=128) or reported_provider
    reported_model = _opt_str(result.get("model"), max_len=128) or reported_model
    reported_version = _opt_str(result.get("version"), max_len=64) or reported_version
    _collect_urls(result, urls)

    tool_call_counts = tuple(sorted(tool_counts.items()))

    return StreamJsonAuditResult(
        diagnostic=STREAM_OK,
        ok=terminal_status == _TERMINAL_STATUS_SUCCESS,
        session_id=session_id,
        terminal_status=terminal_status,
        reported_provider=reported_provider,
        reported_model=reported_model,
        reported_version=reported_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
        duration_ms=duration_ms,
        tool_call_counts=tool_call_counts,
        source_urls=tuple(urls),
        final_text=final_text,
        event_count=len(lines),
        unknown_event_count=unknown,
    )


def tool_calls_within_allowed(result: StreamJsonAuditResult) -> bool:
    """True only when every observed tool call is a permitted ``web`` tool."""
    return all(name in _ALLOWED_TOOL_NAMES for name, _count in result.tool_call_counts)
