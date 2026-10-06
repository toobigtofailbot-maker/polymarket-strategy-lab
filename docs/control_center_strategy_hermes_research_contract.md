# Control Center StrategyLifecycle + Hermes Research Contract (S10-CC-RESEARCH-01)

## Purpose

The Control Center gains a read-only research vertical that makes canonical StrategyLifecycle
state and canonical Hermes **soft** strategy judgments inspectable without creating a second source
of truth. It is presentation only. It never mutates a strategy, invokes Hermes, or grants portfolio,
paper, execution, Gate-C, LIVE-ORCH, order or live authority.

```text
StrategyLifecycle state
!= Hermes soft judgment
!= portfolio / economic authority
!= EXEC-FEAS
!= Gate-C eligibility
!= LIVE-ORCH admission
!= order authority
```

Hermes soft assessment != human approval != portfolio authority != Gate C.

## Sources

`src/operator_cockpit_research.py` is a pure projection adapter. It reads canonical state only
through the two existing verified loaders:

| Source | Loader | Result used |
| --- | --- | --- |
| StrategyLifecycle store | `load_strategy_lifecycle_store(path)` | valid, non-null `StrategyLifecycleSnapshot` |
| Hermes strategy-manager store | `load_hermes_strategy_manager_store(path)` | verified `HermesStrategyManagerStoreSnapshot` |

The module does not import `sqlite3`, open a store, append, initialize, fabricate a snapshot,
re-validate records with a second validator, or compute a second context hash. Strategy definitions
and adaptive bounds are decoded only with the existing lifecycle `parse_strategy_spec` and
`parse_adaptive_bounds`. Assessment currentness uses only the existing
`strategy_lifecycle_context_fingerprint(snapshot, strategy_version_id)`.

Store paths are optional, explicit `CockpitConfig` fields (`strategy_lifecycle_path`,
`hermes_strategy_manager_path`, appended after the existing four fields) and CLI flags
(`--strategy-lifecycle-store`, `--hermes-strategy-manager-store`). There is no environment fallback,
default path, repository scan or path exposure in API output.

## Independent Source Behavior

- Strategy routes require the lifecycle source. If Hermes is unconfigured or unavailable they stay
  usable and return `latest_hermes_assessment: null`; Hermes availability is never a prerequisite
  for viewing canonical lifecycle state.
- Hermes routes require the Hermes source **and** the lifecycle source, because every assessment
  carries a context status derived from the current lifecycle snapshot. If either is unavailable they
  return `SOURCE_UNAVAILABLE`.

## Routes (GET only)

| Route | Response |
| --- | --- |
| `GET /api/strategies` | `{items, count, limit}` of strategy summaries |
| `GET /api/strategies/{strategy_version_id}` | `{item}` strategy detail |
| `GET /api/hermes/assessments` | `{items, count, limit}` of assessment items |
| `GET /api/hermes/assessments/{assessment_id}` | `{item}` assessment detail |

These are the only new routes; the existing fourteen GET routes are unchanged. POST, PUT, PATCH and
DELETE return 405. List routes reuse the existing `limit` rule: default 50, minimum 1, maximum 100;
duplicate or unknown query keys are rejected with `INVALID_INPUT`. `count` is the returned item count,
not the store cardinality.

## Identifier Validation

- Strategy: `^strategyversion:sha256:[0-9a-f]{64}$`
- Assessment: `^hermesstrategyassessment:sha256:[0-9a-f]{64}$`

Malformed ids return `400 INVALID_INPUT` before any source is consulted; valid but absent ids return
`404 NOT_FOUND`. The rejected raw id is never echoed.

## Ordering

- Strategies: `created_time_ns` DESC, then `strategy_version_id` ASC.
- Assessments: `decision_time_ns` DESC, then `assessment_id` ASC.

`limit` is applied after sorting.

## DTO Field Sets

Strategy summary: `strategy_version_id`, `strategy_family_id`, `parent_strategy_version_id`,
`strategy_label`, `evidence_posture`, `adaptation_class`, `created_time_ns`, `current_health_state`,
`current_allocation` (null or `allocation_id`, `policy_id`, `risk_band`, `active_budget_usd`,
`allocation_basis`, `valid_from_ns`, `valid_until_ns`), `active_restriction_count`,
`evidence_ref_count`, `latest_hermes_assessment` (null or `assessment_id`, `information_cutoff`,
`confidence_label`, `lifecycle_action`, `recommended_health_state`, `risk_direction`,
`target_risk_band`, `context_status`).

Strategy detail: `strategy_version_id`, `strategy_family_id`, `parent_strategy_version_id`,
`strategy_label`, `evidence_posture`, `adaptation_class`, `strategy_code_identity`,
`created_time_ns`, `creation_provenance`, `evidence_refs`, `family` (`strategy_family_id`,
`family_key`, `family_label`), `lineage_strategy_version_ids`, `strategy_definition` (`thesis`,
`universe`, `entry_rule`, `exit_rule`, `execution_rule`, `parameters`), `adaptive_bounds`,
`current_state` (`health_state`, `active_policy_id`, `allocation`, `active_restrictions`,
`strategy_lifecycle_context_sha256`), `latest_hermes_assessment`.

