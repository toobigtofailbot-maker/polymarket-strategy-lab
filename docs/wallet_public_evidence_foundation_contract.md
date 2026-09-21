# Public Wallet / Point-in-Time Wallet Evidence Foundation Contract (S10-WALLET-01)

Status: implementation complete; awaiting Side11 independent exact-head review.
Authority owner: Karl / Side11.

This document is the authoritative contract for the S10-WALLET-01 public wallet
evidence foundation. The foundation is a **data / evidence substrate**. It has
**zero** qualification, ranking, promotion, copyability, profitability, sizing,
order, signing, paper, live, scheduler, Hermes, or WP170 authority.

## 1. Modules

| Module | Purpose |
| --- | --- |
| `src/data_layer/point_in_time_market_research/research_provenance.py` | Shared research provenance / PIT time / DQ / replay-fidelity / replay-admissibility core (first implementation of the accepted common R1-R4 contract). |
| `src/data_layer/wallet_intelligence/contracts.py` | Canonical public wallet event model, context-typed identifier and decimal canonicalization, event vocabulary, identity-strength, cost-basis, account role/wallet-type, closed public error vocabulary. |
| `src/data_layer/wallet_intelligence/reconciliation.py` | Append-only API/chain reconciliation, deterministic chain ordering/dedupe, versioned finality policy, event-equivalence assessment. |
| `src/data_layer/wallet_intelligence/ledger.py` | Local append-only SQLite wallet evidence ledger. |
| `src/data_layer/wallet_intelligence/public_ingest.py` | Bounded public Data API v2 wallet ingest lifecycle. |
| `src/data_layer/polymarket/public_client.py` | Bounded public Data API v2 wallet GET methods (fixed host, byte cap, no redirects). |
| `src/data_layer/polymarket/polling_policy.py` | Hard wallet bounds and disabled-by-default wallet feed policies. |

## 2. Shared PIT time vocabulary

`event_time`, `chain_block_time`, `source_publish_time`, `public_available_time`,
`local_first_seen_time`, `ingestion_time`, `confirmation_or_finality_time`,
`correction_or_revision_time`, `resolution_time`. Each is nullable/UNKNOWN when
not evidenced. No timestamp substitution: `event_time` never implies public
availability or local first-seen; historical/backfilled event time never proves
contemporaneous observability. All non-null timestamps are explicit UTC with a
canonical `Z`; naive timestamps are rejected.

## 3. Data-quality vocabulary

Core: OK, MISSING, STALE, DELAYED, CORRECTED, BACKFILLED, PARTIALLY_OBSERVED,
DUPLICATED, SEQUENCE_GAP, TIMESTAMP_UNCERTAIN, SOURCE_UNAVAILABLE, SCHEMA_DRIFT,
SOURCE_DISAGREEMENT. Wallet extensions: REORGED, UNFINALIZED, IDENTITY_AMBIGUOUS,
COST_BASIS_INCOMPLETE, BOOK_UNAVAILABLE. Canonical sorted/deduped; OK cannot
coexist with any non-OK flag; unknown flags reject; absence of evidence is never
coerced to OK.

## 4. Replay fidelity and admissibility

Replay fidelity: EXACT, FAITHFUL, PARTIAL, UNREPLAYABLE. Hash-only evidence with
unavailable raw bytes/reference cannot claim EXACT. Replay admissibility uses one
shared deterministic contract (`evaluate_replay_admissibility` / `observable_at`)
with closed statuses ADMISSIBLE / NOT_ADMISSIBLE / INDETERMINATE and closed bases
LOCAL_FIRST_SEEN, PUBLIC_AVAILABLE, NOT_YET_SEEN, CORRECTION_AFTER_CUTOFF,
TIMESTAMP_UNCERTAIN, NO_OBSERVABILITY_EVIDENCE. `event_time` is never an
admissibility clock.

## 5. Provenance manifest (non-circular)

`ResearchProvenanceManifest` is one common content-addressed core. Direction is
one-way: `WalletProvenanceExtension -> ResearchProvenanceManifest`. The core never
references any wallet/domain extension and carries no `ingest_run_key`; its
identity is computable without any extension existing.

## 6. Canonical wallet event model

Records: `WalletAccountIdentityEvidence`, `WalletEvidenceEvent`,
`WalletEventObservation`, `WalletFeedPageEvidence`, `WalletReconciliationLink`,
`WalletProvenanceExtension`, `WalletIngestRunReceipt`. Canonical economic-event
identity (`WalletEvidenceEvent`) is separate from immutable source observations
(`WalletEventObservation`); observation/acquisition provenance never enters
economic-event identity.

