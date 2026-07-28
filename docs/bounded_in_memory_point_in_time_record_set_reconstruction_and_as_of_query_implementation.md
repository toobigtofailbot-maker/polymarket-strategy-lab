# Bounded In-Memory Point-In-Time Record-Set Reconstruction And As-Of Query Implementation

Canonical WP157 document. This layer is local, offline, stdlib-only,
deterministic, and in-memory. It consumes already-built WP156 public record
objects and produces immutable deterministic query results with an exact
receipt and SHA-256 result hash. It has no file, network, credential,
scheduler, dependency, persistence, strategy, paper, order, risk, or execution
authority.

## 1. Authorization And PR #156 Merge Lineage

WP157 executes only on the merged WP156 foundation.

- PR #156 state: MERGED.
- PR #156 implementation head: `c5d83738e644eabf8690f8a5991ff08e47090553`.
- PR #156 merge commit: `fa796d9be78bf595ab3a6b197c2e81c77cd0fe09`.
- Local `main` and `origin/main` at branch creation:
  `fa796d9be78bf595ab3a6b197c2e81c77cd0fe09`.
- Relation: current `main` equals the PR #156 merge commit; no later commit.

WP157 builds the next bounded deterministic layer beneath the WP155
`POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT` and the WP156
`LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION`, implementing
`BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION`.

## 2. Exact Public Surface

Module: `src/data_layer/point_in_time_market_research/as_of_query.py`.
Synthetic cases: `src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py`.
Package export: `src/data_layer/point_in_time_market_research/__init__.py`.

Public constants:

- `AS_OF_QUERY_LABEL = "POINT_IN_TIME_RECORD_SET_RECONSTRUCTION"`
- `AS_OF_QUERY_POSTURE = "BOUNDED_IN_MEMORY_AS_OF_INGESTION_TIME_RECONSTRUCTION"`
- `SUPPORTED_CUTOFF_MODES`
- `SUPPORTED_RESULT_VIEWS`
- `QUERY_STATUSES`
- `EXCLUSION_REASONS`

Public frozen dataclasses:

- `EventTimeWindow`
- `PointInTimeQuerySpec`
- `PointInTimeQueryReceipt`
- `PointInTimeRecordSetResult`
- `SyntheticAsOfQueryCase`

Public functions:

- `query_point_in_time_record_set`
- `get_synthetic_as_of_query_cases`
- `load_synthetic_as_of_query_case`

Internal helper functions and the WP156 review-only handoff helpers are not
exported from the package root.

## 3. Locked Vocabularies (Canonical Order)

Cutoff modes:

1. `AS_OF_INGESTION_TIME`
2. `AS_OF_OBSERVED_TIME_DIAGNOSTIC`

Result views:

1. `AUTHORITATIVE_CURRENT_STATE`
2. `VISIBLE_HISTORY`
3. `ENTITY_TIMELINE`

Query statuses:

1. `QUERY_VALID`
2. `QUERY_VALID_WITH_WARNINGS`
3. `QUERY_EMPTY`
4. `QUERY_REJECTED_SPEC`
5. `QUERY_REJECTED_RECORD_BATCH`
6. `QUERY_CONFLICT_REQUIRES_REVIEW`

Exclusion reasons:

1. `AFTER_INGESTION_CUTOFF`
2. `AFTER_OBSERVED_CUTOFF`
3. `BEFORE_EVENT_WINDOW`
4. `AFTER_EVENT_WINDOW`
5. `EVENT_TIME_MISSING`
6. `SUPERSEDED_AT_CUTOFF`
7. `RETRACTED_AT_CUTOFF`
8. `CONFLICT_REQUIRES_REVIEW`
9. `INVALID_RECORD_BATCH`
10. `ENTITY_FILTER_MISMATCH`
11. `RECORD_FAMILY_FILTER_MISMATCH`
12. `OBSERVATION_KIND_FILTER_MISMATCH`

## 4. Immutable Query Spec

`PointInTimeQuerySpec` is a frozen dataclass. All repeated filter values are
tuples; no caller list or mapping is retained. `query_id` and `parameter_set_id`
use the WP156 bounded opaque-id rules (non-empty, `<= 256` chars, stripped,
`[A-Za-z0-9._:-]`). Empty filter tuples mean no filter. Non-empty filters are a
deterministic OR within one field and AND across fields. Duplicate filter
values, unsorted filter tuples, and unknown families/kinds/cutoff modes/views
fail closed. `AUTHORITATIVE_CURRENT_STATE` rejects `include_retracted_history`.
`ENTITY_TIMELINE` requires at least one of the event/market/token/source/
resolution-source filters. `include_conflicts_for_review` never converts a
conflict into authoritative data.

