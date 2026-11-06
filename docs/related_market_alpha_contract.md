# Related-Market Discovery and Conditional Basket Economics Contract (S10-R3-REL-01)

Status: RUNTIME / Risk 3, offline research tooling. Modules
`src/data_layer/analytical_research/related_market.py` (discovery, rule binding, formal proof) and
`src/data_layer/analytical_research/related_market_economics.py` (baskets, fees, depth); operator
`tools/alpha/run_related_market_alpha.py`; opt-in hook `tools/alpha/run_source_grounding.py related`.
Tests `tests/tools/alpha/test_related_market_alpha.py`, `tests/tools/alpha/test_related_market_economics.py`
and a compatibility regression in `tests/tools/alpha/test_source_grounding.py`.
Posture: `RESEARCH_ONLY`. No product/provider/account network, credentials, LLM/Hermes, strategy, paper,
order, capital, executable-edge or live authority. No canonical store write, no dependency change.

**A positive result here is never real Alpha, a guaranteed arbitrage or an executable edge.** Every
formal proof is conditional on a caller-declared finite payout model; every economic status is
conditional on caller-supplied venue bytes of unauthenticated origin and on a simultaneous multi-leg fill
that no native route provides.

## Source pins (ADAPT_ALGORITHM, no code copied, no dependency)

| Capability | Upstream pin (commit / blob) | Adapted method |
|---|---|---|
| R3-03 | `YichengYang-Ethan/oracle3-prediction-market-agent@267fb7c48dae7c4ff8922c02a3a223443e51bf0b` `oracle3/arbitrage.py` blob `4805d572b55ce6547c9c46ab92a2aa4ce90de808` | five relation families and reference baskets with payoff lower bounds |
| R3-03-FEES | same commit, `oracle3/fees.py` blob `24624f84d40a43610302f7b8c3d17c347fa62e0c` | prefer per-market fee data; never a fallback default (unknown stays unknown) |
| R3-04 | `YichengYang-Ethan/oracle3-extras@b2d807a0513f37212623ecd3a9127af3ad506658` `oracle3_extras/market/kairos/settlement.py` blob `acb2de215b43f879bddcdd7b5c163396859cf4de` | same/complement settlement compatibility; tie, cancel and unresolved states keep results inconclusive |
| R3-11 | `chainstacklabs/polymarket-alpha-bot@1f4f366b9c677574c8034a8720eaca917a53715b` `backend/core/steps/implications.py` blob `27150d1857da9ff9ef3e2a9d738c469c591e9728` | necessary-implication counterexample logic; an LLM confidence is never proof |
| R3-19 | `Synpath-ai/prediction-market-arbitrage-trading-bot@c906cb36956945a291cb32a2d60a7455a0103a8f` `src/matcher.py` blob `24de654e6c07c297416ea1b5e6f9de17f148432b` | same / insufficient / not_same disposition and side orientation |

Nothing from these repositories is imported, vendored or installed; license review was not needed for
method-only adaptation and remains required before any future code copy.

## Call path (all native, read-only)

1. `tools.alpha.run_source_grounding.verify` cold-verifies a frozen copy of the caller's existing
   S10-R3-SRC-01 scratch. A non-VERIFIED receipt refuses the run (`GROUNDING_RECEIPT_NOT_VERIFIED`).
2. `source_grounding.load_corpus` -> `alpha_discovery.build_alpha_universe_snapshot` over the frozen PIT
   store; `source_grounding.bind_rule_texts` admits rule bytes only when their SHA-256 equals a native
   `rule_content_sha256`; `load_and_verify_point_in_time_record_store` supplies the
   `ResolutionRuleSnapshotRecord` hierarchy rank and human-review state.
3. `related_market.discover_candidates` (`native_universe_relation_candidates_v1`) proposes candidates
   from the native universe only. Generators: `SHARED_CONDITION_ID` (mechanical identity),
   `SHARED_RECORDED_EVENT` (non condition-derived `event_id`, group size 2..`max_group_size`) and
   `CATEGORY_QUESTION_TERMS` (same native category, >= `min_shared_terms` shared question terms). All are
   `LOW_CANDIDATE_ONLY_NOT_PROOF`. Counted noncandidates: `NONBINARY_UNSUPPORTED`, `STATUS_NOT_OPEN`,
   `REQUIRED_METADATA_MISSING`, `METADATA_STALE_OR_CONFLICTED`, `EVENT_ID_CONDITION_DERIVED_NOT_GROUPED`,
   `EVENT_GROUP_TOO_LARGE_SPLIT_UNSUPPORTED`, `CANDIDATE_CAP_EXCEEDED`.
