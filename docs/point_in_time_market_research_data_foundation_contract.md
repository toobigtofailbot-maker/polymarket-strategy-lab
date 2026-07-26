# Point-In-Time Market Research Data Foundation Contract

## 1. Decision Status

Foundation label:

`POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT`

Posture:

`CONTRACT_ONLY_NO_WRITER_NO_DEPENDENCY_NO_COLLECTION`

WP155 is a documentation, repo-truth, status, and focused-test package. It is
the contract prerequisite for implementation of WP154 Phase A. It is not a
dataset, database, storage engine, query engine, normalizer implementation,
real-data run, SDK migration, relationship graph, experiment registry, signal,
alpha evidence, paper readiness, or live readiness.

WP155 implements no schema class, validator, fixture, writer, reader, query
engine, benchmark, migration, dependency, network client, collector, scheduler,
or runtime behavior. Capital at risk is USD 0.

## 2. Merge Lineage And Authority

PR #154 was merged on 2026-07-26.

- PR #154 final implementation head:
  `555a0e7defc0b96dee0f3bd1cef629b4c422b80b`
- PR #154 merge commit:
  `d5fccf764513f79dbe561db089c967f40bee418a`
- WP155 base, local `main`, and `origin/main` at branch creation:
  `d5fccf764513f79dbe561db089c967f40bee418a`
- Lineage result: `main` equaled the PR #154 merge commit; no later commit was
  present at branch creation.

The Centralized Boundary Group Reference in
`docs/ai/codex/PROTECTED_PATHS.md` remains binding. WP155 crosses none of:
credentials/secrets, authenticated clients, wallet/account behavior, order
placement/cancel, execution gateway, paper engine, scheduler/bot loop,
runtime/daemon, dashboard/deployment, dependency/lock changes, external code
copying, or generated artifacts.

WP155 authorizes only this canonical contract, its stable status fragment,
repo-truth reconciliation, deferred-item reconciliation, documentation tests,
and the minimum compatibility maintenance required by existing cross-WP tests.

## 3. Current Repository Inventory

The inventory below is fact about the merged pre-WP155 repository, not a
promotion of legacy names into the canonical contract.

| Surface | Current identity/time/storage behavior | Compatibility finding |
|---|---|---|
| public adapter models | `market_id`, `condition_id`, `token_id`; order books use `snapshot_timestamp` and `source_url` | useful upstream fields, but no platform namespace or three-time envelope |
| snapshot records | `snapshot_id`, `market_id`, `condition_id`, `token_id`, `captured_at_utc`, `source`, `adapter_version` | `captured_at_utc` is one capture timestamp, not event/observed/ingestion time |
| snapshot persistence | append JSONL market/order-book files; one JSON manifest per timestamp-derived snapshot ID; local ignored output only | legacy local inspection format; not canonical PIT storage or record-version history |
| reader/error handling | malformed JSONL lines are errors and may be skipped in non-strict mode | no quarantine record, stable failure vocabulary, or reprocessing lineage |
| catalog | latest market selected by lexicographic `captured_at_utc`; lookup by market, condition, and token | latest-state convenience is not an ingestion-time as-of query |
| replay | finite chronological inspection sorted by `captured_at_utc`, then `market_id`; grouped by `snapshot_id` | inspection only; not point-in-time reconstruction, fill simulation, or backtest |
| deduplication | JSON fingerprint exact duplicates are dropped from the returned valid list; content conflicts sharing local identity are retained and reported | no receipt identity, record-version ID, supersession chain, or semantic-duplicate contract |
| quality | ISO-like capture checks and bounded issue codes; duplicate market/token mapping checks | not strict timezone-aware RFC 3339, quarantine, schema-version, or lineage validation |
| market research features | deterministic indexes over question, `condition_id`, `token_id`, category/resolution date, outcome labels, snapshot and manifest IDs | relationship candidates are advisory metadata, not canonical identity or equivalence |
| resolution ambiguity | `label_id`, `market_id`, rule text snapshot, source artifact reference, `reviewed_at_utc`, ambiguity and review fields | manual label record, not a source or resolution-rule snapshot |
| calibration | `market_id`, `condition_id`, `snapshot_time_utc`, `local_capture_time_utc`, `resolution_time_utc`, resolution source/status fields | research fixture contract, not a canonical PIT observation history |
| wallet records | `event_id`, `source_id`, `observed_at_utc`, wallet, market, condition, and `asset_id` fields | sanitized research fixture semantics; `asset_id` collides conceptually with canonical `token_id` |
| generated/report artifacts | JSON, JSONL, CSV, Markdown, and text under explicit local or temporary paths; some SHA-256 receipts | artifact hashes and timestamps do not establish canonical market-record identity |
| dependencies | `pyproject.toml` has no runtime dependencies and only a pytest test extra; no tracked lock file | Arrow, Parquet, DuckDB, and Polars are not installed |
| official client | sandbox candidate only; no `src/` import, project dependency, authentication, credentials, signing, or orders | current stdlib public adapter remains active; migration remains separately gated |

