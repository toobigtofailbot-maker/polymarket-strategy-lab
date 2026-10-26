# S10-ALPHA-SHADOW-LOOP-01 — foreground public forecast and outcome loop

This is a non-economic research operator. Karl authorized the six-path package on
26 October 2026. It reads public sources, records independent publisher forecasts,
computes cost-aware scenarios, and later evaluates outcomes. It does not place
simulated venue orders, create strategies/intents/permits, call Hermes, run a daemon,
write production stores, or grant trading authority. All state is external scratch.

## Operator interface

```powershell
python -B tools/alpha/run_shadow_alpha_cycle.py init --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_cycle.py cycle --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_cycle.py verify --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_cycle.py update-outcomes --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_cycle.py link-paper --scratch-dir C:/outside-checkouts/shadow --paper-store C:/outside-checkouts/research-paper.sqlite3
```

The parent of a new scratch directory must exist. No default path is inferred.
Reject any checkout ancestor containing `.git`, credential-like directory, symlink
or Windows reparse point. `init` creates exclusively; it never replaces files.
The committed module is the configuration definition; each scratch freezes its
exact configuration. There is no scheduler, retry, credential discovery or URL input.

Each explicit cycle discovers up to 200 current NBA moneyline markets using one
fixed Gamma request, triages **every returned market**, then matches at most eight
games to two dated ESPN scoreboards. It acquires at most eight summaries and sixteen
CLOB books. No caller shortlist or probability value is accepted. The selected
cohort is NBA moneyline, not all markets or all sports. Other dates, unsupported
rules, missing sources and analysis overflow remain counted rather than invented.

At most 32 GET attempts per operation, 2,000,000 bytes per public body, 20 seconds
per request, a 120-second application acquisition deadline, no redirects, environment proxies or
automatic retries. Per-request STARTED is durable before dispatch. Failures count.
Body reads update the remaining deadline on each bounded chunk. Initial DNS/connect
and header handling rely on platform urllib/socket timeouts; this is not an
unconditional OS-level wall-clock watchdog.
Public JSON rejects duplicates, nonfinite constants, excessive depth/nodes/strings;
the ESPN wrapper has its own bounded depth because display metadata is deeper than
native venue snapshots. Native venue parsers and guards remain unchanged.

## Actual source binding and probability semantics

The pre-implementation admission matched real Gamma market `6000454` (Nets/Celtics,
2026-10-27 23:30 UTC) to ESPN NBA event `401909877`. Its source documents were frozen
outside the checkout on 26 October before kickoff; the prompt records their hashes.

Method `espn-nba-pregame-v1` uses ESPN **Matchup Predictor** percentages divided by
100. It checks league, exact team names/ids, complementary probabilities, identical
start time, and unstarted status. The observed example was Nets 0.167/Celtics 0.833.
This is independent of Polymarket prices and of AI verbal confidence. It is an
external publisher forecast, not a repo-trained or proven calibrated model. The
upstream model version, training provenance and prediction publication timestamp
are not supplied by the endpoint and are explicitly unknown. Receipt time proves
availability before kickoff; HTTP Date freshness describes the served document,
not the age of the upstream model calculation. No receipt is backdated.

Only the exact frozen NBA rule template is supported: final winner including
overtime, postponement waits for completion, outright cancellation pays 0.5 on both
tokens. Source teams, market/condition, ordered outcomes/tokens and rule hash are
bound into the forecast. Spread, total, player props and changed rules abstain.

The probability is conditional on completion. The 0.10 stress radius is a disclosed
sensitivity assumption, **not a statistical confidence interval**. The identified
uncalibrated probability bound remains [0,1]. Unknown cancellation probability adds
the exact 0.5 payout to the stress-payout hull. Uncertainty is not hidden behind an
arbitrary high-confidence admission threshold.

## Discovery and native reuse

The operator builds native PIT metadata records from frozen public Gamma bytes in
an isolated scratch SQLite store. ALPHA-02 builds and validates the universe,
triage and queue over that store. Native `HISTORICAL_REPLAY` here is replay of the
just-observed frozen data with no Alpha memory registry; it is not a historical
forecast backtest. Rule/book capture gaps in that discovery registry remain visible.
Current venue books and rules have separate source receipts for shadow scoring.

Current economic normalization, sorted depth sweep, fee function, tick and minimum
dimensions reuse `src/execution_feasibility/`. No native StrategyVersion,
ExecutionIntent, AUTO choice or WP172 PASS is manufactured to satisfy an interface.
WP172 keeps its preregistered OOS, continuity and markout requirements.

## Cost-aware scenarios, not fictional fills

