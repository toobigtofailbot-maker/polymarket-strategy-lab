"""Dry-run or remove allowlisted generated local artifact directories."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATED_ARTIFACT_PATHS = [
    ".venv-security",
    ".venv-official-client",
    "tools/.bin",
    "tools/security/.cache",
    "security-scan-output",
    "official-client-sandbox-output",
    "local_data/polymarket/official_client_sandbox",
]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed with exit {completed.returncode}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def existing_tracked_files() -> list[str]:
    output = run_git(["ls-files", "--", *GENERATED_ARTIFACT_PATHS])
    return [line for line in output.splitlines() if line.strip()]


def existing_staged_files() -> list[str]:
    output = run_git(["diff", "--cached", "--name-only", "--", *GENERATED_ARTIFACT_PATHS])
    return [line for line in output.splitlines() if line.strip()]


def artifact_paths() -> list[Path]:
    return [ROOT / raw for raw in GENERATED_ARTIFACT_PATHS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete allowlisted generated artifact paths.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        tracked = existing_tracked_files()
        if tracked:
            print("Refusing to clean generated artifacts because tracked files exist:", file=sys.stderr)
            for path in tracked:
                print(f"  {path}", file=sys.stderr)
            return 1

        staged = existing_staged_files()
        if staged:
            print("Refusing to clean generated artifacts because staged files exist:", file=sys.stderr)
            for path in staged:
                print(f"  {path}", file=sys.stderr)
            return 1

        mode = "Removing" if args.apply else "Would remove"
        removed_any = False
        for path in artifact_paths():
            if not path.exists():
                continue
            if not path.is_dir():
                raise RuntimeError(f"allowlisted generated artifact path is not a directory: {path.relative_to(ROOT)}")
            print(f"{mode} generated artifact path: {path.relative_to(ROOT)}")
            removed_any = True
            if args.apply:
                shutil.rmtree(path)
        if not removed_any:
            print("No allowlisted generated artifact paths are present.")
    except RuntimeError as exc:
        print(f"Generated artifact cleanup failed: {exc}", file=sys.stderr)
        return 1

    if not args.apply:
        print("Dry run only. Re-run with --apply to delete allowlisted generated artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
