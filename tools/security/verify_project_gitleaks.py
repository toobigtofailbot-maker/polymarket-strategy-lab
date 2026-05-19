"""Verify gitleaks availability without installing anything or running scans.

Checks for gitleaks in:
- tools/.bin/gitleaks (or .exe on Windows)
- System PATH

Exits 0 regardless of whether gitleaks is found.
Reports availability clearly.

Does NOT:
- Install anything.
- Run secret scans.
- Contact trading APIs.
- Read credentials.
- Alter system state.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_BIN = ROOT / "tools" / ".bin"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def local_binary() -> Path:
    suffix = ".exe" if sys.platform.startswith("win") else ""
    return LOCAL_BIN / f"gitleaks{suffix}"


def try_version(command: list[str]) -> tuple[bool, str]:
    """Run a version command and return (success, output_line)."""
    executable = command[0]
    binary_path = Path(executable)

    if binary_path.is_absolute() or "/" in executable or "\\" in executable:
        if not binary_path.is_file():
            return False, "not found"
    elif not shutil.which(executable):
        return False, "not found on PATH"

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"error: {exc}"

    output = (result.stdout or result.stderr or "").strip()
    detail = output.splitlines()[0] if output else f"exit {result.returncode}"
    return result.returncode == 0, detail


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]

    sep = "-+-".join("-" * w for w in widths)
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print(sep)
    for row in rows:
        print(" | ".join(v.ljust(w) for v, w in zip(row, widths)))


def main() -> int:
    local_bin = local_binary()
    checks = [
        {
            "tool": "gitleaks",
            "source": "PROJECT_LOCAL_BIN",
            "version_command": f"{local_bin} version",
            "command": [str(local_bin), "version"],
        },
        {
            "tool": "gitleaks",
            "source": "PATH",
            "version_command": "gitleaks version",
            "command": ["gitleaks", "version"],
        },
    ]

    rows = []
    found_any = False
    for check in checks:
        ok, detail = try_version(check["command"])
        availability = "AVAILABLE" if ok else "NOT_AVAILABLE"
        if ok:
            found_any = True
        rows.append([
            check["tool"],
            check["source"],
            check["version_command"],
            availability,
            detail,
        ])

    print("Gitleaks availability")
    print_table(
        ["Tool", "Source", "Version command", "Availability", "Detail"],
        rows,
    )
    print()

    if found_any:
        print("Result: AVAILABLE")
        print("Next: run tools/security/run_available_security_checks.py")
        print("WP3-D001 is READY_FOR_WP pending a successful scan run.")
    else:
        print("Result: NOT_AVAILABLE")
        print("Next: run tools/security/setup_project_gitleaks.py")
        print("WP3-D001 remains DEFERRED until gitleaks is verified and scan passes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
