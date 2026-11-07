# Public Market Search and Prediction-Market Contract Parity (S10-R3-EXT-CONTRACTS-01)

Posture: `OFFLINE_RESEARCH_ONLY`, `PARTIAL_UPSTREAM_CONTRACT_PARITY`, `LOCAL_PIT_SOURCE_ORIGIN_UNVERIFIED`,
`OWNER_ACCEPTANCE_PENDING`, `NO_PROVIDER_OR_TRADING_AUTHORITY`. Advisory candidates only; a human reviews
every result. Nothing here grants network, provider, credential, Hermes, strategy, paper, order, capital or
live authority, and nothing is written to native PIT, Alpha or WP170 stores.

## Operator

```
python -B tools/alpha/run_public_market_contract_parity.py run --grounding-scratch ABS --cases ABS.json --scratch-dir ABS
python -B tools/alpha/run_public_market_contract_parity.py verify --scratch-dir ABS
```

- `--grounding-scratch` is an existing S10-R3-SRC-01 scratch (`run_source_grounding.py run`). It is cold-verified
  by the unedited `run_source_grounding.verify` **before** copying, copied, and verified again; both receipt ids
  must match the cases file's `grounding_receipt_id`.
- `--scratch-dir` must be an empty absolute directory outside the repository. `run` writes `inputs/` and one
  write-once `receipt.json`; `verify` recomputes everything from the frozen copies and writes nothing.
- Repeating `run` with identical caller bytes returns `IDEMPOTENT_VERIFIED`; any other non-empty scratch refuses
  `SCRATCH_NOT_EMPTY`. Every socket entry point is blocked (`NETWORK_ATTEMPT_BLOCKED`).
- Paths that are relative, contain `..`, are symlinks, reparse points or hardlinks, alias another path, sit in
  secret-shaped directories or the repository, or overlap the scratch are unusable. Files over 1 MiB (cases) or
  160 MiB / 2000 files (grounding) are refused. Results print stable codes only, never input text or paths.

## Cases file (`s10-r3-ext-contracts01-cases-v1`)

Top level, all required: `schema_id`, `corpus_class` (`SANITIZED_SYNTHETIC` or `LOCAL_REAL_PIT`, equal to the
grounding scratch), `grounding_receipt_id`, `as_of` (equal to the grounding cutoff), `label_source`
(`CALLER_SUPPLIED_SYNTHETIC` for synthetic, `CALLER_SUPPLIED_UNVERIFIED` for real), `benchmark_sha256`
(`benchmark_commitment`: method settings plus every case, frozen before comparison), `cases` (1..500) and
`upstream_vectors` (`py_sdk_search`, `ccxt_prediction_markets`, each 0..200).

