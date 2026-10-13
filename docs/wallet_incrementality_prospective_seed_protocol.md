# Prospective wallet comparison method protocol

Status: METHOD_PROTOCOL_COMMITTED / STUDY_NOT_ACTIVATED / REAL_PAIRED_UNITS_NOT_ESTABLISHED.

This is the S10-WALLET-SEED-01 Phase-A method contract, not an operational experiment. Karl authorized only offline documentation/tests. No real enrolled unit, source route, forecast output, qualification receipt or measured advantage is established. Prior inspection found zero verified eligible real pairs in bounded scope; evidence outside it remains UNKNOWN.

## Authority and compatibility

The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` controls: credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts. None is crossed. No collection, private-account read, provider/model call, signing/order, scheduler, paper, execution, Gate C or live authority. WALLET-01/02/03, scientific/qualification gates, WP170, strategy lifecycle, ALPHA-03/04 and DATA-03 are unchanged.

## Method identity and future study seal

The following is the single closed method JSON envelope. Its `method` payload is exactly the valid example in the reviewed machine specification. `method_digest` equals `walletmethod:sha256:` plus SHA-256 of canonical UTF-8 JSON `{"method": method_payload}`: sorted object keys, compact separators, ensure_ascii=false, allow_nan=false, explicit nulls and array order preserved. The digest field is outside its own preimage; no business-policy field is excluded. This METHOD identity is not source authenticity, a real enrolled STUDY seal or implementation/activation authority. Included scalar/array changes alter identity; object insertion order does not.

```json
{
  "method": {
    "schema_id": "wallet-comparison-method@1.0.0",
    "study_state": "NOT_ACTIVATED",
    "target": {
      "kind": "FINAL_BINARY_TARGET_TOKEN_PAYOUT",
      "unit_count": 1,
      "cluster_count": 1,
      "instrument_class": "STANDARD_BINARY_OUTCOME",
      "target_end_min_seconds_after_t0": 3600,
      "target_end_max_seconds_after_t0": 604800,
      "label_deadline_seconds_after_target_end": 2592000
    },
    "freeze": {
      "minimum_predecision_freeze_seconds": 86400,
      "discovery_cutoff_rule": "NOT_AFTER_FREEZE",
      "enrollment": "MANUAL_OPERATIONAL_FEASIBILITY_NO_OUTCOME_RANK_SIGNAL_SCREEN",
      "membership": "ONE_PREDECLARED_CALENDAR_UNIT_NO_REPLACEMENT",
      "evaluation_interval": "T0_INCLUSIVE_T0_PLUS_1_MICROSECOND_EXCLUSIVE",
      "action_lookback_seconds": 3600,
      "amendment": "NEW_HUMAN_APPROVED_DIGEST_AND_FUTURE_PERIOD",
      "no_training": true,
      "study_seal_required_before_collection": true,
      "study_seal_fields": [
        "method_digest",
        "code_sha",
        "condition_id",
        "target_token_id",
        "complement_token_id",
        "rule_snapshot_digest",
        "event_id",
        "leakage_group_id",
        "source_chain_id",
        "cohort_reference_id",
        "profile_source_reference_id",
        "cluster_membership_digest",
        "freeze_time",
        "decision_time",
        "target_event_end",
        "label_deadline",
        "nonwallet_version",
        "wallet_added_version",
        "source_route_evidence_refs",
        "observation_group_missingness_policies",
        "approved_source_call_byte_elapsed_limits",
        "human_approval_record"
      ]
    },
    "forecasts": {
      "nonwallet_version": "NONWALLET_MIDPOINT_V1",
      "wallet_added_version": "WALLET_BLEND_010_V1",
      "baseline_rule": "LATEST_ADMISSIBLE_TARGET_BOOK_MIDPOINT",
      "max_quote_age_seconds": 30,
      "max_spread": "0.1",
      "wallet_weight": "0.1",
      "nonwallet_weight": "0.9",
      "wallet_rule": "LAST_ADMISSIBLE_CLUSTER_BUY_TARGET_1_COMPLEMENT_0",
      "no_signal_rule": "P_WALLET_EQUALS_P_NONWALLET_ONLY_WITH_COMPLETE_COVERAGE",
      "unknown_rule": "NO_FORECAST",
      "conflict_rule": "SAME_CLOCK_OPPOSING_VOTES_OR_BOOKS_UNKNOWN",
      "masked_control_rule": "P_MASKED_EQUALS_P_NONWALLET",
      "decimal_precision": 80,
      "primary_loss": "BINARY_BRIER",
      "delta_direction": "L_NONWALLET_MINUS_L_WALLET_ADDED",
      "costs_enter_score": false,
      "calibrated": false,
      "observation_delay_seconds": 0,
      "baseline_endogeneity_posture": "NO_EXPLICIT_WALLET_FEATURES_NOT_CAUSAL_INDEPENDENCE"
    },
    "sources": {
      "wallet_identity": "CHAIN_NATIVE_STRONG_ONLY",
      "wallet_finality": "FINALIZED_BY_DECISION",
      "chain_proof": "RETAINED_LOG_RECEIPT_CANONICAL_BLOCK_FINALITY_AND_AUDITED_FILL_ABI_MAPPING",
      "api_fallback": false,
      "book_source_system": "POLYMARKET_CLOB",
      "book_endpoint": "/book",
      "book_retrieval_method": "GET",
      "book_media_type": "application/json",
      "book_proof": "ORIGINAL_RAW_BYTES_REFERENCE_MANIFEST_LEDGER_AND_UNCHANGED_WALLET03_BUILDER",
      "two_sides": "TWO_SEPARATE_ONE_WITNESS_CALLS_SAME_ORIGINAL_BOOK_AND_PROFILE",
      "book_admission": "OBSERVED_BOTH_SIDES",
      "source_origin": "FUTURE_CAPTURE_ROUTE_ATTESTATION_REQUIRED_HASH_ALONE_INSUFFICIENT",
      "clock_rule": "NATIVE_ADMISSIBLE_AVAILABILITY_NEVER_EVENT_TIME",
      "existing_source_route_proved": false,
      "native_profile_window_required": true
    },
    "labels": {
      "rule": "FINALIZED_CTF_BINARY_PAYOUT_AND_CONSISTENT_VENUE_RESOLVED_STATUS",
      "instrument_rule": "EXACT_SEALED_CHAIN_CONDITION_TOKEN_RULE_MAPPING",
      "observation_rule": "STRICTLY_AFTER_TARGET_END_AND_DECISION_BY_DEADLINE",
      "unknown_finality_rule": "NO_LABEL",
      "disputed_void_cancelled_rule": "NO_LABEL",
      "weather_substitution": false
    },
    "accounting": {
      "status_precedence": [
        "EXCLUDED",
        "UNKNOWN",
        "UNMATCHED",
        "MATCHED",
        "PENDING",
        "CENSORED"
      ],
      "pending_rule": "PAIRED_FORECASTS_AWAIT_LABEL_BEFORE_DEADLINE",
      "conservation_terms": [
        "EXCLUDED",
        "UNKNOWN",
        "UNMATCHED",
        "PENDING",
        "CENSORED",
        "MATCHED"
      ],
      "denominator": "ENROLLED_UNIT_AND_UNIQUE_FROZEN_MATCHED_LEAKAGE_GROUP",
      "unknown_group_count": null,
      "method_only_enrolled_count": "NOT_ESTABLISHED",
      "duplicate_related_rule": "NO_NEW_UNIT_OR_GROUP",
      "zero_matched_status": "INSUFFICIENT_EVIDENCE",
      "zero_matched_numeric_summaries": null,
      "significance_claim": false
    },
    "authority": {
      "advisory_only": true,
      "no_execution_authority": true,
      "no_strategy_authority": true,
      "no_qualification_authority": true,
      "real_collection_authorized": false,
      "provider_model_calls_authorized": false,
      "gate_c_authorized": false,
      "capital_at_risk_usd": 0
    }
  },
  "method_digest": "walletmethod:sha256:e08fe248dff75bd1e67503426801a6b6940d42ad4acb2bded89dd1650cba1656"
}
```

## Prospective target, clocks and forecasts

Hypothesis: a small fixed directional wallet intervention improves paired binary Brier loss relative to a contemporaneous nonwallet market forecast. It is deliberately uncalibrated; no wallet skill assumption is made. Name arms p_nonwallet and p_wallet_added; do not reuse qualification's B1/B2 names or source classes.

Pilot: ONE predeclared standard-binary condition, target token and complementary token; ONE canonical public-account cluster; ONE calendar decision cutoff T0. Choose these manually for source/contract feasibility before any study data collection, without historical PnL/rank, outcome or wallet-direction screening. The operator must record the selection reason as operational feasibility, not predictive merit. Cohort cluster membership uses only discovery-admissible protocol-declared/onchain-confirmed links; do not infer people. Unknown relation/group coverage blocks independent-sample claims. No second market, alternate wallet, replaced failed unit or automatic extension.

Future activation seal must contain exact method digest; published code SHA; namespaced condition/token pair, binary-rule snapshot digest, event/leakage-group ID and source_chain_id; verified cohort/profile source references and cluster membership digest; Tfreeze, T0, target_event_end and label_deadline; forecast versions NONWALLET_MIDPOINT_V1 / WALLET_BLEND_010_V1; observation/group/missingness policies; source-route evidence references; exact planned source-call/byte/elapsed limits approved by Karl; and human authorization bound to the exact seal digest. No unfilled parameter is permitted in an actual seal.

Require Tfreeze <= T0 - 24 hours; no study collection until freeze/approval; discovery cutoff <= Tfreeze; T0 + 1 hour <= target_event_end <= T0 + 7 days; label_deadline = target_event_end + 30 days. Enrollment is outcome-blind and committed before collection; decision membership is the single sealed unit, not a unit chosen when a wallet trades. The evaluation interval is [T0,T0+1 microsecond); action lookback [T0-3600 seconds,T0]. A study amendment requires human approval, new digest and genuinely future interval; never backdate or replace excluded/censored units in the original pilot. No fit, tuning, cross-validation, formation/selection sample or existing WP170 split is created. With one group, there is no train/test sharing. Future repeat cohorts require separately frozen group exclusion, purge and embargo rules; this pilot grants no repeat right.

All availability clocks are explicit UTC. Local first-seen/retained availability is decisive when present; otherwise native public availability only when independently evidenced under the shared admissibility rule; event/block time never substitutes. Missing/uncertain/corrected/backfilled clocks reject admission. Effective finality must be observed by T0 for wallet actions. Keep source identities, observed clocks and later revisions append-only; post-cutoff corrections cannot improve the original forecast.

Nonwallet rule: select the latest original retained target-token CLOB GET /book observed in [T0-30 seconds,T0], admitted by section 7, with 0 < best_bid <= best_ask < 1 and spread <= 0.1. Select by availability clock, not price; simultaneous semantically conflicting books produce UNKNOWN, while byte-identical duplicates collapse. Let p_nonwallet=(best_bid+best_ask)/2. No last-trade, historical price, complement, stale quote or wallet-based fallback. Use Decimal precision 80 and canonical fixed-point strings; reject floats/exponents/nonfinite values. The 30-second freshness and 0.1 spread limits are frozen feasibility choices, not empirical optimality claims. Nonwallet means no explicit wallet/account/direction features or wallet-dependent book selection; it does not assert that market prices are unaffected by wallet trading. Both arms share that possibly contaminated public price. The comparison tests only additional predictive information conditional on it, not causal independence or an unpriced executable edge.

Wallet input: among admissible finalized standard BUY fills by the sealed cluster for either sealed token within the lookback, use the last decisively observed event after native reconciliation. The action must also satisfy the unchanged native cohort/profile evidence window; never bypass its event-time/window exclusions to manufacture admissibility. v=1 for target-token BUY; v=0 for complement BUY. Ignore sizes, SELL, PnL, rebates, rank and historical skill. Same-clock opposing directions or unsupported identity/finality make the wallet arm UNKNOWN; never tie-break towards a favorable direction. Equivalent actions/related addresses collapse natively; distinct same-direction same-clock fills give the same vote. A COMPLETE source-coverage receipt with no qualifying BUY gives NO_SIGNAL; absent/partial feed coverage is UNKNOWN, not NO_SIGNAL.

Wallet rule: p_wallet_added=0.9*p_nonwallet+0.1*v for a known vote; p_wallet_added=p_nonwallet for proved NO_SIGNAL. Unknown wallet coverage, identity, availability or finality means no wallet-added forecast and UNKNOWN. A forecast absent despite verified applicable source coverage and other admission facts is UNMATCHED. Unknown is never silently converted to a no-signal or unmatched observation. Weight 0.1 is a preregistered conservative perturbation, not fitted/calibrated belief. Both forecasts have decision timestamp T0, with observation_delay_seconds=0: use only information already admissible by T0, with no post-cutoff waiting, interpolation or wallet-triggered decision shift. Same target, information cutoffs and unit membership apply to both arms. Costs/fees/sizing do not enter predictive Brier loss; no economic comparison is claimed. Negative control: on that same matched unit mask wallet information, yielding p_masked=p_nonwallet and exactly zero loss difference; this diagnostic is not a third primary test or additional observation.

## Original source admission

Freeze CHAIN_NATIVE_STRONG as the sole wallet-action route for this seed; no API fallback or SOURCE_CONTENT_DERIVED upgrade. Require retained public chain log, transaction receipt and canonical block/finality evidence, native identity (chain_id, transaction_hash, log_index), block hash/number, transaction index, removed=false, FINALIZED, confirmation/finality availability <=T0; and audited protocol/ABI/contract-version evidence connecting the specific fill, public account, condition/token, BUY direction and standard binary economic object. Exact chain ID/contracts come from the precollection sealed source evidence; no unverified address or ABI is prescribed here. An arbitrary caller label is insufficient. Reorg/disagreement/ambiguous decoding cannot be admitted. Existing contracts represent this data; reconciliation does not supply a real RPC/indexer or prove the decoder. That missing source capture/decoding proof is the ONE prerequisite for the future seed operator, not for this documentation WP.

Load original WALLET-01 ledger with exact expected head; canonically rebuild WALLET-02 cohort/profile and use unchanged build_wallet_copyability_research_assessment. Original source inputs must rederive mapped evidence. A self-hashed standalone mapping never establishes authenticity. Track a verified ledger snapshot at T0 and source-route receipt; later labels/append growth do not redefine the decision head.

Book witnesses require actual retained bytes, SHA-256/byte length, RawEvidenceReference and ResearchProvenanceManifest stored in that ledger; source_system=POLYMARKET_CLOB, endpoint=/book, method=GET, media_type=application/json, request token_id and response asset_id/market matching the sealed identifiers. Raw/witness clocks must agree; manifest cutoff <= quote availability <=T0, ingestion <=T0, no future revision/resolution, DQ OK, replay EXACT/FAITHFUL. Validate both bid and ask top levels and depth against original bytes. To reuse the unchanged builder's duplicate-reference rule, prove bid and ask using two separate calls with the same original profile/head/cohort/context inputs and one witness each; never pass two witnesses sharing a raw reference into one call. Both must be OBSERVED and match the same retained book. The future source operator must independently attest the recorded endpoint/response capture path; hashes alone prove retained-byte integrity. WS frames are not interchangeable with /book. Missing source binding remains inadmissible even if SCENARIO_ONLY calculation is possible.

Copyability delay/cost result status is not forecast or label admission. This predictive method uses quote/event source evidence only and never needs invented fees or realized follower fills; explicit unknown cost assumptions remain unknown. Existing WALLET-03 limits and immutable flags remain binding.

## Labels and mutually exclusive accounting

Prediction target: eventual final binary payout of the sealed target token after target_event_end. Label Y is 1 or 0 only when independently obtained retained public settlement evidence binds the same chain/condition/token mapping and frozen rule snapshot: finalized canonical block, positive CTF payout denominator, binary target/complement numerators summing to the denominator and each 0 or denominator; plus consistent retained public venue resolved status. Label evidence availability must be > target_event_end and > T0 and <= label_deadline. No wallet/provider-model-derived label, weather substitution, unresolved/disputed/void/cancelled label, caller success flag or silent rewriting. Settlement route/contract mapping must be proved by the future source operator before activation; absent proof yields UNKNOWN, not CENSORED. CENSORED is reserved for otherwise admissible forecasts whose verified label source has not produced an admissible final label by the deadline. Early settlement inconsistent with the frozen event end requires review/exclusion, not a shifted horizon.

Status precedence on the sole ENROLLED unit: EXCLUDED for contradiction, unsupported instrument/identity, leak or invalid seal; otherwise UNKNOWN for uncertain grouping, source coverage, clocks, finality or source-route proof; otherwise UNMATCHED when either required forecast is absent despite verified coverage and observability; otherwise MATCHED if both forecasts and an admissible final label are present; otherwise PENDING if both forecasts are present but the final label has not yet become admissible and the deadline has not passed; otherwise CENSORED once the deadline has passed without an admissible final label, provided the source route itself is verified. Before the deadline, unresolved labels are PENDING, not CENSORED, and cannot establish advantage. Primary reasons are mutually exclusive by this order; retain secondary diagnostic reasons without adding them to denominators. Candidate diagnostics before enrollment do not enlarge the enrolled denominator. A negative terminal is a completed pilot, not permission to replace the unit.

Conservation: enrolled = excluded + unknown + unmatched + pending + censored + matched; enrolled=1 only after a real study seal; METHOD-only enrolled count is NOT_ESTABLISHED, not a fake 1. Track forecast-eligible count separately (pending+censored+matched). Independent matched groups are unique frozen leakage groups of matched units; unknown group count stays null and yields UNKNOWN. Related accounts, duplicate fills, shared market/condition/event outcomes never multiply groups. This pilot has at most one independent group, with no significance or generalizable skill inference.

For a MATCHED unit only: L_nonwallet=(p_nonwallet-Y)^2, L_wallet_added=(p_wallet_added-Y)^2, delta=L_nonwallet-L_wallet_added (positive is lower wallet-added Brier loss for that unit). Report both losses, signed delta, complete statuses and the group count together; no winners-only summary. Zero matched units: INSUFFICIENT_EVIDENCE and all numerical loss/advantage summaries null. Statistical power, thresholds, fitting and promotion are later separately authorized decisions.


## Requirement and negative-test evidence

The six named tests in `tests/test_wallet_incrementality_prospective_seed_protocol_docs.py` are documentation checks using synthetic facts and Decimal algebra; they are not a production source authenticator or real study scorer.

| Requirement | Evidence node | Negative boundary |
|---|---|---|
| R001 | test_seed01_method_block_and_freeze_identity | missing/null/wrong-type/empty/extra fields, malformed/duplicate JSON, rehashed policy drift |
| R002 | test_seed01_source_route_and_cutoff_contract | weak identity, unbound/WS/late/stale book, finality/coverage uncertainty, self-hash-only proof |
| R003 | test_seed01_forecast_algebra_and_controls | baseline wallet contamination, floats/exponents, unknown vote, same-clock conflict; proved no-signal positive |
| R004 | test_seed01_label_finality_and_horizon_contract | future/early/wrong-instrument/nonbinary/void labels, missing settlement proof |
| R005 | test_seed01_membership_and_denominator_contract | zero matched, pending/censored precedence, duplicates/related events, unknown groups, replacement/leak |
| R006 | test_seed01_scope_truth_and_non_authority | false authority, extra scope, fake enrolled/accepted/ready state |
| R007 | native final readiness, exact scope, artifact and static/security checks | final diff must equal exactly eight files |
| R008 | one stable committed-head full offline Linux suite | unavailable mandatory validation blocks readiness |

Negative-test matrix required: YES. Free-text credential-token, typo and case-insensitive wording-filter categories are NOT_APPLICABLE because no free-text validator is added. Existing secret/boundary checks remain required. Synthetic negatives do not prove observed adversarial source validation.

Illustrative math only: p0=0.6, Y=1. Target BUY gives pW=0.64, L0=0.16, LW=0.1296, delta=0.0304; complement BUY gives pW=0.54, LW=0.2116, delta=-0.0516. Proved NO_SIGNAL and masked-wallet control give pW=p0 and delta=0. These values are not observations.

## Separately gated successor and rollback

S10-WALLET-SEED-02 owns the one bounded future prerequisite: prove public-chain decode/finality and original-book capture/retention, and form the exact human-approved study/forecast seal. Acquisition requires a separately approved exact source budget/host gate; numerical WALLET-04 waits for genuinely matched labels and groups. No seed operator is implemented here. Revert this docs/tests WP before any activation if rejected; preserve immutable later-study records if any later study has used this method. Do not silently replace their method.
