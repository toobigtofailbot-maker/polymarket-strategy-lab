# Hermes Candidate-Review Research Workflow Runbook

## Purpose

WP119 is a docs/status/tests-only operator runbook for the manual/local/offline
Hermes-assisted candidate-review research workflow after WP118 intake.

This runbook documents advisory-only operator discipline. It does not implement
Hermes runtime, prompt execution, automation, validators, packet builders,
source modules, tools, CLI, scheduler, dashboard, paper/live behavior,
execution/risk/order behavior, network behavior, credentials, storage, or
generated artifacts. It does not add a prompt runner, Hermes provider/model
integration, parser, loader, writer, output schema, validator, storage path, or
any product/account/API behavior.

## Workflow Position

The completed export and CLI convenience chain is:

```text
WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 -> WP114 -> WP115 -> WP116 -> WP117
```

WP118 is the intake contract for manual/local/offline/advisory-only
human-reviewed selection of already-valid upstream candidate-review packets or
export artifacts.

WP119 documents the manual runbook layer after WP118 intake and before any
future research schemas, storage, prompt templates, or implementation.

## Operator Preconditions

Before starting a research workflow, the operator must confirm:

- the selected input passed WP118 intake checks;
- source provenance is explicit;
- evidence references are manually inspectable;
- uncertainty, missing data, and limitations are explicit;
- no raw model/Hermes output is treated as fact;
- no credentials, private state, account state, order data, paper/live data, or
  runtime data is present;
- no generated local artifacts are staged or committed;
- the operator understands all outputs remain advisory review aids only.

## Manual Workflow Steps

This workflow has no execution authority.

A. Select one candidate packet or artifact under WP118 intake criteria.

B. State the research question in neutral non-trading language.

C. List source references and what the operator must manually check.

D. List uncertainty, missing data, and limitations before any advisory review.

E. Optionally draft a Hermes research prompt manually, external to repo runtime;
do not execute it in-repo and do not add a prompt runner.

F. Review any externally/manual research output only as advisory text.

G. Validate the advisory output conceptually through existing validator
boundaries without changing validators.

H. Record human decision intent conceptually as
`ACCEPT_FOR_FURTHER_RESEARCH`, `REJECT_RESEARCH_CANDIDATE`, or
`NEEDS_MORE_EVIDENCE`.

I. Record any follow-up research task conceptually.

J. Keep all records outside committed generated artifacts unless a future
approved WP defines a storage format.

## Research Question Rules

Research questions must be neutral and non-executing.

Allowed research triage families include:

- resolution-rule ambiguity;
- evidence quality gap;
- source conflict;
- wallet/signal uncertainty;
- cross-market inconsistency;
- market-structure/microstructure concern;
- stale/missing data risk.

Forbidden research-question families include:

- should we buy/sell;
- expected return;
- fair value as trade instruction;
- alpha/edge as trade instruction;
- position size/allocation;
- paper/live readiness;
- execution/risk/order instructions;
- PR approval or merge readiness.

## Manual Hermes Prompt Adaptation Boundary

Any Hermes prompt adaptation is manual and external to repo runtime. WP119
installs or invokes no Hermes runtime, provider, model, or prompt runner.

No prompt output is accepted as fact without human review. Raw model output must
not be committed as repo truth. Prompt templates may be discussed only as future
approved WPs if committed.

## Advisory Output Review Boundary

Advisory output is not a decision engine. It must be checked against source
references, uncertainty, missing data, limitations, and falsification checks.

Advisory output cannot authorize strategy promotion, PR approval, merge
readiness, paper/live readiness, execution/risk/order behavior, credentials, or
runtime behavior.

## Human Decision Categories

Conceptual decision categories are:

- `REJECT_RESEARCH_CANDIDATE`
- `NEEDS_MORE_EVIDENCE`
- `ACCEPT_FOR_FURTHER_RESEARCH`
- `ESCALATE_TO_FUTURE_APPROVED_WP`

These categories are not strategy promotion, trade decisions, paper/live
readiness, or implementation approval.

## Cleanup / Repo Hygiene

No generated research notes are committed by WP119. Any local notes must stay
outside tracked repo paths unless a future approved WP defines a storage format.

The operator should check `git status` before committing. No local outputs
should be placed under `docs/`, `src/`, `tests/`, `tools/`, `.github/`,
`local_data/`, generated-artifact paths, or tracked repo paths.

## Future Gates

Separate approved WPs are required for:

- research question record schema;
- manual prompt template pack or adaptation guide;
- advisory output validation receipt integration;
- human decision/follow-up record format;
- storage/local file writer;
- automated report/export pipeline;
- dashboard display;
- Hermes runtime/provider/model/prompt execution;
- credentials/account/private-state behavior;
- paper/live/execution/risk/order behavior;
- scheduler/bot-loop behavior;
- dependency/workflow/lock-file changes;
- committed generated artifacts.

## Non-Authority Statement

WP119 authorizes no implementation, no runtime, no automation, no Hermes
execution, no trading, and no generated artifacts. It documents only a
manual/local/offline/advisory-only runbook for human-reviewed research workflow
after WP118 intake.
