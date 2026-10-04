# Exploratory Gate C Policy Permit Contract (S10-GATE-C-EXPLORE-01)

## 1. Purpose

Answer one question deterministically: given the exact current canonical lifecycle/policy state,
the latest canonical Hermes strategy judgment and the exact current-public EXEC-FEAS evidence for
one execution intent, is that exact intent eligible to proceed to later runtime/account/access/
reconciliation checks inside the current human-authorized exploratory envelope?

The answer is a canonical hard **eligibility** decision. It is not live authority, not order
authority and not account/access truth. An exploratory permit is necessary-but-not-sufficient
future evidence: later protected runtime must still prove everything in section 11 immediately
before any economic mutation.

## 2. Architecture position

Known-candidate path: S10-STRAT-LIFE-01 (MERGED) -> S10-HERMES-STRAT-01 (MERGED) ->
S10-EXEC-FEAS-01 (MERGED) -> S10-GATE-C-EXPLORE-01 (this package) -> S10-DEPLOY-EXEC-01 (next core
successor, NOT STARTED by this package) -> S10-LIVE-ORCH-01 (later). S10-CC-OPS-01 may begin only
after this package merges, under the locked Control Center baseline, as a separate package.
S10-CC-FOUND-01 is parallel/independent; ALPHA-03 is parallel/non-blocking; DATA-03 is unchanged
and non-blocking; S10-DEPLOY-01 host activation is separate. Live trading remains DISABLED;
capital/orders USD 0 / 0.

Source: `src/exploratory_gate_c/` — `models.py` (closed vocabularies, canonical helpers, the two
content-addressed records and strict validators), `evaluator.py` (verified-store loading,
deterministic evaluation, exact permit derivation), `__init__.py` (small import-safe lazy public API:
a fresh `import src.exploratory_gate_c` loads neither submodule nor any consumed dependency chain;
each public name resolves from its submodule on first use). The package
is stdlib-only plus read-only use of the existing public APIs of `src.strategy_lifecycle`,
`src.research_runtime.hermes_controlled_runtime.strategy_manager` and `src.execution_feasibility`,
none of which is modified.

## 3. Public API

- `evaluate_exploratory_gate_c(*, lifecycle_store_path, hermes_manager_store_path,
  strategy_version_id, execution_intent, venue_snapshot, execution_feasibility_assessment,
  evaluated_at_ns) -> ExploratoryGateCDecision`
- `build_exploratory_gate_c_permit(decision, *, execution_intent) -> ExploratoryGateCPermit`
- `validate_exploratory_gate_c_decision`, `validate_exploratory_gate_c_permit`,
  `record_from_mapping` (exact closed loaders that re-derive content ids)
- vocabularies: `REASON_CODES`, `DECISION_STATUSES` (`PERMIT_ELIGIBLE`, `PERMIT_REJECTED`),
  `ERROR_CODES`, `PERMIT_COMPATIBLE_FEASIBILITY_STATUSES`, `PERMIT_COMPATIBLE_HERMES_ACTIONS`,
  `EXPLORATORY_RISK_BAND`

There is no sign, submit, cancel, arm, consume, fetch, store or live API.

## 4. Verified current store inputs

1. The lifecycle store is loaded only through `load_strategy_lifecycle_store`; the result must be
   `STORE_LOADED_VERIFIED` with a non-null verified replay snapshot.
2. The Hermes strategy-manager store is loaded only through
   `load_hermes_strategy_manager_store`.
3. No caller-provided lifecycle or Hermes snapshot is accepted as authority (a non-path argument
   is `FIELD_TYPE_INVALID`).
4. Store paths are operational inputs only: never serialized, hashed into records, logged or
   echoed. No store is written, created or migrated, and no new Gate-C store exists.
5. `evaluated_at_ns` is explicit deterministic evidence time. Future runtime must revalidate
   time/currentness before any economic mutation.

## 5. Strategy, policy, allocation and capacity

- The exact `StrategyVersion` must exist in the verified replay (otherwise `FIELD_VALUE_INVALID`).
- The active policy resolves from `snapshot.active_policy_id`; the current target allocation must
  exist and reference that active policy (otherwise `ALLOCATION_REQUIRED`).
- The allocation must be `EXPLORATORY_LIVE` (`EXPLORATORY_BAND_REQUIRED`), active at
  `evaluated_at_ns` (`ALLOCATION_NOT_ACTIVE`) and have `active_budget_usd > 0`
  (`ACTIVE_BUDGET_REQUIRED`).
- The existing `evaluate_portfolio_capacity(snapshot, evaluated_at_ns)` must be globally
  `PORTFOLIO_CAPACITY_VALID` and must contain a `PORTFOLIO_CAPACITY_VALID` target strategy
  result; otherwise `PORTFOLIO_CAPACITY_REJECTED`. A missing target result counts as a rejection.
  STRAT-LIFE health/restriction/pool/global-capital logic is not reimplemented; its global and
  target reason codes are preserved verbatim in the dedicated inherited fields and are not
  duplicated into the Gate-C reason taxonomy.
