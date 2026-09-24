# Polymarket Point-In-Time Public Population Contract (WP164)

## Label and posture

- Label: `POLYMARKET_REAL_PUBLIC_INITIAL_POINT_IN_TIME_POPULATION`
- Posture: `EXPLICIT_NETWORK_GET_ONLY_BOUNDED_INITIAL_SEED_NO_TRADING_AUTHORITY`
- Source module:
  `src/data_layer/point_in_time_market_research/polymarket_public_population.py`
- Package class: `DATA_LAYER_PUBLIC_POPULATION`; size class L; risk level 1;
  capital at risk USD 0.

WP164 is the first bounded real/public Polymarket population into the merged
point-in-time research foundation. It coordinates existing merged layers; it does
not redesign them.

WP164A is a bounded compatibility repair to this existing coordinator. It adds
closed typed batch and build-failure diagnostics, truthful completed-stage
counts, and strict population-local Gamma lifecycle normalization. It does not
add a client, endpoint, retry, scheduler, credential, or trading authority.

## Official public endpoint basis

Re-verified against current official Polymarket documentation at implementation
time (drafting-time basis 2026-08):

- Gamma API base `https://gamma-api.polymarket.com`; `GET /markets` is a public,
  no-authentication market-list read.
- CLOB API base `https://clob.polymarket.com`; `GET /book?token_id=...` is a
  public, no-authentication single-token order-book read.
- Gamma returns `clobTokenIds`, `outcomes`, and `outcomePrices` as JSON-encoded
  strings and uses the integer `id` field as the market identifier.

If the official public endpoint semantics change materially before execution, the
correct response is an explicit architecture stop, not a silent scope adaptation.
WP164 does not touch the Data API, positions, wallet/user activity, authenticated
CLOB endpoints, `POST /books`, or any trading endpoint.

## GET-only, no-authentication boundary

WP164 performs network reads only through the existing GET-only public client
(`PolymarketPublicClient`), constructed by default with
`allow_unverified_endpoints=False`. The only client methods it may call are
`get_markets` and `get_order_book_snapshot`. It never imports `urllib`,
`requests`, `httpx`, `aiohttp`, `websockets`, `socket`, `subprocess`,
`os.environ`, a credential/wallet module, or an order/execution module. It handles
no credentials and performs no authenticated request.

## Local rate-limit guard remains the runtime authority

The existing conservative local polling policy (`default_polling_policy()` plus
`validate_polling_policy()`) and `RateLimitGuard` remain the sole runtime request
authority. WP164 does not increase, redesign, or reconcile the repo's local
budgets against the venue's published limits (that reconciliation is deferred as
`WP164-D006`). The guard is consulted immediately before the single possible Gamma
request and before every CLOB book request; a guard denial makes no call and, for
a book denial, rejects the whole run before any persistence.

The coordinator never fabricates elapsed guard time. When no `now_provider` is
injected the guard uses its native monotonic clock, so back-to-back requests
inside the conservative minimum interval are denied and the run is rejected;
`order_books_limit` is therefore only an upper bound, not a guarantee. A denial is
never followed by a sleep, wait, backoff, or retry. `network_used` is truthful: it
is `False` until the Gamma GET is actually attempted (so a guard denial before the
first GET reports no network use) and `True` from that GET onward.

## Initial-seed-only design and the empty-store requirement

WP164 performs an INITIAL SEED only. A new network population requires the WP163
record store to be empty. If the record store is non-empty, the network-capable
function makes zero network calls and rejects with
`POPULATION_RECORD_STORE_NOT_EMPTY`.

The seed records are fixed as classification `PRIMARY_ASSERTION`, lifecycle
`NORMALIZED_ACCEPTED`, empty lineage parents, and no supersedes. WP164 never
invents uncommitted cross-run lineage/provenance; incremental/repeated capture
with committed external-parent lineage is a separately gated successor
(`WP164-D001`).

## Public API

- Constants: `POLYMARKET_PUBLIC_POPULATION_LABEL`,
  `POLYMARKET_PUBLIC_POPULATION_POSTURE`,
  `POLYMARKET_PUBLIC_POPULATION_STATUSES` (six ordered statuses),
  `POLYMARKET_PUBLIC_POPULATION_ERROR_CODES` (fourteen ordered codes).
