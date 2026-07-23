# Hermes Remote Provider Track Deferral And Revisit Criteria Decision

## Purpose

WP149 ends repeated unchanged remote-provider research after merged WP148
completed its evidence refresh without producing an eligible candidate. It
defines an explicit deferral state, objective event-driven revisit criteria,
a bounded evidence-packet contract, a fail-closed reopen state machine, and a
productive provider-independent next phase.

WP149 performs no provider research and does not implement the next phase.

## Position After WP148

Merged WP148 is the controlling starting truth:

```text
WP148 evidence-resolution status:
COMPLETE_EVIDENCE_STILL_INSUFFICIENT
Candidate eligibility result:
EVIDENCE_INSUFFICIENT_NO_ELIGIBLE_CANDIDATE
Remote configurations deeply researched:
3
Remote configurations eligible:
0
Remote configurations shortlisted:
0
Provider/model selection:
NOT MADE
Local baseline pivot decision:
DEFER_HARDWARE_EVIDENCE_MISSING
Remote controlled experiment readiness:
NOT_READY
Next phase:
REMOTE_PROVIDER_TRACK_DEFER_OR_RESEARCH_REFRESH_LATER_DECISION
```

The unresolved mandatory classes remain provider-side deletion,
operator-verifiable deletion, exact credential revocation and operator
verification, approval- or agreement-dependent privacy controls, and
operator/account-specific evidence unavailable through public research.
Evidence insufficiency is not provider impossibility.

## Authority And Non-Authority

The Centralized Boundary Group Reference in
`docs/ai/codex/PROTECTED_PATHS.md` is binding. WP149 authorizes one canonical
governance decision, one Markdown-only regression, one stable status fragment,
and exact project-status, repo-truth-index, and deferred-item reconciliation.

WP149 crosses none of the credentials/secrets, authenticated clients,
wallet/account behavior, order placement/cancel, execution gateway, paper
engine, scheduler/bot loop, runtime/daemon, dashboard/deployment,
dependency/lock changes, external code copying, or generated-artifact boundary
groups.

Provider research, candidate addition, shortlisting, selection, Hermes or
provider installation, accounts, terms, credentials, endpoints, model calls,
spending, persistence, source or tool changes, configuration, runtime,
paper/live, execution/risk/order, and trading behavior are not authorized.

## Repository Inputs Reviewed

The agent and Codex rulebooks; current project status, repo-truth index, and
deferred-items log; protected-path, drafting, bundling, validation, review,
evidence, and status-fragment guidance; the Hermes foundation; merged
WP141-WP148 canonical documents, tests, fixtures/source where applicable, and
status fragments; PR #148 merge metadata; project-status compatibility tests;
and architecture boundaries were inspected before editing.

Repository discovery found no accepted WP149 decision, no eligible or
shortlisted remote configuration, no provider selection, no current operator
hardware packet sufficient for local-baseline feasibility, and no paper engine
or paper-trading approval. Existing architecture registrations require no
change.

## Deferral Decision

```text
Remote provider track status:
DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE
Automatic periodic provider re-research:
FORBIDDEN
Provider track may reopen only after:
MATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL
```

The remote-provider track is inactive and deferred. It is not closed and no
candidate is permanently rejected.

## Meaning Of Deferral

Deferral means:

- no active provider candidate;
- no provider shortlist or provider/model selection;
- no scheduled periodic re-research;
- no provider implementation or remote experiment;
- no account, credential, endpoint, model-call, or spend work;
- no assumption that an unresolved evidence gap will eventually resolve; and
- no claim that an evidence-insufficient provider is permanently unsuitable.

Deferral does not abandon the Hermes research architecture, the existing local
deterministic research workflow, or human-reviewed research. It does not prove
model quality, authorize a local model, approve paper trading, or grant
paper/live execution authority.

## Material Revisit Triggers

A remote-track revisit may be proposed only when a concrete evidence artifact
supports at least one of these trigger classes:

1. a current first-party public source materially changes an unresolved
   mandatory gate;
2. a sanitized operator evidence packet proves account-specific controls;
3. a current sanitized contractual artifact materially resolves a mandatory
   gate; or
4. an official provider or deployment architecture change plausibly satisfies
   the unchanged mandatory requirements.

Actual operator hardware evidence is a separate local-hardware trigger. It may
support a local-baseline feasibility decision but does not reopen the remote
provider track.

Every proposed trigger must identify one exact affected mandatory gate and the
prior non-passing state. Discovery of an event is not acceptance of its packet.

## Non-Triggers

None of the following may reopen provider research:

