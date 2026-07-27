# Point-In-Time Observation Schema Validator And Synthetic Fixture Implementation

## 1. Decision And Implementation Status

WP156 implements the first bounded deterministic code layer beneath
`POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT`.

```text
Implementation posture:
LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION
Supported record families:
3
Supported observation kinds:
3
Synthetic cases:
20
Dependencies added:
0
Persistent writers:
0
Query engines:
0
Product/runtime network behavior:
0
Credential or authenticated-client behavior:
0
Scheduler or background behavior:
0
Strategy, paper, order, risk, or execution authority:
0
```

The implementation converts explicit caller-supplied Python mappings into
frozen records or bounded fail-closed results. It does not fetch, load, scan,
persist, schedule, migrate, collect, poll, or query data.

## 2. PR #155 Merge Lineage

- PR #155 final implementation head:
  `54f0aa3afd9c7713ba62448526a39ff32442f92c`.
- PR #155 merge commit:
  `bbb8ab91b96a1a469036189c0d7a9b2a85c9030c`.
- Local `main` and `origin/main` after the WP156 Remote Main Sync Gate:
  `bbb8ab91b96a1a469036189c0d7a9b2a85c9030c`.
- Relation: synchronized `main` exactly equaled the PR #155 merge commit and
  contained no later commit at WP156 branch creation.
- Generated-artifact guard: PASS.
- Existing WP156 branch or open PR before branch creation: none.

The clean merged-main compatibility probe ran 229 tests. It produced 228
passes and one pre-existing failure: WP155's exact nine-file scope regression
continued to demand its branch diff after WP155 was already merged. WP156
therefore includes one minimum branch-aware compatibility repair in
`tests/test_point_in_time_market_research_data_foundation_contract_docs.py`.
The repair disables only the historical WP155 branch-diff assertion after the
WP155 status fragment exists on `origin/main`; every successor WP retains its
own exact-scope gate.

## 3. Authority / Non-Authority Posture

The Centralized Boundary Group Reference in
`docs/ai/codex/PROTECTED_PATHS.md` is binding. WP156 crosses none of
`credentials/secrets`, `authenticated clients`, `wallet/account behavior`,
`order placement/cancel`, `execution gateway`, `paper engine`,
`scheduler/bot loop`, `runtime/daemon`, `dashboard/deployment`,
`dependency/lock changes`, `external code copying`, or `generated artifacts`.

WP156 has implementation authority only for:

- the isolated stdlib package under
  `src/data_layer/point_in_time_market_research/`;
- frozen in-memory records and results;
- bounded canonical JSON and SHA-256;
- three explicit mapping-to-record builders;
- finite in-memory record-batch validation;
- the exact sanitized 20-case in-memory corpus;
- focused tests and repo-truth evidence.

It has no authority for legacy snapshot-model modification, a writer, reader,
manifest, database, query engine, collector, WebSocket, scheduler, CLI,
migration, provider/account/credential access, real fixtures, strategy,
signal, replay/fill, paper, order, accounting, risk, reconciliation,
execution, restricted live, live trading, or WP157.

## 4. Public Package Surface

The public package is:

`src/data_layer/point_in_time_market_research/`

It exports only these constants:

1. `FOUNDATION_LABEL`
2. `IMPLEMENTATION_POSTURE`
3. `SUPPORTED_SCHEMA_ID`
4. `SUPPORTED_SCHEMA_VERSION`
5. `SUPPORTED_RECORD_FAMILIES`
6. `SUPPORTED_OBSERVATION_KINDS`
7. `LIFECYCLE_STATES`
8. `RECORD_CLASSIFICATIONS`
9. `VALIDATION_STATUSES`

It exports only these frozen dataclasses:

1. `PointInTimeEnvelope`
2. `MarketObservationRecord`
3. `SourceSnapshotRecord`
4. `ResolutionRuleSnapshotRecord`
5. `QuarantineDescriptor`
6. `PointInTimeBuildResult`
7. `PointInTimeBatchValidationResult`
8. `SyntheticPointInTimeCase`

It exports only these functions:

1. `canonical_json_bytes`
2. `sha256_hex`
3. `build_market_observation`
4. `build_source_snapshot`
5. `build_resolution_rule_snapshot`
6. `validate_record_batch`
7. `get_synthetic_point_in_time_cases`
8. `load_synthetic_case_input`

