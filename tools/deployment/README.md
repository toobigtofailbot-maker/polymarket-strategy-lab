# Research Platform Runtime Baseline

This directory implements the credential-free, zero-capital S10-DEPLOY-01
research-host baseline for Ubuntu 24.04 x86-64. It does not activate trading,
paper sessions, Hermes, Alpha campaigns, product collectors, DATA-03,
authenticated clients, or live execution.

The operator builds a release from a clean exact commit with
`runtime_baseline.py build-release`, transfers it with human-controlled SSH
tooling, and runs `bootstrap_ubuntu_24_04.sh` as root with explicit
`--release-dir`, `--expected-sha`, and `--ssh-port` arguments. The VPS does not
need Git credentials and does not clone the private repository.

Persistent research state lives under `/var/lib/polymarket`. Releases live at
`/opt/polymarket/releases/<sha>` and become immutable after activation;
`/opt/polymarket/current` changes atomically. The active release's `local_data`
is a symlink to `/var/lib/polymarket/local_data`. The only recurring scheduler
installed by this package is the once-per-minute sanitized host telemetry timer.

Backup and restore verification are explicit operator commands. Restore drills
write only beneath `/var/lib/polymarket/restore_drills` and never overwrite or
promote active state.

The frozen public smoke is a post-merge foreground bounded unauthenticated read
using `tools/polymarket/run_public_market_truth.py`. It must run via finite
`systemd-run --wait --collect --slice=polymarket-research.slice`. Network or
source unavailability produces `BASELINE_INCONCLUSIVE`, never a source or
candidate failure. PASS requires a duration-expired receipt with empty errors and
positive actual raw, normalized, and stored-byte counts; capacity remains
inconclusive unless that smoke passes and required interval telemetry is complete.

Bootstrap creates or reuses the venv, repairs a partial environment when installed
project metadata is missing, requires dependency consistency, and avoids a
redundant install for a complete environment. It installs the base project only
(no cockpit extra), verifies that UFW's effective inbound `ALLOW`/`LIMIT`
permission set is only the supplied SSH TCP port with no routed/FWD permission,
and routes expected operational failures through sanitized closed JSON codes.

## Execution-Host Substrate (S10-DEPLOY-EXEC-01)

S10-DEPLOY-EXEC-01 extends this baseline without replacing it; its contract is
`docs/execution_host_runtime_contract.md`. It adds five closed, credential-free
subcommands to `runtime_baseline.py`:

- `execution-host-bind` verifies the exact active release and atomically writes the
  canonical, timestamp-free `polymarket-execution-host-binding` (pseudonymous
  `pmhost-v1` host id, release SHA, release manifest hash, critical-probe unit hash).
- `execution-host-currentness` re-derives host and boot identity (`pmboot-v1`) and
  fails closed on any host, release, current-symlink, manifest or unit mismatch;
  `--strict --ssh-port` also requires synchronized NTP, exact SSH-only UFW and the
  persistent state layout. It never mutates the host.
- `critical-probe` is the non-economic heartbeat run by
  `polymarket-execution-critical-probe.service` in `polymarket-critical.slice`
  (`Restart=on-failure`, `RestartSec=1s`, no network, no environment, no credentials).
  Its heartbeat and finite 60-second proof samples are ephemeral evidence under
  `/var/lib/polymarket/execution_host`; a second concurrent writer fails closed.
- `execution-host-coexistence-evaluate` returns one closed research-versus-critical
  disposition (`C8G_EXECUTION_HOST_SUFFICIENT`, `UPGRADE_ELIGIBLE:CRITICAL_DEADLINE`,
  `UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION`, `UPGRADE_ELIGIBLE:MEMORY|CPU|DISK|IO` or
  `EXECUTION_HOST_INCONCLUSIVE`); malformed evidence is always inconclusive.
- `execution-host-terminal-evaluate` maps one sanitized real Phase-B evidence document
  to `EXECUTION_HOST_PROVEN_C8G`,
  `EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:<reason>` or
  `EXECUTION_HOST_INCONCLUSIVE`; none of these implies live readiness.

Bootstrap installs, verifies and hashes the probe unit, creates
`/var/lib/polymarket/execution_host` (`polymarket:polymarket`, 0750), and leaves the
probe disabled and inactive. It never writes the execution-host binding; that is an
explicit step of the separately authorized Phase-B host proof. No upgrade, purchase or
extra host is ever automatic, and nothing here grants account, order, capital or live
authority.

## Optional private Control Center (S10-CC-PROD-01)

The production contract is `docs/control_center_production_contract.md`. The only
new substrate is the dormant `systemd/polymarket-control-center.service` template;
the base bootstrap, immutable tracked release verifier, SSH-only firewall, slices,
telemetry, critical probe and backup/recovery are unchanged. Bootstrap neither
installs nor starts this optional service.

Build the locked Node 24.18.0 frontend from the exact verified release source SHA
in a separate build workspace; stage/digest-check assets outside the tracked release
at `/var/lib/polymarket/control_center/assets/<exact-sha>/dist`. Verify the original
release again. Only a separately authorized host operator installs/checks the pinned
cockpit extras in the existing `.venv` and restores root ownership and runtime
non-writability. Supply the three required absolute nonsecret store/dist paths via
root-owned `/etc/polymarket/deployment/control-center.env`; optional stores are not
guessed. Validate systemd and enforce localhost-only network/read-only sandboxing
before any installation or start.

Private Tailscale Serve, narrow grants/ACL, allowed-versus-denied access, GET/API/SSE,
restart/reboot and rollback are Karl-only post-merge operator gates. Never Funnel,
public ingress, command enablement or economic authority. See the production
contract for exact build/config and separately gated activation procedure.
