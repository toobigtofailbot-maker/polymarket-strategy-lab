# Qualification Candidate Contract (S10-QUAL-01)

## 1. Status And Purpose

S10-QUAL-01 implements the deterministic NON-WALLET `QualificationCandidate` substrate in
`src/data_layer/analytical_research/qualification.py`. It is the crossing between canonical
Alpha research memory and the later qualification gate / WP170 experiment OS:

```
verified current supportive Alpha lineage
+ verified AF1_PASS receipt (all ten dimensions PASS)
+ verified ResearchProvenanceManifest inputs
+ frozen hypothesis / feature / label / dataset-split / sample-power / test-family plans
+ conditional B0/B1/B2 forecast-evaluation interface
+ execution-feasibility evidence availability
    -> immutable content-addressed QualificationCandidate
    -> future S10-GATE-QUAL-01 (separately gated)
    -> later WP170 candidate-specific experiment work (separately gated)
```

Core authority invariant: Alpha research support -> qualification candidate packet, which is
NOT a qualification PASS, NOT a preregistered experiment, NOT OOS evidence, NOT an executable
edge and NOT paper/live authority. S10-QUAL-01 itself produces NO qualification
PASS/FAIL/INCONCLUSIVE decision. No real candidate is qualified by this implementation WP;
implementation evidence uses deterministic synthetic fixtures plus the committed canonical AF1
receipt as a predecessor compatibility fixture.

AF1_PASS (receipt
`af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`) remains
research-system gate success only. It proves no candidate is qualified, predictive, profitable
or executable. The current receipt is predecessor evidence, not a hardcoded product constant:
the packet admits any receipt that passes the existing AF1 validator with `AF1_PASS`.

## 2. One Packet, No Second Truth System

The module adds exactly one immutable `QualificationCandidate` and one closed
`QualificationControlResult`, plus strict build / validate / mapping-roundtrip functions. It
adds no SQLite registry, file writer, operator or CLI, provenance family, Alpha memory or gate
receipt. Canonical authorities stay where they are:

- Alpha Factory registry -> canonical research memory;
- `AF1GateReceipt` -> AF1 research-system gate evidence;
- `ResearchProvenanceManifest` -> common provenance core;
- WP170 experiment OS -> later preregistration / OOS authority.

The packet binds those authorities by content id; it never replaces them.

## 3. Public API

Package-root exports (`src.data_layer.analytical_research`): `QUALIFICATION_SCHEMA_VERSION`
(`1.0.0`), `QUALIFICATION_CANDIDATE_SCHEMA_ID` (`polymarket-qualification-candidate`),
`QUALIFICATION_STATUSES`, `QUALIFICATION_MODES`, `WALLET_DEPENDENCY_MODES`,
`QUALIFICATION_FEATURE_SOURCE_CLASSES`, `QUALIFICATION_PROPER_SCORE_IDS`,
`EXECUTION_FEASIBILITY_CLASSES`, `EXECUTION_FEASIBILITY_STATES`, `QUALIFICATION_ERROR_CODES`,
`QualificationCandidate`, `QualificationControlResult`, `build_qualification_candidate`,
`validate_qualification_candidate`, `qualification_candidate_to_mapping` and
`qualification_candidate_from_mapping`.

`build_qualification_candidate(alpha_registry_snapshot, af1_gate_receipt,
provenance_manifests, input_mapping)` returns a `QualificationControlResult`. There is no path
argument, store write, current-time lookup, random seed, environment lookup or network.

`QUALIFICATION_STATUSES` is exactly `QUALIFICATION_CANDIDATE_VALID` /
`QUALIFICATION_CANDIDATE_REJECTED`: packet validity, never qualification.

## 4. Record Identity And Serialization

`QualificationCandidate` is a frozen dataclass with the exact field order frozen in the
package (`schema_id` .. `no_qualification_authority`). Its id is
`qualificationcandidate:sha256:<64 lowercase hex>` over every normalized field except
`qualification_candidate_id`. Nested plans are stored as canonical JSON strings (UTF-8,
`sort_keys`, `(",", ":")` separators, `ensure_ascii=false`, `allow_nan=false`); declared-sorted
arrays are canonicalized so caller order never changes identity; caller duplicates reject.
Binary floats, NaN/Infinity and non-JSON values reject recursively; unknown or missing fields
fail closed.

