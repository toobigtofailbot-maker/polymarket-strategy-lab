from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.data_layer.agent_context.report_generator import (
    AGENT_CONTEXT_REPORT_OUTPUT_DIR,
    generate_agent_context_report,
    validate_agent_context_input_path,
    validate_agent_context_report_output_path,
    write_json_report,
    write_markdown_report,
)
from src.data_layer.agent_context.report_models import REPORT_MODE, REPORT_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[3]


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
            "scheduler": "NOT_STARTED",
            "bot_loop": "NOT_STARTED",
            runtime_key: "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
            "agent_execution_authority": "FORBIDDEN",
            "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
        },
        "included_local_artifacts": [
            {
                "path": "docs/project_status.md",
                "artifact_type": "repo_truth_doc",
                "provenance_classification": "tracked_repo_truth_doc",
            },
            {
                "path": "docs/deferred_items_log.md",
                "artifact_type": "repo_truth_doc",
                "provenance_classification": "tracked_repo_truth_doc",
            },
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
        "deferred_items": [
            {"id": "WP21-D002", "status": "OPEN", "title": "Agent context report generator"},
            {"id": "WP20-D001", "status": "OPEN", "title": "Manual runtime assistant setup"},
        ],
        "allowed_agent_uses": ["observe_local_repo_approved_context"],
        "forbidden_agent_uses": ["order_placement", "trade_execution"],
        "redaction_policy": {"raw_secrets_allowed": False, "account_data_allowed": False},
        "staleness_policy": {
            "repo_truth_precedence": "current_repo_truth_overrides_exported_context",
            "stale_export_rule": "exports_have_no_authority_after_repo_truth_changes",
        },
        "human_review_requirements": {
            "agent_outputs": "advisory_untrusted_until_reviewed",
            "repo_changes": "normal_codex_work_package_and_human_review_required",
        },
    }


def _write_context(repo_root: Path, name: str = "context.local.json") -> Path:
    path = repo_root / "local_data" / "agent_context_exports" / name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_sample_context()), encoding="utf-8")
    return path


def test_report_generator_returns_required_report_fields_and_markdown_sections(tmp_path):
    context_path = _write_context(tmp_path)

    data, markdown = generate_agent_context_report(
        context_path,
        repo_root=tmp_path,
        created_at_utc="2026-05-21T01:02:03Z",
    )

    assert set(data) == {
        "report_schema_version",
        "report_created_at_utc",
        "report_mode",
        "producer",
        "source_context_path",
        "source_context_schema_version",
        "source_commit",
        "export_mode",
        "summary",
        "safety_boundary_summary",
        "included_artifact_summary",
        "deferred_item_summary",
        "staleness_summary",
        "human_review_summary",
        "forbidden_use_caveats",
    }
    assert data["report_schema_version"] == REPORT_SCHEMA_VERSION
    assert data["report_mode"] == REPORT_MODE
    assert data["source_context_schema_version"] == "agent-context-export.v1"
    assert data["source_commit"] == "abc123"
    assert data["included_artifact_summary"]["included_artifact_count"] == 2
    assert data["deferred_item_summary"]["deferred_item_count"] == 2
    for section in (
        "Source Context Metadata",
        "Safety Boundary Summary",
        "Deferred Item Summary",
        "Staleness And Human Review Notes",
        "Forbidden Use Caveats",
        "Next-Step Boundary Statement",
    ):
        assert section in markdown


def test_report_mode_is_local_offline_read_only(tmp_path):
    data, _ = generate_agent_context_report(_write_context(tmp_path), repo_root=tmp_path)

    assert data["report_mode"] == "local_offline_read_only_report"


def test_safety_boundary_summary_includes_required_statuses(tmp_path):
    data, _ = generate_agent_context_report(_write_context(tmp_path), repo_root=tmp_path)
    safety = data["safety_boundary_summary"]

    assert safety["live_trading"] == "DISABLED"
    assert safety["credentials"] == "FORBIDDEN_NOT_USED"
    assert safety["execution"] == "FORBIDDEN_NOT_STARTED"
    assert safety["runtime_assistant"] == "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY"
    assert safety["fully_autonomous_trading_agent"] == "EXCLUDED_FOR_NOW"
    assert any("No Her" "mes runtime" in caveat for caveat in data["forbidden_use_caveats"])


def test_input_path_validation_accepts_agent_context_export_path(tmp_path):
    context_path = _write_context(tmp_path)

    resolved = validate_agent_context_input_path(
        Path("local_data/agent_context_exports/context.local.json"),
        repo_root=tmp_path,
    )

    assert resolved == context_path.resolve()


@pytest.mark.parametrize(
    "bad_path",
    [
        "context.local.json",
        "docs/context.local.json",
        "local_data/context.local.json",
        "local_data/agent_context_reports/context.local.json",
        "local_data/agent_context_exports/../context.local.json",
        ".env",
        "local_data/agent_context_exports/.env",
        "local_data/agent_context_exports/credential.local.json",
        "local_data/agent_context_exports/secret.local.json",
        "local_data/agent_context_exports/private.local.json",
        "local_data/agent_context_exports/wallet.local.json",
        "local_data/agent_context_exports/token.local.json",
        "local_data/agent_context_exports/account.local.json",
    ],
)
def test_input_path_validation_rejects_forbidden_paths(tmp_path, bad_path):
    with pytest.raises(ValueError):
        validate_agent_context_input_path(Path(bad_path), repo_root=tmp_path)


