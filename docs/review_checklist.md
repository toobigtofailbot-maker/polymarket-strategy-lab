# Review Checklist

## WP25 Local Read-Only Analyst Report Generator

- Report generator is local/offline/read-only?
- Input is restricted to `local_data/agent_context_exports/`?
- Output is restricted to `local_data/agent_context_reports/`?
- Default CLI writes nothing?
- No network/client/auth/trading/Hermes/LLM dependency added?
- No signals, strategy proposals, recommendations, or execution authority added?
- Markdown and JSON reports contain safety caveats and human-review requirements?
- Generated report output is not committed?
- WP21-D002 resolved only for the tested local/offline/read-only generator scope?
- WP20-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN?

## WP24 Read-Only Agent Context Exporter Operator Runbook

- Runbook exists and is indexed?
- Commands match existing exporter CLI?
- Default command is no-write?
- Explicit output stays under `local_data/agent_context_exports/`?
- Runbook has git hygiene steps?
- Runbook has JSON validation steps?
- Runbook states no Hermes runtime?
- Runbook states no report generator?
- Runbook states no network?
- Runbook states no credentials?
- Runbook states no execution authority?
- No runtime/exporter code changed unless explicitly justified?

## WP23 Local Read-Only Agent Context Exporter

- Exporter is local/offline/read-only?
- Default CLI writes nothing?
- Output is restricted to `local_data/agent_context_exports/`?
- No network/client/auth/trading/Hermes dependency added?
- No secrets, credentials, account exports, or `.env` reads?
- Required WP21 schema fields are present?
- Included artifacts have provenance, size, checksum, and generated-at metadata?
- Generated output is not committed?
- WP21-D001 resolved only for the tested local exporter scope?
- WP21-D002 remains OPEN?

## WP22 Codex Workflow Hardening And Report-Back Discipline

- Codex workflow docs exist and are indexed?
- `CODEX_START_HERE.md` exists and points to startup repo-truth files?
- PR template requires final report comment?
- PR body is not accepted as the only final report?
- Work package template has package class, exact changed-file set, stop triggers, and final report format?
- Validation matrix defines package-class validation?
- Project status update rules prevent stale WP wording?
- PR review checklist requires validation after final commit and generated-artifact guard after final commit?
- No runtime/exporter/Hermes/trading/dependency changes?
- No dependency or lock file changed?
- Deferred items remain accurate?

## WP21 Read-Only Agent Context Export Schema

- Schema docs are policy/schema-only?
- No exporter implementation added?
- No Hermes runtime or dependency added?
- No agent CLI, runtime, or report generator added?
- Schema includes provenance, redaction, staleness, and human-review fields?
- Schema forbids credentials, account data, order data, private endpoints, execution, scheduler, and bot-loop use?
- WP20-D002 resolved only for schema-contract scope?
- WP20-D001 remains OPEN?
- WP20-D003 remains OPEN?
- No runtime source under `src/` added for agents?
- No tools under `tools/agents/`, `tools/hermes/`, or agent context exporter paths added?
- No dependency file or lock file changed?

## WP20 AI-Agent Read-Only Boundary And Hermes Integration Policy

- Agent docs are policy-only?
- Hermes is not installed?
- Hermes is not a runtime dependency?
- No agent runtime, CLI, scheduler, daemon, memory store, context exporter, or report generator added?
- Fully autonomous trading agent is excluded for now?
- No credentials, authenticated client, account connection, order placement, order cancellation, signing, scheduler, bot loop, or dependency added?
- Allowed advisory roles are clear: read-only analysis, performance review, market research, strategy suggestion, and Codex / WP support?
- Manual user setup requirements are clear?
- Accepted agent suggestions require human review, approved config changes, or normal Codex work packages?
- No dependency file or lock file changed?
- No runtime source under `src/` added for agents?

## WP19 Guard-Aware Snapshot Quality Reports

