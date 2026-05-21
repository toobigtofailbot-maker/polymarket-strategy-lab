from __future__ import annotations

import json
from pathlib import Path

from tools.polymarket.generate_agent_context_report import main


def _sample_context() -> dict:
    runtime_key = "her" "mes"
    return {
        "schema_version": "agent-context-export.v1",
        "export_created_at_utc": "2026-05-21T00:00:00Z",
        "export_mode": "local_offline_read_only",
        "producer": {"name": "test-exporter", "version": "test"},
        "source_commit": "abc123",
        "repo_truth_summary": {
            "live_trading": "DISABLED",
            "credentials": "NOT_USED",
            "execution": "NOT_STARTED",
            runtime_key: "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
            "agent_execution_authority": "FORBIDDEN",
            "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
        },
        "included_local_artifacts": [
            {
                "path": "docs/project_status.md",
                "artifact_type": "repo_truth_doc",
                "provenance_classification": "tracked_repo_truth_doc",
            }
        ],
        "data_quality_summary": {
            "source": "repo_truth_docs_and_optional_allowlisted_local_report_metadata",
            "raw_large_payloads_included": False,
            "credentials_included": False,
            "private_endpoint_data_included": False,
        },
        "safety_boundaries": {
            "live_trading": "DISABLED",
            "credentials": "FORBIDDEN_NOT_USED",
            "execution": "FORBIDDEN_NOT_STARTED",
            "scheduler": "NOT_STARTED",
            "bot_loop": "NOT_STARTED",
            runtime_key: "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
            "agent_execution_authority": "FORBIDDEN",
            "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
        },
        "deferred_items": [{"id": "WP21-D002", "status": "OPEN"}],
        "allowed_agent_uses": ["observe_local_repo_approved_context"],
        "forbidden_agent_uses": ["order_placement"],
        "redaction_policy": {"raw_secrets_allowed": False},
        "staleness_policy": {
            "repo_truth_precedence": "current_repo_truth_overrides_exported_context",
        },
        "human_review_requirements": {
            "agent_outputs": "advisory_untrusted_until_reviewed",
        },
    }


def _write_context(repo_root: Path) -> Path:
    path = repo_root / "local_data" / "agent_context_exports" / "wp25_context.local.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_sample_context()), encoding="utf-8")
    return path


def test_cli_help_exits_zero(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "--context" in capsys.readouterr().out


def test_cli_with_valid_context_exits_zero_and_writes_no_file_by_default(tmp_path, capsys):
    context_path = _write_context(tmp_path)

    result = main(["--context", str(context_path)], repo_root=tmp_path)

    out = capsys.readouterr().out
    assert result == 0
    assert "report schema version: agent-context-report.v1" in out
    assert "report mode: local_offline_read_only_report" in out
    assert "source commit: abc123" in out
    assert "included artifact count: 1" in out
    assert "deferred item count: 1" in out
    assert "output written: no" in out
    assert "no network, no credentials, no orders" in out
    assert not (tmp_path / "local_data" / "agent_context_reports").exists()


def test_cli_with_markdown_out_writes_markdown_under_agent_context_reports(tmp_path):
    context_path = _write_context(tmp_path)
    out = tmp_path / "local_data" / "agent_context_reports" / "wp25_report.local.md"

    result = main(["--context", str(context_path), "--markdown-out", str(out)], repo_root=tmp_path)

    assert result == 0
    text = out.read_text(encoding="utf-8")
    assert "Source Context Metadata" in text
    assert "Safety Boundary Summary" in text
    assert "Deferred Item Summary" in text
    assert "Forbidden Use Caveats" in text


def test_cli_with_json_out_writes_parseable_json_under_agent_context_reports(tmp_path):
    context_path = _write_context(tmp_path)
    out = tmp_path / "local_data" / "agent_context_reports" / "wp25_report.local.json"

    result = main(["--context", str(context_path), "--json-out", str(out)], repo_root=tmp_path)

    assert result == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["report_schema_version"] == "agent-context-report.v1"
    assert data["report_mode"] == "local_offline_read_only_report"
    assert data["source_commit"] == "abc123"
    assert "included_local_artifacts" not in data
    assert "forbidden_agent_uses" not in data


def test_cli_rejects_context_outside_allowed_dir(tmp_path, capsys):
    bad_context = tmp_path / "context.local.json"
    bad_context.write_text(json.dumps(_sample_context()), encoding="utf-8")

    result = main(["--context", str(bad_context)], repo_root=tmp_path)

    assert result == 1
    assert "local_data/agent_context_exports" in capsys.readouterr().err


def test_cli_rejects_output_outside_allowed_dir(tmp_path, capsys):
    context_path = _write_context(tmp_path)

    result = main(
        ["--context", str(context_path), "--markdown-out", str(tmp_path / "report.local.md")],
        repo_root=tmp_path,
    )

    assert result == 1
    assert "local_data/agent_context_reports" in capsys.readouterr().err


def test_cli_does_not_accept_runtime_or_private_flags(tmp_path, capsys):
    context_path = _write_context(tmp_path)

    for flag in (
        "--allow-network",
        "--credential",
        "--account",
        "--private-endpoint",
        "--runtime-assistant",
        "--execute",
        "--trade",
    ):
        try:
            main(["--context", str(context_path), flag], repo_root=tmp_path)
        except SystemExit as exc:
            assert exc.code != 0
        assert flag in capsys.readouterr().err
