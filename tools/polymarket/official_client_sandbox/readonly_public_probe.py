"""Optional public read-only probe using the sandbox official-client package.

Safe default: without --allow-network this script exits before importing the
optional package or constructing any client.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from importlib import metadata
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandbox_policy import (  # noqa: E402
    CANDIDATE_DISTRIBUTION,
    LOCAL_OUTPUT_DIR,
    OUTPUT_DIR,
    VENV_DIR,
    is_running_inside_sandbox,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-network", action="store_true", help="Required before any public network call.")
    parser.add_argument("--markets-limit", type=int, default=3, help="Maximum bounded market rows to request or display.")
    parser.add_argument("--host", default="https://clob.polymarket.com", help="Public CLOB host.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Best-effort timeout value if the client accepts it.")
    parser.add_argument(
        "--output",
        choices=("none", "json"),
        default="none",
        help="Write sanitized summary JSON under ignored sandbox output paths.",
    )
    return parser.parse_args()


def load_client_class():
    module = importlib.import_module("py_clob_client.client")
    client_cls = getattr(module, "ClobClient")
    return client_cls


def build_public_client(client_cls: type, host: str, timeout: float):
    signature = inspect.signature(client_cls)
    kwargs = {}
    if "host" in signature.parameters:
        kwargs["host"] = host
    if "timeout" in signature.parameters:
        kwargs["timeout"] = timeout
    if kwargs:
        return client_cls(**kwargs)
    return client_cls(host)


def call_bounded_public_markets(client: object, limit: int) -> object:
    method = getattr(client, "get_markets", None) or getattr(client, "get_sampling_markets", None)
    if method is None:
        raise RuntimeError("no public market-list method found")
    signature = inspect.signature(method)
    if "limit" in signature.parameters:
        return method(limit=limit)
    if "page_size" in signature.parameters:
        return method(page_size=limit)
    if "size" in signature.parameters:
        return method(size=limit)
    raise RuntimeError("market-list method is not bounded by a recognized limit parameter")


def summarize(data: object, limit: int) -> dict[str, object]:
    if isinstance(data, dict):
        rows = data.get("data") or data.get("markets") or data.get("results") or []
    else:
        rows = data
    row_count = len(rows) if isinstance(rows, list) else None
    sample: list[dict[str, object]] = []
    if isinstance(rows, list):
        for item in rows[:limit]:
            if isinstance(item, dict):
                sample.append(
                    {
                        "condition_id_present": bool(item.get("conditionId") or item.get("condition_id")),
                        "question_present": bool(item.get("question") or item.get("title")),
                    }
                )
            else:
                sample.append({"type": type(item).__name__})
    return {"response_type": type(data).__name__, "row_count": row_count, "sample": sample}


def main() -> int:
    args = parse_args()
    if not args.allow_network:
        print("Official client read-only probe: --allow-network not passed.")
        print("No network call, package import, client construction, credential read, or output write performed.")
        return 0

    if not is_running_inside_sandbox():
        print("Refusing network probe outside .venv-official-client/.")
        print(f"Run with: {VENV_DIR / 'Scripts' / 'python.exe'} tools/polymarket/official_client_sandbox/readonly_public_probe.py --allow-network")
        return 1

    if args.markets_limit < 1 or args.markets_limit > 10:
        print("--markets-limit must be between 1 and 10.", file=sys.stderr)
        return 2

    try:
        version = metadata.version(CANDIDATE_DISTRIBUTION)
        client_cls = load_client_class()
        client = build_public_client(client_cls, args.host, args.timeout)
        data = call_bounded_public_markets(client, args.markets_limit)
    except Exception as exc:
        print(f"Read-only public probe unavailable or failed gracefully: {exc.__class__.__name__}: {exc}")
        print("No authenticated behavior was attempted.")
        return 0

    summary = summarize(data, args.markets_limit)
    summary["distribution"] = CANDIDATE_DISTRIBUTION
    summary["version"] = version
    summary["network"] = "explicitly allowed"
    print("Official client public read-only probe summary")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    if args.output == "json":
        path = OUTPUT_DIR / "readonly_public_probe.summary.json"
        write_json(path, summary)
        local_path = LOCAL_OUTPUT_DIR / "readonly_public_probe.summary.json"
        write_json(local_path, summary)
        print(f"  wrote sanitized summaries under ignored sandbox output paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
