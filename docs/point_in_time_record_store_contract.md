# Point-In-Time Durable Record Store Contract

This document is the canonical contract for the bounded, local, offline,
standard-library-only durable store for the immutable WP156/WP157 point-in-time
research record objects, implemented in
`src/data_layer/point_in_time_market_research/record_store.py` (WP163).

## Label and posture

- Label: `POINT_IN_TIME_DURABLE_RECORD_STORE`.
- Posture:
  `BOUNDED_LOCAL_SQLITE_APPEND_ONLY_RECORD_PERSISTENCE_AND_MATERIALIZATION`.
- Store format id: `point-in-time-record-store`.
- Schema version and SQLite `user_version`: `1`.

The store is the first durable substrate for the actual immutable record objects
named by WP160 `DatasetSnapshotReference` ids. WP161 remains the manifest and
reference store; WP163 is the distinct actual-record store. The two are separate
local SQLite files and there is no cross-file atomic coordinator.

## Locked SQLite durability rationale

A second explicit local SQLite file is the canonical record source of truth. This
adds no new dependency, reuses the transaction/rollback semantics already proven
by WP161, fits append-only immutable rows to the deterministic architecture, and
keeps the exact record payloads and indexing metadata in one bounded file. Future
analytical Parquet materialization would be derived from this canonical store; it
is not adopted here. The store does not adopt PyArrow, Parquet-as-canonical,
DuckDB, Polars, pandas, SQLAlchemy, or any new dependency.

## Public API

Public constants: `POINT_IN_TIME_RECORD_STORE_LABEL`,
`POINT_IN_TIME_RECORD_STORE_POSTURE`, `POINT_IN_TIME_RECORD_STORE_FORMAT_ID`,
`POINT_IN_TIME_RECORD_STORE_SCHEMA_VERSION`,
`POINT_IN_TIME_RECORD_STORE_STATUSES` (seven ordered),
`POINT_IN_TIME_RECORD_STORE_ERROR_CODES` (eighteen ordered), and
`DATASET_MATERIALIZATION_VERIFICATION_MODES` (`VALIDATED_BATCH_RECOMPUTED`,
`AS_OF_REFERENCE_IDS_RESOLVED`). Schema version 1 defines no warning codes; every
result reports an empty warning tuple.

Public frozen dataclasses: `PointInTimeRecordStoreSnapshot`,
`PointInTimeRecordStoreResult`, `DatasetSnapshotMaterializationResult`.

Public functions:

- `initialize_point_in_time_record_store(path)` — create the exact schema on a
  new or pristine file, or verify an existing compatible store.
- `append_point_in_time_records(path, records)` — atomically append a bounded
  batch of already-built immutable records with deterministic idempotency.
- `load_and_verify_point_in_time_record_store(path)` — read one existing store in
  SQLite read-only mode and fully verify it.
- `materialize_dataset_snapshot_reference(path, reference)` — resolve a valid
  WP160 `DatasetSnapshotReference` into the exact durable record objects it names.

## Schema and indexes

Exactly two application tables:

- `record_store_meta(singleton=1, format_id='point-in-time-record-store',
  schema_version=1)`.
- `records(record_version_id PRIMARY KEY, record_type, record_family,
  classification, human_review_required, observed_time, ingestion_time,
  event_time, parameter_set_id, validator_version, observation_kind, platform_id,
  event_id, market_id, token_id, source_id, resolution_source_id, payload_json,
  payload_sha256)` with CHECK constraints binding `record_type`, `record_family`,
  and `human_review_required`.

Exactly five explicit indexes:
`idx_pit_records_ingestion_time`, `idx_pit_records_observed_time`,
`idx_pit_records_event_time`, `idx_pit_records_market_id`, and
`idx_pit_records_source_id`. There are no views or triggers, and no migration.

## Bounds

- Maximum records per append call: 256.
- Maximum records in one store: 4096.
- Maximum canonical full-record payload per row: 131072 UTF-8 bytes.
- Maximum total canonical full-record payload bytes in one store: 134217728
  (128 MiB).
- No unbounded retry or recursion.

## Canonical full-record payload

The complete immutable record object is persisted, not only the canonical market
payload. The canonical stored mapping is
`{"record_type": <exact class name>, "envelope": {every envelope field},
<every top-level record field except "envelope">}`, serialized with the public
`canonical_json_bytes` and digested with the public `sha256_hex`. Strict decode
rejects duplicate keys, NaN/Infinity, a non-object top level, unknown or missing
structural keys, a noncanonical representation, an oversized payload, and any hash
mismatch. Reconstruction rebuilds the exact envelope and record dataclass,
converting only schema-defined tuple fields from JSON arrays back to tuples. The
indexed columns are the exact projection of the reconstructed object and must
match it exactly.

## Ordinary versus review-conflict integrity

An ordinary (non-CONFLICT) record self-validates through the public
`validate_record_batch` with its own lineage parents supplied as known external
parents; it must be valid and reproduce exactly its committed record-version id. A
CONFLICT record self-validates through the public
`revalidate_review_conflict_record`, is always human-review-required, and never
becomes an ordinary authority.

## Complete lineage

