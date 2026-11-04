# Source Grounding and Rule-Aware Market Discovery Contract (S10-R3-SRC-01)

Status: RUNTIME / Risk 3, offline research tooling. Module
`src/data_layer/analytical_research/source_grounding.py`; operator `tools/alpha/run_source_grounding.py`;
tests `tests/tools/alpha/test_source_grounding.py`. Posture: `RESEARCH_ONLY`. No product/provider/model
network, credentials, LLM/Hermes, forecast probability, price, edge, strategy, paper, order, capital or
live authority. No new canonical record, store or promotion path. No dependency change.

## Source pins and adaptation (no code copied)

| Capability | Upstream pin | Files | License | What is adapted |
|---|---|---|---|---|
| R3-02 | `Polymarket/agents@081f2b5594c37edeb9d3780a778c084d5b6f2743` | `agents/connectors/chroma.py`, `agents/application/prompts.py` | MIT | `PolymarketRAG.events` (event description + market linkage) and `.markets` (market question/outcome metadata) scored retrieval, re-implemented as a two-stage lexical BM25 event -> market ranker over native observed markets; `superforecaster` steps 1-2 (break the question down, gather information) as deterministic rule-grounded subquestions without any probability. Not used: Gamma client, Chroma, OpenAI embeddings, trade prompts. |
| R3-01-SOURCE_ARCHIVE | `Metaculus/forecasting-tools@a54dd6443d19745b267e99a3b0b7627e74b9a57a` | `forecasting_tools/agents_and_tools/source_archive/{pipeline,quality}.py` | MIT | `quality.evaluate` (HTTP status >= 400, minimum visible text 200, case-insensitive block signatures) and the pipeline's stored/deduped/quality_failed accounting by content hash, applied to caller-supplied local bytes. Not used: fetchers, browsers, Firecrawl, content store. Local extension: login/paywall signatures. |

Decision: ADAPT_ALGORITHM. The upstream block-signature string list is reproduced as data (13 short
phrases) for behavioural parity; no upstream function or module is imported or vendored.

## Native inputs (read-only)

- Corpus: `alpha_discovery.build_alpha_universe_snapshot(store_path, policy, as_of)` over a PIT record
  store validated by `load_and_verify_point_in_time_record_store`; markets are `ObservedMarketState`
  (`market_id`, `event_id`, `question_text`, `category`, `outcome_labels`, `resolution_date`, `rules`).
  No other market source exists. Native PIT metadata always carries `question_text`;
  `markets_unrankable_no_question` is reported defensively.
- Rule wording: never stored natively (only `rule_content_sha256`). A caller rule-text file binds to a
  market only when its SHA-256 equals one of that market's native `rule_content_sha256` values
  (`BOUND`); otherwise `RULE_HASH_MISMATCH`, `RULE_MARKET_NOT_IN_CORPUS`, `RULE_DUPLICATE`,
  `RULE_BYTES_MISSING`, `RULE_BYTES_INVALID` or `RULE_FIELDS_INVALID`, and the market is reasoned about
  from question/category/outcomes/date only (`RULE_TEXT_UNAVAILABLE`).
- Event identity: the native `event_id` is used as recorded. `event:polymarket:` + `condition_id` is
  labelled `EVENT_ID_CONDITION_DERIVED` (no Gamma event grouping is implied); otherwise
  `EVENT_ID_AS_RECORDED`.
- Optional Alpha join: `load_and_verify_alpha_factory_registry`; only records with `subject_refs`;
  `market:` refs that are in the corpus are joined, others counted as `unresolved_refs`. The registry is
  never used as a market corpus.
- Sources: caller-supplied local bytes. Accepted bytes are bound to native
  `build_raw_evidence_reference` (`source_system=caller-local-bytes`, `retrieval_method` = capture mode,
  `replay_fidelity=FAITHFUL`) and the receipt to `build_research_provenance_manifest`. No
  `SourceSnapshotRecord` is created; an imported page is never labelled a live Polymarket capture.

## Operator contract