`EventTimeWindow` requires at least one non-`None` bound; when both are present,
`start_inclusive < end_exclusive`. The default missing-event behavior is false.

## 5. Query-Spec Canonicalization And Hash

The engine builds one canonical mapping containing every query-spec field,
explicit `null`s, and empty tuples serialized as empty lists. The query-spec
hash is `SHA-256(canonical_json_bytes(spec_mapping))` using the WP156 bounded
canonical JSON. The mapping excludes Python object representation, environment,
paths, runtime timestamps, duration, process id, warnings, and result counts.
Fixed spec hashes are asserted independently in tests.

## 6. Batch-Validation Handoff

`query_point_in_time_record_set(records, spec)` validates the spec first, then
partitions records by committed classification:

- Conflict candidates (`classification == "CONFLICT"`) are routed to the WP156
  review-only handoff and never become authoritative.
- All remaining records are validated with the exact WP156
  `validate_record_batch`. If that batch is invalid the query returns
  `QUERY_REJECTED_RECORD_BATCH` with no records and no receipt.

The WP156 batch `canonical_batch_sha256` is the validated-batch identity in the
receipt. Records are never rebuilt, repaired, reinterpreted, or coerced by
WP157.

Conflict-review handoff: a batch may still yield review-only conflict output
when every non-conflict record is valid and every conflict record is a
structurally valid WP156 conflict record. WP156 exposes two additive, tested,
purely fail-closed surfaces used only for this handoff:

- `build_review_conflict_record` builds a structurally valid `CONFLICT` record
  (a record that satisfies every WP156 integrity rule except the human-review
  gate, with `human_review_required` True).
- `revalidate_review_conflict_record` confirms a conflict record object
  reproduces its committed record-version identity exactly.

The standard family builders and `validate_record_batch` are unchanged and
continue to reject conflicts; a conflict record can never be authoritative. If
any conflict record is not structurally valid the query fails closed with
`QUERY_REJECTED_RECORD_BATCH` and `CONFLICT_NOT_AUTHORIZED_FOR_REVIEW`.

## 7. Visibility Order Of Operations

1. validate the query spec;
2. validate record integrity (batch + review-conflict handoff);
3. ingestion cutoff (`ingestion_time <= T`, default authoritative mode);
4. observed diagnostic cutoff when selected (`observed_time <= T` in addition to
   the ingestion bound; ingestion-bounded and diagnostic only);
5. entity / family / kind filters;
6. event-time window;
7. visible supersession / correction / revision / retraction state;
8. deterministic result ordering;
9. receipt and hash generation.

Because WP156 guarantees `observed_time <= ingestion_time`, the observed
diagnostic cutoff can never admit a record ingested after the cutoff. Event-time
filtering never runs before visibility; corrections are never backdated; no
current/latest state, future source/rule snapshot, or settlement/outcome
knowledge is ever used.

## 8. Filter Semantics

Extracted dimensions per record:

- Market observation: family, observation kind, platform, event, market, token
  (when present), source.
- Source snapshot: family, source.
- Resolution-rule snapshot: family, platform, event, market, resolution source.

An empty filter passes. A non-empty filter passes only when the record has that
dimension and its value is included; a record lacking the filtered dimension
fails that filter. The token filter excludes token-less metadata. The
observation-kind filter applies only to market observations. The
resolution-source filter applies only to rule snapshots. Each filtered-out
record increments exactly one primary exclusion reason using the canonical
precedence: family, observation kind, then any entity dimension
(platform, event, market, token, source, resolution source), which all map to
`ENTITY_FILTER_MISMATCH`. All values remain opaque; no display-name or
question-text matching occurs.

## 9. Event-Time Window Semantics

Applied only after visibility and entity filtering. Start is inclusive, end is
exclusive. A missing event time is excluded with `EVENT_TIME_MISSING` unless
`include_missing_event_time` is true, in which case it is retained with the
`EVENT_TIME_MISSING_INCLUDED` warning and ordered using the explicit null-order
marker. Values before start use `BEFORE_EVENT_WINDOW`; values at or after end use
`AFTER_EVENT_WINDOW`. Event time never changes visibility and no timestamp
precision is altered.

## 10. Entity Keys And State-Chain Semantics

Deterministic entity keys:

- Market observation: `(record_family, observation_kind, platform_id, event_id,
  market_id, token_id-or-null-marker, source_id, observation_id)`.
- Source snapshot: `(record_family, source_id)`; lineage supersession selects the
  terminal snapshot within the source.
- Resolution rule: `(record_family, platform_id, event_id, market_id,
  resolution_source_id)`.

State application is lineage-based, not latest-timestamp. Over the visible
records:

