"""Sanitized local report rendering for offline snapshot quality results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .snapshot_quality import SnapshotQualityReport


SAFETY_STATEMENT = (
    "Offline quality/reporting infrastructure only. It reads WP10/WP11 local "
    "snapshot data, does not call Polymarket APIs, does not capture new data, "
    "does not create strategy signals or trade proposals, does not backtest, "
    "does not simulate fills, does not place, cancel, sign, or simulate orders, "
    "does not authenticate, does not read credentials, and is not a database, "
    "scheduler, bot loop, or production service."
)

DEFERRED_CONSTRAINTS = (
    "WP8-D002 remains open, so these reports must not be used for automated "
    "or frequent market scanning. WP10-D001, WP10-D002, WP11-D001, and "
    "WP11-D002 remain open for schema stability, database backing, catalog "
    "persistence, and backtest readiness."
)

_LOCAL_DATA_PART = "local_data"
_PROTECTED_PARTS = {"src", "docs", "tests", "tools", ".git", "audits"}


def render_quality_report_markdown(
    report: SnapshotQualityReport,
    *,
    max_issues: int = 25,
) -> str:
    """Render a sanitized Markdown quality report."""

    counts = report.issue_counts_by_severity()
    snap = report.snapshot_summary
    cat = report.catalog_summary
    lines = [
        "# Polymarket Snapshot Quality Report",
        "",
        f"- Generated at UTC: `{report.generated_at_utc}`",
        f"- Input directory: `{report.input_dir}`",
        f"- Quality gate: `{report.gate_result.status}`",
        f"- Gate fail-on-warning: `{report.gate_result.fail_on_warning}`",
        "",
        "## Snapshot Files",
        "",
        f"- Markets JSONL present: `{snap.markets_file_present}`",
        f"- Order-books JSONL present: `{snap.order_books_file_present}`",
        f"- Manifest files found: `{snap.manifest_count}`",
        f"- Market records loaded: `{snap.market_record_count}`",
        f"- Order-book records loaded: `{snap.order_book_record_count}`",
        f"- Manifest records loaded: `{snap.manifest_record_count}`",
        f"- Malformed market lines: `{snap.malformed_market_lines}`",
        f"- Malformed order-book lines: `{snap.malformed_order_book_lines}`",
        f"- Malformed manifest files: `{snap.malformed_manifest_files}`",
        f"- Manifests with network_used true: `{snap.manifest_network_used_true_count}`",
        f"- Manifests with empty output_files: `{snap.manifest_output_files_empty_count}`",
        "",
        "## Catalog Summary",
        "",
        f"- Unique markets: `{cat.unique_market_count}`",
        f"- Total market records: `{cat.total_record_count}`",
        f"- Duplicate market records: `{cat.duplicate_market_count}`",
        f"- Tokens: `{cat.token_count}`",
        f"- Snapshot IDs: `{cat.snapshot_id_count}`",
        f"- Latest snapshot timestamp: `{cat.latest_snapshot_timestamp or 'unknown'}`",
        f"- Missing categories: `{cat.missing_category_count}`",
        f"- Missing resolution dates: `{cat.missing_resolution_date_count}`",
        f"- Order-book tokens: `{cat.order_book_token_count}`",
        f"- Order-book tokens without market: `{cat.order_book_tokens_without_market_count}`",
        "",
        "## Issue Counts",
        "",
        f"- ERROR: `{counts.get('ERROR', 0)}`",
        f"- WARNING: `{counts.get('WARNING', 0)}`",
        f"- INFO: `{counts.get('INFO', 0)}`",
        "",
        "## Top Issues",
        "",
    ]

    if report.issues:
        for issue in report.issues[:max_issues]:
            location = _format_issue_location(issue.snapshot_id, issue.market_id, issue.field)
            lines.append(
                f"- `{issue.severity}` `{issue.code}` {location}: {issue.message}"
            )
    else:
        lines.append("- No quality issues found.")

    lines.extend(
        [
            "",
            "## Deferred Constraints",
            "",
            DEFERRED_CONSTRAINTS,
            "",
            "## Safety Statement",
            "",
            SAFETY_STATEMENT,
            "",
        ]
    )
    return "\n".join(lines)


def render_quality_report_json(
    report: SnapshotQualityReport,
    *,
    max_issues: Optional[int] = 25,
) -> dict:
    """Render a sanitized JSON-compatible report dict."""

    data = report.to_dict(max_issues=max_issues)
    data["safety_statement"] = SAFETY_STATEMENT
    data["deferred_constraints"] = DEFERRED_CONSTRAINTS
    data["sanitization"] = {
        "large_source_payloads_included": False,
        "credentials_included": False,
        "local_report_only": True,
    }
    return data


def write_local_report(markdown: str, output_path: Path) -> Path:
    """Write a Markdown report to an approved local_data path."""

    path = _validate_local_report_output_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def write_local_json_report(data: dict, output_path: Path) -> Path:
    """Write a JSON report to an approved local_data path."""

    path = _validate_local_report_output_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _validate_local_report_output_path(output_path: Path) -> Path:
    path = Path(output_path)
    resolved = path.resolve()
    parts_lower = [part.lower() for part in resolved.parts]
    if _LOCAL_DATA_PART not in parts_lower:
        raise ValueError(
            f"Report output path {str(path)!r} is not under local_data/."
        )
    local_data_index = parts_lower.index(_LOCAL_DATA_PART)
    protected_before_local_data = set(parts_lower[:local_data_index]) & _PROTECTED_PARTS
    protected_after_local_data = set(parts_lower[local_data_index + 1 :]) & {
        ".git",
        "src",
        "docs",
        "tests",
        "tools",
    }
    if protected_before_local_data or protected_after_local_data:
        raise ValueError(
            f"Report output path {str(path)!r} crosses a protected repository path."
        )
    if resolved.name in {"", ".", ".."}:
        raise ValueError("Report output path must be a file path.")
    return resolved


def _format_issue_location(
    snapshot_id: Optional[str],
    market_id: Optional[str],
    field: Optional[str],
) -> str:
    parts = []
    if snapshot_id:
        parts.append(f"snapshot={snapshot_id}")
    if market_id:
        parts.append(f"market={market_id}")
    if field:
        parts.append(f"field={field}")
    return "(" + ", ".join(parts) + ")" if parts else ""