Fixed values: `experiment_os_schema_version` equals the current WP170
`EXPERIMENT_OS_SCHEMA_VERSION` (`1.0.0`); `advisory_only`, `human_review_required`,
`no_execution_authority`, `no_strategy_authority` and `no_qualification_authority` are exactly
true. The four result authority flags are always true.

`validate_qualification_candidate` is the single shared record-semantic gate: it decodes every
nested plan, re-validates and re-canonicalizes it byte-for-byte and re-derives the identity, so
direct dataclass construction plus a self-consistent rehash cannot bypass semantic validation.
`qualification_candidate_to_mapping` validates before output;
`qualification_candidate_from_mapping` requires the exact keyset and fully re-validates.
Serialized-record validation alone does NOT claim the bound external artifacts are still
current: the future gate must re-bind and re-verify them.

## 5. Alpha Lineage Crossing

The builder accepts an `AlphaFactoryRegistrySnapshot` (all four authority flags true,
`total_rows == len(entries)`, nonempty, a linked entry chain and a head equal to the final entry
hash) and rechecks every record it uses with the existing public Alpha Factory record-semantic
validator. It requires the exact `alpha_candidate_id`, `hypothesis_family_id` and
`governing_research_episode_id`, the episode's candidate/family equal to the requested pair,
and — using the current Alpha convention (an episode is non-leaf when a later episode names it
as predecessor or reopened episode) — exactly ONE leaf for that lineage, equal to the governing
episode and with `result_state == RESEARCH_SUPPORTIVE`. Missing, mismatched, cross-family,
ambiguous, stale and non-supportive lineages reject. ALPHA-02 CORE / EXPLORATION / AUDIT
selection is research allocation only and is not a builder input or qualification authority.

## 6. AF1 And Provenance Binding

AF1: the existing `validate_af1_record` must pass; the receipt must be `FINALIZED`, have
`overall_disposition == AF1_PASS`, the exact AF1 dimension keyset with every dimension `PASS`,
and all no-authority flags true. Only its `gate_receipt_id` is stored.

Provenance: a nonempty sequence of `ResearchProvenanceManifest` whose identities verify with the
existing provenance validator; sorted unique manifest ids are stored. The candidate
`information_cutoff` is canonical UTC; every manifest cutoff and the governing episode
`research_as_of` are at or before it; every split-plan dataset snapshot ref appears in the union
of manifest `dataset_refs`. DQ, gap and replay-fidelity limitations are preserved by reference
and never upgraded; the later gate may decide they are insufficient.

## 7. Frozen Plans

- Hypothesis plan: closed keys; `human_review_state == REVIEWED`; name / version /
  code_version in the WP170 opaque-id grammar. Future WP170 `predecessor_candidate_ids` derive
  from `alpha_candidate_id` and are never a second caller field.
- Feature plan: qualification LOGICAL feature refs with source classes `PUBLIC_NON_MARKET`,
  `MARKET_PIT`, `TIME_ONLY` or (S10-QUAL-B0X-01) `MARKET_EXTERNAL_RECONSTRUCTION`, identical-keyset evidence refs,
  `FEATURE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME` and
  `NO_POST_DECISION_OR_POST_OUTCOME_INFORMATION`. These refs are NOT claimed to be current WP170
  FeatureDefinition ids: current WP170 `SAFE_FEATURE_SOURCE_DEPENDENCIES` are market-observation
  fields only and cannot encode a B1 public-non-market feature set. Exact
  FeatureDefinition / model / calibrator implementation remains WP170 candidate-specific work.
- Label plan: closed target / horizon / target-time / outcome-source / availability-time /
  censoring semantics with evidence refs; the label ref is never itself a feature ref.
- Dataset split plan: PIT dataset refs, `EXCLUSIVE` group policy,
  `LEAKAGE_MARKET_RELATED_EXCLUSIVE` event grouping (future sample assignment isolates roles on
  the existing WP170 keys `leakage_group_id`, `market_id`, `related_group_id`), ordered
  formation < selection < OOS < end boundaries, the WP170 purge rule, nonnegative embargo,
  `DECISION_TIME_HALF_OPEN` inclusion and a positive per-role minimum. No OOS members are
  exposed or constructed.
- Sample-power plan: declared FACTS only (counts, method, reference, target power in (0, 1],
  significance in (0, 1), minimum detectable effect > 0 as canonical decimals). There is no
  universal power calculator or sample threshold; `available < required` is a valid fact packet
  and `available >= required` never implies a qualification PASS.
