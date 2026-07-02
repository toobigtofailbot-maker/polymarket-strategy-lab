# Hermes Candidate-Review Research Workflow Intake Contract

## Purpose

WP118 defines the manual/local/offline intake contract for the
Hermes-assisted candidate-review research workflow. WP118 is
docs/status/tests-only.

WP118 does not implement Hermes runtime, prompt execution, automation,
validators, packet builders, source modules, tools, CLI, scheduler, dashboard,
paper/live behavior, execution/risk/order behavior, network behavior,
credentials, or generated artifacts. It does not create a runner, prompt
executor, parser, file loader, output schema, writer, validator, storage path,
automation pipeline, provider/model integration, or any product/account/API
behavior.

## Chain Context

The completed local/manual export and CLI convenience chain is:

```text
WP106 -> WP107 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113 -> WP114 -> WP115 -> WP116 -> WP117
```

- WP106: candidate-review operator handoff object.
- WP107: candidate-review handoff local manual export contract.
- WP108: candidate-review handoff manual export artifact builder.
- WP109: local/manual export writer.
- WP110: local manual export operator runbook.
- WP111: temp-only local manual export smoke exercise.
- WP112: local manual export chain closeout and next-phase decision record.
- WP113: local manual export CLI wrapper contract.
- WP114: CLI command-surface and strict input-handoff contract.
- WP115: local/offline/manual CLI wrapper implementation.
- WP116: CLI operator runbook and smoke receipt.
- WP117: CLI chain closeout and research-workflow transition decision record.

WP117 moved the project from export plumbing toward research workflow by
recording Hermes-assisted candidate-review research workflow as the next
recommended phase. WP118 starts that transition with intake discipline only.

## Supported Intake Use

Supported intake is manual operator selection of candidate-review packets or
candidate-review export artifacts for human-reviewed Hermes-assisted research
preparation.

Supported intake must be:

- manual;
- local;
- offline;
- advisory-only;
- human-reviewed;
- based on already-valid upstream artifacts or packets;
- free of credentials, private state, account state, orders, paper/live state,
  runtime logs, and raw model output.

## Allowed Input Surfaces

Allowed future input surfaces, conceptually, are:

- already-valid WP106 candidate-review handoff object or exported
  representation;
- already-valid WP108 manual export artifact result or reviewed local export
  artifact;
- WP115 CLI-exported local review artifact, if generated from a strict valid
  WP108 envelope;
- existing repo-truth docs and status fragments relevant to candidate review;
- human operator notes that are structured, reviewed, non-secret, and not
  raw/free-form metadata.

WP118 does not create any new input parser or file loader.

## Intake Preflight Checklist

Before selecting a packet for future Hermes-assisted research preparation, the
operator must confirm:

- source artifact has valid upstream chain provenance;
- evidence references are manually inspectable;
- uncertainty, missing data, and limitations are explicit;
- no raw model/Hermes output is treated as fact;
- no credential/private/account/order/paper/live/runtime data is present;
- no trade signal, expected return, fair value, alpha/edge as trading
  instruction, position sizing, allocation, paper/live readiness, PR approval,
  merge readiness, strategy promotion, execution authority, or risk override
  wording is present;
- generated local review artifacts are not committed.

## Packet Selection Criteria

Manual candidate selection criteria are non-executing research triage only.
Valid triage reasons include:

- resolution-rule ambiguity;
- evidence quality gaps;
- wallet/signal uncertainty;
- cross-market inconsistency candidate;
- market-structure/microstructure concern;
- stale or missing data risk;
- operator uncertainty requiring deeper research.

Selection is not a trade signal and not a strategy recommendation.

## Expected Future Research Workflow Output

Future outputs may be defined conceptually as:

- research question record;
- source checklist;
- advisory output validation result;
- human decision record;
- follow-up research task;
- rejection/accept-for-further-research label.

WP118 does not implement any output schema, writer, validator, or storage.

## Forbidden Interpretation Matrix

| Interpretation or behavior | WP118 status |
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

## Future Gates

Separate approved WPs are required for:

- research workflow runbook;
- research question record schema;
- manual Hermes prompt adaptation guide;
- advisory output validation receipt integration;
- human decision/follow-up record format;
- storage or local file writing;
- any Hermes runtime/provider/model/prompt execution;
- automation/report pipeline/dashboard;
- paper/live/execution/risk/order/credentials/scheduler/dependency/workflow
  behavior.

## Non-Authority Statement

WP118 authorizes no implementation, no runtime, no automation, no Hermes
execution, no trading, and no generated artifacts. It creates only a
docs/status/tests intake contract for manual/local/offline advisory packet
selection discipline.