Internal constants and helpers are not part of `__all__`.

## 5. Locked Constants And Vocabularies

```text
FOUNDATION_LABEL =
POINT_IN_TIME_APPEND_ONLY_MARKET_RESEARCH_DATA_CONTRACT

IMPLEMENTATION_POSTURE =
LOCAL_OFFLINE_STDLIB_ONLY_IN_MEMORY_VALIDATION

SUPPORTED_SCHEMA_ID =
point-in-time-market-research-record

SUPPORTED_SCHEMA_VERSION =
1.0.0
```

Record families, in canonical order:

1. `MARKET_OBSERVATION`
2. `SOURCE_SNAPSHOT`
3. `RESOLUTION_RULE_SNAPSHOT`

Observation kinds, in canonical order:

1. `MARKET_METADATA`
2. `ORDER_BOOK`
3. `PUBLIC_TRADE`

The six lifecycle states, eight record classifications, and six validation
statuses exactly match WP155 and the WP156 execution package. Ordered tuples
are the canonical vocabulary; internal frozen sets are lookup aids only.

## 6. Immutability And Output Invariants

Every public dataclass uses `@dataclass(frozen=True)`. Repeated scalar fields
are tuples. Arbitrary payloads are stored only as deterministic canonical JSON
text. No successful record retains a caller mapping, list, nested object,
environment value, local path, clock-generated value, or random value.

A valid build result has one record, no quarantine descriptor, no error, and
status `VALID` or `VALID_WITH_WARNINGS`. An invalid result has no record, a
bounded ordered error tuple, an invalid status, and a safe quarantine
descriptor whenever the top-level structure is a mapping.

All public result fields are enumerated and tested. Tests recursively scan full
invalid result objects. No manual public-result serializer is used; direct
dataclass recursion and `dataclasses.asdict` cover every public field.

A hand-built dictionary is not a full output-surface scan unless a field-coverage test
proves it covers every public field.

## 7. Canonical JSON

`canonical_json_bytes` accepts only:

- `None`;
- `bool`;
- `int`;
- `str`;
- mappings with string keys;
- lists and tuples containing accepted values.

Keys are lexicographically sorted, sequence order is retained, explicit nulls
remain, Unicode is emitted directly, output is UTF-8, separators are exactly
`(",", ":")`, and whitespace is absent. Floats—including finite values, NaN,
and Infinity—are rejected. Bytes, bytearray, sets, Decimal, datetime, arbitrary
objects, non-string keys, and custom dataclasses are rejected without implicit
conversion.

Bounds are:

- maximum depth: 8;
- maximum visited nodes: 1,024;
- maximum keys per mapping: 128;
- maximum sequence items: 256;
- maximum string length: 4,096 code points;
- maximum encoded bytes: 65,536.

Failures raise only a neutral stable `ValueError` code.

## 8. Hash Families And Exact Preimages

`sha256_hex` accepts bytes or UTF-8 text and returns lowercase 64-character
SHA-256.

The canonical payload hash is the hash of exact canonical payload bytes.

The observation ID is `obs:sha256:` plus the hash of:

- schema ID/version;
- record family;
- observation kind;
- platform/event/market/token/source identities;
- source snapshot ID;
- stable caller-supplied source assertion ID.

The source snapshot ID is `srcsnap:sha256:` plus the hash of:

- source ID;
- observed time;
- raw-content SHA-256;
- byte length;
- media type.

The resolution-rule snapshot ID is `rulesnap:sha256:` plus the hash of:

- event ID;
- market ID;
- resolution source ID;
- source snapshot ID;
- rule-content SHA-256.

The record version ID is `record:sha256:` plus the hash of:

- schema ID/version and record family;
- canonical payload hash;
- observation/snapshot/source-snapshot/rule-snapshot IDs;
- observed, ingestion, and explicit event-time/null;
- ordered direct lineage parents;
- explicit supersedes ID/null;
- lifecycle and classification;
- normalizer, validator, and parameter-set versions.

Diagnostics, warnings, duration, environment, paths, process identity, object
representation, and wall-clock generation time are excluded.

Fixed synthetic record-version evidence includes:

- C01:
  `record:sha256:2dd194cb035ab38076c98b0fbbdd955cb59081a3e52398f8d885a1a83c96c04e`;