- Frozen dataclasses: `PolymarketPublicPopulationConfig`,
  `PolymarketPublicPopulationResult`.
- Functions: `populate_initial_polymarket_public_data(...)` and
  `recover_initial_polymarket_public_registration(...)`.

`PolymarketPublicPopulationConfig` fixes `markets_limit` (0..25, default 3),
`order_books_limit` (0..20, default 0), and `allow_network` (default `False`). No
path, URL, header, endpoint choice, or HTTP method is caller-configurable. The
optional `client`, `guard`, `now_provider`, and `utcnow_provider` arguments are
testing/injection seams only. Schema v1 defines no warning codes, so
`warning_codes` is always empty; every result fixes `advisory_only=True` and
`no_execution_authority=True`.

The WP164A result extension appends the following fields with fail-closed
null/empty defaults: `batch_is_valid`, `batch_status`, `batch_error_codes`,
`batch_warning_codes`, `batch_accepted_record_version_ids`,
`batch_exact_duplicate_record_version_ids`,
`batch_quarantined_record_version_ids`, and `canonical_batch_sha256`. After a
completed `validate_record_batch` call, these fields preserve the complete typed
`PointInTimeBatchValidationResult`, including on `POPULATION_BATCH_INVALID` and
when WP156 is valid but WP164's stricter one-accepted-id-per-input invariant
rejects the population. They contain no raw payload, URL, path, exception text,
or repr. If batch validation never completes, only the defaults are returned.

The build-diagnostic extension appends six more fail-closed fields:
`build_failure_observation_kind`, `build_status`, `build_error_codes`,
`build_warning_codes`, `build_quarantine_id`, and
`build_input_fingerprint_sha256`. A completed invalid
`PointInTimeBuildResult` keeps the outer `POPULATION_BUILD_FAILED` code while
copying only those closed WP156 fields. Observation kind is exactly
`MARKET_METADATA` or `ORDER_BOOK`. No input record, canonical payload, question,
market/token identifier, exception, URL, path, or provider content crosses this
diagnostic boundary. Paths that do not invoke the builder and successful
populations retain null/empty defaults.

## Dry-run posture

With the default `allow_network=False`, after verifying valid stores, an empty
record store, and a valid polling policy, the coordinator returns a valid
`POPULATION_DRY_RUN` result with `network_used=False`, zero fetched/built/inserted
counts, and no store write and no client method call. A dry run is a valid safety
result, not an error.

## Gamma normalization

Each parsed Gamma market becomes one WP156 `MARKET_METADATA` observation:

- `platform_id = platform:polymarket`; `market_id = market:polymarket:<gamma id>`;
  `event_id = event:polymarket:<condition id>` when a condition id is present,
  otherwise `event:polymarket:market-<gamma id>`;
  `source_id = source:polymarket:gamma-markets`; `token_id = None`; content-addressed
  `source_snapshot_id` and `source_assertion_id`.
- Canonical payload: `question_text`, `market_status`, ordered `outcome_labels`,
  `condition_id`, ordered `token_ids`, `resolution_date` (string or null),
  `category` (string or null), and sorted `raw_field_names`. The full raw Gamma
  object is not stored and no float value enters the canonical payload.

Every selected market is parsed through the public `parse_market_summary`; a
malformed selected market or a duplicate market id rejects the whole run rather
than being silently skipped. `markets_limit == 0` in a network run is rejected as
`POPULATION_INPUT_INVALID` rather than registering an empty seed.

WP164A derives canonical `market_status` locally from the raw Gamma lifecycle
booleans. If `closed is True`, the status is exactly `closed`. Otherwise, only
`active is True` together with `closed is False` produces exactly `open`. Every
other type or lifecycle combination rejects with `POPULATION_RESPONSE_INVALID`.
There is no fallback and no inference from price, liquidity, token/book presence,
accepting-orders data, or outcome. `PolymarketPublicClient` and downstream Alpha
eligible statuses remain unchanged.

