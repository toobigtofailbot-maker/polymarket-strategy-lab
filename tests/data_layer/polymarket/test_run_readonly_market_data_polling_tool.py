from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

import tools.polymarket.run_readonly_market_data_polling as tool


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOL_PATH = REPO_ROOT / "tools" / "polymarket" / "run_readonly_market_data_polling.py"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_help_works():
    result = run_tool("--help")

    assert result.returncode == 0
    assert "--allow-network" in result.stdout


def test_cli_default_runs_offline_and_exits_zero():
    result = run_tool()

    assert result.returncode == 0
    assert "Readonly polling plan" in result.stdout
    assert '"allow_network": false' in result.stdout
    assert '"attempted_request_count": 0' in result.stdout


def test_cli_validate_only_runs_offline_and_exits_zero():
    result = run_tool("--validate-only")

    assert result.returncode == 0
    assert '"dry_run": true' in result.stdout
    assert '"attempted_request_count": 0' in result.stdout


def test_cli_show_plan_runs_offline_and_exits_zero():
    result = run_tool("--show-plan")

    assert result.returncode == 0
    assert "planned_request_count: 1" in result.stdout
    assert '"attempted_request_count": 0' in result.stdout


def test_json_output_path_validation_allows_only_polling_runs(tmp_path, monkeypatch):
    root = tmp_path / "local_data" / "polymarket" / "polling_runs"
    monkeypatch.setattr(tool, "POLLING_RUN_OUTPUT_ROOT", root)

    allowed = tool._validate_json_out(root / "summary.local.json")
    assert allowed == (root / "summary.local.json").resolve()

    with pytest.raises(SystemExit):
        tool._validate_json_out(tmp_path / "outside.local.json")


def test_main_writes_sanitized_json_summary(tmp_path, monkeypatch):
    root = tmp_path / "local_data" / "polymarket" / "polling_runs"
    monkeypatch.setattr(tool, "POLLING_RUN_OUTPUT_ROOT", root)
    output = root / "summary.local.json"

    exit_code = tool.main(["--json-out", str(output)])

    assert exit_code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["attempted_request_count"] == 0
    assert data["dry_run"] is True
    assert "PRIVATE_KEY" not in output.read_text(encoding="utf-8")


def test_cli_source_contains_no_forbidden_runtime_terms():
    source = TOOL_PATH.read_text(encoding="utf-8")
    forbidden_terms = [
        "py_clob_client_v2",
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
        "buy",
        "sell",
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
    ]
    lowered = source.lower()
    offenders = [term for term in forbidden_terms if term.lower() in lowered]

    assert offenders == []


def test_docs_cover_runner_safety_requirements():
    doc = (REPO_ROOT / "docs" / "polymarket_readonly_polling_runner.md").read_text(
        encoding="utf-8"
    )

    assert "--allow-network" in doc
    assert "WP8-D002 remains OPEN" in doc
    assert "does not add a scheduler" in doc
    assert "does not add strategy signals or trade proposals" in doc
