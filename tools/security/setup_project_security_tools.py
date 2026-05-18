"""Create a project-local security-tool environment."""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY_VENV = ROOT / ".venv-security"
APPROVED_SECURITY_TOOLS = ["semgrep", "pip-audit"]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def venv_python() -> Path:
    if sys.platform.startswith("win"):
        return SECURITY_VENV / "Scripts" / "python.exe"
    return SECURITY_VENV / "bin" / "python"


def run(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit {completed.returncode}: {' '.join(command)}")


def git_output(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
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


def require_security_venv_ignore_protection() -> None:
    ignored = git_output(["check-ignore", "-q", "--", ".venv-security/"], check=False)
    if ignored.returncode != 0:
        raise RuntimeError(
            ".venv-security/ is not ignored. Local main may be stale or .gitignore is missing required rules."
        )

    tracked = git_output(["ls-files", "--", ".venv-security"]).stdout.strip()
    if tracked:
        raise RuntimeError(".venv-security/ contains tracked files; refusing to create or reuse it.")

    staged = git_output(["diff", "--cached", "--name-only", "--", ".venv-security"]).stdout.strip()
    if staged:
        raise RuntimeError(".venv-security/ contains staged files; refusing to create or reuse it.")


def write_local_gitignore() -> None:
    local_gitignore = SECURITY_VENV / ".gitignore"
    if not local_gitignore.exists():
        local_gitignore.write_text("*\n", encoding="utf-8")


def main() -> int:
    print("Project-local security tooling setup only.")
    print(f"Target environment: {SECURITY_VENV}")
    print(f"Approved tools: {', '.join(APPROVED_SECURITY_TOOLS)}")
    print("No global, system, user, npm, cargo, runtime, or trading dependency installation is performed.")

    try:
        require_security_venv_ignore_protection()
        if not SECURITY_VENV.exists():
            print(f"Creating {SECURITY_VENV}")
            venv.EnvBuilder(with_pip=True, clear=False).create(SECURITY_VENV)
        else:
            print(f"Reusing existing {SECURITY_VENV}")
        write_local_gitignore()

        python_path = venv_python()
        if not python_path.is_file():
            raise RuntimeError(f"project-local Python not found: {python_path}")

        run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python_path), "-m", "pip", "install", *APPROVED_SECURITY_TOOLS])
    except RuntimeError as exc:
        print(f"Project-local security tooling setup failed: {exc}", file=sys.stderr)
        return 1

    print("Project-local security tooling setup completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