- C02:
  `record:sha256:6469a6762f56408ed8cfe0d97c70493814fceebedc869976edb598fac7540d69`;
- C03:
  `record:sha256:21dc52fd502baafcea537b5f2da73bc05c02c2f77132f0fcc5b4317335188be9`;
- C04:
  `record:sha256:3bb6ea87ab55516736ac96934c3079d32c2caf6d74e32940da457388cca7a623`;
- C05:
  `record:sha256:24ba8feb38a42bbf112cc4813bb7998955986d99265131681e32219d1bedd852`.

Focused tests independently assert canonical bytes, empty/`abc` SHA-256, a
canonical fixture digest, and these fixed record IDs.

## 9. ID And Time Validation

IDs are non-empty printable ASCII strings, at most 256 characters, using only
letters, digits, `.`, `_`, `-`, and `:`. Domain/source IDs require a namespace
colon. Whitespace, controls, and filesystem separators fail closed. Derived
IDs are recomputed; optional caller assertions must match exactly.

Timestamps accept timezone-aware RFC 3339 UTC only with `Z` or `+00:00` and
zero to six fractional digits. `+00:00` normalizes to `Z`; supplied fractional
precision is preserved. Naive values, non-UTC offsets, leap seconds, date-only
values, whitespace, and more than six fractional digits fail closed.

`ingestion_time >= observed_time` is mandatory. Event time may differ from
both; event time later than ingestion produces
`EVENT_TIME_AFTER_INGESTION`. Explicit missing event time produces
`EVENT_TIME_MISSING_ALLOWED` only for permitted families/kinds. Public trades
require event time.

No implementation calls a wall clock, random generator, UUID generator, or
environment source.

## 10. Record Builders

### Market Observations

The builder supports only metadata, order-book, and public-trade observations.
Metadata requires question text, status, and outcome labels. Order books
require bids, asks, tick size, minimum size, token identity, and decimal-string
price/size levels. Public trades require token and event time, decimal-string
price/size, one observed-side value, and a transaction reference.

Unknown fields, unsafe nested keys, floats, invalid decimals, unsupported
schema/family/kind, and identity/time/lineage defects fail closed.

### Source Snapshots

The source builder accepts only three public/synthetic source types and only
`PUBLIC` or `SANITIZED_SYNTHETIC` access. It accepts raw-content SHA-256 and
byte length but never raw bytes or a raw body. The source snapshot ID is
derived. Prior snapshot identity is immutable lineage metadata and does not
replace history.

### Resolution-Rule Snapshots

The rule builder implements the exact ambiguity, source-rank, and review-state
allowlists. It retains only a rule-content hash plus bounded sanitized
canonical payload. Any ambiguity requires human review. Conflicting source
text requires conflict classification and produces
`CONFLICT_REQUIRES_REVIEW`; it is not an accepted authoritative resolution.
No settlement or outcome decision is implemented.

## 11. Safe Quarantine

`QuarantineDescriptor` is in-memory only. Its fingerprint uses sorted
top-level key names, canonical type names, and allowlisted safe structural
fields. It never retains raw input, raw source text, secret values, arbitrary
exception messages, tracebacks, paths, or unbounded diagnostics.

The ID is `quarantine:sha256:` plus a hash of the structural fingerprint and
ordered codes. Operator review and safe-diagnostics-only flags are always
true. No automatic promotion exists.

## 12. Batch And Lineage Validation

`validate_record_batch` accepts at most 256 exact public record objects and an
optional finite set of known external parent IDs. It performs no lookup.

It verifies:

1. exact record types;
2. batch bound;
3. record-version recomputation;
4. identical repeated records accepted once and acknowledged;
5. same-ID/different-content collision rejection;
6. unique, non-self, known parents;
7. acyclic lineage;
8. supersedes presence and parent visibility;
9. entity compatibility for correction/revision/retraction;
10. exact-duplicate payload and identity equality;
11. semantic-duplicate observation and identity equality;
12. non-backdated corrections, revisions, and retractions;
13. retraction lifecycle;
14. conflict quarantine/review behavior;
15. deterministic ordering by ingestion, observation, explicit-null event
    time, and record-version ID;
16. a canonical batch SHA-256 over accepted, duplicate, quarantined, error,
    and warning tuples.

It does not reconstruct an as-of state, choose a source, resolve a conflict,
migrate a schema, persist output, or implement WP157.

