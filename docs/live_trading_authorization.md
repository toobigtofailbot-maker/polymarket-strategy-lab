# Live Trading Authorization

LIVE TRADING STATUS: DISABLED

WP175 implementation status: CODE-COMPLETE_PENDING_EXACT_HEAD_GATE_C_ACTIVATION.
The protected canary code is present only for the separately gated manual
foreground path. Gate-C activation is PENDING, no real economic CREATE has
been performed, and capital at risk is USD 0. `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`
remains open because no exact manually attested WP172/WP173 strategy
qualification is available. This document does not grant live authority.

Merge does not grant live authority. The inert, fully disabled Gate-C
implementation is mergeable as dormant capability with
`FINAL_MERGE_SMOKE_CREATE_ATTEMPTS=0` — no real economic CREATE, secret, capital,
or strategy qualification is a merge prerequisite — while LIVE TRADING STATUS
stays DISABLED and startup stays A0_DISABLED. The single real CREATE
(`FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS=1`) is reserved for the separately
authorized post-merge first live activation canary; `LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`
remains a hard activation blocker only, not a dormant-merge blocker.

S10-GATE-C-EXPLORE-01 (V2.1 exploratory Gate C policy permit core) is separate from
WP175. It is a credential-free deterministic eligibility decision: it issues no legacy WP175
Gate-C live permit, arms no session, enters no A3 state, reads no account or geoblock
state, loads no credential and signs, submits or cancels no order. An exploratory permit is
necessary-but-not-sufficient future evidence for one exact intent, not live activation;
later protected runtime must still revalidate account, access, reconciliation and runtime
identity before any economic mutation. WP175 remains the historical/manual real
restricted-live canary path (Gate-B credential/session, A3 and real CREATE transport),
unchanged. Capital/orders remain USD 0 / 0.

S10-DEPLOY-EXEC-01 (execution-host runtime substrate) grants no live authority. It adds a
sanitized host/release binding, currentness evidence, a non-economic critical-probe service
(installed but inactive) and closed coexistence/terminal host-evidence semantics. It loads no
trading credential, instantiates no authenticated client, reads no account state, issues or
consumes no GateCLivePermit, arms no GateCSession, enters no A3 state and signs, submits or
cancels no order. Even a future real-host EXECUTION_HOST_PROVEN_C8G outcome is necessary but not
sufficient for live execution: S10-LIVE-ORCH-01 must still revalidate the exact exploratory
permit, account, access and reconciliation under separate protected authority. Capital/orders
remain USD 0 / 0.

No live trading code exists in WP1. No strategy is live-authorized. No wallet or API credentials are configured. No external repo code is authorized for live execution.

Live mode requires a future WP, explicit human approval, active risk gateway, kill-switch tests, dashboard visibility, and an updated authorization table.

| Strategy | Live authorized? | Max capital | Approved by | Approval date | Conditions |
|---|---|---|---|---|---|
| Market scanner | No | N/A | N/A | N/A | N/A |
| Wallet intelligence | No | N/A | N/A | N/A | N/A |
| Smart-wallet scoring | No | N/A | N/A | N/A | N/A |
| Copy-trading module | No | N/A | N/A | N/A | N/A |
| YES/NO arbitrage scanner | No | N/A | N/A | N/A | N/A |
| Gabagool / hedged arbitrage scanner | No | N/A | N/A | N/A | N/A |
| Related-market scanner | No | N/A | N/A | N/A | N/A |
| Polymarket-Kalshi cross-market arbitrage scanner | No | N/A | N/A | N/A | N/A |
| Market-making module | No | N/A | N/A | N/A | N/A |
| Paper-trading engine | No | N/A | N/A | N/A | N/A |
| Risk engine | No | N/A | N/A | N/A | N/A |
| Execution gateway | No | N/A | N/A | N/A | N/A |
| AI/Hermes monitoring/reporting assistant | No | N/A | N/A | N/A | N/A |
| WP175 restricted live canary | Pending separate exact-head Gate-C decision | 0 during implementation | N/A | 2026-09-16 package authority only | One strategy/market, LIMIT-only, one attempt; qualification prerequisite unavailable |
