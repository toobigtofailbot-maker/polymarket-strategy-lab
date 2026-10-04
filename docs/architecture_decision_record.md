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

Superseded by V2.1 (historical context only): the permanent "LLM read-only
analyst/proposal layer only" assumption above is superseded as future target
architecture by the accepted V2.1 Strategy Lifecycle + Portfolio Authority
architecture below, under which Hermes will later make soft strategy/lifecycle
judgments inside a human-defined outer envelope. Current runtime truth is
unchanged: Hermes remains research-only until S10-HERMES-STRAT-01, and no LLM
has execution authority today.

### Execution Ladder

Decision: lock this phased ladder:

```text
research-only -> paper -> dry-run -> manual live approval -> restricted live
research-only → paper → dry-run → manual live approval → restricted live
```

Skipping phases requires explicit future approval. Live trading authorization is
still absent. Credentials remain forbidden until an approved future work package.

Superseded by V2.1 (historical context only): this universal research -> paper ->
dry-run -> manual live approval -> restricted live ladder, including manual live
approval per strategy, is superseded as future target architecture by V2.1: a
human-authorized global PortfolioAuthorityPolicy replaces per-strategy manual live
approval, and a known candidate may later reach tiny exploratory live through
lifecycle -> Hermes strategy manager -> execution feasibility -> exploratory Gate C
-> execution host -> live orchestrator. Live trading remains DISABLED today.

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

Superseded status (historical context only): S10-DEPLOY-01 has since merged as a
research runtime baseline (PR #209, head 3e9d595e014275662e90b5f22809f66b3e82cb39,
merge 02eeed13dc0b9552e5685f48198d060e78c797e1); host provisioning/activation
remains separately gated. The serial "after WP172 -> deploy -> WP173" migration
point above is not current universal architecture.

DATA-03 remains on the current operator environment and is not moved to the
VPS.

Implementation constraints:
- No VPS purchase, provisioning, deployment, credentials, scheduler/service
  activation, paper trading, execution, signing, Gate C, live trading, capital
  or orders are authorized by this decision.
- Live trading authorization is unchanged (`docs/live_trading_authorization.md`).

## V2.1 Strategy Lifecycle + Portfolio Authority Architecture (S10-STRAT-LIFE-01)

Status: V2.1 target architecture: ACCEPTED (Karl approved the V2.1 target
architecture and product direction). This is the current target architecture; the
first implementation foundation is S10-STRAT-LIFE-01 (strategy lifecycle + global
portfolio authority core, `docs/strategy_lifecycle_portfolio_authority_contract.md`).
It does not change any current runtime boundary.

Accepted principles:

- Humans define the outer blast radius.
- Hermes will later make soft strategy/lifecycle judgments inside it.
- Deterministic code enforces the outer envelope and account/execution safety.
- Formal QUAL/WP170/WP172 remains the strongest evidence lane, not the universal path.
- ALPHA-03 is a parallel recurring-discovery feeder, not a prerequisite for a known candidate.
- Strategy-local failure is strategy-local by default.
- Bounded child adaptations may inherit bounded freedom.
- Material children lose automatic higher-band inheritance but remain eligible for
  exploratory treatment.
- A human-authorized global PortfolioAuthorityPolicy replaces per-strategy manual live
  approval as target architecture; no per-strategy human approval field exists.

Current V2.1 target graph:

```text
MARKET / PUBLIC DATA / EVENTS
-> ALPHA / EXISTING RESEARCH INPUT
-> STRATEGY FAMILY / VERSION
-> HERMES STRATEGY JUDGMENT
-> PORTFOLIO AUTHORITY / ACTIVE BUDGET
-> HARD EXECUTION SAFETY
-> PAPER OR BOUNDED LIVE
-> PERFORMANCE
-> HERMES REASSESSMENT
-> CONTINUE / SCALE / REDUCE / ADAPT / QUARANTINE
```

Known-candidate path (does not require ALPHA-03):

```text
KNOWN CANDIDATE -> lifecycle -> Hermes strategy manager -> execution feasibility
-> exploratory Gate C -> execution host -> live orchestrator -> tiny exploratory live
```

Parallel discovery lane: ALPHA-03 -> recurring autonomous discovery/research -> new
candidate -> same lifecycle. Strong formal lane: candidate needing durable/larger
evidence -> qualification -> WP170 -> formal WP172 -> qualified paper -> larger
validated risk band.

Hard deterministic protection remains focused on credentials/signing, venue/access
validity, durable mutation semantics, reconciliation/account truth, global
capital/exposure/loss ceilings, kill state, and corrupt/stale shared-state integrity.
Soft strategy judgment is planned for Hermes but is not implemented by S10-STRAT-LIFE-01.

Supersession (future target architecture only; historical text is retained above and
in the referenced documents):

- WP61's permanent "LLM read-only analyst/proposal layer only" assumption: superseded.
- WP61's universal research -> paper -> dry-run -> manual live approval -> restricted
  live ladder: superseded.
- WP95's permanent Hermes-advisory-only / never-final-decision-maker assumption
  (`docs/hermes_research_brain_execution_plan.md`): superseded.
