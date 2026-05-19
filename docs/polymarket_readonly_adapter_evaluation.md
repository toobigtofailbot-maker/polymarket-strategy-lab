# Polymarket Read-Only Adapter Evaluation

## Purpose

This document records the WP8 decision to implement a strictly read-only public data adapter for Polymarket market metadata and order-book style market data. It covers the scope, sources reviewed, endpoint candidates, client options considered, and the rationale for using a Python standard-library-only skeleton before any official SDK or authenticated client.

## Scope

WP8 is strictly limited to:

- Public read-only GET requests to Polymarket endpoints.
- Market metadata and order-book snapshot data.
- Offline tests using mocks and fixtures.
- An optional manual smoke test gated by `--allow-network`.

WP8 does not:

- Add trading logic.
- Add order placement, cancellation, or signing.
- Add authenticated clients or API credentials.
- Add wallet or private-key handling.
- Add live-trading paths.
- Add Kalshi integration.
- Add runtime Python dependency packages.
- Install or vendored external repo code.

## Sources Reviewed

### Repo audit artifacts

| File | Relevance |
|---|---|
| `audits/source_repos/polymarket_clob-client-v2.md` | Official TypeScript V2 CLOB client; candidate for future authenticated use. |
| `audits/source_repos/polymarket_py-clob-client-v2.md` | Official Python V2 CLOB client; candidate for future authenticated use. |
| `audits/source_repos/polymarket_poly-market-maker.md` | Community market-maker; not a dependency candidate. |
| `docs/architecture_skeleton.md` | Defines data layer scope and authority rules. |
| `docs/runtime_boundaries.md` | Defines what adapters may not do. |
| `docs/data_semantics.md` | Defines canonical terms: market, token, order book snapshot, etc. |
| `docs/deferred_items_log.md` | WP3-D007 tracks official CLOB client dependency review as pending. |

### Public endpoint knowledge basis

Polymarket operates two primary public data APIs:

1. **Gamma API** — market metadata, event listings, market conditions. The known public base URL pattern is `https://gamma-api.polymarket.com`. Documented endpoints include `/markets` and `/markets/{condition_id}`.

2. **CLOB REST API** — order-book data (bids, asks, midpoint). The known public base URL pattern is `https://clob.polymarket.com`. Documented public endpoints include `/book` (order-book snapshot by token_id) and `/health`.

**Uncertainty caveat:** WP8 does not confirm production endpoint contract stability or current rate-limit policies. The adapter is built with a configurable base URL and offline tests. No claim of production readiness is made. Production endpoint confirmation and rate-limit policy are deferred items (see WP8-D001 and WP8-D002).

## Public Endpoints Considered

| Endpoint | Base | Method | Auth required | WP8 status |
|---|---|---|---|---|
| `GET /markets` | Gamma API | GET | No | Adapter candidate — marked as unverified contract |
| `GET /markets/{condition_id}` | Gamma API | GET | No | Adapter candidate — marked as unverified contract |
| `GET /book?token_id=...` | CLOB API | GET | No | Adapter candidate — marked as unverified contract |
| `GET /health` | CLOB API | GET | No | Adapter candidate — marked as unverified contract |
| Any POST/PUT/PATCH/DELETE | Any | Any | Any | Excluded — not read-only |
| Authenticated CLOB endpoints | CLOB API | Any | Yes | Excluded — not read-only |

## Official Client Options Considered

### Python V2 CLOB client (`polymarket/py-clob-client-v2`)

- MIT license.
- Reviewed in `audits/source_repos/polymarket_py-clob-client-v2.md`.
- Has live trading logic, signing, private key handling, and order construction.
- Not approved for runtime use by WP2 or WP8.
- Adds runtime Python dependencies that have not been security-audited against this project.
- Decision: **Not used in WP8. Deferred to a future WP after dependency pinning, pip-audit, and boundary review.**

### TypeScript V2 CLOB client (`polymarket/clob-client-v2`)

- MIT license.
- Reviewed in `audits/source_repos/polymarket_clob-client-v2.md`.
- TypeScript; requires Node runtime.
- Not applicable to this Python-only skeleton.
- Decision: **Not used in WP8. Deferred.**

### Python standard library (`urllib`, `http.client`, `json`)

