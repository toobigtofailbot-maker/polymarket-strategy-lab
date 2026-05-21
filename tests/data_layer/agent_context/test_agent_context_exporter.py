from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.data_layer.agent_context.export_models import EXPORT_MODE, SCHEMA_VERSION
from src.data_layer.agent_context.exporter import (
    DEFAULT_DOC_ALLOWLIST,
    build_agent_context_export,
    validate_agent_context_output_path,
    write_agent_context_export,
)


ROOT = Path(__file__).resolve().parents[3]


REQUIRED_SCHEMA_FIELDS = {
    "schema_version",
    "export_created_at_utc",
    "export_mode",
    "producer",
    "source_commit",
    "repo_truth_summary",
    "included_local_artifacts",
    "data_quality_summary",
    "safety_boundaries",
    "deferred_items",
    "allowed_agent_uses",
    "forbidden_agent_uses",
    "redaction_policy",
    "staleness_policy",
    "human_review_requirements",
}


def test_export_dictionary_contains_wp21_top_level_schema_fields():
    data = build_agent_context_export(source_commit="test-commit")

    assert set(data) == REQUIRED_SCHEMA_FIELDS
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["source_commit"] == "test-commit"
    json.dumps(data)


def test_export_mode_is_local_offline_read_only():
    data = build_agent_context_export(source_commit="test-commit")

    assert data["export_mode"] == EXPORT_MODE
    assert data["export_mode"] == "local_offline_read_only"


def test_safety_boundaries_include_required_statuses():
    boundaries = build_agent_context_export(source_commit="test-commit")["safety_boundaries"]

    assert boundaries["live_trading"] == "DISABLED"
    assert boundaries["credentials"] == "FORBIDDEN_NOT_USED"
    assert boundaries["execution"] == "FORBIDDEN_NOT_STARTED"
    assert boundaries["hermes"] == "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY"
    assert boundaries["agent_execution_authority"] == "FORBIDDEN"
    assert boundaries["fully_autonomous_trading_agent"] == "EXCLUDED_FOR_NOW"


def test_default_exporter_includes_only_allowlisted_tracked_docs():
    data = build_agent_context_export(source_commit="test-commit")
    paths = {artifact["path"] for artifact in data["included_local_artifacts"]}

    assert paths == set(DEFAULT_DOC_ALLOWLIST)


@pytest.mark.parametrize(
    "bad_relative",
    [
        ".env",
        ".env.local",
        "docs/credential_store.md",
        "docs/private-key.txt",
        "docs/wallet-key.json",
        "docs/token-cache.json",
        "docs/account-export.json",
    ],
)
def test_output_and_input_path_safety_blocks_forbidden_names(bad_relative):
    from src.data_layer.agent_context import exporter

    assert exporter._is_forbidden_path(bad_relative)


def test_writer_accepts_agent_context_export_output_path(tmp_path):
    data = build_agent_context_export(repo_root=ROOT, source_commit="test-commit")
    out = tmp_path / "repo" / "local_data" / "agent_context_exports" / "context.local.json"
    repo_root = tmp_path / "repo"

    written = write_agent_context_export(data, out, repo_root=repo_root)

    assert written == out.resolve()
    assert json.loads(written.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize(
    "bad_path",
    [
        "context.local.json",
        "docs/context.local.json",
        "local_data/context.local.json",
        "local_data/polymarket/reports/context.local.json",
        "local_data/agent_context_exports/../context.local.json",
    ],
)
def test_writer_rejects_non_allowed_output_paths(tmp_path, bad_path):
    repo_root = tmp_path / "repo"

    with pytest.raises(ValueError):
        validate_agent_context_output_path(Path(bad_path), repo_root=repo_root)


def test_writer_rejects_absolute_path_outside_allowed_dir(tmp_path):
    with pytest.raises(ValueError):
        validate_agent_context_output_path(tmp_path / "outside.local.json", repo_root=ROOT)


def test_deferred_items_include_required_open_agent_context_items():
    data = build_agent_context_export(source_commit="test-commit")
    item_ids = {item["id"] for item in data["deferred_items"]}

    for expected in {"WP21-D001", "WP21-D002", "WP20-D001", "WP20-D003"}:
        assert expected in item_ids


def test_optional_local_report_metadata_is_metadata_only(tmp_path):
    repo_root = tmp_path / "repo"
    report_dir = repo_root / "local_data" / "polymarket" / "reports"
    report_dir.mkdir(parents=True)
    report = report_dir / "sample.local.report.json"
    report.write_text('{"generated_at_utc": "2026-05-21T00:00:00Z", "payload": "x"}', encoding="utf-8")

    data = build_agent_context_export(
        repo_root=repo_root,
        include_local_report_metadata=True,
        source_commit="test-commit",
    )
    reports = [
        artifact
        for artifact in data["included_local_artifacts"]
        if artifact["path"] == "local_data/polymarket/reports/sample.local.report.json"
    ]

    assert len(reports) == 1
    assert reports[0]["included_content"] is False
    assert reports[0]["sanitized_excerpt"] is None
    assert reports[0]["sha256"]
    assert reports[0]["generated_at"] == "2026-05-21T00:00:00Z"


def test_local_report_metadata_does_not_self_ingest_agent_context_exports(tmp_path):
    repo_root = tmp_path / "repo"
    export_dir = repo_root / "local_data" / "agent_context_exports"
    export_dir.mkdir(parents=True)
    (export_dir / "old.local.json").write_text("{}", encoding="utf-8")

    data = build_agent_context_export(
        repo_root=repo_root,
        include_local_report_metadata=True,
        source_commit="test-commit",
    )

    assert all(
        not artifact["path"].startswith("local_data/agent_context_exports/")
        for artifact in data["included_local_artifacts"]
    )


def test_secret_like_excerpt_values_are_redacted(tmp_path):
    from src.data_layer.agent_context import exporter

    text = "sample credential = abcdefgh123456789"

    assert exporter._redact_secret_like_text(text) == "sample [REDACTED_SECRET_LIKE_VALUE]"


class TestSourceSafety:
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

    def test_exporter_sources_have_no_forbidden_runtime_imports(self):
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
            "src/data_layer/agent_context/export_models.py",
            "src/data_layer/agent_context/exporter.py",
            "tools/polymarket/export_agent_context.py",
        ):
            assert self._import_names(self._source(relative)) & forbidden_imports == set()

    def test_exporter_sources_have_no_trading_runtime_function_names(self):
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
            "backtest",
            "fill_order",
            "simulate_fill",
        }
        for relative in (
            "src/data_layer/agent_context/export_models.py",
            "src/data_layer/agent_context/exporter.py",
            "tools/polymarket/export_agent_context.py",
        ):
            assert self._function_names(self._source(relative)) & disallowed == set()

    def test_exporter_sources_have_no_loop_or_delay_runtime_markers(self):
        for relative in (
            "src/data_layer/agent_context/export_models.py",
            "src/data_layer/agent_context/exporter.py",
            "tools/polymarket/export_agent_context.py",
        ):
            source = self._source(relative)
            assert "while True" not in source
            assert "time.sleep" not in source
            assert "--allow-network" not in source
            assert "allow_network" not in source
