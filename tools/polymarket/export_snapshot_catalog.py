"""Manual offline local snapshot catalog export tool.

Reads local snapshot files from local_data/polymarket/snapshots/ by default,
optionally deduplicates records, builds an in-memory catalog, and writes
sanitized exports only when explicit local_data output paths are provided.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.catalog_exports import (
    render_catalog_export_json,
    render_catalog_markets_csv,
    write_local_csv_export,
    write_local_json_export,
)
from src.data_layer.polymarket.market_catalog import MarketCatalog
from src.data_layer.polymarket.snapshot_deduplication import (
    deduplicate_market_records,
    deduplicate_order_book_records,
    summarize_deduplication,
)
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
            "Offline local catalog exporter for Polymarket snapshot files. "
            "Reads local files only and writes only when explicit local_data "
            "output paths are provided."
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
        "--deduplicate",
        action="store_true",
        default=False,
        help="Apply deterministic local record deduplication before catalog export.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional sanitized JSON export path under local_data/.",
    )
    parser.add_argument(
        "--csv-out",
        type=Path,
        default=None,
        help="Optional sanitized CSV export path under local_data/.",
    )
    parser.add_argument(
        "--max-markets",
        type=int,
        default=0,
        help="Maximum number of market summary rows to print to the console.",
    )

    args = parser.parse_args(argv)
    input_dir = Path(args.input_dir)

    print("Polymarket Snapshot Catalog Export (offline)")
    print(f"Input directory: {input_dir}")
    print("Writes files only when explicit local_data output paths are provided.")
    _print_separator()

    file_summary = list_snapshot_files(input_dir)
    if not input_dir.exists():
        print(f"Notice: input directory does not exist: {input_dir}")
        print("No snapshot files to load.")
        return 0

    try:
        market_result = load_market_snapshot_records(input_dir, strict=args.strict)
        order_book_result = load_order_book_snapshot_records(input_dir, strict=args.strict)
        manifest_result = load_snapshot_manifests(input_dir, strict=args.strict)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    market_records = list(market_result.records)
    order_book_records = list(order_book_result.records)
    dedup_summary = {}

    if args.deduplicate:
        market_dedup = deduplicate_market_records(market_records)
        order_book_dedup = deduplicate_order_book_records(order_book_records)
        market_records = list(market_dedup.records)
        order_book_records = list(order_book_dedup.records)
        dedup_summary = {
            "markets": summarize_deduplication(market_dedup),
            "order_books": summarize_deduplication(order_book_dedup),
        }

    catalog_build = MarketCatalog.from_market_records(market_records)
    catalog = catalog_build.catalog
    summary = catalog.summary()

    print(f"Markets JSONL present:       {file_summary.markets_file_present}")
    print(f"Order-books JSONL present:   {file_summary.order_books_file_present}")
    print(f"Manifest files found:        {file_summary.manifest_count}")
    print(f"Market records loaded:       {len(market_result.records)}")
    print(f"Order-book records loaded:   {len(order_book_result.records)}")
    print(f"Manifest records loaded:     {len(manifest_result.records)}")
    _print_separator()
    print(f"Deduplication applied:       {bool(args.deduplicate)}")
    if args.deduplicate:
        print(f"Market duplicates removed:   {dedup_summary['markets']['exact_duplicate_count']}")
        print(f"Market conflicts retained:   {dedup_summary['markets']['conflict_count']}")
        print(f"Book duplicates removed:     {dedup_summary['order_books']['exact_duplicate_count']}")
        print(f"Book conflicts retained:     {dedup_summary['order_books']['conflict_count']}")
    print(f"Unique markets:              {summary['unique_market_count']}")
    print(f"Token count:                 {summary['total_token_count']}")
    print(f"Snapshot ID count:           {summary['snapshot_id_count']}")

    max_markets = max(args.max_markets, 0)
    if max_markets:
        _print_separator()
        print(f"Sample markets (up to {max_markets}):")
        for market_id in catalog.list_market_ids()[:max_markets]:
            market = catalog.get_market(market_id)
            if market is None:
                continue
            question = (
                market.question[:70] + "..."
                if len(market.question) > 70
                else market.question
            )
            print(f"  {market.market_id[:12]}... [{market.market_status}] {question}")

    if args.json_out:
        export_data = render_catalog_export_json(
            catalog,
            dedup_summary=dedup_summary,
        )
        try:
            written = write_local_json_export(export_data, args.json_out)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"JSON export written: {written}")

    if args.csv_out:
        csv_text = render_catalog_markets_csv(catalog)
        try:
            written = write_local_csv_export(csv_text, args.csv_out)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"CSV export written: {written}")

    _print_separator()
    print("Safety: offline local export only; no network, credentials, orders, or automation.")
    return 0


def _print_separator() -> None:
    print("-" * 60)


if __name__ == "__main__":
    raise SystemExit(main())
