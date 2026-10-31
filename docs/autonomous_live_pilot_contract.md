# Integrated Hermes research and protected account adapter

S10-HERMES-LIVE-INTEGRATED-01, PROTECTED/Risk4/XL. The exact execution contract is
the independently certified prompt/spec under `docs/wp_specs/S10-HERMES-LIVE-INTEGRATED-01/`.
This document describes implemented capability, not a trading permit.

## Capability and explicit limit

`src/live_pilot/autonomous_cycle.py` composes the unchanged category-neutral
near-term scanner, native NBA/rain source Hunter and its controlled Hermes runtime,
native policy/custody and LIVE-ORCH account reconciliation. It does not introduce
a venue client, credential store, model backend, strategy identity or order gateway.
The deployment entry point is an explicit finite foreground invocation; it installs
no service, timer or recurring job and does nothing on import.

The production calibrated-method allowlist is empty. Existing ESPN/NWS methods
produce source bounds with calibration UNPROVEN. Cold replay can construct only
`SOURCE_BOUND_ONLY` forecasts, never `QUALIFIED_FOR_ADMISSION`. Arbitrary generic
Hermes probabilities, confidence labels, citations, calibration badges and rehashed
records cannot change this. Therefore this release has no reachable economic
CREATE, SELL or CANCEL path and cannot activate bounded live trading. This is a
software capability limitation; neither credentials nor a green test supplies
an independently calibrated method.

## Invocation and authority

Use `python -B tools/deployment/run_autonomous_hunter.py --policy-path <absolute-path>`.
The remaining explicit native invocation inputs are `--native-policy-path`,
`--owner-record-path`, `--owner-record-sha256`, `--hunter-scratch-dir`,
`--alpha-registry-path`, and the optional complete tuple `--budget-path`,
`--executable`, `--home`. These are public paths/digests, never secrets. Existing
native custody providers alone receive local credentials. No key or seed belongs
in command arguments, this repository, chat or evidence.

OFF requires no runtime inputs and performs no state/account/network work.
RESEARCH and LIVE require the exact native v2 owner/policy binding, matching
wallet, signer, release and state root, a narrower validity/risk envelope, host
currentness, fresh official access proof and native authenticated reconciliation.
LIVE does not grant additional admission capability in this release. The raw
native owner record digest is required; the adapter never manufactures one.

Before reconciliation, both a read-only ledger check and a check under the native
wallet session lock refuse any economic episode. The restrictive native subclass
also unconditionally refuses `_cancel_rounds`; a concurrent resting episode cannot
cause a recovery CANCEL. Existing economic state is handed to the unchanged native
operator recovery path. The adapter's outer pilot lock is a singleton for this
adapter, not proof of exclusivity against every other native command.

## Bounded policy, persistence and replay

The strict canonical `autonomous-cycle-policy@1.0.0` keys and ranges are fixed in
certified section4D: OFF/RESEARCH/LIVE; <=4cycles, <=7200seconds, cadence60..3600s,
shared <=40public GETs/cycle, <=10forecast candidates, <=4provider calls and <=USD2
provider reservation total. Actual owner budgets default to zero and also intersect
native Hunter's <=3calls/invocation and <=USD0.50/run maxima. The fee-inclusive order
ceiling remains USD5, aggregate ceilingUSD30 and free collateral at leastUSD50 or
the stricter actual native profile. No automated scaling or fee-policy renewal.

One immutable policy/owner/wallet binding and contiguous hash-chained journal live
in the native external state root. Each cycle reserves its maximum public requests
and provider calls/cost before dispatch. Exceptions and ambiguous calls never refund
reservations. A terminal repeats the exact claim, bounded actual counts and native
manifest hashes. Exclusive creation and native fsync writing preserve prior records;
torn/missing/reordered/rehashed-invalid entries, changed identity or an unmatched
reservation refuse restart. The first recorded start anchors the duration across
restarts; no process restart clears quotas or extends the owner window.

Native scanner scratch is fresh per cycle and verified cold. A shared wrapper meters
each scanner public transport/native Hunter Fetcher request before dispatch; it keeps
their fixed endpoints, response bounds and source validators. Native partial captures
remain incomplete evidence. Native Hunter is launched only when the remaining deadline
can cover its existing acquisition and worst-case reserved inference window.

The native PILOT_KILL file creates a durable policy-bound latch. Its later removal
does not resume research. Checks occur before and after each bounded public dispatch,
after inference, and in <=1second cadence chunks. An in-flight bounded native request
cannot be interrupted by this adapter; no subsequent dispatch is allowed after kill.