- WP154 Section 5 universal claim that Hermes can never transition/promote/approve
  lifecycle actions, Section 6 universal non-skippable single Alpha lineage, and
  Section 7 universal serial adoption sequence
  (`docs/adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md`):
  superseded.

Current implemented boundaries are unchanged:

- Existing controlled Hermes research mode remains research-only and unchanged until
  S10-HERMES-STRAT-01.
- Current Gate C remains its existing strict qualified/canary implementation until a
  later Gate-C V2.1 WP.
- Existing qualification/WP170/formal-WP172 mechanics remain unchanged.
- Existing WP173 qualified and research-paper modes remain unchanged.
- S10-DEPLOY-01 is merged at main 02eeed13dc0b9552e5685f48198d060e78c797e1, but host
  provisioning/activation remains separately gated.
- DATA-03 remains unchanged and non-blocking.
- ALPHA-03 remains separately gated and off the first-known-candidate critical path.
- Live trading remains DISABLED (`docs/live_trading_authorization.md`).

Non-blocking sequence:

```text
S10-DEPLOY-01 host activation lane       (parallel)
DATA-03 weather evidence lane            (parallel)
S10-ALPHA-03 discovery lane              (parallel)

S10-STRAT-LIFE-01
-> S10-HERMES-STRAT-01
-> S10-EXEC-FEAS-01
-> S10-GATE-C-EXPLORE-01
-> S10-DEPLOY-EXEC-01
-> S10-LIVE-ORCH-01
```

S10-ALPHA-03 feeds future new opportunities into the same lifecycle but is not a hard
prerequisite for first exploratory live from an already-known candidate. No successor
starts automatically; S10-STRAT-LIFE-01 grants no credential, order, paper, execution,
live, capital or merge authority (capital/orders USD 0 / 0).

## V2.1 Hermes Strategy Manager Core (S10-HERMES-STRAT-01)

Status: MERGED (PR #211 merged at `4519aab3d7f8424fc74c59104cc4e7afe0ff11b8`, head `9439283768b78b7302290ba6b8611e3477aa3c6a`; formerly the current
bounded implementation target / implemented candidate on base `dab28ee45c1f8267248d52601c90d3f3509034f9`, after PR #210 /
S10-STRAT-LIFE-01 merged). Contract: `docs/hermes_strategy_manager_contract.md`.

Two Hermes surfaces are distinct:

- Existing generic controlled research primitive: a research-only raw Hermes run with untrusted
  output and no direct strategy/execution/live authority. Its generic and context modes are
  unchanged when strategy mode is off.
- HERMES-STRAT layer: verified STRAT-LIFE context + bounded evidence + existing controlled Hermes
  run + strategy-mode output schema + deterministic repository validation = canonical soft Hermes
  strategy decision.

Raw Hermes output remains untrusted and every raw authority flag is still required. The validated
repository record (`HermesStrategyAssessment`) is the V2.1 soft strategy decision; it is not a hard
authorization. It allocates no budget, moves no risk band, changes no PortfolioAuthorityPolicy,
claims no execution feasibility or Gate-C permission, creates no paper session or exposure, and
never writes the STRAT-LIFE store.

Superseded as a current target statement (historical text retained): the universal wording that
Hermes can never make strategy lifecycle decisions. Hermes now makes canonical soft strategy
judgments (CONTINUE / SCALE / REDUCE / ADAPT / PAPER / QUARANTINE / RETIRE) inside the human outer
envelope.

Hard deterministic ownership is unchanged and explicit: credentials/signing, venue/access
validity, durable mutation semantics, reconciliation/account truth, global capital/exposure/loss
ceilings, kill state, corrupt/stale shared-state integrity, the PortfolioAuthorityPolicy,
lifecycle state transitions and execution remain deterministic or human-owned; Hermes cannot
override them. Formal QUAL/WP170/WP172 remains the strongest evidence lane but is not made a
universal gate for Hermes assessments.

Known-candidate path capability status: lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy
manager (S10-HERMES-STRAT-01: implemented capability) -> execution feasibility (S10-EXEC-FEAS-01:
next core package after HERMES-STRAT review and merge) -> exploratory Gate C -> execution host ->
live orchestrator -> tiny exploratory live. ALPHA-03 remains a parallel, non-blocking feeder.
S10-CC-FOUND-01 is NOT AUTHORIZED / NOT STARTED until S10-HERMES-STRAT-01 actually merges; the
Control Center remains NOT STARTED. DATA-03 remains unchanged and non-blocking; S10-DEPLOY-01 host
activation is separate; Gate C is unchanged; live trading remains DISABLED; capital/orders USD 0 / 0.

## V2.1 Current Public Execution Feasibility Core (S10-EXEC-FEAS-01)