On append (the complete proposed store) and on load (the complete reconstructed
store), the store validates unique ids, parent existence, no duplicate or self
parent, no cycle, that an ordinary record never takes a CONFLICT record as an
authoritative parent, that a present supersedes id exists, is a lineage parent,
and resolves to a non-CONFLICT record, correction identity and non-decreasing
ingestion-time rules for revisions/corrections/retractions, and exact/semantic
duplicate comparison against a non-CONFLICT reference parent. Failures are bounded
`RECORD_STORE_LINEAGE_INVALID` or `RECORD_STORE_AUTHORITY_VIOLATION`.

## Append-only and idempotency

Appends only INSERT new rows; there is no production UPDATE or DELETE of persisted
records. An exact retry of an already-stored equal record is idempotent; a same-id
record that is not exactly equal is a `RECORD_STORE_DUPLICATE_CONFLICT`; equal
duplicates within one input collapse. Inserted and idempotent id tuples are unique
and lexicographically sorted. A new insert yields `RECORD_STORE_APPEND_COMMITTED`;
no new insert yields `RECORD_STORE_APPEND_IDEMPOTENT`.

## Transaction and lock posture

Writes use `isolation_level=None`, `timeout=0.0`, DELETE journal, FULL
synchronous, enabled foreign keys, and an explicit `BEGIN IMMEDIATE` with explicit
`COMMIT`/`ROLLBACK`. A second writer holding the immediate lock causes an
immediate `RECORD_STORE_BUSY` with no retry, sleep, backoff, or partial write. A
rollback before commit leaves no partial row. A successful close leaves no
`-wal`/`-shm`/`-journal` sidecar. WAL, `journal_mode` OFF/MEMORY, synchronous
OFF/NORMAL, `executescript`, and `check_same_thread=False` are forbidden.

## Corruption and no-echo

Read and load verify DELETE journal, the exact schema, meta row, `user_version`,
indexes, `integrity_check`, and `foreign_key_check`, enforce the record and total
payload bounds, and strictly decode, reconstruct, and revalidate every record and
the complete lineage. Any schema drift, configuration drift, stored-payload
tampering, or lineage violation fails closed. No public malformed case escapes as
a raw `TypeError`, `KeyError`, `ValueError`, JSON error, `sqlite3.Error`,
`OSError`, `RuntimeError`, or traceback, and `BaseException` is never caught. An
invalid result never exposes a path, SQL string, `payload_json`, canonical market
payload, `source_reference`, raw object repr, exception text, filesystem detail,
environment value, credential, or strategy/trading content.

## DatasetSnapshotReference materialization

`materialize_dataset_snapshot_reference` requires an exact
`DatasetSnapshotReference`, rebuilds it through the public
`build_dataset_snapshot_reference`, and requires the rebuilt object to equal the
caller before any store access; a malformed reference is
`RECORD_STORE_REFERENCE_INVALID`, and no rejected result exposes the caller
reference. The fully verified store then resolves every ordinary id and every
review id in exact reference-owned order (no sorting). A missing id is
`RECORD_STORE_REFERENCE_MISSING_RECORD`; an ordinary id that resolves to a
CONFLICT record, or a review id that resolves to a non-CONFLICT or
non-human-review record, is `RECORD_STORE_AUTHORITY_VIOLATION`.

### Batch mode: full recomputation

For `derivation_mode=VALIDATED_RECORD_BATCH` the review tuple must be empty and
the ordinary tuple non-empty. The store recomputes `validate_record_batch` over
the resolved ordinary records with no external parents and requires the batch to
be valid, its accepted ids to equal the reference ordinary ids, and its
`canonical_batch_sha256` to equal the reference `validated_batch_sha256`; any
mismatch is `RECORD_STORE_REFERENCE_CONTENT_MISMATCH`. Success reports
`verification_mode=VALIDATED_BATCH_RECOMPUTED`.

### As-of mode: id-resolution only

For `derivation_mode=AS_OF_QUERY_RESULT` the store does not claim a full WP157
query replay. The reference alone does not carry the complete original query spec
or every excluded input record id, so the store verifies only reference
self-consistency through WP160, complete record-store integrity, existence of
every referenced ordinary/review id, exact authority classification, and exact
reference-owned order. It never recomputes `query_spec_sha256`,
`query_result_sha256`, or `validated_batch_sha256` from only the output subset.
Success reports `verification_mode=AS_OF_REFERENCE_IDS_RESOLVED`. Full persisted
as-of replay is deferred.

## Boundaries

- No network, API, or WebSocket collection; no real/public data population; no raw
  HTTP or source-response bytes are stored.
- No manifest-store schema change; the WP161 manifest/reference store is
  unchanged.
- No Parquet/Arrow/DuckDB/Polars and no new dependency.
- No strategy, signal, feature/label, backtest/replay, paper, portfolio/risk, or
  order/execution/live authority.

## Successor boundary

The next phase is bounded real/public Polymarket point-in-time data population
(WP164), which would move from synthetic/caller-supplied records to bounded real
public data while remaining read-only and non-trading, using the existing
read-only public collection architecture, WP156 record construction, WP163 durable
record storage, and WP162 logical manifest registration. It is separately gated
and unimplemented here.
