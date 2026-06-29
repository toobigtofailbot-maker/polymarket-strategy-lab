"""Focused docs tests for the WP107 Hermes candidate-review handoff local
manual export contract.

WP107 is docs/status/tests-only. No exporter or writer is implemented.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_handoff_local_manual_export_contract.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP107.md"
WP106_STATUS = ROOT / "docs" / "status_entries" / "WP106.md"


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
    assert match, f"Missing section: {title!r}"
    return match.group("body")


# ── Requirement 1: Contract document exists ──────────────────────────────────


def test_contract_doc_exists() -> None:
    assert DOC.is_file(), f"Missing: {DOC}"


# ── Requirement 2: States WP107 is docs/status/tests-only ────────────────────


def test_contract_states_wp107_is_docs_status_tests_only() -> None:
    text = _doc()
    assert "docs/status/tests-only" in text
    assert "WP107" in text


# ── Requirement 3: States no exporter/writer implemented in WP107 ────────────


def test_contract_states_no_exporter_writer_implemented_in_wp107() -> None:
    text = _normalized(_doc())
    assert "No exporter or writer is implemented in WP107" in text or \
        "no exporter or writer is implemented in wp107" in text.lower()


# ── Requirement 4: References WP105 and WP106 ────────────────────────────────


def test_contract_references_wp105_and_wp106() -> None:
    text = _doc()
    assert "WP105" in text
    assert "WP106" in text
    section = _section(text, "Relationship To WP105/WP106")
    assert "WP105" in section
    assert "WP106" in section


# ── Requirement 5: Future exporters must use valid WP106 handoff output ───────


def test_contract_requires_valid_wp106_handoff_output() -> None:
    text = _doc()
    assert "valid WP106 handoff" in text or "valid WP106 handoff output" in text
    section = _normalized(_section(text, "Permitted Future Inputs"))
    assert "valid WP106 handoff result" in section
    assert "must not operate on arbitrary raw model output" in section or \
        "must not accept" in section or \
        "arbitrary" in section


# ── Requirement 6: Requires local/offline/manual scope ───────────────────────


def test_contract_requires_local_offline_manual_scope() -> None:
    text = _doc()
    assert "local" in text.lower()
    assert "offline" in text.lower()
    assert "manual" in text.lower()
    section = _section(text, "Title and Scope")
    assert "local" in section.lower()
    assert "manual" in section.lower()
    gate = _section(text, "Future Implementation Gate")
    assert "local, offline, and manual only" in gate


# ── Requirement 7: Requires fail-closed behavior ─────────────────────────────


def test_contract_requires_fail_closed_behavior() -> None:
    text = _doc()
    assert "fail closed" in text.lower() or "fail-closed" in text.lower()
    section = _section(text, "Validation Expectations For Future Source Implementation")
    assert "fail closed" in section.lower() or "fail-closed" in section.lower()
    assert "Invalid" in section or "invalid" in section


# ── Requirement 8: Requires no unsafe echo ───────────────────────────────────


def test_contract_requires_no_unsafe_echo() -> None:
    text = _doc()
    assert "No-unsafe-echo" in text or "no unsafe echo" in text.lower() or \
        "must not echo unsafe" in text.lower()
    section = _section(text, "No Unsafe Echo Policy")
    assert "must never echo unsafe caller input" in section or \
        "must not echo unsafe content" in section or \
        "never echo" in section.lower()
    assert "neutral codes" in section.lower() or "neutral code" in section.lower()


# ── Requirement 9: Rejects raw/free-form metadata and arbitrary blobs ─────────


def test_contract_rejects_raw_free_form_metadata() -> None:
    text = _doc()
    assert "raw" in text.lower() and "free-form" in text.lower() or \
        "free_form" in text.lower()
    section = _section(text, "Raw Metadata / Free-Form Data Policy")
    assert "raw" in section.lower()
    assert "free-form" in section.lower() or "free_form" in section.lower()
    assert "must not serialize" in section.lower() or \
        "must not" in section.lower()
    assert "reject" in section.lower() or "excluded" in section.lower()


# ── Requirement 10: Lists all required future artifact conceptual groups ──────


def test_contract_lists_all_required_artifact_conceptual_groups() -> None:
    text = _doc()
    for group in (
        "artifact_identity",
        "source_handoff_identity",
        "chain_stage_summary",
        "manual_review_summary",
        "evidence_and_provenance_summary",
        "staleness_and_missing_data_summary",
        "uncertainty_and_limitations_summary",
        "falsification_summary",
        "human_decision_record_summary",
        "next_manual_research_step",
        "safety_flags",
        "forbidden_scope_notice",
    ):
        assert group in text, f"Missing conceptual group: {group!r}"


# ── Requirement 11: Lists all required safety flags ──────────────────────────


def test_contract_lists_all_required_safety_flags() -> None:
    text = _doc()
    for flag in (
        "advisory_only",
        "human_review_required",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "no_prompt_execution",
        "no_file_or_network_beyond_explicit_local_manual_export",
        "no_strategy_promotion_authority",
        "no_pr_approval_authority",
        "no_trade_signal",
        "no_position_sizing",
        "no_expected_return",
    ):
        assert flag in text, f"Missing safety flag: {flag!r}"


# ── Requirement 12: Lists all allowed decision labels ─────────────────────────


def test_contract_lists_all_allowed_decision_labels() -> None:
    text = _doc()
    for label in (
        "ACCEPT_FOR_MANUAL_RESEARCH_REVIEW",
        "REJECT_FOR_INSUFFICIENT_EVIDENCE",
        "REJECT_FOR_STALE_OR_MISSING_DATA",
        "REJECT_FOR_RESOLUTION_AMBIGUITY",
        "REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT",
        "NEEDS_SOURCE_RECHECK",
        "NEEDS_DETERMINISTIC_VALIDATION",
        "DEFER_PENDING_MORE_CONTEXT",
    ):
        assert label in text, f"Missing decision label: {label!r}"


# ── Requirement 13: Lists forbidden output wording families ──────────────────


def test_contract_lists_forbidden_output_wording_families() -> None:
    text = _doc()
    section = _section(text, "Forbidden Output Wording Matrix")
    assert "explicitly marked forbidden matrix" in section
    for token in (
        "buy",
        "sell",
        "order",
        "trade",
        "execute",
        "position",
        "expected return",
        "edge",
        "alpha",
        "fair value",
        "live ready",
        "paper ready",
        "approve PR",
        "merge ready",
        "credential",
        "private key",
        "API key",
        "secret",
        "passphrase",
        "wallet",
        "provider",
        "model call",
        "prompt execution",
        "prompt runner",
        "Hermes runtime",
        "scheduler",
        "bot loop",
    ):
        assert token.lower() in section.lower(), \
            f"Missing forbidden token: {token!r}"


# ── Requirement 14: Future file/export/report writer/CLI requires separate WP ─


def test_contract_states_future_file_writer_requires_separate_approved_wp() -> None:
    text = _doc()
    assert "separately approved" in text.lower() or "separate approved" in text.lower()
    gate = _section(text, "Future Implementation Gate")
    assert "separately approved" in gate.lower() or "separate approved" in gate.lower()
    assert "file writer" in gate.lower() or "file write" in gate.lower() or \
        "file writer" in text.lower()
    assert "cli" in gate.lower()


# ── Requirement 15: Forbids Hermes runtime, prompt execution, etc. ────────────


def test_contract_forbids_hermes_runtime_prompt_execution_and_related() -> None:
    text = _doc()
    scope = _section(text, "Title and Scope")
    for phrase in (
        "Hermes",
        "prompt execution",
        "provider",
        "network",
        "credentials",
        "paper",
        "live",
        "scheduler",
        "dashboard",
        "bot-loop",
        "dependency",
        "workflow",
    ):
        assert phrase.lower() in scope.lower(), \
            f"Missing forbidden authority phrase in scope: {phrase!r}"


def test_contract_no_implementation_authority_stated() -> None:
    text = _doc()
    normalized = _normalized(text)
    assert "No exporter" in text or "no exporter" in text.lower()
    assert "not implemented" in text.lower() or "not yet implemented" in text.lower()
    assert "does not authorize" in text.lower()


# ── Requirement 16: Project status records WP107 and preserves boundaries ─────


def test_project_status_records_wp107_and_preserves_protected_boundary_phrases() -> None:
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP107" in merged_line
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP107", "WP108", "WP109"))
    assert "Hermes candidate-review handoff local manual export contract status" in text
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
    ):
        assert phrase in text, f"Missing boundary phrase: {phrase!r}"


# ── Requirement 17: Repo truth index registers new contract doc/test/fragment ─


def test_repo_truth_index_registers_wp107_contract_test_and_status_fragment() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_handoff_local_manual_export_contract.md",
        "tests/test_hermes_candidate_review_handoff_local_manual_export_contract_docs.py",
        "docs/status_entries/WP107.md",
    ):
        assert path in text, f"Missing from repo truth index: {path!r}"


# ── Requirement 18: WP107 status entry exists and lists exact changed files ───


def test_wp107_status_entry_exists() -> None:
    assert STATUS_ENTRY.is_file(), f"Missing: {STATUS_ENTRY}"


def test_wp107_status_entry_lists_exact_changed_file_inventory() -> None:
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_handoff_local_manual_export_contract.md",
        "tests/test_hermes_candidate_review_handoff_local_manual_export_contract_docs.py",
        "docs/status_entries/WP107.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
    ):
        assert path in text, f"Missing from WP107 status entry: {path!r}"


# ── Requirement 19: No dynamic stale wording in WP107 status entry ───────────


def test_wp107_status_entry_contains_no_dynamic_stale_wording() -> None:
    text = _read(STATUS_ENTRY)
    for stale_phrase in (
        "count depends",
        "TBD after merge",
        "active branch",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert stale_phrase not in text, \
            f"Stale wording found in WP107 status entry: {stale_phrase!r}"
    assert "Ready for review: YES" in text
    assert "stable and non-self-referential" in text
    fixed_sha = re.compile(
        r"Current live PR head:\s*`?[0-9a-f]{40}`?", re.IGNORECASE
    )
    assert fixed_sha.search(text) is None, \
        "WP107 status entry must not commit a fixed live PR head SHA"


# ── Requirement 20: No src/ implementation file added by WP107 ───────────────


def test_no_src_implementation_file_added_by_wp107() -> None:
    import pathlib
    src_dir = ROOT / "src"
    wp107_mentioned_src_files = [
        "hermes_candidate_review_handoff_local_manual_export.py",
        "hermes_handoff_local_manual_export.py",
        "hermes_handoff_export.py",
    ]
    for filename in wp107_mentioned_src_files:
        for src_file in src_dir.rglob(filename):
            assert False, f"WP107 must not add src implementation: {src_file}"


def test_wp107_status_entry_authority_posture_is_docs_status_tests_only() -> None:
    text = _read(STATUS_ENTRY)
    assert "docs/status/tests-only" in text.lower() or \
        "docs/status/tests-only future local manual export contract" in text.lower() or \
        "Package class: docs/status/tests-only" in text
    assert "Implementation authority: NO" in text
    assert "Source implementation authority: NO" in text
    assert "Report/export authority: NO" in text
    assert "CLI authority: NO" in text
    assert "Network authority: NO" in text
    assert "Hermes runtime" in text and "NO" in text
    assert "File writer" in text or "file writer" in text.lower()
