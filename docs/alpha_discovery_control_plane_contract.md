# S10-ALPHA-02 Alpha Discovery Control Plane Contract

Status: current bounded implementation target. Schema version: `1.0.0`.

## Authority and non-authority

This package is a deterministic, local/offline, advisory-only research control plane. It reads a
verified canonical PIT store and, only in current-build mode, a verified ALPHA-01 registry. It
writes only its separate discovery registry. It has no product-network, Hermes/provider, scheduler,
credential, qualification, expected-return, strategy, paper, execution, order, or live authority.
Capital at risk is USD 0. The protected boundary groups in
`docs/ai/codex/PROTECTED_PATHS.md` remain closed.

Research priority is not expected return, qualification, strategy, executable edge, or trading
authority. Capture requests are inert data records; they do not fetch or schedule anything.

## Authority separation

The canonical authorities remain separate:

1. The PIT record store owns versioned market, rule, source, and book evidence.
2. The ALPHA-02 discovery registry owns universe, change, triage, skip, and queue history.
3. The ALPHA-01 registry owns research candidates, families, and episodes.

ALPHA-02 never mutates the first or third authority. It uses the shared PIT as-of query as the sole
historical visibility/supersession/retraction authority and never implements a second latest-record
engine.

## Canonical records

The five frozen, closed, content-addressed records are:

- `AlphaDiscoveryPolicy` — `alphadiscoverypolicy:sha256:`
- `AlphaUniverseSnapshot` — `alphauniverse:sha256:`
- `MaterialChangeEvent` — `alphachange:sha256:`
- `MarketTriageDecision` — `alphatriage:sha256:`
- `AlphaResearchQueueSnapshot` — `alphaqueue:sha256:`

`PreAllocationTriageBasis` is internal-only and is never persisted as a registry kind. Every public
record binds `advisory_only=True`, `no_execution_authority=True`,
`no_strategy_authority=True`, and `no_qualification_authority=True`. Canonical mappings reject
binary floats, unknown/authority-leaking fields, noncanonical content, and identity mismatch.

One shared semantic validator covers all five persisted record types and their nested canonical
state. Every public builder validates before return; `to_mapping`, `from_mapping`, registry append
serialization, and registry load/decode invoke that same validator. A correctly re-hashed record
that violates a semantic invariant is therefore invalid at every public or persistence boundary.

No wall clock, local path, process/environment value, random UUID, or registry sequence enters
semantic identity.

## Policy

The policy makes all selection-affecting parameters explicit: eligible statuses; metadata, book,
and rule freshness windows; four canonical Decimal change thresholds; queue capacity; nonzero
exploration and audit reservations; category cap; audit seed; and taxonomy version. Production
callers supply a policy explicitly. The numeric values are parameters, not universal research
truths.

## Observed PIT universe

Universe construction loads and verifies the PIT store, enumerates candidate market ids only from
canonical Gamma metadata, and makes separate family-scoped queries for metadata, books, rules, and
each referenced source snapshot. Static projections include complete applicable history plus
lineage closure. More than 256 records fails closed with `PIT_QUERY_INPUT_LIMIT_EXCEEDED`; no
truncation or local newest-record selection is allowed.

Every query uses `AS_OF_INGESTION_TIME`. Ingestion time controls historical visibility. The exact
authoritative record envelope `observed_time` controls freshness. The boundary is exact: age equal
to the threshold is fresh; a larger age is stale; a future or malformed observed time is
`INVALID_CLOCK`.

Q-METADATA, Q-BOOK, Q-RULE, and Q-SOURCE set `include_conflicts_for_review=True`. Only
`authoritative_records` and `history_records` provide state. Returned review-conflict records remain
review evidence and are never promoted or used to replace authoritative payloads. Their canonical
entity identifiers apply exact metadata, token-book, resolution-source, or referenced-source
conflict overlays. Conflict-only metadata never admits a market to the universe.

The universe identity commits only to the policy, exact cutoff/query contract, included markets'
query-spec hashes, exact authoritative T0 record ids, and normalized market state. It deliberately
excludes complete-store counts/digests and full query batch/result hashes, so unrelated post-cutoff
store growth cannot rewrite a semantic T0 identity.

Coverage is always `BOUNDED_OBSERVED_UNIVERSE`; external all-Polymarket completeness is
`UNPROVEN`. Complete triage means complete triage of this exact frozen observed universe only.

## Freshness and gaps

Required metadata is market status plus nonempty unique tokens and outcomes. Required metadata
conflict/missing or stale/invalid metadata defers the market. Missing optional condition, category,
or resolution date creates a capture gap. Missing/stale/conflicted rule, referenced source, or
book evidence also creates a capture gap without globally making an otherwise eligible market
ineligible. Missing evidence is never fabricated from a current external API.

## Material change

Comparisons require the same policy and strictly increasing cutoffs. A record-version change alone
is never material. The closed hard classes cover status, condition, token/outcome sets,
resolution-rule/source sets, tick size, and minimum order size. Closed soft classes cover last
price, midpoint, spread, and relative top-depth changes at the policy's inclusive `>=` Decimal
threshold. Question and category changes are review-only and cannot reopen research.

