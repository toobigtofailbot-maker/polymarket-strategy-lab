"""Run available local security checks without installing tools."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INCLUDE_TEMP_CLONES_ENV = "SECURITY_SCAN_INCLUDE_TEMP_CLONES"
KNOWN_TEMP_DIRS = [
    ROOT / "tmp",
    ROOT / "temp",
    ROOT / ".tmp",
    ROOT / "audits" / "source_repos" / "_clones",
]


@dataclass
class CheckResult:
    tool: str
    command: str
    result: str
    detail: str
    exit_code: int = 0


def has_temp_clone_dirs() -> bool:
    return any(path.exists() for path in KNOWN_TEMP_DIRS)


def temp_clone_guard(tool: str) -> CheckResult | None:
    if os.environ.get(INCLUDE_TEMP_CLONES_ENV) == "1":
        return None
    if has_temp_clone_dirs():
        return CheckResult(
            tool=tool,
            command="not run",
            result="SKIPPED_TEMP_CLONES_PRESENT",
            detail=f"Set {INCLUDE_TEMP_CLONES_ENV}=1 only after confirming temporary clone folders may be scanned.",
        )
    return None


def run_command(tool: str, command: list[str]) -> CheckResult:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(tool, " ".join(command), "ERROR", str(exc), 2)

    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip())
    detail = output.splitlines()[0] if output else f"exit {completed.returncode}"
    result = "PASS" if completed.returncode == 0 else "FINDING_OR_ERROR"
    return CheckResult(tool, " ".join(command), result, detail, completed.returncode)


def semgrep_command() -> list[str] | None:
    if shutil.which("semgrep"):
        return ["semgrep", "scan", "--config", "auto", "."]
    return ["python", "-m", "semgrep", "scan", "--config", "auto", "."]


def semgrep_available() -> bool:
    if shutil.which("semgrep"):
        return True
    completed = subprocess.run(
        ["python", "-m", "semgrep", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return completed.returncode == 0


def build_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    guard = temp_clone_guard("gitleaks")
    if guard:
        results.append(guard)
    elif shutil.which("gitleaks"):
        results.append(run_command("gitleaks", ["gitleaks", "detect", "--source", ".", "--redact"]))
    else:
        results.append(CheckResult("gitleaks", "gitleaks detect --source . --redact", "SKIPPED_NOT_AVAILABLE", "gitleaks not found on PATH"))

    guard = temp_clone_guard("semgrep")
    if guard:
        results.append(guard)
    elif semgrep_available():
        command = semgrep_command()
        assert command is not None
        results.append(run_command("semgrep", command))
    else:
        results.append(CheckResult("semgrep", "semgrep scan --config auto .", "SKIPPED_NOT_AVAILABLE", "semgrep not found as CLI or Python module"))

    if (ROOT / "package.json").exists():
        if shutil.which("npm"):
            results.append(run_command("npm audit", ["npm", "audit", "--audit-level=moderate"]))
        else:
            results.append(CheckResult("npm audit", "npm audit --audit-level=moderate", "SKIPPED_NOT_AVAILABLE", "npm not found on PATH"))
    else:
        results.append(CheckResult("npm audit", "npm audit --audit-level=moderate", "SKIPPED_NOT_APPLICABLE", "package.json not present"))

    python_dependency_files = [(ROOT / "pyproject.toml"), (ROOT / "requirements.txt")]
    if any(path.exists() for path in python_dependency_files):
        if shutil.which("pip-audit"):
            results.append(run_command("pip-audit", ["pip-audit"]))
        else:
            results.append(CheckResult("pip-audit", "pip-audit", "SKIPPED_NOT_AVAILABLE", "pip-audit not found on PATH"))
    else:
        results.append(CheckResult("pip-audit", "pip-audit", "SKIPPED_NOT_APPLICABLE", "Python dependency files not present"))

    if (ROOT / "Cargo.lock").exists():
        if shutil.which("cargo"):
            results.append(run_command("cargo audit", ["cargo", "audit"]))
        else:
            results.append(CheckResult("cargo audit", "cargo audit", "SKIPPED_NOT_AVAILABLE", "cargo not found on PATH"))
    else:
        results.append(CheckResult("cargo audit", "cargo audit", "SKIPPED_NOT_APPLICABLE", "Cargo.lock not present"))

    return results


def print_table(results: list[CheckResult]) -> None:
    headers = ["Tool", "Command", "Result", "Detail"]
    rows = [[result.tool, result.command, result.result, result.detail] for result in results]
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    def format_row(values: list[str]) -> str:
        return " | ".join(value.ljust(width) for value, width in zip(values, widths))

    print(format_row(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(format_row(row))


def main() -> int:
    results = build_checks()
    print("Security check summary")
    print_table(results)
    failing = [result for result in results if result.result in {"FINDING_OR_ERROR", "ERROR"}]
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
