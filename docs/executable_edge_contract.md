# WP172 Alpha + Executable Edge MVP Contract

## Authority and purpose

This contract governs the local/offline `src/research_runtime/executable_edge/`
research boundary. It converts an already-preregistered WP170 first-look OOS result and
hash-bound WP168 pmxt-v2 replay truth into a cost-aware assessment. It never places,
submits, cancels, signs, recommends, or allocates an order; never reads credentials or
account state; and has no paper, OMS, risk, execution, network, scheduler, Hermes, or live
authority. The protected Credential / Secret, Runtime / Bot-Loop / Scheduler, Paper,
Execution / OMS / Reconciliation, Risk / Capital, Live-Trading, Workflow, and Dependency
boundary groups in `docs/ai/codex/PROTECTED_PATHS.md` remain uncrossed.

`EXECUTABLE_EDGE_PASS` means only that WP173 may evaluate the evidence under the frozen
assumptions. It is not actual profit, trade readiness, execution readiness, capital
approval, or live readiness.

## Predecessor bindings

`build_research_decision_trace` validates both supplied WP170 records through the merged
WP170 record validator. The trace binds exact `experiment_id` and
`run_evidence_receipt_id`. Promotion requires a valid `OUT_OF_SAMPLE` receipt with
`oos_exposure_ordinal == 1`, `uncertainty_state == NONE`, both preregistered criteria true,
and `result_status == OOS_CRITERIA_MET_UNCOSTED`.

`build_market_truth_window` calls the merged WP168 `convert_pmxt_v2_events` boundary. It
retains the external-dataset ID, instrument ID, conversion-policy identity, ordered event
digests, and source `known_gap_policy` in a new content-addressed lineage ID. Receive time
is the execution-knowledge clock. `known_gap_policy` must be exactly `NONE` for continuity
to be complete. WP168 remains authoritative; WP172 never rewrites its records and never
uses Nautilus default fills as edge evidence.

## Immutable records

`ResearchDecisionEvent` contains market/asset IDs, integer decision time, closed BUY/SELL
and ENTER/EXIT research semantics, intended quantity, decision reference price, and the
estimated research value available at decision time. Events are strictly ordered by
`(decision_time_ns, market_id, asset_id)`. The trace has no account or order identifier.
Its ID is `decisiontrace:sha256:<digest>` over canonical JSON excluding the ID and the two
non-authority flags.

`ExecutionCostModel` freezes model version, execution mode, fee reference and possibly
unknown fee value, maker rebate plus its required evidence reference when nonzero,
latency, passive TTL, strictly increasing size grid, conservative queue multiplier,
markout horizon, minimum net edge, minimum fill ratio, minimum capacity, and maximum data
age. Decimal inputs are plain finite strings; scientific notation and binary floats are
not accepted. Unknown fees remain `None`. Maker rebate defaults to exact zero. Its ID is
`costmodel:sha256:<digest>` over every model assumption.

`ExecutableEdgeAssessment` binds the exact experiment, receipt, trace, cost model, and
market-truth lineage. It records gross research result, spread, depth/slippage, latency,
fee, adverse-selection markout, filled/intended quantities, fill ratio, net result, net
edge per filled unit, capacity result, assumptions, diagnostics, and non-authority flags.
Its ID is `edgeassessment:sha256:<digest>` over the entire canonical record excluding only
the ID and fixed non-authority flags.

## Fill and cost semantics

Arrival is `decision_time_ns + latency_ns`. Only market events with receive time at or
before arrival build the arrival book. A missing, crossed/one-sided, too-old, or gapped
book makes the result inconclusive. Future market events never affect the decision trace.

Aggressive BUY consumes ascending asks; aggressive SELL consumes descending bids. Visible
levels are consumed once and insufficient depth remains a partial or zero fill. Passive
orders require an exact visible price level at arrival. Queue ahead is visible size times
the frozen multiplier. Only subsequent opposite-aggressor trade flow at an eligible price,
between arrival and TTL, consumes that queue. A price touch or book update alone creates no
fill.

