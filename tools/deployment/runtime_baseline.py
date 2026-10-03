"""Standard-library research-host deployment baseline.

The helper is credential-free and zero-capital. It packages tracked repository
files, verifies releases, records sanitized host telemetry, and performs
operator-controlled backup/restore drills. It cannot place or simulate orders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


MANIFEST_NAME = "DEPLOYMENT_MANIFEST.json"
BACKUP_MANIFEST_NAME = "BACKUP_MANIFEST.json"
TELEMETRY_MAX_BYTES = 10 * 1024 * 1024
TELEMETRY_RETAINED = 7
STATE_ROOT = pathlib.Path("/var/lib/polymarket")
BACKUP_ROOT = STATE_ROOT / "backups"
RESTORE_ROOT = STATE_ROOT / "restore_drills"
CAPACITY_DISPOSITIONS = frozenset(
    {
        "C8G_RESEARCH_BASELINE_SUFFICIENT",
        "UPGRADE_ELIGIBLE:MEMORY",
        "UPGRADE_ELIGIBLE:CPU",
        "UPGRADE_ELIGIBLE:DISK",
        "UPGRADE_ELIGIBLE:IO",
        "BASELINE_INCONCLUSIVE",
    }
)
_SECRET_PARTS = frozenset(
    {".env", "credentials", "private_keys", "secrets", "wallets"}
)
_SECRET_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})
_STATE_EXCLUSIONS = frozenset({"backups", "restore_drills"})
_DATA03_PARTS = frozenset({"data-03", "data03", "data_03"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class BaselineError(RuntimeError):
    """A closed operational failure represented by a stable safe code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _safe_relative(value: object) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BaselineError("UNSAFE_PATH")
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BaselineError("UNSAFE_PATH")
    return path


def _credential_like(path: pathlib.PurePath) -> bool:
    parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    return bool(
        set(parts) & _SECRET_PARTS
        or path.suffix.lower() in _SECRET_SUFFIXES
        or name.startswith("id_rsa")
        or name.startswith("id_ed25519")
    )


def _contains_private_key_marker(path: pathlib.Path) -> bool:
    if path.stat().st_size > 16 * 1024 * 1024:
        return False
    with path.open("rb") as handle:
        sample = handle.read(256 * 1024)
    begin = b"-----" + b"BEGIN "
    end = b"-----" + b"END "
    pattern = re.compile(
        begin
        + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+(.+?)\s+"
        + end
        + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    )
    return any(b"EXAMPLE" not in match.group(1) for match in pattern.finditer(sample))


