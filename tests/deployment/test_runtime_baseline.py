from __future__ import annotations

import hashlib
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
