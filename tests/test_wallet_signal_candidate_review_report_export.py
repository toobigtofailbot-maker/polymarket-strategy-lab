"""Focused tests for WP90 wallet candidate review report local export."""

from __future__ import annotations

import ast
import dataclasses
import json
import re
import unittest.mock
from dataclasses import fields
from pathlib import Path

import pytest

from src.data_layer.wallet_signal_candidate_review_report import (
    build_wallet_signal_candidate_review_report,
    render_wallet_signal_candidate_review_report,
)
from src.data_layer.wallet_signal_candidate_review_report_export import (
    EXPORT_STATUS_EXPORT_NOT_WRITTEN,
    EXPORT_STATUS_EXPORT_PARTIAL,
    EXPORT_STATUS_EXPORT_WRITTEN,
    FORMAT_JSON,
    FORMAT_MARKDOWN,
    WRITE_STATUS_SKIPPED_UNREQUESTED,
    WRITE_STATUS_WRITTEN,
    CandidateReviewReportExportFile,
    CandidateReviewReportExportResult,
    candidate_review_report_export_result_to_dict,
    export_wallet_signal_candidate_review_report,
    render_candidate_review_report_json,
)
from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    load_wallet_signal_paper_strategy_candidate_fixtures,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "data_layer" / "wallet_signal_candidate_review_report_export.py"
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

ALLOWED_EXPORT_STATUSES: frozenset[str] = frozenset({
    EXPORT_STATUS_EXPORT_WRITTEN,
    EXPORT_STATUS_EXPORT_PARTIAL,
    EXPORT_STATUS_EXPORT_NOT_WRITTEN,
})

ALLOWED_WRITE_STATUSES: frozenset[str] = frozenset({
    WRITE_STATUS_WRITTEN,
    WRITE_STATUS_SKIPPED_UNREQUESTED,
})

ALLOWED_FORMATS: frozenset[str] = frozenset({FORMAT_MARKDOWN, FORMAT_JSON})

SAFE_ADVISORY_NOTICE = "Local file export only. No account activity is authorized."


def _build_report(fixture_path: Path | str):
    load_result = load_wallet_signal_paper_strategy_candidate_fixtures(fixture_path)
    return build_wallet_signal_candidate_review_report(load_result)


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