Naming collisions and ambiguities are locked as follows:

- legacy `captured_at_utc`, `snapshot_timestamp`, `snapshot_time_utc`,
  `local_capture_time_utc`, and `observed_at_utc` do not silently become any
  canonical time field;
- Gamma `id`, `conditionId`, CLOB `market`, `asset_id`, and local `market_id`,
  `condition_id`, `token_id`, or `asset_id` require explicit namespaced mapping;
- a source URL is a reference, not `source_id` or `source_snapshot_id`;
- a source order-book `hash` is not the project canonical payload hash;
- `resolution_date`, a current question/title, and manual rule text are not a
  point-in-time resolution-rule snapshot;
- local file paths, file modification times, labels, slugs, titles, questions,
  tickers, and URLs are never canonical entity identities.

## 4. Canonical Identity Model

All accepted IDs are opaque strings after validation. Source-native identifiers
must be namespaced by platform and source. Aliases are explicit immutable alias
records; they never silently replace an identity. A record version cannot
change its canonical entity identity after creation.

### 4.1 Domain Identities

| ID | Classification | Contract |
|---|---|---|
| `platform_id` | deterministic-derived registry ID | derived from a controlled platform registry key; never from display text |
| `event_id` | source-native when present; otherwise deterministic-derived | namespace the upstream event ID; derived fallback may use only stable platform/source identity and stable upstream semantic keys |
| `market_id` | source-native when present; otherwise deterministic-derived | namespace the upstream market ID; `condition_id`, slug, question, and URL are aliases or attributes unless explicitly registered |
| `token_id` | source-native when present; otherwise deterministic-derived | namespace the upstream asset/token ID; outcome label is not identity |
| `source_id` | deterministic-derived registry ID | identifies an approved source family and platform; a mutable URL alone is insufficient |
| `resolution_source_id` | deterministic-derived registry ID | identifies a registered resolution authority/source separately from ordinary market-data sources |

When an upstream ID is missing, a later implementation may derive an ID only
from `platform_id`, `source_id`, record family, and stable upstream semantic
keys explicitly allowlisted by that schema. Display names, titles, questions,
slugs, tickers, mutable URLs, prices, liquidity, outcomes learned later,
filesystem paths, observation order, and local clock values are forbidden
derived-ID inputs. The full preimage and derivation version must be recorded.
If two non-equivalent entities collide, both inputs are quarantined with an
identity-conflict code; no suffix, overwrite, or silent merge is allowed.

### 4.2 Observation, Snapshot, Schema, And Version Identities

