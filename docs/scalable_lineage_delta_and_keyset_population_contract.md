# Scalable Lineage-Delta References and Manual Keyset Market-Universe Expansion (WP166)

Canonical contract for the bounded, scalable, one-page keyset lineage-delta public
Polymarket point-in-time capture layer. This document is repo truth; the
implementation, focused tests, and status/deferred/repo-truth reconciliation are
authoritative alongside it.

## Objective

Remove WP165's cumulative-256 historical ceiling without weakening lineage
integrity, and add one-page manual Gamma keyset capture so the real public research
corpus can expand materially beyond the first 25 markets. WP166 adds two coordinated
capabilities: scalable lineage-delta dataset references (schema v2) and manual
keyset market-universe expansion.

## A. Scalable lineage-delta dataset references (schema v2)

- Version 1.0.0 dataset snapshot references remain byte-for-byte identity- and
  behavior-compatible: `DATASET_REFERENCE_SCHEMA_VERSION = "1.0.0"` is unchanged, v1
  `created_from_manifest_entry_id` stays `None`, the v1 external-parent tuple is
  empty, and an existing persisted v1 payload that lacks the new field still decodes
  and verifies to the identical reference id.
- New constants:
  `DATASET_REFERENCE_SCHEMA_VERSION_LINEAGE = "2.0.0"` and
  `DATASET_REFERENCE_SUPPORTED_SCHEMA_VERSIONS = ("1.0.0", "2.0.0")`.
- New derivation mode `LINEAGE_DELTA_RECORD_BATCH`.
- `DatasetSnapshotReference` is extended with a trailing defaulted field
  `external_parent_record_version_ids: tuple[str, ...] = ()` and its
  `created_from_manifest_entry_id` type becomes `str | None`.
- A v2 lineage reference sets `schema_version = "2.0.0"`,
  `derivation_mode = LINEAGE_DELTA_RECORD_BATCH`, `ordinary_record_version_ids` to
  the CURRENT run accepted ids only, an empty review-conflict tuple, the exact
  sorted direct external-parent id set, `created_from_manifest_entry_id` to the
  exact manifest head that existed immediately BEFORE this registration, all query
  fields null, `human_review_required=False`, `advisory_only=True`,
  `no_execution_authority=True`. Ordinary and external-parent ids are unique and
  disjoint, each tuple is bounded at 256, and the external-parent order is lexical
  record-version-id ascending. The v2 self-id canonical preimage additionally
  commits `external_parent_record_version_ids` and `created_from_manifest_entry_id`.

## WP156 — actual external parent record context

`validate_record_batch` gains a keyword-only `known_parent_records=()` argument
alongside the existing `known_parent_record_ids=()`. Supplying the actual immutable
external-parent record objects lets a current record be compared against the
parent's committed object semantics, which a bare id can never prove.

- `known_parent_records` is bounded at 256, admits only the exact WP156 ordinary
  record classes with an exact `PointInTimeEnvelope`, carries no CONFLICT authority,
  requires each parent object to independently revalidate its record-version
  identity, canonical payload hash, family-derived ids, and immutable structure, and
  requires the external parent ids to be unique.
- For a CURRENT record whose relevant parent is external, the SAME semantic checks
  applied when the parent object is local are run against the actual parent object:
  `SOURCE_REVISION`/`PROJECT_CORRECTION`/`SOURCE_RETRACTION` require equal entity
  identity and `current ingestion_time >= parent ingestion_time`; `EXACT_DUPLICATE`
  requires equal canonical payload hash and entity identity; `SEMANTIC_DUPLICATE`
  requires equal observation identity and entity identity. All normal
  parent/supersedes existence rules remain.
- When `known_parent_records` is non-empty the canonical batch material additionally
  commits `"external_parent_record_version_ids": sorted(parent ids)`; when it is
  empty the key is not added, so legacy batch hashes stay byte-for-byte identical.
- `accepted_record_version_ids` always names the CURRENT records only. External
  parent ancestors are never required recursively; manifest authority proves the
  parent itself was previously committed.

## WP160 — manifest chain authority for v2 parents

`validate_manifest_chain` walks entries in manifest sequence order while maintaining
a bounded set of record ids authorized by EARLIER REGISTER entries. For each v2
`LINEAGE_DELTA_RECORD_BATCH` REGISTER, `entry.previous_manifest_entry_id` must equal
`reference.created_from_manifest_entry_id`, and every external-parent id must already
be in the earlier-registered authority set — an external parent first introduced in
this same entry or a later entry is forbidden, and there is no future-entry
authority. A reference's ordinary current ids join the authority set only after the
entry is validated. The cumulative unique ordinary id count is bounded at 4096,
matching the WP163 physical research-store horizon. Two closed error codes are added:
`REFERENCE_PARENT_CONTEXT_INVALID` and `REFERENCE_PARENT_CONTEXT_UNCOMMITTED`.

