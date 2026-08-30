# Polymarket Incremental Point-In-Time Population Contract (WP165)

## Label and posture

- Label: `POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION`
- Posture:
  `MANUAL_GET_ONLY_CUMULATIVE_256_RECORD_CROSS_RUN_LINEAGE_NO_TRADING_AUTHORITY`
- Source module:
  `src/data_layer/point_in_time_market_research/polymarket_incremental_population.py`
- Package class: `DATA_LAYER_PUBLIC_POPULATION`; size class L; risk level 1;
  capital at risk USD 0.

WP165 is the first safe REPEATED real/public Polymarket capture after the WP164
initial seed. It captures into an already-populated and already-registered WP163
record store and commits deterministic cross-run lineage. It coordinates existing
merged layers; it does not redesign them and it does not amend the WP164 or WP163
contracts.

## Cumulative-in-one-reference technique and why WP162-D004 stays open

WP162-D004 remains OPEN: the current `DatasetSnapshotReference` schema does not
commit an external known-parent context field. WP165 MUST NOT silently pass
uncommitted external `known_parent_record_ids` through WP162. Instead every
cross-run parent is a record already committed in the same WP163 store, so the
cumulative validated batch — the prior registered records plus the new lineage
records — is validated together through `validate_record_batch` with NO external
known parents and registered as one WP160 `DatasetSnapshotReference`.

Because every parent is inside the same registered dataset snapshot, no schema
migration is needed and every cross-run parent remains committed. The deliberate
tradeoff is that the cumulative total is bounded to 256 records, since WP156 and
WP162 batch validation is capped at 256. The scalable external-parent/reference
schema extension beyond 256 is a separately gated successor (`WP165-D001`).

## Baseline convergence proof before any network

Before any network activity WP165 verifies a valid, nonempty, bounded WP163 record
store whose records are all supported WP164-shaped observations
(`platform:polymarket`, Gamma `MARKET_METADATA` or CLOB `ORDER_BOOK`) carrying only
the three cross-run lineage classifications, with config-matching provenance.

It then loads the WP161 manifest, requires a valid nonempty chain, takes the highest
`sequence_number` entry, and requires it to be a
`REGISTER_DATASET_SNAPSHOT_REFERENCE` / `ACTIVE_REFERENCE` / `INITIAL_REGISTRATION`
entry whose `DatasetSnapshotReference` exists exactly once with derivation mode
`VALIDATED_RECORD_BATCH`, no review conflicts, and config-matching
validator/parameter versions. It then proves exact convergence:

- `set(reference.ordinary_record_version_ids) == set(store record ids)`;
- `validate_record_batch(all store records)` with no known parents is valid, its
  accepted ids equal the reference ordinary ids in canonical accepted order, and
  its batch hash equals the reference `validated_batch_sha256`;
- `materialize_dataset_snapshot_reference` succeeds with
  `VALIDATED_BATCH_RECOMPUTED`.

Any divergence yields zero network. If the store is a strict superset of the
registered ids, WP165 returns `INCREMENTAL_BASELINE_UNREGISTERED` with
`recovery_required=True` — exactly the shape a committed-but-unregistered orphan run
leaves behind.

## Public API

- Constants: `POLYMARKET_INCREMENTAL_POPULATION_LABEL`,
  `POLYMARKET_INCREMENTAL_POPULATION_POSTURE`,
  `POLYMARKET_INCREMENTAL_POPULATION_STATUSES` (six ordered statuses),
  `POLYMARKET_INCREMENTAL_POPULATION_ERROR_CODES` (eighteen ordered codes).
- Frozen dataclass: `PolymarketIncrementalPopulationResult`.
- Functions: `capture_incremental_polymarket_public_data(...)` and
  `recover_incremental_polymarket_public_registration(...)`.

WP165 reuses the exact WP164 `PolymarketPublicPopulationConfig`; it defines no
second config. The optional `client`, `guard`, `now_provider`, and
`utcnow_provider` arguments are testing/injection seams only. Schema v1 defines no
warning codes, so `warning_codes` is always empty; every result fixes
`advisory_only=True` and `no_execution_authority=True`. The package export inventory
grew by exactly 7 (four constants, one result dataclass, two functions) appended
after the WP164 export block.

