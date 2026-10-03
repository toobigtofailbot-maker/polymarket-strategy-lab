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