- passage of a week, month, quarter, or year by itself;
- a model release without relevant privacy, deletion, or credential evidence;
- a price reduction;
- a benchmark improvement;
- social-media discussion;
- provider marketing;
- a help article repeating existing evidence;
- Tier 2 repetition of already-known evidence;
- a renamed model alias;
- an unsupported claim from sales or support;
- a login-only control without sanitized operator evidence;
- unchanged provider documentation;
- a new Codex session;
- a new WP number;
- user impatience;
- a desire to force a shortlist;
- the fact that the local harness is complete;
- the fact that remote readiness remains zero;
- general industry adoption;
- another provider having similar policies;
- cost compatibility; or
- Hermes API compatibility.

These are non-triggers even when multiple items occur together unless a
separate material evidence artifact satisfies the standard below.

## Materiality Standard

A proposed trigger is material only when it could change at least one named
mandatory row from a non-passing state to `PASS` for the exact evaluated
candidate, API, account, credential, contract, and deployment posture.

Every materiality record must contain exactly these required fields:

```text
trigger_id
trigger_type
candidate_or_architecture
affected_mandatory_gate
previous_state
new_evidence_summary
source_or_operator_evidence_type
evidence_date
freshness_status
why_material
remaining_unresolved_gates
sanitization_status
```

The record is non-material when it repeats existing evidence, changes only a
preferred criterion, cost, or performance, cannot affect eligibility, is
stale or unverifiable, assumes enterprise access, or applies to a different
API, account, credential, contract, region, or deployment posture.

Freshness is evaluated at packet review:

- public evidence must still be in force and must be accessed no more than 30
  calendar days before the packet decision;
- an undated live public page must be re-accessed no more than 7 calendar days
  before the packet decision;
- operator control evidence must be captured no more than 30 calendar days
  before the packet decision, while account rate/spend limits must be captured
  no more than 7 calendar days before it;
- contractual evidence must be current and effective, with review recorded no
  more than 30 calendar days before the packet decision; and
- architecture or hardware evidence must describe the current proposed
  posture and be captured or accessed no more than 30 calendar days before the
  packet decision.

Superseded evidence is stale regardless of age. A later research WP must
recheck freshness only where needed; freshness alone is never materiality.

## Revisit Evidence Packet

Before a new provider-research WP may be drafted, an operator or reviewer must
supply or identify one bounded packet containing:

1. the exact candidate, provider, API, model, or architecture;
2. the exact mandatory gate affected;
3. the previous evidence state;
4. the new source or sanitized operator evidence;
5. the source date or effective date;
6. the access date;
7. the source tier or operator-evidence class;
8. the direct-versus-inferred classification;
9. the account or contract dependency;
10. why the evidence could change eligibility;
11. known remaining blockers; and
12. confirmation that no secret or personal data is included.

The packet decision must be exactly one of:

```text
Revisit evidence packet:
ACCEPTED_FOR_SEPARATE_RESEARCH_WP
```

```text
Revisit evidence packet:
REJECTED_NO_MATERIAL_CHANGE
```

```text
Revisit evidence packet:
REJECTED_UNSAFE_OR_UNSANITIZED
```

Missing required fields produce `REJECTED_NO_MATERIAL_CHANGE` unless unsafe or
unsanitized content requires `REJECTED_UNSAFE_OR_UNSANITIZED`. Acceptance
means only that a separately approved bounded research WP may be proposed.
WP149 processes no real packet.

## Public Evidence Trigger

A public-evidence trigger requires a current first-party provider
API/admin/legal/privacy/security/subprocessor document that directly affects
the exact posture and could resolve a mandatory gate. Examples include
standard-posture provider-side deletion, per-experiment operator verification,
a complete exact credential lifecycle, standard access to a formerly
approval-dependent privacy control, new subprocessor/security evidence that
resolves a blocker, or an official product/API change affecting the exact
candidate.

Search snippets, aggregators, social media, marketing, repeated help content,
and unchanged Tier 2 material cannot independently trigger a revisit.

## Operator Evidence Trigger

A sanitized operator packet may prove account eligibility; exact retention
controls; exact ZDR/MAM enrollment; exact key scope and revocation; deletion
verification; region/jurisdiction configuration; and current account
rate/spend limits.

No secret, API key, token, account ID, invoice, personal data, raw provider
content, authorization header, or credential-derived value may be committed.
The packet must state who captured the evidence, when it was captured, which
exact account/API posture it applies to, which fields were sanitized, and
which mandatory gate it could change. Operator evidence is account-specific
and is not transferable to another posture.

