"""WP175H v0.21.3 output-handling traps (R008 usage fails closed, R009 bounded).

Pinned v0.21.3 has no stream-json: the final response is plain stdout and usage
comes from a bounded ``--usage-file`` JSON report.
"""

from __future__ import annotations

import json
from decimal import Decimal

from src.research_runtime.hermes_controlled_runtime import (
    capture_final_response,
    cost_within_cap,
    parse_usage_report,
)
from src.research_runtime.hermes_controlled_runtime import response_capture as rc


def test_capture_final_response_returns_plain_text():
    result = capture_final_response('{"ok": true}', max_bytes=1_000_000)
    assert result.ok is True
    assert result.diagnostic == rc.RESPONSE_OK
    assert result.final_text == '{"ok": true}'


def test_empty_response_fails_closed():
    result = capture_final_response("   \n ", max_bytes=1_000_000)
    assert result.ok is False
    assert result.diagnostic == rc.RESPONSE_EMPTY


def test_r009_oversized_stdout_fails_boundedly():
    result = capture_final_response(b"x" * 5000, max_bytes=100)
    assert result.ok is False
    assert result.diagnostic == rc.RESPONSE_TOO_LARGE
    assert result.final_text is None


def test_valid_usage_report_is_sanitized():
    usage = json.dumps(
        {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
            "estimated_cost_usd": "0.04",
            "model": "example-model",
            "provider": "example-provider",
            "session_id": "sess-1",
            "completed": True,
        }
    ).encode("utf-8")
    report = parse_usage_report(usage)
    assert report.ok is True
    assert report.input_tokens == 10 and report.output_tokens == 20
    assert report.total_tokens == 30
    assert report.estimated_cost_usd == "0.04"
    assert report.session_id == "sess-1"
    assert report.completed is True


def test_missing_usage_file_fails_closed():
    report = parse_usage_report(None)
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_MISSING


def test_r008_malformed_usage_report_fails_closed_without_raw_echo():
    poison = b'{bad json SENSITIVE_TOKEN_ghp_abcdefghij}'
    report = parse_usage_report(poison)
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_MALFORMED
    assert "SENSITIVE" not in repr(report)


def test_oversized_usage_file_fails_boundedly():
    report = parse_usage_report(b"{" + b"0" * 100, max_bytes=10)
    assert report.diagnostic == rc.USAGE_TOO_LARGE


def test_usage_rejects_unsafe_types():
    usage = json.dumps(
        {"input_tokens": -5, "output_tokens": "lots", "estimated_cost_usd": "abc"}
    ).encode("utf-8")
    report = parse_usage_report(usage)
    assert report.ok is True  # object parses; unsafe fields are dropped
    assert report.input_tokens is None
    assert report.output_tokens is None
    assert report.estimated_cost_usd is None


def test_cost_within_cap():
    ok = parse_usage_report(json.dumps({"estimated_cost_usd": "1.50"}).encode())
    assert cost_within_cap(ok, Decimal("2")) is True
    over = parse_usage_report(json.dumps({"estimated_cost_usd": "9.99"}).encode())
    assert cost_within_cap(over, Decimal("2")) is False
    missing = parse_usage_report(None)
    assert cost_within_cap(missing, Decimal("2")) is True