Exact `Decimal` arithmetic computes:

- gross research result from estimated value versus decision reference;
- spread from arrival best price versus arrival mid;
- latency from arrival mid versus decision reference;
- depth/slippage from volume-weighted fill versus arrival best;
- fee from filled notional and explicit basis points, net of an explicitly evidenced
  maker rebate only;
- adverse selection as only the unfavorable arrival-mid-to-markout-mid move.

Capacity is the largest frozen grid quantity meeting the minimum fill ratio. Aggregate
PASS requires fill ratio, capacity, and net edge to meet their frozen thresholds.

## Closed classification precedence

1. Invalid/tampered WP170 records or mismatched trace lineage reject the call.
2. A null/mismatched cost-model reference or non-authoritative/reused OOS receipt produces
   `DIAGNOSTIC_ONLY` and never WP173 eligibility.
3. Unknown fees, incomplete continuity, stale/unavailable required windows, or missing
   markout truth produces `EXECUTABLE_EDGE_INCONCLUSIVE`.
4. Known complete evidence that misses fill, capacity, or net-edge thresholds produces
   `EXECUTABLE_EDGE_FAIL`.
5. Only known complete evidence passing every gate produces `EXECUTABLE_EDGE_PASS` and
   `wp173_evaluation_eligible=true`.

Negative, partial, and inconclusive results are preserved. No status is an order,
recommendation, allocation, or authorization.

## Persistence

`serialize_assessment` emits canonical sorted-key compact UTF-8 JSON plus one newline and
revalidates the complete content-addressed record. `deserialize_assessment` requires byte
canonicality and recomputes identity. `write_assessment` accepts only an explicit `.json`
path whose parent already exists. Relative paths must be under ignored `local_data/`;
tests may use explicit absolute temporary paths. Creation is exclusive, identical bytes
are idempotent, and different existing bytes are never overwritten. Generated assessment
files are not repository artifacts.

## Compatibility and successor boundary

| Required behavior | Controlling mechanism | Compatible | Evidence |
|---|---|---:|---|
| First-look/cost binding | WP170 record validator and receipt literals | YES | WP170 integration tests |
| PIT event ordering and source hashes | WP168 pmxt-v2 conversion | YES | adapter and adjacent conversion tests |
| Conservative fill/cost/capacity | WP172 exact evaluator | YES | aggressive/passive negative matrix |
| Immutable local evidence | canonical serializer and exclusive writer | YES | persistence tests |
| No protected runtime authority | module imports, exact scope, boundary tests | YES | final diff/security/architecture gates |

WP173 — Serious Paper Trading System is next and separately gated. WP172 creates no
persistent account, portfolio accounting, OMS, risk controls, real execution, or live path
and cannot automatically promote itself into WP173.

## WP175E additive native market-truth path

WP175E / S10-DATA-03 adds a parallel `NativeMarketTruthWindow`; it does not
replace or reinterpret the PMXT path above. Its `source_capture_id` derives from
the durable WP169 WS session, and its bound `NativeContinuityAttestation` derives
from verified accepted-WS observation, session, gap, and initial full-book
evidence. The complete contract is
`docs/native_continuity_attested_market_truth_bridge_contract.md`.

Only `NONE` makes the existing PMXT window continuity-complete. PMXT
`AS_CAPTURED` remains incomplete. The native path has its own
`nativemarkettruthwindow:sha256:` identity and never writes a native capture ID
into `source_external_dataset_id`. It preserves receive time as the execution-
knowledge clock, uses integer/Decimal exactness, and cannot use quarantined,
unsupported, or non-WS public API records as order-book truth.

The evaluator accepts exactly the existing PMXT type or the additive native type
at a type-specific validation boundary. The classification precedence, fee,
fill, capacity, net-edge, first-look, and WP173 eligibility rules above are
unchanged. Native continuity merely makes it possible to satisfy the existing
continuity gate; it grants no automatic PASS. WP173 `run_wp172_replay` accepts the
same union with unchanged strategy binding, fill, accounting, risk,
reconciliation, and paper/live separation semantics.