- Test-family plan: WP170-compatible metric direction and correction policy (`SINGLETON`
  requires family size 1), a frozen multiplicity declaration, the WP170 `acceptance_thresholds`
  mapping whose operator matches the direction, and the matching WP170 baseline acceptance rule.

## 8. B0 / B1 / B2 Forecast Evaluation

`GENERIC_METRIC` requires exactly `{"applicability":"NOT_APPLICABLE"}`. `BINARY_PROBABILITY`
requires exactly one of two B0 rules, `PIT_MARKET_PROBABILITY_V1` (canonical-PIT B0) or
`EXTERNAL_PIT_MARKET_PROBABILITY_V1` (external-reconstruction B0, added by S10-QUAL-B0X-01), with
bounded canonical parameters; B1 refs drawn only from `PUBLIC_NON_MARKET` / `TIME_ONLY` features
(`MARKET_PIT` and `MARKET_EXTERNAL_RECONSTRUCTION` both reject in B1); B2 equal to the exact sorted
union of B1 and a nonempty explicit market-added set whose every ref has the B0 rule's own source
class; `BRIER_SCORE` or `LOG_LOSS` as the primary proper score, equal to the test-family primary
metric with `LOWER_IS_BETTER` / `CANDIDATE_LTE_BASELINE`; a calibration diagnostic; and mandatory
true same-OOS-membership, B1-vs-B0, B2-vs-B0 and B2-vs-B1-incrementality requirements.

Rule-to-class coupling (fail closed, no mixing):

| B0 rule | Source authority | Every `b2_market_added_feature_ref` must be |
|---|---|---|
| `PIT_MARKET_PROBABILITY_V1` | canonical PIT | `MARKET_PIT` |
| `EXTERNAL_PIT_MARKET_PROBABILITY_V1` | third-party external reconstruction | `MARKET_EXTERNAL_RECONSTRUCTION` |

A `MARKET_EXTERNAL_RECONSTRUCTION` addition under the canonical rule, a `MARKET_PIT` addition under
the external rule, a mixed canonical/external addition set and an unknown B0 literal all reject
`FORECAST_PLAN_INVALID`.

`PIT_MARKET_PROBABILITY_V1`: at each future decision time use the latest canonical PIT two-sided
valid book available at or before decision time; B0 is the midpoint when best bid/ask exist and
the spread is within `max_midpoint_spread`; otherwise the latest canonical PIT public trade price
at or before decision time only when its age is within `max_last_trade_age_seconds`; otherwise B0
is unavailable and the preregistered missing-data policy governs. Current or future website
probability and post-decision market data are never used. S10-QUAL-01 only freezes this
interface; it materializes no samples, fits no B1/B2 model, calibrates nothing and scores no OOS.

`EXTERNAL_PIT_MARKET_PROBABILITY_V1` has the identical parameter keys, bounds and fallback
mechanics (`max_midpoint_spread` in `[0, 1]`, `max_last_trade_age_seconds` a nonnegative integer)
but a distinct source authority: it is a third-party reconstruction, never canonical PIT. At each
decision time the midpoint is used only when an observed two-sided book exists at or before
decision time and `ask - bid <= max_midpoint_spread`, with the spread recomputed from best bid/ask
(a source-provided spread field is never trusted); otherwise the latest observed last trade whose
age is `<= max_last_trade_age_seconds`; otherwise B0 is unavailable and the preregistered
missing-data policy governs. `NOT_OBSERVED_IN_SEARCHED_HOURS` is never imputed into a trade.
Observability is the external capture `timestamp_received <= decision_time`; this is not a claim
that the archive itself was publicly readable at decision time.

No backdating and no canonicalization: an archive HTTP `Last-Modified` / `public_available_time`
may be later than the decision checkpoint and is never used to backdate canonical availability.
External evidence (for example the S10-QUAL-DATA-02 `THIRD_PARTY_NATIVE_FRAME_ARCHIVE` /
`EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION` corpus) is never labelled `MARKET_PIT` or
`SOURCE_KIND_CANONICAL_PIT`, never becomes a `DatasetSnapshotReference`, and never receives a
derived or fabricated `local_first_seen_time`; there is no import bridge. The addition is
additive: `QUALIFICATION_SCHEMA_VERSION` stays `1.0.0`, the record fields and identity preimage are
unchanged, and existing canonical packets keep byte-identical content and candidate ids. The
S10-GATE-QUAL-01 gate is unchanged and applies its existing dimensions to either rule.