def test_export_markdown_file_from_report(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    export_wallet_signal_candidate_review_report(report, tmp_path, formats=(FORMAT_MARKDOWN,))
    md_file = tmp_path / "candidate_review_report.md"
    assert md_file.is_file()
    assert md_file.read_text(encoding="utf-8")


def test_export_json_file_from_report(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    export_wallet_signal_candidate_review_report(report, tmp_path, formats=(FORMAT_JSON,))
    json_file = tmp_path / "candidate_review_report.json"
    assert json_file.is_file()
    content = json_file.read_text(encoding="utf-8")
    assert isinstance(json.loads(content), dict)


def test_export_both_formats_by_default(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    assert (tmp_path / "candidate_review_report.md").is_file()
    assert (tmp_path / "candidate_review_report.json").is_file()
    written = [f for f in result.files if f.write_status == WRITE_STATUS_WRITTEN]
    assert len(written) == 2


def test_export_respects_requested_formats(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path, formats=(FORMAT_JSON,))
    assert (tmp_path / "candidate_review_report.json").is_file()
    assert not (tmp_path / "candidate_review_report.md").is_file()
    skipped = [f for f in result.files if f.write_status == WRITE_STATUS_SKIPPED_UNREQUESTED]
    assert len(skipped) >= 1
    assert all(f.bytes_written == 0 for f in skipped)


def test_export_output_is_deterministic(tmp_path: Path) -> None:
    report = _build_report(FIXTURE_DIR)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    result_a = export_wallet_signal_candidate_review_report(report, out_a)
    result_b = export_wallet_signal_candidate_review_report(report, out_b)
    md_a = (out_a / "candidate_review_report.md").read_text(encoding="utf-8")
    md_b = (out_b / "candidate_review_report.md").read_text(encoding="utf-8")
    json_a = (out_a / "candidate_review_report.json").read_text(encoding="utf-8")
    json_b = (out_b / "candidate_review_report.json").read_text(encoding="utf-8")
    assert md_a == md_b
    assert json_a == json_b
    sha_a = {f.relative_path: f.content_sha256 for f in result_a.files if f.write_status == WRITE_STATUS_WRITTEN}
    sha_b = {f.relative_path: f.content_sha256 for f in result_b.files if f.write_status == WRITE_STATUS_WRITTEN}
    assert sha_a == sha_b


def test_export_overwrite_is_deterministic_or_safely_rejected(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result_1 = export_wallet_signal_candidate_review_report(report, tmp_path)
    result_2 = export_wallet_signal_candidate_review_report(report, tmp_path)
    sha_1 = {f.relative_path: f.content_sha256 for f in result_1.files}
    sha_2 = {f.relative_path: f.content_sha256 for f in result_2.files}
    assert sha_1 == sha_2


def test_export_writes_only_under_output_dir(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    out_dir = tmp_path / "report_output"
    export_wallet_signal_candidate_review_report(report, out_dir)
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert str(f).startswith(str(out_dir)), (
                f"File {f} is outside expected output directory {out_dir}"
            )


def test_export_result_paths_are_relative_and_safe(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    for export_file in result.files:
        rel = export_file.relative_path
        assert not Path(rel).is_absolute(), f"relative_path must not be absolute: {rel}"
        assert ".." not in rel, f"relative_path must not contain parent traversal: {rel}"
        assert ":" not in rel, f"relative_path must not contain drive letters: {rel}"
        assert "/home/" not in rel.lower()
        assert "/users/" not in rel.lower()


def test_export_result_contains_sha256_and_byte_counts(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    for export_file in result.files:
        if export_file.write_status == WRITE_STATUS_WRITTEN:
            assert export_file.bytes_written > 0
            assert len(export_file.content_sha256) == 64
            assert re.match(r"^[0-9a-f]{64}$", export_file.content_sha256)


def test_export_json_has_sorted_keys_and_trailing_newline(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    export_wallet_signal_candidate_review_report(report, tmp_path)
    content = (tmp_path / "candidate_review_report.json").read_text(encoding="utf-8")
    assert content.endswith("\n")
    parsed = json.loads(content)
    assert isinstance(parsed, dict)
    top_keys = list(parsed.keys())
    assert top_keys == sorted(top_keys)


def test_export_markdown_matches_report_markdown(tmp_path: Path) -> None:
    report = _build_report(FIXTURE_DIR)
    export_wallet_signal_candidate_review_report(report, tmp_path)
    md_content = (tmp_path / "candidate_review_report.md").read_text(encoding="utf-8")
    expected = render_wallet_signal_candidate_review_report(report)
    assert md_content == expected


def test_export_does_not_read_network_or_runtime_modules() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    allowed_imports = {
        "src.data_layer.wallet_signal_candidate_review_report",
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


def test_export_does_not_import_forbidden_modules() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    forbidden_patterns = (
        r"import requests",
        r"from urllib",
        r"from http",
        r"import socket",
        r"import asyncio",
        r"import aiohttp",
        r"from polymarket",
        r"import polymarket",
        r"from scheduler",
        r"from paper",
        r"from live",
        r"from credential",
        r"import credential",
        r"from hermes",
        r"import hermes",
    )
    for pattern in forbidden_patterns:
        assert not re.search(pattern, source), f"Forbidden import found: {pattern}"


def test_export_does_not_write_outside_temp_output_dir(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    out_dir = tmp_path / "safe_output"
    original_write_bytes = Path.write_bytes
    written_paths: list[str] = []

    def tracked_write_bytes(self: Path, data: bytes) -> int:
        written_paths.append(str(self.resolve()))
        return original_write_bytes(self, data)

    with unittest.mock.patch.object(Path, "write_bytes", tracked_write_bytes):
        export_wallet_signal_candidate_review_report(report, out_dir)

    resolved_out = str(out_dir.resolve())
    for path_str in written_paths:
        assert path_str.startswith(resolved_out), (
            f"Write to {path_str!r} is outside expected output directory {resolved_out!r}"
        )


def test_export_generated_markdown_has_no_forbidden_terms(tmp_path: Path) -> None:
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        out_dir = tmp_path / fixture.stem
        report = _build_report(fixture)
        export_wallet_signal_candidate_review_report(report, out_dir)
        content = (out_dir / "candidate_review_report.md").read_text(encoding="utf-8")
        violations = _scan_for_forbidden_variants(content, include_keys=False)
        assert violations == [], f"Forbidden terms in generated markdown ({fixture.name}): {violations}"


def test_export_generated_json_has_no_forbidden_terms(tmp_path: Path) -> None:
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        out_dir = tmp_path / fixture.stem
        report = _build_report(fixture)
        export_wallet_signal_candidate_review_report(report, out_dir)
        content = (out_dir / "candidate_review_report.json").read_text(encoding="utf-8")
        violations = _scan_for_forbidden_variants(content, include_keys=False)
        assert violations == [], f"Forbidden terms in generated JSON ({fixture.name}): {violations}"


def test_full_export_result_has_no_forbidden_terms(tmp_path: Path) -> None:
    for fixture in (VALID_FIXTURE, INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        out_dir = tmp_path / fixture.stem
        report = _build_report(fixture)
        result = export_wallet_signal_candidate_review_report(report, out_dir)
        serialized = candidate_review_report_export_result_to_dict(result)
        violations = _scan_for_forbidden_variants(serialized)
        assert violations == [], f"Forbidden terms in export result ({fixture.name}): {violations}"


def test_export_result_serializer_covers_all_public_result_fields(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    serialized = candidate_review_report_export_result_to_dict(result)
    assert {f.name for f in fields(CandidateReviewReportExportResult)} <= set(serialized)


def test_export_result_serializer_covers_all_public_file_fields(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    serialized = candidate_review_report_export_result_to_dict(result)
    assert len(serialized["files"]) > 0
    for file_dict in serialized["files"]:
        assert {f.name for f in fields(CandidateReviewReportExportFile)} <= set(file_dict)


def test_export_status_values_are_allowlisted(tmp_path: Path) -> None:
    report = _build_report(FIXTURE_DIR)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    assert result.export_status in ALLOWED_EXPORT_STATUSES
    for export_file in result.files:
        assert export_file.write_status in ALLOWED_WRITE_STATUSES
        assert export_file.format in ALLOWED_FORMATS


def test_export_field_names_are_safe() -> None:
    public_names = (
        {f.name for f in fields(CandidateReviewReportExportResult)}
        | {f.name for f in fields(CandidateReviewReportExportFile)}
    )
    assert public_names.isdisjoint(FORBIDDEN_FIELD_NAMES)
    violations = _scan_for_forbidden_variants(tuple(public_names), include_keys=False)
    assert violations == []


def test_export_boundary_notice_is_safe(tmp_path: Path) -> None:
    report = _build_report(VALID_FIXTURE)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    assert result.advisory_notice == SAFE_ADVISORY_NOTICE
    violations = _scan_for_forbidden_variants((result.advisory_notice,), include_keys=False)
    assert violations == []


def test_export_uses_wp89_report_contract(tmp_path: Path) -> None:
    load_result = load_wallet_signal_paper_strategy_candidate_fixtures(FIXTURE_DIR)
    report = build_wallet_signal_candidate_review_report(load_result)
    result = export_wallet_signal_candidate_review_report(report, tmp_path)
    assert result.export_status == EXPORT_STATUS_EXPORT_WRITTEN
    written = [f for f in result.files if f.write_status == WRITE_STATUS_WRITTEN]
    assert len(written) == 2


def test_export_invalid_fixture_no_unsafe_content_in_any_surface(tmp_path: Path) -> None:
    """Export from invalid/malformed loader inputs must not echo unsafe content in any surface."""
    for fixture in (INVALID_STATUS_FIXTURE, INVALID_METADATA_FIXTURE, MALFORMED_FIXTURE):
        out_dir = tmp_path / fixture.stem
        report = _build_report(fixture)
        result = export_wallet_signal_candidate_review_report(report, out_dir)
        serialized = candidate_review_report_export_result_to_dict(result)

        # Full export result object
        assert _scan_for_forbidden_variants(serialized) == [], (
            f"Forbidden in export result ({fixture.name})"
        )
        # Generated file contents
        for export_file in result.files:
            if export_file.write_status == WRITE_STATUS_WRITTEN:
                content = (out_dir / export_file.relative_path).read_text(encoding="utf-8")
                assert _scan_for_forbidden_variants(content, include_keys=False) == [], (
                    f"Forbidden in {export_file.relative_path} ({fixture.name})"
                )
        # Warnings
        assert _scan_for_forbidden_variants(result.warnings, include_keys=False) == [], (
            f"Forbidden in warnings ({fixture.name})"
        )
        # Advisory notice
        assert _scan_for_forbidden_variants((result.advisory_notice,), include_keys=False) == [], (
            f"Forbidden in advisory_notice ({fixture.name})"
        )
        # Relative paths
        rel_paths = tuple(f.relative_path for f in result.files)
        assert _scan_for_forbidden_variants(rel_paths, include_keys=False) == [], (
            f"Forbidden in relative paths ({fixture.name})"
        )


def test_export_does_not_include_user_home_or_absolute_paths_in_file_content(tmp_path: Path) -> None:
    report = _build_report(FIXTURE_DIR)
    out_dir = tmp_path / "output"
    export_wallet_signal_candidate_review_report(report, out_dir)
    home_patterns = ("/home/", "/users/", "C:\\Users\\", "C:/Users/")
    for file_name in ("candidate_review_report.md", "candidate_review_report.json"):
        content = (out_dir / file_name).read_text(encoding="utf-8").lower()
        for pattern in home_patterns:
            assert pattern.lower() not in content, f"{pattern!r} found in {file_name}"


def test_export_rejects_or_ignores_path_traversal_inputs(tmp_path: Path) -> None:
    """V1 uses fixed allowlisted filenames; no user-provided path affects output filename."""
    report = _build_report(VALID_FIXTURE)
    out_dir = tmp_path / "output"
    result = export_wallet_signal_candidate_review_report(report, out_dir)
    allowed_filenames = frozenset({"candidate_review_report.md", "candidate_review_report.json"})
    for export_file in result.files:
        assert export_file.relative_path in allowed_filenames, (
            f"Unexpected relative_path: {export_file.relative_path!r}"
        )
        assert "../" not in export_file.relative_path
        assert "..\\" not in export_file.relative_path
        assert not Path(export_file.relative_path).is_absolute()