Forecast identity is SHA256 of native canonical JSON excluding only its own hash;
cycle identity binds wallet/release/policy/index; journal identity excludes only its
own entry hash. These hashes are integrity checks, not authority. Source bytes and
native manifests must rederive independently. The exact20-field forecast binds
StrategyVersion, market/condition/token/outcome, rule, native method, source receipts,
cutoff and interval. Its lifetime is at most30seconds and ends before the native
event deadline. Unsupported or uncalibrated evidence always abstains.

## Negative evidence and activation checkpoint

The test matrix covers strict types/keys/nonfinite values, stale/tampered source and
hashes, generic confidence forgery, source-bound-only replay, fee/minimum conflicts,
wallet mismatch, authentication/access/host refusal, prior economic episodes and the
post-ledger race, singleton, kill, exhausted budgets and crash reservations. Positive
fixtures are explicitly synthetic and never establish empirical calibration or live
permission. Test-node traceability and exact validation results belong in the status
fragment and current PR body.

One consolidated owner setup checkpoint preserves the existing secure local custody,
public wallet/signer/Deposit Wallet, funded bounded capital/provider policy, current
host/official eligibility and exact first-canary record requirements. First live
CREATE remains the unchanged `src/execution_gateway/live_canary.py` composer with
witnessed OAuth and attended Stage-B owner confirmation. No lower-level canary call
is an alternative. Independently calibrated admission is unavailable on this base;
do not request secrets or fund/execute an order to hide that limitation. Merge is
Karl-only and does not activate an account, research process or trading.


## S10-AUTONOMOUS-EDGE-TO-LIVE-01 successor software

The separately certified successor adds deterministic mathematical diagnostics and
native refusal/risk/session guards. It does not establish a production-calibrated
method, an executable structural hedge, an account, or trading eligibility.
Production corpus acceptance: **0**. Production method acceptance: **0**. The finite
cycle cold-verifies scanner capture and reports missing settlement proof, then
replays supported native source forecasts and invokes the independent empty-corpus
calibration boundary. It cannot promote synthetic rows or arbitrary calibration
files. It has no economic dispatch while these acceptance sets are empty.

`calibration.historical_bound` validates exact method/rule/horizon identity,
pre-resolution source cutoffs, unique event groups and resolved-before-decision
observations. It sorts by resolution time/group, uses floor(0.7*N) training rows,
rejects a resolution-time tie across the split and a method frozen after holdout
sources, and uses training prevalence for the fixed comparison baseline. It checks
holdout Brier and at least50 holdout groups in the current fixed decile. Wilson is
one-sided95%, z1.6448536269514722, checked Decimal precision80, floored to1e-6.
These results are TEST_ONLY diagnostics: self-hashed rows do not authenticate
historical provenance or settlement, and sampling intervals do not prove future
stationarity. No real NBA/ESPN or daily-rain/NWS corpus has been accepted here.

`structural.verify_complement` computes synthetic/research-only two-outcome
payoff/cost diagnostics. `assess_capture` cold-verifies native scanner artifacts
but returns SETTLEMENT_UNVERIFIED: binary token labels alone do not rule out
void/cancel ambiguity. The existing single-order FOK gateway cannot prove all-leg
atomicity. There is no sequential hedge-leg dispatch. Structural execution remains
MULTI_LEG_EXECUTION_UNPROVEN; a positive arithmetic example is not live evidence.

An opt-in `autonomous_edge` execution-rule marker contains exactly method_id,
method_sha256 and corpus_proof_sha256. The proof is independent of the strategy;
the native StrategyVersion and intent hash the whole rule. LIVE-ORCH re-reads and
checks this marker under its existing wallet lock immediately before admission,
including the unchanged attended first-canary route. Missing/unaccepted proof
refuses. No admission result is hashed into its own parent strategy identity.

Both historical USD5 profiles remain unchanged. AUTONOMOUS_EDGE_01 is a distinct
dormant profile: account ceilingUSD100, fee-inclusive order ceilingUSD10,
aggregate commitmentUSD10, free-collateral reserveUSD90 and gross realized-loss
plus worst-case open/ambiguous/proposed exposure ceilingUSD10. USD6-8 is an initial
target, not a minimum. V3 Hunter policy and owner records bind activation_id,
activation_ledger_head, previous_session_sha256, provider_max_rolling24h_usd and
first_canary_receipt_sha256 in addition to historical public fields. Session-key
custody on this new version requires exactly CLOB scope, native provider support
and real official account acceptance. Legacy v2 parsing/scope compatibility stays.

