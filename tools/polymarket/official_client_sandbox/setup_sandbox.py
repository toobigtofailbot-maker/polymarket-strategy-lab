"""Create or populate the ignored official-client sandbox environment.

Safe default: with no action flags this script prints status only. It does not
create a venv, install packages, read local environment files, or contact APIs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from importlib import metadata
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sandbox_policy import (  # noqa: E402
    CANDIDATE_DISTRIBUTION,
    LOCAL_OUTPUT_DIR,
    OUTPUT_DIR,
    ROOT,
    VENV_DIR,
    require_ignored,
    venv_python,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true", help="Create .venv-official-client/ if it is absent.")
    parser.add_argument(
        "--install-package",
        action="store_true",
        help="Install the candidate package into .venv-official-client/ only.",
    )
    parser.add_argument("--package", default=CANDIDATE_DISTRIBUTION, help="Package name to install.")
    parser.add_argument("--package-version", help="Required when --install-package is used.")
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )


def create_venv() -> None:
    require_ignored([VENV_DIR, OUTPUT_DIR, LOCAL_OUTPUT_DIR])
    if VENV_DIR.exists():
        print(f"Sandbox venv already exists: {VENV_DIR.relative_to(ROOT)}")
        return
    print(f"Creating ignored sandbox venv: {VENV_DIR.relative_to(ROOT)}")
    venv.EnvBuilder(with_pip=True).create(VENV_DIR)


def install_package(package: str, version: str | None) -> int:
    require_ignored([VENV_DIR, OUTPUT_DIR, LOCAL_OUTPUT_DIR])
    if package != CANDIDATE_DISTRIBUTION:
        print(f"Refusing unexpected package: {package!r}", file=sys.stderr)
        return 2
    if not version:
        print("--package-version is required for sandbox package installation.", file=sys.stderr)
        return 2
    python = venv_python()
    if not python.exists():
        print("Sandbox venv is absent. Run with --create first.", file=sys.stderr)
        return 2

    spec = f"{package}=={version}"
    print(f"Installing into sandbox venv only: {spec}")
    result = run([str(python), "-m", "pip", "install", "--disable-pip-version-check", spec])
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print("Sandbox package installation failed cleanly; project dependencies were not modified.", file=sys.stderr)
        return result.returncode

    version_result = run([str(python), "-c", f"from importlib import metadata; print(metadata.version({package!r}))"])
    if version_result.returncode == 0:
        print(f"Installed sandbox package version: {version_result.stdout.strip()}")
    return 0


def print_status() -> None:
    print("Official client sandbox setup status")
    print(f"  repo: {ROOT}")
    print(f"  sandbox venv: {VENV_DIR.relative_to(ROOT)} ({'present' if VENV_DIR.exists() else 'absent'})")
    try:
        installed = metadata.version(CANDIDATE_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        installed = "not installed in current interpreter"
    print(f"  current interpreter package status: {installed}")
    print("  no action flags passed: no venv creation, package installation, network, or output write performed")


def main() -> int:
    args = parse_args()
    try:
        if not args.create and not args.install_package:
            print_status()
            return 0
        if args.create:
            create_venv()
        if args.install_package:
            return install_package(args.package, args.package_version)
    except RuntimeError as exc:
        print(f"Sandbox setup refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
