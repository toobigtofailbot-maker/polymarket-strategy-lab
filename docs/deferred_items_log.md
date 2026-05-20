# Deferred Items Log

## Purpose

This log tracks material issues, unavailable tools, unresolved dependency decisions, blocked security checks, and postponed decisions that are intentionally deferred from the current work package. Deferred items remain visible repo truth until they are resolved, superseded, or promoted into a later approved work package.

Research and workbench artifacts do not gain runtime authority because they are listed here.

## Status Definitions

- OPEN: known item requiring triage or action.
- BLOCKED: cannot proceed until an external dependency, decision, or approval is available.
- DEFERRED: intentionally postponed and not blocking the current work package.
- READY_FOR_WP: ready to be scheduled into a specific future work package.
- RESOLVED: completed and no longer blocking.
- SUPERSEDED: replaced by a later decision, item, or repo-truth document.

## Priority Definitions

- P0: blocks safety or repo integrity.
- P1: blocks runtime/API/dependency integration.
- P2: blocks production readiness.
- P3: useful but not blocking.

## Deferred Item Table

| ID | Item | Status | Priority | Reason | Required before | Resolution condition |
|---|---|---|---|---|---|---|
| WP3-D001 | Security tool unavailable: gitleaks | READY_FOR_WP | P1 | WP7 downloaded gitleaks v8.27.2 into ignored `tools/.bin/`; checksum verified; `gitleaks git --redact` scan passed with no findings. Must be rerun before relevant runtime/dependency/copy/API/live work. | External dependency runtime integration, vendoring, live execution. | Rerun gitleaks before each relevant future WP; update scan result and status each time. |
| WP3-D002 | Security tool unavailable: semgrep | READY_FOR_WP | P1 | WP5 installed and verified Semgrep in project-local `.venv-security/`; repo scan passed. It must be rerun immediately before relevant runtime/dependency/copy work. | External dependency runtime integration, copied code, live execution. | Install and verify semgrep or an approved equivalent, then run relevant static checks before runtime use. |
| WP3-D003 | Node dependency audit unavailable: npm / npm audit | DEFERRED | P1 | Unavailable during WP2; WP4 found no `package.json`, so npm audit was not applicable, but this does not resolve the future Node/TypeScript audit gate. | TypeScript client integration or dashboard/runtime dependency installation. | Make npm available and document audit results, or document an approved alternative. |
| WP3-D004 | Python dependency audit unavailable: pip-audit | READY_FOR_WP | P1 | WP5 installed and verified pip-audit in project-local `.venv-security/`; current repo audit passed. It must be rerun immediately before Python dependency integration. | Python client integration or runtime Python dependency installation. | Make pip-audit available and document audit results, or document an approved alternative. |
| WP3-D005 | Rust dependency audit unavailable: cargo audit | DEFERRED | P2 unless Rust is selected, then P1 | Unavailable during WP2; WP4 and WP5 found no `Cargo.toml` or `Cargo.lock`, so cargo audit was not applicable, but Rust is not permanently excluded from runtime scope. | Any Rust runtime component. | Make cargo audit available and document audit results, or explicitly exclude Rust from runtime scope. |
| WP3-D006 | Relayer clients license unresolved | DEFERRED | P1 if relayer integration is proposed | WP2 found no license file in the shallow clone for builder-relayer clients. | Any relayer runtime dependency. | Clarify the license and approve it in repo truth. |
| WP3-D007 | Official CLOB client dependency security review pending | DEFERRED | P1 | WP2 marked TypeScript and Python V2 clients as core dependency candidates, not approved runtime dependencies. WP8 uses standard library only and defers the official client decision. | API integration. | Complete version pinning, dependency audit, adapter boundary review, and security review in a later work package. |
| WP8-D001 | Polymarket public endpoint contract not confirmed | READY_FOR_WP | P2 | WP9 controlled probe confirmed: Gamma /markets (HTTP 200), Gamma /markets/{id} (HTTP 200, integer id required), CLOB /book (HTTP 200, bids/asks confirmed). CLOB /health returned HTTP 404 and remains unverified. Parser updated for JSON-encoded clobTokenIds and outcomes fields. Confirmed endpoints are sufficient for limited dev/paper read-only use. WP10 uses only these three confirmed endpoints. | Production use of CLOB /health; automated scanning beyond dev/paper scope. | Remaining: confirm CLOB /health path or remove it from the adapter; confirm rate-limit policy (WP8-D002); confirm identifier stability. |
| WP8-D002 | Polymarket public endpoint rate-limit policy not confirmed | OPEN | P2 | Rate-limit policy for public Gamma and CLOB endpoints is not confirmed. WP9 single low-volume probe (limit=3) returned no 429 responses and no rate-limit headers were observed. A single low-volume probe does not confirm sustained or burst rate limits. WP10 does not add automated polling; manual capture uses small limits (default 3 markets). | Automated or frequent market scanning. | Document confirmed rate-limit policy before scheduling automated adapter calls. |
| WP9-D001 | CLOB /health endpoint not found at expected path | OPEN | P3 | WP9 probe returned HTTP 404 for GET https://clob.polymarket.com/health. The correct CLOB health/status endpoint path is unknown. Not blocking for read-only market data use but prevents service health monitoring. WP10 does not use CLOB /health. | Service health monitoring or CLOB API availability check. | Identify the correct CLOB health endpoint path from authoritative docs or by probing alternate paths in a future WP. |
| WP9-D002 | clobTokenIds and outcomes are JSON-encoded strings not Python lists | READY_FOR_WP | P2 | WP9 discovered that the Gamma API returns clobTokenIds and outcomes as JSON-encoded strings (e.g. '["token1","token2"]'), not Python lists. WP9 updates the adapter parser. WP10 snapshot capture uses parse_market_summary() which handles JSON-encoded string fields correctly; verified by offline tests in test_snapshot_capture_tool.py. | Snapshot persistence (WP10+). | RESOLVED for WP10 scope: snapshot writer correctly handles JSON-encoded string fields via the updated parser. |
| WP10-D001 | Snapshot persistence schema not yet production-stable | OPEN | P2 | WP10 snapshot record schema (MarketMetadataSnapshotRecord, OrderBookSnapshotRecord, SnapshotManifest) is research-only and may change in later WPs. Records written in WP10 may not be forward-compatible with future schema versions. | Production use of snapshot data, database migration, or schema-dependent tooling. | Declare schema stable in a later WP after sufficient real-data validation. |
| WP10-D002 | Snapshot output not yet database-backed | OPEN | P3 | WP10 uses JSONL files only. No database, indexing, or query capability exists. JSONL append mode has no deduplication or conflict resolution. | Queryable market catalog, snapshot replay, or research tooling requiring structured access. | A future WP may migrate to SQLite or another local database after schema stabilization and explicit scope approval. |
| WP11-D001 | Market catalog not yet persisted or database-backed | OPEN | P3 | WP11 builds an in-memory catalog from JSONL snapshot files. The catalog is not persisted between runs and has no indexing or query capability beyond in-memory dicts. | Persistent queryable market catalog or cross-session research tooling. | A future WP may add SQLite or another local database after WP10-D001 schema stabilization and explicit scope approval. |
| WP11-D002 | Snapshot replay is inspection-only, not backtest-ready | OPEN | P3 | WP11 replay iterates over captured snapshot records chronologically. It does not provide tick-level price simulation, position tracking, order filling, or strategy evaluation. | Research or strategy backtesting requiring price simulation or order execution replay. | A future WP may add a dedicated backtest scaffold after strategy module scope is defined and safety gates are in place. |
| WP12-D001 | Snapshot quality gates are research-only and not CI-blocking for production | OPEN | P3 | WP12 adds offline quality gates for local research reports, but does not promote those gates into mandatory CI or production-readiness policy. | Any production use of snapshot quality gates or CI enforcement based on snapshot quality. | A future WP explicitly defines quality gate enforcement policy and updates CI/review rules. |
| WP12-D002 | Local reports are not dashboard-backed | OPEN | P3 | WP12 writes sanitized local Markdown/JSON reports only under ignored local_data/ when explicitly requested. No dashboard, monitoring service, scheduler, or database-backed reporting stack is added. | Dashboard-backed reporting or operational monitoring. | A future approved WP adds a dashboard/reporting stack after scope, storage, and safety boundaries are documented. |
| WP13-D001 | Catalog exports are local-file only and not database-backed | OPEN | P3 | WP13 writes sanitized catalog exports only under ignored local_data/ when explicitly requested. No database, indexing, migration, dashboard, or query service is added. | Persistent queryable catalog, database-backed reporting, or operational export service. | A future approved WP adds database-backed catalog/reporting after schema stability, storage requirements, and safety boundaries are documented. |
| WP13-D002 | Deduplication policy is research-only and not production canonical | OPEN | P3 | WP13 removes exact duplicate local records and reports conflicts for research inspection, but does not declare canonical production deduplication or conflict-resolution policy. | Production use of deduplicated snapshots or canonical historical datasets. | A future approved WP defines canonical deduplication policy, schema compatibility rules, and production validation requirements. |
| WP14-D001 | Official Python V2 client not installed or audited as dependency | OPEN | P1 | WP14 classifies `py-clob-client-v2` as `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION` but does not install, pin, audit, or integrate it. | Any official Python client dependency installation or runtime integration. | A future approved WP pins the package, restores/runs required security checks, documents audit results, and keeps evaluation isolated/read-only first. |
| WP14-D002 | Authenticated CLOB client integration remains blocked pending credential/key/security boundary WP | BLOCKED | P0 | Official client L1/L2 behavior requires private-key signing and API credentials; WP14 adds no credential, key, auth, signing, account, trade, or order path. | Any authenticated client, credential/private-key handling, signing, account/trade query, order placement, or cancellation. | A future approved credential/key/security boundary WP defines custody, secret handling, auth scope, risk/execution boundaries, and live-trading authorization constraints. |
| WP14-D003 | Official client read-only sandbox implemented for dev-only evaluation | READY_FOR_WP | P2 | WP15 adds an isolated sandbox under `tools/polymarket/official_client_sandbox/`, ignored `.venv-official-client/` handling, explicit-network-only probing, and tests proving no runtime/auth/trading boundary violation. | Any follow-up official-client public-data experiment. | A future approved WP runs a pinned sandbox package inspection/probe or decides to keep the existing stdlib adapter as the only active path. |
| WP15-D001 | Official client sandbox API shape not fully confirmed | OPEN | P2 | WP15 provides offline inspection and optional public probe tooling, but the package was not installed in the required default command path and no pinned-version API shape was promoted to repo truth. | Any future official-client adapter design or runtime dependency proposal. | Install an explicit sandbox version, run inspection and optional public read-only probe, document method compatibility, and keep auth/order behavior excluded. |
| WP15-D002 | Official client package not audited as project dependency | OPEN | P1 | WP15 does not add, pin, or audit `py-clob-client-v2` as a project dependency. Sandbox-only local installation, if performed, does not satisfy project dependency review. | Any official-client project dependency or runtime integration. | A future approved WP pins the dependency, restores/runs required security tooling including pip-audit or approved equivalent, and records dependency audit results. |
| WP16-D001 | Read-only polling runner not yet implemented | RESOLVED | P2 | WP17 adds a manual finite explicit-network read-only polling runner with WP16 guard enforcement, structured summaries, offline tests, and no trading authority. It still does not add automated or scheduled polling. | Any automated or repeated public market-data polling. | Resolved for manual bounded runner scope only; automated or scheduled polling remains blocked by WP17-D001. |
| WP16-D002 | Rate-limit budgets are conservative local policy, not confirmed venue limits | OPEN | P2 | WP8-D002 remains OPEN. WP16 budgets are local safety defaults and are not authoritative Polymarket venue limits. | Higher-frequency polling or production scanning. | Authoritative docs and/or controlled probe evidence update repo truth before higher-frequency polling is proposed. |
| WP17-D001 | Automated/scheduled polling not implemented | OPEN | P2 | WP17 adds only a manual finite runner and intentionally excludes scheduled, recurring, daemonized, service, and bot-loop polling. | Any scheduled, recurring, daemonized, service, or bot-loop polling. | Future approved WP adds scheduling only after rate-limit evidence, observability, kill switch, and safety boundaries are updated. |
| WP17-D002 | Polling runner remains dev-only/manual because venue rate limits are unconfirmed | OPEN | P2 | WP8-D002 and WP16-D002 remain OPEN; WP17 uses conservative local budgets but does not confirm venue limits. | Production or higher-frequency polling. | Authoritative rate-limit evidence and controlled production-readiness policy update repo truth. |
| WP3-D008 | Archived old Polymarket V1 clients unresolved placeholder | DEFERRED | P3 | WP2 blocked the placeholder because no concrete repo URL exists. | Any legacy-client research. | Add exact repo URLs or explicitly drop legacy clients from scope. |
| WP3-D009 | Deployment jurisdiction / geoblocking decision | DEFERRED | P1 before live trading | Deployment location affects compliance and order placement. | Live execution. | Document deployment jurisdiction and compliance decision. |
| WP3-D010 | Incident response document not yet created | DEFERRED | P2 | WP1 marked it as needed before live. | Live execution. | Create and review `docs/incident_response.md`. |
| WP3-D011 | Live trading authorization remains disabled | DEFERRED | P0 before live execution | Live trading is intentionally blocked. | Any real order path. | Future work package updates `docs/live_trading_authorization.md` with explicit human approval and tested risk controls. |

