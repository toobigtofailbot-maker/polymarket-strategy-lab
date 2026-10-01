# Architecture Decision Record

This file records planning-level architecture decisions that are repo truth only
after the approving work package merges. It does not grant implementation
authority beyond the active work package scope.

## WP61 Direction Lock-In - User-Approved Execution Path

Status: WP61_MERGED (PR #62; merge commit fa84711471fcd81a9f6a447584d0e5dd92e4f4c4)

Scope: planning constraints and research-data metadata only. There is no database, dashboard, runtime, deployment, scheduler, or execution implementation in WP61.

### Database Direction

Decision: SQLite first for local research snapshots, paper-trading state,
positions, orders, PnL, local reports, and early bot state.

Postgres deferred until multi-process, hosted runtime, larger data volume, team
access, or production reliability needs justify it.

Implementation constraints:
- No database implementation in WP61.
- Future schemas should be written in a migration-friendly way where practical.
- No Postgres dependency may be added until explicitly approved.

### Dashboard Direction

Decision: Streamlit first for fast internal operator/research dashboard.
Grafana later for runtime metrics and operations monitoring. Next.js only if productizing
or if a polished user-facing dashboard becomes necessary.

Implementation constraints:
- No dashboard implementation in WP61.
- The Streamlit choice does not imply immediate dependency addition.

### Runtime Direction

Decision: local development first. Cheap VPS later for a controlled live pilot.
Avoid serverless for live runtime because durable state and predictable process
behavior matter.

Implementation constraints:
- No VPS, deployment, scheduler, bot loop, or hosted-runtime implementation in
  WP61.

Superseded (historical context only): the generic "cheap VPS later" hosting
shorthand above is superseded by the S10-DEPLOY-PLAN-01 Production VPS Hosting
Direction Lock below. The "avoid serverless for live runtime" constraint remains.

### Strategy Direction

Decision: rules-based + research-score-driven strategy first.

LLM may be used only as read-only analyst/proposal layer. There is no autonomous LLM execution authority.

Implementation constraints:
- Human review remains required.
- Advisory-only semantics remain binding.
- Live execution remains forbidden unless a future explicit authorization updates
  repo truth.

### Execution Ladder

Decision: lock this phased ladder:

```text
research-only -> paper -> dry-run -> manual live approval -> restricted live
research-only → paper → dry-run → manual live approval → restricted live
```

Skipping phases requires explicit future approval. Live trading authorization is
still absent. Credentials remain forbidden until an approved future work package.

### Remaining Research Before Live

These are future research or investigation topics only. They are candidates for
Agent Mode / deep research before any execution or live phase:

- Polymarket API/CLOB execution architecture.
- Legal, terms, jurisdiction, and access review.
- Prediction-market strategy realism.
- Paper trading realism requirements.
- Hosting and runtime architecture.

WP61 implements none of these topics.

## S10-DEPLOY-PLAN-01 Production VPS Hosting Direction Lock

Status: APPROVED_PLANNING_DIRECTION (repo truth after S10-DEPLOY-PLAN-01 merges);
deployment status NOT_PROVISIONED / NOT_DEPLOYED.

Scope: planning truth only. The focused contract is
`docs/production_vps_hosting_direction.md`. Nothing is purchased, provisioned,
deployed, configured or benchmarked, and no runtime, source, workflow or
dependency change is made.

Decision: Karl's final production-hosting direction supersedes the WP61
"cheap VPS later" shorthand and the open VPS/cloud choice:

- Provider: AlphaVPS.
- Location: Sofia, Bulgaria.
- Initial tier: C8G (4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10).
- OS: Ubuntu 24.04 LTS / x86-64.
- Architecture: ONE_CONSOLIDATED_POLYMARKET_VPS. The same host is intended
  eventually to run Hermes, Alpha Factory/research, data, persistence,
  orchestration, monitoring, market-data/runtime, strategy execution, hard-risk
  controls, order placement/cancellation, reconciliation, paper trading and
  eventual restricted live execution, each only as separately authorized.
- Default separate research/live VPS: NO. A second VPS needs a future explicit
  architecture decision backed by evidence that same-host isolation is
  insufficient.
- Upgrade path: C8G -> C12G -> C16G/P-series -> larger only by telemetry
  evidence. Upgrade eligibility criteria are review triggers, never automatic
  upgrades or purchases; Karl decides after reviewing telemetry.
- Isolation: research workloads must not starve execution-critical components;
  the mechanism (Docker/systemd/other) is not frozen here and Kubernetes is not
  required.

Migration point: after a real strategy-specific WP172 EXECUTABLE_EDGE_PASS
exists and before the first serious production-hosted paper runtime using the
existing WP173 system (generic WP172 and WP173 are already merged; WP173 is
not reimplemented).

Future package: S10-DEPLOY-01 — Production VPS Runtime Baseline, a dedicated
bounded package, DRAFT-ELIGIBLE LATER / NOT AUTHORIZED NOW.

DATA-03 remains on the current operator environment and is not moved to the
VPS.

Implementation constraints:
- No VPS purchase, provisioning, deployment, credentials, scheduler/service
  activation, paper trading, execution, signing, Gate C, live trading, capital
  or orders are authorized by this decision.
- Live trading authorization is unchanged (`docs/live_trading_authorization.md`).
