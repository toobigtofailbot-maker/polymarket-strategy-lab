"""Standard-library research-host deployment baseline.

The helper is credential-free and zero-capital. It packages tracked repository
files, verifies releases, records sanitized host telemetry, and performs
operator-controlled backup/restore drills. It cannot place or simulate orders.

S10-DEPLOY-EXEC-01 adds the execution-host substrate: a sanitized host/release
binding, currentness evidence, a non-economic critical-slice heartbeat probe, a
closed research-versus-critical coexistence evaluator and closed terminal
Phase-B evidence semantics. None of it grants credential, order or live authority.
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
from fractions import Fraction
from typing import IO, Any, Callable, Iterable

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX development hosts
    fcntl = None  # type: ignore[assignment]
try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX hosts
    msvcrt = None  # type: ignore[assignment]


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
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# S10-DEPLOY-EXEC-01 execution-host substrate (non-economic; no credential/order/live authority).
MACHINE_ID_PATH = pathlib.Path("/etc/machine-id")
BOOT_ID_PATH = pathlib.Path("/proc/sys/kernel/random/boot_id")
RELEASES_ROOT = pathlib.Path("/opt/polymarket/releases")
EXECUTION_HOST_STATE = STATE_ROOT / "execution_host"
CRITICAL_PROBE_UNIT = "polymarket-execution-critical-probe.service"
CRITICAL_PROBE_PERIOD_MS = 250
CRITICAL_PROBE_MAX_DURATION_SECONDS = 600
BINDING_SCHEMA_ID = "polymarket-execution-host-binding"
CURRENTNESS_SCHEMA_ID = "polymarket-execution-host-currentness"
PROBE_HEARTBEAT_SCHEMA_ID = "polymarket-execution-critical-probe-heartbeat"
PROBE_SAMPLE_SCHEMA_ID = "polymarket-execution-critical-probe-sample"
TERMINAL_EVIDENCE_SCHEMA_ID = "polymarket-execution-host-phase-b-evidence"
EXECUTION_SCHEMA_VERSION = "1.0.0"
PERSISTENT_STATE_DIRS = ("local_data", "telemetry", "backups", "restore_drills", "execution_host")
COEXISTENCE_MIN_COVERAGE_NS = 55 * 1_000_000_000
CRITICAL_DEADLINE_MS = 500.0
CRITICAL_DEGRADATION_RATIO = Fraction(6, 5)
COEXISTENCE_MAX_SAMPLES = 100_000
EVIDENCE_MAX_BYTES = 16 * 1024 * 1024
UPGRADE_REASONS = ("CRITICAL_DEADLINE", "CRITICAL_DEGRADATION", "MEMORY", "CPU", "DISK", "IO")
COEXISTENCE_DISPOSITIONS = frozenset(
    {"C8G_EXECUTION_HOST_SUFFICIENT", "EXECUTION_HOST_INCONCLUSIVE"}
    | {f"UPGRADE_ELIGIBLE:{reason}" for reason in UPGRADE_REASONS}
)
TERMINAL_OUTCOMES = frozenset(
    {"EXECUTION_HOST_PROVEN_C8G", "EXECUTION_HOST_INCONCLUSIVE"}
    | {f"EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:{reason}" for reason in UPGRADE_REASONS}
)
_ASCII_WHITESPACE = b" \t\n\r\x0b\x0c"
_MACHINE_ID = re.compile(rb"[0-9a-f]{32}")
_BOOT_UUID = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_HOST_INSTANCE_ID = re.compile(r"^pmhost-v1:[0-9a-f]{64}$")
_BOOT_INSTANCE_ID = re.compile(r"^pmboot-v1:[0-9a-f]{64}$")
_PROCESS_INSTANCE_ID = re.compile(r"^pmproc-v1:[0-9a-f]{64}$")


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


def _ntp_state() -> str:
    try:
        ntp_value = _run(
            ["timedatectl", "show", "--property=NTPSynchronized", "--value"]
        )
    except BaselineError:
        return "unknown"
    return "synchronized" if ntp_value.lower() == "yes" else "not_synchronized"


def _unit_hashes(unit_dir: pathlib.Path) -> dict[str, str]:
    names = (
        "polymarket-critical.slice",
        CRITICAL_PROBE_UNIT,
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
    ntp_state = _ntp_state()
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


def _positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _research_smoke_passed(smoke_result: Any) -> bool:
    """The frozen DEPLOY-01 truthful smoke success contract (actual counts only)."""
    return (
        isinstance(smoke_result, dict)
        and smoke_result.get("status") == "STOPPED"
        and smoke_result.get("stop_reason") == "DURATION_EXPIRED"
        and smoke_result.get("error_codes") == []
        and _positive_integer(smoke_result.get("raw_count"))
        and _positive_integer(smoke_result.get("normalized_count"))
        and _positive_integer(smoke_result.get("store_bytes"))
    )


def evaluate_research_smoke(
    smoke_result: dict[str, Any], telemetry: list[dict[str, Any]]
) -> dict[str, Any]:
    smoke_passed = _research_smoke_passed(smoke_result)
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
        permitting_actions = [action for action in ("ALLOW", "LIMIT") if action in upper]
        if not permitting_actions:
            continue
        action_index = min(upper.index(action) for action in permitting_actions)
        if "ROUTE" in upper[:action_index] or "FWD" in upper:
            raise BaselineError("FIREWALL_NOT_SSH_ONLY")
        if action_index + 1 < len(upper) and upper[action_index + 1] == "OUT":
            continue
        if tokens[0].lower() == "ufw":
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


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01 execution-host identity, binding and currentness
# ---------------------------------------------------------------------------


def _domain_hash(domain: bytes, *parts: bytes) -> str:
    return hashlib.sha256(domain + b"\0".join(parts)).hexdigest()


def derive_host_instance_id(machine_id: bytes) -> str:
    """Stable pseudonymous host key; the raw machine id is never returned or stored."""
    if not isinstance(machine_id, (bytes, bytearray)):
        raise BaselineError("HOST_IDENTITY_INVALID")
    normalized = bytes(machine_id).strip(_ASCII_WHITESPACE)
    if not _MACHINE_ID.fullmatch(normalized):
        raise BaselineError("HOST_IDENTITY_INVALID")
    return "pmhost-v1:" + _domain_hash(b"polymarket-execution-host-v1\0", normalized)


def derive_boot_instance_id(boot_id: bytes) -> str:
    """Ephemeral pseudonymous boot key; the raw kernel boot UUID is never returned."""
    if not isinstance(boot_id, (bytes, bytearray)):
        raise BaselineError("BOOT_IDENTITY_INVALID")
    normalized = bytes(boot_id).strip(_ASCII_WHITESPACE)
    if not _BOOT_UUID.fullmatch(normalized):
        raise BaselineError("BOOT_IDENTITY_INVALID")
    return "pmboot-v1:" + _domain_hash(b"polymarket-execution-boot-v1\0", normalized)


def _read_identity_source(path: pathlib.Path, code: str) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(256)
    except OSError as error:
        raise BaselineError(code) from error


def read_host_instance_id(path: pathlib.Path = MACHINE_ID_PATH) -> str:
    return derive_host_instance_id(_read_identity_source(path, "HOST_IDENTITY_INVALID"))


def read_boot_instance_id(path: pathlib.Path = BOOT_ID_PATH) -> str:
    return derive_boot_instance_id(_read_identity_source(path, "BOOT_IDENTITY_INVALID"))


def derive_process_instance_id(
    boot_instance_id: str, start_monotonic_ns: int, release_sha: str
) -> str:
    """Pseudonymous per-process identity: boot identity + process-start clock + exact release."""
    if (
        not isinstance(boot_instance_id, str)
        or not _BOOT_INSTANCE_ID.fullmatch(boot_instance_id)
        or not isinstance(start_monotonic_ns, int)
        or isinstance(start_monotonic_ns, bool)
        or start_monotonic_ns < 0
        or not isinstance(release_sha, str)
        or not _HEX40.fullmatch(release_sha)
    ):
        raise BaselineError("PROCESS_IDENTITY_INVALID")
    return "pmproc-v1:" + _domain_hash(
        b"polymarket-execution-probe-process-v1\0",
        boot_instance_id.encode("ascii"),
        str(start_monotonic_ns).encode("ascii"),
        release_sha.encode("ascii"),
    )


def _atomic_write_json(path: pathlib.Path, value: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(value) + b"\n")
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def _release_sha_from_manifest(active_release: pathlib.Path) -> str:
    try:
        manifest = json.loads((active_release / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BaselineError("ACTIVE_RELEASE_INVALID") from error
    repo_sha = manifest.get("repo_sha") if isinstance(manifest, dict) else None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_id") != "polymarket-research-release-manifest"
        or not isinstance(repo_sha, str)
        or not _HEX40.fullmatch(repo_sha)
    ):
        raise BaselineError("ACTIVE_RELEASE_INVALID")
    return repo_sha


def _require_exact_release_root(
    active_release: pathlib.Path, releases_root: pathlib.Path, expected_sha: str
) -> None:
    try:
        resolved = active_release.resolve(strict=True)
        expected = (releases_root / expected_sha).resolve(strict=True)
    except OSError as error:
        raise BaselineError("CURRENT_RELEASE_MISMATCH") from error
    if resolved != expected:
        raise BaselineError("CURRENT_RELEASE_MISMATCH")


def _critical_probe_unit_sha256(unit_dir: pathlib.Path) -> str:
    unit = unit_dir / CRITICAL_PROBE_UNIT
    if unit.is_symlink() or not unit.is_file():
        raise BaselineError("CRITICAL_PROBE_UNIT_MISSING")
    return _sha256(unit)


def build_execution_host_binding(
    *,
    active_release: pathlib.Path,
    expected_sha: str,
    unit_dir: pathlib.Path,
    releases_root: pathlib.Path = RELEASES_ROOT,
    machine_id_path: pathlib.Path = MACHINE_ID_PATH,
) -> dict[str, Any]:
    """Verify the exact active release, then bind it to the stable host identity.

    The binding is durable identity, not an observation: it carries no timestamp.
    """
    if not isinstance(expected_sha, str) or not _HEX40.fullmatch(expected_sha):
        raise BaselineError("EXPECTED_SHA_INVALID")
    _require_exact_release_root(active_release, releases_root, expected_sha)
    verified = verify_release(active_release, expected_sha, allow_activation_artifacts=True)
    return {
        "schema_id": BINDING_SCHEMA_ID,
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "host_instance_id": read_host_instance_id(machine_id_path),
        "bound_release_sha": expected_sha,
        "release_manifest_sha256": verified["release_manifest_sha256"],
        "critical_probe_unit_sha256": _critical_probe_unit_sha256(unit_dir),
    }


def write_execution_host_binding(output: pathlib.Path, binding: dict[str, Any]) -> None:
    """Atomically write canonical binding JSON readable but not writable by the runtime user."""
    _atomic_write_json(output, validate_execution_host_binding(binding), mode=0o644)


def validate_execution_host_binding(binding: Any) -> dict[str, Any]:
    keys = {
        "schema_id",
        "schema_version",
        "host_instance_id",
        "bound_release_sha",
        "release_manifest_sha256",
        "critical_probe_unit_sha256",
    }
    if (
        not isinstance(binding, dict)
        or set(binding) != keys
        or binding["schema_id"] != BINDING_SCHEMA_ID
        or binding["schema_version"] != EXECUTION_SCHEMA_VERSION
        or not isinstance(binding["host_instance_id"], str)
        or not _HOST_INSTANCE_ID.fullmatch(binding["host_instance_id"])
        or not isinstance(binding["bound_release_sha"], str)
        or not _HEX40.fullmatch(binding["bound_release_sha"])
        or not all(
            isinstance(binding[key], str) and _HEX64.fullmatch(binding[key])
            for key in ("release_manifest_sha256", "critical_probe_unit_sha256")
        )
    ):
        raise BaselineError("BINDING_INVALID")
    return dict(binding)


def _firewall_state(ssh_port: int | None) -> str:
    try:
        status_text = _run(["ufw", "status"])
    except BaselineError:
        return "unknown"
    lines = status_text.splitlines()
    if not lines or lines[0].strip().lower() != "status: active":
        return "inactive"
    if ssh_port is None:
        return "active"
    try:
        verify_ufw_ssh_only(status_text, ssh_port, allow_empty=False)
    except BaselineError:
        return "not_ssh_only"
    return "ssh_only_inbound"


def _persistent_state(state_root: pathlib.Path) -> str:
    for name in PERSISTENT_STATE_DIRS:
        path = state_root / name
        if path.is_symlink() or not path.is_dir():
            return "missing"
    return "present"


def evaluate_execution_host_currentness(
    *,
    binding: Any,
    active_release: pathlib.Path,
    expected_sha: str,
    unit_dir: pathlib.Path,
    releases_root: pathlib.Path = RELEASES_ROOT,
    state_root: pathlib.Path = STATE_ROOT,
    machine_id_path: pathlib.Path = MACHINE_ID_PATH,
    boot_id_path: pathlib.Path = BOOT_ID_PATH,
    strict: bool = False,
    ssh_port: int | None = None,
) -> dict[str, Any]:
    """Read-only currentness evidence. Every mismatch fails closed with a stable code."""
    if strict and ssh_port is None:
        raise BaselineError("STRICT_SSH_PORT_REQUIRED")
    bound = validate_execution_host_binding(binding)
    if not isinstance(expected_sha, str) or not _HEX40.fullmatch(expected_sha):
        raise BaselineError("EXPECTED_SHA_INVALID")
    host_instance_id = read_host_instance_id(machine_id_path)
    if host_instance_id != bound["host_instance_id"]:
        raise BaselineError("HOST_BINDING_MISMATCH")
    if bound["bound_release_sha"] != expected_sha:
        raise BaselineError("RELEASE_BINDING_MISMATCH")
    _require_exact_release_root(active_release, releases_root, expected_sha)
    active_sha = _release_sha_from_manifest(active_release)
    if active_sha != expected_sha:
        raise BaselineError("ACTIVE_RELEASE_MISMATCH")
    verified = verify_release(active_release, expected_sha, allow_activation_artifacts=True)
    if verified["release_manifest_sha256"] != bound["release_manifest_sha256"]:
        raise BaselineError("RELEASE_MANIFEST_MISMATCH")
    unit_sha = _critical_probe_unit_sha256(unit_dir)
    if unit_sha != bound["critical_probe_unit_sha256"]:
        raise BaselineError("CRITICAL_PROBE_UNIT_MISMATCH")
    boot_instance_id = read_boot_instance_id(boot_id_path)
    ntp_state = _ntp_state()
    firewall_state = _firewall_state(ssh_port)
    persistent_state = _persistent_state(state_root)
    if strict:
        if ntp_state != "synchronized":
            raise BaselineError("HOST_NTP_NOT_SYNCHRONIZED")
        if firewall_state != "ssh_only_inbound":
            raise BaselineError("HOST_FIREWALL_NOT_SSH_ONLY")
        if persistent_state != "present":
            raise BaselineError("PERSISTENT_STATE_MISSING")
    return {
        "schema_id": CURRENTNESS_SCHEMA_ID,
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "status": "EXECUTION_HOST_CURRENT",
        "verification_mode": "strict" if strict else "observe",
        "host_instance_id": host_instance_id,
        "boot_instance_id": boot_instance_id,
        "bound_release_sha": bound["bound_release_sha"],
        "active_release_sha": active_sha,
        "release_manifest_sha256": verified["release_manifest_sha256"],
        "critical_probe_unit_sha256": unit_sha,
        "critical_probe_state": _systemctl_state(CRITICAL_PROBE_UNIT),
        "telemetry_timer_state": _systemctl_state("polymarket-host-telemetry.timer"),
        "research_target_state": _systemctl_state("polymarket-research.target"),
        "ntp_state": ntp_state,
        "firewall_state": firewall_state,
        "persistent_state": persistent_state,
    }


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01 non-economic critical probe
# ---------------------------------------------------------------------------


def _acquire_writer_lock(lock_path: pathlib.Path) -> IO[bytes]:
    """Single-writer guard released by the kernel when the holding process dies."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif msvcrt is not None:  # pragma: no cover - Windows development hosts
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:  # pragma: no cover - unsupported platform
            raise OSError("no advisory lock primitive")
    except OSError as error:
        handle.close()
        raise BaselineError("PROBE_WRITER_ACTIVE") from error
    return handle