## WP161 — mixed v1/v2 persistence without SQLite migration

No SQLite table, column, index, or `PRAGMA user_version` changes. WP161 stores
canonical object payload JSON; an old v1 persisted payload missing
`external_parent_record_version_ids` decodes as the empty tuple, v1 stays
identity-compatible, v2 references serialize and reload exactly, mixed v1/v2 chains
verify, and a tampered v2 payload fails closed. There is no migration script.

## WP162 — lineage-delta persistence adapter

`persist_lineage_delta_record_batch_snapshot(path, records, parent_records, *,
manifest_id, effective_time, parameter_set_id, validator_version)` persists ONLY the
current records as a v2 lineage-delta reference. Current and parent records are exact
and bounded at 256; provenance binds both; a nonempty valid existing chain is
required; the supplied parent id set must EXACTLY equal the current lineage-parent
ids not present among the current ids (no missing parent, no unused extra parent);
every supplied parent must already be authorized by an earlier registered reference;
the current records are validated against the actual parent objects; the v2 reference
binds the accepted current ids, the sorted external parents, the validated batch
hash, and the prior manifest head; registration goes through the unchanged WP160
builder and WP161 store; and a head change between pre-read and append fails closed
rather than silently retargeting the backlink. Three adapter error codes are added:
`ADAPTER_PARENT_CONTEXT_INVALID`, `ADAPTER_PARENT_CONTEXT_UNREGISTERED`, and
`ADAPTER_PARENT_CONTEXT_HEAD_CHANGED`. The existing v1 batch and as-of adapters are
behavior-compatible.

## WP163 — v2 dataset materialization

`DatasetSnapshotMaterializationResult` gains a trailing defaulted
`external_parent_records: tuple[PointInTimeRecord, ...] = ()`, and a new verification
mode `LINEAGE_DELTA_PARENT_CONTEXT_RECOMPUTED` is added. For a v2 reference the
materializer resolves the ordinary current ids and external parent ids in reference
order (external parents may not be CONFLICT), reruns
`validate_record_batch(ordinary_records, known_parent_records=external_parent_records)`,
requires the accepted current ids and canonical batch hash to match the reference
exactly, and returns the ordinary current records plus the resolved external parent
records. Manifest ancestry authority remains WP160/WP161; v1 materialization behavior
is exact.

## B. Manual keyset market-universe expansion

`GET /markets/keyset` is added to the read-only public client as
`gamma_markets_keyset` with `verified=False`. Official Polymarket documentation was
checked 2026-08-30: GET-only, documented `limit` range 1..100 (default 20),
`after_cursor` accepts the previous `next_cursor`, `offset` is explicitly rejected,
and the response is a wrapper object with a `markets` list and an optional
`next_cursor` omitted on the last page. The endpoint has NOT been live-probed by this
repo's WP9 process and is documented-but-repo-unverified.

`get_markets_keyset(*, limit=100, after_cursor=None)` performs one GET whose query
always includes `limit`, includes `after_cursor` only when non-null, and NEVER sends
`offset`; the endpoint-verification guard remains authoritative. One WP166 invocation
performs at most ONE keyset page request (at most 100 markets) plus optionally at
most 20 CLOB books, and returns the response `next_cursor` for a later manual
invocation. There is no automatic cursor loop, scheduler, daemon, background worker,
sleep, retry, backoff, authenticated endpoint, or trading/execution.

### Polling policy

`gamma_markets_keyset` is added to `NETWORK_ENDPOINT_KEYS` with a conservative
endpoint policy: `enabled_by_default=False`, `max_requests_per_window=6`,
`window_seconds=60`, `minimum_interval_seconds=10.0`, `max_markets_per_run=100`,
`max_tokens_per_run=0`, `requires_explicit_network=True`,
`allow_automated_loop=False`. No existing endpoint budget is loosened.

## Scaled population coordinator

`src/data_layer/point_in_time_market_research/polymarket_scaled_population.py`
performs one manual keyset page into WP156 immutable current observations, direct
parent-object validation, a WP163 append of the CURRENT records, and a WP162 v2
lineage-delta registration.

- Label `POLYMARKET_SCALABLE_KEYSET_LINEAGE_DELTA_POPULATION`; posture
  `MANUAL_ONE_PAGE_KEYSET_GET_ONLY_EXTERNAL_PARENT_COMMITTED_NO_TRADING_AUTHORITY`.