| ID | Classification | Contract |
|---|---|---|
| `observation_id` | deterministic-derived | identifies one source assertion/observation claim from record family, canonical entity IDs, source snapshot, and stable source assertion identity |
| `snapshot_id` | implementation-generated | identifies one coherent capture boundary; fixtures may use deterministic caller-supplied IDs and never require random UUIDs |
| `source_snapshot_id` | deterministic-derived | identifies `source_id`, capture identity, `observed_time`, and raw-content hash together |
| `resolution_rule_snapshot_id` | deterministic-derived | identifies event/market, resolution source, source snapshot, and rule-content hash |
| `ingestion_batch_id` | implementation-generated | identifies one bounded acceptance batch; deterministic caller-supplied fixture IDs are permitted |
| `schema_id` | deterministic-derived registry ID | identifies record family plus schema family independently of a schema version |
| `record_version_id` | deterministic-derived | unique content-derived ID for one immutable audit-envelope version |
| `supersedes_record_version_id` | reference to classified ID | optional direct predecessor; never reused as the new version ID |
| `lineage_parent_ids` | ordered references to classified IDs | direct immutable parents only; duplicates and cycles fail closed |

Every accepted record version has exactly one unique `record_version_id`.
`observation_id` identifies a claim; `snapshot_id` identifies a coherent capture.
A correction or lifecycle change creates a new record version. No random UUID
is required for deterministic fixtures.

## 5. Observation Envelope And Three-Time Semantics

Every future normalized or quarantine record envelope must identify its record
family, schema, canonical entities, observation or snapshot, source snapshot,
record version, lineage, validation state, and the applicable time fields.

The time order is exactly:

1. `event_time`
2. `observed_time`
3. `ingestion_time`

### 5.1 `event_time`

`event_time` is when the represented domain event or state is asserted by the
source to have occurred or become effective: for example, trade execution,
order-book update, market opening/closing, or a source-declared rule effective
time. It may be absent only when the record-family schema explicitly permits
absence because the source supplies no meaningful domain-event time. Absence
is explicit; `observed_time` or `ingestion_time` may not be substituted. Source
text, precision, and timezone metadata may be preserved in the raw envelope.

### 5.2 `observed_time`

`observed_time` is when the project observation boundary first received or
captured the source content. It is required for every observation and snapshot,
is never backdated to `event_time`, and remains the actual import time for a
replay or imported historical source.

### 5.3 `ingestion_time`

`ingestion_time` is when a record version was accepted into the canonical local
data layer. It is required for every accepted normalized or quarantine record.
It must not precede `observed_time`; an exception is not acceptance but an
explicit clock-anomaly failure state. `ingestion_time` determines canonical
availability unless a separately approved contract adds publication/commit
time.

### 5.4 Format, Precision, Clock, And Ordering

- UTC only; timezone-aware RFC 3339; canonical UTC offset is `Z`.
- Naive local datetimes are invalid.
- Precision is explicit and never fabricated.
- Original timestamp text, declared timezone, and source precision may remain
  in raw metadata.
- Missing source time, clock anomaly, invalid timezone, and precision loss have
  deterministic bounded failure or warning codes.
- Filesystem modification time is never a canonical time.

Default deterministic record ordering is:

1. `ingestion_time`;
2. `observed_time`;
3. `event_time` when present, with explicit null ordering;
4. `record_version_id`.

Point-in-time replay never sorts solely by `event_time`.

## 6. Point-In-Time Visibility And As-Of Queries

No-look-ahead invariant:

> A record version is not visible to an as-of query before its
> `ingestion_time`.

The cutoff types are:

- `AS_OF_INGESTION_TIME` — default reproducible research visibility;
- `AS_OF_OBSERVED_TIME` — diagnostic comparison only;
- `EVENT_TIME_WINDOW` — a domain-time filter applied only after visibility.

For cutoff `T`, the deterministic algorithm is:

1. retain only versions with `ingestion_time <= T`;
2. for `AS_OF_OBSERVED_TIME`, additionally require `observed_time <= T`; this
   never admits a version ingested after `T`;
3. apply only lifecycle, correction, supersession, revision, or retraction
   events whose own `ingestion_time <= T`;