def _run(command: list[str], *, cwd: pathlib.Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise BaselineError("COMMAND_FAILED") from error
    return result.stdout.strip()


def _git(repo_root: pathlib.Path, *arguments: str) -> str:
    return _run(["git", *arguments], cwd=repo_root)


def validate_host_facts(facts: dict[str, Any]) -> None:
    """Require the frozen Ubuntu/x86-64/C8G research-host resource floor."""
    if facts.get("os_id") != "ubuntu" or facts.get("os_version") != "24.04":
        raise BaselineError("HOST_OS_UNSUPPORTED")
    if facts.get("architecture") != "x86_64":
        raise BaselineError("HOST_ARCH_UNSUPPORTED")
    if not isinstance(facts.get("logical_cpu_count"), int) or facts["logical_cpu_count"] < 4:
        raise BaselineError("HOST_CPU_FLOOR_NOT_MET")
    if not isinstance(facts.get("memory_total_bytes"), int) or facts["memory_total_bytes"] < 7_500 * 1024 * 1024:
        raise BaselineError("HOST_MEMORY_FLOOR_NOT_MET")
    if not isinstance(facts.get("disk_total_bytes"), int) or facts["disk_total_bytes"] < 70 * 1024 * 1024 * 1024:
        raise BaselineError("HOST_DISK_FLOOR_NOT_MET")


def _release_payload(repo_sha: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_id": "polymarket-research-release-manifest",
        "schema_version": "1.0.0",
        "repo_sha": repo_sha,
        "files": files,
    }


def build_release(
    repo_root: pathlib.Path, expected_sha: str, output_root: pathlib.Path
) -> dict[str, Any]:
    repo_root = repo_root.resolve(strict=True)
    if not _HEX40.fullmatch(expected_sha) or _git(repo_root, "rev-parse", "HEAD") != expected_sha:
        raise BaselineError("HEAD_MISMATCH")
    if _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise BaselineError("SOURCE_TREE_DIRTY")
    try:
        raw = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        names = [item.decode("utf-8") for item in raw.split(b"\0") if item]
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        raise BaselineError("TRACKED_FILE_ENUMERATION_FAILED") from error
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root.resolve() / expected_sha
    if destination.exists():
        raise BaselineError("RELEASE_ALREADY_EXISTS")
    staging = pathlib.Path(
        tempfile.mkdtemp(prefix=f".{expected_sha}.", dir=output_root.resolve())
    )
    inventory: list[dict[str, Any]] = []
    try:
        for name in sorted(names):
            relative = _safe_relative(name)
            if _credential_like(relative):
                raise BaselineError("CREDENTIAL_LIKE_TRACKED_PATH")
            source = repo_root.joinpath(*relative.parts)
            if source.is_symlink():
                raise BaselineError("TRACKED_SYMLINK_REJECTED")
            if not source.is_file():
                raise BaselineError("TRACKED_FILE_INVALID")
            if _contains_private_key_marker(source):
                raise BaselineError("CREDENTIAL_LIKE_TRACKED_PAYLOAD")
            target = staging.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            inventory.append(
                {
                    "path": relative.as_posix(),
                    "sha256": _sha256(target),
                    "size": target.stat().st_size,
                }
            )
        payload = _release_payload(expected_sha, inventory)
        manifest_hash = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        _write_json(
            staging / MANIFEST_NAME,
            {**payload, "release_manifest_sha256": manifest_hash},
        )
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "status": "RELEASE_BUILT",
        "repo_sha": expected_sha,
        "file_count": len(inventory),
        "release_manifest_sha256": manifest_hash,
    }


def verify_release(
    release_dir: pathlib.Path,
    expected_sha: str,
    *,
    allow_activation_artifacts: bool = False,
) -> dict[str, Any]:
    if not _HEX40.fullmatch(expected_sha):
        raise BaselineError("EXPECTED_SHA_INVALID")
    root = release_dir.resolve(strict=True)
    try:
        manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BaselineError("MANIFEST_INVALID") from error
    required = {
        "schema_id",
        "schema_version",
        "repo_sha",
        "files",
        "release_manifest_sha256",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != required
        or manifest.get("schema_id") != "polymarket-research-release-manifest"
        or manifest.get("schema_version") != "1.0.0"
        or manifest.get("repo_sha") != expected_sha
        or not isinstance(manifest.get("files"), list)
    ):
        raise BaselineError("MANIFEST_INVALID")
    inventory = manifest["files"]
    payload = _release_payload(expected_sha, inventory)
    manifest_hash = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    if manifest_hash != manifest.get("release_manifest_sha256"):
        raise BaselineError("MANIFEST_HASH_MISMATCH")
    expected: dict[str, dict[str, Any]] = {}
    for entry in inventory:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise BaselineError("MANIFEST_INVALID")
        relative = _safe_relative(entry["path"])
        name = relative.as_posix()
        if name in expected or _credential_like(relative):
            raise BaselineError("MANIFEST_INVALID")
        if not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise BaselineError("MANIFEST_INVALID")
        if not isinstance(entry["size"], int) or isinstance(entry["size"], bool) or entry["size"] < 0:
            raise BaselineError("MANIFEST_INVALID")
        expected[name] = entry
    actual: set[str] = set()
    for item in root.rglob("*"):
        relative = item.relative_to(root).as_posix()
        if allow_activation_artifacts and (
            relative == ".venv" or relative.startswith(".venv/")
        ):
            continue
        if allow_activation_artifacts and relative == "local_data" and item.is_symlink():
            if item.readlink() != pathlib.Path("/var/lib/polymarket/local_data"):
                raise BaselineError("RELEASE_SYMLINK_REJECTED")
            continue
        if item.is_symlink():
            raise BaselineError("RELEASE_SYMLINK_REJECTED")
        if item.is_file():
            if relative != MANIFEST_NAME:
                actual.add(relative)
    if actual != set(expected):
        raise BaselineError("RELEASE_FILE_SET_MISMATCH")
    for name, entry in expected.items():
        item = root.joinpath(*pathlib.PurePosixPath(name).parts)
        if item.stat().st_size != entry["size"] or _sha256(item) != entry["sha256"]:
            raise BaselineError("RELEASE_FILE_TAMPERED")
    return {
        "status": "RELEASE_VERIFIED",
        "repo_sha": expected_sha,
        "file_count": len(expected),
        "release_manifest_sha256": manifest_hash,
    }


