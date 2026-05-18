"""Report local availability of required security tooling."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY_VENV = ROOT / ".venv-security"
LOCAL_BIN = ROOT / "tools" / ".bin"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class ToolCheck:
    name: str
    availability: str
    source: str
    version_command: str
    detail: str


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


def command_text(command: list[str]) -> str:
    return " ".join(command)


def run_version(command: list[str]) -> tuple[bool, str]:
    executable = command[0]
    if executable != "python" and shutil.which(executable) is None:
        return False, "not found on PATH"

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
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"error: {exc}"

    output = (completed.stdout or completed.stderr).strip().splitlines()
    detail = output[0] if output else f"exit {completed.returncode}"
    return completed.returncode == 0, detail


def run_existing_path(command: list[str]) -> tuple[bool, str]:
    executable = Path(command[0])
    if not executable.is_file():
        return False, "not found in project-local path"
    return run_version(command)


def detect_semgrep() -> ToolCheck:
    semgrep_path = venv_binary("semgrep")
    local_semgrep = local_binary("semgrep")
    command_options = [
        ("PROJECT_LOCAL_VENV", [str(semgrep_path), "--version"]),
        ("PROJECT_LOCAL_BIN", [str(local_semgrep), "--version"]),
        ("PATH", ["semgrep", "--version"]),
        ("PATH", ["python", "-m", "semgrep", "--version"]),
    ]
    details: list[str] = []
    for source, command in command_options:
        ok, detail = run_existing_path(command) if source.startswith("PROJECT_LOCAL") else run_version(command)
        details.append(f"{command_text(command)} => {detail}")
        if ok:
            return ToolCheck("semgrep", "AVAILABLE", source, command_text(command), detail)
    return ToolCheck("semgrep", "NOT_AVAILABLE", "NOT_AVAILABLE", "project-local or PATH semgrep", "; ".join(details))


def detect_simple(name: str, command: list[str]) -> ToolCheck:
    ok, detail = run_version(command)
    return ToolCheck(name, "AVAILABLE" if ok else "NOT_AVAILABLE", "PATH" if ok else "NOT_AVAILABLE", command_text(command), detail)


def detect_project_or_path(name: str, module: str, path_command: list[str]) -> ToolCheck:
    python_path = venv_python()
    venv_tool = venv_binary(name)
    local_tool = local_binary(name)
    command_options = [
        ("PROJECT_LOCAL_VENV", [str(venv_tool), "--version"]),
        ("PROJECT_LOCAL_VENV", [str(python_path), "-m", module, "--version"]),
        ("PROJECT_LOCAL_BIN", [str(local_tool), "--version"]),
        ("PATH", path_command),
    ]
    details: list[str] = []
    for source, command in command_options:
        ok, detail = run_existing_path(command) if source.startswith("PROJECT_LOCAL") else run_version(command)
        details.append(f"{command_text(command)} => {detail}")
        if ok:
            return ToolCheck(name, "AVAILABLE", source, command_text(command), detail)
    return ToolCheck(name, "NOT_AVAILABLE", "NOT_AVAILABLE", f"project-local or PATH {name}", "; ".join(details))


def detect_gitleaks() -> ToolCheck:
    local_tool = local_binary("gitleaks")
    command_options = [
        ("PROJECT_LOCAL_BIN", [str(local_tool), "version"]),
        ("PATH", ["gitleaks", "version"]),
    ]
    details: list[str] = []
    for source, command in command_options:
        ok, detail = run_existing_path(command) if source == "PROJECT_LOCAL_BIN" else run_version(command)
        details.append(f"{command_text(command)} => {detail}")
        if ok:
            return ToolCheck("gitleaks", "AVAILABLE", source, command_text(command), detail)
    return ToolCheck("gitleaks", "NOT_AVAILABLE", "NOT_AVAILABLE", "project-local or PATH gitleaks", "; ".join(details))


def ecosystem_status() -> list[tuple[str, str]]:
    files = [
        ("package.json", ROOT / "package.json"),
        ("pyproject.toml", ROOT / "pyproject.toml"),
        ("requirements.txt", ROOT / "requirements.txt"),
        ("Cargo.toml", ROOT / "Cargo.toml"),
        ("Cargo.lock", ROOT / "Cargo.lock"),
    ]
    return [(name, "PRESENT" if path.exists() else "ABSENT") for name, path in files]


def print_table(headers: list[str], rows: list[list[str]]) -> None:
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
    checks = [
        detect_gitleaks(),
        detect_semgrep(),
        detect_simple("npm", ["npm", "--version"]),
        detect_project_or_path("pip-audit", "pip_audit", ["pip-audit", "--version"]),
        detect_simple("cargo", ["cargo", "--version"]),
        detect_simple("cargo-audit", ["cargo", "audit", "--version"]),
    ]

    print("Security tool availability")
    print_table(
        ["Tool", "Availability", "Source", "Version command", "Detail"],
        [[check.name, check.availability, check.source, check.version_command, check.detail] for check in checks],
    )
    print()
    print("Project ecosystem files")
    print_table(["File", "Status"], [[name, status] for name, status in ecosystem_status()])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
