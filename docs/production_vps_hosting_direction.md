# Production VPS Hosting Direction

This document originated as the focused planning contract recorded by S10-DEPLOY-PLAN-01 and is
reconciled by S10-DEPLOY-01. The provider/tier direction remains planning truth. S10-DEPLOY-01
adds a repository implementation for a research-only zero-capital host baseline; it still does
not purchase, provision, remotely access, or activate a VPS.

## 1. Decision Record

```text
decision status:                    APPROVED_PLANNING_DIRECTION
deployment status:                  NOT_PROVISIONED / NOT_DEPLOYED
provider:                           AlphaVPS
location:                           Sofia, Bulgaria
initial tier:                       C8G
initial resources:                  4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10
OS:                                 Ubuntu 24.04 LTS / x86-64
architecture:                       ONE_CONSOLIDATED_POLYMARKET_VPS
default separate research/live VPS: NO
upgrade path:                       C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence
implementation package:             S10-DEPLOY-01
repository implementation state:    IMPLEMENTED_ON_BRANCH / ACTIVATION_DEFERRED
```

C8G is the initial production-host target. Recording it is not evidence that the host has been
purchased, provisioned, benchmarked or approved for paper or live execution.

Later operator truth (S10-DEPLOY-EXEC-01): the `deployment status` line above is the historical
pre-purchase planning snapshot. Karl has since reported the AlphaVPS host purchased and
provisioned; project deployment on it has not been performed and its technical facts remain
unverified. Section 11 records that current state without rewriting this planning record.

## 2. Superseded Planning Statements

This decision supersedes, as current planning truth:

- the WP61 runtime-direction shorthand "local development first. Cheap VPS later for a controlled
  live pilot" in `docs/architecture_decision_record.md` (kept there as historical context only);
- the `docs/project_charter.md` statement that VPS and cloud choices remain open;
- any roadmap implication that deployment or hosting work should occur before WP173 is
  implemented, or the shorthand "after WP172 and before WP173".

WP61's "avoid serverless for live runtime" constraint is unchanged and is consistent with this
decision.

For compatibility with the original S10-DEPLOY-PLAN-01 planning record, its now-superseded
pre-authorization fields were: `future implementation package: S10-DEPLOY-01` and
`future package state: NOT AUTHORIZED`. They describe the historical planning snapshot, not the
current repository implementation state recorded in Section 1. Its readiness label was
`DRAFT-ELIGIBLE LATER / NOT AUTHORIZED NOW`.

## 3. Consolidated Architecture

The intended Polymarket production architecture is ONE consolidated Polymarket VPS. The same host
is intended eventually to run, each only as separately authorized by its own approved package:

- Hermes;
- Alpha Factory / research components;
- research agents and supporting services;
- data acquisition and processing;
- databases and persistent state;
- orchestration;
- monitoring and logging;
- market-data / runtime services;
- strategy execution;
- hard-risk controls;
- order placement and cancellation;
- reconciliation;
- paper trading;
- eventual restricted live execution.

Separate research and live VPS machines are not the default roadmap architecture. A second VPS is
not a normal scaling step: it requires a future explicit architecture decision supported by
evidence that software/process isolation on one host is insufficient.

## 4. Capacity / Cost Policy

```text
C8G
  -> C12G
  -> C16G / P-series
  -> larger only when measured evidence requires it
```

C8G is the default starting point. C12G, C16G, P16G and larger tiers are upgrade options only. The
project must not overprovision from estimates; upgrade eligibility is driven by production-host
telemetry.

### Upgrade eligibility criteria

These are eligibility triggers for review, not automatic upgrades. A larger tier becomes eligible
for review when one or more of the following is recurrent under representative workloads:

1. Memory: RAM utilization repeatedly exceeds ~85% for >=15 minutes; or `MemAvailable` repeatedly
   falls below ~15%; or active swap-in/swap-out recurs during normal or critical workloads.
2. CPU: aggregate CPU remains above ~85% for >=15 minutes; or runnable workload/load pressure
   repeatedly exceeds practical 4-vCPU capacity during execution-critical windows.
3. Disk capacity: persistent storage exceeds ~80% used; or measured growth gives less than ~30
   days safe headroom.
