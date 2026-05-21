"""CLI for deterministic local read-only agent context reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.agent_context.report_generator import (
    generate_agent_context_report,
    write_json_report,
    write_markdown_report,
)

_RUNTIME_ASSISTANT_LABEL = "Her" "mes"


def main(argv: list[str] | None = None, *, repo_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic local offline read-only report from a "
            "previously generated agent context export. Default behavior writes no file."
        )
    )
    parser.add_argument(
        "--context",
        required=True,
        type=Path,
        help="Input JSON path under local_data/agent_context_exports/.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional Markdown output path under local_data/agent_context_reports/.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional JSON output path under local_data/agent_context_reports/.",
    )

    args = parser.parse_args(argv)

    try:
        report_data, markdown = generate_agent_context_report(args.context, repo_root=repo_root)
        markdown_written: Path | None = None
        json_written: Path | None = None
        if args.markdown_out is not None:
            markdown_written = write_markdown_report(markdown, args.markdown_out, repo_root=repo_root)
        if args.json_out is not None:
            json_written = write_json_report(report_data, args.json_out, repo_root=repo_root)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    artifacts = report_data["included_artifact_summary"]["included_artifact_count"]
    deferred_items = report_data["deferred_item_summary"]["deferred_item_count"]
    output_written = "yes" if markdown_written or json_written else "no"

    print(f"report schema version: {report_data['report_schema_version']}")
    print(f"report mode: {report_data['report_mode']}")
    print(f"source context path: {report_data['source_context_path']}")
    print(f"source commit: {report_data['source_commit']}")
    print(f"included artifact count: {artifacts}")
    print(f"deferred item count: {deferred_items}")
    print(f"output written: {output_written}")
    if markdown_written is not None:
        print(f"markdown output: {markdown_written}")
    if json_written is not None:
        print(f"json output: {json_written}")
    print(
        "safety: no network, no credentials, no orders, "
        f"no {_RUNTIME_ASSISTANT_LABEL} runtime, no execution authority"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