## Rules For Adding Items

- Add or update an entry in this file in the same work package that defers a material issue.
- Include a clear reason, status, priority, required-before gate, and resolution condition.
- Use the lowest priority that honestly reflects the blocking impact.
- Do not use this log to authorize runtime execution, dependency installation, copied external code, or live trading.

## Rules For Resolving Items

- Mark an item RESOLVED only after the resolution condition is complete and documented in repo truth or reviewed artifacts.
- Mark an item SUPERSEDED only when a later repo-truth decision replaces it.
- Keep historical resolved or superseded entries unless a later approved work package intentionally archives the log.
- If resolving an item introduces new risk or scope, create a new deferred item instead of hiding the risk in the resolution note.

## WP3 Initial Entries

WP3 adds entries WP3-D001 through WP3-D011. These items are not blockers for WP3 because WP3 is documentation-only and does not integrate runtime dependencies, venue APIs, external code, or live execution paths.

## WP4 Security Tooling Update

WP4 adds `docs/security_tooling_status.md` and local wrappers under `tools/security/`. Detection was attempted without installing global or system tools. WP3-D001 through WP3-D005 remain deferred unless a later approved work package satisfies their exact resolution conditions or documents approved equivalents.

## WP5 Security Tooling Completion Update

WP5 adds a Remote Main Sync Gate under `tools/git/`, project-local setup and verification scripts under `tools/security/`, and `docs/security_tooling_completion.md`.