- No additional dependencies.
- Supports GET requests and JSON parsing.
- Zero supply-chain risk from this adapter.
- Suitable for a read-only skeleton used offline and in a limited manual smoke test.
- Decision: **Used in WP8.**

## Why WP8 Uses A Read-Only Public Adapter Skeleton First

WP8 is the first controlled Polymarket integration step. A read-only skeleton:

- Establishes the adapter interface and data model before any authenticated or trading-capable code is introduced.
- Lets offline tests verify boundary enforcement (no POST methods, no credentials, no signing) without live network risk.
- Provides a concrete foundation for evaluating whether the official Python client is needed or whether this skeleton suffices for market scanning.
- Keeps the dependency surface at zero while confirming the data model.

## Why No Authenticated Client Is Added Yet

- Authenticated clients require private keys or API credentials.
- WP3-D011 disables live trading and defers all credential handling.
- WP3-D007 defers official client dependency security review.
- pip-audit and semgrep must be rerun on any new runtime dependency before integration.
- Adding an authenticated client now would expand risk surface before risk controls, execution gateway, and paper-trading engine are built.

## Why No SDK Dependency Is Added Yet

Using Python standard library only:

- Avoids supply-chain risk before pip-audit can run on proposed packages.
- Avoids installing a package that bundles trading, signing, and order-construction code into the data layer.
- Defers the decision of which client SDK to adopt until WP9 or later, when the endpoint contract is confirmed and the dependency decision is formally documented.

If the official Python client is eventually needed, the skeleton makes that transition explicit — the adapter class simply delegates to the SDK instead of `urllib`.

## Allowed Data Types

- Market metadata: market id, condition id, question, status, outcome labels, timestamps.
- Order-book snapshots: token id, bids (price/size pairs), asks (price/size pairs), timestamp.
- Health responses: service status.
- Request provenance: URL, timestamp, adapter version, response latency indication.

## Disallowed Behavior

The WP8 adapter must never:

- Send POST, PUT, PATCH, or DELETE requests.
- Read or use credentials, private keys, wallet keys, passphrases, mnemonics, or API tokens.
- Return or store signing material.
- Call any method named or behaving like: `place_order`, `create_order`, `post_order`, `submit_order`, `cancel_order`, `sign_order`, `execute_trade`, `trade`, `buy`, `sell`.
- Start background loops or scheduled polling.
- Write to persistent storage autonomously.

## Future Transition Path

1. **WP9 option A — Snapshot persistence**: persist market snapshots to local files for strategy research; adapter remains read-only skeleton.
2. **WP9 option B — Official client dependency decision**: pin `py-clob-client-v2` version, run pip-audit and semgrep, document results, then integrate behind adapter boundary.
3. **Later**: add CLOB authenticated client behind the execution gateway only, after paper-trading engine and risk controls are in place.
4. **Live execution**: gated by `docs/live_trading_authorization.md` and explicit human approval.

The adapter boundary means strategies never import venue clients directly. All data flows through `src/data_layer/polymarket/`.

## Security And Terms Of Service Notes

- Public Gamma and CLOB endpoints are documented for developer use. No terms confirmation is included here; the project operator must confirm ToS compliance before running automated or high-frequency requests.
- Rate-limit policy is not confirmed; the smoke test uses a short timeout and a small limit to minimize footprint.
- No credentials are stored, transmitted, or generated.
- The `user_agent` parameter is configurable to identify the client honestly.

## Manual Smoke-Test Instructions

The optional smoke test is at `tools/polymarket/readonly_smoke_test.py`. It requires explicit `--allow-network` to make any network call. Without the flag it exits immediately.

```
python tools/polymarket/readonly_smoke_test.py --help
python tools/polymarket/readonly_smoke_test.py --allow-network --markets-limit 3
```

The smoke test is not run by `pytest`. It is safe to skip in CI.

## Next WP Recommendation

**WP9 — Polymarket Market Metadata Snapshot Persistence** (if endpoint contract is confirmed)
or
**WP9 — Official Python Client Dependency Decision** (if the stdlib adapter proves insufficient for market scanning)

The recommended next step depends on whether the smoke test or manual review confirms the Gamma API endpoint contract. If endpoints respond as expected, WP9 should add minimal snapshot persistence (local JSON files) under `src/data_layer/polymarket/`. If the endpoint contract is uncertain, WP9 should formally evaluate and pin the official Python client after a full pip-audit and semgrep run.
