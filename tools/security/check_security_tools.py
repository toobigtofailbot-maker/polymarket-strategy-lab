"""Report local availability of required security tooling."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ToolCheck:
    name: str
    availability: str
    version_command: str
    detail: str


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
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"error: {exc}"

    output = (completed.stdout or completed.stderr).strip().splitlines()
    detail = output[0] if output else f"exit {completed.returncode}"
    return completed.returncode == 0, detail


def detect_semgrep() -> ToolCheck:
    command_options = [["semgrep", "--version"], ["python", "-m", "semgrep", "--version"]]
    details: list[str] = []
    for command in command_options:
        ok, detail = run_version(command)
        details.append(f"{command_text(command)} => {detail}")
        if ok:
            return ToolCheck("semgrep", "AVAILABLE", command_text(command), detail)
    return ToolCheck("semgrep", "NOT_AVAILABLE", "semgrep --version or python -m semgrep --version", "; ".join(details))


def detect_simple(name: str, command: list[str]) -> ToolCheck:
    ok, detail = run_version(command)
    return ToolCheck(name, "AVAILABLE" if ok else "NOT_AVAILABLE", command_text(command), detail)


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
        detect_simple("gitleaks", ["gitleaks", "version"]),
        detect_semgrep(),
        detect_simple("npm", ["npm", "--version"]),
        detect_simple("pip-audit", ["pip-audit", "--version"]),
        detect_simple("cargo", ["cargo", "--version"]),
        detect_simple("cargo-audit", ["cargo", "audit", "--version"]),
    ]

    print("Security tool availability")
    print_table(
        ["Tool", "Availability", "Version command", "Detail"],
        [[check.name, check.availability, check.version_command, check.detail] for check in checks],
    )
    print()
    print("Project ecosystem files")
    print_table(["File", "Status"], [[name, status] for name, status in ecosystem_status()])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
