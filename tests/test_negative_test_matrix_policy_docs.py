"""Docs tests for docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md — WP58."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "ai" / "codex" / "NEGATIVE_TEST_MATRIX_POLICY.md"


def read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.is_file(), f"Missing: {DOC_PATH}"


def test_doc_applies_to_validators():
    content = read_doc()
    assert "validator" in content.lower()


def test_doc_applies_to_scorers():
    content = read_doc()
    assert "scorer" in content.lower()


def test_doc_applies_to_parsers():
    content = read_doc()
    assert "parser" in content.lower()


def test_doc_applies_to_schema_validators():
    content = read_doc()
    assert "schema validator" in content.lower()


def test_doc_includes_null_missing_wrong_type():
    content = read_doc()
    lower = content.lower()
    assert "null" in lower or "missing required" in lower
    assert "wrong type" in lower or "type" in lower


def test_doc_includes_forbidden_wording():
    content = read_doc()
    assert "forbidden wording" in content.lower() or "forbidden" in content.lower()


def test_doc_includes_credential_like():
    content = read_doc()
    assert "credential" in content.lower()


def test_doc_includes_trade_like():
    content = read_doc()
    assert "trade" in content.lower()


def test_doc_includes_case_insensitive():
    content = read_doc()
    assert "case" in content.lower()


def test_doc_includes_spelling_variants():
    content = read_doc()
    lower = content.lower()
    assert "spell" in lower or "variant" in lower


def test_doc_includes_safe_wording_category():
    content = read_doc()
    lower = content.lower()
    assert "safe" in lower or "allowed wording" in lower or "positive case" in lower


def test_doc_requires_pr_body_statement():
    content = read_doc()
    lower = content.lower()
    assert "Negative test matrix required" in content or "pr body must state" in lower


def test_doc_ready_yes_forbidden_without_matrix():
    content = read_doc()
    lower = content.lower()
    assert "Ready for review: YES" in content
    assert "must not" in lower or "forbidden" in lower or "not be marked" in lower
