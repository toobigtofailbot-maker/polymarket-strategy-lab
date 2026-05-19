"""Tests for tools/polymarket/export_snapshot_catalog.py."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.polymarket.export_snapshot_catalog import main
from tests.data_layer.polymarket.test_snapshot_quality import (
    _manifest,
    _market_record,
    _order_book_record,
)


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


def _write_manifest(path: Path, manifest) -> None:
    path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")


def test_help_exits_cleanly():
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_missing_input_dir_exits_cleanly(tmp_path, capsys):
    result = main(["--input-dir", str(tmp_path / "missing")])

    assert result == 0
    assert "does not exist" in capsys.readouterr().out


def test_empty_input_dir_exits_cleanly(tmp_path):
    assert main(["--input-dir", str(tmp_path)]) == 0


def test_default_run_writes_no_files(tmp_path):
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [_market_record().to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())

    result = main(["--input-dir", str(tmp_path)])

    assert result == 0
    assert not list(tmp_path.glob("*.csv"))
    assert not (tmp_path / "local_data").exists()


def test_explicit_local_data_exports_are_accepted(tmp_path):
    market = _market_record()
    book = _order_book_record("token-market-1-yes")
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [market.to_dict(), market.to_dict()])
    _write_jsonl(tmp_path / "order_book_snapshots.jsonl", [book.to_dict(), book.to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())
    json_out = tmp_path / "local_data" / "polymarket" / "exports" / "catalog.local.json"
    csv_out = tmp_path / "local_data" / "polymarket" / "exports" / "catalog.local.csv"

    result = main([
        "--input-dir",
        str(tmp_path),
        "--deduplicate",
        "--json-out",
        str(json_out),
        "--csv-out",
        str(csv_out),
    ])

    assert result == 0
    assert json_out.exists()
    assert csv_out.exists()
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["deduplication_summary"]["markets"]["exact_duplicate_count"] == 1
    assert data["unique_market_count"] == 1
    assert "market_id" in csv_out.read_text(encoding="utf-8")


def test_output_outside_local_data_fails(tmp_path):
    result = main(["--input-dir", str(tmp_path), "--json-out", str(tmp_path / "bad.json")])

    assert result == 1


def test_strict_mode_returns_one_on_malformed_input(tmp_path):
    (tmp_path / "market_metadata_snapshots.jsonl").write_text("{bad json}\n", encoding="utf-8")

    assert main(["--input-dir", str(tmp_path), "--strict"]) == 1


class TestSourceSafety:
    def _source(self, relative: str) -> str:
        return (Path(__file__).resolve().parents[3] / relative).read_text(encoding="utf-8")

    def _import_names(self, source: str) -> set:
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

    def _function_names(self, source: str) -> set:
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_sources_do_not_import_network_or_public_client(self):
        for relative in (
            "tools/polymarket/export_snapshot_catalog.py",
            "src/data_layer/polymarket/snapshot_deduplication.py",
            "src/data_layer/polymarket/catalog_exports.py",
        ):
            imports = self._import_names(self._source(relative))
            assert "PolymarketPublicClient" not in imports
            assert not any("public_client" in name for name in imports)
            assert not (imports & {"urllib", "urllib.request", "http.client", "requests", "aiohttp"})

    def test_cli_source_has_no_network_flag_or_credential_loading(self):
        source = self._source("tools/polymarket/export_snapshot_catalog.py")

        assert "allow-network" not in source
        assert "allow_network" not in source
        assert ".env" not in source
        assert "dotenv" not in source
        assert "API_KEY" not in source

    def test_sources_have_no_disallowed_function_names(self):
        disallowed = {
            "place_order",
            "create_order",
            "post_order",
            "submit_order",
            "cancel_order",
            "sign_order",
            "execute_trade",
            "trade",
            "buy",
            "sell",
            "generate_signal",
            "create_trade_proposal",
            "backtest",
            "fill_order",
            "simulate_fill",
        }
        for relative in (
            "tools/polymarket/export_snapshot_catalog.py",
            "src/data_layer/polymarket/snapshot_deduplication.py",
            "src/data_layer/polymarket/catalog_exports.py",
        ):
            found = self._function_names(self._source(relative)) & disallowed
            assert found == set(), f"Disallowed function names in {relative}: {found}"

    def test_sources_have_no_http_mutation_method_literals(self):
        for relative in (
            "tools/polymarket/export_snapshot_catalog.py",
            "src/data_layer/polymarket/snapshot_deduplication.py",
            "src/data_layer/polymarket/catalog_exports.py",
        ):
            source = self._source(relative)
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                assert f'method="{method}"' not in source
                assert f"method='{method}'" not in source


def test_docs_include_required_safety_statements():
    source = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "polymarket_snapshot_deduplication_exports.md"
    ).read_text(encoding="utf-8")

    required = [
        "offline local data hygiene/export infrastructure only",
        "does not call Polymarket APIs",
        "does not create strategy signals",
        "does not create trade proposals",
        "does not backtest",
        "does not simulate fills",
        "No Database Support",
        "local_data/",
    ]
    for text in required:
        assert text in source
