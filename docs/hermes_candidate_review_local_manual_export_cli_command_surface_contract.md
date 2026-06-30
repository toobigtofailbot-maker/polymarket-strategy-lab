# Hermes Candidate-Review Local Manual Export CLI Command Surface Contract

## 1. Purpose

WP114 defines only the future CLI command surface and strict input handoff
contract for a possible local/manual/offline wrapper around the existing WP109
writer.

WP114 does not implement a CLI. WP114 does not authorize implementation. WP114
is docs/status/tests-only.

## 2. Chain Context

The completed candidate-review local manual export chain is:

WP106 -> WP108 -> WP109 -> WP110 -> WP111 -> WP112 -> WP113

WP107 remains the contract layer between the WP106 handoff and the WP108
artifact builder.

WP113 established the high-level future CLI-wrapper contract. WP114 narrows the
future command/input/output contract before any implementation WP may define a
parser, runner, wrapper, or source module.

## 3. Future CLI Command Surface

The future command shape is conceptual only, not runnable code:

```text
python -m tools.hermes_candidate_review_manual_export_cli \
  --artifact-json <local_path_to_strict_wp108_artifact_result_snapshot.json> \
  --output <explicit_local_output_path.md_or_txt> \
  [--overwrite]
```

Required future command-surface constraints:

- Exactly one input artifact path argument: `--artifact-json`.
- Exactly one explicit output path argument: `--output`.
- Optional overwrite flag only: `--overwrite`, default false.
- No auto path selection.
- No directory creation.
- No batch mode.
- No watch mode.
- No scheduler mode.
- No daemon mode.
- No network option.
- No model option.
- No provider option.
- No Hermes option.
- No credentials option.
- No account option.
- No private-state option.
- No paper option.
- No live option.
- No execution option.
- No risk option.
- No order option.
- No dashboard option.
- No config-mutation option.
- No stdin artifact-content mode unless a separate future WP approves it.
- No stdout artifact-content mode unless a separate future WP approves it.

## 4. Future Input Handoff Envelope

A future implementation must accept only an already-built WP108 artifact-result
snapshot, not raw Hermes output, raw model output, or arbitrary caller data.

The conceptual strict JSON handoff envelope is:

```text
{
  "envelope_type": "HERMES_CANDIDATE_REVIEW_MANUAL_EXPORT_ARTIFACT_RESULT_V1",
  "source_wp": "WP108",
  "source_contract": "WP107",
  "produced_by": "<allowed deterministic WP108 artifact builder identifier>",
  "artifact_result": {
    "is_valid": true,
    "artifact": "<object with exactly the required WP108 artifact groups>",
    "errors": [],
    "warnings": "<list of neutral codes only>"
  },
  "safety_flags": "<all required WP108/WP109 safety flags true>",
  "provenance_notice": "<local/manual/offline/synthetic-or-reviewed status only>",
  "human_review_required": true
}
```

A future implementation must fail closed if the envelope is missing, malformed,
stale, contains extra raw/free-form metadata, contains forbidden terms, has
`is_valid` not true, has missing required artifact groups, has missing or false
safety flags, or contains raw model or Hermes output.

## 5. Future Input Rejection Rules

The future CLI must reject:

- Raw model output.
- Raw Hermes response.
- Arbitrary caller dictionaries.
- Raw/free-form metadata.
- Credentials.
- API keys.
- Private state.
- Account state.
- Wallet identifiers, private identifiers, wallet secrets, and private keys.
- Order state.
- Paper state.
- Live state.
- Runtime logs.
- Prompt-runner output.
- Strategy recommendation text.
- Trade signal text.
- Expected-return text.
- Fair-value text when used as a trade instruction.
- Alpha or edge text when used as a trade instruction.
- Position-sizing text.
- Allocation text.
- PR approval text.
- Merge-readiness text.
- Unsafe path-like values.
- URI-like values.

## 6. Future Output Behavior

The future CLI may only write through the existing WP109 writer, or an explicitly
approved equivalent in the future implementation WP.

Required output rules:

- Explicit local `.md` or `.txt` path only.
- Parent directory must already exist.
- No parent-directory creation.
- No automatic path selection.
- No committed generated artifacts.
- No write under `docs/`, `src/`, `tests/`, `tools/`, `.github/`, or
  `local_data/` unless a future approved WP explicitly defines ignored scratch
  behavior.
- No artifact contents printed to stdout by default.
- No artifact contents printed to stderr by default.
- Stdout may only contain neutral bounded summary fields if separately approved
  in the implementation WP: status, output path, bytes_written, sha256, and
  neutral warning/error codes.
- Stderr may only contain neutral bounded failure codes and must never echo
  unsafe input.

## 7. Future Exit-Code Policy

Expected future implementation exit codes:

| Code | Meaning |
|---:|---|
| 0 | Success, valid artifact written. |
| 2 | Input/envelope validation failed. |
| 3 | Path/output validation failed. |
| 4 | Protected-boundary refusal. |
| 5 | Unexpected internal error, sanitized and no unsafe echo. |

## 8. Future Failure Behavior

A future CLI must fail closed. It must create no output file on invalid input.
It must not overwrite unless `--overwrite` is explicitly supplied.

A future implementation must not weaken validation, bypass WP108/WP109,
manually edit artifacts, or infer trading meaning.

## 9. Future Negative-Test Matrix

Mandatory future implementation tests:

- Valid strict envelope writes to `tmp_path` only.
- Invalid envelope fails closed.
- Missing required artifact group fails closed.
- Missing safety flag fails closed.
- False safety flag fails closed.
- Raw metadata key fails closed at any nesting depth.
- Raw model output fails closed.
- Raw Hermes output fails closed.
- Forbidden wording family fails closed.
- URI-like input path fails closed.
- URI-like output path fails closed.
- Parent directory missing fails closed.
- Existing output path without `--overwrite` fails closed.
- `--overwrite` true overwrites only explicit local path.
- No unsafe echo in stdout, stderr, errors, or warnings.
- Stdout does not contain artifact content.
- Stderr does not contain artifact content.
- No writes under tracked repo paths.
- No generated artifacts committed.
- No network, requests, or socket imports.
- No Hermes, model, or provider imports.
- No credentials, account, paper, live, execution, risk, order, scheduler,
  dashboard, or bot-loop behavior.
- Exact changed-file inventory/status tests.

Forbidden variant families that must be rejected:

- Buy, sell, trade, order, execute, entry, and exit.
- Expected return, fair value, alpha, and edge as a trade instruction.
- Position size, sizing, and allocation.
- Paper ready, live ready, and deployment ready.
- PR approval and merge readiness.
- Credentials, API key, private key, and wallet secret.
- Hermes runtime, model provider, and prompt runner.
- Network, API, account, and product behavior.
- Scheduler, daemon, and bot loop.
- Dashboard, workflow, and dependency changes.
- Generated artifacts committed.

## 10. Human Review Requirement

All output remains a manual review aid only and requires human review.

## 11. Non-Authority Statement

WP114 is docs/status/tests-only and authorizes no implementation. It adds no
source implementation, tools implementation, CLI implementation, command parser,
command runner, shell wrapper, JSON parser implementation, dependency change,
lock-file change, workflow change, generated artifact, network/API/product/
account behavior, credentials/private state, paper/live behavior, execution/
risk/order behavior, scheduler/dashboard/bot-loop/runtime/daemon behavior,
Hermes runtime/provider/model/prompt-runner behavior, copied external code, or
live-trading behavior.