Each case: `case_id`, `decision_time` (null or canonical UTC; earlier than `as_of` abstains `POST_CUTOFF`),
`query` and `expected_market_ids` (the caller's labels, which must all be native universe members). Query keys,
all optional: `q`, `events_status`, `events_tag`, `market_id`, `condition_id`, `event_id`, `resolution_after`,
`resolution_before`, `require_rule`. Duplicate keys, NaN, invalid UTF-8, credential-shaped keys or values are
refused. A canonical condition id (`0x` + 64 hex) is accepted only as a `conditionId` / `condition_id` value.
Refused cases (invalid fields, duplicate id, label outside the corpus) stay in the input count and leave the
paired denominator; they are never scored as negatives or successes.

## Native identity (R3-27 concept)

One row per native `ObservedMarketState`: `market_id`, `event_id`, `condition_id`, `category`, `market_status`,
`resolution_date`, metadata record version and clock, rule digests and source ids are separate fields. The row
abstains on `MARKET_ID_NONCANONICAL` (not `market:polymarket:<decimal>`), `TOKEN_ID_NONCANONICAL` (not
`token:polymarket:<decimal>`), `CONDITION_ID_MISSING`/`CONDITION_ID_INVALID`, `DUPLICATE_CONDITION`,
`EVENT_RELATION_CONFLICT`, `OUTCOME_TOKEN_COUNT_MISMATCH`, `TOKEN_COLLISION`, native metadata gaps or conflicts,
`POST_CUTOFF` or a missing question. Native snapshots sort tokens and outcome labels independently, so every row
is `ORIENTATION_UNPROVEN` with `yes_token_id: null` and `tradable_side: null`.

Upstream vectors mirror ccxt `ts/src/prediction/polymarket.ts` `parseEventToMarkets` at commit
`28d9b2ca6e06173ce00f020cfd5bfac3275604d4` (blob `d7fb1dff…`): id = conditionId, `type: prediction`, outcome *i*
paired with `clobTokenIds[i]`, binary iff two outcomes, `active && !closed`, resolved if closed or UMA-resolved.
The positional pairing is kept only as `upstream_yes_token_claim`; orientation stays `ORIENTATION_UNPROVEN` and
two disagreeing claims for one market flag `UPSTREAM_ORIENTATION_CLAIMS_DISAGREE`. Stricter than ccxt: length
mismatch, duplicate tokens or labels, non-decimal ids and invalid condition ids refuse instead of being skipped.
`ts/src/polymarket.ts` (blob `a428bf5e…`) is Polymarket **perpetual futures** (`swap: true`); a perps product or
swap/contract marker is `PERPETUAL_PRODUCT_REJECTED`. A normalized vector is cross-checked against the native
row: `IDENTITY_CONSISTENT`, `IDENTITY_CONFLICT`, `NOT_IN_UNIVERSE` or `NATIVE_IDENTITY_ABSTAINED`.

## Public search projection (R3-23 concept)

py-sdk `PublicClient.search` at commit `aa94ec431e3d4946576fb7c0d079fe1c14fcf676` (`examples/search.py`
`895d728f…`, `clients/public.py` `c0e1d178…`) returns one mixed `events`/`tags`/`profiles` payload per page.
Each offline vector (request + one results page) is projected: request keys are `SUPPORTED` (`q`,
`events_status`, `events_tag`, `page_size`, `search_tags`, `search_profiles`), `PARAMETER_UNSUPPORTED` (the
other pinned keywords) or `PARAMETER_UNKNOWN`; each event maps its markets to native rows (`EVENT_PROJECTED`,
`NOT_IN_UNIVERSE`, `IDENTITY_CONFLICT`, `EVENT_RELATION_CONFLICT`); every tag and profile is
`TAG_OR_PROFILE_UNSUPPORTED`. The native field-aware search also emits a py-sdk shaped single page for the same
request, and the receipt counts shared markets. No endpoint is called (`online_fetch: false`).

## Field-aware search and baseline

`field_aware_search_v1`: deterministic tokens (the SRC-01 tokenizer, at most 16 terms), exact `market_id` /
`condition_id` / `event_id`, then category / status / resolution-window / rule-presence filters; only VALID
identity rows are admissible. Score = sum over query terms of the best field weight (question 3, category 2,
rule text, outcomes and resolution year/month 1) times a smoothed IDF; stable order by score then market id;
top 10. Reasons: `NOT_IN_UNIVERSE`, `AMBIGUOUS` (exact top tie across events), `MISSING_METADATA`,
`POST_CUTOFF`, `NO_ADMISSIBLE_MATCH` (including coverage below one half of the query terms). The baseline is the
merged R3-02 `source_grounding.rank_markets` on the identical native index; `field_aware_text_only_v1` is the
same scorer without filters or ids, so filter help is not mistaken for ranking quality. All three run on
exactly the same valid cases (paired denominator). Metrics reuse `source_grounding._method_metrics` and add
false top-1 and false exact-identifier matches. Fewer than 50 valid cases gives `BENCHMARK_REFUSED` with no
metrics. `lift_claim` is always null and `real_value` is `NOT_VERIFIED`.

Synthetic result at commit time (60 input, 57 paired, 50 positive): field-aware recall@10 49/58 vs baseline
52/58, precision@10 49/152 vs 52/196, false top-1 0/42 vs 2/44. The new method is more precise but recalls
less; this is callable-behaviour evidence on a constructed corpus, not lift. The real benchmark is `NOT_RUN`
because no genuine local real corpus was supplied; a `LOCAL_REAL_PIT` grounding scratch runs the same path with
`OBSERVED_CALLER_LABELS_AWAITING_INDEPENDENT_REVIEW`, never self-declared value.

## Remaining gaps (no silent closure)

R3-23 and R3-27 advance only to executed offline partial parity and stay `OWNER_ACCEPTANCE_PENDING`. R3-24 (TS
public search) and the other 10 parity ids stay open; the six provider lanes, Lane B, real Hermes specialist
sessions, citation origin authenticity and real-source value stay separately gated. All 36 capability rows are
retained with zero new value acceptances. See `docs/deferred_items_log.md` (S10-R3-EXT-CONTRACTS-01).