Active restrictions come only from `snapshot.restrictions_of(strategy_version_id)` and expose
`restriction_receipt_id`, `restriction_key`, `restriction_kind`, `max_active_budget_usd`,
`created_time_ns`. Cleared restrictions are never shown as active and a restriction is never a command.

Allocation is a lifecycle budget reservation, not actual exposure. No private account identifier is
returned.

Assessment item: `assessment_id`, `strategy_version_id`, `strategy_family_id`,
`predecessor_assessment_id`, `information_cutoff`, `decision_time_ns`, `trigger`,
`confidence_label`, `assessment_summary`, `lifecycle_action`, `recommended_health_state`,
`risk_direction`, `target_risk_band`, `context_status`, `canonical_soft_strategy_decision` (true).

Assessment detail adds: `run_record_id`, `runtime_request_id`, `runtime_receipt_id`, `subject_refs`,
`input_evidence_refs`, `evidence_for`, `evidence_against`, `uncertainties`, `known_missing_data`,
`falsification_checks_performed`, `limitations`, `what_would_change_the_conclusion`,
`suggested_next_research_steps`, `adaptation_recommendation`, `strategy_lifecycle_context_sha256`,
`lifecycle_store_head_entry_hash`, `active_policy_id`, `run` (`provider_label`, `model_label`,
`hermes_version`, `terminal_status`, `start_utc`, `end_utc`, `estimated_cost_usd`, `cost_status`,
`cost_source`) and `non_authority` (`canonical_soft_strategy_decision`, `no_credential_authority`,
`no_portfolio_policy_authority`, `no_hard_risk_override`, `no_paper_execution_authority`,
`no_order_authority`, `no_execution_authority`, `no_live_authority`). `run` is resolved by exact
`run_record_id` from the same verified Hermes snapshot; an impossible missing run fails closed.

No raw model output, prompt, hidden reasoning, chain-of-thought, source URL list or raw draft field
is exposed.

## Lineage

`lineage_strategy_version_ids` is derived only from exact `parent_strategy_version_id` links in the
verified lifecycle snapshot, ordered root to target, within the target's family. A bounded cycle and
length guard applies; if a finite same-family lineage cannot be produced the route fails
`SOURCE_UNAVAILABLE`.

## Context Status (display only)

For each assessment exactly one status is derived:

- `CURRENT` iff the StrategyVersion exists in the current lifecycle snapshot and
  `assessment.strategy_lifecycle_context_sha256 == strategy_lifecycle_context_fingerprint(snapshot, assessment.strategy_version_id)`;
- `STALE_CONTEXT` iff the version exists but the fingerprint differs (for example after a canonical
  health, allocation, restriction or active-policy transition);
- `TARGET_MISSING` iff the version does not exist in the current lifecycle snapshot.

The status is not Gate-C eligibility, tradeability, execution feasibility, deployment readiness or
live permission. A Hermes assessment is never called approved.

## Latest-Assessment Derivation

A strategy's `latest_hermes_assessment` comes only from the verified manager snapshot mapping
`latest_assessment_by_strategy_version`. It is never chosen by timestamp, list order or lexical id.

## Closed Error Mapping

| Condition | Response |
| --- | --- |
| malformed id, bad `limit`, duplicate or unknown query key | `400 {"error":{"code":"INVALID_INPUT"}}` |
| valid but absent id | `404 {"error":{"code":"NOT_FOUND"}}` |
| unconfigured required source; any loader, path, schema, tamper, parse or internal projection failure | `503 {"error":{"code":"SOURCE_UNAVAILABLE"}}` |

Internal error codes, paths, raw exceptions, SQLite messages, raw Hermes output, prompts and
environment values are never echoed.

## Frontend

Routes `/strategies` and `/hermes` join `/overview`, `/markets`, `/experiments`, `/paper` and
`/audit`. Query families `strategies` and `hermes` use the keys `["cc","strategies","list"]`,
`["cc","strategies","detail",strategy_version_id]`, `["cc","hermes","list"]` and
`["cc","hermes","detail",assessment_id]`. The existing conservative Query defaults (no retry, no
focus/reconnect refetch, `staleTime` Infinity, no polling) and active-family manual Refresh are
unchanged; selection is component-local. The views state that allocation is a lifecycle budget
reservation, that Hermes assessments are soft research judgments that grant no portfolio, execution,
Gate-C or live authority, and show the context status. There is no Run, Reassess, Approve, Apply,
Allocate, Pause, Scale or Trade control.

## Alpha Exclusion

Alpha Factory lineage (`OpportunityCandidate -> HypothesisFamily -> ResearchEpisode`) has no
universal canonical mapping to a `StrategyVersion`. This vertical does not import Alpha Factory code
and never infers an Alpha-to-Strategy relationship from evidence refs, subject refs, labels, text or
provenance. Alpha/Evidence integration = S10-CC-RESEARCH-02 (separately gated).

## Non-Authority

No mutation, network, credential, account, Hermes-runtime, strategy, paper, Gate-C, LIVE-ORCH,
signing, order, execution, deployment, live or capital authority. Live trading remains DISABLED;
capital at risk USD 0.