def _read_key_values(path: pathlib.Path, separator: str = ":") -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if separator in line:
            key, value = line.split(separator, 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def _systemctl_state(unit: str) -> str:
    try:
        value = _run(["systemctl", "is-active", unit])
    except BaselineError:
        return "unknown"
    allowed = {"active", "activating", "deactivating", "failed", "inactive"}
    return value if value in allowed else "unknown"


def _unit_hashes(unit_dir: pathlib.Path) -> dict[str, str]:
    names = (
        "polymarket-critical.slice",
        "polymarket-host-telemetry.service",
        "polymarket-host-telemetry.timer",
        "polymarket-research.slice",
        "polymarket-research.target",
    )
    return {
        name: _sha256(unit_dir / name)
        for name in names
        if (unit_dir / name).is_file() and not (unit_dir / name).is_symlink()
    }


def collect_host_manifest(
    *,
    active_release: pathlib.Path,
    unit_dir: pathlib.Path,
    opt_path: pathlib.Path,
    state_path: pathlib.Path,
) -> dict[str, Any]:
    os_release = _read_key_values(pathlib.Path("/etc/os-release"), "=")
    meminfo = _read_key_values(pathlib.Path("/proc/meminfo"))
    release = json.loads(
        (active_release / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    try:
        systemd_version = _run(["systemctl", "--version"]).splitlines()[0]
    except BaselineError:
        systemd_version = "unavailable"
    try:
        ntp_value = _run(
            ["timedatectl", "show", "--property=NTPSynchronized", "--value"]
        )
        ntp_state = "synchronized" if ntp_value.lower() == "yes" else "not_synchronized"
    except BaselineError:
        ntp_state = "unknown"
    try:
        firewall_line = _run(["ufw", "status"]).splitlines()[0].lower()
        firewall_state = "active" if firewall_line == "status: active" else "inactive"
    except BaselineError:
        firewall_state = "unknown"
    disks: dict[str, dict[str, int]] = {}
    for label, path in (("opt", opt_path), ("state", state_path)):
        usage = shutil.disk_usage(path)
        disks[label] = {"total_bytes": usage.total, "free_bytes": usage.free}
    return {
        "schema_id": "polymarket-research-host-manifest",
        "schema_version": "1.0.0",
        "os": os_release.get("PRETTY_NAME", "unknown"),
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "logical_cpu_count": os.cpu_count(),
        "memory_total_kib": int(meminfo.get("MemTotal", "0 kB").split()[0]),
        "disk": disks,
        "python_version": platform.python_version(),
        "systemd_version": systemd_version,
        "ntp_state": ntp_state,
        "active_release_sha": release.get("repo_sha", "unknown"),
        "systemd_unit_hashes": _unit_hashes(unit_dir),
        "telemetry_timer_state": _systemctl_state("polymarket-host-telemetry.timer"),
        "firewall_state": firewall_state,
    }


def _rotate(path: pathlib.Path) -> None:
    if not path.exists() or path.stat().st_size < TELEMETRY_MAX_BYTES:
        return
    path.with_name(f"{path.name}.{TELEMETRY_RETAINED}").unlink(missing_ok=True)
    for index in range(TELEMETRY_RETAINED - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            source.replace(path.with_name(f"{path.name}.{index + 1}"))
    path.replace(path.with_name(f"{path.name}.1"))


def _read_cpu_times(stat_path: pathlib.Path = pathlib.Path("/proc/stat")) -> tuple[int, ...]:
    fields = stat_path.read_text(encoding="utf-8").splitlines()[0].split()
    if not fields or fields[0] != "cpu" or len(fields) < 6:
        raise ValueError("CPU_STAT_INVALID")
    # guest and guest_nice are already included in user and nice on Linux.
    return tuple(int(value) for value in fields[1:9])


def _cpu_delta_percentages(
    first: tuple[int, ...], second: tuple[int, ...]
) -> tuple[float | None, float | None]:
    if len(first) < 5 or len(first) != len(second):
        return None, None
    deltas = tuple(after - before for before, after in zip(first, second))
    total_delta = sum(deltas)
    if total_delta <= 0 or any(value < 0 for value in deltas):
        return None, None
    idle_delta = deltas[3]
    io_wait_delta = deltas[4]
    return (
        round(((total_delta - idle_delta) / total_delta) * 100, 3),
        round((io_wait_delta / total_delta) * 100, 3),
    )


def collect_telemetry(
    *,
    disk_path: pathlib.Path,
    stat_reader: Callable[[], tuple[int, ...]] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    sample_interval_seconds: float = 0.1,
) -> dict[str, Any]:
    meminfo = _read_key_values(pathlib.Path("/proc/meminfo"))
    total = int(meminfo.get("MemTotal", "0 kB").split()[0])
    available = int(meminfo.get("MemAvailable", "0 kB").split()[0])
    swap_total = int(meminfo.get("SwapTotal", "0 kB").split()[0])
    swap_free = int(meminfo.get("SwapFree", "0 kB").split()[0])
    vmstat = _read_key_values(pathlib.Path("/proc/vmstat"), " ")
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    usage = shutil.disk_usage(disk_path)
    cpu_percent: float | None = None
    io_wait_percent: float | None = None
    try:
        if sample_interval_seconds <= 0 or sample_interval_seconds > 1:
            raise ValueError("CPU_SAMPLE_INTERVAL_INVALID")
        reader = stat_reader or _read_cpu_times
        first = reader()
        sleeper(sample_interval_seconds)
        second = reader()
        cpu_percent, io_wait_percent = _cpu_delta_percentages(first, second)
    except (OSError, ValueError, IndexError, StopIteration):
        pass
    return {
        "schema_id": "polymarket-research-host-telemetry",
        "schema_version": "1.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cpu_utilization_percent": cpu_percent,
        "load_average": [round(value, 3) for value in load],
        "memory_available_kib": available,
        "memory_utilization_percent": round(((total - available) / total) * 100, 3) if total else None,
        "swap_used_kib": swap_total - swap_free,
        "swap_in_pages": int(vmstat.get("pswpin", "0").split()[0]),
        "swap_out_pages": int(vmstat.get("pswpout", "0").split()[0]),
        "disk_utilization_percent": round(((usage.total - usage.free) / usage.total) * 100, 3),
        "io_wait_percent": io_wait_percent,
        "research_target_state": _systemctl_state("polymarket-research.target"),
        "telemetry_timer_state": _systemctl_state("polymarket-host-telemetry.timer"),
    }


def append_telemetry(output: pathlib.Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _rotate(output)
    with output.open("ab") as handle:
        handle.write(_canonical_bytes(payload) + b"\n")


def _iter_state_files(
    state_root: pathlib.Path,
) -> Iterable[tuple[pathlib.Path, pathlib.PurePosixPath]]:
    root = state_root.resolve(strict=True)
    for path in sorted(root.rglob("*")):
        relative = pathlib.PurePosixPath(path.relative_to(root).as_posix())
        lowered = {part.lower() for part in relative.parts}
        if lowered & _STATE_EXCLUSIONS:
            continue
        if lowered & _DATA03_PARTS:
            raise BaselineError("BACKUP_DATA03_PATH_REJECTED")
        if path.is_symlink():
            raise BaselineError("BACKUP_SYMLINK_REJECTED")
        if path.is_file():
            if _credential_like(relative):
                raise BaselineError("BACKUP_SECRET_PATH_REJECTED")
            yield path, relative


def create_backup(
    state_root: pathlib.Path, backup_root: pathlib.Path, backup_id: str
) -> dict[str, Any]:
    if not _SAFE_ID.fullmatch(backup_id):
        raise BaselineError("BACKUP_ID_INVALID")
    destination = backup_root.resolve() / backup_id
    if destination.exists():
        raise BaselineError("BACKUP_ALREADY_EXISTS")
    destination.mkdir(parents=True)
    inventory: list[dict[str, Any]] = []
    try:
        for source, relative in _iter_state_files(state_root):
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            is_sqlite = source.suffix == ".sqlite3"
            if is_sqlite:
                with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
                    with sqlite3.connect(target) as target_db:
                        source_db.backup(target_db)
            else:
                shutil.copyfile(source, target)
            inventory.append(
                {
                    "path": relative.as_posix(),
                    "sha256": _sha256(target),
                    "size": target.stat().st_size,
                    "sqlite": is_sqlite,
                }
            )
        payload = {
            "schema_id": "polymarket-research-backup-manifest",
            "schema_version": "1.0.0",
            "backup_id": backup_id,
            "files": inventory,
        }
        manifest_hash = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        _write_json(
            destination / BACKUP_MANIFEST_NAME,
            {**payload, "backup_manifest_sha256": manifest_hash},
        )
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        "status": "BACKUP_COMPLETE",
        "backup_id": backup_id,
        "file_count": len(inventory),
        "backup_manifest_sha256": manifest_hash,
    }


def restore_verify(
    backup_dir: pathlib.Path, restore_root: pathlib.Path, drill_id: str
) -> dict[str, Any]:
    if not _SAFE_ID.fullmatch(drill_id):
        raise BaselineError("RESTORE_ID_INVALID")
    source = backup_dir.resolve(strict=True)
    destination = restore_root.resolve() / drill_id
    if destination.exists():
        raise BaselineError("RESTORE_TARGET_EXISTS")
    try:
        manifest = json.loads(
            (source / BACKUP_MANIFEST_NAME).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise BaselineError("BACKUP_MANIFEST_INVALID") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise BaselineError("BACKUP_MANIFEST_INVALID")
    inventory = manifest["files"]
    payload = {
        key: manifest.get(key)
        for key in ("schema_id", "schema_version", "backup_id", "files")
    }
    if (
        payload["schema_id"] != "polymarket-research-backup-manifest"
        or payload["schema_version"] != "1.0.0"
        or hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        != manifest.get("backup_manifest_sha256")
    ):
        raise BaselineError("BACKUP_MANIFEST_INVALID")
    expected_names: set[str] = set()
    for entry in inventory:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size", "sqlite"}:
            raise BaselineError("BACKUP_MANIFEST_INVALID")
        name = _safe_relative(entry["path"]).as_posix()
        if (
            name in expected_names
            or not isinstance(entry["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
            or not isinstance(entry["size"], int)
            or isinstance(entry["size"], bool)
            or entry["size"] < 0
            or not isinstance(entry["sqlite"], bool)
        ):
            raise BaselineError("BACKUP_MANIFEST_INVALID")
        expected_names.add(name)
    actual_names = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.name != BACKUP_MANIFEST_NAME
    }
    if expected_names != actual_names:
        raise BaselineError("BACKUP_FILE_SET_MISMATCH")
    destination.mkdir(parents=True)
    try:
        for entry in inventory:
            relative = _safe_relative(entry["path"])
            item = source.joinpath(*relative.parts)
            if (
                item.is_symlink()
                or item.stat().st_size != entry["size"]
                or _sha256(item) != entry["sha256"]
            ):
                raise BaselineError("BACKUP_TAMPERED")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
            if entry["sqlite"]:
                try:
                    with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as database:
                        row = database.execute("PRAGMA integrity_check").fetchone()
                except sqlite3.DatabaseError as error:
                    raise BaselineError("SQLITE_INTEGRITY_FAILED") from error
                if row is None or row[0] != "ok":
                    raise BaselineError("SQLITE_INTEGRITY_FAILED")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        "status": "RESTORE_VERIFIED",
        "drill_id": drill_id,
        "file_count": len(inventory),
        "source_backup_id": manifest["backup_id"],
    }


def evaluate_research_smoke(
    smoke_result: dict[str, Any], telemetry: list[dict[str, Any]]
) -> dict[str, Any]:
    def positive_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    smoke_passed = (
        smoke_result.get("status") == "STOPPED"
        and smoke_result.get("stop_reason") == "DURATION_EXPIRED"
        and smoke_result.get("error_codes") == []
        and positive_integer(smoke_result.get("raw_count"))
        and positive_integer(smoke_result.get("normalized_count"))
        and positive_integer(smoke_result.get("store_bytes"))
    )
    smoke_disposition = (
        "PUBLIC_RESEARCH_SMOKE_PASS" if smoke_passed else "BASELINE_INCONCLUSIVE"
    )
    required_metrics = (
        "memory_utilization_percent",
        "cpu_utilization_percent",
        "disk_utilization_percent",
        "io_wait_percent",
    )

    def usable_metric(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and 0 <= value <= 100
        )

    telemetry_complete = bool(telemetry) and all(
        isinstance(row, dict)
        and all(usable_metric(row.get(metric)) for metric in required_metrics)
        for row in telemetry
    )
    if not smoke_passed or not telemetry_complete:
        capacity = "BASELINE_INCONCLUSIVE"
    else:
        memory = [row.get("memory_utilization_percent") for row in telemetry]
        disk = [row.get("disk_utilization_percent") for row in telemetry]
        io_wait = [row.get("io_wait_percent") for row in telemetry]
        cpu = [row.get("cpu_utilization_percent") for row in telemetry]
        if any(isinstance(value, (int, float)) and value >= 85 for value in memory):
            capacity = "UPGRADE_ELIGIBLE:MEMORY"
        elif any(isinstance(value, (int, float)) and value >= 85 for value in cpu):
            capacity = "UPGRADE_ELIGIBLE:CPU"
        elif any(isinstance(value, (int, float)) and value >= 80 for value in disk):
            capacity = "UPGRADE_ELIGIBLE:DISK"
        elif any(isinstance(value, (int, float)) and value >= 10 for value in io_wait):
            capacity = "UPGRADE_ELIGIBLE:IO"
        else:
            capacity = "C8G_RESEARCH_BASELINE_SUFFICIENT"
    if capacity not in CAPACITY_DISPOSITIONS:  # pragma: no cover - defensive
        raise BaselineError("CAPACITY_DISPOSITION_INVALID")
    return {
        "status": "RESEARCH_SMOKE_EVALUATED",
        "smoke_disposition": smoke_disposition,
        "capacity_disposition": capacity,
        "sample_count": len(telemetry),
    }


def verify_ufw_ssh_only(status_text: str, ssh_port: int, *, allow_empty: bool) -> dict[str, Any]:
    if not isinstance(ssh_port, int) or isinstance(ssh_port, bool) or not 1 <= ssh_port <= 65535:
        raise BaselineError("SSH_PORT_INVALID")
    allowed: list[str] = []
    for raw_line in status_text.splitlines():
        line = re.sub(r"^\s*\[\s*\d+\]\s*", "", raw_line.strip())
        if not line or line.lower().startswith(("status:", "to ", "--", "added user rules")):
            continue
        tokens = line.split()
        upper = [token.upper() for token in tokens]
        if "ALLOW" not in upper:
            continue
        action_index = upper.index("ALLOW")
        if action_index + 1 < len(upper) and upper[action_index + 1] == "OUT":
            continue
        if tokens[0].lower() == "ufw":
            if "ROUTE" in upper[:action_index]:
                raise BaselineError("FIREWALL_NOT_SSH_ONLY")
            target_index = action_index + 1
            if target_index < len(tokens) and upper[target_index] == "IN":
                target_index += 1
            if target_index >= len(tokens):
                raise BaselineError("FIREWALL_NOT_SSH_ONLY")
            target = tokens[target_index].lower()
        else:
            target = tokens[0].lower()
        if target != f"{ssh_port}/tcp":
            raise BaselineError("FIREWALL_NOT_SSH_ONLY")
        allowed.append(target)
    if not allowed and not allow_empty:
        raise BaselineError("FIREWALL_NOT_SSH_ONLY")
    return {"status": "FIREWALL_VERIFIED", "ssh_port": ssh_port, "allow_count": len(allowed)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research-only deployment baseline")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-release")
    build.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    build.add_argument("--expected-sha", required=True)
    build.add_argument("--output-root", type=pathlib.Path)
    verify = commands.add_parser("verify-release")
    verify.add_argument("--release-dir", type=pathlib.Path, required=True)
    verify.add_argument("--expected-sha", required=True)
    verify.add_argument("--allow-activation-artifacts", action="store_true")
    host = commands.add_parser("host-manifest")
    host.add_argument("--active-release", type=pathlib.Path, required=True)
    host.add_argument("--unit-dir", type=pathlib.Path, default=pathlib.Path("/etc/systemd/system"))
    host.add_argument("--opt-path", type=pathlib.Path, default=pathlib.Path("/opt/polymarket"))
    host.add_argument("--state-path", type=pathlib.Path, default=STATE_ROOT)
    host.add_argument("--output", type=pathlib.Path)
    telemetry = commands.add_parser("telemetry")
    telemetry.add_argument("--disk-path", type=pathlib.Path, default=STATE_ROOT)
    telemetry.add_argument("--output", type=pathlib.Path, required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--backup-id", required=True)
    restore = commands.add_parser("restore-verify")
    restore.add_argument("--backup-dir", type=pathlib.Path, required=True)
    restore.add_argument("--drill-id", required=True)
    smoke = commands.add_parser("research-smoke-evaluate")
    smoke.add_argument("--smoke-result", type=pathlib.Path, required=True)
    smoke.add_argument("--telemetry-jsonl", type=pathlib.Path, required=True)
    firewall = commands.add_parser("verify-firewall")
    firewall.add_argument("--status-file", type=pathlib.Path, required=True)
    firewall.add_argument("--ssh-port", type=int, required=True)
    firewall.add_argument("--allow-empty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build-release":
            output_root = args.output_root or args.repo_root / "local_data" / "deployment"
            result = build_release(args.repo_root, args.expected_sha, output_root)
        elif args.command == "verify-release":
            result = verify_release(
                args.release_dir,
                args.expected_sha,
                allow_activation_artifacts=args.allow_activation_artifacts,
            )
        elif args.command == "host-manifest":
            result = collect_host_manifest(
                active_release=args.active_release,
                unit_dir=args.unit_dir,
                opt_path=args.opt_path,
                state_path=args.state_path,
            )
            if args.output:
                _write_json(args.output, result)
        elif args.command == "telemetry":
            result = collect_telemetry(disk_path=args.disk_path)
            append_telemetry(args.output, result)
        elif args.command == "backup":
            result = create_backup(STATE_ROOT, BACKUP_ROOT, args.backup_id)
        elif args.command == "restore-verify":
            result = restore_verify(args.backup_dir, RESTORE_ROOT, args.drill_id)
        elif args.command == "research-smoke-evaluate":
            smoke_result = json.loads(args.smoke_result.read_text(encoding="utf-8"))
            telemetry_rows = [
                json.loads(line)
                for line in args.telemetry_jsonl.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            result = evaluate_research_smoke(smoke_result, telemetry_rows)
        else:
            result = verify_ufw_ssh_only(
                args.status_file.read_text(encoding="utf-8"),
                args.ssh_port,
                allow_empty=args.allow_empty,
            )
    except (BaselineError, OSError, ValueError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, BaselineError) else "CLOSED_FAILURE"
        sys.stdout.write(
            json.dumps({"status": "FAILED", "error_code": code}, separators=(",", ":"))
            + "\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
