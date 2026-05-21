# Project Status

- Current phase: WP22 - Codex Workflow Hardening And Report-Back Discipline
- Repo state: Codex workflow hardening on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8, WP9, WP10, WP10-Follow-up, WP11, WP12, WP13, WP14, WP15, WP16, WP17, WP18, WP19, WP20, WP21
- Current branch: `wp22-codex-workflow-hardening-report-discipline`
- API integration status: STDLIB_READ_ONLY_PUBLIC_DATA_ACTIVE; MANUAL_EXPLICIT_NETWORK_POLLING_RUNNER_DEV_ONLY; MANUAL_GUARD_ENFORCED_SNAPSHOT_CAPTURE_DEV_ONLY
- Runtime dependency integration status: NOT_STARTED_FOR_NEW_RUNTIME_DEPENDENCIES
- Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME
- Live trading status: DISABLED
- Credentials status: NOT_USED
- Execution status: NOT_STARTED
- Official Python client status: SANDBOX_CANDIDATE_ONLY_NOT_PROJECT_DEPENDENCY
- Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP
- AI-agent layer status: POLICY_ONLY_NOT_IMPLEMENTED
- Agent context export schema status: POLICY_SCHEMA_ONLY_NOT_IMPLEMENTED
- Agent context exporter status: NOT_STARTED
- Agent report generation status: NOT_STARTED
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Fully autonomous trading agent status: EXCLUDED_FOR_NOW
- Polling status: MANUAL_EXPLICIT_NETWORK_BOUNDED_RUNNER_DEV_ONLY; SNAPSHOT_CAPTURE_MANUAL_EXPLICIT_NETWORK_BOUNDED_GUARD_ENFORCED_DEV_ONLY
- Scheduler status: NOT_STARTED
- Bot loop status: NOT_STARTED
- Sandbox status: OFFICIAL_CLIENT_SANDBOX_DEV_ONLY; DEV_ONLY_READ_ONLY_NO_CREDENTIALS
- Storage status: LOCAL_FILE_SNAPSHOTS_ONLY
- Catalog status: IN_MEMORY_LOCAL_ONLY
- Reporting status: LOCAL_REPORTS_ONLY
- Export status: LOCAL_EXPORTS_ONLY
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates; WP10 adds local file-based snapshot persistence (JSONL) under src/data_layer/polymarket/ and manual capture tool under tools/polymarket/; WP11 adds offline snapshot reader, in-memory market catalog, replay helpers, and manual inspection CLI under src/data_layer/polymarket/ and tools/polymarket/; WP12 adds offline snapshot quality gates, catalog quality metrics, and local report generation under src/data_layer/polymarket/ and tools/polymarket/; WP13 adds offline snapshot deduplication and sanitized local catalog exports under src/data_layer/polymarket/ and tools/polymarket/; WP14 adds official Python client dependency decision and boundary review docs/tests only; WP15 adds official-client sandbox tooling under tools/polymarket/official_client_sandbox/ only; WP16 adds offline polling policy and local rate-limit guard only; WP17 adds a manual finite explicit-network read-only polling runner only; WP18 adds guard-enforced manual snapshot capture using WP16 policy before Gamma and optional CLOB reads; WP19 adds offline guard-aware quality/reporting for WP18 guarded capture manifests; WP20 adds policy/docs/tests only for advisory AI-agent and Hermes read-only boundaries; WP21 adds schema/docs/tests only for a future local read-only agent context export; WP22 adds persistent Codex workflow guidance, templates, checklists, and tests only.
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); WP8-D002 remains OPEN (rate-limit not confirmed); WP9-D001 OPEN (CLOB /health path unknown); WP9-D002 READY_FOR_WP (parser updated, snapshot writer uses it); WP10-D001 OPEN (snapshot schema not production-stable); WP10-D002 OPEN (snapshot output not database-backed); WP11-D001 OPEN (catalog not yet database-backed); WP11-D002 OPEN (replay is inspection-only, not historical-simulation-ready); WP12-D001 OPEN (quality gates research-only); WP12-D002 OPEN (reports not dashboard-backed); WP13-D001 OPEN (catalog exports local-file only); WP13-D002 OPEN (deduplication policy research-only); WP14-D001 OPEN (official Python V2 client not installed or audited as dependency); WP14-D002 BLOCKED (authenticated CLOB client integration blocked pending credential/key/security boundary WP); WP14-D003 READY_FOR_WP (isolated read-only sandbox exists and is tested); WP15-D001 OPEN (sandbox API shape not fully confirmed); WP15-D002 OPEN (official client package not audited as project dependency); WP16-D001 RESOLVED for manual bounded runner scope; WP16-D002 OPEN (rate-limit budgets are conservative local policy, not confirmed venue limits); WP17-D001 OPEN (automated/scheduled polling not implemented); WP17-D002 OPEN (runner remains dev-only/manual because venue rate limits are unconfirmed); WP18 updates snapshot capture guard enforcement without resolving WP8-D002, WP16-D002, WP17-D001, WP17-D002, WP10-D001, or WP10-D002; WP19 updates offline local reports to summarize guarded-capture provenance without resolving WP8-D002, WP16-D002, WP17-D001, WP17-D002, WP10-D001, WP10-D002, WP12-D001, or WP12-D002; WP20 records advisory-agent policy and adds WP20-D001, WP20-D002, and WP20-D003 without resolving any prior deferred items; WP21 resolves WP20-D002 for schema-only scope and adds WP21-D001 and WP21-D002; WP22 updates workflow discipline without resolving exporter, report generator, Hermes, rate-limit, scheduler, snapshot, catalog, quality, or dashboard deferred items; gitleaks READY_FOR_WP (scan PASS in WP22); semgrep and pip-audit READY_FOR_WP but unavailable/skipped in WP22 because `.venv-security/` is absent.
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed); WP10 local_data/ added to .gitignore (snapshot files must not be committed); WP11 catalog output also under ignored local_data/; WP12 local reports output under ignored local_data/polymarket/reports/ only; WP13 local catalog exports output under ignored local_data/polymarket/exports/ only; WP15 adds ignored .venv-official-client/, official-client-sandbox-output/, and local_data/polymarket/official_client_sandbox/; WP16 optional polling policy output remains under ignored local_data/polymarket/polling_policy/; WP17 optional polling-run summaries remain under ignored local_data/polymarket/polling_runs/.
- Next intended WP: WP23 - Local Read-Only Agent Context Exporter, if WP22 succeeds and remains local/offline/no-Hermes-runtime. Or WP23 - Codex Workflow Hardening Follow-Up, if workflow/test gaps remain.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters. The Python V2 client is candidate-only and not installed in WP14/WP15/WP16.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
- CLOB /health correct endpoint path unknown (WP9-D001).
- Rate-limit policy not confirmed (WP8-D002).
- Automated, scheduled, or higher-frequency public market-data polling requires a future approved WP with authoritative rate-limit evidence and repo-truth updates.
- AI-agent and Hermes integrations remain advisory-only. WP21 defines a schema-only agent context export contract, but any future exporter implementation, report generation, runtime selection, provider choice, command approval, network permission, memory policy, or installation requires future human approval and repo-truth work packages.