The owner activation ledger head must be present in replay-verified native
history. Initial equity is latched by activation identity before economic history
exists, preserved across policy/release renewals and never reset by gains or days.
Cost-bearing completed native BUY lifecycles include the V1 first canary; each
loss is max(BUY cost/fees minus that lifecycle's confirmed SELL net proceeds,0).
Unverified redemption proceeds count as zero conservatively. Native current open
and unresolved commitments are counted once by their canonical episode identity.
New-profile exits select their own native profile; legacy v2 cannot own them.

Before post-canary admission the external native state root must contain the
owner-bound original first-canary.json and first-canary-stage-a.json. Verification
requires original receipt shape/hash, production class, all four native dispatch/
confirmation/order counts, permit/intent/episode correlation, reconciled fee state
and the StageA digest/menu/wallet/release/window. An invented minimal receipt or
an OFFLINE_TEST_ONLY result is rejected. These files are activation inputs, not
artifacts generated by implementation or CI. The unchanged first composer still
uses V1's USD5 envelope. If fee/minimum requirements cannot fit, no first canary
occurs; the USD10 profile cannot bypass it.

Autonomous policy/journal v2 preserves the same existing run lock and external
state root. An immutable activation.json binds activation/wallet/root/native
baseline. Each renewable session has its exact policy snapshot and native-style
journal in session-<policy-digest>, names the previous completed terminal digest,
and retains all prior history. Missing/forked/pending history, a new root against
native economic history, backward clocks and changed activation bindings refuse.
There are at most256 preserved sessions; reaching that bound refuses further work
rather than discarding history. Provider consent defaults to zero and expires
with the owner record. Rolling24h spend includes every reserved maximum through
terminal+24h, conservatively covering late dispatch; pending ambiguity refuses and
is never refunded. The tighter native per-call/per-session limits also apply.
Finite cycles retain default OFF, deadlines, current host/access/account checks,
immutable kill latch, reservations before dispatch and bounded pause checks.
No timer/service is installed or started. New all-horizons scanner mode removes
the two-hour filter while retaining native request/page/body/time ceilings and
cold replay; the historical scanner default stays7200seconds. Coverage is partial
and endDate never proves settlement.

Every public result field is covered explicitly by output tests; numeric/boolean
fields are exempt from textual echo, and string/list/hash/status fields are scanned
or validated by closed grammars. A hand-built dictionary is not a full
output-surface scan unless a field-coverage test proves it covers every public field.
Invalid numerical/record/source inputs return closed reasons without raw values.

The single post-merge owner checkpoint is READY_BUT_ACTIVATION_BLOCKED until real
edge/provenance, exact wallet/funds, current eligible host, protected custody,
provider consent, current fees/minimums/risk and an attended reconciled native
canary exist. Owner setup alone cannot populate the code-pinned empty production
acceptance sets. Software validation does not prove profitable trading, actual
balances, a source sample denominator or real order receipt. No new speculative
research WP is required by this report. Any actual promotion remains separately
authenticated/authorized and within exact approved protected scope. Merge is Karl-only.

Official references checked2026-10-30: [fees](https://docs.polymarket.com/trading/fees),
[Session Keys](https://docs.polymarket.com/trading/session-keys),
[orders](https://docs.polymarket.com/trading/place-orders).
These references are not proof of account eligibility or beta availability. The
existing fee-policy expiry2026-11-04T00:00:00Z remains unchanged.


## S10-EDGE-EVIDENCE-ACTIVATION-01 forward evidence checkpoint

The same-engagement protected evidence software reuses one finite native rain
Hunter capture and offline replay. See `docs/edge_evidence_activation_contract.md`.
No accepted production corpus/method or historical settlement proof is supplied
by capture. Current source receipts are forward-only research; genuine resolved
holdout denominator remains0. Independent event groups are not inferred from
station/day identity or duplicated market tokens. Caller flags/hashes never
promote financial authority. Training labels must predate all holdout forecasts.

The capture is explicitly invoked, no scheduler/provider/account dispatch; its
capture-local kill is checked and latched before source requests. Access refusal
401/403/451 or redirects stops future dispatch. ESPN is not queried without
separate automated-use permission. Existing native first-canary/custody/account/
Gate C/gateway/risk/session behavior and empty production allowlists remain.
The new offline checkpoint marks host/account/canary NOT_OBSERVED. Windows public
research is not production-host qualification. The original5USD first attended
canary and dormant10USD profile remain separate. Karl-only merge; LIVE DISABLED.
