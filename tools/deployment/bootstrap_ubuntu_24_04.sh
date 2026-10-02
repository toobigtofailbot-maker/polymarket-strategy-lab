#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 027

fail() {
  printf '{"status":"FAILED","error_code":"%s"}\n' "$1"
  exit 1
}

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

# shellcheck disable=SC1091
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 ]] || fail UBUNTU_24_04_REQUIRED
[[ $(uname -m) == x86_64 ]] || fail X86_64_REQUIRED
(( $(nproc) >= 4 )) || fail CPU_FLOOR_NOT_MET
mem_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
((mem_kib >= 7864320)) || fail MEMORY_FLOOR_NOT_MET
opt_disk_kib=$(df -Pk /opt | awk 'NR==2 {print $2}')
state_disk_kib=$(df -Pk /var | awk 'NR==2 {print $2}')
((opt_disk_kib >= 73400320 && state_disk_kib >= 73400320)) || fail DISK_FLOOR_NOT_MET

for command_name in python3 systemctl systemd-analyze timedatectl ufw realpath; do
  command -v "$command_name" >/dev/null || fail REQUIRED_COMMAND_UNAVAILABLE
done
[[ $(timedatectl show --property=NTPSynchronized --value) == yes ]] || fail NTP_NOT_SYNCHRONIZED

python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-release \
  --release-dir "$release_dir" \
  --expected-sha "$expected_sha" >/tmp/polymarket-release-verify.json \
  || fail RELEASE_VERIFY_FAILED

# Validate every firewall operation before changing firewall state. The explicit
# SSH allow is then installed before deny-by-default is enabled.
ufw --dry-run allow "${ssh_port}/tcp" >/dev/null || fail FIREWALL_VALIDATION_FAILED
ufw --dry-run default deny incoming >/dev/null || fail FIREWALL_VALIDATION_FAILED
ufw --dry-run default allow outgoing >/dev/null || fail FIREWALL_VALIDATION_FAILED

getent group polymarket >/dev/null || groupadd --system polymarket
id -u polymarket >/dev/null 2>&1 || useradd \
  --system --gid polymarket --home-dir /var/lib/polymarket \
  --shell /usr/sbin/nologin polymarket

install -d -o root -g root -m 0755 /opt/polymarket /opt/polymarket/releases
install -d -o polymarket -g polymarket -m 0750 \
  /var/lib/polymarket \
  /var/lib/polymarket/local_data \
  /var/lib/polymarket/telemetry \
  /var/lib/polymarket/backups \
  /var/lib/polymarket/restore_drills \
  /var/log/polymarket
install -d -o root -g root -m 0755 /etc/polymarket /etc/polymarket/deployment

target_release="/opt/polymarket/releases/$expected_sha"
if [[ ! -e $target_release ]]; then
  cp -a --no-preserve=ownership "$release_dir" "$target_release"
  python3 "$target_release/tools/deployment/runtime_baseline.py" verify-release \
    --release-dir "$target_release" --expected-sha "$expected_sha" >/dev/null \
    || fail RELEASE_TARGET_INVALID
else
  python3 "$release_dir/tools/deployment/runtime_baseline.py" verify-release \
    --release-dir "$target_release" --expected-sha "$expected_sha" \
    --allow-activation-artifacts >/dev/null || fail RELEASE_TARGET_INVALID
fi
[[ -f $target_release/DEPLOYMENT_MANIFEST.json ]] || fail RELEASE_TARGET_INVALID
chown -R root:root "$target_release"
chmod -R go-w "$target_release"
ln -sfn /var/lib/polymarket/local_data "$target_release/local_data"

if [[ ! -x $target_release/.venv/bin/python ]]; then
  python3 -m venv "$target_release/.venv"
fi
"$target_release/.venv/bin/python" -m pip install \
  --disable-pip-version-check "$target_release[cockpit]"
"$target_release/.venv/bin/python" -m pip check
chmod -R a-w "$target_release"

for unit in \
  polymarket-research.slice \
  polymarket-critical.slice \
  polymarket-host-telemetry.service \
  polymarket-host-telemetry.timer \
  polymarket-research.target; do
  install -o root -g root -m 0644 \
    "$target_release/tools/deployment/systemd/$unit" \
    "/etc/systemd/system/$unit"
done

systemd-analyze verify \
  /etc/systemd/system/polymarket-research.slice \
  /etc/systemd/system/polymarket-critical.slice \
  /etc/systemd/system/polymarket-host-telemetry.service \
  /etc/systemd/system/polymarket-host-telemetry.timer \
  /etc/systemd/system/polymarket-research.target

ufw allow "${ssh_port}/tcp"
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
ufw status | grep -Fq "${ssh_port}/tcp" || fail FIREWALL_VALIDATION_FAILED

ln -sfn "$target_release" /opt/polymarket/.current-new
mv -Tf /opt/polymarket/.current-new /opt/polymarket/current
systemctl daemon-reload
systemctl enable --now polymarket-host-telemetry.timer polymarket-research.target
systemctl is-active --quiet polymarket-host-telemetry.timer || fail TELEMETRY_TIMER_INACTIVE
systemctl is-active --quiet polymarket-research.target || fail RESEARCH_TARGET_INACTIVE

/opt/polymarket/current/.venv/bin/python \
  /opt/polymarket/current/tools/deployment/runtime_baseline.py host-manifest \
  --active-release /opt/polymarket/current \
  --output /etc/polymarket/deployment/HOST_MANIFEST.json \
  >/tmp/polymarket-host-manifest.json

printf '{"status":"BOOTSTRAP_COMPLETE","repo_sha":"%s","research_only":true,"telemetry_timer":"active","firewall":"ssh_only_inbound"}\n' "$expected_sha"