def run_critical_probe(
    *,
    active_release: pathlib.Path,
    heartbeat_output: pathlib.Path,
    period_ms: int = CRITICAL_PROBE_PERIOD_MS,
    samples_output: pathlib.Path | None = None,
    duration_seconds: int | None = None,
    boot_id_path: pathlib.Path = BOOT_ID_PATH,
    clock: Callable[[], int] = time.monotonic_ns,
    sleeper: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Local deterministic heartbeat/timing work only.

    Service mode (no duration) runs until stopped and atomically replaces one
    heartbeat file. Finite mode additionally writes bounded JSONL samples.
    """
    if not isinstance(period_ms, int) or isinstance(period_ms, bool) or period_ms != CRITICAL_PROBE_PERIOD_MS:
        raise BaselineError("PROBE_PERIOD_INVALID")
    if duration_seconds is not None and (
        not isinstance(duration_seconds, int)
        or isinstance(duration_seconds, bool)
        or not 1 <= duration_seconds <= CRITICAL_PROBE_MAX_DURATION_SECONDS
    ):
        raise BaselineError("PROBE_DURATION_INVALID")
    if samples_output is not None and duration_seconds is None:
        raise BaselineError("PROBE_SAMPLES_REQUIRE_DURATION")
    release_sha = _release_sha_from_manifest(active_release)
    boot_instance_id = read_boot_instance_id(boot_id_path)
    lock = _acquire_writer_lock(heartbeat_output.with_name(heartbeat_output.name + ".lock"))
    samples: IO[bytes] | None = None
    sequence = 0
    try:
        if samples_output is not None:
            samples_output.parent.mkdir(parents=True, exist_ok=True)
            try:
                samples = samples_output.open("xb")
            except FileExistsError as error:
                raise BaselineError("PROBE_OUTPUT_EXISTS") from error
        start = clock()
        process_instance_id = derive_process_instance_id(boot_instance_id, start, release_sha)
        period_ns = period_ms * 1_000_000
        deadline = None if duration_seconds is None else start + duration_seconds * 1_000_000_000
        max_samples = None if duration_seconds is None else duration_seconds * 1000 // period_ms + 8
        previous = start
        target = start + period_ns
        while True:
            now = clock()
            if target > now:
                sleeper((target - now) / 1_000_000_000)
                now = clock()
            if now <= previous:
                raise BaselineError("PROBE_CLOCK_INVALID")
            sequence += 1
            sample = {
                "schema_version": EXECUTION_SCHEMA_VERSION,
                "release_sha": release_sha,
                "process_instance_id": process_instance_id,
                "sequence": sequence,
                "monotonic_ns": now,
                "interval_ms": round((now - previous) / 1_000_000, 3),
            }
            _atomic_write_json(heartbeat_output, {"schema_id": PROBE_HEARTBEAT_SCHEMA_ID, **sample})
            if samples is not None:
                samples.write(_canonical_bytes({"schema_id": PROBE_SAMPLE_SCHEMA_ID, **sample}) + b"\n")
                samples.flush()
            previous = now
            if deadline is not None and (now >= deadline or sequence >= max_samples):  # type: ignore[operator]
                break
            if should_stop is not None and should_stop():
                break
            target += period_ns
            if target <= now:
                target = now + period_ns
    finally:
        if samples is not None:
            samples.close()
        lock.close()
    return {
        "status": "CRITICAL_PROBE_STOPPED",
        "release_sha": release_sha,
        "process_instance_id": process_instance_id,
        "period_ms": period_ms,
        "sample_count": sequence,
    }


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01 research-versus-critical coexistence evaluator
# ---------------------------------------------------------------------------


def _finite_non_negative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _non_negative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validated_probe_stream(rows: Any) -> tuple[str, list[float]] | None:
    """Return (release_sha, intervals) for one valid finite probe stream, else None."""
    keys = {
        "schema_id",
        "schema_version",
        "release_sha",
        "process_instance_id",
        "sequence",
        "monotonic_ns",
        "interval_ms",
    }
    if not isinstance(rows, list) or not rows or len(rows) > COEXISTENCE_MAX_SAMPLES:
        return None
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != keys
            or row["schema_id"] != PROBE_SAMPLE_SCHEMA_ID
            or row["schema_version"] != EXECUTION_SCHEMA_VERSION
            or not isinstance(row["release_sha"], str)
            or not _HEX40.fullmatch(row["release_sha"])
            or not isinstance(row["process_instance_id"], str)
            or not _PROCESS_INSTANCE_ID.fullmatch(row["process_instance_id"])
            or not _positive_integer(row["sequence"])
            or not _non_negative_integer(row["monotonic_ns"])
            or not _finite_non_negative(row["interval_ms"])
        ):
            return None
    first = rows[0]
    for index, row in enumerate(rows):
        if (
            row["release_sha"] != first["release_sha"]
            or row["process_instance_id"] != first["process_instance_id"]
            or row["sequence"] != first["sequence"] + index
        ):
            return None
        if index and row["monotonic_ns"] <= rows[index - 1]["monotonic_ns"]:
            return None
    coverage_ns = rows[-1]["monotonic_ns"] - first["monotonic_ns"] + first["interval_ms"] * 1_000_000
    if coverage_ns < COEXISTENCE_MIN_COVERAGE_NS:
        return None
    return first["release_sha"], [float(row["interval_ms"]) for row in rows]


def _validated_mixed_telemetry(rows: Any) -> list[dict[str, Any]] | None:
    percent_metrics = (
        "memory_utilization_percent",
        "cpu_utilization_percent",
        "disk_utilization_percent",
        "io_wait_percent",
    )
    counters = ("swap_used_kib", "swap_in_pages", "swap_out_pages")
    if not isinstance(rows, list) or len(rows) < 2 or len(rows) > COEXISTENCE_MAX_SAMPLES:
        return None
    for row in rows:
        if not isinstance(row, dict):
            return None
        if not all(
            _finite_non_negative(row.get(metric)) and row.get(metric) <= 100
            for metric in percent_metrics
        ):
            return None
        if not all(_non_negative_integer(row.get(counter)) for counter in counters):
            return None
    return rows


def nearest_rank_p95(values: list[float]) -> float:
    """Nearest-rank p95: the ceil(0.95 * n)-th smallest value (1-based), exact integer rank."""
    if not values:
        raise BaselineError("P95_REQUIRES_SAMPLES")
    ordered = sorted(values)
    rank = (95 * len(ordered) + 99) // 100
    return ordered[rank - 1]


def evaluate_execution_host_coexistence(
    isolated_probe: Any,
    mixed_probe: Any,
    mixed_telemetry: Any,
    research_smoke: Any,
    *,
    expected_release_sha: str | None = None,
) -> dict[str, Any]:
    """Closed research-versus-critical coexistence disposition.

    Invalid or incomplete evidence is always EXECUTION_HOST_INCONCLUSIVE and takes
    precedence over every upgrade or sufficiency label. The output grants no
    purchase, resize, second-host, execution or live authority.
    """
    result: dict[str, Any] = {
        "status": "EXECUTION_HOST_COEXISTENCE_EVALUATED",
        "coexistence_disposition": "EXECUTION_HOST_INCONCLUSIVE",
        "evidence_failure": None,
        "release_sha": None,
        "isolated_sample_count": None,
        "mixed_sample_count": None,
        "telemetry_sample_count": None,
        "isolated_p95_interval_ms": None,
        "mixed_p95_interval_ms": None,
        "critical_degradation_percent": None,
        "critical_deadline_miss": None,
        "research_smoke_raw_count": None,
        "research_smoke_normalized_count": None,
        "research_smoke_store_bytes": None,
    }

    def inconclusive(failure: str) -> dict[str, Any]:
        result["evidence_failure"] = failure
        return result

    isolated = _validated_probe_stream(isolated_probe)
    if isolated is None:
        return inconclusive("ISOLATED_PROBE_EVIDENCE_INVALID")
    mixed = _validated_probe_stream(mixed_probe)
    if mixed is None:
        return inconclusive("MIXED_PROBE_EVIDENCE_INVALID")
    if isolated[0] != mixed[0] or (
        expected_release_sha is not None and isolated[0] != expected_release_sha
    ):
        return inconclusive("RELEASE_BINDING_MISMATCH")
    telemetry = _validated_mixed_telemetry(mixed_telemetry)
    if telemetry is None:
        return inconclusive("MIXED_TELEMETRY_INCOMPLETE")
    if not _research_smoke_passed(research_smoke):
        return inconclusive("RESEARCH_SMOKE_NOT_PASSED")
    isolated_p95 = nearest_rank_p95(isolated[1])
    mixed_p95 = nearest_rank_p95(mixed[1])
    deadline_miss = any(value > CRITICAL_DEADLINE_MS for value in isolated[1] + mixed[1])
    # Exact rational comparison: strictly more than 20% degradation (boundary is not a trigger).
    degraded = Fraction(mixed_p95) > Fraction(isolated_p95) * CRITICAL_DEGRADATION_RATIO
    first = telemetry[0]
    memory = (
        any(row["memory_utilization_percent"] >= 85 for row in telemetry)
        or any(row["swap_used_kib"] > 0 for row in telemetry)
        or any(row["swap_in_pages"] > first["swap_in_pages"] for row in telemetry)
        or any(row["swap_out_pages"] > first["swap_out_pages"] for row in telemetry)
    )
    triggers = (
        ("CRITICAL_DEADLINE", deadline_miss),
        ("CRITICAL_DEGRADATION", degraded),
        ("MEMORY", memory),
        ("CPU", any(row["cpu_utilization_percent"] >= 85 for row in telemetry)),
        ("DISK", any(row["disk_utilization_percent"] >= 80 for row in telemetry)),
        ("IO", any(row["io_wait_percent"] >= 10 for row in telemetry)),
    )
    disposition = next(
        (f"UPGRADE_ELIGIBLE:{reason}" for reason, fired in triggers if fired),
        "C8G_EXECUTION_HOST_SUFFICIENT",
    )
    if disposition not in COEXISTENCE_DISPOSITIONS:  # pragma: no cover - defensive
        raise BaselineError("COEXISTENCE_DISPOSITION_INVALID")
    result.update(
        {
            "coexistence_disposition": disposition,
            "release_sha": isolated[0],
            "isolated_sample_count": len(isolated[1]),
            "mixed_sample_count": len(mixed[1]),
            "telemetry_sample_count": len(telemetry),
            "isolated_p95_interval_ms": isolated_p95,
            "mixed_p95_interval_ms": mixed_p95,
            "critical_degradation_percent": (
                round((mixed_p95 - isolated_p95) / isolated_p95 * 100, 3) if isolated_p95 > 0 else None
            ),
            "critical_deadline_miss": deadline_miss,
            "research_smoke_raw_count": research_smoke["raw_count"],
            "research_smoke_normalized_count": research_smoke["normalized_count"],
            "research_smoke_store_bytes": research_smoke["store_bytes"],
        }
    )
    return result


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01 terminal Phase-B evidence semantics
# ---------------------------------------------------------------------------


def _strict_current(currentness: Any, merge_sha: str) -> bool:
    return (
        isinstance(currentness, dict)
        and currentness.get("schema_id") == CURRENTNESS_SCHEMA_ID
        and currentness.get("schema_version") == EXECUTION_SCHEMA_VERSION
        and currentness.get("status") == "EXECUTION_HOST_CURRENT"
        and currentness.get("verification_mode") == "strict"
        and isinstance(currentness.get("host_instance_id"), str)
        and bool(_HOST_INSTANCE_ID.fullmatch(currentness["host_instance_id"]))
        and isinstance(currentness.get("boot_instance_id"), str)
        and bool(_BOOT_INSTANCE_ID.fullmatch(currentness["boot_instance_id"]))
        and currentness.get("bound_release_sha") == merge_sha
        and currentness.get("active_release_sha") == merge_sha
        and isinstance(currentness.get("release_manifest_sha256"), str)
        and bool(_HEX64.fullmatch(currentness["release_manifest_sha256"]))
        and isinstance(currentness.get("critical_probe_unit_sha256"), str)
        and bool(_HEX64.fullmatch(currentness["critical_probe_unit_sha256"]))
        and currentness.get("telemetry_timer_state") == "active"
        and currentness.get("research_target_state") == "active"
        and currentness.get("ntp_state") == "synchronized"
        and currentness.get("firewall_state") == "ssh_only_inbound"
        and currentness.get("persistent_state") == "present"
    )


def _valid_heartbeat(heartbeat: Any, merge_sha: str) -> bool:
    return (
        isinstance(heartbeat, dict)
        and heartbeat.get("schema_id") == PROBE_HEARTBEAT_SCHEMA_ID
        and heartbeat.get("schema_version") == EXECUTION_SCHEMA_VERSION
        and heartbeat.get("release_sha") == merge_sha
        and isinstance(heartbeat.get("process_instance_id"), str)
        and bool(_PROCESS_INSTANCE_ID.fullmatch(heartbeat["process_instance_id"]))
        and _positive_integer(heartbeat.get("sequence"))
        and _non_negative_integer(heartbeat.get("monotonic_ns"))
        and _finite_non_negative(heartbeat.get("interval_ms"))
    )


def _proof(present: bool, passed: bool) -> str:
    if not present:
        return "INCONCLUSIVE"
    return "PASS" if passed else "FAIL"


def evaluate_execution_host_terminal(evidence: Any) -> dict[str, Any]:
    """Closed terminal outcome for one real Phase-B run.

    EXECUTION_HOST_PROVEN_C8G means only that the host/runtime substrate was proven on
    the tested instance. It never implies account access, reconciliation, order
    permission, live enablement or that S10-LIVE-ORCH-01 may be skipped.
    """
    document = evidence if isinstance(evidence, dict) else {}
    valid_document = (
        document.get("schema_id") == TERMINAL_EVIDENCE_SCHEMA_ID
        and document.get("schema_version") == EXECUTION_SCHEMA_VERSION
        and isinstance(document.get("merge_sha"), str)
        and bool(_HEX40.fullmatch(document["merge_sha"]))
    )
    merge_sha = document.get("merge_sha") if valid_document else ""

    pre = document.get("currentness_pre_reboot")
    post = document.get("currentness_post_reboot")
    pre_ok = valid_document and _strict_current(pre, merge_sha)
    post_ok = valid_document and _strict_current(post, merge_sha)

    restart = document.get("process_restart")
    restart_ok = (
        valid_document
        and isinstance(restart, dict)
        and _valid_heartbeat(restart.get("pre_heartbeat"), merge_sha)
        and _valid_heartbeat(restart.get("post_heartbeat"), merge_sha)
        and restart["pre_heartbeat"]["process_instance_id"] != restart["post_heartbeat"]["process_instance_id"]
        and restart["post_heartbeat"]["sequence"] >= 2
        and restart.get("service_state_after") == "active"
        and restart.get("active_writer_count") == 1
        and not isinstance(restart.get("active_writer_count"), bool)
    )

    backup = document.get("backup")
    restore = document.get("restore")
    post_restore = document.get("post_reboot_restore")
    backup_ok = (
        isinstance(backup, dict)
        and backup.get("status") == "BACKUP_COMPLETE"
        and _positive_integer(backup.get("file_count"))
        and isinstance(backup.get("backup_manifest_sha256"), str)
        and bool(_HEX64.fullmatch(backup["backup_manifest_sha256"]))
        and isinstance(backup.get("backup_id"), str)
        and bool(_SAFE_ID.fullmatch(backup["backup_id"]))
    )

    def restored(drill: Any) -> bool:
        return (
            backup_ok
            and isinstance(drill, dict)
            and drill.get("status") == "RESTORE_VERIFIED"
            and drill.get("source_backup_id") == backup["backup_id"]
            and _positive_integer(drill.get("file_count"))
            and drill["file_count"] == backup["file_count"]
        )

    restore_ok = restored(restore)
    persistent_ok = (
        restored(post_restore)
        and restore_ok
        and post_restore.get("drill_id") != restore.get("drill_id")
        and post_ok
    )

    reboot_ok = (
        pre_ok
        and post_ok
        and pre["host_instance_id"] == post["host_instance_id"]
        and pre["boot_instance_id"] != post["boot_instance_id"]
        and pre["release_manifest_sha256"] == post["release_manifest_sha256"]
        and pre["critical_probe_unit_sha256"] == post["critical_probe_unit_sha256"]
        and post.get("critical_probe_state") == "active"
    )
    host_controls_ok = (
        pre_ok
        and post_ok
        and isinstance(restart, dict)
        and restart.get("observed_slice") == "polymarket-critical.slice"
    )

    coexistence = document.get("coexistence")
    disposition = coexistence.get("coexistence_disposition") if isinstance(coexistence, dict) else None
    coexistence_ok = (
        valid_document
        and isinstance(coexistence, dict)
        and coexistence.get("status") == "EXECUTION_HOST_COEXISTENCE_EVALUATED"
        and disposition in COEXISTENCE_DISPOSITIONS
        and disposition != "EXECUTION_HOST_INCONCLUSIVE"
        and coexistence.get("release_sha") == merge_sha
    )

    authority = document.get("authority")
    authority_ok = (
        isinstance(authority, dict)
        and set(authority) == {"trading_credentials_used", "orders", "capital_usd", "live"}
        and authority["trading_credentials_used"] is False
        and _non_negative_integer(authority["orders"])
        and authority["orders"] == 0
        and _non_negative_integer(authority["capital_usd"])
        and authority["capital_usd"] == 0
        and authority["live"] == "DISABLED"
    )

    proofs = {
        "currentness": _proof(isinstance(pre, dict), pre_ok),
        "host_binding": _proof(
            isinstance(pre, dict) and isinstance(post, dict),
            pre_ok and post_ok and pre["host_instance_id"] == post["host_instance_id"],
        ),
        "process_restart": _proof(isinstance(restart, dict), restart_ok),
        "reboot_recovery": _proof(isinstance(pre, dict) and isinstance(post, dict), reboot_ok),
        "backup_restore": _proof(isinstance(backup, dict) and isinstance(restore, dict), restore_ok),
        "persistent_state": _proof(isinstance(post_restore, dict), persistent_ok),
        "host_controls": _proof(isinstance(pre, dict) and isinstance(post, dict), host_controls_ok),
        "coexistence": _proof(isinstance(coexistence, dict), coexistence_ok),
        "authority": _proof(isinstance(authority, dict), authority_ok),
    }
    if valid_document and all(value == "PASS" for value in proofs.values()):
        if disposition == "C8G_EXECUTION_HOST_SUFFICIENT":
            outcome = "EXECUTION_HOST_PROVEN_C8G"
        else:
            outcome = "EXECUTION_HOST_EVIDENCE_COMPLETE_" + str(disposition)
    else:
        outcome = "EXECUTION_HOST_INCONCLUSIVE"
    if outcome not in TERMINAL_OUTCOMES:  # pragma: no cover - defensive
        raise BaselineError("TERMINAL_OUTCOME_INVALID")
    return {
        "status": "EXECUTION_HOST_TERMINAL_EVALUATED",
        "terminal_outcome": outcome,
        "proofs": proofs,
        "coexistence_disposition": disposition if coexistence_ok else "EXECUTION_HOST_INCONCLUSIVE",
        "live_readiness": "NOT_IMPLIED",
        "required_successor": "S10-LIVE-ORCH-01",
    }


def _load_evidence_bytes(path: pathlib.Path) -> bytes | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > EVIDENCE_MAX_BYTES:
            return None
        return path.read_bytes()
    except OSError:
        return None


def _load_jsonl_evidence(path: pathlib.Path) -> list[Any] | None:
    raw = _load_evidence_bytes(path)
    if raw is None:
        return None
    try:
        return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeError, ValueError):
        return None


def _load_json_evidence(path: pathlib.Path) -> Any:
    raw = _load_evidence_bytes(path)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return None


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
    bind = commands.add_parser("execution-host-bind")
    bind.add_argument("--active-release", type=pathlib.Path, required=True)
    bind.add_argument("--expected-sha", required=True)
    bind.add_argument("--unit-dir", type=pathlib.Path, required=True)
    bind.add_argument("--output", type=pathlib.Path, required=True)
    current = commands.add_parser("execution-host-currentness")
    current.add_argument("--binding-file", type=pathlib.Path, required=True)
    current.add_argument("--active-release", type=pathlib.Path, required=True)
    current.add_argument("--expected-sha", required=True)
    current.add_argument("--unit-dir", type=pathlib.Path, required=True)
    current.add_argument("--strict", action="store_true")
    current.add_argument("--ssh-port", type=int)
    probe = commands.add_parser("critical-probe")
    probe.add_argument("--active-release", type=pathlib.Path, required=True)
    probe.add_argument("--period-ms", type=int, default=CRITICAL_PROBE_PERIOD_MS)
    probe.add_argument("--heartbeat-output", type=pathlib.Path, required=True)
    probe.add_argument("--samples-output", type=pathlib.Path)
    probe.add_argument("--duration-seconds", type=int)
    coexist = commands.add_parser("execution-host-coexistence-evaluate")
    coexist.add_argument("--isolated-probe-jsonl", type=pathlib.Path, required=True)
    coexist.add_argument("--mixed-probe-jsonl", type=pathlib.Path, required=True)
    coexist.add_argument("--mixed-telemetry-jsonl", type=pathlib.Path, required=True)
    coexist.add_argument("--research-smoke-result", type=pathlib.Path, required=True)
    coexist.add_argument("--expected-sha")
    terminal = commands.add_parser("execution-host-terminal-evaluate")
    terminal.add_argument("--evidence", type=pathlib.Path, required=True)
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
        elif args.command == "execution-host-bind":
            result = build_execution_host_binding(
                active_release=args.active_release,
                expected_sha=args.expected_sha,
                unit_dir=args.unit_dir,
                releases_root=RELEASES_ROOT,
                machine_id_path=MACHINE_ID_PATH,
            )
            write_execution_host_binding(args.output, result)
        elif args.command == "execution-host-currentness":
            result = evaluate_execution_host_currentness(
                binding=_load_json_evidence(args.binding_file),
                active_release=args.active_release,
                expected_sha=args.expected_sha,
                unit_dir=args.unit_dir,
                releases_root=RELEASES_ROOT,
                state_root=STATE_ROOT,
                machine_id_path=MACHINE_ID_PATH,
                boot_id_path=BOOT_ID_PATH,
                strict=args.strict,
                ssh_port=args.ssh_port,
            )
        elif args.command == "critical-probe":
            result = run_critical_probe(
                active_release=args.active_release,
                heartbeat_output=args.heartbeat_output,
                period_ms=args.period_ms,
                samples_output=args.samples_output,
                duration_seconds=args.duration_seconds,
                boot_id_path=BOOT_ID_PATH,
            )
        elif args.command == "execution-host-coexistence-evaluate":
            result = evaluate_execution_host_coexistence(
                _load_jsonl_evidence(args.isolated_probe_jsonl),
                _load_jsonl_evidence(args.mixed_probe_jsonl),
                _load_jsonl_evidence(args.mixed_telemetry_jsonl),
                _load_json_evidence(args.research_smoke_result),
                expected_release_sha=args.expected_sha,
            )
        elif args.command == "execution-host-terminal-evaluate":
            result = evaluate_execution_host_terminal(_load_json_evidence(args.evidence))
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