4. resolve each visible chain without replacing or deleting prior versions;
5. exclude quarantine and contract-invalid versions from valid research views,
   while counting them;
6. apply any `EVENT_TIME_WINDOW` to the already-visible result;
7. order by the canonical ordering rule and emit the audit receipt.

Later correction, rule clarification, source snapshot, settlement/outcome,
price, liquidity, wallet performance, or quality knowledge cannot change a
prior result. A “latest” query without a cutoff is not point-in-time safe.

Every future query result records cutoff type and value, supported schema/version,
ordered included `record_version_id` values or their deterministic result hash,
query/transform version, parameters, and exclusion/failure counts.

## 7. Append-Only Lifecycle

History posture:

`NO_DESTRUCTIVE_HISTORY_REWRITE`

Accepted records are append-only. Lifecycle states are:

1. `RAW_CAPTURED`
2. `NORMALIZED_ACCEPTED`
3. `QUARANTINED`
4. `SUPERSEDED`
5. `RETRACTED_BY_SOURCE`
6. `INVALIDATED_BY_CONTRACT`

A lifecycle change is a new immutable event/version, never an in-place update.
Superseded records remain queryable for historical reconstruction. Retraction
is not deletion. Contract-invalid data remains auditable but is excluded from
valid research views. Physical retention, deletion, privacy, and compaction are
separately gated and cannot silently alter logical history. Later source
deletion does not erase prior observation identity or lineage, subject to a
future legal/privacy policy.

## 8. Raw, Normalized, And Quarantine Boundaries

### 8.1 Raw

Raw capture preserves exact source bytes/content and retrieval context for
audit and reprocessing. Its envelope includes source ID and reference,
`observed_time`, media type, response/status metadata where applicable,
retrieval method/version, raw-content SHA-256, byte length, and access
classification. It stores no credential, secret, authenticated header, or
unsafe auth material and makes no validity claim. WP155 authorizes no raw
writer.

### 8.2 Normalized

Normalized data is validated canonical data suitable for deterministic research.
It includes schema ID/version, canonical entity IDs, three-time fields,
source/source-snapshot references, canonical payload and hash, immutable
lineage, validation status, and no raw credential/auth material. Unknown fields
are never silently discarded.

### 8.3 Quarantine

Quarantine retains invalid, ambiguous, incomplete, conflicting, unsupported, or
contract-incompatible input without treating it as valid. It includes a
quarantine record ID, source/raw reference, bounded ordered failure codes,
observed and ingestion times, failed schema/version, safe bounded diagnostics,
operator-review status, and reprocessing lineage. It never echoes secrets or
unsafe raw data.

Quarantined records are not silently dropped and are not visible in valid
research views. Promotion requires a new deterministic validation result and a
new record version; the quarantined version remains immutable.

## 9. Duplicate, Arrival, Revision, And Conflict Semantics

| Classification | Meaning | Required action |
|---|---|---|
| `EXACT_DUPLICATE` | same canonical source/content identity and semantic record | retain receipt/audit count, link capture to original, and do not add a second valid semantic state unless the schema requires a distinct capture |
| `SEMANTIC_DUPLICATE` | different raw representation, same canonical assertion | compare deterministically, retain capture/source lineage, and never silently merge conflicting sources |
| `LATE_ARRIVAL` | observed or ingested outside the expected interval for its `event_time` | preserve real times, mark late, never backdate, and expose only in later as-of views |
| `SOURCE_REVISION` | source republishes or changes a record or rule | create source snapshot and record version, reference prior version, classify changed fields, preserve both |
| `PROJECT_CORRECTION` | project fixes parsing, mapping, identity, or normalization | create record version with reason, code/schema version, superseded reference, and correction ingestion visibility |
| `SOURCE_RETRACTION` | source explicitly withdraws prior content | create retraction version, preserve prior record, apply only after retraction ingestion |
| `CONFLICT` | accepted sources/snapshots assert incompatible facts | retain all source-specific versions; quarantine or label by later deterministic policy; require source hierarchy and operator review |

