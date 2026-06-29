"""Focused docs tests for the WP110 local manual export operator runbook."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_operator_runbook.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP110.md"
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


def test_runbook_exists_at_expected_path() -> None:
    assert DOC.is_file()


def test_runbook_states_manual_local_offline_scope() -> None:
    text = _normalized(_doc()).lower()
    assert "manual-only local procedure" in text
    assert "local human-review artifact" in text
    assert "import-based python use" in text


def test_runbook_forbids_runtime_and_automation_scope() -> None:
    text = _doc().lower()
    for phrase in (
        "no source implementation",
        "cli",
        "scheduler",
        "daemon",
        "background writer",
        "network exporter",
        "hermes runtime",
        "provider",
        "model",
        "prompt runner",
        "dashboard",
        "bot loop",
        "dependency",
        "workflow",
        "generated-artifact",
        "credentials",
        "paper/live",
        "execution",
        "risk",
        "order",
    ):
        assert phrase in text


def test_runbook_requires_explicit_operator_supplied_local_path() -> None:
    section = _section(_doc(), "Allowed Output")
    normalized = _normalized(section)
    assert "operator supplies one explicit local output path" in normalized
    assert "not URI-like" in normalized or "URI-like" in normalized
    assert "must not create parent directories" in normalized
    assert "choose paths automatically" in normalized


def test_runbook_requires_parent_directory_and_suffix_limit() -> None:
    text = _doc()
    allowed_output = _section(text, "Allowed Output")
    preflight = _section(text, "Manual Preflight")
    combined = allowed_output + preflight
    assert "parent directory must already exist" in combined
    assert ".md" in combined
    assert ".txt" in combined


def test_runbook_forbids_committing_generated_artifacts() -> None:
    text = _doc()
    assert "Generated artifact files" in text
    assert "must not be committed" in text
    assert "No generated artifact is staged" in text


def test_runbook_forbids_misinterpretation_as_trading_or_readiness() -> None:
    text = _normalized(_doc()).lower()
    for phrase in (
        "not a trade signal",
        "not a strategy recommendation",
        "not a paper or live readiness statement",
        "not a pr approval",
        "not a merge-readiness statement",
        "not include real market data",
        "position sizing",
        "expected-return language",
        "trade language",
        "strategy promotion",
    ):
        assert phrase in text


def test_runbook_requires_human_review() -> None:
    text = _doc()
    assert "Human review is required" in text
    assert "local human-review artifact" in text


def test_runbook_failure_handling_forbids_validation_bypass() -> None:
    section = _section(_doc(), "Failure Handling")
    normalized = _normalized(section)
    assert "Do not retry by weakening validation" in normalized
    assert "editing artifacts manually" in normalized
    assert "bypassing WP108" in normalized


def test_code_example_is_illustrative_not_cli_and_uses_scratch_path() -> None:
    text = _doc()
    section = _section(text, "Safe Usage Pattern")
    assert "not a CLI" in section
    assert "local_data/manual_export_scratch/example_artifact.md" in section
    forbidden_example_phrases = (
        "api_key",
        "private_key",
        "wallet",
        "place_order",
        "submit_order",
        "live_ready",
        "paper_ready",
        "buy",
        "sell",
        "expected_return",
        "merge_ready",
    )
    code_blocks = re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)
    assert code_blocks, "Expected illustrative Python example"
    code = "\n".join(code_blocks).lower()
    for phrase in forbidden_example_phrases:
        assert phrase not in code


def test_status_entry_has_exact_changed_file_inventory_and_stable_wording() -> None:
    assert STATUS_ENTRY.is_file()
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_operator_runbook.md",
        "docs/status_entries/WP110.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_candidate_review_operator_handoff_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_operator_runbook_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
        "tests/test_project_status_docs.py",
    ):
        assert path in text
    assert "Changed files (9):" in text
    for stale in (
        "WP110 on branch",
        "WP110 active branch",
        "TBD after merge",
        "PR: TBD",
        "count depends",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None
    assert "Ready for review: YES" in text


def test_project_status_records_wp110_without_runtime_activation() -> None:
    text = _read(PROJECT_STATUS)
    assert "WP110" in text
    assert "Hermes candidate-review local manual export operator runbook status" in text
    assert "DOCS_STATUS_TESTS_ONLY_LOCAL_MANUAL_EXPORT_OPERATOR_RUNBOOK_REVIEW_TARGET" in text
    for phrase in (
        "no Hermes install/connect/run",
        "no source implementation",
        "no CLI",
        "product/runtime network",
        "credential",
        "paper/live",
        "execution/risk",
        "scheduler",
        "dashboard",
        "bot-loop",
        "dependency",
        "lock-file",
    ):
        assert phrase in text


def test_repo_truth_index_registers_wp110_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_operator_runbook.md",
        "tests/test_hermes_candidate_review_local_manual_export_operator_runbook_docs.py",
        "docs/status_entries/WP110.md",
    ):
        assert path in text


def test_project_status_preserves_protected_boundaries() -> None:
    text = _read(PROJECT_STATUS)
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Agent runtime status: NOT_STARTED",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
    ):
        assert phrase in text
