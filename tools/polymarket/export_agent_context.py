"""CLI for the local offline read-only agent context exporter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.agent_context.exporter import (
    build_agent_context_export,
    write_agent_context_export,
)


def main(argv: list[str] | None = None, *, repo_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local offline read-only agent context package from "
            "repo-approved local inputs. Default behavior writes no file."
        )
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional JSON output path under local_data/agent_context_exports/.",
    )
    parser.add_argument(
        "--include-local-report-metadata",
        action="store_true",
        default=False,
        help="Include metadata only for allowlisted ignored local report paths.",
    )
    parser.add_argument(
        "--include-excerpts",
        action="store_true",
        default=False,
        help="Include bounded sanitized excerpts for allowlisted tracked docs.",
    )
    parser.add_argument(
        "--max-excerpt-chars",
        type=int,
        default=1200,
        help="Maximum sanitized excerpt characters per included tracked doc.",
    )

    args = parser.parse_args(argv)

    try:
        export_data = build_agent_context_export(
            repo_root=repo_root,
            include_local_report_metadata=args.include_local_report_metadata,
            include_excerpts=args.include_excerpts,
            max_excerpt_chars=max(0, args.max_excerpt_chars),
        )
        output_written = "no"
        if args.out is not None:
            written = write_agent_context_export(export_data, args.out, repo_root=repo_root)
            output_written = str(written)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"schema version: {export_data['schema_version']}")
    print(f"export mode: {export_data['export_mode']}")
    print(f"source commit: {export_data['source_commit']}")
    print(f"included artifact count: {len(export_data['included_local_artifacts'])}")
    print(f"deferred item count: {len(export_data['deferred_items'])}")
    print(f"output written: {output_written}")
    print(
        "safety: no network, no credentials, no orders, "
        "no Hermes runtime, no execution authority"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
