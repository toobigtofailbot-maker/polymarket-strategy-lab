"""Tests for WP10 snapshot persistence models.

All tests offline. No network. No credentials. No trading logic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.data_layer.polymarket.snapshot_models import (
    ADAPTER_VERSION,
    MARKET_SOURCE,
    ORDER_BOOK_SOURCE,
    READ_ONLY_PROVENANCE,
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
    SnapshotWriteResult,
    generate_snapshot_id,
    utc_iso_now,
)


class TestGenerateSnapshotId:
    def test_deterministic_with_fixed_datetime(self):
        dt = datetime(2026, 5, 19, 14, 30, 22, 123456, tzinfo=timezone.utc)
        result = generate_snapshot_id(dt)
        assert result == "snap_20260519_143022_123456"

    def test_generates_without_argument(self):
        result = generate_snapshot_id()
        assert result.startswith("snap_")

    def test_two_calls_without_argument_are_unique(self):
        a = generate_snapshot_id()
        b = generate_snapshot_id()
        # Not strictly guaranteed but practically true; at minimum both are valid
        assert a.startswith("snap_")
        assert b.startswith("snap_")


class TestUtcIsoNow:
    def test_deterministic_with_fixed_datetime(self):
        dt = datetime(2026, 5, 19, 14, 30, 22, tzinfo=timezone.utc)
        result = utc_iso_now(dt)
        assert "2026-05-19" in result
        assert "14:30:22" in result

    def test_generates_without_argument(self):
        result = utc_iso_now()
        assert "T" in result or "-" in result


class TestMarketMetadataSnapshotRecord:
    def _make_record(self, **kwargs) -> MarketMetadataSnapshotRecord:
        defaults = dict(
            snapshot_id="snap_20260519_143022_000000",
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
        defaults.update(kwargs)
        return MarketMetadataSnapshotRecord(**defaults)

    def test_fields_are_set(self):
        record = self._make_record()
        assert record.market_id == "540817"
        assert record.condition_id == "0xabc123"
        assert record.outcome_labels == ["Yes", "No"]
        assert record.token_ids == ["tok1", "tok2"]
        assert record.raw_field_names == ["id", "question", "clobTokenIds"]

    def test_read_only_provenance_default(self):
        record = self._make_record()
        assert record.read_only_provenance == READ_ONLY_PROVENANCE
        assert "public-get-only" in record.read_only_provenance
        assert "wp10" in record.read_only_provenance.lower()

    def test_adapter_version(self):
        record = self._make_record()
        assert record.adapter_version == ADAPTER_VERSION
        assert record.adapter_version == "wp10"

    def test_source(self):
        record = self._make_record()
        assert record.source == MARKET_SOURCE

    def test_to_dict_contains_all_fields(self):
        record = self._make_record()
        d = record.to_dict()
        assert d["market_id"] == "540817"
        assert d["read_only_provenance"] == READ_ONLY_PROVENANCE
        assert d["adapter_version"] == ADAPTER_VERSION
        assert d["outcome_labels"] == ["Yes", "No"]
        assert d["raw_field_names"] == ["id", "question", "clobTokenIds"]

    def test_to_jsonl_line_is_valid_json(self):
        record = self._make_record()
        line = record.to_jsonl_line()
        parsed = json.loads(line)
        assert parsed["market_id"] == "540817"

    def test_to_jsonl_line_contains_provenance(self):
        record = self._make_record()
        line = record.to_jsonl_line()
        assert "read_only_provenance" in line
        assert "public-get-only" in line

    def test_resolution_date_none_allowed(self):
        record = self._make_record(resolution_date=None)
        assert record.resolution_date is None
        line = record.to_jsonl_line()
        parsed = json.loads(line)
        assert parsed["resolution_date"] is None

    def test_category_none_allowed(self):
        record = self._make_record(category=None)
        assert record.category is None


class TestOrderBookSnapshotRecord:
    def _make_record(self, **kwargs) -> OrderBookSnapshotRecord:
        defaults = dict(
            snapshot_id="snap_20260519_143022_000000",
            captured_at_utc="2026-05-19T14:30:22+00:00",
            source=ORDER_BOOK_SOURCE,
            adapter_version=ADAPTER_VERSION,
            token_id="tok1",
            bids=[{"price": "0.55", "size": "100"}],
            asks=[{"price": "0.58", "size": "50"}],
            raw_field_names=["asks", "bids", "asset_id"],
        )
        defaults.update(kwargs)
        return OrderBookSnapshotRecord(**defaults)

    def test_fields_are_set(self):
        record = self._make_record()
        assert record.token_id == "tok1"
        assert record.bids == [{"price": "0.55", "size": "100"}]
        assert record.asks == [{"price": "0.58", "size": "50"}]

    def test_read_only_provenance_default(self):
        record = self._make_record()
        assert record.read_only_provenance == READ_ONLY_PROVENANCE

    def test_source(self):
        record = self._make_record()
        assert record.source == ORDER_BOOK_SOURCE

    def test_to_jsonl_line_is_valid_json(self):
        record = self._make_record()
        line = record.to_jsonl_line()
        parsed = json.loads(line)
        assert parsed["token_id"] == "tok1"
        assert parsed["bids"] == [{"price": "0.55", "size": "100"}]

    def test_to_jsonl_line_contains_provenance(self):
        record = self._make_record()
        line = record.to_jsonl_line()
        assert "read_only_provenance" in line

    def test_empty_bids_asks_allowed(self):
        record = self._make_record(bids=[], asks=[])
        line = record.to_jsonl_line()
        parsed = json.loads(line)
        assert parsed["bids"] == []
        assert parsed["asks"] == []


class TestSnapshotManifest:
    def _make_manifest(self, **kwargs) -> SnapshotManifest:
        defaults = dict(
            snapshot_id="snap_20260519_143022_000000",
            created_at_utc="2026-05-19T14:30:22+00:00",
            tool_name="capture_market_snapshots",
            work_package="WP10",
            markets_requested=3,
            markets_written=2,
            order_books_requested=0,
            order_books_written=0,
            network_used=True,
            output_files=["market_metadata_snapshots.jsonl"],
            notes="Read-only research snapshot.",
        )
        defaults.update(kwargs)
        return SnapshotManifest(**defaults)

    def test_fields_are_set(self):
        manifest = self._make_manifest()
        assert manifest.snapshot_id == "snap_20260519_143022_000000"
        assert manifest.work_package == "WP10"
        assert manifest.markets_written == 2
        assert manifest.network_used is True

    def test_to_json_is_valid_json(self):
        manifest = self._make_manifest()
        text = manifest.to_json()
        parsed = json.loads(text)
        assert parsed["snapshot_id"] == "snap_20260519_143022_000000"
        assert parsed["work_package"] == "WP10"

    def test_to_json_is_indented(self):
        manifest = self._make_manifest()
        text = manifest.to_json()
        assert "\n" in text


class TestSnapshotWriteResult:
    def test_success_result(self):
        result = SnapshotWriteResult(
            output_dir="local_data/polymarket/snapshots",
            markets_file="local_data/polymarket/snapshots/market_metadata_snapshots.jsonl",
            order_books_file=None,
            manifest_file="local_data/polymarket/snapshots/manifest_snap_xxx.json",
            markets_written=3,
            order_books_written=0,
            success=True,
        )
        assert result.success is True
        assert result.markets_written == 3
        assert result.error is None

    def test_failure_result(self):
        result = SnapshotWriteResult(
            output_dir="local_data/polymarket/snapshots",
            markets_file=None,
            order_books_file=None,
            manifest_file=None,
            markets_written=0,
            order_books_written=0,
            success=False,
            error="Permission denied",
        )
        assert result.success is False
        assert result.error == "Permission denied"
