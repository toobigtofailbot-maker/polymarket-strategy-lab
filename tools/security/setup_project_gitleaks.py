"""Set up a project-local gitleaks binary under ignored tools/.bin/.

This script does NOT perform global or system-level installation.
It only places a binary under tools/.bin/ which must already be in .gitignore.

Rules enforced:
- Verifies tools/.bin/ is ignored by git before writing anything there.
- Verifies no files under tools/.bin/ are tracked or staged.
- Downloads a pinned gitleaks release from GitHub into tools/.bin/ only.
- Verifies the resulting binary returns exit 0 from 'gitleaks version'.
- Does not use winget, choco, brew, apt, npm, cargo install, or pip --user.
- Does not install globally or system-wide.
- Does not touch src/ or any runtime file.
- Does not read credentials or contact trading APIs.
- Does not add the binary to git tracking.

If acquisition fails for any reason the script exits with a non-zero code
and documents the blocker. WP3-D001 remains DEFERRED in that case.
"""

from __future__ import annotations

import hashlib
import io
import platform
import subprocess
import sys
import urllib.request
import zipfile
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_BIN = ROOT / "tools" / ".bin"

# Pinned version. Change only in an approved work package with documented rationale.
GITLEAKS_VERSION = "8.27.2"
GITLEAKS_TAG = f"v{GITLEAKS_VERSION}"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def verify_local_bin_is_ignored() -> None:
    """Fail fast if tools/.bin/ is not ignored by git."""
    # Use relative path with trailing slash so git check-ignore matches directory patterns.
    relative_path = "tools/.bin/"
    result = run_git(["check-ignore", "-q", "--", relative_path])
    if result.returncode != 0:
        raise RuntimeError(
            "tools/.bin/ is NOT ignored by git. "
            "Add 'tools/.bin/' to .gitignore before using this script. "
            "WP3-D001 remains DEFERRED."
        )
    print(f"Ignore protection verified: {LOCAL_BIN} is git-ignored.")


def verify_no_tracked_or_staged_bin_files() -> None:
    """Fail fast if any file under tools/.bin/ is tracked or staged."""
    tracked = run_git(["ls-files", "--", str(LOCAL_BIN)])
    if tracked.stdout.strip():
        raise RuntimeError(
            f"Tracked files found under tools/.bin/: {tracked.stdout.strip()!r}. "
            "Remove them from tracking before proceeding. WP3-D001 remains DEFERRED."
        )
    staged = run_git(["diff", "--cached", "--name-only", "--", str(LOCAL_BIN)])
    if staged.stdout.strip():
        raise RuntimeError(
            f"Staged files found under tools/.bin/: {staged.stdout.strip()!r}. "
            "Unstage them before proceeding. WP3-D001 remains DEFERRED."
        )
    print("Tracking/staging check passed: no tracked or staged files under tools/.bin/.")


