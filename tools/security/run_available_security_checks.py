"""Run available local security checks without installing tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY_VENV = ROOT / ".venv-security"
LOCAL_BIN = ROOT / "tools" / ".bin"
INCLUDE_TEMP_CLONES_ENV = "SECURITY_SCAN_INCLUDE_TEMP_CLONES"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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


def venv_python() -> Path:
    if sys.platform.startswith("win"):
        return SECURITY_VENV / "Scripts" / "python.exe"
    return SECURITY_VENV / "bin" / "python"


def local_binary(name: str) -> Path:
    suffix = ".exe" if sys.platform.startswith("win") else ""
    return LOCAL_BIN / f"{name}{suffix}"


def venv_binary(name: str) -> Path:
    suffix = ".exe" if sys.platform.startswith("win") else ""
    folder = "Scripts" if sys.platform.startswith("win") else "bin"
    return SECURITY_VENV / folder / f"{name}{suffix}"


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
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(tool, " ".join(command), "ERROR", str(exc), 2)

    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip())
    detail = output.splitlines()[0] if output else f"exit {completed.returncode}"
    result = "PASS" if completed.returncode == 0 else "FINDING_OR_ERROR"
    return CheckResult(tool, " ".join(command), result, detail, completed.returncode)


def command_succeeds(command: list[str]) -> bool:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def gitleaks_command() -> list[str] | None:
    local_tool = local_binary("gitleaks")
    if local_tool.is_file() and command_succeeds([str(local_tool), "version"]):
        return [str(local_tool), "detect", "--source", ".", "--redact"]
    if shutil.which("gitleaks") and command_succeeds(["gitleaks", "version"]):
        return ["gitleaks", "detect", "--source", ".", "--redact"]
    return None


def semgrep_command() -> list[str] | None:
    venv_tool = venv_binary("semgrep")
    local_tool = local_binary("semgrep")
    if venv_tool.is_file() and command_succeeds([str(venv_tool), "--version"]):
        return [str(venv_tool), "scan", "--config", "auto", "."]
    if local_tool.is_file() and command_succeeds([str(local_tool), "--version"]):
        return [str(local_tool), "scan", "--config", "auto", "."]
    if shutil.which("semgrep") and command_succeeds(["semgrep", "--version"]):
        return ["semgrep", "scan", "--config", "auto", "."]
    if command_succeeds(["python", "-m", "semgrep", "--version"]):
        return ["python", "-m", "semgrep", "scan", "--config", "auto", "."]
    return None


def pip_audit_command() -> list[str] | None:
    python_path = venv_python()
    venv_tool = venv_binary("pip-audit")
    local_tool = local_binary("pip-audit")
    if venv_tool.is_file() and command_succeeds([str(venv_tool), "--version"]):
        return [str(venv_tool), "--progress-spinner", "off"]
    if python_path.is_file() and command_succeeds([str(python_path), "-m", "pip_audit", "--version"]):
        return [str(python_path), "-m", "pip_audit", "--progress-spinner", "off"]
    if local_tool.is_file() and command_succeeds([str(local_tool), "--version"]):
        return [str(local_tool), "--progress-spinner", "off"]
    if shutil.which("pip-audit") and command_succeeds(["pip-audit", "--version"]):
        return ["pip-audit", "--progress-spinner", "off"]
    return None


def build_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    guard = temp_clone_guard("gitleaks")
    if guard:
        results.append(guard)
    else:
        command = gitleaks_command()
        if command:
            results.append(run_command("gitleaks", command))
        else:
            results.append(CheckResult("gitleaks", "gitleaks detect --source . --redact", "SKIPPED_NOT_AVAILABLE", "gitleaks not found in project-local path or PATH"))

    guard = temp_clone_guard("semgrep")
    if guard:
        results.append(guard)
    else:
        command = semgrep_command()
        if command:
            results.append(run_command("semgrep", command))
        else:
            results.append(CheckResult("semgrep", "semgrep scan --config auto .", "SKIPPED_NOT_AVAILABLE", "semgrep not found in project-local path or PATH"))

    if (ROOT / "package.json").exists():
        if shutil.which("npm"):
            results.append(run_command("npm audit", ["npm", "audit", "--audit-level=moderate"]))
        else:
            results.append(CheckResult("npm audit", "npm audit --audit-level=moderate", "SKIPPED_NOT_AVAILABLE", "npm not found on PATH"))
    else:
        results.append(CheckResult("npm audit", "npm audit --audit-level=moderate", "SKIPPED_NOT_APPLICABLE", "package.json not present"))

    python_dependency_files = [(ROOT / "pyproject.toml"), (ROOT / "requirements.txt")]
    if any(path.exists() for path in python_dependency_files):
        command = pip_audit_command()
        if command:
            results.append(run_command("pip-audit", command))
        else:
            results.append(CheckResult("pip-audit", "pip-audit", "SKIPPED_NOT_AVAILABLE", "pip-audit not found in project-local path or PATH"))
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