4. Caller `models` only qualify discovered candidates (matched by relation + market ids; symmetric
   relations ignore order). A model for a pair the native discovery did not propose is
   `NOT_NATIVE_CANDIDATE`: the caller cannot substitute a manual pair list.
5. `related_market.formal_proof` and `real_world_classification` (below), then
   `related_market_economics.assess_leg` / `assess_basket` over
   `src.execution_feasibility.public_market.build_public_venue_snapshot` built from frozen Gamma/CLOB bytes
   (no `public_get`), using the native evaluator helpers `_market_dimension`, `_identity_dimension`,
   `_tick_dimension`, `_minimum_order`, `_sweep`, `_taker_fee`, `_fee` and `FEE_QUANTUM`. These helpers are
   module-private but pure; their file bytes are part of the receipt code identity, so drift is
   `TAMPER_DETECTED`. `src.research_runtime.executable_edge.assess_executable_edge` is never called.

## Operator contract

```
python -B tools/alpha/run_related_market_alpha.py run --grounding-scratch ABS --request-file ABS --scratch-dir ABS
python -B tools/alpha/run_related_market_alpha.py verify --scratch-dir ABS
python -B tools/alpha/run_source_grounding.py related --grounding-scratch ABS --request-file ABS --scratch-dir ABS
```

`related` delegates to the same `run_safe("run")`; legacy `run`/`verify` are unchanged and never import the
new module. Exit 0: `RUN_COMPLETE`, `VERIFIED`, `IDEMPOTENT_VERIFIED` (including runs with zero candidates
or zero economic rows). Exit 1: `STOPPED` with one stable `reason_code` (no input, path or exception text)
or `TAMPER_DETECTED` with failure codes.

Path guards: absolute, no `..`, no symlink/reparse point/hard link/non-regular entry (including parents),
alias (`resolve` != `abspath`) rejected, secret-shaped directories (`.ssh`, `.aws`, `.gnupg`, `.azure`,
`.kube`, `.docker`, `credentials`, `secrets`, `.password-store`) rejected, nothing inside the repository,
no overlap between scratch and any input. Bounds: request 1 MiB, venue body 4 MiB, grounding scratch
160 MiB / 2000 files, 200 models, 400 venue entries, 500 candidates, 300 s run budget. Strict
duplicate-free JSON without NaN/Infinity; secret-shaped keys or values refuse. All socket entry points
are blocked for the whole run and verify; any attempt, even if caught, refuses
`NETWORK_ATTEMPT_BLOCKED`.

Scratch layout (write-once): `inputs/grounding/**` (byte copy of the SRC-01 scratch),
`inputs/request.source.json` (caller bytes), `inputs/request.json` (canonical, venue paths relative),
`inputs/venue/NNN-{gamma,clob}.bin` (an unusable caller path freezes as an empty file and is counted
`VENUE_FILE_UNUSABLE`), `receipt.json` (opened `xb`). A non-empty scratch without a verified receipt
refuses `SCRATCH_NOT_EMPTY`; an identical request + grounding receipt over a verified scratch returns
`IDEMPOTENT_VERIFIED` and writes nothing. An aborted run never leaves a receipt; resume needs a new scratch.

## Request `s10-r3-rel01-request-v1`

Keys (exact): `schema_id`, `request_label`, `corpus_class` (`SANITIZED_SYNTHETIC` | `LOCAL_REAL_PIT`, must
equal the SRC-01 case), `decision_time` (UTC `...Z`, seconds), `max_book_age_seconds` (1..3600),
`basket_shares` (plain decimal, <= 6 dp, 0 < s <= 1e6), `search` {`families`, `max_group_size` 2..4,
`min_shared_terms` 1..10, `max_candidates` 1..500}, `fee_policy` {`policy_id`, `kind`, `valid_from`,
`valid_until`, `test_rate`, `test_exponent`}, `models`, `venue`, `benchmark_sha256`.