WP5 installed only `semgrep` and `pip-audit` into ignored `.venv-security/`. Semgrep version `1.163.0` was verified and the Semgrep scan passed. pip-audit version `2.10.0` was verified and the audit reported no known vulnerabilities. WP3-D002 and WP3-D004 are now `READY_FOR_WP`, meaning the tools are available but must be rerun immediately before any relevant runtime dependency integration, copied code, venue API integration, or live/API execution.

WP3-D001 remains `DEFERRED` because gitleaks is still unavailable and no approved equivalent is documented. WP3-D003 remains `DEFERRED` because no `package.json` exists and npm was not installed. WP3-D005 remains `DEFERRED` because no `Cargo.lock` exists and Rust is not permanently excluded from future runtime scope.

## WP7 Gitleaks Secret Scan Gate Update

WP7 adds `tools/security/setup_project_gitleaks.py`, `tools/security/verify_project_gitleaks.py`, and `docs/gitleaks_secret_scan_gate.md`.

WP7 downloaded gitleaks v8.27.2 into ignored `tools/.bin/` using the project-local acquisition script. No global or system installation was performed. Checksum verification was performed against the official release checksums file and passed (SHA256 matched). The scan command `tools/.bin/gitleaks.exe git --redact` ran and returned exit 0 with no findings.

