from __future__ import annotations

import ast
import hashlib
import inspect
import math
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import tomllib

import pytest

from tools.deployment import runtime_baseline as baseline


ROOT = pathlib.Path(__file__).resolve().parents[2]


def _git(repo: pathlib.Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: pathlib.Path, files: dict[str, str]) -> tuple[pathlib.Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    return repo, _git(repo, "rev-parse", "HEAD")


def _manifest_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(baseline._canonical_bytes(payload)).hexdigest()


def test_release_requires_clean_exact_head(tmp_path: pathlib.Path) -> None:
    repo, head = _repo(tmp_path, {"safe.txt": "safe\n"})
    with pytest.raises(baseline.BaselineError, match="HEAD_MISMATCH"):
        baseline.build_release(repo, "0" * 40, tmp_path / "wrong")
    (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="SOURCE_TREE_DIRTY"):
        baseline.build_release(repo, head, tmp_path / "dirty")


def test_release_excludes_untracked_and_secret_like_paths(tmp_path: pathlib.Path) -> None:
    repo, head = _repo(
        tmp_path,
        {".gitignore": "local_data/\n", "safe.txt": "safe\n"},
    )
    ignored = repo / "local_data" / "ignored.txt"
    ignored.parent.mkdir()
    ignored.write_text("ignored", encoding="utf-8")
    baseline.build_release(repo, head, tmp_path / "output")
    manifest = json.loads(
        (tmp_path / "output" / head / baseline.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert {item["path"] for item in manifest["files"]} == {".gitignore", "safe.txt"}

    secret_repo, secret_head = _repo(
        tmp_path / "secret-case", {"credentials/value.txt": "placeholder"}
    )
    with pytest.raises(baseline.BaselineError, match="CREDENTIAL_LIKE_TRACKED_PATH"):
        baseline.build_release(secret_repo, secret_head, tmp_path / "secret-output")

    payload_repo, payload_head = _repo(
        tmp_path / "payload-case",
        {
            "unsafe.txt": "-----BEGIN " + "PRIVATE KEY-----\n"
            + ("QUJD" * 20)
            + "\n-----END " + "PRIVATE KEY-----\n"
        },
    )
    with pytest.raises(baseline.BaselineError, match="CREDENTIAL_LIKE_TRACKED_PAYLOAD"):
        baseline.build_release(payload_repo, payload_head, tmp_path / "payload-output")


def test_release_manifest_is_deterministic(tmp_path: pathlib.Path) -> None:
    repo, head = _repo(tmp_path, {"b.txt": "beta", "a.txt": "alpha"})
    baseline.build_release(repo, head, tmp_path / "one")
    baseline.build_release(repo, head, tmp_path / "two")
    first = (tmp_path / "one" / head / baseline.MANIFEST_NAME).read_bytes()
    second = (tmp_path / "two" / head / baseline.MANIFEST_NAME).read_bytes()
    assert first == second
    assert str(tmp_path).encode() not in first
    assert baseline.verify_release(tmp_path / "one" / head, head)["status"] == "RELEASE_VERIFIED"


def test_release_verifier_rejects_file_set_and_hash_changes(tmp_path: pathlib.Path) -> None:
    repo, head = _repo(tmp_path, {"a.txt": "alpha", "b.txt": "beta"})
    baseline.build_release(repo, head, tmp_path / "output")
    release = tmp_path / "output" / head
    added = tmp_path / "added"
    missing = tmp_path / "missing"
    tampered = tmp_path / "tampered"
    shutil.copytree(release, added)
    shutil.copytree(release, missing)
    shutil.copytree(release, tampered)
    (added / "extra.txt").write_text("extra", encoding="utf-8")
    (missing / "a.txt").unlink()
    (tampered / "a.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="RELEASE_FILE_SET_MISMATCH"):
        baseline.verify_release(added, head)
    with pytest.raises(baseline.BaselineError, match="RELEASE_FILE_SET_MISMATCH"):
        baseline.verify_release(missing, head)
    with pytest.raises(baseline.BaselineError, match="RELEASE_FILE_TAMPERED"):
        baseline.verify_release(tampered, head)


def test_host_floor_accepts_frozen_target() -> None:
    assert baseline.validate_host_facts(
        {
            "os_id": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
            "logical_cpu_count": 4,
            "memory_total_bytes": 8 * 1024**3,
            "disk_total_bytes": 75 * 1024**3,
        }
    ) is None


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("os_version", "22.04", "HOST_OS_UNSUPPORTED"),
        ("architecture", "aarch64", "HOST_ARCH_UNSUPPORTED"),
        ("logical_cpu_count", 3, "HOST_CPU_FLOOR_NOT_MET"),
        ("memory_total_bytes", 1, "HOST_MEMORY_FLOOR_NOT_MET"),
        ("disk_total_bytes", 1, "HOST_DISK_FLOOR_NOT_MET"),
    ],
)
def test_host_floor_rejects_wrong_facts(field: str, value: object, code: str) -> None:
    facts = {
        "os_id": "ubuntu",
        "os_version": "24.04",
        "architecture": "x86_64",
        "logical_cpu_count": 4,
        "memory_total_bytes": 8 * 1024**3,
        "disk_total_bytes": 75 * 1024**3,
    }
    facts[field] = value
    with pytest.raises(baseline.BaselineError, match=code):
        baseline.validate_host_facts(facts)


def test_host_manifest_is_sanitized(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / baseline.MANIFEST_NAME).write_text(
        json.dumps({"repo_sha": "a" * 40}), encoding="utf-8"
    )
    units = tmp_path / "units"
    units.mkdir()
    monkeypatch.setattr(
        baseline,
        "_run",
        lambda command, cwd=None: "active" if "is-active" in command else "unavailable",
    )
    result = baseline.collect_host_manifest(
        active_release=release,
        unit_dir=units,
        opt_path=tmp_path,
        state_path=tmp_path,
    )
    encoded = json.dumps(result).lower()
    for forbidden in (
        "hostname",
        "ip_address",
        "ssh_username",
        "environment",
        "provider_account",
        "credential",
    ):
        assert forbidden not in encoded
    assert result["active_release_sha"] == "a" * 40


def test_telemetry_schema_is_sanitized(tmp_path: pathlib.Path) -> None:
    result = baseline.collect_telemetry(disk_path=tmp_path)
    assert set(result) == {
        "schema_id",
        "schema_version",
        "timestamp_utc",
        "cpu_utilization_percent",
        "load_average",
        "memory_available_kib",
        "memory_utilization_percent",
        "swap_used_kib",
        "swap_in_pages",
        "swap_out_pages",
        "disk_utilization_percent",
        "io_wait_percent",
        "research_target_state",
        "telemetry_timer_state",
    }
    assert not any(key in result for key in ("hostname", "ip", "environment", "command_line"))


def test_cpu_and_iowait_are_computed_from_interval_delta() -> None:
    first = (1000, 200, 300, 4000, 500, 60, 70, 80)
    second = (1040, 210, 310, 4020, 510, 60, 70, 80)
    cpu, io_wait = baseline._cpu_delta_percentages(first, second)
    assert cpu == 77.778
    assert io_wait == 11.111


def test_cpu_percentages_ignore_cumulative_since_boot_magnitude() -> None:
    small = baseline._cpu_delta_percentages(
        (10, 20, 30, 40, 50), (20, 20, 30, 50, 50)
    )
    large = baseline._cpu_delta_percentages(
        (1_000_010, 2_000_020, 3_000_030, 4_000_040, 5_000_050),
        (1_000_020, 2_000_020, 3_000_030, 4_000_050, 5_000_050),
    )
    assert small == large == (50.0, 0.0)


def test_collect_telemetry_uses_two_bounded_samples(tmp_path: pathlib.Path) -> None:
    samples = iter(((100, 0, 0, 900, 0), (150, 0, 0, 950, 10)))
    sleeps: list[float] = []
    result = baseline.collect_telemetry(
        disk_path=tmp_path,
        stat_reader=lambda: next(samples),
        sleeper=sleeps.append,
        sample_interval_seconds=0.25,
    )
    assert sleeps == [0.25]
    assert result["cpu_utilization_percent"] == 54.545
    assert result["io_wait_percent"] == 9.091


def test_nonpositive_cpu_delta_is_unavailable(tmp_path: pathlib.Path) -> None:
    samples = iter(((100, 0, 0, 900, 0), (100, 0, 0, 900, 0)))
    result = baseline.collect_telemetry(
        disk_path=tmp_path,
        stat_reader=lambda: next(samples),
        sleeper=lambda _: None,
    )
    assert result["cpu_utilization_percent"] is None
    assert result["io_wait_percent"] is None


def test_telemetry_rotation_is_bounded(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(baseline, "TELEMETRY_MAX_BYTES", 1)
    output = tmp_path / "host.jsonl"
    for sample in range(10):
        baseline.append_telemetry(output, {"sample": sample})
    assert output.exists()
    rotations = sorted(tmp_path.glob("host.jsonl.*"))
    assert len(rotations) == baseline.TELEMETRY_RETAINED
    assert not (tmp_path / "host.jsonl.8").exists()


def test_backup_uses_sqlite_snapshot_and_hashes(tmp_path: pathlib.Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    database = state / "research.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('bounded')")
    backups = tmp_path / "backups"
    backups.mkdir()
    result = baseline.create_backup(state, backups, "backup-1")
    manifest = json.loads(
        (backups / "backup-1" / baseline.BACKUP_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert result["status"] == "BACKUP_COMPLETE"
    assert manifest["files"][0]["sqlite"] is True
    assert len(manifest["files"][0]["sha256"]) == 64


def test_backup_rejects_symlink_and_secret_paths(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("outside", encoding="utf-8")
    escape = state / "escape"
    try:
        escape.symlink_to(outside)
    except OSError:
        escape.write_text("stand-in", encoding="utf-8")
        original_is_symlink = pathlib.Path.is_symlink
        monkeypatch.setattr(
            pathlib.Path,
            "is_symlink",
            lambda self: self == escape or original_is_symlink(self),
        )
    backups = tmp_path / "backups"
    backups.mkdir()
    with pytest.raises(baseline.BaselineError, match="BACKUP_SYMLINK_REJECTED"):
        baseline.create_backup(state, backups, "backup-1")
    escape.unlink()
    (state / "credentials").mkdir()
    (state / "credentials" / "value.txt").write_text("placeholder", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="BACKUP_SECRET_PATH_REJECTED"):
        baseline.create_backup(state, backups, "backup-2")
    shutil.rmtree(state / "credentials")
    (state / "DATA-03").mkdir()
    (state / "DATA-03" / "evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="BACKUP_DATA03_PATH_REJECTED"):
        baseline.create_backup(state, backups, "backup-3")


def _create_backup_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    state = tmp_path / "state"
    state.mkdir(parents=True)
    with sqlite3.connect(state / "research.sqlite3") as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('bounded')")
    (state / "note.json").write_text("{}", encoding="utf-8")
    backups = tmp_path / "backups"
    backups.mkdir()
    baseline.create_backup(state, backups, "backup-1")
    return backups / "backup-1"


def test_restore_is_isolated_and_never_overwrites(tmp_path: pathlib.Path) -> None:
    backup = _create_backup_fixture(tmp_path)
    restore_root = tmp_path / "restore_drills"
    restore_root.mkdir()
    active = tmp_path / "active.txt"
    active.write_text("unchanged", encoding="utf-8")
    result = baseline.restore_verify(backup, restore_root, "drill-1")
    assert result["status"] == "RESTORE_VERIFIED"
    assert active.read_text(encoding="utf-8") == "unchanged"
    with pytest.raises(baseline.BaselineError, match="RESTORE_TARGET_EXISTS"):
        baseline.restore_verify(backup, restore_root, "drill-1")


def test_restore_detects_tamper_and_sqlite_corruption(tmp_path: pathlib.Path) -> None:
    backup = _create_backup_fixture(tmp_path)
    restore_root = tmp_path / "restore_drills"
    restore_root.mkdir()
    (backup / "note.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="BACKUP_TAMPERED"):
        baseline.restore_verify(backup, restore_root, "tamper")

    clean = _create_backup_fixture(tmp_path / "corrupt-case")
    database = clean / "research.sqlite3"
    database.write_bytes(b"not a sqlite database")
    manifest_path = clean / baseline.BACKUP_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in manifest["files"] if item["sqlite"])
    entry["size"] = database.stat().st_size
    entry["sha256"] = hashlib.sha256(database.read_bytes()).hexdigest()
    payload = {key: manifest[key] for key in ("schema_id", "schema_version", "backup_id", "files")}
    manifest["backup_manifest_sha256"] = _manifest_hash(payload)
    manifest_path.write_bytes(baseline._canonical_bytes(manifest) + b"\n")
    with pytest.raises(baseline.BaselineError, match="SQLITE_INTEGRITY_FAILED"):
        baseline.restore_verify(clean, restore_root, "corrupt")


def _successful_smoke() -> dict[str, object]:
    return {
        "status": "STOPPED",
        "stop_reason": "DURATION_EXPIRED",
        "error_codes": [],
        "raw_count": 2,
        "normalized_count": 2,
        "store_bytes": 128,
    }


def _complete_telemetry(**overrides: float) -> dict[str, float]:
    result = {
        "memory_utilization_percent": 20.0,
        "cpu_utilization_percent": 20.0,
        "disk_utilization_percent": 20.0,
        "io_wait_percent": 1.0,
    }
    result.update(overrides)
    return result


def test_smoke_requires_duration_expiry_and_positive_actual_evidence() -> None:
    passed = baseline.evaluate_research_smoke(_successful_smoke(), [_complete_telemetry()])
    assert passed["smoke_disposition"] == "PUBLIC_RESEARCH_SMOKE_PASS"
    assert passed["capacity_disposition"] == "C8G_RESEARCH_BASELINE_SUFFICIENT"

    for stop_reason in (
        "NETWORK_CALL_LIMIT",
        "RECONNECT_LIMIT",
        "QUEUE_LIMIT",
        "STORE_LIMIT",
        "CALLER_STOP",
    ):
        receipt = {**_successful_smoke(), "stop_reason": stop_reason}
        result = baseline.evaluate_research_smoke(receipt, [_complete_telemetry()])
        assert result["smoke_disposition"] == "BASELINE_INCONCLUSIVE"
        assert result["capacity_disposition"] == "BASELINE_INCONCLUSIVE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("raw_count", 0),
        ("normalized_count", 0),
        ("store_bytes", 0),
        ("raw_count", "1"),
        ("normalized_count", None),
        ("store_bytes", 1.5),
        ("error_codes", ["SOURCE_UNAVAILABLE"]),
    ],
)
def test_smoke_rejects_zero_missing_or_malformed_actual_evidence(field: str, value: object) -> None:
    receipt = {**_successful_smoke(), field: value}
    result = baseline.evaluate_research_smoke(receipt, [_complete_telemetry()])
    assert result["smoke_disposition"] == "BASELINE_INCONCLUSIVE"
    assert result["capacity_disposition"] == "BASELINE_INCONCLUSIVE"

    missing = _successful_smoke()
    missing.pop(field)
    assert baseline.evaluate_research_smoke(missing, [_complete_telemetry()])[
        "smoke_disposition"
    ] == "BASELINE_INCONCLUSIVE"


def test_failed_smoke_and_incomplete_telemetry_are_inconclusive() -> None:
    failed = {**_successful_smoke(), "status": "FAILED"}
    assert baseline.evaluate_research_smoke(failed, [_complete_telemetry()])[
        "capacity_disposition"
    ] == "BASELINE_INCONCLUSIVE"
    for telemetry in ([], [{"memory_utilization_percent": 20}], [_complete_telemetry(cpu_utilization_percent=float("nan"))]):
        result = baseline.evaluate_research_smoke(_successful_smoke(), telemetry)
        assert result["capacity_disposition"] == "BASELINE_INCONCLUSIVE"


def test_capacity_evaluator_has_only_closed_dispositions() -> None:
    cases = [
        ({}, [], "BASELINE_INCONCLUSIVE"),
        (_successful_smoke(), [_complete_telemetry(memory_utilization_percent=90)], "UPGRADE_ELIGIBLE:MEMORY"),
        (_successful_smoke(), [_complete_telemetry(cpu_utilization_percent=90)], "UPGRADE_ELIGIBLE:CPU"),
        (_successful_smoke(), [_complete_telemetry(disk_utilization_percent=90)], "UPGRADE_ELIGIBLE:DISK"),
        (_successful_smoke(), [_complete_telemetry(io_wait_percent=20)], "UPGRADE_ELIGIBLE:IO"),
        (_successful_smoke(), [_complete_telemetry()], "C8G_RESEARCH_BASELINE_SUFFICIENT"),
    ]
    for smoke, telemetry, expected in cases:
        result = baseline.evaluate_research_smoke(smoke, telemetry)
        assert result["capacity_disposition"] == expected
        assert result["capacity_disposition"] in baseline.CAPACITY_DISPOSITIONS


def _unit(name: str) -> str:
    return (ROOT / "tools" / "deployment" / "systemd" / name).read_text(encoding="utf-8")


def test_research_slice_has_exact_controls() -> None:
    text = _unit("polymarket-research.slice")
    for value in ("CPUWeight=25", "CPUQuota=250%", "MemoryHigh=4G", "MemoryMax=5G", "IOWeight=25"):
        assert value in text


def test_critical_slice_has_exact_controls() -> None:
    text = _unit("polymarket-critical.slice")
    for value in ("CPUWeight=100", "MemoryLow=2G", "IOWeight=100"):
        assert value in text


def test_telemetry_timer_is_exactly_one_minute_and_persistent() -> None:
    text = _unit("polymarket-host-telemetry.timer")
    assert "OnBootSec=60s" in text
    assert "OnUnitActiveSec=60s" in text
    assert "Persistent=true" in text
    assert "OnUnitActiveSec=1s" not in text


def test_research_target_contains_only_baseline_telemetry() -> None:
    text = _unit("polymarket-research.target")
    dependency_lines = [line for line in text.splitlines() if line.startswith(("Wants=", "Requires="))]
    assert dependency_lines == ["Wants=polymarket-host-telemetry.timer"]
    lowered = "\n".join(dependency_lines).lower()
    for forbidden in ("market-truth", "hermes", "alpha", "paper", "execution", "trading"):
        assert forbidden not in lowered


def test_bootstrap_shell_contract_is_strict() -> None:
    path = ROOT / "tools" / "deployment" / "bootstrap_ubuntu_24_04.sh"
    text = path.read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in text
    assert all(argument in text for argument in ("--release-dir", "--expected-sha", "--ssh-port"))
    bash = shutil.which("bash")
    git_bash = pathlib.Path(r"C:\Program Files\Git\bin\bash.exe")
    if os.name == "nt" and git_bash.is_file():
        bash = str(git_bash)
    if bash is not None:
        result = subprocess.run(
            [bash, "-n", str(path)], capture_output=True, text=True
        )
        if "execvpe(/bin/bash) failed" in result.stderr:
            pytest.skip("the Windows WSL bash shim has no installed distribution")
        assert result.returncode == 0, result.stderr


def test_firewall_requires_explicit_ssh_port_before_enable() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    assert "((ssh_port >= 1 && ssh_port <= 65535))" in text
    assert "ufw --dry-run allow" in text
    assert text.index('ufw allow "${ssh_port}/tcp"') < text.index("ufw --force enable")


def test_firewall_verifier_accepts_clean_exact_and_ipv6_equivalent_rules() -> None:
    assert baseline.verify_ufw_ssh_only("Status: inactive\n", 2222, allow_empty=True)[
        "allow_count"
    ] == 0
    active = "Status: active\n2222/tcp ALLOW IN Anywhere\n2222/tcp (v6) ALLOW IN Anywhere (v6)\n"
    assert baseline.verify_ufw_ssh_only(active, 2222, allow_empty=False)["allow_count"] == 2
    configured = "Added user rules:\nufw allow 2222/tcp\n"
    assert baseline.verify_ufw_ssh_only(configured, 2222, allow_empty=True)["allow_count"] == 1


def test_firewall_verifier_accepts_exact_ssh_limit_rule() -> None:
    status = "Status: active\n2222/tcp LIMIT IN Anywhere\n2222/tcp (v6) LIMIT IN Anywhere (v6)\n"
    assert baseline.verify_ufw_ssh_only(status, 2222, allow_empty=False)["allow_count"] == 2
    configured = "Added user rules:\nufw limit 2222/tcp\n"
    assert baseline.verify_ufw_ssh_only(configured, 2222, allow_empty=True)["allow_count"] == 1


@pytest.mark.parametrize(
    "conflict",
    [
        "80/tcp ALLOW IN Anywhere",
        "53/udp ALLOW IN Anywhere",
        "80/tcp LIMIT IN Anywhere",
        "53/udp LIMIT IN Anywhere",
        "Anywhere LIMIT FWD Anywhere",
        "ufw route limit 80/tcp",
    ],
)
def test_firewall_verifier_rejects_any_other_inbound_allow(conflict: str) -> None:
    status = f"Status: active\n2222/tcp ALLOW IN Anywhere\n{conflict}\n"
    with pytest.raises(baseline.BaselineError, match="FIREWALL_NOT_SSH_ONLY"):
        baseline.verify_ufw_ssh_only(status, 2222, allow_empty=False)


def test_firewall_success_requires_effective_exact_rule() -> None:
    with pytest.raises(baseline.BaselineError, match="FIREWALL_NOT_SSH_ONLY"):
        baseline.verify_ufw_ssh_only("Status: active\n", 2222, allow_empty=False)


def test_bootstrap_installs_base_project_without_cockpit_extra() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    assert '--disable-pip-version-check "$target_release"' in text
    assert "[cockpit]" not in text
    assert "fastapi" not in text.lower()
    assert "uvicorn" not in text.lower()
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    base_dependencies = metadata["project"]["dependencies"]
    assert any(item.startswith("polymarket-client==") for item in base_dependencies)
    assert any(item.startswith("websockets==") for item in base_dependencies)


def test_bootstrap_repairs_partial_venv_without_reinstalling_complete_environment() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    create_guard = "if [[ ! -x $target_release/.venv/bin/python ]]; then"
    metadata_probe = 'metadata.version("polymarket-strategy-lab")'
    install_command = 'run_or_fail PACKAGE_INSTALL_FAILED "$target_release/.venv/bin/python" -m pip install'
    dependency_check = 'run_or_fail PACKAGE_CHECK_FAILED "$target_release/.venv/bin/python" -m pip check'
    assert create_guard in text
    assert metadata_probe in text
    assert text.index(create_guard) < text.index("python3 -m venv") < text.index(metadata_probe)
    assert text.index(metadata_probe) < text.index(install_command) < text.index(dependency_check)
    metadata_block = text[text.index("if ! \"$target_release/.venv/bin/python\" -c") :]
    assert metadata_block.index(install_command) < metadata_block.index("\nfi\n")
    assert ">/dev/null 2>&1; then" in metadata_block
    assert "[cockpit]" not in install_command


def test_bootstrap_broken_environment_cannot_bypass_closed_dependency_check() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    dependency_check = 'run_or_fail PACKAGE_CHECK_FAILED "$target_release/.venv/bin/python" -m pip check'
    success = "BOOTSTRAP_COMPLETE"
    assert dependency_check in text
    assert text.index(dependency_check) < text.index(success)
    assert '"$@" >/dev/null 2>&1 || fail "$error_code"' in text


def test_bootstrap_routes_operational_failures_to_sanitized_codes() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    assert '"$@" >/dev/null 2>&1 || fail "$error_code"' in text
    assert '"$@" >"$output_path" 2>/dev/null || fail "$error_code"' in text
    assert "trap 'fail UNEXPECTED_OPERATION_FAILED' ERR" in text
    for code in (
        "RELEASE_VERIFY_FAILED",
        "HOST_SETUP_FAILED",
        "PYTHON_ENV_SETUP_FAILED",
        "PACKAGE_INSTALL_FAILED",
        "PACKAGE_CHECK_FAILED",
        "SYSTEMD_INSTALL_FAILED",
        "SYSTEMD_VERIFY_FAILED",
        "FIREWALL_APPLY_FAILED",
        "SERVICE_ACTIVATION_FAILED",
        "HOST_MANIFEST_FAILED",
    ):
        assert code in text


def test_corrected_contract_prompt_and_spec_are_consistent() -> None:
    paths = (
        ROOT / "docs/research_platform_runtime_baseline_contract.md",
        ROOT / "docs/wp_specs/S10-DEPLOY-01/wp_prompt.txt",
        ROOT / "docs/wp_specs/S10-DEPLOY-01/wp_spec.json",
    )
    combined = " ".join(path.read_text(encoding="utf-8") for path in paths)
    for truth in (
        "DURATION_EXPIRED",
        "raw_count",
        "normalized_count",
        "store_bytes",
        "interval",
        "SSH-only",
        "base project",
        "cockpit extra",
        "sanitized",
        "LIMIT",
        "partial venv",
    ):
        assert truth.lower() in combined.lower()


def test_bootstrap_never_modifies_sshd_or_reads_secrets() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8").lower()
    assert "sshd_config" not in text
    assert "printenv" not in text
    assert "${api" not in text
    assert "${secret" not in text
    assert "${token" not in text


def test_deployment_has_no_container_or_second_host_mechanism() -> None:
    files = [
        ROOT / "tools/deployment/README.md",
        ROOT / "tools/deployment/runtime_baseline.py",
        ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)
    for forbidden in ("docker compose", "dockerfile", "kubectl", "kubernetes manifest", "second vps"):
        assert forbidden not in combined


# ---------------------------------------------------------------------------
# S10-DEPLOY-EXEC-01 execution-host substrate (repository mechanism only; no
# test here claims a real host restart, reboot or capacity observation happened)
# ---------------------------------------------------------------------------

MACHINE_ID = "0123456789abcdef0123456789abcdef"
OTHER_MACHINE_ID = "fedcba9876543210fedcba9876543210"
BOOT_ID = "8f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"
OTHER_BOOT_ID = "1b2c3d4e-5f60-4718-a9b0-c1d2e3f4a5b6"
PROBE_UNIT = "polymarket-execution-critical-probe.service"


def _write_bytes(path: pathlib.Path, data: bytes) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class _ExecutionHost:
    """Synthetic local fixture: one exact release, installed units and identity sources."""

    def __init__(self, tmp_path: pathlib.Path) -> None:
        repo, head = _repo(tmp_path / "source", {"a.txt": "alpha", "tools/x.py": "print(1)\n"})
        self.releases = tmp_path / "releases"
        baseline.build_release(repo, head, self.releases)
        self.head = head
        self.release = self.releases / head
        self.units = tmp_path / "units"
        self.units.mkdir()
        shutil.copyfile(ROOT / "tools/deployment/systemd" / PROBE_UNIT, self.units / PROBE_UNIT)
        self.machine = _write_bytes(tmp_path / "machine-id", (MACHINE_ID + "\n").encode())
        self.boot = _write_bytes(tmp_path / "boot_id", (BOOT_ID + "\n").encode())
        self.state = tmp_path / "state"
        for name in baseline.PERSISTENT_STATE_DIRS:
            (self.state / name).mkdir(parents=True)

    def bind(self) -> dict[str, object]:
        return baseline.build_execution_host_binding(
            active_release=self.release,
            expected_sha=self.head,
            unit_dir=self.units,
            releases_root=self.releases,
            machine_id_path=self.machine,
        )

    def current(self, binding: object, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "binding": binding,
            "active_release": self.release,
            "expected_sha": self.head,
            "unit_dir": self.units,
            "releases_root": self.releases,
            "state_root": self.state,
            "machine_id_path": self.machine,
            "boot_id_path": self.boot,
        }
        arguments.update(overrides)
        return baseline.evaluate_execution_host_currentness(**arguments)  # type: ignore[arg-type]


def _host_commands(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ntp: str = "yes",
    ufw: str = "Status: active\n2222/tcp ALLOW IN Anywhere\n",
) -> None:
    real_run = _REAL_RUN

    def fake_run(command: list[str], cwd: pathlib.Path | None = None) -> str:
        if command[:2] == ["systemctl", "is-active"]:
            return "active"
        if command[0] == "timedatectl":
            return ntp
        if command[:2] == ["ufw", "status"]:
            return ufw
        return real_run(command, cwd=cwd)

    monkeypatch.setattr(baseline, "_run", fake_run)


_REAL_RUN = baseline._run


def test_host_instance_id_is_domain_separated_and_never_emits_raw_machine_id(tmp_path: pathlib.Path) -> None:
    first = baseline.derive_host_instance_id(MACHINE_ID.encode())
    assert first == baseline.derive_host_instance_id(f"  {MACHINE_ID}\n".encode())
    assert first == "pmhost-v1:" + hashlib.sha256(
        b"polymarket-execution-host-v1\0" + MACHINE_ID.encode()
    ).hexdigest()
    assert first != "pmhost-v1:" + hashlib.sha256(MACHINE_ID.encode()).hexdigest()
    assert baseline.derive_host_instance_id(OTHER_MACHINE_ID.encode()) != first
    assert MACHINE_ID not in first
    host = _ExecutionHost(tmp_path)
    assert MACHINE_ID not in json.dumps(host.bind())
    for malformed in (
        b"",
        b"   \n",
        MACHINE_ID.upper().encode(),
        MACHINE_ID[:-1].encode(),
        (MACHINE_ID[:-1] + "g").encode(),
        b"uninitialized",
        b"0123456789abcdef 0123456789abcdef",
    ):
        with pytest.raises(baseline.BaselineError) as error:
            baseline.derive_host_instance_id(malformed)
        assert str(error.value) == "HOST_IDENTITY_INVALID"
    with pytest.raises(baseline.BaselineError, match="HOST_IDENTITY_INVALID"):
        baseline.derive_host_instance_id(MACHINE_ID)  # type: ignore[arg-type]
    with pytest.raises(baseline.BaselineError, match="HOST_IDENTITY_INVALID"):
        baseline.read_host_instance_id(tmp_path / "missing-machine-id")


def test_boot_instance_id_changes_while_host_id_stays_stable(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boot = baseline.derive_boot_instance_id(BOOT_ID.encode())
    assert boot == baseline.derive_boot_instance_id(f"{BOOT_ID}\n".encode())
    assert boot == "pmboot-v1:" + hashlib.sha256(b"polymarket-execution-boot-v1\0" + BOOT_ID.encode()).hexdigest()
    assert boot.split(":", 1)[1] != hashlib.sha256(b"polymarket-execution-host-v1\0" + BOOT_ID.encode()).hexdigest()
    assert baseline.derive_boot_instance_id(OTHER_BOOT_ID.encode()) != boot
    assert BOOT_ID not in boot
    for malformed in (
        b"",
        BOOT_ID.upper().encode(),
        BOOT_ID.replace("-", "").encode(),
        f"{{{BOOT_ID}}}".encode(),
        BOOT_ID[:-1].encode(),
        b"not-a-uuid",
    ):
        with pytest.raises(baseline.BaselineError) as error:
            baseline.derive_boot_instance_id(malformed)
        assert str(error.value) == "BOOT_IDENTITY_INVALID"
    # Simulated reboot of the same host: only the kernel boot id source changes.
    _host_commands(monkeypatch)
    host = _ExecutionHost(tmp_path)
    binding = host.bind()
    before = host.current(binding)
    host.boot.write_bytes((OTHER_BOOT_ID + "\n").encode())
    after = host.current(binding)
    assert before["host_instance_id"] == after["host_instance_id"] == binding["host_instance_id"]
    assert before["boot_instance_id"] != after["boot_instance_id"]
    encoded = json.dumps([before, after])
    assert BOOT_ID not in encoded and OTHER_BOOT_ID not in encoded and MACHINE_ID not in encoded


def test_execution_host_binding_is_canonical_atomic_and_timestamp_free(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _ExecutionHost(tmp_path)
    monkeypatch.setattr(baseline, "RELEASES_ROOT", host.releases)
    monkeypatch.setattr(baseline, "MACHINE_ID_PATH", host.machine)
    output = tmp_path / "etc" / "EXECUTION_HOST_BINDING.json"
    command = [
        "execution-host-bind", "--active-release", str(host.release), "--expected-sha", host.head,
        "--unit-dir", str(host.units), "--output",
    ]
    assert baseline.main([*command, str(output)]) == 0
    binding = json.loads(output.read_text(encoding="utf-8"))
    assert output.read_bytes() == baseline._canonical_bytes(binding) + b"\n"
    assert set(binding) == {
        "schema_id", "schema_version", "host_instance_id", "bound_release_sha",
        "release_manifest_sha256", "critical_probe_unit_sha256",
    }
    assert binding["schema_id"] == "polymarket-execution-host-binding"
    assert binding["bound_release_sha"] == host.head
    assert not any("time" in key for key in binding)
    assert str(tmp_path) not in output.read_text(encoding="utf-8")
    assert not list(output.parent.glob(".EXECUTION_HOST_BINDING.json.*"))
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o644
    assert binding == host.bind()
    # A tampered release is rejected before any binding is written.
    (host.release / "a.txt").write_text("changed", encoding="utf-8")
    second = tmp_path / "etc" / "SECOND.json"
    assert baseline.main([*command, str(second)]) == 1
    assert not second.exists()


def test_execution_host_currentness_rejects_host_and_release_binding_mismatch(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _ExecutionHost(tmp_path)
    _host_commands(monkeypatch)
    binding = host.bind()
    result = host.current(binding)
    assert result["status"] == "EXECUTION_HOST_CURRENT"
    assert result["active_release_sha"] == result["bound_release_sha"] == host.head
    other_host = {**binding, "host_instance_id": baseline.derive_host_instance_id(OTHER_MACHINE_ID.encode())}
    with pytest.raises(baseline.BaselineError, match="HOST_BINDING_MISMATCH"):
        host.current(other_host)
    with pytest.raises(baseline.BaselineError, match="RELEASE_BINDING_MISMATCH"):
        host.current({**binding, "bound_release_sha": "f" * 40})
    with pytest.raises(baseline.BaselineError, match="RELEASE_MANIFEST_MISMATCH"):
        host.current({**binding, "release_manifest_sha256": "0" * 64})
    for invalid in (
        None,
        {},
        {**binding, "extra": 1},
        {**binding, "schema_id": "other"},
        {**binding, "host_instance_id": MACHINE_ID},
        {**binding, "bound_release_sha": "F" * 40},
    ):
        with pytest.raises(baseline.BaselineError, match="BINDING_INVALID"):
            host.current(invalid)
    # The active path resolves to a different root than releases/<expected sha>.
    elsewhere = tmp_path / "elsewhere"
    shutil.copytree(host.release, elsewhere)
    with pytest.raises(baseline.BaselineError, match="CURRENT_RELEASE_MISMATCH"):
        host.current(binding, active_release=elsewhere)
    current_link = tmp_path / "current"
    try:
        current_link.symlink_to(elsewhere, target_is_directory=True)
    except OSError:
        pass
    else:
        with pytest.raises(baseline.BaselineError, match="CURRENT_RELEASE_MISMATCH"):
            host.current(binding, active_release=current_link)
    # A release root named for another SHA whose manifest records a different repo SHA.
    wrong_sha = "e" * 40
    shutil.copytree(host.release, host.releases / wrong_sha)
    with pytest.raises(baseline.BaselineError, match="ACTIVE_RELEASE_MISMATCH"):
        host.current(
            {**binding, "bound_release_sha": wrong_sha},
            active_release=host.releases / wrong_sha,
            expected_sha=wrong_sha,
        )
    (host.release / "a.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="RELEASE_FILE_TAMPERED"):
        host.current(binding)


def test_execution_host_currentness_rejects_missing_or_tampered_critical_unit(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _ExecutionHost(tmp_path)
    _host_commands(monkeypatch)
    binding = host.bind()
    assert PROBE_UNIT in baseline._unit_hashes(host.units)
    unit = host.units / PROBE_UNIT
    unit.write_text(unit.read_text(encoding="utf-8") + "Nice=5\n", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="CRITICAL_PROBE_UNIT_MISMATCH"):
        host.current(binding)
    unit.unlink()
    with pytest.raises(baseline.BaselineError, match="CRITICAL_PROBE_UNIT_MISSING"):
        host.current(binding)
    with pytest.raises(baseline.BaselineError, match="CRITICAL_PROBE_UNIT_MISSING"):
        host.bind()
    try:
        unit.symlink_to(ROOT / "tools/deployment/systemd" / PROBE_UNIT)
    except OSError:
        return
    with pytest.raises(baseline.BaselineError, match="CRITICAL_PROBE_UNIT_MISSING"):
        host.current(binding)
    assert PROBE_UNIT not in baseline._unit_hashes(host.units)


def test_execution_host_currentness_strict_requires_ntp_and_ssh_only_firewall(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _ExecutionHost(tmp_path)
    binding = host.bind()
    _host_commands(monkeypatch)
    strict = host.current(binding, strict=True, ssh_port=2222)
    assert strict["verification_mode"] == "strict"
    assert (strict["ntp_state"], strict["firewall_state"], strict["persistent_state"]) == (
        "synchronized", "ssh_only_inbound", "present")
    assert set(strict) == {
        "schema_id", "schema_version", "status", "verification_mode", "host_instance_id", "boot_instance_id",
        "bound_release_sha", "active_release_sha", "release_manifest_sha256", "critical_probe_unit_sha256",
        "critical_probe_state", "telemetry_timer_state", "research_target_state", "ntp_state",
        "firewall_state", "persistent_state",
    }
    encoded = json.dumps(strict)
    for raw in (MACHINE_ID, BOOT_ID, str(tmp_path), "2222"):
        assert raw not in encoded
    with pytest.raises(baseline.BaselineError, match="STRICT_SSH_PORT_REQUIRED"):
        host.current(binding, strict=True)
    _host_commands(monkeypatch, ntp="no")
    assert host.current(binding)["ntp_state"] == "not_synchronized"
    with pytest.raises(baseline.BaselineError, match="HOST_NTP_NOT_SYNCHRONIZED"):
        host.current(binding, strict=True, ssh_port=2222)
    for ufw in (
        "Status: active\n2222/tcp ALLOW IN Anywhere\n80/tcp ALLOW IN Anywhere\n",
        "Status: inactive\n",
        "Status: active\n",
    ):
        _host_commands(monkeypatch, ufw=ufw)
        with pytest.raises(baseline.BaselineError, match="HOST_FIREWALL_NOT_SSH_ONLY"):
            host.current(binding, strict=True, ssh_port=2222)
    _host_commands(monkeypatch)
    shutil.rmtree(host.state / "execution_host")
    with pytest.raises(baseline.BaselineError, match="PERSISTENT_STATE_MISSING"):
        host.current(binding, strict=True, ssh_port=2222)


class _FakeClock:
    def __init__(self, start: int) -> None:
        self.now = start

    def clock(self) -> int:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += round(seconds * 1_000_000_000)


def _run_probe(
    host: _ExecutionHost,
    tmp_path: pathlib.Path,
    *,
    start: int = 5_000_000_000,
    duration: int | None = 60,
    samples: str | None = "samples.jsonl",
    **extra: object,
) -> dict[str, object]:
    clock = _FakeClock(start)
    return baseline.run_critical_probe(
        active_release=host.release,
        heartbeat_output=host.state / "execution_host" / "critical_probe_heartbeat.json",
        samples_output=None if samples is None else tmp_path / samples,
        duration_seconds=duration,
        boot_id_path=host.boot,
        clock=clock.clock,
        sleeper=clock.sleep,
        **extra,  # type: ignore[arg-type]
    )


def test_finite_critical_probe_produces_contiguous_monotonic_sanitized_samples(tmp_path: pathlib.Path) -> None:
    host = _ExecutionHost(tmp_path)
    result = _run_probe(host, tmp_path)
    assert result["status"] == "CRITICAL_PROBE_STOPPED" and result["sample_count"] == 240
    lines = (tmp_path / "samples.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    assert [row["sequence"] for row in rows] == list(range(1, 241))
    assert all(later["monotonic_ns"] > earlier["monotonic_ns"] for earlier, later in zip(rows, rows[1:]))
    assert {row["interval_ms"] for row in rows} == {250.0}
    heartbeat_path = host.state / "execution_host" / "critical_probe_heartbeat.json"
    heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    keys = {"schema_id", "schema_version", "release_sha", "process_instance_id", "sequence", "monotonic_ns", "interval_ms"}
    assert set(heartbeat) == set(rows[0]) == keys
    assert heartbeat["schema_id"] == "polymarket-execution-critical-probe-heartbeat"
    assert rows[0]["schema_id"] == "polymarket-execution-critical-probe-sample"
    assert heartbeat["sequence"] == 240 and heartbeat["release_sha"] == host.head
    remaining = sorted(path.name for path in heartbeat_path.parent.iterdir())
    assert remaining == ["critical_probe_heartbeat.json", "critical_probe_heartbeat.json.lock"]
    assert BOOT_ID not in heartbeat_path.read_text(encoding="utf-8")
    coexistence = baseline.evaluate_execution_host_coexistence(
        rows, rows, _telemetry_rows(), _successful_smoke(), expected_release_sha=host.head
    )
    assert coexistence["evidence_failure"] is None
    for kwargs, code in (
        ({"period_ms": 100}, "PROBE_PERIOD_INVALID"),
        ({"duration": 0}, "PROBE_DURATION_INVALID"),
        ({"duration": 601}, "PROBE_DURATION_INVALID"),
        ({"duration": None}, "PROBE_SAMPLES_REQUIRE_DURATION"),
        ({}, "PROBE_OUTPUT_EXISTS"),
    ):
        with pytest.raises(baseline.BaselineError, match=code):
            _run_probe(host, tmp_path, **kwargs)  # type: ignore[arg-type]


def test_critical_probe_process_instance_id_changes_per_process_start(tmp_path: pathlib.Path) -> None:
    host = _ExecutionHost(tmp_path)
    boot = baseline.derive_boot_instance_id(BOOT_ID.encode())
    other_boot = baseline.derive_boot_instance_id(OTHER_BOOT_ID.encode())
    first = baseline.derive_process_instance_id(boot, 10, host.head)
    assert first == baseline.derive_process_instance_id(boot, 10, host.head)
    assert first != baseline.derive_process_instance_id(boot, 11, host.head)
    assert first != baseline.derive_process_instance_id(other_boot, 10, host.head)
    assert first != baseline.derive_process_instance_id(boot, 10, "f" * 40)
    assert first.startswith("pmproc-v1:") and BOOT_ID not in first
    for bad in ((BOOT_ID, 10, host.head), (boot, -1, host.head), (boot, True, host.head), (boot, 10, "short")):
        with pytest.raises(baseline.BaselineError, match="PROCESS_IDENTITY_INVALID"):
            baseline.derive_process_instance_id(*bad)  # type: ignore[arg-type]
    one = _run_probe(host, tmp_path, start=1_000_000_000, duration=None, samples=None, should_stop=lambda: True)
    two = _run_probe(host, tmp_path, start=2_000_000_000, duration=None, samples=None, should_stop=lambda: True)
    assert one["process_instance_id"] != two["process_instance_id"]
    heartbeat_path = host.state / "execution_host" / "critical_probe_heartbeat.json"
    heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    assert heartbeat["process_instance_id"] == two["process_instance_id"]
    assert "pid" not in heartbeat and "boot_id" not in heartbeat


def test_critical_probe_rejects_duplicate_writer(tmp_path: pathlib.Path) -> None:
    host = _ExecutionHost(tmp_path)
    heartbeat = host.state / "execution_host" / "critical_probe_heartbeat.json"
    holder = baseline._acquire_writer_lock(heartbeat.with_name(heartbeat.name + ".lock"))
    try:
        with pytest.raises(baseline.BaselineError, match="PROBE_WRITER_ACTIVE"):
            _run_probe(host, tmp_path, duration=None, samples=None, should_stop=lambda: True)
        assert not heartbeat.exists()
    finally:
        holder.close()
    # Once the previous writer is gone (lock released by the kernel), a recovered writer proceeds.
    recovered = _run_probe(host, tmp_path, duration=None, samples=None, should_stop=lambda: True)
    assert recovered["sample_count"] == 1


def test_critical_probe_has_no_network_credential_or_trading_surface(tmp_path: pathlib.Path) -> None:
    source = inspect.getsource(baseline.run_critical_probe) + inspect.getsource(baseline._acquire_writer_lock)
    lowered = source.lower()
    for forbidden in (
        "environ", "getenv", "socket", "urlopen", "http", "wallet", "credential", "order", "account",
        "execution_gateway", "subprocess", "_run(",
    ):
        assert forbidden not in lowered, forbidden
    module = ast.parse((ROOT / "tools/deployment/runtime_baseline.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {
        "__future__", "argparse", "hashlib", "json", "math", "os", "pathlib", "platform", "re", "shutil",
        "sqlite3", "subprocess", "sys", "tempfile", "time", "datetime", "fractions", "typing", "fcntl", "msvcrt",
    }
    unit = (ROOT / "tools/deployment/systemd" / PROBE_UNIT).read_text(encoding="utf-8")
    assert "PrivateNetwork=true" in unit and "RestrictAddressFamilies=AF_UNIX" in unit
    for forbidden in (
        "environment", "loadcredential", "setcredential", "secret", "token", "wallet", "order",
        "account", "trading", "http", "network-online", "wants=network",
    ):
        assert forbidden not in unit.lower(), forbidden
    host = _ExecutionHost(tmp_path)
    _run_probe(host, tmp_path, duration=1, samples="one.jsonl")
    written = {path.name for path in (host.state / "execution_host").iterdir()}
    assert written == {"critical_probe_heartbeat.json", "critical_probe_heartbeat.json.lock"}
    assert (tmp_path / "one.jsonl").is_file()


def _unit_lines(name: str) -> list[str]:
    return [line.strip() for line in _unit(name).splitlines() if line.strip()]


def test_critical_probe_unit_runs_in_critical_slice_with_restart_policy() -> None:
    lines = _unit_lines(PROBE_UNIT)
    for directive in (
        "User=polymarket", "Group=polymarket", "Slice=polymarket-critical.slice", "Restart=on-failure",
        "RestartSec=1s", "Type=simple", "NoNewPrivileges=true", "ProtectSystem=strict", "ProtectHome=true",
        "PrivateTmp=true",
    ):
        assert directive in lines, directive
    assert sum(line.startswith("Slice=") for line in lines) == 1
    assert sum(line.startswith("Restart=") for line in lines) == 1
    exec_start = next(line for line in lines if line.startswith("ExecStart="))
    assert exec_start.startswith(
        "ExecStart=/opt/polymarket/current/.venv/bin/python "
        "/opt/polymarket/current/tools/deployment/runtime_baseline.py critical-probe "
    )
    assert "--period-ms 250" in exec_start and "--duration-seconds" not in exec_start
    assert "--heartbeat-output /var/lib/polymarket/execution_host/critical_probe_heartbeat.json" in exec_start
    # The reused critical slice reservation is unchanged.
    assert _unit_lines("polymarket-critical.slice")[-3:] == ["CPUWeight=100", "MemoryLow=2G", "IOWeight=100"]


def test_execution_host_layout_is_reboot_safe() -> None:
    lines = _unit_lines(PROBE_UNIT)
    assert lines[lines.index("[Install]") + 1] == "WantedBy=multi-user.target"
    assert "After=local-fs.target" in lines
    assert "ReadWritePaths=/var/lib/polymarket/execution_host" in lines
    assert any(line.startswith("StartLimitBurst=") for line in lines)
    exec_start = next(line for line in lines if line.startswith("ExecStart="))
    paths = [token for token in exec_start.split("=", 1)[1].split() if token.startswith("/")]
    assert paths and all(
        path == "/opt/polymarket/current"
        or path.startswith(("/opt/polymarket/current/", "/var/lib/polymarket/execution_host/"))
        for path in paths
    )
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    assert '"/etc/systemd/system/$unit"' in text
    assert "mv -Tf /opt/polymarket/.current-new /opt/polymarket/current" in text
    assert "Persistent=true" in _unit("polymarket-host-telemetry.timer")


def test_bootstrap_creates_execution_host_state_directory() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    start = text.index("install -d -o polymarket -g polymarket -m 0750")
    block = text[start : text.index("/var/log/polymarket", start)]
    assert "/var/lib/polymarket/execution_host" in block
    assert baseline.EXECUTION_HOST_STATE.as_posix() == "/var/lib/polymarket/execution_host"
    assert "execution_host" in baseline.PERSISTENT_STATE_DIRS


def test_bootstrap_installs_critical_probe_but_leaves_it_inactive() -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    loop_start = text.index("for unit in")
    install_loop = text[loop_start : text.index("done", loop_start)]
    verify_start = text.index("run_or_fail SYSTEMD_VERIFY_FAILED systemd-analyze verify")
    verify = text[verify_start : text.index("polymarket-research.target", verify_start)]
    assert PROBE_UNIT in install_loop and "-m 0644" in text[loop_start:]
    assert f"/etc/systemd/system/{PROBE_UNIT}" in verify
    enable_line = next(line for line in text.splitlines() if "systemctl enable --now" in line)
    assert PROBE_UNIT not in enable_line
    disable = f"systemctl disable --now {PROBE_UNIT}"
    assert text.index(enable_line) < text.index(disable) < text.index("BOOTSTRAP_COMPLETE")
    assert "CRITICAL_PROBE_UNEXPECTEDLY_ENABLED" in text and "CRITICAL_PROBE_UNEXPECTEDLY_ACTIVE" in text
    for line in text.splitlines():
        if PROBE_UNIT in line and "systemctl" in line:
            assert "disable --now" in line or "is-enabled" in line or "is-active" in line, line
    assert '"research_only":true' in text and '"critical_probe":"installed_inactive"' in text
    assert "execution-host-bind" not in text
    assert "git clone" not in text and "git pull" not in text


def test_backup_covers_execution_host_state_without_secret_regression(tmp_path: pathlib.Path) -> None:
    state = tmp_path / "state"
    (state / "execution_host").mkdir(parents=True)
    (state / "execution_host" / "critical_probe_heartbeat.json").write_text('{"sequence":1}\n', encoding="utf-8")
    with sqlite3.connect(state / "research.sqlite3") as connection:
        connection.execute("CREATE TABLE evidence (value TEXT)")
    backups = tmp_path / "backups"
    backups.mkdir()
    baseline.create_backup(state, backups, "exec-1")
    manifest = json.loads((backups / "exec-1" / baseline.BACKUP_MANIFEST_NAME).read_text(encoding="utf-8"))
    entries = {item["path"]: item for item in manifest["files"]}
    heartbeat = entries["execution_host/critical_probe_heartbeat.json"]
    assert heartbeat["sqlite"] is False and len(heartbeat["sha256"]) == 64
    assert entries["research.sqlite3"]["sqlite"] is True
    restore_root = tmp_path / "restore_drills"
    restore_root.mkdir()
    assert baseline.restore_verify(backups / "exec-1", restore_root, "drill-1")["file_count"] == 2
    (state / "execution_host" / "wallets").mkdir()
    (state / "execution_host" / "wallets" / "value.txt").write_text("placeholder", encoding="utf-8")
    with pytest.raises(baseline.BaselineError, match="BACKUP_SECRET_PATH_REJECTED"):
        baseline.create_backup(state, backups, "exec-2")
    shutil.rmtree(state / "execution_host" / "wallets")
    (state / "data_03").mkdir()
    with pytest.raises(baseline.BaselineError, match="BACKUP_DATA03_PATH_REJECTED"):
        baseline.create_backup(state, backups, "exec-3")


SHA = "a" * 40


def _probe_rows(
    intervals: list[float],
    *,
    release: str = SHA,
    start_sequence: int = 1,
    process: str = "pmproc-v1:" + "b" * 64,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    monotonic = 1_000_000_000
    for index, interval in enumerate(intervals):
        monotonic += int(round(interval * 1_000_000)) if math.isfinite(interval) else 250_000_000
        rows.append(
            {
                "schema_id": "polymarket-execution-critical-probe-sample",
                "schema_version": "1.0.0",
                "release_sha": release,
                "process_instance_id": process,
                "sequence": start_sequence + index,
                "monotonic_ns": monotonic,
                "interval_ms": interval,
            }
        )
    return rows


def _steady(value: float = 250.0, count: int = 240) -> list[dict[str, object]]:
    return _probe_rows([value] * count)


def _telemetry_rows(**overrides: object) -> list[dict[str, object]]:
    base: dict[str, object] = {
        "memory_utilization_percent": 40.0,
        "cpu_utilization_percent": 30.0,
        "disk_utilization_percent": 20.0,
        "io_wait_percent": 1.0,
        "swap_used_kib": 0,
        "swap_in_pages": 5,
        "swap_out_pages": 7,
    }
    return [dict(base), {**base, **overrides}]


_DEFAULT = object()


def _coexist(
    isolated: object = _DEFAULT,
    mixed: object = _DEFAULT,
    telemetry: object = _DEFAULT,
    smoke: object = _DEFAULT,
    **kwargs: object,
) -> dict[str, object]:
    return baseline.evaluate_execution_host_coexistence(
        _steady() if isolated is _DEFAULT else isolated,
        _steady() if mixed is _DEFAULT else mixed,
        _telemetry_rows() if telemetry is _DEFAULT else telemetry,
        _successful_smoke() if smoke is _DEFAULT else smoke,
        **kwargs,  # type: ignore[arg-type]
    )


def test_low_load_synthetic_fixture_maps_to_sufficient_evaluator_semantics_not_host_capacity_evidence() -> None:
    result = _coexist(expected_release_sha=SHA)
    assert result["coexistence_disposition"] == "C8G_EXECUTION_HOST_SUFFICIENT"
    assert result["isolated_p95_interval_ms"] == result["mixed_p95_interval_ms"] == 250.0
    assert result["critical_deadline_miss"] is False and result["critical_degradation_percent"] == 0.0
    assert result["research_smoke_raw_count"] == 2 and result["release_sha"] == SHA
    # Evaluator semantics only: the terminal outcome still needs every real Phase-B proof.
    terminal = baseline.evaluate_execution_host_terminal({"coexistence": result})
    assert terminal["terminal_outcome"] == "EXECUTION_HOST_INCONCLUSIVE"


def _broken_streams() -> list[object]:
    gap = _steady()
    gap[5] = {**gap[5], "sequence": 99}
    regression = _steady()
    regression[3] = {**regression[3], "sequence": 1}
    monotonic = _steady()
    monotonic[10] = {**monotonic[10], "monotonic_ns": monotonic[9]["monotonic_ns"]}
    mixed_release = _steady()
    mixed_release[7] = {**mixed_release[7], "release_sha": "c" * 40}
    two_processes = _steady()
    two_processes[8] = {**two_processes[8], "process_instance_id": "pmproc-v1:" + "d" * 64}
    extra_key = _steady()
    extra_key[0] = {**extra_key[0], "pid": 42}
    missing_key = _steady()
    missing_key[0] = {key: value for key, value in missing_key[0].items() if key != "interval_ms"}

    def replace(index: int, **fields: object) -> list[dict[str, object]]:
        rows = _steady()
        rows[index] = {**rows[index], **fields}
        return rows

    return [
        None, [], "not rows", _steady(count=219), gap, regression, monotonic, mixed_release, two_processes,
        extra_key, missing_key,
        _probe_rows([250.0] * 239 + [float("nan")]),
        _probe_rows([250.0] * 239 + [float("inf")]),
        replace(4, interval_ms=-1.0), replace(4, interval_ms="250"), replace(0, sequence=True),
        replace(0, schema_id="polymarket-execution-critical-probe-heartbeat"),
        _probe_rows([250.0] * 240, start_sequence=0),
    ]


def test_coexistence_rejects_invalid_isolated_probe_evidence() -> None:
    assert _coexist(isolated=_steady(count=220))["coexistence_disposition"] == "C8G_EXECUTION_HOST_SUFFICIENT"
    for broken in _broken_streams():
        result = _coexist(isolated=broken)
        assert result["coexistence_disposition"] == "EXECUTION_HOST_INCONCLUSIVE"
        assert result["evidence_failure"] == "ISOLATED_PROBE_EVIDENCE_INVALID"
        assert result["isolated_p95_interval_ms"] is None


def test_coexistence_requires_valid_mixed_probe_and_telemetry() -> None:
    for broken in _broken_streams():
        result = _coexist(mixed=broken)
        assert (result["coexistence_disposition"], result["evidence_failure"]) == (
            "EXECUTION_HOST_INCONCLUSIVE", "MIXED_PROBE_EVIDENCE_INVALID")
    mismatched = _coexist(mixed=_probe_rows([250.0] * 240, release="c" * 40))
    assert mismatched["evidence_failure"] == "RELEASE_BINDING_MISMATCH"
    assert _coexist(expected_release_sha="c" * 40)["evidence_failure"] == "RELEASE_BINDING_MISMATCH"
    first = _telemetry_rows()[0]
    for telemetry in (
        None, "rows", [], [first],
        [first, {**first, "cpu_utilization_percent": None}],
        [first, {key: value for key, value in first.items() if key != "io_wait_percent"}],
        [first, {**first, "memory_utilization_percent": 100.5}],
        [first, {**first, "disk_utilization_percent": float("nan")}],
        [first, {**first, "swap_used_kib": -1}],
        [first, {**first, "swap_in_pages": True}],
        [first, {**first, "swap_out_pages": 1.5}],
        [first, "row"],
    ):
        result = _coexist(telemetry=telemetry)
        assert (result["coexistence_disposition"], result["evidence_failure"]) == (
            "EXECUTION_HOST_INCONCLUSIVE", "MIXED_TELEMETRY_INCOMPLETE"), telemetry


def test_coexistence_requires_actual_research_smoke_counts() -> None:
    passed = _coexist()
    assert (
        passed["research_smoke_raw_count"],
        passed["research_smoke_normalized_count"],
        passed["research_smoke_store_bytes"],
    ) == (2, 2, 128)
    requested_limits_only = {
        "status": "STOPPED", "stop_reason": "DURATION_EXPIRED", "error_codes": [],
        "max_pages": 1, "duration_seconds": 60,
    }
    failures: list[object] = [
        None, "not a receipt", {}, requested_limits_only,
        {**_successful_smoke(), "status": "FAILED"},
        {**_successful_smoke(), "stop_reason": "NETWORK_CALL_LIMIT"},
        {**_successful_smoke(), "error_codes": ["SOURCE_UNAVAILABLE"]},
    ]
    for field in ("raw_count", "normalized_count", "store_bytes"):
        for value in (0, None, "1", 1.5, True):
            failures.append({**_successful_smoke(), field: value})
    for smoke in failures:
        result = _coexist(smoke=smoke)
        assert (result["coexistence_disposition"], result["evidence_failure"]) == (
            "EXECUTION_HOST_INCONCLUSIVE", "RESEARCH_SMOKE_NOT_PASSED"), smoke
        assert result["research_smoke_raw_count"] is None


def test_coexistence_degradation_boundary_is_strictly_more_than_twenty_percent() -> None:
    exact = _coexist(mixed=_steady(300.0, 200))
    assert exact["mixed_p95_interval_ms"] == 300.0 and exact["critical_degradation_percent"] == 20.0
    assert exact["coexistence_disposition"] == "C8G_EXECUTION_HOST_SUFFICIENT"
    over = _coexist(mixed=_steady(300.001, 200))
    assert over["coexistence_disposition"] == "UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION"
    # Non-binary-exact decimal boundary: 120.12 == 100.1 * 1.20 exactly, so it is not degradation,
    # even though the binary float approximations of these decimals compare greater-than.
    decimal_isolated = _steady(100.1, 600)
    assert _coexist(isolated=decimal_isolated, mixed=_steady(120.12, 500))["coexistence_disposition"] == (
        "C8G_EXECUTION_HOST_SUFFICIENT")
    assert _coexist(isolated=decimal_isolated, mixed=_steady(120.121, 500))["coexistence_disposition"] == (
        "UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION")
    # Nearest-rank p95 uses the ceil(0.95 * n)-th smallest sample.
    assert baseline.nearest_rank_p95([float(value) for value in range(1, 21)]) == 19.0
    assert baseline.nearest_rank_p95([5.0]) == 5.0
    assert baseline.nearest_rank_p95([float(value) for value in range(100, 0, -1)]) == 95.0
    with pytest.raises(baseline.BaselineError, match="P95_REQUIRES_SAMPLES"):
        baseline.nearest_rank_p95([])


def test_coexistence_deadline_boundary_is_strictly_more_than_500_ms() -> None:
    boundary = _probe_rows([250.0] * 239 + [500.0])
    assert _coexist(mixed=boundary)["coexistence_disposition"] == "C8G_EXECUTION_HOST_SUFFICIENT"
    assert _coexist(isolated=boundary)["critical_deadline_miss"] is False
    for stream in ("isolated", "mixed"):
        result = _coexist(**{stream: _probe_rows([250.0] * 239 + [500.001])})
        assert result["coexistence_disposition"] == "UPGRADE_ELIGIBLE:CRITICAL_DEADLINE"
        assert result["critical_deadline_miss"] is True


def test_coexistence_resource_triggers_have_closed_precedence() -> None:
    cases = [
        ({"memory_utilization_percent": 84.999}, "C8G_EXECUTION_HOST_SUFFICIENT"),
        ({"memory_utilization_percent": 85.0}, "UPGRADE_ELIGIBLE:MEMORY"),
        ({"swap_used_kib": 1}, "UPGRADE_ELIGIBLE:MEMORY"),
        ({"swap_in_pages": 6}, "UPGRADE_ELIGIBLE:MEMORY"),
        ({"swap_out_pages": 8}, "UPGRADE_ELIGIBLE:MEMORY"),
        ({"cpu_utilization_percent": 84.999}, "C8G_EXECUTION_HOST_SUFFICIENT"),
        ({"cpu_utilization_percent": 85.0}, "UPGRADE_ELIGIBLE:CPU"),
        ({"disk_utilization_percent": 79.999}, "C8G_EXECUTION_HOST_SUFFICIENT"),
        ({"disk_utilization_percent": 80.0}, "UPGRADE_ELIGIBLE:DISK"),
        ({"io_wait_percent": 9.999}, "C8G_EXECUTION_HOST_SUFFICIENT"),
        ({"io_wait_percent": 10.0}, "UPGRADE_ELIGIBLE:IO"),
        ({"cpu_utilization_percent": 90.0, "memory_utilization_percent": 90.0}, "UPGRADE_ELIGIBLE:MEMORY"),
        ({"cpu_utilization_percent": 90.0, "disk_utilization_percent": 90.0}, "UPGRADE_ELIGIBLE:CPU"),
        ({"disk_utilization_percent": 90.0, "io_wait_percent": 50.0}, "UPGRADE_ELIGIBLE:DISK"),
    ]
    for overrides, expected in cases:
        result = _coexist(telemetry=_telemetry_rows(**overrides))
        assert result["coexistence_disposition"] == expected, overrides
        assert result["coexistence_disposition"] in baseline.COEXISTENCE_DISPOSITIONS
    everything = _telemetry_rows(
        memory_utilization_percent=99.0, cpu_utilization_percent=99.0,
        disk_utilization_percent=99.0, io_wait_percent=99.0,
    )
    degraded = _steady(400.0, 200)
    assert _coexist(mixed=degraded, telemetry=everything)["coexistence_disposition"] == (
        "UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION")
    deadline = _probe_rows([400.0] * 199 + [600.0])
    assert _coexist(mixed=deadline, telemetry=everything)["coexistence_disposition"] == (
        "UPGRADE_ELIGIBLE:CRITICAL_DEADLINE")
    # Invalid evidence outranks every upgrade label.
    assert _coexist(mixed=degraded, telemetry=everything, smoke={})["coexistence_disposition"] == (
        "EXECUTION_HOST_INCONCLUSIVE")
    assert baseline.COEXISTENCE_DISPOSITIONS == {
        "C8G_EXECUTION_HOST_SUFFICIENT", "UPGRADE_ELIGIBLE:CRITICAL_DEADLINE",
        "UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION", "UPGRADE_ELIGIBLE:MEMORY", "UPGRADE_ELIGIBLE:CPU",
        "UPGRADE_ELIGIBLE:DISK", "UPGRADE_ELIGIBLE:IO", "EXECUTION_HOST_INCONCLUSIVE",
    }


def test_coexistence_cli_reads_bounded_evidence_and_never_defaults_green(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {
        "iso.jsonl": "\n".join(json.dumps(row) for row in _steady()),
        "mixed.jsonl": "\n".join(json.dumps(row) for row in _steady()),
        "telemetry.jsonl": "\n".join(json.dumps(row) for row in _telemetry_rows()),
        "smoke.json": json.dumps(_successful_smoke()),
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    arguments = [
        "execution-host-coexistence-evaluate",
        "--isolated-probe-jsonl", str(tmp_path / "iso.jsonl"),
        "--mixed-probe-jsonl", str(tmp_path / "mixed.jsonl"),
        "--mixed-telemetry-jsonl", str(tmp_path / "telemetry.jsonl"),
        "--research-smoke-result", str(tmp_path / "smoke.json"),
    ]
    assert baseline.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["coexistence_disposition"] == "C8G_EXECUTION_HOST_SUFFICIENT"
    (tmp_path / "mixed.jsonl").write_text('{"truncated": ', encoding="utf-8")
    assert baseline.main(arguments) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["coexistence_disposition"] == "EXECUTION_HOST_INCONCLUSIVE"
    assert "truncated" not in output
    (tmp_path / "smoke.json").unlink()
    assert baseline.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["coexistence_disposition"] == "EXECUTION_HOST_INCONCLUSIVE"


def _currentness(boot: str, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": "polymarket-execution-host-currentness",
        "schema_version": "1.0.0",
        "status": "EXECUTION_HOST_CURRENT",
        "verification_mode": "strict",
        "host_instance_id": baseline.derive_host_instance_id(MACHINE_ID.encode()),
        "boot_instance_id": baseline.derive_boot_instance_id(boot.encode()),
        "bound_release_sha": SHA,
        "active_release_sha": SHA,
        "release_manifest_sha256": "1" * 64,
        "critical_probe_unit_sha256": "2" * 64,
        "critical_probe_state": "active",
        "telemetry_timer_state": "active",
        "research_target_state": "active",
        "ntp_state": "synchronized",
        "firewall_state": "ssh_only_inbound",
        "persistent_state": "present",
    }
    value.update(overrides)
    return value


def _heartbeat(process: str, sequence: int) -> dict[str, object]:
    return {
        "schema_id": "polymarket-execution-critical-probe-heartbeat",
        "schema_version": "1.0.0",
        "release_sha": SHA,
        "process_instance_id": process,
        "sequence": sequence,
        "monotonic_ns": 10 + sequence,
        "interval_ms": 250.0,
    }


def _phase_b_evidence(**overrides: object) -> dict[str, object]:
    evidence: dict[str, object] = {
        "schema_id": "polymarket-execution-host-phase-b-evidence",
        "schema_version": "1.0.0",
        "merge_sha": SHA,
        "currentness_pre_reboot": _currentness(BOOT_ID),
        "currentness_post_reboot": _currentness(OTHER_BOOT_ID),
        "process_restart": {
            "pre_heartbeat": _heartbeat("pmproc-v1:" + "3" * 64, 40),
            "post_heartbeat": _heartbeat("pmproc-v1:" + "4" * 64, 8),
            "service_state_after": "active",
            "active_writer_count": 1,
            "observed_slice": "polymarket-critical.slice",
        },
        "backup": {
            "status": "BACKUP_COMPLETE", "backup_id": "phase-b-1", "file_count": 3,
            "backup_manifest_sha256": "5" * 64,
        },
        "restore": {
            "status": "RESTORE_VERIFIED", "drill_id": "drill-pre", "file_count": 3,
            "source_backup_id": "phase-b-1",
        },
        "post_reboot_restore": {
            "status": "RESTORE_VERIFIED", "drill_id": "drill-post", "file_count": 3,
            "source_backup_id": "phase-b-1",
        },
        "coexistence": _coexist(expected_release_sha=SHA),
        "authority": {"trading_credentials_used": False, "orders": 0, "capital_usd": 0, "live": "DISABLED"},
    }
    evidence.update(overrides)
    return evidence


def test_terminal_host_outcome_requires_every_real_phase_b_proof() -> None:
    proven = baseline.evaluate_execution_host_terminal(_phase_b_evidence())
    assert proven["terminal_outcome"] == "EXECUTION_HOST_PROVEN_C8G"
    assert set(proven["proofs"].values()) == {"PASS"}
    assert proven["live_readiness"] == "NOT_IMPLIED" and proven["required_successor"] == "S10-LIVE-ORCH-01"
    upgrade = baseline.evaluate_execution_host_terminal(
        _phase_b_evidence(coexistence=_coexist(telemetry=_telemetry_rows(cpu_utilization_percent=95.0)))
    )
    assert upgrade["terminal_outcome"] == "EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:CPU"
    base = _phase_b_evidence()
    for key in base:
        missing = {name: value for name, value in base.items() if name != key}
        result = baseline.evaluate_execution_host_terminal(missing)
        assert result["terminal_outcome"] == "EXECUTION_HOST_INCONCLUSIVE", key
    restart = dict(base["process_restart"])  # type: ignore[arg-type]
    other_host = baseline.derive_host_instance_id(OTHER_MACHINE_ID.encode())
    failing: dict[str, dict[str, object]] = {
        "reboot_recovery": {"currentness_post_reboot": _currentness(BOOT_ID)},
        "host_binding": {"currentness_post_reboot": _currentness(OTHER_BOOT_ID, host_instance_id=other_host)},
        "currentness": {"currentness_pre_reboot": _currentness(BOOT_ID, verification_mode="observe")},
        "host_controls": {"process_restart": {**restart, "observed_slice": "polymarket-research.slice"}},
        "process_restart": {"process_restart": {**restart, "active_writer_count": 2}},
        "backup_restore": {"restore": {
            "status": "RESTORE_VERIFIED", "drill_id": "drill-pre", "file_count": 2, "source_backup_id": "phase-b-1"}},
        "persistent_state": {"post_reboot_restore": {
            "status": "RESTORE_VERIFIED", "drill_id": "drill-pre", "file_count": 3, "source_backup_id": "phase-b-1"}},
        "coexistence": {"coexistence": _coexist(smoke={})},
        "authority": {"authority": {
            "trading_credentials_used": False, "orders": 1, "capital_usd": 0, "live": "DISABLED"}},
    }
    for proof, override in failing.items():
        result = baseline.evaluate_execution_host_terminal(_phase_b_evidence(**override))
        assert result["terminal_outcome"] == "EXECUTION_HOST_INCONCLUSIVE", proof
        assert result["proofs"][proof] == "FAIL", (proof, result["proofs"])
    same_process = {**restart, "post_heartbeat": restart["pre_heartbeat"]}
    result = baseline.evaluate_execution_host_terminal(_phase_b_evidence(process_restart=same_process))
    assert result["proofs"]["process_restart"] == "FAIL"
    for authority in (
        {"trading_credentials_used": 0, "orders": False, "capital_usd": 0, "live": "DISABLED"},
        {"trading_credentials_used": False, "orders": 0, "capital_usd": 0, "live": "ENABLED"},
    ):
        result = baseline.evaluate_execution_host_terminal(_phase_b_evidence(authority=authority))
        assert result["proofs"]["authority"] == "FAIL"
    wrong_release = _phase_b_evidence(
        currentness_post_reboot=_currentness(OTHER_BOOT_ID, active_release_sha="f" * 40)
    )
    assert baseline.evaluate_execution_host_terminal(wrong_release)["terminal_outcome"] == (
        "EXECUTION_HOST_INCONCLUSIVE")
    for document in (None, [], "text", {**base, "merge_sha": "short"}, {**base, "schema_id": "other"}):
        result = baseline.evaluate_execution_host_terminal(document)
        assert result["terminal_outcome"] == "EXECUTION_HOST_INCONCLUSIVE"
    assert baseline.TERMINAL_OUTCOMES == {"EXECUTION_HOST_PROVEN_C8G", "EXECUTION_HOST_INCONCLUSIVE"} | {
        f"EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:{reason}"
        for reason in ("CRITICAL_DEADLINE", "CRITICAL_DEGRADATION", "MEMORY", "CPU", "DISK", "IO")
    }


def test_execution_host_authority_regression_no_credentials_orders_or_live() -> None:
    spec = json.loads((ROOT / "docs/wp_specs/S10-DEPLOY-EXEC-01/wp_spec.json").read_text(encoding="utf-8"))
    for key in (
        "credentials", "execution", "live", "source_runtime", "paper", "strategy", "dependencies",
        "workflow_files", "hermes_runtime",
    ):
        assert spec["authority"][key] is False, key
    for key in ("network", "scheduler", "local_offline_tooling"):
        assert spec["authority"][key] is True, key
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 18
    assert not any(path.startswith(("src/", ".github/", "tools/wp/")) for path in scope["required_changed_files"])
    assert spec["identity"]["risk_level"] == 3 and spec["identity"]["capital_at_risk_usd"] == 0
    assert spec["successor_boundary"]["next_wp"] == "S10-LIVE-ORCH-01"
    live = (ROOT / "docs/live_trading_authorization.md").read_text(encoding="utf-8")
    assert live.splitlines()[2] == "LIVE TRADING STATUS: DISABLED"
    source = (ROOT / "tools/deployment/runtime_baseline.py").read_text(encoding="utf-8")
    for forbidden in (
        "GateCLivePermit", "GateCSession", "A3_RESTRICTED_LIVE", "execution_gateway", "py_clob_client",
        "polymarket_client", "mnemonic", "os.environ", "getenv",
    ):
        assert forbidden not in source, forbidden


_STAGING_HARNESS = r"""
set -Eeuo pipefail
source "$1"
root=$2
current_link="$root/current"
target="$root/releases/target"
old="$root/releases/old"
mkdir -p "$target/.venv/bin" "$old/.venv/bin"
for release in "$target" "$old"; do
  printf '#!/bin/sh\n' > "$release/.venv/bin/python"
  chmod +x "$release/.venv/bin/python"
done
# 1. First deployment, verification PASS: current resolves for verify, then the staged link is removed.
stage_current_for_verify "$target"
[[ -x "$current_link/.venv/bin/python" ]] || exit 11
[[ "$(readlink "$current_link")" == "$target" ]] || exit 12
cleanup_staged_current
[[ ! -e "$current_link" && ! -L "$current_link" ]] || exit 13
# 2. First deployment, verification FAIL: fail() removes the staged link before exiting.
set +e
( stage_current_for_verify "$target"; [[ -x "$current_link/.venv/bin/python" ]] || exit 21
  fail SYSTEMD_VERIFY_FAILED ) > "$root/fail.out"
status=$?
set -e
[[ $status -eq 1 ]] || exit 22
grep -q '"error_code":"SYSTEMD_VERIFY_FAILED"' "$root/fail.out" || exit 23
[[ ! -e "$current_link" && ! -L "$current_link" ]] || exit 24
# 3. Existing current release: never replaced for verification, kept on PASS and FAIL.
ln -s "$old" "$current_link"
stage_current_for_verify "$target"
[[ "$(readlink "$current_link")" == "$old" ]] || exit 31
set +e
( stage_current_for_verify "$target"; fail SYSTEMD_VERIFY_FAILED ) > /dev/null
set -e
[[ "$(readlink "$current_link")" == "$old" ]] || exit 32
cleanup_staged_current
[[ "$(readlink "$current_link")" == "$old" ]] || exit 33
echo STAGING_HARNESS_OK
"""


def test_bootstrap_first_deploy_verify_stages_and_always_cleans_current(tmp_path: pathlib.Path) -> None:
    text = (ROOT / "tools/deployment/bootstrap_ubuntu_24_04.sh").read_text(encoding="utf-8")
    stage = 'stage_current_for_verify "$target_release"'
    verify = "run_or_fail SYSTEMD_VERIFY_FAILED systemd-analyze verify"
    cleanup = "/etc/systemd/system/polymarket-research.target\ncleanup_staged_current\n"
    activate = "mv -Tf /opt/polymarket/.current-new /opt/polymarket/current"
    # Ordering: stage -> verify -> cleanup -> firewall apply -> governed atomic switch -> enable.
    assert text.index(stage) < text.index(verify) < text.index(cleanup) < text.index('ufw allow "${ssh_port}/tcp"')
    assert text.index(cleanup) < text.index(activate) < text.index("systemctl enable --now")
    assert text.count(stage) == 1 and text.index(stage) > text.index("for unit in")
    assert "trap cleanup_staged_current EXIT" in text
    block = text[text.index("# BEGIN_FIRST_DEPLOY_VERIFY_STAGING") : text.index("# END_FIRST_DEPLOY_VERIFY_STAGING")]
    assert "current_link=/opt/polymarket/current" in block
    assert block.index("cleanup_staged_current\n  printf") > block.index("fail() {")
    # Probe default-inactive semantics are unchanged.
    assert f"systemctl disable --now {PROBE_UNIT}" in text and '"critical_probe":"installed_inactive"' in text
    # The bootstrap targets Ubuntu 24.04 only; MSYS bash on Windows rewrites symlink path forms, so
    # the real-symlink execution proof runs on POSIX hosts (the Linux CI jobs) and never on Windows.
    if os.name == "nt":
        pytest.skip("the first-deploy staging execution proof runs only on POSIX hosts")
    bash = shutil.which("bash")
    assert bash is not None, "bash is required on POSIX hosts for the staging execution proof"
    (tmp_path / "staging.sh").write_text(block, encoding="utf-8", newline="\n")
    (tmp_path / "harness.sh").write_text(_STAGING_HARNESS, encoding="utf-8", newline="\n")
    result = subprocess.run(
        [bash, str(tmp_path / "harness.sh"), str(tmp_path / "staging.sh"), str(tmp_path / "root")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert result.stdout.strip() == "STAGING_HARNESS_OK"
