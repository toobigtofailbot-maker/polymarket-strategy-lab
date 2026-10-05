# Live Orchestration Contract (S10-LIVE-ORCH-01)

Restricted Live Orchestration + First-Live Canary Core. Governance track PROTECTED, risk 4,
exact 27-path scope, independent certificate. Frozen base
`3f4d9ed91c0e96b9fc19389ac59e01f079caa3fe` (PR #218 merged). Implementation:
`src/execution_gateway/live_orch.py` (foreground orchestrator) over the existing Gate-B
(`gate_b.py`), Gate-C (`gate_c.py`) and gateway/store persistence (`gateway.py`, `store.py`).

`LIVE TRADING STATUS: DISABLED`. This package merges a dormant protected capability only.
Implementation and CI performed zero real product network calls, zero real credentials, zero
authenticated account access, zero real economic CREATE/CANCEL and USD 0 capital. The first real
canary requires a separate exact-merge Karl authorization (successor S10-LIVE-CANARY-01).

## 1. Authority chain

```
exact current ExploratoryGateCPermit + exact ExecutionIntent
+ strict execution-host currentness / NTP PASS + fresh geoblock PASS
+ exact authenticated signer / Deposit Wallet identity
+ fresh complete bounded account truth + fresh compatible public venue snapshot and feasibility
+ hard capital envelope + healthy canonical LIVE-ORCH ledger
    -> durable LIVE_ORCH_ADMISSION -> durable CREATE_STARTED -> at most one economic transmit
    -> authoritative reconciliation -> terminal / settlement-pending / blocked -> no-new-exposure
```

The permit is consumed read-only and is never regenerated, widened or substituted. Its
no-credential / no-order / no-live flags stay truthful: LIVE-ORCH is the separately protected
successor that performs the mandatory runtime revalidations and only then issues process-local,
one-use mutation authority (`GateCLivePermit`) inside the Gate-C LIVE-ORCH boundary.
`GateCStrategyQualification` and paper `PreparedLimitOrder` are not required on this path.

## 2. Frozen capital envelope

| Constant | Value |
|---|---|
| `AUTHORIZED_ACCOUNT_CAPITAL_USD` | 100 |
| `TYPICAL_INITIAL_ORDER_USD` | 3-5 (operator target only) |
| `SINGLE_ORDER_WORST_CASE_MAX_USD` | 5 |
| `MAX_TOTAL_EARLY_COMMITMENT_USD` | 30 |
| `MIN_FREE_COLLATERAL_RESERVE_USD` | 70 |
| `AUTO_SCALING` | FALSE |
| `MAX_OBSERVED_REALIZED_PNL_LOSS_USD` | 5 |
| `MAX_OBSERVED_POSITION_PNL_DRAWDOWN_USD` | 7.5 |
| `MAX_OBSERVED_CUMULATIVE_CANARY_LOSS_USD` | 10 |

`LiveOrchCapitalEnvelope.validate()` rejects any widened value (`CAPITAL_ENVELOPE_INVALID`). No
account profit, strategy/Hermes state, venue response, configuration or environment value can
increase a limit.

The first-live economic CREATE side is BUY only. A SELL permit returns
`SIDE_UNSUPPORTED_FIRST_CANARY` immediately after strict permit validation and before any
authentication, durable admission, signing or transmit. Exposure-reducing cancellation remains
allowed.

## 3. Permit / intent revalidation

`verify_permit_authority` requires: exact-type permit validation; BUY; `exact_intent_only`;
`issued_at_ns <= now < valid_until_ns` (`PERMIT_EXPIRED`); the verified STRAT-LIFE store head,
active policy id and EXPLORATORY_LIVE allocation id equal to the permit and the allocation active
now; the latest Hermes assessment for the StrategyVersion equal to the permit-bound assessment
(`PERMIT_NOT_CURRENT`); `validate_execution_intent(intent, strategy_version=...)` (execution-rule
lineage); every intent field equal to the permit and the exact authorized notional
(`PERMIT_INTENT_MISMATCH`). A permit already present in the ledger returns
`PERMIT_ALREADY_CONSUMED`.

## 4. Host, access and identity

Strict execution-host currentness is required before protected authentication and again
immediately before CREATE admission: the read-only `runtime_baseline.py
execution-host-currentness --strict` document must be `polymarket-execution-host-currentness@1.0.0`
`EXECUTION_HOST_CURRENT` in strict mode for the exact expected release (bound and active), NTP
synchronized, firewall SSH-only and persistent state present (`HOST_NOT_CURRENT`). No fixed sleep
substitutes for currentness PASS. A fresh host-side official geoblock read must prove
`blocked=false`; only the sanitized proof id and observed time are persisted, never IP, country or
region.

Credentials: interactive no-echo owner key (`InteractiveGateBSecretProvider`, TTY only), exact
public signer plus expected Deposit Wallet, production / chain 137, ephemeral secret only; no
argv/file/env/pipe secret; no persisted API credential, private key or signature. Session Keys and
Builder credentials are out of scope.

## 5. Account completeness

REST authenticated reads through Gate-B (`GateBSession.live_orch_account_truth`) are the recovery
truth: collateral, allowance, open orders, account trades (IDs and settlement status) and
positions, each bounded to 100 items; more fails `ACCOUNT_HISTORY_LIMIT_EXCEEDED` and forbids new
exposure. Before new exposure: exact wallet identity, no unknown open order
(`ACCOUNT_UNKNOWN_OPEN_ORDER`) or position (`ACCOUNT_POSITION_UNKNOWN`), no unresolved prior
mutation, a healthy canonical ledger and no close-only mode. The user WebSocket is not recovery
authority. Arbitrary busy-account history migration is not implemented.

## 6. Capital-commitment accounting

The $30 ceiling is capital commitment, never mark-to-market:

```
TOTAL_EARLY_CAPITAL_COMMITTED =
    unresolved known BUY position entry commitment + open BUY unfilled remainder commitment
  + nonterminal matched-trade commitment + ambiguous CREATE reserve + fee commitment not yet reflected
```

Identity-based dedupe: per token, confirmed plus nonterminal matched principal (from the episode's
order-associated trades) and the reported position entry commitment
`max(total_cost_usdc, entry_cost_usdc + entry_fees_usdc)` describe the same shares, so the larger is
counted once. Open BUY remainder is `open_remainder_shares x price_limit`. Every unresolved episode
(ADMITTED, CREATE_STARTED, CREATE_AMBIGUOUS, CANCEL_STARTED, RECONCILIATION_BLOCKED) reserves its full
`worst_case_commitment_usd`. Partitions never exceed the original principal
(`ACCOUNT_COMMITMENT_INCONSISTENT` blocks). `current_value` is never read, so a mark-to-market
decline never frees budget. Unknown position entry commitment fails closed.

## 7. Hard pre-CREATE risk checks

`check_admission_risk` requires independently: `proposed_worst_case_commitment = principal +
worst_case_fee_reserve <= 5`; `current_total_commitment + proposed <= 30`;
`projected_free_collateral = collateral - undebited commitment - proposed >= 70`; fixed human
capital basis `collateral + debited commitment <= 100` (`ACCOUNT_CAPITAL_BASIS_EXCEEDED`; profit
never widens a limit); observed-PnL guards; allowance for the standard exchange `>= proposed`
(`ALLOWANCE_INSUFFICIENT`, no auto-approval); and no blocking account/reconciliation code. Unknown
input fails closed.

## 8. Truthful observed-PnL guards

No UTC-day realized-loss ledger or account-equity high-water drawdown is claimed. Source fields are
the authenticated position records:

- observed realized-PnL loss = sum over positions of `max(-realized_pnl, 0)` (guard <= 5);
- observed position-PnL drawdown = sum over positions of `max(-total_pnl, 0)` (guard <= 7.5);
- observed cumulative canary economic loss = `max(observed realized loss, observed position
  drawdown)` (guard <= 10).

Any guard above its limit returns `OBSERVED_PNL_GUARD_EXCEEDED`; an unparseable input fails
`ACCOUNT_TRUTH_INVALID`. True daily / high-water accounting is deferred.

## 9. Fresh venue revalidation / drift contract

Immediately before admission LIVE-ORCH acquires a NEW public snapshot through
`fetch_public_venue_snapshot(*, gamma_market_id, condition_id, token_id, opener=None,
clock_ns=None)` and evaluates the exact intent. Snapshot / assessment IDs, books, depth, best
prices, spread and fill/fee/slippage metrics may change; fresh IDs are persisted in the admission
and never compared to the historical permit IDs. These must remain compatible or reject before
admission: exact gamma_market_id / condition_id / token_id (`VENUE_IDENTITY_DRIFT`; the three IDs
stay distinct and are never substituted); BUY side and the exact style / order type /
requested_shares / price_limit (bound by the intent); active, not closed, accepting orders, order
book enabled (`MARKET_NOT_ELIGIBLE`); `neg_risk` false (`NEG_RISK_UNSUPPORTED`); `seconds_delay ==
0` (`SECONDS_DELAY_UNSUPPORTED`); tick compatible (`TICK_INCOMPATIBLE`); both minimum-order
constraints independently re-checked (`MINIMUM_ORDER_UNKNOWN` / `MINIMUM_ORDER_NOT_MET`); fee
configuration known (`FEE_CONFIGURATION_UNKNOWN`); fresh assessment FEASIBLE or LIMITED
(`VENUE_NOT_FEASIBLE`); and every account/risk check above.

## 10. Fees

Standard binary fee-enabled markets are allowed. Pretrade reserve: fee disabled -> 0; passive maker
with a known taker-only schedule -> 0; aggressive BUY -> the fresh EXEC-FEAS conservative
five-decimal upper bound, never below the same schedule applied to the full requested shares at the
worst price the permit price limit allows; unknown / unsupported -> reject. No exact per-trade fee
field is invented. After settlement an actual fee is recorded only when attributable from
dedicated-account pre/post collateral, the confirmed principal and the absence of concurrent
mutation (`0 <= delta <= reserve`); otherwise `FEE_RECONCILIATION_AMBIGUOUS` retains the reserve and
blocks new exposure.

## 11. BUY-only order construction (pinned polymarket-client 0.10.0)

PASSIVE_MAKER BUY: GTC/GTD only, `create_limit_order` with the exact token, price_limit,
requested_shares, `post_only=true` and the exact GTD expiration. AGGRESSIVE_TAKER BUY: FOK/FAK only,
`create_market_order` with `amount = requested_shares x price_limit`, `max_price = price_limit`,
`max_spend = proposed_worst_case_commitment` and the exact order type. Both are local signing only
through the private Gate-B handle; `place_limit_order` / `place_market_order` are never used and
missing allowance is never auto-approved.

After construction and before admission `inspect_live_orch_signed_buy` requires the exact token,
BUY, order type, expiration, post-only flag, signature type 3, `maker == signer == Deposit Wallet`
and a zero builder; encoded price never above price_limit; encoded principal never above the
permit principal; encoded taker shares never above requested_shares; FOK and passive orders target
exactly requested_shares. Any widening or rounding-sensitive drift fails
`ORDER_ENCODING_UNSUPPORTED`. On pinned 0.10.0 this is an expected outcome for a
rounding-sensitive aggressive BUY (e.g. 7.33 shares x 0.57) and is not permission to upgrade the SDK
or loosen the permit.

## 12. Durable admission and CREATE idempotency

`LIVE_ORCH_ADMITTED` persists, before `LIVE_ORCH_CREATE_STARTED`: exploratory_permit_id,
execution_intent_id, fresh venue_snapshot_id and execution_feasibility_assessment_id, release /
host-currentness identity, geoblock proof id and observed time, public signer and wallet, account
truth id, current committed capital, proposed principal, worst-case fee reserve, proposed
worst-case commitment, projected free collateral, observed-PnL guard values, the exact
market/condition/token/side/style/type and decision ADMITTED. Sequence: durable ADMISSION ->
durable CREATE_STARTED -> one economic transmit maximum. Admission persistence failure means zero
transmit.

One permit -> at most one CREATE_STARTED and one `post_order` transmit. CREATE_STARTED consumes the
permit's economic use regardless of outcome. There is no automatic CREATE retry for timeout, 425,
429, 5xx, restart or transport ambiguity. Classification: recognized accepted (`live`/`matched`)
with a stable order id -> DEFINITIVE_ACCEPTED; recognized venue rejection codes proving
non-acceptance -> DEFINITIVE_REJECTED; everything else, including the venue code `unknown`, a
`delayed` status or a transport error -> AMBIGUOUS, which reserves the full worst-case commitment
and blocks new exposure until authoritative reconciliation converges. An unbound ambiguous CREATE
converges only on positive authoritative evidence: exactly one unattributable order/trade on the
episode token is bound and reconciled; more than one candidate is RECONCILIATION_BLOCKED. Absence
alone never releases an unbound ambiguous CREATE: no elapsed time and no empty REST snapshot
converts it to TERMINAL_NO_POSITION, so it keeps the full worst-case reserve and forbids any new
CREATE.

## 13. Passive observation, settlement and cancel recovery

An accepted resting passive order is observed in the foreground for at most 60 seconds with
REST-authoritative polling every 1 second (bounded, never a background loop), with no reprice,
cancel-replace, style change or second CREATE; at the deadline the remainder is cancelled and
reconciled. A normal or interrupted operator exit never intentionally leaves a known resting order.

Trade settlement: MATCHED, MATCHED_NOT_BROADCASTED, MINED and RETRYING are nonterminal committed;
CONFIRMED is terminal success; FAILED is terminal failure and never an active fill. Cancellation
removes only the remaining live quantity; matched fills remain. No new CREATE while economically
relevant settlement is nonterminal. Automatic redemption is out of scope.

`LIVE_ORCH_CANCEL_STARTED` is persisted before each cancel transmit and the same cancel attempt
identity is never resent. On ambiguity: authoritative reconcile; if the order is no longer live,
reconcile fills/residual; if it is definitively still live, a NEW attempt identity may be sent. At
most three cancel/reconcile rounds per foreground invocation; still unresolved ->
RECONCILIATION_BLOCKED (`CANCEL_UNCONVERGED`). A later foreground reconcile may continue
risk-reducing recovery with fresh identities. No CREATE while blocked.

## 14. Multi-episode restart-safe ledger

LIVE-ORCH extends the existing tamper-evident gateway journal (no second subsystem) with one
sanitized `live_orch_checkpoint` and six events (`LIVE_ORCH_ADMITTED`, `_CREATE_STARTED`,
`_CREATE_OUTCOME`, `_CANCEL_STARTED`, `_CANCEL_OUTCOME`, `_RECONCILED`). The canonical ledger is one
store per persistent state root and public wallet. Each episode binds permit, intent, strategy
version, execution rule, market/condition/token, BUY, order style/type, authorized economics,
release identity and public wallet identity; one permit can never appear in a second episode.
Closed states: ADMISSION_PENDING (in-memory only), ADMITTED, CREATE_STARTED, CREATE_REJECTED,
CREATE_ACCEPTED, CREATE_AMBIGUOUS, RESTING, CANCEL_STARTED, RECONCILING, SETTLEMENT_PENDING,
TERMINAL_NO_POSITION, TERMINAL_KNOWN_POSITION, RECONCILIATION_BLOCKED. Every transition is
replay-validated against a closed table; binding and admission are immutable; CONFIRMED/FAILED
trade evidence and a reconciled fee are final; a durable CREATE_STARTED without a durable outcome
may only become CREATE_AMBIGUOUS; an ADMITTED episode that never started provably transmitted
nothing and closes as TERMINAL_NO_POSITION.

Restart sets `restart_reconciliation_required` and never restores mutation authority (the WP175
A0-A3 state is untouched). Restart -> no-new-exposure -> discover -> cancel/reconcile; admission
requires an authoritative REST reconciliation to clear the flag. A clean terminal prior episode
(CREATE_REJECTED, TERMINAL_NO_POSITION) does not block a fresh permit after restart. A known
reconciled residual BUY position (TERMINAL_KNOWN_POSITION) survives restart and stays in aggregate
commitment until the position is explicitly reported closed. Unknown, corrupt or replay-mismatched
state blocks. Public venue order IDs and the release SHA are persisted only under exact allowlisted
field names; secrets, signatures and raw responses never are.

## 15. Foreground surface

`live_orch.py` exposes `preflight` (read-only: no authentication, ledger write or mutation),
`canary` (one CREATE maximum) and `reconcile` (risk-reducing recovery only; never new exposure).
The CLI requires an interactive confirmation phrase for `canary`; a pipe never confirms. There is
no daemon, scheduler, service, heartbeat loop, WebSocket recovery authority, cockpit mutation UI,
raw SDK client construction or automatic scaling.

## 16. Activation separation

Merge does not activate live trading. After merge, Side16 verifies the actual merge SHA and creates
a standalone activation artifact binding the actual merge/deployed SHA, exact permit ID, exact
intent ID, public canary-wallet identity, one CREATE maximum, the $100/$5/$30/$70 envelope and
operator confirmation. This contract never authorizes a real order.

## 17. Deferred

Economic SELL CREATE; Session Keys / Builder keys; SDK upgrade; heartbeat daemon; user-WebSocket
recovery authority; automatic CREATE retry; auto scaling; neg-risk / delayed markets; redemption;
funding/withdrawal/bridge; wallet deployment / approval automation; arbitrary busy-account
migration; Control Center mutation UI; multi-strategy unattended scheduling; second VPS / VPS
upgrade; true UTC-day / high-water loss accounting.
