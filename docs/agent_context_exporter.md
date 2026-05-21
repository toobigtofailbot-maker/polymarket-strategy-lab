# Agent Context Exporter

## Status

- Agent context exporter status: LOCAL_OFFLINE_READ_ONLY_EXPORTER
- Hermes runtime dependency status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent report generation status: NOT_STARTED
- Agent execution authority: FORBIDDEN

WP23 adds a local/offline/read-only JSON exporter only. It does not install Hermes, add an agent runtime, generate analyst reports, call network services, connect accounts, read credentials, create strategy signals, create trade proposals, backtest, paper trade, or touch live execution paths.

## Allowed Inputs

Default inputs are fixed, tracked repo-truth and policy docs:

- `docs/project_status.md`
- `docs/deferred_items_log.md`
- `docs/repo_truth_index.md`
- `docs/ai_agent_integration_policy.md`
- `docs/hermes_readonly_boundary.md`
- `docs/agent_context_export_schema.md`
- `docs/review_checklist.md`
- `docs/testing_requirements.md`

Optional local report metadata can be included only with an explicit flag and only from:

- `local_data/polymarket/reports/`
- `local_data/polymarket/exports/`
- `local_data/polymarket/polling_runs/`

`local_data/agent_context_exports/` is not self-ingested by default.

## Forbidden Inputs

The exporter must not read `.env`, secrets, credentials, private keys, wallet keys, tokens, account exports, private endpoint data, authenticated headers, or arbitrary paths.

## Output Location

The exporter writes JSON only when an explicit output path is provided under:

- `local_data/agent_context_exports/`

Generated output is ignored local data and must not be committed.

## Example Commands

Default no-write summary:

```powershell
python tools/polymarket/export_agent_context.py
```

Explicit local JSON output:

```powershell
python tools/polymarket/export_agent_context.py --out local_data/agent_context_exports/wp23_context.local.json
```

Optional local report metadata:

```powershell
python tools/polymarket/export_agent_context.py --include-local-report-metadata --out local_data/agent_context_exports/wp23_context.local.json
```

## Safety Boundaries

- no network calls;
- no credentials;
- no account connection;
- no order placement, cancellation, signing, or submission;
- no Hermes runtime or dependency;
- no agent runtime;
- no report generator;
- no scheduler, daemon, service loop, background worker, or bot loop;
- no execution authority.

Repo truth overrides exported context if they conflict. Any future use of the output for advisory AI or Hermes consumption requires human review and a later approved work package.
