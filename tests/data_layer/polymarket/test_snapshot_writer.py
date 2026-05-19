"""Tests for WP10 snapshot writer.

All tests offline. Uses pytest tmp_path. No network. No credentials.
No writes to real local_data/ — all writes go to temporary directories.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data_layer.polymarket.snapshot_models import (
    ADAPTER_VERSION,
    MARKET_SOURCE,
    ORDER_BOOK_SOURCE,
    READ_ONLY_PROVENANCE,
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
    generate_snapshot_id,
)
from src.data_layer.polymarket.snapshot_writer import (
    DEFAULT_OUTPUT_DIR,
    MARKETS_JSONL_NAME,
    ORDER_BOOKS_JSONL_NAME,
    SnapshotWriter,
    _validate_output_path,
)


def _make_market_record(snap_id: str = "snap_test_001") -> MarketMetadataSnapshotRecord:
    return MarketMetadataSnapshotRecord(
        snapshot_id=snap_id,
        captured_at_utc="2026-05-19T14:30:22+00:00",
        source=MARKET_SOURCE,
        adapter_version=ADAPTER_VERSION,
        market_id="540817",
        condition_id="0xabc123",
        question="Will X happen?",
        market_status="True",
        outcome_labels=["Yes", "No"],
        token_ids=["tok1", "tok2"],
        resolution_date="2026-12-31",
        category="politics",
        raw_field_names=["id", "question", "clobTokenIds"],
    )


def _make_order_book_record(snap_id: str = "snap_test_001") -> OrderBookSnapshotRecord:
    return OrderBookSnapshotRecord(
        snapshot_id=snap_id,
        captured_at_utc="2026-05-19T14:30:22+00:00",
        source=ORDER_BOOK_SOURCE,
        adapter_version=ADAPTER_VERSION,
        token_id="tok1",
        bids=[{"price": "0.55", "size": "100"}],
        asks=[{"price": "0.58", "size": "50"}],
        raw_field_names=["asks", "bids", "asset_id"],
    )


def _make_manifest(snap_id: str = "snap_test_001") -> SnapshotManifest:
    return SnapshotManifest(
        snapshot_id=snap_id,
        created_at_utc="2026-05-19T14:30:22+00:00",
        tool_name="capture_market_snapshots",
        work_package="WP10",
        markets_requested=3,
        markets_written=1,
        order_books_requested=0,
        order_books_written=0,
        network_used=True,
        output_files=[],
        notes="Read-only test manifest.",
    )


class TestValidateOutputPath:
    def test_rejects_path_without_local_data(self, tmp_path):
        some_path = tmp_path / "some_other_dir"
        with pytest.raises(ValueError, match="local_data"):
            _validate_output_path(some_path)

    def test_rejects_src_path(self, tmp_path):
        src_path = tmp_path / "local_data" / "src" / "snapshots"
        # Contains local_data but also 'src' — should be rejected
        # NOTE: on Windows, tmp_path may have 'Temp' or similar — we test
        # the path that has both local_data and src explicitly
        # The validator rejects 'src' as a forbidden component.
        # We construct a path that has local_data then src.
        # Actually the validator checks all parts — a path like
        # /tmp/local_data/src/snapshots has both; forbidden check fires first.
        src_inside_local = tmp_path / "local_data" / "src" / "snapshots"
        with pytest.raises(ValueError, match="src"):
            _validate_output_path(src_inside_local)

    def test_rejects_docs_path(self, tmp_path):
        docs_path = tmp_path / "local_data" / "docs" / "snapshots"
        with pytest.raises(ValueError, match="docs"):
            _validate_output_path(docs_path)

    def test_accepts_local_data_path(self, tmp_path):
        valid_path = tmp_path / "local_data" / "polymarket" / "snapshots"
        # Should not raise
        _validate_output_path(valid_path)


class TestSnapshotWriterPathValidation:
    def test_writer_refuses_path_without_local_data(self, tmp_path):
        with pytest.raises(ValueError, match="local_data"):
            SnapshotWriter(output_dir=tmp_path / "not_local_data")

    def test_writer_refuses_src_path(self, tmp_path):
        with pytest.raises(ValueError):
            SnapshotWriter(output_dir=tmp_path / "local_data" / "src" / "sub")

    def test_writer_accepts_local_data_path(self, tmp_path):
        valid = tmp_path / "local_data" / "polymarket" / "snapshots"
        writer = SnapshotWriter(output_dir=valid)
        assert writer._output_dir == valid

    def test_writer_allow_any_bypasses_check(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        assert writer._output_dir == tmp_path

    def test_default_output_dir_is_local_data(self):
        # DEFAULT_OUTPUT_DIR should contain local_data
        assert "local_data" in str(DEFAULT_OUTPUT_DIR)


class TestSnapshotWriterWriteMarkets:
    def test_creates_jsonl_file(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        record = _make_market_record()
        out = writer.write_market_snapshots([record])
        assert out.exists()
        assert out.name == MARKETS_JSONL_NAME

    def test_jsonl_file_contains_valid_json_lines(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        record = _make_market_record()
        writer.write_market_snapshots([record])
        lines = (tmp_path / MARKETS_JSONL_NAME).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["market_id"] == "540817"

    def test_multiple_records_written_as_multiple_lines(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        records = [_make_market_record("snap_001"), _make_market_record("snap_002")]
        writer.write_market_snapshots(records)
        lines = (tmp_path / MARKETS_JSONL_NAME).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_append_on_second_call(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        writer.write_market_snapshots([_make_market_record("snap_001")])
        writer.write_market_snapshots([_make_market_record("snap_002")])
        lines = (tmp_path / MARKETS_JSONL_NAME).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_record_contains_read_only_provenance(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        writer.write_market_snapshots([_make_market_record()])
        content = (tmp_path / MARKETS_JSONL_NAME).read_text(encoding="utf-8")
        assert "read_only_provenance" in content
        assert "public-get-only" in content

    def test_record_does_not_contain_large_raw_payload(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        writer.write_market_snapshots([_make_market_record()])
        content = (tmp_path / MARKETS_JSONL_NAME).read_text(encoding="utf-8")
        parsed = json.loads(content.strip())
        # raw_field_names is a list of strings, not the full raw dict
        assert isinstance(parsed["raw_field_names"], list)
        for item in parsed["raw_field_names"]:
            assert isinstance(item, str)


class TestSnapshotWriterWriteOrderBooks:
    def test_creates_jsonl_file(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        record = _make_order_book_record()
        out = writer.write_order_book_snapshots([record])
        assert out.exists()
        assert out.name == ORDER_BOOKS_JSONL_NAME

    def test_jsonl_contains_valid_bids_asks(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        writer.write_order_book_snapshots([_make_order_book_record()])
        lines = (tmp_path / ORDER_BOOKS_JSONL_NAME).read_text(encoding="utf-8").splitlines()
        parsed = json.loads(lines[0])
        assert parsed["bids"] == [{"price": "0.55", "size": "100"}]
        assert parsed["asks"] == [{"price": "0.58", "size": "50"}]
        assert "read_only_provenance" in parsed


class TestSnapshotWriterWriteManifest:
    def test_creates_json_file(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        manifest = _make_manifest("snap_test_001")
        out = writer.write_manifest(manifest)
        assert out.exists()
        assert "manifest_snap_test_001" in out.name

    def test_manifest_is_valid_json(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        writer.write_manifest(_make_manifest())
        manifest_files = list(tmp_path.glob("manifest_*.json"))
        assert len(manifest_files) == 1
        parsed = json.loads(manifest_files[0].read_text(encoding="utf-8"))
        assert parsed["work_package"] == "WP10"
        assert parsed["tool_name"] == "capture_market_snapshots"


class TestSnapshotWriterWriteAll:
    def test_write_all_success(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        result = writer.write_all(
            market_records=[_make_market_record()],
            order_book_records=[],
            manifest=_make_manifest(),
        )
        assert result.success is True
        assert result.markets_written == 1
        assert result.order_books_written == 0
        assert result.markets_file is not None
        assert result.order_books_file is None
        assert result.manifest_file is not None
        assert result.error is None

    def test_write_all_with_order_books(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        result = writer.write_all(
            market_records=[_make_market_record()],
            order_book_records=[_make_order_book_record()],
            manifest=_make_manifest(),
        )
        assert result.success is True
        assert result.order_books_written == 1
        assert result.order_books_file is not None

    def test_write_all_empty_records_skips_jsonl(self, tmp_path):
        writer = SnapshotWriter(output_dir=tmp_path, _allow_any_output_dir=True)
        result = writer.write_all(
            market_records=[],
            order_book_records=[],
            manifest=_make_manifest(),
        )
        assert result.success is True
        assert result.markets_file is None
        assert result.order_books_file is None
        assert result.manifest_file is not None

    def test_write_all_creates_output_dir(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        writer = SnapshotWriter(output_dir=nested, _allow_any_output_dir=True)
        result = writer.write_all(
            market_records=[_make_market_record()],
            order_book_records=[],
            manifest=_make_manifest(),
        )
        assert result.success is True
        assert nested.is_dir()