4. Disk I/O: sustained I/O wait above ~10% for >=10 minutes during representative workload; or
   database/evidence persistence latency materially affects execution-critical processes.
5. Execution-path interference: mixed Hermes/research/Alpha workloads cause >=20% degradation
   versus an isolated execution baseline in frozen p95 market-data or order-path latency; or
   execution-critical heartbeats/deadlines are missed because of resource contention.
6. Recovery: the host cannot meet the deployment package's frozen restart/recovery objective under
   representative load.
7. Resource-isolation failure: execution-critical processes require repeated emergency throttling
   of research jobs simply to remain within their latency/recovery SLOs.

S10-DEPLOY-01 freezes the research-baseline telemetry and closed capacity dispositions in
`docs/research_platform_runtime_baseline_contract.md`. These do not establish future execution
capacity. No tier upgrade is automatic and nothing is auto-purchased. Karl decides after
reviewing telemetry.

## 5. Software Isolation On The Single VPS

Research workloads must not be allowed to starve later execution-critical components.
S10-DEPLOY-01 implements the initial native-systemd isolation baseline:

- `polymarket-research.slice`: CPUWeight 25, CPUQuota 250%, MemoryHigh 4G,
  MemoryMax 5G, IOWeight 25;
- `polymarket-critical.slice`: CPUWeight 100, MemoryLow 2G, IOWeight 100;
- `polymarket-research.target`: baseline telemetry only;
- `polymarket-host-telemetry.timer`: the only recurring scheduler, once per minute.

The mechanism is systemd + Python venv + exact release + persistent `/var/lib` state. Kubernetes
is not required; Docker, Kubernetes, and a second VPS are not introduced. No execution service is
activated here. A later
real-candidate execution coexistence/hardening proof remains required.

## 6. Research Baseline Now / Execution Migration Later

