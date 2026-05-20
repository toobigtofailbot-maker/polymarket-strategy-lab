"""Fail if generated local artifacts are visible, staged, or tracked."""

from __future__ import annotations

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
REMEDIATION_COMMAND = "python tools/git/cleanup_generated_artifacts.py --apply"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
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
    if check and completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed with exit {completed.returncode}: {completed.stderr.strip()}")
    return completed


def git_lines(args: list[str]) -> list[str]:
    output = run_git(args).stdout.strip()
    return [line for line in output.splitlines() if line.strip()]


def visible_status_entries() -> list[str]:
    return git_lines(["status", "--short", "--", *GENERATED_ARTIFACT_PATHS])


def tracked_entries() -> list[str]:
    return git_lines(["ls-files", "--", *GENERATED_ARTIFACT_PATHS])


def staged_entries() -> list[str]:
    return git_lines(["diff", "--cached", "--name-only", "--", *GENERATED_ARTIFACT_PATHS])


def missing_ignore_rules() -> list[str]:
    missing = []
    for raw in GENERATED_ARTIFACT_PATHS:
        completed = run_git(["check-ignore", "-q", "--", f"{raw}/"], check=False)
        if completed.returncode != 0:
            missing.append(raw)
    return missing


def print_failure(kind: str, entries: list[str]) -> None:
    print(f"Generated artifact guard failed: {kind}", file=sys.stderr)
    for entry in entries:
        print(f"  {entry}", file=sys.stderr)


def main() -> int:
    try:
        failures = False
        missing_ignores = missing_ignore_rules()
        if missing_ignores:
            failures = True
            print_failure("missing ignore protection", missing_ignores)

        tracked = tracked_entries()
        if tracked:
            failures = True
            print_failure("tracked generated artifact files exist", tracked)

        staged = staged_entries()
        if staged:
            failures = True
            print_failure("staged generated artifact files exist", staged)

        visible = visible_status_entries()
        if visible:
            failures = True
            print_failure("generated artifact paths are visible in git status", visible)

        if failures:
            print(f"Remediation, if files are untracked and unstaged: {REMEDIATION_COMMAND}", file=sys.stderr)
            return 1
    except RuntimeError as exc:
        print(f"Generated artifact guard failed: {exc}", file=sys.stderr)
        return 1

    print("Generated artifact guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