WP3-D001 is updated from DEFERRED to READY_FOR_WP. It is READY_FOR_WP rather than RESOLVED because the scan must be rerun immediately before any relevant future runtime dependency integration, copied external code, venue API integration, or live/API execution. The gitleaks binary in `tools/.bin/` is not committed; a clean checkout requires rerunning `tools/security/setup_project_gitleaks.py`.

WP3-D002 and WP3-D004 remain READY_FOR_WP. The `.venv-security/` environment was absent on this branch (removed during WP6 cleanup); semgrep and pip-audit require `tools/security/setup_project_security_tools.py` to be rerun. Their READY_FOR_WP status is unchanged from WP5.

WP3-D003 and WP3-D005 remain DEFERRED. No `package.json` or `Cargo.lock` exists, and npm/cargo-audit were not installed.

## WP11 Snapshot Replay And Catalog Update

WP11 adds `src/data_layer/polymarket/snapshot_reader.py`, `src/data_layer/polymarket/market_catalog.py`, `src/data_layer/polymarket/snapshot_replay.py`, `tools/polymarket/inspect_snapshot_catalog.py`, and `docs/polymarket_snapshot_replay_catalog.md`.

WP11 reads WP10 JSONL snapshot files and builds an in-memory market catalog. No network calls are made. No database is added. No scheduler or bot loop is added. Catalog output (if exported) goes to git-ignored `local_data/polymarket/catalog/`.