## Contractual Evidence Trigger

A current executed or reviewable agreement, DPA, or order form may trigger a
packet only when it materially resolves a mandatory gate. It must be supplied
by the operator, sanitized before repository use, separately reviewed,
classified as operator-specific, and treated as non-transferable to another
provider or account posture.

Contractual evidence is insufficient by itself to activate an account,
credential, endpoint, provider, model, or experiment.

## Provider Architecture Trigger

A new provider or deployment architecture may be considered only when an
official current artifact plausibly shows that it satisfies the same mandatory
requirements without weakening them. It requires an accepted packet and a
separately approved discovery WP.

WP149 adds no provider candidate, provider architecture, deployment option,
shortlist entry, or selection.

## Local Hardware Trigger

Actual operator hardware evidence may justify a separately approved
local-baseline hardware and feasibility research decision. The packet must
cover current CPU/instruction set, physical and available RAM, GPU/VRAM,
usable storage, driver/runtime support, and sustained thermal/power
constraints.

This trigger does not reopen the remote-provider track, select a local model,
authorize installation, or change the chosen next phase in WP149.

## Anti-Loop Rules

```text
Repeated unchanged provider research:
FORBIDDEN
Scheduled periodic provider sweep:
FORBIDDEN
Reopen based only on elapsed time:
FORBIDDEN
Reopen based on new material evidence:
SEPARATE_APPROVAL_REQUIRED
```

A future research WP must cite the accepted packet, inspect only affected
gates plus necessary freshness checks, preserve unaffected prior evidence,
avoid rebuilding the candidate universe, avoid repeating unchanged sources,
recalculate eligibility fail-closed, stop when evidence cannot change
eligibility, and never force a shortlist.

## Deferral Review Cadence

```text
Deferral review cadence:
EVENT_DRIVEN_ONLY
```

WP149 creates no task, reminder, monitor, schedule, recurring sweep, daemon, or
background loop. Optional manual review may occur during a major Hermes
architecture review, an operator-identified provider-policy change, a
paper-trading phase transition, a security/privacy governance review, or a
documented hardware upgrade. The review may only decide whether a packet
should be proposed; it does not itself reopen research.

## Reopen State Transition

The only remote-track states are:

```text
DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE
REVISIT_PACKET_PROPOSED
REVISIT_PACKET_REJECTED
REVISIT_PACKET_ACCEPTED_PENDING_SEPARATE_WP
RESEARCH_REFRESH_AUTHORIZED
RESEARCH_REFRESH_COMPLETE_NO_ELIGIBLE_CANDIDATE
RESEARCH_REFRESH_COMPLETE_ELIGIBLE_CANDIDATE_EXISTS
```

Allowed transitions are:

- `DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE` →
  `REVISIT_PACKET_PROPOSED` when a concrete packet is submitted;
- `REVISIT_PACKET_PROPOSED` → `REVISIT_PACKET_REJECTED` when the packet has no
  material change, is unsafe/unsanitized, or is incomplete;
- `REVISIT_PACKET_PROPOSED` →
  `REVISIT_PACKET_ACCEPTED_PENDING_SEPARATE_WP` when it is safe, complete,
  fresh, and plausibly affects a mandatory gate;
- `REVISIT_PACKET_ACCEPTED_PENDING_SEPARATE_WP` →
  `RESEARCH_REFRESH_AUTHORIZED` only after separate WP approval; and
- `RESEARCH_REFRESH_AUTHORIZED` → exactly one research-refresh completion
  state after bounded research and fail-closed eligibility recalculation.

Forbidden direct transitions are:

- deferred → provider selected;
- deferred → remote implementation;
- proposed → model call;
- accepted → credential creation;
- eligible candidate exists → activation; and
- any state → paper/live trading.

A rejected or no-eligible completion returns the governance posture to
`DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE`. An eligible completion still requires
separate shortlisting, selection, control, implementation, dry-run, and
promotion decisions.

## Productive Next Phase

```text
Next phase:
LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION
```

This separately approved future phase may assess how the existing
deterministic/local research workflow creates measurable research value
without remote Hermes; research throughput; candidate rejection quality;
deterministic hypothesis records; offline/manual analyst review;
strategy-validation handoff quality; and missing market-data, replay,
accounting, risk, observability, and operational prerequisites for a later
paper-trading decision.

The next phase is provider-independent. It may decide whether paper trading is
technically and governance-ready, but it may not start paper trading, install
Hermes, use a provider/model, create credentials, call a model, trade,
implement live execution, or weaken deterministic authority.

