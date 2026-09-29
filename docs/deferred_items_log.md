# Deferred Items Log

## Purpose

This log tracks material issues, unavailable tools, unresolved dependency decisions, blocked security checks, and postponed decisions that are intentionally deferred from the current work package. Deferred items remain visible repo truth until they are resolved, superseded, or promoted into a later approved work package.

Research and workbench artifacts do not gain runtime authority because they are listed here.

## S10-GATE-AF1 Post-WP164A Deferred-Item Reconciliation

WP164A Attempt-03 was consumed on runtime-certified head
`1c7de22f31cd093771d6bc0748c440ad5284b105` as `WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS`
and merged by PR #193 at `70f867bdcd5e97b0dc05d4008c2c023feb461658`; the WP164A
dependency certification is complete and no longer blocks S10-GATE-AF1. AF1 Attempt-03 was
later authorized, executed and CONSUMED (S10-GATE-AF1-D007); the successor AF1 Attempt-04 was
authorized, executed on runtime execution head `dead42658e8fc9139d82f772e1f2fff67ba07674`, CONSUMED, and finalized `AF1_PASS`
(receipt `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`); S10-GATE-AF1-D001/D002/D004 are resolved.
No new public, provider, credential, scheduler, strategy, paper/live, execution, or
capital authority is created.

## WP156A Deferred-Item Reconciliation

WP156A adds no new product capability and resolves only the private large-canonical-payload
batch-fingerprint contradiction. Consumed WP164A Attempt-02 remains permanently consumed.
WP164A branch reconciliation, a new zero-network Phase-A candidate, any future fresh public
smoke, and AF1 Attempt-03 remain separately gated and are not started by WP156A. No existing
dependency, security-tool, rate-limit, persistence, scheduler, strategy, paper/live, execution,
or capital deferral is promoted or silently resolved.

- S10-HERMES-CTX-01-D001 (OPEN, evidence limitation): pinned Hermes v0.21.3 exposes no
  direct remote Firecrawl HTTP/redirect telemetry and cannot always attest whether its
  bounded same-provider primary-transport recovery fired. Therefore remote HTTP remains
  `UNAVAILABLE`, remote private-target proof `UNKNOWN`, recovery `UNKNOWN_POSSIBLE`, and
  exact physical provider-attempt count `UNKNOWN` where direct future evidence is absent.
  This does not block the deterministic context layer and grants no H1 #5 or runtime authority.

## Status Definitions

- WP175-D001 (BLOCKED, P0): `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE` — S10-EVID-01B completed `EVIDENCE_INCONCLUSIVE`; genuine PMXT evidence reached WP170/WP172, but the tested candidate missed first-look OOS criteria and PMXT `AS_CAPTURED` correctly remained continuity-incomplete. WP175E does not resolve qualification or authorize live. Revisit only after WP175E merges and a separately gated prospective run preregisters a fresh candidate before its forward OOS/native capture, produces genuine WP172/WP173 evidence, and receives a separate exact-head human Gate-C decision.
- WP175-D002 (RESOLVED_WP175D, P2) — external historical research bridge (Side10 ID S10-DATA-02): merged WP175D / PR #179 supplies the provenance-separated `PmxtV2ResearchLineage` -> `ExternalDatasetBinding` -> WP170 path without canonical-PIT backdating or registry migration. This resolution did not qualify a strategy or authorize live.
- WP175E-D001 (IN REVIEW via WP175E, P2) — native continuity-attested market-truth bridge (Side10 ID S10-DATA-03): the exact FAST/risk-2 package adds bounded verified WP169 accepted-WS observation/session/gap reads, store-derived `NativeContinuityAttestation`, and parallel `NativeMarketTruthWindow` admission into unchanged WP172 evaluator and WP173 paper replay semantics. Resolution condition: merge after exact-head Side10 review and green evidence. It resolves/narrows WP169-D001 only for the actual WP169-native -> WP172 bridge; a generic PIT -> Nautilus adapter remains open. It does not claim `LIVE_PATH_EVIDENCE_READY`, authorize Gate C, or start WP176. Normative contract: `docs/native_continuity_attested_market_truth_bridge_contract.md`.


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
| WP20-D001 | Hermes installation and setup not performed | READY_FOR_MANUAL_SETUP_DECISION | P3 | WP20 records Hermes policy only. WP27 adds `docs/agent_hermes_manual_setup_decision_record.md` defining the manual setup gates, user decisions, and approval steps. Hermes remains not installed, not required, and not a runtime dependency. Decision state: DECISION_DEFERRED_PENDING_USER_SELECTION. | Any Hermes runtime use, command approval, memory/persistence setup, network permission, or provider integration. | User explicitly selects runtime/provider/environment; future approved WP documents manual setup and keeps it outside protected runtime boundaries unless explicitly approved. WP27 does not resolve this item because Hermes is still not installed or configured. |
| WP27-D001 | Runtime/provider/environment decision remains pending user selection | OPEN | P3 | WP27 creates decision gates but does not make the runtime/provider/environment selection. The user must explicitly choose Hermes, an alternative runtime, or the no-runtime path before any setup work begins. | Any Hermes or agent runtime installation, provider key setup, network permission, memory/persistence, or command execution. | User explicitly states runtime preference in a future work package instruction, repo truth is updated, and required approval gates are satisfied. |
| WP20-D002 | Agent context export schema not implemented | RESOLVED | P3 | WP21 defines and tests `docs/agent_context_export_schema.md` as a schema-only contract without exporter implementation, runtime Hermes dependency, or execution authority. | Any AI-agent read-only context export or local report handoff. | Resolved for schema-contract scope only by WP21; exporter implementation remains not started under WP21-D001. |
| WP20-D003 | Performance and strategy logs unavailable for performance-review agent | OPEN | P3 | WP20 does not add paper trading, backtesting, live trading, strategy signals, or log schemas. Performance review remains future advisory policy only. | Any performance-review agent or strategy suggestion workflow. | Future approved WPs define authorized logs/schemas and review workflow before advisory analysis uses them. |
| WP21-D001 | Local agent context exporter not implemented | RESOLVED | P3 | WP23 implements and tests a local/offline/read-only context exporter using allowlisted repo-truth docs and optional allowlisted local report metadata only. It adds no scheduler, runtime, network polling, Hermes dependency, credentials, execution authority, or generated committed context package. | Any actual local agent context export generation. | Resolved for WP23 local/offline/read-only exporter scope only. |
| WP21-D002 | Agent context report generator not implemented | RESOLVED | P3 | WP25 implements and tests a deterministic local/offline/read-only report generator that reads only WP23-compatible local context exports and writes reports only under ignored `local_data/agent_context_reports/` when explicit output paths are provided. It adds no Hermes runtime dependency, LLM dependency, strategy suggestion, signal, or execution authority. | Any agent report generation or analyst report handoff. | Resolved for WP25 deterministic local/offline/read-only report-generator scope only; future runtime or Hermes consumption remains separate. |
| WP25-D001 | Analyst report operator runbook not implemented | RESOLVED | P3 | WP26 adds and tests `docs/agent_context_report_operator_runbook.md` for repeatable human operation of deterministic local/offline/read-only report generation. | Routine operator use of local analyst report generation. | Resolved for WP26 local/offline/read-only operator runbook scope only; future Hermes, AI runtime, or advisory consumption remains separate. |
| WP28-D001 | Token-efficiency helper tooling not fully closed | OPEN | P3 | WP30, WP32, WP34, and WP36 implemented the approved local/offline/read-only helper stack for diff/scope, validation-output, code blast-radius, and status snapshot use. WP37 consolidates the sequence but broader command-output compression remains unimplemented. | Any implementation of broader command-output compression helper tooling or any expansion beyond the implemented advisory helper stack. | Future approved design/implementation WP explicitly scopes broader command-output compression or repo truth declares the item superseded. |
| WP37-D001 | Advisory/product work not resumed after token-efficiency closeout | RESOLVED (WP38 docs-only handoff selection) | P3 | WP37 is docs/test-only closeout and did not resume advisory-agent, Hermes, product, runtime, database, dashboard, scheduler, polling, strategy, paper-trading, live-trading, wallet/copy-trading, or official-client runtime work. | Runtime/product implementation remains future-only. | Resolved only for selecting and documenting the local advisory handoff path in WP38; no runtime/product work is implemented or authorized. |
| WP38-D001 | Advisory runtime boundary and consumption design not implemented | RESOLVED (WP39 docs-only design completion) | P3 | WP38 is docs/test-only handoff and does not design a future advisory consumer boundary in detail. WP39 adds the docs-only advisory runtime boundary and consumption design. | Any advisory consumer implementation or runtime-adjacent consumption design. | Resolved only for design completion. No advisory consumer, runtime, LLM, Hermes, network, account, or trading implementation is authorized. |
| WP38-D002 | Local advisory consumer prototype implemented for deterministic local/offline/read-only scope | RESOLVED (WP40 local/offline/read-only prototype) | P3 | WP40 implements `tools/advisory/local_advisory_consumer.py` as an explicit-input-only local advisory consumer prototype. | Any local advisory consumer prototype. | Resolved only for deterministic local/offline/read-only advisory consumer prototype scope; no LLM, network, Hermes, account, trading, scheduler, database, dashboard, or runtime behavior is authorized. |
| WP39-D001 | Local advisory consumer prototype implemented after boundary design | RESOLVED (WP40 local/offline/read-only prototype) | P3 | WP40 implements a deterministic local/offline/read-only advisory consumer prototype within the WP39 boundary. | Any local advisory consumer prototype. | Resolved only for the tested local/offline/read-only prototype under `tools/advisory/local_advisory_consumer.py`; runtime, LLM, Hermes, account, trading, scheduler, database, and dashboard work remain unauthorized. |
| WP39-D002 | Advisory prompt/runbook package implemented for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates human-operated advisory prompt templates and an operator runbook package. | Any advisory prompt/runbook package. | Resolved only for docs-only advisory prompt/runbook package scope; no runtime, LLM/Hermes authorization, credentials, account access, trading authority, prompt runner, or implementation authority is authorized. |
| WP40-D001 | Advisory prompt/runbook package implemented after prototype for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates advisory prompt templates and an operator runbook package after the deterministic local advisory consumer prototype. | Any advisory prompt/runbook package. | Resolved only for docs-only advisory prompt/runbook package scope; no runtime, LLM/Hermes authorization, credentials, account access, trading authority, prompt runner, or implementation authority is authorized. |
| WP40-D002 | LLM/Hermes/provider integration not designed or implemented | OPEN | P3 | WP40 remains deterministic, local/offline/read-only, and non-LLM. It does not select or integrate Hermes, providers, credentials, network permissions, memory, or command authority. | Any LLM, Hermes, provider, runtime, network, memory, or command integration. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any integration work. |
| WP41-D001 | Advisory consumer integration review / operator workflow hardening completed for docs-only scope | RESOLVED (WP42 docs-only operator workflow hardening) | P3 | WP42 documents the local human-operated advisory workflow around WP40 and WP41 with evidence, stop/reject, decision-log, and future-WP conversion rules. | No runtime/product implementation is authorized by this resolution. | Resolved only for docs-only advisory consumer integration review / operator workflow hardening scope. |
| WP41-D002 | Provider/Hermes decision refresh not performed after prompt/runbook package | OPEN | P3 | WP41 does not revisit provider, Hermes, runtime, network, memory, command, credential, or data-sharing decisions. | Any provider/Hermes decision refresh or setup path. | Future approved WP records explicit user selection and repo-truth approval before any provider/Hermes/runtime integration or setup work. |
| WP42-D001 | Provider/Hermes decision refresh not performed after operator workflow hardening | OPEN | P3 | WP42 is docs-only operator workflow hardening and does not revisit provider, Hermes, runtime, network, memory, command, credential, or data-sharing decisions. | Any provider/Hermes decision refresh, setup, or integration path. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any provider/Hermes/runtime work. |
| WP42-D002 | No runtime or prompt runner implemented after operator workflow hardening | OPEN | P3 | WP42 intentionally adds no runtime behavior, workflow runner, prompt runner, LLM/Hermes/provider integration, scheduler, database, dashboard, polling, or trading behavior. | Any runtime, workflow runner, prompt runner, LLM/Hermes/provider integration, or protected product behavior. | Future approved WP explicitly scopes and authorizes the design first; implementation requires separate protected-boundary, security, dependency, and human-review gates. |
| WP3-D008 | Archived old Polymarket V1 clients unresolved placeholder | DEFERRED | P3 | WP2 blocked the placeholder because no concrete repo URL exists. | Any legacy-client research. | Add exact repo URLs or explicitly drop legacy clients from scope. |
| WP3-D009 | Deployment jurisdiction / geoblocking decision | DEFERRED | P1 before live trading | Deployment location affects compliance and order placement. | Live execution. | Document deployment jurisdiction and compliance decision. |
| WP3-D010 | Incident response document not yet created | DEFERRED | P2 | WP1 marked it as needed before live. | Live execution. | Create and review `docs/incident_response.md`. |
| WP3-D011 | Live trading authorization remains disabled | DEFERRED | P0 before live execution | Live trading is intentionally blocked. | Any real order path. | Future work package updates `docs/live_trading_authorization.md` with explicit human approval and tested risk controls. |
| WP44-D001 | Market Research Priority Scoring implementation not started | RESOLVED (WP49 core scorer scope) | P3 | WP44 defines docs-only design; WP48 defines schema/output contract. WP49 implements the local/offline/read-only core scorer at src/data_layer/market_research_priority_scoring.py. | Any scoring implementation, CLI, report/export, or advisory integration. | Resolved only for local/offline/read-only core scorer scope by WP49. Feature extraction, CLI/export/report, and advisory consumer integration remain not started. |
| WP44-D002 | Score laundering mitigation not enforced by implementation | RESOLVED (WP49 core scorer scope) | P3 | WP44 documents score-laundering mitigations in design-only form; WP48 defines contract-level forbidden fields and advisory labels. WP49 enforces advisory-only, non-signal, staleness/provenance/missing-data penalties, forbidden-output checks, and human-review-required enforcement via implementation tests. | Any scoring implementation or report/export output. | Resolved only for local/offline/read-only core scorer scope by WP49; feature extraction, export, and advisory consumer integration mitigations remain to be added. |
| WP48-D001 | Market Research Priority Scoring implementation not started after schema/output contract | RESOLVED (WP49 core scorer scope) | P3 | WP48 defines the schema/output contract only. WP49 implements the local/offline/read-only core scorer. | Any scoring implementation, CLI, report/export, or advisory integration. | Resolved only for local/offline/read-only core scorer scope by WP49. Feature extraction, CLI/export/report, and advisory consumer integration remain not started (see WP49-D001, WP49-D002, WP49-D003). |
| WP48-D002 | Schema/output contract not enforced by implementation yet | RESOLVED (WP49 core scorer scope) | P3 | WP48 adds a docs-only contract. WP49 adds implementation tests enforcing required top-level fields, required market fields, advisory label, human_review_required, score bounds [0.0, 1.0], forbidden fields (recursive), staleness caps, missing-provenance caps, missing-data caps, and quality-gate caps. | Any scoring implementation or scored output generation. | Resolved only for local/offline/read-only core scorer scope by WP49. Contract enforcement for future exporters, report writers, and advisory consumers remains to be added. |
| WP49-D001 | Feature extraction from local/offline artifacts not started | RESOLVED (WP51 basic feature extraction foundation scope) | P3 | WP49 implements only the local/offline/read-only core scorer with already-prepared in-memory inputs. No feature extraction from real local Polymarket snapshot/catalog/export artifacts is implemented. | Any scoring run that reads real local artifact files (snapshots, catalogs, exports). | Resolved only for the narrow WP51 basic feature extraction foundation scope: src/data_layer/market_research_priority_features.py implements basic metadata/provenance/staleness/missing-data feature extraction from MarketMetadataSnapshotRecord, OrderBookSnapshotRecord, and SnapshotManifest objects. Advanced feature groups remain deferred (WP51-D001, WP51-D002, WP51-D003). |
| WP49-D002 | CLI/export/report writer not started | RESOLVED (WP65 local/offline/explicit/manual export scope) | P3 | WP49 adds no CLI, no JSON writer/exporter, no report writer, no local output file generation, and no advisory consumer integration. WP65 implements a local/offline/explicit/manual export CLI at tools/research_queue/local_research_queue_export.py that reads WP64 report objects or market context lists and writes JSON or Markdown to stdout or an explicit local path. | Resolved only for narrow local/offline/explicit/manual export scope. Scheduled/automated export, database/dashboard-backed queue, and advisory consumer integration remain deferred (see WP65-D001, WP65-D002, WP65-D003). |
| WP49-D003 | Core scorer not integrated with advisory consumer or market catalog | OPEN | P3 | WP49 core scorer is standalone and in-memory only. It is not wired to the local advisory consumer (tools/advisory/local_advisory_consumer.py) or the local market catalog (src/data_layer/polymarket/market_catalog.py). | Any advisory consumer use of scoring output or automated catalog-driven scoring. | Future approved WP integrates core scorer with advisory consumer or catalog only after feature extraction is implemented and user explicitly approves. |
| WP50-D001 | Research direction locked but implementation sequencing still requires explicit future WPs | OPEN | P3 | WP50 locks the research-phase direction in docs/research_data_foundation_direction.md but does not draft, approve, or schedule any future implementation WP. Each item in the approved near-term sequence requires separate explicit user approval before a WP is drafted. | Any feature extraction, CLI/export/report, advisory integration, calibration, wallet-attention, official-source latency, paper-trading, live-trading, or execution WP. | Future approved WP explicitly selected by user after WP50 is merged; implementation sequencing remains user-gated. |
| WP51-D001 | Provenance/staleness enforcement hardening beyond foundation not started | RESOLVED (WP53 data-integrity hardening scope) | P3 | WP51 implements basic staleness and provenance detection only. WP53 adds explicit provenance_degraded flag, provenance_weakness_reasons, provenance_warning, future-timestamp detection, missing_question and missing_market_status detection, non-compensatory missing_data_penalty, quality-impacting vs informational weakness separation, and expanded staleness/quality-gate semantics. | Any further provenance/staleness hardening WP. | Resolved only for the narrow WP53 provenance/staleness/missing-data hardening scope; resolution-rule ambiguity extraction (WP51-D002), microstructure quality extraction (WP51-D003), and CLI/export/report (WP51-D004) remain OPEN. |
| WP51-D002 | Resolution-rule ambiguity extraction not started | OPEN | P3 | WP51 implements only basic metadata/staleness/provenance feature extraction. Resolution-rule ambiguity taxonomy, manual-label workflow, and ambiguity feature extraction are not started. WP55 adds the taxonomy and manual-label workflow (docs/schema/tests only); automated parser and feature extraction from ambiguity labels remain not started (see WP55-D001, WP55-D002). | Any automated resolution-rule ambiguity extraction or feature extraction WP. | WP55 addresses the taxonomy/manual-label workflow portion only. Future approved WP explicitly scopes automated parser and feature extraction after WP55 is merged and user explicitly approves. |
| WP51-D003 | Microstructure quality feature extraction beyond basic availability not started | RESOLVED (WP61 Microstructure Quality V1 metadata scope) | P3 | WP51 determines only basic order book availability and two-sided structure. WP61 adds advisory-only `microstructure_quality` metadata from local OrderBookSnapshotRecord objects. Numeric modeling and downstream integration remain deferred. | Any further microstructure quality feature extraction or downstream integration WP. | Resolved only for WP61 local/offline/read-only metadata scope. Future numeric modeling or downstream use requires explicit approval. |
| WP51-D004 | CLI/export/report writer not started | RESOLVED (WP65 local/offline/explicit/manual export scope) | P3 | WP51 adds no CLI, no JSON writer/exporter, no report writer, no local output file generation, and no advisory consumer integration. WP65 implements a local/offline/explicit/manual export CLI consuming WP64 report objects. | Resolved only for narrow local/offline/explicit/manual export scope. Scheduled/automated export, database/dashboard-backed queue, and advisory consumer integration remain deferred (see WP65-D001, WP65-D002, WP65-D003). |
| WP52-D001 | Long-term roadmap locked but milestone implementation remains gated by explicit future WPs | OPEN | P3 | WP52 locks the long-term bot-completion roadmap in docs/long_term_bot_completion_roadmap.md but does not draft, approve, or schedule any future implementation WP. Each milestone phase requires separate explicit user approval before a WP is drafted. | Any implementation WP beyond docs/tests-only roadmap/onboarding lock. | Future approved WP explicitly selected by user after WP52 is merged; milestone implementation sequencing remains user-gated. |

