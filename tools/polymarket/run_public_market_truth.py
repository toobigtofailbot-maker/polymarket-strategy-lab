"""Manual foreground public market-truth acquisition runtime CLI (WP169).

READ-ONLY PUBLIC DATA ONLY. Requires --allow-network to make any network call;
without it the tool prints sanitized usage guidance and exits 0. Output is a
sanitized JSON receipt: closed status/error/stop-reason codes, counts, and the
checkpoint sequence only -- never URLs, headers, paths, response bodies, raw
invalid inputs, or exception text.

PROHIBITED -- this tool must never:
- Make any network call without --allow-network being passed explicitly.
- Accept, read, print, or log credentials, API keys, private keys, or secrets.
- Place, cancel, sign, submit, post, or simulate orders.
- Install a service, daemon, scheduler, or background worker.
- Write outside the approved ignored local_data/polymarket directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.market_truth import (  # noqa: E402
    AcquisitionReceipt,
    MarketTruthError,
    MarketTruthRuntimeConfig,
)
from src.data_layer.polymarket.market_truth_runtime import (  # noqa: E402
    run_market_truth_runtime,
)

_OUTPUT_ROOT = _REPO_ROOT / "local_data" / "polymarket"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual foreground public Polymarket market-truth acquisition."
    )
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--asset-id", action="append", default=[], dest="asset_ids")
    parser.add_argument("--discover-active", action="store_true")
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--onchain-lookback-blocks", type=int, default=100)
    parser.add_argument("--wallet", default=None)
    parser.add_argument("--condition-id", default=None)
    parser.add_argument("--rpc-provider", default="drpc")
    parser.add_argument("--from-block", type=int, default=None)
    parser.add_argument("--to-block", type=int, default=None)
    parser.add_argument("--output-db", required=True)
    return parser


def _resolve_output(output_db: str) -> pathlib.Path | None:
    """Return a path strictly beneath the ignored local_data/polymarket dir, else None."""
    candidate = pathlib.Path(output_db)
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / candidate)
    try:
        resolved_parent = candidate.parent.resolve()
        root = _OUTPUT_ROOT.resolve()
    except OSError:
        return None
    if resolved_parent != root and root not in resolved_parent.parents:
        return None
    if candidate.suffix != ".sqlite3":
        return None
    return candidate


def _print_receipt(receipt: AcquisitionReceipt) -> None:
    payload = {
        "status": receipt.status,
        "error_codes": list(receipt.error_codes),
        "raw_count": receipt.raw_count,
        "normalized_count": receipt.normalized_count,
        "quarantined_count": receipt.quarantined_count,
        "gap_count": receipt.gap_count,
        "checkpoint_sequence": receipt.checkpoint_sequence,
        "store_bytes": receipt.store_bytes,
        "stop_reason": receipt.stop_reason,
    }
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    if not args.allow_network:
        sys.stdout.write(
            json.dumps(
                {
                    "status": "NO_NETWORK",
                    "note": "Pass --allow-network to perform bounded public unauthenticated acquisition.",
                },
                separators=(",", ":"),
            )
            + "\n"
        )
        return 0

    resolved = _resolve_output(args.output_db)
    if resolved is None:
        sys.stdout.write(json.dumps({"status": "FAILED", "error_codes": ["STORE_CONFLICT"]}) + "\n")
        return 1
    try:
        _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError:
        sys.stdout.write(json.dumps({"status": "FAILED", "error_codes": ["STORE_CONFLICT"]}) + "\n")
        return 1

    config = MarketTruthRuntimeConfig(
        output_db=resolved,
        asset_ids=tuple(args.asset_ids),
        discover_active=args.discover_active,
        duration_seconds=args.duration_seconds,
        max_pages=args.max_pages,
        wallet=args.wallet,
        condition_id=args.condition_id,
        rpc_provider=args.rpc_provider,
        from_block=args.from_block,
        to_block=args.to_block,
        onchain_lookback_blocks=args.onchain_lookback_blocks,
    )

    stop_event = asyncio.Event()
    try:
        # The default runtime path performs the full certified Polygon RPC acquisition; no
        # transport injection is required (nor permitted by the frozen public signature).
        receipt = asyncio.run(run_market_truth_runtime(config, stop_event))
    except MarketTruthError as error:
        sys.stdout.write(
            json.dumps({"status": "FAILED", "error_codes": list(error.error_codes)}) + "\n"
        )
        return 3
    except Exception:
        sys.stdout.write(
            json.dumps({"status": "FAILED", "error_codes": ["INTERNAL_CLOSED_FAILURE"]}) + "\n"
        )
        return 3

    _print_receipt(receipt)
    if receipt.status == "FAILED":
        # Provider/network unavailability is an operational limitation, not proof.
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