WP8-D001 remains READY_FOR_WP. WP8-D002 remains OPEN — no automated scanning added; rate-limit policy still unconfirmed. WP9-D001 remains OPEN — CLOB /health not used. WP10-D001 remains OPEN — snapshot schema not declared stable. WP10-D002 remains OPEN — no database added in WP11. WP11-D001 and WP11-D002 added (see table above).

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP12 Snapshot Quality Gates And Local Research Reports Update

WP12 adds `src/data_layer/polymarket/snapshot_quality.py`, `src/data_layer/polymarket/local_reports.py`, `tools/polymarket/generate_snapshot_quality_report.py`, and `docs/polymarket_snapshot_quality_reports.md`.

WP12 reads WP10/WP11 local snapshot data only. It makes no network calls, adds no runtime dependency, adds no database, adds no scheduler or bot loop, and adds no strategy signals, trade proposals, backtesting, paper trading, order placement, cancellation, signing, authentication, credential reading, or live-trading path. Local report output is allowed only under git-ignored `local_data/polymarket/reports/` when explicitly requested.

WP8-D002 remains OPEN — no automated scanning added and rate-limit policy remains unconfirmed. WP9-D001 remains OPEN — CLOB `/health` is still not used or confirmed. WP10-D001 remains OPEN — quality validation does not declare the snapshot schema production-stable. WP10-D002 remains OPEN — no database support added. WP11-D001 remains OPEN — catalog remains in-memory only. WP11-D002 remains OPEN — replay remains inspection-only and not backtest-ready.

WP12-D001 and WP12-D002 are added because quality gates are research-only and local reports are not dashboard-backed.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP13 Snapshot Deduplication And Catalog Export Hardening Update

WP13 adds `src/data_layer/polymarket/snapshot_deduplication.py`, `src/data_layer/polymarket/catalog_exports.py`, `tools/polymarket/export_snapshot_catalog.py`, and `docs/polymarket_snapshot_deduplication_exports.md`.

WP13 reads WP10/WP11/WP12 local snapshot/catalog/quality data only. It makes no network calls, adds no runtime dependency, adds no database, adds no scheduler or bot loop, and adds no strategy signals, trade proposals, backtesting, paper trading, order placement, cancellation, signing, authentication, credential reading, or live-trading path. Local catalog export output is allowed only under git-ignored `local_data/polymarket/exports/` when explicitly requested.

