# Wallet Profile Snapshot Contract

Status: S10-WALLET-02 canonical local/offline research-evidence contract.

## Authority

This layer reads one existing, verified WALLET-01 evidence ledger. It never initializes,
mutates, or supplements that ledger and creates no second profile store. Its outputs are
advisory research evidence only. They grant no qualification, strategy, paper, execution,
live, signing, order, sizing, capital, or Gate-C authority.

## Canonical records

- `WalletProfileMarketContext` binds exact condition/token identifiers, instrument class,
  caller-supplied descriptive labels, optional independence group, separate metadata and
  resolution observability/DQ/replay evidence, provenance, policy version, and authority
  booleans. Its id is `walletmarketctx:sha256:<sha256>` over all logical content except
  the id itself.
- `WalletDiscoveryCohortSnapshot` freezes discovery cutoff, forward evaluation interval,
  selection policy, PIT-admissible member discovery evidence, provenance, roles, and the
  `RETAIN_MEMBERS_IMMUTABLY` survivorship rule. Its id is
  `walletcohort:sha256:<sha256>` over all logical content except the id itself.
- `WalletProfileSnapshot` binds the public-account subject cluster, frozen cohort and role,
  as-of/window, exact verified ledger head, event/observation decisions, context/provenance,
  DQ/admissibility basis, scope cells, sample/skill/specialization/archetype evidence, and
  authority booleans. Its id is `walletprofile:sha256:<sha256>` over the complete logical
  snapshot except the id itself.

All records are frozen. Canonical JSON rejects binary floats, unknown fields, invalid ids,
and silent coercion. Build-to-mapping-to-load round trips reproduce identical mappings and
ids; any material change changes the relevant id.

## PIT and evidence selection

`build_wallet_profile_snapshot` accepts an explicit ledger path and calls
`load_and_verify_wallet_evidence_ledger`. Invalid, missing, foreign, or tampered ledgers
fail closed through a bounded no-echo error code. `event_time` only places and orders an
action; it never establishes observability. Events, cohort discovery, context metadata,
resolution, and relationship evidence use shared `evaluate_replay_admissibility` rules.

Strong same-event and chain-confirmation links collapse before metrics. Canonical
representation rank is chain-native, API-native, source-content-derived, then weak-partial,
with id tie-break. Admissible supersession uses the successor; reorg/removal and source
disagreement do not increase sample or skill; unresolved similarity never merges events.
Each decision remains explicit in `ProfileEvidenceDecision`.

## Public-account relationships

Profiles describe public-account clusters, never people. Only `PROTOCOL_DECLARED` or
`ONCHAIN_CONFIRMED` links with a related account, effective at cohort discovery, and
independently admissible at that cutoff may aggregate transitively. Source-reported,
statistical-similarity, unknown, or late evidence remains non-aggregating. A strong cluster
spanning candidate and control roles fails closed. All linked addresses share one sample
accounting surface.

## Sample and directional evidence

The evidence window is the cohort evaluation start through the earlier of profile `as_of`
and cohort evaluation end. Directional episodes require a canonical admissible clean
faithful/exact BUY fill, exact standard-binary context, price in `[0,1]`, explicit
independence group, independently admissible binary resolution, and action strictly before
decisive resolution availability. SELL and unsupported instruments do not become
directional evidence.

Repeated activity collapses to the earliest eligible BUY per condition/token inside a
group. Correlated episodes in one group contribute one equal-weight group result. Missing
grouping yields `UNKNOWN_INDEPENDENCE`; raw trades, conditions, addresses, PnL, size, rank,
and rebates never substitute for an independent sample.

Per episode, `signed_entry_residual = resolved_token_value - entry_price`. A group's mean
residual is success when positive, failure when negative, and neutral at zero. Across groups
the mean is equal-weight. Jeffreys evidence is exactly:

`alpha = successes + 0.5`; `beta = failures + 0.5`;
`mean = alpha / (alpha + beta)`;
`variance = alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1))`.

All calculations use `Decimal` precision 50. Exported derived decimals use 18-place
`ROUND_HALF_EVEN` quantization and canonical fixed-point text. The result is
`ESTIMATED_UNCALIBRATED`, not a future probability, significance claim, universal score,
or promotion state.

## Scope, specialization, and archetype

Scope cells are overall plus observed category, mechanism, and horizon labels. Each cell
has its own sample and directional evidence. Specialization is only the descriptive
distribution of independent groups across those dimensions, including `MIXED` and
`UNKNOWN`; one group may show a 100% share but never creates a specialist conclusion.

Archetypes are direct behavioral composition only: eligible directional episodes;
maker rebates; split/merge/conversion/combo transformations; incentives/rebates;
settlement; and transfers/capital flows. Unsupported evidence stays unclassified. One
observed class resolves to that class, multiple to `MIXED`, none to `UNKNOWN`. No intent or
human identity is inferred.

## Successor boundary

WP79 remains historical fixture compatibility. WALLET-03 owns observable copyability and
follower economics. WALLET-04 owns incremental value versus non-wallet baselines. The
wallet evidence gate remains conditional for wallet-dependent hypotheses. S10-ALPHA-02 is
the next separately gated package after WALLET-02 review, merge authorization, and merge.
