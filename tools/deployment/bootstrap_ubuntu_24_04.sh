#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 027

fail() {
  printf '{"status":"FAILED","error_code":"%s"}\n' "$1"
  exit 1
}

run_or_fail() {
  local error_code=$1
  shift
  "$@" >/dev/null 2>&1 || fail "$error_code"
}

run_capture_or_fail() {
  local error_code=$1
  local output_path=$2
  shift 2
  "$@" >"$output_path" 2>/dev/null || fail "$error_code"
}

trap 'fail UNEXPECTED_OPERATION_FAILED' ERR

release_dir=""
expected_sha=""
ssh_port=""
while (($#)); do
  case "$1" in
    --release-dir)
      [[ $# -ge 2 ]] || fail ARGUMENT_REQUIRED
      release_dir=$2
      shift 2
      ;;
    --expected-sha)
      [[ $# -ge 2 ]] || fail ARGUMENT_REQUIRED
      expected_sha=$2
      shift 2
      ;;
    --ssh-port)
      [[ $# -ge 2 ]] || fail ARGUMENT_REQUIRED
      ssh_port=$2
      shift 2
      ;;
    *) fail UNKNOWN_ARGUMENT ;;
  esac
done

[[ $EUID -eq 0 ]] || fail ROOT_REQUIRED
[[ -n $release_dir && -d $release_dir ]] || fail RELEASE_DIR_INVALID
[[ $expected_sha =~ ^[0-9a-f]{40}$ ]] || fail EXPECTED_SHA_INVALID
[[ $ssh_port =~ ^[0-9]+$ ]] || fail SSH_PORT_INVALID
((ssh_port >= 1 && ssh_port <= 65535)) || fail SSH_PORT_INVALID

[[ -r /etc/os-release ]] || fail HOST_SETUP_FAILED
# shellcheck disable=SC1091
source /etc/os-release || fail HOST_SETUP_FAILED
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 ]] || fail UBUNTU_24_04_REQUIRED
machine_arch=$(uname -m 2>/dev/null) || fail HOST_SETUP_FAILED
[[ $machine_arch == x86_64 ]] || fail X86_64_REQUIRED
cpu_count=$(nproc 2>/dev/null) || fail HOST_SETUP_FAILED
((cpu_count >= 4)) || fail CPU_FLOOR_NOT_MET
mem_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null) || fail HOST_SETUP_FAILED
((mem_kib >= 7864320)) || fail MEMORY_FLOOR_NOT_MET
opt_disk_kib=$(df -Pk /opt 2>/dev/null | awk 'NR==2 {print $2}') || fail HOST_SETUP_FAILED
state_disk_kib=$(df -Pk /var 2>/dev/null | awk 'NR==2 {print $2}') || fail HOST_SETUP_FAILED
((opt_disk_kib >= 73400320 && state_disk_kib >= 73400320)) || fail DISK_FLOOR_NOT_MET

for command_name in python3 systemctl systemd-analyze timedatectl ufw realpath; do
  command -v "$command_name" >/dev/null || fail REQUIRED_COMMAND_UNAVAILABLE
done
ntp_state=$(timedatectl show --property=NTPSynchronized --value 2>/dev/null) || fail HOST_SETUP_FAILED
[[ $ntp_state == yes ]] || fail NTP_NOT_SYNCHRONIZED

run_capture_or_fail RELEASE_VERIFY_FAILED /tmp/polymarket-release-verify.json \
  python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-release \
  --release-dir "$release_dir" \
  --expected-sha "$expected_sha"

# Validate every firewall operation before changing firewall state. The explicit
# SSH allow is then installed before deny-by-default is enabled.
run_or_fail FIREWALL_APPLY_FAILED ufw --dry-run allow "${ssh_port}/tcp"
run_or_fail FIREWALL_APPLY_FAILED ufw --dry-run default deny incoming
run_or_fail FIREWALL_APPLY_FAILED ufw --dry-run default allow outgoing
run_capture_or_fail FIREWALL_APPLY_FAILED /tmp/polymarket-ufw-added-before.txt ufw show added
run_or_fail FIREWALL_PREEXISTING_RULE_CONFLICT \
  python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-firewall \
  --status-file /tmp/polymarket-ufw-added-before.txt --ssh-port "$ssh_port" --allow-empty

getent group polymarket >/dev/null 2>&1 || run_or_fail HOST_SETUP_FAILED groupadd --system polymarket
if ! id -u polymarket >/dev/null 2>&1; then
  run_or_fail HOST_SETUP_FAILED useradd \
    --system --gid polymarket --home-dir /var/lib/polymarket \
    --shell /usr/sbin/nologin polymarket
fi

run_or_fail HOST_SETUP_FAILED install -d -o root -g root -m 0755 /opt/polymarket /opt/polymarket/releases
run_or_fail HOST_SETUP_FAILED install -d -o polymarket -g polymarket -m 0750 \
  /var/lib/polymarket \
  /var/lib/polymarket/local_data \
  /var/lib/polymarket/telemetry \
  /var/lib/polymarket/backups \
  /var/lib/polymarket/restore_drills \
  /var/log/polymarket
run_or_fail HOST_SETUP_FAILED install -d -o root -g root -m 0755 /etc/polymarket /etc/polymarket/deployment

target_release="/opt/polymarket/releases/$expected_sha"
if [[ ! -e $target_release ]]; then
  run_or_fail HOST_SETUP_FAILED cp -a --no-preserve=ownership "$release_dir" "$target_release"
  run_or_fail RELEASE_VERIFY_FAILED \
    python3 "$target_release/tools/deployment/runtime_baseline.py" verify-release \
    --release-dir "$target_release" --expected-sha "$expected_sha"
else
  run_or_fail RELEASE_VERIFY_FAILED python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-release \
    --release-dir "$target_release" --expected-sha "$expected_sha" \
    --allow-activation-artifacts
fi
[[ -f $target_release/DEPLOYMENT_MANIFEST.json ]] || fail RELEASE_TARGET_INVALID
run_or_fail HOST_SETUP_FAILED chown -R root:root "$target_release"
run_or_fail HOST_SETUP_FAILED chmod -R go-w "$target_release"
if [[ -L $target_release/local_data ]]; then
  local_data_target=$(realpath "$target_release/local_data" 2>/dev/null) || fail HOST_SETUP_FAILED
  [[ $local_data_target == /var/lib/polymarket/local_data ]] || fail RELEASE_TARGET_INVALID
else
  run_or_fail HOST_SETUP_FAILED ln -s /var/lib/polymarket/local_data "$target_release/local_data"
fi

if [[ ! -x $target_release/.venv/bin/python ]]; then
  run_or_fail PYTHON_ENV_SETUP_FAILED python3 -m venv "$target_release/.venv"
  run_or_fail PACKAGE_INSTALL_FAILED "$target_release/.venv/bin/python" -m pip install \
    --disable-pip-version-check "$target_release"
fi
run_or_fail PACKAGE_CHECK_FAILED "$target_release/.venv/bin/python" -m pip check
run_or_fail HOST_SETUP_FAILED chmod -R a-w "$target_release"

for unit in \
  polymarket-research.slice \
  polymarket-critical.slice \
  polymarket-host-telemetry.service \
  polymarket-host-telemetry.timer \
  polymarket-research.target; do
  run_or_fail SYSTEMD_INSTALL_FAILED install -o root -g root -m 0644 \
    "$target_release/tools/deployment/systemd/$unit" \
    "/etc/systemd/system/$unit"
done

run_or_fail SYSTEMD_VERIFY_FAILED systemd-analyze verify \
  /etc/systemd/system/polymarket-research.slice \
  /etc/systemd/system/polymarket-critical.slice \
  /etc/systemd/system/polymarket-host-telemetry.service \
  /etc/systemd/system/polymarket-host-telemetry.timer \
  /etc/systemd/system/polymarket-research.target

run_or_fail FIREWALL_APPLY_FAILED ufw allow "${ssh_port}/tcp"
run_or_fail FIREWALL_APPLY_FAILED ufw default deny incoming
run_or_fail FIREWALL_APPLY_FAILED ufw default allow outgoing
run_or_fail FIREWALL_APPLY_FAILED ufw --force enable
run_capture_or_fail FIREWALL_APPLY_FAILED /tmp/polymarket-ufw-status-after.txt ufw status
run_or_fail FIREWALL_NOT_SSH_ONLY \
  python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-firewall \
  --status-file /tmp/polymarket-ufw-status-after.txt --ssh-port "$ssh_port"

run_or_fail HOST_SETUP_FAILED ln -sfn "$target_release" /opt/polymarket/.current-new
run_or_fail HOST_SETUP_FAILED mv -Tf /opt/polymarket/.current-new /opt/polymarket/current
run_or_fail SERVICE_ACTIVATION_FAILED systemctl daemon-reload
run_or_fail SERVICE_ACTIVATION_FAILED systemctl enable --now polymarket-host-telemetry.timer polymarket-research.target
run_or_fail SERVICE_ACTIVATION_FAILED systemctl is-active --quiet polymarket-host-telemetry.timer
run_or_fail SERVICE_ACTIVATION_FAILED systemctl is-active --quiet polymarket-research.target

run_capture_or_fail HOST_MANIFEST_FAILED /tmp/polymarket-host-manifest.json \
  /opt/polymarket/current/.venv/bin/python \
  /opt/polymarket/current/tools/deployment/runtime_baseline.py host-manifest \
  --active-release /opt/polymarket/current \
  --output /etc/polymarket/deployment/HOST_MANIFEST.json

printf '{"status":"BOOTSTRAP_COMPLETE","repo_sha":"%s","research_only":true,"telemetry_timer":"active","firewall":"ssh_only_inbound"}\n' "$expected_sha"
