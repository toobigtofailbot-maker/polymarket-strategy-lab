"""Focused tests for WP89 wallet candidate review report generation."""

from __future__ import annotations

import ast
import dataclasses
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer.wallet_signal_candidate_review_report import (
    INVALID_CONTRACT_RECORD,
    MALFORMED_FIXTURE_FILE_REASON,
    MISSING_FIXTURE_PATH_REASON,
    REVIEW_MALFORMED_FIXTURE,
    REVIEW_MISSING_FIXTURE_PATH,
    REVIEW_REJECTED_RECORD,
    REVIEW_UNSUPPORTED_FIXTURE_PATH,
    REVIEW_VALIDATED_RECORD,
    UNSUPPORTED_FIXTURE_PATH_REASON,
    CandidateReviewReport,
    CandidateReviewReportItem,
    CandidateReviewReportSummary,
    build_wallet_signal_candidate_review_report,
    candidate_review_report_to_dict,
    render_wallet_signal_candidate_review_report,
)
from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    load_wallet_signal_paper_strategy_candidate_fixtures,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "data_layer" / "wallet_signal_candidate_review_report.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "wallet_signal_paper_strategy_candidates"
VALID_FIXTURE = FIXTURE_DIR / "valid_candidate.json"
INVALID_STATUS_FIXTURE = FIXTURE_DIR / "invalid_forbidden_status.json"
INVALID_METADATA_FIXTURE = FIXTURE_DIR / "invalid_forbidden_metadata.json"
MALFORMED_FIXTURE = FIXTURE_DIR / "malformed_json.json"

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

FORBIDDEN_FIELD_NAMES: frozenset[str] = frozenset({
    "trade_signal",
    "paper_trading_candidate",
    "strategy_signal",
    "buy_signal",
    "sell_signal",
    "entry",
    "exit",
    "position_size",
    "expected_return",
    "execution_status",
    "order_status",
    "copy_instruction",
})

ALLOWED_REVIEW_STATUSES: frozenset[str] = frozenset({
    REVIEW_VALIDATED_RECORD,
    REVIEW_REJECTED_RECORD,
    REVIEW_MALFORMED_FIXTURE,
    REVIEW_MISSING_FIXTURE_PATH,
    REVIEW_UNSUPPORTED_FIXTURE_PATH,
})

ALLOWED_REASON_CODES: frozenset[str] = frozenset({
    "VALIDATED_CONTRACT_RECORD",
    INVALID_CONTRACT_RECORD,
    MALFORMED_FIXTURE_FILE_REASON,
    MISSING_FIXTURE_PATH_REASON,
    UNSUPPORTED_FIXTURE_PATH_REASON,
    "NO_SAFE_REASON_AVAILABLE",
})


def _report_from_fixture(path: Path | str) -> CandidateReviewReport:
    result = load_wallet_signal_paper_strategy_candidate_fixtures(path)
    return build_wallet_signal_candidate_review_report(result)


def _recursive_strings(obj: object, include_keys: bool = True) -> list[str]:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _recursive_strings(dataclasses.asdict(obj), include_keys=include_keys)
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


def _json_text(obj: object) -> str:
    return json.dumps(obj, sort_keys=True)


def test_build_report_from_valid_loader_result() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    assert isinstance(report, CandidateReviewReport)
    assert report.summary.total_items == 1
    assert report.summary.valid_records == 1
    assert report.summary.invalid_records == 0
    assert report.items[0].review_status == REVIEW_VALIDATED_RECORD
    assert report.items[0].is_valid is True
    assert report.report_markdown == render_wallet_signal_candidate_review_report(report)


def test_build_report_from_mixed_loader_result_counts() -> None:
    report = _report_from_fixture(FIXTURE_DIR)
    assert report.summary.total_items == 4
    assert report.summary.valid_records == 1
    assert report.summary.invalid_records == 2
    assert report.summary.malformed_files == 1
    assert report.summary.missing_or_unsupported_paths == 0


def test_build_report_preserves_deterministic_item_order() -> None:
    report = _report_from_fixture(FIXTURE_DIR)
    paths = [item.fixture_path for item in report.items]
    assert paths == sorted(paths)


def test_report_markdown_is_deterministic() -> None:
    report_a = _report_from_fixture(FIXTURE_DIR)
    report_b = _report_from_fixture(FIXTURE_DIR)
    assert report_a.report_markdown == report_b.report_markdown


def test_report_does_not_read_or_write_files(monkeypatch: pytest.MonkeyPatch) -> None:
    load_result = load_wallet_signal_paper_strategy_candidate_fixtures(VALID_FIXTURE)

    def fail_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("report builder must not perform filesystem I/O")

    monkeypatch.setattr(Path, "read_text", fail_io)
    monkeypatch.setattr(Path, "write_text", fail_io)
    report = build_wallet_signal_candidate_review_report(load_result)
    assert report.summary.total_items == 1


def test_report_does_not_import_network_or_runtime_modules() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    allowed_imports = {
        "src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader",
    }
    forbidden = (
        "requests",
        "urllib",
        "http",
        "socket",
        "asyncio",
        "aiohttp",
        "polymarket",
        "scheduler",
        "dashboard",
        "paper",
        "live",
        "credential",
        "auth",
        "execution",
        "hermes",
    )
    violations = [
        name
        for name in imported
        if name not in allowed_imports
        and any(term in name.lower() for term in forbidden)
    ]
    assert violations == []


