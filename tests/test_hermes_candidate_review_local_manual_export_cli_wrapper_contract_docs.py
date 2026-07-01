"""Focused docs tests for the WP113 local manual export CLI wrapper contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_cli_wrapper_contract.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP113.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _doc() -> str:
    return _read(DOC)


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, title: str) -> str:
    pattern = re.compile(
        rf"^## \d+\. {re.escape(title)}\n(?P<body>.*?)(?=^## \d+\. |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    assert match, f"Missing section: {title}"
    return match.group("body")


def test_contract_doc_exists() -> None:
    assert DOC.is_file()


def test_contract_states_wp113_docs_status_tests_only_and_no_cli_implementation() -> None:
    text = _normalized(_doc()).lower()
    assert "wp113 itself does not implement the cli" in text
    assert "docs/status/tests-only" in text
    for phrase in (
        "creates no command parser",
        "runner",
        "source module",
        "tool",
        "shell wrapper",
        "automation",
    ):
        assert phrase in text


def test_contract_references_completed_chain_and_wp107_contract_layer() -> None:
    text = _normalized(_doc())
    assert "WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112" in text
    for phrase in (
        "WP106 valid in-memory candidate-review operator handoff",
        "WP108 valid in-memory manual export artifact builder",
        "WP109 explicit local/manual file writer",
        "WP110 operator runbook",
        "WP111 temp-only pytest smoke exercise",
        "WP112 chain closeout and next-phase decision record",
        "WP107 remains the contract layer",
    ):
        assert phrase in text


def test_contract_states_future_cli_manual_local_offline_operator_only() -> None:
    text = _normalized(_section(_doc(), "Future CLI Required Boundaries")).lower()
    for phrase in (
        "manual-only",
        "local-only",
        "offline-only",
        "explicit operator invocation only",
    ):
        assert phrase in text


def test_contract_requires_explicit_local_md_txt_output_path_and_existing_parent() -> None:
    text = _normalized(_section(_doc(), "Future CLI Required Boundaries"))
    assert "Explicit operator-supplied output path only" in text
    assert ".md" in text
    assert ".txt" in text
    assert "Parent directory must exist" in text
    assert "explicit, local, operator supplied" in text


def test_contract_forbids_auto_paths_background_commits_and_parent_creation() -> None:
    text = _normalized(_section(_doc(), "Future CLI Required Boundaries")).lower()
    for phrase in (
        "no automatic path selection",
        "no parent-directory creation unless separately approved",
        "no generated artifacts committed",
        "no background writes",
    ):
        assert phrase in text


def test_contract_forbids_runtime_automation_network_credential_and_order_scope() -> None:
    text = _normalized(_section(_doc(), "Forbidden CLI Behavior Matrix")).lower()
    for phrase in (
        "scheduler",
        "daemon",
        "bot loop",
        "runtime service",
        "dashboard integration",
        "network/api/product/account access",
        "hermes runtime/provider/model/prompt-runner",
        "credentials/private state",
        "paper/live/execution/risk/order behavior",
    ):
        assert phrase in text


def test_contract_forbids_signal_readiness_approval_and_authority_interpretations() -> None:
    text = _normalized(_doc()).lower()
    for phrase in (
        "trade signal",
        "strategy recommendation",
        "expected return",
        "position sizing",
        "paper/live readiness",
        "pr approval",
        "merge readiness",
        "runtime instruction",
        "execution authority",
        "strategy promotion",
    ):
        assert phrase in text


def test_contract_requires_future_cli_fail_closed_on_invalid_input() -> None:
    text = _normalized(_section(_doc(), "Future CLI Input Contract Requirements")).lower()
    assert "must fail closed on invalid input" in text


def test_contract_forbids_raw_input_unsafe_echo_and_private_state() -> None:
    text = _normalized(_section(_doc(), "Future CLI Input Contract Requirements")).lower()
    for phrase in (
        "must never accept raw model output",
        "arbitrary raw caller dictionaries",
        "raw/free-form metadata",
        "account/private state",
        "paper/live state",
        "order state",
        "runtime logs",
        "must never echo unsafe input",
    ):
        assert phrase in text


def test_contract_preserves_safety_flags_and_requires_human_review() -> None:
    text = _normalized(_doc()).lower()
    assert "preserve wp108 and wp109 safety flags" in text
    assert "human review remains required" in text
    assert "must require human review" in text


def test_contract_states_future_implementation_requires_separate_approved_wp() -> None:
    text = _normalized(_section(_doc(), "Future Implementation Gate")).lower()
    assert "future implementation wp must be separately approved" in text
    for phrase in (
        "exact command surface",
        "arguments",
        "output behavior",
        "failure behavior",
        "tests",
        "allowed files",
        "negative tests",
    ):
        assert phrase in text


def test_wp113_status_entry_exists_and_lists_exact_changed_file_inventory() -> None:
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_wrapper_contract.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
        "docs/status_entries/WP113.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
    ):
        assert path in text
    assert "Changed files (7):" in text


def test_wp113_status_entry_uses_stable_branch_pr_head_wording() -> None:
    text = _read(STATUS_ENTRY)
    for stale in (
        "WP113 on branch",
        "WP113 active branch",
        "TBD",
        "count depends",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "Current live PR head: see GitHub PR metadata and PR body." in text


def test_project_status_records_wp113_review_target_and_preserves_boundaries() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert any(wp in current_phase_line for wp in ("WP113", "WP114", "WP115", "WP116", "WP117"))
    assert "WP112" in merged_line
    assert "WP113" in merged_line
    assert "Hermes candidate-review local manual export CLI wrapper contract status" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_WRAPPER_CONTRACT_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_COMMAND_SURFACE_CONTRACT_MERGED" in text
    assert (
        "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_REVIEW_TARGET" in text
        or "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED" in text
    )
    for phrase in (
        "no source implementation under `src/`",
        "no product/runtime network",
        "no Hermes runtime",
        "no credentials",
        "no paper/live",
        "no execution/risk/order",
        "no scheduler/dashboard/bot-loop",
        "no dependency/workflow/lock-file",
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


def test_repo_truth_index_registers_wp113_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_wrapper_contract.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
        "docs/status_entries/WP113.md",
    ):
        assert path in text


def test_status_inventory_adds_no_source_file() -> None:
    status = _read(STATUS_ENTRY)
    inventory = status.split("Forbidden prefixes and files:")[0]
    assert "`src/" not in "\n".join(
        line for line in inventory.splitlines() if line.startswith("- `")
    )