## 9. Execution Feasibility And Wallet Boundary

The execution-feasibility plan has exactly `FEES`, `RESOLUTION_RULES`, `TICK_SIZE_MIN_ORDER`,
`SPREAD_DEPTH`, `LATENCY` and `PARTIAL_FILL`, each `AVAILABLE` / `PARTIAL` (nonempty evidence
refs) or `MISSING` / `NOT_APPLICABLE` (no refs). It is feasibility EVIDENCE AVAILABILITY only:
no expected return, PnL, price edge, slippage-adjusted edge, capacity, sizing, profitability or
side decision exists. S10-GATE-QUAL-01 decides sufficiency later; WP172 owns executable economics.

Valid v1 packets are `NON_WALLET` only. `WALLET_DEPENDENT` returns `WALLET_GATE_REQUIRED` with no
record, before any other crossing. No wallet-gate receipt schema, id prefix, "wallet evidence
passed" string or bypass exists. Wallet-dependent qualification remains blocked on
S10-WALLET-03 -> S10-WALLET-04 -> S10-GATE-WALLET-01 -> a wallet evidence lane in S10-QUAL-01 ->
S10-GATE-QUAL-01.

## 10. Failure Discipline

Public failures expose one closed code from `QUALIFICATION_ERROR_CODES` (`SCHEMA_UNSUPPORTED` ..
`INTERNAL_VALIDATION_FAILED`) and never raw mappings, secrets, paths, URLs, question text,
exception repr or local environment details.

## 11. WP170 Crossing Boundary

`experiment_os.py` and `experiment_registry.py` are unchanged and consumed read-only. Compatible
crossing parts: hypothesis plan -> future `AlphaHypothesis` fields; candidate alpha id -> future
`predecessor_candidate_ids`; split policy -> existing `TemporalSplitManifest` group / purge /
embargo / inclusion semantics; metric direction -> `MetricDefinition`; correction policy ->
`ExperimentFamily`; threshold mapping -> `PreregisteredExperiment.acceptance_thresholds`; baseline
rule -> `BaselineDefinition`. No FeatureDefinition, LabelDefinition, ResearchDatasetManifest,
TemporalSplitManifest, BaselineDefinition, ExperimentFamily, PreregisteredExperiment, lifecycle
receipt or run evidence is created. WP170 remains the preregistration/OOS authority.

## 12. Successor Boundary And Non-Authority

Next, only after independent Side13 exact-head review and Karl merge: S10-GATE-QUAL-01 —
Deterministic Qualification Packet Acceptance Gate, which must re-verify the exact candidate and
its bound external evidence and may decide PASS / FAIL / INCONCLUSIVE under its separately frozen
policy. Only after a valid future gate result may separately gated WP170 candidate work begin.

S10-GATE-QUAL-01: NOT AUTHORIZED. WP170 experiment/OOS: NOT STARTED. WP172/WP173: NOT STARTED.
Wallet qualification: NOT AUTHORIZED. H1 #5: NOT AUTHORIZED. Gate C: NOT AUTHORIZED.
Capital/orders: 0. Network, Hermes/provider, scheduler, credential, strategy, paper, execution
and live authority: none. Merge: NOT AUTHORIZED by the executor.

## 13. Merged Predecessor And Qualification Gate Consumer (S10-GATE-QUAL-01)

Section 12 is the historical S10-QUAL-01 boundary. PR #197 / S10-QUAL-01 is MERGED (head
`652a2181926ac6f92f72d0013af99ec5e24ba892`, merge `b5cfb9846ff78af2d1a260843d5f2f1a67639305`) and
this packet remains a non-qualifying substrate: `QualificationCandidate` and `qualification.py`
are unchanged. The separately authorized S10-GATE-QUAL-01 consumer
(`docs/qualification_gate_contract.md`, `qualification_gate.py`) re-validates an existing packet
with `validate_qualification_candidate`, re-binds its Alpha ancestry / current lineage, AF1
receipt and exact provenance manifest set, and alone emits QUAL_PASS / QUAL_FAIL /
QUAL_INCONCLUSIVE in a separate `QualificationGateReceipt`. A packet's `no_qualification_authority`
flag stays true; qualification decision authority lives only in the gate receipt. No real
candidate has been built or evaluated; the first real candidate, WP170 and merge remain NOT
AUTHORIZED by that WP.