| WP53-D001 | Resolution-rule ambiguity extraction still not started after WP53 hardening | OPEN | P3 | WP53 hardens provenance/staleness/missing-data enforcement but does not add resolution-rule ambiguity taxonomy, parser, manual-label workflow, or ambiguity feature extraction. WP55 adds the taxonomy and manual-label workflow (docs/schema/tests only); automated parser and feature extraction remain not started (see WP55-D001, WP55-D002). | Any automated resolution-rule ambiguity extraction or feature extraction WP. | WP55 addresses the taxonomy/manual-label workflow portion only. Future approved WP explicitly scopes automated parser and feature extraction after WP55 is merged and user explicitly approves. |
| WP53-D002 | Microstructure quality feature extraction still not started after WP53 hardening | RESOLVED (WP61 Microstructure Quality V1 metadata scope) | P3 | WP53 hardens provenance/staleness/missing-data enforcement. WP61 adds advisory-only `microstructure_quality` metadata from local order-book records without scorer changes. Numeric modeling and downstream integration remain deferred. | Any further microstructure quality feature extraction or downstream integration WP. | Resolved only for WP61 local/offline/read-only metadata scope. Future numeric modeling or downstream use requires explicit approval. |
| WP54-D001 | GitHub-posted evidence still requires human or Claude manual verification because the guard remains local/offline | OPEN | P4 | WP54 hardens posted evidence self-check rules and adds the follow-up process-defect classification policy, but the guard at `tools/git/pr_evidence_consistency_guard.py` remains local/offline and does not fetch or validate live GitHub PR body or posted PR comments. WP46-D001 and WP47-D001 remain open for the same scope. Any future requirement to validate already-posted GitHub content automatically is deferred to a future approved GitHub-aware helper WP with explicit network/auth boundary. | Any WP requiring automatic live GitHub PR content verification. | Future approved WP adds a GitHub-aware guard or validation helper with explicit network/auth boundary defined in repo truth. |
| WP55-D001 | Resolution ambiguity labels are not yet consumed by feature extraction or scoring | RESOLVED (WP57 local/offline/read-only feature extraction from validated manual labels scope) | P3 | WP55 defines the resolution-rule ambiguity taxonomy, manual-label workflow, and label schema in docs/schema/tests form only. WP56 implements the schema validator and read-only label reader. WP57 implements local/offline/read-only feature extraction from validated manual labels in src/data_layer/market_research_priority_features.py. Scorer integration, advisory consumer integration, and CLI/export/report writer remain not started (see WP57-D001). | Any WP consuming ambiguity labels in scoring, advisory consumer, or reporting. | Resolved only for WP57 local/offline/read-only feature extraction scope; scorer integration, advisory consumer integration, and report writer remain deferred. |
| WP55-D002 | Automated resolution-rule parser remains not started | OPEN | P3 | WP55 defines human-review taxonomy and manual-label workflow but does not implement any automated parser for resolution rule text. WP57 adds feature extraction from manually authored validated labels only; no automated parser is added. Automated extraction of ambiguity categories from free-text resolution rules remains deferred. This item subsumes the automated-parser portion of WP51-D002 and WP53-D001. | Any automated resolution-rule parsing or automated ambiguity extraction WP. | Future approved WP explicitly scopes automated parser design after WP55 is merged and user explicitly approves. Parser must not use LLM/Hermes without separate boundary review and approval. |
| WP56-D001 | Resolution ambiguity labels validated but not yet consumed by feature extraction | RESOLVED (WP57 local/offline/read-only feature extraction from validated manual labels scope) | P3 | WP56 implements the local/offline/read-only schema validator (src/data_layer/resolution_ambiguity_labels.py) and optional read-only JSON/JSONL reader. WP57 implements feature extraction from validated labels in src/data_layer/market_research_priority_features.py. Scorer integration, advisory consumer integration, and CLI/export/report writer remain not started (see WP57-D001). | Any downstream scoring, report, or advisory use of resolution ambiguity labels. | Resolved only for WP57 local/offline/read-only feature extraction scope; scorer weighting, advisory consumer integration, and CLI/export/report writer remain deferred. |
| WP57-D001 | Resolution ambiguity feature extraction not yet integrated into scorer/report/advisory consumer | OPEN | P3 | WP57 adds local/offline/read-only feature extraction from validated manual labels and attaches a safe resolution_ambiguity sub-dict to market contexts. The sub-dict is not yet used in scorer weights/components, advisory consumer integration, CLI/export/report writer, or any downstream consumer. No new score component, no report writer, no advisory integration is added in WP57. | Any WP that integrates resolution ambiguity data into scorer weights, report generation, or advisory consumer output. | Future approved WP explicitly scopes integration with the scorer, advisory consumer, or report writer only after WP57 is merged and user explicitly approves. |
| WP61-D001 | Postgres implementation deferred | OPEN | P3 | WP61 locks SQLite first and Postgres later only if justified. No database implementation or dependency is added. | Any Postgres dependency, schema, migration, hosted state store, or production database work. | Future approved WP explicitly authorizes database implementation and confirms security/dependency gates. |
| WP61-D002 | Dashboard implementation deferred | OPEN | P3 | WP61 locks Streamlit first for internal dashboard planning, Grafana later for runtime metrics, and Next.js only if productizing. No dashboard implementation or dependency is added. | Any Streamlit, Grafana, Next.js, dashboard, or monitoring implementation. | Future approved WP explicitly scopes the selected dashboard path and dependency gates. |
| WP61-D003 | VPS/runtime scheduler deferred | OPEN | P3 | WP61 locks local development first and cheap VPS later for controlled live pilot planning. No deployment, scheduler, bot loop, or hosted runtime implementation is added. | Any VPS, deployment, scheduler, bot loop, service, or hosted runtime work. | Future approved WP explicitly scopes runtime/deployment work and protected-boundary review. |
| WP61-D004 | Paper/live execution ladder phases deferred | OPEN | P3 | WP61 locks the phased ladder research-only -> paper -> dry-run -> manual live approval -> restricted live. No phase after research-only is implemented or authorized. | Any paper, dry-run, manual live approval, restricted live, credential, account, or execution work. | Future approved WP explicitly authorizes the next phase and satisfies protected-boundary gates. |
| WP61-D005 | Slippage/fill/tradability/execution modeling remains forbidden until explicit future WP | OPEN | P3 | WP61 adds only advisory local order-book metadata. It does not add slippage, fill probability, tradability, execution-confidence, order-size, or downstream modeling. | Any numeric modeling or downstream consumer that could be interpreted as execution readiness. | Future approved WP explicitly scopes modeling and preserves non-signal boundaries. |
| WP62-D001 | Semantic/fuzzy/LLM cross-market matching remains deferred | OPEN | P3 | WP62 adds deterministic metadata-only local key comparison only. No semantic similarity, fuzzy match, embedding, or LLM-based equivalence detection is implemented. | Any WP that adds semantic or fuzzy cross-market matching. | Future approved WP explicitly scopes semantic/fuzzy/LLM matching and confirms non-signal boundary. |
| WP62-D002 | Price-incoherence/arbitrage/opportunity detection remains forbidden until explicit future WP | OPEN | P3 | WP62 adds metadata-only relationship candidates only. No price comparison, incoherence detection, arbitrage detection, or opportunity scoring is implemented or authorized. | Any WP that adds cross-market price comparison, incoherence scoring, arbitrage detection, or opportunity detection. | Future approved WP explicitly authorizes the scope, non-signal boundaries, and security/compliance gates. |
| WP62-D003 | Cross-market relationship metadata not integrated into scorer weights | OPEN | P3 | WP62 adds relationship metadata to market_context only. No new score component, no scorer weight change, and no advisory consumer integration is added. | Any WP that integrates cross-market relationship metadata into scorer weights or advisory consumer output. | Future approved WP explicitly scopes integration with the scorer and preserves non-signal boundaries. |
| WP63-D001 | Automated resolution-rule parser remains deferred | OPEN | P3 | WP63 adds metadata-only field presence checks only. No resolution-rule parsing, NLP extraction, or automated rule interpretation is implemented. | Any WP that adds a resolution-rule parser. | Future approved WP explicitly scopes a resolution-rule parser and confirms non-signal boundary. |
| WP63-D002 | Official-source monitoring/polling remains deferred | OPEN | P3 | WP63 detects source URL patterns in local text only. No official-source monitoring, URL fetching, source polling, or network access is implemented. | Any WP that adds official-source monitoring or network-backed source verification. | Future approved WP explicitly authorizes official-source monitoring with network/auth boundary review. |
| WP63-D003 | Source authority ranking remains deferred | OPEN | P3 | WP63 adds only presence/absence metadata flags. No source ranking, authority scoring, or source hierarchy ordering is implemented. | Any WP that adds source authority ranking or scoring. | Future approved WP explicitly scopes source authority ranking and preserves non-signal boundaries. |
| WP63-D004 | Resolution source hierarchy metadata not integrated into scorer weights | OPEN | P3 | WP63 adds resolution_source_hierarchy to market_context only. No new score component, no scorer weight change, and no advisory consumer integration is added. | Any WP that integrates resolution source hierarchy metadata into scorer weights or advisory consumer output. | Future approved WP explicitly scopes integration with the scorer and preserves non-signal boundaries. |
| WP64-D001 | CLI/export/report writer for research queue remains deferred | OPEN | P3 | WP64 adds only in-memory queue/report/packet objects. No CLI, no JSON file writer, no markdown report writer, no export service, no dashboard, and no database-backed queue is added. | Any WP that adds a CLI-driven or file-export research queue output. | Future approved WP explicitly scopes the export/CLI path as a local/offline/read-only explicit command only; no scheduler; no strategy; no trading. |
| WP64-D002 | Advisory consumer integration of research queue remains deferred | OPEN | P3 | WP64 adds queue/report/packet objects only. No advisory consumer integration, no strategy proposal integration, and no paper/live trading integration is added. | Any WP that wires the research queue into an advisory consumer, strategy, or execution path. | Future approved WP explicitly scopes integration with advisory consumer only after explicit user authorization and protected-boundary review. |
| WP64-D003 | Strategy/paper/live use of research queue remains forbidden until explicit future WP | OPEN | P3 | WP64 queue/report/packet is advisory-only research triage. No trade signal, no expected return, no position sizing, no paper trading, and no live trading use is authorized. | Any WP that proposes using the research queue as a trading signal or paper/live trading input. | Future approved WP explicitly authorizes the research scope expansion and satisfies all protected-boundary gates. |
| WP64-D004 | Dashboard/database-backed research queue remains deferred | OPEN | P3 | WP64 adds in-memory-only objects. No dashboard, no database, no persistence, no scheduler, and no hosted runtime is added. | Any WP that adds a dashboard, database, or persistent queue. | Future approved WP explicitly scopes database/dashboard integration after protected-boundary review and schema stabilization. |
| WP65-D001 | Scheduled/automated research queue export remains deferred | OPEN | P3 | WP65 adds only a manually invoked export CLI. No scheduler, daemon, cron, bot loop, or automated report generation is added or authorized. | Any WP that adds automated or scheduled research queue export. | Future approved WP explicitly scopes scheduled export with scheduler/daemon boundary review and safety gates. |
| WP65-D002 | Dashboard/database-backed research queue remains deferred | OPEN | P3 | WP65 adds only a local/offline/explicit export to stdout or an explicit local file. No dashboard, no database, no persistent queue, and no hosted runtime is added. | Any WP that adds a dashboard, database, or persistent queue backed by the research queue. | Future approved WP explicitly scopes database/dashboard integration after protected-boundary review and schema stabilization. |
| WP65-D003 | Advisory consumer integration of research queue remains deferred | OPEN | P3 | WP65 adds only a local export tool. No advisory consumer integration, no strategy proposal integration, and no paper/live trading integration is added. | Any WP that wires the research queue export into an advisory consumer, strategy, or execution path. | Future approved WP explicitly scopes integration with advisory consumer only after explicit user authorization and protected-boundary review. |
| WP65-D004 | Calibration of queue thresholds remains deferred | OPEN | P3 | WP65 adds no threshold calibration, no resolved-outcome ingestion, and no validation of queue accuracy. Queue thresholds from WP64 remain unchanged. | Any WP that calibrates queue thresholds using resolved outcomes or backtested data. | Future approved WP explicitly scopes calibration harness and resolved-outcome ingestion with safety and non-signal boundaries. |
| WP66-D001 | Calibration record schema validator implementation deferred | RESOLVED (WP67 local/offline/read-only calibration record schema validator scope) | P3 | WP66 adds the calibration harness design and resolved outcome data requirements in docs/schema/tests form only. WP67 implements the local/offline/read-only calibration record schema validator at `src/data_layer/calibration_record_validation.py`. | Any WP that reads resolved outcome fixtures or generates calibration reports. | Resolved only for the narrow local/offline/read-only schema validator scope by WP67. Resolved outcome ingestion (WP66-D002), calibration report generator (WP66-D003), and paper/live performance metrics (WP66-D004) remain deferred. |
| WP66-D002 | Resolved outcome ingestion not implemented | OPEN | P3 | WP66 defines resolved outcome data field requirements in docs form only. No Polymarket API calls, no network access, no ingestion pipeline, no automated fetch, no credential use, and no external data access is implemented or authorized. | Any WP that ingests resolved outcome data from Polymarket or any external source. | Future approved WP explicitly scopes resolved outcome ingestion with explicit network boundary, credential policy, non-signal enforcement, and full repo-truth update. |
| WP66-D003 | Calibration report generator deferred | OPEN | P3 | WP66 defines calibration metrics and human review labels in docs form only. No calibration report writer, no aggregate metric calculator, no report file generator, and no display layer is added. | Any WP that generates calibration summary reports or aggregate calibration metrics. | Future approved WP explicitly scopes a local/offline calibration report generator as a separate Phase 4 implementation. |
| WP66-D004 | Paper/live performance metrics remain forbidden and deferred | OPEN | P3 | WP66 calibration design explicitly forbids PnL, ROI, expected return, Sharpe, win rate, trade hit rate, fill quality, and execution slippage from calibration scope. Paper/live trading and performance measurement remain blocked behind protected boundaries. | Any WP that adds paper trading, live trading, performance measurement, or profitability metrics to the calibration harness. | Future approved WP must explicitly satisfy all protected-boundary gates before any paper/live behavior or performance metric is added. |
| WP67-D001 | Local resolved outcome fixture loader implemented for local/offline/read-only scope | RESOLVED (WP68 local/offline/read-only fixture loader scope) | P3 | WP67 adds only a local/offline/read-only structural validator. WP68 implements `load_resolved_outcome_fixtures` at `src/data_layer/resolved_outcome_fixture_loader.py`, accepting explicit local paths to JSON object files, JSON list files, or direct-child *.json directories. | Any WP that loads resolved outcome fixture files from disk or implements a resolved outcome record reader. | Resolved only for the narrow local/offline/read-only explicit-path fixture loader scope by WP68. API/network ingestion, calibration report generator, and metric computation remain deferred. |
| WP67-D002 | Calibration report generator remains deferred | OPEN | P3 | WP67 adds only a structural validator. WP68 adds only a local fixture loader. No calibration summary report writer, no aggregate calibration metric calculator, no report file generator, and no display layer is implemented or authorized. | Any WP that generates calibration summary reports or aggregate calibration metrics. | Future approved WP explicitly scopes a local/offline calibration report generator as a separate Phase 4 implementation per the WP66 calibration harness design phases. |
| WP67-D003 | Human review label workflow implementation remains deferred | OPEN | P3 | WP67 validates the human_review_usefulness_label field value but does not implement the human review workflow, reviewer assignment, timestamp tracking, or label propagation pipeline. WP68 does not change this. | Any WP that implements a human reviewer workflow, reviewer assignment, or label propagation beyond simple field presence validation. | Future approved WP explicitly scopes the human review label workflow and confirms non-signal boundary. |
| WP67-D004 | Calibration records not used for scoring weight changes until explicit future WP | OPEN | P3 | WP67 validates calibration record structure only. WP68 adds a local fixture loader only. No calibration record is connected to the research priority scorer, no scoring weights are updated based on calibration outcomes, and no feedback loop between calibration and scoring is implemented. | Any WP that uses calibration records to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the calibration-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP68-D001 | Network/API resolved outcome ingestion remains deferred | OPEN | P3 | WP68 adds only a local/offline fixture loader accepting explicit local paths. No Polymarket API calls, no network access, no ingestion pipeline, no automated fetch, no credential use, and no external data access is implemented or authorized. | Any WP that ingests resolved outcome data from Polymarket or any external source. | Future approved WP explicitly scopes resolved outcome ingestion with explicit network boundary, credential policy, non-signal enforcement, and full repo-truth update. |
| WP68-D002 | Calibration report generator remains deferred | OPEN | P3 | WP68 adds only a local/offline fixture loader. No calibration summary report writer, no aggregate metric calculator, no report file generator, and no display layer is added. WP69 adds a local/offline calibration report generator design only (docs/schema/tests); implementation remains deferred. | Any WP that implements a calibration summary report generator or aggregate calibration metric computation. | Future approved WP explicitly scopes local/offline calibration report generator implementation as a separate Phase 6 per the WP66 calibration harness design phases and WP69 design. |
| WP68-D003 | Calibration metric computation remains deferred | OPEN | P3 | WP68 loads and validates calibration record fixtures only. No calibration metric computation, no aggregate score, no resolution quality metric, no research-usefulness rate calculation, and no baseline comparison is performed or added. | Any WP that computes calibration metrics, aggregate scores, or resolution quality rates from loaded fixtures. | Future approved WP explicitly scopes local/offline calibration metric computation with non-signal boundary review. |
| WP68-D004 | Fixture loader is not used for scoring weight changes until explicit future WP | OPEN | P3 | WP68 adds a local fixture loader only. No loaded calibration record is connected to the research priority scorer, no scoring weights are updated based on calibration outcomes, and no feedback loop between the fixture loader and scoring is implemented or authorized. | Any WP that uses loaded calibration records to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the calibration-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP69-D001 | Calibration metric computation implementation remains deferred | RESOLVED (WP70 local/offline/read-only metric computation scope) | P3 | WP69 adds a local/offline calibration report generator design only. WP70 implements `compute_calibration_metrics` and `compute_calibration_metrics_from_load_result` at `src/data_layer/calibration_metric_computation.py` with allowed research-quality metrics only (coverage, missingness, staleness, review burden, bucket distribution, label distribution, excluded count, post-resolution audit count). No report generator, no trading/performance metrics, no network, no file I/O, no credentials. | Resolved only for local/offline/read-only research-quality metric computation scope by WP70. Report generator implementation, human review label workflow, scorer weight changes, and paper/live performance metrics remain deferred (see WP70-D001 through WP70-D004). |
| WP69-D002 | Calibration report generator implementation remains deferred | RESOLVED (WP71 in-memory report object scope) | P3 | WP69 adds a local/offline calibration report generator design only. WP71 implements `build_calibration_report` and `build_calibration_report_from_load_result` at `src/data_layer/calibration_report_generator.py`, building a frozen `LocalCalibrationReport` dataclass using WP70 metrics. No CLI/export/file writer, no network, no credentials, no trading/performance metrics. | Resolved only for local/offline/read-only in-memory report object scope by WP71. CLI/export/file writing, human review label workflow, scoring weight changes, and paper/live performance metrics remain deferred (see WP71-D001 through WP71-D004). |
| WP69-D003 | Human review label workflow implementation remains deferred | OPEN | P3 | WP69 adds a design doc and schema tests only. No human reviewer workflow, no reviewer assignment, no timestamp tracking, no label propagation pipeline, and no review scheduling is implemented or authorized. | Any WP that implements a human reviewer workflow, reviewer assignment, or label propagation beyond simple field presence validation. | Future approved WP explicitly scopes the human review label workflow and confirms non-signal boundary per WP69 design Phase 7. |
| WP69-D004 | Calibration report is not used for scoring weight changes until explicit future WP | OPEN | P3 | WP69 adds a calibration report generator design only. No calibration report is connected to the research priority scorer, no scoring weights are updated based on calibration results, and no feedback loop between the report generator and scoring is implemented or authorized. | Any WP that uses calibration report results to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the calibration-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP70-D001 | Calibration report generator implementation remains deferred | RESOLVED (WP71 in-memory report object scope) | P3 | WP70 adds only local/offline/read-only metric computation. WP71 implements the in-memory `LocalCalibrationReport` at `src/data_layer/calibration_report_generator.py`. No CLI/export/file writer, no dashboard/database, no network, no credentials, no trading/performance metrics. | Resolved only for the local/offline/read-only in-memory report object scope by WP71. CLI/export/file writing remains deferred (WP71-D001). |
| WP70-D002 | Human review label workflow implementation remains deferred | OPEN | P3 | WP70 adds metric computation from the human_review_usefulness_label field but does not implement the human review workflow, reviewer assignment, timestamp tracking, or label propagation pipeline. WP71 does not change this. | Any WP that implements a human reviewer workflow, reviewer assignment, or label propagation beyond simple field presence and counting. | Future approved WP explicitly scopes the human review label workflow and confirms non-signal boundary per WP69 design Phase 7. |
| WP70-D003 | Metric results are not used for scoring weight changes until explicit future WP | OPEN | P3 | WP70 computes research-quality metrics only. WP71 builds a report object from those metrics. No metric result or report result is connected to the research priority scorer, no scoring weights are updated based on metric or report outcomes. | Any WP that uses calibration metric or report results to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the metric-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP70-D004 | Paper/live performance metrics remain forbidden and deferred | OPEN | P3 | WP70 explicitly computes only research-quality and data-completeness metrics. WP71 builds an in-memory report from those metrics. PnL, ROI, expected return, Sharpe, win rate, trade hit rate, fill quality, and execution slippage remain outside calibration scope and forbidden from the metric helper and report generator. Paper/live trading and performance measurement remain blocked behind protected boundaries. | Any WP that adds paper trading, live trading, performance measurement, or profitability metrics to the calibration metric helper, report generator, or calibration harness. | Future approved WP must explicitly satisfy all protected-boundary gates before any paper/live behavior or performance metric is added. |
| WP71-D001 | CLI/export/report writer remains deferred | PARTIALLY_RESOLVED (WP72 explicit manual local export scope only) | P3 | WP71 adds only a local/offline/read-only in-memory report object. WP72 adds an explicit manual local export CLI at `tools/calibration/local_calibration_report_export.py` (JSON and Markdown, stdout or explicit local path, no scheduler, no dashboard/database, no network, no trading). Automated/scheduled export, dashboard/database export, and network ingestion remain deferred (WP72-D001 and WP72-D002). | Any WP that adds a scheduler, dashboard/database export, or network ingestion for calibration reports. | WP72 resolves this for explicit manual local export scope only. |
| WP71-D002 | Human review label workflow implementation remains deferred | OPEN | P3 | WP71 builds a report object that includes the human review usefulness label distribution but does not implement the human review workflow, reviewer assignment, timestamp tracking, or label propagation pipeline. WP72 does not add this. | Any WP that implements a human reviewer workflow, reviewer assignment, or label propagation beyond simple field presence and counting. | Future approved WP explicitly scopes the human review label workflow and confirms non-signal boundary per WP69 design Phase 7. |
| WP71-D003 | Report output is not used for scoring weight changes until explicit future WP | OPEN | P3 | WP71 builds a research-usefulness report object only. WP72 adds only export of that object. No report result is connected to the research priority scorer, no scoring weights are updated based on report outcomes, and no feedback loop between the report generator and scoring is implemented or authorized. | Any WP that uses calibration report results to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the report-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP71-D004 | Paper/live performance metrics remain forbidden and deferred | OPEN | P3 | WP71 adds only a local/offline/read-only in-memory report object covering research-quality metrics only. WP72 adds only export of that object. PnL, ROI, expected return, Sharpe, win rate, trade hit rate, fill quality, and execution slippage remain outside calibration scope and forbidden from the report generator and export tool. Paper/live trading and performance measurement remain blocked behind protected boundaries. | Any WP that adds paper trading, live trading, performance measurement, or profitability metrics to the calibration report generator, metric helper, export tool, or calibration harness. | Future approved WP must explicitly satisfy all protected-boundary gates before any paper/live behavior or performance metric is added. |
| WP72-D001 | Scheduled/automated calibration report generation remains deferred | OPEN | P3 | WP72 adds explicit manual local export only. No scheduler, cron job, daemon, polling loop, or automated report generation trigger is implemented or authorized. | Any WP that adds scheduler-driven or automated report generation. | Future approved WP explicitly scopes automated report generation with safety gates and explicit scope authorization. |
| WP72-D002 | Dashboard/database-backed calibration reports remain deferred | OPEN | P3 | WP72 exports to stdout or an explicit local file only. No dashboard, database, report history, or query service is implemented or authorized. | Any WP that adds a dashboard display layer or database-backed report storage for calibration reports. | Future approved WP explicitly scopes dashboard/database report storage after storage and safety requirements are documented. |
| WP72-D003 | Human review label workflow implementation remains deferred | DESIGN_ADDRESSED_WP73_DESIGN_ONLY | P3 | WP72 exports the report object only; the human review label workflow (reviewer assignment, timestamp tracking, label propagation pipeline) is not implemented or authorized. WP73 adds docs/human_review_label_workflow_design.md and a static schema example (design and schema only; no implementation). Implementation remains deferred per WP73-D001 through WP73-D004. | Any WP that implements a human reviewer workflow, reviewer assignment, or label propagation. | Design-addressed by WP73 for design/schema scope only. Implementation of label record validator, fixture loader, report integration, and automated/LLM labeling remain deferred. |
| WP72-D004 | Report output is not used for scoring weight changes until explicit future WP | OPEN | P3 | WP72 adds only export of the research-usefulness report object. No calibration report export result is connected to the research priority scorer, no scoring weights are updated, and no feedback loop is implemented or authorized. | Any WP that uses calibration report export results to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the report-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP73-D001 | Human review label record validator remains deferred | RESOLVED | P3 | WP73 adds design and schema only. No label record validator, no structural validator implementation, no field-enforcement code, and no validator test suite is implemented. | Any WP that validates human review label records against the WP73 schema. | Resolved by WP74: validate_human_review_label_record implemented in src/data_layer/human_review_label_validation.py with 77 focused tests; local/offline/read-only, stdlib-only, no file I/O, no network, no automation. |
| WP73-D002 | Human review label fixture loader remains deferred | OPEN | P3 | WP73 adds design and schema only. No fixture loader, no file reader for label records, no JSON/JSONL label reader, and no directory scanner for label fixtures is implemented or authorized. | Any WP that loads human review label records from explicit local paths. | Future approved WP explicitly scopes a local/offline/read-only label fixture loader after WP73-D001 label validator is implemented. |
| WP73-D003 | Label/report integration remains deferred | OPEN | P3 | WP73 adds design and schema only. No integration of human review labels into calibration reports, no join of label records with calibration records, no label aggregate in report sections, and no report exporter change is implemented or authorized. | Any WP that integrates human review labels into calibration report output or the calibration metric/report generator. | Future approved WP explicitly scopes label/report integration after WP73-D001 (validator) and WP73-D002 (fixture loader) are implemented. |
| WP73-D004 | Automated or LLM-based labeling remains forbidden and deferred | OPEN | P3 | WP73 defines only a manual human review label workflow. No automated label generation, no LLM/Hermes-based labeling, no automated workflow state transitions, and no AUTO_LABELED_BY_LLM state is implemented or authorized. Any automation requires separate explicit approval, risk review, protected-boundary review, and a separate dedicated WP. | Any WP that proposes automated label generation, LLM-based labeling, or automated label workflow state transitions. | Future approved WP with explicit authorization, separate boundary review, and separate user approval. |
| WP74-D001 | Human review label fixture loader remains deferred | RESOLVED | P3 | WP74 adds a local/offline/read-only validator only. No fixture loader, no file reader for label records, no JSON/JSONL label reader, and no directory scanner for label fixtures is implemented or authorized. | Any WP that loads human review label records from explicit local paths. | Resolved by WP75: load_human_review_label_fixtures implemented in src/data_layer/human_review_label_fixture_loader.py with 47 focused tests; local/offline/read-only, stdlib-only, no file writes, no network, no automation, no LLM labeling. |
| WP74-D002 | Label/report integration remains deferred | OPEN | P3 | WP74 adds a local/offline/read-only validator only. WP75 adds a local/offline/read-only fixture loader only. No integration of human review labels into calibration reports, no join of label records with calibration records, no label aggregate in report sections, and no report exporter change is implemented or authorized. | Any WP that integrates human review labels into calibration report output or the calibration metric/report generator. | Future approved WP explicitly scopes label/report integration after WP75 (fixture loader) is implemented. |
| WP74-D003 | Label editor remains deferred | OPEN | P3 | WP74 adds a local/offline/read-only validator only. WP75 adds a local/offline/read-only fixture loader only. No label editor, no label writer, no label update function, and no label mutation interface is implemented or authorized. | Any WP that implements a human review label editor or label writer. | Future approved WP explicitly scopes a local/offline label editor with safety boundary review and explicit authorization. |
| WP74-D004 | Automated or LLM-based labeling remains forbidden and deferred | OPEN | P3 | WP74 adds a local/offline/read-only validator that explicitly rejects automated workflow states (AUTO_LABELED_BY_LLM, AUTO_LABELED, LLM_LABELED) and forbidden automation keys/values. WP75 adds a local/offline/read-only fixture loader that does not automate, LLM-label, or compute trading metrics. No automated label generation, no LLM/Hermes-based labeling, no automated workflow state transitions, and no AUTO_LABELED_BY_LLM state is implemented or authorized. | Any WP that proposes automated label generation, LLM-based labeling, or automated label workflow state transitions. | Future approved WP with explicit authorization, separate boundary review, and separate user approval. |
| WP75-D001 | Label/report integration remains deferred | OPEN | P3 | WP75 adds a local/offline/read-only fixture loader only. No integration of human review labels into calibration reports, no join of label records with calibration records, no label aggregate in report sections, and no report exporter change is implemented or authorized. | Any WP that integrates human review labels into calibration report output or the calibration metric/report generator. | Future approved WP explicitly scopes label/report integration with non-signal boundary review and explicit authorization. |
| WP75-D002 | Human review label editor remains deferred | OPEN | P3 | WP75 adds a local/offline/read-only fixture loader only. No label editor, no label writer, no label update function, and no label mutation interface is implemented or authorized. | Any WP that implements a human review label editor or label writer. | Future approved WP explicitly scopes a local/offline label editor with safety boundary review and explicit authorization. |
| WP75-D003 | Automated or LLM-based labeling remains forbidden and deferred | OPEN | P3 | WP75 adds a local/offline/read-only fixture loader only. No automated label generation, no LLM/Hermes-based labeling, no automated workflow state transitions, and no AUTO_LABELED_BY_LLM state is implemented or authorized. | Any WP that proposes automated label generation, LLM-based labeling, or automated label workflow state transitions. | Future approved WP with explicit authorization, separate boundary review, and separate user approval. |
| WP75-D004 | Labels are not used for scoring weight changes until explicit future WP | OPEN | P3 | WP75 adds a local/offline/read-only fixture loader only. No loaded human review label record is connected to the research priority scorer, no scoring weights are updated based on label outcomes, and no feedback loop between the fixture loader and scoring is implemented or authorized. | Any WP that uses loaded human review label records to update scorer weights, thresholds, or bucket boundaries. | Future approved WP explicitly scopes the label-to-scoring feedback loop with non-signal boundary review and protected-boundary gates. |
| WP76-D001 | Wallet intelligence architecture/registry/profile contract remains deferred | RESOLVED (WP77 docs/schema/tests design scope) | P3 | WP76 locked the wallet intelligence roadmap in docs/tests form only. WP77 adds the docs/schema/tests-only wallet architecture, registry/profile, and signal-contract design layer. | Any future WP that implements a wallet registry, wallet profile validator, wallet signal validator, loader, profiler, or integration. | Resolved only for WP77 design scope; implementation remains deferred through WP77-D001 through WP77-D008. |
| WP76-D002 | Wallet trade event schema/local loader/validator remains deferred | RESOLVED (WP78 local/offline/read-only scope) | P3 | WP76 locked the roadmap only. WP78 adds the wallet trade event snapshot schema doc, static example, validator, and explicit-path local fixture loader. | Any future expansion beyond local fixture schema/loading, including wallet API/network ingestion, monitoring, scoring, copyability, or integration. | Resolved only for WP78 local/offline/read-only schema, static example, validator, and explicit-path fixture loader scope; no network ingestion. |
| WP76-D003 | Wallet skill/niche profiler and research queue integration remain deferred | RESOLVED (WP79 local/offline/read-only advisory profiling and annotation scope) | P3 | WP76 locks the roadmap only. No wallet skill classifier, no niche profiler, and no research queue integration is designed or implemented. WP79 resolved this for advisory profiling and annotation scope only. | Any WP that implements a wallet skill profiler or integrates wallet signals into the research queue. | Resolved by WP79: build_wallet_signal_research_profiles and build_wallet_research_queue_annotations implemented; produces deterministic advisory frozen dataclasses; local/offline/read-only, stdlib-only, no network, no buyxsell signals, no scoring weight changes. |
| WP76-D004 | Copyability delay simulator and wallet intelligence report generator remain deferred | RESOLVED (WP80 docs/schema/tests-only copyability delay simulator design and report contract scope) | P3 | WP76 locks the roadmap only. No copyability delay simulator, no PnL delay evaluation, and no wallet intelligence report generator is designed or implemented. WP80 resolved this for docs/schema/tests-only design and contract scope only. | Any WP that designs or implements a copyability delay simulator or wallet intelligence report generator. | Resolved for docs/schema/tests-only design scope by WP80. Copyability delay implementation deferred to WP81. Report generator implementation deferred to WP82. No live execution; no trading signals. |
| WP76-D005 | Wallet signal paper strategy contract remains deferred | OPEN | P3 | WP76 locks the roadmap only. No wallet signal paper trading contract, no paper strategy implementation, and no live strategy implementation is authorized. WP83 is the next candidate. | Any WP that defines a wallet-signal-driven paper trading strategy contract or paper/live execution behavior. | Future approved WP83 explicitly scopes a paper-trading candidate generation contract only; requires prior copyability evidence from WP81; no live execution without full live boundary conditions. |
| WP76-D006 | Any direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP76 explicitly forbids direct wallet-signal-driven live execution. No order placement, no position sizing, no risk override, no parameter auto-change, and no live trading authority is granted by this or any future wallet intelligence WP until all live boundary conditions are satisfied: delayed-copy evidence, paper-trading evidence, risk-gate approval, explicit live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. | Any WP that proposes wallet-signal-driven order placement, live execution, or live trading. | All live boundary conditions from docs/wallet_intelligence_research_signal_roadmap.md Section M must be satisfied before any live-trading WP is proposed. |
| WP76-D007 | Automated copy-trading remains forbidden until delayed-copy evidence, paper-trading proof, risk review, and live authorization exist | OPEN | P0 | WP76 explicitly classifies automatic copy-trading as a forbidden behavior. No wallet signal may trigger automatic trade entry, exit, position sizing, or order placement without the full evidence chain and explicit user authorization. | Any WP that proposes automatic copy-trading, automatic position mirroring, or automated wallet-following strategy without the full evidence chain. | Future WP that proposes copy-trading must demonstrate delayed-copy evidence (WP80+), paper-trading proof (WP81+), risk-gate review, and explicit user authorization documented in repo truth. |
| WP77-D001 | Wallet trade event snapshot schema/local loader/validator remains deferred | RESOLVED (WP78 local/offline/read-only scope) | P3 | WP77 added architecture and static examples only. WP78 adds local/offline/read-only wallet trade event snapshot schema, static example, validator, and explicit-path fixture loader. | Any future expansion beyond local fixture schema/loading, including wallet API/network ingestion, monitoring, scoring, copyability, report generation, or integration. | Resolved only for WP78 local/offline/read-only schema, static example, validator, and explicit-path fixture loader scope; no network ingestion. |
| WP77-D002 | Wallet skill/niche profiler remains deferred | OPEN | P3 | WP77 defines profile fields and signal categories only. No profiler, classification logic, or wallet skill computation is implemented. | Any WP that classifies wallet skill, niche, category specialization, or timing quality from wallet event records. | Future approved WP79 explicitly scopes local/offline/read-only profiling from validated local fixtures. |
| WP77-D003 | Wallet research queue integration remains deferred | OPEN | P3 | WP77 defines advisory research-priority effects only. It does not integrate wallet signals into the research queue, scorer weights, reports, or advisory consumer. | Any WP that uses wallet signals to alter research queue output, report output, or scoring behavior. | Future approved WP79 or successor explicitly scopes advisory-only research queue integration and preserves non-signal boundaries. |
| WP77-D004 | Copyability delay simulator remains deferred | RESOLVED (WP80 docs/schema/tests-only copyability delay simulator design scope) | P3 | WP77 defines copyability statuses and delay-window concepts only. No simulator, delayed-copy computation, PnL estimate, or execution-realism model is implemented. WP80 resolved this for docs/schema/tests-only design scope. | Any WP that evaluates delayed copyability or simulated follower outcomes. | Resolved for design scope by WP80 (docs/wallet_copyability_delay_simulator_design.md). Copyability delay implementation deferred to WP81. |
| WP77-D005 | Wallet intelligence report generator remains deferred | RESOLVED (WP80 docs/schema/tests-only wallet intelligence report contract scope) | P3 | WP77 adds no report generator, export, dashboard, or advisory-consumer handoff. WP80 resolved this for docs/schema/tests-only report contract scope. | Any WP that generates wallet intelligence reports or exports. | Resolved for contract design scope by WP80 (docs/wallet_intelligence_report_contract.md). Report generator implementation deferred to WP82. |
| WP77-D006 | Wallet signal paper strategy contract remains deferred | OPEN | P3 | WP77 forbids wallet signals as trade instructions and does not define paper-trading candidate generation. | Any WP that defines wallet-signal-driven paper-trading candidate contracts or paper strategy behavior. | Future approved WP83 explicitly scopes a paper strategy contract after copyability evidence; no live execution. |
| WP77-D007 | Any wallet API/network ingestion remains forbidden until explicit future authorization | OPEN | P0 | WP77 is docs/schema/tests-only and does not add network ingestion, wallet API clients, credentials, authenticated endpoints, scheduler, or bot loop. | Any WP proposing wallet API access, network ingestion, monitoring, polling, or external wallet data source integration. | Future approved WP explicitly authorizes the network/API boundary and satisfies security, credential, rate-limit, and protected-boundary gates. |
| WP77-D008 | Any direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP77 repeats that wallet signals are advisory-only and must not control order placement, cancellations, position sizing, risk override, parameter changes, or live execution. | Any WP proposing wallet-driven order placement, cancellation, position sizing, risk override, parameter auto-change, or live execution. | Future approved live-trading WP satisfies delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. |
| WP78-D001 | Wallet skill/niche profiler remains deferred | RESOLVED (WP79 local/offline/read-only advisory profiling scope) | P3 | WP78 validates and loads local wallet trade event fixtures only. It does not classify wallet skill, niche, category specialization, timing quality, or rank wallets. | Any WP that classifies wallet skill or niche from wallet event records. | Resolved by WP79: build_wallet_signal_research_profiles implemented in src/data_layer/wallet_signal_research_profile.py; produces deterministic advisory WalletSignalResearchProfile frozen dataclasses; local/offline/read-only, stdlib-only, no network, no copyability PnL, no buy/sell signals, no scoring weight changes. |
| WP78-D002 | Wallet research queue integration remains deferred | RESOLVED (WP79 local/offline/read-only advisory annotation scope) | P3 | WP78 does not connect wallet event fixtures to the research queue, scorer weights, reports, advisory consumer, or market prioritization behavior. | Any WP that uses wallet event records or wallet signals to alter research queue output, report output, or scoring behavior. | Resolved by WP79: build_wallet_research_queue_annotations implemented in src/data_layer/wallet_signal_research_profile.py; produces deterministic advisory WalletResearchQueueAnnotation frozen dataclasses; advisory-only, does not modify scoring weights, does not create trade signals, does not create position sizing outputs. |
| WP78-D003 | Copyability delay simulator remains deferred | RESOLVED (WP80 docs/schema/tests-only copyability delay simulator design scope) | P3 | WP78 does not simulate delayed copying, follower outcomes, execution realism, spread/slippage/fee effects, or copyability PnL. WP80 resolved this for docs/schema/tests-only design scope. | Any WP that evaluates delayed copyability or simulated follower outcomes. | Resolved for design scope by WP80. Copyability delay implementation deferred to WP81. |
| WP78-D004 | Wallet intelligence report generator remains deferred | RESOLVED (WP80 docs/schema/tests-only wallet intelligence report contract scope) | P3 | WP78 adds no report generator, export, dashboard, or advisory-consumer handoff. WP80 resolved this for docs/schema/tests-only report contract scope. | Any WP that generates wallet intelligence reports or exports. | Resolved for contract design scope by WP80. Report generator implementation deferred to WP82. |
| WP78-D005 | Wallet signal paper strategy contract remains deferred | OPEN | P3 | WP78 forbids wallet event observations as trade instructions and does not define paper-trading candidate generation. | Any WP that defines wallet-signal-driven paper-trading candidate contracts or paper strategy behavior. | Future approved WP83 explicitly scopes a paper strategy contract after copyability evidence; no live execution. |
| WP78-D006 | Wallet API/network ingestion remains forbidden until explicit future authorization | OPEN | P0 | WP78 accepts only explicit local JSON fixtures. It adds no network ingestion, wallet API client, credentials, authenticated endpoints, monitoring, polling, scheduler, or bot loop. | Any WP proposing wallet API access, network ingestion, monitoring, polling, or external wallet data source integration. | Future approved WP explicitly authorizes the network/API boundary and satisfies security, credential, rate-limit, and protected-boundary gates. |
| WP78-D007 | Direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP78 repeats that wallet trade event observations are advisory-only and must not control order placement, cancellations, position sizing, risk override, parameter changes, or live execution. | Any WP proposing wallet-driven order placement, cancellation, position sizing, risk override, parameter auto-change, or live execution. | Future approved live-trading WP satisfies delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. |
| WP79-D001 | Copyability delay simulator remains deferred | RESOLVED (WP80 docs/schema/tests-only copyability delay simulator design scope) | P3 | WP79 classifies advisory wallet signal profiles and annotations from local fixtures only. It does not simulate delayed copying, follower outcomes, execution realism, spread/slippage/fee effects, or copyability PnL. WP80 resolved this for docs/schema/tests-only design scope. | Any WP that evaluates delayed copyability or simulated follower outcomes. | Resolved for design scope by WP80. Copyability delay implementation deferred to WP81. |
| WP79-D002 | Wallet intelligence report generator remains deferred | RESOLVED (WP80 docs/schema/tests-only wallet intelligence report contract scope) | P3 | WP79 adds only advisory classification logic. It adds no report generator, export, dashboard, or advisory-consumer handoff. WP80 resolved this for docs/schema/tests-only report contract scope. | Any WP that generates wallet intelligence reports or exports. | Resolved for contract design scope by WP80. Report generator implementation deferred to WP82. |
| WP79-D003 | Wallet signal paper strategy contract remains deferred | OPEN | P3 | WP79 forbids wallet signal profiles as trade instructions and does not define paper-trading candidate generation. | Any WP that defines wallet-signal-driven paper-trading candidate contracts or paper strategy behavior. | Future approved WP83 explicitly scopes a paper strategy contract after copyability evidence; no live execution. |
| WP79-D004 | Wallet API/network ingestion remains forbidden until explicit future authorization | OPEN | P0 | WP79 accepts only validated local WP78 records. It adds no network ingestion, wallet API client, credentials, authenticated endpoints, monitoring, polling, scheduler, or bot loop. | Any WP proposing wallet API access, network ingestion, monitoring, polling, or external wallet data source integration. | Future approved WP explicitly authorizes the network/API boundary and satisfies security, credential, rate-limit, and protected-boundary gates. |
| WP79-D005 | Direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP79 repeats that wallet signal research profiles and annotations are advisory-only and must not control order placement, cancellations, position sizing, risk override, parameter changes, or live execution. | Any WP proposing wallet-driven order placement, cancellation, position sizing, risk override, parameter auto-change, or live execution. | Future approved live-trading WP satisfies delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. |
| WP79-D006 | Scoring weight changes from wallet profiles remain deferred | OPEN | P3 | WP79 adds advisory annotation objects only. No research_priority_score weights are modified based on wallet signal profiles or annotations. | Any WP that connects wallet signal profiles to scorer weight changes. | Future approved WP explicitly scopes scoring integration with non-signal boundary review and protected-boundary gates. |
| WP80-D001 | Copyability delay evaluation implementation remains deferred | RESOLVED (WP81 local/offline/read-only evaluator implementation scope) | P3 | WP80 is docs/schema/tests-only. No copyability delay simulator implementation, no delayed-copy computation, no PnL estimate, and no execution-realism model is implemented. WP81 resolved this for local/offline/read-only evaluator implementation scope only. | Any WP that evaluates delayed copyability from local fixtures. | Resolved for local/offline/read-only evaluator scope by WP81 (src/data_layer/wallet_copyability_delay_evaluation.py). Report generator implementation deferred to WP82. |
| WP80-D002 | Wallet intelligence report generator implementation remains deferred | RESOLVED (WP82 local/offline/read-only report generator implementation scope) | P3 | WP80 defines the report contract only. No report generator, no export CLI, no dashboard, and no advisory-consumer handoff is implemented. WP82 resolved this for local/offline/read-only in-memory report generator scope only. | Any WP that generates wallet intelligence reports. | Resolved for local/offline/read-only in-memory report generator scope by WP82 (src/data_layer/wallet_intelligence_report_generator.py). Export CLI, dashboard, and live execution remain deferred. |
| WP80-D003 | Wallet signal paper strategy contract remains deferred | RESOLVED (WP83 contract-definition scope only) | P3 | WP80 is docs/schema/tests-only and does not define paper-trading candidate generation. No paper strategy contract, no paper strategy implementation, and no live strategy implementation is authorized. | Any WP that defines a wallet-signal-driven paper trading strategy contract or paper/live execution behavior. | Resolved for contract-definition scope only by WP83 (docs/wallet_signal_paper_strategy_contract.md, docs/schemas/wallet_signal_paper_strategy_contract_v1.example.json, tests/test_wallet_signal_paper_strategy_contract_docs.py). Paper strategy implementation and all live account access remain deferred. |
| WP80-D004 | Wallet API/network ingestion remains forbidden until explicit future authorization | OPEN | P0 | WP80 is docs/schema/tests-only. It adds no network ingestion, wallet API client, credentials, authenticated endpoints, monitoring, polling, scheduler, or bot loop. | Any WP proposing wallet API access, network ingestion, monitoring, polling, or external wallet data source integration. | Future approved WP explicitly authorizes the network/API boundary and satisfies security, credential, rate-limit, and protected-boundary gates. |
| WP80-D005 | Direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP80 repeats that copyability delay design and report contract are advisory-only and must not control order placement, cancellations, position sizing, risk override, parameter changes, or live execution. | Any WP proposing wallet-driven order placement, cancellation, position sizing, risk override, parameter auto-change, or live execution. | Future approved live-trading WP satisfies delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. |
| WP80-D006 | Human review label and calibration record join remains deferred | OPEN | P3 | WP80 is docs/schema/tests-only and does not define or implement the join between human review labels and calibration records. | Any WP that joins human review label records with calibration records. | Future approved WP84 explicitly scopes join design or implementation with non-signal boundary review and protected-boundary gates. |

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

