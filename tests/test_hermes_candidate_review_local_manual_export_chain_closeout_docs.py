"""Focused WP112 docs tests for local manual export chain closeout."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_chain_closeout.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP112.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_closeout_doc_exists() -> None:
    assert DOC.is_file()


def test_closeout_references_chain_order() -> None:
    text = _normalized(_read(DOC))
    assert "WP106 -> WP111" in text
    assert "WP106 -> WP108 -> WP109 -> WP110 -> WP111" in text
    for wp in ("WP106", "WP108", "WP109", "WP110", "WP111"):
        assert wp in text
    assert text.index("WP106 valid") < text.index("WP108 valid") < text.index("WP109 explicit")
    assert text.index("WP109 explicit") < text.index("WP110 operator") < text.index("WP111 temp-only")


def test_closeout_states_manual_only_local_offline_bounded_use() -> None:
    text = _normalized(_read(DOC)).lower()
    assert "manual-only, local-only, and offline-only" in text
    assert "valid wp106 in-memory candidate-review operator handoff" in text
    assert "valid wp108 in-memory manual export artifact" in text
    assert "existing wp109 explicit local/manual file writer" in text
    assert "wp110 operator runbook" in text
    assert "wp111 temp-only pytest smoke exercise" in text


def test_closeout_states_wp112_adds_no_src_tool_runtime_changes() -> None:
    text = _normalized(_read(DOC)).lower()
    for phrase in (
        "wp112 is a docs/status/tests-only closeout",
        "creates no source implementation",
        "new writer",
        "cli",
        "tool",
        "runtime execution",
        "scheduler",
        "daemon",
        "bot-loop behavior",
        "dependency or lock-file change",
        "workflow change",
    ):
        assert phrase in text


def test_output_surface_inventory_forbids_committed_generated_artifacts() -> None:
    text = _read(DOC)
    for phrase in (
        "WP106 in-memory handoff result",
        "WP108 in-memory manual export artifact",
        "WP109 explicit local `.md` or `.txt` artifact file",
        "WP111 pytest `tmp_path` Markdown file",
        "Generated artifacts are never committed",
        "WP112 adds no generated artifact file",
    ):
        assert phrase in text


def test_forbidden_scope_matrix_lists_required_forbidden_interpretations() -> None:
    text = _normalized(_read(DOC)).lower()
    for phrase in (
        "trade signal",
        "strategy recommendation",
        "expected-return estimate",
        "position sizing",
        "paper readiness",
        "live readiness",
        "pr approval",
        "merge readiness",
        "strategy promotion",
        "execution authority",
        "runtime instruction",
        "credential permission",
        "automated report pipeline",
        "hermes runtime authorization",
        "scheduler/bot-loop authorization",
    ):
        assert phrase in text


def test_future_phase_options_are_separate_and_not_authorized() -> None:
    text = _read(DOC)
    normalized = _normalized(text)
    for option in (
        "A. Human/manual usage only, no further code",
        "B. CLI wrapper for local manual export artifact layer",
        "C. Automated local report/export pipeline",
        "D. Dashboard display",
        "E. Hermes runtime/provider/model/prompt-runner integration",
        "F. Paper-trading review assistant integration",
        "G. Live/manual approval packet integration",
    ):
        assert option in text
    assert text.count("Not authorized by WP112") >= 7
    assert normalized.count("requires a separate approved WP") >= 7


def test_deferred_items_remain_open_for_cli_and_report_automation() -> None:
    text = _normalized(_read(DOC)).lower()
    assert "cli wrapper for the local manual export artifact layer" in text
    assert "automated local report/export pipeline" in text
    assert "wp112 resolves no implementation deferred item" in text
    assert "remain open and require separate approved wps" in text


def test_human_review_is_required() -> None:
    text = _normalized(_read(DOC)).lower()
    assert "human review remains required" in text
    assert "manual review aid only" in text


def test_forbidden_interpretation_families_are_rejected() -> None:
    text = _normalized(_read(DOC)).lower()
    for phrase in (
        "trade signal",
        "paper readiness",
        "live readiness",
        "execution authority",
        "risk behavior",
        "credential",
        "scheduler",
        "hermes runtime",
        "prompt runner",
    ):
        assert phrase in text


def test_wp112_status_entry_exists_and_has_exact_inventory() -> None:
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_chain_closeout.md",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
        "docs/status_entries/WP112.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
    ):
        assert path in text
    assert "Changed files (6):" in text


def test_wp112_status_entry_has_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    for stale in (
        "WP112 on branch",
        "WP112 active branch",
        "TBD after merge",
        "PR: TBD",
        "count depends",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None
    assert "Ready for review: YES only after final validation and posted evidence checks pass" in text


def test_project_status_records_wp112_and_preserves_boundaries() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert any(wp in current_phase_line for wp in ("WP112", "WP113", "WP114"))
    assert "WP111" in merged_line
    assert "WP112" in merged_line
    assert "WP113" in merged_line
    assert "Hermes candidate-review local manual export chain closeout status" in text
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_CHAIN_CLOSEOUT_REVIEW_TARGET" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_COMMAND_SURFACE_CONTRACT_REVIEW_TARGET" in text
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
    ):
        assert phrase in text


def test_repo_truth_index_registers_wp112_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_chain_closeout.md",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
        "docs/status_entries/WP112.md",
    ):
        assert path in text


def test_wp112_adds_no_src_file() -> None:
    status = _read(STATUS_ENTRY)
    inventory = status.split("Forbidden prefixes and files:")[0]
    assert "`src/" not in "\n".join(
        line for line in inventory.splitlines() if line.startswith("- `")
    )
