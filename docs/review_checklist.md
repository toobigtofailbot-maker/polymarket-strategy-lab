# Review Checklist

## WP35 Memory / Status Snapshot Helper Design

- Design doc `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` exists and is indexed in `docs/repo_truth_index.md`?
- Design doc states design status `DESIGN_ONLY` and future helper status `NOT_IMPLEMENTED`?
- Design doc explicitly states `Applies to: Claude Code and Codex`?
- Design doc states `NO_RUNTIME_CHANGE`, `NO_TOOL_IMPLEMENTATION`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, `NO_PROTECTED_BOUNDARY_CHANGE`, and `ADVISORY_ONLY_NOT_REPO_TRUTH`?
- Design doc includes authority model with explicit repo-truth-wins rule and cannot-override list?
- Design doc includes safe input sources allowlist?
- Design doc includes prohibited input sources list?
- Design doc includes intended future modes (stdout, snapshot file, compare/staleness, design-only)?
- Design doc includes intended future CLI shape (`tools/git/status_snapshot.py` and proposed flags)?
- Design doc includes intended output structure fields?
- Design doc includes sanitization and sensitive-output model?
- Design doc includes staleness model?
- Design doc includes snapshot lifecycle and storage policy?
- Design doc includes relationship to existing helpers?
- Design doc includes future implementation test plan?
- Design doc includes open design questions and recommended next WP?
- Design doc explicitly states the helper cannot replace repo truth, validation, security checks, human review, or final PR comment?
- No helper implementation added (`tools/git/status_snapshot.py` must not exist)?
- No tools/source/dependency/lock files changed?
- No generated snapshot output committed?
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` cross-references the design?
- `docs/ai/codex/README.md` cross-references the design?
- `docs/repo_truth_index.md` numbering is unique and sequential?
- `docs/deferred_items_log.md`, `docs/project_status.md`, `docs/review_checklist.md`, and `docs/testing_requirements.md` are updated?
- WP35-D001 added; WP28-D001, WP30-D001, WP32-D001, WP34-D001 remain OPEN?
- Focused tests pass (`tests/test_memory_status_snapshot_helper_design_docs.py`)?
- Full pytest passes after final commit?

## WP34 Code Index / Blast-Radius Helper Implementation

- Helper exists under `tools/git/code_blast_radius.py`?
- Helper is standard-library only (no subprocess, no requests/httpx/aiohttp/socket/openai/anthropic/langchain)?
- Helper is local/offline/read-only (no network calls, no command execution, no file mutation by default)?
- Helper does not import subprocess or os.system?
- Helper implements text and JSON output (`--format text|json`)?
- Helper default writes no file?
- Optional `--output` restricted to repo-relative `local_data/code_blast_radius/`?
- Absolute and traversal output paths rejected with exit 2?
- No persistent index is implemented?
- Excluded/sensitive paths (`.git/`, `local_data/`, `.venv-*`, `.env`, credential files) are skipped?
- Protected/dependency/generated/package-class warnings are present and tested?
- `--fail-on-protected-hit` exits 1 when protected hits detected?
- Exit 0 for success, 1 for protected hit + flag, 2 for usage error?
- `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md` exists and is indexed in `docs/repo_truth_index.md`?
- `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` updated with WP34 implementation decision section?
- `docs/repo_truth_index.md` numbering is unique and sequential?
- `docs/deferred_items_log.md`, `docs/project_status.md`, `docs/review_checklist.md`, and `docs/testing_requirements.md` are updated?
- WP30-D002 resolved; WP28-D001, WP30-D001, WP32-D001 remain OPEN; WP34-D001 added?
- 123+ focused tests pass in `tests/tools/git/test_code_blast_radius.py`?
- Full pytest passes after final commit?
- No runtime source under `src/` added or modified?
- No dependency or lock files changed?
- No Hermes/LLM/provider/network/credential behavior added?
- No strategy/trading/execution behavior added?
- No generated artifacts committed?

## WP33 Code Index / Blast-Radius Helper Design

- Design doc `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` exists and is indexed in `docs/repo_truth_index.md`?
- Design doc states design status `DESIGN_ONLY` and future helper status `NOT_IMPLEMENTED`?
- Design doc explicitly applies to Claude Code and Codex?
- Design doc states `NO_RUNTIME_CHANGE`, `NO_TOOL_IMPLEMENTATION`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, and `NO_PROTECTED_BOUNDARY_CHANGE`?
- Design doc includes intended future modes: on-demand scan, snapshot/index file, query, and design-only?
- Design doc says first implementation should prefer on-demand scan?
- Design doc includes intended future CLI shape for `tools/git/code_blast_radius.py` and required flags?
- Design doc includes relationship model: direct references, naming heuristics, repo-truth relationships, protected/sensitive relationships, and confidence high/medium/low?
- Design doc includes package-class awareness warnings?
- Design doc includes stale-index model?
- Design doc includes excluded paths and sensitive-content model?
- Design doc preserves validation and direct inspection?
- Design doc includes future implementation test plan, open design questions, and recommended next WP?
- Focused design doc test exists at `tests/test_code_index_blast_radius_helper_design_docs.py`?
- `docs/repo_truth_index.md` numbering is unique and sequential?
- `docs/deferred_items_log.md`, `docs/review_checklist.md`, and `docs/testing_requirements.md` are updated?
- No implementation path exists: no `tools/git/code_blast_radius.py`, no `tools/git/code_index.py`, no `tools/code_index*`, no `tools/blast_radius*`?
- No tracked `local_data/code_index/` path exists?
- No dependency or lock files changed?
- No Hermes/LLM/provider/network/credential behavior added?
- No strategy/trading/execution behavior added?
- No generated artifacts committed?

## WP32 Validation Output Summary Helper Implementation

- Helper exists under `tools/validation/validation_output_summary.py`?
- Helper is stdlib-only (no subprocess, requests, httpx, aiohttp, websockets, openai, anthropic, hermes imports)?
- Helper is local, offline, and read-only (no network calls, no file mutation, no command execution)?
- Helper does not execute `--command` (display/evidence only)?
- Helper has text and JSON output (`--format text|json`)?
- Helper default writes no file?
- Optional output restricted to repo-relative `local_data/validation_summaries/`?
- Input files restricted to repo-relative `local_data/validation_summaries/inputs/`?
- Input/output absolute paths and traversal (`..`) are rejected with exit 2?
- Helper does not replace validation (validation reminder in all output)?
- Helper parses pytest pass/fail/error/warning output?
- Helper parses artifact guard output (PASS/FAIL)?
- Helper parses Remote Main Sync Gate output (PASS/FAIL)?
- Helper handles security tool availability without treating unavailable/skipped as PASS?
- Helper classifies PASS/FAIL/SKIPPED/UNAVAILABLE/PARTIAL/ERROR correctly?
- Helper detects and redacts obvious secret-like output?
- Helper produces concise failure snippets and truncation flags?
- Helper includes validation reminder and raw log retention note in all output?
- 73+ focused tests pass in `tests/tools/validation/test_validation_output_summary.py`?
- No runtime source under `src/` added or modified?
- No unrelated `tools/` files modified?
- No dependency or lock files changed?
- No generated artifacts committed?
- No Hermes/LLM/agent runtime/credentials/network/trading behavior added?
- `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md` exists and is indexed in `docs/repo_truth_index.md`?
- `docs/repo_truth_index.md` has no duplicate numeric prefixes and numbering is sequential?
- WP31-D001 resolved; WP28-D001, WP30-D001, WP30-D002 remain OPEN?
- WP32-D001 added (runner mode forbidden/unimplemented)?
- WP20-D001, WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, WP17-D002 unchanged?

## WP31 Validation Output Summary Helper Design

- Design doc `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` exists and is indexed in `docs/repo_truth_index.md`?
- Design doc states design status `DESIGN_ONLY` and future helper status `NOT_IMPLEMENTED`?
- Design doc explicitly applies to Claude Code and Codex?
- Design doc states stdlib/local/offline/read-only/no-network future implementation constraints?
- Design doc includes intended modes (parser, metadata, future runner), with first implementation preferring parser/metadata?
- Design doc includes intended future CLI shape (`--command`, `--exit-code`, `--check-type`, `--stdout-file`, `--stderr-file`, `--from-stdin`, `--format text|json`, `--max-failure-lines`, `--tool-availability`, `--output`, `--fail-on-missing-required-evidence`)?
- Design doc includes intended input sources (command string, exit code, stdout/stderr, pytest lines, artifact guard, sync gate, security tool availability, diff/scope helper)?
- Design doc includes intended output structure (all required fields)?
- Design doc includes status classification rules (PASS/FAIL/UNAVAILABLE/SKIPPED/PARTIAL/ERROR)?
- Design doc includes failure-snippet and truncation rules?
- Design doc explicitly says no validation weakening and no validation replacement?
- Design doc includes security and sensitive-output model?
- Design doc includes package-class usage guidance?
- Design doc includes future implementation test plan?
- Design doc includes open design questions and recommended next WP?
- `TOKEN_EFFICIENCY_OPERATING_MODEL.md`, `CONCISE_REPORTING_RULES.md`, `VALIDATION_MATRIX.md`, and `docs/ai/codex/README.md` cross-reference the new design doc?
- No helper implementation added (no `tools/validation/validation_output_summary.py` or any impl)?
- No tools/source/dependency/lock files changed?
- WP31-D001 added; WP28-D001, WP30-D001, WP30-D002 remain OPEN?

## WP30 Local Diff And Scope Summary Helper Implementation

- Helper exists under `tools/git/diff_scope_summary.py`?
- Helper is stdlib-only, local, offline, and read-only?
- Helper has text and JSON output (`--format text|json`)?
- Helper default writes no file?
- Optional output restricted to `local_data/diff_scope_summaries/`?
- Output path traversal and outside-directory output are rejected with exit 2?
- Helper does not replace validation (validation reminder in all output)?
- Dependency/lock-file changes are flagged?
- Generated-artifact/local output paths are flagged?
- Protected-path hits (builtin + `--forbidden-prefix`) are flagged?
- Out-of-scope files are flagged (when allowed scope is declared)?
- Package-class warnings are emitted for misalignment patterns?
- Default exit 0 with warnings present; `--fail-on-warning` exits 1?
- Usage/config errors exit 2?
- 79 focused tests pass in `tests/tools/git/test_diff_scope_summary.py`?
- No runtime source under `src/` added or modified?
- No unrelated `tools/` files modified?
- No dependency or lock files changed?
- No generated artifacts committed?
- No Hermes/LLM/agent runtime/credentials/network/trading behavior added?
- `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md` exists and is indexed in `docs/repo_truth_index.md`?
- `docs/repo_truth_index.md` has no duplicate numeric prefixes?
- WP29-D001 resolved; WP28-D001 remains OPEN?
- WP20-D001, WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, WP17-D002 unchanged?

## WP29 Local Diff And Scope Summary Helper Design

- Design doc `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` exists and is indexed in `docs/repo_truth_index.md`?
- Design doc states design status `DESIGN_ONLY` and future helper status `NOT_IMPLEMENTED`?
- Design doc is explicitly stdlib-only, local, offline, and read-only?
- Design doc includes intended CLI shape (`--base`, `--head`, `--package-class`, `--allowed-file`, `--allowed-prefix`, `--forbidden-prefix`)?
- Design doc includes intended input sources (git diff commands, protected-path docs, WP-provided path lists)?
- Design doc includes intended output modes (stdout default, optional JSON, no file by default)?
- Design doc includes protected-path model (flag not modify; no automatic failure; dependency/lock/generated artifact highlights)?
- Design doc includes package-class warnings (docs-only, design, read-only public-data, live-trading)?
- Design doc includes exit status design (0/1/2; cannot bypass validation)?
- Design doc includes future implementation test plan (fixture-based, protected path, dependency/lock, generated artifact, Windows path)?
- Design doc includes open design questions and recommended next WP?
- No helper implementation added (no `tools/git/diff_scope_summary.py`, no helper source under `tools/` or `src/`)?
- No tools/source/dependency/lock files added or modified beyond allowed WP29 scope?
- `TOKEN_EFFICIENCY_OPERATING_MODEL.md` and `docs/ai/codex/README.md` cross-reference the new design doc?
- WP28-D001 remains OPEN; WP29-D001 added?
- WP20-D001, WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, WP17-D002 remain unchanged?

## WP28 Codex/Claude Code Token Efficiency Operating Model Lock

- Token-efficiency operating model doc exists at `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`?
- Concise reporting rules doc exists at `docs/ai/codex/CONCISE_REPORTING_RULES.md`?
- Reusable WP prompt blocks doc exists at `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`?
- New docs indexed in `docs/repo_truth_index.md`?
- Token-efficiency doc explicitly applies to Codex and Claude Code?
- Token-efficiency doc explicitly prohibits validation weakening?
- Token-efficiency doc explicitly preserves protected boundaries?
- Concise reporting keeps mandatory final PR comment and validation evidence?
- Reusable prompt blocks do not replace package-specific WP fields?
- Existing workflow docs (`AGENTS.md`, `CODEX_START_HERE.md`, `docs/ai/codex/README.md`, `docs/codex_execution_guidelines.md`, `docs/work_package_template.md`) cross-reference the new guidance?
- PR template retains all existing required checks?
- No runtime/source/tooling implementation added?
- No dependency or lock files changed?
- WP20-D001, WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, WP17-D002 remain unchanged?

## WP27 Agent/Hermes Manual Setup Decision Record

- Decision record exists and is indexed in `docs/repo_truth_index.md`?
- Decision state is explicit (DECISION_DEFERRED_PENDING_USER_SELECTION or equivalent)?
- Hermes remains not installed, not configured, and not a runtime dependency?
- Agent runtime remains not started?
- Manual user decisions are listed in the decision record?
- Future approval gates are listed in the decision record?
- Codex-safe future preparation items are listed?
- Forbidden automatic actions are listed?
- No runtime source under `src/` is added or modified?
- No `tools/agents/`, `tools/hermes/`, `agent_runtime/`, or `agent_memory/` directory is added?
- No dependency file, package manager file, or lock file is changed?
- No credentials, `.env`, API keys, private keys, or tokens are added?
- No network access, provider SDK, or LLM dependency is added?
- No memory/persistence, command execution, or scheduler/bot loop is added?
- WP20-D001 is updated to READY_FOR_MANUAL_SETUP_DECISION but not marked RESOLVED?
- WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN?

## WP26 Read-Only Analyst Report Operator Runbook

- Report operator runbook exists and is indexed?
- Commands match existing exporter/report-generator CLIs?
- Default report command is no-write?
- Explicit outputs stay under `local_data/agent_context_reports/`?
- Runbook has JSON and Markdown validation steps?
- Runbook has git hygiene steps?
- Runbook states no Hermes runtime, no LLM, no agent runtime, no strategy recommendations, no trade proposals, no signals, no network, no credentials, no execution authority?
- No runtime code changed unless explicitly justified?
- WP25-D001 resolved only for the tested local/offline/read-only report runbook scope?
- WP20-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN?

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
