# S10-DEPLOY-EXEC-01R2 Status Entry

## Identity

- WP ID: S10-DEPLOY-EXEC-01R2
- Title: Polygon RPC Transport Compatibility + Failure-Classification Repair
- Parent: S10-DEPLOY-EXEC-01 (repair envelope; not a new roadmap capability or architecture)
- Triggered by: real Phase-B Polygon RPC failure on cb82114ce13a300b728df049b1db9a24639fdbaf
  (S10-DEPLOY-EXEC-01 follow-ups 11 / 12 / 12A on the AlphaVPS C8G host)
- Repair class: bounded public RPC transport compatibility/failure-classification repair
- Package class / size / risk: PUBLIC_RPC_TRANSPORT_REPAIR / S / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-deploy-exec-01r2-polygon-rpc-transport-repair
- Frozen base: cb82114ce13a300b728df049b1db9a24639fdbaf
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Real-Host Evidence

- Direct dRPC `eth_chainId` from the same host (one request, curl): HTTP 200 / `0x89`, 0.109 s
- Repository canonical smoke (urllib): repeated immediate `NETWORK_TIMEOUT` (two runs about 22 minutes
  apart, each about 1.1 s), zero Polygon raw rows
- Other public HTTP (Gamma/CLOB/Data) and WebSocket surfaces: healthy in both runs
- Mixed window invalid; coexistence `EXECUTION_HOST_INCONCLUSIVE` (`RESEARCH_SMOKE_NOT_PASSED`);
  not a C8G capacity failure

## Implementation Defect

- The Polygon default transport (`_default_rpc_transport`) lacks the fixed WP169 User-Agent and
  collapses `HTTPError` into `NETWORK_TIMEOUT`, so an HTTP-layer rejection is indistinguishable from a
  genuine transport timeout.

## Repair

- Fixed headers exactly `Content-Type: application/json`, `Accept: application/json`,
  `User-Agent: wp169-public-market-truth/1.0`; no caller, environment or credential headers.
- `HTTPError` is returned as `(status, headers, body)`; the existing `_rpc_call` non-2xx rule yields
  `RESPONSE_INVALID`. Genuine DNS/connect/TLS/timeout failures remain `NETWORK_TIMEOUT`.
- No retry, redirect or fallback logic added; no new dependency; no new error code or receipt field.
- Provider set: UNCHANGED — drpc only
- RPC methods: UNCHANGED (eth_chainId, eth_blockNumber, eth_getLogs, eth_getBlockByNumber)
- Offline behavioral regressions exercise the real default transport with `urlopen` intercepted and
  a socket guard; no test contacts the internet.

## Exact Scope (5 paths)

- docs/status_entries/S10-DEPLOY-EXEC-01R2.md
- docs/wp_specs/S10-DEPLOY-EXEC-01R2/wp_prompt.txt
- docs/wp_specs/S10-DEPLOY-EXEC-01R2/wp_spec.json
- src/data_layer/polymarket/market_truth_onchain.py
- tests/data_layer/polymarket/test_market_truth_onchain.py

## Authority / Non-Authority Posture

- Credentials: NO
- Authenticated account access: NO
- Orders: 0
- Capital: USD 0
- Live: DISABLED
- Phase B: SUSPENDED pending repair merge and a fresh Phase-B authorization bound to the new merge SHA
- Formal reboot consumed: NO
- VPS mutation during repair: NO (current cb82114 release and binding, telemetry/research baseline
  as is, critical probe disabled/inactive, FU11 forensic and FU12 failed smoke DBs preserved)
- Successor: the S10-DEPLOY-EXEC-01 Phase B on the new merge SHA (separately authorized);
  S10-LIVE-ORCH-01 remains separately gated
