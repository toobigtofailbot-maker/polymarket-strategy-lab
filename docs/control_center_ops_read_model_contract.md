# Control Center Portfolio / Risk / Runtime Operations Read Model Contract (S10-CC-OPS-01)

## Purpose

S10-CC-OPS-01 adds one bounded, read-only `/ops` Control Center workspace. It shows three existing
canonical sources side by side, without combining them and without creating a second portfolio,
risk, execution, currentness or incident truth system:

1. **Portfolio Authority**: StrategyLifecycle portfolio policy, budget reservations and the canonical
   `evaluate_portfolio_capacity(snapshot, at_time_ns)` result, through one new GET endpoint.
2. **Simulated Paper Risk**: the existing `/api/paper/summary` and `/api/paper/risk` projections,
   visibly `SIMULATED PAPER ONLY`.
3. **Recorded Runtime / Gateway**: the existing sanitized `/api/gateway/status` and
   `/api/gateway/audit` projections, visibly recorded gateway state rather than a fresh account,
   host or network check.

The separations are permanent:

```text
portfolio policy/reservations
!= actual account exposure
!= paper account/risk
!= recorded gateway state
!= current authenticated account risk
!= EXECUTION_HOST_CURRENT
!= EXECUTION_NETWORK_ELIGIBLE
!= Gate-C eligibility
!= execution/live authority
```

## Portfolio source (verified loader only)

| Concern | Only allowed owner | Requirement |
|---|---|---|
| Lifecycle state | `load_strategy_lifecycle_store(path)` | `result.is_valid` and a non-null `StrategyLifecycleSnapshot` |
| Capacity | `evaluate_portfolio_capacity(snapshot, evaluated_at_ns)` | called exactly once per request with the same verified snapshot |
| Store path | the existing `CockpitConfig.strategy_lifecycle_path` / `--strategy-lifecycle-store` | no new config field, flag, default path or discovery |

The projection is the new pure module `src/operator_cockpit_ops.py`. Its only `src.*` import is the
public `src.strategy_lifecycle` package. It never imports `sqlite3`, opens a store, appends,
initializes, re-validates records, fabricates a snapshot or performs capacity arithmetic. It does not
import the paper, execution-gateway, LIVE-ORCH, Gate-C, EXEC-FEAS, deployment, subprocess or network
families. Reads leave the lifecycle store bytes unchanged.

### Evaluation time

`src/operator_cockpit.py` validates the query (none allowed), then reads `time.time_ns()` exactly
once per `/api/ops/portfolio` request and passes that integer to the projection. The same value drives
the canonical evaluator, every `allocation.is_active_at(evaluated_at_ns)` check and the response
`evaluated_at_ns`. The browser clock never drives capacity semantics. (Nanosecond integers above
2^53 may lose low-order digits when a browser parses JSON; the displayed time is informational and
never re-used for any computation.)

## `GET /api/ops/portfolio`

- GET only; POST/PUT/PATCH/DELETE return 405.
- No query parameters: any query pair returns `400 INVALID_INPUT`.
- Total `/api` route set after this WP: exactly 25.
- Any unconfigured, missing, invalid-path, wrong-schema, tampered, malformed or unexpected
  source/projection failure returns `503 {"error": {"code": "SOURCE_UNAVAILABLE"}}` only. No path,
  exception text, raw store value or traceback is emitted.

Top-level keys: `read_only` (always `true`), `evaluated_at_ns`, `lifecycle_store_head_entry_hash`,
`active_policy`, `capacity`, `strategy_reservations`, `non_authority`.

### `active_policy`

`null` when `snapshot.active_policy_id is None`; otherwise the exact same-snapshot policy:
`policy_id`, `predecessor_policy_id`, `policy_label`, `venue_scope`, `account_scope_ref`,
`effective_from_ns`, `expires_at_ns`, `limits`, `allowed_order_styles`, `created_time_ns`.

`limits` carries exactly the 17 policy money/count limit fields (global capital-at-risk, gross
exposure, daily/drawdown/cumulative loss ceilings; exploratory/validated/mature pool ceilings;
per-strategy ceilings by band; per-market and order-notional ceilings; max active strategies,
markets, simultaneous open orders and mutations per minute). They are policy ceilings, never actual
exposure, balance or utilization.

### `capacity`

The canonical evaluator result, projected exactly: `status`, `reason_codes`, `evaluated_at_ns`
(the evaluator's `at_time_ns`), `policy_id`, `reserved_budget_usd` {`exploratory` <-
`exploratory_active_usd`, `validated` <- `validated_active_usd`, `mature` <- `mature_active_usd`,
`total` <- `total_active_usd`} and `active_real_risk_strategy_count`. No other capacity arithmetic
exists in the backend or the frontend.

A valid store with no active policy is an HTTP 200 domain state: `active_policy = null` and the
canonical `PORTFOLIO_CAPACITY_REJECTED` / `POLICY_NOT_ACTIVE` result. A canonical capacity rejection
(health, restriction, pool, global or per-strategy reasons) is also HTTP 200 domain truth, never
`SOURCE_UNAVAILABLE`.