There is at most one `MaterialChangeEvent` per market and universe pair. Per-token classes compare
only shared tokens and retain affected token ids. Resolution-rule hash changes compare shared
sources; source additions/removals are separately recorded. Missing/noncomparable evidence is an
explicit diagnostic, never an invented change.

Current-only markets are `NEWLY_OBSERVED_LOCALLY` only when an exact prior universe was supplied.
Prior-only ids appear only in the queue's `prior_only_market_ids` with no current triage or reopen.
All comparison-derived identities bind `comparison_prior_universe_id`.

## Alpha-memory clocks and matching

`HISTORICAL_REPLAY` fixes posture to `HISTORICAL_AVAILABILITY_UNPROVEN`, forbids loading or hashing
today's Alpha registry, stores a null head and empty matches, and is valid only for replaying market
evidence. Historical Alpha memory remains unavailable.

`CURRENT_BUILD_ANALYSIS` fixes posture to `CURRENT_REGISTRY_BUILD_TIME_ONLY`, requires a verified
current registry, and binds its head and exact matches. It is a current/prospective allocation view,
not proof that those Alpha records existed at the market cutoff and not a canonical historical
selection replay. `ResearchEpisode.research_as_of` never proves registry availability.

Matches use exact full-string equality against canonical PIT `market:`, `event:`, and `token:` ids.
No raw-id stripping, invented `market_id:` wrappers, prose/fuzzy/model matching, or independent
condition namespace is allowed.

Side12 explicitly ratified these direct canonical PIT namespaces; no outer wrapper namespace is
required or permitted in v1.

## Reopen, priority, and coverage

Reopen decisioning exists only in current-build mode. Episodes are grouped by exact
`(candidate_id, hypothesis_family_id)` and leaves are determined within each independent lineage.
A unique, unambiguous governing latest leaf in `WATCH_FOR_CHANGE` or `RESEARCH_STALE` plus a
reopen-material change is eligible. Multiple governing groups, an ambiguous group, or any matched
candidate without a usable group fails closed to `REOPEN_REVIEW_REQUIRED`; no lineage may borrow
another candidate's leaf. Supportive/already-reopened states do
not automatically reopen; ambiguous, missing, falsified, exhausted, uneconomic, no-edge, or
insufficient-data bases require review as specified by the closed decision table. A reopen decision
means only that research should be reconsidered; it writes no ALPHA-01 record.

Priority is a closed lexicographic control, not a score:

`(priority class ascending, hard-change count descending, soft-change count descending, readiness
ascending, market id ascending)`.

The closed priority classes are material reopen, existing follow-up, new research, market-evidence
only, existing other, deferred capture refresh, and ineligible. The legacy float score and threshold
have no authority here.

Coverage uses the 14-cell versioned taxonomy. Only exact matched episode lanes and controlled
producer type apply the declared mapping. Supported outranks partial. Unmapped cells remain
unknown; negative research does not become a category blacklist.

## Allocation, skips, and capture data

The pipeline is one-way:

1. derive one pre-allocation basis for every current observed market;
2. allocate over the complete canonical basis set;
3. materialize exactly one final triage decision per current market;
4. build the queue as an index of those immutable decisions.

Core reserves exploration and audit slots first and obeys the category cap. Exploration recomputes
its under-coverage/category key after every choice. Audit ordering is SHA-256 over policy id,
universe id, seed, and market id, fixed before outcomes. Reserved capacity is never backfilled in
v1; Side12 explicitly ratified this no-backfill rule. Unused reservations retain closed exhaustion
reasons. Every current market is selected,
deferred, skipped-ineligible, or skipped-capacity—none disappears.

Capture request types are metadata refresh, order book, resolution rule, and source snapshot. They
contain only pre-allocation inputs and never final triage/queue ids or allocation outcomes. There is
no automatic v1 fee request because no canonical fee-state trigger exists.

## Discovery registry

The separate explicit-path SQLite registry uses format `s10-alpha-discovery-registry`, application
id `1464877426`, user version 1, DELETE journaling, FULL synchronous mode, and foreign keys on. Its
ordered kinds are policy, universe, material change, triage, and queue. It provides deterministic
caller-order-independent atomic append, idempotent identical reappend, unique content identity,
per-entry SHA-256 chaining, read-only verified load, and update/delete triggers. It never initializes
implicitly; a bad record or reference rolls back the whole batch.

## Residual limits and successor

This v1 does not prove exhaustive external market acquisition, tune empirical thresholds, run a
campaign/scheduler, learn from outcomes, qualify candidates, calculate economics, or create paper
or live execution authority. After separate review and merge, the next gate is `S10-GATE-AF1`.
`S10-ALPHA-03`, `S10-ALPHA-04`, qualification, economics, paper, Gate C, and live remain separately
gated.

## S10-GATE-AF1 benchmark posture

S10-GATE-AF1 consumes the frozen universe, complete triage/skip accounting, and queue identity
under `HISTORICAL_REPLAY` with `HISTORICAL_AVAILABILITY_UNPROVEN` Alpha memory. The benchmark does
not manufacture an Alpha registry head and does not reinterpret discovery priority as expected
return, qualification, or strategy authority.