## WP20 AI-Agent Read-Only Boundary And Hermes Integration Policy Update

WP20 adds `docs/ai_agent_integration_policy.md`, `docs/hermes_readonly_boundary.md`, `docs/agent_model_registry.md`, repo-truth updates, and tests for the AI-agent/Hermes boundary.

WP20 is documentation/test-only. It records that future AI-agent and Hermes capabilities are read-only/advisory unless a later repo-truth decision changes the boundary. It adds no Hermes installation, Hermes runtime dependency, agent runtime, agent CLI, scheduler, daemon, memory store, context exporter, report generator, network polling, credential handling, provider SDK, account connection, strategy signal, trade proposal, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

The fully autonomous trading agent remains EXCLUDED_FOR_NOW. Agent-controlled execution, credentials, signing, autonomous order placement, autonomous order cancellation, scheduler or bot-loop activation, autonomous parameter application, and live authorization remain FORBIDDEN.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed. WP10-D001 remains OPEN because WP20 does not declare snapshot schema production-stable. WP10-D002 remains OPEN because WP20 does not add database-backed snapshot storage. WP11-D001 and WP11-D002 remain OPEN. WP12-D001 remains OPEN because quality gates remain research-only. WP12-D002 remains OPEN because reports remain local files only and not dashboard-backed. WP13-D001 and WP13-D002 remain OPEN. WP20-D001, WP20-D002, and WP20-D003 are added for future manual setup, context export, and performance-log prerequisites.

## WP21 Read-Only Agent Context Export Schema Update

WP21 adds `docs/agent_context_export_schema.md`, repo-truth updates, and tests for a future read-only AI-agent context export schema.

WP21 is schema/docs/test-only. It defines required top-level fields, provenance rules, redaction policy, staleness policy, human-review requirements, allowed advisory uses, and forbidden use boundaries for a future local context package. It adds no local context exporter, agent runtime, agent CLI, scheduler, daemon, memory store, report generator, network polling, credential handling, provider SDK, account connection, strategy signal, trade proposal, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP20-D002 is resolved for schema-contract scope only because WP21 defines and tests the read-only context export schema without runtime Hermes dependency or execution authority. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents. WP21-D001 and WP21-D002 are added because the local exporter and agent context report generator remain not implemented.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed. WP10-D001 remains OPEN because WP21 does not declare snapshot schema production-stable. WP10-D002 remains OPEN because WP21 does not add database-backed snapshot storage. WP11-D001 and WP11-D002 remain OPEN. WP12-D001 remains OPEN because quality gates remain research-only. WP12-D002 remains OPEN because reports remain local files only and not dashboard-backed. WP13-D001 and WP13-D002 remain OPEN.

## WP22 Codex Workflow Hardening And Report-Back Discipline Update

WP22 adds `CODEX_START_HERE.md`, Codex workflow guidance under `docs/ai/codex/`, stricter PR/work-package templates, review/testing guidance, repo-truth updates, and tests for the workflow docs.

WP22 is documentation/test-only. It adds no local agent context exporter, agent report generator, Hermes installation, Hermes runtime dependency, agent runtime, agent CLI, scheduler, daemon, memory store, network polling, credential handling, provider SDK, account connection, strategy signal, trade proposal, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP21-D001 remains OPEN because the local agent context exporter is not implemented. WP21-D002 remains OPEN because the agent context report generator is not implemented. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed. WP10-D001 remains OPEN because WP22 does not declare snapshot schema production-stable. WP10-D002 remains OPEN because WP22 does not add database-backed snapshot storage. WP11-D001 and WP11-D002 remain OPEN. WP12-D001 remains OPEN because quality gates remain research-only. WP12-D002 remains OPEN because reports remain local files only and not dashboard-backed. WP13-D001 and WP13-D002 remain OPEN.

WP3-D001 (gitleaks): rerun this WP - gitleaks scan PASS, no findings. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

## WP23 Local Read-Only Agent Context Exporter Update

WP23 adds `src/data_layer/agent_context/`, `tools/polymarket/export_agent_context.py`, focused tests, `docs/agent_context_exporter.md`, and repo-truth updates for a local/offline/read-only JSON context exporter.

The exporter reads only fixed allowlisted tracked docs by default and may include metadata only for allowlisted ignored local report paths when explicitly requested. Output is written only when an explicit path under ignored `local_data/agent_context_exports/` is provided. Default CLI behavior is offline, no-network, no-write, and safe.

WP23 adds no Hermes installation, Hermes runtime dependency, agent runtime, report generator, scheduler, daemon, memory store, network polling, credentials, account connection, provider SDK, strategy signal, trade proposal, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP21-D001 is RESOLVED only for the tested local/offline/read-only exporter scope. WP21-D002 remains OPEN because no agent context report generator is implemented. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun/assessed this WP. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP unless explicitly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit availability must be honestly reported by validation.

## WP24 Read-Only Agent Context Exporter Operator Runbook Update

WP24 adds `docs/agent_context_exporter_operator_runbook.md`, doc tests, and repo-truth cross-references for safe manual operation of the WP23 local/offline/read-only exporter.

WP24 is documentation/test-only. It adds no exporter runtime behavior change, Hermes installation, Hermes runtime dependency, agent runtime, agent report generator, scheduler, daemon, memory store, network polling, credentials, account connection, provider SDK, strategy signal, trade proposal, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP21-D002 remains OPEN because no agent context report generator is implemented. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun in WP24; available-check wrapper reports PASS. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

## WP25 Local Read-Only Analyst Report Generator Update

WP25 adds `src/data_layer/agent_context/report_models.py`, `src/data_layer/agent_context/report_generator.py`, `tools/polymarket/generate_agent_context_report.py`, focused tests, `docs/agent_context_report_generator.md`, and repo-truth updates for deterministic local/offline/read-only report generation from WP23-compatible context exports.

The generator reads context JSON only from `local_data/agent_context_exports/` and writes Markdown or JSON reports only under ignored `local_data/agent_context_reports/` when explicit output paths are provided. Default CLI behavior is offline, no-network, no-write, and safe.

WP25 adds no Hermes installation, Hermes runtime dependency, LLM dependency, agent runtime, scheduler, daemon, memory store, network polling, credentials, account connection, provider SDK, strategy signal, trade proposal, parameter recommendation, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP21-D002 is RESOLVED only for the tested deterministic local/offline/read-only report-generator scope. WP25-D001 is added because a dedicated analyst report operator runbook remains future work. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun in WP25; available-check wrapper reports PASS. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

## WP26 Read-Only Analyst Report Operator Runbook Update

WP26 adds `docs/agent_context_report_operator_runbook.md`, focused doc tests, and repo-truth cross-references for safe manual operation of the WP25 deterministic local/offline/read-only analyst report generator.

WP26 is documentation/test-only. It adds no report-generator runtime behavior change, exporter runtime behavior change, Hermes installation, Hermes runtime dependency, LLM dependency, agent runtime, scheduler, daemon, memory store, network polling, credentials, account connection, provider SDK, strategy signal, trade proposal, parameter recommendation, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP25-D001 is RESOLVED only for the tested local/offline/read-only analyst report operator runbook scope. WP20-D001 remains OPEN because Hermes installation/setup is not performed. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun/assessed in WP26. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP unless explicitly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit availability must be honestly reported by validation.

## WP30 Local Diff And Scope Summary Helper Implementation Update

WP30 adds `tools/git/diff_scope_summary.py`, `tests/tools/git/test_diff_scope_summary.py`,
`docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md`, and repo-truth updates implementing the
local/offline/read-only diff scope summary helper designed in WP29.

WP30 is local-tooling/implementation-only. It adds no Hermes installation, Hermes runtime
dependency, LLM dependency, agent runtime, report generator, scheduler, daemon, memory store,
network polling, credentials, account connection, provider SDK, strategy signal, trade proposal,
paper trading, live trading, execution, risk, OMS, reconciliation, database, dashboard,
dependency file, or lock file.

WP29-D001 is RESOLVED for the tested local/offline/read-only stdlib helper scope. The helper
exists at `tools/git/diff_scope_summary.py`, 79 tests pass, and all open design questions from
WP29 Section 12 are resolved.

WP28-D001 remains OPEN because command-output compression, code indexing, and memory snapshot
helpers are not implemented. WP30 implements only the diff/scope summary helper.

WP30-D001 and WP30-D002 are added for the remaining unimplemented token-efficiency helpers.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP30. WP27-D001 remains
OPEN — not changed by WP30. WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain
OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP30. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/`
not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP;
no project dependency added and pip-audit was unavailable/skipped.

| WP30-D001 | Command-output compression helper not implemented | OPEN | P3 | WP30 implements only the diff/scope summary helper. Command-output compression is part of the WP28-D001 token-efficiency helper set but was not scoped into WP30. | Any implementation of command-output compression helper tooling. | Future approved design WP defines the helper, scope, stdlib-only constraints, and safety gates; implementation WP follows after design approval. |
| WP30-D002 | Code indexing / blast-radius helper not implemented | RESOLVED (WP34) | P3 | WP30 implements only the diff/scope summary helper. Code indexing and blast-radius analysis are part of the WP28-D001 token-efficiency helper set but were not scoped into WP30. | Resolved by WP34: local/offline/read-only stdlib helper implemented at tools/git/code_blast_radius.py with focused tests. | Resolved in WP34. Persistent index mode remains deferred (WP34-D001). |

## WP31 Validation Output Summary Helper Design Update

WP31 adds `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md`,
`tests/test_validation_output_summary_helper_design_docs.py`, and repo-truth updates for the
design of a future local/offline/read-only validation-output summary helper.

WP31 is documentation/design/test-only. It adds no helper implementation, no command runner,
no command-output compression, no code indexing, no memory store, no Hermes installation,
no Hermes runtime dependency, no agent runtime, no scheduler, no daemon, no network polling,
no credentials, no provider SDK, no strategy signal, no trade proposal, no paper trading,
no live trading, no execution, no risk, no OMS, no reconciliation, no database, no dashboard,
no dependency file, and no lock file.

WP28-D001 remains OPEN because token-efficiency helper tooling (command-output compression,
validation-output summary, code indexing, memory snapshot) is still not implemented. WP31
contributes the validation-output summary design to the design-first gate, but does not
implement it.

WP30-D001 remains OPEN because command-output/validation-output compression tooling is still
not implemented.

WP30-D002 remains OPEN because code indexing helper is still not implemented.

WP31-D001 is added because the validation-output summary helper implementation is not started;
it requires a separate approved implementation WP.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP31. WP27-D001 remains
OPEN — not changed by WP31. WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain
OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP31; binary absent in this environment, UNAVAILABLE/SKIPPED.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was
unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and
pip-audit was unavailable/skipped.

| WP31-D001 | Validation-output summary helper implementation not started | RESOLVED | P3 | WP31 defines the design for a future local/offline/read-only validation-output summary helper but does not implement it. An approved implementation WP is required before any code is written. | Any implementation of the validation-output summary helper. | RESOLVED by WP32: stdlib-only helper implemented at `tools/validation/validation_output_summary.py`; 73 focused tests pass; open design questions from WP31 Section 15 resolved. |
| WP32-D001 | Runner mode remains forbidden and unimplemented | OPEN | P3 | WP32 implements parser + metadata mode only. Runner mode (subprocess-based command execution) remains forbidden and is not implemented in WP32 or any prior WP. | Any future implementation of runner mode in the validation output summary helper. | Future approved implementation WP explicitly scopes runner mode, defines safety constraints, and adds subprocess execution guards before any runner-mode code is written. |

## WP32 Validation Output Summary Helper Implementation Update

WP32 adds `tools/validation/validation_output_summary.py`,
`tests/tools/validation/test_validation_output_summary.py`,
`docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md`, and repo-truth updates implementing the
local/offline/read-only validation output summary helper designed in WP31.

WP32 is local-tooling/implementation-only. It adds no command runner, no subprocess execution,
no Hermes installation, no Hermes runtime dependency, no LLM dependency, no agent runtime,
no report generator, no scheduler, no daemon, no memory store, no network polling,
no credentials, no account connection, no provider SDK, no strategy signal, no trade proposal,
no paper trading, no live trading, no execution, no risk, no OMS, no reconciliation,
no database, no dashboard, no dependency file, and no lock file.

WP31-D001 is RESOLVED for the tested local/offline/read-only stdlib helper scope. The helper
exists at `tools/validation/validation_output_summary.py`, 73 focused tests pass, all open
design questions from WP31 Section 15 are resolved in Section 17 of the design doc.

WP28-D001 remains OPEN because command-output compression, code indexing, and memory snapshot
helpers are not implemented. WP32 implements only the validation-output summary helper.

WP30-D001 remains OPEN. WP32 implements validation-output summary (narrowing part of the
token-efficiency helper scope), but broader command-output compression tooling remains not
implemented.

WP30-D002 remains OPEN because code indexing / blast-radius helper is still not implemented.

WP32-D001 is added because runner mode (subprocess-based command execution) is forbidden
and remains unimplemented.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP32. WP27-D001 remains
OPEN — not changed by WP32. WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain
OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP32; binary absent in this environment, UNAVAILABLE/SKIPPED.
WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was
unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and
pip-audit was unavailable/skipped.

## WP33 Code Index / Blast-Radius Helper Design Update

WP33 adds `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md`,
`tests/test_code_index_blast_radius_helper_design_docs.py`, and repo-truth
updates for a future advisory code-index / blast-radius helper.

WP33 is documentation/design/test-only. It adds no helper implementation, no
generated index, no code-index generator, no AST or Tree-sitter indexer, no
external indexing tool, no runtime source, no dependency file, no lock file, no
Hermes/LLM/provider behavior, no network behavior, no credentials behavior, no
strategy/trading/execution behavior, and no generated artifact.

WP30-D002 remains OPEN because WP33 provides only design guidance; code-index /
blast-radius helper implementation is not started. WP28-D001 remains OPEN
because memory/status snapshot tooling is not implemented and broader
token-efficiency helper work remains incomplete. WP30-D001 remains OPEN.
WP32-D001 remains OPEN.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP33.
WP27-D001 remains OPEN — not changed by WP33. WP20-D003, WP8-D002, WP16-D002,
WP17-D001, and WP17-D002 remain OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP33. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP34 Code Index / Blast-Radius Helper Implementation Update

WP34 adds `tools/git/code_blast_radius.py` (local/offline/read-only stdlib
helper), `tests/tools/git/test_code_blast_radius.py` (focused tests),
`docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md` (user-facing reference),
and repo-truth updates.

WP34 is a local-tooling implementation WP. It adds no runtime source under
`src/`, no dependency or lock file, no Hermes/LLM/provider behavior, no network
behavior, no credentials, no strategy/trading/execution behavior, and no
generated artifact.

WP30-D002 is RESOLVED for the tested local/offline/read-only stdlib code-index
/ blast-radius helper scope. The helper is implemented at
`tools/git/code_blast_radius.py` with focused tests.

WP28-D001 remains OPEN because command-output compression and memory/status
snapshot helpers are still not implemented. Code indexing is now implemented
(WP34), but the full token-efficiency helper set is not complete.

WP30-D001 remains OPEN because broader command-output compression tooling is
still not implemented.

WP32-D001 remains OPEN because runner mode remains forbidden/unimplemented.

WP34-D001 is added because persistent snapshot/index file mode is not
implemented. On-demand scan only is the implemented mode.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP34-D001 | Persistent snapshot/index file mode not implemented | OPEN | P4 | WP34 implements on-demand scan mode only. Snapshot/index file mode was deferred by design in WP33 Section 4 and confirmed as out of scope for WP34. | Future approved WP explicitly scopes persistent snapshot mode with staleness detection, output path isolation, and advisory-only guards. | Not expected in near term; on-demand mode is sufficient for current token-efficiency goals. |

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP34.
WP27-D001 remains OPEN — not changed by WP34. WP20-D003, WP8-D002, WP16-D002,
WP17-D001, and WP17-D002 remain OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP34. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP35 Memory / Status Snapshot Helper Design Update

WP35 adds `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md`,
`tests/test_memory_status_snapshot_helper_design_docs.py`, and repo-truth
updates for the design of a future local/offline/read-only memory/status
snapshot helper.

WP35 is documentation/design/test-only. It adds no helper implementation, no
snapshot generator, no persistent memory file, no command runner, no network
calls, no Hermes installation, no Hermes runtime dependency, no agent runtime,
no scheduler, no daemon, no credentials, no provider SDK, no strategy signal,
no trade proposal, no paper trading, no live trading, no execution, no risk,
no OMS, no reconciliation, no database, no dashboard, no dependency file, and
no lock file.

WP28-D001 remains OPEN because command-output compression and memory/status
snapshot helpers are not implemented. WP35 contributes the memory/status
snapshot design to the design-first gate, but does not implement it.

WP30-D001 remains OPEN because broader command-output compression tooling is
still not implemented.

WP32-D001 remains OPEN because runner mode remains forbidden/unimplemented.

WP34-D001 remains OPEN because persistent snapshot/index file mode is not
implemented.

WP35-D001 is added because the memory/status snapshot helper implementation
is not started; it requires a separate approved implementation WP.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP35-D001 | Memory/status snapshot helper implementation not started | RESOLVED (WP36) | P3 | WP35 defines the design for a future local/offline/read-only memory/status snapshot helper but does not implement it. | WP36 implements the local/offline/read-only stdlib helper at tools/git/status_snapshot.py with focused tests and advisory-only guards. | Resolved for local/offline/read-only stdlib helper scope only. Markdown output (WP36-D001) and input file hashes (WP36-D002) remain deferred. |

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP35.
WP27-D001 remains OPEN — not changed by WP35. WP20-D003, WP8-D002, WP16-D002,
WP17-D001, and WP17-D002 remain OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP35. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP36 Memory / Status Snapshot Helper Implementation Update

WP36 implements `tools/git/status_snapshot.py`, the local/offline/read-only
memory/status snapshot helper designed in WP35. It adds focused tests at
`tests/tools/git/test_status_snapshot.py` and the user-facing reference at
`docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md`.

WP36 is a local-tooling implementation WP. It adds no command runner, no
network calls, no Hermes installation, no agent runtime, no scheduler, no
daemon, no credentials, no provider SDK, no strategy signal, no trade proposal,
no paper trading, no live trading, no execution, no risk, no database, no
dashboard, no dependency file, and no lock file.

WP35-D001 is resolved for the tested local/offline/read-only stdlib helper
scope. The helper reads only allowlisted repo-truth files, runs no commands,
makes no network calls, writes no file by default, and includes mandatory
advisory-only and repo-truth-verification reminders.

WP28-D001 remains OPEN because command-output compression helper tooling is
not yet implemented. The memory/status snapshot helper narrows WP28-D001 but
does not resolve it.

WP30-D001 remains OPEN because broader command-output compression tooling is
still not implemented.

WP32-D001 remains OPEN because runner mode remains forbidden/unimplemented.

WP34-D001 remains OPEN because persistent snapshot/index file mode is not
implemented for the blast-radius helper.

WP36-D001 is added because Markdown snapshot output is not implemented.
WP36-D002 is added because input file hashes are not implemented.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP35-D001 | Memory/status snapshot helper implementation not started | RESOLVED (WP36) | P3 | WP35 defines the design for a future local/offline/read-only memory/status snapshot helper but does not implement it. | WP36 implements the helper per WP35 design constraints with full pytest and advisory-only guards. | Resolved for local/offline/read-only stdlib helper scope only. |
| WP36-D001 | Markdown snapshot output deferred | OPEN | P4 | WP36 implements text and JSON output only. `--format markdown` exits 2. Markdown output is out of scope for WP36. | Future approved WP explicitly scopes and implements Markdown output. | Not expected in near term. |
| WP36-D002 | Input file hashes deferred | OPEN | P4 | WP36 staleness metadata includes commit SHA, branch, timestamp, schema, and source file list, but not file-level hashes. | Future approved WP implements per-file hash staleness check. | Not expected in near term. |

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP36.
WP27-D001 remains OPEN — not changed by WP36. WP20-D003, WP8-D002, WP16-D002,
WP17-D001, and WP17-D002 remain OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP36. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP37 Token Efficiency Sequence Closeout / Repo Truth Consolidation Update

WP37 adds `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md`,
`tests/test_token_efficiency_sequence_closeout_docs.py`, and narrow repo-truth
updates that consolidate the WP28-WP36 token-efficiency sequence.

WP37 is docs/test-only closeout. It adds no helper implementation, no changes to
`tools/git/diff_scope_summary.py`, `tools/validation/validation_output_summary.py`,
`tools/git/code_blast_radius.py`, or `tools/git/status_snapshot.py`, no runtime
source, no dependency or lock-file change, no generated output, no command
runner, no network behavior, no Hermes installation, no agent runtime, no
scheduler, no database/dashboard work, no credentials, no provider SDK, no
strategy signal, no trade proposal, no paper trading, no live trading, no
execution, no risk, no OMS, and no reconciliation.

WP28-D001 remains OPEN but is narrowed to broader command-output compression
helper tooling. The implemented helper stack now covers diff/scope,
validation-output summarization, code blast-radius, and memory/status snapshot
orientation, but broader command-output compression is still not implemented.

WP30-D001 remains OPEN because broader command-output compression tooling is
still not implemented.

WP32-D001 remains OPEN because validation-output runner mode remains
forbidden/unimplemented.

WP34-D001 remains OPEN because persistent code-index snapshot/index mode is not
implemented.

WP36-D001 remains OPEN because Markdown snapshot output remains deferred.
WP36-D002 remains OPEN because input file hashes for status snapshots remain
deferred.

WP37-D001 is added because WP37 does not resume advisory/product/runtime work.
Any Local Advisory Handoff Package, Hermes, advisory-agent, database, dashboard,
scheduler, polling, strategy, paper-trading, live-trading, wallet/copy-trading,
or official-client runtime continuation requires an explicit user-selected
future WP.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP37-D001 | Advisory/product work not resumed after token-efficiency closeout | RESOLVED (WP38 docs-only handoff selection) | P3 | WP37 is docs/test-only closeout and does not resume advisory-agent, Hermes, product, runtime, database, dashboard, scheduler, polling, strategy, paper-trading, live-trading, wallet/copy-trading, or official-client runtime work. | No runtime/product implementation is authorized by this resolution. | Resolved only for selecting and documenting the local advisory handoff path in WP38; future runtime/product work requires separate approved WPs. |

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP37.
WP27-D001 remains OPEN — not changed by WP37. WP20-D003, WP8-D002, WP16-D002,
WP17-D001, and WP17-D002 remain OPEN and unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP37. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP38 Local Advisory Handoff Package Update

WP38 adds `docs/local_advisory_handoff_package.md`,
`tests/test_local_advisory_handoff_package_docs.py`, and narrow repo-truth
updates for the safe post-WP37 advisory planning bridge.

WP38 is docs/test-only handoff work. It adds no agent runtime, no Hermes
runtime or installation, no LLM/provider SDK, no credentials, no network
polling, no paper trading, no live trading, no order placement/cancellation,
no signing, no account connection, no scheduler/daemon/bot loop, no database,
no dashboard, no deployment, no runtime source, no helper/tool implementation,
no dependency file, no lock file, and no generated output.

WP37-D001 is RESOLVED only for selecting and documenting the local advisory
handoff path. It is not resolved for product/runtime implementation.

WP38-D001 is added because advisory runtime boundary and consumption design is
not implemented in WP38.

WP38-D002 is added because a local advisory consumer prototype is not
implemented in WP38.

WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION. WP27-D001, WP20-D003,
WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and unchanged.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP37-D001 | Advisory/product work not resumed after token-efficiency closeout | RESOLVED (WP38 docs-only handoff selection) | P3 | WP37 did not resume advisory/product/runtime work. WP38 selects and documents the safe local advisory handoff path only. | No runtime/product implementation is authorized by this resolution. | Resolved only for docs-only handoff selection; future runtime/product work requires separate approved WPs. |
| WP38-D001 | Advisory runtime boundary and consumption design not implemented | RESOLVED (WP39 docs-only design completion) | P3 | WP38 records the handoff path but does not design a consumer boundary in detail. WP39 adds the docs-only advisory runtime boundary and consumption design. | No implementation authority is authorized by this resolution. | Resolved only for design completion; future consumer implementation requires a separate approved WP. |
| WP38-D002 | Local advisory consumer prototype not implemented | OPEN | P3 | WP38 does not implement a local advisory consumer prototype. | Future approved WP implements an optional local/offline/read-only deterministic consumer with no LLM, network, Hermes, account, trading, scheduler, database, dashboard, or runtime behavior. | Candidate later WP: WP40 - Local Advisory Consumer Prototype. |

WP3-D001 (gitleaks): rerun/assessed in WP38. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP39 Advisory Runtime Boundary And Consumption Design Update

WP39 adds `docs/advisory_runtime_boundary_consumption_design.md`,
`tests/test_advisory_runtime_boundary_consumption_design_docs.py`, and narrow
repo-truth updates defining the future advisory consumer boundary and local
advisory consumption model.

WP39 is docs/test-only design work. It adds no advisory consumer
implementation, agent runtime, Hermes runtime or installation, LLM/provider SDK,
credentials, network polling, paper trading, live trading, order placement or
cancellation, signing, account connection, scheduler/daemon/bot loop, database,
dashboard, deployment, runtime source, helper/tool implementation, dependency
file, lock file, or generated output.

WP38-D001 is RESOLVED only for docs-only design completion. It is not resolved
for advisory consumer implementation or runtime/product implementation.

WP38-D002 remains OPEN because a local advisory consumer prototype is not
implemented in WP39.

WP39-D001 is added because the local advisory consumer prototype is not
implemented after boundary design.

WP39-D002 is added because the advisory prompt/runbook package is not
implemented.

WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION. WP27-D001, WP20-D003,
WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and unchanged.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP38-D001 | Advisory runtime boundary and consumption design not implemented | RESOLVED (WP39 docs-only design completion) | P3 | WP38 recorded the handoff path but did not design a consumer boundary in detail. WP39 defines it in repo truth. | No implementation authority is authorized by this resolution. | Resolved only for docs-only design completion. |
| WP38-D002 | Local advisory consumer prototype not implemented | OPEN | P3 | WP39 defines the boundary but does not implement a prototype. | Future approved WP implements an optional local/offline/read-only deterministic consumer with no LLM, network, Hermes, account, trading, scheduler, database, dashboard, or runtime behavior. | Candidate next WP: WP40 - Local Advisory Consumer Prototype. |
| WP39-D001 | Local advisory consumer prototype not implemented after boundary design | OPEN | P3 | WP39 is design-only and does not implement the consumer. | Future approved WP40 implements a local/offline/read-only deterministic advisory consumer prototype within the WP39 boundary. | Candidate next WP: WP40 - Local Advisory Consumer Prototype. |
| WP39-D002 | Advisory prompt/runbook package not implemented | OPEN | P3 | WP39 does not create advisory prompts or operator runbooks. | Future approved WP creates docs/tests for advisory prompts/runbooks without runtime, LLM/Hermes authorization, credentials, account access, or trading authority. | Candidate later WP: WP41 - Advisory Prompt/Runbook Package. |

WP3-D001 (gitleaks): rerun/assessed in WP39. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP40 Local Advisory Consumer Prototype Update

WP40 adds `tools/advisory/local_advisory_consumer.py`,
`docs/local_advisory_consumer_prototype.md`,
`tests/tools/advisory/test_local_advisory_consumer.py`, and narrow repo-truth
updates for the deterministic local/offline/read-only advisory consumer
prototype.

WP40 is local tooling / advisory prototype work. It adds no runtime source
under `src/`, no agent runtime, no Hermes runtime or installation,
no LLM/provider SDK, no credentials, no network polling, no paper trading,
no live trading, no order placement or cancellation, no signing, no account
connection, no scheduler/daemon/bot loop, no database, no dashboard,
no deployment, no dependency file, no lock file, and no generated output.

WP38-D002 is RESOLVED only for the deterministic local/offline/read-only local
advisory consumer prototype scope. It is not resolved for runtime, LLM, Hermes,
account, trading, scheduler, database, dashboard, or product implementation.

WP39-D001 is RESOLVED only for the deterministic local/offline/read-only local
advisory consumer prototype scope implemented within the WP39 boundary.

WP39-D002 is RESOLVED only for docs-only advisory prompt/runbook package scope.

WP40-D001 is RESOLVED only for docs-only advisory prompt/runbook package scope.

WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed or
implemented.

WP41-D001 is added because advisory consumer integration review / operator
workflow hardening is not implemented.

WP41-D002 is added because provider/Hermes decision refresh is not performed
after the prompt/runbook package.

WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION. WP27-D001,
WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and
unchanged.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP38-D002 | Local advisory consumer prototype implemented for deterministic local/offline/read-only scope | RESOLVED (WP40 local/offline/read-only prototype) | P3 | WP40 implements `tools/advisory/local_advisory_consumer.py` as an explicit-input-only local advisory consumer prototype. | No runtime/product implementation is authorized by this resolution. | Resolved only for deterministic local/offline/read-only advisory consumer prototype scope; future runtime/product work requires separate approved WPs. |
| WP39-D001 | Local advisory consumer prototype implemented after boundary design | RESOLVED (WP40 local/offline/read-only prototype) | P3 | WP40 implements a deterministic local/offline/read-only advisory consumer prototype within the WP39 boundary. | No runtime/product implementation is authorized by this resolution. | Resolved only for the tested local/offline/read-only prototype under `tools/advisory/local_advisory_consumer.py`; runtime, LLM, Hermes, account, trading, scheduler, database, and dashboard work remain unauthorized. |
| WP39-D002 | Advisory prompt/runbook package implemented for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates human-operated advisory prompt templates and an operator runbook package. | No implementation authority is authorized by this resolution. | Resolved only for docs-only prompt/runbook package scope. |
| WP40-D001 | Advisory prompt/runbook package implemented after prototype for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates advisory prompt templates and an operator runbook package after the WP40 prototype. | No implementation authority is authorized by this resolution. | Resolved only for docs-only prompt/runbook package scope. |
| WP40-D002 | LLM/Hermes/provider integration not designed or implemented | OPEN | P3 | WP40 remains deterministic, local/offline/read-only, and non-LLM. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any integration work. | Candidate later WP only after explicit user selection and repo-truth approval. |
| WP41-D001 | Advisory consumer integration review / operator workflow hardening not implemented | OPEN | P3 | WP41 is docs-only prompt/runbook work and does not harden the local human-operated workflow around the WP40 consumer. | Future approved WP reviews and hardens local advisory consumer/operator workflow boundaries. | Candidate next WP: WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening. |
| WP41-D002 | Provider/Hermes decision refresh not performed after prompt/runbook package | OPEN | P3 | WP41 does not revisit provider, Hermes, runtime, network, memory, command, credential, or data-sharing decisions. | Future approved WP records explicit user decisions and repo-truth approval before any provider/Hermes/runtime integration or setup work. | Candidate later WP only after explicit user approval. |

WP3-D001 (gitleaks): rerun/assessed in WP40. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP41 Advisory Prompt/Runbook Package Update

WP41 adds `docs/advisory_prompt_runbook_package.md`,
`tests/test_advisory_prompt_runbook_package_docs.py`, and narrow repo-truth
updates for human-operated advisory prompt templates and operator review steps.

WP41 is docs/test-only. It adds no implementation, prompt runner, runtime
source, tools implementation, dependency file, lock file, generated output,
Hermes runtime or installation, LLM/provider SDK, credentials, network polling,
paper trading, live trading, order placement or cancellation, signing, account
connection, scheduler/daemon/bot loop, database, dashboard, deployment, or
product behavior.

WP39-D002 is RESOLVED only for docs-only advisory prompt/runbook package scope.
It is not resolved for runtime, LLM, Hermes, provider, credential, account,
trading, scheduler, database, dashboard, or product implementation.

WP40-D001 is RESOLVED only for docs-only advisory prompt/runbook package scope.
It is not resolved for implementation, prompt execution, LLM/Hermes/provider
integration, account access, trading, scheduler, database, dashboard, or product
work.

WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed
or implemented.

WP41-D001 is added because advisory consumer integration review / operator
workflow hardening is not implemented.

WP41-D002 is added because provider/Hermes decision refresh is not performed
after the prompt/runbook package.

WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION. WP27-D001,
WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and
unchanged.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP39-D002 | Advisory prompt/runbook package implemented for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates human-operated advisory prompt templates and an operator runbook package. | No runtime/product implementation is authorized by this resolution. | Resolved only for docs-only prompt/runbook package scope. |
| WP40-D001 | Advisory prompt/runbook package implemented after prototype for docs-only scope | RESOLVED (WP41 docs-only prompt/runbook package) | P3 | WP41 creates advisory prompt templates and an operator runbook package after the deterministic local advisory consumer prototype. | No runtime/product implementation is authorized by this resolution. | Resolved only for docs-only prompt/runbook package scope. |
| WP40-D002 | LLM/Hermes/provider integration not designed or implemented | OPEN | P3 | WP41 remains docs-only and does not select or integrate Hermes, providers, credentials, network permissions, memory, or command authority. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any integration work. | Candidate later WP only after explicit user selection and repo-truth approval. |
| WP41-D001 | Advisory consumer integration review / operator workflow hardening not implemented | OPEN | P3 | WP41 creates prompt/runbook docs but does not harden the local human-operated workflow around the WP40 consumer. | Future approved WP reviews and hardens the local advisory consumer/operator workflow without runtime, LLM/Hermes, credentials, account access, trading, database, dashboard, scheduler, or dependency changes unless separately authorized. | Candidate next WP: WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening. |
| WP41-D002 | Provider/Hermes decision refresh not performed after prompt/runbook package | OPEN | P3 | WP41 does not revisit provider, Hermes, runtime, network, memory, command, credential, or data-sharing decisions. | Future approved WP records explicit user decisions and repo-truth approval before any provider/Hermes/runtime integration or setup work. | Candidate later WP only after explicit user approval. |

WP3-D001 (gitleaks): rerun/assessed in WP41. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP42 Advisory Consumer Operator Workflow Hardening Update

WP42 adds `docs/advisory_consumer_operator_workflow.md`,
`tests/test_advisory_consumer_operator_workflow_docs.py`, and narrow repo-truth
updates for docs-only advisory consumer integration review / operator workflow
hardening.

WP42 is docs/test-only. It adds no implementation, workflow runner, prompt
runner, runtime source, tools implementation, dependency file, lock file,
generated output, Hermes runtime or installation, LLM/provider SDK, credentials,
network polling, paper trading, live trading, order placement or cancellation,
signing, account connection, scheduler/daemon/bot loop, database, dashboard,
deployment, or product behavior.

WP41-D001 is RESOLVED only for docs-only advisory consumer integration review /
operator workflow hardening scope. It is not resolved for runtime, LLM, Hermes,
provider, credential, account, trading, scheduler, database, dashboard, prompt
runner, workflow runner, or product implementation.

WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed
or implemented.

WP41-D002 remains OPEN because provider/Hermes decision refresh is not
performed.

WP42-D001 is added because provider/Hermes decision refresh is not performed
after operator workflow hardening.

WP42-D002 is added because no runtime or prompt runner is implemented after
operator workflow hardening.

WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION. WP27-D001,
WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and
unchanged.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP41-D001 | Advisory consumer integration review / operator workflow hardening completed for docs-only scope | RESOLVED (WP42 docs-only operator workflow hardening) | P3 | WP42 documents the local human-operated advisory workflow around WP40 and WP41 with evidence, stop/reject, decision-log, and future-WP conversion rules. | No runtime/product implementation is authorized by this resolution. | Resolved only for docs-only advisory consumer integration review / operator workflow hardening scope. |
| WP40-D002 | LLM/Hermes/provider integration not designed or implemented | OPEN | P3 | WP42 remains docs-only and does not select or integrate Hermes, providers, credentials, network permissions, memory, or command authority. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any integration work. | Candidate later WP only after explicit user selection and repo-truth approval. |
| WP41-D002 | Provider/Hermes decision refresh not performed after prompt/runbook package | OPEN | P3 | WP42 does not revisit provider, Hermes, runtime, network, memory, command, credential, or data-sharing decisions. | Future approved WP records explicit user decisions and repo-truth approval before any provider/Hermes/runtime integration or setup work. | Candidate later WP only after explicit user approval. |
| WP42-D001 | Provider/Hermes decision refresh not performed after operator workflow hardening | OPEN | P3 | WP42 does not perform the provider/Hermes decision refresh. | Future approved WP records explicit user decisions, security/dependency review, data-sharing boundaries, and repo-truth authorization before any provider/Hermes/runtime work. | Candidate later WP: WP43 - Provider/Hermes Decision Refresh, only if explicitly approved. |
| WP42-D002 | No runtime or prompt runner implemented after operator workflow hardening | OPEN | P3 | WP42 intentionally adds no runtime behavior, workflow runner, prompt runner, LLM/Hermes/provider integration, scheduler, database, dashboard, polling, or trading behavior. | Future approved WP explicitly scopes and authorizes design first; implementation requires separate protected-boundary, security, dependency, and human-review gates. | Candidate later WP only after explicit user approval and repo-truth authorization. |

WP3-D001 (gitleaks): rerun/assessed in WP42. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP29 Local Diff And Scope Summary Helper Design Update

WP29 adds `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md`, `tests/test_diff_scope_summary_helper_design_docs.py`, and repo-truth updates for the design of a future local/offline/read-only diff scope summary helper.

WP29 is documentation/design/test-only. It adds no helper implementation, no command-output compression, no code indexing, no memory store, no Hermes installation, no Hermes runtime dependency, no agent runtime, no scheduler, no daemon, no network polling, no credentials, no provider SDK, no strategy signal, no trade proposal, no paper trading, no live trading, no execution, no risk, no OMS, no reconciliation, no database, no dashboard, no dependency file, and no lock file.

WP28-D001 remains OPEN because token-efficiency helper tooling (command-output compression, diff/scope summary, code indexing, memory snapshot) is still not implemented. WP29 contributes the diff/scope summary design to the design-first gate, but does not implement it.

WP29-D001 is added because the diff/scope summary helper implementation is not started; it requires a separate approved implementation WP.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP29. WP27-D001 remains OPEN — not changed by WP29. WP20-D003 remains OPEN. WP8-D002 remains OPEN. WP16-D002 remains OPEN. WP17-D001 remains OPEN. WP17-D002 remains OPEN.

WP3-D001 (gitleaks): rerun/assessed in WP29. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

| WP29-D001 | Diff/scope summary helper implementation not started | RESOLVED | P3 | WP29 defines the design for a future local/offline/read-only diff/scope summary helper but does not implement it. An approved implementation WP is required before any code is written. | Any implementation of the diff/scope summary helper. | RESOLVED by WP30: stdlib-only helper implemented under `tools/git/diff_scope_summary.py` with tests under `tests/tools/git/test_diff_scope_summary.py`; 79 tests pass; all open design questions resolved. |

## WP28 Codex/Claude Code Token Efficiency Operating Model Lock Update

WP28 adds `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`, `docs/ai/codex/CONCISE_REPORTING_RULES.md`, `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`, `tests/test_codex_token_efficiency_docs.py`, and repo-truth updates locking token-efficiency discipline into existing Codex workflow docs.

WP28 is documentation/test-only. It adds no helper tooling implementation, command-output compression, diff summary tool, code indexing, memory store, Hermes installation, Hermes runtime dependency, agent runtime, scheduler, daemon, network polling, credentials, provider SDK, strategy signal, trade proposal, paper trading, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP28-D001 is added because token-efficiency helper tooling (command-output compression, diff/scope summary, code indexing, memory snapshot) is not implemented yet; design-first WPs are required before any implementation.

WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION — not changed by WP28. WP27-D001 remains OPEN — not changed by WP28. WP20-D003 remains OPEN. WP8-D002 remains OPEN. WP16-D002 remains OPEN. WP17-D001 remains OPEN. WP17-D002 remains OPEN.

WP3-D001 (gitleaks): rerun/assessed in WP28. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

| WP28-D001 | Token-efficiency helper tooling not implemented | OPEN | P3 | WP28 locks operating-model discipline for future helper tools but does not implement any helper. Design-first WPs required before implementation. | Any implementation of command-output compression, diff/scope summary, code indexing, or memory snapshot helper. | Future approved design WP defines the helper, scope, stdlib-only constraints, and safety gates; implementation WP follows after design approval. |

## WP27 Agent/Hermes Manual Setup Decision Record Update

WP27 adds `docs/agent_hermes_manual_setup_decision_record.md`, `tests/test_agent_hermes_manual_setup_decision_record_docs.py`, and repo-truth updates defining the manual setup gates, user decisions, and approval steps required before any future Hermes or agent runtime work begins.

WP27 is documentation/test-only. It adds no Hermes installation, Hermes runtime dependency, Hermes config, agent runtime, agent CLI, scheduler, daemon, memory store, network polling, LLM dependency, credentials, account connection, provider SDK, strategy signal, trade proposal, parameter recommendation, paper trading, backtesting, live trading, execution, risk, OMS, reconciliation, database, dashboard, dependency file, or lock file.

WP20-D001 is updated from OPEN to READY_FOR_MANUAL_SETUP_DECISION because WP27 defines decision gates and documents required user decisions, but does not install or configure Hermes. WP20-D001 is not RESOLVED. WP27-D001 is added because the runtime/provider/environment decision remains pending user selection. WP20-D003 remains OPEN because performance and strategy logs remain unavailable for performance-review agents.

WP8-D002 remains OPEN because no authoritative public endpoint rate-limit policy was added. WP16-D002 remains OPEN because local budgets remain conservative policy, not confirmed venue limits. WP17-D001 remains OPEN because no automated or scheduled polling is implemented. WP17-D002 remains OPEN because public-data runners and guarded capture remain dev-only/manual until venue rate limits are confirmed.

WP3-D001 (gitleaks): rerun/assessed in WP27. WP3-D002 (semgrep): READY_FOR_WP; `.venv-security/` not restored this WP and semgrep was unavailable/skipped. WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit was unavailable/skipped.

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

## WP44 Market Research Priority Scoring Layer Design Update

WP44 adds `docs/market_research_priority_scoring_layer.md` (docs-only design for
a future local/offline/read-only Market Research Priority Scoring Layer),
`tests/test_market_research_priority_scoring_layer_docs.py` (focused docs test),
and narrow repo-truth updates to `docs/project_status.md`,
`docs/repo_truth_index.md`, and `docs/deferred_items_log.md`.

WP44 is docs/test-only. It adds no schema, source implementation, CLI,
report writer, scoring logic, workflow runner, prompt runner, runtime source,
tools implementation, dependency file, lock file, generated output,
Hermes runtime or installation, LLM/provider SDK, credentials, network polling,
paper trading, live trading, order placement or cancellation, signing, account
connection, scheduler/daemon/bot loop, database, dashboard, deployment, or
product behavior.

WP44 resolves no existing deferred items. WP40-D002, WP41-D002, WP42-D001,
WP42-D002, WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and
WP36-D002 remain OPEN. WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION.
WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain
OPEN and unchanged.

WP44-D001 is added: Market Research Priority Scoring implementation not started
(OPEN, P3). Any scoring implementation, schema, CLI, report/export, or advisory
integration is deferred to a future approved WP.

WP44-D002 is added: Score laundering mitigation not enforced by implementation
(OPEN, P3). No implementation exists to enforce advisory-only labels, caps,
missing-data penalties, or forbidden-output checks. A future approved WP adds
tests and output constraints enforcing advisory-only, non-signal,
provenance/staleness, and forbidden-output rules.

| Item | Status | Priority | Why Deferred | Resolution Condition |
|---|---|---|---|---|
| WP44-D001 | OPEN | P3 | WP44 defines design-only; no schema or implementation added. | Future approved WP (WP45 schema WP or later) defines schema/output contract first, then implementation in a later WP. |
| WP44-D002 | OPEN | P3 | WP44 documents score-laundering mitigations but no implementation enforces them. | Future approved WP adds tests and output constraints. |

WP3-D001 (gitleaks): rerun/assessed in WP44; results reported in WP44 PR.
WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be honestly
reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP45 Codex / Claude PR Evidence Reporting Hardening Update

WP45 adds `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` (central
workflow reference), `tests/test_pr_evidence_reporting_discipline_docs.py`
(focused docs test), and updates to `AGENTS.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/CONCISE_REPORTING_RULES.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/work_package_template.md`, `docs/review_checklist.md`,
`docs/repo_truth_index.md`, and `docs/project_status.md`.

WP45 is docs/test-only workflow/governance hardening. It adds no implementation,
helper tooling, runtime source, tools implementation, dependency file, lock file,
generated output, Hermes runtime or installation, LLM/provider SDK, credentials,
network polling, paper trading, live trading, order placement or cancellation,
signing, account connection, scheduler/daemon/bot loop, database, dashboard,
deployment, or product behavior.

WP45 resolves no existing deferred items. All WP44-forward deferred items remain
unchanged.

WP3-D001 (gitleaks): rerun/assessed in WP45. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP46 PR Evidence Consistency Guard Helper Update

WP46 adds `tools/git/pr_evidence_consistency_guard.py` (local/offline/stdlib
CLI guard helper), `tests/tools/git/test_pr_evidence_consistency_guard.py`
(focused tests), and `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`
(user-facing reference). It updates `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`, `docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`, `docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/work_package_template.md`, `docs/review_checklist.md`,
`docs/project_status.md`, `docs/repo_truth_index.md`, and
`docs/deferred_items_log.md`.

WP46 is a local/offline stdlib governance helper WP. It adds no runtime source
under `src/`, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP46 resolves no existing deferred items. All WP45-forward deferred items remain
unchanged.

WP46-D001 is added: guard validates local PR body/final comment drafts only,
not live GitHub PR data (OPEN, P4). See table below.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP46-D001 | PR evidence guard does not fetch live GitHub PR data | OPEN | P4 | WP46 intentionally validates local PR body/final comment drafts only and does not call GitHub. | Any future requirement to validate already-posted GitHub PR body/comments automatically. | Future approved GitHub/API-aware WP, only if explicitly authorized. |

WP3-D001 (gitleaks): rerun/assessed in WP46. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP47 Posted PR Evidence Review Hardening Deferred Items

WP47 hardens the guard with five new optional flags and updates workflow docs
to require current-final evidence markers, forbid inline test counts in file
lists, and require Guard input source notes. WP47 adds no runtime source,
no dependency or lock-file changes, no Hermes/LLM/provider integration, no
credentials, no network/account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP47 resolves no existing deferred items. All WP46-forward deferred items remain
unchanged.

WP47-D001 is added: guard still does not fetch live GitHub PR body/comments
(OPEN, P4). WP47 hardens local posted-evidence discipline and current-final
markers but intentionally avoids GitHub API/network/auth behavior. See table below.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP47-D001 | Guard still does not fetch live GitHub PR body/comments | PARTIALLY_RESOLVED_PUBLIC_ONLY | P4 | WP47 hardens local posted-evidence discipline and current-final markers but intentionally avoids GitHub API/network/auth behavior. WP58 adds tools/git/posted_pr_evidence_verifier.py for public-repo manual verification only; authenticated/private GitHub verification remains unsupported. | Authenticated or private GitHub verification requires a separate future WP with explicit secrets/auth policy review. | WP58 addresses the public-repo case. Authenticated/private case deferred to WP58-D001. |

WP3-D001 (gitleaks): rerun/assessed in WP47. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP48 Market Research Priority Scoring Schema / Output Contract Deferred Items

WP48 defines the formal schema and output contract for the future local/offline/
read-only Market Research Priority Scoring Layer. WP48 adds no runtime source,
no scoring implementation, no CLI tooling, no JSON writer, no report writer,
no dependency or lock-file changes, no Hermes/LLM/provider integration, no
credentials, no network/account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP48 resolves no existing deferred items. WP44-D001 and WP44-D002 remain OPEN
because implementation is still not started and no implementation exists to
enforce the schema/output contract. All WP47-forward deferred items remain
unchanged.

WP48-D001 is added: Market Research Priority Scoring implementation not started
after schema/output contract (OPEN, P3).
WP48-D002 is added: schema/output contract not enforced by implementation yet
(OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP48-D001 | Market Research Priority Scoring implementation not started after schema/output contract | OPEN | P3 | WP48 defines the schema/output contract only. No implementation, scoring logic, CLI, report writer, or JSON writer is added. | Future approved WP implements scoring logic only after WP48 is merged and the user explicitly approves an implementation WP. | Candidate later WP: Market Research Priority Scoring implementation, local/offline/read-only only, if explicitly approved. |
| WP48-D002 | Schema/output contract not enforced by implementation yet | OPEN | P3 | WP48 adds a docs-only contract. No implementation exists to enforce required fields, labels, bounds, forbidden fields, staleness, or provenance rules. | Future approved implementation WP adds tests enforcing all contract requirements before any scored output is produced. | Candidate later WP: Market Research Priority Scoring implementation, only after WP48 merged and user approval. |

WP3-D001 (gitleaks): rerun/assessed in WP48. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP49 Market Research Priority Scoring Core Implementation Deferred Items

WP49 adds the local/offline/read-only core scorer at
src/data_layer/market_research_priority_scoring.py. WP49 is stdlib-only,
in-memory output only, no network, no file writes, no CLI, no export, no
feature extraction, no advisory consumer integration, no runtime/product/
trading behavior, no Hermes/LLM/provider integration, no credentials, no
account access, no trading or paper trading, no database/dashboard/scheduler/
polling/product behavior, and no generated outputs committed.

WP49 resolves WP44-D001, WP44-D002, WP48-D001, and WP48-D002 only for the
local/offline/read-only core scorer scope. Feature extraction, CLI/export/
report, and advisory consumer integration remain not started.

WP49-D001 is added: feature extraction from local/offline artifacts not
started (OPEN, P3).
WP49-D002 is added: CLI/export/report writer not started (OPEN, P3).
WP49-D003 is added: core scorer not integrated with advisory consumer or
market catalog (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP49-D001 | Feature extraction from local/offline artifacts not started | RESOLVED (WP51 basic feature extraction foundation scope) | P3 | WP49 implements only the in-memory core scorer; no feature extraction from real local Polymarket snapshot/catalog/export artifacts. | Resolved for narrow WP51 basic scope only; advanced feature groups remain deferred (WP51-D001, WP51-D002, WP51-D003). | WP51 adds src/data_layer/market_research_priority_features.py. |
| WP49-D002 | CLI/export/report writer not started | OPEN | P3 | WP49 adds no CLI, no JSON writer/exporter, no report writer, no local output file generation. | Future approved WP implements CLI/export/report integration only, after WP49 merged and user approval. | Candidate: Market Research Priority Scoring CLI/export WP, local/offline/read-only only. |
| WP49-D003 | Core scorer not integrated with advisory consumer or market catalog | OPEN | P3 | WP49 core scorer is standalone and in-memory only; not wired to advisory consumer or catalog. | Future approved WP integrates core scorer after feature extraction is implemented and user explicitly approves. | Candidate: follow-on integration WP after feature extraction WP. |

## WP50 Research Data Foundation Direction Lock-In Deferred Items

WP50 adds `docs/research_data_foundation_direction.md` as a docs-only direction
lock. WP50 is docs/tests-only and adds no runtime source, no feature extraction,
no CLI/export/report, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP50 resolves no existing deferred items. WP50 adds WP50-D001 (research
direction locked, but implementation sequencing still requires explicit future
WPs, OPEN, P3). WP49-D001, WP49-D002, and WP49-D003 remain OPEN at WP50 merge.

WP3-D001 (gitleaks): rerun/assessed in WP50. WP3-D002 (semgrep):
READY_FOR_WP; semgrep availability must be honestly reported by validation.
WP3-D004 (pip-audit): READY_FOR_WP; no project dependency added and pip-audit
availability must be honestly reported by validation.

## WP51 Market Research Priority Feature Extraction Foundation Deferred Items

WP51 adds the local/offline/read-only feature extraction foundation at
src/data_layer/market_research_priority_features.py. WP51 is stdlib-only,
in-memory output only, no network, no file writes, no CLI, no export/report
writer, no advisory consumer integration, no runtime/product/trading behavior,
no Hermes/LLM/provider integration, no credentials, no account access, no
trading or paper trading, no database/dashboard/scheduler/polling/product
behavior, and no generated outputs committed.

WP51 resolves WP49-D001 only for the narrow basic feature extraction foundation
scope: basic metadata/provenance/staleness/missing-data features from
MarketMetadataSnapshotRecord, OrderBookSnapshotRecord, and SnapshotManifest.
Advanced feature groups remain deferred.

WP49-D002 and WP49-D003 remain OPEN. WP50-D001 remains OPEN.

WP51-D001 is added: provenance/staleness enforcement hardening beyond foundation
not started (OPEN, P3).
WP51-D002 is added: resolution-rule ambiguity extraction not started (OPEN, P3).
WP51-D003 is added: microstructure quality feature extraction beyond basic
availability not started (OPEN, P3).
WP51-D004 is added: CLI/export/report writer not started (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP51-D001 | Provenance/staleness enforcement hardening beyond foundation not started | OPEN | P3 | WP51 implements basic staleness and provenance detection only. Non-compensatory caps, cross-session provenance audit, and full guard-policy version tracking remain not implemented. | Future approved WP explicitly scopes and implements provenance/staleness hardening after WP51 is merged and user explicitly approves. | Candidate: provenance/staleness hardening WP, local/offline/read-only only. |
| WP51-D002 | Resolution-rule ambiguity extraction not started | OPEN | P3 | WP51 implements only basic metadata/staleness/provenance feature extraction. Resolution-rule ambiguity taxonomy, manual-label workflow, and ambiguity feature extraction are not started. | Future approved WP explicitly scopes resolution-rule ambiguity work after WP51 is merged and user explicitly approves. | Candidate: resolution-rule ambiguity taxonomy and manual-label workflow WP. |
| WP51-D003 | Microstructure quality feature extraction beyond basic availability not started | OPEN | P3 | WP51 determines only basic order book availability and two-sided structure. Spread bps, depth buckets, slippage, tradability, fill probability, order size, and execution confidence are not computed. | Future approved WP explicitly scopes microstructure quality extraction after WP51 is merged, local artifact schema is confirmed, and user explicitly approves. | Candidate: microstructure quality feature extraction WP, local/offline/read-only only. |
| WP51-D004 | CLI/export/report writer not started | OPEN | P3 | WP51 adds no CLI, no JSON writer/exporter, no report writer, no local output file generation, and no advisory consumer integration. | Future approved WP implements CLI/export/report integration only after WP51 is merged and user explicitly approves. | Candidate: Market Research Priority Scoring CLI/export WP, local/offline/read-only only. |

WP3-D001 (gitleaks): rerun/assessed in WP51; binary absent in this environment,
UNAVAILABLE/SKIPPED. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability
must be honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP;
no project dependency added and pip-audit availability must be honestly reported
by validation.

## WP52 Long-Term Bot Roadmap And Side 4 Onboarding Lock-In Update

WP52 adds `docs/long_term_bot_completion_roadmap.md` and focused tests at
`tests/test_long_term_bot_completion_roadmap_docs.py`. It updates
`docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/research_data_foundation_direction.md`, and `docs/deferred_items_log.md`.

WP52 is docs/test-only. It adds no source under `src/`, no tools implementation,
no runtime, no network, no dependency or lock-file changes, no
Hermes/LLM/provider integration, no credentials, no account access, no trading
or paper trading, no database/dashboard/scheduler/polling/product behavior, and
no generated outputs committed.

WP52 resolves no existing deferred items.

WP49-D002, WP49-D003, WP50-D001, WP51-D001, WP51-D002, WP51-D003, and
WP51-D004 remain OPEN.

WP52-D001 is added: long-term roadmap locked, but milestone implementation
remains gated by explicit future WPs (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP52-D001 | Long-term roadmap locked but milestone implementation remains gated by explicit future WPs | OPEN | P3 | WP52 locks the long-term bot-completion roadmap in docs/long_term_bot_completion_roadmap.md but does not draft, approve, or schedule any future implementation WP. Each milestone phase requires separate explicit user approval before a WP is drafted. | Future approved WP explicitly selected by user after WP52 is merged; milestone implementation sequencing remains user-gated. | Candidate: any explicitly approved safe next WP after WP52 is merged. |

WP3-D001 (gitleaks): rerun/assessed in WP52; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP53 Repo-Truth Reconciliation And Provenance/Staleness/Missing-Data Enforcement Hardening Update

WP53 updates `src/data_layer/market_research_priority_features.py` with explicit
`provenance_degraded` flag, `provenance_weakness_reasons`, `provenance_warning`,
future-timestamp detection, `missing_question` and `missing_market_status`
detection, and quality-impacting vs informational provenance weakness separation.
It updates `docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/deferred_items_log.md`, `docs/research_data_foundation_direction.md`,
`docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It adds focused tests at
`tests/test_market_research_priority_features.py`.

