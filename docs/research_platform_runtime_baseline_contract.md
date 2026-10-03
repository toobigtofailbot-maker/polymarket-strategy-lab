# Research Platform Runtime Baseline Contract

## Status And Authority

S10-DEPLOY-01 implements a reproducible zero-capital research-host baseline. It
authorizes repository implementation only. Provider purchase, provisioning,
remote login, credentials, post-merge activation, product scheduling, paper
sessions, execution, Gate C, live trading, capital, and orders remain unauthorized.

The baseline targets AlphaVPS C8G in Sofia, Bulgaria: Ubuntu 24.04 LTS x86-64,
4 logical CPUs, at least 7.5 GiB visible RAM, and at least 70 GiB target-filesystem
capacity. Before activation, the human operator must recheck that this offering
still materially matches the resource floor and that official Polymarket
restriction documentation still does not list Bulgaria as restricted. Drift is
`STOP HOST_DIRECTION_DRIFT`; no alternate provider, region, or tier is implicit.

## Native Host Model

The only deployment mechanism is Ubuntu, systemd, a per-release Python virtual
environment, an exact repository release, and persistent local state. Docker,
Kubernetes, orchestrators, a second VPS, and new repository dependencies are
outside authority.

```text
/opt/polymarket/releases/<repo-head>/
/opt/polymarket/current -> releases/<repo-head>/
/var/lib/polymarket/local_data/
/var/lib/polymarket/telemetry/
/var/lib/polymarket/backups/
/var/lib/polymarket/restore_drills/
/var/log/polymarket/
/etc/polymarket/deployment/
```

The active release's `local_data` is a symlink to persistent state. Releases are
immutable after activation and `current` changes atomically. The non-login
`polymarket` user owns mutable state. This host contains no DATA-03 workspace or
evidence and requires no repository, provider, Polymarket, wallet, or Git secret.

## Release Integrity

`tools/deployment/runtime_baseline.py build-release` requires a clean source tree
and a requested commit equal to `HEAD`. It copies only tracked regular files into
the ignored `local_data/deployment/<repo-head>/` output, rejects secret-like paths,
private-key markers and symlinks, and writes a deterministic canonical file/hash/
size inventory. The identity contains the exact repository SHA and no absolute
operator path.

`verify-release` recomputes the manifest identity and rejects unknown manifest
shape, wrong SHA, added, missing or tampered files, duplicate/unsafe paths, and
all symlinks.

## Host Manifest And Telemetry

The host manifest records only OS, architecture, kernel, CPU count, total memory,
free/total space for `/opt` and `/var/lib`, Python/systemd versions, NTP state,
active release SHA, unit hashes, timer state, and a closed firewall summary. It
never records IP addresses, hostname, operator username, account identifiers,
environment variables, command lines, or credentials.

The only recurring scheduler is `polymarket-host-telemetry.timer`: first run no
later than 60 seconds after activation, exactly 60-second cadence, persistent.
Telemetry is sanitized JSONL containing UTC time, CPU/load, memory, swap, disk,
I/O wait, research target state, and timer state. CPU utilization and I/O wait
are computed from a bounded delta between two `/proc/stat` snapshots, never from
cumulative-since-boot values. Invalid or non-positive deltas are recorded as
unavailable rather than zero. The active file is limited to 10 MiB and exactly
seven rotations are retained.

## Systemd Isolation

`polymarket-research.slice` freezes `CPUWeight=25`, `CPUQuota=250%`,
`MemoryHigh=4G`, `MemoryMax=5G`, and `IOWeight=25`.

`polymarket-critical.slice` reserves `CPUWeight=100`, `MemoryLow=2G`, and
`IOWeight=100`. No execution unit is activated by this package.

`polymarket-research.target` owns only the host telemetry timer. It starts no
market collector, Hermes run, Alpha campaign, paper session, strategy, execution,
or trading service. The telemetry service is oneshot, runs as `polymarket` in the
research slice, uses fixed absolute paths, and enables the frozen systemd
hardening and explicit telemetry write path.

## Bootstrap And Firewall

The strict idempotent bootstrap requires root and explicit `--release-dir`,
`--expected-sha`, and `--ssh-port`. It fails closed on platform/resource/NTP/
release/tooling validation, creates the frozen user and directories, installs
the base project from existing metadata without the optional cockpit extra, runs
`pip check`, installs and verifies the exact
units, and activates only the timer and research target.

Expected operational failures are wrapped and emit one sanitized terminal JSON
object with a stable closed error code. Raw Python, pip, UFW, systemd, copy, link,
ownership, or host-manifest diagnostics are not the canonical evidence stream.

UFW operations are dry-run validated before firewall mutation. Configured rules
are checked before activation and conflicting inbound allows fail closed without
being deleted. The explicit operator SSH TCP port is allowed before inbound
deny-by-default is enabled; after enablement the effective inbound allow set is
verified as only that exact TCP port (equivalent IPv4/IPv6 forms are accepted).
Outbound remains allowed for bootstrap and separately authorized public research.
No public cockpit/API port or sshd configuration change is permitted.

## Backup And Restore

Backup is an explicit operator action over `/var/lib/polymarket` research state.
It excludes backup/restore roots, DATA-03 and secret-like paths; rejects symlinks;
uses the SQLite online backup API for `*.sqlite3`; and hashes every output in a
canonical manifest. Restore verification creates a new directory only beneath
`/var/lib/polymarket/restore_drills`, verifies the complete file set and hashes,
and runs `PRAGMA integrity_check`. It never overwrites or promotes active state.

## Public Smoke And Capacity

After this implementation merges and a human separately authorizes activation,
exactly one bounded foreground public smoke may run in the research slice:

```bash
python tools/polymarket/run_public_market_truth.py \
  --allow-network \
  --discover-active \
  --duration-seconds 60 \
  --max-pages 1 \
  --output-db local_data/polymarket/deploy_smoke.sqlite3
```

It is unauthenticated, read-only, finite, and not a service. A smoke passes only
when its actual WP169 receipt is `STOPPED` for `DURATION_EXPIRED`, has an empty
`error_codes` list, and reports positive integer raw, normalized, and stored-byte
counts. Every other terminal reason and missing, malformed, or zero actual
evidence maps to `BASELINE_INCONCLUSIVE`, never source/candidate failure. Capacity
is also inconclusive unless the smoke passed and every evaluated sample has
usable numeric CPU, memory, disk, and I/O telemetry. Capacity output is closed to
`C8G_RESEARCH_BASELINE_SUFFICIENT`, `UPGRADE_ELIGIBLE:MEMORY`,
`UPGRADE_ELIGIBLE:CPU`, `UPGRADE_ELIGIBLE:DISK`, `UPGRADE_ELIGIBLE:IO`, or
`BASELINE_INCONCLUSIVE`. It applies only to this research baseline and cannot
prove future execution/live capacity.

## Activation And Successor Boundary

Post-merge activation must separately prove exact merged-main deployment,
resource floor, unit validity, telemetry after reboot, slice controls, bounded
public smoke or truthful inconclusive status, backup, isolated restore, release/
state survival, SSH-only inbound firewall, and absence of credentials. Evidence
is sanitized and untracked.

Research hosting may now precede weather DATA-03 completion and candidate-specific
WP172. A real candidate still requires qualification, WP170, WP172, and a later
execution coexistence/hardening proof before production-hosted serious paper
or live consideration. DATA-03 remains unchanged on its current operator system.