No classification authorizes destructive replacement or retroactive visibility.

## 10. Source And Resolution-Rule Snapshots

A source snapshot contains at minimum:

- `source_snapshot_id`, `source_id`, source type, and canonical source reference;
- `observed_time`, `ingestion_time`, retrieval method/version, and media type;
- source-content SHA-256 and byte length;
- upstream revision, ETag, or last-modified values when available;
- prior/parent snapshot ID when applicable;
- validation state, access classification, and non-authority notice.

A resolution-rule snapshot contains at minimum:

- `resolution_rule_snapshot_id`, `event_id`, `market_id`;
- `resolution_source_id`, `source_snapshot_id`;
- original rule text/content hash and only deterministically supported normalized
  rule fields;
- source-declared effective time when present, `observed_time`, and
  `ingestion_time`;
- ambiguity labels, source hierarchy/rank reference, superseded snapshot ID,
  revision/correction type, validation state, and human-review state.

Resolution rules are point-in-time data. A later clarification cannot be used
in an earlier analysis. A URL or content hash alone is not a stable source
snapshot. Resolution source and ordinary market-data source are distinct.
Normalization preserves original snapshot lineage. WP155 implements no
settlement logic.

## 11. Canonical Serialization, Hashes, And Lineage

Hash posture:

- SHA-256 with an explicit algorithm/version token;
- UTF-8;
- deterministic field ordering;
- explicit nulls;
- canonical `Z` timestamps and locale-independent number formatting;
- no NaN or Infinity;
- no environment or absolute paths;
- no serialization-generated timestamps.

Hash families are distinct:

| Hash family | Included | Excluded |
|---|---|---|
| raw-content hash | exact source bytes only | retrieval envelope, paths, timestamps, credentials |
| canonical payload hash | hash version, schema ID/version, record family, canonical entity IDs, explicit event-time/null, source assertion fields, normalized payload, source-content hash/reference where applicable | record-version ID, batch ID, observed/ingestion time, local path, operator note, diagnostics, lifecycle state |
| record-version hash / ID | hash version, payload hash, observation/snapshot/source-snapshot IDs, observed/ingestion time, direct lineage parents, superseded ID, lifecycle/classification, normalizer/validator versions, parameter-set ID | environment path, wall-clock generation time, unbounded diagnostics |
| query-result hash | query/transform version, cutoff type/value, schema support set, deterministic parameters, ordered included record-version IDs, exclusions/failure counts | elapsed time, machine path, process ID, memory measurement |
| future file/manifest hash | exact immutable file bytes or canonical manifest payload as separately specified | mutable catalog pointer, filesystem metadata |

Every normalized record version references raw/source snapshot IDs, direct
lineage parents, schema ID/version, normalizer/validator version, canonical
payload hash, applicable source-content hash, transformation parameters or
parameter-set ID, and—when later implemented—a validation receipt/result ID.
Operational fields excluded from content identity remain in the immutable audit
envelope. Lineage cycles, missing parents, duplicate parents, and hash mismatch
fail closed.

## 12. Schema Evolution

Schemas use semantic versions:

- major: incompatible field or meaning change;
- minor: backward-compatible optional/additive change;
- patch: clarification or validation hardening that does not change valid
  serialized meaning.

Readers declare supported versions. Unknown major versions fail closed. Unknown
fields are never silently discarded during canonical conversion. Required-field
removal is major. Unit, precision, timezone, identity, or semantic changes are
major unless a proved backward-compatible mapping exists.

Migration is append-only and lineage-preserving; it never overwrites the source
record. Each migrated version records source/destination schema versions,
migration code version, input/output record IDs, and hashes. WP155 implements no
migration.

## 13. Parquet And Arrow Architecture Decision

Decision:

`PARQUET_ARROW_PREFERRED_BUT_NOT_INSTALLED`

