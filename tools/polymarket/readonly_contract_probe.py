"""Read-only Polymarket endpoint contract probe for WP9.

SAFETY: This script makes NO network calls unless --allow-network is passed.
        It performs GET-only requests to public endpoints.
        It uses no credentials, private keys, or secrets.
        It does not place, cancel, or sign orders.
        It is NOT run by pytest.
        Output reports are written only to ignored local paths.

Purpose:
    Validate the Polymarket public endpoint contracts introduced in WP8 before
    adding snapshot persistence, automated polling, or SDK dependencies.

Usage:
    python tools/polymarket/readonly_contract_probe.py --help
    python tools/polymarket/readonly_contract_probe.py --allow-network --markets-limit 3
    python tools/polymarket/readonly_contract_probe.py --allow-network --markets-limit 3 --report-path security-scan-output/contract_probe_report.json
"""

import argparse
import json
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

# Identifiers discovered during probe; used only for chained endpoint probes.
_NO_NETWORK_MESSAGE = textwrap.dedent("""\
    Contract probe: --allow-network not passed. No network calls made. Exiting.

    To run actual endpoint contract validation:
        python tools/polymarket/readonly_contract_probe.py --allow-network --markets-limit 3

    Purpose: validate Polymarket public endpoint contracts (WP9).
    - GET-only requests to public Polymarket endpoints.
    - No credentials, private keys, or secrets are used or accepted.
    - No orders are placed, cancelled, or signed.
    - Any --report-path output is written to an ignored local directory.
""")

DISALLOWED_SECRET_TERMS = (
    "private_key",
    "api_key",
    "api_secret",
    "wallet",
    "mnemonic",
    "passphrase",
    "bearer ",
    "-----BEGIN",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""\
            Read-only Polymarket endpoint contract probe (WP9).
            Validates current public endpoint response shapes.
            Makes no network calls unless --allow-network is passed.
            GET-only. No credentials. No order placement.
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
        help="Number of markets to fetch from Gamma /markets (default: 3).",
    )
    parser.add_argument(
        "--gamma-base-url",
        default="https://gamma-api.polymarket.com",
        help="Gamma API base URL.",
    )
    parser.add_argument(
        "--clob-base-url",
        default="https://clob.polymarket.com",
        help="CLOB API base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        metavar="PATH",
        help=(
            "Write a sanitized JSON report to this path. "
            "Use an ignored directory (e.g. security-scan-output/). "
            "No report is written if not specified."
        ),
    )
    return parser.parse_args()


def _sanitize_text(value: str) -> str:
    """Reject strings that look like secrets."""
    for term in DISALLOWED_SECRET_TERMS:
        if term.lower() in value.lower():
            return "[REDACTED — looks like a secret term]"
    return value


def _safe_str(value: object, max_len: int = 120) -> str:
    s = str(value)[:max_len]
    return _sanitize_text(s)


def _summarize_field_names(data: object) -> list[str]:
    if isinstance(data, dict):
        return sorted(data.keys())
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return sorted(data[0].keys())
    return []