## 13. Error And Warning Vocabulary

The implementation defines the full bounded WP156 error vocabulary for
schema/field, identity, time, payload/safety, lineage/classification,
source/rule, hash, and batch-bound failures. Codes are deduplicated and sorted
by one canonical tuple plus stable occurrence order.

Warnings use the exact ordered vocabulary:

1. `EVENT_TIME_AFTER_INGESTION`
2. `EVENT_TIME_MISSING_ALLOWED`
3. `LATE_ARRIVAL_DECLARED`
4. `SOURCE_REVISION_DECLARED`
5. `PROJECT_CORRECTION_DECLARED`
6. `SOURCE_RETRACTION_DECLARED`
7. `SEMANTIC_DUPLICATE_DECLARED`
8. `CONFLICT_DECLARED`

Caller values never enter a code.

## 14. Exact Synthetic Corpus

The corpus has exactly these ordered IDs:

1. `PIT-C01-VALID-MARKET-METADATA`
2. `PIT-C02-VALID-ORDER-BOOK-MISSING-EVENT-TIME`
3. `PIT-C03-VALID-PUBLIC-TRADE`
4. `PIT-C04-VALID-SOURCE-SNAPSHOT`
5. `PIT-C05-VALID-RESOLUTION-RULE-SNAPSHOT`
6. `PIT-C06-VALID-LATE-ARRIVAL`
7. `PIT-C07-VALID-SOURCE-REVISION`
8. `PIT-C08-VALID-PROJECT-CORRECTION`
9. `PIT-C09-VALID-SOURCE-RETRACTION`
10. `PIT-C10-VALID-EXACT-DUPLICATE`
11. `PIT-C11-VALID-SEMANTIC-DUPLICATE`
12. `PIT-C12-CONFLICT-REQUIRES-REVIEW`
13. `PIT-C13-INVALID-NAIVE-TIME`
14. `PIT-C14-INVALID-INGESTION-BEFORE-OBSERVED`
15. `PIT-C15-INVALID-SCHEMA-MAJOR`
16. `PIT-C16-INVALID-UNKNOWN-FIELD`
17. `PIT-C17-INVALID-NESTED-SECRET-KEY`
18. `PIT-C18-INVALID-FLOAT-PAYLOAD`
19. `PIT-C19-INVALID-LINEAGE-CYCLE`
20. `PIT-C20-INVALID-CORRECTION-BACKDATE`

It uses invented identities, fixed timestamps/hashes, reserved
`example.invalid`, and no real market, wallet, account, credential, current
time, random ID, path, strategy, expected-return, order, paper, or live data.
Inputs are stored as deterministic JSON text. Each load performs `json.loads`
and returns a fresh mutable mapping.

## 15. Compatibility / Impossibility Check

| Required behavior | Controlling mechanism | Allowed | Compatible | Action |
|---|---|---:|---:|---|
| frozen PIT records and validators | isolated new stdlib package | YES | YES | implement and test |
| deterministic bounded canonical JSON/hash | WP155 Section 11 and WP156 locks | YES | YES | implement exact preimages |
| finite lineage validation | in-memory public records only | YES | YES | no lookup/query |
| sanitized corpus | in-memory JSON text only | YES | YES | exact 20 cases |
| legacy snapshot compatibility | existing `src/data_layer/polymarket/` | READ ONLY | YES | no changed legacy path |
| WP155 clean-main scope regression | historical branch-only assertion | YES WITH REPAIR | YES | one branch-aware compatibility edit |
| persistence, collector, query, migration | protected/non-authorized scope | NO | NO | defer |
| dependency, credential, runtime network, scheduler, paper/live | protected boundaries | NO | NO | stop if required |

## 16. Exact Changed-File Scope

WP156 changes exactly 16 files:

1. `src/data_layer/point_in_time_market_research/__init__.py`
2. `src/data_layer/point_in_time_market_research/records.py`
3. `src/data_layer/point_in_time_market_research/synthetic_corpus.py`
4. `tests/data_layer/point_in_time_market_research/test_records_and_synthetic_corpus.py`
5. `docs/point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md`
6. `docs/status_entries/WP156.md`
7. `docs/project_status.md`
8. `docs/repo_truth_index.md`
9. `docs/deferred_items_log.md`
10. `tests/test_project_status_docs.py`
11. `tests/test_point_in_time_market_research_data_foundation_contract_docs.py`
12. `tests/test_adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in_docs.py`
13. `tests/test_architecture_boundaries.py`
14. `tests/test_local_research_workflow_value_measurement_harness_contract_docs.py`
15. `tests/test_wallet_intelligence_architecture_contract_docs.py`
16. `tests/test_hermes_research_prompt_pack_operator_runbooks_docs.py`

