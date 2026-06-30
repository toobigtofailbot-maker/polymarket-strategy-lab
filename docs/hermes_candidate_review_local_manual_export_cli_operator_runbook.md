# Hermes Candidate-Review Local Manual Export CLI Operator Runbook

## Purpose

WP116 documents safe operator use of the existing WP115 local/offline/manual
CLI wrapper. WP116 is docs/status/tests-only and does not modify the CLI.

The WP115 CLI is a manual convenience wrapper around the existing WP109 writer.
It accepts only an already-valid WP108 artifact-result JSON envelope and writes
one explicit local `.md` or `.txt` review artifact. The output remains a manual
review aid only and has no execution, strategy, PR approval, or merge-readiness
authority.

## Command Shape

Use exactly this command shape:

```text
python -m tools.hermes_candidate_review_manual_export_cli --artifact-json <path.json> --output <path.md_or_txt> [--overwrite]
```

Arguments:

- `--artifact-json`: explicit path to one local JSON file.
- `--output`: explicit path to one local `.md` or `.txt` output file.
- `--overwrite`: optional; without it, an existing output file is refused.

No batch, watch, stdin artifact-content, stdout artifact-content, scheduler,
daemon, dashboard, network, provider, model, Hermes, credential, account,
paper, live, execution, risk, order, or config-mutation mode is authorized.

## Input Preflight

Before running the CLI, the operator must confirm the input is:

- a local JSON file only;
- a strict WP108 artifact-result JSON envelope only;
- an already valid artifact result, not a raw source artifact candidate;
- marked with `human_review_required` set to `true`;
- marked with all required WP108/WP109 safety flags set to `true`;
- free of raw Hermes output, raw model output, prompt-runner output, or raw prompt text;
- free of raw metadata, free-form metadata, arbitrary caller metadata, and
  unreviewed extra mappings;
- free of credentials, private state, account state, wallet secrets, order state,
  paper state, live state, runtime logs, and private operational state;
- free of trade-signal, expected-return, position-sizing, buy/sell/order, PR
  approval, and merge-readiness language.

If any input preflight item fails, do not run the CLI. Rebuild or re-review the
artifact through the approved earlier chain instead.

## Output Preflight

Before running the CLI, the operator must confirm the output path is:

- an explicit local `.md` or `.txt` path only;
- inside a parent directory that already exists;
- not dependent on parent-directory creation;
- not a URI-like path such as `file:`, `http:`, `https:`, `s3:`, `gs:`, or
  another scheme-like value;
- not under `docs/`, `src/`, `tests/`, `tools/`, `.github/`, `local_data/`,
  generated-artifact paths, or tracked repo paths;
- not an existing file unless `--overwrite` is explicitly supplied.

Prefer a temporary directory or an ignored local scratch location outside tracked
repo paths. Do not place generated review artifacts in committed documentation,
source, tests, tool, workflow, local-data, or generated-artifact directories.

## Expected Success Behavior

On success:

- the process exits `0`;
- stdout contains only a bounded neutral JSON summary;
- stderr is empty;
- the output file is written by the existing WP109 writer;
- the artifact remains a manual review aid only.

The stdout summary is not an artifact body, trading recommendation, approval,
readiness statement, strategy instruction, or runtime instruction.

## Expected Failure Behavior

Expected failure exit codes:

| Code | Meaning |
|---:|---|
| 2 | Input/envelope validation failure. |
| 3 | Path/output validation failure. |
| 4 | Protected-boundary refusal. |
| 5 | Sanitized unexpected internal error. |

On invalid input or invalid paths, the CLI must create no output file and must not echo unsafe content.
Failure output must remain bounded and neutral.

## Operator Cleanup

Generated local artifacts are not committed.

After any local run:

- keep generated artifacts only under temporary or ignored local scratch policy;
- run `git status --short` before committing unrelated work;
- delete or retain generated files only according to the local ignored-artifact
  policy;
- never stage generated local review artifacts.

## Future Gates

The following require separate approved WPs before any implementation or
operational use:

- dashboard display;
- automation or report pipeline behavior;
- Hermes runtime, provider, model, or prompt-runner behavior;
- paper assistant or live approval packet behavior;
- credentials, account, or private-state behavior;
- execution, risk, order, or OMS behavior;
- scheduler, daemon, service loop, or bot-loop behavior;
- dependency, workflow, or lock-file changes.

This runbook does not promote the WP115 CLI beyond local/offline/manual
operator use.
