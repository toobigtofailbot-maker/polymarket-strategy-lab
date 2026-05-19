"""Tests for tools/polymarket/inspect_snapshot_catalog.py (WP11).

All tests are offline. No live network access. CLI tested via main() directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.polymarket.inspect_snapshot_catalog import main


def _make_market_record_dict(
    market_id: str = "market-1",
    snapshot_id: str = "snap_001",
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "captured_at_utc": "2026-01-01T00:00:00+00:00",
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


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


class TestCLIWithEmptyOrMissingDir:
    def test_missing_input_dir_exits_cleanly(self, tmp_path):
        missing = tmp_path / "nonexistent"
        result = main(["--input-dir", str(missing)])
        assert result == 0

    def test_empty_dir_exits_cleanly(self, tmp_path):
        result = main(["--input-dir", str(tmp_path)])
        assert result == 0

    def test_help_exits_cleanly(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestCLIWithData:
    def test_basic_run_with_market_records(self, tmp_path, capsys):
        records = [
            _make_market_record_dict("market-1"),
            _make_market_record_dict("market-2"),
        ]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        result = main(["--input-dir", str(tmp_path)])
        assert result == 0
        output = capsys.readouterr().out
        assert "2" in output  # at least mentions the count

    def test_show_markets_option(self, tmp_path, capsys):
        records = [_make_market_record_dict("market-1")]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        result = main(["--input-dir", str(tmp_path), "--show-markets", "3"])
        assert result == 0

    def test_market_id_option_found(self, tmp_path, capsys):
        records = [_make_market_record_dict("market-abc")]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        result = main(["--input-dir", str(tmp_path), "--market-id", "market-abc"])
        assert result == 0
        output = capsys.readouterr().out
        assert "market-abc" in output

    def test_market_id_option_not_found(self, tmp_path, capsys):
        records = [_make_market_record_dict("market-1")]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        result = main(["--input-dir", str(tmp_path), "--market-id", "nonexistent"])
        assert result == 0
        output = capsys.readouterr().out
        assert "not found" in output

    def test_strict_mode_raises_on_malformed(self, tmp_path):
        path = tmp_path / "market_metadata_snapshots.jsonl"
        path.write_text("{bad json}\n")
        with pytest.raises(ValueError):
            main(["--input-dir", str(tmp_path), "--strict"])


class TestCLISummaryJsonExport:
    def test_summary_json_written_to_local_data_path(self, tmp_path):
        records = [_make_market_record_dict("market-1")]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        output_path = tmp_path / "local_data" / "polymarket" / "catalog" / "summary.json"
        result = main([
            "--input-dir", str(tmp_path),
            "--summary-json", str(output_path),
        ])
        assert result == 0
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "catalog_summary" in data

    def test_summary_json_rejected_outside_local_data(self, tmp_path):
        records = [_make_market_record_dict("market-1")]
        _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", records)
        bad_path = tmp_path / "src" / "summary.json"
        result = main([
            "--input-dir", str(tmp_path),
            "--summary-json", str(bad_path),
        ])
        assert result == 1


class TestCLIDoesNotRequireNetwork:
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

    def _cli_source(self) -> str:
        from pathlib import Path
        return (
            Path(__file__).resolve().parents[3]
            / "tools" / "polymarket" / "inspect_snapshot_catalog.py"
        ).read_text(encoding="utf-8")

    def test_cli_source_does_not_import_public_client(self):
        source = self._cli_source()
        import_names = self._get_import_names(source)
        assert "PolymarketPublicClient" not in import_names
        assert not any("public_client" in n for n in import_names)

    def test_cli_source_has_no_network_imports(self):
        source = self._cli_source()
        import_names = self._get_import_names(source)
        network_imports = {"urllib", "urllib.request", "http.client", "requests", "aiohttp"}
        found = import_names & network_imports
        assert found == set(), f"Network imports found: {found}"

    def test_cli_source_does_not_use_allow_network(self):
        source = self._cli_source()
        assert "allow_network" not in source
        assert "allow-network" not in source

    def test_cli_source_has_no_credential_parameters(self):
        import ast
        source = self._cli_source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    assert "private_key" not in arg.arg
                    assert "api_key" not in arg.arg
                    assert "wallet_key" not in arg.arg
                    assert "mnemonic" not in arg.arg

    def test_cli_source_has_no_http_mutation_literals(self):
        source = self._cli_source()
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert f'method="{method}"' not in source
            assert f"method='{method}'" not in source

    def test_cli_source_has_no_disallowed_function_names(self):
        source = self._cli_source()
        disallowed = {
            "place_order", "create_order", "post_order", "submit_order",
            "cancel_order", "sign_order", "execute_trade",
            "trade", "buy", "sell", "generate_signal", "create_trade_proposal",
        }
        found = self._get_function_names(source) & disallowed
        assert found == set(), f"Disallowed function names found in CLI: {found}"
