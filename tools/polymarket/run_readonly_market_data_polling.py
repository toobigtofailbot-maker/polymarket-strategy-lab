"""Manual finite read-only Polymarket public market-data polling CLI."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.polymarket.readonly_polling_runner import (  # noqa: E402
    ReadonlyPollingRunConfig,
    build_readonly_polling_plan,
    run_readonly_polling,
)

POLLING_RUN_OUTPUT_ROOT = REPO_ROOT / "local_data" / "polymarket" / "polling_runs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual finite read-only public market-data polling runner."
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Permit the bounded public GET run. Omit for offline planning only.",
    )
    parser.add_argument(
        "--markets-limit",
        type=int,
        default=3,
        help="Maximum Gamma market records to request in the bounded run.",
    )
    parser.add_argument(
        "--order-books-limit",
        type=int,
        default=0,
        help="Maximum CLOB order-book token calls. Default is 0.",
    )
    parser.add_argument(
        "--token-id",
        action="append",
        default=[],
        help="Public token id for an optional CLOB order-book request.",
    )
    parser.add_argument(
        "--json-out",
        type=pathlib.Path,
        help="Write sanitized summary under local_data/polymarket/polling_runs/.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the local policy and bounded plan, then exit.",
    )
    parser.add_argument(
        "--show-plan",
        action="store_true",
        help="Print the finite request plan.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = ReadonlyPollingRunConfig(
        allow_network=bool(args.allow_network and not args.validate_only),
        markets_limit=args.markets_limit,
        order_books_limit=args.order_books_limit,
        token_ids=tuple(args.token_id),
    )

    summary = run_readonly_polling(config)
    if args.show_plan or args.validate_only or not args.allow_network:
        print(_plan_text(config))
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))

    if args.json_out is not None:
        output_path = _validate_json_out(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return 0 if summary.policy_validation["passed"] else 1


def _plan_text(config: ReadonlyPollingRunConfig) -> str:
    plan = build_readonly_polling_plan(config)
    lines = [
        "Readonly polling plan",
        f"allow_network: {config.allow_network}",
        f"markets_limit: {config.markets_limit}",
        f"order_books_limit: {config.order_books_limit}",
        f"planned_request_count: {len(plan)}",
    ]
    for index, request in enumerate(plan, start=1):
        suffix = f" token_id={request.token_id}" if request.token_id else ""
        limit = f" limit={request.limit}" if request.limit is not None else ""
        lines.append(f"{index}. {request.endpoint_key}{limit}{suffix}")
    return "\n".join(lines)


def _validate_json_out(path: pathlib.Path) -> pathlib.Path:
    if not path.is_absolute():
        path = REPO_ROOT / path
    resolved = path.resolve()
    root = POLLING_RUN_OUTPUT_ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            "--json-out must be under local_data/polymarket/polling_runs/"
        ) from exc
    if resolved.suffix != ".json":
        raise SystemExit("--json-out must use a .json suffix")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