- a `SOURCE_REVISION` / `PROJECT_CORRECTION` / `SOURCE_RETRACTION` marks its
  explicit visible `supersedes` parent as superseded;
- a visible `SOURCE_RETRACTION` and its retracted target are removed from
  authoritative current state (`RETRACTED_AT_CUTOFF`);
- `EXACT_DUPLICATE` and `SEMANTIC_DUPLICATE` never create a second authoritative
  state; `SEMANTIC_DUPLICATE` emits `SEMANTIC_DUPLICATE_HISTORY_ONLY`;
- `LATE_ARRIVAL` is visible only at its actual ingestion time
  (`LATE_ARRIVAL_VISIBLE`) and is never backdated;
- `CONFLICT` never enters authoritative current state.

Because WP156 requires a correction/revision/retraction to have ingestion time
no earlier than its parent, any visible child necessarily has a visible parent.
An invisible future child never affects an earlier result. Original and
superseding records remain available in history views; retracted history is
available only when explicitly requested.

## 11. Result Views

- `AUTHORITATIVE_CURRENT_STATE`: terminal visible states after supersession and
  retraction; empty history tuple; no conflicts, superseded, retracted, or
  duplicate second state. Non-terminal visible records are excluded via
  `SUPERSEDED_AT_CUTOFF` or `RETRACTED_AT_CUTOFF`.
- `VISIBLE_HISTORY`: all visible valid records in canonical order in the history
  tuple; empty authoritative tuple; retracted historical parents excluded when
  `include_retracted_history` is false, otherwise retained with
  `RETRACTED_HISTORY_INCLUDED`.
- `ENTITY_TIMELINE`: requires at least one entity filter; the authoritative tuple
  is the terminal state and the history tuple is the visible timeline for the
  filtered scope.

## 12. Deterministic Ordering

Canonical record order: ingestion time, observed time, event-time null-order
marker (present sorts before missing), event time when present, record-family
canonical order, record-version id. Authoritative current state is additionally
ordered by canonical entity key, ingestion time, and record-version id. History
and timeline use canonical record order. Ordering never depends on input
sequence order, dict/set iteration order, object identity, filesystem order, or
locale. Any permutation of the same valid record set yields identical ids,
receipt, and result hash.

## 13. Exclusion Accounting And Reconciliation

`exclusion_counts` lists every canonical reason with an integer count including
zeros, in exact order. Its sum equals the receipt `excluded_count`. Every unique
validated record is accounted for exactly once under the documented per-view
model:

`validated_unique_record_count == primary_result_count + review_conflict_count
+ excluded_count`

where `primary_result_count` is the authoritative result count for
`AUTHORITATIVE_CURRENT_STATE` and the history result count for `VISIBLE_HISTORY`
and `ENTITY_TIMELINE`. In `ENTITY_TIMELINE` the authoritative tuple is a derived
subset of the history tuple and is not separately counted. Exact-duplicate input
objects (same identity supplied twice) are acknowledged through the WP156
validated-batch identity and are not double counted.

## 14. Result Receipt And Hash Preimage

`PointInTimeQueryReceipt` records the query id, query-spec hash, validated-batch
hash, cutoff mode/time, event-window bounds, result view, input and validated
unique record counts, visible-before-state count, per-tuple counts, ordered
result id tuples, exclusion counts, result hash, engine version
(`point-in-time-as-of-query@1.0.0`), parameter-set id, and the fixed safety
booleans `advisory_only=True` and `no_execution_authority=True`.

The result SHA-256 preimage includes the query-spec hash, validated-batch hash,
cutoff mode/time, event window, result view, ordered authoritative/history/
review-conflict record-version ids, canonical exclusion counts, engine version,
parameter-set id, and the explicit safety booleans. It excludes runtime
duration, memory, environment, paths, Python object representation, current
time, and warning display text. Rejected queries (invalid spec or invalid batch)
return no records, no receipt, deterministic neutral codes, and never echo raw
caller values, exceptions, tracebacks, or paths.

## 15. Synthetic As-Of Query Corpus

`get_synthetic_as_of_query_cases()` returns the exact ordered immutable 24-case
corpus built only from deterministic valid WP156 records with fixed timestamps
and no wall clock, random ids, real market/account/wallet data, or file paths.
Expected result hashes are committed constants and are never generated from the
result under test.

