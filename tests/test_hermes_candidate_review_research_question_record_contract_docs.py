"""Focused docs tests for WP120 research question record contract."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_research_question_record_contract.md"
STATUS_ENTRY = ROOT / "docs" / "status_entries" / "WP120.md"
PROJECT_STATUS = ROOT / "docs" / "project_status.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_contract_doc_exists() -> None:
    assert DOC.is_file()


def test_wp120_docs_status_tests_only_and_no_implementation_authority() -> None:
    text = _normalized(DOC)
    assert "WP120 is docs/status/tests-only" in text
    for phrase in (
        "authorizes no implementation",
        "parser",
        "writer",
        "schema",
        "storage",
        "runtime",
        "Hermes execution",
        "automation",
        "trading",
        "generated artifact",
    ):
        assert phrase in text


def test_wp118_intake_and_wp119_runbook_context_is_referenced() -> None:
    text = _normalized(DOC)
    assert "WP118 is the intake contract" in text
    assert "WP119 is the operator runbook" in text
    assert "after intake selection and before any manual Hermes prompt adaptation" in text
    assert "human-authored planning surface, not a runtime object or decision engine" in text


def test_conceptual_required_fields_are_listed() -> None:
    text = _read(DOC)
    for field in (
        "record_id",
        "source_wp_context",
        "selected_candidate_reference",
        "intake_basis",
        "research_question",
        "research_question_type",
        "evidence_references_to_check",
        "uncertainty_notes",
        "known_missing_data",
        "limitations",
        "falsification_checks_to_perform",
        "forbidden_interpretation_flags",
        "human_review_required",
        "next_manual_step",
        "created_by_operator_note",
        "non_authority_notice",
    ):
        assert f"`{field}`" in text


def test_field_concepts_are_not_implemented_as_schema_or_storage() -> None:
    text = _normalized(DOC)
    for phrase in (
        "contractual future field concepts only",
        "does not create a schema implementation",
        "dataclass",
        "parser",
        "writer",
        "loader",
        "storage path",
        "machine-readable record object",
        "do not define a storage location or serialization format",
    ):
        assert phrase in text


def test_allowed_research_question_types_are_listed() -> None:
    text = _normalized(DOC)
    for phrase in (
        "non-executing triage families",
        "resolution-rule ambiguity",
        "evidence quality gap",
        "source conflict",
        "wallet/signal uncertainty",
        "cross-market inconsistency",
        "market-structure/microstructure concern",
        "stale/missing data risk",
        "operator uncertainty requiring deeper research",
        "source-provenance weakness",
        "falsification-check need",
    ):
        assert phrase in text


def test_forbidden_research_question_types_are_listed() -> None:
    text = _normalized(DOC)
    for phrase in (
        "buy/sell/hold/short/trade/order/execute questions",
        "expected-return questions as trade instructions",
        "fair-value questions as trade instructions",
        "alpha/edge questions as trade instructions",
        "position sizing/allocation questions",
        "paper/live/deployment readiness questions",
        "execution/risk/order instructions",
        "PR approval or merge readiness questions",
        "credential/account/private-state access questions",
        "prompt-runner/runtime/model-provider instruction questions",
        "dashboard/scheduler/bot-loop instruction questions",
    ):
        assert phrase in text


def test_evidence_and_preflight_requirements_are_listed() -> None:
    text = _normalized(DOC)
    for phrase in (
        "upstream intake passed WP118",
        "source provenance explicit",
        "evidence references manually inspectable",
        "uncertainty, missing data, and limitations explicit",
        "no raw model/Hermes output treated as fact",
        "no credentials/private/account/order/paper/live/runtime data",
        "no generated artifact commit",
        "no trading/readiness/approval language",
    ):
        assert phrase in text


def test_human_review_requirement_is_explicit() -> None:
    text = _normalized(DOC)
    assert "Human review is required for every research question record" in text
    for phrase in (
        "cannot authorize implementation",
        "strategy promotion",
        "paper/live readiness",
        "execution",
        "risk changes",
        "PR approval",
        "merge readiness",
    ):
        assert phrase in text


def test_future_gates_require_separate_approved_wps() -> None:
    text = _normalized(DOC)
    assert "Separate approved WPs are required for" in text
    for phrase in (
        "concrete schema or dataclass implementation",
        "parser/loader",
        "writer/storage path",
        "validation receipt integration",
        "prompt template pack",
        "manual Hermes prompt adaptation guide",
        "advisory output validation receipt",
        "human decision/follow-up record format",
        "automation/report pipeline/dashboard",
        "Hermes runtime/provider/model/prompt execution",
        "paper/live/execution/risk/order/credentials/scheduler/dependency/workflow behavior",
        "committed generated artifacts",
    ):
        assert phrase in text


def test_status_fragment_has_exact_inventory_and_stable_wording() -> None:
    text = _read(STATUS_ENTRY)
    assert "Changed files (12):" in text
    for path in (
        "docs/hermes_candidate_review_research_question_record_contract.md",
        "tests/test_hermes_candidate_review_research_question_record_contract_docs.py",
        "docs/status_entries/WP120.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        "tests/test_project_status_docs.py",
        "tests/test_hermes_candidate_review_research_workflow_runbook_docs.py",
        "tests/test_hermes_candidate_review_research_workflow_intake_contract_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_chain_closeout_docs.py",
        "tests/test_hermes_candidate_review_local_manual_export_cli_operator_runbook_docs.py",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
        "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py",
    ):
        assert path in text
    for stale in (
        "WP120 on branch",
        "WP120 active branch",
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
    assert "WP121" in current_phase_line
    assert "WP119" in merged_line
    assert "WP120" in merged_line
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_WORKFLOW_RUNBOOK_MERGED" in text
    assert "DOCS_STATUS_TESTS_ONLY_RESEARCH_QUESTION_RECORD_CONTRACT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_RESEARCH_QUESTION_RECORD_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_ADVISORY_OUTPUT_VALIDATION_RECEIPT_MERGED" in text
    assert "LOCAL_OFFLINE_READ_ONLY_IN_MEMORY_HUMAN_DECISION_FOLLOW_UP_RECORD_REVIEW_TARGET" in text
    assert "docs/hermes_candidate_review_research_question_record_contract.md" in text
    assert "src/data_layer/hermes_candidate_review_research_question_record.py" in text
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


def test_repo_truth_index_registers_wp120_surfaces() -> None:
    text = _read(INDEX)
    for path in (
        "docs/hermes_candidate_review_research_question_record_contract.md",
        "tests/test_hermes_candidate_review_research_question_record_contract_docs.py",
        "docs/status_entries/WP120.md",
    ):
        assert path in text


def test_changed_file_inventory_excludes_forbidden_paths() -> None:
    text = _read(STATUS_ENTRY)
    inventory = text.split("Changed files (12):", 1)[1].split("Forbidden prefixes and files:", 1)[0]
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