Current repo truth already contains the generic WP172 executable-edge substrate (WP172 — Alpha +
Executable Edge MVP, merged via PR #174) and the WP173 Serious Paper Trading System implementation
(WP173 — Serious Paper Trading System + Paper Cockpit, merged via PR #175). WP173 code is not
reimplemented by this direction. WP173 supplies simulated-paper runtime, accounting, risk and
reconciliation, but explicitly adds no OS scheduler/service, daemon or deployment authority.
Where current status lines say "WP170/WP172/WP173: NOT STARTED", they mean candidate-specific work
for the current qualification chain, not the generic merged substrates.

The old serial migration rule is superseded. A zero-capital research host baseline may now follow
the generic research-paper bridge without waiting for DATA-03 or a real WP172 candidate:

```text
S10-PAPER-RESEARCH-01
-> S10-DEPLOY-01 research-host baseline
-> later separately authorized research services and evidence loops
```

The original planning contract placed the package "after a real strategy-specific WP172
EXECUTABLE_EDGE_PASS exists and before the first serious production-hosted paper runtime using the
existing WP173 system" and recorded this superseded serial sequence:

```text
-> real WP172 executable-edge evidence / EXECUTABLE_EDGE_PASS -> S10-DEPLOY-01 Production VPS Runtime Baseline -> serious production-hosted WP173 paper runtime
```

That quotation is retained as historical compatibility evidence only. It does not override the
current split between the research-host baseline and the later execution migration gate.

Execution/live migration remains separately gated:

```text
candidate qualification
-> candidate-specific WP170
-> real WP172 executable-edge evidence / EXECUTABLE_EDGE_PASS
-> execution coexistence and host-hardening proof
-> serious production-hosted WP173 paper runtime
-> later auth/signing/live gates only if separately authorized
```

This split is required because:

- current research hosting has zero capital and no execution authority;
- WP172 still proves candidate-specific executable-edge eligibility;
- WP173 supplies simulated-paper machinery but no OS scheduler/service authority;
- the current research baseline cannot manufacture execution/live coexistence evidence;
- production-hosted serious paper remains downstream of the later coexistence proof.

## 7. Implemented Repository Package

```text
S10-DEPLOY-01 — Research Platform Runtime Baseline
REPOSITORY IMPLEMENTATION AUTHORIZED / HOST ACTIVATION DEFERRED
```

S10-DEPLOY-01 is a dedicated bounded package under `tools/deployment/`; it is not folded into
WP173 or WP174. Its contract is `docs/research_platform_runtime_baseline_contract.md`. Provider
purchase, provisioning, SSH access and activation remain a separately authorized post-merge human
operator closure.

## 8. Current Research-Host Proof And Deferred Execution Proof

The implementation freezes mechanisms for:

- Host identity / reproducibility: exact AlphaVPS / Sofia / C8G target identity; Ubuntu 24.04 LTS
  / x86-64; machine/resource facts captured; reproducible host bootstrap/configuration; pinned
  runtime/package versions; exact repo commit / deployment manifest; deployed-code hash/commit
  verification.
- Persistence: explicit persistent-state directories; permissions/ownership; SQLite/database
  durability semantics; evidence/log locations; disk-space protections; no accidental
  ephemeral-only authoritative state.
- Process/service supervision: deterministic service/process inventory; dependency/start order;
  deterministic stop/shutdown; bounded restart policy; no duplicate writers where repo contracts
  require a single writer; reboot recovery.
- Recovery proof: clean restart; unclean process restart; full host reboot; journal/database
  integrity; reconciliation on restart; fail-closed state when recovery evidence is inconsistent.
- Clock: UTC system posture; NTP/time-sync active; measurable clock offset; hard failure/warning
  threshold frozen by S10-DEPLOY-01; evidence that time-sensitive market/runtime components use
  the intended clock.
- Secrets: no repo secrets; no secrets in logs/tests/docs; least-readable runtime secret surface;
  host file / environment / approved secret-manager mechanism frozen later; rotation/revocation
  procedure; permissions test.
- Firewall / network: host firewall posture; minimum inbound exposure; operator access path;
  cockpit/API binding rules; outbound network policy compatible with each separately authorized
  runtime; no infrastructure-level Full egress treated as product authority.
- Backup / restore: automated or operator-controlled backup design; integrity metadata;
  retention; off-host or provider-independent restore source as appropriate; successful restore
  drill into a clean target; restored state reconciles before operation.
- Health / monitoring: process health; restart count; uptime; disk; RAM; swap; CPU/load; I/O wait;
  per-process/service resource consumption; database/storage health; market-data latency;
  order-path latency when applicable; application error rates / blocked states.
- Logs / evidence: bounded rotation/retention; authoritative evidence not lost by rotation; no
  secret/raw-sensitive leakage; enough retained history to investigate restarts, latency and
  resource contention.

### Single-host coexistence proof (deferred)

S10-DEPLOY-EXEC-01 implements the repository mechanism for this proof
(`docs/execution_host_runtime_contract.md`); the real host proof stays a separately authorized
Phase B. The original deferred requirements below are retained:

After a real candidate reaches WP172 PASS and before production-hosted serious paper/live, a later
separately authorized proof must show:

- Hermes/research/Alpha workloads active within frozen limits;
- execution-critical services remain responsive;
- resource controls actually constrain the research workload;
- no execution-critical starvation;
- latency/resource metrics remain within the frozen production-host SLO;
- stopping/throttling research does not require a second VPS.

### C8G research sizing only

The current package may produce only a research-baseline disposition:

```text
C8G_RESEARCH_BASELINE_SUFFICIENT
or
UPGRADE_ELIGIBLE:MEMORY|CPU|DISK|IO
or
BASELINE_INCONCLUSIVE
```

The historical planning contract used the generic labels `C8G_SUFFICIENT` and
`UPGRADE_ELIGIBLE:<reason>`; the implementation narrows them to the research-only closed labels
above. It must not auto-upgrade or auto-purchase. It must not infer execution capacity.

## 9. DATA-03 And The Current Qualification Chain

DATA-03 is not moved to the VPS. DATA-03 remains on the current operator environment.

S10-QUAL-DATA-03 (PR #206, merged) already has its merged implementation, uses a manual bounded
operator, has no scheduler, requires historical local DATA-02 evidence for zero-network
`prepare`, and starts real prospective accrual no earlier than `2026-10-15T00:00:00Z`. Moving it
now would add infrastructure migration and local-evidence transfer risk without being required by
the frozen DATA-03 contract. The already-drafted S10-QUAL-DATA-03 POST-MERGE PREPARE CLOSURE
remains substantively unchanged; this package edits no DATA-03 code, contract or WP artifact.

The two lanes now proceed independently until later candidate promotion:

```text
research lane: S10-PAPER-RESEARCH-01 -> S10-DEPLOY-01 research baseline
weather lane: DATA-03 prepare/accrual/seal -> S10-QUAL-REAL-01
promotion lane: candidate-specific WP170 -> WP172 PASS
                -> execution coexistence proof -> serious hosted WP173 paper
                -> later separately authorized auth/signing/live gates
```

## 10. Authority Boundary

S10-DEPLOY-01 authorizes the repository implementation and, after merge, requires a separate human
activation closure. This document does not authorize VPS purchase, provisioning, remote login,
credentials, host activation, product scheduling, paper trading, execution, signing, Gate C,
live trading, capital, or orders. Current live authority remains unchanged
(`docs/live_trading_authorization.md`). Live remains DISABLED; Gate C is NOT AUTHORIZED; capital
at risk USD 0; orders 0.

## 11. Current Operator-Reported Provisioning State (S10-DEPLOY-EXEC-01)

This block is later, superseding current truth for the provisioning state only. The planning
statements above (including `deployment status: NOT_PROVISIONED / NOT_DEPLOYED`) are retained as
the historical pre-purchase record; they were true when written.

```text
VPS purchased: YES (operator-reported by Karl; not observed by the repository)
VPS provisioned: YES (operator-reported by Karl; not observed by the repository)
project deployment/configuration on that VPS: NOT PERFORMED
host activation / bootstrap / binding / reboot proof: NOT PERFORMED
actual host technical facts: UNKNOWN until a separately authorized Phase B verifies them
initial intended tier/direction: AlphaVPS / Sofia / C8G / one consolidated host
```

The repository has not observed this VPS. No provider, OS, architecture, resource, NTP, firewall or
capacity fact about it is claimed until Phase B records sanitized evidence. A material mismatch
between the actual host and this direction is `STOP HOST_DIRECTION_DRIFT`.

## 12. Execution-Host Substrate (S10-DEPLOY-EXEC-01)

S10-DEPLOY-EXEC-01 extends, and does not replace, the S10-DEPLOY-01 native-systemd baseline. Its
contract is `docs/execution_host_runtime_contract.md`. Phase A (repository mechanism) adds:

- a sanitized execution-host binding and currentness contract (pseudonymous `pmhost-v1` host id,
  `pmboot-v1` boot id, exact release SHA, release manifest hash, critical-probe unit hash);
- `polymarket-execution-critical-probe.service`, a non-economic heartbeat diagnostic in the
  existing `polymarket-critical.slice` with deterministic `Restart=on-failure` / `RestartSec=1s`
  semantics, installed but disabled/inactive after bootstrap;
- a closed research-versus-critical coexistence evaluator (60-second isolated and mixed windows,
  250 ms probe period, `> 500.0` ms deadline, `> 20%` nearest-rank p95 degradation, and the
  memory/CPU/disk/I/O review triggers) with dispositions `C8G_EXECUTION_HOST_SUFFICIENT`,
  `UPGRADE_ELIGIBLE:CRITICAL_DEADLINE|CRITICAL_DEGRADATION|MEMORY|CPU|DISK|IO` or
  `EXECUTION_HOST_INCONCLUSIVE`;
- closed terminal Phase-B evidence semantics: `EXECUTION_HOST_PROVEN_C8G`,
  `EXECUTION_HOST_EVIDENCE_COMPLETE_UPGRADE_ELIGIBLE:<reason>` or `EXECUTION_HOST_INCONCLUSIVE`.

The research and critical slice values in Section 5 are unchanged. An upgrade-eligible or
inconclusive result is a review trigger only: nothing is auto-purchased or auto-upgraded, Karl
decides, and a second VPS remains a separate material architecture decision rather than a scaling
step. `EXECUTION_HOST_PROVEN_C8G` would mean only that the host/runtime substrate was proven on the
tested C8G instance; it never implies account access, reconciliation, order permission or live
enablement, and S10-LIVE-ORCH-01 remains the separately gated successor. Phase B (real AlphaVPS
proof) is not authorized by the Phase-A implementation. Live remains DISABLED; capital/orders
USD 0 / 0.