All arithmetic is Decimal. For ten intended shares, the best-ask depth sweep
computes capacity and notional, native taker fees rounded upward, and a separately
disclosed 0.005/share residual-cost stress. Spread/depth already in acquisition
price are not charged again. Both native minimum dimensions must pass (Gamma's
repo-defined minimum USDC notional and CLOB minimum shares); ticks and identities
must agree. Unknown fees, stale/crossed books and insufficient depth are unscorable.

The point completion scenario is `shares*p - acquisition_notional - fee - residual`.
The stress scenario substitutes the lower expected-payout sensitivity/cancellation
bound. Both assume fill/outcome independence; that assumption is explicitly
unverified. No realized fill ratio or fill probability has been observed. Therefore
positive scenario value produces `RESEARCH`, **not an actionable SHADOW_CANDIDATE**.
Unknown per-intended-order EV is reported with a coarse valid identification bound
including adverse selected fills and no fill. Passive queue/fill probability stays
unknown; a posted quote never produces a fill. Zero fill produces zero trade profit.
Market midpoint is a forecast comparison baseline, not an executable acquisition price.

This implements the source-backed economics boundary without promising positive EV
or inventing a fill model. Measured actionable per-order edge remains unproven.
The snapshot may show the venue's `restricted` flag; no account/geographic eligibility
is inferred or circumvented.

## Repetition, replay and evidence classes

Every manual operation has STARTED before work and exactly one terminal after work.
A kernel-held operation lock prevents concurrent writers and releases on a crash.
Before new dispatch the operator verifies prior history under that lock. A started
operation without a terminal becomes INTERRUPTED_OR_UNKNOWN on the next operation;
it is never redispatched. Request starts survive a crash before a response and are
counted as unknown attempts. Repeated source/model lineage retains one forecast id,
but every occurrence and every observed attempt remains in the ledger.

Terminals bind all input-file hashes. `verify` replays native discovery, probability,
economics, outcome labels and learning from frozen inputs with zero fresh dispatch.
It validates receipt binding and counts completed, interrupted and unknown-request
denominators. These local checks detect inconsistent edits; they are not a signature
or proof against an attacker rewriting the entire scratch history and its hashes.
There is no canonical evidence-policy or execution-authority promotion.

`SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS` means the operator obtained actual public
forecasts and at least one admissible cost calculation. It does not mean positive
edge, calibrated skill, fill probability, realized profit or learning improvement.
Offline fixtures test logic only. Empirical receipts are separately inspectable.

If a native research-paper source is explicitly supplied, freeze a byte copy outside
all checkouts, reject sidecars, verify the copied store with native PaperStore and
build the native performance snapshot. The original stays unchanged. The evidence
is `NATIVE_RESEARCH_PAPER / UNLINKED_NOT_CAUSAL`, with no shadow-fill or live-profit
credit. Absence is `NO_PAPER_SESSION`. Real live P&L is never inferred or imported.

## Resolution and learning

Outcome update matches the original market/condition/ordered tokens/outcomes/rules,
requires a final Gamma `resolved` state and valid later closedTime, and corroborates
the matching final ESPN winner. A cancellation/0.5 settlement requires independent
cancellation status and is excluded from binary Brier/log loss. Disputed, unverified,
postponed and unsupported payouts stay pending. Labels are observed later; no final
source may become a pregame feature.

One earliest pregame forecast/book baseline per independent event gets calibration
credit. Repeat forecasts and duplicate finalizations do not create independent
trials or profit. Brier uses raw probabilities; log loss alone clips endpoints to
[0.000001,0.999999]. Unresolved events/abstentions and canceled games stay distinct.

One reversible research-only blend proposal weights the independent forecast vs
market midpoint over the frozen grid 0.25/0.5/0.75/1. The first ten finalized events
form the immutable formation roster. Holdout takes the first ten later finalized
events whose predictions occurred strictly after every formation label was available.
Both rosters and the formation closure clock are in the proposal identity; appending
a delayed event cannot move them. The candidate, original and market are compared
on the identical holdout. A point improvement is not statistical significance.
There is no automatic adoption. Insufficient evidence is
`IMPROVEMENT_NOT_YET_MEASURABLE`. No-trade P&L zero is an economic baseline, not a
probability forecast or a realized shadow return.

## Boundaries and rollback

All Centralized Boundary Group Reference entries in
`docs/ai/codex/PROTECTED_PATHS.md` remain closed: credentials/secrets, authenticated
clients, wallet/account behavior, order placement/cancel, execution gateway, paper
engine mutation, scheduler/bot loop, runtime/daemon, dashboard/deployment,
dependency/lock changes, external code copying and tracked generated artifacts.
Only the declared foreground public research and isolated scratch/paper-copy reads
are authorized. Revert the six additive paths to remove this capability. No package
step authorizes a future autonomous pilot, canary reuse, capital, deployment or merge.