Arrow is the preferred future typed in-memory/interchange schema candidate.
Parquet is the preferred future immutable research-file candidate. Neither is
authoritative for repository identity, time, correction, lineage, quarantine,
visibility, or validation semantics.

Preferred future logical layout:

- one dataset per record family and schema major;
- immutable files referenced by a manifest/catalog;
- no one-file-per-record design;
- no default market-ID directory explosion;
- low/moderate-cardinality ingestion dimensions only.

Initial partition contract:

`record_family / schema_major / ingestion_date_utc`

Additional partitions require measured selectivity and file-count evidence.
Raw question/title, URL, wallet address, token ID, market ID by default, and
other high-cardinality values are forbidden partitions.

Future benchmarks may evaluate within-file/row-group ordering by platform/entity
IDs, `ingestion_time`, `observed_time`, `event_time`, and record version. No
physical sort is authorized now.

A future file/manifest contract must define deterministic filenames, schema
metadata, min/max time statistics, row count, hashes, record family/schema
version, creator/version, source batches, manifest lineage, atomic publication,
partial-write recovery, small-file limits, and history-preserving compaction.
WP155 installs nothing and creates no writer or dataset.

## 14. DuckDB And Polars Benchmark Contract

Decision:

`BENCHMARK_REQUIRED_NO_ADOPTION_DECISION`

A later separately approved benchmark compares a repository-native/stdlib
reference where practical, DuckDB, Polars, and Arrow/Parquet round trips.
Semantic correctness is the primary gate and cannot be overridden by speed.

Required synthetic fixture families are ordered observations, out-of-order
event times, late arrivals, exact and semantic duplicates, source revisions,
project corrections, source retractions, conflicting sources, missing event
time, timestamp precision variants, schema-version variants, quarantine cases,
resolution-rule changes, and high/low-selectivity as-of queries.

Required operations are as-of reconstruction, event-time window after
visibility, latest visible version per entity, source-specific history,
correction chain, quarantine exclusion/count, deterministic result hash,
projection, predicate filtering, and bounded event/market/token/source joins.

Outputs include semantic equality to reference, result hash, elapsed time,
peak/estimated memory where measurable, input/output rows, file count/size,
warnings, tool/version, exact command/config, and repeatability. The benchmark
is local, finite, operator-initiated, synthetic or separately approved
sanitized-fixture only, and has no provider/network, credentials, scheduler, or
persistent production writer. DuckDB and Polars remain uninstalled.

## 15. Validation And Failure Vocabulary

Validation states:

- `VALID`
- `VALID_WITH_WARNINGS`
- `QUARANTINED`
- `REJECTED_CONTRACT`
- `UNSUPPORTED_SCHEMA`
- `CONFLICT_REQUIRES_REVIEW`

Bounded failure/warning families cover identity missing/invalid/conflict;
timestamp missing/naive/invalid/order anomaly; source missing/unsupported; hash
mismatch; duplicate classification failure; correction/supersession lineage
failure; unknown schema major or field; unit/precision mismatch; invalid numeric
value; unsafe/secret-like field; quarantine required; as-of/look-ahead
violation; partition/manifest mismatch; and resolution-rule ambiguity/conflict.

Failure is closed, deterministic, ordered, and bounded. It returns no partial
accepted object, performs no unsafe echo, and applies no automatic correction
unless a future approved normalizer contract explicitly permits it.

## 16. No-Look-Ahead Negative Matrix

| Forbidden use | Required rejection |
|---|---|
| future settlement/outcome in prior features | `AS_OF_LOOK_AHEAD_VIOLATION` |
| correction before its ingestion time | `CORRECTION_VISIBILITY_VIOLATION` |
| current title/rule for an earlier snapshot | `SOURCE_SNAPSHOT_AFTER_CUTOFF` |
| future wallet profitability to select earlier cohorts | `FUTURE_SELECTION_KNOWLEDGE` |
| future liquidity/fill evidence in prior maker evaluation | `FUTURE_MARKET_STATE` |
| settlement-known labels without permitted lag | `LABEL_AVAILABILITY_VIOLATION` |
| historical in-place rewrite after normalization fix | `DESTRUCTIVE_HISTORY_REWRITE` |
| future inclusion/exclusion knowledge | `FUTURE_SELECTION_KNOWLEDGE` |
| filesystem modification time as canonical time | `INVALID_TIME_SOURCE` |
| latest-record query without cutoff | `MISSING_AS_OF_CUTOFF` |
| event-time filter as the only safety filter | `VISIBILITY_FILTER_MISSING` |

