"""Docs tests for docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md — WP58."""

from __future__ import annotations

import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "ai" / "codex" / "POSTED_GITHUB_EVIDENCE_VERIFICATION.md"
VERIFIER_PATH = ROOT / "tools" / "git" / "posted_pr_evidence_verifier.py"


def read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.is_file(), f"Missing: {DOC_PATH}"


def test_verifier_exists():
    assert VERIFIER_PATH.is_file(), f"Missing: {VERIFIER_PATH}"


def test_doc_states_local_guard_limitation():
    content = read_doc()
    lower = content.lower()
    assert (
        "does not fetch" in lower
        or "local drafts only" in lower
        or "local guard" in lower
    ), "Doc must state that the local guard does not verify posted content"


def test_doc_requires_verifier_after_posting():
    content = read_doc()
    assert "posted_pr_evidence_verifier.py" in content
    assert "after" in content.lower()


def test_doc_defines_current_final_marker():
    content = read_doc()
    assert "CURRENT FINAL WP EVIDENCE" in content


def test_doc_references_verifier_tool():
    content = read_doc()
    assert "posted_pr_evidence_verifier.py" in content


def test_doc_states_pr_body_alone_insufficient():
    content = read_doc()
    lower = content.lower()
    assert (
        "not sufficient" in lower
        or "not prove" in lower
        or "does not prove" in lower
    ), "Doc must state that PR body alone is not sufficient proof"


def test_doc_says_ready_yes_forbidden_if_verifier_fails():
    content = read_doc()
    assert "Ready for review: NO" in content


def test_doc_no_auth_token_in_wp58():
    content = read_doc()
    lower = content.lower()
    assert (
        "no authentication" in lower
        or "no auth" in lower
        or "no token" in lower
        or "require authentication" in lower
        or "authentication" in lower
    ), "Doc must state that WP58 verifier uses no authentication"


def test_doc_references_discipline_checklist_and_report():
    content = read_doc()
    assert "PR_EVIDENCE_REPORTING_DISCIPLINE" in content
    assert "PR_REVIEW_CHECKLIST" in content
    assert "WP_EXECUTION_REPORT" in content


def test_doc_defines_manual_fallback():
    content = read_doc()
    lower = content.lower()
    assert "manual" in lower
    assert "unavailable" in lower or "cannot run" in lower