Status: MERGED (PR #212 merged at `35db4f05347b8b27f7bd0296cf9b1b0627e58d12`, head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`; formerly the
current bounded implementation target / implemented review target on base
`4519aab3d7f8424fc74c59104cc4e7afe0ff11b8`, after PR #211 / S10-HERMES-STRAT-01 merged). Contract:
`docs/execution_feasibility_contract.md`. The known-candidate path paragraph below is the
EXEC-FEAS implementation-time record; see the S10-GATE-C-EXPLORE-01 section for current status.

S10-HERMES-STRAT-01: MERGED. S10-EXEC-FEAS-01 is implemented as the current public mechanical
feasibility sibling of the formal evidence lane. Three execution concepts stay distinct:

- Qualification evidence availability: metadata saying whether evidence exists about fees,
  resolution rules, tick/min-order, spread/depth, latency and partial fill. Unchanged.
- S10-EXEC-FEAS-01 current public execution feasibility: can this exact proposed intent
  mechanically operate under current public venue state? It binds one exact StrategyVersion and
  its execution-rule digest, bounded current public Gamma/CLOB evidence and a deterministic
  venue-mechanics evaluation into content-addressed records with the closed status vocabulary
  FEASIBLE / LIMITED / INCONCLUSIVE / NOT_FEASIBLE.
- WP172 formal executable edge: does a preregistered/OOS strategy retain executable edge after
  execution frictions? WP172 remains the formal durable executable-edge evidence lane;
  EXECUTABLE_EDGE_PASS is not reused, renamed, bypassed or weakened.

Current public execution feasibility is not WP172 executable edge, not strategy merit, not
profitability, not account capacity and not a Gate-C or order decision. It has no persistence,
reads no account state and has no credential, order, execution or live authority.

Known-candidate path capability status: lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy
manager (S10-HERMES-STRAT-01: MERGED) -> execution feasibility (S10-EXEC-FEAS-01: implemented
capability, current review target) -> exploratory Gate C (S10-GATE-C-EXPLORE-01: next core package
after EXEC-FEAS review and merge; NOT AUTHORIZED / NOT STARTED) -> execution host -> live
orchestrator -> tiny exploratory live. The path is unchanged. ALPHA-03 remains a parallel,
non-blocking feeder and is not a prerequisite. DATA-03 remains unchanged and non-blocking;
S10-CC-FOUND-01 remains a parallel lane; S10-DEPLOY-01 host activation is separate; Gate C is
unchanged; live trading remains DISABLED; capital/orders USD 0 / 0.

## V2.1 Exploratory Gate C Policy Permit Core (S10-GATE-C-EXPLORE-01)

Status: current protected implementation target / implemented review target (base
`35db4f05347b8b27f7bd0296cf9b1b0627e58d12`, after PR #212 / S10-EXEC-FEAS-01 merged). Governance track PROTECTED,
risk 4, independent draftability certificate hash-bound to the exact prompt/spec. Contract:
`docs/exploratory_gate_c_contract.md`.

S10-EXEC-FEAS-01: MERGED. S10-GATE-C-EXPLORE-01 is implemented as the first V2.1 deterministic
exploratory execution-eligibility Gate C. Given the current verified STRAT-LIFE lifecycle/policy
state, the latest canonical Hermes strategy judgment and the exact current-public EXEC-FEAS
evidence for one execution intent, it decides whether that exact intent may proceed to later
runtime/account/access/reconciliation checks inside the current human-authorized exploratory
envelope. Both canonical stores are read only through their verified loaders; no caller snapshot
is authority and no store is written or created.

The output is an immutable content-addressed ExploratoryGateCDecision (PERMIT_ELIGIBLE /
PERMIT_REJECTED with closed ordered reasons and the inherited STRAT-LIFE capacity reasons) and,
only when eligible, an ExploratoryGateCPermit scoped to the exact intent. This is hard
eligibility authority, not live or order authority: the exploratory permit is
necessary-but-not-sufficient future evidence and fixes runtime account, access, reconciliation
and identity revalidation as required. A SCALE judgment never widens the current
EXPLORATORY_LIVE allocation, and the static exact-intent ceilings make no account-capacity claim.

Legacy separation: WP175 remains the historical/manual real restricted-live canary (Gate-B
credential/session, A3 and real CREATE transport), unchanged. S10-GATE-C-EXPLORE-01 is the V2.1
credential-free exploratory policy permit: it neither edits nor imports `src/execution_gateway/`,
issues no legacy WP175 Gate-C live permit, enters no A3 state and has no account, geoblock,
credential, signing, order or live authority.

Known-candidate path capability status (current): lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes
strategy manager (S10-HERMES-STRAT-01: MERGED) -> execution feasibility (S10-EXEC-FEAS-01: MERGED)
-> exploratory Gate C (S10-GATE-C-EXPLORE-01: implemented capability, current review target) ->
execution host (S10-DEPLOY-EXEC-01: next core successor after GATE-C-EXPLORE review and merge;
NOT STARTED) -> live orchestrator (S10-LIVE-ORCH-01: later) -> tiny exploratory live. The accepted
V2.1 architecture and the locked Control Center baseline are unchanged. S10-CC-OPS-01 may begin
only after GATE-C-EXPLORE merges, as a separate package; S10-CC-FOUND-01 is parallel and
independent; ALPHA-03 remains a parallel, non-blocking feeder; DATA-03 remains unchanged and
non-blocking; S10-DEPLOY-01 host activation is separate; live trading remains DISABLED;
capital/orders USD 0 / 0.
