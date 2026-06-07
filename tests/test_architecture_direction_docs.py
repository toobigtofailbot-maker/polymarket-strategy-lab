"""Focused docs tests for WP61 architecture direction lock-in."""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "architecture_decision_record.md"


def test_architecture_direction_record_exists():
    assert ADR.exists()


def test_architecture_direction_lockin_contains_required_decisions():
    text = ADR.read_text(encoding="utf-8")
    lower = text.lower()

    assert "## WP61 Direction Lock-In - User-Approved Execution Path" in text
    assert "sqlite first" in lower
    assert "postgres deferred" in lower or "postgres later" in lower
    assert "streamlit first" in lower
    assert "grafana later" in lower
    assert "next.js only if productizing" in lower
    assert "local development first" in lower
    assert "cheap vps later" in lower
    assert "rules-based + research-score-driven strategy first" in lower
    assert "llm may be used only as read-only analyst/proposal layer" in lower
    assert "no autonomous llm execution authority" in lower
    assert "research-only -> paper -> dry-run -> manual live approval -> restricted live" in lower
    assert "no database, dashboard, runtime, deployment, scheduler, or execution implementation in wp61" in lower
    assert "agent mode / deep research" in lower