`benchmark_sha256` must equal SHA-256 of the canonical JSON of discovery id, baseline id and threshold,
`search`, and every model's `[model_id, relation, market_ids, expected]`; it is checked before any
comparison (`BENCHMARK_FREEZE_MISMATCH`).

Model keys: `model_id`, `relation`, `market_ids` (2..4), `states` (admitted YES-payout rows, strict
integers 0/1), `special_states` [{`kind` TIE|VOID|CANCEL|RESCHEDULE|PARTIAL, `payout` row or null}],
`timezones`, `yes_token_ids` (null or the caller's belief, checked against Gamma outcome order),
`claimed_rule_sha256` (null or per-market digests, checked against native), `claimed_verdict` (recorded,
never consulted), `cross_venue` (null or a venue label), `combo`, `expected`. Field defects are counted
per model (`MODEL_FIELDS_INVALID`), not a whole-run refusal.

Venue entry keys: `market_id`, `gamma_market_id`, `token_id` (digits; must be a native token of that
market), `gamma_file`, `clob_file`, `acquisition_started`, `acquisition_completed`. Side (YES/NO) is
derived from the frozen Gamma `outcomes` / `clobTokenIds` order, never from the caller. Per-entry
statuses: `BOUND`, `VENUE_FIELDS_INVALID`, `VENUE_MARKET_NOT_IN_CORPUS`, `VENUE_IDENTITY_MISMATCH`,
`VENUE_FILE_UNUSABLE`, `VENUE_CLOCK_INVALID`, `VENUE_SOURCE_INVALID`, `ORIENTATION_UNKNOWN`,
`VENUE_DUPLICATE` (both copies dropped).

## Rule identity (`NATIVE_RULE_HASH_BOUND` is byte identity, not meaning)

Per market: `NATIVE_RULE_HASH_BOUND` (bound bytes, PRIMARY rank, `NONE_IDENTIFIED`, review not required,
fresh), `RULE_TEXT_UNBOUND`, `RULE_RECORD_MISSING`, `RULE_STALE`, `RULE_AMBIGUOUS` (non-primary rank,
ambiguity label or `REVIEW_REQUIRED`), `RULE_CONFLICT` (`REVIEWED_CONFLICT_UNRESOLVED`,
`CONFLICTING_SOURCE_TEXT`, or native rule/source conflict gaps). Each row records the native
`rule_content_sha256`, `rule_record_version_id`, `resolution_source_id`, observed time and source record,
and `origin_authentication: UNKNOWN_CALLER_LOCAL_BYTES`. Native standard PIT builders refuse ambiguity
labels and conflicting text, so on native stores ambiguity appears as a non-primary rank.

## Formal proof and real-world classification

Formal (`formal_proof`): exhaustive over the declared rows plus binary-modelled special states.
IMPLICATION (n=2): no admitted (1,0). EXCLUSIVITY (2..4): at most one YES. COMPLEMENT (2): exactly one.
SAME_EVENT (2): identical payout. EVENT_SUM (2..4): exactly one. Statuses:
`FORMAL_BOUNDED_PAYOFF_PROOF` (trust `MODEL_CONDITIONAL_NOT_REAL_VERIFIED`), `FORMAL_COUNTEREXAMPLE`
(every violating state listed), `INCONCLUSIVE_SPECIAL_STATE_UNMODELLED` (special state with unknown or
non-binary payout), `FRACTIONAL_OR_NONBINARY_PAYOUT_UNSUPPORTED`, `MODEL_STATE_SHAPE_INVALID`,
`MODEL_DUPLICATE_STATE`, `GROUP_SIZE_UNSUPPORTED`.

Real world (`real_world_classification`, first match): `EXTERNAL_VENUE_UNVERIFIED` (any `cross_venue`
claim), `RULE_CONFLICT` (native conflict, `FORGED_RULE_DIGEST`, `CROSS_MARKET_RULE_DIGEST`,
`ORIENTATION_CONTRADICTED`), `MECHANICAL_IDENTITY_NOT_INDEPENDENT` (SAME_EVENT on one native
condition_id: not a new independent relation), `INCONCLUSIVE_RULE_UNBOUND`,
`INCONCLUSIVE_RULE_AMBIGUOUS_OR_STALE`, `INCONCLUSIVE_TIME_WINDOW_MISMATCH` (timezones differ, or
resolution dates differ for non-implication relations), else `INCONCLUSIVE_RULE_SEMANTICS` (native PIT
has a rule hash but no formal resolver). `REAL_WORLD_RULE_VERIFIED` is never emitted;
`real_world_rule_verified` and `tradeable_equivalence_proven` are always false.

Disposition (benchmark label space): `FORMAL_VALID`, `COUNTEREXAMPLE`, `RULE_CONFLICT`, `INCONCLUSIVE`
(includes external-venue claims), `NOT_NATIVE_CANDIDATE`, `MODEL_INVALID`.

## Conditional basket economics

Evaluated only for `FORMAL_BOUNDED_PAYOFF_PROOF` with real-world class other than `RULE_CONFLICT` /
`EXTERNAL_VENUE_UNVERIFIED`. Reference baskets: IMPLICATION NO(A)+YES(B) min 1; EXCLUSIVITY NO all min
n-1; COMPLEMENT YES both or NO both min 1; SAME_EVENT YES(A)+NO(B) or NO(A)+YES(B) min 1; EVENT_SUM YES all
min 1 or NO all min n-1. The minimum is re-derived over admitted states (`certified_min_payout`); below the
reference minimum (e.g. wrong implication direction) is `NOT_EXECUTABLE` / `BASKET_ORIENTATION_INVALID`.
Units: payout USD = certified minimum x `basket_shares`; cost USD = sum of price x size over the
best-first ask sweep for `basket_shares` per leg; fee USD = shares x rate x (p(1-p))^exponent per fill,
rounded up (ROUND_CEILING) to 5 dp per leg; all arithmetic in the native trap-on-inexact Decimal context.

Leg (taker ask sweep only; a maker zero fee is never assumed): `NOT_EXECUTABLE` (inactive / closed / not
accepting / book disabled, `NEG_RISK_UNSUPPORTED`, `PRICE_OFF_TICK`, `MINIMUM_ORDER_NOTIONAL_NOT_MET`
(Gamma USDC notional), `MINIMUM_ORDER_SHARES_NOT_MET` (CLOB share count)), `QUOTE_INCONCLUSIVE`
(`QUOTE_MISSING`, venue binding failure, `VENUE_SOURCE_INVALID`, `MARKET_STATE_UNKNOWN`,
`VENUE_EVIDENCE_AFTER_DECISION`, `BOOK_TIMESTAMP_INVALID` (book after acquisition), `BOOK_STALE`, `NO_ASKS`,
`TICK_UNKNOWN`, `MINIMUM_ORDER_UNKNOWN`), `COST_INCONCLUSIVE` (`DEPTH_INSUFFICIENT`, fee unknown),
`COST_KNOWN`.

Fee policy at `decision_time`: `GAMMA_BODY_PER_MARKET` (native `_fee` on the frozen Gamma `feeSchedule`;
provenance `CALLER_SUPPLIED_GAMMA_FEE_SCHEDULE_UNAUTHENTICATED`), `TEST_ONLY_HYPOTHETICAL` (id must start
`test-only-`; results carry `fee_basis: TEST_ONLY_HYPOTHETICAL`), `NATIVE_NEAR_TERM_SCREENER` (pinned
`documented-fees-20261028-near-term-02`, expiry `2026-11-04T00:00:00Z`; any later `valid_until` is
`FEE_POLICY_EXTENSION_REJECTED`; at or after expiry `FEE_POLICY_EXPIRED`; inside the window it is a
documented bound, not per-market data, so `FEE_CONFIG_UNKNOWN`), `NONE` (`FEE_POLICY_ABSENT`). The
2026-11-06 public fee page is context only, not per-market evidence. Unknown fees are never zero.

Basket status: `NOT_EXECUTABLE` (combo, any non-executable leg), `MECHANICALLY_INCONCLUSIVE` (any quote gap),
`THEORETICAL_PRICE_INCONSISTENCY` (costs unknown but top-of-book sum < certified payout),
`NO_CONDITIONAL_EDGE` (top-of-book or all-in cost >= payout), `FEE_AND_DEPTH_CONDITIONAL` (all-in
cost < payout). Always: `atomicity: NOT_PROVEN_NO_NATIVE_MULTI_LEG_ROUTE`, `executable_edge: false`,
`guaranteed_arbitrage: false`, `profit_proven: false`, and `conditional_on` lists the declared model,
unauthenticated venue bytes and unproven simultaneous fill. A model's economic status is its best basket.

## Receipt `s10-r3-rel01-related-market-research-receipt-v1`

`receipt.json` = {`core`, `receipt_id`}; `receipt_id` = `relmarket:sha256:` + SHA-256 of canonical
`{"core": core}`. `core` holds: schema, WP, posture, label, corpus class, caller chain, code identity
(SHA-256 over the two new modules, the runner, `source_grounding.py`, `run_source_grounding.py`,
`alpha_discovery.py`, `execution_feasibility/evaluator.py` and `public_market.py`), source pins, method
settings, inputs (as-of, decision time, every frozen file SHA-256, grounding receipt id, Alpha policy and
universe ids, benchmark SHA), corpus rule rows, discovery, venue entries, fee policy, per-model results
(formal + real-world + economics + baseline), benchmark, adoption and authority (all false except
`research_only`). `verify` re-runs the SRC-01 verify on the frozen grounding copy and recomputes the
whole core with sockets blocked; any difference is `TAMPER_DETECTED` with `OUTPUT_MISMATCH:<key>`,
`RECEIPT_ID_MISMATCH` or `RECOMPUTE_REFUSED:<code>`.

## Benchmark and baseline

`baseline_native_relation_fields_v0` is a new comparison baseline (not an existing verifier): related iff
all markets share the recorded `event_id` (condition-derived ids included) or share a native category with
at least 2 shared question terms pairwise. Truth is `expected == FORMAL_VALID`. Reported per method:
proposed, true matches, false relationship matches, precision, recall, false-positive rate (with
numerators and denominators), plus eligible inspected, native candidates matched, formal conditional
proofs, native identity only, semantic unknown, abstained/ambiguous, price inconsistencies, after-cost
test-evaluable baskets, fee known/unknown legs, `real_world_verified: 0`, `real_world_evaluable: 0`.

Frozen corpus (inline in `tests/tools/alpha/test_related_market_alpha.py`, SANITIZED_SYNTHETIC, 32
markets, 13 venue legs, 49 models: 15 FORMAL_VALID across all five families, 11 COUNTEREXAMPLE, 7
INCONCLUSIVE, 4 RULE_CONFLICT, 7 NOT_NATIVE_CANDIDATE, 5 MODEL_INVALID), corpus SHA-256
`244756ff9f45cb16c10d0b96cb342df8a9f2590f0d4a2301663733bc6507f312`. Observed: baseline proposed 44,
true 15, false relationship matches 29/34 negatives (precision 15/44); verifier proposed 15, true 15,
false 0/34; 40 native candidates matched; 25 formal conditional proofs; 3 native identity only; 32
semantic unknown; economics FEE_AND_DEPTH_CONDITIONAL 2, THEORETICAL_PRICE_INCONSISTENCY 2,
NO_CONDITIONAL_EDGE 1, NOT_EXECUTABLE 1, MECHANICALLY_INCONCLUSIVE 9; fee known 20 / unknown 34 legs.
The labels are the expected formal dispositions authored with the corpus, so the verifier's 49/49
agreement measures closed-rule consistency, not real-world discovery lift. Model `v11` is formally valid
only because the caller's model omits a rate hike: the formal layer cannot detect an incomplete declared
state space, which is why real-world status stays inconclusive.

## Adoption truth

R3-03 `INTEGRATED_OFFLINE_CONDITIONAL_NOT_VALUE_VERIFIED`; R3-03-FEES
`NATIVE_FEE_PATH_CONDITIONAL_EXPIRED_POLICY_REFUSED`; R3-04
`SETTLEMENT_COMPATIBILITY_INCONCLUSIVE_WITHOUT_FORMAL_RESOLVER`; R3-11
`COUNTEREXAMPLE_CHECK_INTEGRATED_NO_LLM_PROOF`; R3-19 `SAME_INSUFFICIENT_NOT_SAME_DISPOSITION_INTEGRATED`.
The other 31 capability ids, 12 parity candidates, six provider lanes, R3-02 retrieval improvement,
real-source forecasting/learning, Hermes specialist citations and independent Lane B are unchanged and
separately owner-gated. Limitations are tracked as S10-R3-REL-01-D001..D004 in `docs/deferred_items_log.md`.
