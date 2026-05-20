"""Offline tests for the WP16 polling policy CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TOOL = Path("tools/polymarket/inspect_readonly_polling_policy.py")


def test_cli_help_works_offline():
    result = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "network" in result.stdout.lower()


def test_cli_runs_offline_and_exits_zero():
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Polymarket Read-Only Polling Policy Inspector (offline)" in result.stdout
    assert "Validation: PASS" in result.stdout


def test_cli_validate_only_runs_offline_and_exits_zero():
    result = subprocess.run(
        [sys.executable, str(TOOL), "--validate-only"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "PASS"


def test_cli_can_write_only_under_local_polling_policy_output(tmp_path):
    allowed = Path("local_data/polymarket/polling_policy/polling_policy.local.json")
    denied = tmp_path / "polling_policy.local.json"

    ok = subprocess.run(
        [sys.executable, str(TOOL), "--json-out", str(allowed), "--validate-only"],
        check=False,
        capture_output=True,
        text=True,
    )
    bad = subprocess.run(
        [sys.executable, str(TOOL), "--json-out", str(denied), "--validate-only"],
        check=False,
        capture_output=True,
        text=True,
    )

    try:
        assert ok.returncode == 0
        assert allowed.exists()
        assert bad.returncode == 1
        assert "local_data/polymarket/polling_policy" in bad.stderr
    finally:
        if allowed.exists():
            allowed.unlink()


def test_cli_source_has_no_client_imports_network_or_scheduler_terms():
    source = TOOL.read_text(encoding="utf-8")
    forbidden = [
        "PolymarketPublicClient",
        "py_clob_client_v2",
        "urllib.request",
        "import requests",
        "from requests",
        "httpx",
        "aiohttp",
        "websockets",
        "apscheduler",
        "celery",
        "schedule",
        "while True",
        "time.sleep",
        "--allow-network",
    ]

    for term in forbidden:
        assert term not in source