- Public constants `POLYMARKET_SCALED_POPULATION_LABEL`,
  `POLYMARKET_SCALED_POPULATION_POSTURE`, `POLYMARKET_SCALED_POPULATION_STATUSES`,
  `POLYMARKET_SCALED_POPULATION_ERROR_CODES`; frozen config
  `PolymarketScaledPopulationConfig`; frozen result
  `PolymarketScaledPopulationResult`; functions
  `capture_scaled_polymarket_public_page` and
  `recover_scaled_polymarket_public_registration`. Exactly 8 new package-root
  symbols are exported.
- Config fields: `manifest_id`, `parameter_set_id`, `normalizer_version`,
  `validator_version`, `page_limit` (exact int 1..100), `after_cursor` (None or an
  exact stripped control-free str of 1..2048 chars), `order_books_limit` (exact int
  0..20), `allow_network` (bool), `allow_documented_unverified_keyset` (bool).

### Double opt-in

With `allow_network=False` the coordinator makes zero network calls and returns a
valid dry run. Real keyset use requires BOTH `allow_network=True` and
`allow_documented_unverified_keyset=True`; a lone `allow_network=True` is rejected
before any client construction or GET. Only that double-opted-in path constructs the
default client with `allow_unverified_endpoints=True`, and only the explicitly
documented keyset call relies on that posture; the CLOB book endpoint remains already
repo-verified.

### Run identity and boundaries

The deterministic run preimage commits the label, the single `captured_at_utc`,
`config.after_cursor`, `config.page_limit`, the ordered Gamma and CLOB payload
hashes, and the config provenance, deriving `snapshot:sha256:...` and
`ingest:sha256:...`. `next_cursor` is never part of the immutable record identity.
The keyset response boundary requires a built-in dict with a `markets` built-in list
of 1..page_limit built-in dicts and an absent/None or bounded-cursor `next_cursor`;
duplicate market ids reject the whole run; a single failed or denied book aborts the
page before any persistence. `next_cursor` is returned only after a successfully
validated keyset response and passes the bounded cursor grammar.

### Baseline, capacity, and persistence order

Before network the coordinator loads and verifies WP163, loads and verifies the WP161
mixed v1/v2 chain, computes the union of all registered ordinary ids, and requires the
physical WP163 record-id set to EXACTLY equal that registered union; the entire
registered history selects the latest prior entity record by actual UTC chronology.
Capacity gates run before any network: WP163 `physical_count + page_limit +
order_books_limit <= 4096`, WP161 fewer than 256 entries and 256 references, and
current-page `page_limit + order_books_limit <= 256`; otherwise
`SCALED_CAPACITY_EXCEEDED` with zero network. After the whole page succeeds the
current records are validated against the actual direct external parents, appended
through WP163, and registered as the v2 delta; the returned reference is proven to
carry the exact current accepted ids, the exact direct external parent ids, the exact
validated hash, and the exact prior manifest-head backlink, and WP161/WP163 are
independently reloaded to prove convergence. A registration failure after the record
append preserves the immutable records, reports a records-persisted/registration-failed
status with `recovery_required=True` and `network_used=True`, preserves the validated
`next_cursor`, and never re-fetches.

### Offline recovery

`recover_scaled_polymarket_public_registration` performs zero network and zero record
writes. It is a valid `SCALED_ALREADY_REGISTERED` no-op when the store already
converges; otherwise it requires exactly one unregistered scaled page (a strict
superset of 1..120 orphan records sharing one snapshot id, batch id, and observed ==
ingestion time, with at least one Gamma record, Gamma count within the page limit,
book count within the book limit, books reproducing the deterministic same-run token
selection, the run identity recomputed using `config.after_cursor`, the lineage
rebuilt object-for-object against the registered history, and every direct external
parent existing as an earlier registered record) and re-registers that delta through
the WP162 lineage-delta adapter. A wrong `after_cursor` config, a multi-page orphan
identity, or a forged orphan set fails closed as `SCALED_RECOVERY_INVALID`.

## Closed diagnostics

All invalid public results carry only closed WP166 error codes plus whitelisted
downstream WP162/WP163 codes, and never a URL, path, raw payload, question text, SQL,
exception repr, credential, or arbitrary cursor. Only ordinary `Exception` is
contained; `BaseException` always escapes.

## Successor boundary

WP166 does not implement analytical research storage. The intended successor is
WP167 (analytical research store and query layer: derived Parquet/Arrow
materialization from verified canonical PIT records, DuckDB/Polars analytical
queries, SQLite remaining the canonical integrity authority). Prepared does not mean
merge-authorized.
