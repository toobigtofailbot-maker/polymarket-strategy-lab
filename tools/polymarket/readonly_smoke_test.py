"""Optional manual smoke test for the read-only Polymarket public adapter.

SAFETY: This script makes NO network calls unless --allow-network is passed.
        It performs GET-only requests to public endpoints.
        It uses no credentials.
        It does not place, cancel, or sign orders.
        It is NOT run by pytest.

Usage:
    python tools/polymarket/readonly_smoke_test.py --help
    python tools/polymarket/readonly_smoke_test.py --allow-network --markets-limit 3
"""

import argparse
import sys
import textwrap
import time
from pathlib import Path

# Allow imports from repo root when run directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket import (
    PolymarketPublicClient,
    PolymarketReadOnlyError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""\
            Optional manual smoke test for the read-only Polymarket public adapter.
            Makes no network calls unless --allow-network is passed.
            Performs GET-only requests. No credentials. No order placement.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help="Required to enable actual network calls. Without this flag the script exits immediately.",
    )
    parser.add_argument(
        "--markets-limit",
        type=int,
        default=3,
        metavar="N",
        help="Number of markets to fetch (default: 3).",
    )
    parser.add_argument(
        "--gamma-base-url",
        default="https://gamma-api.polymarket.com",
        help="Gamma API base URL (default: https://gamma-api.polymarket.com).",
    )
    parser.add_argument(
        "--clob-base-url",
        default="https://clob.polymarket.com",
        help="CLOB API base URL (default: https://clob.polymarket.com).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 10).",
    )
    return parser.parse_args()


def summarize_markets(data: object, limit: int) -> None:
    if not isinstance(data, list):
        print(f"  Markets response is not a list (type={type(data).__name__}). Raw snippet:")
        print(f"  {str(data)[:300]}")
        return
    print(f"  Received {len(data)} market(s) (requested up to {limit}).")
    for i, m in enumerate(data[:limit]):
        if isinstance(m, dict):
            q = m.get("question", m.get("title", "(no question field)"))
            cid = m.get("conditionId", m.get("condition_id", "(no condition_id)"))
            print(f"  [{i+1}] condition_id={cid!r}  question={str(q)[:80]!r}")
        else:
            print(f"  [{i+1}] unexpected item type: {type(m).__name__}")


def run_health_check(client: PolymarketPublicClient) -> bool:
    print("\n[1] CLOB health check")
    print(f"  Endpoint: GET {client._clob_base_url}/health  (UNVERIFIED contract)")
    try:
        result = client.get_health()
        info = result.request_info
        print(f"  HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        if isinstance(result.data, dict):
            print(f"  Response: {dict(list(result.data.items())[:5])}")
        else:
            print(f"  Response type: {type(result.data).__name__}")
        return True
    except PolymarketReadOnlyError as exc:
        print(f"  FAILED: {exc}")
        return False


def run_markets_fetch(client: PolymarketPublicClient, limit: int) -> bool:
    print(f"\n[2] Gamma markets list (limit={limit})")
    print(f"  Endpoint: GET {client._gamma_base_url}/markets?limit={limit}  (UNVERIFIED contract)")
    try:
        result = client.get_markets(limit=limit)
        info = result.request_info
        print(f"  HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        summarize_markets(result.data, limit)
        return True
    except PolymarketReadOnlyError as exc:
        print(f"  FAILED: {exc}")
        return False


def main() -> int:
    args = parse_args()

    if not args.allow_network:
        print("Smoke test: --allow-network not passed. No network calls made. Exiting.")
        print("Pass --allow-network to run actual endpoint checks.")
        return 0

    print("=" * 70)
    print("Polymarket Read-Only Smoke Test")
    print("GET-only. No credentials. No orders. No trading.")
    print("Endpoint contracts are UNVERIFIED (WP8 evaluation scope).")
    print("=" * 70)

    client = PolymarketPublicClient(
        gamma_base_url=args.gamma_base_url,
        clob_base_url=args.clob_base_url,
        timeout_seconds=args.timeout,
    )

    results = []
    results.append(run_health_check(client))
    results.append(run_markets_fetch(client, args.markets_limit))

    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed.")
    if passed < total:
        print("Some checks failed. This may indicate unverified endpoint paths.")
        print("See docs/polymarket_readonly_adapter_evaluation.md.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
