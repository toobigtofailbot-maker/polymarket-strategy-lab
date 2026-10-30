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