def test_input_path_validation_rejects_absolute_path_outside_allowed_dir(tmp_path):
    with pytest.raises(ValueError):
        validate_agent_context_input_path(tmp_path / "outside.local.json", repo_root=ROOT)


@pytest.mark.parametrize(
    "good_path",
    [
        "local_data/agent_context_reports/report.local.md",
        "local_data/agent_context_reports/report.local.json",
    ],
)
def test_output_path_validation_accepts_agent_context_report_paths(tmp_path, good_path):
    resolved = validate_agent_context_report_output_path(Path(good_path), repo_root=tmp_path)

    assert resolved == (tmp_path / good_path).resolve()


@pytest.mark.parametrize(
    "bad_path",
    [
        "report.local.md",
        "docs/report.local.md",
        "local_data/report.local.md",
        "local_data/agent_context_exports/report.local.md",
        "local_data/agent_context_reports/../report.local.md",
        "local_data/polymarket/reports/report.local.md",
    ],
)
def test_output_path_validation_rejects_non_allowed_paths(tmp_path, bad_path):
    with pytest.raises(ValueError):
        validate_agent_context_report_output_path(Path(bad_path), repo_root=tmp_path)


def test_write_markdown_and_json_reports_under_allowed_output_dir(tmp_path):
    data, markdown = generate_agent_context_report(_write_context(tmp_path), repo_root=tmp_path)
    md_out = tmp_path / AGENT_CONTEXT_REPORT_OUTPUT_DIR / "report.local.md"
    json_out = tmp_path / AGENT_CONTEXT_REPORT_OUTPUT_DIR / "report.local.json"

    written_md = write_markdown_report(markdown, md_out, repo_root=tmp_path)
    written_json = write_json_report(data, json_out, repo_root=tmp_path)

    assert "Source Context Metadata" in written_md.read_text(encoding="utf-8")
    parsed = json.loads(written_json.read_text(encoding="utf-8"))
    assert parsed["report_schema_version"] == REPORT_SCHEMA_VERSION
    assert "included_local_artifacts" not in parsed
    assert "forbidden_agent_uses" not in parsed


def test_missing_required_context_fields_are_rejected(tmp_path):
    context_path = _write_context(tmp_path)
    data = _sample_context()
    data.pop("human_review_requirements")
    context_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required fields"):
        generate_agent_context_report(context_path, repo_root=tmp_path)


class TestReportSourceSafety:
    def _source(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def _import_names(self, source: str) -> set[str]:
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

    def _function_names(self, source: str) -> set[str]:
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_report_sources_have_no_forbidden_runtime_imports(self):
        forbidden_imports = {
            "py_clob_client_v2",
            "PolymarketPublicClient",
            "requests",
            "httpx",
            "aiohttp",
            "websockets",
            "openai",
            "anthropic",
            "apscheduler",
            "celery",
        }
        for relative in (
            "src/data_layer/agent_context/report_models.py",
            "src/data_layer/agent_context/report_generator.py",
            "tools/polymarket/generate_agent_context_report.py",
        ):
            assert self._import_names(self._source(relative)) & forbidden_imports == set()

    def test_report_sources_have_no_trading_runtime_function_names(self):
        disallowed = {
            "create_and_post_order",
            "create_order",
            "post_order",
            "submit_order",
            "cancel_order",
            "sign_order",
            "execute_trade",
            "generate_signal",
            "create_trade_proposal",
            "back" "test",
            "fill_order",
            "simulate_fill",
        }
        for relative in (
            "src/data_layer/agent_context/report_models.py",
            "src/data_layer/agent_context/report_generator.py",
            "tools/polymarket/generate_agent_context_report.py",
        ):
            assert self._function_names(self._source(relative)) & disallowed == set()

    def test_report_sources_have_no_forbidden_runtime_markers(self):
        disallowed_markers = (
            "py_clob_client_v2",
            "PolymarketPublicClient",
            "PRIVATE_KEY",
            "CLOB_API_KEY",
            "CLOB_SECRET",
            "CLOB_PASS_PHRASE",
            "mne" "monic",
            "requests",
            "httpx",
            "aiohttp",
            "websockets",
            "openai",
            "anthropic",
            "her" "mes",
            "create_and_post_order",
            "create_order",
            "post_order",
            "submit_order",
            "cancel_order",
            "sign_order",
            "execute_trade",
            "generate_signal",
            "create_trade_proposal",
            "back" "test",
            "fill_order",
            "simulate_fill",
            "apscheduler",
            "celery",
            "while True",
            "time.sleep",
        )
        for relative in (
            "src/data_layer/agent_context/report_models.py",
            "src/data_layer/agent_context/report_generator.py",
            "tools/polymarket/generate_agent_context_report.py",
        ):
            source = self._source(relative).lower()
            for marker in disallowed_markers:
                assert marker.lower() not in source