def detect_existing_gitleaks() -> tuple[str, str] | None:
    """Return (source, binary_path) if gitleaks is already available, else None."""
    suffix = ".exe" if sys.platform.startswith("win") else ""
    local_binary = LOCAL_BIN / f"gitleaks{suffix}"

    if local_binary.is_file():
        result = subprocess.run(
            [str(local_binary), "version"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode == 0:
            version_line = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else ""
            print(f"Gitleaks already available at PROJECT_LOCAL_BIN: {local_binary}")
            print(f"  version: {version_line}")
            return "PROJECT_LOCAL_BIN", str(local_binary)

    import shutil
    if shutil.which("gitleaks"):
        result = subprocess.run(
            ["gitleaks", "version"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode == 0:
            version_line = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else ""
            print(f"Gitleaks already available on PATH.")
            print(f"  version: {version_line}")
            return "PATH", "gitleaks"

    return None


def platform_asset() -> tuple[str, str]:
    """Return (asset_filename, binary_name_in_archive) for the current platform."""
    machine = platform.machine().lower()
    arch = "x64" if machine in ("amd64", "x86_64") else ("arm64" if "arm" in machine or "aarch" in machine else "x64")

    if sys.platform.startswith("win"):
        asset = f"gitleaks_{GITLEAKS_VERSION}_windows_{arch}.zip"
        binary = "gitleaks.exe"
    elif sys.platform.startswith("darwin"):
        asset = f"gitleaks_{GITLEAKS_VERSION}_darwin_{arch}.tar.gz"
        binary = "gitleaks"
    else:
        asset = f"gitleaks_{GITLEAKS_VERSION}_linux_{arch}.tar.gz"
        binary = "gitleaks"

    return asset, binary


def download_gitleaks() -> str:
    """Download the pinned gitleaks binary into tools/.bin/. Returns path to binary."""
    LOCAL_BIN.mkdir(parents=True, exist_ok=True)

    asset_filename, binary_name = platform_asset()
    download_url = (
        f"https://github.com/gitleaks/gitleaks/releases/download/"
        f"{GITLEAKS_TAG}/{asset_filename}"
    )
    checksum_url = (
        f"https://github.com/gitleaks/gitleaks/releases/download/"
        f"{GITLEAKS_TAG}/gitleaks_{GITLEAKS_VERSION}_checksums.txt"
    )

    print(f"Gitleaks pinned version: {GITLEAKS_VERSION}")
    print(f"Source URL: {download_url}")
    print(f"Target directory: {LOCAL_BIN}")

    print(f"Downloading {asset_filename} ...")
    try:
        with urllib.request.urlopen(download_url, timeout=120) as response:
            archive_data = response.read()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download gitleaks from {download_url}: {exc}. "
            "WP3-D001 remains DEFERRED. Check network access and try again."
        ) from exc

    print(f"Downloaded {len(archive_data):,} bytes.")

    # Attempt checksum verification (best-effort; limitation documented if unavailable)
    sha256_computed = hashlib.sha256(archive_data).hexdigest()
    print(f"SHA256 of downloaded archive: {sha256_computed}")

    try:
        with urllib.request.urlopen(checksum_url, timeout=30) as resp:
            checksums_text = resp.read().decode("utf-8", errors="replace")
        expected_hash: str | None = None
        for line in checksums_text.splitlines():
            parts = line.split()
            if len(parts) == 2 and asset_filename in parts[1]:
                expected_hash = parts[0].lower()
                break
        if expected_hash:
            if sha256_computed.lower() != expected_hash:
                raise RuntimeError(
                    f"SHA256 mismatch for {asset_filename}: "
                    f"computed {sha256_computed!r}, expected {expected_hash!r}. "
                    "Do not use this binary. WP3-D001 remains DEFERRED."
                )
            print(f"Checksum VERIFIED: SHA256 matches release checksum.")
        else:
            print(
                f"WARNING: Could not find {asset_filename} in checksums file. "
                "Checksum verification skipped for this asset. "
                "WP3-D001 will be marked READY_FOR_WP only, not RESOLVED."
            )
    except RuntimeError:
        raise
    except Exception as exc:
        print(
            f"WARNING: Could not fetch or parse checksums file ({exc}). "
            "Checksum verification unavailable. "
            "WP3-D001 will be marked READY_FOR_WP only, not RESOLVED."
        )

    # Extract binary from archive
    binary_dest = LOCAL_BIN / binary_name
    if asset_filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive_data)) as zf:
            names = zf.namelist()
            matching = [n for n in names if Path(n).name == binary_name]
            if not matching:
                raise RuntimeError(
                    f"Could not find {binary_name!r} in archive. Members: {names}. "
                    "WP3-D001 remains DEFERRED."
                )
            binary_data = zf.read(matching[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(archive_data)) as tf:
            matching_members = [m for m in tf.getmembers() if Path(m.name).name == binary_name]
            if not matching_members:
                names = [m.name for m in tf.getmembers()]
                raise RuntimeError(
                    f"Could not find {binary_name!r} in archive. Members: {names}. "
                    "WP3-D001 remains DEFERRED."
                )
            f = tf.extractfile(matching_members[0])
            if f is None:
                raise RuntimeError(f"Could not read {binary_name!r} from archive.")
            binary_data = f.read()

    binary_dest.write_bytes(binary_data)
    if not sys.platform.startswith("win"):
        binary_dest.chmod(0o755)

    print(f"Binary written to: {binary_dest}")
    return str(binary_dest)


def verify_binary(binary_path: str) -> str:
    """Run `gitleaks version` and return the version string. Raise on failure."""
    result = subprocess.run(
        [binary_path, "version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        raise RuntimeError(
            f"Binary at {binary_path!r} failed version check (exit {result.returncode}): {output}. "
            "WP3-D001 remains DEFERRED."
        )
    version_line = output.splitlines()[0] if output else f"exit {result.returncode}"
    print(f"Binary version check PASSED: {version_line}")
    return version_line


def verify_not_tracked(binary_path: str) -> None:
    """Confirm the binary is not tracked by git."""
    result = run_git(["ls-files", "--", binary_path])
    if result.stdout.strip():
        raise RuntimeError(
            f"Binary {binary_path!r} is tracked by git! "
            "Remove it from tracking immediately. WP3-D001 remains DEFERRED."
        )
    print(f"Tracking check passed: {binary_path} is not tracked by git.")


def main() -> int:
    print("=" * 60)
    print("WP7 Gitleaks Project-Local Setup")
    print(f"Pinned version: {GITLEAKS_VERSION}")
    print(f"Target path: {LOCAL_BIN}")
    print("=" * 60)

    try:
        verify_local_bin_is_ignored()
        verify_no_tracked_or_staged_bin_files()

        existing = detect_existing_gitleaks()
        if existing:
            source, binary = existing
            print(f"\nGitleaks already available ({source}). No download needed.")
            verify_binary(binary)
            print("\nSetup complete. WP3-D001 is READY_FOR_WP pending scan evidence.")
            return 0

        print(f"\nGitleaks not found. Attempting project-local acquisition ...")
        binary_path = download_gitleaks()
        verify_binary(binary_path)
        verify_not_tracked(binary_path)

        print("\n" + "=" * 60)
        print("Gitleaks setup SUCCEEDED.")
        print(f"Binary: {binary_path}")
        print(f"Version: {GITLEAKS_VERSION}")
        print("Next: run verify_project_gitleaks.py, then run_available_security_checks.py")
        print("WP3-D001 is READY_FOR_WP after a successful scan.")
        print("=" * 60)
        return 0

    except RuntimeError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("WP3-D001 remains DEFERRED.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