## Default network posture and dry run

Default `allow_network=False`. After the full baseline convergence, policy, and
worst-case capacity verification, the coordinator returns a valid
`INCREMENTAL_DRY_RUN` result with `network_used=False`, no store write and no client
method call, and `prior_registered_record_count == cumulative_record_count` equal to
the current store count. A dry run is a valid safety result, not an error.

## GET-only capture boundary reused from WP164

When `allow_network=True`, WP165 reuses the WP164 bounded GET-only Gamma
`GET /markets` and optional CLOB `GET /book` capture boundary through the existing
GET-only public client, and the existing conservative local
`default_polling_policy()`/`RateLimitGuard` remains the sole runtime request
authority consulted before every request. It never fabricates elapsed guard time and
adds no scheduler, retry, backoff, or sleep. `network_used` is truthful: it is
`False` until the Gamma GET is actually attempted. A guard denial makes no call, and
a book denial rejects the whole run before any persistence. It never touches the
Data API, `POST /books`, keyset/pagination, authenticated endpoints, or any trading
method.

## Hard cumulative capacity

The authoritative cumulative cap is 256 records. Before any client call WP165
computes the worst case `existing + bounded_markets_limit + bounded_order_books_limit`
and, if it exceeds 256, returns `INCREMENTAL_CAPACITY_EXCEEDED` before any network.
There is no pruning, deletion, compaction, or partial registration.

## Deterministic WP165 run identity

WP165 does NOT reuse the WP164 `_run_identities`, because that commits the
initial-seed label. After the reads succeed a single captured UTC time and the
ordered Gamma/CLOB payload hashes derive deterministic content-addressed
`snapshot:sha256:` and `ingest:sha256:` identities whose canonical preimage commits
the `POLYMARKET_BOUNDED_CUMULATIVE_INCREMENTAL_POINT_IN_TIME_POPULATION` label, the
captured time, the ordered payload hashes, and the config identity. No random UUID
is used and API response order never controls dataset identity; every new record
shares the snapshot/batch/observed/ingestion time of that invocation.

## Lineage classification

Each new capture becomes one temporary current-capture `PRIMARY_ASSERTION`
candidate, built through the WP164 normalization/build helpers with the WP165
snapshot/batch identities. The latest prior record for the same WP156 entity —
identity `(platform, event, market, token, source, observation_kind)` — is chosen by
ingestion time, then observed time, then `record_version_id`. Each candidate is
classified deterministically and the FINAL record is rebuilt through the public
`build_market_observation`, replacing only classification, lifecycle, lineage
parents, and supersedes:

- `PRIMARY_ASSERTION`: entity never seen; parents empty, no supersedes.
- `EXACT_DUPLICATE`: identical canonical payload as the latest prior; parent is the
  latest prior, no supersedes.
- `SOURCE_REVISION`: changed canonical payload; parent and supersedes are the latest
  prior.

WP165 never writes `SEMANTIC_DUPLICATE`, `PROJECT_CORRECTION`, `SOURCE_RETRACTION`,
or `CONFLICT`. The three classification counts sum to `new_record_count`.

## Identity drift is rejected

WP165 never silently forks identity. It rejects with `INCREMENTAL_IDENTITY_DRIFT`
when the same Gamma market/source/kind was previously seen under a different
`event_id`, when the same book market/token/source/kind was previously seen under a
different `event_id`, or when the same raw token was previously associated with a
different `market_id`.

## Complete cumulative validation, append-new, register-cumulative

The complete cumulative record set (prior registered records plus new lineage
records) is validated through `validate_record_batch` with NO
`known_parent_record_ids` and must be fully valid with no quarantine and all new ids
accepted; this proves every parent is internally present, no cycles, each
`SOURCE_REVISION` shares its parent entity with revision ingestion at or after the
parent and supersedes in lineage, and each `EXACT_DUPLICATE` shares payload and
entity with its parent.

