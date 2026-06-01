"""Tests for tools/advisory/local_advisory_consumer.py."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
HELPER_PATH = REPO_ROOT / "tools" / "advisory" / "local_advisory_consumer.py"
PYTHON = sys.executable

_spec = importlib.util.spec_from_file_location("local_advisory_consumer", HELPER_PATH)
consumer = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(consumer)


def _make_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "project_status.md").write_text(
        "\n".join(
            [
                "- Live trading status: DISABLED",
                "- Credentials status: NOT_USED",
                "- Execution status: NOT_STARTED",
                "- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
                "- Agent runtime status: NOT_STARTED",
                "- Agent execution authority: FORBIDDEN",
                "- Fully autonomous trading agent status: EXCLUDED_FOR_NOW",
                "- Scheduler status: NOT_STARTED",
                "- Bot loop status: NOT_STARTED",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (docs / "repo_truth_index.md").write_text("# Index\n", encoding="utf-8")
    (docs / "local_advisory_handoff_package.md").write_text("# Handoff\n", encoding="utf-8")
    (docs / "advisory_runtime_boundary_consumption_design.md").write_text("# Design\n", encoding="utf-8")
    (docs / "security_and_secrets.md").write_text("# Secrets\n", encoding="utf-8")
    (docs / "live_trading_authorization.md").write_text(
        "LIVE TRADING STATUS: DISABLED\n", encoding="utf-8"
    )
    return tmp_path


def _write_context(root: pathlib.Path, name: str = "sample.local.json", extra=None) -> pathlib.Path:
    out_dir = root / "local_data" / "agent_context_exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "agent-context-export.v1",
        "export_created_at_utc": "2026-05-30T00:00:00Z",
        "export_mode": "local_offline_read_only",
        "producer": {"name": "test", "version": "1"},
        "source_commit": "abc123",
        "repo_truth_summary": {"live_trading": "DISABLED"},
        "included_local_artifacts": [
            {"path": "docs/project_status.md", "type": "repo_truth_doc", "provenance": "tracked"}
        ],
        "data_quality_summary": {"source": "test"},
        "safety_boundaries": {"execution": "FORBIDDEN"},
        "deferred_items": [{"id": "WP39-D002", "status": "OPEN"}],
        "warnings": ["review stale context"],
    }
    if extra:
        payload.update(extra)
    path = out_dir / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_report(root: pathlib.Path, name: str = "report.local.md", text: str | None = None) -> pathlib.Path:
    out_dir = root / "local_data" / "agent_context_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(
        text
        or "# Local Report\n\n- Source commit: abc123\n- Warning: stale context\n- Finding: review docs\n",
        encoding="utf-8",
    )
    return path


def _rel(path: pathlib.Path, root: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def _run_cli(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(HELPER_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )


def test_cli_help_exits_zero():
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "advisory" in result.stdout.lower()


def test_required_input_behavior(tmp_path):
    root = _make_repo(tmp_path)
    result = _run_cli("--repo-root", str(root))
    assert result.returncode == 2
    assert "At least one" in result.stderr


def test_context_export_path_restriction_accepts_allowlist(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root))
    assert result.returncode == 0
    assert "Advisory-only: yes" in result.stdout


@pytest.mark.parametrize(
    "bad_path",
    [
        "docs/project_status.md",
        "../outside.json",
        "local_data/agent_context_reports/report.local.md",
    ],
)
def test_context_export_path_restriction_rejects_bad_paths(tmp_path, bad_path):
    root = _make_repo(tmp_path)
    result = _run_cli("--repo-root", str(root), "--context-export", bad_path)
    assert result.returncode == 2


def test_rejects_absolute_context_export_path(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli("--repo-root", str(root), "--context-export", str(context))
    assert result.returncode == 2
    assert "repo-relative" in result.stderr


def test_analyst_report_path_restriction(tmp_path):
    root = _make_repo(tmp_path)
    report = _write_report(root)
    result = _run_cli("--repo-root", str(root), "--analyst-report", _rel(report, root))
    assert result.returncode == 0
    assert "analyst_report" in result.stdout


def test_repo_root_validation(tmp_path):
    result = _run_cli("--repo-root", str(tmp_path), "--context-export", "local_data/agent_context_exports/x.json")
    assert result.returncode == 2
    assert "repo files" in result.stderr


def test_no_crawling_requires_explicit_files(tmp_path):
    root = _make_repo(tmp_path)
    _write_context(root)
    result = _run_cli("--repo-root", str(root), "--context-export", "local_data/agent_context_exports/")
    assert result.returncode == 2


def test_json_context_export_parsing(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    summary = consumer.build_summary(
        argparse_namespace(
            repo_root=str(root),
            context_export=[_rel(context, root)],
            analyst_report=[],
        )
    )
    parsed = summary["input_file_summaries"][0]
    assert parsed["parse_status"] == "parsed"
    assert parsed["metadata"]["schema_version"] == "agent-context-export.v1"
    assert "included_local_artifacts" in parsed["metadata"]


def test_invalid_json_context_export_exits_two_without_brief(tmp_path):
    root = _make_repo(tmp_path)
    context_dir = root / "local_data" / "agent_context_exports"
    context_dir.mkdir(parents=True, exist_ok=True)
    invalid_context = context_dir / "invalid.local.json"
    invalid_context.write_text('{"schema_version": ', encoding="utf-8")

    result = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(invalid_context, root),
    )

    assert result.returncode == 2
    assert "context export JSON is invalid" in result.stderr
    assert "LOCAL ADVISORY CONSUMER BRIEF" not in result.stdout


def test_analyst_report_parsing(tmp_path):
    root = _make_repo(tmp_path)
    report = _write_report(root)
    summary = consumer.build_summary(
        argparse_namespace(
            repo_root=str(root),
            context_export=[],
            analyst_report=[_rel(report, root)],
        )
    )
    parsed = summary["input_file_summaries"][0]
    assert parsed["headings"] == ["Local Report"]
    assert any("Warning" in line for line in parsed["warnings_or_risk_lines"])


def test_text_output_contains_advisory_labels(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--format",
        "text",
        "--include-review-checklist",
    )
    assert result.returncode == 0
    assert "Advisory-only: yes" in result.stdout
    assert "Human review required: yes" in result.stdout
    assert "Human-review checklist:" in result.stdout


def test_json_output_parseable_and_required_fields(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root), "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    required = [
        "summary_schema_version",
        "mode",
        "advisory_only",
        "repo_truth_reminder",
        "human_review_required",
        "validation_reminder",
        "input_files",
        "input_file_summaries",
        "boundary_status",
        "advisory_brief",
        "research_questions",
        "risk_uncertainty_notes",
        "human_review_checklist",
        "forbidden_output_reminder",
        "sensitive_content_detected",
        "redaction_applied",
        "warnings",
    ]
    for key in required:
        assert key in data
    assert data["advisory_only"] is True
    assert data["human_review_required"] is True


def test_optional_output_restricted_and_written(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    out_rel = "local_data/advisory_outputs/out.local.json"
    result = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--format",
        "json",
        "--output",
        out_rel,
    )
    assert result.returncode == 0
    out_path = root / out_rel
    assert out_path.is_file()
    assert json.loads(out_path.read_text(encoding="utf-8"))["advisory_only"] is True


def test_optional_output_rejects_outside_path(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--output",
        "local_data/agent_context_reports/out.local.json",
    )
    assert result.returncode == 2


def test_default_writes_no_file(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root))
    assert result.returncode == 0
    assert not (root / "local_data" / "advisory_outputs").exists()


def test_sensitive_redaction_in_text_and_json(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root, extra={"warnings": ["API_KEY=secret123456789"]})
    text_result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root))
    json_result = _run_cli(
        "--repo-root", str(root), "--context-export", _rel(context, root), "--format", "json"
    )
    assert text_result.returncode == 0
    assert json_result.returncode == 0
    assert "secret123456789" not in text_result.stdout
    assert "secret123456789" not in json_result.stdout
    assert "[REDACTED]" in json_result.stdout
    assert json.loads(json_result.stdout)["sensitive_content_detected"] is True


def test_fail_on_sensitive_hit_exits_one(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root, extra={"warnings": ["TOKEN=secret123456789"]})
    result = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--fail-on-sensitive-hit",
    )
    assert result.returncode == 1
    assert "secret123456789" not in result.stdout


def test_trading_execution_language_handling(tmp_path):
    root = _make_repo(tmp_path)
    report = _write_report(root, text="# Report\n\n- buy now and place order\n")
    result = _run_cli("--repo-root", str(root), "--analyst-report", _rel(report, root), "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    rendered = json.dumps(data)
    assert "buy now" not in rendered.lower()
    assert "place order" not in rendered.lower()
    assert "Input contained trading-like language; human review required." in data["warnings"]


def test_max_caps(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    low_bytes = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--max-input-bytes",
        "999",
    )
    low_items = _run_cli(
        "--repo-root",
        str(root),
        "--context-export",
        _rel(context, root),
        "--max-items",
        "0",
    )
    assert low_bytes.returncode == 2
    assert low_items.returncode == 2


def test_no_forbidden_imports_or_command_execution():
    source = HELPER_PATH.read_text(encoding="utf-8")
    forbidden_imports = [
        "import subprocess",
        "from subprocess",
        "import requests",
        "import httpx",
        "import aiohttp",
        "import websockets",
        "import socket",
        "import openai",
        "import anthropic",
        "import langchain",
        "import hermes",
        "import py_clob_client",
        "import web3",
        "import ccxt",
        "import fastapi",
        "import streamlit",
        "import plotly",
        "import sqlalchemy",
    ]
    forbidden_calls = ["os.system(", "subprocess.run(", "subprocess.Popen(", "check_output(", "eval(", "exec("]
    for term in forbidden_imports + forbidden_calls:
        assert term not in source


def test_no_project_runtime_imports():
    source = HELPER_PATH.read_text(encoding="utf-8")
    assert "from src." not in source
    assert "import src." not in source


def test_cli_smoke_text_and_json(tmp_path):
    root = _make_repo(tmp_path)
    context = _write_context(root)
    text_result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root), "--format", "text")
    json_result = _run_cli("--repo-root", str(root), "--context-export", _rel(context, root), "--format", "json")
    assert text_result.returncode == 0
    assert "LOCAL ADVISORY CONSUMER BRIEF" in text_result.stdout
    assert json_result.returncode == 0
    assert json.loads(json_result.stdout)["summary_schema_version"] == consumer.SUMMARY_SCHEMA_VERSION


def test_repo_truth_index_numbering_remains_sequential():
    text = (REPO_ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "docs/local_advisory_consumer_prototype.md" in text
    numbers = [
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\.\s+`", text, flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) == len(set(numbers))


def test_wp40_docs_and_repo_truth_updates_present():
    doc = (REPO_ROOT / "docs" / "local_advisory_consumer_prototype.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_PROTOTYPE",
        "NO_NETWORK",
        "NO_COMMAND_EXECUTION",
        "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "local_data/agent_context_exports/",
        "local_data/agent_context_reports/",
        "local_data/advisory_outputs/",
        "no LLM",
        "no trading",
    ]:
        assert phrase in doc

    project_status = (REPO_ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    for phrase in [
        "WP40 - Local Advisory Consumer Prototype",
        "LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_ON_BRANCH",
        "tools/advisory/local_advisory_consumer.py",
        "WP41 - Advisory Prompt/Runbook Package",
    ]:
        assert phrase in project_status

    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    for phrase in [
        "WP38-D002",
        "RESOLVED (WP40 local/offline/read-only prototype)",
        "WP39-D001",
        "WP39-D002",
        "WP40-D001",
        "WP40-D002",
    ]:
        assert phrase in deferred


def argparse_namespace(**overrides):
    base = {
        "context_export": [],
        "analyst_report": [],
        "format": "text",
        "output": None,
        "repo_root": str(REPO_ROOT),
        "max_input_bytes": 200000,
        "max_items": 20,
        "include_review_checklist": False,
        "fail_on_sensitive_hit": False,
    }
    base.update(overrides)
    return type("Args", (), base)()
