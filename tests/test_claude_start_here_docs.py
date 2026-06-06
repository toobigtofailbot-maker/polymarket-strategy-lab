"""Docs tests for CLAUDE_START_HERE.md — WP58."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "CLAUDE_START_HERE.md"


def read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.is_file(), f"Missing: {DOC_PATH}"


def test_doc_references_agents_md():
    content = read_doc()
    assert "AGENTS.md" in content


def test_doc_references_codex_start_here():
    content = read_doc()
    assert "CODEX_START_HERE.md" in content


def test_doc_references_project_status():
    content = read_doc()
    assert "docs/project_status.md" in content


def test_doc_references_repo_truth_index():
    content = read_doc()
    assert "docs/repo_truth_index.md" in content


def test_doc_references_deferred_items_log():
    content = read_doc()
    assert "docs/deferred_items_log.md" in content


def test_doc_says_repo_truth_overrides_chat_memory():
    content = read_doc()
    lower = content.lower()
    assert "repo truth" in lower or "merged repo truth" in lower
    assert "chat" in lower or "memory" in lower


def test_doc_says_live_github_beats_summaries():
    content = read_doc()
    lower = content.lower()
    assert "live" in lower or "github pr state" in lower


def test_doc_mentions_posted_github_evidence():
    content = read_doc()
    lower = content.lower()
    assert "posted" in lower and ("evidence" in lower or "github" in lower)


def test_doc_includes_stop_rules():
    content = read_doc()
    assert "stop" in content.lower()
