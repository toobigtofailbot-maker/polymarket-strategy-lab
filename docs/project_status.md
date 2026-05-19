# Project Status

- Current phase: WP13 - Snapshot Deduplication And Catalog Export Hardening
- Repo state: offline snapshot deduplication/catalog export hardening on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8, WP9, WP10, WP10-Follow-up, WP11, WP12
- Current branch: `wp13-snapshot-deduplication-catalog-export-hardening`
- API integration status: READ_ONLY_PUBLIC_DATA_LOCAL_EXPORTS
- Runtime dependency integration status: NOT STARTED
- Live trading status: DISABLED
- Credentials status: NOT USED
- Execution status: NOT STARTED
- Storage status: LOCAL_FILE_SNAPSHOTS_ONLY
- Catalog status: IN_MEMORY_LOCAL_ONLY
- Reporting status: LOCAL_REPORTS_ONLY
- Export status: LOCAL_EXPORTS_ONLY
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates; WP10 adds local file-based snapshot persistence (JSONL) under src/data_layer/polymarket/ and manual capture tool under tools/polymarket/; WP11 adds offline snapshot reader, in-memory market catalog, replay helpers, and manual inspection CLI under src/data_layer/polymarket/ and tools/polymarket/; WP12 adds offline snapshot quality gates, catalog quality metrics, and local report generation under src/data_layer/polymarket/ and tools/polymarket/; WP13 adds offline snapshot deduplication and sanitized local catalog exports under src/data_layer/polymarket/ and tools/polymarket/
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); WP8-D002 remains OPEN (rate-limit not confirmed); WP9-D001 OPEN (CLOB /health path unknown); WP9-D002 READY_FOR_WP (parser updated, snapshot writer uses it); WP10-D001 OPEN (snapshot schema not production-stable); WP10-D002 OPEN (snapshot output not database-backed); WP11-D001 OPEN (catalog not yet database-backed); WP11-D002 OPEN (replay is inspection-only, not backtest-ready); WP12-D001 OPEN (quality gates research-only); WP12-D002 OPEN (reports not dashboard-backed); WP13-D001 OPEN (catalog exports local-file only); WP13-D002 OPEN (deduplication policy research-only); gitleaks READY_FOR_WP (scan passed); semgrep and pip-audit READY_FOR_WP (require .venv-security/ restoration).
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed); WP10 local_data/ added to .gitignore (snapshot files must not be committed); WP11 catalog output also under ignored local_data/; WP12 local reports output under ignored local_data/polymarket/reports/ only; WP13 local catalog exports output under ignored local_data/polymarket/exports/ only.
- Next intended WP: WP14 - Official Python Client Dependency Decision And Boundary Review, if local data tooling is stable enough. Or WP14 - Snapshot Deduplication Follow-Up, if dedup/export issues remain.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
- CLOB /health correct endpoint path unknown (WP9-D001).
- Rate-limit policy not confirmed (WP8-D002).
