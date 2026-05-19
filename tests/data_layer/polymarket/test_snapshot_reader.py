"""Tests for snapshot_reader.py (WP11).

All tests are offline. No live network access. Uses tmp_path fixtures only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data_layer.polymarket.snapshot_reader import (
    SnapshotFileSummary,
    SnapshotLoadResult,
    list_snapshot_files,
    load_market_snapshot_records,
    load_order_book_snapshot_records,
    load_snapshot_manifests,
)
from src.data_layer.polymarket.snapshot_models import (
    MarketMetadataSnapshotRecord,
    OrderBookSnapshotRecord,
    SnapshotManifest,
)


def _make_market_record_dict(
    market_id: str = "market-1",
    snapshot_id: str = "snap_001",
    captured_at: str = "2026-01-01T00:00:00+00:00",
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "captured_at_utc": captured_at,
        "source": "gamma-api/markets",
        "adapter_version": "wp10",
        "market_id": market_id,
        "condition_id": f"cond-{market_id}",
        "question": f"Question for {market_id}?",
        "market_status": "active",
        "outcome_labels": ["Yes", "No"],
        "token_ids": [f"token-{market_id}-yes", f"token-{market_id}-no"],
        "resolution_date": "2026-12-31",
        "category": "crypto",
        "raw_field_names": ["id", "question"],
        "read_only_provenance": "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    }


def _make_order_book_record_dict(
    token_id: str = "token-1",
    snapshot_id: str = "snap_001",
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "captured_at_utc": "2026-01-01T00:00:00+00:00",
        "source": "clob-api/book",
        "adapter_version": "wp10",
        "token_id": token_id,
        "bids": [{"price": "0.5", "size": "100"}],
        "asks": [{"price": "0.6", "size": "50"}],
        "raw_field_names": ["market", "asset_id", "bids", "asks"],
        "read_only_provenance": "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only",
    }


def _make_manifest_dict(snapshot_id: str = "snap_001") -> dict:
    return {
        "snapshot_id": snapshot_id,
        "created_at_utc": "2026-01-01T00:00:00+00:00",
        "tool_name": "capture_market_snapshots",
        "work_package": "WP10",
        "markets_requested": 3,
        "markets_written": 3,
        "order_books_requested": 0,
        "order_books_written": 0,
        "network_used": True,
        "output_files": ["market_metadata_snapshots.jsonl"],
        "notes": "test manifest",
    }


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


class TestListSnapshotFiles:
    def test_missing_directory_returns_empty_summary(self, tmp_path):
        missing = tmp_path / "nonexistent"
        result = list_snapshot_files(missing)
        assert isinstance(result, SnapshotFileSummary)
        assert result.markets_file_present is False
        assert result.order_books_file_present is False
        assert result.manifest_count == 0
        assert result.manifest_files == []

    def test_empty_directory(self, tmp_path):
        result = list_snapshot_files(tmp_path)
        assert result.markets_file_present is False
        assert result.order_books_file_present is False
        assert result.manifest_count == 0

    def test_detects_present_files(self, tmp_path):
        (tmp_path / "market_metadata_snapshots.jsonl").write_text("")
        (tmp_path / "order_book_snapshots.jsonl").write_text("")
        (tmp_path / "manifest_snap_001.json").write_text("{}")
        (tmp_path / "manifest_snap_002.json").write_text("{}")

        result = list_snapshot_files(tmp_path)
        assert result.markets_file_present is True
        assert result.order_books_file_present is True
        assert result.manifest_count == 2
        assert len(result.manifest_files) == 2


class TestLoadMarketSnapshotRecords:
    def test_returns_empty_for_missing_file(self, tmp_path):
        result = load_market_snapshot_records(tmp_path)
        assert isinstance(result, SnapshotLoadResult)
        assert result.records == []
        assert result.errors == []
        assert result.lines_read == 0

    def test_loads_valid_records(self, tmp_path):
        records = [
            _make_market_record_dict("market-1"),
            _make_market_record_dict("market-2"),
        ]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)

        result = load_market_snapshot_records(tmp_path)
        assert len(result.records) == 2
        assert result.errors == []
        assert all(isinstance(r, MarketMetadataSnapshotRecord) for r in result.records)
        assert result.records[0].market_id == "market-1"
        assert result.records[1].market_id == "market-2"

    def test_skips_malformed_line_in_non_strict_mode(self, tmp_path):
        path = tmp_path / "market_metadata_snapshots.jsonl"
        with open(path, "w") as fh:
            fh.write(json.dumps(_make_market_record_dict("market-1")) + "\n")
            fh.write("{this is not valid json}\n")
            fh.write(json.dumps(_make_market_record_dict("market-2")) + "\n")

        result = load_market_snapshot_records(tmp_path, strict=False)
        assert len(result.records) == 2
        assert len(result.errors) == 1
        assert result.lines_skipped == 1

    def test_raises_on_malformed_line_in_strict_mode(self, tmp_path):
        path = tmp_path / "market_metadata_snapshots.jsonl"
        with open(path, "w") as fh:
            fh.write("{bad json}\n")

        with pytest.raises(ValueError, match="Malformed record"):
            load_market_snapshot_records(tmp_path, strict=True)

    def test_missing_required_field_in_non_strict(self, tmp_path):
        bad_record = {"snapshot_id": "snap_001"}  # missing many required fields
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [bad_record])
        result = load_market_snapshot_records(tmp_path, strict=False)
        assert len(result.records) == 0
        assert len(result.errors) == 1

    def test_empty_file_returns_zero_records(self, tmp_path):
        (tmp_path / "market_metadata_snapshots.jsonl").write_text("")
        result = load_market_snapshot_records(tmp_path)
        assert result.records == []
        assert result.lines_read == 0


class TestLoadOrderBookSnapshotRecords:
    def test_returns_empty_for_missing_file(self, tmp_path):
        result = load_order_book_snapshot_records(tmp_path)
        assert isinstance(result, SnapshotLoadResult)
        assert result.records == []

    def test_loads_valid_records(self, tmp_path):
        records = [_make_order_book_record_dict("token-1")]
        _write_jsonl(tmp_path / "order_book_snapshots.jsonl", records)

        result = load_order_book_snapshot_records(tmp_path)
        assert len(result.records) == 1
        assert isinstance(result.records[0], OrderBookSnapshotRecord)
        assert result.records[0].token_id == "token-1"

    def test_skips_malformed_line_non_strict(self, tmp_path):
        path = tmp_path / "order_book_snapshots.jsonl"
        with open(path, "w") as fh:
            fh.write("{not json}\n")
            fh.write(json.dumps(_make_order_book_record_dict("token-ok")) + "\n")

        result = load_order_book_snapshot_records(tmp_path, strict=False)
        assert len(result.records) == 1
        assert len(result.errors) == 1

    def test_raises_in_strict_mode(self, tmp_path):
        path = tmp_path / "order_book_snapshots.jsonl"
        path.write_text("{bad}\n")
        with pytest.raises(ValueError):
            load_order_book_snapshot_records(tmp_path, strict=True)


class TestLoadSnapshotManifests:
    def test_returns_empty_for_missing_directory(self, tmp_path):
        result = load_snapshot_manifests(tmp_path / "nonexistent")
        assert result.records == []

    def test_returns_empty_for_no_manifest_files(self, tmp_path):
        result = load_snapshot_manifests(tmp_path)
        assert result.records == []

    def test_loads_valid_manifests(self, tmp_path):
        for snap_id in ("snap_001", "snap_002"):
            path = tmp_path / f"manifest_{snap_id}.json"
            path.write_text(json.dumps(_make_manifest_dict(snap_id)))

        result = load_snapshot_manifests(tmp_path)
        assert len(result.records) == 2
        assert all(isinstance(r, SnapshotManifest) for r in result.records)

    def test_skips_malformed_manifest_non_strict(self, tmp_path):
        (tmp_path / "manifest_bad.json").write_text("{not valid")
        (tmp_path / "manifest_ok.json").write_text(
            json.dumps(_make_manifest_dict("snap_ok"))
        )

        result = load_snapshot_manifests(tmp_path, strict=False)
        assert len(result.records) == 1
        assert len(result.errors) == 1

    def test_raises_on_malformed_manifest_strict(self, tmp_path):
        (tmp_path / "manifest_bad.json").write_text("{not valid")
        with pytest.raises(ValueError):
            load_snapshot_manifests(tmp_path, strict=True)


class TestNoNetworkOrTradingImports:
    def _get_function_names(self, source: str) -> set:
        import ast
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def _get_import_names(self, source: str) -> set:
        import ast
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                for alias in node.names:
                    names.add(alias.name)
        return names

    def test_snapshot_reader_has_no_disallowed_function_names(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_reader.py"
        ).read_text(encoding="utf-8")
        disallowed = {
            "place_order", "create_order", "post_order", "submit_order",
            "cancel_order", "sign_order", "execute_trade",
            "trade", "buy", "sell", "generate_signal", "create_trade_proposal",
        }
        found = self._get_function_names(source) & disallowed
        assert found == set(), f"Disallowed function names found: {found}"

    def test_snapshot_reader_has_no_http_mutation_literals(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_reader.py"
        ).read_text(encoding="utf-8")
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert f'method="{method}"' not in source
            assert f"method='{method}'" not in source

    def test_snapshot_reader_does_not_import_public_client(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_reader.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        assert "PolymarketPublicClient" not in import_names
        assert not any("public_client" in n for n in import_names)

    def test_snapshot_reader_has_no_network_imports(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_reader.py"
        ).read_text(encoding="utf-8")
        import_names = self._get_import_names(source)
        network_imports = {"urllib", "urllib.request", "http.client", "requests", "aiohttp"}
        found = import_names & network_imports
        assert found == set(), f"Network imports found: {found}"

    def test_snapshot_reader_has_no_credential_parameters(self):
        from pathlib import Path
        import ast
        source = (
            Path(__file__).resolve().parents[3]
            / "src" / "data_layer" / "polymarket" / "snapshot_reader.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    assert "private_key" not in arg.arg
                    assert "api_key" not in arg.arg
                    assert "wallet_key" not in arg.arg
                    assert "mnemonic" not in arg.arg
