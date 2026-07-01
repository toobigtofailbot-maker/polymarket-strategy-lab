# Hermes Candidate-Review Local Manual Export CLI Chain Closeout

## Purpose

WP117 closes out the WP109 -> WP116 local/manual export and CLI convenience
chain as complete enough for bounded operator use. WP117 is a
docs/status/tests-only closeout and research-workflow transition decision
record.

WP117 does not implement new code. It does not modify the WP115 CLI. It does
not add source implementation, tools implementation, command parser behavior,
CLI behavior, report automation, Hermes runtime, scheduler, dashboard, network,
API, product, account, credential, paper/live, execution/risk/order,
dependency, workflow, lock-file, copied external code, or committed generated
artifact behavior.

## Completed Chain

The completed local/manual export chain is:

```text
WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 -> WP114 -> WP115 -> WP116
```

- WP106: operator handoff object.
- WP107: local manual export contract.
- WP108: manual export artifact builder.
- WP109: local/manual writer.
- WP110: writer operator runbook.
- WP111: temp-only writer smoke exercise.
- WP112: chain closeout / next-phase decision record.
- WP113: CLI wrapper contract.
- WP114: CLI command surface and input handoff contract.
- WP115: local/offline/manual CLI wrapper implementation.
- WP116: CLI operator runbook and smoke receipt.

## What Is Now Supported

The local/manual export chain through WP116 is complete enough for bounded
operator use.

Supported use is only manual, local, offline, and human-reviewed export of
already-valid WP108 artifact-result envelopes through either:

- the WP115 CLI convenience wrapper; or
- the lower-level import path that uses the earlier approved builder and writer
  layers.

The WP115 CLI is a convenience wrapper, not automation. It helps an operator
write one explicit local `.md` or `.txt` review artifact from one strict local
WP108 artifact-result JSON envelope.

## What Is Still Not Supported

The completed chain does not support research decisions, trading signals,
expected-return estimates, fair-value trading instructions, edge/alpha trading
instructions, position sizing, allocation instructions, strategy
recommendations, paper readiness, live readiness, deployment readiness, PR
approval, merge readiness, strategy promotion, runtime instructions,
credential permission, account/private-state access, order placement/cancel,
execution authority, risk overrides, scheduler/bot-loop behavior, dashboard
display, Hermes runtime/provider/model/prompt-runner integration, automated
report/export pipelines, dependency/workflow/lock-file changes, or committed
generated artifacts.

## Operator Use Boundary

Operators may use the chain only as a local manual review aid. Generated local
artifacts must not be committed. Human review remains required before any
interpretation, follow-up, or future WP proposal.

The exported artifact is not a source of authority. It is a review surface for
an already-valid WP108 envelope, not a decision engine.

## Evidence Of Local Coherence

WP115 focused tests prove the CLI command path can load a strict WP108
artifact-result envelope from a pytest `tmp_path` JSON file and export through
the existing WP109 writer to a pytest `tmp_path` `.md` or `.txt` file.

WP116 records the operator runbook and smoke receipt for that path. WP117 adds
no new smoke output and commits no generated artifact content.

## Output Surface Inventory

The completed chain has these bounded output surfaces:

- WP106 in-memory candidate-review operator handoff object.
- WP108 in-memory manual export artifact result.
- WP109 explicit local `.md` or `.txt` artifact file, written only to an
  operator-supplied local path.
- WP115 bounded neutral CLI stdout/stderr summaries and the explicit local
  `.md` or `.txt` artifact file written through WP109.
- WP116 operator runbook and smoke receipt documentation.
- WP117 closeout/transition documentation, focused docs/status tests, project
  status update, repo-truth-index update, and stable status fragment.

Generated artifacts are never committed.

## Forbidden Interpretation Matrix

| Interpretation or behavior | WP117 status |
|---|---|
| trade signal | Forbidden / not authorized |
| strategy recommendation | Forbidden / not authorized |
| expected-return estimate | Forbidden / not authorized |
| fair-value trading instruction | Forbidden / not authorized |
| alpha/edge trading instruction | Forbidden / not authorized |
| position sizing | Forbidden / not authorized |
| allocation instruction | Forbidden / not authorized |
| paper readiness | Forbidden / not authorized |
| live readiness | Forbidden / not authorized |
| deployment readiness | Forbidden / not authorized |
| PR approval | Forbidden / not authorized |
| merge readiness | Forbidden / not authorized |
| strategy promotion | Forbidden / not authorized |
| runtime instruction | Forbidden / not authorized |
| credential permission | Forbidden / not authorized |
| account/private-state access | Forbidden / not authorized |
| order placement/cancel | Forbidden / not authorized |
| execution authority | Forbidden / not authorized |
| risk override | Forbidden / not authorized |
| scheduler/bot-loop behavior | Forbidden / not authorized |
| dashboard display | Forbidden / not authorized |
| Hermes runtime/provider/model/prompt-runner integration | Forbidden / not authorized |
| automated report/export pipeline | Forbidden / not authorized |
| dependency/workflow/lock-file change | Forbidden / not authorized |
| committed generated artifacts | Forbidden / not authorized |

## Deferred Items That Remain Open

WP117 resolves no implementation deferred item. The following remain
future-only and require separate approved WPs:

- automated report/export pipeline;
- dashboard display;
- Hermes runtime/provider/model/prompt-runner integration;
- paper assistant integration;
- live/manual approval packet integration;
- credentials/account/private state;
- execution/risk/order behavior;
- scheduler/bot-loop behavior;
- dependency/workflow/lock-file changes.

## Next Phase Decision

The next phase should shift from local export plumbing to Hermes-assisted
candidate-review research workflow. The next phase may define how an operator
selects candidate-review packets, runs or adapts Hermes research prompts
manually, validates Hermes advisory outputs through existing validators,
records human decisions, and stores research follow-up records.

That next phase must remain advisory/manual/offline/local unless a future
approved WP explicitly changes that. WP117 does not implement that next phase;
it records the decision and required gates.

## Future Research-Workflow Options

Future approved WPs may consider:

- manual packet-selection criteria for candidate-review research;
- manual Hermes research-prompt adaptation guidance;
- validator-backed review of Hermes advisory outputs;
- human decision record format and follow-up record storage;
- local/offline research workflow runbook updates.

Each option remains future-only until separately scoped and approved. None of
these options authorizes runtime Hermes integration, prompt runner execution,
automation, paper/live trading, credentials, account/private state, dashboard
display, scheduler/bot-loop behavior, execution/risk/order behavior, dependency
changes, workflow changes, or generated artifact commits.

## Human Review Requirement

Human review remains required. Operators must treat all outputs as advisory
review aids only. Any accepted observation must flow through human review and a
separate approved WP before it changes repo behavior or runtime behavior.

## Non-Authority Statement

WP117 authorizes no implementation change, no WP115 CLI modification, does not
add source implementation under `src/`, no tools change, no runtime/Hermes
runtime/provider/model/prompt-runner behavior, no product/API/account network
behavior, no credential/private-state behavior, no paper/live behavior, no
execution/risk/order behavior, no scheduler/dashboard/bot-loop behavior, no
dependency/workflow/lock-file change, no copied external code, and no committed
generated artifact behavior.