WP8-D002 remains OPEN — no automated scanning added and rate-limit policy remains unconfirmed. WP9-D001 remains OPEN — CLOB `/health` is still not used or confirmed. WP10-D001 remains OPEN — dedup/export helpers do not declare the snapshot schema production-stable. WP10-D002 remains OPEN — no database support added. WP11-D001 remains OPEN — catalog remains in-memory only. WP11-D002 remains OPEN — replay remains inspection-only and not backtest-ready. WP12-D001 remains OPEN — quality gates remain research-only. WP12-D002 remains OPEN — reports remain not dashboard-backed.

WP13-D001 and WP13-D002 are added because catalog exports are local-file only and deduplication policy is not production canonical.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP14 Official Python Client Dependency Decision And Boundary Review Update

WP14 adds `docs/official_python_client_dependency_decision.md`, `docs/polymarket_client_boundary_review.md`, repo-truth updates, and tests for official-client dependency boundaries.

WP14 marks the old official `Polymarket/py-clob-client` as `DO_NOT_USE_ARCHIVED` / avoid because it is archived, no longer maintained, no longer functional for new or existing integrations, and points users to V2.

WP14 marks `Polymarket/py-clob-client-v2` / `py-clob-client-v2` as `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION`. Runtime reuse is `NOT_APPROVED`; copied code is `NOT_ALLOWED`; dependency install is `NOT_APPROVED_IN_WP14`; auth/trading use is `FORBIDDEN_UNTIL_EXPLICIT_WP`; security review remains pending before installation.

WP14 adds no runtime dependency, no official client import, no network calls, no credential handling, no private-key or wallet handling, no signing, no order placement, no order cancellation, no account/trade querying, no strategy signals, no trade proposals, no backtesting, no paper trading, no database, no scheduler, no bot loop, and no live-trading path. The current stdlib public adapter remains the active data path.

WP14-D001, WP14-D002, and WP14-D003 are added because the V2 client remains uninstalled/unaudited as a dependency, authenticated integration remains blocked pending credential/key/security boundaries, and no read-only sandbox exists yet.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP15 Official Client Read-Only Sandbox Audit Update

WP15 adds `tools/polymarket/official_client_sandbox/`, `docs/official_client_readonly_sandbox_audit.md`, ignore protection for `.venv-official-client/` and sandbox outputs, and offline tests for sandbox boundaries.

WP15 keeps `py-clob-client-v2` project-level status `NOT_INSTALLED`. It adds no runtime dependency, no official client import under `src/`, no credentials, no private-key or wallet handling, no signing, no order placement, no order cancellation, no account/trade querying, no strategy signals, no trade proposals, no backtesting, no paper trading, no database, no scheduler, no bot loop, and no live-trading path. The current stdlib public adapter remains the active data path.

WP14-D001 remains OPEN because the official client is not pinned or audited as a project dependency. WP14-D002 remains BLOCKED because no credential/key/security boundary exists. WP14-D003 moves to READY_FOR_WP because the isolated read-only sandbox now exists and is tested. WP15-D001 and WP15-D002 are added for unresolved sandbox API-shape confirmation and project dependency audit status.

WP3-D001 (gitleaks): rerun this WP — initial scan reported a documentation false positive for the exact phrase "credential/key/security boundary" in this log. WP15 added a narrow `.gitleaks.toml` allowlist scoped to `docs/deferred_items_log.md` and that exact phrase; rerun PASS, no leaks found.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no runtime dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and sandbox package not installed in required default command path, pip-audit not rerun.

## WP16 Read-Only Polling Policy And Rate-Limit Guard Update

WP16 adds `src/data_layer/polymarket/rate_limit_guard.py`, `src/data_layer/polymarket/polling_policy.py`, `tools/polymarket/inspect_readonly_polling_policy.py`, and `docs/polymarket_readonly_polling_policy.md`.