- Quality reports are offline-only?
- Guarded-capture manifest counts are reported?
- Network-used unguarded manifests are warnings, not errors?
- Local WP16 policy caveat appears in reports?
- No network/client/auth/trading imports added to quality/reporting code?
- Deferred items remain open?
- WP8-D002 remains OPEN?
- WP16-D002 remains OPEN?
- WP17-D001 remains OPEN?
- WP17-D002 remains OPEN?
- WP10-D001 remains OPEN?
- WP10-D002 remains OPEN?
- WP12-D001 remains OPEN?
- WP12-D002 remains OPEN?

## WP18 Guarded Manual Snapshot Capture

- Snapshot capture requires `--allow-network`?
- Default snapshot capture behavior is offline?
- Guard consulted before Gamma market reads?
- Guard consulted before optional CLOB order-book reads?
- Guard denial prevents public client call?
- Capture remains finite, bounded, manual, and dev/local only?
- No scheduler/bot loop/daemon added?
- No strategy/trading/auth behavior added?
- Snapshot output remains under ignored `local_data/polymarket/snapshots/`?
- WP8-D002 remains OPEN?
- WP16-D002 remains OPEN?
- WP17-D001 remains OPEN?
- WP17-D002 remains OPEN?

## WP17 Manual Read-Only Polling Runner

- Manual runner requires `--allow-network`?
- Default runner behavior is offline?
- Runner is finite and exits?
- Runner uses WP16 `RateLimitGuard` before requests?
- Runner enforces per-run market/token bounds?
- Runner logs guard decisions and outcomes?
- No scheduler/bot loop/daemon added?
- No strategy/trade proposal/backtest/paper trading added?
- No credentials/auth/official-client runtime dependency added?
- WP8-D002 not falsely resolved?

