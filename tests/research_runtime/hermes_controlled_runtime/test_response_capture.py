"""WP175H v0.21.3 output-handling traps (R008 usage fails closed, R009 bounded).

Pinned v0.21.3 has no stream-json: the final response is plain stdout and usage
comes from a bounded ``--usage-file`` JSON report. A valid usage report is mandatory
success evidence, and cost acceptance is fail-closed on unknown cost.
"""

from __future__ import annotations

import json
from decimal import Decimal

from src.research_runtime.hermes_controlled_runtime import (
    COST_ABOVE_THRESHOLD,
    COST_ACCEPTED,
    COST_EVIDENCE_UNAVAILABLE,
    capture_final_response,
    cost_acceptance,
    parse_usage_report,
)
from src.research_runtime.hermes_controlled_runtime import response_capture as rc


def _full_usage(**overrides) -> bytes:
    """A complete v0.21.3 success-evidence usage object (exact tagged keys)."""
    doc = {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
        "api_calls": 1,
        "estimated_cost_usd": "0.04",
        "cost_status": "estimated",
        "cost_source": "official_docs_snapshot",
        "model": "example-model",
        "provider": "example-provider",
        "session_id": "sess-1",
        "completed": True,
        "failed": False,
    }
    doc.update(overrides)
    return json.dumps(doc).encode("utf-8")


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


def test_valid_usage_report_is_sanitized_success_evidence():
    report = parse_usage_report(_full_usage())
    assert report.ok is True
    assert report.diagnostic == rc.USAGE_OK
    assert report.input_tokens == 10 and report.output_tokens == 20
    assert report.total_tokens == 30 and report.api_calls == 1
    assert report.estimated_cost_usd == "0.04"
    assert report.cost_status == "estimated"
    assert report.cost_source == "official_docs_snapshot"
    assert report.session_id == "sess-1"
    assert report.completed is True and report.failed is False


def test_missing_usage_file_fails_closed():  # T12
    report = parse_usage_report(None)
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_MISSING


def test_r008_malformed_usage_report_fails_closed_without_raw_echo():  # T13
    poison = b'{bad json SENSITIVE_TOKEN_ghp_abcdefghij}'
    report = parse_usage_report(poison)
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_MALFORMED
    assert "SENSITIVE" not in repr(report)


def test_oversized_usage_file_fails_boundedly():
    report = parse_usage_report(b"{" + b"0" * 100, max_bytes=10)
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_TOO_LARGE


def test_usage_completed_not_true_fails_closed():  # T14
    for value in (False, "true", 1, None):
        report = parse_usage_report(_full_usage(completed=value))
        assert report.ok is False
        assert report.diagnostic == rc.USAGE_INCOMPLETE


def test_usage_failed_flag_set_fails_closed():  # T15
    report = parse_usage_report(_full_usage(failed=True))
    assert report.ok is False
    assert report.diagnostic == rc.USAGE_FAILED_FLAG


def test_usage_integer_fields_type_and_range_fail_closed():  # T21
    for override in (
        {"input_tokens": -5},
        {"output_tokens": "lots"},
        {"total_tokens": None},
        {"api_calls": True},  # bool is not an int here
    ):
        report = parse_usage_report(_full_usage(**override))
        assert report.ok is False
        assert report.diagnostic == rc.USAGE_FIELD_INVALID


def test_usage_missing_identity_label_fails_closed():
    for label in ("model", "provider", "session_id"):
        doc = json.loads(_full_usage().decode())
        del doc[label]
        report = parse_usage_report(json.dumps(doc).encode())
        assert report.ok is False
        assert report.diagnostic == rc.USAGE_FIELD_INVALID


def test_cost_acceptance_known_cost_within_threshold():
    ok = parse_usage_report(_full_usage(estimated_cost_usd="1.50", cost_status="actual"))
    assert cost_acceptance(ok, Decimal("2")) == COST_ACCEPTED


def test_cost_acceptance_above_threshold():  # T17
    over = parse_usage_report(_full_usage(estimated_cost_usd="9.99", cost_status="estimated"))
    assert cost_acceptance(over, Decimal("2")) == COST_ABOVE_THRESHOLD


def test_cost_acceptance_unknown_or_missing_is_unavailable():  # T16
    # Missing cost is never treated as zero.
    missing = parse_usage_report(None)
    assert cost_acceptance(missing, Decimal("2")) == COST_EVIDENCE_UNAVAILABLE
    # cost_status "unknown" (exact tagged vocabulary) is not a known cost.
    unknown = parse_usage_report(_full_usage(estimated_cost_usd="0.01", cost_status="unknown"))
    assert cost_acceptance(unknown, Decimal("2")) == COST_EVIDENCE_UNAVAILABLE
    # An invalid cost string is unavailable, not accepted.
    bad = parse_usage_report(_full_usage(estimated_cost_usd="abc", cost_status="actual"))
    assert cost_acceptance(bad, Decimal("2")) == COST_EVIDENCE_UNAVAILABLE
    # A missing cost_status is unavailable even with a numeric cost present.
    doc = json.loads(_full_usage().decode())
    del doc["cost_status"]
    no_status = parse_usage_report(json.dumps(doc).encode())
    assert cost_acceptance(no_status, Decimal("2")) == COST_EVIDENCE_UNAVAILABLE


def test_included_zero_cost_is_accepted():
    included = parse_usage_report(
        _full_usage(estimated_cost_usd="0", cost_status="included", cost_source="none")
    )
    assert cost_acceptance(included, Decimal("2")) == COST_ACCEPTED