The final six test files are narrow compatibility repairs: the first was
clean-main-proven in Section 2, while the WP154, architecture, WP152, and
wallet-architecture gates plus the commit-aware WP98 source guard are
successor-aware exact-scope/approved-namespace updates required by the
mandatory adjacent and full-suite validation. No
existing `src/data_layer/polymarket/` behavior, writer, reader, tool,
workflow, config, dependency, lock file, real fixture, or generated artifact
is changed.

## 17. Deferred-Item Reconciliation

WP155-D001, D002, and D003 are resolved only for the bounded local in-memory
validator, synthetic corpus, and source/rule validator delivered here. Those
resolutions confer no persistence, production-data, collector, Arrow/Parquet,
DuckDB/Polars, query, or migration authority.

WP155-D004 through D010 remain open. WP156-D001 through D010 record separately
gated as-of reconstruction, persistence, dependency/physical-schema,
benchmark, migration, retention/privacy, collector, graph, persisted
quarantine/review, and higher timestamp-precision work.

## 18. Validation And Negative Matrix

The focused regression covers exact public surface, frozen fields, field
coverage, invalid full-surface no-echo, caller immutability, canonical bytes
and limits, fixed hashes, three builders, time normalization, ID derivation,
recursive secret/authority keys, decimal strings, source/rule allowlists,
lineage/supersession/cycle/backdating, exact and semantic duplicates, record
hashes, batch bounds/order/hash, corpus order/mutation, no files, AST
side-effect boundaries, no writer/query/collector/migration, and unchanged
legacy snapshot paths.

Negative test matrix required: YES. It covers missing/null/wrong/empty fields,
unsupported schema/family/kind, unknown fields, IDs, derived-ID mismatch,
naive/non-UTC/precision/order times, floats/NaN/Infinity, unsupported objects,
all payload bounds, nested secret and authority shapes, no unsafe echo,
decimals, SHA-256, lineage duplicate/self/unknown/cycle, supersedes failures,
backdating, identity changes, duplicate mismatches, conflict review, source
access, rule allowlists, batch bound, mutation isolation, and side-effect/
dependency/protected-boundary source inspection.

Exact final validation commands, counts, exit codes, warnings, tool
availability, diff scope, and evidence mode belong in the PR body.

## 19. Requirement-To-Evidence Traceability

| Requirement | Evidence | Status |
|---|---|---|
| exact public API and vocabularies | Sections 4–5; focused export tests | SATISFIED |
| frozen/no caller reference | Section 6; frozen and mutation tests | SATISFIED |
| canonical JSON bounds | Section 7; exact/negative bound tests | SATISFIED |
| exact SHA-256/preimages | Section 8; fixed hash tests | SATISFIED |
| ID/time validation | Section 9; identity/time negative matrix | SATISFIED |
| three record builders | Section 10; positive/negative builder tests | SATISFIED |
| safe quarantine/no echo | Section 11; recursive full-result scans | SATISFIED |
| batch lineage/supersession | Section 12; chain/cycle/backdate tests | SATISFIED |
| exact 20-case corpus | Section 14; exact order/hash/mutation tests | SATISFIED |
| no side effects/dependencies | Sections 1, 3, 18; AST/behavior tests | SATISFIED |
| legacy snapshot unchanged | Sections 15–16; diff and adjacent tests | SATISFIED |
| honest deferral | Section 17; deferred-log tests | SATISFIED |
| WP157 absent | Sections 1, 3, 12, 20 | SATISFIED |

## 20. Next Separately Gated Package

Recommended, not implemented:

`WP157 — BOUNDED IN-MEMORY POINT-IN-TIME RECORD-SET RECONSTRUCTION AND AS-OF QUERY IMPLEMENTATION`

WP157 requires separate approval. WP156 contains no as-of reconstruction,
query receipt, persistence, Arrow/Parquet, DuckDB/Polars, collector, network,
credentials, scheduler, strategy, paper, or live behavior.