## Truthful completed-stage counts

WP164A initializes bounded counters before network population and advances them
only after completed facts: fetched markets immediately after a successful Gamma
list response, each fetched book immediately after its successful CLOB response
and before book normalization, each built record immediately after its builder
returns, and inserted records only after the append commits. Any later rejection
preserves these known values and leaves unreached stages at zero. Counts never
stand in for batch validity, persistence, or registration evidence.

On a build rejection, the result also preserves the already-captured
`captured_at_utc` and already-derived `snapshot_id`. A metadata failure before
the first successful build reports zero built records; a later metadata failure
reports the exact successful prefix; and an order-book failure after 25 metadata
builds reports 25. No partial batch is persisted.

## Optional CLOB normalization

Each selected token becomes one WP156 `ORDER_BOOK` observation whose parent is the
unique Gamma market that owns the token. Token IDs come only from successfully
parsed Gamma markets; any token that maps to more than one market rejects the run.
Token selection is deterministic: markets sorted by namespaced market id, token
order preserved within each market, exact duplicate token IDs removed, first
`bounded_order_books_limit` taken.

- Identifiers: parent `event_id`/`market_id`;
  `token_id = token:polymarket:<raw token id>`;
  `source_id = source:polymarket:clob-book`; content-addressed source ids.
- Canonical payload: ordered `bids`/`asks` levels each with exactly `price` and
  `size` string fields, `tick_size`, `minimum_order_size`, and the bounded extras
  `clob_timestamp`, `book_hash`, `last_trade_price` (each string or null), and
  sorted `raw_field_names`. `asset_id`, when present, must equal the requested raw
  token id. A malformed requested book rejects the entire run.

## Deterministic run identities and record order

After all requested network reads succeed, a single UTC timestamp is captured
(canonical `Z`, at most six fractional digits) and used as `observed_time`,
`ingestion_time`, and manifest `effective_time` for every record. Deterministic
run identities are content-addressed from the captured timestamp, the ordered
normalized Gamma and CLOB payload hashes, and the config parameter set and
normalizer/validator versions:

- `snapshot_id = "snapshot:sha256:" + SHA256(canonical preimage)`
- `ingestion_batch_id = "ingest:sha256:" + SHA256(canonical preimage)`

No random UUID is used and API response order never controls dataset identity. The
final record order is Gamma `MARKET_METADATA` sorted by namespaced `market_id`,
then `ORDER_BOOK` sorted by `market_id` then `token_id`.

For identity derivation only, values already within WP156 bounds retain the
exact existing canonical bytes. If an otherwise normalized payload contains an
oversized sequence, deterministic JSON-compatible identity bytes are derived so
the authoritative WP156 builder—not the preliminary identity step—returns the
closed `PAYLOAD_SEQUENCE_LIMIT_EXCEEDED` result. This does not weaken
`canonical_json_bytes`, validate or reshape the payload, or grant persistence.

## WP156 validation before persistence

Every record is built only through the public `build_market_observation`. Before
any persistence call the complete batch is validated with `validate_record_batch`
and no external known parents; the batch must be valid, carry no quarantine, have
accepted ids equal to and matching the built records uniquely, and stay within 256
records.

## Records-first, reference-second ordering

Records are persisted through WP163 `append_point_in_time_records` (requiring
`RECORD_STORE_APPEND_COMMITTED` and inserted ids exactly equal to the validated
built ids) before the exact validated batch is registered through WP162
`persist_validated_record_batch_snapshot` into WP161. This fail-safe ordering is
locked: records first, reference second.

- A record-append failure never registers a manifest reference and returns
  `POPULATION_REJECTED` / `POPULATION_RECORD_APPEND_FAILED`, copying only closed
  WP163 error codes.
- After a committed append, EVERY registration failure mode — an invalid adapter
  result, a raised exception, or a malformed result — returns
  `POPULATION_RECORDS_PERSISTED_REGISTRATION_FAILED` with `recovery_required=True`,
  the committed `record_store_status` and counts preserved, and null
  reference/entry IDs. It never deletes the immutable WP163 records, never
  fabricates cross-store rollback, and never echoes an exception. A raised
  registration exception is contained into the same recoverable partial result, so
  committed records can never be stranded under a generic unrecoverable rejection.
