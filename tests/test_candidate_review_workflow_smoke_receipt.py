"""Focused smoke tests for WP94 candidate review workflow receipt."""

from __future__ import annotations

import json
from pathlib import Path

from src.data_layer.wallet_signal_candidate_review_report import (
    build_wallet_signal_candidate_review_report,
    candidate_review_report_to_dict,
    render_wallet_signal_candidate_review_report,
)
from src.data_layer.wallet_signal_candidate_review_report_export import (
    EXPORT_STATUS_EXPORT_WRITTEN,
    FORMAT_JSON,
    FORMAT_MARKDOWN,
    WRITE_STATUS_WRITTEN,
    candidate_review_report_export_result_to_dict,
    export_wallet_signal_candidate_review_report,
)
from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    load_wallet_signal_paper_strategy_candidate_fixtures,
)


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "runbooks" / "candidate_review_report_operator_runbook.md"
SMOKE_RECEIPT = ROOT / "docs" / "runbooks" / "candidate_review_workflow_local_smoke_receipt.md"
STATUS_README = ROOT / "docs" / "status_entries" / "README.md"
WP94_STATUS = ROOT / "docs" / "status_entries" / "WP94.md"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "wallet_signal_paper_strategy_candidates"

FORBIDDEN_VARIANTS: tuple[str, ...] = (
    "buy",
    "sell",
    "trade",
    "trading",
    "execute",
    "execution",
    "order",
    "order_ready",
    "execution_ready",
    "entry",
    "exit",
    "position_size",
    "position sizing",
    "position-size",
    "expected_return",
    "expected return",
    "expected-return",
    "profit_target",
    "profit target",
    "stop_loss",
    "stop loss",
    "take_profit",
    "take profit",
    "live_signal",
    "live signal",
    "auto_copy",
    "auto copy",
    "copy signal",
    "wallet copy instruction",
    "pnl_target",
    "pnl target",
    "paper_trading_candidate",
    "paper trading candidate",
    "strategy_signal",
    "strategy signal",
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "EXECUTION_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "AUTO_APPROVED",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _recursive_strings(obj: object, include_keys: bool = True) -> list[str]:
    if isinstance(obj, dict):
        strings: list[str] = []
        for key, value in obj.items():
            if include_keys:
                strings.append(str(key))
            strings.extend(_recursive_strings(value, include_keys=include_keys))
        return strings
    if isinstance(obj, (list, tuple)):
        strings = []
        for value in obj:
            strings.extend(_recursive_strings(value, include_keys=include_keys))
        return strings
    if isinstance(obj, str):
        return [obj]
    return []


def _scan_for_forbidden_variants(obj: object, include_keys: bool = True) -> list[str]:
    violations: list[str] = []
    for text in _recursive_strings(obj, include_keys=include_keys):
        normalized = text.lower().replace("_", " ").replace("-", " ")
        for term in FORBIDDEN_VARIANTS:
            normalized_term = term.lower().replace("_", " ").replace("-", " ")
            if normalized_term in normalized:
                violations.append(f"{term!r} in {text!r}")
                break
    return violations


def test_smoke_receipt_doc_exists_and_has_required_sections() -> None:
    text = _read(SMOKE_RECEIPT)
    required = (
        "## 1. Purpose",
        "## 2. Verified Repo Surfaces",
        "## 3. Local Smoke Path",
        "## 4. What Was Exercised",
        "## 5. What Was Not Exercised",
        "## 6. Non-Authority / Safety Notes",
        "## 7. Validation Commands",
        "## 8. Stable Status Fragment Policy Compliance",
        "## 9. Known Limitations / Deferred Items",
        "## 10. Next WP Suggestion",
    )
    for section in required:
        assert section in text


def test_smoke_receipt_uses_verified_import_surfaces_only() -> None:
    text = _read(SMOKE_RECEIPT)
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
    forbidden = (
        "candidate_review_report_cli",
        "python -m tools.",
        "tools.some_new_cli",
        "--input",
        "--output",
    )
    for token in forbidden:
        assert token not in text
    assert "No CLI is introduced by this WP." in text
    assert "existing import surfaces only" in text


def test_runbook_and_smoke_receipt_agree_on_import_only_no_cli_posture() -> None:
    runbook = _read(RUNBOOK)
    receipt = _read(SMOKE_RECEIPT)
    assert "No CLI exists" in runbook
    assert "import-based only" in runbook
    assert "No CLI is introduced by this WP." in receipt
    assert "import-only" in receipt


def test_smoke_receipt_non_authority_and_boundary_language() -> None:
    text = _read(SMOKE_RECEIPT).lower()
    required = (
        "local/offline",
        "not trading advice",
        "not a signal",
        "not a recommendation",
        "does not authorize paper or live trading",
        "does not authorize order placement",
        "strategy promotion",
        "candidate ranking for execution",
        "expected-return computation",
        "position-size computation",
        "network/api behavior",
        "credentials",
        "scheduler",
        "dashboard",
        "bot-loop",
    )
    for phrase in required:
        assert phrase in text


def test_smoke_receipt_references_stable_status_fragment_policy() -> None:
    text = _read(SMOKE_RECEIPT)
    status_readme = _read(STATUS_README)
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "Current live PR head: see GitHub PR metadata and PR body." in text
    assert "stable status-fragment policy" in text.lower()
    assert "PR: see GitHub PR metadata and PR body." in status_readme


def test_wp94_status_fragment_is_stable_only() -> None:
    text = _read(WP94_STATUS)
    assert "WP ID: WP94" in text
    assert "PR: see GitHub PR metadata and PR body." in text
    assert "Current live PR head: see GitHub PR metadata and PR body" in text
    assert "stable and non-self-referential" in text
    assert "PR: TBD" not in text
    assert "Guard input source: LOCAL_DRAFT_VERIFIED" not in text
    assert "Head commit:" not in text


def test_candidate_review_workflow_exercises_existing_apis_to_temp_export(
    tmp_path: Path,
) -> None:
    load_result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    assert load_result.total_files == 4
    assert load_result.valid_records == 1
    assert load_result.invalid_records == 2
    assert load_result.malformed_files == 1

    report = build_wallet_signal_candidate_review_report(load_result)
    assert report.summary.total_items == len(load_result.items)
    assert report.summary.valid_records == load_result.valid_records
    assert report.summary.invalid_records == load_result.invalid_records
    assert report.summary.malformed_files == load_result.malformed_files
    assert report.report_markdown == render_wallet_signal_candidate_review_report(report)
    assert candidate_review_report_to_dict(report)["summary"]["total_items"] == 4

    output_dir = tmp_path / "candidate_review_smoke_output"
    export_result = export_wallet_signal_candidate_review_report(
        report,
        output_dir,
        formats=(FORMAT_MARKDOWN, FORMAT_JSON),
    )
    export_dict = candidate_review_report_export_result_to_dict(export_result)

    assert export_result.export_status == EXPORT_STATUS_EXPORT_WRITTEN
    assert Path(export_result.output_directory).resolve() == output_dir.resolve()
    assert export_dict["export_status"] == EXPORT_STATUS_EXPORT_WRITTEN
    assert {file.relative_path for file in export_result.files} == {
        "candidate_review_report.md",
        "candidate_review_report.json",
    }
    assert all(file.write_status == WRITE_STATUS_WRITTEN for file in export_result.files)

    generated_files = sorted(output_dir.iterdir())
    assert [path.name for path in generated_files] == [
        "candidate_review_report.json",
        "candidate_review_report.md",
    ]
    assert all(str(path.resolve()).startswith(str(output_dir.resolve())) for path in generated_files)

    checkout_root = str(ROOT.resolve()).lower()
    path_markers = ("c:\\", "c:/", "/users/", "/home/")
    for generated in generated_files:
        content = generated.read_text(encoding="utf-8")
        assert _scan_for_forbidden_variants(content, include_keys=False) == []
        assert checkout_root not in content.lower()
        for marker in path_markers:
            assert marker not in content.lower()

    json_content = json.loads((output_dir / "candidate_review_report.json").read_text(encoding="utf-8"))
    assert json_content["summary"]["total_items"] == 4
    assert json_content["summary"]["valid_records"] == 1
