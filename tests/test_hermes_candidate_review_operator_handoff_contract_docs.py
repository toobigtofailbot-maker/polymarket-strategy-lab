"""Focused docs tests for the WP105 Hermes operator handoff contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_operator_handoff_contract.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP105.md"


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


def test_canonical_doc_exists() -> None:
    assert DOC.is_file()


def test_doc_references_wp99_through_wp104_chain_accurately() -> None:
    text = _doc()
    for wp in ("WP99", "WP100", "WP101", "WP102", "WP103", "WP104"):
        assert wp in text
    relationship = _section(text, "Relationship to WP99-WP104")
    assert "WP103 candidate-review context packet" in relationship
    assert "-> WP101 dry-run receipt" in relationship
    assert "-> WP102 manual operator review" in relationship
    assert "-> WP104 chain smoke" in relationship


def test_doc_states_advisory_only_and_human_review_required() -> None:
    text = _doc()
    normalized = _normalized(text)
    assert "advisory_only" in text
    assert "human_review_required" in text
    assert "advisory research workflow contract only" in normalized


def test_doc_states_all_required_no_authority_boundaries() -> None:
    text = _doc()
    for phrase in (
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "no_prompt_execution",
        "no_file_or_network",
    ):
        assert phrase in text
    purpose = _section(text, "Purpose")
    for phrase in (
        "no trade",
        "order",
        "live",
        "paper",
        "risk",
        "credential",
        "runtime",
        "scheduler",
        "dashboard",
        "prompt execution authority",
    ):
        assert phrase in purpose


def test_doc_contains_all_required_conceptual_handoff_groups() -> None:
    text = _doc()
    for group in (
        "handoff_identity",
        "source_chain_summary",
        "packet_stage_summary",
        "receipt_stage_summary",
        "operator_review_stage_summary",
        "source_review_checklist",
        "evidence_and_provenance",
        "staleness_and_missing_data",
        "uncertainty_and_limitations",
        "falsification_checks",
        "human_decision_record",
        "next_research_step",
        "safety_flags",
        "rejection_reasons",
    ):
        assert group in text


def test_doc_contains_all_allowed_operator_decision_labels() -> None:
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
        assert label in text
    assert "research workflow labels only" in text
    assert "not trading recommendations" in _normalized(text)


def test_doc_contains_forbidden_interpretation_section() -> None:
    section = _section(_doc(), "Forbidden Interpretation")
    for phrase in (
        "buy/sell/order instruction",
        "trade signal",
        "expected-return estimate",
        "fair-value estimate",
        "edge score",
        "confidence-to-trade score",
        "position-sizing advice",
        "paper/live approval",
        "strategy promotion",
        "risk override",
        "PR approval or merge-readiness claim",
        "permission for Hermes to run or execute prompts",
        "permission to access credentials/private endpoints/account data",
    ):
        assert phrase in section


def test_doc_contains_forbidden_output_wording_matrix() -> None:
    section = _section(_doc(), "Forbidden Output / Wording Matrix")
    assert "explicitly marked forbidden matrix" in section
    for token in (
        "buy",
        "sell",
        "order",
        "trade",
        "execute",
        "position",
        "position_size",
        "entry",
        "exit",
        "stop_loss",
        "take_profit",
        "expected_return",
        "edge",
        "alpha",
        "fair_value",
        "live_ready",
        "paper_ready",
        "approve_pr",
        "merge_ready",
        "credential",
        "private_key",
        "api_key",
        "secret",
        "passphrase",
        "wallet",
        "provider",
        "model call",
        "prompt execution",
    ):
        assert token in section


def test_doc_contains_raw_metadata_free_form_policy() -> None:
    section = _section(_doc(), "Raw Metadata / Free-Form Mapping Policy")
    assert "must not include raw/free-form metadata blobs" in section
    assert "recursively scan keys and values" in section


def test_doc_contains_no_unsafe_echo_policy() -> None:
    text = _normalized(_doc())
    assert "Unsafe caller-provided input must not be echoed" in text
    assert "No-unsafe-echo is a hard requirement" in text
    assert "neutral codes" in text


def test_doc_contains_fail_closed_policy() -> None:
    section = _section(_doc(), "Fail-Closed Policy")
    assert "Missing required conceptual groups" in section
    assert "must make a future handoff invalid" in section
    assert "Invalid handoffs must be empty or neutral" in section
    assert "must not echo unsafe content" in section


def test_doc_contains_future_implementation_gating_rules() -> None:
    section = _normalized(_section(_doc(), "Future Implementation Guidance"))
    for phrase in (
        "in-memory handoff object only after this contract is merged",
        "separate future WP is required for any file export/report writer",
        "separate future WP is required for any CLI",
        "separate future WP is required for any network/API/product behavior",
        "separate future WP is required for any Hermes runtime/model/provider/prompt execution",
        "No future WP may use this contract to authorize paper/live/execution/risk or credentials",
    ):
        assert phrase in section


def test_live_paper_merge_ready_and_approve_pr_are_only_in_allowed_sections() -> None:
    text = _doc()
    allowed_sections = (
        _section(text, "Forbidden Interpretation")
        + _section(text, "Forbidden Output / Wording Matrix")
    )
    text_without_allowed = text.replace(_section(text, "Forbidden Interpretation"), "")
    text_without_allowed = text_without_allowed.replace(
        _section(text, "Forbidden Output / Wording Matrix"), ""
    )
    for phrase in ("live ready", "paper ready", "merge ready", "approve PR"):
        assert phrase.lower() not in text_without_allowed.lower()
    for phrase in ("live_ready", "paper_ready", "merge_ready", "approve_pr"):
        assert phrase in allowed_sections


def test_doc_does_not_describe_current_runtime_or_export_surfaces() -> None:
    text = _doc().lower()
    forbidden_current_claims = (
        "there is a current cli",
        "currently provides a cli",
        "there is a current report writer",
        "currently provides a report writer",
        "there is a current file export",
        "currently provides file export",
        "there is a current scheduler",
        "currently provides a scheduler",
        "there is a current hermes runtime",
        "currently provides hermes runtime",
        "there is a current prompt runner",
        "currently provides a prompt runner",
        "there is a current network poller",
        "currently provides a network poller",
        "there is a current paper engine",
        "currently provides a paper engine",
        "there is a current live trading path",
        "currently provides a live trading path",
        "there is current credential use",
        "currently uses credentials",
        "there is a current execution path",
        "currently provides an execution path",
    )
    for phrase in forbidden_current_claims:
        assert phrase not in text


def test_repo_truth_index_registers_new_doc_test_and_status_entry() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_operator_handoff_contract.md",
        "tests/test_hermes_candidate_review_operator_handoff_contract_docs.py",
        "docs/status_entries/WP105.md",
    ):
        assert path in text


def test_project_status_records_wp105_and_preserves_boundaries() -> None:
    text = _read(PROJECT_STATUS)
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP105" in merged_line
    assert "Post-WP105 Hermes candidate-review operator handoff contract V1 lock-in" in text
    assert "Hermes candidate-review operator handoff contract status" in text
    for phrase in (
        "Live trading status: DISABLED",
        "Credentials status: NOT_USED",
        "Execution status: NOT_STARTED",
        "Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "Scheduler status: NOT_STARTED",
        "Bot loop status: NOT_STARTED",
        "Agent execution authority: FORBIDDEN",
    ):
        assert phrase in text


def test_wp105_status_entry_exists_and_lists_exact_changed_files() -> None:
    assert STATUS_ENTRY.is_file()
    text = _read(STATUS_ENTRY)
    for path in (
        "docs/hermes_candidate_review_operator_handoff_contract.md",
        "tests/test_hermes_candidate_review_operator_handoff_contract_docs.py",
        "docs/status_entries/WP105.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
    ):
        assert path in text
    assert "Package size class: L (8 changed files" in text
    for stale in (
        "count depends",
        "TBD",
        "WP105 on branch",
        "WP105 active branch",
        "Head commit:",
        "LOCAL_DRAFT_VERIFIED",
    ):
        assert stale not in text
    assert "Ready for review: YES" in text
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "stable and non-self-referential" in text
