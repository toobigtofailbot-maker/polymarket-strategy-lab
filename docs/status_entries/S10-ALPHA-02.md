# S10-ALPHA-02 — PIT Market-Universe Alpha Discovery Control Plane

Status: IMPLEMENTATION COMPLETE (local validation and hosted evidence are authoritative only in the
current PR body)

PR: see GitHub PR metadata and PR body. Current live PR head: see GitHub PR metadata and PR body.
This fragment is stable and non-self-referential; it does not encode the commit containing itself
or predict mutable hosted-check state.

Ready for review: see the current PR body after exact-head hosted CI and live evidence verification.
Merge authorized: NO.

## Frozen base and scope

- Base/main and PR #190 merge SHA: `a2fba4d770cd6fac1cfb551419d040d65768a8e9`.
- Required predecessor implementation head: `2d53af9b3a51f8f9a27334e8bc3b2c40efe6864a`.
- Branch: `codex/s10-alpha-02-pit-discovery-control-plane`.
- Governance track: FAST; Risk level: 2; exact scope: 17 required = 17 allowed paths.
- Evidence mode expected: `PRIVATE_REPO_MANUAL_VERIFIED`.
- Negative matrix required: YES. N01-N24 cover PIT/Alpha lookahead, typed subject namespaces,
  decision-table and ordering drift, triage/queue circularity, Decimal material-change formulas,
  future-store identity, prior/current set differences, closed coverage, distinct clocks, external
  completeness honesty, complete skip accounting, pre-outcome audit selection, category caps and
  reserved capacity, no Alpha mutation/network execution, legacy-score non-authority, identity,
  append-only atomic registry behavior, and downstream authority rejection.

## Delivered

- Five frozen content-addressed schema-1.0.0 records: explicit policy, bounded observed-universe
  snapshot, typed material-change event, final per-market triage decision, and queue snapshot.
- Existing shared PIT as-of query remains sole T0 visibility authority; semantic universe identity
  excludes complete-current-store digests and remains stable under unrelated post-cutoff growth.
- Q-METADATA/Q-BOOK/Q-RULE/Q-SOURCE expose review-conflict records without promoting them to
  authority; exact market/token/resolution-source/referenced-source overlays fail closed.
- Explicit `HISTORICAL_REPLAY` versus `CURRENT_BUILD_ANALYSIS` Alpha-memory posture, exact canonical
  PIT subject matching, read-only current-registry integration, and no invented historical Alpha
  availability.
- Side12 ratified direct canonical PIT `market:`/`event:`/`token:` subject refs and deterministic
  no-backfill reserved lanes. Reopen lineage is grouped by exact candidate/family and ambiguous or
  incomplete multi-candidate governance requires review.
- Deterministic two-phase triage and bounded core/exploration/audit allocation with complete current
  market skip accounting, prior-only separation, inert prospective capture-request data, and no
  reserved-slot backfill.
- Separate append-only SQLite discovery registry, format `s10-alpha-discovery-registry`, application
  id `1464877426`, hash-chain integrity, atomic caller-order-independent append, and read-only load.
- One shared full semantic validator protects all five persisted records at builder, mapping,
  append, and load boundaries; correct re-hashing cannot launder invalid semantics.

## Side12 exact-head follow-up history

Side12 exact-head review required a same-WP correction. Hosted run `35873393203` on historical head
`667e6e9c8c7b5487835ebf14df0b93903b1f31b1` failed for an implementation-related lexical safety
guard finding. Run `35874820891` on historical reviewed head
`40bcee515251d2e958754bddd3dfae278928ec5c` later passed, but the amendment/new-head CI recovery was
outside the original closed retry authority. Side12 follow-up 01 explicitly authorized this one
correction cycle. Those runs remain historical evidence; only the fresh corrected exact-head run
recorded in PR #191 is current final evidence.

## Authority and residual limits

Product market/wallet network calls: 0. Hermes/provider/model calls: 0. H1 #5: NOT AUTHORIZED.
Scheduler/campaign actions: 0. Credential/private-key operations: 0. Qualification, expected-return,
strategy, paper/live, order, signing, and execution operations: 0. Capital at risk: USD 0. Gate C:
NOT AUTHORIZED. Dependencies/locks/workflows/tools: UNCHANGED.

External all-Polymarket completeness remains UNPROVEN. Empirical parameter tuning, ALPHA-03
campaign autonomy, ALPHA-04 outcome learning, qualification, economics, paper, execution, and live
remain deferred. After separate review and merge, the next gate is S10-GATE-AF1.

## Validation summary

Preimplementation readiness: `IMPLEMENTATION_READY`; FAST; minimum FAST; exact scope 17; no
certificate required. Strengthened focused evidence covers real PIT post-cutoff growth, real
T1-T9 current/historical cases, full material-change boundaries, all priority directions, semantic
mapping/store/load symmetry, exact PIT conflict overlays, and multi-candidate reopen grouping.
Exact regression, architecture, security, scope, full-suite, fresh exact-head CI, PR evidence guard,
and `PRIVATE_REPO_MANUAL_VERIFIED` results are recorded in the current PR body after final
committed-head validation.