```
python -B tools/alpha/run_source_grounding.py run --case CASE.json --scratch-dir ABS_EMPTY_DIR
python -B tools/alpha/run_source_grounding.py verify --scratch-dir ABS_EMPTY_DIR
```

`run` validates the case, refuses an absolute scratch path inside the repository or a non-empty scratch,
copies every named input into `scratch/inputs/` (`pit.sqlite3`, `alpha.sqlite3`, `rules/NNN.bin`,
`sources/NNN.bin`; an unusable item path freezes as an empty file so it is counted, never dropped),
writes `frozen_case.json`, computes the core from the frozen copies only and writes `receipt.json`
write-once. Input paths must be absolute regular non-symlink files outside the repository and scratch;
SQLite sidecars (`-wal`, `-shm`, `-journal`) stop the run. Both commands run under a socket guard; any
attempt stops `NETWORK_ATTEMPT_BLOCKED`. Exit 0 only for `RUN_COMPLETE` / `VERIFIED`.

### Case schema `s10-r3-src01-case-v1` (exact keys)

`schema_id`, `case_label` (`[a-z0-9][a-z0-9_-]{0,47}`), `corpus_class` (`SANITIZED_SYNTHETIC` |
`LOCAL_REAL_PIT`), `pit_store` (abs path), `alpha_registry` (abs path | null), `policy` (native
`AlphaDiscoveryPolicy` mapping), `as_of` (UTC), `rule_texts` [`{market_id, file}`], `sources`
[`{source_label, market_id, file, url, http_status, media_type, capture_mode, declared_sha256,
source_publish_time, public_available_time, local_first_seen_time, ingestion_time, revision_time}`],
`queries` [`{query_id, text, category_hint, relevant_market_ids}`] (empty labels = expected no match).
Lists are capped at 500. Whole-case stops: wrong/missing keys, bad UTC `as_of`, invalid policy or
universe, empty queries, credential-shaped keys anywhere (`api_key`, `secret`, `password`, access/refresh `token`
variants, `wallet`, ...), trade-shaped key words (`order`, `side`, `size`, `price`, `amount`,
`signature`, `stake`, `bet`) outside the native policy subtree, credential-like values, NaN/duplicate
JSON keys. Free-text values (for example a query about "the price of eggs") are allowed.

### Source admission (per item, counted)

Order: fields -> duplicate label (`CONFLICTING_SOURCE_IDENTITY`) -> market in corpus -> URL safety (http(s),
no userinfo, no token/key/sig/auth/session query keys) -> bytes present -> SHA-256 equals
`declared_sha256` (`SOURCE_BYTES_CHANGED`) -> UTC clocks (`SOURCE_CLOCK_INVALID`) -> ingestion present,
not before first-seen (`SOURCE_CLOCK_INCONSISTENT`), and for prospective capture not after cutoff
(`SOURCE_INGESTED_AFTER_CUTOFF`) -> native `evaluate_replay_admissibility` (`LATER_IMPORT` passes no
local first-seen, so only `public_available_time` can admit it, and keeps `BACKFILLED`; revision after
cutoff -> `LATE_REVISION`; not yet seen -> `FUTURE_CONTENT`; no clock -> `NO_OBSERVABILITY_EVIDENCE`) ->
quality (`HTTP_STATUS_<n>`, `INVALID_BYTES`, `BLOCK_SIGNATURE`, `LOGIN_WALL`, `THIN_CONTENT`) -> same
market + same content hash `DEDUPED`/`DUPLICATE_CONTENT` -> `ACCEPTED` with a native raw evidence id.

## Ranking and baseline (frozen before the benchmark corpus)

Tokenizer: case-folded `[a-z0-9]+`, fixed stopword list in the module. Shared by both methods.

