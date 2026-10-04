# Execution-Host Runtime Contract

## Status And Authority

S10-DEPLOY-EXEC-01 (Execution-Host Runtime Substrate & Coexistence Proof) extends the merged
S10-DEPLOY-01 research-host baseline (`docs/research_platform_runtime_baseline_contract.md`,
which remains the canonical DEPLOY-01 contract and is not rewritten). It is a RUNTIME, risk 3,
zero-capital package that adds an execution-capable host substrate only, not economic execution
authority.

```text
Phase A (repository mechanism):   this package's implementation PR
Phase B (real AlphaVPS proof):    NOT AUTHORIZED by Phase A; separately authorized by Karl after merge
credentials / account / orders:   NONE
live trading:                     DISABLED
capital / orders:                 USD 0 / 0
required successor:               S10-LIVE-ORCH-01 (separately gated)
```

A merged Phase A proves the mechanism. Only a separately authorized real Phase-B run proves the
actual host. Neither phase issues or consumes a `GateCLivePermit`, arms a `GateCSession`, enters
`A3_RESTRICTED_LIVE`, instantiates an authenticated client, reads private account state, or signs,
creates, posts, amends or cancels an order. Per `docs/ai/codex/PROTECTED_PATHS.md`, this package
does not cross credentials/secrets, authenticated clients, wallet/account behavior, order
placement/cancel, execution gateway, paper engine, dependency/lock changes, external code copying
or generated-artifact boundaries.

## Reused DEPLOY-01 Substrate

The exact clean-HEAD tracked-files-only release, `DEPLOYMENT_MANIFEST.json`, release
verification/tamper rejection, immutable `/opt/polymarket/releases/<sha>`, the atomic
`/opt/polymarket/current` symlink, persistent `/var/lib/polymarket`, the non-login `polymarket`
user, the per-release venv, the Ubuntu 24.04 / x86-64 floor, NTP-before-activation, SSH-only UFW
without sshd mutation, sanitized telemetry, the 60-second telemetry timer, SQLite-aware hashed
backup, isolated restore drills and the public read-only research smoke are reused unchanged. The
research slice (CPUWeight 25, CPUQuota 250%, MemoryHigh 4G, MemoryMax 5G, IOWeight 25) and the
critical slice (CPUWeight 100, MemoryLow 2G, IOWeight 100) are unchanged.

## Host And Boot Identity

```text
host_instance_id = "pmhost-v1:" + sha256(b"polymarket-execution-host-v1\0" + machine_id)
boot_instance_id = "pmboot-v1:" + sha256(b"polymarket-execution-boot-v1\0" + boot_id)
```

`machine_id` is the local `/etc/machine-id` token stripped of surrounding ASCII whitespace and
required to be exactly 32 lowercase hexadecimal characters; anything else fails closed with
`HOST_IDENTITY_INVALID`. `boot_id` is `/proc/sys/kernel/random/boot_id` stripped of surrounding
ASCII whitespace and required to be canonical lowercase UUID text; anything else fails closed with
`BOOT_IDENTITY_INVALID`. Raw machine and boot identifiers are never emitted, persisted or echoed in
diagnostics. Provider account IDs, IP addresses, hostnames, SSH users and operator identity are
never host keys. A real reboot keeps `host_instance_id` and changes `boot_instance_id`.

The existing `polymarket-research-host-manifest` stays sanitized and leaks no host identity; its
fixed unit-hash inventory now includes `polymarket-execution-critical-probe.service`.

## Execution-Host Binding

`runtime_baseline.py execution-host-bind --active-release <path> --expected-sha <40-hex>
--unit-dir <path> --output <path>` requires `--active-release` to resolve exactly to
`/opt/polymarket/releases/<expected-sha>`, fully verifies that release, and atomically writes the
canonical, timestamp-free binding (mode 0644; root-owned when run by the operator; read-only to
the runtime user):

```text
schema_id: polymarket-execution-host-binding
schema_version: 1.0.0
host_instance_id, bound_release_sha, release_manifest_sha256, critical_probe_unit_sha256
```

