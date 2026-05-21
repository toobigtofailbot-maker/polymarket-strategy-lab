# Agent Context Report Operator Runbook

## Status

- Runbook status: LOCAL_ANALYST_REPORT_OPERATOR_RUNBOOK
- Report generator status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR
- Context exporter status: LOCAL_OFFLINE_READ_ONLY_EXPORTER
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Live trading status: DISABLED
- Credentials status: NOT_USED

## Purpose

This runbook documents safe manual operation of the WP25 deterministic local/offline/read-only analyst report generator at `tools/polymarket/generate_agent_context_report.py`.

Reports are deterministic local summaries for human review only. They summarize a previously generated local context export and do not override repo truth, current merged state, current branch state, or later human review.

## Non-Goals / Forbidden Uses

This runbook is not:

- a Hermes setup guide;
- an LLM report generator;
- an agent runtime guide;
- a strategy recommendation;
- a trade proposal;
- a signal generator;
- a backtest;
- paper trading;
- live trading;
- scheduler or bot loop operation;
- account, credential, or private endpoint access.

The report must not be used to place orders, cancel orders, sign orders, submit orders, connect accounts, read credentials, query private endpoints, mutate configs, start a scheduler, start a bot loop, run a backtest, run paper trading, produce strategy recommendations, produce trade proposals, generate signals, estimate trade probabilities, recommend parameters, or make live trading decisions.

## Pre-Run Checklist

- Confirm the local repo is clean with `git status --short`.
- Run commands from the repository root.
- Confirm a prerequisite context export exists under `local_data/agent_context_exports/`.
- Confirm any report output path is under `local_data/agent_context_reports/`.
- Use default no-write mode first unless Markdown or JSON output is intentionally needed.
- Do not commit generated exports or reports.
- Do not feed reports into Hermes or an AI runtime unless a future approved work package allows it.
- Do not treat report content as a signal, recommendation, parameter recommendation, trade proposal, or trading instruction.

## Commands

Generate prerequisite context export:

```powershell
python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp26_context.local.json
```

Default no-write report summary:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp26_context.local.json
```

Help command:

```powershell
python tools/polymarket/generate_agent_context_report.py --help
```

Explicit Markdown report:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp26_context.local.json --markdown-out local_data/agent_context_reports/wp26_report.local.md
```

Explicit JSON report:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp26_context.local.json --json-out local_data/agent_context_reports/wp26_report.local.json
```

Explicit Markdown + JSON report:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp26_context.local.json --markdown-out local_data/agent_context_reports/wp26_report.local.md --json-out local_data/agent_context_reports/wp26_report.local.json
```

## Expected Default Console Summary

The default report command writes no file and prints a console summary with:

- report schema version;
- report mode;
- source context path;
- source commit;
- included artifact count;
- deferred item count;
- output written: no;
- safety line.

Expected safety line:

```text
safety: no network, no credentials, no orders, no Hermes runtime, no execution authority
```

## Output Validation

Validate JSON output using Python standard-library JSON tooling.

Windows PowerShell/cmd-compatible:

```powershell
python -m json.tool local_data/agent_context_reports/wp26_report.local.json > NUL
```

Cross-platform:

```sh
python -m json.tool local_data/agent_context_reports/wp26_report.local.json > /dev/null
```

Confirm Markdown output opens as text and contains required headings:

- Source Context Metadata
- Repo-Truth Status Snapshot
- Safety Boundary Summary
- Included Local Artifact Summary
- Deferred Item Summary
- Data Quality And Redaction Notes
- Staleness And Human Review Notes
- Forbidden Use Caveats
- Next-Step Boundary Statement

## Git Hygiene After Report Generation

Run:

```powershell
git status --short
```

Generated output must not be staged, tracked, or committed. Generated export/report output belongs under ignored `local_data/agent_context_exports/` and `local_data/agent_context_reports/`.

If generated output appears as staged or tracked, stop and do not commit. Confirm the path is under ignored `local_data/`, investigate ignore coverage, and keep the generated file out of staging.

## Interpreting The Report

- Source context metadata: identifies the input export path, export schema version, source commit, export mode, export timestamp, report timestamp, and report producer.
- Repo-truth status snapshot: summarizes safety and status values from the source context. Current repo truth still overrides the report if they differ.
- Safety boundary summary: shows live trading, credentials, execution, scheduler, bot loop, Hermes runtime dependency, agent execution authority, and autonomous-agent status.
- Included local artifact summary: gives deterministic counts by artifact type and provenance class. It is not a raw artifact dump.
- Deferred item summary: lists deterministic counts, statuses, and IDs from the source context so reviewers can see unresolved interpretation limits.
- Data quality/redaction notes: states the source context's local data quality source and whether raw large payloads, credentials, or private endpoint data were reported as included.
- Staleness and human review notes: repeats that repo truth and current merged state override stale exports and generated reports.
- Forbidden-use caveats: states that the report does not produce signals, recommendations, trades, parameter changes, backtests, paper-trading output, or live-trading decisions.
- Next-step boundary statement: confirms any future repo, runtime, configuration, polling, trading, deployment, or operations change requires human review and a separate approved Codex work package.

## Sharing / Future Advisory Use

Reports can become stale immediately after repo changes. Repo truth overrides report content.

Review reports before sharing or using them in future advisory workflows. Do not send reports to unapproved third-party tools if they contain local metadata or excerpts unless the user explicitly approves.

Future Hermes or AI consumption requires a separate approved work package or manual setup decision. This runbook does not install, configure, or authorize Hermes; Hermes remains NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY and is not a runtime dependency.

## Troubleshooting

- Missing context file: generate the prerequisite export with `python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp26_context.local.json`, then rerun the report command.
- Context path outside `local_data/agent_context_exports/`: rerun with `--context local_data/agent_context_exports/<name>.local.json`.
- Report output path outside `local_data/agent_context_reports/`: rerun with `--markdown-out local_data/agent_context_reports/<name>.local.md` or `--json-out local_data/agent_context_reports/<name>.local.json`.
- Path traversal rejected: remove `..` from the input or output path and keep paths under the allowlisted directories.
- JSON parse failure: discard the malformed local output, rerun the generator, and validate again with `python -m json.tool`.
- Source commit unknown or stale: treat the report as lower-confidence advisory context; rerun the context export and report generator in a normal current Git checkout before sharing or using the report.
- Generated output visible in `git status --short`: stop, do not stage or commit it, and confirm `local_data/` ignore behavior before continuing.
- Missing expected report headings: rerun the generator from a current context export and compare the Markdown against the required heading list above.

## Operator Stop Conditions

Stop if:

- credential, secret, private endpoint, wallet, token, or account data is suspected;
- input/output path outside allowlisted directories is needed or observed;
- a network, account, Hermes, or runtime need arises;
- the intention changes to strategy suggestion, signal generation, recommendation, parameter recommendation, or execution;
- tests/guards fail.

When a stop condition occurs, do not broaden this report workflow. Create or request a separate approved work package if the intended use has changed.