def probe_clob_health(client: PolymarketPublicClient) -> dict:
    """Probe CLOB GET /health. Returns a sanitized result dict."""
    result = {
        "endpoint": "CLOB /health",
        "url": f"{client._clob_base_url}/health",
        "method": "GET",
        "status": "NOT_RUN",
        "http_status": None,
        "latency_ms": None,
        "response_type": None,
        "response_field_names": [],
        "notes": "",
    }
    print(f"\n[1] CLOB /health  (contract: UNVERIFIED)")
    print(f"    URL: {result['url']}")
    try:
        r = client.get_health()
        info = r.request_info
        result["http_status"] = info.status_code
        result["latency_ms"] = round(info.latency_ms, 1)
        result["response_type"] = type(r.data).__name__
        result["response_field_names"] = _summarize_field_names(r.data)
        result["status"] = "PASS"
        print(f"    HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        print(f"    Response type: {type(r.data).__name__}")
        if isinstance(r.data, dict):
            snippet = {k: _safe_str(v) for k, v in list(r.data.items())[:6]}
            print(f"    Response fields: {list(snippet.keys())}")
            print(f"    Sample: {snippet}")
            result["notes"] = f"Response fields: {list(snippet.keys())}"
        elif isinstance(r.data, str):
            print(f"    Response (string): {_safe_str(r.data, 200)}")
            result["notes"] = f"String response: {_safe_str(r.data, 80)}"
        else:
            print(f"    Unexpected response type: {type(r.data).__name__}")
            result["notes"] = f"Unexpected type: {type(r.data).__name__}"
    except PolymarketReadOnlyError as exc:
        result["status"] = "FAIL"
        result["notes"] = f"Error: {_safe_str(str(exc))}"
        print(f"    FAILED: {exc}")
    return result


def probe_gamma_markets(client: PolymarketPublicClient, limit: int) -> tuple[dict, list[dict]]:
    """Probe Gamma GET /markets. Returns (result dict, list of raw market dicts)."""
    result = {
        "endpoint": "Gamma /markets",
        "url": f"{client._gamma_base_url}/markets?limit={limit}",
        "method": "GET",
        "status": "NOT_RUN",
        "http_status": None,
        "latency_ms": None,
        "response_type": None,
        "response_is_list": None,
        "response_count": None,
        "first_record_field_names": [],
        "notes": "",
    }
    raw_markets: list[dict] = []
    print(f"\n[2] Gamma /markets?limit={limit}  (contract: UNVERIFIED)")
    print(f"    URL: {result['url']}")
    try:
        r = client.get_markets(limit=limit)
        info = r.request_info
        result["http_status"] = info.status_code
        result["latency_ms"] = round(info.latency_ms, 1)
        result["response_type"] = type(r.data).__name__
        result["response_is_list"] = isinstance(r.data, list)
        print(f"    HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        print(f"    Response type: {type(r.data).__name__}")

        if isinstance(r.data, list):
            result["response_count"] = len(r.data)
            print(f"    Records received: {len(r.data)} (requested limit={limit})")
            if r.data and isinstance(r.data[0], dict):
                fields = sorted(r.data[0].keys())
                result["first_record_field_names"] = fields
                print(f"    First record field names: {fields}")
                for i, m in enumerate(r.data[:limit]):
                    if isinstance(m, dict):
                        q = _safe_str(m.get("question", m.get("title", "(none)")))
                        cid = m.get("conditionId", m.get("condition_id", "(none)"))
                        mid = m.get("id", m.get("marketId", "(none)"))
                        print(f"    [{i+1}] id={_safe_str(str(mid))}  conditionId={_safe_str(str(cid))}  question={q!r}")
                        raw_markets.append(m)
                result["notes"] = f"Fields: {fields}"
            result["status"] = "PASS"
        elif isinstance(r.data, dict):
            # Some APIs wrap lists in an object
            possible_keys = ["markets", "data", "results", "items"]
            for k in possible_keys:
                if k in r.data and isinstance(r.data[k], list):
                    inner = r.data[k]
                    result["response_count"] = len(inner)
                    result["response_is_list"] = True
                    if inner and isinstance(inner[0], dict):
                        fields = sorted(inner[0].keys())
                        result["first_record_field_names"] = fields
                        raw_markets.extend(inner[:limit])
                    result["notes"] = f"Wrapped list under key '{k}'; fields: {result['first_record_field_names']}"
                    print(f"    Response is dict with list under key '{k}', count={len(inner)}")
                    result["status"] = "PASS"
                    break
            else:
                result["status"] = "SHAPE_MISMATCH"
                result["notes"] = f"Unexpected dict shape; top-level keys: {sorted(r.data.keys())}"
                print(f"    SHAPE MISMATCH: dict with keys {sorted(r.data.keys())}")
        else:
            result["status"] = "SHAPE_MISMATCH"
            result["notes"] = f"Unexpected response type: {type(r.data).__name__}"
            print(f"    SHAPE MISMATCH: unexpected type {type(r.data).__name__}")
    except PolymarketReadOnlyError as exc:
        result["status"] = "FAIL"
        result["notes"] = f"Error: {_safe_str(str(exc))}"
        print(f"    FAILED: {exc}")
    return result, raw_markets


def probe_gamma_market_by_id(client: PolymarketPublicClient, identifier: str) -> dict:
    """Probe Gamma GET /markets/{identifier}. Returns a sanitized result dict."""
    result = {
        "endpoint": "Gamma /markets/{identifier}",
        "url": f"{client._gamma_base_url}/markets/{identifier}",
        "method": "GET",
        "status": "NOT_RUN",
        "http_status": None,
        "latency_ms": None,
        "response_type": None,
        "response_field_names": [],
        "identifier_used": _safe_str(identifier),
        "notes": "",
    }
    print(f"\n[3] Gamma /markets/{{identifier}}  (contract: UNVERIFIED)")
    print(f"    identifier={_safe_str(identifier)}")
    print(f"    URL: {result['url']}")
    try:
        r = client.get_market(identifier)
        info = r.request_info
        result["http_status"] = info.status_code
        result["latency_ms"] = round(info.latency_ms, 1)
        result["response_type"] = type(r.data).__name__
        print(f"    HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        print(f"    Response type: {type(r.data).__name__}")
        if isinstance(r.data, dict):
            fields = sorted(r.data.keys())
            result["response_field_names"] = fields
            print(f"    Response field names: {fields}")
            result["status"] = "PASS"
            result["notes"] = f"Fields: {fields}"
        elif isinstance(r.data, list):
            result["status"] = "SHAPE_MISMATCH"
            result["notes"] = "Returned a list, expected a single market dict"
            print(f"    SHAPE MISMATCH: list returned instead of single dict")
        else:
            result["status"] = "SHAPE_MISMATCH"
            result["notes"] = f"Unexpected type: {type(r.data).__name__}"
            print(f"    SHAPE MISMATCH: unexpected type {type(r.data).__name__}")
    except PolymarketReadOnlyError as exc:
        result["status"] = "FAIL"
        result["notes"] = f"Error: {_safe_str(str(exc))}"
        print(f"    FAILED: {exc}")
    return result


def probe_clob_book(client: PolymarketPublicClient, token_id: str) -> dict:
    """Probe CLOB GET /book?token_id=... Returns a sanitized result dict."""
    result = {
        "endpoint": "CLOB /book",
        "url": f"{client._clob_base_url}/book?token_id={token_id}",
        "method": "GET",
        "status": "NOT_RUN",
        "http_status": None,
        "latency_ms": None,
        "response_type": None,
        "response_field_names": [],
        "token_id_used": _safe_str(token_id),
        "notes": "",
    }
    print(f"\n[4] CLOB /book?token_id=...  (contract: UNVERIFIED)")
    print(f"    token_id={_safe_str(token_id)}")
    print(f"    URL: {result['url']}")
    try:
        r = client.get_order_book_snapshot(token_id)
        info = r.request_info
        result["http_status"] = info.status_code
        result["latency_ms"] = round(info.latency_ms, 1)
        result["response_type"] = type(r.data).__name__
        print(f"    HTTP {info.status_code}  latency={info.latency_ms:.0f}ms")
        print(f"    Response type: {type(r.data).__name__}")
        if isinstance(r.data, dict):
            fields = sorted(r.data.keys())
            result["response_field_names"] = fields
            print(f"    Response field names: {fields}")
            has_bids = "bids" in r.data
            has_asks = "asks" in r.data
            result["status"] = "PASS" if (has_bids or has_asks) else "SHAPE_MISMATCH"
            result["notes"] = (
                f"Fields: {fields}; has_bids={has_bids}, has_asks={has_asks}"
            )
            print(f"    has_bids={has_bids}, has_asks={has_asks}")
            if has_bids and isinstance(r.data["bids"], list) and r.data["bids"]:
                print(f"    Sample bid: {r.data['bids'][0]}")
            if has_asks and isinstance(r.data["asks"], list) and r.data["asks"]:
                print(f"    Sample ask: {r.data['asks'][0]}")
        else:
            result["status"] = "SHAPE_MISMATCH"
            result["notes"] = f"Unexpected type: {type(r.data).__name__}"
            print(f"    SHAPE MISMATCH: unexpected type {type(r.data).__name__}")
    except PolymarketReadOnlyError as exc:
        result["status"] = "FAIL"
        result["notes"] = f"Error: {_safe_str(str(exc))}"
        print(f"    FAILED: {exc}")
    return result


def _extract_token_id(market: dict) -> str | None:
    """Try to extract a token_id from a market dict. Returns None if not found.

    WP9 finding: clobTokenIds is a JSON-encoded string (not a Python list).
    """
    import json as _json

    for field in ("tokens", "clobTokenIds", "tokenIds"):
        val = market.get(field)
        # WP9: clobTokenIds arrives as a JSON-encoded string
        if isinstance(val, str) and val.startswith("["):
            try:
                val = _json.loads(val)
            except Exception:
                continue
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, str) and first:
                return first
            if isinstance(first, dict):
                for sub in ("token_id", "tokenId", "id"):
                    if sub in first and first[sub]:
                        return str(first[sub])
    # Some APIs embed token_id directly
    for field in ("token_id", "tokenId"):
        val = market.get(field)
        if isinstance(val, str) and val:
            return val
    return None


def _extract_identifier(market: dict) -> str | None:
    """Try to extract the integer market id for /markets/{id} lookup.

    WP9 finding: The correct identifier for GET /markets/{id} is the integer
    numeric 'id' field (e.g. '540817'), NOT the conditionId hash. Using
    conditionId returns HTTP 422.
    """
    # Prefer numeric id first (WP9-confirmed identifier format)
    val = market.get("id")
    if val is not None:
        return str(val)
    for field in ("marketId", "conditionId", "condition_id"):
        val = market.get(field)
        if val is not None:
            return str(val)
    return None


def write_report(path: str, report: dict) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  Report written: {out}")


def main() -> int:
    args = parse_args()

    if not args.allow_network:
        print(_NO_NETWORK_MESSAGE)
        return 0

    print("=" * 72)
    print("Polymarket Read-Only Endpoint Contract Probe (WP9)")
    print("GET-only. No credentials. No orders. No trading.")
    print("Endpoint contracts are UNVERIFIED (WP8 evaluation scope).")
    print("=" * 72)

    client = PolymarketPublicClient(
        gamma_base_url=args.gamma_base_url,
        clob_base_url=args.clob_base_url,
        timeout_seconds=args.timeout,
    )

    probe_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report: dict = {
        "probe_tool": "readonly_contract_probe.py",
        "work_package": "WP9",
        "probe_timestamp_utc": probe_timestamp,
        "gamma_base_url": args.gamma_base_url,
        "clob_base_url": args.clob_base_url,
        "markets_limit": args.markets_limit,
        "probes": [],
        "token_id_discovered": None,
        "identifier_discovered": None,
        "sanitization_note": (
            "This report contains only public market metadata schema summaries. "
            "No private data, credentials, or large raw payloads are included."
        ),
    }

    # Probe 1: CLOB /health
    health_result = probe_clob_health(client)
    report["probes"].append(health_result)

    # Probe 2: Gamma /markets
    markets_result, raw_markets = probe_gamma_markets(client, args.markets_limit)
    report["probes"].append(markets_result)

    # Try to extract identifiers for chained probes
    identifier: str | None = None
    token_id: str | None = None
    if raw_markets:
        identifier = _extract_identifier(raw_markets[0])
        token_id = _extract_token_id(raw_markets[0])

    report["identifier_discovered"] = identifier
    report["token_id_discovered"] = token_id

    if identifier:
        print(f"\n  Discovered identifier for chained probe: {_safe_str(identifier)}")
    else:
        print("\n  No identifier extracted from markets response — skipping /markets/{id} probe.")

    if token_id:
        print(f"  Discovered token_id for chained probe: {_safe_str(token_id)}")
    else:
        print("  No token_id extracted from markets response — skipping /book probe.")

    # Probe 3: Gamma /markets/{identifier} (only if identifier found)
    if identifier:
        market_result = probe_gamma_market_by_id(client, identifier)
        report["probes"].append(market_result)
    else:
        report["probes"].append({
            "endpoint": "Gamma /markets/{identifier}",
            "status": "SKIPPED",
            "notes": "No identifier extracted from /markets response.",
        })

    # Probe 4: CLOB /book?token_id=... (only if token_id found)
    if token_id:
        book_result = probe_clob_book(client, token_id)
        report["probes"].append(book_result)
    else:
        report["probes"].append({
            "endpoint": "CLOB /book",
            "status": "SKIPPED",
            "notes": "No token_id extracted from /markets response.",
        })

    # Summary
    print("\n" + "=" * 72)
    print("Contract probe summary")
    print("=" * 72)
    statuses = {p["endpoint"]: p["status"] for p in report["probes"]}
    for ep, status in statuses.items():
        print(f"  {ep}: {status}")

    passed = sum(1 for s in statuses.values() if s == "PASS")
    total_attempted = sum(1 for s in statuses.values() if s != "SKIPPED")
    skipped = sum(1 for s in statuses.values() if s == "SKIPPED")
    print(f"\n  {passed}/{total_attempted} attempted probes PASSED  ({skipped} skipped)")

    if args.report_path:
        write_report(args.report_path, report)

    return 0 if passed == total_attempted else 1


if __name__ == "__main__":
    sys.exit(main())
