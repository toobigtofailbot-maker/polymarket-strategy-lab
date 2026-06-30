# Hermes Candidate-Review Local Manual Export CLI Wrapper Contract

## 1. Purpose

WP113 defines the contract for a possible future CLI wrapper around the
existing WP109 local manual export writer.

WP113 itself does not implement the CLI. It is docs/status/tests-only and
creates no command parser, runner, source module, tool, shell wrapper, or
automation.

## 2. Chain Context

The completed bounded local manual export chain is:

WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112

1. WP106 valid in-memory candidate-review operator handoff.
2. WP108 valid in-memory manual export artifact builder.
3. WP109 explicit local/manual file writer.
4. WP110 operator runbook.
5. WP111 temp-only pytest smoke exercise.
6. WP112 chain closeout and next-phase decision record.

WP107 remains the contract layer between the WP106 handoff and the later WP108
artifact builder.

## 3. Future CLI Purpose

A future CLI, if separately approved, would be a manual operator convenience
wrapper only.

The future CLI would accept only an already-valid WP108 artifact input through
an approved deterministic local handoff mechanism defined by that future WP.
It would write only through the existing WP109 writer or an explicitly approved
equivalent.

It would not create or validate raw Hermes outputs, raw model outputs, raw
free-form metadata, account/private state, paper/live state, order state, or
runtime logs.

## 4. Future CLI Required Boundaries

A future CLI wrapper must remain:

- Manual-only.
- Local-only.
- Offline-only.
- Explicit operator invocation only.
- Explicit operator-supplied output path only.
- `.md` or `.txt` output only unless a future approved WP changes this.
- Parent directory must exist.
- No automatic path selection.
- No parent-directory creation unless separately approved.
- No generated artifacts committed.
- No background writes.

The output path must be explicit, local, operator supplied, and limited to a
`.md` or `.txt` file. The future CLI must fail closed if the parent directory
does not already exist.

## 5. Forbidden CLI Behavior Matrix

| Behavior or interpretation | WP113 contract |
|---|---|
| Automatic report/export pipeline | Forbidden |
| Scheduler | Forbidden |
| Daemon | Forbidden |
| Background writer | Forbidden |
| Bot loop | Forbidden |
| Runtime service | Forbidden |
| Dashboard integration | Forbidden |
| Hermes runtime/provider/model/prompt-runner | Forbidden |
| Network/API/product/account access | Forbidden |
| Credentials/private state | Forbidden |
| Paper/live/execution/risk/order behavior | Forbidden |
| Strategy recommendation | Forbidden |
| Trade signal | Forbidden |
| Expected return | Forbidden |
| Position sizing | Forbidden |
| Paper/live readiness | Forbidden |
| PR approval / merge readiness | Forbidden |
| Dependency/workflow changes | Forbidden |
| Committed generated artifacts | Forbidden |

## 6. Future CLI Input Contract Requirements

A future CLI must fail closed on invalid input.

It must never accept raw model output or arbitrary raw caller dictionaries. It
must never accept raw/free-form metadata, account/private state, paper/live
state, order state, or runtime logs.

It must never echo unsafe input in errors, warnings, stdout, stderr, logs, or
any output artifact. It must preserve WP108 and WP109 safety flags and
forbidden-output boundaries. It must require human review and must not infer
trading meaning from the artifact.

## 7. Future CLI Output Contract Requirements

Output may be only a local manual review artifact.

Output is not a trade signal, strategy recommendation, paper/live readiness
statement, PR approval, merge-readiness statement, expected-return estimate,
position-sizing instruction, runtime instruction, execution authority, or
strategy promotion.

Any summary printed to console by a future CLI must be bounded, neutral, and
must not contain artifact contents unless separately approved. Any future
stdout or stderr behavior must be specified before implementation.

## 8. Future Implementation Gate

A future implementation WP must be separately approved.

That future WP must state the exact command surface, arguments, output
behavior, failure behavior, tests, and allowed files before implementation.

It must include negative tests for forbidden paths, invalid input, unsafe echo,
committed generated artifacts, and runtime/network/credential/order behavior.

It must stop if implementation requires broad runtime, dependency, workflow,
scheduler, dashboard, Hermes runtime, account, paper/live, execution/risk/order,
or credential changes.

## 9. Human Review Requirement

Human review remains required for all exported artifacts and all future CLI
output. A future CLI cannot convert an artifact into an automated decision,
runtime instruction, approval, readiness claim, or strategy promotion.

## 10. Non-Authority Statement

WP113 is docs/status/tests-only and does not implement or authorize a CLI. It
adds no source implementation, tool implementation, command parser, shell
wrapper, command runner, report/export automation, scheduler, daemon,
background writer, bot loop, runtime service, dashboard integration, Hermes
runtime/provider/model/prompt runner, network/API/product/account behavior,
credentials/private state, paper/live behavior, execution/risk/order behavior,
dependency change, workflow change, lock-file change, copied external code, or
committed generated-artifact behavior.
