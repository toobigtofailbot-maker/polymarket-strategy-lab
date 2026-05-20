"""Tests for tools/polymarket/generate_snapshot_quality_report.py.

All tests are offline. The CLI is exercised through main().
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.polymarket.generate_snapshot_quality_report import main
from tests.data_layer.polymarket.test_snapshot_quality import _manifest, _market_record


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
    assert not list(tmp_path.glob("*.md"))
    assert not list(tmp_path.glob("*.report.json"))


def test_console_summary_includes_guarded_capture_counts(tmp_path, capsys):
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [_market_record().to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())

    result = main(["--input-dir", str(tmp_path)])
    out = capsys.readouterr().out

    assert result == 0
    assert "Guard-enforced manifests:" in out
    assert "Unguarded network manifests:" in out
    assert "Guard provenance unknown:" in out
    assert "Local WP16 policy count:" in out
    assert "Safety: offline quality/reporting only; no network, credentials, orders, or automation." in out


def test_explicit_outputs_write_under_local_data(tmp_path):
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [_market_record().to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())
    markdown_out = tmp_path / "local_data" / "polymarket" / "reports" / "quality.local.md"
    json_out = tmp_path / "local_data" / "polymarket" / "reports" / "quality.local.json"

    result = main([
        "--input-dir",
        str(tmp_path),
        "--markdown-out",
        str(markdown_out),
        "--json-out",
        str(json_out),
    ])

    assert result == 0
    assert markdown_out.exists()
    assert json_out.exists()
    assert json.loads(json_out.read_text(encoding="utf-8"))["gate_result"]["status"] == "PASS"


def test_output_outside_local_data_fails(tmp_path):
    result = main(["--input-dir", str(tmp_path), "--markdown-out", str(tmp_path / "bad.md")])

    assert result == 1


def test_strict_mode_returns_one_on_malformed_input(tmp_path):
    (tmp_path / "market_metadata_snapshots.jsonl").write_text("{bad json}\n", encoding="utf-8")

    assert main(["--input-dir", str(tmp_path), "--strict"]) == 1


def test_fail_on_error_returns_one(tmp_path):
    record = _market_record()
    record.question = ""
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [record.to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())

    assert main(["--input-dir", str(tmp_path), "--fail-on-error"]) == 1


def test_fail_on_warning_returns_one(tmp_path):
    record = _market_record(token_ids=["token-a", "token-b"], outcome_labels=["Yes"])
    _write_jsonl(tmp_path / "market_metadata_snapshots.jsonl", [record.to_dict()])
    _write_manifest(tmp_path / "manifest_snap_001.json", _manifest())

    assert main(["--input-dir", str(tmp_path), "--fail-on-warning"]) == 1


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

    def test_cli_source_does_not_import_network_or_public_client(self):
        source = self._source("tools/polymarket/generate_snapshot_quality_report.py")
        imports = self._import_names(source)

        assert "PolymarketPublicClient" not in imports
        assert not any("public_client" in name for name in imports)
        assert not (imports & {"urllib", "urllib.request", "http.client", "requests", "aiohttp"})

    def test_quality_and_report_sources_do_not_import_network_or_public_client(self):
        for relative in (
            "src/data_layer/polymarket/snapshot_quality.py",
            "src/data_layer/polymarket/local_reports.py",
        ):
            imports = self._import_names(self._source(relative))
            assert "PolymarketPublicClient" not in imports
            assert not any("public_client" in name for name in imports)
            assert not (imports & {"urllib", "urllib.request", "http.client", "requests", "aiohttp"})

    def test_cli_source_has_no_allow_network_or_credential_loading(self):
        source = self._source("tools/polymarket/generate_snapshot_quality_report.py")

        assert "allow-network" not in source
        assert "allow_network" not in source
        assert ".env" not in source
        assert "dotenv" not in source

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
            "tools/polymarket/generate_snapshot_quality_report.py",
            "src/data_layer/polymarket/snapshot_quality.py",
            "src/data_layer/polymarket/local_reports.py",
        ):
            found = self._function_names(self._source(relative)) & disallowed
            assert found == set(), f"Disallowed function names in {relative}: {found}"

    def test_quality_report_sources_have_no_forbidden_runtime_terms(self):
        forbidden_terms = {
            "py_clob_client_v2",
            "PolymarketPublicClient",
            "PRIVATE_KEY",
            "CLOB_API_KEY",
            "CLOB_SECRET",
            "CLOB_PASS_PHRASE",
            "mnemonic",
            "create_and_post_order",
            "create_order",
            "post_order",
            "submit_order",
            "cancel_order",
            "sign_order",
            "execute_trade",
            "generate_signal",
            "create_trade_proposal",
            "backtest",
            "fill_order",
            "simulate_fill",
            "apscheduler",
            "celery",
            "while True",
            "time.sleep",
            "requests",
            "httpx",
            "aiohttp",
            "websockets",
        }
        for relative in (
            "tools/polymarket/generate_snapshot_quality_report.py",
            "src/data_layer/polymarket/snapshot_quality.py",
            "src/data_layer/polymarket/local_reports.py",
        ):
            source = self._source(relative)
            found = sorted(term for term in forbidden_terms if term in source)
            assert found == [], f"Forbidden terms in {relative}: {found}"

    def test_sources_have_no_http_mutation_method_literals(self):
        for relative in (
            "tools/polymarket/generate_snapshot_quality_report.py",
            "src/data_layer/polymarket/snapshot_quality.py",
            "src/data_layer/polymarket/local_reports.py",
        ):
            source = self._source(relative)
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                assert f'method="{method}"' not in source
                assert f"method='{method}'" not in source
