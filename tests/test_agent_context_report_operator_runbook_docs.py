from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "agent_context_report_operator_runbook.md"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _normalized_runbook() -> str:
    return _runbook().lower()


def test_report_operator_runbook_exists():
    assert RUNBOOK.is_file()


def test_runbook_contains_required_status_phrases():
    text = _runbook()

    for phrase in (
        "LOCAL_ANALYST_REPORT_OPERATOR_RUNBOOK",
        "LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR",
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
        "python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp26_context.local.json",
        "python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp26_context.local.json",
        "python tools/polymarket/generate_agent_context_report.py --help",
        "--markdown-out local_data/agent_context_reports/wp26_report.local.md",
        "--json-out local_data/agent_context_reports/wp26_report.local.json",
    ):
        assert phrase in text


def test_runbook_documents_expected_default_console_summary():
    text = _normalized_runbook()

    for phrase in (
        "report schema version",
        "report mode",
        "source context path",
        "source commit",
        "included artifact count",
        "deferred item count",
        "output written",
        "safety line",
    ):
        assert phrase in text


def test_runbook_documents_required_markdown_headings():
    text = _runbook()

    for heading in (
        "Source Context Metadata",
        "Repo-Truth Status Snapshot",
        "Safety Boundary Summary",
        "Included Local Artifact Summary",
        "Deferred Item Summary",
        "Data Quality And Redaction Notes",
        "Staleness And Human Review Notes",
        "Forbidden Use Caveats",
        "Next-Step Boundary Statement",
    ):
        assert heading in text


def test_runbook_documents_json_validation():
    text = _runbook()

    assert "python -m json.tool" in text
    assert "local_data/agent_context_reports/wp26_report.local.json" in text


def test_runbook_documents_git_hygiene():
    text = _normalized_runbook()

    assert "git status --short" in text
    assert "generated output must not be staged, tracked, or committed" in text
    assert "local_data/agent_context_exports/" in text
    assert "local_data/agent_context_reports/" in text


def test_runbook_documents_non_goals_and_forbidden_uses():
    text = _normalized_runbook()

    for phrase in (
        "hermes setup",
        "llm report generator",
        "agent runtime",
        "strategy recommendation",
        "trade proposal",
        "signal generator",
        "backtest",
        "paper trading",
        "live trading",
        "scheduler",
        "bot loop",
        "account, credential, or private endpoint access",
    ):
        assert phrase in text


def test_runbook_documents_stop_conditions():
    text = _normalized_runbook()

    for phrase in (
        "credential, secret, private endpoint, wallet, token, or account data is suspected",
        "input/output path outside allowlisted directories",
        "network, account, hermes, or runtime need arises",
        "intention changes to strategy suggestion, signal generation, recommendation, parameter recommendation, or execution",
        "tests/guards fail",
    ):
        assert phrase in text


def test_repo_truth_index_indexes_report_runbook():
    index = _read("docs/repo_truth_index.md")

    assert "docs/agent_context_report_operator_runbook.md" in index


def test_agent_context_report_generator_doc_references_report_runbook():
    generator_doc = _read("docs/agent_context_report_generator.md")

    assert "docs/agent_context_report_operator_runbook.md" in generator_doc


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
