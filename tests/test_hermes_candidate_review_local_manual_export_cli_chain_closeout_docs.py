"""Focused docs tests for WP117 CLI chain closeout and transition decision."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_cli_chain_closeout.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP117.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_closeout_doc_exists() -> None:
    assert DOC.is_file()


def test_completed_chain_is_recorded_in_correct_order() -> None:
    text = _normalized(DOC)
    chain = (
        "WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> "
        "WP112 -> WP113 -> WP114 -> WP115 -> WP116"
    )
    assert chain in text
    labels = (
        "WP106: operator handoff object",
        "WP107: local manual export contract",
        "WP108: manual export artifact builder",
        "WP109: local/manual writer",
        "WP110: writer operator runbook",
        "WP111: temp-only writer smoke exercise",
        "WP112: chain closeout / next-phase decision record",
        "WP113: CLI wrapper contract",
        "WP114: CLI command surface and input handoff contract",
        "WP115: local/offline/manual CLI wrapper implementation",
        "WP116: CLI operator runbook and smoke receipt",
    )
    for label in labels:
        assert label in text


def test_wp117_docs_status_tests_only_and_no_implementation_authority() -> None:
    text = _normalized(DOC)
    for phrase in (
        "WP117 is a docs/status/tests-only closeout",
        "does not implement new code",
        "does not modify the WP115 CLI",
        "does not add source implementation",
        "does not add source implementation under `src/`",
    ):
        assert phrase in text


def test_local_manual_export_layer_complete_for_bounded_operator_use() -> None:
    text = _normalized(DOC)
    assert "complete enough for bounded operator use" in text
    assert "local/manual export chain through WP116" in text


def test_supported_use_is_manual_local_offline_human_reviewed_only() -> None:
    text = _normalized(DOC)
    assert "only manual, local, offline, and human-reviewed export" in text
    assert "already-valid WP108 artifact-result envelopes" in text
    assert "WP115 CLI convenience wrapper" in text
    assert "lower-level import path" in text


def test_wp115_cli_is_convenience_wrapper_not_automation() -> None:
    text = _normalized(DOC)
    assert "The WP115 CLI is a convenience wrapper, not automation" in text


def test_generated_local_artifacts_must_not_be_committed() -> None:
    text = _normalized(DOC)
    assert "Generated local artifacts must not be committed" in text
    assert "Generated artifacts are never committed" in text


def test_human_review_remains_required() -> None:
    text = _normalized(DOC)
    assert "Human review remains required" in text
    assert "manual review aid" in text


def test_forbidden_interpretation_matrix_includes_required_families() -> None:
    text = _normalized(DOC).lower()
    for phrase in (
        "trade signal",
        "strategy recommendation",
        "expected-return estimate",
        "fair-value trading instruction",
        "alpha/edge trading instruction",
        "position sizing",
        "allocation instruction",
        "paper readiness",
        "live readiness",
        "deployment readiness",
        "pr approval",
        "merge readiness",
        "strategy promotion",
        "runtime instruction",
        "credential permission",
        "account/private-state access",
        "order placement/cancel",
        "execution authority",
        "risk override",
        "scheduler/bot-loop behavior",
        "dashboard display",
        "hermes runtime/provider/model/prompt-runner integration",
        "automated report/export pipeline",
        "dependency/workflow/lock-file change",
        "committed generated artifacts",
    ):
        assert phrase in text


def test_deferred_future_directions_remain_separate_approved_wps() -> None:
    text = _normalized(DOC)
    assert "WP117 resolves no implementation deferred item" in text
    assert "future-only and require separate approved WPs" in text
    for phrase in (
        "automated report/export pipeline",
        "dashboard display",
        "Hermes runtime/provider/model/prompt-runner integration",
        "paper assistant integration",
        "live/manual approval packet integration",
        "credentials/account/private state",
        "execution/risk/order behavior",
        "scheduler/bot-loop behavior",
        "dependency/workflow/lock-file changes",
    ):
        assert phrase in text


def test_next_phase_decision_points_to_hermes_assisted_research_workflow() -> None:
    text = _normalized(DOC)
    assert (
        "The next phase should shift from local export plumbing to "
        "Hermes-assisted candidate-review research workflow"
    ) in text
    assert "selects candidate-review packets" in text
    assert "runs or adapts Hermes research prompts manually" in text
    assert "validates Hermes advisory outputs through existing validators" in text
    assert "records human decisions" in text
    assert "stores research follow-up records" in text
    assert "WP117 does not implement that next phase" in text


def test_status_fragment_exact_changed_file_inventory_is_present() -> None:
    text = _read(STATUS_ENTRY)
    assert "Changed files (12):" in text
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_chain_closeout.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "docs/status_entries/WP117.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
    ):
        assert path in text


def test_status_fragment_stable_wording_no_dynamic_placeholders() -> None:
    text = _read(STATUS_ENTRY)
    for stale in (
        "WP117 on branch",
        "WP117 active branch",
        "PR: TBD",
        "TBD after merge",
        "LOCAL_DRAFT_VERIFIED",
        "count depends",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None
    assert "Branch: see GitHub PR metadata and PR body" in text
    assert "Current live PR head: see GitHub PR metadata and PR body" in text


def test_project_status_records_wp117_merged_or_later_review_target() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP117" in current_phase_line or "WP117" in merged_line
    assert any(wp in current_phase_line for wp in ("WP118", "WP119", "WP120", "WP121", "WP128"))
    assert "WP116" in merged_line
    assert "WP117" in merged_line
    assert "WP118" in merged_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
    assert "DOCS_STATUS_TESTS_ONLY_CLI_OPERATOR_RUNBOOK_SMOKE_RECEIPT_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_CHAIN_CLOSEOUT_RESEARCH_WORKFLOW_TRANSITION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_INTAKE_CONTRACT_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_RUNBOOK_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_MERGED" in text
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


def test_repo_truth_index_registers_wp117_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_chain_closeout.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "docs/status_entries/WP117.md",
    ):
        assert path in text


def test_changed_file_inventory_excludes_forbidden_paths() -> None:
    text = _read(STATUS_ENTRY)
    inventory = text.split("Changed files (12):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
    for forbidden in (
        "`src/",
        "tools/hermes_candidate_review_manual_export_cli.py",
        ".github/workflows/",
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "local_data/",
        "generated artifact",
    ):
        assert forbidden not in inventory
