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
| WP3-D001 | Security tool unavailable: gitleaks | DEFERRED | P1 | Unavailable during WP2. | External dependency runtime integration, vendoring, live execution. | Install and verify gitleaks or document an approved equivalent, then run it on the repo plus audited dependency candidates before runtime use. |
| WP3-D002 | Security tool unavailable: semgrep | DEFERRED | P1 | Unavailable during WP2. | External dependency runtime integration, copied code, live execution. | Install and verify semgrep or an approved equivalent, then run relevant static checks before runtime use. |
| WP3-D003 | Node dependency audit unavailable: npm / npm audit | DEFERRED | P1 | Unavailable during WP2. | TypeScript client integration or dashboard/runtime dependency installation. | Make npm available and document audit results, or document an approved alternative. |
| WP3-D004 | Python dependency audit unavailable: pip-audit | DEFERRED | P1 | Unavailable during WP2. | Python client integration or runtime Python dependency installation. | Make pip-audit available and document audit results, or document an approved alternative. |
| WP3-D005 | Rust dependency audit unavailable: cargo audit | DEFERRED | P2 unless Rust is selected, then P1 | Unavailable during WP2. | Any Rust runtime component. | Make cargo audit available and document audit results, or explicitly exclude Rust from runtime scope. |
| WP3-D006 | Relayer clients license unresolved | DEFERRED | P1 if relayer integration is proposed | WP2 found no license file in the shallow clone for builder-relayer clients. | Any relayer runtime dependency. | Clarify the license and approve it in repo truth. |
| WP3-D007 | Official CLOB client dependency security review pending | DEFERRED | P1 | WP2 marked TypeScript and Python V2 clients as core dependency candidates, not approved runtime dependencies. | API integration. | Complete version pinning, dependency audit, adapter boundary review, and security review in a later work package. |
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
