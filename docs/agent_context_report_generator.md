# Agent Context Report Generator

## Status

- Report generator status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR
- Input: `local_data/agent_context_exports/`
- Output: `local_data/agent_context_reports/`
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Live trading status: DISABLED
- Credentials status: NOT_USED

## Purpose

WP25 adds deterministic local analyst report generation from a WP23-compatible context export. The report is advisory context for human review only.

The generator is local, offline, read-only, and non-LLM. It summarizes export metadata, source commit, repo-truth safety status, safety boundaries, included local artifact counts, deferred items, staleness policy, human-review requirements, and explicit no-trading/no-execution caveats.

Operator instructions for safe repeatable manual use are in `docs/agent_context_report_operator_runbook.md`.

## Non-Goals

The generator does not add:

- LLM integration;
- Hermes installation, configuration, runtime dependency, memory, or network use;
- agent runtime, command authority, scheduler, daemon, service loop, or bot loop;
- strategy recommendations;
- trade proposals;
- backtests;
- paper trading;
- live trading;
- account access, credential access, authenticated client access, or private endpoint access.

## Commands

First generate a context export:

```powershell
python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp25_context.local.json
```

Default no-write report summary:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp25_context.local.json
```

Explicit Markdown output:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp25_context.local.json --markdown-out local_data/agent_context_reports/wp25_report.local.md
```

Explicit Markdown and JSON output:

```powershell
python tools/polymarket/generate_agent_context_report.py --context local_data/agent_context_exports/wp25_context.local.json --markdown-out local_data/agent_context_reports/wp25_report.local.md --json-out local_data/agent_context_reports/wp25_report.local.json
```

Help:

```powershell
python tools/polymarket/generate_agent_context_report.py --help
```

## Output Validation

Confirm JSON parses using the Python standard library:

```powershell
python -m json.tool local_data/agent_context_reports/wp25_report.local.json
```

Confirm generated output remains ignored and uncommitted:

```powershell
git status --short
```

Files under `local_data/agent_context_reports/` are generated local output and must not be staged or committed.

## Report Interpretation

- Source context metadata: input export path, export schema version, source commit, export mode, export timestamp, report timestamp, and local producer.
- Repo-truth status snapshot: summarized safety statuses from the source context.
- Safety boundary summary: live trading, credentials, execution, scheduler, bot loop, Hermes runtime dependency, agent execution authority, and autonomous-agent status.
- Included local artifact summary: deterministic counts by artifact type and provenance class, not raw artifact expansion.
- Deferred item summary: deterministic counts and IDs from the source context.
- Data quality and redaction notes: whether raw payloads, credentials, or private endpoint data are reported as included by the source context.
- Staleness and human-review notes: repo truth and current merged state override stale exports and generated reports.
- Forbidden use caveats: explicit statement that the report does not produce signals, recommendations, trades, parameter changes, backtests, paper-trading output, or live-trading decisions.

## Stop Conditions

Stop if:

- the input context is missing or outside `local_data/agent_context_exports/`;
- output is outside `local_data/agent_context_reports/`;
- credential, account, private endpoint, or secret material is suspected;
- the intended use changes to strategy suggestion, signal generation, parameter recommendation, or execution;
- network, Hermes, account, credential, private endpoint, runtime, scheduler, or bot-loop behavior is needed;
- tests or guards fail.

Do not broaden this generator workflow. Use a separate approved work package for any changed intent.
