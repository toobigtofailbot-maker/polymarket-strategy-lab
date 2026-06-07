"""Docs tests for WP60A multi-agent startup layer — AI_CODING_AGENT_START_HERE.md and adapter alignment."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

AI_START = ROOT / "AI_CODING_AGENT_START_HERE.md"
AGENTS = ROOT / "AGENTS.md"
CODEX_START = ROOT / "CODEX_START_HERE.md"
CLAUDE_START = ROOT / "CLAUDE_START_HERE.md"
CODEX_README = ROOT / "docs" / "ai" / "codex" / "README.md"
WORK_PKG_TEMPLATE = ROOT / "docs" / "work_package_template.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
REPO_TRUTH_INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# --- AI_CODING_AGENT_START_HERE.md existence and content ---

def test_ai_coding_agent_start_here_exists():
    assert AI_START.is_file(), f"Missing: {AI_START}"


def test_ai_start_references_agents_md():
    assert "AGENTS.md" in _read(AI_START)


def test_ai_start_references_codex_start_here():
    assert "CODEX_START_HERE.md" in _read(AI_START)


def test_ai_start_references_claude_start_here():
    assert "CLAUDE_START_HERE.md" in _read(AI_START)


def test_ai_start_references_project_status():
    assert "docs/project_status.md" in _read(AI_START)


def test_ai_start_references_repo_truth_index():
    assert "docs/repo_truth_index.md" in _read(AI_START)


def test_ai_start_references_deferred_items_log():
    assert "docs/deferred_items_log.md" in _read(AI_START)


def test_ai_start_references_wp_execution_state_machine():
    assert "docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md" in _read(AI_START)


def test_ai_start_defines_shared_startup_for_all_agents():
    content = _read(AI_START).lower()
    assert "all ai coding agents" in content or "every ai coding agent" in content


def test_ai_start_preserves_tool_specific_adapters():
    content = _read(AI_START)
    assert "CODEX_START_HERE.md" in content
    assert "CLAUDE_START_HERE.md" in content


# --- AGENTS.md title and shared wording ---

def test_agents_md_title_is_not_codex_rulebook():
    text = _read(AGENTS)
    assert "# Codex Rulebook" not in text


def test_agents_md_uses_ai_coding_agent_shared_wording():
    text = _read(AGENTS)
    assert "AI coding agent" in text or "AI Coding Agent" in text


def test_agents_md_external_code_rule_uses_agent_neutral_wording():
    text = _read(AGENTS)
    assert "the AI coding agent must check" in text, (
        "AGENTS.md External Code section must use 'the AI coding agent must check', not 'Codex must check'"
    )


def test_agents_md_no_shared_rule_codex_must_check():
    text = _read(AGENTS)
    assert "Codex must check" not in text, (
        "AGENTS.md must not contain 'Codex must check' — use 'the AI coding agent must check' for shared rules"
    )


# --- CODEX_START_HERE.md is Codex-specific adapter ---

def test_codex_start_identifies_as_codex_specific_adapter():
    content = _read(CODEX_START).lower()
    assert "codex" in content
    assert "adapter" in content or "codex-specific" in content


def test_codex_start_references_ai_coding_agent_start_here():
    assert "AI_CODING_AGENT_START_HERE.md" in _read(CODEX_START)


# --- CLAUDE_START_HERE.md is Claude-specific adapter ---

def test_claude_start_identifies_as_claude_specific_adapter():
    content = _read(CLAUDE_START).lower()
    assert "claude" in content
    assert "adapter" in content or "claude-specific" in content or "claude code" in content


def test_claude_start_references_ai_coding_agent_start_here():
    assert "AI_CODING_AGENT_START_HERE.md" in _read(CLAUDE_START)


# --- docs/ai/codex/README.md historical path clarity ---

def test_codex_readme_explains_historical_shared_path():
    content = _read(CODEX_README).lower()
    assert "historical" in content or "shared" in content
    assert "docs/ai/codex/" in _read(CODEX_README)


# --- .github/pull_request_template.md AI coding agent field ---

def test_pr_template_includes_ai_coding_agent_used():
    assert "AI coding agent used" in _read(PR_TEMPLATE)


# --- docs/work_package_template.md execution agent field ---

def test_work_package_template_includes_execution_agent():
    assert "Execution agent" in _read(WORK_PKG_TEMPLATE)


# --- docs/repo_truth_index.md includes shared startup file ---

def test_repo_truth_index_includes_ai_coding_agent_start_here():
    assert "AI_CODING_AGENT_START_HERE.md" in _read(REPO_TRUTH_INDEX)