The recommended Phase-B path is `/etc/polymarket/deployment/EXECUTION_HOST_BINDING.json`. The
binding is durable identity, not an observation. Bootstrap never writes it: it is created only by
the explicit governed Phase-B procedure.

## Currentness Evidence

`runtime_baseline.py execution-host-currentness --binding-file <path> --active-release <path>
--expected-sha <40-hex> --unit-dir <path> [--strict --ssh-port <port>]` performs no mutation and
emits `polymarket-execution-host-currentness` 1.0.0 with `status`, `verification_mode`,
`host_instance_id`, `boot_instance_id`, `bound_release_sha`, `active_release_sha`,
`release_manifest_sha256`, `critical_probe_unit_sha256`, `critical_probe_state`,
`telemetry_timer_state`, `research_target_state`, `ntp_state`, `firewall_state` and
`persistent_state`. It contains no raw path, port, machine id or boot id.

Closed failures, in evaluation order: `STRICT_SSH_PORT_REQUIRED`, `BINDING_INVALID`,
`EXPECTED_SHA_INVALID`, `HOST_IDENTITY_INVALID`, `HOST_BINDING_MISMATCH`,
`RELEASE_BINDING_MISMATCH`, `CURRENT_RELEASE_MISMATCH` (the active path does not resolve to
`/opt/polymarket/releases/<sha>`), `ACTIVE_RELEASE_INVALID`, `ACTIVE_RELEASE_MISMATCH`, the
existing release-verification codes (`RELEASE_FILE_SET_MISMATCH`, `RELEASE_FILE_TAMPERED`, ...),
`RELEASE_MANIFEST_MISMATCH`, `CRITICAL_PROBE_UNIT_MISSING` (missing or symlinked unit),
`CRITICAL_PROBE_UNIT_MISMATCH`, `BOOT_IDENTITY_INVALID`, and in strict mode
`HOST_NTP_NOT_SYNCHRONIZED`, `HOST_FIREWALL_NOT_SSH_ONLY` (effective UFW is not exactly the SSH
TCP port) and `PERSISTENT_STATE_MISSING`.

## Non-Economic Critical Probe

`tools/deployment/systemd/polymarket-execution-critical-probe.service` is a host/runtime
diagnostic, not an execution gateway. It runs `runtime_baseline.py critical-probe` from the
current release venv as `polymarket:polymarket` in `polymarket-critical.slice` with
`Restart=on-failure`, `RestartSec=1s`, a bounded start limit, `PrivateNetwork=true`,
`RestrictAddressFamilies=AF_UNIX`, the telemetry service's hardening, no environment, no
credential and `ReadWritePaths=/var/lib/polymarket/execution_host` only. It has
`WantedBy=multi-user.target` so a separately authorized proof can enable it for the real reboot.

`critical-probe --active-release <path> [--period-ms 250] --heartbeat-output <path>
[--samples-output <path> --duration-seconds <1..600>]`: the period is exactly 250 ms (anything else
is `PROBE_PERIOD_INVALID`); the canonical finite proof uses `--duration-seconds 60`; samples require
a duration (`PROBE_SAMPLES_REQUIRE_DURATION`) and refuse to overwrite (`PROBE_OUTPUT_EXISTS`).
Service mode runs until stopped and atomically replaces one heartbeat file,
`/var/lib/polymarket/execution_host/critical_probe_heartbeat.json`. A kernel-released advisory lock
beside the heartbeat makes a second concurrent writer fail closed (`PROBE_WRITER_ACTIVE`); a
restarted process acquires it once the dead writer is gone.

Heartbeat (`polymarket-execution-critical-probe-heartbeat`) and sample
(`polymarket-execution-critical-probe-sample`) rows carry exactly `schema_id`, `schema_version`,
`release_sha`, `process_instance_id`, `sequence`, `monotonic_ns` and `interval_ms`. No PID or raw
boot id is emitted:

```text
process_instance_id = "pmproc-v1:" + sha256(b"polymarket-execution-probe-process-v1\0"
                      + boot_instance_id + b"\0" + process_start_monotonic_ns + b"\0" + release_sha)
```

The probe imports no execution gateway, strategy, Hermes or Gate-C code, opens no socket, reads no
environment, account or wallet state, simulates no fill or order, and writes only the explicit
execution-host state/evidence destinations.

