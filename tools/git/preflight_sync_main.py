"""Synchronize local main with origin/main before starting a work package."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if check and completed.returncode != 0:
        raise RuntimeError(f"command failed with exit {completed.returncode}: {' '.join(command)}")
    return completed


def git_text(args: list[str]) -> str:
    completed = run_git(args)
    return completed.stdout.strip()


def require_clean_worktree() -> None:
    status = git_text(["status", "--short"])
    if status:
        raise RuntimeError("working tree is dirty after main sync")


def require_head_equals_origin_main() -> tuple[str, str]:
    local_head = git_text(["rev-parse", "HEAD"])
    origin_main = git_text(["rev-parse", "origin/main"])
    print(f"local HEAD:  {local_head}")
    print(f"origin/main: {origin_main}")
    if local_head != origin_main:
        raise RuntimeError("local HEAD does not equal origin/main")
    return local_head, origin_main


def require_revision_present(required_revision: str) -> None:
    run_git(["cat-file", "-e", f"{required_revision}^{{commit}}"])
    revisions = git_text(["rev-list", "HEAD"]).splitlines()
    if required_revision not in revisions:
        raise RuntimeError(f"required previous WP revision is missing: {required_revision}")
    print(f"required previous WP revision present: {required_revision}")


def require_files_present(required_files: list[str]) -> None:
    missing = [path for path in required_files if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"required previous WP file missing: {', '.join(missing)}")
    for path in required_files:
        print(f"required previous WP file present: {path}")


def run_generated_artifact_guard_if_available() -> None:
    guard = ROOT / "tools" / "git" / "preflight_generated_artifact_guard.py"
    if not guard.is_file():
        print("Generated artifact guard not present on this revision; skipping.")
        return
    command = [sys.executable, str(guard)]
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError("generated artifact guard failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-commit", action="append", default=[], help="Required previous WP commit hash.")
    parser.add_argument("--required-file", action="append", default=[], help="Required previous WP file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_generated_artifact_guard_if_available()
        require_clean_worktree()
        run_git(["fetch", "origin", "--prune"])
        run_git(["switch", "main"])
        run_git(["pull", "--ff-only", "origin", "main"])
        require_clean_worktree()
        require_head_equals_origin_main()
        for required_revision in args.required_commit:
            require_revision_present(required_revision)
        require_files_present(args.required_file)
    except RuntimeError as exc:
        print(f"Remote Main Sync Gate failed: {exc}", file=sys.stderr)
        return 1

    print("Remote Main Sync Gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
