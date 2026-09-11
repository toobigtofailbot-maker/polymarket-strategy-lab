"""Docs tests for WP42 advisory consumer operator workflow hardening."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_DOC = REPO_ROOT / "docs" / "advisory_consumer_operator_workflow.md"


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_operator_workflow_doc_exists():
    assert WORKFLOW_DOC.is_file()


def test_status_phrases_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_HARDENING",
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
        "NO_PROMPT_RUNNER",
    ]
    for phrase in required:
        assert phrase in text


def test_component_chain_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "docs/local_advisory_handoff_package.md",
        "docs/advisory_runtime_boundary_consumption_design.md",
        "docs/local_advisory_consumer_prototype.md",
        "tools/advisory/local_advisory_consumer.py",
        "docs/advisory_prompt_runbook_package.md",
        "docs/agent_context_exporter_operator_runbook.md",
        "docs/agent_context_report_operator_runbook.md",
        "tools/git/status_snapshot.py",
        "tools/git/diff_scope_summary.py",
        "tools/git/code_blast_radius.py",
        "tools/validation/validation_output_summary.py",
    ]
    for phrase in required:
        assert phrase in text


def test_workflow_stages_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "Stage 0",
        "verify repo truth directly",
        "identify allowed local artifacts",
        "check freshness",
        "optionally run WP40 local advisory consumer manually",
        "inspect WP40 advisory output",
        "select WP41 prompt template manually",
        "prepare sanitized context package",
        "human-operated advisory session",
        "review output against forbidden-output checklist",
        "separate approved WP",
    ]
    for phrase in required:
        assert phrase in text


def test_evidence_package_checklist_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "repo-truth files checked",
        "source commit recorded",
        "generated timestamp recorded",
        "local artifact paths explicitly listed",
        "stale/missing context noted",
        "warnings copied",
        "forbidden input check completed",
        "human reviewer",
        "no credentials/account/private endpoint/trading account data included",
    ]
    for phrase in required:
        assert phrase in text


def test_allowed_artifact_paths_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "local_data/agent_context_exports/",
        "local_data/agent_context_reports/",
        "local_data/advisory_outputs/",
        "explicit files only",
        "no implicit crawling",
        "no arbitrary file reads",
        "no tracked generated outputs",
    ]
    for phrase in required:
        assert phrase in text


def test_forbidden_inputs_and_stop_conditions_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        ".env",
        "credentials",
        "API keys",
        "private keys",
        "wallet keys",
        "mnemonics",
        "tokens",
        "account data",
        "private endpoint responses",
        "authenticated API data",
        "live/paper trading account state",
        "arbitrary local_data crawling",
        "network/GitHub API responses as runtime input",
    ]
    for phrase in required:
        assert phrase in text


def test_forbidden_output_checklist_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "executable trading signals",
        "order instructions",
        "signing requests",
        "account actions",
        "copy-trading instructions",
        "liquidation-sensitive bot parameters",
        "position sizing",
        "leverage recommendations",
        "scheduler/bot-loop instructions",
        "live/paper trading decisions",
        "claims of merge readiness",
        "implementation approval",
        "automatic PR approval",
        "credential handling instructions",
        "command-runner instructions",
    ]
    for phrase in required:
        assert phrase in text


def test_decision_log_template_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "workflow date",
        "operator",
        "repo commit checked",
        "repo-truth files checked",
        "local artifacts used",
        "artifact generated timestamps",
        "stale-context notes",
        "WP40 consumer command used",
        "WP41 prompt template used",
        "rejected outputs",
        "accepted advisory observations",
        "resulting repo action",
        "required next WP",
        "confirmation no protected work was authorized",
    ]
    for phrase in required:
        assert phrase in text


def test_conversion_rules_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "advisory observations do not become work automatically",
        "every repo change needs a separate explicit WP",
        "runtime/protected areas require explicit authorization",
        "first create a design WP",
        "Provider/Hermes Decision Refresh",
        "separate risk/legal/authorization WPs",
    ]
    for phrase in required:
        assert phrase in text


def test_relationship_to_wp41_present():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    required = [
        "WP41 prompt templates are manual-only",
        "WP42 defines how to operate them safely",
        "does not create a prompt runner",
        "does not authorize LLM/Hermes/provider runtime",
    ]
    for phrase in required:
        assert phrase in text


def test_repo_truth_index_indexes_workflow_doc_and_numbers_are_sequential():
    text = read_repo_file("docs/repo_truth_index.md")
    assert "docs/advisory_consumer_operator_workflow.md" in text
    numbers = [
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\.\s+`", text, flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) == len(set(numbers))


def test_project_status_references_wp42_and_next_wps():
    text = read_repo_file("docs/project_status.md")
    required = [
        "WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening",
        "WP41",
        "WP43 - Provider/Hermes Decision Refresh",
        "WP43 - Local Advisory Workflow Follow-Up",
    ]
    for phrase in required:
        assert phrase in text


def test_deferred_items_log_references_required_items():
    text = read_repo_file("docs/deferred_items_log.md")
    required = [
        "WP41-D001",
        "WP41-D002",
        "WP40-D002",
        "WP42-D001",
        "WP42-D002",
    ]
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
        "tools/advisory/workflow_runner",
        "tools/advisory/prompt_runner",
        "tools/advisory/llm",
        "tools/hermes/",
        "src/agents/",
        "src/agent_layer/",
        "agent_runtime/",
        "agent_memory/",
        "local_data/advisory_workflows/",
        "local_data/advisory_outputs/",
    ]
    for path in tracked:
        normalized = path.replace("\\", "/")
        assert not any(
            normalized.startswith(prefix) for prefix in forbidden_exact_or_prefixes
        ), normalized


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
