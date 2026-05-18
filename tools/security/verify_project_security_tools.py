"""Verify security-tool availability from PATH and project-local locations."""

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
class ToolProbe:
    tool: str
    source: str
    command: list[str]


@dataclass(frozen=True)
class ToolResult:
    tool: str
    source: str
    version_command: str
    availability: str
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


def available_probe(probe: ToolProbe) -> ToolResult:
    ok, detail = run_version(probe.command)
    return ToolResult(
        probe.tool,
        probe.source,
        command_text(probe.command),
        "AVAILABLE" if ok else "NOT_AVAILABLE",
        detail,
    )


def probes() -> list[ToolProbe]:
    python_path = venv_python()
    probe_list: list[ToolProbe] = []

    for tool, command in [
        ("gitleaks", ["gitleaks", "version"]),
        ("semgrep", ["semgrep", "--version"]),
        ("npm", ["npm", "--version"]),
        ("pip-audit", ["pip-audit", "--version"]),
        ("cargo", ["cargo", "--version"]),
        ("cargo-audit", ["cargo", "audit", "--version"]),
    ]:
        if shutil.which(command[0]):
            probe_list.append(ToolProbe(tool, "PATH", command))
        else:
            probe_list.append(ToolProbe(tool, "PATH", command))

    if python_path.is_file():
        probe_list.extend(
            [
                ToolProbe("semgrep", "PROJECT_LOCAL_VENV", [str(venv_binary("semgrep")), "--version"]),
                ToolProbe("semgrep", "PROJECT_LOCAL_VENV_MODULE", [str(python_path), "-m", "semgrep", "--version"]),
                ToolProbe("pip-audit", "PROJECT_LOCAL_VENV", [str(venv_binary("pip-audit")), "--version"]),
                ToolProbe("pip-audit", "PROJECT_LOCAL_VENV", [str(python_path), "-m", "pip_audit", "--version"]),
            ]
        )
    else:
        probe_list.extend(
            [
                ToolProbe("semgrep", "PROJECT_LOCAL_VENV", [str(venv_binary("semgrep")), "--version"]),
                ToolProbe("semgrep", "PROJECT_LOCAL_VENV_MODULE", [str(python_path), "-m", "semgrep", "--version"]),
                ToolProbe("pip-audit", "PROJECT_LOCAL_VENV", [str(venv_binary("pip-audit")), "--version"]),
                ToolProbe("pip-audit", "PROJECT_LOCAL_VENV", [str(python_path), "-m", "pip_audit", "--version"]),
            ]
        )

    for tool in ["gitleaks", "semgrep", "pip-audit"]:
        binary = local_binary(tool)
        command = [str(binary), "version"] if tool == "gitleaks" else [str(binary), "--version"]
        probe_list.append(ToolProbe(tool, "PROJECT_LOCAL_BIN", command))

    return probe_list


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
    results = [available_probe(probe) for probe in probes()]
    print("Project security tool availability")
    print_table(
        ["Tool", "Source", "Version command", "Availability", "Detail"],
        [[result.tool, result.source, result.version_command, result.availability, result.detail] for result in results],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
