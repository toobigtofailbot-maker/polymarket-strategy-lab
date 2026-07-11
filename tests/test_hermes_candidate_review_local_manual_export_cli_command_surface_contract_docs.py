"""Focused docs tests for the WP114 CLI command-surface contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_local_manual_export_cli_command_surface_contract.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP114.md"
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


def test_contract_states_wp114_docs_status_tests_only_and_no_implementation_authority() -> None:
    text = _normalized(_doc()).lower()
    assert "wp114 defines only the future cli command surface" in text
    assert "wp114 does not implement a cli" in text
    assert "wp114 does not authorize implementation" in text
    assert "docs/status/tests-only" in text
    for phrase in (
        "source implementation",
        "tools implementation",
        "cli implementation",
        "command parser",
        "command runner",
        "shell wrapper",
        "json parser implementation",
    ):
        assert phrase in text


def test_contract_references_chain_order_and_wp107_contract_layer() -> None:
    text = _normalized(_doc())
    assert "WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113" in text
    assert "WP107 remains the contract layer" in text
    assert "WP113 established the high-level future CLI-wrapper contract" in text


def test_future_command_surface_has_one_artifact_json_output_and_optional_overwrite() -> None:
    text = _normalized(_section(_doc(), "Future CLI Command Surface"))
    assert "python -m tools.hermes_candidate_review_manual_export_cli" in text
    assert "--artifact-json <local_path_to_strict_wp108_artifact_result_snapshot.json>" in text
    assert "--output <explicit_local_output_path.md_or_txt>" in text
    assert "[--overwrite]" in text
    assert "Exactly one input artifact path argument: `--artifact-json`" in text
    assert "Exactly one explicit output path argument: `--output`" in text
    assert "Optional overwrite flag only: `--overwrite`, default false" in text


def test_future_command_surface_forbids_unsafe_modes_and_options() -> None:
    text = _normalized(_section(_doc(), "Future CLI Command Surface")).lower()
    for phrase in (
        "no auto path selection",
        "no directory creation",
        "no batch mode",
        "no watch mode",
        "no scheduler mode",
        "no daemon mode",
        "no network option",
        "no model option",
        "no provider option",
        "no hermes option",
        "no credentials option",
        "no paper option",
        "no live option",
        "no order option",
        "no dashboard option",
        "no config-mutation option",
        "no stdin artifact-content mode",
        "no stdout artifact-content mode",
    ):
        assert phrase in text


def test_future_input_envelope_requires_strict_wp108_snapshot_fields() -> None:
    text = _normalized(_section(_doc(), "Future Input Handoff Envelope"))
    for phrase in (
        "already-built WP108 artifact-result snapshot",
        "HERMES_CANDIDATE_REVIEW_MANUAL_EXPORT_ARTIFACT_RESULT_V1",
        '"source_wp": "WP108"',
        '"source_contract": "WP107"',
        "allowed deterministic WP108 artifact builder identifier",
        '"is_valid": true',
        "object with exactly the required WP108 artifact groups",
        '"errors": []',
        "list of neutral codes only",
        "all required WP108/WP109 safety flags true",
        "local/manual/offline/synthetic-or-reviewed status only",
        '"human_review_required": true',
    ):
        assert phrase in text


def test_future_input_envelope_failure_conditions_are_fail_closed() -> None:
    text = _normalized(_section(_doc(), "Future Input Handoff Envelope")).lower()
    for phrase in (
        "fail closed",
        "missing",
        "malformed",
        "stale",
        "extra raw/free-form metadata",
        "forbidden terms",
        "is_valid` not true",
        "missing required artifact groups",
        "missing or false safety flags",
        "raw model or hermes output",
    ):
        assert phrase in text


def test_future_input_rejection_rules_include_required_families() -> None:
    text = _normalized(_section(_doc(), "Future Input Rejection Rules")).lower()
    for phrase in (
        "raw model output",
        "raw hermes response",
        "arbitrary caller dictionaries",
        "raw/free-form metadata",
        "credentials",
        "api keys",
        "private state",
        "account state",
        "wallet identifiers",
        "order state",
        "paper state",
        "live state",
        "runtime logs",
        "prompt-runner output",
        "strategy recommendation text",
        "trade signal text",
        "expected-return text",
        "position-sizing text",
        "pr approval text",
        "merge-readiness text",
        "unsafe path-like values",
        "uri-like values",
    ):
        assert phrase in text


def test_future_output_behavior_requires_local_paths_and_no_artifact_echo() -> None:
    text = _normalized(_section(_doc(), "Future Output Behavior")).lower()
    for phrase in (
        "existing wp109 writer",
        "explicit local `.md` or `.txt` path only",
        "parent directory must already exist",
        "no parent-directory creation",
        "no automatic path selection",
        "no committed generated artifacts",
        "no write under `docs/`, `src/`, `tests/`, `tools/`, `.github/`, or `local_data/`",
        "no artifact contents printed to stdout",
        "no artifact contents printed to stderr",
        "status, output path, bytes_written, sha256",
        "must never echo unsafe input",
    ):
        assert phrase in text


def test_future_exit_code_policy_includes_required_codes_and_meanings() -> None:
    text = _normalized(_section(_doc(), "Future Exit-Code Policy"))
    for phrase in (
        "| 0 | Success, valid artifact written. |",
        "| 2 | Input/envelope validation failed. |",
        "| 3 | Path/output validation failed. |",
        "| 4 | Protected-boundary refusal. |",
        "| 5 | Unexpected internal error, sanitized and no unsafe echo. |",
    ):
        assert phrase in text


def test_future_failure_behavior_is_fail_closed_and_no_output_on_invalid_input() -> None:
    text = _normalized(_section(_doc(), "Future Failure Behavior")).lower()
    assert "must fail closed" in text
    assert "must create no output file on invalid input" in text
    assert "must not overwrite unless `--overwrite` is explicitly supplied" in text
    for phrase in (
        "must not weaken validation",
        "bypass wp108/wp109",
        "manually edit artifacts",
        "infer trading meaning",
    ):
        assert phrase in text


def test_future_negative_test_matrix_includes_required_cases() -> None:
    text = _normalized(_section(_doc(), "Future Negative-Test Matrix")).lower()
    for phrase in (
        "valid strict envelope writes to `tmp_path` only",
        "invalid envelope fails closed",
        "missing required artifact group fails closed",
        "missing safety flag fails closed",
        "false safety flag fails closed",
        "raw metadata key fails closed at any nesting depth",
        "raw model output fails closed",
        "raw hermes output fails closed",
        "forbidden wording family fails closed",
        "uri-like input path fails closed",
        "uri-like output path fails closed",
        "parent directory missing fails closed",
        "existing output path without `--overwrite` fails closed",
        "`--overwrite` true overwrites only explicit local path",
        "no unsafe echo in stdout, stderr, errors, or warnings",
        "stdout does not contain artifact content",
        "stderr does not contain artifact content",
        "no writes under tracked repo paths",
        "no generated artifacts committed",
        "no network, requests, or socket imports",
        "no hermes, model, or provider imports",
        "no credentials, account, paper, live, execution, risk, order, scheduler",
        "exact changed-file inventory/status tests",
    ):
        assert phrase in text


def test_forbidden_variant_matrix_contains_required_rejected_families() -> None:
    text = _normalized(_section(_doc(), "Future Negative-Test Matrix")).lower()
    for phrase in (
        "buy, sell, trade, order, execute, entry, and exit",
        "expected return, fair value, alpha, and edge as a trade instruction",
        "position size, sizing, and allocation",
        "paper ready, live ready, and deployment ready",
        "pr approval and merge readiness",
        "credentials, api key, private key, and wallet secret",
        "hermes runtime, model provider, and prompt runner",
        "network, api, account, and product behavior",
        "scheduler, daemon, and bot loop",
        "dashboard, workflow, and dependency changes",
        "generated artifacts committed",
    ):
        assert phrase in text


def test_human_review_remains_required() -> None:
    text = _normalized(_section(_doc(), "Human Review Requirement")).lower()
    assert "manual review aid only" in text
    assert "requires human review" in text


def test_wp114_status_entry_exact_inventory_and_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_command_surface_contract.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py",
        "docs/status_entries/WP114.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_wrapper_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_chain_closeout_docs.py",
    ):
        assert path in text
    assert "Changed files (8):" in text
    for stale in (
        "WP114 on branch",
        "WP114 active branch",
        "TBD",
        "PR: TBD",
        "count depends",
        "LOCAL_DRAFT_VERIFIED",
        "Head commit:",
    ):
        assert stale not in text
    fixed_live_head = re.compile(r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE)
    assert fixed_live_head.search(text) is None


def test_project_status_records_wp114_and_preserves_protected_boundaries() -> None:
    text = _read(PROJECT_STATUS)
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert any(wp in current_phase_line for wp in ("WP114", "WP115", "WP116", "WP117", "WP125", "WP128"))
    assert "WP113" in merged_line
    assert "WP114" in merged_line
    assert "Hermes candidate-review local manual export CLI command surface contract status" in text
    assert "DOCS_STATUS_TESTS_ONLY_CLI_COMMAND_SURFACE_CONTRACT_MERGED" in text
    assert "Hermes candidate-review local manual export CLI wrapper implementation status" in text
    assert (
        "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_REVIEW_TARGET" in text
        or "LOCAL_OFFLINE_MANUAL_CLI_WRAPPER_MERGED" in text
    )
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


def test_repo_truth_index_registers_wp114_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_local_manual_export_cli_command_surface_contract.md",
        "tests/test_hermes_candidate_review_local_manual_export_cli_command_surface_contract_docs.py",
        "docs/status_entries/WP114.md",
    ):
        assert path in text


def test_status_inventory_adds_no_src_or_tools_file() -> None:
    status = _read(STATUS_ENTRY)
    inventory = status.split("Forbidden prefixes and files:")[0]
    changed_lines = "\n".join(
        line for line in inventory.splitlines() if line.startswith("- `")
    )
    assert "`src/" not in changed_lines
    assert "`tools/" not in changed_lines