1. `ASOF-C01-BEFORE-FIRST-INGESTION`
2. `ASOF-C02-PRIMARY-VISIBLE`
3. `ASOF-C03-BEFORE-CORRECTION`
4. `ASOF-C04-AFTER-CORRECTION`
5. `ASOF-C05-BEFORE-SOURCE-REVISION`
6. `ASOF-C06-AFTER-SOURCE-REVISION`
7. `ASOF-C07-BEFORE-RETRACTION`
8. `ASOF-C08-AFTER-RETRACTION`
9. `ASOF-C09-LATE-ARRIVAL-NOT-BACKDATED`
10. `ASOF-C10-OBSERVED-DIAGNOSTIC-INGESTION-BOUNDED`
11. `ASOF-C11-EVENT-WINDOW-AFTER-VISIBILITY`
12. `ASOF-C12-MISSING-EVENT-TIME-EXCLUDED`
13. `ASOF-C13-MISSING-EVENT-TIME-INCLUDED`
14. `ASOF-C14-ENTITY-FILTER`
15. `ASOF-C15-FAMILY-AND-KIND-FILTER`
16. `ASOF-C16-VISIBLE-HISTORY`
17. `ASOF-C17-ENTITY-TIMELINE`
18. `ASOF-C18-CONFLICT-EXCLUDED`
19. `ASOF-C19-CONFLICT-REVIEW-ONLY`
20. `ASOF-C20-INVALID-BATCH-REJECTED`
21. `ASOF-C21-INVALID-SPEC-REJECTED`
22. `ASOF-C22-INPUT-PERMUTATION-INVARIANT`
23. `ASOF-C23-EMPTY-VALID-RECEIPT`
24. `ASOF-C24-FUTURE-RULE-SNAPSHOT-EXCLUDED`

## 16. No-Look-Ahead Negative Matrix

Focused tests prove: future corrections, revisions, retractions, and rule
snapshots cannot change an earlier cutoff; late arrivals are never backdated; an
event time before the cutoff cannot override a later ingestion time; the
diagnostic observed cutoff cannot include a later-ingested record; and an event
window cannot make an invisible record visible. Query-spec, record-batch,
temporal-integrity, determinism/accounting, and boundary negative cases fail
closed with bounded neutral codes and no raw echo.

## 17. No Side Effects And Boundary Evidence

The two source modules import only `__future__`, `collections.abc`,
`dataclasses`, `datetime`, `re`, and intra-package WP156 symbols. There is no
file, network, subprocess, environment, random, UUID, wall-clock, Arrow,
Parquet, DuckDB, Polars, or Pydantic usage. Behavioral tests confirm no files are
created while every case runs. No writer, reader, collector, poller, scheduler,
daemon, or CLI is introduced.

## 18. Compatibility With WP155/WP156 And Legacy Snapshot Modules

WP157 consumes WP155 contract semantics and WP156 public records unchanged. The
only WP156 change is the narrow additive review-only conflict handoff
(`build_review_conflict_record` and `revalidate_review_conflict_record` plus a
default-off `allow_review_conflict` keyword threaded through the existing
builders). The standard builders and `validate_record_batch` keep identical
behavior; all previous WP156 tests are preserved. Legacy Polymarket snapshot
readers, writers, replay, and catalog behavior are untouched.

## 19. Explicit Non-Authority

WP157 selects no strategy, computes no expected return, and authorizes no paper,
order, fill, accounting, risk, reconciliation, restricted-live, or live
behavior. Every result carries `advisory_only=True` and
`no_execution_authority=True`. Capital at risk is USD 0.

## 20. Changed-File Scope

- `src/data_layer/point_in_time_market_research/as_of_query.py`
- `src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py`
- `src/data_layer/point_in_time_market_research/records.py` (narrow additive
  review-only conflict handoff)
- `src/data_layer/point_in_time_market_research/__init__.py`
- `tests/data_layer/point_in_time_market_research/test_as_of_query.py`
- `tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py`
  (successor scope/surface maintenance only)
- `docs/bounded_in_memory_point_in_time_record_set_reconstruction_and_as_of_query_implementation.md`
- `docs/status_entries/WP157.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- `tests/test_project_status_docs.py`
- `tests/test_point_in_time_market_research_data_foundation_contract_docs.py`
  (forward next-gate assertion advanced WP157 → WP158 and cascade scope guard)
- `tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py`
  (forward next-gate assertion advanced WP157 → WP158 and cascade scope guard)
- `tests/test_local_research_workflow_value_measurement_harness_contract_docs.py`
  (cascade scope guard admits the WP157 changed-file set)
- `tests/test_wallet_intelligence_architecture_contract_docs.py`
  (allowed-src scope guard admits the two WP157 source files)

## 21. Next Separately Gated Package

`WP158 — APPEND-ONLY LOCAL MANIFEST AND DETERMINISTIC DATASET SNAPSHOT REFERENCE
CONTRACT`. WP158 requires separate approval and is not implemented. It remains
contract-first with no writer, no Arrow/Parquet dependency, no DuckDB/Polars, no
collector/network/credentials/scheduler, and no strategy/paper/live behavior.