Activation posture: bootstrap installs (root:root 0644), `systemd-analyze verify`s and hashes the
unit, then runs `systemctl disable --now` on it and fails closed if it is still enabled or active.
Normal steady state: telemetry timer active, research target active, critical probe installed and
inactive. Phase B may start/enable it only for the authorized restart/reboot proof and must stop
and disable it afterwards unless a later package authorizes persistent operation.

## Restart, Reboot And Persistence

Repository tests prove the mechanism; they never claim a real restart or reboot happened. A Phase-B
process-restart proof terminates only the service main process through systemd with a signal
systemd treats as failure (for example `systemctl kill --kill-whom=main --signal=SIGKILL`; SIGTERM
is a clean exit that `Restart=on-failure` does not restart), then requires `active` within a bounded
window, a new `process_instance_id`, a resumed heartbeat sequence, the same binding and release,
the critical slice, and exactly one active writer.

Authoritative/persistent execution-host files: the binding in `/etc/polymarket/deployment` and the
installed unit in `/etc/systemd/system`. Ephemeral operational evidence: the heartbeat, its lock,
and finite-proof sample JSONL under `/var/lib/polymarket/execution_host`. These are non-secret and
are included in the existing DEPLOY-01 hashed backup like other state; they are not economic or
canonical trading state. The existing backup/restore machinery is reused unchanged (SQLite online
backup, per-file hashes, secret/DATA-03/symlink rejection, restore only under
`/var/lib/polymarket/restore_drills`, never promoted to active state).

## Research-Versus-Critical Coexistence

`execution-host-coexistence-evaluate --isolated-probe-jsonl <path> --mixed-probe-jsonl <path>
--mixed-telemetry-jsonl <path> --research-smoke-result <path> [--expected-sha <40-hex>]` is separate
from `evaluate_research_smoke()`; `C8G_RESEARCH_BASELINE_SUFFICIENT` is never reinterpreted as
execution-host proof. Canonical Phase-B windows: one isolated 60-second probe, then one mixed
60-second probe in `polymarket-critical.slice` concurrent with the existing DEPLOY-01 public
research smoke in `polymarket-research.slice`, with host telemetry (at least two samples) covering
the mixed window. No new market client or strategy workload is introduced.

Evidence validity (any failure returns `EXECUTION_HOST_INCONCLUSIVE` with a closed
`evidence_failure` code and never defaults green): each probe stream parses, has the exact sample
keys, one release SHA and one process identity, contiguous sequences starting at 1 or more,
strictly increasing monotonic values, finite non-negative intervals and at least 55 seconds of
coverage; both streams bind the same release SHA (and `--expected-sha` when supplied); telemetry
has finite 0-100 memory/CPU/disk/I/O-wait percentages and non-negative integer swap counters in
every row; the smoke satisfies the DEPLOY-01 truthful success contract (`STOPPED`,
`DURATION_EXPIRED`, empty `error_codes`, positive actual `raw_count`, `normalized_count` and
`store_bytes`; requested limits are never results).

Timing oracle: p95 is nearest-rank, the `ceil(0.95 * n)`-th smallest interval computed with an exact
integer rank. A critical deadline miss is any isolated or mixed interval `> 500.0` ms (exactly 500.0
is not a miss). Critical degradation is `mixed_p95 > isolated_p95 * 1.20`, evaluated by exact
rational comparison, so exactly 20% is not degradation and more than 20% is; this is the bounded
proof form of the hosting direction's >=20% review trigger.

Resource triggers on otherwise valid evidence: memory `>= 85%`, any `swap_used_kib > 0`, or a swap
in/out counter increase during the window; CPU `>= 85%`; disk `>= 80%`; I/O wait `>= 10%`. They are
bounded-proof review triggers, not 15-minute production saturation claims.