- The adapter call and the inspection of its returned object are one exception
  boundary that extracts only already-validated immutable scalars — the status and
  the reference/entry IDs — from an exact `DatasetPersistenceAdapterResult` with a
  genuine `DatasetSnapshotReference`/`ManifestEntry`; the raw adapter object is
  never dereferenced afterward. `registration_error_codes` carries only exact
  members of the closed WP162 `DATASET_PERSISTENCE_ADAPTER_ERROR_CODES` vocabulary;
  any arbitrary string, unknown code, hostile iterable, or malformed shape yields
  an empty tuple, so no arbitrary string, URL, or payload ever crosses the boundary.

WP164 makes no cross-file atomicity claim; a true cross-store coordinator is
deferred (`WP164-D007`, tracking `WP163-D002`).

## Offline registration recovery

`recover_initial_polymarket_public_registration` performs zero network activity,
constructs no client, and never writes records. It re-registers a store proven to
be exactly one valid unregistered/retryable WP164 seed: 1..45 total records
(at most 25 Gamma metadata plus at most 20 books), every record an exact
`MarketObservationRecord` on `platform:polymarket` with a WP164 source id matching
its observation kind, `PRIMARY_ASSERTION`/`NORMALIZED_ACCEPTED`, no lineage parents
or supersedes, and config-matching parameter/normalizer/validator versions, all
sharing exactly one `snapshot_id`, one `ingestion_batch_id`, and one
`observed_time == ingestion_time`.

Because a caller can craft WP156-valid records that merely reuse the WP164 source
IDs and share arbitrary snapshot/batch IDs, recovery additionally re-proves the
WP164 construction invariants before it trusts the store: at least one Gamma
`MARKET_METADATA` record (a book-only store is rejected); the exact Gamma and CLOB
canonical payload key sets; the exact Gamma and CLOB identifier derivations
(`market:polymarket:`/`event:polymarket:`/`token:polymarket:` and `token_id=None`
for metadata); each token owned by exactly one Gamma market's `token_ids` with the
book parented to that market; the content-addressed `source_snapshot_id` and
`source_assertion_id` re-derived from the stored snapshot and payload; and the
content-addressed `snapshot_id`/`ingestion_batch_id` recomputed from the unique
captured time, the ordered payload hashes, and the config, requiring an exact
match. Only then does it re-sort into WP164 order, re-run `validate_record_batch`,
and re-register through WP162 using the unique ingestion time as `effective_time`.
A forged or mismatched store fails closed as `POPULATION_RECOVERY_INVALID`.

## No raw-response persistence, no old JSONL write path

WP164 persists only normalized WP156 observations; it never stores raw
HTTP/source-response bytes (deferred as `WP164-D002`). WP164 does not write WP10
JSONL snapshots and does not import or call `snapshot_writer`, `write_snapshots`,
`capture_market_snapshots`, or any `local_data/` path. The durable authority is the
WP163 SQLite record store plus the WP161 manifest store. The historical WP10 JSONL
snapshot infrastructure remains historical and is not a WP164 write authority.

## No scheduler, retry, or incremental authority

WP164 adds no scheduler, daemon, cron, background loop, retry, backoff, or sleep.
It contains ordinary `Exception` around every policy, guard, client, parser,
normalization, builder, validation, store, registration, and clock call; it never
catches `BaseException` and never echoes a path, URL, raw response, question text,
source payload, record repr, exception text, or credential.

## Successor boundary

Repeated/incremental public capture into a non-empty store, automatic
`SOURCE_REVISION`/`EXACT_DUPLICATE` cross-run lineage, external committed parent
context, wider keyset/pagination active-market coverage, order-book depth/history
scaling, historical trades / Data API ingestion, official rate-limit reconciliation,
and a cross-file transaction coordinator or stronger recovery ledger are all
separately gated successors (`WP164-D001` through `WP164-D007`). This document does
not amend the WP163 record-store contract, which remains historically correct that
WP163 itself had no real/public population authority.