## Promotion Gates

Remote-track promotion requires, in order: a material trigger; a complete safe
fresh packet; packet acceptance; separate research-WP approval; bounded
affected-gate research; fail-closed eligibility recalculation; a separate
shortlist/configuration decision; separate operator/security/privacy approval;
and later separately approved implementation, dry-run, and promotion gates.

Local workflow value validation and paper-trading readiness require a separate
WP. Readiness analysis does not authorize a paper engine or paper execution.
No gate may be collapsed into another.

## Explicit Deferred Capabilities

Hermes installation/version/invocation; provider/model research, candidate
addition, shortlist, selection, or activation; account/terms; credentials or
secret store; endpoint allowlist; sandbox; adapter/client/controller;
prompt/config; requests/retries; model output; benchmark; raw/stable storage;
billing/spending; local-model feasibility; paper engine; paper/live;
execution/risk/order; and trading integration remain deferred and
unauthorized.

## Output Surface Inventory

WP149 changes only:

1. this canonical Markdown decision;
2. one Markdown-only focused regression;
3. one stable WP149 status fragment;
4. `docs/project_status.md`;
5. `docs/repo_truth_index.md`;
6. `docs/deferred_items_log.md`; and
7. `tests/test_project_status_docs.py`; and
8. `tests/test_wallet_intelligence_architecture_contract_docs.py`.

There are three additions and five documentation/test updates. There are zero
source, tool, fixture, workflow, dependency, lock, configuration, credential,
prompt, runtime, provider/model output, generated artifact, billing, paper,
execution, risk, order, or trading changes.

## Forbidden Interpretations

- Deferral is not permanent provider rejection.
- Deferral is not provider selection.
- Event-driven review is not scheduled research.
- An accepted revisit packet is not research authorization.
- Research authorization is not model-call authorization.
- Eligibility is not shortlisting.
- Shortlisting is not selection.
- Selection is not activation.
- Remote-provider deferral is not Hermes architecture abandonment.
- Local workflow validation is not paper-trading approval.
- Paper-trading readiness is not paper-trading execution.
- WP149 does not implement WP150.
- No execution/risk/order/trading authority changes.

## Future WP150 Boundary

The supported separately gated boundary is:

```text
WP150 — Local Research Workflow Value Validation And Paper-Trading Readiness Decision V1
```

WP150 may inventory the existing local deterministic research workflow; define
value, throughput, rejection-quality, and hypothesis-to-validation metrics;
assess market-data, replay, paper accounting, risk, observability, and
operational prerequisites; define a paper-trading readiness matrix; and
produce docs/status/tests-only evidence deciding whether a later
implementation WP is justified.

WP150 must not start paper trading, place orders, connect credentials, install
Hermes, call a model, activate a provider, modify live execution, authorize
live capital, or implement WP151.

WP150 requires separate approval

## Decision

```text
Remote provider track status:
DEFERRED_PENDING_MATERIAL_NEW_EVIDENCE
Automatic periodic provider re-research:
FORBIDDEN
Repeated unchanged provider research:
FORBIDDEN
Scheduled periodic provider sweep:
FORBIDDEN
Reopen based only on elapsed time:
FORBIDDEN
Provider track may reopen only after:
MATERIAL_EVIDENCE_TRIGGER_AND_SEPARATE_APPROVAL
Deferral review cadence:
EVENT_DRIVEN_ONLY
Remote configurations eligible:
0
Remote configurations shortlisted:
0
Provider/model selection:
NOT MADE
Remote controlled experiment readiness:
NOT_READY
Provider/model activation:
NOT AUTHORIZED
Provider/model call:
NOT AUTHORIZED
Hermes installation/invocation:
NOT AUTHORIZED
Provider account creation:
NOT AUTHORIZED
Credential creation/use:
NOT AUTHORIZED
Network endpoint activation:
NOT AUTHORIZED
Experiment spending:
NOT AUTHORIZED
Raw input/output persistence:
NOT AUTHORIZED
Paper/live/execution authority:
FORBIDDEN
Next phase:
LOCAL_RESEARCH_WORKFLOW_VALUE_VALIDATION_AND_PAPER_TRADING_READINESS_DECISION
WP150 requires separate approval
```

## Non-Authority Statement

This deferral and revisit-governance decision has no execution authority. It
does not research, add, shortlist, select, activate, install, configure, call,
fund, persist, schedule, or trade through a provider, model, Hermes, paper
engine, execution gateway, OMS, reconciliation path, risk cap, bounded
overlay, safe mode, order path, or live-trading path.