- **Address**: canonical lowercase `0x` + 40 hex, ASCII only, no EIP-55.
- **Generic account role** and **Polymarket wallet type** are independent
  dimensions. Roles: ACCOUNT_WALLET, SIGNER, PROTOCOL_CONTRACT, OTHER_CONTRACT,
  UNKNOWN. Wallet types: EOA, POLY_PROXY, GNOSIS_SAFE, DEPOSIT_WALLET, UNKNOWN.
- **Context-typed identifiers**: bytes32 (tx/block hash), DATA_API_RESPONSE,
  PROTOCOL_STANDARD, MARKET_SELECTOR, and COMBO condition-id contexts stay
  distinct; no helper leaks across contexts.
- **Decimals**: exact base-10 canonical strings; binary floats never participate
  in content-addressed identity; JSON numbers parse with `parse_float=Decimal`.
- **Identity strength**: CHAIN_NATIVE_STRONG, API_NATIVE_STRONG,
  SOURCE_CONTENT_DERIVED, WEAK_PARTIAL. Trade combo state: FALSE, TRUE, UNKNOWN.
- **`/v2/trades` combo state**: current drafting-time disposition is E2 =
  UNKNOWN (primary sources do not prove ordinary-market-only). UNKNOWN is a
  first-class state and is never coerced to FALSE for deduplication.
- **Cost basis**: KNOWN, PARTIAL, UNKNOWN, NOT_APPLICABLE; imported/transferred
  inventory basis stays UNKNOWN/PARTIAL when unknown.

## 7. Reconciliation

Append-only. States: API_ONLY, CHAIN_ONLY, API_AND_CHAIN_CONFIRMED,
SOURCE_DISAGREEMENT, SUPERSEDED_BY_STRONGER_EVIDENCE, REORGED_OR_REMOVED,
UNRESOLVED. Finality: UNKNOWN, UNFINALIZED, CONFIRMED, FINALIZED, REORGED, under
an explicit versioned policy (no hardcoded block-count folklore). Weak similarity
never merges distinct events; deterministic strong native/chain identity or an
explicit protocol relation may establish equivalence append-only.

## 8. Ledger

Local stdlib `sqlite3`, explicit caller path. Unique `application_id`
(`0x57414C31`), frozen schema, append-only rows with UPDATE/DELETE protection,
per-entry hash chain in a caller-order-independent canonical topological order,
reference integrity, exact-duplicate idempotency, same-id/different-payload
conflict, atomic append, and complete semantic verified load. It is not Alpha
Factory research memory and holds no qualification or trading authority.

## 9. Bounded public network

Trust root frozen to `https://data-api.polymarket.com`. GET-only, no auth, one
request per method, no cursor loop, no retry, no sleep, no daemon. Network is
disabled by default. Hard bounds: 10 pages/feed, page size <= 100, 1000
rows/feed-run, 3000 rows/run, 4 MiB response byte cap enforced during the read,
4096-char cursor cap. Redirects to another origin are rejected.

## 10. Ingest lifecycle

Pre-run `ingest_run_key` (carried by page/observation/receipt only; never by raw
evidence, events, or the manifest). Collision reuse fails closed before transport
(LEDGER_IDENTITY_CONFLICT). Each successful page (including zero-event pages) is
committed atomically before the next request, preserving first-seen durability.
The terminal `WalletIngestRunReceipt` has its own identity and references only
already-committed evidence. Collection COMPLETE is derived only when all three
required feeds are COMPLETE against their own acquisition contract; combo activity
reports `time_filter_capability=NOT_SUPPORTED`. Offline recovery appends exactly
one PARTIAL_INTERRUPTED terminal receipt with zero network calls and no rewrites.

## 11. Closed public error vocabulary

See `WALLET_PUBLIC_ERROR_CODES`. Public errors never echo arbitrary exception
text, raw response bodies, unsafe URLs, paths, or unbounded source material.

## 12. Later-WP boundaries

WALLET-02 (profiling/specialization/cohorts/promotion/clustering), WALLET-03
(copyability/latency/depth/slippage/capacity), WALLET-04 (anomaly/incremental
value), S10-GATE-WALLET-01, QUAL-01, WP170, and Gate C own everything beyond this
evidence substrate. No surface here is named or semantically equivalent to
rank_wallets, score_wallet_skill, qualify_wallet, copy_wallet, recommend_trade,
place_order, size_position, paper_trade, or activate_strategy.
