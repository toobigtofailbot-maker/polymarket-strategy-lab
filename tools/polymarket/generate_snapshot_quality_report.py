"""Offline local snapshot quality report generator.

Reads WP10/WP11 local snapshot files from local_data/polymarket/snapshots/
and prints a sanitized quality summary. Writes reports only when explicit
local_data output paths are provided.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.local_reports import (
    render_quality_report_json,
    render_quality_report_markdown,
    write_local_json_report,
    write_local_report,
)
from src.data_layer.polymarket.snapshot_quality import build_snapshot_quality_report
from src.data_layer.polymarket.snapshot_reader import (
    DEFAULT_INPUT_DIR,
    list_snapshot_files,
    load_market_snapshot_records,
    load_order_book_snapshot_records,
    load_snapshot_manifests,
)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline quality report generator for local Polymarket snapshot files. "
            "Reads local files only and writes only when explicit local_data paths "
            "are provided."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing local snapshot files. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Raise on malformed JSONL or manifest input instead of collecting errors.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        default=False,
        help="Treat WARNING issues as quality gate failures.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        default=False,
        help="Exit 1 when ERROR issues are present.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional Markdown report path under local_data/.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional JSON report path under local_data/.",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=25,
        help="Maximum number of quality issues to print or write in report summaries.",
    )

    args = parser.parse_args(argv)
    input_dir = Path(args.input_dir)

    print("Polymarket Snapshot Quality Report (offline)")
    print(f"Input directory: {input_dir}")
    print("Writes files only when explicit local_data output paths are provided.")
    _print_separator()

    file_summary = list_snapshot_files(input_dir)
    if not input_dir.exists():
        print(f"Notice: input directory does not exist: {input_dir}")
        print("No snapshot files to load.")

    try:
        market_result = load_market_snapshot_records(input_dir, strict=args.strict)
        order_book_result = load_order_book_snapshot_records(input_dir, strict=args.strict)
        manifest_result = load_snapshot_manifests(input_dir, strict=args.strict)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report = build_snapshot_quality_report(
        file_summary=file_summary,
        market_result=market_result,
        order_book_result=order_book_result,
        manifest_result=manifest_result,
        fail_on_warning=args.fail_on_warning,
    )

    _print_console_summary(report, max_issues=max(args.max_issues, 0))

    if args.markdown_out:
        markdown = render_quality_report_markdown(
            report,
            max_issues=max(args.max_issues, 0),
        )
        try:
            written = write_local_report(markdown, args.markdown_out)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Markdown report written: {written}")

    if args.json_out:
        data = render_quality_report_json(
            report,
            max_issues=max(args.max_issues, 0),
        )
        try:
            written = write_local_json_report(data, args.json_out)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"JSON report written: {written}")

    if args.fail_on_warning and not report.gate_result.passed:
        return 1
    if args.fail_on_error and report.gate_result.error_count > 0:
        return 1
    return 0


def _print_console_summary(report, *, max_issues: int) -> None:
    snap = report.snapshot_summary
    cat = report.catalog_summary
    counts = report.issue_counts_by_severity()

    print(f"Markets JSONL present:       {snap.markets_file_present}")
    print(f"Order-books JSONL present:   {snap.order_books_file_present}")
    print(f"Manifest files found:        {snap.manifest_count}")
    print(f"Market records loaded:       {snap.market_record_count}")
    print(f"Order-book records loaded:   {snap.order_book_record_count}")
    print(f"Manifest records loaded:     {snap.manifest_record_count}")
    _print_separator()
    print(f"Quality gate status:         {report.gate_result.status}")
    print(f"Errors:                      {counts.get('ERROR', 0)}")
    print(f"Warnings:                    {counts.get('WARNING', 0)}")
    print(f"Info:                        {counts.get('INFO', 0)}")
    _print_separator()
    print(f"Unique markets:              {cat.unique_market_count}")
    print(f"Total records:               {cat.total_record_count}")
    print(f"Duplicate market records:    {cat.duplicate_market_count}")
    print(f"Tokens:                      {cat.token_count}")
    print(f"Order-book tokens unmatched: {cat.order_book_tokens_without_market_count}")
    print(f"Latest snapshot timestamp:   {cat.latest_snapshot_timestamp or 'unknown'}")

    if max_issues and report.issues:
        _print_separator()
        print(f"Top issues (up to {max_issues}):")
        for issue in report.issues[:max_issues]:
            print(f"  {issue.severity:<7} {issue.code}: {issue.message}")

    _print_separator()
    print("Safety: offline quality/reporting only; no network, credentials, orders, or automation.")


def _print_separator() -> None:
    print("-" * 60)


if __name__ == "__main__":
    raise SystemExit(main())
