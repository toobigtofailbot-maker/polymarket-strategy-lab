"""Docs tests for WP38 local advisory handoff package."""

import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HANDOFF_DOC = REPO_ROOT / "docs" / "local_advisory_handoff_package.md"


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_handoff_doc_exists():
    assert HANDOFF_DOC.is_file()


def test_handoff_doc_contains_status_phrases():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "DOCS_ONLY_LOCAL_ADVISORY_HANDOFF",
        "Codex and Claude Code",
        "NO_RUNTIME_CHANGE",
        "NO_NEW_TOOLING",
        "NO_DEPENDENCY_CHANGE",
        "NO_NETWORK",
        "NO_VALIDATION_WEAKENING",
        "NO_PROTECTED_BOUNDARY_CHANGE",
        "NO_AGENT_RUNTIME",
        "NO_HERMES_INSTALL_OR_RUNTIME",
        "NO_TRADING_EXECUTION",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_references_existing_components():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "docs/agent_model_registry.md",
        "docs/agent_context_export_schema.md",
        "docs/agent_context_exporter.md",
        "docs/agent_context_exporter_operator_runbook.md",
        "docs/agent_context_report_generator.md",
        "docs/agent_context_report_operator_runbook.md",
        "docs/agent_hermes_manual_setup_decision_record.md",
        "tools/git/diff_scope_summary.py",
        "tools/validation/validation_output_summary.py",
        "tools/git/code_blast_radius.py",
        "tools/git/status_snapshot.py",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_approved_advisory_capabilities():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "read-only analyst",
        "performance review",
        "market research",
        "strategy suggestion",
        "Codex / WP support",
        "advisory narrative only",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_forbidden_capabilities():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "fully autonomous trading agent",
        "live trading",
        "paper trading",
        "order placement",
        "order cancellation",
        "signing",
        "account connection",
        "credential use",
        "private authenticated APIs",
        "copy-trading execution",
        "scheduler/daemon/bot loop",
        "Hermes runtime",
        "LLM/provider runtime",
        "database/dashboard/deployment",
        "official-client runtime integration",
        "production polling",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_parameter_recommendation_boundary():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "Parameter recommendations may only be future advisory narrative",
        "No executable parameter recommendation engine",
        "No position sizing",
        "human-reviewed hypotheses",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_hermes_manual_setup_status():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "Hermes is not installed",
        "Hermes is not a runtime dependency",
        "No manual setup is required for WP38",
        "Future Hermes work requires explicit user approval",
        "Codex can prepare docs/tests/runbooks",
        "cannot complete user-side account/provider setup or credential creation",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_future_sequence():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "WP39 - Advisory Runtime Boundary And Consumption Design",
        "WP40 - Local Advisory Consumer Prototype",
        "WP41 - Advisory Prompt/Runbook Package",
        "WP42",
        "Recommended next WP after WP38 is WP39 - Advisory Runtime Boundary And Consumption Design",
    ]
    for phrase in required:
        assert phrase in text


def test_handoff_doc_contains_safety_boundary_checklist():
    text = HANDOFF_DOC.read_text(encoding="utf-8")
    required = [
        "no runtime behavior",
        "no network",
        "no credentials",
        "no Hermes install",
        "no LLM/provider dependency",
        "no trading",
        "no scheduler/bot loop",
        "no database/dashboard",
        "no generated outputs committed",
    ]
    for phrase in required:
        assert phrase in text


def test_repo_truth_index_indexes_handoff_doc_and_numbers_are_sequential():
    text = read_repo_file("docs/repo_truth_index.md")
    assert "docs/local_advisory_handoff_package.md" in text

    numbers = [
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\.\s+`", text, flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) == len(set(numbers))


def test_project_status_references_wp38_and_next_wps():
    text = read_repo_file("docs/project_status.md")
    required = [
        "WP38 - Local Advisory Handoff Package",
        "WP37",
        "WP39 - Advisory Runtime Boundary And Consumption Design",
        "WP39 - Local Advisory Handoff Follow-Up",
    ]
    for phrase in required:
        assert phrase in text


def test_deferred_items_references_wp38_items_and_wp37_item():
    text = read_repo_file("docs/deferred_items_log.md")
    required = ["WP38-D001", "WP38-D002", "WP37-D001"]
    for phrase in required:
        assert phrase in text


def test_no_forbidden_implementation_paths_exist():
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    forbidden_exact_or_prefixes = [
        "src/agents/",
        "src/agent_layer/",
        "tools/hermes/",
        "agent_runtime/",
        "agent_memory/",
        "local_data/advisory_agent/",
    ]
    forbidden_tool_patterns = [
        re.compile(r"^tools/advisory_agent"),
        re.compile(r"^tools/hermes(?:/|$)"),
    ]
    for path in tracked:
        normalized = path.replace("\\", "/")
        assert not any(normalized.startswith(prefix) for prefix in forbidden_exact_or_prefixes)
        assert not any(pattern.search(normalized) for pattern in forbidden_tool_patterns)


def test_dependency_files_do_not_add_forbidden_dependencies():
    dependency_files = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.cfg",
        "setup.py",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "Cargo.toml",
        "Cargo.lock",
    ]
    forbidden = [
        "openai",
        "anthropic",
        "langchain",
        "hermes",
        "py-clob-client",
        "py_clob_client",
        "web3",
        "ccxt",
        "fastapi",
        "streamlit",
        "plotly",
        "sqlalchemy",
        "chromadb",
        "llama-index",
        "mem0",
        "rich",
        "click",
        "typer",
    ]
    for rel in dependency_files:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert name not in text, f"Forbidden dependency marker {name!r} in {rel}"