Every future experiment references a fixed data manifest/snapshot and as-of
cutoff.

## 17. Authority Boundary

The deterministic data layer exclusively owns identity and schema validation,
timestamp validation, point-in-time visibility, duplicate/correction
classification, hashes, lineage, quarantine, as-of construction, and future
deterministic export/manifest validation.

AI/Hermes may suggest source relationships, ambiguity labels, possible
duplicate/correction relationships, critiques of quality reports, and
investigation questions. AI/Hermes may not create canonical IDs, validate
records, select accepted versions, resolve conflicts, backdate data, promote
quarantine data, alter hashes/lineage, define visibility, approve migration, or
authorize storage, network, paper, or live behavior.

Arrow, Parquet, DuckDB, Polars, and external SDKs may not become authority over
project semantics.

## 18. Compatibility / Impossibility Check

| Required behavior | Controlling repo mechanism | Allowed | Compatible | Decision |
|---|---|---:|---:|---|
| three-time PIT semantics | new canonical contract; legacy snapshot models inspected only | YES | YES | document exact mapping prohibition; no migration |
| append-only version lineage | new contract; legacy JSONL writer unchanged | YES | YES | architecture contract only |
| Arrow/Parquet preference | WP154 registry plus official format docs | YES | YES | preferred but uninstalled |
| DuckDB/Polars evaluation | WP154 deferral plus bounded benchmark contract | YES | YES | no adoption or dependency |
| current adapter compatibility | `src/data_layer/polymarket/` read-only inventory | READ ONLY | YES | preserve current runtime behavior |
| exact WP155 docs/status/tests scope | current merged branch-scope guards | YES | YES WITH REPAIR | two pre-existing guards failed on clean merged `main`; apply minimal branch-aware test compatibility edits |
| writer, validator, fixture, collector, migration, query engine | protected/non-authorized scope | NO | NO | defer; do not implement |
| authenticated SDK, dependency, lock, config, runtime network | protected boundaries | NO | NO | stop if required |

## 19. Requirement-To-Evidence Traceability

| Requirement | Evidence |
|---|---|
| label, posture, lineage, authority | Sections 1–2 |
| repo field/time/storage inventory | Section 3 |
| identity classifications and collision handling | Section 4 |
| exact three-time and ordering semantics | Section 5 |
| ingestion-time visibility and query receipts | Section 6 |
| append-only lifecycle and boundaries | Sections 7–8 |
| duplicate/revision/correction/retraction/conflict | Section 9 |
| source and resolution-rule snapshots | Section 10 |
| serialization, hash families, lineage | Section 11 |
| schema compatibility and append-only migration | Section 12 |
| Parquet/Arrow and partition decisions | Section 13 |
| DuckDB/Polars bounded benchmark | Section 14 |
| failure vocabulary and no-look-ahead negatives | Sections 15–16 |
| deterministic/AI/external-tool authority | Section 17 |
| impossibility and package boundary | Section 18 |
| official source verification | Section 20 |
| deferred implementation | Section 21 and `docs/deferred_items_log.md` |

## 20. Official Source Observation Register

Observed 2026-07-26. These sources document external capabilities and upstream
field surfaces only; they do not supply repository semantics.