- Gate C never mutates policy, allocation, health or restrictions.

Lifecycle currentness binding: the decision and permit bind the exact
`lifecycle_store_head_entry_hash`, `active_policy_id`, `allocation_id` and `strategy_version_id`.
The full lifecycle head is deliberately a hard currentness key because unrelated allocations or
restrictions can change global capacity; later runtime must reject a permit whose bound head no
longer equals the current head.

## 6. Hermes latest-assessment rule

`latest_id = hermes_snapshot.latest_assessment_id(strategy_version_id)`; null rejects with
`HERMES_ASSESSMENT_REQUIRED`. The assessment object is resolved by that id from the verified
snapshot; a caller-selected historical assessment cannot be supplied. Required:

- `assessment.active_policy_id == current active policy id` (else `HERMES_POLICY_MISMATCH`);
- `assessment.strategy_lifecycle_context_sha256 == strategy_lifecycle_context_fingerprint(current
  snapshot, target strategy)` (else `HERMES_CONTEXT_STALE`).

Permit-compatible actions are exactly `CONTINUE + UNCHANGED` and `SCALE + INCREASE`, with
`recommended_health_state` not `QUARANTINED`/`RETIRED` (else `HERMES_ACTION_BLOCKS_NEW_EXPOSURE`),
and `target_risk_band` null or not `PAPER` (else `HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE`).
REDUCE, ADAPT, PAPER, QUARANTINE and RETIRE reject new exposure. A SCALE assessment never increases
the hard allocation: even a VALIDATED_LIVE or MATURE_LIVE target leaves the permit bounded to the
current EXPLORATORY_LIVE allocation and the exact intent. No child StrategyVersion is created.

The Hermes manager store head is recorded as audit provenance only; an unrelated later Hermes
assessment does not invalidate a permit by store head alone.

## 7. Exact EXEC-FEAS binding

The intent, venue snapshot and feasibility assessment must be the exact EXEC-FEAS types and pass
their closed round trips (`EXECUTION_INTENT_INVALID`, `VENUE_SNAPSHOT_INVALID`,
`EXECUTION_ASSESSMENT_INVALID`). The intent must bind the exact current StrategyVersion and the
assessment must reference that intent and snapshot. The supplied assessment must equal
`assess_execution_feasibility(intent, snapshot, evaluated_at_ns=assessment.evaluated_at_ns)`
exactly; otherwise `EXECUTION_BINDING_INVALID`. `evaluated_at_ns` earlier than the assessment
time is `FIELD_VALUE_INVALID`.

Only `FEASIBLE` and `LIMITED` are permit-compatible; `INCONCLUSIVE` and `NOT_FEASIBLE` reject with
`EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE`. LIMITED stays visible, all original diagnostic codes are
preserved, and there is no automatic size haircut.

## 8. Exact-intent static policy ceilings

- `execution_intent.execution_style` must be in `active_policy.allowed_order_styles`
  (`ORDER_STYLE_NOT_ALLOWED`).
- `intent_order_notional_usd = requested_shares * price_limit` with exact Decimal arithmetic
  (rounding traps); it must equal `assessment.intent_notional_at_price_limit_usd`.
- It must not exceed `allocation.active_budget_usd` (`ORDER_NOTIONAL_EXCEEDS_ALLOCATION`),
  `policy.max_order_notional_usd` (`ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX`) or
  `policy.max_per_market_usd` (`ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX`).

These are conservative static exact-intent ceilings only; no current account, gross or
per-market exposure capacity is claimed. Ceilings whose referent is absent (no allocation or no
active policy) are not evaluated; the decision is already rejected by `ALLOCATION_REQUIRED` or
`PORTFOLIO_CAPACITY_REJECTED`.

## 9. Freshness and permit window

- `public_mechanics_deadline_ns = venue_snapshot.book_timestamp_ns +
  execution_intent.max_public_data_age_ns` (null when the snapshot has no book timestamp).
  `EXECUTION_PUBLIC_DATA_STALE` when the deadline is null or `evaluated_at_ns >= deadline`.
- GTD: `gtd_effective_deadline_ns = gtd_expiration_unix_s * 1_000_000_000 - 60_000_000_000`,
  otherwise null. `GTD_EFFECTIVE_WINDOW_EXPIRED` when `evaluated_at_ns >= gtd deadline`.
- `permit_valid_until_ns` = minimum of the non-null public deadline, `active_policy.expires_at_ns`,
  `allocation.valid_until_ns` and GTD deadline. `PERMIT_WINDOW_EMPTY` when it is null or
  `evaluated_at_ns >= permit_valid_until_ns`.

No arbitrary TTL (no 10-minute WP175 arm/qualification validity) is used.

## 10. Records, reasons and errors