- [ ] Repo-truth updated?
- [ ] `docs/project_status.md` updated?
- [ ] Remote Main Sync Gate passed?
- [ ] Local `main` equals `origin/main` before branch creation?
- [ ] Previous WP merge commit/files verified?
- [ ] Generated artifact guard passed before branch work?
- [ ] Generated artifact guard passed after setup?
- [ ] `.venv-security/` absent from changed files?
- [ ] `tools/.bin/` absent from changed files?
- [ ] No generated dependency files committed?
- [ ] No stacked WP branch?
- [ ] No manual local merge of prior WP branch?
- [ ] `docs/source_repo_registry.md` updated if relevant?
- [ ] `docs/deferred_items_log.md` added or updated for deferred material issues?
- [ ] Security tooling status updated?
- [ ] Deferred security-tool items updated?
- [ ] No unavailable security tool falsely marked as resolved?
- [ ] No runtime dependencies added without required security scans?
- [ ] Architecture boundaries reviewed?
- [ ] No live trading added?
- [ ] No secrets?
- [ ] Tests pass?
- [ ] Docs consistent?
- [ ] Scope respected?
- [ ] PR template completed?
- [ ] Human review required before merge?
- [ ] Gitleaks status updated in `docs/security_tooling_status.md`?
- [ ] Gitleaks scan result documented in `docs/gitleaks_secret_scan_gate.md`?
- [ ] `tools/.bin/` confirmed absent from staged/committed files?
- [ ] `security-scan-output/` confirmed absent from staged/committed files?
- [ ] WP3-D001 status accurately reflects actual scan evidence?
- [ ] No broad gitleaks suppressions added?
- [ ] Official-client sandbox isolated under `tools/polymarket/official_client_sandbox/` only?
- [ ] `.venv-official-client/` ignored and not committed?
- [ ] No official client dependency added to project files?
- [ ] No official client import under `src/`?
- [ ] No credentials/private keys/signing/authenticated methods?
- [ ] Optional network probe gated by `--allow-network`?
- [ ] Sandbox outputs ignored and not committed?
- [ ] Read-only adapter only? (WP8+)
- [ ] No authenticated client added? (WP8+)
- [ ] No credentials added? (WP8+)
- [ ] No POST/PUT/PATCH/DELETE in adapter? (WP8+)
- [ ] No order placement/cancellation/signing method added? (WP8+)
- [ ] Offline tests cover adapter behavior and boundaries? (WP8+)
- [ ] Optional network smoke test gated by `--allow-network`? (WP8+)
- [ ] Endpoint contract validation documented? (WP9+)
- [ ] Any network probe explicitly gated by `--allow-network`? (WP9+)
- [ ] No raw large payload committed? (WP9+)
- [ ] No credentials or private identifiers used? (WP9+)
- [ ] Rate-limit status not overclaimed? (WP9+)
- [ ] Deferred items WP8-D001 and WP8-D002 updated accurately? (WP9+)
- [ ] Endpoint verification metadata updated only where probe evidence supports it? (WP9+)
- [ ] Snapshot output path ignored? (WP10+)
- [ ] No snapshot files committed? (WP10+)
- [ ] Snapshot writer read-only (no network calls)? (WP10+)
- [ ] No automated polling or scheduler added? (WP10+)
- [ ] No scheduler or bot loop added? (WP10+)
- [ ] No raw large API payload committed? (WP10+)
- [ ] No CLOB /health dependency added? (WP10+)
- [ ] Rate-limit status not overclaimed? (WP10+)
- [ ] Snapshot capture tool requires --allow-network? (WP10+)
- [ ] Snapshot writer tests use tmp_path not real local_data/? (WP10+)
- [ ] Snapshot replay/catalog offline-only? (WP11+)
- [ ] No network calls added? (WP11+)
- [ ] No strategy signals or trade proposals added? (WP11+)
- [ ] No database added? (WP11+)
- [ ] No scheduler or bot loop added? (WP11+)
- [ ] No local_data files committed? (WP11+)
- [ ] Reader handles malformed/missing files safely? (WP11+)
- [ ] Catalog tests use tmp_path fixtures? (WP11+)
- [ ] Snapshot quality/reporting offline-only? (WP12+)
- [ ] No network calls added? (WP12+)
- [ ] No strategy signals/trade proposals/backtesting added? (WP12+)
- [ ] No database added? (WP12+)
- [ ] No scheduler/bot loop added? (WP12+)
- [ ] No local_data report files committed? (WP12+)
- [ ] Report writer refuses non-local_data paths? (WP12+)
- [ ] Quality tests use tmp_path fixtures? (WP12+)
- [ ] Snapshot dedup/export offline-only? (WP13+)
- [ ] No network calls added? (WP13+)
- [ ] No strategy signals/trade proposals/backtesting added? (WP13+)
- [ ] No database added? (WP13+)
- [ ] No scheduler/bot loop added? (WP13+)
- [ ] No local_data export files committed? (WP13+)
- [ ] Export writer refuses non-local_data paths? (WP13+)
- [ ] Dedup tests use tmp_path fixtures or synthetic local records? (WP13+)
- [ ] Conflicts are reported, not silently merged? (WP13+)
- [ ] Official client dependency not installed? (WP14+)
- [ ] No `py_clob_client_v2` imports? (WP14+)
- [ ] No private-key / wallet / API credential handling? (WP14+)
- [ ] No authenticated client setup? (WP14+)
- [ ] No order placement/cancellation/signing methods? (WP14+)
- [ ] Client decision docs updated? (WP14+)
- [ ] Archived old client marked avoid? (WP14+)
- [ ] V2 client marked candidate only? (WP14+)
- [ ] Polling policy added without polling runner? (WP16+)
- [ ] Rate-limit guard offline-only? (WP16+)
- [ ] No network calls added? (WP16+)
- [ ] No scheduler/bot loop added? (WP16+)
- [ ] No strategy signals/trade proposals added? (WP16+)
- [ ] No credentials/auth/client setup? (WP16+)
- [ ] WP8-D002 not falsely resolved? (WP16+)
- [ ] Future polling requires explicit-network and guard enforcement? (WP16+)