| Source | URL | Bounded observation |
|---|---|---|
| Apache Arrow columnar format | https://arrow.apache.org/docs/format/Columnar.html | language-agnostic in-memory columnar structures, typed timestamps, null representation, and implementation-owned mutation coordination |
| Apache Parquet documentation | https://parquet.apache.org/docs/ | column-oriented file format and specification index |
| Apache Parquet concepts | https://parquet.apache.org/docs/concepts/ | files contain row groups, row groups contain column chunks, and column chunks contain pages |
| DuckDB Parquet | https://duckdb.org/docs/stable/data/parquet/overview | Parquet scans, schema/metadata access, multi-file reads, and filter/projection pushdown |
| Polars lazy API | https://docs.pola.rs/user-guide/lazy/ | lazy query planning and schema checking before processing |
| Polars lazy optimizations | https://docs.pola.rs/user-guide/lazy/optimizations/ | predicate, projection, slice, common-subplan, join, and expression optimizations |
| Polymarket market-data overview | https://docs.polymarket.com/market-data/overview | event/market model; markets map to condition, question, address, and token IDs; public market data surfaces |
| Polymarket events | https://docs.polymarket.com/api-reference/events/list-events | event `id`, titles/slugs, dates, `resolutionSource`, nested markets, and update fields |
| Polymarket markets | https://docs.polymarket.com/api-reference/markets/list-markets | market `id`, `conditionId`, `questionID`, `clobTokenIds`, outcomes, dates, status, resolution, and update fields |
| Polymarket order book | https://docs.polymarket.com/api-reference/market-data/get-order-book | condition in `market`, token in `asset_id`, source `timestamp`, source `hash`, bids/asks, tick/size fields |
| Polymarket public trades | https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets | asset/token, condition, transaction hash, price/size, side, outcome, and timestamp fields |
| Polymarket resolution | https://docs.polymarket.com/concepts/resolution | rules distinguish resolution source, end date, and edge-case handling; title alone does not define resolution |

The upstream surface is mutable and sometimes uses different names or timestamp
representations for related concepts. Exact raw source text and precision must
therefore remain available to later approved implementations; no upstream field
is silently promoted into a canonical project identity or time.

## 21. Deferred Implementation And Next Gate

Writing this contract resolves WP154-D002 only for the architecture-level
Parquet/Arrow point-in-time storage-contract decision. It does not resolve a
writer, dependency, schema implementation, dataset, migration, or production
storage item. WP154-D003 remains open: this document defines the future bounded
benchmark contract, but no representative implementation dataset, dependency,
or benchmark execution exists.

All implementation items remain separately gated in
`docs/deferred_items_log.md`.

Recommended next package, not implemented here:

`WP156 — BOUNDED POINT-IN-TIME OBSERVATION SCHEMA VALIDATOR AND SYNTHETIC FIXTURE IMPLEMENTATION`

Expected WP156 scope is stdlib-only immutable conceptual records, deterministic
validators, canonical serialization and SHA-256, three-time and
duplicate/correction/supersession validation, source/rule snapshot validation,
and a sanitized synthetic in-memory fixture corpus. It authorizes no Arrow,
Parquet, DuckDB, Polars, file writer, collector, provider/network, credential,
scheduler, strategy, paper, or live behavior. WP156 requires separate approval.

## 22. Forbidden Interpretations

- WP155 does not implement the data layer.
- Parquet storage is not active.
- DuckDB is not adopted.
- Polars is not installed.
- Historical records are not updated in place.
- Corrections do not apply retroactively.
- Event time does not determine repository availability.
- Latest data is not automatically safe for backtesting.
- Quarantine data is not valid research data.
- AI/Hermes may not resolve conflicts.
- WP155 does not authorize market-data collection.
- WP155 does not enable paper trading.
- WP156 is not implemented.

## 23. Decision

The point-in-time market research foundation is contractually defined. The
default reproducible visibility boundary is ingestion time, history is
append-only, corrections and retractions are never backdated, source and
resolution-rule content is snapshotted with lineage, and external formats/tools
remain non-authoritative candidates. Implementation remains blocked behind a
separately approved work package.