WP16 is offline policy-and-guard-only. It adds no automated polling, live scanner, scheduler, daemon, background worker, bot loop, database, strategy signal, trade proposal, backtest, paper trading, order placement, order cancellation, signing, authenticated client, credential reading, `.env` loading, live-trading path, official-client project dependency, or official-client import under `src/`.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP15-D001 remains OPEN because the official-client sandbox API shape is not fully confirmed. WP15-D002 remains OPEN because the official client package is still not audited as a project dependency.

WP16-D001 and WP16-D002 are added because no polling runner exists yet and the local budgets are conservative policy rather than confirmed venue limits.

WP3-D001 (gitleaks): rerun this WP - gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no runtime dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added, pip-audit not rerun.

## WP17 Controlled Read-Only Market Data Polling Runner Update

WP17 adds `src/data_layer/polymarket/readonly_polling_runner.py`, `tools/polymarket/run_readonly_market_data_polling.py`, offline runner/CLI tests, and `docs/polymarket_readonly_polling_runner.md`.

WP17 is manual, finite, explicit-network, bounded, and read-only. Default CLI behavior is offline and makes no network calls. Network use requires `--allow-network`, uses only existing public stdlib adapter methods, and calls the WP16 `RateLimitGuard` before public adapter calls. Optional JSON summaries are sanitized and restricted to ignored `local_data/polymarket/polling_runs/`.

WP17 adds no automated polling, scheduler, daemon, background worker, bot loop, database, dashboard, strategy signal, trade proposal, backtest, paper trading, order placement, order cancellation, signing, authenticated client, credential reading, `.env` loading, live-trading path, official-client project dependency, or official-client import under `src/`.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because WP16 budgets remain conservative local policy, not confirmed venue limits. WP16-D001 is RESOLVED for the manual bounded runner condition because the runner is explicit-network, bounded, guard-enforced, logged, tested, and has no trading authority.

WP17-D001 and WP17-D002 are added because automated/scheduled polling is still not implemented and the runner remains dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun this WP - gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable.

## WP18 Snapshot Capture Integration With Guarded Runner Update

WP18 updates `src/data_layer/polymarket/snapshot_capture.py`, `tools/polymarket/capture_market_snapshots.py`, focused offline tests, and repo-truth docs so manual snapshot capture uses the WP16 `RateLimitGuard` before public Gamma and optional CLOB order-book reads.

Snapshot capture remains manual, finite, explicit-network, bounded, read-only, dev/local only, and restricted to ignored `local_data/polymarket/snapshots/`. Default CLI behavior remains offline and exits without network calls unless `--allow-network` is explicitly passed. WP18 adds no scheduler, daemon, background worker, bot loop, database, dashboard, strategy signal, trade proposal, backtest, paper trading, order placement, order cancellation, signing, authenticated client, credential reading, `.env` loading, live-trading path, official-client project dependency, or official-client import under `src/`.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because WP16 budgets remain conservative local policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP10-D001 remains OPEN because WP18 does not declare the snapshot schema production-stable. WP10-D002 remains OPEN because WP18 does not add database-backed snapshot storage.

WP3-D001 (gitleaks): rerun this WP - gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable.

## WP19 Snapshot Quality Gate Integration For Guarded Captures Update

WP19 updates `src/data_layer/polymarket/snapshot_quality.py`, `src/data_layer/polymarket/local_reports.py`, `tools/polymarket/generate_snapshot_quality_report.py`, focused offline tests, and repo-truth docs so local quality reports summarize WP18 guarded-capture manifest provenance.

The WP19 quality/reporting layer remains offline-only and reads only local snapshot files already loaded by `snapshot_reader.py`. It adds no network calls, runtime dependency, database, dashboard, scheduler, daemon, background worker, bot loop, strategy signal, trade proposal, historical trading simulation, paper trading, order placement, order cancellation, signing, authenticated client, credential reading, `.env` loading, live-trading path, official-client project dependency, or official-client import under `src/`.

