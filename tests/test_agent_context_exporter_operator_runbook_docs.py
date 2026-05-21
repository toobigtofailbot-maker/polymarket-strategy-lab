from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "agent_context_exporter_operator_runbook.md"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_operator_runbook_exists():
    assert RUNBOOK.is_file()


def test_runbook_contains_required_status_phrases():
    text = _runbook()

    for phrase in (
        "LOCAL_OPERATOR_RUNBOOK",
        "LOCAL_OFFLINE_READ_ONLY_EXPORTER",
        "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "NOT_STARTED",
        "FORBIDDEN",
        "DISABLED",
        "NOT_USED",
    ):
        assert phrase in text


def test_runbook_contains_required_commands():
    text = _runbook()

    for phrase in (
        "python tools/polymarket/export_agent_context.py",
        "python tools/polymarket/export_agent_context.py --help",
        "--out local_data/agent_context_exports/",
        "--include-local-report-metadata",
        "--include-excerpts",
        "--max-excerpt-chars",
    ):
        assert phrase in text


def test_runbook_documents_required_output_validation_fields():
    text = _runbook()

    for field in (
        "schema_version",
        "export_mode",
        "source_commit",
        "included_local_artifacts",
        "safety_boundaries",
        "deferred_items",
        "redaction_policy",
        "staleness_policy",
        "human_review_requirements",
    ):
        assert f"`{field}`" in text


def test_runbook_documents_git_hygiene():
    text = _runbook()

    assert "git status --short" in text
    assert "Generated output must not be committed" in text
    assert "local_data/agent_context_exports/" in text


def test_runbook_documents_non_goals_and_forbidden_uses():
    text = _runbook()

    for phrase in (
        "Hermes setup",
        "agent runtime",
        "report generator",
        "signal generator",
        "trade proposal",
        "backtest",
        "paper trading",
        "live trading",
        "scheduler",
        "bot loop",
        "account, credential, or private endpoint access",
    ):
        assert phrase in text


def test_runbook_documents_stop_conditions():
    text = _runbook()

    for phrase in (
        "credentials, secrets, or account data are suspected",
        "output path is outside the allowlisted",
        "network, account, Hermes, or runtime need arises",
        "intention changes from context export to report generation, strategy suggestion, or execution",
        "tests or guards fail",
    ):
        assert phrase in text


def test_repo_truth_index_indexes_runbook():
    index = _read("docs/repo_truth_index.md")

    assert "docs/agent_context_exporter_operator_runbook.md" in index


def test_agent_context_exporter_doc_references_runbook():
    exporter_doc = _read("docs/agent_context_exporter.md")

    assert "docs/agent_context_exporter_operator_runbook.md" in exporter_doc


def test_no_new_forbidden_runtime_paths_are_introduced():
    forbidden_paths = (
        "src/agents",
        "src/agent_layer",
        "tools/agents",
        "tools/hermes",
        "agent_reports",
    )

    for relative in forbidden_paths:
        assert not (ROOT / relative).exists()


def test_dependency_files_do_not_add_agent_runtime_dependencies():
    dependency_files = (
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "poetry.lock",
        "uv.lock",
    )
    forbidden_dependency_markers = (
        "hermes",
        "openai",
        "anthropic",
        "langchain",
        "autogen",
        "crewai",
        "py-clob-client-v2",
        "py_clob_client_v2",
    )

    for relative in dependency_files:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for marker in forbidden_dependency_markers:
            assert marker not in text
