"""Report official-client sandbox status without installing or contacting APIs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandbox_policy import CANDIDATE_DISTRIBUTION, ROOT, VENV_DIR, venv_python  # noqa: E402


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def main() -> int:
    python = venv_python()
    print("Official client sandbox verification")
    print(f"  sandbox venv: {VENV_DIR.relative_to(ROOT)} ({'present' if VENV_DIR.exists() else 'absent'})")
    print(f"  sandbox python: {python.relative_to(ROOT)} ({'present' if python.exists() else 'absent'})")

    if not python.exists():
        print(f"  package {CANDIDATE_DISTRIBUTION}: unavailable (sandbox not created)")
        print("  no installation, network call, credential read, or output write performed")
        return 0

    code = (
        "from importlib import metadata\n"
        f"dist={CANDIDATE_DISTRIBUTION!r}\n"
        "try:\n"
        "    print(metadata.version(dist))\n"
        "except metadata.PackageNotFoundError:\n"
        "    print('NOT_INSTALLED')\n"
    )
    result = run([str(python), "-c", code])
    version = result.stdout.strip() if result.returncode == 0 else "UNKNOWN"
    print(f"  package {CANDIDATE_DISTRIBUTION}: {version}")
    print("  no installation, network call, credential read, or output write performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
