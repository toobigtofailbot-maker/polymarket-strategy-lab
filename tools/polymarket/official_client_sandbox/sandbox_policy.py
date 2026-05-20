"""Shared policy helpers for the official-client sandbox.

The helpers in this file are standard-library only. They do not import the
official client, create clients, read local environment files, or make network
calls.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VENV_DIR = ROOT / ".venv-official-client"
OUTPUT_DIR = ROOT / "official-client-sandbox-output"
LOCAL_OUTPUT_DIR = ROOT / "local_data" / "polymarket" / "official_client_sandbox"
CANDIDATE_DISTRIBUTION = "py-clob-client-v2"
CANDIDATE_IMPORTS = ("py_clob_client_v2", "py_clob_client")
PUBLIC_METHOD_CANDIDATES = (
    "get_markets",
    "get_sampling_markets",
    "get_market",
    "get_order_book",
    "get_order_books",
    "get_price",
    "get_prices",
    "get_spread",
    "get_midpoint",
    "get_midpoints",
)
EXCLUDED_METHOD_KEYWORDS = (
    "create",
    "derive",
    "post",
    "order",
    "cancel",
    "sign",
    "auth",
    "credential",
    "account",
    "balance",
    "trade",
    "allowance",
    "buy",
    "sell",
)


def _git(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=check,
    )


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def check_ignored(path: Path) -> bool:
    probe = rel(path)
    if path.suffix == "" and not probe.endswith("/"):
        probe = f"{probe}/"
    return _git(["check-ignore", "-q", "--", probe]).returncode == 0


def require_ignored(paths: list[Path]) -> None:
    missing = [rel(path) for path in paths if not check_ignored(path)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"missing git ignore protection for sandbox path(s): {joined}")


def venv_python() -> Path:
    if sys.platform.startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def is_running_inside_sandbox() -> bool:
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def write_json(path: Path, data: object) -> None:
    require_ignored([path.parent])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
