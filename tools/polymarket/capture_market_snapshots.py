"""Manual read-only snapshot capture tool for Polymarket market metadata.

Requires --allow-network to make any network request.
Without --allow-network, exits 0 and prints usage guidance.

Writes to local_data/polymarket/snapshots/ by default.
No credentials. No trading. No automated polling.

PROHIBITED — this tool must never:
- Make any network call without --allow-network being passed explicitly.
- Accept, read, print, or log credentials, API keys, private keys, or secrets.
- Place, cancel, sign, submit, post, or simulate orders.
- Run continuously or schedule repeated requests.
- Write outside the approved local_data/ directory.

See docs/polymarket_snapshot_persistence.md for design and safety record.
See docs/deferred_items_log.md WP8-D002 for rate-limit status.

Usage:
    python tools/polymarket/capture_market_snapshots.py
    python tools/polymarket/capture_market_snapshots.py --help
    python tools/polymarket/capture_market_snapshots.py --allow-network --markets-limit 3
    python tools/polymarket/capture_market_snapshots.py \\
        --allow-network --markets-limit 3 --include-order-books --max-order-books 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow imports from repo root when run directly as a script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.snapshot_capture import capture_market_snapshots  # noqa: E402
from src.data_layer.polymarket.snapshot_writer import DEFAULT_OUTPUT_DIR, SnapshotWriter  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capture_market_snapshots.py",
        description=(
            "Read-only Polymarket market metadata snapshot capture tool.\n"
            "\n"
            "Fetches public market data via GET-only endpoints and writes\n"
            "normalized JSONL snapshots to an ignored local directory.\n"
            "\n"
            "Requires --allow-network to make any network request.\n"
            "No credentials are used. No orders are placed.\n"
            "Rate-limit policy not confirmed (WP8-D002 OPEN) — do not\n"
            "use for automated or frequent scanning.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help=(
            "Explicitly allow GET-only network requests to public Polymarket endpoints. "
            "Without this flag the tool exits 0 with no network calls made."
        ),
    )
    parser.add_argument(
        "--markets-limit",
        type=int,
        default=3,
        metavar="N",
        help="Maximum number of markets to fetch from GET /markets (default: 3).",
    )
    parser.add_argument(
        "--include-order-books",
        action="store_true",
        default=False,
        help=(
            "Also fetch CLOB order-book snapshots for outcome tokens. "
            "Requires --max-order-books > 0."
        ),
    )
    parser.add_argument(
        "--max-order-books",
        type=int,
        default=2,
        metavar="N",
        help=(
            "Maximum number of order-book token snapshots to fetch (default: 2). "
            "Only used when --include-order-books is set."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        metavar="PATH",
        help=(
            f"Output directory for snapshot files (default: {DEFAULT_OUTPUT_DIR}). "
            "Must be under local_data/."
        ),
    )
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.allow_network:
        print(
            "capture_market_snapshots.py: --allow-network not passed. No network calls made.\n"
            "\n"
            "To capture snapshots, run with --allow-network:\n"
            "\n"
            "  python tools/polymarket/capture_market_snapshots.py \\\n"
            "    --allow-network --markets-limit 3\n"
            "\n"
            "Optional order-book capture:\n"
            "\n"
            "  python tools/polymarket/capture_market_snapshots.py \\\n"
            "    --allow-network --markets-limit 3 --include-order-books --max-order-books 2\n"
            "\n"
            "Default output: local_data/polymarket/snapshots/ (git-ignored).\n"
            "No credentials used. No orders placed.\n"
            "Run with --help for full usage.\n"
        )
        return 0

    print(f"[capture] Fetching up to {args.markets_limit} markets from public Gamma API ...")
    if args.include_order_books:
        print(
            f"[capture] Order books: up to {args.max_order_books} token(s) "
            "from public CLOB API."
        )
    print(f"[capture] Output directory: {args.output_dir}")
    print()

    try:
        market_records, ob_records, manifest = capture_market_snapshots(
            allow_network=True,
            markets_limit=args.markets_limit,
            include_order_books=args.include_order_books,
            max_order_books=args.max_order_books if args.include_order_books else 0,
        )
    except Exception as exc:
        print(f"[capture] ERROR during capture: {exc}", file=sys.stderr)
        return 1

    writer = SnapshotWriter(output_dir=args.output_dir)
    result = writer.write_all(market_records, ob_records, manifest)

    if not result.success:
        print(f"[capture] ERROR writing snapshots: {result.error}", file=sys.stderr)
        return 1

    print(f"[capture] Markets written:     {result.markets_written}")
    print(f"[capture] Order books written: {result.order_books_written}")
    print(f"[capture] Manifest:            {result.manifest_file}")
    if result.markets_file:
        print(f"[capture] Market JSONL:        {result.markets_file}")
    if result.order_books_file:
        print(f"[capture] Order book JSONL:    {result.order_books_file}")
    print()
    print("[capture] Done. No credentials used. No orders placed.")
    print(
        "[capture] Note: Rate-limit policy not confirmed (WP8-D002 OPEN). "
        "Do not use for automated or frequent scanning."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
