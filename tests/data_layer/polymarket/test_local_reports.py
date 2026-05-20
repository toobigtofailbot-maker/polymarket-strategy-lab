"""Tests for sanitized local quality report rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data_layer.polymarket.local_reports import (
    render_quality_report_json,
    render_quality_report_markdown,
    write_local_json_report,
    write_local_report,
)
from src.data_layer.polymarket.snapshot_quality import build_snapshot_quality_report
from src.data_layer.polymarket.snapshot_reader import SnapshotFileSummary, SnapshotLoadResult
from tests.data_layer.polymarket.test_snapshot_quality import _manifest, _market_record


def _load_result(records: list) -> SnapshotLoadResult:
    return SnapshotLoadResult(
        records=records,
        errors=[],
        lines_read=len(records),
        lines_skipped=0,
        source_file=None,
    )


def _report(tmp_path: Path):
    return build_snapshot_quality_report(
        file_summary=SnapshotFileSummary(
            input_dir=str(tmp_path),
            markets_file_present=True,
            order_books_file_present=False,
            manifest_files=[],
            manifest_count=1,
        ),
        market_result=_load_result([_market_record()]),
        order_book_result=_load_result([]),
        manifest_result=_load_result([_manifest()]),
        generated_at_utc="2026-01-02T00:00:00+00:00",
    )


def test_markdown_contains_gate_status_and_safety_statement(tmp_path):
    markdown = render_quality_report_markdown(_report(tmp_path))

    assert "Quality gate" in markdown
    assert "PASS" in markdown
    assert "Safety Statement" in markdown
    assert "Offline quality/reporting infrastructure only" in markdown
    assert "does not call Polymarket APIs" in markdown


def test_markdown_contains_guarded_capture_counts_and_caveat(tmp_path):
    markdown = render_quality_report_markdown(_report(tmp_path))

    assert "Guard-enforced manifests" in markdown
    assert "Unguarded network-used manifests" in markdown
    assert "Guard-provenance-unknown manifests" in markdown
    assert "Local WP16 policy provenance count" in markdown
    assert "WP8-D002 remains OPEN" in markdown
    assert "local budgets are not confirmed venue limits" in markdown


def test_json_report_is_sanitized_and_has_no_raw_payload(tmp_path):
    data = render_quality_report_json(_report(tmp_path))

    snapshot_summary = data["snapshot_summary"]
    assert snapshot_summary["guard_enforced_manifest_count"] == 1
    assert snapshot_summary["unguarded_network_manifest_count"] == 0
    assert snapshot_summary["guard_provenance_unknown_manifest_count"] == 0
    assert snapshot_summary["local_budget_policy_manifest_count"] == 1
    assert data["sanitization"]["large_source_payloads_included"] is False
    assert data["sanitization"]["credentials_included"] is False
    assert "raw_payload" not in json.dumps(data).lower()
    assert "api_key" not in json.dumps(data).lower()
    assert "private_key" not in json.dumps(data).lower()


def test_markdown_writer_accepts_local_data_path(tmp_path):
    out = tmp_path / "local_data" / "polymarket" / "reports" / "snapshot_quality.local.md"
    written = write_local_report("# report\n", out)

    assert written == out.resolve()
    assert out.read_text(encoding="utf-8") == "# report\n"


def test_json_writer_accepts_local_data_path(tmp_path):
    out = tmp_path / "local_data" / "polymarket" / "reports" / "snapshot_quality.local.json"
    written = write_local_json_report({"ok": True}, out)

    assert written == out.resolve()
    assert json.loads(out.read_text(encoding="utf-8")) == {"ok": True}


def test_writer_refuses_output_outside_local_data(tmp_path):
    with pytest.raises(ValueError, match="local_data"):
        write_local_report("# report\n", tmp_path / "reports" / "bad.md")


def test_writer_refuses_protected_path_with_local_data_inside(tmp_path):
    with pytest.raises(ValueError, match="protected"):
        write_local_json_report({"ok": True}, tmp_path / "docs" / "local_data" / "bad.json")
