"""Tests for offline snapshot quality checks.

All tests are offline and use synthetic in-memory records or tmp_path files.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.data_layer.polymarket.snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)
from src.data_layer.polymarket.snapshot_quality import (
    ERROR,
    WARNING,
    QualityIssue,
    build_snapshot_quality_report,
    evaluate_quality_gate,
)
from src.data_layer.polymarket.snapshot_reader import (
    SnapshotFileSummary,
    SnapshotLoadResult,
    load_market_snapshot_records,
)


def _market_record(
    market_id: str = "market-1",
    snapshot_id: str = "snap_001",
    token_ids: list | None = None,
    outcome_labels: list | None = None,
    category: str | None = "crypto",
    resolution_date: str | None = "2026-12-31",
    provenance: str = "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
) -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc="2026-01-01T00:00:00+00:00",
        source="gamma-api/markets",
        adapter_version="wp10",
        market_id=market_id,
        condition_id=f"cond-{market_id}",
        question=f"Question for {market_id}?",
        market_status="active",
        outcome_labels=outcome_labels if outcome_labels is not None else ["Yes", "No"],
        token_ids=token_ids if token_ids is not None else [f"token-{market_id}-yes", f"token-{market_id}-no"],
        resolution_date=resolution_date,
        category=category,
        raw_field_names=["id", "question"],
        read_only_provenance=provenance,
    )


def _order_book_record(
    token_id: str = "token-market-1-yes",
    snapshot_id: str = "snap_001",
) -> OrderBookSnapshotRecord:
    return OrderBookSnapshotRecord(
        snapshot_id=snapshot_id,
        captured_at_utc="2026-01-01T00:00:00+00:00",
        source="clob-api/book",
        adapter_version="wp10",
        token_id=token_id,
        bids=[],
        asks=[],
        raw_field_names=["asset_id", "bids", "asks"],
        read_only_provenance="polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    )


def _manifest(
    snapshot_id: str = "snap_001",
    output_files: list | None = None,
    network_used: bool = True,
) -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        created_at_utc="2026-01-01T00:00:00+00:00",
        tool_name="capture_market_snapshots",
        work_package="WP10",
        markets_requested=1,
        markets_written=1,
        order_books_requested=0,
        order_books_written=0,
        network_used=network_used,
        output_files=output_files if output_files is not None else ["market_metadata_snapshots.jsonl"],
        notes="test",
    )


def _load_result(records: list, errors: list | None = None) -> SnapshotLoadResult:
    return SnapshotLoadResult(
        records=records,
        errors=errors or [],
        lines_read=len(records),
        lines_skipped=len(errors or []),
        source_file=None,
    )


def _file_summary(tmp_path: Path) -> SnapshotFileSummary:
    return SnapshotFileSummary(
        input_dir=str(tmp_path),
        markets_file_present=True,
        order_books_file_present=True,
        manifest_files=[],
        manifest_count=1,
    )


def _report(
    tmp_path: Path,
    *,
    markets: list,
    order_books: list | None = None,
    manifests: list | None = None,
    market_errors: list | None = None,
    fail_on_warning: bool = False,
):
    return build_snapshot_quality_report(
        file_summary=_file_summary(tmp_path),
        market_result=_load_result(markets, market_errors),
        order_book_result=_load_result(order_books or []),
        manifest_result=_load_result(manifests if manifests is not None else [_manifest()]),
        fail_on_warning=fail_on_warning,
        generated_at_utc="2026-01-02T00:00:00+00:00",
    )


def test_valid_minimal_records_pass(tmp_path):
    report = _report(
        tmp_path,
        markets=[_market_record()],
        order_books=[_order_book_record("token-market-1-yes")],
    )

    assert report.gate_result.passed is True
    assert report.gate_result.error_count == 0
    assert report.catalog_summary.unique_market_count == 1
    assert report.catalog_summary.order_book_tokens_without_market_count == 0


def test_malformed_reader_errors_become_quality_errors(tmp_path):
    path = tmp_path / "market_metadata_snapshots.jsonl"
    path.write_text("{bad json}\n" + json.dumps(_market_record().to_dict()) + "\n")
    read_result = load_market_snapshot_records(tmp_path)

    report = build_snapshot_quality_report(
        file_summary=_file_summary(tmp_path),
        market_result=read_result,
        order_book_result=_load_result([]),
        manifest_result=_load_result([_manifest()]),
        generated_at_utc="2026-01-02T00:00:00+00:00",
    )

    assert any(issue.code == "MALFORMED_LOCAL_RECORD" for issue in report.issues)
    assert report.gate_result.passed is False


def test_missing_required_fields_loaded_record_produce_errors(tmp_path):
    record = _market_record()
    record.market_id = ""
    record.question = ""
    record.token_ids = "not-a-list"

    report = _report(tmp_path, markets=[record])

    codes = {issue.code for issue in report.issues}
    assert "REQUIRED_FIELD_EMPTY" in codes
    assert "REQUIRED_FIELD_NOT_LIST" in codes
    assert report.gate_result.error_count >= 3


def test_token_outcome_mismatch_is_warning_and_gate_can_fail_on_warning(tmp_path):
    record = _market_record(token_ids=["token-a", "token-b"], outcome_labels=["Yes"])

    report = _report(tmp_path, markets=[record])
    strict_report = _report(tmp_path, markets=[record], fail_on_warning=True)

    assert any(issue.code == "TOKEN_OUTCOME_LENGTH_MISMATCH" for issue in report.issues)
    assert report.gate_result.passed is True
    assert strict_report.gate_result.passed is False


def test_duplicate_market_id_within_snapshot_detected(tmp_path):
    records = [_market_record("market-1"), _market_record("market-1")]
    report = _report(tmp_path, markets=records)

    assert any(issue.code == "DUPLICATE_MARKET_ID_IN_SNAPSHOT" for issue in report.issues)
    assert report.gate_result.passed is False


def test_duplicate_token_id_across_markets_detected(tmp_path):
    records = [
        _market_record("market-1", token_ids=["shared-token", "token-a"]),
        _market_record("market-2", token_ids=["shared-token", "token-b"]),
    ]
    report = _report(tmp_path, markets=records)

    assert any(issue.code == "TOKEN_ID_MULTIPLE_MARKETS" for issue in report.issues)
    assert report.gate_result.passed is False


def test_missing_read_only_provenance_detected(tmp_path):
    report = _report(tmp_path, markets=[_market_record(provenance="")])

    assert any(issue.code == "READ_ONLY_PROVENANCE_MISSING" for issue in report.issues)


def test_manifest_output_files_empty_detected_and_network_summarized(tmp_path):
    report = _report(tmp_path, markets=[_market_record()], manifests=[_manifest(output_files=[])])

    assert any(issue.code == "MANIFEST_OUTPUT_FILES_EMPTY" for issue in report.issues)
    assert report.snapshot_summary.manifest_network_used_true_count == 1
    assert report.snapshot_summary.manifest_output_files_empty_count == 1


def test_catalog_summary_fields_present(tmp_path):
    records = [
        _market_record("market-1", category=None, resolution_date=None),
        _market_record("market-2", snapshot_id="snap_002"),
    ]
    report = _report(tmp_path, markets=records)

    assert report.catalog_summary.unique_market_count == 2
    assert report.catalog_summary.total_record_count == 2
    assert report.catalog_summary.missing_category_count == 1
    assert report.catalog_summary.missing_resolution_date_count == 1
    assert report.catalog_summary.latest_snapshot_timestamp == "2026-01-01T00:00:00+00:00"


def test_order_book_token_without_market_is_warning(tmp_path):
    report = _report(
        tmp_path,
        markets=[_market_record()],
        order_books=[_order_book_record("unknown-token")],
    )

    assert any(issue.code == "ORDER_BOOK_TOKEN_WITHOUT_MARKET" for issue in report.issues)
    assert report.gate_result.warning_count == 1


def test_evaluate_quality_gate_default_passes_warnings():
    issues = [QualityIssue(WARNING, "WARN", "message", "market")]

    assert evaluate_quality_gate(issues).passed is True
    assert evaluate_quality_gate(issues, fail_on_warning=True).passed is False


def test_evaluate_quality_gate_fails_errors():
    issues = [QualityIssue(ERROR, "ERR", "message", "market")]

    assert evaluate_quality_gate(issues).passed is False