`pa_event_market_bm25_v1`: market document = question tokens x2 + category + outcome labels +
resolution year/month + hash-bound rule text; event document = union of its markets' documents. BM25
k1=1.2, b=0.75 (textbook defaults). Score = market BM25 + 0.5 x event BM25, rounded to 9 dp, ties by
`market_id`; top 10. Abstains `NO_MATCH` (no positive score) or `LOW_QUERY_COVERAGE` (best market plus
its event match fewer than half of distinct query terms). Flags `AMBIGUOUS_TOP_RANK` (second result from
another event within 95% of the top) and `SAME_TITLE_DIFFERENT_RULES` (identical question text with
different rule hashes in the result: same titles are not treated as same payouts). The top three results
get subquestions with claim-source links (metadata record id, rule record id + `rule:sha256:`, accepted
raw evidence ids).

`baseline_plain_v0` (constructed native-field baseline, not a pre-existing tool): count of distinct query
tokens present in `ObservedMarketState.question_text`; ties prefer exact native `category` equal to the
query `category_hint`, then `market_id`; zero overlap excluded; top 10; identical corpus.

Metrics (numerator, denominator, 6-dp value) per method over valid cases: `recall_at_10` (micro over
labeled relevant ids), `precision_at_10` (hits / retrieved on positive cases), `false_relatedness_items`
(retrieved non-relevant / retrieved), `negative_queries_with_results`, `positive_queries_with_zero_hits`,
`abstained`, and cost (`LOCAL_CPU_ONLY`, 0 provider/network calls, spend 0). Elapsed times are reported
under `non_identity` and excluded from receipt identity. Fewer than 30 valid labeled cases ->
`BENCHMARK_REFUSED` with metrics null and all per-case rows and denominators preserved. Refused queries
(`QUERY_FIELDS_INVALID`, `DUPLICATE_QUERY_ID`, `QUERY_EMPTY`, `DUPLICATE_LABEL`, `LABEL_NOT_IN_CORPUS`)
stay in `cases_total`.

## Frozen benchmark corpus

`SANITIZED_SYNTHETIC`, inline in the test file: 39 markets / 34 events / 8 hash-bound rule texts / 45
queries (39 labeled, 44 relevant ids, 6 expected no-match). Canonical corpus SHA-256
`4a3639c3b66a9b55b06d2bdd5f9504ef18222dffe284b13292f0fa3ad7c2d030`. Observed (not tuned):

| Method | recall@10 | precision@10 | negative queries with results | abstained |
|---|---|---|---|---|
| `pa_event_market_bm25_v1` | 41/44 | 41/146 | 1/6 | 8/45 |
| `baseline_plain_v0` | 42/44 | 42/128 | 3/6 | 3/45 |

The ranker wins only the rule-only query (LaGuardia wording) and abstains more on no-match queries; it
loses two labeled cases to abstention. This proves the callable path and honest accounting; it is NOT
real-world lift. Both corpus and parameters were authored in this WP, so the comparison is not
independent.

## Receipt `s10-r3-src01-grounding-receipt-v1`

`{core, provenance_manifest, receipt_id, non_identity}`. `core` binds WP id, posture, caller, code
identity (SHA-256 of module + operator bytes), source pins, method parameters, input hashes, case hash,
policy and universe ids, corpus accounting, rule and source outcomes, accepted raw evidence references,
Alpha join, benchmark denominators/metrics/per-case rows, adoption status and authority flags.
`provenance_manifest` = native manifest with `output_hash = sha256(core)`. `receipt_id = srcground:sha256:`
over `{core, provenance_manifest}`. `verify` recomputes the core from the frozen inputs and fails closed
on any difference (`RECEIPT_ID_MISMATCH`, `MANIFEST_ID_MISMATCH`, `MANIFEST_OUTPUT_BINDING_MISMATCH`,
`RAW_EVIDENCE_ID_MISMATCH`, `INPUT_BYTES_TAMPERED`, `OUTPUT_MISMATCH:<field>`); a corrupt store stops
`UNIVERSE_INVALID`. Code changes also fail verify (code identity is in the core).

## Adoption status

R3-02: `NOT_VALUE_VERIFIED` always from this tool (synthetic: callable behaviour only; `LOCAL_REAL_PIT`:
awaiting independent review). R3-01-SOURCE_ARCHIVE: `INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED`. The six
provider lanes, twelve parity rows and Lane B are unchanged. The external 36-ID register is updated only
after independent assessment.