WP19 flags `network_used=True` manifests without guard provenance as WARNING, not ERROR, because older local data may predate WP18. WP19 also warns when guard provenance omits local-budget/rate-limit uncertainty. These warnings do not make quality gates production-ready and do not make local reports dashboard-backed.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because WP16 budgets remain conservative local policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP10-D001 remains OPEN because WP19 does not declare the snapshot schema production-stable. WP10-D002 remains OPEN because WP19 does not add database-backed snapshot storage. WP11-D001 remains OPEN because the catalog remains in-memory only. WP11-D002 remains OPEN because replay remains inspection-only. WP12-D001 remains OPEN because quality gates remain research-only. WP12-D002 remains OPEN because reports remain local files only and not dashboard-backed. WP13-D001 and WP13-D002 remain OPEN.

## WP10 Snapshot Persistence Update

WP10 adds `src/data_layer/polymarket/snapshot_models.py`, `src/data_layer/polymarket/snapshot_writer.py`, `src/data_layer/polymarket/snapshot_capture.py`, `tools/polymarket/capture_market_snapshots.py`, and `docs/polymarket_snapshot_persistence.md`.

WP10 uses only the three WP9-confirmed endpoints (Gamma /markets, Gamma /markets/{id}, CLOB /book). CLOB /health is not used. No automated polling is added. Snapshot output goes to git-ignored `local_data/polymarket/snapshots/`.

WP8-D001 remains READY_FOR_WP. WP8-D002 remains OPEN — no automated polling added. WP9-D001 remains OPEN — CLOB /health not used. WP9-D002 updated: resolved for WP10 scope (snapshot capture uses updated parser). WP10-D001 and WP10-D002 added.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP9 Endpoint Contract Validation Update

WP9 adds `tools/polymarket/readonly_contract_probe.py` (contract probe tool), `tests/data_layer/polymarket/test_readonly_contract_probe.py` (offline tests), and `docs/polymarket_endpoint_contract_validation.md` (validation record).

WP9 ran a controlled `--allow-network` probe against four endpoint candidates. Three passed (Gamma /markets, Gamma /markets/{id}, CLOB /book). CLOB /health returned HTTP 404.

Key discoveries:
- `clobTokenIds` and `outcomes` fields are JSON-encoded strings, not Python lists. Adapter parser updated.
- Correct identifier for Gamma `/markets/{id}` is the integer `id` field, not `conditionId`.
- CLOB `/book` bids/asks structure matches WP8 parser expectations.

WP8-D001 updated from OPEN to READY_FOR_WP (partial scope). WP8-D002 remains OPEN. WP9-D001 and WP9-D002 added.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP8 Read-Only Adapter Evaluation Update

WP8 adds `src/data_layer/polymarket/` (read-only public data adapter, Python stdlib only), `tests/data_layer/polymarket/` (offline adapter tests), `tools/polymarket/readonly_smoke_test.py` (optional manual network smoke test), and evaluation/semantics docs under `docs/`.

WP8 does not add any runtime Python dependency. No new package is installed or vendored. WP3-D007 remains DEFERRED; the official Python CLOB client is not used.

WP8 adds WP8-D001 (endpoint contract unconfirmed) and WP8-D002 (rate-limit policy unconfirmed). These are P2 items that block production use of the adapter but do not block the WP8 evaluation scope.

WP3-D001 (gitleaks): rerun this WP — gitleaks scan PASS, no findings.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP (no new Python dependency added).
WP3-D004 (pip-audit): READY_FOR_WP; no new Python dependency added, pip-audit not rerun.

## WP6 Generated Artifact Incident Update

WP6 found `.venv-security/` visible as an untracked generated local artifact on stale local `main`. Investigation showed no tracked or staged generated artifact files under `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, or `security-scan-output/`.

This incident is RESOLVED in WP6 by deleting only allowlisted untracked local artifacts, documenting the investigation in `docs/local_generated_artifacts.md`, adding cleanup and preflight guard scripts under `tools/git/`, and requiring `.venv-security/` ignore protection before `tools/security/setup_project_security_tools.py` creates or reuses the project-local security environment.
