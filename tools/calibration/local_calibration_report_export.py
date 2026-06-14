"""Local/offline/read-only manual calibration report export tool.

WP72 — turns WP71 in-memory LocalCalibrationReport objects into a local
briefing a human can read: JSON or Markdown output to stdout or an explicit
local path.

Usage:
    python tools/calibration/local_calibration_report_export.py \
        --input path/to/calibration_records.json --format json
    python tools/calibration/local_calibration_report_export.py \
        --input path/to/calibration_records.json --format markdown
    python tools/calibration/local_calibration_report_export.py \
        --input path/to/calibration_records.json --format markdown \
        --output local_data/calibration_reports/report.md

Input types accepted (via WP68 loader):
    - Single JSON file containing one calibration record object.
    - Single JSON file containing a JSON list of calibration record objects.
    - Directory: loads direct-child *.json files (not recursive).

This tool:
- reads only an explicitly provided local input path;
- produces JSON or Markdown output to stdout (default) or an explicit path;
- performs no network access;
- uses no credentials, .env, wallet files, or secret paths;
- adds no scheduler, daemon, database, dashboard, or polling behavior;
- adds no advisory consumer integration;
- produces no trading signals, no buy/sell recommendations, no expected
  returns, no position sizing, no execution instructions;
- is advisory-only and requires human review before any use.

Exit codes:
    0 — success
    1 — invalid input / load failure / unsupported format / missing input
    2 — unsafe output path
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
from typing import Any, Mapping, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ADVISORY_NOTICE = (
    "ADVISORY-ONLY LOCAL CALIBRATION REPORT. "
    "This output is not a trading signal, not expected return, not position "
    "sizing, and not an execution instruction. It is for human research "
    "calibration audit only. ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT."
)

_FORBIDDEN_INTERPRETATION_NOTICE = (
    "FORBIDDEN INTERPRETATIONS: Do not interpret any field, rate, count, "
    "bucket, section, or label in this report as a trading signal, buy/sell "
    "recommendation, expected return, position size, execution instruction, "
    "or indication of any actionable research conclusion. Human review "
    "required before any use."
)

# Paths that the output flag must not point into (safety guard).
_FORBIDDEN_OUTPUT_PATH_PREFIXES = (
    "src/",
    "tests/",
    "docs/",
    "tools/",
    ".github/",
)

# Repo root and resolved forbidden directories (used by the resolved-path guard).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FORBIDDEN_OUTPUT_DIRS = tuple(
    (_REPO_ROOT / p).resolve()
    for p in ("src", "tests", "docs", "tools", ".github")
)

_SUPPORTED_FORMATS = {"json", "markdown"}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _is_relative_to(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Output path safety check
# ---------------------------------------------------------------------------

def _check_output_path(output_path: pathlib.Path) -> None:
    """Exit 2 if the output path is under a tracked repo directory."""
    path_str = str(output_path).replace("\\", "/")
    for prefix in _FORBIDDEN_OUTPUT_PATH_PREFIXES:
        if path_str.startswith(prefix) or ("/" + prefix) in path_str:
            print(
                f"Error: unsafe output path — writing to {prefix!r} directories "
                "is not allowed. Use local_data/calibration_reports/ or an "
                "absolute path outside the project for outputs.",
                file=sys.stderr,
            )
            sys.exit(2)

    try:
        resolved = output_path.resolve()
    except OSError:
        resolved = output_path
    for forbidden_dir in _FORBIDDEN_OUTPUT_DIRS:
        if resolved == forbidden_dir or _is_relative_to(resolved, forbidden_dir):
            print(
                "Error: unsafe output path — resolved path is under a tracked "
                f"repository directory ({forbidden_dir.name!r}). Use "
                "local_data/calibration_reports/ or an absolute path outside "
                "the project for outputs.",
                file=sys.stderr,
            )
            sys.exit(2)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def _load_input(input_path: pathlib.Path):
    """Load calibration records via WP68 loader and build WP71 report.

    Returns a LocalCalibrationReport. Exits 1 on fatal load failure.
    """
    from src.data_layer.resolved_outcome_fixture_loader import (
        load_resolved_outcome_fixtures,
    )
    from src.data_layer.calibration_report_generator import (
        build_calibration_report_from_load_result,
    )

    load_result = load_resolved_outcome_fixtures(input_path)
    if load_result.errors:
        for err in load_result.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    return build_calibration_report_from_load_result(load_result)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _make_serialisable(obj: Any) -> Any:
    """Recursively convert dataclasses, tuples, and mappings to JSON-safe types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _make_serialisable(v)
            for k, v in dataclasses.asdict(obj).items()
        }
    if isinstance(obj, tuple):
        return [_make_serialisable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serialisable(v) for v in obj]
    return obj