Gate-C reasons are unique and emitted in this frozen order: PORTFOLIO_CAPACITY_REJECTED,
ALLOCATION_REQUIRED, EXPLORATORY_BAND_REQUIRED, ALLOCATION_NOT_ACTIVE, ACTIVE_BUDGET_REQUIRED,
HERMES_ASSESSMENT_REQUIRED, HERMES_CONTEXT_STALE, HERMES_POLICY_MISMATCH,
HERMES_ACTION_BLOCKS_NEW_EXPOSURE, HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE,
EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE, EXECUTION_PUBLIC_DATA_STALE, ORDER_STYLE_NOT_ALLOWED,
ORDER_NOTIONAL_EXCEEDS_ALLOCATION, ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX,
ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX, GTD_EFFECTIVE_WINDOW_EXPIRED, PERMIT_WINDOW_EMPTY.
`PERMIT_ELIGIBLE` iff the reason set is empty; otherwise `PERMIT_REJECTED`.

`ExploratoryGateCDecision` (`polymarket-exploratory-gate-c-decision` 1.0.0, id prefix
`exploratorygatecdecision:sha256:`) and `ExploratoryGateCPermit`
(`polymarket-exploratory-gate-c-permit` 1.0.0, id prefix `exploratorygatecpermit:sha256:`) are
immutable closed-schema records. Each content id is SHA-256 of canonical JSON (sorted keys,
`,`/`:` separators, `ensure_ascii=false`, no NaN, UTF-8, explicit nulls and array order preserved)
over every top-level field except the id itself, including the fixed truths. Arrays are bounded,
reason arrays closed and ordered, decimals canonical text, and floats rejected. Reasons that are
pure functions of recorded fields (capacity, missing allocation/assessment, feasibility status,
freshness, GTD and window) are cross-checked on load, so a tampered record fails closed.

The permit builder accepts only an exact `PERMIT_ELIGIBLE` decision and the exact intent it binds;
it takes no independent market, order or cap input. `authorized_order_notional_usd` equals the
exact intent notional and is not a reusable cap; `issued_at_ns` is the decision evaluation time
and `valid_until_ns` the decision `permit_valid_until_ns`.

Structural, tamper and store-load failures raise `ExploratoryGateCError(code)` with the closed
codes FIELD_TYPE_INVALID, FIELD_VALUE_INVALID, LIMIT_EXCEEDED, LIFECYCLE_STORE_INVALID,
HERMES_STORE_INVALID, EXECUTION_INTENT_INVALID, VENUE_SNAPSHOT_INVALID,
EXECUTION_ASSESSMENT_INVALID, EXECUTION_BINDING_INVALID, IDENTITY_DERIVATION_MISMATCH and
INTERNAL_VALIDATION_FAILED, and never create a misleading business rejection. Error precedence:
argument types/values, lifecycle store, StrategyVersion resolution, Hermes store, EXEC-FEAS
records and binding, then evaluation time order. Errors never echo paths, payloads, upstream
exceptions, secrets or account values.

## 11. Fixed runtime-revalidation and non-authority truths

Both records fix to true: `requires_runtime_account_revalidation`,
`requires_access_revalidation`, `requires_reconciliation_revalidation`,
`requires_runtime_identity_revalidation`, `no_credential_authority`, `no_signing_authority`,
`no_order_authority`, `no_execution_transport_authority`, `no_live_authority`. The decision also
fixes `canonical_hard_eligibility_decision`; the permit fixes `exact_intent_only`. No constructor
or loader can set them false.

The permit does NOT establish collateral balance, allowance, positions, gross or per-market
account exposure, committed exposure, open-order count, active-market count, mutation rate,
realized daily loss, drawdown, cumulative account loss, geoblock/access eligibility,
close-only/cancel-only/engine state, credential availability, wallet/session ownership,
reconciliation health, execution host identity or restart/recovery state. Later protected runtime
must prove these immediately before economic mutation. Durable permit consumption and mutation
idempotency belong to future LIVE-ORCH/execution runtime.

## 12. Legacy WP175 separation

WP175 remains the historical/manual real restricted-live canary: Gate-B credential/session, A3 and
real CREATE transport, unchanged. S10-GATE-C-EXPLORE-01 is the V2.1 credential-free exploratory
policy permit: it does not edit or import `src/execution_gateway/**`, issues or consumes no legacy
WP175 Gate-C live permit, arms no session and enters no A3 state.

## 13. Explicit non-goals

No network or account/geoblock read, credential, authenticated client, signing, order
create/post/cancel/amend, paper session, Hermes run, STRAT-LIFE or policy/allocation mutation,
scheduler/daemon/retry loop, new store/cache/ledger/permit-consumption journal, DEPLOY-EXEC,
LIVE-ORCH or Control Center route/UI/endpoint, and no DATA-03 change. Natural canonical semantics
may later support a read-only Control Center view of eligibility reasons, bindings, permit scope,
expiry and revalidation requirements; CC-OPS remains separate. Capital/orders USD 0 / 0;
`LIVE TRADING STATUS: DISABLED`.