Closed dispositions and precedence after validity: `UPGRADE_ELIGIBLE:CRITICAL_DEADLINE`,
`UPGRADE_ELIGIBLE:CRITICAL_DEGRADATION`, `UPGRADE_ELIGIBLE:MEMORY`, `UPGRADE_ELIGIBLE:CPU`,
`UPGRADE_ELIGIBLE:DISK`, `UPGRADE_ELIGIBLE:IO`, else `C8G_EXECUTION_HOST_SUFFICIENT`;
`EXECUTION_HOST_INCONCLUSIVE` outranks all of them. A synthetic low-load unit-test fixture that
maps to `C8G_EXECUTION_HOST_SUFFICIENT` proves evaluator semantics only, never actual host capacity.

No automatic scale action: the evaluator grants no purchase, resize or second-host authority. An
upgrade-eligible or inconclusive Phase-B result is recorded truthfully and returned to Karl, who
decides whether the same single-host architecture is retried on an approved larger tier. A second
host is a separate material architecture decision, never a same-package scaling action.

## Terminal Phase-B Evidence

`execution-host-terminal-evaluate --evidence <path>` evaluates one sanitized
`polymarket-execution-host-phase-b-evidence` 1.0.0 document (merge SHA, strict pre- and
post-reboot currentness, process-restart heartbeats/service state/writer count/observed slice,
backup, pre-reboot restore, post-reboot restore of the same backup, coexistence result, and the
authority attestation `trading_credentials_used: false`, `orders: 0`, `capital_usd: 0`,
`live: DISABLED`). Each proof is PASS, FAIL (present but wrong) or INCONCLUSIVE (missing):
currentness, host binding, process restart, reboot recovery, backup/restore, persistent state,
host controls (firewall/NTP/unit/slice), coexistence and authority.

```text
EXECUTION_HOST_PROVEN_C8G                                  every proof PASS + C8G_EXECUTION_HOST_SUFFICIENT
EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:<reason> every proof PASS + UPGRADE_ELIGIBLE:<reason>
EXECUTION_HOST_INCONCLUSIVE                                anything missing, ambiguous or failing
```

`EXECUTION_HOST_PROVEN_C8G` means only that the host/runtime substrate required by the current
architecture has been proven on the tested C8G instance. It never means account access is valid,
geoblock/account checks passed, balances or allowances are reconciled, an order may be submitted,
live is enabled, or that S10-LIVE-ORCH-01 may be skipped. Every terminal result carries
`live_readiness: NOT_IMPLIED` and `required_successor: S10-LIVE-ORCH-01`.

## Phase-B Sequence (separately authorized; not executed by Phase A)

Only after the Phase-A merge, a refreshed `main`, the recorded merge SHA, explicit Karl Phase-B
authorization and Karl-controlled host access: build and verify the release from a clean checkout
at the merge SHA (never the PR head); transfer it without Git credentials; verify the actual
provider/OS/architecture/resources/systemd/cgroup/NTP/UFW facts and that no unexpected deployment
would be overwritten; run the governed bootstrap; verify release/symlink/manifest/unit
hashes/UFW/NTP/ownership; bind; verify strict currentness; run the process-kill/restart proof; run
the isolated and mixed 60-second windows and evaluate coexistence; run a real backup and isolated
restore; enable the probe only for the reboot proof; capture pre-reboot evidence; perform one real
reboot; verify same host id, changed boot id, same merge release, state, units, UFW, NTP and service
recovery (including a post-reboot restore of the pre-reboot backup); stop and disable the probe;
emit sanitized terminal evidence; return it to Side 16 / Karl. Evidence never contains host IP,
hostname, SSH username or key material, provider account ID, raw machine/boot IDs, environment
dumps, trading credentials or wallet material. A material host-direction mismatch is
`STOP HOST_DIRECTION_DRIFT`; an irreversible provider resize/rebuild needs Karl's explicit
additional decision.

## Successor Boundary

S10-LIVE-ORCH-01 remains the next core package and stays responsible for runtime
consumption/revalidation of the exact exploratory Gate-C permit, account/access checks,
authenticated credential handling under explicit authority, private account truth,
reconciliation, hard runtime admission, bounded order orchestration and any separately authorized
tiny exploratory live transition. DEPLOY-EXEC success is necessary but not sufficient for live
execution. `LIVE TRADING STATUS: DISABLED` remains true; capital/orders USD 0 / 0.
