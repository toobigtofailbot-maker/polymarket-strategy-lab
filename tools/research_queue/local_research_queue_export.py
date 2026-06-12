"""Local/offline/read-only manual research queue export tool.

WP65 — turns WP64 in-memory research queue objects into a local morning
briefing: a local JSON file and/or Markdown briefing a human can read.

Usage:
    python tools/research_queue/local_research_queue_export.py \
        --input local_data/example/research_queue_input.json \
        --format markdown

This tool:
- reads only an explicitly provided local JSON input file;
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
    1 — invalid input / validation error / unsupported format
    2 — unsafe output path or forbidden option
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOOL_VERSION = "local-research-queue-export.v1"
_ADVISORY_LABEL = "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
_REPORT_TYPE = "LOCAL_HUMAN_REVIEW_REPORT_V1"

_ADVISORY_NOTICE = (
    "ADVISORY-ONLY LOCAL RESEARCH QUEUE BRIEFING. "
    "This output is not a trading signal, not expected return, not position "
    "sizing, and not an execution instruction. It is for human research triage "
    "only. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED."
)

_FORBIDDEN_INTERPRETATION_NOTICE = (
    "FORBIDDEN INTERPRETATIONS: Do not interpret any field, bucket, rank, score, "
    "flag, or section in this briefing as a trading signal, buy/sell "
    "recommendation, expected return, position size, execution instruction, or "
    "indication of any actionable research conclusion. Human review "
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

# Bucket display order for Markdown output.
_BUCKET_ORDER = [
    "REVIEW_FIRST",
    "MANUAL_SOURCE_REVIEW_REQUIRED",
    "REVIEW_LATER",
    "DATA_QUALITY_BLOCKED",
    "DEPRIORITIZED",
]

_BUCKET_HEADINGS = {
    "REVIEW_FIRST": "Review First",
    "MANUAL_SOURCE_REVIEW_REQUIRED": "Manual Source Review Required",
    "REVIEW_LATER": "Review Later",
    "DATA_QUALITY_BLOCKED": "Data Quality Blocked",
    "DEPRIORITIZED": "Deprioritized",
}


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
# Input loading and validation
# ---------------------------------------------------------------------------

def _load_input(path: pathlib.Path) -> dict:
    """Load and validate the local JSON input file.

    Accepts either:
    - a list of market context dicts (raw queue input), or
    - an already-built WP64 LOCAL_HUMAN_REVIEW_REPORT_V1 object.

    Returns a LOCAL_HUMAN_REVIEW_REPORT_V1 dict.
    """
    if not path.exists():
        print(f"Error: input file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error: cannot read input file: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: input is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    if isinstance(data, list):
        return _build_report_from_contexts(data)

    if isinstance(data, dict):
        report_type = data.get("report_type", "")
        if report_type == _REPORT_TYPE:
            return data
        # Attempt to treat a bare dict as a single-market context list.
        if "market_id" in data or "question" in data:
            return _build_report_from_contexts([data])
        print(
            "Error: JSON input is neither a list of market contexts nor a "
            f"LOCAL_HUMAN_REVIEW_REPORT_V1 object (report_type={report_type!r}).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "Error: JSON input must be a list or a LOCAL_HUMAN_REVIEW_REPORT_V1 dict.",
        file=sys.stderr,
    )
    sys.exit(1)


def _build_report_from_contexts(
    contexts: list[dict],
    generated_at_utc: Optional[str] = None,
) -> dict:
    """Build a LOCAL_HUMAN_REVIEW_REPORT_V1 dict from a list of market contexts."""
    from src.data_layer.market_research_priority_review_queue import (
        build_local_human_review_report,
    )

    ref_time: Optional[datetime] = None
    if generated_at_utc:
        try:
            ref_time = datetime.fromisoformat(generated_at_utc)
        except ValueError:
            print(
                f"Error: --generated-at-utc value is not a valid ISO timestamp: "
                f"{generated_at_utc!r}",
                file=sys.stderr,
            )
            sys.exit(1)

    return build_local_human_review_report(contexts, generated_at_utc=ref_time)


# ---------------------------------------------------------------------------
# Timestamp override
# ---------------------------------------------------------------------------

def _apply_generated_at_override(report: dict, generated_at_utc: Optional[str]) -> dict:
    """Return report with generated_at_utc overridden if flag was passed."""
    if not generated_at_utc:
        return report
    try:
        datetime.fromisoformat(generated_at_utc)
    except ValueError:
        print(
            f"Error: --generated-at-utc value is not a valid ISO timestamp: "
            f"{generated_at_utc!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    updated = dict(report)
    updated["generated_at_utc"] = generated_at_utc
    return updated


# ---------------------------------------------------------------------------
# Output path safety check
# ---------------------------------------------------------------------------

def _check_output_path(output_path: pathlib.Path) -> None:
    """Reject unsafe output paths."""
    # String-form check (conservative: catches relative paths before they exist).
    path_str = str(output_path).replace("\\", "/")
    for prefix in _FORBIDDEN_OUTPUT_PATH_PREFIXES:
        if path_str.startswith(prefix) or ("/" + prefix) in path_str:
            print(
                f"Error: unsafe output path — writing to {prefix!r} directories "
                "is not allowed. Use local_data/ or an absolute path outside the "
                "project for test/dev outputs.",
                file=sys.stderr,
            )
            sys.exit(2)

    # Resolved-path check (catches symlinks and absolute paths under tracked dirs).
    try:
        resolved = output_path.resolve()
    except OSError:
        resolved = output_path
    for forbidden_dir in _FORBIDDEN_OUTPUT_DIRS:
        if resolved == forbidden_dir or _is_relative_to(resolved, forbidden_dir):
            print(
                "Error: unsafe output path — resolved path is under a tracked "
                f"repository directory ({forbidden_dir.name!r}). Use local_data/ "
                "or an absolute path outside the project for test/dev outputs.",
                file=sys.stderr,
            )
            sys.exit(2)


# ---------------------------------------------------------------------------
# JSON renderer
# ---------------------------------------------------------------------------

def _render_json(report: dict, max_items: Optional[int]) -> str:
    """Render the report as JSON, optionally capping queue items."""
    out = dict(report)
    if max_items is not None and max_items > 0:
        out = _cap_queue(out, max_items)
    return json.dumps(out, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_markdown(report: dict, max_items: Optional[int]) -> str:
    """Render the report as a human-readable Markdown briefing."""
    lines: list[str] = []

    generated_at = report.get("generated_at_utc", "")
    advisory_label = report.get("advisory_label", _ADVISORY_LABEL)
    qs = report.get("queue_summary") or {}
    total = qs.get("total_markets", 0)
    review_first = qs.get("review_first_count", 0)
    manual_source = qs.get("manual_source_review_required_count", 0)
    review_later = qs.get("review_later_count", 0)
    blocked = qs.get("data_quality_blocked_count", 0)
    deprio = qs.get("deprioritized_count", 0)

    lines.append("# Local Research Queue Briefing")
    lines.append("")
    lines.append(f"> **{_ADVISORY_NOTICE}**")
    lines.append("")
    if generated_at:
        lines.append(f"Generated at UTC: `{generated_at}`")
        lines.append("")

    # Queue summary
    lines.append("## Queue Summary")
    lines.append("")
    lines.append(f"- Total markets in input: {total}")
    lines.append(f"- Review First: {review_first}")
    lines.append(f"- Manual Source Review Required: {manual_source}")
    lines.append(f"- Review Later: {review_later}")
    lines.append(f"- Data Quality Blocked: {blocked}")
    lines.append(f"- Deprioritized: {deprio}")
    lines.append("")

    # Global warnings
    global_warnings: list[str] = report.get("global_warnings") or []
    if global_warnings:
        lines.append("## Global Warnings")
        lines.append("")
        for w in global_warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Build bucket → packets mapping
    all_packets: list[dict] = list(report.get("review_queue") or [])
    all_packets += list(report.get("excluded_or_deprioritized") or [])
    if max_items is not None and max_items > 0:
        all_packets = all_packets[:max_items]

    buckets: dict[str, list[dict]] = {b: [] for b in _BUCKET_ORDER}
    for pkt in all_packets:
        b = pkt.get("research_queue_bucket", "DEPRIORITIZED")
        if b in buckets:
            buckets[b].append(pkt)
        else:
            buckets.setdefault(b, []).append(pkt)

    for bucket in _BUCKET_ORDER:
        packets = buckets.get(bucket, [])
        heading = _BUCKET_HEADINGS.get(bucket, bucket)
        lines.append(f"## {heading}")
        lines.append("")
        if not packets:
            lines.append("_No items in this bucket._")
            lines.append("")
            continue
        for pkt in packets:
            lines += _render_packet_md(pkt)
        lines.append("")

    # Forbidden interpretation notice at end
    lines.append("---")
    lines.append("")
    lines.append(f"> **{_FORBIDDEN_INTERPRETATION_NOTICE}**")
    lines.append("")

    return "\n".join(lines)


def _render_packet_md(pkt: dict) -> list[str]:
    """Render a single research session packet as Markdown lines."""
    lines: list[str] = []
    rank = pkt.get("queue_rank", "?")
    market_id = pkt.get("market_id", "")
    question = pkt.get("question", "")
    bucket = pkt.get("research_queue_bucket", "")
    priority = pkt.get("research_review_priority", "")
    score = pkt.get("research_priority_score")
    score_str = f"{score:.4f}" if score is not None else "N/A"
    human_review = pkt.get("human_review_required", True)
    review_reasons = pkt.get("review_reasons") or []
    caution_flags = pkt.get("blocking_or_caution_flags") or []

    lines.append(
        f"### [{rank}] {question or market_id}"
    )
    lines.append("")
    lines.append(f"- **Market ID**: `{market_id}`")
    lines.append(f"- **Queue bucket**: `{bucket}`")
    lines.append(f"- **Research review priority**: `{priority}`")
    lines.append(f"- **Research priority score**: `{score_str}`")
    lines.append(f"- **Human review required**: `{human_review}`")

    if review_reasons:
        lines.append(f"- **Review reasons**: {', '.join(f'`{r}`' for r in review_reasons)}")
    if caution_flags:
        lines.append(f"- **Caution flags**: {', '.join(f'`{f}`' for f in caution_flags)}")

    # Data quality summary (compact)
    dqs = pkt.get("data_quality_summary") or {}
    if dqs:
        q_status = dqs.get("quality_status", "UNKNOWN")
        lines.append(f"- **Data quality status**: `{q_status}`")

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Queue cap helper
# ---------------------------------------------------------------------------

def _cap_queue(report: dict, max_items: int) -> dict:
    """Return a copy of report with review_queue capped to max_items."""
    out = dict(report)
    rq = list(report.get("review_queue") or [])
    excl = list(report.get("excluded_or_deprioritized") or [])
    combined = rq + excl
    combined = combined[:max_items]
    # Redistribute back into the report buckets.
    new_rq = []
    new_excl = []
    for pkt in combined:
        b = pkt.get("research_queue_bucket", "DEPRIORITIZED")
        if b in ("DATA_QUALITY_BLOCKED", "DEPRIORITIZED"):
            new_excl.append(pkt)
        else:
            new_rq.append(pkt)
    out["review_queue"] = new_rq
    out["excluded_or_deprioritized"] = new_excl
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Local/offline/read-only manual research queue export. "
            "Advisory-only. Not a trading signal."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=pathlib.Path,
        help=(
            "Path to a local JSON input file containing either a list of "
            "prepared market contexts or an already-built WP64 "
            "LOCAL_HUMAN_REVIEW_REPORT_V1 object."
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
            "Recommended: local_data/research_queue_exports/ (git-ignored)."
        ),
    )
    parser.add_argument(
        "--generated-at-utc",
        dest="generated_at_utc",
        default=None,
        help=(
            "Optional ISO timestamp override for generated_at_utc field "
            "(e.g. 2026-06-11T09:00:00+00:00). Useful for deterministic tests."
        ),
    )
    parser.add_argument(
        "--max-items",
        dest="max_items",
        type=int,
        default=None,
        help="Optional cap on the number of queue items in the output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    # Validate format before any file I/O.
    if args.output_format not in {"json", "markdown"}:
        print(f"Error: unsupported format: {args.output_format!r}", file=sys.stderr)
        sys.exit(1)

    # Validate output path before any processing.
    if args.output is not None:
        _check_output_path(args.output)

    # Load and validate input.
    report = _load_input(args.input)

    # Apply timestamp override.
    if args.generated_at_utc:
        report = _apply_generated_at_override(report, args.generated_at_utc)

    # Render.
    if args.output_format == "json":
        output_text = _render_json(report, args.max_items)
    else:
        output_text = _render_markdown(report, args.max_items)

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
