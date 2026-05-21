# Agent Context Exporter Operator Runbook

## Status

- Runbook status: LOCAL_OPERATOR_RUNBOOK
- Exporter status: LOCAL_OFFLINE_READ_ONLY_EXPORTER
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent report generation status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Live trading status: DISABLED
- Credentials status: NOT_USED

## Purpose

This runbook documents safe manual operation of the WP23 local/offline/read-only agent context exporter at `tools/polymarket/export_agent_context.py`.

Exported context is advisory evidence for future human review only. It has no execution authority and cannot override current repo truth.

## Non-Goals / Forbidden Uses

This runbook is not:

- a Hermes setup guide;
- an agent runtime guide;
- a report generator;
- a signal generator;
- a trade proposal;
- a backtest;
- paper trading;
- live trading;
- scheduler or bot loop operation;
- account, credential, or private endpoint access.

The exporter must not be used to place orders, cancel orders, sign orders, submit orders, connect accounts, read credentials, query private endpoints, mutate configs, start a scheduler, start a bot loop, run a backtest, run paper trading, or make live trading decisions.

## Pre-Run Checklist

- Confirm the local repo is clean with `git status --short`.
- Run commands from the repository root.
- Confirm any explicit output path is under `local_data/agent_context_exports/`.
- Use default no-write mode unless a local JSON file is intentionally needed.
- Do not include local report metadata unless intentionally needed.
- Do not include bounded excerpts unless intentionally needed and reviewed for redaction/staleness caveats.
- Do not commit generated output.
- Do not feed output into Hermes, an AI runtime, or any automated advisory tool unless a future approved work package allows it.

## Commands

Default no-write command:

```powershell
python tools/polymarket/export_agent_context.py
```

Help command:

```powershell
python tools/polymarket/export_agent_context.py --help
```

Explicit output command:

```powershell
python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp24_context.local.json
```

Optional metadata command:

```powershell
python tools/polymarket/export_agent_context.py --include-local-report-metadata --out local_data/agent_context_exports/wp24_context_with_metadata.local.json
```

Optional bounded excerpts command:

```powershell
python tools/polymarket/export_agent_context.py --include-excerpts --max-excerpt-chars 800 --out local_data/agent_context_exports/wp24_context_with_excerpts.local.json
```

Local report metadata is metadata-only. Bounded excerpts apply to allowlisted tracked docs only, are capped by `--max-excerpt-chars`, and use best-effort secret-like redaction. Operators must still review excerpts before sharing because redaction is not a substitute for human review.

## Expected Default Console Summary

The default command writes no file and prints a console summary with:

- schema version;
- export mode;
- source commit;
- included artifact count;
- deferred item count;
- output written;
- safety line.

Expected safety line:

```text
safety: no network, no credentials, no orders, no Hermes runtime, no execution authority
```

## Output Validation

Confirm JSON parses using the Python standard library:

```powershell
python -m json.tool local_data/agent_context_exports/wp24_context.local.json > NUL
```

Cross-platform alternative:

```sh
python -m json.tool local_data/agent_context_exports/wp24_context.local.json > /dev/null
```

Confirm these fields exist:

- `schema_version`
- `export_mode`
- `source_commit`
- `included_local_artifacts`
- `safety_boundaries`
- `deferred_items`
- `redaction_policy`
- `staleness_policy`
- `human_review_requirements`

Minimal field inspection:

```powershell
python -c "import json; p='local_data/agent_context_exports/wp24_context.local.json'; d=json.load(open(p, encoding='utf-8')); print(d['schema_version'], d['export_mode'], d['source_commit']); print(len(d['included_local_artifacts']), len(d['deferred_items']))"
```

## Git Hygiene After Export

Run:

```powershell
git status --short
```

Generated output must not be committed. Expected behavior: files under `local_data/agent_context_exports/` are ignored local data and must not appear as staged or tracked.

If generated output appears in `git status --short`, stop and do not commit it. Confirm the path is under ignored `local_data/`, investigate ignore coverage, and keep the generated file out of staging.

## Interpreting The Export

- `repo_truth_summary`: machine-readable summary of current repo-truth safety and status fields. Current repo truth still overrides the export if they differ.
- `included_local_artifacts`: allowlisted tracked docs and optional allowlisted local report metadata. Each item records path, type, provenance, size, checksum, generated timestamp when detected, and whether content was included.
- Checksums/provenance: `sha256` and provenance classification help identify the exact local evidence observed by the exporter. They do not make stale output authoritative.
- `deferred_items`: selected unresolved deferred items that affect interpretation, including report generation, Hermes setup, rate-limit, and scheduler gaps.
- `safety_boundaries`: status values for live trading, credentials, execution, scheduler, bot loop, Hermes runtime, account connection, network use, and agent execution authority.
- `staleness_policy`: states that current repo truth and current merged state override stale exported context.
- `human_review_requirements`: states that any agent output affecting repo files, runtime behavior, configuration, polling, trading, deployment, or operations requires human review and the normal Codex work-package flow.

## Sharing / Future Advisory Use

Exports can become stale immediately after repo changes. Repo truth overrides output.

Review output before sharing or feeding it into future advisory tooling. Do not send output to unapproved third-party tools if it includes local report metadata or excerpts unless the user explicitly approves that sharing.

Future Hermes or AI consumption requires a separate approved work package or manual setup decision. This runbook does not install, configure, or authorize Hermes; Hermes remains NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY.

## Local Report Generation

After a context export is generated, WP25 allows a deterministic local/offline/read-only report with `python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/<name>.local.json`. Report outputs are optional and must be explicit paths under `local_data/agent_context_reports/`. See `docs/agent_context_report_generator.md`.

## Troubleshooting

- Path rejected because it is not under `local_data/agent_context_exports/`: rerun with an explicit `--out local_data/agent_context_exports/<name>.local.json` path.
- Path traversal rejected: remove `..` from the output path and keep output under the allowlisted directory.
- Missing docs reduce artifact count: confirm the repo is current and the allowlisted docs are tracked; missing allowlisted docs are skipped rather than replaced by arbitrary paths.
- Local report metadata path absent: this is acceptable; optional metadata adds entries only when allowlisted local report directories exist.
- Generated output visible in `git status --short`: stop, do not stage or commit it, and confirm `local_data/` ignore behavior before continuing.
- JSON parse failure: rerun the exporter, validate with `python -m json.tool`, and discard malformed local output.
- Source commit unknown if git unavailable: treat the export as lower-confidence advisory context and rerun in a normal Git checkout before sharing or using it.

## Operator Stop Conditions

Stop if:

- credentials, secrets, or account data are suspected in local reports;
- output path is outside the allowlisted `local_data/agent_context_exports/` directory;
- a network, account, Hermes, or runtime need arises;
- the intention changes from context export to report generation, strategy suggestion, or execution;
- tests or guards fail.

When a stop condition occurs, do not broaden this exporter workflow. Create or request a separate approved work package if the intended use has changed.
