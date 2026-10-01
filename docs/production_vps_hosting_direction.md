# Production VPS Hosting Direction

This document is the focused planning contract recorded by S10-DEPLOY-PLAN-01 (Production VPS
Hosting Direction Lock). It records Karl's final production-hosting decision as planning truth
only. It is PLANNING_GUIDANCE_ONLY / NOT_AUTHORIZATION: it purchases, provisions, deploys,
configures, benchmarks or authorizes nothing.

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
future implementation package:      S10-DEPLOY-01
future package state:               NOT AUTHORIZED
```

C8G is the initial production-host target. Recording it is not evidence that the host has been
purchased, provisioned, benchmarked or approved for paper or live execution.

## 2. Superseded Planning Statements

This decision supersedes, as current planning truth:

- the WP61 runtime-direction shorthand "local development first. Cheap VPS later for a controlled
  live pilot" in `docs/architecture_decision_record.md` (kept there as historical context only);
- the `docs/project_charter.md` statement that VPS and cloud choices remain open;
- any roadmap implication that deployment or hosting work should occur before WP173 is
  implemented, or the shorthand "after WP172 and before WP173".

WP61's "avoid serverless for live runtime" constraint is unchanged and is consistent with this
decision.

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

S10-DEPLOY-01 must freeze exact metric definitions, observation windows and baseline methodology
before these criteria are used as evidence. No tier upgrade is automatic and nothing is
auto-purchased. Karl decides after reviewing telemetry.

## 5. Software Isolation On The Single VPS

Research workloads must not be allowed to starve execution-critical components. S10-DEPLOY-01 must
implement and prove appropriate same-host isolation, such as:

- separate service/process groups;
- CPU/memory/I/O limits or weights;
- priority classes;
- controlled concurrency;
- bounded research/Hermes worker counts;
- execution-critical service reservation/prioritization;
- explicit degradation/fail-closed behavior under resource pressure.

This planning package does not freeze Docker, systemd or Kubernetes. Kubernetes is not required by
this decision. S10-DEPLOY-01 chooses the smallest reproducible mechanism that satisfies the proof,
with no second-VPS assumption.

## 6. Migration Point

Current repo truth already contains the generic WP172 executable-edge substrate (WP172 — Alpha +
Executable Edge MVP, merged via PR #174) and the WP173 Serious Paper Trading System implementation
(WP173 — Serious Paper Trading System + Paper Cockpit, merged via PR #175). WP173 code is not
reimplemented by this direction. WP173 supplies simulated-paper runtime, accounting, risk and
reconciliation, but explicitly adds no OS scheduler/service, daemon or deployment authority.
Where current status lines say "WP170/WP172/WP173: NOT STARTED", they mean candidate-specific work
for the current qualification chain, not the generic merged substrates.

The production migration point is:

```text
after a real strategy-specific WP172 EXECUTABLE_EDGE_PASS exists
and
before the first serious production-hosted paper runtime using the existing WP173 system
```

Equivalently:

```text
candidate qualification
-> candidate-specific WP170
-> real WP172 executable-edge evidence / EXECUTABLE_EDGE_PASS
-> S10-DEPLOY-01 Production VPS Runtime Baseline
-> serious production-hosted WP173 paper runtime
-> later auth/signing/live gates only if separately authorized
```

The host transition must not be moved earlier merely for convenience. Reasons for this placement:

- WP172 proves executable-edge eligibility.
- WP173 already supplies the simulated-paper runtime/accounting/risk/reconciliation, but not OS
  daemon/service/deployment authority.
- Production-host proof is a separate cross-cutting infrastructure concern.
- Serious paper results are more useful when generated on substantially the same host/runtime
  environment intended for later restricted live operation.

## 7. Future Dedicated Package

```text
S10-DEPLOY-01 — Production VPS Runtime Baseline
DRAFT-ELIGIBLE LATER / NOT AUTHORIZED NOW
```

S10-DEPLOY-01 is a dedicated bounded package. It is not folded into WP173 or WP174. Its full
implementation WP is not drafted here. It becomes draft-eligible only when the strategy/evidence
chain reaches the migration point above, unless Karl explicitly revises timing.

## 8. Minimum Production-Host Proof Before Serious Paper

S10-DEPLOY-01 must eventually prove at least:

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

### Single-host coexistence proof

S10-DEPLOY-01 must run a representative mixed-load proof showing:

- Hermes/research/Alpha workloads active within frozen limits;
- execution-critical services remain responsive;
- resource controls actually constrain the research workload;
- no execution-critical starvation;
- latency/resource metrics remain within the frozen production-host SLO;
- stopping/throttling research does not require a second VPS.

### C8G sizing proof

S10-DEPLOY-01 must produce a telemetry-backed disposition:

```text
C8G_SUFFICIENT
or
UPGRADE_ELIGIBLE:<reason>
```

It must not auto-upgrade or auto-purchase.

## 9. DATA-03 And The Current Qualification Chain

DATA-03 is not moved to the VPS. DATA-03 remains on the current operator environment.

S10-QUAL-DATA-03 (PR #206, merged) already has its merged implementation, uses a manual bounded
operator, has no scheduler, requires historical local DATA-02 evidence for zero-network
`prepare`, and starts real prospective accrual no earlier than `2026-10-15T00:00:00Z`. Moving it
now would add infrastructure migration and local-evidence transfer risk without being required by
the frozen DATA-03 contract. The already-drafted S10-QUAL-DATA-03 POST-MERGE PREPARE CLOSURE
remains substantively unchanged; this package edits no DATA-03 code, contract or WP artifact.

Expected high-level sequence:

```text
DATA-03 prepare/accrual/seal
-> S10-QUAL-REAL-01
-> candidate-specific WP170
-> real WP172 executable-edge evidence / PASS
-> S10-DEPLOY-01 Production VPS Runtime Baseline
-> serious production-hosted WP173 paper runtime
-> later separately authorized auth/signing/live gates
```

## 10. No Authority Delta

This hosting decision does not authorize: VPS purchase; VPS provisioning; deployment; credentials;
scheduler/service activation; paper trading; execution; signing; Gate C; live trading; capital;
or orders. Current live authority remains unchanged (`docs/live_trading_authorization.md`). Live
remains DISABLED; Gate C is NOT AUTHORIZED; capital at risk USD 0; orders 0.