WP53 is a local/offline/read-only source-implementation and docs/tests WP. It adds
no CLI/export/report writer, no advisory consumer integration, no market catalog
integration, no runtime/product/trading behavior, no Hermes/LLM/provider integration,
no credentials, no network, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed. No dependency or lock-file changes.

WP53 resolves WP51-D001 only for the narrow provenance/staleness/missing-data
hardening scope. WP49-D002, WP49-D003, WP50-D001, WP51-D002, WP51-D003,
WP51-D004, and WP52-D001 remain OPEN.

WP53-D001 is added: resolution-rule ambiguity extraction still not started after
WP53 hardening (OPEN, P3).

WP53-D002 is added: microstructure quality feature extraction still not started
after WP53 hardening (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP53-D001 | Resolution-rule ambiguity extraction still not started after WP53 hardening | OPEN | P3 | WP53 hardens provenance/staleness/missing-data enforcement but does not add resolution-rule ambiguity taxonomy, parser, manual-label workflow, or ambiguity feature extraction. WP51-D002 remains open for the same scope. | Future approved WP explicitly scopes resolution-rule ambiguity work after WP53 is merged and user explicitly approves. | Candidate: WP55 resolution-rule ambiguity taxonomy and manual-label workflow. |
| WP53-D002 | Microstructure quality feature extraction still not started after WP53 hardening | OPEN | P3 | WP53 hardens provenance/staleness/missing-data enforcement but does not add spread bps, depth buckets, slippage, tradability, fill probability, order size, or execution confidence computation. WP51-D003 remains open for the same scope. | Future approved WP explicitly scopes microstructure quality extraction after WP53 is merged, local artifact schema is confirmed, and user explicitly approves. | Candidate: future microstructure quality feature extraction WP. |

WP3-D001 (gitleaks): rerun/assessed in WP53; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP54 PR Evidence Follow-Up Defect And Bundled-WP Execution Policy Hardening Update

WP54 hardens `tools/git/pr_evidence_consistency_guard.py` with a new `--require-guard-result`
flag (category P) and creates `docs/ai/codex/WP_BUNDLING_POLICY.md`. It also updates
workflow/governance docs, the WP template, the PR template, and the PR review checklist.
It updates `docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/work_package_template.md`,
`.github/pull_request_template.md`,
`docs/review_checklist.md`,
`docs/testing_requirements.md`,
`tests/test_codex_workflow_docs.py`, and
`tests/tools/git/test_pr_evidence_consistency_guard.py`.

WP54 is a local/offline/stdlib workflow-governance helper hardening WP. It adds no source
under `src/`, no Polymarket/trading/advisory tooling, no runtime, no network, no dependency
or lock-file changes, no Hermes/LLM/provider integration, no credentials, no account access,
no trading or paper trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP54 resolves no existing implementation deferred items. All prior open deferred
items remain unchanged.

WP54-D001 is added: GitHub-posted evidence still requires human or Claude manual
verification because the guard remains local/offline and does not fetch live GitHub
PR content (OPEN, P4).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP54-D001 | GitHub-posted evidence still requires human or Claude manual verification | PARTIALLY_RESOLVED_PUBLIC_ONLY | P4 | WP54 hardens posted evidence self-check rules but the guard remains local/offline and does not fetch live GitHub PR content. WP58 adds tools/git/posted_pr_evidence_verifier.py for public-repo manual verification only; authenticated/private GitHub verification remains unsupported (see WP58-D001). | Authenticated or private GitHub verification requires a separate future WP with explicit secrets/auth policy review. | WP58 addresses the public-repo case. Authenticated/private case deferred to WP58-D001. |

WP3-D001 (gitleaks): rerun/assessed in WP54; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP55 Resolution Ambiguity Taxonomy And Manual-Label Workflow Update

WP55 adds `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` and focused
tests at `tests/test_resolution_ambiguity_taxonomy_manual_label_workflow_docs.py`.
It updates `docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/deferred_items_log.md`, `docs/research_data_foundation_direction.md`,
`docs/long_term_bot_completion_roadmap.md`, `docs/market_research_priority_scoring_layer.md`,
`docs/market_research_priority_scoring_output_contract.md`, and
`tests/test_project_status_docs.py`.

WP55 is docs/tests-only. It adds no source under `src/`, no Polymarket/trading/advisory
tooling, no automated parser, no feature extraction, no scorer integration, no CLI/export/report
writer, no runtime, no network, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs committed.

WP55 reconciles docs/project_status.md after WP54 merge (merge commit
fb45fb849b0641e2007ef66f50bfd5725354b8f0). WP54 is now listed in merged WPs.

WP55 narrows WP51-D002 and WP53-D001: the taxonomy and manual-label workflow (docs/schema/tests
only) are addressed; automated parser and feature extraction from ambiguity labels remain not
started. WP49-D002, WP49-D003, WP50-D001, WP51-D003, WP51-D004, WP52-D001, and WP54-D001
remain OPEN.

WP55-D001 is added: resolution ambiguity labels not yet consumed by feature extraction or
scoring (OPEN, P3).
WP55-D002 is added: automated resolution-rule parser remains not started (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP55-D001 | Resolution ambiguity labels not yet consumed by feature extraction or scoring | OPEN | P3 | WP55 adds only docs/schema/tests for the taxonomy and manual-label workflow. No label store, feature extraction, scorer integration, CLI/export/report is implemented. | Future approved WP implements label consumption only after integration gate conditions in docs/resolution_ambiguity_taxonomy_manual_label_workflow.md Section 10 are satisfied and user explicitly approves. | Expected in WP56 or later; requires explicit approval. |
| WP55-D002 | Automated resolution-rule parser remains not started | OPEN | P3 | WP55 defines human-review workflow only. No automated parser for resolution rule text extraction is added. | Future approved WP explicitly scopes automated parser design after WP55 merge and user explicitly approves; non-LLM parser design preferred. | Not expected until feature extraction foundation is validated. |

WP3-D001 (gitleaks): rerun/assessed in WP55; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP56 Resolution Ambiguity Manual Label Schema Validation Update

WP56 adds `src/data_layer/resolution_ambiguity_labels.py` (stdlib-only, local/offline/read-only
schema validator) and focused tests. It reconciles repo truth after WP55 merge (WP55 is now listed
in merged WPs).

WP56 resolves WP55-D001 only for the narrow schema validation scope; feature extraction from
validated labels remains not started. WP55-D002 (automated parser) remains OPEN.

WP56-D001 is added: resolution ambiguity labels validated but not yet consumed by feature
extraction or scoring (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP56-D001 | Resolution ambiguity labels validated but not yet consumed by feature extraction | RESOLVED (WP57 scope) | P3 | WP56 implements schema validator only. Feature extraction from validated labels is not implemented. WP57 implements local/offline/read-only feature extraction from validated manual labels. | Resolved only for WP57 local/offline/read-only feature extraction scope. Scorer integration, advisory consumer integration, and CLI/export/report writer remain deferred. | Expected in WP57; resolved for WP57 scope. |

WP3-D001 (gitleaks): rerun/assessed in WP56. WP3-D002 (semgrep): READY_FOR_WP.
WP3-D004 (pip-audit): READY_FOR_WP.

## WP57 Repo-Truth Reconciliation And Resolution Ambiguity Feature Extraction Deferred Items

WP57 adds local/offline/read-only resolution ambiguity label feature extraction to
`src/data_layer/market_research_priority_features.py` and focused tests. It reconciles
repo truth after WP56 merge (WP56 is now listed in merged WPs).

WP57 resolves WP55-D001 and WP56-D001 only for the narrow local/offline/read-only feature
extraction from validated manual labels scope. WP55-D002 (automated parser) remains OPEN.

WP57-D001 is added: resolution ambiguity feature extraction not yet integrated into
scorer/report/advisory consumer (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP57-D001 | Resolution ambiguity feature extraction not yet integrated into scorer/report/advisory consumer | OPEN | P3 | WP57 adds feature extraction only. The resolution_ambiguity sub-dict in market contexts is not yet used in scorer weights/components, advisory consumer integration, CLI/export/report writer, or any downstream consumer. | Future approved WP explicitly scopes integration only after WP57 is merged and user explicitly approves. | Not expected until scorer integration WP is approved. |

WP3-D001 (gitleaks): rerun/assessed in WP57. WP3-D002 (semgrep): READY_FOR_WP.
WP3-D004 (pip-audit): READY_FOR_WP.

## WP58 Posted GitHub Evidence Verification, Claude Start Layer, And Workflow Hardening Deferred Items

WP58 adds `CLAUDE_START_HERE.md`, `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md`,
`docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md`, `tools/git/posted_pr_evidence_verifier.py`,
focused tests, and workflow/governance docs updates. It reconciles repo truth after WP57 merge
(WP57 is now listed in merged WPs).

WP58 is a workflow/governance hardening WP. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no runtime, no dependency or lock-file changes, no
Hermes/LLM/provider integration, no credentials, no account access, no trading or paper trading,
no database/dashboard/scheduler/polling/product behavior, and no generated outputs committed.

WP58 marks WP54-D001 and WP47-D001 as PARTIALLY_RESOLVED_PUBLIC_ONLY — the new public GitHub
manual read-only helper addresses the public-repo case; authenticated/private GitHub verification
remains unsupported.

WP58-D001 is added: authenticated or private GitHub posted-evidence verification not implemented
(OPEN, P4). Future optional helper may support a token only after explicit secrets/auth policy review.

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP58-D001 | Authenticated or private GitHub posted-evidence verification not implemented | OPEN | P4 | WP58 adds tools/git/posted_pr_evidence_verifier.py for public-repo manual verification only. Authenticated access (tokens, private repos) is not supported in WP58. No secrets/auth policy review has been performed for this tool. | Future optional helper WP explicitly scopes token support after secrets/auth policy review and explicit user approval. | Not expected in near term; public-repo verifier addresses the main use case. |

WP3-D001 (gitleaks): rerun/assessed in WP58; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

WP58-D001 is narrowed in WP59: public unauthenticated helper exists (`tools/git/posted_pr_evidence_verifier.py`); private/authenticated support remains deferred. The WP59 PRIVATE_REPO_MANUAL_VERIFIED mode documents the expected pattern for this private repository.

## WP59 / WF-STAB-1 Canonical WP Execution State Machine And Private-Repo Evidence Mode Deferred Items

WP59 creates `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` and updates startup and evidence docs to be
evidence-mode-aware. It reconciles repo truth after WP58 merge (WP58 is now listed in merged WPs).

WP59 is a workflow/governance-docs-tests-state-machine WP. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no runtime, no dependency or lock-file changes, no
Hermes/LLM/provider integration, no credentials, no account access, no trading or paper trading,
no database/dashboard/scheduler/polling/product behavior, no helper code changes, and no generated outputs committed.

WP59-D001 is added: local evidence-mode linter not implemented (OPEN, P4).
WP59-D002 is added: `docs/project_status.md` slimming/history split not implemented (OPEN, P4).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP59-D001 | Local evidence-mode linter not implemented | OPEN | P4 | WP59 defines evidence modes in docs and tests but adds no automated linter to enforce mode selection in PR body/comment text. | Future optional workflow helper WP after WP59 is stable. | Not required for WP59 acceptance. |
| WP59-D002 | docs/project_status.md slimming/history split not implemented | OPEN | P4 | docs/project_status.md is long; splitting architecture history into a separate file is desirable but not required for workflow stabilization. | Future workflow stabilization WP (WF-STAB-2 or equivalent). | Not required for WP59 acceptance. |

WP3-D001 (gitleaks): rerun/assessed in WP59; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP60A / WF-STAB-2 Agent-Neutral Startup Layer Deferred Items

WP60A creates `AI_CODING_AGENT_START_HERE.md` (shared startup entry point) and updates AGENTS.md,
CODEX_START_HERE.md, CLAUDE_START_HERE.md, docs/ai/codex/README.md, docs/codex_execution_guidelines.md,
docs/work_package_template.md, and .github/pull_request_template.md to use agent-neutral shared wording
where rules apply to all AI coding agents. It reconciles repo truth after WP59 merge (WP59 is now listed
in merged WPs).

WP60A is a workflow/governance-docs-tests-agent-neutral-startup WP. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no runtime, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no account access, no trading or paper trading, no database/dashboard/scheduler/
polling/product behavior, and no generated outputs committed.

WP60A-D001 is added: full directory migration from `docs/ai/codex/` to agent-neutral path not performed (OPEN, P4).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP60A-D001 | Full docs/ai/codex/ directory migration not performed | OPEN | P4 | WP60A clarifies that docs/ai/codex/ is the historical current shared workflow path and its contents apply to all AI coding agents. Renaming the directory was out of scope for WP60A. | Future optional governance cleanup WP when directory rename is explicitly authorized. | Not required for WP60A acceptance. |

WP3-D001 (gitleaks): rerun/assessed in WP60A; availability reported honestly in
validation. WP3-D002 (semgrep): READY_FOR_WP; semgrep availability must be
honestly reported by validation. WP3-D004 (pip-audit): READY_FOR_WP; no project
dependency added and pip-audit availability must be honestly reported by
validation.

## WP61 Architecture Direction Lock-In And Microstructure Quality V1 Deferred Items

WP61 creates `docs/architecture_decision_record.md` and adds advisory-only
`microstructure_quality` metadata to `src/data_layer/market_research_priority_features.py`.
It reconciles repo truth after WP60A merge (WP60A is now listed in merged WPs).

WP61 is local/offline/read-only research-data feature extraction plus planning
docs. It adds no database, dashboard, runtime, deployment, scheduler, bot loop,
credentials, dependency, lock-file, network, parser, report writer, advisory
consumer integration, scorer implementation change, scorer weight change, paper
trading, live trading, or execution behavior.

WP61 resolves WP51-D003 and WP53-D002 only for the narrow Microstructure Quality
V1 metadata scope. Numeric modeling and downstream integration remain deferred.

WP61-D001 is added: Postgres implementation deferred (OPEN, P3).
WP61-D002 is added: Dashboard implementation deferred (OPEN, P3).
WP61-D003 is added: VPS/runtime scheduler deferred (OPEN, P3).
WP61-D004 is added: Paper/live execution ladder phases deferred (OPEN, P3).
WP61-D005 is added: slippage/fill/tradability/execution modeling remains
forbidden until explicit future WP (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP61-D001 | Postgres implementation deferred | OPEN | P3 | WP61 locks SQLite first and Postgres later only if justified. No database implementation or dependency is added. | Future approved WP explicitly authorizes database implementation and confirms security/dependency gates. | Candidate: future state-store/database WP after research-data needs justify it. |
| WP61-D002 | Dashboard implementation deferred | OPEN | P3 | WP61 locks Streamlit first for internal dashboard planning, Grafana later for runtime metrics, and Next.js only if productizing. No dashboard implementation or dependency is added. | Future approved WP explicitly scopes the selected dashboard path and dependency gates. | Candidate: future internal dashboard WP. |
| WP61-D003 | VPS/runtime scheduler deferred | OPEN | P3 | WP61 locks local development first and cheap VPS later for controlled live pilot planning. No deployment, scheduler, bot loop, or hosted runtime implementation is added. | Future approved WP explicitly scopes runtime/deployment work and protected-boundary review. | Candidate: future deployment/runtime design WP, not implementation by default. |
| WP61-D004 | Paper/live execution ladder phases deferred | OPEN | P3 | WP61 locks the phased ladder research-only -> paper -> dry-run -> manual live approval -> restricted live. No phase after research-only is implemented or authorized. | Future approved WP explicitly authorizes the next phase and satisfies protected-boundary gates. | Candidate: future paper design only after research-data foundations mature. |
| WP61-D005 | Slippage/fill/tradability/execution modeling remains forbidden until explicit future WP | OPEN | P3 | WP61 adds only advisory local order-book metadata. It does not add slippage, fill probability, tradability, execution-confidence, order-size, or downstream modeling. | Future approved WP explicitly scopes modeling and preserves non-signal boundaries. | Candidate: future execution-realism design after data-quality foundations mature. |

## WP62 Repo-Truth Reconciliation And Cross-Market Relationship Metadata V1 Deferred Items

WP62 reconciles repo truth after WP61 merge (WP61 is now listed in merged WPs).
WP62 adds deterministic, metadata-only `cross_market_relationships` sub-dict to
`src/data_layer/market_research_priority_features.py`.

WP62 is local/offline/read-only research-data feature extraction. It adds no
database, dashboard, runtime, deployment, scheduler, bot loop, credentials,
dependency, lock-file, network, parser, report writer, advisory consumer
integration, scorer implementation change, scorer weight change, paper trading,
live trading, semantic matching, fuzzy matching, price comparison, arbitrage
detection, or execution behavior.

WP62 does not resolve WP62-D001, WP62-D002, or WP62-D003 as those remain
explicitly deferred.

WP62-D001 is added: Semantic/fuzzy/LLM cross-market matching remains deferred
(OPEN, P3).
WP62-D002 is added: Price-incoherence/arbitrage/opportunity detection remains
forbidden until explicit future WP (OPEN, P3).
WP62-D003 is added: Cross-market relationship metadata not integrated into
scorer weights (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP62-D001 | Semantic/fuzzy/LLM cross-market matching remains deferred | OPEN | P3 | WP62 adds deterministic metadata-only local key comparison only. No semantic similarity, fuzzy match, embedding, or LLM-based equivalence detection is implemented. | Future approved WP explicitly scopes semantic/fuzzy/LLM matching and confirms non-signal boundary. | Candidate: future NLP/semantic matching WP after research-data foundations mature. |
| WP62-D002 | Price-incoherence/arbitrage/opportunity detection remains forbidden until explicit future WP | OPEN | P3 | WP62 adds metadata-only relationship candidates only. No price comparison, incoherence detection, arbitrage detection, or opportunity scoring is implemented or authorized. | Future approved WP explicitly authorizes the scope, non-signal boundaries, and security/compliance gates. | Candidate: forbidden until explicit future WP. |
| WP62-D003 | Cross-market relationship metadata not integrated into scorer weights | OPEN | P3 | WP62 adds relationship metadata to market_context only. No new score component, no scorer weight change, and no advisory consumer integration is added. | Future approved WP explicitly scopes integration with the scorer and preserves non-signal boundaries. | Candidate: future scorer integration WP after cross-market metadata matures. |

## WP63 Repo-Truth Reconciliation And Resolution Source Hierarchy Metadata V1 Deferred Items

WP63 reconciles repo truth after WP62 merge (WP62 is now listed in merged WPs).
WP63 adds deterministic, metadata-only `resolution_source_hierarchy` sub-dict to every
market context in `src/data_layer/market_research_priority_features.py`, derived from
local field presence checks only (resolution_date timing, question text source hints and
URL pattern detection). No resolution-rule parsing, no source authority judgment, no
official-source monitoring, no network access.

WP63 is local/offline/read-only research-data feature extraction. It adds no
resolution-rule parser, no automated source authority judgment, no semantic source
ranking, no official-source monitoring, no source polling, no network access, no file
writes, no CLI, no export/report writer, no LLM/NLP extraction, no strategy logic,
no scorer weight changes, no new score components, no advisory consumer integration,
no runtime, no credentials, no trading, no paper trading, no execution, no database,
no dashboard, no scheduler.

WP63 does not resolve WP63-D001, WP63-D002, WP63-D003, or WP63-D004 as those remain
open for future approved WPs.

WP63-D001 is added: Automated resolution-rule parser remains deferred (OPEN, P3).
WP63-D002 is added: Official-source monitoring/polling remains deferred (OPEN, P3).
WP63-D003 is added: Source authority ranking remains deferred (OPEN, P3).
WP63-D004 is added: Resolution source hierarchy metadata not integrated into scorer
weights (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP63-D001 | Automated resolution-rule parser remains deferred | OPEN | P3 | WP63 adds metadata-only field presence checks only. No resolution-rule parsing, NLP extraction, or automated rule interpretation is implemented. | Future approved WP explicitly scopes a resolution-rule parser and confirms non-signal boundary. | Candidate: forbidden until explicit future WP with explicit scope approval. |
| WP63-D002 | Official-source monitoring/polling remains deferred | OPEN | P3 | WP63 detects source URL patterns in local text only. No official-source monitoring, URL fetching, source polling, or network access is implemented. | Future approved WP explicitly authorizes official-source monitoring with network/auth boundary review. | Candidate: forbidden until explicit future WP. |
| WP63-D003 | Source authority ranking remains deferred | OPEN | P3 | WP63 adds only presence/absence metadata flags. No source ranking, authority scoring, or source hierarchy ordering is implemented. | Future approved WP explicitly scopes source authority ranking and preserves non-signal boundaries. | Candidate: future approved WP after research-data foundations mature. |
| WP63-D004 | Resolution source hierarchy metadata not integrated into scorer weights | OPEN | P3 | WP63 adds resolution_source_hierarchy to market_context only. No new score component, no scorer weight change, and no advisory consumer integration is added. | Future approved WP explicitly scopes integration with the scorer and preserves non-signal boundaries. | Candidate: future scorer integration WP after resolution-source metadata matures. |

## WP64 Repo-Truth Reconciliation, Research Queue Ranking, Local Human Review Report, And Research Session Packet V1 Deferred Items

WP64 reconciles repo truth after WP63 merge (WP63 is now listed in merged WPs;
merge commit `e1ab1aa7e0915a3c65afc9eb5a55c58292ef6910`).

WP64 adds a local/offline/read-only research-output packaging layer at
`src/data_layer/market_research_priority_review_queue.py`. It produces
deterministic in-memory queue/report/packet objects for human research triage
only. Advisory-only. Not a trading signal.

WP64 is local/offline/read-only research-output packaging. It adds no
CLI/export/report file writer, no advisory consumer integration, no strategy
integration, no paper/live trading path, no network access, no file writes
beyond existing test fixture behavior, no database, no dashboard, no scheduler,
no scorer weight changes, no new score components, no runtime, no credentials,
no trading, no execution.

WP64-D001 is added: CLI/export/report writer for research queue remains deferred (OPEN, P3).
WP64-D002 is added: Advisory consumer integration of research queue remains deferred (OPEN, P3).
WP64-D003 is added: Strategy/paper/live use of research queue remains forbidden until explicit future WP (OPEN, P3).
WP64-D004 is added: Dashboard/database-backed research queue remains deferred (OPEN, P3).

| Item | Title | Status | Priority | Why Deferred | Resolution Condition | Path |
|---|---|---|---|---|---|---|
| WP64-D001 | CLI/export/report writer for research queue remains deferred | OPEN | P3 | WP64 adds only in-memory objects. No CLI, no file writer, no export service, no dashboard, no database-backed queue. | Future approved WP explicitly scopes local/offline/read-only explicit CLI export path; no scheduler; no strategy; no trading. | Candidate: WP65 Local Research Queue Export/CLI V1. |
| WP64-D002 | Advisory consumer integration of research queue remains deferred | OPEN | P3 | WP64 adds queue/report/packet objects only. No advisory consumer integration, no strategy proposal, no paper/live trading integration. | Future approved WP explicitly scopes integration with advisory consumer only after explicit user authorization. | Candidate: future advisory consumer integration WP. |
| WP64-D003 | Strategy/paper/live use of research queue remains forbidden until explicit future WP | OPEN | P3 | WP64 queue/report/packet is advisory-only research triage. No trade signal, no expected return, no paper/live trading use is authorized. | Future approved WP explicitly authorizes scope expansion and satisfies all protected-boundary gates. | Candidate: forbidden until explicitly authorized future WP. |
| WP64-D004 | Dashboard/database-backed research queue remains deferred | OPEN | P3 | WP64 adds in-memory-only objects. No dashboard, no database, no persistence, no scheduler, no hosted runtime. | Future approved WP explicitly scopes database/dashboard integration after protected-boundary review. | Candidate: future dashboard/database WP after schema stabilization. |

## WP75 Post-WP74 Repo-Truth Reconciliation And Local Human Review Label Fixture Loader V1 Deferred Items

WP75 reconciles repo truth after WP74 merge (WP74 is now listed in merged WPs;
PR #75 merge commit `e70013a2e1e9a6dbe0365831f9dd96bdc2d579be`).

WP75 adds a local/offline/read-only human review label fixture loader at
`src/data_layer/human_review_label_fixture_loader.py`. It accepts single JSON
object files, JSON list files, or direct-child *.json directories; validates each
loaded record with the WP74 validator; returns frozen deterministic dataclasses;
rejects URL-like paths, unsupported extensions, missing paths, non-object list
entries; no file writes, no network, no credentials, no automation.

WP75 resolves WP74-D001 and WP73-D002 only for the local/offline/read-only fixture
loader scope. WP75 adds WP75-D001 through WP75-D004 (see table above).

## WP76 Post-WP75 Repo-Truth Reconciliation And Wallet Intelligence Roadmap Lock-In Deferred Items

WP76 reconciles repo truth after WP75 merge (WP75 / PR #76 merge commit
`0160ac1c7087625a4596edd541524445bc004bd5`).

WP76 locks the wallet intelligence roadmap into repo truth in docs/tests-only form.
It records that top wallets are a major future research signal layer (not an
automatic trade trigger), defines the five wallet intelligence jobs, required wallet
metrics, copyability delay principle, wallet signal categories, suspicious-flow
boundary, research queue influence target (25%–35%), forbidden-boundary list, and
the near-term roadmap WP77–WP82.

WP76 adds no source implementation, no wallet registry, no wallet API client, no
copyability simulator, no automatic copy-trading, no live execution, no paper
trading, no credentials, no network ingestion, no scheduler, no bot loop, no
dashboard, no Hermes/LLM runtime, no dependency or lock-file changes.

WP76 resolves no existing deferred items by implementation. WP76 adds WP76-D001
through WP76-D007 (see table above). WP76-D006 and WP76-D007 are classified P0
because they govern the live execution and copy-trading safety boundaries.

WP77 resolves WP76-D001 only for the docs/schema/tests design scope: architecture,
registry/profile contract, static profile example, signal contract, and static
signal example. It does not resolve any implementation, loader, profiler,
copyability simulator, report generator, paper strategy, wallet API/network, or
execution boundary.

## WP77 Post-WP76 Repo-Truth Reconciliation And Wallet Intelligence Architecture, Registry, Profile, And Signal Contract Deferred Items

WP77 reconciles repo truth after WP76 merge (WP76 / PR #77 merge commit
`91cd26e4fe16d492fa2f7b319fba176ee60cd9d5`; PR #77 head SHA
`831a958cfef716e4974abe6620dfd02f66caff93`).

WP77 creates the first wallet-intelligence architecture/profile/signal contract
layer in docs/schema/tests-only form. It adds the architecture and signal
contract doc, static advisory-only wallet profile example, static advisory-only
wallet signal contract example, and focused tests.

WP77 adds no source implementation, no tools implementation, no wallet data
loader, no wallet API client, no wallet monitoring, no copyability simulator,
no research queue code integration, no report generator, no paper-trading
strategy, no network ingestion, no credentials, no scheduler, no bot loop, no
dashboard, no Hermes/LLM runtime, no dependency or lock-file changes, and no
paper/live trading behavior.

WP77 adds WP77-D001 through WP77-D008 (see table above). WP77-D007 and
WP77-D008 are classified P0 because they govern wallet API/network ingestion
and live-execution safety boundaries.

## WP78 Post-WP77 Repo-Truth Reconciliation And Wallet Trade Event Snapshot Schema, Local Loader, And Validation Deferred Items

WP78 reconciles repo truth after WP77 merge (WP77 / PR #78 merge commit
`24badbfb7a9da06ee4c8ae94795e1f2c862af913`; PR #78 head SHA
`250ff5c0190453c615a28ad7d8a56e37615bffcc`).

WP78 creates the first local/offline wallet trade event fixture layer. It adds a
schema/design doc, static advisory-only example, validator, explicit-path local
loader, and focused tests.

WP78 adds no wallet API client, no network ingestion, no real wallet monitoring,
no wallet skill/niche profiler, no copyability delay simulator, no wallet
intelligence report generator, no research queue integration, no paper-trading
strategy, no credentials, no scheduler, no bot loop, no dashboard, no Hermes/LLM
runtime, no dependency or lock-file changes, and no paper/live trading behavior.

WP78 resolves WP76-D002 and WP77-D001 only for local/offline/read-only schema,
static example, validator, and explicit-path fixture loader scope.
WP78 adds WP78-D001 through WP78-D007 (see table above). WP78-D006 and
WP78-D007 are classified P0 because they govern wallet API/network ingestion
and live-execution safety boundaries.

## WP79 Post-WP78 Repo-Truth Reconciliation And Wallet Skill/Niche Profiler And Research Queue Integration V1 Deferred Items

WP79 reconciles repo truth after WP78 merge (WP78 / PR #79 merge commit
`7ff117f6caf78eab62e6a116db72b60d76d305f5`; PR #79 head SHA
`d59ed363d16262553314730af36812803076696e`).

WP79 creates the first local/offline advisory wallet signal research profile and
research queue annotation layer. It adds a source module, focused tests, and
an advisory doc.

WP79 adds no wallet API client, no network ingestion, no real wallet monitoring,
no copyability delay simulator, no wallet intelligence report generator, no
paper-trading strategy, no credentials, no scheduler, no bot loop, no dashboard,
no Hermes/LLM runtime, no dependency or lock-file changes, no scoring weight
changes, and no paper/live trading behavior.

WP79 resolves WP78-D001 only for local/offline/read-only advisory wallet signal
profile classification scope. WP79 resolves WP78-D002 only for local/offline/
read-only advisory research queue annotation scope.
WP79 adds WP79-D001 through WP79-D006 (see table above). WP79-D004 and
WP79-D005 are classified P0 because they govern wallet API/network ingestion
and live-execution safety boundaries.

## WP80 Post-WP79 Repo-Truth Reconciliation And Copyability Delay Simulator Design Plus Wallet Intelligence Report Contract Deferred Items

WP80 reconciles repo truth after WP79 merge (WP79 / PR #80 merge commit
`4266aefa09da9b06a7e2f547aae70149c203da80`; PR #80 head SHA
`3b65ce56fd94364ad238d306f3bfd8176f3eaf27`).

WP80 creates the copyability delay simulator design and wallet intelligence report
contract in docs/schema/tests-only form. It adds design docs, static JSON examples,
and focused tests.

WP80 adds no wallet API client, no network ingestion, no real wallet monitoring,
no live copyability simulator, no PnL computation, no expected-return calculation,
no paper-trading strategy, no credentials, no scheduler, no bot loop, no dashboard,
no Hermes/LLM runtime, no dependency or lock-file changes, no scoring weight
changes, and no paper/live trading behavior.

WP80 resolves WP79-D001 and WP79-D002 (and related WP76-D004, WP77-D004,
WP77-D005, WP78-D003, WP78-D004) only for docs/schema/tests-only copyability
delay simulator design and wallet intelligence report contract scope. Copyability
delay implementation is deferred to WP81. Report generator implementation is
deferred to WP82.

WP80 adds WP80-D001 through WP80-D006 (see table below). WP80-D004 and
WP80-D005 are classified P0 because they govern wallet API/network ingestion
and live-execution safety boundaries.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP80-D001 | Copyability delay evaluation implementation remains deferred | RESOLVED (WP81 local/offline/read-only evaluator implementation scope) | P3 | WP80 is docs/schema/tests-only. No copyability delay simulator implementation, no delayed-copy computation, no PnL estimate, and no execution-realism model is implemented. WP81 resolved this for local/offline/read-only evaluator implementation scope only. | Any WP that evaluates delayed copyability from local fixtures. | Resolved for local/offline/read-only evaluator scope by WP81 (src/data_layer/wallet_copyability_delay_evaluation.py). Report generator implementation deferred to WP82. |
| WP80-D002 | Wallet intelligence report generator implementation remains deferred | RESOLVED (WP82 local/offline/read-only report generator implementation scope) | P3 | WP80 defines the report contract only. No report generator, no export CLI, no dashboard, and no advisory-consumer handoff is implemented. WP82 resolved this for local/offline/read-only in-memory report generator scope only. | Any WP that generates wallet intelligence reports. | Resolved for local/offline/read-only in-memory report generator scope by WP82 (src/data_layer/wallet_intelligence_report_generator.py). Export CLI, dashboard, and live execution remain deferred. |
| WP80-D003 | Wallet signal paper strategy contract remains deferred | RESOLVED (WP83 contract-definition scope only) | P3 | WP80 is docs/schema/tests-only and does not define paper-trading candidate generation. No paper strategy contract, no paper strategy implementation, and no live strategy implementation is authorized. | Any WP that defines a wallet-signal-driven paper trading strategy contract or paper/live execution behavior. | Resolved for contract-definition scope only by WP83 (docs/wallet_signal_paper_strategy_contract.md, docs/schemas/wallet_signal_paper_strategy_contract_v1.example.json, tests/test_wallet_signal_paper_strategy_contract_docs.py). Paper strategy implementation and all live account access remain deferred. |
| WP80-D004 | Wallet API/network ingestion remains forbidden until explicit future authorization | OPEN | P0 | WP80 is docs/schema/tests-only. It adds no network ingestion, wallet API client, credentials, authenticated endpoints, monitoring, polling, scheduler, or bot loop. | Any WP proposing wallet API access, network ingestion, monitoring, polling, or external wallet data source integration. | Future approved WP explicitly authorizes the network/API boundary and satisfies security, credential, rate-limit, and protected-boundary gates. |
| WP80-D005 | Direct wallet-driven live execution remains forbidden until explicit future authorization | OPEN | P0 | WP80 repeats that copyability delay design and report contract are advisory-only and must not control order placement, cancellations, position sizing, risk override, parameter changes, or live execution. | Any WP proposing wallet-driven order placement, cancellation, position sizing, risk override, parameter auto-change, or live execution. | Future approved live-trading WP satisfies delayed-copy evidence, paper-trading evidence, risk-gate approval, live-trading authorization, credential boundary, execution gateway, kill switch, monitoring, and human approval. |
| WP80-D006 | Human review label and calibration record join remains deferred | OPEN | P3 | WP80 is docs/schema/tests-only and does not define or implement the join between human review labels and calibration records. | Any WP that joins human review label records with calibration records. | Future approved WP84 explicitly scopes join design or implementation with non-signal boundary review and protected-boundary gates. |

## WP81 Post-WP80 Repo-Truth Reconciliation And Local Copyability Delay Evaluation From Validated Fixtures V1 Deferred Items

WP81 reconciles repo truth after WP80 merge (PR #81, merge commit
`ee3d10296dce5504164b7e747b286e8fe5a09991`; PR #81 head SHA
`0f7b2defb6c2392f75be800286304577b800dbef`).

WP81 implements the first local/offline/read-only copyability delay evaluator
in `src/data_layer/wallet_copyability_delay_evaluation.py`. It adds focused
tests and updates simulator design doc and repo-truth docs.

WP81 adds no wallet API client, no network ingestion, no real wallet monitoring,
no live copyability simulation, no dollar PnL computation, no expected-return
calculation, no paper-trading strategy, no credentials, no scheduler, no bot
loop, no dashboard, no LLM/AI agent runtime, no dependency or lock-file changes,
no scoring weight changes, and no paper/live trading behavior.

WP81 resolves WP80-D001 only for the local/offline/read-only copyability delay
evaluator implementation scope. WP80-D002 through WP80-D006 remain OPEN.

WP81 adds WP81-D001 and WP81-D002. WP80-D004 and WP80-D005 remain classified P0.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP81-D001 | Wallet intelligence report generator remains deferred | RESOLVED (WP82 local/offline/read-only report generator implementation scope) | P3 | WP81 adds a local/offline/read-only evaluator only. No report generator, no export CLI, no dashboard, and no advisory-consumer handoff is implemented. WP82 resolved this for local/offline/read-only in-memory report generator scope. | Any WP that generates wallet intelligence reports. | Resolved for local/offline/read-only in-memory report generator scope by WP82 (src/data_layer/wallet_intelligence_report_generator.py). |
| WP81-D002 | Wallet signal paper strategy contract remains deferred | RESOLVED (WP83 contract-definition scope only) | P3 | WP81 adds only an advisory evaluator. No wallet-signal-driven paper strategy contract, no paper strategy implementation, and no live strategy is authorized. | Any WP that defines a wallet-signal-driven paper trading strategy contract or paper/live execution behavior. | Resolved for contract-definition scope only by WP83. Paper strategy implementation and all live account access remain deferred. |

## WP82 Deferred Items

WP82 implements the first local/offline/read-only wallet intelligence report
generator in `src/data_layer/wallet_intelligence_report_generator.py` and
`tests/test_wallet_intelligence_report_generator.py`. It merges from main
at PR #82 merge commit `4f77d5233e51e6379677fd5dec049de372f847a9` (WP81).

WP82 adds no wallet API client, no network ingestion, no real wallet monitoring,
no live report data, no dollar PnL computation, no expected-return calculation,
no paper-trading strategy, no credentials, no scheduler, no bot loop, no
dashboard, no LLM/AI agent runtime, no dependency or lock-file changes, no
scoring weight changes, and no paper/live trading behavior.

WP82 resolves WP80-D002 and WP81-D001 for the local/offline/read-only
in-memory report generator scope only. WP80-D003 through WP80-D006 remain
OPEN. WP81-D002 remains OPEN.

WP82 adds WP82-D001 and WP82-D002. WP80-D004 and WP80-D005 remain classified P0.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP82-D001 | Wallet signal paper strategy contract remains deferred | RESOLVED (WP83 contract-definition scope only) | P3 | WP82 adds only a local/offline/read-only advisory report generator. No wallet-signal-driven paper strategy contract, no paper strategy implementation, and no live strategy is authorized. | Any WP that defines a wallet-signal-driven paper trading strategy contract or paper/live execution behavior. | Resolved for contract-definition scope only by WP83. Paper strategy implementation and all live account access remain deferred. |
| WP82-D002 | Wallet intelligence report export CLI remains deferred | OPEN | P3 | WP82 adds only an in-memory report object. No CLI export tool, no file writer, no dashboard, and no advisory-consumer handoff is implemented. | Any WP that exports wallet intelligence reports to files, stdout, or a dashboard. | Future approved WP explicitly scopes a local/offline report export CLI following the pattern of WP65 (research queue export) or WP72 (calibration report export). |

## WP83 Post-WP82 Repo-Truth Reconciliation And Wallet Signal Paper Strategy Contract V1 Deferred Items

WP83 reconciles repo truth after WP82 merge (PR #83, merge commit
`5c2bd9df3182e6f0035750cd6faa3f6ec8144256`; PR #83 head SHA
`aa88f8d519a04db089cdd6b5b99a5fb3363bde79`).

WP83 creates the first wallet-signal paper strategy contract in
docs/schema/tests-only form only.

WP83 adds no wallet API client, no network ingestion, no real wallet
monitoring, no live copyability simulator, no dollar PnL computation, no
expected-return calculation, no paper strategy implementation, no paper order
model, no paper portfolio ledger, no paper fill model, no paper PnL
calculation, no credentials, no scheduler, no bot loop, no dashboard, no
Hermes/LLM runtime, no dependency or lock-file changes, and no live or paper
account activity behavior.

WP83 resolves WP80-D003, WP81-D002, and WP82-D001 only for
contract-definition scope only. WP80-D004 and WP80-D005 remain classified P0.

WP83 adds WP83-D001. WP82-D002 remains OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP83-D001 | Wallet signal paper strategy contract local validator not started | RESOLVED (WP84 local/offline/read-only validator scope only) | P3 | WP83 defines the contract and static example only. No local validator, no validator implementation, no record loader, and no advisory-consumer handoff is implemented. | Any WP that validates wallet-signal paper strategy contract records from local fixtures. | Resolved for local/offline/read-only validator scope only by WP84 (src/data_layer/wallet_signal_paper_strategy_contract_validator.py, tests/test_wallet_signal_paper_strategy_contract_validator.py). Candidate fixture loader, advisory-consumer handoff, and all other paper strategy implementation remain deferred. |

## WP84 Post-WP83 Repo-Truth Reconciliation And Wallet Signal Paper Strategy Contract Local Validator V1 Deferred Items

WP84 reconciles repo truth after WP83 merge (PR #84, merge commit
`ac66cd582bf2a53cc29869b3e49ffdb7f020ea44`; PR #84 head SHA
`08874da0893c7c29567979b6cd1101833fd0b0c9`) and implements the first
local/offline/read-only wallet signal paper strategy contract validator
in `src/data_layer/wallet_signal_paper_strategy_contract_validator.py`.

WP84 adds no paper strategy implementation, no paper order model, no paper
portfolio ledger, no paper fill model, no paper PnL computation, no
network/API wallet ingestion, no real wallet monitoring, no automatic
following behavior, no live account access, no credentials, no scheduler,
no dashboard, no bot loop, no Hermes/LLM runtime, no dependency or
lock-file changes, and no live or paper account activity behavior.

WP84 resolves WP83-D001 only for local/offline/read-only validator scope.
WP80-D004 and WP80-D005 remain classified P0.

WP84 adds WP84-D001. WP82-D002 remains OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP84-D001 | Wallet signal paper strategy contract candidate fixture loader not started | RESOLVED (WP87 local/offline/read-only fixture loader scope) | P3 | WP84 adds only the local/offline/read-only contract validator. No candidate fixture loader, no advisory-consumer handoff, no fixture-loading pipeline, and no contract record generator is implemented. | Any WP that loads wallet-signal paper strategy contract records from local fixtures for validation. | Resolved by WP87: load_wallet_signal_paper_strategy_candidate_fixtures implemented in src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py; local/offline/read-only; stdlib-only; no file writes; no network; no automation; no credentials; no paper engine. |
| WP86-D001 | Final GitHub PR comment transition policy active during WP86–WP90 | DEFERRED | P3 | WP86 introduces status fragments as the preferred committed evidence surface but keeps final GitHub PR comments required during transition (WP86–WP90). A later WP must explicitly decide to keep, simplify, or replace the final GitHub comment requirement. | Any WP that wants to remove or simplify the final GitHub PR comment requirement. | Future WP (WP90 or later) explicitly reviews the transition, updates docs/status_entries/README.md, and records the decision in repo truth. |
| WP86-D002 | Compact WP template not yet created | DEFERRED | P3 | WP86 creates WP_DRAFTING_STANDARD.md and updates docs/work_package_template.md but does not create a separate compact template. A future WP may create docs/ai/codex/COMPACT_WP_TEMPLATE.md if the full template proves too verbose for simple WPs. | Any WP that specifically requires a compact template. | Future WP explicitly scopes and creates COMPACT_WP_TEMPLATE.md after evaluating whether a compact form is needed without losing required gates. |

## WP87 Post-WP86 Wallet Signal Paper Strategy Candidate Fixture Loader V1 Deferred Items

WP87 implements the first local/offline/read-only wallet signal paper strategy
candidate fixture loader in
`src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py`.

WP87 adds no paper strategy implementation, no paper order model, no paper
portfolio ledger, no paper fill model, no paper PnL computation, no
network/API wallet ingestion, no real wallet monitoring, no automatic
following behavior, no live account access, no credentials, no scheduler,
no dashboard, no bot loop, no Hermes/LLM runtime, no dependency or
lock-file changes, and no live or paper account activity behavior.

WP87 resolves WP84-D001 only for local/offline/read-only candidate fixture loader scope.
WP80-D004 and WP80-D005 remain classified P0.

WP87 adds WP87-D001. WP82-D002, WP86-D001, and WP86-D002 remain OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP87-D001 | Wallet signal paper strategy candidate review report generator not started | RESOLVED (WP89 local/offline/read-only report generator scope) | P3 | WP87 adds only the local/offline/read-only candidate fixture loader. WP89 implements the in-memory candidate review report generator from loaded fixture results only. | Any WP that generates a local advisory report from loaded candidate fixture results. | Resolved on the WP89 branch for local/offline/read-only in-memory report generation only; export, advisory-consumer handoff, paper engine, live execution, credentials, network/API behavior, scheduler, dashboard, and bot loop remain deferred. |

## WP88 Evidence Architecture And Result-Object Invariant Repair

WP88 implements Side 12's Model D evidence architecture feedback. This is a workflow/docs/tests repair WP. No product behavior, runtime behavior, trading behavior, network behavior, credential behavior, or dependency behavior is changed.

WP88 resolves the following deferred items (adding them as ON_BRANCH, not yet merged):

- WP88-D001: evidence architecture transition clarified with Model D — adds EVIDENCE_ARCHITECTURE.md defining PR body as current review surface, status fragment as stable non-self-referential record, final comment as transition-only pointer, and the evidence contradiction matrix.
- WP88-D002: result-object field coverage standard added — adds RESULT_OUTPUT_INVARIANT_STANDARD.md with field inventory, serializer losslessness rule, and invalid-output no-echo full public result scan requirement.
- WP88-D003: manual serializer losslessness standard added — included in RESULT_OUTPUT_INVARIANT_STANDARD.md.
- WP88-D004: root-cause-first follow-up prompt standard added — adds FOLLOWUP_PROMPT_STANDARD.md with classification template and root-cause requirement.

The following items remain OPEN and deferred from WP88:

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP88-DEFER-001 | GitHub-aware evidence verifier tool not implemented | OPEN | P4 | WP88 is workflow/docs/tests only; a GitHub-aware verifier that fetches live PR state is a separate tooling WP. The manual verification path (PRIVATE_REPO_MANUAL_VERIFIED) remains the current required mode. | Any future automated posted-evidence verification for private repos. | Future approved tooling WP explicitly scopes the GitHub-aware verifier; no live execution, no credentials. |
| WP88-DEFER-002 | Removal of final GitHub comments after WP86–WP90 transition | RESOLVED (WP91) | P4 | The transition policy (WP86–WP90) required both committed status entries and final GitHub comments. WP91 explicitly retires mandatory final GitHub evidence comments. Final comments are now optional/non-canonical. PR body is the current review evidence surface. Status fragment is the stable non-self-referential record. | N/A — resolved. | Resolved by WP91: FINAL_COMMENT_POLICY.md created; EVIDENCE_ARCHITECTURE.md, PR_EVIDENCE_REPORTING_DISCIPLINE.md, PR_REVIEW_CHECKLIST.md, VALIDATION_MATRIX.md, status_entries/README.md, PR template all updated. |
| WP88-DEFER-003 | WP89 candidate review report generator | RESOLVED (WP89 local/offline/read-only report generator scope) | P3 | WP88 fixes the inspection system. WP89 implements the next product-support report piece using the new evidence and result-object standards. | After WP88 merges. | Resolved on the WP89 branch for local/offline/read-only in-memory candidate review report generation using WP88 standards; export, dashboard, paper strategy, network/API behavior, credentials, scheduler, bot loop, and live execution remain deferred. |

WP82-D002, WP86-D001, WP86-D002, WP88-DEFER-001, and WP88-DEFER-002 remain OPEN.

## WP89 Wallet Signal Candidate Review Report V1 Deferred Items

WP89 reconciles repo truth after WP88 merge (PR #88, merge commit
`a3cf399b7158fd00af255f57c5bf5cd1024b2c86`) and implements the first
local/offline/read-only candidate review report generator in
`src/data_layer/wallet_signal_candidate_review_report.py`.

WP89 adds no paper strategy implementation, no paper order model, no paper
portfolio ledger, no paper fill model, no paper PnL computation, no
network/API wallet ingestion, no real wallet monitoring, no automatic following
behavior, no live account access, no credentials, no scheduler, no dashboard,
no bot loop, no Hermes/LLM runtime, no dependency or lock-file changes, and
no live or paper account activity behavior.

WP89 resolves WP87-D001 and WP88-DEFER-003 only for local/offline/read-only
in-memory candidate review report generation from WP87 loader output.
WP82-D002, WP86-D001, WP86-D002, WP88-DEFER-001, and WP88-DEFER-002 remain OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP89-D001 | Candidate review report local file export not started | RESOLVED (WP90 local/offline/read-only report export scope) | P3 | WP89 adds only the local/offline/read-only in-memory candidate review report generator. No file export, no CLI, no dashboard, no scheduler, no paper engine, and no live execution is added. WP90 implements deterministic Markdown and JSON export under an operator-specified output directory. | Any WP that writes candidate review report files to disk. | Resolved on the WP90 branch for local/offline/read-only deterministic file export scope only; paper strategy, live execution, credentials, scheduler, dashboard, and bot loop remain deferred. |

## WP90 Candidate Review Report Local Export V1 Deferred Items

WP90 reconciles repo truth after WP89 merge (PR #89, merge commit
`d74c4e696adb5e2fa55345434607a376e8343d9d`) and implements the local/offline/read-only
candidate review report export layer in
`src/data_layer/wallet_signal_candidate_review_report_export.py`.

WP90 adds no paper strategy implementation, no paper order model, no paper
portfolio ledger, no paper fill model, no paper PnL computation, no
network/API wallet ingestion, no real wallet monitoring, no automatic following
behavior, no live account access, no credentials, no scheduler, no dashboard,
no bot loop, no Hermes/LLM runtime, no dependency or lock-file changes, and
no live or paper account activity behavior.

WP90 resolves WP89-D001 only for local/offline/read-only deterministic
Markdown and JSON file export under operator-specified output directory.
WP82-D002, WP86-D001, WP86-D002, WP88-DEFER-001, and WP88-DEFER-002 remain OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP90-D001 | Paper strategy implementation remains deferred | OPEN | P3 | WP90 adds only a local/offline/read-only file export. No paper strategy logic, paper order model, paper portfolio ledger, paper fill model, or paper PnL computation is added or authorized. | Any WP that implements paper strategy, paper orders, paper portfolio, or paper fill logic. | Future approved WP explicitly scopes paper strategy after all protected-boundary gates are satisfied. |
| WP90-D002 | Final comment transition removal after WP86-WP90 | RESOLVED (WP91) | P4 | The transition policy (WP86-WP90) required both committed status entries and final GitHub comments. Removal or simplification decision was deferred to WP91. | N/A — resolved. | Resolved by WP91: mandatory final GitHub evidence comments retired; final comments optional/non-canonical; PR body is current review evidence surface; status fragment is stable non-self-referential record; FINAL_COMMENT_POLICY.md created; all workflow docs updated. |

## WP91 Final Comment Transition Retirement Decision Deferred Items

WP91 reconciles repo truth after WP90 merge (PR #90, merge commit
`7fa1d72c66f77dc3815762fe742144d8e43adad8`) and implements the final comment
transition retirement decision.

WP91 resolves WP88-DEFER-002 and WP90-D002. It retires mandatory final GitHub
evidence comments, documents the decision in FINAL_COMMENT_POLICY.md, and
updates all workflow docs to reflect the new optional final comment policy.

WP91 adds no product source code, no tooling implementation, no runtime/paper/
live/credential/network/API behavior, and no dependency or lock-file changes.

WP88-DEFER-001, WP90-D001, and the long-running deferred items listed below
remain OPEN after WP91.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP91-D001 | GitHub-aware private evidence verifier tool still not implemented | OPEN | P4 | WP91 retires mandatory final comments, making the private-repo verifier less urgent. The local guard remains the only mechanical evidence check. Any future requirement to automatically validate already-posted GitHub PR body content in a private repo is still deferred. | Any WP requiring automatic live GitHub PR content verification for private repos. | Future approved tooling WP explicitly scopes a GitHub-aware private verifier with explicit network/auth boundary defined in repo truth. |

WP82-D002, WP86-D001, WP86-D002, WP88-DEFER-001, and WP90-D001 remain OPEN.

## WP92 Repo-Truth Policy Guard And One-Shot Execution Gate Deferred Items

WP92 reconciles repo truth after WP91 merge (PR #91, merge commit
`5f0d5a594f98f2204698c25d487fc4c826cdcd42`) and implements the repo-truth policy
guard and one-shot execution gate.

WP92 adds no product source code, no tooling implementation, no runtime/paper/
live/credential/network/API behavior, and no dependency or lock-file changes.

WP91-D001 remains OPEN. WP82-D002, WP86-D001, WP86-D002, WP88-DEFER-001,
and WP90-D001 remain OPEN.

| ID | Summary | Status | Priority | Reason | Required Before | Resolution Condition |
|----|---------|--------|----------|--------|-----------------|---------------------|
| WP92-D001 | GitHub-aware private evidence verifier tool still not implemented | OPEN | P4 | WP92 adds docs/tests-only guard and gate; the local guard remains the only mechanical evidence check. Any future requirement to automatically validate already-posted GitHub PR body content in a private repo is still deferred. | Any WP requiring automatic live GitHub PR content verification for private repos. | Future approved tooling WP explicitly scopes a GitHub-aware private verifier with explicit network/auth boundary defined in repo truth. |

## WP93 Candidate Review Report Operator Runbook V1 Deferred Items

WP93 reconciles repo truth after WP92 merge (PR #92, merge commit
`1d9e59aa94aef1609352123473c6eee8fd6d12c1`) and adds a docs-only operator
runbook for the existing local/offline/import-based candidate review workflow.

WP93 adds no source code, no tools, no CLI, no runtime behavior, no paper
engine, no order logic, no live execution, no credentials, no runtime/API/
product/account network behavior, no scheduler, no dashboard, no bot loop, no
dependency file, and no lock file.

WP93 resolves no deferred implementation item. WP90-D001 remains OPEN for
future paper strategy implementation. WP91-D001 and WP92-D001 remain OPEN for
any future GitHub-aware private evidence verifier. Existing runtime, paper,
live, credential, network/API, scheduler, dashboard, bot-loop, and dependency
deferred items remain unchanged.

WP93 final follow-up repairs the WP93 status fragment dynamic PR placeholder
and hardens stable-only status-fragment policy/tests. It resolves no deferred
implementation item and adds no source code, tools, CLI, runtime behavior,
paper engine, order logic, live execution, credentials, runtime/API/product/
account network behavior, scheduler, dashboard, bot loop, dependency file, or
lock file.

## WP94 Candidate Review Workflow Local Smoke Receipt V1 Deferred Items

WP94 reconciles repo truth after WP93 merge (PR #93, merge commit
`01d916242d3ba93c757bcf84f4195183b9ea2336`) and adds a local/offline smoke
receipt for the existing import-based candidate review workflow.

WP94 adds no source code, no tools, no CLI, no runtime behavior, no paper
engine, no order logic, no live execution, no credentials, no runtime/API/
product/account network behavior, no scheduler, no dashboard, no bot loop, no
dependency file, and no lock file. Generated report exports are temp/test-only
and are not committed.

WP94 resolves no deferred implementation item. WP90-D001 remains OPEN for
future paper strategy implementation. WP91-D001 and WP92-D001 remain OPEN for
any future GitHub-aware private evidence verifier. Existing runtime, paper,
live, credential, network/API, scheduler, dashboard, bot-loop, and dependency
deferred items remain unchanged.

## WP154 Adoption Architecture, Dependency Registry And Alpha-Factory Roadmap Deferred Items

WP154 records architecture and adoption governance only. At WP154 publication,
each item below was `OPEN`, had no implementation authority, and required a
separately approved work package. Later status changes must remain explicit.
`LISTED != APPROVED`, `EVALUATE != ADOPT`,
`ADOPT != ACTIVATE`, and `ACTIVATE != AUTHORIZE`.

| ID | Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval requirement |
|---|---|---|---|---|---|
| WP154-D001 | Official Polymarket SDK compatibility/migration decision | A current adapter gap or V2 migration requirement is evidenced | Phase A identity/PIT requirements and refreshed official sources | Listing an SDK means migration, credentials, trading, or activation | YES — compatibility decision WP |
| WP154-D002 | Parquet/Arrow point-in-time storage contract | WP155 is separately approved | Canonical identities, three-time semantics, correction, schema, and mutation rules | Preferred interchange means a production writer or database is authorized | YES — WP155 or later storage-contract WP |
| WP154-D003 | DuckDB/Polars bounded benchmark | A representative PIT dataset contract exists | Exact local workloads, outputs, resource limits, and deterministic version policy | Preferred candidate means dependency adoption | YES — benchmark WP |
| WP154-D004 | Graph schema and NetworkX prototype | Required relation queries and constraints are defined | Canonical node/edge identities and false-positive review method | Prototype means graph database, signal, or automatic equivalence authority | YES — graph contract/prototype WP |
| WP154-D005 | Preregistration and experiment registry contract | Stable PIT lineage exists | Immutable hypothesis, split, metric, cost, exclusion, and failure fields | Experiment registry means strategy approval or promotion authority | YES — registry contract WP |
| WP154-D006 | MLflow compatibility spike | Repository-native registry contract exists | Authority map plus local storage/network isolation rules | MLflow tracking/model registry means promotion or deployment authority | YES — isolated compatibility WP |
| WP154-D007 | First resolution/source-integrity alpha program | Phase C/D contracts pass | Normalized rules, snapshots, relations, constraints, and false-positive process | A constraint violation means proven or tradable alpha | YES — research-program WP |
| WP154-D008 | Wallet behavior persistence and copyability research | PIT wallet-observation use is approved | Look-ahead/survivorship controls, realized/MTM split, liquidity, size, and crowding treatment | Historical wallet profitability means copyability or automatic copy trading | YES — wallet research WP |
| WP154-D009 | Calibration and market-disagreement program | Resolved PIT cohorts exist | Proper scoring rules, horizons, independent evidence, and OOS partitions | Probability disagreement alone means edge | YES — calibration research WP |
| WP154-D010 | Fill/queue model | Granular book/event evidence exists | Timing, fees/rebates, cancellations, partial fills, latency, and opportunity cost | Visible spread means maker return or paper eligibility | YES — fill-model contract/implementation WPs |
| WP154-D011 | NautilusTrader compatibility spike | Every Phase F prerequisite passes | PIT dataset, deterministic strategy input, explicit fill/cost assumptions, and boundary map | Spike means wholesale adoption, core replacement, Polymarket adapter, or live authority | YES — isolated spike WP |
| WP154-D012 | Observability naming and sensitive-data policy | Deterministic paper event families are defined | Owners, redaction, retention, access, and runbooks | Dashboard or alert means accounting, risk, or state authority | YES — observability contract WP |
| WP154-D013 | Prefect research-orchestration decision | Mature idempotent deterministic research jobs exist | Bounded retries/concurrency, exact inputs/outputs, and receipts | Research orchestration means trading scheduler or paper/live scheduling | YES — research-orchestration WP |
| WP154-D014 | Paper-core implementation sequence | Foundational paper contracts are complete | Explicit paper-boundary authority, mode separation, fill/lifecycle/accounting/risk/reconciliation contracts | Paper-eligible means paper-authorized or live-ready | YES — protected paper WPs |
| WP154-D015 | Restricted-live eligibility contract | Sufficient paper and operational evidence exists | Risk, reconciliation, incidents, observability, runbooks, and human approval gate | Restricted-live eligibility means live authorization | YES — restricted-live eligibility WP |

WP154 changes no earlier deferred-item status. No dependency, SDK, storage
engine, graph tool, experiment tracker, trading engine, orchestrator, or
observability component is installed or activated by this registry.

## WP155 Point-In-Time Market Research Data Foundation Deferred Items

WP155 reconciles the WP154 storage and benchmark deferrals without converting
contract work into implementation authority.

- WP154-D002 is `RESOLVED_CONTRACT_ONLY` for the architecture-level
  Parquet/Arrow point-in-time storage contract. The canonical identity,
  three-time, append-only, correction, schema, partition, and non-authority
  decisions now exist in
  `docs/point_in_time_market_research_data_foundation_contract.md`. No schema
  class, writer, dataset, dependency, storage engine, migration, or real-data
  implementation is resolved.
- WP154-D003 remains `OPEN`. WP155 defines a correctness-first bounded
  DuckDB/Polars benchmark contract, but no representative implementation
  dataset, dependency, benchmark runner, or benchmark execution exists.

The original WP155 disposition is preserved in the table below. WP156 later
resolves D001–D003 only for its bounded local in-memory implementation; D004
through D010 remain `OPEN`. Every broader interpretation still has no
implementation authority and requires a separately approved work package.

| ID | Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval requirement |
|---|---|---|---|---|---|
| WP155-D001 | Point-in-time observation schema and validator implementation | WP156 is separately approved | WP155 identities, three-time semantics, lifecycle, failures, and hash preimages | The contract means a schema class or accepted validator already exists | YES — WP156 or later validator WP |
| WP155-D002 | Sanitized synthetic fixture corpus | WP156 is separately approved | Deterministic IDs, exact time precision cases, correction chains, and secret-safe content rules | Synthetic fixtures are real market data, benchmark evidence, or paper evidence | YES — WP156 or later fixture WP |
| WP155-D003 | Source and resolution-rule snapshot schema/validator | Observation validator foundation exists | Source registry, rule snapshot fields, ambiguity vocabulary, and lineage validation | A source URL or current rule text is already a canonical snapshot | YES — source/rule snapshot implementation WP |
| WP155-D004 | Append-only local manifest/reference implementation | Immutable record validation exists | Atomic publication, hashes, recovery, file limits, and retention boundaries | An append-only contract authorizes a persistent writer or database | YES — local manifest/storage implementation WP |
| WP155-D005 | Parquet/Arrow dependency and schema implementation decision | Synthetic reference behavior and schema contract pass | Dependency/security audit, version pin, round-trip schema, null/time compatibility, and file contract | Preferred format means installed, adopted, or production-ready | YES — dependency/schema decision WP |
| WP155-D006 | DuckDB/Polars bounded benchmark execution | Representative synthetic PIT dataset and reference query implementation exist | Exact workloads, resource bounds, deterministic versions, equality oracle, and approved dependencies | Benchmark contract means either engine is adopted | YES — bounded benchmark WP |
| WP155-D007 | Migration and reprocessing contract/implementation | At least two supported schema versions require conversion | Append-only lineage, correction visibility, idempotency, rollback, and receipt design | Migration may overwrite legacy JSONL or backdate corrections | YES — migration contract then implementation WP |
| WP155-D008 | Retention, deletion, legal, and privacy policy | Persistent raw or canonical storage is proposed | Data classification, jurisdiction, retention, deletion exceptions, audit, and legal review | Append-only logical history forbids all legally required deletion | YES — retention/privacy policy WP |
| WP155-D009 | Real public market-data collector/capture decision | Validated schemas and authoritative rate-limit evidence exist | Provider terms, endpoint/rate limits, bounded scheduling policy, storage, observability, and failure controls | Existing manual public GET paths authorize a collector, WebSocket, daemon, or service | YES — collector/capture decision WP |
| WP155-D010 | Relationship-graph prerequisites | Canonical PIT event/market/token/source identities and rule snapshots exist | Node/edge schema, temporal validity, false-positive review, and constraint queries | Metadata overlap means semantic equivalence, signal, or automatic relationship authority | YES — graph contract WP |

WP155 does not change the status of unrelated deferred items. It adds no
dependency, source/runtime behavior, collector, network call, credential,
writer, query engine, benchmark execution, migration, strategy, paper, or live
authority.

## WP156 Bounded Point-In-Time Validator Deferred-Item Reconciliation

WP156 records these exact narrow resolutions:

- WP155-D001:
  `RESOLVED_BOUNDED_LOCAL_IN_MEMORY_VALIDATOR_ONLY`.
- WP155-D002:
  `RESOLVED_SYNTHETIC_IN_MEMORY_CORPUS_ONLY`.
- WP155-D003:
  `RESOLVED_BOUNDED_LOCAL_SOURCE_AND_RULE_VALIDATOR_ONLY`.

Those statuses resolve only frozen caller-mapping validation, the sanitized
in-memory corpus, and source/rule metadata validation. They do not authorize
persistence, production or real market data, collectors, Arrow/Parquet,
DuckDB/Polars, queries, migration, or legacy snapshot-model changes.

WP155-D004 through WP155-D010 remain `OPEN`.

Every WP156 item below is `OPEN`, has no implementation authority, and
requires a separately approved work package.

| ID | Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval requirement |
|---|---|---|---|---|---|
| WP156-D001 | In-memory as-of query and record-set reconstruction | WP157 is separately approved | Valid WP156 record objects, exact cutoff semantics, visible-chain precedence, deterministic result receipt | Batch validation already reconstructs authoritative point-in-time state | YES — WP157 or later query WP |
| WP156-D002 | Persisted append-only manifest/reference layer | Persistent research datasets are separately approved | Atomic publication, immutable file/hash contract, recovery, retention, small-file limits, and operator ownership | In-memory records authorize a writer, catalog, database, or durable quarantine | YES — manifest/storage implementation WP |
| WP156-D003 | Arrow/Parquet dependency and physical schema decision | Reference behavior and representative schema cases pass | Dependency/security audit, version pin, null/time/decimal compatibility, round-trip equality, and file contract | Canonical JSON records mean Arrow/Parquet is installed, adopted, or authoritative | YES — dependency/physical-schema decision WP |
| WP156-D004 | DuckDB/Polars bounded benchmark execution | Representative persisted or approved temporary columnar fixture exists | Approved dependencies, exact workloads, reference oracle, resource bounds, and deterministic versions | A benchmark contract means either engine is adopted | YES — bounded benchmark WP |
| WP156-D005 | Migration and reprocessing | Multiple supported versions require conversion | Append-only migration contract, idempotency, visibility, lineage, rollback, and receipt design | A validator may overwrite legacy JSONL or backdate corrections | YES — migration contract then implementation WP |
| WP156-D006 | Retention, deletion, legal, and privacy policy | Persistent raw or canonical storage is proposed | Data classification, jurisdiction, retention, deletion exceptions, access, audit, and legal review | Logical append-only history overrides required privacy or legal deletion | YES — retention/privacy policy WP |
| WP156-D007 | Real public collector/capture | Valid schemas, storage decision, and authoritative rate-limit evidence exist | Provider terms, endpoints, rate limits, bounded orchestration, observability, failure recovery, and operator controls | Synthetic builders authorize real collection, polling, WebSockets, a daemon, or service | YES — collector/capture decision WP |
| WP156-D008 | Relationship graph | Canonical PIT identity and resolution-rule histories exist | Temporal node/edge schema, deterministic constraints, query cases, and false-positive review | Shared IDs or payload similarity establish semantic equivalence, signal, or trade authority | YES — graph contract/implementation WP |
| WP156-D009 | Persisted quarantine/operator-review workflow | Durable invalid-input handling is approved | Safe storage contract, access/retention, operator roles, promotion lineage, and audit receipts | In-memory quarantine descriptors are a durable queue or automatic promotion mechanism | YES — quarantine workflow WP |
| WP156-D010 | Timestamp precision beyond six fractional digits | A real approved source proves higher precision is required | Canonical representation, comparison, round-trip, hash compatibility, and schema-version decision | The validator may truncate, round, or silently accept unsupported precision | YES — precision/schema WP |

WP156 adds no dependency, file I/O, writer, query, collector, product/runtime
network, credential, scheduler, strategy, paper/live, order, risk,
reconciliation, accounting, or execution authority.

## WP157 Bounded In-Memory As-Of Query Deferred-Item Reconciliation

WP157 records this exact narrow resolution:

- WP156-D001:
  `RESOLVED_BOUNDED_IN_MEMORY_AS_OF_QUERY_ONLY`.

That status resolves only the bounded in-memory point-in-time reconstruction and
as-of query over already-valid WP156 record objects. It does not authorize
persisted queries, manifests, catalogs, real datasets, provider capture,
Arrow/Parquet, DuckDB/Polars, migration, or strategy/paper/live use.

WP156-D002 through WP156-D010 remain `OPEN`.

Every WP157 item below is `OPEN`, has no implementation authority, and requires
a separately approved work package.

| ID | Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval requirement |
|---|---|---|---|---|---|
| WP157-D001 | Persisted append-only manifest/reference implementation | Persistent research datasets are separately approved | Immutable dataset/manifest identity, atomic publication, file/partition manifest, content/file/result hashes, recovery, small-file policy | In-memory reconstruction authorizes a writer, catalog, database, or durable manifest | YES — manifest/reference implementation WP |
| WP157-D002 | Arrow/Parquet physical schema and dependency decision | Reference manifest behavior and representative schema cases pass | Dependency/security audit, version pin, null/time/decimal compatibility, round-trip equality, physical file contract | Canonical JSON records mean Arrow/Parquet is installed, adopted, or authoritative | YES — dependency/physical-schema decision WP |
| WP157-D003 | DuckDB/Polars correctness/performance benchmark | Representative persisted or approved temporary columnar fixture exists | Approved dependencies, exact workloads, reference oracle, resource bounds, deterministic versions | A benchmark contract means either engine is adopted | YES — bounded benchmark WP |
| WP157-D004 | Real public-data capture/adapter integration | Valid schemas, storage decision, and authoritative rate-limit evidence exist | Provider terms, endpoints, rate limits, bounded orchestration, observability, failure recovery, operator controls | Synthetic corpora authorize real collection, polling, WebSockets, a daemon, or service | YES — collector/capture decision WP |
| WP157-D005 | Persisted quarantine/review workflow | Durable invalid-input and conflict-review handling is approved | Safe storage contract, access/retention, operator roles, promotion lineage, audit receipts | In-memory review-only conflict output is a durable queue or automatic promotion mechanism | YES — quarantine/review workflow WP |
| WP157-D006 | Source hierarchy / conflict resolution policy | Human-review governance and precedence rules are approved | Source-rank precedence, deterministic conflict resolution, review roles, audit, and appeal | The query may pick a source-hierarchy winner or auto-resolve a conflict | YES — conflict-resolution policy WP |
| WP157-D007 | Relationship graph | Canonical PIT identity and resolution-rule histories exist | Temporal node/edge schema, deterministic constraints, query cases, false-positive review | Shared ids or payload similarity establish semantic equivalence, signal, or trade authority | YES — graph contract/implementation WP |
| WP157-D008 | Preregistered experiment registry | Reproducible as-of feature/label snapshots are approved | Registry schema, immutability, preregistration, leakage controls, audit | As-of queries authorize backtests, alpha claims, or preregistered experiments | YES — experiment registry WP |
| WP157-D009 | Point-in-time feature/label construction | Approved as-of query snapshots and outcome data exist | Leakage-safe feature/label contract, horizon rules, deterministic joins, validation | Reconstruction authorizes feature engineering, labels, or model training | YES — feature/label construction WP |
| WP157-D010 | Replay/paper consumption contract | Approved as-of snapshots and an execution-boundary policy exist | Deterministic replay contract, no-look-ahead proof, paper-boundary controls, audit | Query results authorize replay, paper, order, or live behavior | YES — replay/paper consumption WP |

WP157 adds no dependency, file I/O, writer, persisted query, collector,
product/runtime network, credential, scheduler, strategy, paper/live, order,
risk, reconciliation, accounting, or execution authority.

## WP158 Append-Only Local Manifest And Deterministic Dataset Snapshot Reference Deferred Items

WP158 is a contract-only package. WP157-D001 through WP157-D010 remain `OPEN` and
separately gated. Every WP158 item below is `OPEN`, has no implementation
authority, and requires a separately approved work package.

| ID | Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval requirement |
|---|---|---|---|---|---|
| WP158-D001 | Manifest writer | RESOLVED_BOUNDED_SQLITE_APPEND | WP161 implements parameterized INSERT-only bounded append over already-valid WP160 objects | Resolution is limited to the explicit-path SQLite schema-1 store | NO for bounded WP161 scope; broader writers remain separately gated |
| WP158-D002 | Manifest reader/verifier | RESOLVED_BOUNDED_SQLITE_VERIFIED_READ | WP161 read-only reopen reconstructs every row through WP160 and revalidates the complete chain | Resolution grants no generic loader or raw-data reader | NO for bounded WP161 scope; broader readers remain separately gated |
| WP158-D003 | Storage path/container selection | RESOLVED_SQLITE_SINGLE_FILE_EXPLICIT_CALLER_PATH | WP161 selects one stdlib SQLite file at an explicit caller path | No default/global/discovered path or analytical container is selected | NO for bounded WP161 scope |
| WP158-D004 | Atomic append and file locking | RESOLVED_BOUNDED_SQLITE_TRANSACTION_AND_FAIL_FAST_SINGLE_WRITER | WP161 uses `BEGIN IMMEDIATE`, rollback/commit, `timeout=0.0`, and no retry | No multi-writer service coordination or backoff is implemented | NO for bounded WP161 scope; service concurrency remains gated |
| WP158-D005 | Crash recovery and torn-write policy | RESOLVED_BOUNDED_SQLITE_ATOMIC_TRANSACTION_PRIMITIVE | SQLite DELETE-journal atomic transactions are the bounded durability primitive; rollback injection proves no partial batch | No destructive power-failure simulator, backup, or recovery service is implemented | NO for bounded WP161 scope |
| WP158-D006 | Schema migration and version compatibility | New schema majors are separately approved | Fail-closed migration, lineage preservation, and version-compatibility matrix | Fixed `1.0.0` schemas mean migration or multi-version support exists | YES — schema-migration WP |
| WP158-D007 | Compaction | Persisted manifests exist and compaction is separately approved | Compaction that preserves append-only lineage and identity, with audit | Append-only permits history rewrite or compaction | YES — compaction WP (forbidden until approved) |
| WP158-D008 | Arrow/Parquet materialization | Dependency and physical-schema decisions are approved | Dependency/security audit, round-trip equality, and physical file contract | Canonical JSON identity means Arrow/Parquet is installed or authoritative | YES — Arrow/Parquet materialization WP |
| WP158-D009 | DuckDB/Polars query layer | Approved persisted or temporary columnar fixtures exist | Approved dependencies, exact workloads, reference oracle, and resource bounds | A reference contract adopts DuckDB or Polars | YES — DuckDB/Polars query WP |
| WP158-D010 | Signing and external attestation | External trust requirements are approved | Signing scheme, key custody, and attestation/audit contract | Identity hashes imply signing or external attestation exists | YES — signing/attestation WP |

## WP161 Bounded Local SQLite Manifest Store Deferred Items

| ID | Deferred item | Status | Required future gate | Non-implication |
|---|---|---|---|---|
| WP161-D001 | Multi-writer retry, backoff, and service concurrency | OPEN | Separate scheduler/service/concurrency WP with bounded retry and observability policy | Fail-fast SQLite locking is not multi-writer coordination |
| WP161-D002 | Schema migration beyond version 1 | OPEN | Separate migration WP with lineage preservation and compatibility matrix | `user_version=1` does not authorize migration |
| WP161-D003 | Storage scale above 256 references or entries | OPEN | Separate scale/storage WP with resource and failure bounds | The bounded store is not a general database service |
| WP161-D004 | Adapters from WP156/WP157 outputs into persistence | RESOLVED_BOUNDED_WP162_REFERENCE_AND_REGISTRATION_ADAPTER | Resolved by WP162 for existing in-memory validated records/query computation into a WP160 logical reference plus registration persisted through the WP161 store; durable raw/real record storage remains separately gated | Resolution does not mean raw records themselves are stored |
| WP161-D005 | Persisted raw or real market data | PARTIALLY_RESOLVED_WP163_RECORD_STORAGE_REAL_DATA_POPULATION_OPEN | WP163 durably stores immutable WP156/WP157 record objects and their canonical full-record payloads, but no real/public network collection has occurred and raw HTTP/source-response bytes are still not stored; real/public data population remains separately gated (WP163-D001) | Durable record-object storage is not raw-byte capture or real-data collection |
| WP161-D006 | Arrow/Parquet analytical materialization | OPEN | Dependency/security and physical-schema WP | Canonical SQLite metadata does not adopt analytical formats |
| WP161-D007 | Backup, export, compaction, or signing | OPEN | Separate durability/audit WP for each capability | Atomic local append does not provide backup or attestation |

## WP162 Deterministic Dataset Persistence Adapter Deferred Items

WP161-D004 is resolved by WP162 only for the bounded reference-and-registration
scope. Every item below is `OPEN`, separately gated, and outside WP162
implementation authority.

| ID | Deferred item | Status | Required future gate | Non-implication |
|---|---|---|---|---|
| WP162-D001 | Durable raw/public point-in-time record storage/materialization | RESOLVED_BOUNDED_WP163_SQLITE_RECORD_STORE_AND_REFERENCE_MATERIALIZATION | Resolved by WP163 for the bounded local SQLite record store: immutable WP156/WP157 record objects and their canonical full-record payloads are durably stored and a WP160 DatasetSnapshotReference resolves to the exact durable record objects; no real/public network collection has occurred and raw HTTP/source-response bytes are not stored | Durable record-object storage is not real/public network collection or raw-byte capture |
| WP162-D002 | Real/public market-data population through a bounded collection path | RESOLVED_BOUNDED_WP164_INITIAL_PUBLIC_MARKET_POPULATION | Resolved by WP164 for a bounded initial-seed only: WP164 performs explicit GET-only Gamma/CLOB reads under the existing local guard, normalizes them into WP156 records, and registers the batch through WP162; repeated/incremental population with committed cross-run lineage remains open (WP164-D001) | An initial-seed public population is not continuous or incremental collection |
| WP162-D003 | Mixed validator-version or parameter-set snapshots | OPEN | Separate multi-provenance WP with committed aggregate semantics | Bounded v1 provenance requires a single validator and parameter set |
| WP162-D004 | External known-parent lineage context committed into adapter provenance | RESOLVED_BOUNDED_WP166_REGISTERED_EXTERNAL_PARENT_CONTEXT | Resolved by WP166 for the bounded registered external-parent context: the schema-2.0.0 `LINEAGE_DELTA_RECORD_BATCH` reference validates actual parent record objects, commits the exact sorted external-parent ids into the v2 reference identity, requires that authority to pre-exist in an earlier manifest entry, and keeps the current and direct-parent contexts each bounded at 256 | Actual parent objects are validated and their ids committed; the current/direct-parent contexts each remain bounded at 256 |
| WP162-D005 | Automated supersede/invalidate lifecycle transitions | OPEN | Separate lifecycle WP with a bounded transition policy | The adapter registers only; it never supersedes or invalidates |
| WP162-D006 | Automated retry/backoff/concurrent adapter orchestration | OPEN | Separate orchestration WP with concurrency and observability policy | A stale-head conflict fails closed and is retried as a fresh invocation |
| WP162-D007 | Feature/label materialization and experiment registry | OPEN | Separate feature/experiment WP with leakage-safe construction review | Dataset lineage registration is not feature or label construction |

## WP163 Bounded Durable Point-In-Time Record Store Deferred Items

WP162-D001 is resolved by WP163 for the bounded local SQLite record-store and
reference-materialization scope, and WP161-D005 is partially resolved (record
objects and canonical payloads can be durably stored; no real/public collection
has occurred and raw HTTP/source-response bytes are not stored). Every item below
is `OPEN`, separately gated, and outside WP163 implementation authority.

| ID | Deferred item | Status | Required future gate | Non-implication |
|---|---|---|---|---|
| WP163-D001 | Real/public Polymarket data population into WP163 through bounded existing read-only collection architecture | RESOLVED_BOUNDED_WP164_INITIAL_PUBLIC_MARKET_POPULATION | Resolved by WP164 for a bounded initial-seed only: WP164 fetches public Gamma/CLOB reads under the existing guard and appends normalized WP156 records into the empty WP163 store before WP162 registration; repeated/incremental population remains open (WP164-D001) | WP163 itself performs no network collection; an initial-seed population is not continuous collection |
| WP163-D002 | Cross-store coordinator for record-store append plus WP162 manifest registration | OPEN | Separate coordinator WP; do not claim true cross-file atomicity | Two independent local SQLite files are not one atomic transaction |
| WP163-D003 | Scale above 4096 records or 128 MiB | OPEN | Separate scale/storage WP with resource and failure bounds | The bounded record store is not a general database service |
| WP163-D004 | Parquet/Arrow analytical materialization | OPEN | Dependency/security and physical-schema WP | Canonical SQLite record storage does not adopt analytical formats |
| WP163-D005 | DuckDB/Polars analytical query layer | OPEN | Dependency/security and query-engine WP | The canonical store exposes no analytical query engine |
| WP163-D006 | Persisted full WP157 query spec and full input provenance for exact as-of replay | OPEN | Separate provenance WP with a committed query/provenance schema | AS_OF_QUERY_RESULT materialization resolves IDs only and never claims query replay |
| WP163-D007 | Migration, backup, export, compaction, or signing | OPEN | Separate durability/audit WP for each capability | Atomic local append does not provide migration, backup, or attestation |

## WP164 Bounded Real/Public Initial Polymarket Population Deferred Items

WP162-D002 and WP163-D001 are resolved by WP164 for the bounded initial-seed
public population only: WP164 performs explicit GET-only Gamma/CLOB reads under the
existing conservative local guard, normalizes them into WP156 records, appends them
into an empty WP163 store, and registers the exact validated batch through WP162.
No credentials, authenticated endpoints, trading, scheduler, or incremental
cross-run lineage are introduced. Every item below is `OPEN`, separately gated, and
outside WP164 implementation authority. The local guard remains the runtime
authority.

| ID | Deferred item | Status | Required future gate | Non-implication |
|---|---|---|---|---|
| WP164-D001 | Incremental/repeated public capture with committed external-parent lineage | PARTIALLY_RESOLVED_WP165_CUMULATIVE_INTERNAL_PARENT_LINEAGE | Partially resolved by WP165: bounded incremental capture now commits deterministic cross-run SOURCE_REVISION/EXACT_DUPLICATE lineage where every parent is a committed internal record inside one cumulative registered snapshot (<=256 records). The scalable external-parent/reference-schema extension beyond 256 remains open as WP165-D001 | WP164 seeds only into an empty store; WP165 keeps every parent committed internally and does not add an external known-parent schema |
| WP164-D002 | Persisted source-snapshot/wire-response fidelity beyond normalized public observations | OPEN | Separate raw-capture WP with retention and security policy | WP164 persists only normalized WP156 observations, never raw HTTP/source bytes |
| WP164-D003 | Pagination/keyset active-market universe beyond one bounded `/markets` request | PARTIALLY_RESOLVED_WP166_MANUAL_ONE_PAGE_KEYSET | Partially resolved by WP166: one manual `GET /markets/keyset` page per invocation captures at most 100 markets and returns the response `next_cursor` for a later manual invocation; there is no automatic page loop, scheduler, or full-universe walk | One manual keyset page per invocation is not an automatic full active-market universe walk |
| WP164-D004 | Historical public trades / Data API ingestion | OPEN | Separate ingestion WP with source and leakage policy | WP164 reads only Gamma markets and CLOB books |
| WP164-D005 | Automated scheduler/orchestrated polling | OPEN | Separate orchestration WP with concurrency and observability policy | WP164 is a single manual invocation with no loop, retry, or sleep |
| WP164-D006 | Official rate-limit-policy reconciliation versus conservative repo-local guard | OPEN | Separate policy WP reconciling venue limits; the local guard remains runtime authority | WP164 does not increase or redesign the existing local budgets |
| WP164-D007 | Cross-file transaction coordinator or stronger recovery ledger | OPEN | Separate coordinator/durability WP; do not claim true cross-file atomicity | Records-first/reference-second ordering plus offline recovery is not one atomic transaction |

## WP165 Bounded Incremental Public Polymarket Cumulative Cross-Run Lineage Deferred Items

WP164-D001 is `PARTIALLY_RESOLVED_WP165_CUMULATIVE_INTERNAL_PARENT_LINEAGE` for the
bounded cumulative case only: WP165 commits deterministic cross-run
SOURCE_REVISION/EXACT_DUPLICATE lineage where every parent is a committed internal
record and the complete prior-plus-new dataset is registered as one WP160
`DatasetSnapshotReference` (<=256 records). WP162-D004 remains OPEN because WP165
does not add an external known-parent reference-context schema; WP164-D003 remains
OPEN because WP165 adds no keyset/pagination; WP164-D002, WP164-D004, WP164-D005,
WP164-D006, WP164-D007 and WP163-D003, WP163-D004, WP163-D005 remain OPEN. No
credentials, authenticated endpoints, trading, scheduler, or manifest/dataset schema
migration are introduced. Every item below is `OPEN`, separately gated, and outside
WP165 implementation authority. The local guard remains the runtime authority.

| ID | Deferred item | Status | Priority | Required future gate | Non-implication |
|---|---|---|---|---|---|
| WP165-D001 | Scalable lineage beyond 256 / external-parent reference schema | RESOLVED_BY_WP166_LINEAGE_DELTA | P1 | Resolved by WP166 within the current physical horizon: the schema-2.0.0 `LINEAGE_DELTA_RECORD_BATCH` reference registers only the current records with an explicit external-parent set already committed by an earlier manifest entry, so physical history grows to the WP163 4096-record horizon with a WP161 256-entry/reference horizon without a cumulative <=256 snapshot | Cross-run parents no longer need to all live in one cumulative <=256 snapshot; growth beyond WP163 4096 records or WP161 256 entries remains open |
| WP165-D002 | Gamma keyset broader active-market universe | PARTIALLY_RESOLVED_WP166_MANUAL_ONE_PAGE_KEYSET | P2 | Partially resolved by WP166: one manual bounded `GET /markets/keyset` page per invocation (<=100 markets) returns the response `next_cursor` for a later manual invocation; an automatic multi-page cursor walk remains open | One manual keyset page per invocation is not an automatic broader-universe walk |
| WP165-D003 | Store growth/partitioning beyond the bounded research horizon | OPEN | P2 | Separate durability/partitioning WP for datasets beyond the bounded research horizon | WP165 stays within the existing bounded SQLite record store and the 256 cumulative cap |
| WP165-D004 | Scheduled recurring collection | OPEN | P2 | Separate orchestration WP with concurrency and observability policy | WP165 is a single manual invocation with no loop, retry, sleep, or scheduler |
| WP165-D005 | Raw source/wire preservation | OPEN | P3 | Separate raw-capture WP with retention and security policy | WP165 persists only normalized WP156 observations, never raw HTTP/source bytes |
| WP165-D006 | Historical public trades / Data API ingestion | OPEN | P2 | Separate ingestion WP with source and leakage policy | WP165 reads only Gamma markets and CLOB books |
| WP165-D007 | Analytical columnar/query layer | RESOLVED_BOUNDED_WP167_ANALYTICAL_RESEARCH_FOUNDATION | P2 | Resolved (bounded) by WP167: a local/offline derived Parquet/Arrow materialization and DuckDB/Polars analytical layer with SQLite as the canonical integrity authority | WP165 added no analytical columnar or query layer; WP167 delivers the bounded analytical foundation while additional adapters and scale remain open successors |

WP158 adds no dependency, file I/O, writer, reader, persistence, persisted
query, collector, product/runtime network, credential, scheduler, strategy,
paper/live, order, risk, reconciliation, accounting, or execution authority, and
no new `src` module or package export.

## WP166 Scalable Lineage-Delta References And Manual Keyset Market-Universe Expansion Deferred Items

WP166 resolves `WP162-D004` as
`RESOLVED_BOUNDED_WP166_REGISTERED_EXTERNAL_PARENT_CONTEXT`, resolves `WP165-D001`
as `RESOLVED_BY_WP166_LINEAGE_DELTA` within the current physical horizon (WP163 4096
records, WP161 256 entries/references), and partially resolves `WP164-D003` and
`WP165-D002` as `PARTIALLY_RESOLVED_WP166_MANUAL_ONE_PAGE_KEYSET` (one manual keyset
page per invocation, at most 100 markets, `next_cursor` returned, no automatic page
loop). Every WP166 item below is `OPEN`, separately gated, and outside WP166
implementation authority.

| ID | Deferred item | Status | Priority | Required future gate | Non-implication |
|---|---|---|---|---|---|
| WP166-D001 | Analytical research store and query layer | RESOLVED_BOUNDED_WP167_ANALYTICAL_RESEARCH_FOUNDATION | P2 | Resolved (bounded) by WP167: derived Parquet/Arrow materialization and DuckDB/Polars queries with SQLite as the canonical integrity authority | WP166 added no analytical columnar or query layer; WP167 delivers the bounded analytical foundation |
| WP166-D002 | Automated cursor orchestration / scheduler | OPEN | P2 | Separate orchestration WP with concurrency, retry, and observability policy | WP166 is a single manual invocation that fetches exactly one keyset page with no loop, retry, sleep, or scheduler |
| WP166-D003 | Record store growth and partitioning beyond 4096 records / manifest beyond 256 entries | OPEN | P2 | Separate durability/partitioning WP for datasets beyond the bounded research horizon | WP166 stays within the WP163 4096-record and WP161 256-entry/reference horizons and performs no pruning, compaction, or rollover |

## WP167 Analytics, External History And Materialization Foundation Deferred Items

WP167 resolves `WP165-D007` and `WP166-D001` as
`RESOLVED_BOUNDED_WP167_ANALYTICAL_RESEARCH_FOUNDATION`: a local, offline,
read-only-against-canonical derived Parquet/Arrow materialization plane with DuckDB
and Polars analytical access and a provenance-separated external-history descriptor,
proven with the pmxt v2 representative adapter, while canonical SQLite records and
manifests stay the sole integrity authority. Every WP167 item below is `OPEN`,
separately gated, and outside WP167 implementation authority.

| ID | Deferred item | Status | Priority | Required future gate | Non-implication |
|---|---|---|---|---|---|
| WP167-D001 | Additional external history adapters (pmxt v1, Jon Becker, Kalshi, OpenMarket) | OPEN | P2 | Separate adapter WPs each with source, schema, license, and provenance policy | WP167 integrates only the pmxt Polymarket Orderbook Archive v2 representative source |
| WP167-D002 | NautilusTrader offline kernel / ParquetDataCatalog (WP168) | OPEN | P2 | Separate WP168 adding NautilusTrader, instrument mapping, catalog, and offline replay parity | WP167 installs no NautilusTrader and builds no catalog or replay engine |
| WP167-D003 | Public WebSocket raw/realtime capture (WP169) | OPEN | P2 | Separate realtime-capture WP with rate-limit, retention, and security policy | WP167 has no WebSocket runtime and no realtime collector |
| WP167-D004 | Public Data API activity/wallet plane (WP169 or narrow successor) | OPEN | P2 | Separate ingestion WP with source and leakage policy | WP167 reads no Data API, wallet, or account activity |
| WP167-D005 | Experiment registry / feature-label identity (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved (bounded) by WP170 with feature/label/sample/split lineage, preregistration, sealed OOS evidence, and append-only registry | WP170 adds research-control metadata only; strategy, cost-adjusted, paper, execution, and live authority remain absent |
| WP167-D006 | Automated external downloader / refresh | OPEN | P3 | Separate network-gated WP with download provenance, retention, and security policy | WP167 accepts only explicitly supplied local Parquet paths and performs no download or network access |
| WP167-D007 | Analytical partition/compaction at scale | OPEN | P3 | Separate durability/partitioning WP if analytical scale proves it necessary | WP167 writes one derived partition per table and performs no rollover, compaction, or pruning |

## WP168 NautilusTrader Offline Kernel And Deterministic Replay Deferred Items

WP168 resolves `WP167-D002` as `RESOLVED_BOUNDED_WP168_NAUTILUS_OFFLINE_REPLAY_FOUNDATION`: a local, offline, deterministic NautilusTrader event-replay foundation with `ParquetDataCatalog` adoption over verified WP167 pmxt-v2 external history. Canonical WP167/PIT truth stays the sole integrity authority. Every WP168 item below is `OPEN`, separately gated, and outside WP168 implementation authority.

| ID | Deferred item | Status | Priority | Required future gate | Non-implication |
|---|---|---|---|---|---|
| WP167-D002 | NautilusTrader offline kernel / ParquetDataCatalog (WP168) | RESOLVED_BOUNDED_WP168_NAUTILUS_OFFLINE_REPLAY_FOUNDATION | P2 | Resolved (bounded) by WP168: offline instrument mapping, catalog build/query, and deterministic replay parity | WP168 delivers the bounded offline replay foundation while realistic fills, executable edge, paper, and live remain open successors |
| WP168-D001 | Public realtime WebSocket + public activity/wallet data plane (WP169) | OPEN | P2 | Separate WP169 with rate-limit, gap/reconnect, retention, and security policy | WP168 has no WebSocket runtime, no Data API, and no realtime collector |
| WP168-D002 | Leakage-safe experiment registry & research-dataset OS (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved (bounded) by WP170 with immutable experiment identities, half-open split/purge/embargo/group rules, preregistration, and OOS lifecycle control | WP170 does not add replay strategy, fill realism, paper, execution, or live authority |
| WP168-D003 | Executable-edge fill/queue/slippage/latency modelling | OPEN | P2 | Separate execution-realism WP with fill-model and queue-position evidence | WP168 is an event-replay proof only and makes no fill, queue, slippage, latency, or executable-edge claim |
| WP168-D004 | Live Polymarket adapter / authenticated execution | OPEN | P1 | Separate credentialed WP with signing, execution, and risk/reconciliation authority | WP168 uses no live data client, no live execution client, no authenticated Polymarket client, and no credentials |
| WP168-D005 | Deterministic tick-regime segmentation | OPEN | P3 | Separate WP only if a valid dataset defeats the finest-tick single-instrument model | WP168 uses one stable instrument at the finest valid increment and does not implement segmentation |

## WP159 Draftability Foundation And Exact Scope Enforcement Deferred Items

WP159 is a local/offline/stdlib-only governance-helper package. Every item below
is `OPEN`, separately gated, and outside WP159 implementation authority.

| ID | Deferred item | Target | Status | Forbidden early interpretation |
|---|---|---|---|---|
| WP159-D001 | Class-specific WP template pack | WP160 | OPEN | WP159 creates or authorizes class-specific templates |
| WP159-D002 | Pre-ready semantic certificate and evidence enforcement | WP160 | OPEN | A `PRE_READY_SEMANTIC_PASS` control already exists |
| WP159-D003 | PR evidence renderer | WP160 | OPEN | WP159 automatically renders or publishes PR evidence |
| WP159-D004 | Active historical exact-diff migration | WP160 | OPEN | Existing historical WPs are retroactively migrated by WP159 |
| WP159-D005 | Manifest-entry and dataset-snapshot-reference validator | WP161 | OPEN | Governance tooling grants feature-validator, persistence, or runtime authority |
| WP159-D006 | Secondary template/checklist/diff-helper-guide propagation | WP160 | OPEN | `docs/work_package_template.md`, PR checklist, or diff-helper guide are updated in WP159 |

WP159 adds no source/runtime behavior, workflow file, dependency, product
network behavior, credential use, scheduler, Hermes runtime, strategy, signal,
paper/live, order, risk, reconciliation, accounting, or execution authority.

## WP6 Generated Artifact Incident Update

WP6 found `.venv-security/` visible as an untracked generated local artifact on stale local `main`. Investigation showed no tracked or staged generated artifact files under `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, or `security-scan-output/`.

This incident is RESOLVED in WP6 by deleting only allowlisted untracked local artifacts, documenting the investigation in `docs/local_generated_artifacts.md`, adding cleanup and preflight guard scripts under `tools/git/`, and requiring `.venv-security/` ignore protection before `tools/security/setup_project_security_tools.py` creates or reuses the project-local security environment.

## WP169 Public Market Truth / Realtime Data Plane Deferred Items

WP169 resolves `WP168-D001` as `RESOLVED_BOUNDED_WP169_PUBLIC_MARKET_TRUTH_REALTIME_DATA_PLANE`: a bounded public unauthenticated Market WebSocket + Data/Gamma/CLOB GET + Polygon read-only RPC acquisition plane with raw-first evidence, gap/reconnect semantics, retention bounds, and closed no-echo output. Canonical PIT truth stays the sole integrity authority. Every WP169 item below is `OPEN`, separately gated, and outside WP169 implementation authority.

| ID | Item | Status | Priority | Resolution path | Evidence |
|---|---|---|---|---|---|
| WP168-D001 | Public realtime WebSocket + public activity/wallet data plane (WP169) | RESOLVED_BOUNDED_WP169_PUBLIC_MARKET_TRUTH_REALTIME_DATA_PLANE | P2 | Resolved (bounded) by WP169: raw-first archive, book gap/reconnect, bounded public GET/RPC, PIT promotion | WP169 delivers the bounded public data plane while orders, OMS, paper, live, and strategy remain open successors |
| WP169-D001 | Direct PIT-to-Nautilus ingestion adapter | PARTIALLY_RESOLVED_WP175E_NATIVE_BRIDGE | P2 | WP175E supplies only the verified WP169-native -> WP172 market-truth bridge; it does not supply or claim a generic PIT -> Nautilus adapter | Merge WP175E for the native bridge extent; separately review any future generic PIT -> Nautilus adapter |
| WP169-D002 | Falsification-grade experiment registry & research-dataset OS (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved (bounded) by WP170 with dataset binding, experiment/feature/label identity, preregistration, evidence lifecycle, and append-only registry | WP170 consumes existing identities as research metadata; WP169 acquisition and PIT authority are unchanged |
| WP169-D003 | Full UMA proposal/dispute/voting/finality/semantic adjudication | OPEN | P2 | Deferred to the WP172 Hermes boundary or a separately certified prerequisite | WP169 captures only basic raw market lifecycle evidence, not adjudication |
| WP169-D004 | Authenticated/private Polymarket access, signing, orders, OMS, execution | OPEN | P1 | Separate credentialed WPs (WP176+) with signing/execution/risk authority | WP169 uses no credentials, no authenticated client, and no order/execution path |

## WP170 Falsification-Grade Experiment Registry & Research Dataset OS Deferred Items

WP170 resolves `WP167-D005`, `WP168-D002`, and `WP169-D002` as
`RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS`: one local/offline
research-control substrate with immutable content identities, leakage-aware temporal
partitions, preregistration, sealed OOS evidence, retained outcomes, and an explicit-path
bounded append-only SQLite registry. Existing canonical PIT and analytical identities are
revalidated and referenced, never replaced. Every open item below is separately gated and
outside WP170 authority.

| ID | Item | Status | Priority | Resolution path | Non-implication |
|---|---|---|---|---|---|
| WP167-D005 | Experiment registry / feature-label identity (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved by the canonical WP170 contract and implementation | No strategy or execution authority follows from research identities |
| WP168-D002 | Leakage-safe experiment registry & research-dataset OS (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved by exact split, purge, embargo, group, preregistration, and OOS lifecycle rules | Offline replay is not a fill, edge, or profitability proof |
| WP169-D002 | Falsification-grade experiment registry & research-dataset OS (WP170) | RESOLVED_BOUNDED_WP170_FALSIFICATION_GRADE_EXPERIMENT_OS | P2 | Resolved by existing-dataset binding, evidence retention, and complete-history registry verification | WP169 acquisition and canonical PIT promotion remain unchanged |
| WP170-D001 | Interactive Operator Cockpit (WP171) | RESOLVED_BOUNDED_WP171_COCKPIT | P2 | Resolved by WP171 with a local read-only FastAPI and four-view React cockpit over validated WP169/WP170 evidence | The cockpit has no authoritative writes, external product network, credentials, strategy, promotion, paper, portfolio, risk, execution, live, or Hermes authority |
| WP170-D002 | Hermes research runtime and autonomous alpha factory (WP172) | OPEN | P2 | Separate WP172 with provider/model, prompt, semantic-adjudication, and human-control gates | WP170 makes no model/provider call and performs no autonomous research loop |
| WP170-D003 | Executable-edge and cost realism (WP173) | OPEN | P1 | Separate WP173 with fill, queue, spread, slippage, latency, capacity, adverse-selection, and cost-model evidence | `OOS_CRITERIA_MET_UNCOSTED` is explicitly not executable edge or expected profit |
| WP170-D004 | Portfolio accounting, reconciliation, and deterministic risk controls (WP174) | OPEN | P1 | Separate protected-boundary WP with explicit risk authority | WP170 never sizes positions, allocates capital, reconciles accounts, or sets risk caps |
| WP170-D005 | Paper-trading execution and evidence (WP175) | OPEN | P1 | Separate paper OMS WP after prior gates | WP170 preregistration/evidence is not paper eligibility or simulated execution |
| WP170-D006 | Authenticated execution gateway and private account access (WP176) | OPEN | P1 | Separate credentialed signing/order/OMS package | WP170 creates or reads no credentials and submits no order |
| WP170-D007 | Restricted and mature live trading (WP177-WP178) | OPEN | P1 | Separate explicit live authorization after all predecessor gates | WP170 grants no restricted-live eligibility or live-trading authority |

## WP171 Interactive Operator Cockpit MVP Deferred Items

WP171 resolves `WP170-D001` as `RESOLVED_BOUNDED_WP171_COCKPIT`: a local
loopback-only, read-only operator view over validated WP169/WP170 SQLite evidence.
All remaining items are separately gated and outside WP171 authority.

| ID | Item | Status | Priority | Resolution path | Non-implication |
|---|---|---|---|---|---|
| WP170-D001 | Interactive Operator Cockpit (WP171) | RESOLVED_BOUNDED_WP171_COCKPIT | P2 | Exact six-route FastAPI backend and four-view React/Vite frontend | A view is not evidence mutation, promotion, execution, or trading authority |
| WP171-D001 | Hermes Runtime + Alpha Factory (WP172) | OPEN | P2 | Separately certified WP172 with provider/model, prompt, semantic-adjudication, orchestration, and human-control gates | WP171 makes no provider/model call, starts no agent loop, and implements no alpha factory |
| WP171-D002 | Executable-edge and cost realism (WP173) | OPEN | P1 | Separately certified cost/fill/queue/slippage evidence package | Displaying `OOS_CRITERIA_MET_UNCOSTED` never claims expected profit or tradeability |
| WP171-D003 | Portfolio, risk, paper, authenticated execution, and live trading (WP174-WP178) | OPEN | P1 | Separate protected-boundary packages with explicit authority | WP171 has no credentials, orders, portfolio, risk, paper, execution, or live path |

## WP171G Lean Agent Execution Governance Deferred Items

WP171G creates no new product/runtime deferral. It reclassifies the existing successor
boundary without implementing it. The parked local WP172 worktree remains separate and
untouched. Side review's prompt/spec authority-divergence finding is resolved in WP171G
through the required exact governance-authority mirror and is not deferred.

| ID | Item | Status | Priority | Resolution path | Boundary note |
|---|---|---|---|---|---|
| WP171-D001 | Alpha + Executable Edge MVP (WP172) | OPEN_REFRAMED_WP171G | P1 | Separately gated WP172 under the mechanically derived governance track after WP171G merges | WP171G adds no Hermes runtime, strategy, cost/fill model, paper, execution, or live capability |
| WP171-D002 | Executable-edge and cost realism | CONSOLIDATED_INTO_WP172_DIRECTION | P1 | WP172 package drafting must define its exact authorized alpha/executable-edge envelope | No successor implementation is authorized by WP171G |
| WP171-D003 | Portfolio, risk, paper, authenticated execution, and live trading | OPEN_PROTECTED_SUCCESSORS | P1 | Later separately authorized PROTECTED packages | FAST/RUNTIME can never authorize credentials, execution, or live capital |

## WP172 Alpha + Executable Edge MVP Deferred Items

WP172 resolves the reframed executable-edge direction as
`RESOLVED_BOUNDED_WP172_EXECUTABLE_EDGE_RESEARCH`: a local/offline assessment boundary
over exact WP170 first-look evidence and WP168 replay lineage. The older Hermes-labelled
WP172 direction is superseded for the critical path and remains untouched. Every item
below remains separately gated and outside WP172 authority.

| ID | Item | Status | Priority | Resolution path | Non-implication |
|---|---|---|---|---|---|
| WP171-D001 | Alpha + Executable Edge MVP (WP172) | RESOLVED_BOUNDED_WP172_EXECUTABLE_EDGE_RESEARCH | P1 | Deterministic decision trace, cost model, conservative fill/cost/capacity assessment, and explicit-path evidence | Research PASS is only eligibility for separately gated WP173 evaluation |
| WP171-D002 | Executable-edge and cost realism | RESOLVED_BOUNDED_WP172_EXECUTABLE_EDGE_RESEARCH | P1 | Exact taker depth, maker queue flow, explicit fees, latency, markout, fill ratio, and frozen capacity grid | No actual-profit or execution claim follows |
| WP172-D001 | Serious Paper Trading System (WP173) | OPEN | P1 | Separately authorized successor with persistent paper-account and accounting semantics | WP172 creates no paper account, OMS, order, portfolio, or capital state |
| WP172-D002 | Portfolio, deterministic risk caps, reconciliation, authenticated execution, and live trading | OPEN_PROTECTED_SUCCESSORS | P1 | Later separately authorized protected packages | No credential, signing, real order, risk, execution, or live authority follows |

## WP173 Serious Paper Trading System Deferred Items

WP173 resolves the paper portion of the WP172 successor boundary as
`RESOLVED_BOUNDED_WP173_SERIOUS_PAPER`: persistent simulated orders, exact spot
accounting, deterministic hard paper risk, hashed-journal recovery/reconciliation,
finite replay, read-only WP169 live-store tailing, manual foreground controls,
and a GET-only cockpit projection. It does not resolve any credentialed or live
boundary. The obsolete Hermes-labelled WP172 remains superseded/off the critical
path; later Hermes/alpha automation may proceed separately during paper soak and
is not a paper gate.

| ID | Item | Status | Priority | Resolution path | Non-implication |
|---|---|---|---|---|---|
| WP172-D001 | Serious Paper Trading System (WP173) | RESOLVED_BOUNDED_WP173_SERIOUS_PAPER | P1 | WP173 deterministic simulated-paper runtime, accounting, risk, recovery, and cockpit | Paper results do not authorize or prove real execution or future profit |
| WP172-D002 | Portfolio, deterministic risk caps, reconciliation, authenticated execution, and live trading | PARTIALLY_RESOLVED_PAPER_ONLY | P1 | WP173 resolves simulated portfolio/accounting/risk/reconciliation only; credentialed and live successors remain open | No private account, credential, signing, venue-order, or live authority follows |
| WP173-D001 | Auth / Signing / Execution Gateway (WP174) | OPEN_PROTECTED_SUCCESSOR | P1 | Separate PROTECTED WP with explicit credential/execution authority and security gates | WP173 has no authenticated client or real order path |
| WP173-D002 | Restricted Live Canary (WP175) | OPEN_PROTECTED_SUCCESSOR | P1 | Separate explicit live-authorization WP after WP174 | Paper readiness is not live readiness |
| WP173-D003 | Mature Controlled Live (WP176) | OPEN_PROTECTED_SUCCESSOR | P1 | Separate mature-live WP after restricted-canary evidence | A canary does not imply mature live authority |
| WP173-D004 | Hermes/alpha automation during paper soak | OPEN_PARALLEL_NOT_PAPER_GATE | P2 | Separately authorized advisory/strategy package may proceed in parallel later | No Hermes/model provider or autonomous promotion authority is added |

## WP174 Protected Authentication, Signing & Execution Gateway Deferred Items

WP174 resolves the bounded Gate A portion of WP173-D001 as
`RESOLVED_BOUNDED_WP174_GATE_A`: official-SDK type integration, deterministic LIMIT
construction, reference-only credential state, fixture-only would-submit/mutation
evidence, reconciliation/heartbeat/access controls, tamper-evident recovery, and a
read-only cockpit projection. It does not load a real secret, invoke a venue mutation,
authorize capital, or start WP175.

| ID | Item | Status | Priority | Resolution path | Non-implication |
|---|---|---|---|---|---|
| WP173-D001 | Auth / Signing / Execution Gateway (WP174) | RESOLVED_BOUNDED_WP174_GATE_A | P1 | WP174 Gate-A-only protected gateway with exact dependencies and fail-closed evidence | Gate A does not grant Gate B mutation or Gate C capital authority |
| WP174-D001 | Real secret loading and real SDK signing/mutation | RESOLVED_WP174B (was BLOCKED_GATE_B) | P1 | Closed by WP174B: ephemeral no-echo signer key, in-memory L2, Deposit Wallet identity, real local LIMIT signing without post, real cancellation transport, and one empty-wallet cancel proof; every real economic create stays GATE_C_REQUIRED | Gate B grants real credential/signing/cancel capability only; it grants no capital, no A3, and no Gate C |
| WP174-D002 | Restricted Live Canary (WP175) | OPEN_PROTECTED_SUCCESSOR | P1 | Separate WP175 certification, readiness, and explicit Gate C authorization after Gate B | WP174 has no A3 state, capital sizing, allowlist, deployment, or live authority |
| WP174-D003 | MARKET orders and broader venue instruction surface | DEFERRED | P2 | Future separately scoped package after LIMIT-only evidence | LIMIT construction does not authorize additional order types |
| WP174-D004 | Hermes, strategy automation, scheduler, or hosted deployment | DEFERRED | P2 | Separate protected-boundary work packages | Gateway control evidence cannot promote research or operate autonomously |

## WP174B Post-Gate-B Deferred Items

| ID | Item | Status | Priority | Resolution path | Boundary note |
|---|---|---|---|---|---|
| WP174B-D001 | Restricted Live Canary (WP175): A3_RESTRICTED_LIVE, dedicated canary capital, one-market/one-strategy allowlist, live exposure/loss limits, manual live arm, and the first real economic LIMIT create | OPEN_PROTECTED_SUCCESSOR | P1 | Separate WP175 certification, readiness, and explicit Gate C authorization | WP174B enables Gate B credential/signing/cancel only; it adds no A3, no capital, and no Gate C |
| WP174B-D002 | Mature long-running credential hardening: CLOB-only Session Keys, OS/cloud secrets manager, owner-key isolation from a long-running process, rotation/revocation | DEFERRED | P2 | WP176 Mature Controlled Live or a separately approved mature-live credential package | WP174B deliberately uses a manual foreground ephemeral owner-signer path with zero capital |

## WP175H Controlled Hermes Research Runtime Core Deferred Items

| ID | Item | Status | Priority | Resolution path | Boundary note |
|---|---|---|---|---|---|
| WP175H-D001 | S10-GATE-H1 Controlled Public Research Pilot: the first real provider-backed / public-web Hermes v0.21.3 research run (installed binary, provider/model choice, account privacy/retention posture, out-of-repo research-only credential, projected cost, exact request, explicit public-web network authorization) | OPEN_RUNTIME_SUCCESSOR | P1 | Separate human/Side S10-GATE-H1 authorization after merge | WP175H is CODE COMPLETE but RUNTIME ACTIVATED: NO; real provider/model call count 0; it does not activate Gate C or start S10-ALPHA-01 |
| WP175H-D002 | S10-ALPHA-01 Multi-Lane Alpha Factory Core: market-universe snapshots, OpportunityCandidate, HypothesisFamily, evidence-lane classification, novelty/negative memory, and research campaigns | DEFERRED | P2 | Separate S10-ALPHA-01 package after a successful S10-GATE-H1 pilot | S10-ALPHA-01 gains no trading authority; WP175H creates no candidate/probability/trade object |
| WP175H-D003 | `REAL_HERMES_BINARY_NOT_PRESENT`: no Hermes Agent v0.21.3 binary is installed on the build machine | OPEN_ACTIVATION_PREREQUISITE | P2 | Resolved as part of S10-GATE-H1 activation, outside repository code | An activation prerequisite, not a code blocker; tests use a fake executable and make zero paid/provider calls |

## WP175I Controlled Research Profile Enforcement Deferred Items

WP175I corrects the merged WP175H external runtime so pristine pinned Hermes v0.21.3
runs under a controlled research profile: it removes `--safe-mode` from the real
research invocation (safe mode suppresses the bundled Firecrawl backend on exact tagged
v0.21.3) and replaces the lost isolation with a deterministic repo-owned non-secret
managed-scope `config.yaml` injected through an ephemeral `HERMES_MANAGED_DIR`, plus a
fail-closed research-home control-plane preflight. It performs zero real
provider/OAuth/Firecrawl/web activity, changes no dependency/workflow, and does not
execute or consume S10-GATE-H1.

| ID | Item | Status | Priority | Resolution path | Boundary note |
|---|---|---|---|---|---|
| WP175I-D001 | S10-GATE-H1 Controlled Public Research Pilot (resumed): the first real provider-backed / public-web Hermes v0.21.3 research run under the controlled profile (installed binary, provider/model choice, account privacy/retention, out-of-repo research-only Firecrawl/OAuth credential, projected cost, exact request, explicit public-web authorization) | OPEN_RUNTIME_SUCCESSOR | P1 | Separate human/Side S10-GATE-H1 authorization after WP175I merge and Side10 review | The prior H1 attempt consumed 0 real research invocations so the authorization is unspent; WP175I is CODE COMPLETE but RUNTIME ACTIVATED: NO; it does not activate Gate C or start S10-ALPHA-01 |
| WP175I-D002 | Bounded same-provider primary transport recovery: exact tagged v0.21.3 `agent/agent_runtime_helpers.py` `try_recover_primary_transport` may rebuild the primary client once after the single ordinary provider attempt exhausts on a transient transport error | DOCUMENTED_H1_EVIDENCE_LIMITATION | P2 | Recorded in the runtime contract and H1 evidence limitations; never suppressed by a Hermes fork | Same provider, same model, same web backend, no second controller invocation, no provider/model/web fallback; it is not a project-level automatic retry |
| WP175I-D003 | S10-ALPHA-01 Multi-Lane Alpha Factory Core | DEFERRED | P2 | Separate S10-ALPHA-01 package after a genuine S10-GATE-H1 PASS plus Side10 review | S10-ALPHA-01 gains no trading authority; WP175I creates no candidate/probability/trade object |

## WP175J Hermes Version Banner Preflight Parser Correction Deferred Items

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WP175J-D001 | S10-GATE-H1 Controlled Public Research Pilot (resumed) | BLOCKED_BY_WP175J_VERSION_PREFLIGHT_PARSER_CORRECTION | P1 | WP175J merge, post-merge review, then a fresh human one-real-run checkpoint | Real H1 research entitlement remains unconsumed: research invocations 0, provider/API calls 0, Firecrawl research calls 0; WP175J does not activate runtime |
| WP175J-D002 | S10-ALPHA-01 Multi-Lane Alpha Factory Core | DEFERRED | P2 | Genuine S10-GATE-H1 PASS plus Side11 quality review | Immediate successor is H1, not Alpha; Gate C and WP176 remain separately blocked |

## WP175K Sanitized Hermes Failure-Evidence Capture Hardening Deferred Items

WP175K hardens only the observability of a failed controlled Hermes research
invocation. After WP175J merged, the single authorized S10-GATE-H1 real invocation was
CONSUMED (= 1) and FAILED (FAIL_RUNTIME_CONTRACT / EXIT_CODE_NONZERO, usage evidence
MISSING, validated research NONE). DIAG-01 = ROOT_CAUSE_NARROWED_NOT_CONFIRMED and
DIAG-02 = PREACCOUNTING_PATHS_PASS_ROOT_CAUSE_STILL_UNRECOVERABLE. WP175K retains a
sanitized, bounded, secret/path-scrubbed stderr excerpt (raw stderr still forbidden)
and bumps the receipt schema to `hermes-research-run-receipt/1.2.0`; it does not repair
the exit-1 mechanism, activate runtime, authorize any H1 rerun, or unlock Alpha.

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WP175K-D001 | Second real S10-GATE-H1 run decision | BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION | P1 | A separate new human/governance decision after WP175K merge and Side11 review | The one authorized H1 run was consumed (= 1) and failed; the root cause is unconfirmed and unrecoverable from retained evidence; a software correction does not itself recreate H1 authorization; H1 rerun is NOT AUTHORIZED |
| WP175K-D002 | S10-GATE-H1 unique-diagnosis on any future run | ENABLED_BY_SANITIZED_EVIDENCE_HARDENING | P2 | Only exercised if a future H1 run is separately authorized | Receipt 1.2.0 now preserves a sanitized bounded stderr excerpt, redaction/status flags, and usage-file presence so a future exit-1 is uniquely diagnosable; no network/provider/Firecrawl activity during WP175K |
| WP175K-D003 | S10-ALPHA-01 Multi-Lane Alpha Factory Core | DEFERRED | P2 | Genuine S10-GATE-H1 PASS plus Side11 quality review | Immediate successor is the second-run governance decision, not Alpha; Gate C and WP176 remain separately blocked |

## WP175L Sanitized Windows Runtime Envelope And Startup Preflight Deferred Items

WP175L corrects the controlled Hermes wrapper runtime environment and adds an offline
startup preflight. Historical real H1 research invocations consumed = 2; H1 #2's confirmed
root cause is
`CONTROLLED_WINDOWS_RUNTIME_ENVIRONMENT_INSUFFICIENT_FOR_HERMES_PROFILE_INITIALIZATION`
(the merged controlled child lacked ordinary Windows home/runtime context, so pinned
Hermes profile-home resolution raised `RuntimeError: Could not determine home
directory.`; research/provider-binding/Firecrawl were NOT_REACHED). WP175L uses a HYBRID
sanitized runtime envelope: it inherits only real benign Windows MACHINE/runtime values
and SYNTHESIZES the per-user identity roots (USERPROFILE/HOMEDRIVE/HOMEPATH/APPDATA/
LOCALAPPDATA) under a backend-owned ephemeral runtime-user root, keeps the secret-name
rejection, adds an explicit injection denylist, and gates research on an offline
`hermes --help` startup preflight. Side11 Finding E on head c73934c required this hybrid
correction so a sticky personal `%LOCALAPPDATA%\hermes\active_profile` cannot re-home the
explicit H1 HERMES_HOME. WP175L does not activate the runtime, authorize any H1 run, or
unlock Alpha.

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WP175L-D001 | Controlled startup preflight using the exact patched runner | POST_MERGE_LOCAL_VERIFICATION | P1 | After WP175L merge and Side11 review, run the controlled startup preflight (not a research invocation) | Verifies the sanitized envelope resolves Hermes profile-home offline; consumes no H1 research slot; provider/Firecrawl/network 0 |
| WP175L-D002 | Third real S10-GATE-H1 run (H1 #3) decision | BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION | P1 | A separate new human/governance decision after WP175L merge, post-merge verification, and Side11 review | Two real H1 runs (H1 #1, H1 #2) were consumed and failed, so the next possible invocation is H1 #3; a wrapper-runtime correction does not itself recreate H1 authorization; H1 #3 is NOT AUTHORIZED |
| WP175L-D003 | S10-ALPHA-01 Multi-Lane Alpha Factory Core | DEFERRED | P2 | Genuine S10-GATE-H1 PASS plus Side11 quality review | Immediate successor is post-merge preflight verification then the H1 #3 / third-run governance decision, not Alpha; Gate C and WP176 remain separately blocked |

## WP175M — Hermes Draft Contract Alignment And Schema Diagnostics

WP175M aligns the Hermes draft prompt/output contract with the deterministic validator and
adds sanitized schema-failure observability. H1 #3 (the third real S10-GATE-H1 run) was
consumed and failed `OUTPUT_SCHEMA_INVALID` / `DRAFT_FIELD_MISSING` because the permanent
instruction referenced a research-draft schema the envelope never embedded (only
`draft_schema_version`); the model improvised an alternative schema and the validator
failed closed at first missing canonical field `advisory_only`. WP175M embeds a canonical
machine-generated `draft_output_schema` derived from the validator's own constants, bumps
the receipt to `hermes-research-run-receipt/1.3.0` with sanitized additive evidence, and
preserves the actual provider/model on a schema failure. It does not activate the runtime,
authorize any H1 run, perform substantive post-hoc repair, inject authority flags, or
unlock Alpha.

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WP175M-D001 | Controlled structured-output contract validation using the exact patched runtime | POST_MERGE_LOCAL_VERIFICATION | P1 | After WP175M merge and Side11 review, validate the embedded output contract locally (not a research invocation) | Confirms the generated schema and validator required sets remain identical; consumes no H1 research slot; provider/Firecrawl/network 0 |
| WP175M-D002 | Fourth real S10-GATE-H1 run (H1 #4) decision | BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION | P1 | A separate new human/governance decision after WP175M merge, post-merge verification, and Side11 review | Three real H1 runs (H1 #1, H1 #2, H1 #3) were consumed and failed, so the next possible invocation is H1 #4; a prompt/output-contract correction does not itself recreate H1 authorization; H1 #4 is NOT AUTHORIZED |
| WP175M-D003 | S10-ALPHA-01 Multi-Lane Alpha Factory Core | DEFERRED | P2 | Genuine S10-GATE-H1 PASS plus Side11 quality review | Immediate successor is post-merge contract verification then the H1 #4 / fourth-run governance decision, not Alpha; Gate C and WP176 remain separately blocked |

## WP175N — Multi-Lane Alpha Factory Core (S10-ALPHA-01, current review target)

WP175N implements the first canonical Alpha Factory research-memory substrate (record model
plus a separate append-only SQLite registry, application id 1464877425, distinct from
WP170's 1464877424). It is unlocked by `GENUINE_H1_PASS` (accepted H1 #4; historical real
H1 invocations 4; H1 #5 NOT AUTHORIZED). Alpha Factory records research history only; it
performs no qualification, prioritization, economics, scheduling, wallet ingestion, Hermes
runtime call, or network activity, and creates no strategy/paper/live/Gate-C authority.

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WP175N-D001 | S10-WALLET-01 Public Wallet Event Ingestion & PIT Identity Evidence | DEFERRED | P2 | After WP175N merge and Side11 exact-head review | Immediate software successor after WP175N merge; NOT started by WP175N; the wallet gate is wallet-specific and not global |
| WP175N-D002 | S10-HERMES-CTX-01 read-only project-aware context broker | DEFERRED | P2 | After S10-WALLET-01 | Consumes verified Alpha memory; no repository shell/admin or trading authority |
| WP175N-D003 | S10-ALPHA-02 universe triage / freshness / material-change / reopen / prioritization | RESOLVED_BY_S10_ALPHA_02_BOUNDED_SCOPE | P3 | S10-ALPHA-02 review and merge | Resolved only for the deterministic bounded observed-PIT-universe, explicit Alpha-memory-posture, reopen-decision, complete-triage, core/exploration/audit allocation, inert capture-request-data, and separate append-only discovery-memory scope; no scheduler, qualification, economics, or live authority |

## S10-ALPHA-02 — Residual Discovery-Control-Plane Deferrals

S10-ALPHA-02 implements complete triage of the exact frozen observed PIT universe, not exhaustive
external acquisition or empirical optimization. These residuals are nonblocking for its bounded
deterministic contract and require separate authority.

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| S10-ALPHA-02-D001 | External all-Polymarket universe completeness and automated exhaustive acquisition | DEFERRED | P2 | Separate product-network/acquisition package | ALPHA-02 truth remains BOUNDED_OBSERVED_UNIVERSE / external completeness UNPROVEN; no crawler, pagination loop, or market fetch is authorized |
| S10-ALPHA-02-D002 | Empirical tuning of soft-change thresholds, queue capacity, lane reservations, category caps, and audit seed policy | DEFERRED | P2 | Separately preregistered evidence/tuning package | V1 exposes explicit parameters and deterministic behavior; it does not claim the chosen values are universal research truths |
| S10-ALPHA-02-D003 | S10-ALPHA-03 recurring research campaign, scheduler, budgets/rates, and provider escalation | DEFERRED | P2 | S10-ALPHA-03 | No cron, daemon, worker, loop, provider invocation, or automatic capture consumption exists in ALPHA-02 |
| S10-ALPHA-02-D004 | S10-ALPHA-04 downstream outcome learning and adaptive allocation | DEFERRED | P2 | S10-ALPHA-04 | ALPHA-02 allocation is fixed pre-outcome deterministic control; no settlement-informed selection or bandit learning |
| S10-ALPHA-02-D005 | Qualification, executable economics, paper trading, execution, Gate C, and live capital | DEFERRED_BLOCKED_BY_SEPARATE_GATES | P1 | S10-GATE-AF1 then QUAL/GATE-QUAL/WP170/WP172/WP173 and human Gate C | Discovery priority is not expected return, qualification, strategy, executable edge, or paper/live authority |

## Wallet-Intelligence Roadmap Anchor (durable)

Objective: prove when PUBLIC wallet behavior deserves strategic use; do not assume
profitable wallets should be copied. Frozen packages: WALLET-01 (Public Wallet Event
Ingestion & PIT Identity Evidence), WALLET-02 (PIT Profiles, Archetypes, Specialization &
Independent Clusters), WALLET-03 (Historical Copyability & Microstructure Evidence),
WALLET-04 (Anomaly, Public-Information Control, Consensus & Incremental Edge), and
GATE-WALLET-01 (wallet-specific evidence gate). Frozen semantics: the wallet gate is NOT
global; unrelated Alpha hypotheses do not wait for wallet packages; wallet-derived
hypotheses must satisfy wallet-specific evidence; WP169 public API/CLOB/Polygon
acquisition must be reused, not duplicated; no deanonymization; no insider-probability
claims; no nonpublic information; Hermes wallet context is read-only/research-only; Alpha
Factory owns canonical research memory; and wallet evidence creates NO shortcut around
qualification/economic/paper/live/Gate-C authority (no wallet live shortcut created).

| ID | Item | Status | Priority | Resolution gate | Notes |
|---|---|---|---|---|---|
| WALLET-01 | Public Wallet Event Ingestion & PIT Identity Evidence | ROADMAP_ANCHOR_BLOCKED | P2 | Genuine H1 PASS + Side11 quality acceptance; S10-ALPHA-01 merged/verified; fresh live state; exact WP169 inspection | No wallet code is implemented in WP175L; the wallet gate is wallet-specific and not global |
| S10-WALLET-01-D001 | Universal raw-retention/licensing storage backend | DEFERRED_NONBLOCKING | P3 | Separate storage/licensing decision | S10-WALLET-01 requires durable SHA-256 + raw reference and downgrades replay fidelity when raw bytes/ref are unavailable; no universal blob/tick warehouse is frozen. Configurable/deferred. |
| S10-WALLET-01-D002 | Live/public chain acquisition provider (RPC/indexer) | DEFERRED_NONBLOCKING | P3 | Separate gated adapter WP | S10-WALLET-01 implements canonical chain-native evidence schema, deterministic LOCAL chain import/normalization, API/chain reconciliation, and finality/reorg representation, but adds no RPC/indexer credentials or always-on listener. A live chain adapter is separately gated. |
| S10-WALLET-01-D003 | Wallet n_eff / promotion / cluster thresholds | PARTIALLY_RESOLVED_BY_WALLET_02 | P3 | Future empirical threshold package | S10-WALLET-02 implements deterministic independent-group sample evidence, PIT cohorts, descriptive specialization, and strong-evidence public-account clustering. Universal promotion, minimum-n, HHI, posterior, and empirical cluster thresholds remain deliberately deferred; no SKILLED/UNSKILLED or specialist promotion state was invented. |
| S10-WALLET-01-D004 | L2 / fill / copyability calibration | DEFERRED_TO_LATER_WP | P3 | ALPHA-02 / WALLET-03 / QUAL / WP170 | Executable copy edge, latency, spread/depth/slippage, partial fill, crowding/capacity remain later WPs. |
| S10-GATE-AF1-D001 | Real AF1 public population and up to three controlled blind provider invocations | RESOLVED_BY_ATTEMPT_04_CONSUMED | P1 | Attempt-04 authorized and executed on runtime execution head dead42658e8fc9139d82f772e1f2fff67ba07674 (envelope SHA-256 627fcd4cb6c946cabfb86bb2b38ef18b27b8c7fbb73400314b96adeb1d3530b1) | Exactly 1 public population (25/1 actual, built 26, inserted 26) and 3 controller invocations, all RESEARCH_DRAFT_VALIDATED; zero retry/fallback/replacement/fourth call; receipt-reported accepted cost USD 0.0 per case; backend telemetry NOT_DIRECTLY_ATTESTED and Firecrawl count UNKNOWN remain truthful limitations |
| S10-GATE-AF1-D002 | Independent blinded Side12 usefulness review | RESOLVED_BY_SIDE12_BLIND_REVIEW | P1 | Decision SHA-256 eba65849219faf65f27849a6b5be0fe1c1cf27e0cc47bb3ada084afb77d99bc3 over bundle SHA-256 12058c282bd24d332bb767b7a75c201e4f0b9fcbdebdf0f7cb09c07672a8e74f | All three opaque slots labelled USEFUL_RESEARCH_OUTPUT; verify-review VALID; deterministic finalization produced AF1_PASS with receipt af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2 |
| S10-GATE-AF1-D003 | Qualification, wallet copyability, ALPHA-03/04, WP170/172/173, execution, Gate C and live capital | DEFERRED_BLOCKED_BY_SEPARATE_GATES | P1 | AF1_PASS recorded; later separately approved packages and human gates | AF1_PASS measures research-system quality only and never proves hypothesis quality, predictive edge, executable edge, or profitability; non-wallet S10-QUAL-01 is now separately eligible to be drafted/authorized but not authorized |
| S10-GATE-AF1-D004 | AF1 Attempt-04 successor runtime after consumed Attempts 01/02/03 | RESOLVED_ATTEMPT_04_CONSUMED | P1 | Attempt-04 ran once on runtime execution head dead42658e8fc9139d82f772e1f2fff67ba07674 in workspace_attempt_id s10-gate-af1-attempt-04 | Attempt-04 is CONSUMED and finalized AF1_PASS; no Attempt-05 or other additional AF1 attempt is authorized; Attempt-03 evidence stays immutable and noncanonical |
| S10-GATE-AF1-D005 | Frozen contract digest verification on non-LF checkouts | OPEN_OPERATIONAL_CONSTRAINT | P2 | Run Phase B from a checkout whose working-tree bytes of the three frozen contract files equal the committed LF bytes | run-real compares raw on-disk bytes with the authorized digests and fails closed as STATE_DRIFT with zero calls on byte drift, including CRLF conversion |
| S10-GATE-AF1-D006 | Research HERMES_HOME clean control-plane admission of Hermes-seeded SOUL.md | RESOLVED_BY_S10_HERMES_CTX_02 | P1 | PR #194 merged at 15097f70f5f5358879fde73b2b30d26ecdb80402 admits only the exact pinned stock SOUL.md (667 bytes, SHA-256 36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f) | Pinned Hermes seeds SOUL.md into every initialized home; the dedicated AF1 home is re-verified by names and the stock-file digest only; no credential content is read and no home is mutated |
| S10-GATE-AF1-D007 | AF1 Attempt-03 request-builder secret-scanner false positive on canonical public event id | RESOLVED_BY_S10_HERMES_CTX_03 | P1 | PR #195 merged at 1ccf42df0e95586b98c79a0bf912343f9c34df31 admits exact canonical public Polymarket ids inside public_market_context only; AF1 adds a live-shaped cross-layer regression | Attempt-03 stays CONSUMED with TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT and AF1 gate result NONE (population succeeded 25/1/26/26; provider/model/Firecrawl calls 0; cost USD 0); its local evidence stays immutable and noncanonical and is never converted into Attempt-04 |
| S10-QUAL-01-D001 | Qualification packet acceptance decision (PASS/FAIL/INCONCLUSIVE) | CAPABILITY_RESOLVED_BY_S10_GATE_QUAL_01_IMPLEMENTATION | P1 | S10-GATE-QUAL-01 deterministic gate implemented on branch codex/s10-gate-qual-01-acceptance-gate (base b5cfb9846ff78af2d1a260843d5f2f1a67639305); merge still requires Side13 exact-head review and Karl | Only the implementation-capability dependency is resolved: qualification_gate.py re-binds the exact candidate, Alpha ancestry/current lineage, AF1 receipt and provenance manifests and emits QUAL_PASS/QUAL_FAIL/QUAL_INCONCLUSIVE. No real candidate has been evaluated or has passed; synthetic outcomes are test fixtures only. First real evaluation tracked by S10-GATE-QUAL-01-D001. |
| S10-QUAL-01-D002 | WP170 B1 public-non-market FeatureDefinition / model / calibrator capability | DEFERRED_TO_WP170_CANDIDATE_WORK | P1 | Separately gated WP170 candidate-specific work after a valid S10-GATE-QUAL-01 result | Current WP170 SAFE_FEATURE_SOURCE_DEPENDENCIES are market-observation fields only; S10-QUAL-01 freezes qualification logical feature refs and does not claim current WP170 can instantiate B1 PUBLIC_NON_MARKET inputs. experiment_os.py / experiment_registry.py unchanged. |
| S10-QUAL-01-D003 | Wallet-dependent qualification evidence lane | DEFERRED_BLOCKED_BY_WALLET_GATE | P2 | S10-WALLET-03 -> S10-WALLET-04 -> S10-GATE-WALLET-01 real receipt contract, then a same-capability S10-QUAL integration | WALLET_DEPENDENT packets fail WALLET_GATE_REQUIRED with no record; no placeholder wallet-gate schema, id prefix or bypass exists. |
| S10-QUAL-01-D004 | First real (non-synthetic) qualification candidate packet | DEFERRED_NOT_AUTHORIZED | P2 | Separate explicit authorization after S10-QUAL-01 merge | S10-QUAL-01 evidence uses deterministic synthetic fixtures plus the committed AF1 receipt as a compatibility fixture only; no production/local research candidate was built or qualified. |
| S10-GATE-QUAL-01-D001 | First real qualification evaluation, durable real receipt handling and WP170 receipt binding | DEFERRED_NOT_AUTHORIZED | P1 | Separately authorized real NON_WALLET candidate build/evaluation with the merged gate, then separately authorized candidate-specific WP170 work | S10-GATE-QUAL-01 builds the deterministic gate only: no real candidate is built or evaluated, no real QualificationGateReceipt exists or is persisted, and no persistence mechanism, gate registry or PreregisteredExperiment qualification-receipt field is invented. Only a real valid QUAL_PASS makes candidate-specific WP170 work eligible to be drafted. |
| S10-ALPHA-REAL-01-D001 | Merged ValidatedResearchDraft discards the substantive research lists | DEFERRED_NONBLOCKING_TOOL_SIDE_WORKAROUND | P2 | Future separately gated src WP may retain the validated lists in the controller result | S10-ALPHA-REAL-01 recaptures the bounded stdout through a capture backend, re-applies merged capture_final_response and validate_research_draft and requires equality on the six retained fields before building FULL_DRAFT_PROJECTION; no src/ change. |
| S10-ALPHA-REAL-01-D002 | Hermes receipt binds no response or draft digest | DEFERRED_NONBLOCKING | P3 | Future separately gated receipt-schema WP | The binding used here is equality of the revalidated draft with the controller's six retained validated fields plus the projection SHA-256 bound in the Side13 decision. |
| S10-ALPHA-REAL-01-D003 | Cited webpage content bytes are not captured | DEFERRED_NONBLOCKING | P3 | Separate source-capture/licensing decision | Alpha ResearchSourceReference content_sha256 is null for every S10-ALPHA-REAL-01 source; no page hash is fabricated. |
| S10-ALPHA-REAL-01-D004 | Provider cost evidence is reported-estimate only | OPEN_OPERATIONAL_CONSTRAINT | P3 | Invoice-level attestation outside this repo | USD 5 is the accepted REPORTED estimated-cost ceiling enforced by the merged post-run gate; it is not invoice-attested and not a pre-spend hard limit. Attempt-01 receipt reported USD 0.0 with cost status included and cost source none. |
| S10-ALPHA-REAL-01-D005 | Qualification/data readiness of the RESEARCH_SUPPORTIVE NWS daily-rain lineage | DEFERRED_TO_S10_QUAL_REAL_01 | P1 | Separately drafted and authorized S10-QUAL-REAL-01 | RESEARCH_SUPPORTIVE (episode alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c) is not a qualification PASS, OOS evidence, executable edge or profitability claim. Missing historical-vintage, price-construction, rule-census, sample/power and PIT facts remain explicit; the successor must independently establish real dataset refs, PIT provenance, sample/power, a B0/B1/B2 or generic metric plan, critical execution evidence and exact AF1 binding. |
| S10-ALPHA-REAL-01-D006 | Machine-state-dependent operator CLI test after human home setup | RESOLVED_IN_PR200_D006_MICRO_AMENDMENT | P3 | Side13-authorized three-path test-hermeticity micro-amendment on PR #200 after head 31565430569cd0e8651df6b61c53bde24730bf82 | Root cause: tests/tools/alpha/test_run_s10_alpha_real_01.py::test_cli_prepare_prints_closed_code_only was non-hermetic; it ran the CLI against the real pinned research home and assumed that home was absent, so it failed on the operator machine after Karl's authorized manual home setup. Resolution: the test now injects the HUMAN_CREDENTIAL_SETUP_REQUIRED / PRE_RUNTIME_STOP condition through the operator check_home seam and asserts the exact closed stderr line, exit 2, empty stdout and no workspace, independent of the physical home. Operator/runtime behavior did not change (tools/alpha/run_s10_alpha_real_01.py unchanged); runtime evidence and the canonical Alpha lineage were not rerun or mutated. |
| S10-NDFD-GRIB-01-D001 | NDFD decoder capability beyond Python 3.12 on ubuntu-24.04 / windows-2022 | DEFERRED_NOT_CLAIMED | P3 | Separately gated dependency WP if a Python 3.13/3.14, macOS or ARM decoder target is needed | eccodes 2.48.0 publishes no CPython 3.14 win_amd64 wheel; the optional ndfd-grib extra is pinned to Python 3.12 and only the two hosted ndfd-grib-compat targets are claimed. Global project Python support (3.12-3.14) is unchanged. |
| S10-NDFD-GRIB-01-D002 | ecCodes message API leniency on a missing GRIB2 end section | CONSUMER_CONSTRAINT_HONORED_BY_S10_QUAL_DATA_01_PRODUCTION_GUARD | P2 | S10-QUAL-DATA-01 historical NDFD adapter | codes_new_from_message decodes a message whose 7777 end section is missing and returns a handle for bytes without GRIB magic; any consumer must validate magic, edition 2, section-0 total length and the trailing 7777 before decoding (as the focused test does). Truncation inside header/data sections is refused by ecCodes itself. |
| S10-NDFD-GRIB-01-D003 | S10-QUAL-DATA-01 NDFD_DEPENDENCY_REQUIRED decoder blocker | RESOLVED_BY_S10_NDFD_GRIB_01_ON_GREEN_EXACT_HEAD_CI | P1 | Redraft/resume S10-QUAL-DATA-01 (separately gated) | Resolved only by green exact-head hosted ndfd-grib-compat (ubuntu-24.04 and windows-2022 / Python 3.12) and ndfd-grib-dependency-audit evidence recorded in the S10-NDFD-GRIB-01 PR body. S10-QUAL-DATA-01 itself remains unimplemented; no QualificationC| S10-QUAL-DATA-01-D001 | B0 canonical-PIT compatibility of PendulumFlow-derived checkpoint market history | DEFERRED_TO_SEPARATE_COMPATIBILITY_DECISION | P1 | Side14 decides/drafts the smallest separately gated B0 provenance/qualification-contract compatibility package before S10-QUAL-REAL-01 | PendulumFlow v3 is THIRD_PARTY_NATIVE_FRAME_ARCHIVE; this WP reports b0_contract_compatibility = EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION and never relabels it canonical PIT. qualification.py / PIT_MARKET_PROBABILITY_V1 unchanged. |
| S10-QUAL-DATA-01-D002 | PendulumFlow best_bid_ask / last_trade_price row-group chunks cannot be digest-verified in isolation | OPEN_SOURCE_LIMITATION | P2 | Archive-published per-row-group digests, or a budget that allows whole-product verification | Manifest SHA-256 covers whole products and the whole file only. Small products are fetched whole and verified (EXACT); targeted chunks and footers are bound to the declared product byte range and retained exactly but recorded FAITHFUL. |
| S10-QUAL-DATA-01-D003 | Resolution-rule text is current-only | OPEN_SOURCE_LIMITATION | P2 | Historically captured rule text (not available from the frozen sources) | The Gamma description is retrieved after resolution; RESOLUTION_RULES is recorded CURRENT_ONLY per market (cohort/hash bound), never HISTORICALLY_EVIDENCED. |
| S10-QUAL-DATA-01-D004 | Checkpoint B structural ineligibility for same-day-created daily-rain markets | PARTIAL_REPLACEMENT_RUN_115_NOT_OPEN_52_B_ROWS | P2 | Successor checkpoint choice (S10-QUAL-REAL-01 or compatibility decision); no tuning in this WP | Implementation-time discovery and the run show daily-rain markets for target date D are created about 11:09Z on D, after local-standard midnight of D, so TARGET_CLIMATE_DAY_START_V1 rows are excluded as CHECKPOINT_B_MARKET_NOT_OPEN_60M. |
| S10-QUAL-DATA-01-D005 | PendulumFlow archive license/terms not verified | OPEN_LEGAL_REVIEW | P2 | Separate licensing review before any redistribution or product use | Data retained only as ignored local research evidence; descriptor license_id UNSPECIFIED_PUBLIC_ARCHIVE with attribution. |
| S10-QUAL-DATA-01-D006 | Daily-rain discovery bounded to the 11:00 and 12:00 UTC hours of each target date | FROZEN_PLAN_LIMITATION | P3 | A future evidence package may widen discovery before seeing performance | Markets created outside those hours are not discovered; discovery-hour failures are reported in the bundle source facts. |
| S10-QUAL-DATA-01-D007 | Gamma response byte accounting counts canonical decoded JSON bytes | OPEN_OPERATIONAL_CONSTRAINT | P3 | A future public-client change exposing raw response bytes (public_client.py is out of scope) | The existing PolymarketPublicClient.get_market returns parsed JSON only; attempts are exact, Gamma bytes are the canonical JSON length of the returned document. |
| S10-QUAL-DATA-01-D008 | Rule parser missed two frozen finality-policy wordings | RESOLVED_BY_SIDE14_CORRECTION_A456D2E_REPLACEMENT_RUN_0_UNSUPPORTED | P1 | Side14 decides whether a separately authorized same-capability parser correction plus re-acquisition (a second corpus run) is warranted | run-01 excluded 450 markets as RULE_SEMANTICS_UNSUPPORTED: 420 use 'as published by 2:00 PM ET ... the last version published before that time governs' (LAST_BEFORE_1400_ET) and 30 use 'the most recent CLI report ... the last version published before 11:59 PM ET ... governs' (LATEST_BEFORE_2359_ET). The frozen code digests and the single-run rule prevent correcting and re-deriving inside this run; the QUAL_DATA_READY corpus (104 rows / 7 dates, all FIRST_PUBLISHED_FINAL) understates the available markets. |
| S10-QUAL-DATA-01-D009 | Truncated HTTP 200 bodies accepted without a Content-Length check | RESOLVED_BY_SIDE14_CORRECTION_A456D2E_HOURS_RECOVERED | P2 | Any future operator run: compare body length to Content-Length and treat a short body as a transport truncation | Two v3 manifests (2026-09-09/12, 2026-09-24/11) were retained truncated, failed validation and were reported as discovery-hour failures. Both dates carry the D008 rule wording, so no ready row is affected; discovered-candidate counts for 2026-09-24 may be understated. |
| S10-QUAL-DATA-01-D010 | Non-target market_resolved rows with non-canonical 32-byte winning_asset_id | RECORDED_SOURCE_FACT | P3 | Future source-contract review of v3 market_resolved rows without a canonical winner token | 905 such rows were skipped fail-closed during full-product decoding; none belonged to a target market (0 LABEL_V3_RESOLUTION_MISSING exclusions). |
| S10-QUAL-DATA-01-D011 | Failed targeted best_bid_ask/footer read still counts the hour as scanned | OPEN_OPERATOR_DEFECT_ZERO_ROW_IMPACT | P2 | Any future operator run: exclude an hour whose targeted read failed from the scanned set | Verified against the sealed replacement bundle: 0 of 212 rows have a failed best_bid_ask chunk or footer read between their selected event and checkpoint (the only failed read inside a row span is a market_resolved product), so no row is affected. Failed-manifest hours are already treated as inadmissible. |
| S10-QUAL-DATA-01-D012 | Frozen 2 GiB budget insufficient for the full frozen corpus once all frozen-policy markets are admitted | OPEN_SIDE14_DECISION | P1 | Side14 decides whether a separately authorized evidence capability (budget, byte-efficiency or narrower frozen plan decided before performance) is warranted | Replacement run exhausted BYTE_BUDGET (2,147,013,454 bytes; 428 HTTP 503 archive responses, 228 retries; checkpoint-B 24 h history scans); 225 LAST_BEFORE_1400_ET markets unevaluated; terminal QUAL_DATA_INSUFFICIENT. No tuning performed. |
andidate or real gate receipt exists. |
