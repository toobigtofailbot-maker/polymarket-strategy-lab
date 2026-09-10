"""Docs tests for WP41 advisory prompt/runbook package."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNBOOK_DOC = REPO_ROOT / "docs" / "advisory_prompt_runbook_package.md"


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_prompt_runbook_doc_exists():
    assert RUNBOOK_DOC.is_file()


def test_status_phrases_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "DOCS_ONLY_ADVISORY_PROMPT_RUNBOOK_PACKAGE",
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


def test_approved_advisory_use_cases_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "read-only market-state analysis",
        "performance review",
        "market research question planning",
        "strategy hypothesis narrative",
        "Codex / WP planning support",
        "advisory-only",
        "human-reviewed",
    ]
    for phrase in required:
        assert phrase in text


def test_required_input_package_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "repo-truth docs read directly",
        "local_data/advisory_outputs/",
        "local_data/agent_context_exports/",
        "local_data/agent_context_reports/",
        "freshness",
        "source commit",
        "generated timestamp",
        "no implicit `local_data` crawling",
    ]
    for phrase in required:
        assert phrase in text


def test_forbidden_inputs_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
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
        "chat/user memory outside repo truth",
    ]
    for phrase in required:
        assert phrase in text


def test_mandatory_output_rules_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        "uncertainty/assumptions",
        "source/freshness limitations",
        "human-review checklist",
        "repo-truth verification reminder",
        "validation/security reminder",
        "avoid executable instructions",
    ]
    for phrase in required:
        assert phrase in text


def test_forbidden_outputs_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
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
        "automatic PR approval",
        "credential handling instructions",
    ]
    for phrase in required:
        assert phrase in text


def test_prompt_templates_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "Prompt Template: Read-Only Market-State Analysis",
        "Prompt Template: Performance Review From Local Reports/Exports",
        "Prompt Template: Market Research Question Planning",
        "Prompt Template: Strategy Hypothesis Narrative",
        "Prompt Template: Codex / WP Planning Support",
        "Role:",
        "Allowed inputs:",
        "Forbidden inputs/outputs:",
        "Required analysis sections:",
        "Uncertainty requirements:",
    ]
    for phrase in required:
        assert phrase in text


def test_operator_runbook_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "verify repo truth directly",
        "Identify allowed local artifacts",
        "Optionally run the WP40 local advisory consumer manually",
        "Prepare a sanitized context package",
        "Choose the correct prompt template",
        "Verify output contains `ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED`",
        "Reject output if it contains forbidden instructions",
        "separate approved WP",
    ]
    for phrase in required:
        assert phrase in text


def test_stop_escalation_conditions_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "credentials or secrets present",
        "private keys/wallet/account material present",
        "executable trading instructions",
        "merge readiness without direct GitHub/repo review",
        "runtime/Hermes/LLM/provider/network/database/dashboard/scheduler/paper/live",
        "trading/account/order/signing/copy-trading/dependency changes",
        "stale or missing provenance",
        "repo truth conflicts with prompt output",
    ]
    for phrase in required:
        assert phrase in text


def test_relationship_to_wp40_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "WP40 output may be used only as advisory context",
        "WP40 output is not repo truth",
        "WP40 output is not validation",
        "WP40 output cannot authorize trades, merges, runtime work, or protected changes",
    ]
    for phrase in required:
        assert phrase in text


def test_future_llm_hermes_separation_present():
    text = RUNBOOK_DOC.read_text(encoding="utf-8")
    required = [
        "does not authorize LLM/Hermes/provider runtime",
        "explicit user approval",
        "manual setup decision",
        "dependency/security review",
        "data-sharing boundary",
        "prompt boundary",
        "The repo must not run it",
    ]
    for phrase in required:
        assert phrase in text


def test_repo_truth_index_indexes_doc_and_numbers_are_sequential():
    text = read_repo_file("docs/repo_truth_index.md")
    assert "docs/advisory_prompt_runbook_package.md" in text
    numbers = [
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\.\s+`", text, flags=re.MULTILINE)
    ]
    assert numbers == list(range(1, len(numbers) + 1))
    assert len(numbers) == len(set(numbers))


def test_project_status_references_wp41_and_next_wps():
    text = read_repo_file("docs/project_status.md")
    required = [
        "WP41 - Advisory Prompt/Runbook Package",
        "WP40",
        "WP42 - Advisory Prompt/Runbook Package Follow-Up",
        "WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening",
        "WP42 - Provider/Hermes Decision Refresh",
    ]
    for phrase in required:
        assert phrase in text


def test_deferred_items_log_references_required_items():
    text = read_repo_file("docs/deferred_items_log.md")
    required = [
        "WP39-D002",
        "WP40-D001",
        "WP40-D002",
        "WP41-D001",
        "WP41-D002",
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
        "tools/advisory/prompt_runner",
        "tools/advisory/runbook_runner",
        "tools/advisory/llm",
        "tools/hermes/",
        "src/agents/",
        "src/agent_layer/",
        "agent_runtime/",
        "agent_memory/",
        "local_data/advisory_prompts/",
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