ONLY the new records are appended through WP163 `append_point_in_time_records`
(requiring `RECORD_STORE_APPEND_COMMITTED` and inserted ids exactly the new ids).
The COMPLETE cumulative dataset is then registered through the unchanged WP162
`persist_validated_record_batch_snapshot` into WP161, with `effective_time` set to
the captured time. This fail-safe ordering is locked: new records first, cumulative
reference second. The new reference contains the exact prior-plus-new accepted ids,
and the prior reference remains immutable.

## Registration failure and offline recovery

A record-append failure never registers a reference and returns
`INCREMENTAL_REJECTED` / `INCREMENTAL_RECORD_APPEND_FAILED`, copying only closed
WP163 record-store error codes. After a committed append, EVERY registration failure
mode — an invalid adapter result, a raised registration exception is contained, or a
malformed result — returns
`INCREMENTAL_RECORDS_PERSISTED_REGISTRATION_FAILED` with `recovery_required=True`,
the committed `record_store_status` and truthful counts preserved, and null
reference/entry ids. It never deletes the immutable WP163 records. The adapter call
and the inspection of its returned object are one exception boundary that extracts
only already-validated immutable scalars; the raw adapter object is never
dereferenced afterward. `registration_error_codes` carries only exact members of the
closed WP162 `DATASET_PERSISTENCE_ADAPTER_ERROR_CODES` vocabulary, so no arbitrary
string, URL, or payload ever crosses the boundary.

`recover_incremental_polymarket_public_registration` performs zero network activity,
constructs no client, and never writes records. When the store already converges
with the latest registered reference it is a valid `INCREMENTAL_ALREADY_REGISTERED`
no-op. When the registered ids are a strict subset of the store, the orphan suffix
must be exactly one genuine WP165 incremental run: 1..45 orphan records, total store
at most 256, all supported observations sharing exactly one snapshot id, one
ingestion batch id, and one `observed_time == ingestion_time`, with config-matching
provenance. The WP165 run identity is recomputed from only the orphan payload hashes
and must equal the single stored snapshot/batch ids, and every orphan is
reconstructed from only the registered prior state through the exact WP165 lineage
and required to be equal object-for-object. Only then does it re-run
`validate_record_batch` over the complete store and re-register through WP162 using
the orphan ingestion time as `effective_time`. A forged orphan, a wrong
parent/supersedes, two distinct orphan batches, identity drift, or any non-WP165
classification fails closed as `INCREMENTAL_RECOVERY_INVALID`. WP165 keeps no queue
of failed runs.

## No raw bytes, keyset, scheduler, authentication, or trading

WP165 persists only normalized WP156 observations; it never stores raw
HTTP/source-response bytes. It never imports a direct network library, credential or
wallet module, or order/execution module, and it never catches `BaseException`. It
never echoes a path, URL, raw response, question text, source payload, record repr,
exception text, or credential. It adds no keyset/pagination, no Data API, no
scheduler/daemon/cron/background loop, no retry/backoff/sleep, no authenticated
endpoint, and no order/trading/execution authority.

It imports ONLY the allowlisted sibling-private WP164 helpers and constants
(`_PLATFORM_ID`, `_GAMMA_SOURCE_ID`, `_CLOB_SOURCE_ID`, `_GAMMA_ENDPOINT_KEY`,
`_CLOB_ENDPOINT_KEY`, `_bounded_limits`, `_build_guard`, `_consult_guard`,
`_get_markets`, `_parse_markets`, `_select_tokens`, `_get_order_book`,
`_normalize_order_book`, `_capture_time`, `_build_gamma_record`,
`_build_order_book_record`), plus the WP164 `PolymarketPublicPopulationConfig`. It
imports none of the WP164 persistence/recovery/result helpers or
`_run_network_population`.

## Successor boundary

The scalable external-parent/reference-schema extension beyond the cumulative 256,
Gamma keyset/pagination across a materially broader active-market universe, store
growth/partitioning, scheduled recurring collection, raw source/wire preservation,
historical public trades / Data API ingestion, and an analytical columnar/query
layer are all separately gated successors (`WP165-D001` through `WP165-D007`).
`WP162-D004`, `WP164-D003`, `WP165-D001`, and `WP165-D002` remain OPEN and are the
intended scope of WP166. This document does not amend the WP164 initial-seed contract
or the WP163 record-store contract.