### `strategy_reservations`

One item per `snapshot.current_allocation_by_strategy_version` record: `allocation_id`,
`strategy_version_id`, `strategy_label`, `policy_id`, `risk_band`, `active_budget_usd`,
`allocation_basis`, `valid_from_ns`, `valid_until_ns`, `active_at_evaluation`, `health_state`,
`capacity_status`, `capacity_reason_codes`, `active_restrictions` (`restriction_receipt_id`,
`restriction_key`, `restriction_kind`, `max_active_budget_usd`, `created_time_ns`).

- `active_at_evaluation` means only `allocation.is_active_at(evaluated_at_ns)`; it is not policy,
  capacity, Gate-C or live eligibility.
- `capacity_status` / `capacity_reason_codes` are the exact `capacity.strategy_result(id)` values;
  when the evaluator returns no per-strategy result (for example, no active policy) they are `null`
  and `[]`. No rejection reason is ever invented.
- Labels, health and restrictions come from the same snapshot only.
- Order: active at evaluation first; then canonical `RISK_BANDS` order; then `strategy_label`; then
  `strategy_version_id`.

### `non_authority`

Exactly: `budget_reservation_only`, `actual_account_exposure_not_measured`, `orders_not_measured`,
`fills_not_measured`, `pnl_not_measured`, `gate_c_not_implied`, `execution_not_implied`,
`live_not_implied`, all `true`.

## Paper and gateway composition (frontend only)

There is no backend aggregate endpoint. The `/ops` browser view independently consumes the existing
`/api/paper/summary`, `/api/paper/risk`, `/api/gateway/status` and `/api/gateway/audit` endpoints.
Their backend DTOs, semantics and source (`src/paper_trading/**`, `src/execution_gateway/**`) are
unchanged.

- Paper panel: `SIMULATED PAPER ONLY`. Paper cash and PnL are never combined with budget
  reservations or gateway values. Detailed orders, fills and positions stay on `/paper`.
- Gateway panel: `Recorded gateway state`, `Recorded gateway access state` and the notice
  `Persisted gateway evidence; not a fresh account, host or network eligibility check.` The recorded
  `access_state`, heartbeat, reconciliation and restricted-live summary are never promoted to current
  authenticated account truth, `EXECUTION_HOST_CURRENT`, `EXECUTION_NETWORK_ELIGIBLE`, Gate-C
  eligibility or live readiness.
- Gateway audit rows keep the exact source metadata (`sequence`, `event_id`, `event_type`,
  `event_time_ns`, `event_hash`) under the label `Recent recorded gateway events`. No incident or
  alert registry exists and none is invented.

## Frontend contract

- Exactly one new primary route, `/ops` ("Operations"), between `/alpha` and `/paper`; all existing
  routes are preserved.
- `QueryFamily` gains `ops`. OPS-owned keys: `["cc","ops","portfolio"]`,
  `["cc","ops","gateway","status"]`, `["cc","ops","gateway","audit"]`,
  `["cc","ops","paper","summary"]`, `["cc","ops","paper","risk"]`. Manual Refresh on `/ops`
  invalidates only these keys.
- Foundation defaults are unchanged: no retry, no focus/reconnect refetch, `staleTime: Infinity`,
  no polling, interval, SSE or WebSocket, manual Refresh only.
- Each of the five sections (Portfolio Authority, Recorded Runtime / Gateway, Simulated Paper Risk,
  Strategy Reservations, Recent Recorded Gateway Events) renders its own query state, so one
  unavailable source leaves the other panels usable.
- Required visible notices: `Budget reservations — not actual account exposure.`,
  `SIMULATED PAPER ONLY.`, `Recorded gateway state — not a fresh account, host or network check.`
- No new dependency; no page-level horizontal overflow at 375 px.
- Storybook/MSW: six deterministic OPS states (all sources, no active policy, capacity rejected with
  restriction, gateway unavailable, paper unavailable, recorded restricted-live), each with closed
  handlers and an `/api/ops/*` closed fallback.

## Deferred / forbidden (unchanged by this WP)

| Capability | Status |
|---|---|
| Full LIVE-ORCH episode drill-down | DEFER (would need execution-gateway source widening) |
| Fresh private account risk | FORBID (credentials/account boundary) |
| Current host currentness | DEFER (host/subprocess boundary) |
| Current network eligibility | DEFER (product-network boundary) |
| Generic EXEC-FEAS / Gate-C history | DEFER (no canonical registry) |
| Incident / alert lifecycle | DEFER (no canonical registry) |
| Streaming / currentness transport | DEFER to S10-CC-STREAM-01 |
| Operator commands / mutations | DEFER to S10-CC-CMD-01 |

## Authority

Read-only presentation only. StrategyLifecycle, paper and gateway mutations 0; credentials 0;
account reads 0; LIVE-ORCH, canary, reconcile or Gate-C actions 0; host-currentness or geoblock
requests 0; product network 0; new persistence 0; dependency/lock/workflow change 0; signatures and
orders 0; capital USD 0; live DISABLED.