def test_invalid_item_uses_neutral_reason_code() -> None:
    report = _report_from_fixture(INVALID_STATUS_FIXTURE)
    assert report.items[0].review_status == REVIEW_REJECTED_RECORD
    assert report.items[0].safe_reason_code == INVALID_CONTRACT_RECORD
    assert "TRADE_READY" not in report.items[0].safe_reason_summary


def test_malformed_item_uses_neutral_reason_code() -> None:
    report = _report_from_fixture(MALFORMED_FIXTURE)
    assert report.items[0].review_status == REVIEW_MALFORMED_FIXTURE
    assert report.items[0].safe_reason_code == MALFORMED_FIXTURE_FILE_REASON


def test_missing_path_item_uses_neutral_reason_code() -> None:
    report = _report_from_fixture(ROOT / "tests" / "fixtures" / "missing_wp89.json")
    assert report.items[0].review_status == REVIEW_MISSING_FIXTURE_PATH
    assert report.items[0].safe_reason_code == MISSING_FIXTURE_PATH_REASON
    assert report.summary.missing_or_unsupported_paths == 1


def test_unsupported_path_item_uses_neutral_reason_code(tmp_path: Path) -> None:
    text_file = tmp_path / "candidate.txt"
    text_file.write_text("plain text", encoding="utf-8")
    report = _report_from_fixture(text_file)
    assert report.items[0].review_status == REVIEW_UNSUPPORTED_FIXTURE_PATH
    assert report.items[0].safe_reason_code == UNSUPPORTED_FIXTURE_PATH_REASON


def test_report_does_not_echo_forbidden_status_input() -> None:
    report = _report_from_fixture(INVALID_STATUS_FIXTURE)
    text = _json_text(candidate_review_report_to_dict(report))
    assert "TRADE_READY" not in text


def test_report_does_not_echo_forbidden_metadata_input() -> None:
    report = _report_from_fixture(INVALID_METADATA_FIXTURE)
    text = _json_text(candidate_review_report_to_dict(report)).lower()
    assert "metadata" not in text
    assert "position_size" not in text
    assert "expected_return" not in text
    assert "25" not in text


def test_report_does_not_echo_raw_json_input() -> None:
    report = _report_from_fixture(MALFORMED_FIXTURE)
    text = _json_text(candidate_review_report_to_dict(report))
    assert "unclosed_object" not in text
    assert "intentionally_malformed" not in text
    assert "WP87 reviewer" not in text


def test_report_serializer_covers_all_public_report_fields() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    serialized = candidate_review_report_to_dict(report)
    assert {f.name for f in fields(CandidateReviewReport)} <= set(serialized)


def test_report_serializer_covers_all_public_summary_fields() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    serialized = candidate_review_report_to_dict(report)
    assert {f.name for f in fields(CandidateReviewReportSummary)} <= set(serialized["summary"])


def test_report_serializer_covers_all_public_item_fields() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    serialized = candidate_review_report_to_dict(report)
    assert {f.name for f in fields(CandidateReviewReportItem)} <= set(serialized["items"][0])


def test_full_report_object_has_no_forbidden_terms() -> None:
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        report = _report_from_fixture(fixture)
        assert _scan_for_forbidden_variants(candidate_review_report_to_dict(report)) == []


def test_report_markdown_has_no_forbidden_terms() -> None:
    report = _report_from_fixture(FIXTURE_DIR)
    assert _scan_for_forbidden_variants(report.report_markdown, include_keys=False) == []


def test_report_status_values_are_allowlisted() -> None:
    report = _report_from_fixture(FIXTURE_DIR)
    for item in report.items:
        assert item.review_status in ALLOWED_REVIEW_STATUSES
        assert item.safe_reason_code in ALLOWED_REASON_CODES


def test_report_field_names_are_safe() -> None:
    public_names = (
        {f.name for f in fields(CandidateReviewReport)}
        | {f.name for f in fields(CandidateReviewReportSummary)}
        | {f.name for f in fields(CandidateReviewReportItem)}
    )
    assert public_names.isdisjoint(FORBIDDEN_FIELD_NAMES)
    assert _scan_for_forbidden_variants(tuple(public_names), include_keys=False) == []


def test_report_boundary_notices_are_safe() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    assert report.advisory_notice == "Local review summary only. No account activity is authorized."
    assert report.evidence_notice == "Review report is generated from local validated fixture-loader output only."
    assert _scan_for_forbidden_variants((
        report.advisory_notice,
        report.evidence_notice,
        report.summary.boundary_notice,
    ), include_keys=False) == []


def test_report_uses_wp87_loader_result_contract() -> None:
    load_result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    report = build_wallet_signal_candidate_review_report(load_result)
    assert report.summary.valid_records == load_result.valid_records
    assert report.summary.invalid_records == load_result.invalid_records
    assert report.summary.malformed_files == load_result.malformed_files
    assert len(report.items) == len(load_result.items)


def test_report_objects_are_frozen() -> None:
    report = _report_from_fixture(VALID_FIXTURE)
    with pytest.raises((AttributeError, TypeError)):
        report.report_title = "changed"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        report.summary.total_items = 99  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        report.items[0].is_valid = False  # type: ignore[misc]


def test_report_source_has_no_file_write_calls() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    write_patterns = (
        r"\.write\(",
        r"\.write_text\(",
        r"\.write_bytes\(",
        r"open\([^)]*['\"][wa]['\"]",
        r"json\.dump\(",
    )
    for pattern in write_patterns:
        assert re.search(pattern, source) is None
