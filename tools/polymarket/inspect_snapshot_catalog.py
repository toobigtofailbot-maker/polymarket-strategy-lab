"""Offline CLI inspection tool for WP10 local snapshot catalog.

Reads local snapshot JSONL files and manifests from local_data/polymarket/snapshots/
and prints a sanitized summary. Makes no network calls. Requires no credentials.
Does not run continuously. Does not schedule polling.

Usage:
  python tools/polymarket/inspect_snapshot_catalog.py
  python tools/polymarket/inspect_snapshot_catalog.py --input-dir local_data/polymarket/snapshots/
  python tools/polymarket/inspect_snapshot_catalog.py --show-markets 5
  python tools/polymarket/inspect_snapshot_catalog.py --market-id <market_id>
  python tools/polymarket/inspect_snapshot_catalog.py --strict
  python tools/polymarket/inspect_snapshot_catalog.py --summary-json local_data/polymarket/catalog/summary.local.json

PROHIBITED — this tool must never:
- Make network calls.
- Import PolymarketPublicClient or any network adapter.
- Read .env files or credentials.
- Accept private keys, API keys, wallet keys, mnemonics, or secrets.
- Place, cancel, sign, submit, post, or simulate orders.
- Run continuously or schedule polling.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.snapshot_reader import (
    list_snapshot_files,
    load_market_snapshot_records,
    load_order_book_snapshot_records,
    load_snapshot_manifests,
)
from src.data_layer.polymarket.market_catalog import MarketCatalog

_DEFAULT_INPUT_DIR = Path("local_data") / "polymarket" / "snapshots"
_APPROVED_OUTPUT_ROOT = "local_data"


def _validate_summary_output_path(path: Path) -> None:
    resolved = path.resolve()
    parts_lower = [p.lower() for p in resolved.parts]
    if _APPROVED_OUTPUT_ROOT not in parts_lower:
        raise ValueError(
            f"Summary output path {str(path)!r} is not under 'local_data/'. "
            "Catalog summary files must be written to local_data/."
        )


def _print_separator() -> None:
    print("-" * 60)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline inspection tool for WP10 local Polymarket snapshot catalog. "
            "Makes no network calls. Requires no credentials."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=_DEFAULT_INPUT_DIR,
        help="Directory containing snapshot JSONL and manifest files. "
             f"Default: {_DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Raise on malformed JSONL lines instead of skipping them.",
    )
    parser.add_argument(
        "--show-markets",
        type=int,
        default=0,
        metavar="N",
        help="Print a sample of up to N markets from the catalog.",
    )
    parser.add_argument(
        "--market-id",
        type=str,
        default=None,
        metavar="MARKET_ID",
        help="Print detail for a specific market_id.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Export sanitized summary JSON to a local ignored path "
             "(must be under local_data/).",
    )

    args = parser.parse_args(argv)
    input_dir: Path = args.input_dir
    strict: bool = args.strict

    print("Polymarket Snapshot Catalog Inspector (offline)")
    print(f"Input directory: {input_dir}")
    _print_separator()

    file_summary = list_snapshot_files(input_dir)

    if not Path(input_dir).exists():
        print(f"Notice: input directory does not exist: {input_dir}")
        print("No snapshot files to load.")
        return 0

    print(f"Markets JSONL present:     {file_summary.markets_file_present}")
    print(f"Order-books JSONL present: {file_summary.order_books_file_present}")
    print(f"Manifest files found:      {file_summary.manifest_count}")
    _print_separator()

    market_result = load_market_snapshot_records(input_dir, strict=strict)
    ob_result = load_order_book_snapshot_records(input_dir, strict=strict)
    manifest_result = load_snapshot_manifests(input_dir, strict=strict)

    print(f"Market records loaded:     {len(market_result.records)}")
    if market_result.errors:
        print(f"  Skipped (malformed):   {market_result.lines_skipped}")

    print(f"Order-book records loaded: {len(ob_result.records)}")
    if ob_result.errors:
        print(f"  Skipped (malformed):   {ob_result.lines_skipped}")

    print(f"Manifests loaded:          {len(manifest_result.records)}")
    if manifest_result.errors:
        print(f"  Skipped (malformed):   {manifest_result.lines_skipped}")

    _print_separator()

    if not market_result.records:
        print("No market records loaded. Catalog is empty.")
        return 0

    build_result = MarketCatalog.from_market_records(market_result.records)
    catalog = build_result.catalog
    cat_summary = catalog.summary()

    print(f"Unique markets:            {cat_summary['unique_market_count']}")
    print(f"Total tokens:              {cat_summary['total_token_count']}")
    print(f"Snapshot run IDs:          {cat_summary['snapshot_id_count']}")

    if cat_summary["snapshot_ids"]:
        latest_snap = max(cat_summary["snapshot_ids"])
        print(f"Latest snapshot_id:        {latest_snap}")

    _print_separator()

    if cat_summary["category_distribution"]:
        print("Category distribution:")
        for cat, count in sorted(
            cat_summary["category_distribution"].items(),
            key=lambda x: -x[1],
        ):
            print(f"  {cat or 'unknown':<30} {count}")
        _print_separator()

    if cat_summary["status_distribution"]:
        print("Status distribution:")
        for status, count in sorted(
            cat_summary["status_distribution"].items(),
            key=lambda x: -x[1],
        ):
            print(f"  {status:<30} {count}")
        _print_separator()

    if args.market_id:
        market = catalog.get_market(args.market_id)
        if market is None:
            print(f"Market not found: {args.market_id}")
        else:
            print(f"Market detail: {args.market_id}")
            print(f"  Question:      {market.question}")
            print(f"  Status:        {market.market_status}")
            print(f"  Category:      {market.category}")
            print(f"  Resolution:    {market.resolution_date}")
            print(f"  Snapshot:      {market.snapshot_id}")
            print(f"  Captured:      {market.captured_at_utc}")
            print(f"  Tokens ({len(market.outcome_tokens)}):")
            for token in market.outcome_tokens:
                print(f"    {token.outcome_label}: {token.token_id}")
        _print_separator()

    if args.show_markets and args.show_markets > 0:
        print(f"Sample markets (up to {args.show_markets}):")
        market_ids = catalog.list_market_ids()[: args.show_markets]
        for mid in market_ids:
            m = catalog.get_market(mid)
            if m:
                q = m.question[:70] + "..." if len(m.question) > 70 else m.question
                print(f"  {mid[:12]}...  [{m.market_status}]  {q}")
        _print_separator()

    if args.summary_json:
        out_path = Path(args.summary_json)
        try:
            _validate_summary_output_path(out_path)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        out_path.parent.mkdir(parents=True, exist_ok=True)
        export = {
            "input_dir": str(input_dir),
            "market_record_count": len(market_result.records),
            "order_book_record_count": len(ob_result.records),
            "manifest_count": len(manifest_result.records),
            "catalog_summary": cat_summary,
        }
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(export, fh, indent=2)
        print(f"Summary written to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
