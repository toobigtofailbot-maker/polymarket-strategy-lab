# S10-WALLET-01 — Public Wallet / Point-in-Time Wallet Evidence Foundation

Status: DRAFT (implementation complete; awaiting Side11 independent exact-head review)

PR: see GitHub PR metadata and PR body.
Current live PR head: see GitHub PR metadata and PR body.
This status entry is stable and non-self-referential.

Ready for review: NO (until exact-head hosted CI is green and the PR body evidence is reconciled)
Merge authorized: NO

## Post-merge precondition (verified before drafting)
- PR #187 / WP175N / S10-ALPHA-01: MERGED at merge/main SHA
  `584924b5a23e00e13d400885fc50b8eebdd412a3`.
- S10-ALPHA-01: COMPLETE. Accepted roadmap next implementation package: S10-WALLET-01.
- Successor after this package, if separately authorized later: S10-HERMES-CTX-01.

## Scope delivered
- Shared research provenance / PIT time / DQ / replay-fidelity / replay-admissibility
  core (first implementation of the accepted common R1-R4 contract) in
  `src/data_layer/point_in_time_market_research/research_provenance.py`.
- New `src/data_layer/wallet_intelligence/` package:
  - `contracts.py` — canonical public wallet event model, context-typed identifier
    and decimal canonicalization, event vocabulary, identity-strength, cost-basis,
    account role/wallet-type dimensions, and the closed public error vocabulary.
  - `reconciliation.py` — append-only API/chain reconciliation, deterministic chain
    ordering/dedupe, versioned finality policy, and event-equivalence assessment.
  - `ledger.py` — local append-only SQLite wallet evidence ledger with a unique
    application_id, caller-order-independent topological hash-chain, reference
    integrity, atomic append, and semantic verified load.
  - `public_ingest.py` — bounded public ingest lifecycle: pre-run ingest_run_key,
    collision guard, per-page atomic commit, zero-event-page evidence, terminal
    receipt, and offline interrupted-run recovery.
- Bounded public Data API v2 wallet reads added to the existing GET-only client
  (`/v2/trades`, `/v2/activity`, `/v2/activity/combos`) with fixed-host trust,
  read-time byte cap, redirect rejection, and Decimal-preserving parsing; hard
  bounds and disabled-by-default wallet feed policies in `polling_policy.py`.

## Authority (all zero for this evidence foundation)
- credentials: 0; private keys/signing: 0; authenticated API: 0
- Hermes calls: 0; H1 calls: 0; qualification: NO; WP170 experiment creation: NO
- paper/live: NO; Gate C: NOT AUTHORIZED; capital: 0; orders: 0
- WALLET-02: NOT STARTED; HERMES-CTX-01: NOT STARTED

## Boundaries preserved
- Live trading remains DISABLED; execution/paper/qualification untouched.
- Alpha Factory research memory is not modified and holds no wallet raw evidence.
- No dependency, workflow, or generated-artifact change.

## Unresolved non-blocking
- Universal raw-retention/licensing backend remains configurable/deferred.
- Live chain/indexer acquisition provider remains separately gated.
- Wallet n_eff/promotion/cluster thresholds remain WALLET-02.
- L2/fill/copyability calibration remains ALPHA-02 / WALLET-03 / QUAL / WP170.
