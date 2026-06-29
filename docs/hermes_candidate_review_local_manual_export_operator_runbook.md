# Hermes Candidate-Review Local Manual Export Operator Runbook

## 1. Purpose

This runbook documents the manual-only local procedure for using the WP109
writer to export valid WP108 candidate-review manual export artifacts.

The output is a local human-review artifact. It is not a trade signal, not a
strategy recommendation, not a paper or live readiness statement, not a PR
approval, and not a merge-readiness statement.

WP110 is docs/status/tests-only. It adds no source implementation, CLI,
scheduler, daemon, background writer, network exporter, Hermes runtime,
provider, model, prompt runner, dashboard, dependency, workflow, paper/live,
execution, risk, order, credential, account, or generated-artifact behavior.

## 2. Allowed Inputs

Use only valid WP108 `CandidateReviewManualExportArtifactResult` objects
created by `build_candidate_review_manual_export_artifact`.

The artifact must already have passed the WP106 handoff checks and the WP108
artifact safety checks. The writer must receive `artifact_result.is_valid=True`
and all required WP108 artifact groups and safety flags.

Do not pass raw model output, raw free-form metadata, arbitrary external text,
credentials, private state, account state, order state, paper or live state,
runtime logs, prompt-runner output, or any unvalidated caller data.

## 3. Allowed Output

The operator supplies one explicit local output path ending in `.md` or `.txt`.

The parent directory must already exist. The writer must not create parent
directories, choose paths automatically, create a directory tree, or write to a
URI-like path. Generated artifact files are local working artifacts only and
must not be committed.

## 4. Manual Preflight

Before writing an artifact, the operator confirms:

- PR/WP dependencies are merged: WP106, WP107, WP108, and WP109 are present on
  current `main`.
- The local worktree is clean, or the output path is outside tracked repo paths
  or under ignored local scratch space.
- The artifact data contains no secrets, credentials, private state, account
  state, order state, runtime logs, raw model output, or raw/free-form metadata.
- The output path is local and not URI-like.
- The output suffix is `.md` or `.txt`.
- No generated artifact file is staged.

## 5. Safe Usage Pattern

The safe pattern is import-based Python use from an operator-controlled local
script or REPL. This example is illustrative only; it is not a CLI.

```python
from pathlib import Path

from src.data_layer.hermes_candidate_review_handoff_manual_export_writer import (
    write_candidate_review_manual_export_artifact,
)

# artifact_result must be a valid WP108 CandidateReviewManualExportArtifactResult.
scratch_path = Path("local_data/manual_export_scratch/example_artifact.md")

result = write_candidate_review_manual_export_artifact(
    artifact_result=artifact_result,
    output_path=scratch_path,
)

assert result.is_valid is True
print(result.bytes_written, result.sha256)
```

Use ignored local scratch paths for real operator work. Do not place generated
artifacts under tracked documentation, source, test, workflow, or tooling paths.
Do not include real market data, wallet or account identifiers, credentials,
API keys, private state, order text, position sizing, expected-return language,
or trade language in examples or committed docs.

## 6. Operator Review Checklist

After running the writer, verify:

- The file exists only as a local artifact.
- The boundary notice is present.
- All required safety flags are present.
- `bytes_written` is greater than zero if the result is valid.
- `sha256` is recorded locally if the operator needs an integrity check.
- No generated artifact is staged.
- The artifact is deleted or retained only according to ignored local-file
  policy.

Human review is required before any interpretation of the exported artifact.

## 7. Failure Handling

If the writer returns an invalid result, stop and inspect the neutral error
codes. Do not retry by weakening validation, changing safety flags, bypassing
WP108, editing artifacts manually, or moving generated output into committed
repo paths.

Do not use a failed or manually edited output for execution, risk override,
paper readiness, live readiness, strategy promotion, PR approval, merge
readiness, or any automated process.

## 8. Forbidden Scope Matrix

| Scope | WP110 authority |
|---|---|
| CLI | Not authorized |
| Scheduler / daemon / bot loop | Not authorized |
| Background writer | Not authorized |
| Automatic report or export pipeline | Not authorized |
| Network / API / product / account behavior | Not authorized |
| Hermes runtime / provider / model / prompt runner | Not authorized |
| Credentials / private state | Not authorized |
| Paper / live behavior | Not authorized |
| Execution / risk / order behavior | Not authorized |
| Dashboard display | Not authorized |
| Dependency or lock-file changes | Not authorized |
| Workflow changes | Not authorized |
| Committed generated artifacts | Forbidden |

## 9. Future Gates

Separate approved work packages are required for:

- CLI wrapper.
- Report automation.
- Dashboard display.
- Scheduler integration.
- Hermes runtime integration.
- Any paper, live, execution, risk, order, credential, account, network, product,
  dependency, or workflow integration.

## 10. Related Files

- `src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py`
- `src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py`
- `tests/test_hermes_candidate_review_handoff_manual_export_writer.py`
- `docs/hermes_candidate_review_handoff_local_manual_export_contract.md`
- `docs/status_entries/WP108.md`
- `docs/status_entries/WP109.md`
