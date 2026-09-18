"""WP175H stream-json audit parser traps (R008 malformed, R009 oversized)."""

from __future__ import annotations

import json

from src.research_runtime.hermes_controlled_runtime import (
    parse_stream_json,
    tool_calls_within_allowed,
)
from src.research_runtime.hermes_controlled_runtime import stream_json as sj


def _success_events(final_text: str = '{"ok": true}') -> list[dict]:
    return [
        {
            "type": "session",
            "session_id": "sess-1",
            "provider": "example-provider",
            "model": "example-model",
            "version": "hermes-agent 0.21.3",
        },
        {"type": "tool_call", "tool": "web_search"},
        {"type": "tool_call", "tool": "web_extract"},
        {"type": "tool_result", "tool": "web_search", "urls": ["https://example.com/a"]},
        {
            "type": "result",
            "subtype": "success",
            "result": final_text,
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "total_cost_usd": "0.05",
            "duration_ms": 900,
        },
    ]


def _transcript(events) -> bytes:
    return ("\n".join(json.dumps(e) for e in events)).encode("utf-8")


def test_success_collects_audit_facts():
    result = parse_stream_json(_transcript(_success_events()), max_bytes=1_000_000)
    assert result.ok is True
    assert result.diagnostic == sj.STREAM_OK
    assert result.session_id == "sess-1"
    assert result.reported_version == "hermes-agent 0.21.3"
    assert result.input_tokens == 10 and result.output_tokens == 20
    assert result.estimated_cost_usd == "0.05"
    assert result.duration_ms == 900
    assert dict(result.tool_call_counts) == {"web_search": 1, "web_extract": 1}
    assert result.source_urls == ("https://example.com/a",)
    assert result.final_text == '{"ok": true}'
    assert tool_calls_within_allowed(result) is True


def test_r008_malformed_stream_json_fails_closed_without_raw_echo():
    poison = "SENSITIVE https://leak.example/secret"
    raw = json.dumps({"type": "session"}) + "\n" + poison + " {not json"
    result = parse_stream_json(raw, max_bytes=1_000_000)
    assert result.ok is False
    assert result.diagnostic == sj.STREAM_MALFORMED
    assert result.final_text is None
    # The neutral audit result carries no raw payload text.
    assert poison not in repr(result)


def test_r009_oversized_stdout_fails_boundedly():
    big = _transcript(_success_events("x" * 100))
    result = parse_stream_json(big, max_bytes=10)
    assert result.ok is False
    assert result.diagnostic == sj.STREAM_OUTPUT_TOO_LARGE


def test_no_final_result_fails_closed():
    events = [{"type": "session", "session_id": "s"}, {"type": "tool_call", "tool": "web_search"}]
    result = parse_stream_json(_transcript(events), max_bytes=1_000_000)
    assert result.diagnostic == sj.STREAM_NO_FINAL_RESULT


def test_ambiguous_two_results_fails_closed():
    events = _success_events()
    events.append({"type": "result", "subtype": "success", "result": "{}"})
    result = parse_stream_json(_transcript(events), max_bytes=1_000_000)
    assert result.diagnostic == sj.STREAM_AMBIGUOUS_RESULT


def test_error_subtype_is_not_ok():
    events = [
        {"type": "session", "version": "hermes-agent 0.21.3"},
        {"type": "result", "subtype": "error"},
    ]
    result = parse_stream_json(_transcript(events), max_bytes=1_000_000)
    assert result.diagnostic == sj.STREAM_OK
    assert result.ok is False
    assert result.terminal_status == "ERROR"
    assert result.final_text is None


def test_empty_stream_fails_closed():
    result = parse_stream_json("   \n  ", max_bytes=1_000_000)
    assert result.diagnostic == sj.STREAM_EMPTY


def test_unknown_events_are_counted_not_crashed():
    events = _success_events()
    events.insert(1, {"type": "totally_unknown_shape", "payload": {"deep": [1, 2, 3]}})
    events.insert(2, "a-bare-string-event-line")
    # a bare string line is valid JSON but not a dict -> counted unknown
    raw = "\n".join(
        (json.dumps(e) if not isinstance(e, str) else json.dumps(e)) for e in events
    )
    result = parse_stream_json(raw, max_bytes=1_000_000)
    assert result.ok is True
    assert result.unknown_event_count >= 2


def test_tool_calls_within_allowed_flags_forbidden_tool():
    events = _success_events()
    events.insert(1, {"type": "tool_call", "tool": "terminal"})
    result = parse_stream_json(_transcript(events), max_bytes=1_000_000)
    assert result.ok is True
    assert tool_calls_within_allowed(result) is False


def test_final_text_over_hard_cap_fails_closed():
    huge = "y" * (sj._MAX_FINAL_TEXT_BYTES + 10)
    events = _success_events(huge)
    result = parse_stream_json(_transcript(events), max_bytes=10_000_000)
    assert result.diagnostic == sj.STREAM_OUTPUT_TOO_LARGE
