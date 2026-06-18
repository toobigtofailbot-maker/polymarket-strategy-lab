"""Local/offline/read-only candidate review report for WP87 loader results.

The module consumes an in-memory CandidateFixtureLoadResult and returns frozen
report dataclasses plus deterministic Markdown. It performs no file reads,
file writes, network calls, credential access, scheduling, or account activity.

Added in WP89.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    LOADED_INVALID_CONTRACT_RECORD,
    LOADED_VALID_CONTRACT_RECORD,
    MALFORMED_FIXTURE_FILE,
    CandidateFixtureLoadItem,
    CandidateFixtureLoadResult,
)

REVIEW_VALIDATED_RECORD = "REVIEW_VALIDATED_RECORD"
REVIEW_REJECTED_RECORD = "REVIEW_REJECTED_RECORD"
REVIEW_MALFORMED_FIXTURE = "REVIEW_MALFORMED_FIXTURE"
REVIEW_MISSING_FIXTURE_PATH = "REVIEW_MISSING_FIXTURE_PATH"
REVIEW_UNSUPPORTED_FIXTURE_PATH = "REVIEW_UNSUPPORTED_FIXTURE_PATH"

VALIDATED_CONTRACT_RECORD = "VALIDATED_CONTRACT_RECORD"
INVALID_CONTRACT_RECORD = "INVALID_CONTRACT_RECORD"
MALFORMED_FIXTURE_FILE_REASON = "MALFORMED_FIXTURE_FILE"
MISSING_FIXTURE_PATH_REASON = "MISSING_FIXTURE_PATH"
UNSUPPORTED_FIXTURE_PATH_REASON = "UNSUPPORTED_FIXTURE_PATH"
NO_SAFE_REASON_AVAILABLE = "NO_SAFE_REASON_AVAILABLE"

ADVISORY_NOTICE = "Local review summary only. No account activity is authorized."
EVIDENCE_NOTICE = "Review report is generated from local validated fixture-loader output only."
BOUNDARY_NOTICE = (
    "Local offline human review summary from fixture-loader output only; "
    "no account activity is authorized."
)

_SAFE_REPORT_TITLE = "Wallet Candidate Local Review Report"

_UNSAFE_PATH_TOKENS: tuple[str, ...] = (
    "metadata",
    "position_size",
    "expected_return",
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "EXECUTION_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "AUTO_APPROVED",
)


@dataclass(frozen=True)
class CandidateReviewReportItem:
    fixture_path: str
    review_status: str
    validation_status: str
    is_valid: bool
    safe_reason_code: str
    safe_reason_summary: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class CandidateReviewReportSummary:
    total_items: int
    valid_records: int
    invalid_records: int
    malformed_files: int
    missing_or_unsupported_paths: int
    warning_count: int
    boundary_notice: str


@dataclass(frozen=True)
class CandidateReviewReport:
    report_title: str
    summary: CandidateReviewReportSummary
    items: tuple[CandidateReviewReportItem, ...]
    report_markdown: str
    advisory_notice: str
    evidence_notice: str


def _safe_fixture_path(raw_path: str, index: int) -> str:
    """Return a deterministic report label without unsafe local or input text."""
    normalized = raw_path.replace("\\", "/").strip()
    lowered = normalized.lower()
    if (
        not normalized
        or normalized.startswith("/")
        or ":/" in normalized
        or "../" in normalized
        or "/users/" in lowered
        or "/home/" in lowered
        or any(token.lower() in lowered for token in _UNSAFE_PATH_TOKENS)
    ):
        return f"fixture_item_{index:03d}.json"
    return normalized.split("/")[-1]


def _safe_warnings(warnings: tuple[str, ...]) -> tuple[str, ...]:
    if not warnings:
        return ()
    return tuple("Loader warning withheld from report output." for _ in warnings)


def _item_from_loader_item(
    item: CandidateFixtureLoadItem,
    index: int,
) -> CandidateReviewReportItem:
    if item.load_status == LOADED_VALID_CONTRACT_RECORD:
        return CandidateReviewReportItem(
            fixture_path=_safe_fixture_path(item.fixture_path, index),
            review_status=REVIEW_VALIDATED_RECORD,
            validation_status=item.validation_status,
            is_valid=True,
            safe_reason_code=VALIDATED_CONTRACT_RECORD,
            safe_reason_summary="Local fixture passed contract validation.",
            warnings=_safe_warnings(item.warnings),
        )
    if item.load_status == LOADED_INVALID_CONTRACT_RECORD:
        return CandidateReviewReportItem(
            fixture_path=_safe_fixture_path(item.fixture_path, index),
            review_status=REVIEW_REJECTED_RECORD,
            validation_status=item.validation_status,
            is_valid=False,
            safe_reason_code=INVALID_CONTRACT_RECORD,
            safe_reason_summary="Local fixture did not pass contract validation.",
            warnings=_safe_warnings(item.warnings),
        )
    if item.load_status == MALFORMED_FIXTURE_FILE:
        return CandidateReviewReportItem(
            fixture_path=_safe_fixture_path(item.fixture_path, index),
            review_status=REVIEW_MALFORMED_FIXTURE,
            validation_status=item.validation_status,
            is_valid=False,
            safe_reason_code=MALFORMED_FIXTURE_FILE_REASON,
            safe_reason_summary="Local fixture could not be parsed as a supported record.",
            warnings=_safe_warnings(item.warnings),
        )
    return CandidateReviewReportItem(
        fixture_path=_safe_fixture_path(item.fixture_path, index),
        review_status=REVIEW_UNSUPPORTED_FIXTURE_PATH,
        validation_status=item.validation_status,
        is_valid=False,
        safe_reason_code=NO_SAFE_REASON_AVAILABLE,
        safe_reason_summary="Local fixture was outside the supported review categories.",
        warnings=_safe_warnings(item.warnings),
    )


def _path_status_from_loader_errors(
    load_result: CandidateFixtureLoadResult,
) -> CandidateReviewReportItem | None:
    if load_result.items or not load_result.errors:
        return None
    error_text = " ".join(load_result.errors).lower()
    if "does not exist" in error_text:
        return CandidateReviewReportItem(
            fixture_path="fixture_path_unavailable",
            review_status=REVIEW_MISSING_FIXTURE_PATH,
            validation_status="",
            is_valid=False,
            safe_reason_code=MISSING_FIXTURE_PATH_REASON,
            safe_reason_summary="Local fixture path was not found.",
            warnings=(),
        )
    if "unsupported" in error_text or "url-like" in error_text:
        return CandidateReviewReportItem(
            fixture_path="fixture_path_unavailable",
            review_status=REVIEW_UNSUPPORTED_FIXTURE_PATH,
            validation_status="",
            is_valid=False,
            safe_reason_code=UNSUPPORTED_FIXTURE_PATH_REASON,
            safe_reason_summary="Local fixture path type is not supported.",
            warnings=(),
        )
    return None


def _build_summary(
    items: tuple[CandidateReviewReportItem, ...],
) -> CandidateReviewReportSummary:
    return CandidateReviewReportSummary(
        total_items=len(items),
        valid_records=sum(1 for item in items if item.review_status == REVIEW_VALIDATED_RECORD),
        invalid_records=sum(1 for item in items if item.review_status == REVIEW_REJECTED_RECORD),
        malformed_files=sum(1 for item in items if item.review_status == REVIEW_MALFORMED_FIXTURE),
        missing_or_unsupported_paths=sum(
            1
            for item in items
            if item.review_status in {
                REVIEW_MISSING_FIXTURE_PATH,
                REVIEW_UNSUPPORTED_FIXTURE_PATH,
            }
        ),
        warning_count=sum(len(item.warnings) for item in items),
        boundary_notice=BOUNDARY_NOTICE,
    )


def render_wallet_signal_candidate_review_report(report: CandidateReviewReport) -> str:
    """Render a deterministic Markdown report from a report object."""
    lines = [
        f"# {report.report_title}",
        "",
        report.advisory_notice,
        "",
        report.evidence_notice,
        "",
        "## Summary",
        "",
        f"- Total items: {report.summary.total_items}",
        f"- Valid records: {report.summary.valid_records}",
        f"- Invalid records: {report.summary.invalid_records}",
        f"- Malformed files: {report.summary.malformed_files}",
        f"- Missing or unsupported paths: {report.summary.missing_or_unsupported_paths}",
        f"- Warning count: {report.summary.warning_count}",
        f"- Boundary notice: {report.summary.boundary_notice}",
        "",
        "## Items",
        "",
        "| Fixture | Review status | Validation status | Safe reason code | Warnings |",
        "|---|---|---|---|---:|",
    ]
    for item in report.items:
        lines.append(
            "| "
            f"{item.fixture_path} | "
            f"{item.review_status} | "
            f"{item.validation_status} | "
            f"{item.safe_reason_code} | "
            f"{len(item.warnings)} |"
        )
    if not report.items:
        lines.append("| none | NO_SAFE_RECORDS_AVAILABLE |  | NO_SAFE_REASON_AVAILABLE | 0 |")
    return "\n".join(lines) + "\n"


def build_wallet_signal_candidate_review_report(
    load_result: CandidateFixtureLoadResult,
) -> CandidateReviewReport:
    """Build a deterministic candidate review report from a WP87 load result."""
    report_items = tuple(
        _item_from_loader_item(item, index)
        for index, item in enumerate(load_result.items, start=1)
    )
    path_status_item = _path_status_from_loader_errors(load_result)
    if path_status_item is not None:
        report_items = (path_status_item,)
    summary = _build_summary(report_items)
    partial = CandidateReviewReport(
        report_title=_SAFE_REPORT_TITLE,
        summary=summary,
        items=report_items,
        report_markdown="",
        advisory_notice=ADVISORY_NOTICE,
        evidence_notice=EVIDENCE_NOTICE,
    )
    markdown = render_wallet_signal_candidate_review_report(partial)
    return CandidateReviewReport(
        report_title=partial.report_title,
        summary=partial.summary,
        items=partial.items,
        report_markdown=markdown,
        advisory_notice=partial.advisory_notice,
        evidence_notice=partial.evidence_notice,
    )


def candidate_review_report_to_dict(
    report: CandidateReviewReport,
) -> dict[str, Any]:
    """Return a full dataclass serialization for output-surface scanning."""
    return asdict(report)
