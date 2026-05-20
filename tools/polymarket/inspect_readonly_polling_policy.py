"""Offline CLI for inspecting the WP16 read-only polling policy.

Default behavior prints and validates local policy only. The tool does not
create clients, call capture utilities, read environment files, run forever, or
start recurring polling.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.data_layer.polymarket.polling_policy import (  # noqa: E402
    default_polling_policy,
    validate_polling_policy,
)


_APPROVED_OUTPUT_DIR = Path("local_data") / "polymarket" / "polling_policy"


def _validate_json_output_path(path: Path) -> None:
    resolved = path.resolve()
    approved = (_REPO_ROOT / _APPROVED_OUTPUT_DIR).resolve()
    try:
        resolved.relative_to(approved)
    except ValueError as exc:
        raise ValueError(
            "Policy JSON output must be under local_data/polymarket/polling_policy/."
        ) from exc


def _print_summary(*, show_endpoints: bool = False) -> int:
    policy = default_polling_policy()
    result = validate_polling_policy(policy)

    print("Polymarket Read-Only Polling Policy Inspector (offline)")
    print(f"Policy: {policy.policy_id}")
    print(f"Automated polling enabled: {policy.automated_polling_enabled}")
    print(f"WP8-D002 status: {policy.wp8_d002_status}")
    print(f"Endpoint classes: {len(policy.endpoints)}")
    print(f"Validation: {'PASS' if result.passed else 'FAIL'}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")

    if show_endpoints:
        print("-" * 60)
        for endpoint in policy.endpoints.values():
            print(endpoint.endpoint_key)
            print(f"  enabled_by_default: {endpoint.enabled_by_default}")
            print(f"  requires_explicit_network: {endpoint.requires_explicit_network}")
            print(f"  allow_automated_loop: {endpoint.allow_automated_loop}")
            print(
                "  budget: "
                f"{endpoint.max_requests_per_window}/"
                f"{endpoint.window_seconds}s, "
                f"min_interval={endpoint.minimum_interval_seconds}s"
            )
            print(f"  notes: {endpoint.notes}")

    if result.issues:
        print("-" * 60)
        for issue in result.issues:
            print(f"{issue.severity} {issue.code} {issue.endpoint_key}: {issue.message}")

    return 0 if result.passed else 1


def _write_json(path: Path) -> None:
    _validate_json_output_path(path)
    policy = default_polling_policy()
    result = validate_polling_policy(policy)
    payload = {
        "policy": policy.to_dict(),
        "validation": result.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and validate the offline WP16 read-only polling policy. "
            "No network access is available in this tool."
        )
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Optional local JSON output path. Must be under "
            "local_data/polymarket/polling_policy/."
        ),
    )
    parser.add_argument(
        "--show-endpoints",
        action="store_true",
        default=False,
        help="Print endpoint policy details.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        default=False,
        help="Validate policy and print only the validation result.",
    )
    args = parser.parse_args(argv)

    if args.json_out:
        try:
            _write_json(args.json_out)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.validate_only:
        result = validate_polling_policy(default_polling_policy())
        print("PASS" if result.passed else "FAIL")
        return 0 if result.passed else 1

    return _print_summary(show_endpoints=args.show_endpoints)


if __name__ == "__main__":
    sys.exit(main())
