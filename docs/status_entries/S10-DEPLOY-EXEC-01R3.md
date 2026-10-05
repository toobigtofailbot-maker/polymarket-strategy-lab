# S10-DEPLOY-EXEC-01R3 Status Entry

## Identity

- WP ID: S10-DEPLOY-EXEC-01R3
- Title: Adaptive Polygon eth_getLogs Response-Bound Chunking Repair
- Parent: S10-DEPLOY-EXEC-01 (repair envelope; not a new roadmap capability or architecture)
- Triggered by: real Phase-B FU15 canonical smoke -> RESPONSE_TOO_LARGE on
  b815eedb2ca47b2ab89351e90aaa50d03335149e (S10-DEPLOY-EXEC-01 follow-up 15 on the AlphaVPS C8G host)
- Repair class: bounded public read-only RPC response-bound repair
- Package class / size / risk: PUBLIC_RPC_RESPONSE_BOUND_REPAIR / S / 3
- Governance track: RUNTIME; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-deploy-exec-01r3-adaptive-polygon-log-chunking
- Base: b815eedb2ca47b2ab89351e90aaa50d03335149e
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Real-Host Evidence

- Host proof before failure: bootstrap, binding, strict currentness, SIGKILL restart and the isolated
  window PASS (240 samples, p95 250.084 ms, max 250.134 ms)
- Canonical smoke (one invocation): FAILED `RESPONSE_TOO_LARGE` after about 1 s; raw 9, normalized
  110, store_bytes 726660; zero Polygon raw rows; Gamma/CLOB/Data HTTP and WebSocket stored rows
- Mixed window invalid; coexistence `EXECUTION_HOST_INCONCLUSIVE` (`RESEARCH_SMOKE_NOT_PASSED`)
- Capacity conclusion: NOT A C8G CAPACITY FAILURE
- The R2 transport repair worked: the provider answers; the next deterministic failure is the
  certified response-size bound on the 100-block eth_getLogs range

## Implementation Defect

- `_collect_log_chunk` turns an eth_getLogs `RESPONSE_TOO_LARGE` from `_rpc_call` directly into a
  terminal failed receipt; an oversized range is never subdivided.

## Repair

- Deterministic adaptive bisection only for oversized multi-block eth_getLogs ranges:
  `[A, B]` -> `[A, floor((A + B) / 2)]` then `[mid + 1, B]`, left first, recursing only when a child is
  itself oversized; no gap, no overlap, no estimated or time-dependent sizing.
- Single-block oversized: terminal `RESPONSE_TOO_LARGE`; the same range is never re-requested.
- Every other error stays terminal and is never subdivided; no retry of an identical request; no
  provider fallback.
- Every child goes through the same rate-limited rpc closure and shared network budget, with the same
  store, limits, latest block, received_at and seen_log_ids; raw cursors name the actual child range.
- Checkpoint is written only after the whole requested range completes, as before; earlier child
  evidence stays append-only after a later child failure.
- Frozen safety bound: max_response_bytes remains 4 MiB (4,194,304)
- Frozen runtime lookback: 100 blocks unchanged; max block span 2,000 unchanged
- Provider: drpc only / unchanged; RPC methods unchanged; R2 headers and error classification unchanged
- Offline behavioral regressions use an injected transport and a socket guard; no test contacts the
  internet.

## Exact Scope (5 paths)

- docs/status_entries/S10-DEPLOY-EXEC-01R3.md
- docs/wp_specs/S10-DEPLOY-EXEC-01R3/wp_prompt.txt
- docs/wp_specs/S10-DEPLOY-EXEC-01R3/wp_spec.json
- src/data_layer/polymarket/market_truth_onchain.py
- tests/data_layer/polymarket/test_market_truth_onchain.py

## Authority / Non-Authority Posture

- Credentials/account/orders/capital/live: NO / NO / 0 / USD 0 / DISABLED
- Phase B: SUSPENDED pending repair merge and a fresh Phase-B authorization bound to the new merge SHA
- Formal reboot: 0
- VPS mutation during repair: NO (current b815eed release and binding, telemetry/research baseline as
  is, critical probe disabled/inactive, FU11 forensic DB, FU12 archived DB and the FU15 failed
  canonical DB preserved)
- Successor: the S10-DEPLOY-EXEC-01 Phase B on the new merge SHA (separately authorized; it archives
  the FU15 DB before a fresh canonical smoke); S10-LIVE-ORCH-01 remains separately gated
