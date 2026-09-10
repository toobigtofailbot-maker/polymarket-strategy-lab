"""Docs tests for WP39 advisory runtime boundary and consumption design."""

import json
import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN_DOC = REPO_ROOT / "docs" / "advisory_runtime_boundary_consumption_design.md"


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_design_doc_exists():
    assert DESIGN_DOC.is_file()


def test_design_doc_contains_status_phrases():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "DOCS_ONLY_ADVISORY_RUNTIME_BOUNDARY_DESIGN",
        "Codex and Claude Code",
        "NO_RUNTIME_CHANGE",
        "NO_NEW_TOOLING",
        "NO_DEPENDENCY_CHANGE",
        "NO_NETWORK",
        "NO_VALIDATION_WEAKENING",
        "NO_PROTECTED_BOUNDARY_CHANGE",
        "NO_AGENT_RUNTIME",
        "NO_HERMES_INSTALL_OR_RUNTIME",
        "NO_LLM_PROVIDER_RUNTIME",
        "NO_TRADING_EXECUTION",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_references_existing_components():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "docs/agent_model_registry.md",
        "docs/agent_context_export_schema.md",
        "docs/agent_context_exporter.md",
        "docs/agent_context_exporter_operator_runbook.md",
        "docs/agent_context_report_generator.md",
        "docs/agent_context_report_operator_runbook.md",
        "docs/agent_hermes_manual_setup_decision_record.md",
        "docs/local_advisory_handoff_package.md",
        "tools/git/diff_scope_summary.py",
        "tools/validation/validation_output_summary.py",
        "tools/git/code_blast_radius.py",
        "tools/git/status_snapshot.py",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_defines_advisory_consumer_boundary():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "advisory consumer",
        "local/offline/read-only",
        "not agent runtime",
        "not Hermes",
        "not LLM/provider runtime",
        "not scheduler/bot loop",
        "not trading/execution system",
        "not database/dashboard",
        "not account-connected",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_allowed_input_sources():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "local_data/agent_context_exports/",
        "local_data/agent_context_reports/",
        "explicitly provided by the operator",
        "no implicit crawling of `local_data`",
        "no arbitrary file reads",
        "no network input",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_forbidden_input_sources():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        ".env",
        "credentials",
        "private keys",
        "wallet keys",
        "mnemonics",
        "tokens",
        "account data",
        "private endpoint responses",
        "authenticated API data",
        "arbitrary `local_data` crawling",
        "chat/user memory outside repo truth",
        "live/paper trading account state",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_allowed_output_types():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "market-state summary",
        "performance review summary",
        "research question list",
        "strategy hypothesis narrative",
        "risk/uncertainty notes",
        "Codex/WP planning notes",
        "human-review checklist",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_forbidden_output_types():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "executable trading signals",
        "order instructions",
        "order placement/cancellation requests",
        "signing requests",
        "account actions",
        "copy-trading instructions",
        "liquidation-sensitive bot parameters",
        "position sizing",
        "autonomous parameter updates",
        "scheduler/bot-loop instructions",
        "live/paper trading decisions",
        "automatic PR approval",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_deterministic_local_advisory_model():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "first future prototype should be deterministic",
        "parse existing report/export files",
        "bounded advisory brief",
        "must not call an LLM",
        "must not call Hermes",
        "must not call network",
        "must not call account",
        "must not generate orders",
        "must not generate signals",
        "advisory-only, human-review, and validation reminders",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_future_llm_hermes_separation():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "LLM/Hermes consumption is not authorized by WP39",
        "separate provider/manual setup decision",
        "security/dependency review",
        "prompt boundary",
        "data-sanitization review",
        "deterministic local consumer may be built before any LLM/Hermes integration",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_future_wp40_requirements():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "WP40 - Local Advisory Consumer Prototype",
        "local/offline/read-only deterministic advisory consumer prototype",
        "reads only explicitly provided local export/report paths",
        "no LLM/Hermes/network/account/trading",
        "no signal/order output",
        "no credential reads",
    ]
    for phrase in required:
        assert phrase in text


def test_design_doc_contains_security_and_human_review_requirements():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    required = [
        "safe input allowlist",
        "output redaction for obvious secrets",
        "no command execution",
        "no credential file reading",
        "no generated output committed",
        "Every advisory output must be clearly labeled advisory-only",
        "Outputs must include uncertainty/assumptions",
        "Outputs cannot decide merge readiness",
    ]
    for phrase in required:
        assert phrase in text


def test_repo_truth_index_indexes_design_doc_and_numbers_are_sequential():
    text = read_repo_file("docs/repo_truth_index.md")
    assert "docs/advisory_runtime_boundary_consumption_design.md" in text

    numbers = [
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\.\s+`", text, flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) == len(set(numbers))


def test_project_status_references_wp39_and_next_wps():
    text = read_repo_file("docs/project_status.md")
    required = [
        "WP39 - Advisory Runtime Boundary And Consumption Design",
        "WP38",
        "WP40 - Local Advisory Consumer Prototype",
        "WP40 - Advisory Runtime Boundary Design Follow-Up",
    ]
    for phrase in required:
        assert phrase in text


def test_deferred_items_references_wp39_and_wp38_items():
    text = read_repo_file("docs/deferred_items_log.md")
    required = ["WP38-D001", "WP38-D002", "WP39-D001", "WP39-D002"]
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
        "local_data/advisory_outputs/",
    ]
    forbidden_tool_patterns = [
        re.compile(r"^tools/advisory_agent"),
        re.compile(r"^tools/advisory_consumer"),
        re.compile(r"^tools/hermes(?:/|$)"),
    ]
    for path in tracked:
        normalized = path.replace("\\", "/")
        assert not any(normalized.startswith(prefix) for prefix in forbidden_exact_or_prefixes)
        assert not any(pattern.search(normalized) for pattern in forbidden_tool_patterns)


def test_dependency_files_do_not_add_forbidden_dependencies():
    wp171_spec = REPO_ROOT / "docs/wp_specs/WP171/wp_spec.json"
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
            if name == "fastapi" and rel == "pyproject.toml" and wp171_spec.is_file():
                spec = json.loads(wp171_spec.read_text(encoding="utf-8"))
                assert "pyproject.toml" in spec["scope"]["required_changed_files"]
                assert spec["authority"]["dependencies"] is True
                continue
            assert name not in text, f"Forbidden dependency marker {name!r} in {rel}"
