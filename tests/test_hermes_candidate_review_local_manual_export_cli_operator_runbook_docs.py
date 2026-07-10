"""Focused docs tests for WP116 CLI operator runbook and smoke receipt."""

from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "hermes_candidate_review_local_manual_export_cli_operator_runbook.md"
SMOKE_RECEIPT = ROOT / "docs" / "hermes_candidate_review_local_manual_export_cli_smoke_receipt.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP116.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _status() -> str:
    return STATUS_ENTRY.read_text(encoding="utf-8")


def test_runbook_exists_at_expected_path() -> None:
    assert RUNBOOK.is_file()


def test_runbook_records_exact_command_shape_and_arguments() -> None:
    text = _runbook()
    assert (
        "python -m tools.hermes_candidate_review_manual_export_cli "
        "--artifact-json <path.json> --output <path.md_or_txt> [--overwrite]"
    ) in text
    for arg in ("--artifact-json", "--output", "--overwrite"):
        assert arg in text


def test_runbook_states_wp116_docs_status_tests_only_and_no_cli_modification() -> None:
    text = _runbook()
    assert "WP116 is docs/status/tests-only" in text
    assert "does not modify the CLI" in text


def test_runbook_requires_strict_wp108_artifact_result_json_envelope() -> None:
    text = _runbook()
    assert "strict WP108 artifact-result JSON envelope only" in text
    assert "already valid artifact result" in text


def test_runbook_forbids_raw_hermes_model_prompt_output_and_raw_metadata() -> None:
    text = _runbook()
    for phrase in (
        "raw Hermes output",
        "raw model output",
        "prompt-runner output",
        "raw prompt text",
        "raw metadata",
        "free-form metadata",
        "arbitrary caller metadata",
    ):
        assert phrase in text


def test_runbook_forbids_private_account_order_paper_live_runtime_state() -> None:
    text = _runbook()
    for phrase in (
        "credentials",
        "private state",
        "account state",
        "order state",
        "paper state",
        "live state",
        "runtime logs",
    ):
        assert phrase in text


def test_runbook_forbids_signal_order_return_sizing_approval_interpretations() -> None:
    text = _runbook()
    for phrase in (
        "trade-signal",
        "expected-return",
        "position-sizing",
        "buy/sell/order",
        "PR approval",
        "merge-readiness",
    ):
        assert phrase in text


def test_runbook_requires_explicit_local_output_and_existing_parent() -> None:
    text = _runbook()
    assert "explicit local `.md` or `.txt` path only" in text
    assert "parent directory that already exists" in text
    assert "not dependent on parent-directory creation" in text


def test_runbook_forbids_uri_like_and_tracked_protected_repo_paths() -> None:
    text = _runbook()
    assert "not a URI-like path" in text
    for path in ("`docs/`", "`src/`", "`tests/`", "`tools/`", "`.github/`", "`local_data/`"):
        assert path in text
    assert "tracked repo paths" in text
    assert "generated-artifact paths" in text


def test_runbook_documents_success_stdout_stderr_and_output_behavior() -> None:
    text = _runbook()
    for phrase in (
        "process exits `0`",
        "stdout contains only a bounded neutral JSON summary",
        "stderr is empty",
        "output file is written by the existing WP109 writer",
        "manual review aid only",
    ):
        assert phrase in text


def test_runbook_documents_failure_exit_codes_and_no_unsafe_echo() -> None:
    text = _runbook()
    for phrase in ("| 2 | Input/envelope validation failure.", "| 3 | Path/output validation failure.", "| 4 | Protected-boundary refusal.", "| 5 | Sanitized unexpected internal error."):
        assert phrase in text
    assert "must create no output file" in text
    assert "must not echo unsafe content" in text


def test_runbook_requires_human_review() -> None:
    assert "manual review aid only" in _runbook()


def test_runbook_says_generated_artifacts_are_not_committed() -> None:
    text = _runbook()
    assert "Generated local artifacts are not committed" in text
    assert "never stage generated local review artifacts" in text


def test_runbook_documents_future_gates_as_separate_approved_wps() -> None:
    text = _runbook()
    assert "require separate approved WPs" in text
    for phrase in (
        "dashboard display",
        "automation or report pipeline behavior",
        "Hermes runtime",
        "paper assistant or live approval packet",
        "credentials",
        "execution, risk, order",
        "scheduler",
        "dependency, workflow, or lock-file changes",
    ):
        assert phrase in text


def test_smoke_receipt_exists_and_contains_no_generated_artifact_content() -> None:
    assert SMOKE_RECEIPT.is_file()
    text = SMOKE_RECEIPT.read_text(encoding="utf-8")
    assert "WP115 focused tests already prove" in text
    assert "pytest `tmp_path`" in text
    assert "does not commit generated artifact content" in text
    assert "synthetic-artifact-001" not in text
    assert "Hermes Candidate-Review Handoff Manual Export Artifact" not in text


def test_wp116_status_fragment_inventory_and_stable_wording() -> None:
    text = _status()
    assert "Changed files (11):" in text
    expected = (
        "docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md",
        "docs/hermes_candidate_review_local_manual_export_cli_smoke_receipt.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
        "docs/status_entries/WP116.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_manual_export_cli.py",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
    )
    for path in expected:
        assert path in text
    for phrase in (
        "WP116 on branch",
        "WP116 active branch",
        "PR: TBD",
        "Merge commit: TBD",
        "LOCAL_DRAFT_VERIFIED",
        "count depends",
    ):
        assert phrase not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None


def test_project_status_records_wp116_wp117_merged_and_wp118_review_target() -> None:
    text = PROJECT_STATUS.read_text(encoding="utf-8")
    current_phase_line = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP118" in current_phase_line
    assert "WP119" in current_phase_line
    assert "WP120" in current_phase_line
    assert "WP121" in current_phase_line
    assert "WP115" in merged_line
    assert "WP116" in merged_line
    assert "WP117" in merged_line
    assert "WP118" in merged_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
    assert "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_OPERATOR_RUNBOOK_SMOKE_RECEIPT_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_CHAIN_CLOSEOUT_RESEARCH_WORKFLOW_TRANSITION_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_INTAKE_CONTRACT_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_RUNBOOK_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_MERGED" in text


def test_repo_truth_index_registers_wp116_surfaces() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_operator_runbook.md",
        "docs/hermes_candidate_review_local_manual_export_cli_smoke_receipt.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
        "docs/status_entries/WP116.md",
    ):
        assert path in text


def test_wp116_changed_file_inventory_excludes_src_and_tools_files() -> None:
    text = _status()
    inventory = text.split("Changed files (11):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
    assert "src/" not in inventory
    assert "tools/hermes_candidate_review_manual_export_cli.py" not in inventory
    assert "historical" not in inventory.lower()
