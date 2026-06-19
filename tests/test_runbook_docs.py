"""Focused docs tests for WP93 candidate review report operator runbook."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "runbooks" / "candidate_review_report_operator_runbook.md"
STATUS = ROOT / "docs" / "project_status.md"
REPO_TRUTH = ROOT / "docs" / "repo_truth_index.md"
DEFERRED = ROOT / "docs" / "deferred_items_log.md"
WP93_STATUS = ROOT / "docs" / "status_entries" / "WP93.md"


REQUIRED_SECTIONS = (
    "## 1. Purpose",
    "## 2. Scope and Non-Authority",
    "## 3. Prerequisites",
    "## 4. Local Input Fixtures",
    "## 5. Candidate Fixture Loading",
    "## 6. Candidate Review Report Generation",
    "## 7. Local Report Export",
    "## 8. Reading The Report Safely",
    "## 9. Validation Before Use",
    "## 10. Troubleshooting",
    "## 11. Known Limitations / Deferred Items",
    "## 12. Boundary Checklist",
    "## 13. Related Tests / Docs",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_candidate_review_report_runbook_exists() -> None:
    assert RUNBOOK.is_file()


def test_candidate_review_report_runbook_has_required_sections() -> None:
    text = _read(RUNBOOK)
    for section in REQUIRED_SECTIONS:
        assert section in text


def test_candidate_review_report_runbook_references_verified_import_surfaces() -> None:
    text = _read(RUNBOOK)
    required = (
        "CandidateFixtureLoadResult",
        "load_wallet_signal_paper_strategy_candidate_fixtures",
        "CandidateReviewReport",
        "build_wallet_signal_candidate_review_report",
        "candidate_review_report_to_dict",
        "render_wallet_signal_candidate_review_report",
        "CandidateReviewReportExportResult",
        "export_wallet_signal_candidate_review_report",
        "candidate_review_report_export_result_to_dict",
    )
    for token in required:
        assert token in text


def test_candidate_review_report_runbook_does_not_invent_cli() -> None:
    text = _read(RUNBOOK)
    forbidden = (
        "python -m tools.",
        "tools.some_new_cli",
        "candidate_review_report_cli",
        "--input",
        "--output",
    )
    for token in forbidden:
        assert token not in text
    assert "No CLI exists" in text
    assert "import-based only" in text


def test_candidate_review_report_runbook_includes_verified_validation_commands() -> None:
    text = _read(RUNBOOK)
    assert "python -m pytest tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py -v" in text
    assert "python -m pytest tests/test_wallet_signal_candidate_review_report.py -v" in text
    assert "python -m pytest tests/test_wallet_signal_candidate_review_report_export.py -v" in text


def test_candidate_review_report_runbook_safe_interpretation_language() -> None:
    text = _read(RUNBOOK).lower()
    required = (
        "local review aid only",
        "not trading advice",
        "not a signal",
        "not a recommendation",
        "does not authorize paper or live trading",
        "does not authorize order placement",
        "does not rank candidates for execution",
        "does not compute expected return",
        "position size",
        "does not use credentials or account access",
    )
    for phrase in required:
        assert phrase in text


def test_candidate_review_report_runbook_boundary_checklist_complete() -> None:
    text = _read(RUNBOOK)
    required = (
        "network/API used: NO",
        "credentials used: NO",
        "account/private endpoint access: NO",
        "order placement/cancel: NO",
        "paper/live/runtime touched: NO",
        "scheduler/dashboard/bot loop touched: NO",
        "strategy promotion authority: NO",
        "candidate ranking for execution: NO",
        "expected-return/position-size computation: NO",
    )
    for phrase in required:
        assert phrase in text


def test_candidate_review_report_runbook_path_safety_language() -> None:
    text = _read(RUNBOOK)
    assert "operator-selected local output directory" in text
    assert "Do not commit local export outputs" in text
    assert "Avoid committing local checkout paths" in text
    assert "drive-letter paths" in text
    assert "home paths" in text
    assert "temp paths" in text
    assert "C:\\" not in text
    assert "/Users/" not in text
    assert "/home/" not in text


def test_candidate_review_report_runbook_known_limitations_deferred_items() -> None:
    text = _read(RUNBOOK)
    assert "WP90-D001 remains open" in text
    assert "WP91-D001 and WP92-D001 remain open" in text
    assert "No CLI exists" in text
    assert "does not ingest wallet data from a network or API source" in text


def test_candidate_review_report_runbook_indexed_in_repo_truth() -> None:
    text = _read(REPO_TRUTH)
    assert "candidate_review_report_operator_runbook.md" in text
    assert "docs/status_entries/WP93.md" in text


def test_wp93_project_status_and_deferred_items_recorded() -> None:
    status = _read(STATUS)
    deferred = _read(DEFERRED)
    assert "WP93 - Candidate Review Report Operator Runbook V1" in status
    assert "DOCS_ONLY_OPERATOR_RUNBOOK_ON_BRANCH" in status
    assert "WP93 Candidate Review Report Operator Runbook V1 Deferred Items" in deferred
    assert "WP93 resolves no deferred implementation item" in deferred


def test_wp93_status_fragment_exists_and_is_non_self_referential() -> None:
    text = _read(WP93_STATUS)
    assert "WP ID: WP93" in text
    assert "Current live PR head: see GitHub PR metadata and PR body" in text
    assert "stable and non-self-referential" in text
    assert "Ready for review:" in text
