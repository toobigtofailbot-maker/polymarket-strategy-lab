# Hermes live preflight bridge contract (S10-HERMES-LIVE-BRIDGE-01)

`src/research_runtime/live_preflight_bridge.py` exposes one function, `run_live_preflight_bridge`. It composes unchanged native interfaces in the foreground and returns one sanitized receipt with status `PASS`, `BLOCKED` or `ABSTAIN`. It never raises, never trades and has no authority of its own.

## Chain

1. **Witness.** The caller passes an already produced, in-memory `OAuthPlanResult`. `is_witnessed_result` must hold, so a replayed, mock, forged or edited result fails with `REAL_ORIGIN_UNVERIFIED` before any store is read. The bridge never starts an OAuth or provider call.
2. **Choice and strategy.** `autonomous_feedback.admit_oauth_choice` runs the AUTO-01 admission. It binds the raw choice bytes, the exact ordered menu, the clocks, the latest canonical `HermesStrategyAssessment`, its context and the active policy. If the assessment is missing, stale or forged, the result is `STRATEGY_ASSESSMENT_UNAVAILABLE` plus the native code.
3. **Abstention.** `NO_TRADE`, `PAUSE` and `REASSESS` return `ABSTAIN`. No venue is read, no permit is built and preflight is not called.
4. **Native strategy.** The bridge reads the verified Hermes store and requires the latest assessment's run record to exist and match. The heads must be the ones AUTO-01 bound.
5. **Fresh native permit.** The bridge reads one fresh public venue and rebuilds the `ExecutionIntent` from the choice's order shape. Native feasibility, `evaluate_exploratory_gate_c` and `build_exploratory_gate_c_permit` then run on that venue. The AUTO-01 preview permit is never used. BUY only.
6. **Preflight.** Only `LiveOrchestrator.preflight(permit, intent)` is called. The secret-provider, client and pause seams are replaced with functions that refuse, and canary and reconcile are never called.

The choice window is `min(choice expiry, deadline, assessment decision time + max Hermes age)`. It is checked before the fresh venue read and again before preflight.

## Labels and limits

- `choice_proof_level` is always `SYNTHETIC_ONLY`, the frozen Stage B schema value. It is a label, not live venue or market evidence. The witness proves only that the choice bytes came from a real OAuth call (`PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC`).
- `strategy_assessment: VALIDATED_CANONICAL_ONLY` means the store replay and lineage are valid. The run's provider and model labels are not proof of authenticated inference (`strategy_origin_proof`). The bridge never creates a Strategy Manager run, receipt, cost or source record.
- Injecting any of the four read-only seams (clock, host currentness, geoblock, venue fetcher) makes the receipt `evidence_class: OFFLINE_TEST_ONLY` with `claim: PROTOCOL_ONLY` and `choice_origin: OFFLINE_TEST_ONLY`. Only the native defaults give `NATIVE_READ_ONLY_SEAMS`.
- `PASS` means native read-only preflight passed. It does not cover account, wallet, ledger-balance or capital readiness (`account_readiness: NOT_EVALUATED`).
- `calls` counts provider, OAuth dispatch, venue fetch, permit, preflight, canary, reconcile, private session and order. Everything except venue fetch, permit and preflight is always 0.

## Non-authority

The bridge has no OAuth, credential, account, signing, order, capital, scheduler or risk-limit authority. The LIVE-ORCH capital envelope and `docs/live_trading_authorization.md` (DISABLED) are unchanged. A first live canary is the separately authorized S10-LIVE-CANARY-01.
