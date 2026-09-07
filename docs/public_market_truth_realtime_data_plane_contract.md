# Public Market Truth / Realtime Data Plane Contract (WP169)

Package class: PUBLIC_MARKET_TRUTH_REALTIME_DATA_PLANE
Package size class: XL (exact changed-file scope: 35)
Risk level: 3
Capital at risk: USD 0

## Purpose

WP169 delivers one native public market-truth plane under
`src/data_layer/polymarket`. It preserves exact raw bytes before normalization,
normalizes supported Polymarket Market WebSocket events deterministically without
floats, maintains per-asset book readiness with disconnect/regression/hash-conflict
gap handling, persists append-only raw envelopes, normalized observations, sessions,
gaps, and checkpoints transactionally in bounded local SQLite, collects public
unauthenticated Data/Gamma/CLOB GET pages with closed Retry-After handling, decodes
public Polygon V2 OrderFilled logs with confirmation and reorg handling, and promotes
only eligible accepted observations through the existing canonical point-in-time (PIT)
record builder. A manual foreground CLI/runtime with graceful stop and bounded backoff
drives acquisition; there is no import-time network, thread, process, scheduler, or
file side effect.

## Authority and non-authority

- Paper-trading execution: NOT AUTHORIZED.
- Live-trading execution: FORBIDDEN. Public live market observation is not live trading.
- Credentials created/used: 0. Credential-bearing inputs and secret-like RPC URLs fail closed.
- No credentials, authentication, signing, orders, order cancellation, OMS, execution
  gateway, risk engine, strategy, expected-return claims, paper trading, simulated fills,
  Hermes runtime, dashboard, hosted database, message bus, cloud service, background-service
  installation, generic scheduler, or WP170 implementation.
- Canonical PIT authority unchanged: YES. The acquisition SQLite archive has no canonical
  promotion authority; only validated normalized records promoted through the existing PIT
  builder/store become canonical PIT records.
- Direct Nautilus ingestion claimed: NO. WP168 Nautilus replay accepts only its frozen
  WP167 pmxt-v2 external dataset; no direct PIT-to-Nautilus adapter is added by WP169.

## Network authority (closed transport policy)

Public unauthenticated only:

- Polymarket Data API GET: `/trades`, `/activity`, `/positions`, `/holders`.
- Polymarket Gamma GET: `/markets`, `/markets/{id}`.
- Polymarket CLOB GET: `/book`, `/fee-rate`, `/clob-markets/{condition_id}`.
- Polymarket Market WebSocket: `wss://ws-subscriptions-clob.polymarket.com/ws/market`.
- Polygon read-only JSON-RPC (provider enum `drpc` -> `https://polygon.drpc.org`):
  `eth_chainId`, `eth_blockNumber`, `eth_getLogs`, `eth_getBlockByNumber`.

Every response is byte-bounded before JSON parse. HTTP retries only 429/502/503/504 up to
the retry bound; Retry-After must be an ASCII integer within the closed bound or
`RETRY_AFTER_INVALID` is recorded and deterministic exponential backoff applies. No
POST/PUT/PATCH/DELETE product call, authenticated header, arbitrary RPC method, or
credential-like URL is structurally reachable.

## Dependency posture

New direct runtime dependency: `websockets==17.1` (BSD-3-Clause; install-not-vendor). The
exact existing pins are preserved: `pyarrow==25.0.1`, `duckdb==1.5.5`, `polars==1.44.1`,
`nautilus_trader==1.231.0`. Supported Python range: `>=3.12,<3.15`.

## Source modules

- `src/data_layer/polymarket/market_truth.py` — canonical JSON, closed error precedence,
  content/occurrence identities, frozen public records, WebSocket and public-record
  normalizers, recursive no-echo sanitization, and the PIT promotion adapter.
- `src/data_layer/polymarket/market_truth_store.py` — bounded append-only local SQLite
  archive with an append-only checkpoint history hash chain and a derived cache.
- `src/data_layer/polymarket/market_truth_websocket.py` — deterministic decimal-only book
  reconstruction, the queue-owning subscription controller, and the manual foreground runner.
- `src/data_layer/polymarket/market_truth_data_api.py` — GET-only public Data/Gamma/CLOB client.
- `src/data_layer/polymarket/market_truth_onchain.py` — public Polygon V2 OrderFilled decoding.
- `src/data_layer/polymarket/market_truth_runtime.py` — manual bounded runtime orchestration.
- `tools/polymarket/run_public_market_truth.py` — manual foreground CLI (requires `--allow-network`).

## Output sanitization

Public output is closed and sanitized: stable status/error codes, counts, hashes, logical
source identifiers, event timestamps, and public market values only. Exceptions, URLs,
headers, environment values, local absolute paths, raw invalid inputs, and response bodies
are never echoed by result/error surfaces. `RawEnvelope.raw_bytes` and
`PublicPageResult.attempts` are the only authorized raw-evidence boundaries.

## Governance state chain

LOCAL_DRAFT -> DRAFTABILITY_PASS (separate independent exact-hash certificate) ->
AUTHORIZED (WP168G readiness IMPLEMENTATION_READY plus the user's Side 8 conditional
authorization) -> IMPLEMENTED_LOCAL (exactly the certified 35 paths). Merge authority is
never granted; independent live PR review is required.

## Successor boundary

WP170 — Falsification-Grade Experiment Registry & Research Dataset OS is next and separately
gated. WP169 implements no WP170 work. WP171 Interactive Operator Cockpit, WP172 Hermes
Runtime + Alpha Factory, WP173 Executable Edge / Microstructure, WP174 Portfolio /
Accounting / Reconciliation / Hard Risk, WP175 Serious Paper OMS + Operations, WP176 Auth /
Signing / Execution Gateway, WP177 Restricted Live Canary, and WP178 Mature Controlled Live
remain separately gated and unimplemented. Full UMA proposal, dispute, voting, finality
indexing, and semantic adjudication are deferred to the WP172 boundary (or a separately
certified prerequisite).

## Evidence mode

Evidence mode: BLOCKED_NOT_READY until implementation evidence is complete; target
PRIVATE_REPO_MANUAL_VERIFIED at the final hosted-CI head. Merge authorized: NO.
