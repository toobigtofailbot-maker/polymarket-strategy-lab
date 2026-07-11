"""Focused docs tests for WP119 research workflow runbook."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_research_workflow_runbook.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP119.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_runbook_file_exists() -> None:
    assert DOC.is_file()


def test_wp119_states_docs_status_tests_only_and_no_implementation_authority() -> None:
    text = _normalized(DOC)
    assert "WP119 is a docs/status/tests-only operator runbook" in text
    for phrase in (
        "does not implement Hermes runtime",
        "does not add a prompt runner",
        "no implementation, no runtime, no automation",
        "no Hermes execution, no trading, and no generated artifacts",
    ):
        assert phrase in text


def test_runbook_references_wp118_intake_contract() -> None:
    text = _normalized(DOC)
    assert "WP118 is the intake contract" in text
    assert "after WP118 intake" in text


def test_runbook_references_completed_wp106_to_wp117_chain() -> None:
    text = _normalized(DOC)
    chain = (
        "WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> "
        "WP113 -> WP114 -> WP115 -> WP116 -> WP117"
    )
    assert chain in text
    assert "completed export and CLI convenience chain" in text


def test_operator_preconditions_include_required_boundaries() -> None:
    text = _normalized(DOC)
    for phrase in (
        "selected input passed WP118 intake checks",
        "source provenance is explicit",
        "evidence references are manually inspectable",
        "uncertainty, missing data, and limitations are explicit",
        "no raw model/Hermes output is treated as fact",
        "no credentials, private state, account state, order data, paper/live data, or runtime data is present",
        "no generated local artifacts are staged or committed",
        "all outputs remain advisory review aids only",
    ):
        assert phrase in text


def test_manual_workflow_steps_include_required_sequence() -> None:
    text = _normalized(DOC)
    for phrase in (
        "Select one candidate packet or artifact under WP118 intake criteria",
        "State the research question in neutral non-trading language",
        "List source references and what the operator must manually check",
        "List uncertainty, missing data, and limitations",
        "Optionally draft a Hermes research prompt manually",
        "do not execute it in-repo and do not add a prompt runner",
        "Review any externally/manual research output only as advisory text",
        "Validate the advisory output conceptually through existing validator boundaries without changing validators",
        "Record human decision intent conceptually",
        "Record any follow-up research task conceptually",
        "Keep all records outside committed generated artifacts",
    ):
        assert phrase in text


def test_research_question_rules_include_allowed_and_forbidden_families() -> None:
    text = _normalized(DOC).lower()
    for phrase in (
        "neutral and non-executing",
        "resolution-rule ambiguity",
        "evidence quality gap",
        "source conflict",
        "wallet/signal uncertainty",
        "cross-market inconsistency",
        "market-structure/microstructure concern",
        "stale/missing data risk",
        "should we buy/sell",
        "expected return",
        "fair value as trade instruction",
        "alpha/edge as trade instruction",
        "position size/allocation",
        "paper/live readiness",
        "execution/risk/order instructions",
        "pr approval or merge readiness",
    ):
        assert phrase in text


def test_manual_hermes_prompt_adaptation_boundary() -> None:
    text = _normalized(DOC)
    for phrase in (
        "manual and external to repo runtime",
        "installs or invokes no Hermes runtime, provider, model, or prompt runner",
        "No prompt output is accepted as fact without human review",
        "Raw model output must not be committed as repo truth",
        "Prompt templates may be discussed only as future approved WPs",
    ):
        assert phrase in text


def test_advisory_output_review_boundary_forbids_decision_engine_interpretation() -> None:
    text = _normalized(DOC)
    assert "Advisory output is not a decision engine" in text
    for phrase in (
        "source references",
        "uncertainty, missing data, limitations, and falsification checks",
        "cannot authorize strategy promotion",
        "PR approval",
        "merge readiness",
        "paper/live readiness",
        "execution/risk/order behavior",
        "credentials",
        "runtime behavior",
    ):
        assert phrase in text


def test_human_decision_categories_are_present_and_non_authoritative() -> None:
    text = _normalized(DOC)
    for category in (
        "REJECT_RESEARCH_CANDIDATE",
        "NEEDS_MORE_EVIDENCE",
        "ACCEPT_FOR_FURTHER_RESEARCH",
        "ESCALATE_TO_FUTURE_APPROVED_WP",
    ):
        assert category in text
    assert "not strategy promotion, trade decisions, paper/live readiness, or implementation approval" in text


def test_cleanup_repo_hygiene_forbids_tracked_and_protected_local_notes() -> None:
    text = _normalized(DOC)
    for phrase in (
        "No generated research notes are committed by WP119",
        "local notes must stay outside tracked repo paths",
        "check `git status` before committing",
        "No local outputs should be placed under `docs/`, `src/`, `tests/`, `tools/`, `.github/`, `local_data/`, generated-artifact paths, or tracked repo paths",
    ):
        assert phrase in text


def test_future_gates_require_separate_approved_wps() -> None:
    text = _normalized(DOC)
    assert "Separate approved WPs are required for" in text
    for phrase in (
        "research question record schema",
        "manual prompt template pack or adaptation guide",
        "advisory output validation receipt integration",
        "human decision/follow-up record format",
        "storage/local file writer",
        "automated report/export pipeline",
        "dashboard display",
        "Hermes runtime/provider/model/prompt execution",
        "credentials/account/private-state behavior",
        "paper/live/execution/risk/order behavior",
        "scheduler/bot-loop behavior",
        "dependency/workflow/lock-file changes",
        "committed generated artifacts",
    ):
        assert phrase in text


def test_status_fragment_has_exact_inventory_and_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    assert "Changed files (9):" in text
    for path in (
        "docs/hermes_candidate_review_research_workflow_runbook.md",
        "tests/test_hermes_candidate_review_research_workflow_runbook_docs.py",
        "docs/status_entries/WP119.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
    ):
        assert path in text
    for stale in (
        "WP119 on branch",
        "WP119 active branch",
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
    assert "stable and non-self-referential" in text


def test_project_status_records_wp120_merged_and_wp121_review_target() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert any(wp in current_phase_line for wp in ("WP121", "WP128", "WP130"))
    assert "WP118" in merged_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
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


def test_repo_truth_index_registers_wp119_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_research_workflow_runbook.md",
        "tests/test_hermes_candidate_review_research_workflow_runbook_docs.py",
        "docs/status_entries/WP119.md",
    ):
        assert path in text


def test_changed_file_inventory_excludes_forbidden_paths() -> None:
    text = _read(STATUS_ENTRY)
    inventory = text.split("Changed files (9):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
    for forbidden in (
        "`src/",
        "`tools/",
        ".github/workflows/",
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "local_data/",
        "generated artifact",
    ):
        assert forbidden not in inventory