def _report_to_dict(report) -> dict:
    """Convert LocalCalibrationReport to a plain dict for JSON output."""
    d = _make_serialisable(report)
    # validation_summary.warnings is a tuple stored as list after asdict;
    # ensure it stays a list (already handled by _make_serialisable).
    return d


# ---------------------------------------------------------------------------
# JSON renderer
# ---------------------------------------------------------------------------

def _render_json(report) -> str:
    d = _report_to_dict(report)
    return json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _render_markdown(report) -> str:
    lines: list[str] = []

    lines.append("# Local Calibration Report")
    lines.append("")
    lines.append(f"> **{_ADVISORY_NOTICE}**")
    lines.append("")

    # Advisory label
    lines.append(f"**Advisory label**: `{report.advisory_label}`")
    lines.append("")

    # Report scope
    lines.append("## Report Scope")
    lines.append("")
    scope = report.report_scope
    for k, v in scope.items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")

    # Input summary
    lines.append("## Input Summary")
    lines.append("")
    inp = report.input_summary
    lines.append(f"- **Total records**: {inp.get('record_count', 0)}")
    lines.append(f"- **Valid records**: {inp.get('valid_record_count', 0)}")
    lines.append(f"- **Invalid records**: {inp.get('invalid_record_count', 0)}")
    lines.append("")

    # Validation summary
    lines.append("## Validation Summary")
    lines.append("")
    val = report.validation_summary
    lines.append(f"- **Warning count**: {val.get('warning_count', 0)}")
    ws = val.get("warnings", ())
    if ws:
        lines.append(f"- **Warnings**: {', '.join(f'`{w}`' for w in ws)}")
    else:
        lines.append("- **Warnings**: _none_")
    lines.append("")

    # Coverage summary
    lines.append("## Coverage Summary")
    lines.append("")
    cov = report.coverage_summary
    lines.append(f"- **Coverage rate**: {_pct(cov.get('coverage_rate', 0.0))}")
    lines.append("")

    # Missingness summary
    lines.append("## Missingness Summary")
    lines.append("")
    mis = report.missingness_summary
    lines.append(
        f"- **Missing required field rate**: "
        f"{_pct(mis.get('missing_required_field_rate', 0.0))}"
    )
    lines.append("")

    # Staleness summary
    lines.append("## Staleness Summary")
    lines.append("")
    stale = report.staleness_summary
    lines.append(f"- **Staleness rate**: {_pct(stale.get('staleness_rate', 0.0))}")
    lines.append("")

    # Resolution-source summary
    lines.append("## Resolution-Source Summary")
    lines.append("")
    res = report.resolution_source_summary
    lines.append(
        f"- **Source metadata available rate**: "
        f"{_pct(res.get('source_metadata_available_rate', 0.0))}"
    )
    lines.append(
        f"- **Resolution source missing rate**: "
        f"{_pct(res.get('resolution_source_missing_rate', 0.0))}"
    )
    lines.append("")

    # Manual-review summary
    lines.append("## Manual-Review Summary")
    lines.append("")
    mr = report.manual_review_summary
    lines.append(
        f"- **Manual review required rate**: "
        f"{_pct(mr.get('manual_review_required_rate', 0.0))}"
    )
    lines.append(
        f"- **Ambiguity review required rate**: "
        f"{_pct(mr.get('ambiguity_review_required_rate', 0.0))}"
    )
    lines.append("")

    # Bucket summary
    lines.append("## Bucket Summary")
    lines.append("")
    bkt = report.bucket_summary
    dist = bkt.get("bucket_distribution") or {}
    if dist:
        for bucket_name, count in sorted(dist.items()):
            lines.append(f"- **{bucket_name}**: {count}")
    else:
        lines.append("_No bucket distribution data._")
    lines.append("")

    # Human-review usefulness summary
    lines.append("## Human-Review Usefulness Summary")
    lines.append("")
    hru = report.human_review_usefulness_summary
    label_dist = hru.get("human_review_usefulness_label_distribution") or {}
    if label_dist:
        for label_name, count in sorted(label_dist.items()):
            lines.append(f"- **{label_name}**: {count}")
    else:
        lines.append("_No human-review usefulness label data._")
    lines.append("")

    # Excluded-record summary
    lines.append("## Excluded-Record Summary")
    lines.append("")
    excl = report.excluded_record_summary
    lines.append(f"- **Excluded record count**: {excl.get('excluded_record_count', 0)}")
    lines.append(
        f"- **Post-resolution audit warning count**: "
        f"{excl.get('post_resolution_audit_warning_count', 0)}"
    )
    lines.append("")

    # Warnings
    lines.append("## Warnings")
    lines.append("")
    if report.warnings:
        for w in report.warnings:
            lines.append(f"- `{w}`")
    else:
        lines.append("_No warnings._")
    lines.append("")

    # Forbidden interpretation notice
    lines.append("---")
    lines.append("")
    lines.append(f"> **{_FORBIDDEN_INTERPRETATION_NOTICE}**")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Local/offline/read-only manual calibration report export. "
            "Advisory-only. Not a trading signal."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=pathlib.Path,
        help=(
            "Path to a local JSON file (single record object, list of record "
            "objects) or a directory of direct-child *.json calibration record "
            "files. URL-like paths are rejected."
        ),
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default="json",
        help="Output format: json (default) or markdown.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help=(
            "Optional local output path. If omitted, writes to stdout. "
            "Recommended: local_data/calibration_reports/ (git-ignored)."
        ),
    )
    parser.add_argument(
        "--include-invalid-records",
        dest="include_invalid_records",
        action="store_true",
        default=False,
        help=(
            "If set, the export proceeds even when the loader reports invalid "
            "records. By default any loader error causes exit 1."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    # Validate format before any file I/O (exit 1 per WP72 contract).
    if args.output_format not in _SUPPORTED_FORMATS:
        print(f"Error: unsupported format: {args.output_format!r}", file=sys.stderr)
        sys.exit(1)

    # Validate output path before any processing.
    if args.output is not None:
        _check_output_path(args.output)

    # Reject URL-like input paths before passing to loader.
    input_str = str(args.input).strip().lower()
    if any(input_str.startswith(p) for p in ("http://", "https://", "ftp://", "ftps://")):
        print(
            f"Error: URL-like input path rejected: {args.input!r}. "
            "Only explicit local paths are accepted.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load and generate report.
    from src.data_layer.resolved_outcome_fixture_loader import (
        load_resolved_outcome_fixtures,
    )
    from src.data_layer.calibration_report_generator import (
        build_calibration_report_from_load_result,
    )

    load_result = load_resolved_outcome_fixtures(args.input)

    if load_result.errors and not args.include_invalid_records:
        for err in load_result.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    report = build_calibration_report_from_load_result(load_result)

    # Render.
    if args.output_format == "json":
        output_text = _render_json(report)
    else:
        output_text = _render_markdown(report)

    # Write.
    if args.output is None:
        print(output_text)
    else:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output_text, encoding="utf-8")
        except OSError as exc:
            print(f"Error: cannot write output file: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Written to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
