"""Focused docs tests for WP118 research workflow intake contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_research_workflow_intake_contract.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP118.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_contract_doc_exists() -> None:
    assert DOC.is_file()


def test_wp118_is_docs_status_tests_only() -> None:
    text = _normalized(DOC)
    assert "WP118 is docs/status/tests-only" in text
    for phrase in (
        "does not implement Hermes runtime",
        "does not implement any output schema, writer, validator, or storage",
        "no implementation, no runtime, no automation",
    ):
        assert phrase in text


def test_chain_context_through_wp117_is_recorded() -> None:
    text = _normalized(DOC)
    chain = (
        "WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> "
        "WP113 -> WP114 -> WP115 -> WP116 -> WP117"
    )
    assert chain in text
    assert "WP117 moved the project from export plumbing toward research workflow" in text
    assert "WP118 starts that transition with intake discipline only" in text


def test_supported_intake_is_manual_local_offline_advisory_and_reviewed() -> None:
    text = _normalized(DOC)
    for phrase in (
        "manual operator selection of candidate-review packets",
        "manual",
        "local",
        "offline",
        "advisory-only",
        "human-reviewed",
        "based on already-valid upstream artifacts or packets",
        "free of credentials, private state, account state, orders, paper/live state, runtime logs, and raw model output",
    ):
        assert phrase in text


def test_allowed_input_surfaces_are_listed() -> None:
    text = _normalized(DOC)
    for phrase in (
        "already-valid WP106 candidate-review handoff object or exported representation",
        "already-valid WP108 manual export artifact result or reviewed local export artifact",
        "WP115 CLI-exported local review artifact",
        "strict valid WP108 envelope",
        "existing repo-truth docs and status fragments",
        "human operator notes that are structured, reviewed, non-secret",
        "not raw/free-form metadata",
    ):
        assert phrase in text


def test_no_parser_loader_or_implementation_is_created_or_authorized() -> None:
    text = _normalized(DOC)
    assert "does not create any new input parser or file loader" in text
    for phrase in (
        "does not create a runner",
        "prompt executor",
        "parser",
        "file loader",
        "provider/model integration",
    ):
        assert phrase in text


def test_intake_preflight_includes_required_safety_checks() -> None:
    text = _normalized(DOC)
    for phrase in (
        "valid upstream chain provenance",
        "evidence references are manually inspectable",
        "uncertainty, missing data, and limitations are explicit",
        "no raw model/Hermes output is treated as fact",
        "no credential/private/account/order/paper/live/runtime data is present",
        "no trade signal, expected return, fair value, alpha/edge as trading instruction",
        "position sizing",
        "allocation",
        "paper/live readiness",
        "PR approval",
        "merge readiness",
        "strategy promotion",
        "execution authority",
        "risk override",
        "generated local review artifacts are not committed",
    ):
        assert phrase in text


def test_packet_selection_criteria_are_research_triage_only() -> None:
    text = _normalized(DOC)
    assert "non-executing research triage only" in text
    for phrase in (
        "resolution-rule ambiguity",
        "evidence quality gaps",
        "wallet/signal uncertainty",
        "cross-market inconsistency candidate",
        "market-structure/microstructure concern",
        "stale or missing data risk",
        "operator uncertainty requiring deeper research",
    ):
        assert phrase in text
    assert "Selection is not a trade signal and not a strategy recommendation" in text


def test_future_output_concepts_are_listed_but_not_implemented() -> None:
    text = _normalized(DOC)
    for phrase in (
        "research question record",
        "source checklist",
        "advisory output validation result",
        "human decision record",
        "follow-up research task",
        "rejection/accept-for-further-research label",
        "does not implement any output schema, writer, validator, or storage",
    ):
        assert phrase in text


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


def test_future_gates_require_separate_approved_wps() -> None:
    text = _normalized(DOC)
    assert "Separate approved WPs are required for" in text
    for phrase in (
        "research workflow runbook",
        "research question record schema",
        "manual Hermes prompt adaptation guide",
        "advisory output validation receipt integration",
        "human decision/follow-up record format",
        "storage or local file writing",
        "any Hermes runtime/provider/model/prompt execution",
        "automation/report pipeline/dashboard",
        "paper/live/execution/risk/order/credentials/scheduler/dependency/workflow behavior",
    ):
        assert phrase in text


def test_status_fragment_has_exact_inventory_and_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    assert "Changed files (8):" in text
    for path in (
        "docs/hermes_candidate_review_research_workflow_intake_contract.md",
        "tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py",
        "docs/status_entries/WP118.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
    ):
        assert path in text
    for stale in (
        "WP118 on branch",
        "WP118 active branch",
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


def test_project_status_records_wp118_review_target_and_wp117_merged() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert any(wp in current_phase_line for wp in ("WP118", "WP120", "WP121", "WP128", "WP130"))
    assert "WP117" in merged_line
    assert "WP118" in merged_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
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


def test_repo_truth_index_registers_wp118_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_research_workflow_intake_contract.md",
        "tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py",
        "docs/status_entries/WP118.md",
    ):
        assert path in text


def test_changed_file_inventory_excludes_forbidden_paths() -> None:
    text = _read(STATUS_ENTRY)
    inventory = text.split("Changed files (8):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
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
