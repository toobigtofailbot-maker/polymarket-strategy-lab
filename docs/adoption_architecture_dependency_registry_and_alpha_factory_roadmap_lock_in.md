# Adoption Architecture, Dependency Registry, And Alpha-Factory Roadmap Lock-In

## 1. Purpose And Decision Status

WP154 is the canonical architecture decision and roadmap package for the
post-WP153 repository. It locks the intended finished system, the
alpha-factory lineage, the external-component evaluation registry, the
adoption order, the first research priorities, the deterministic-versus-AI
authority boundary, and the prerequisites for later implementation packages.

```text
Finished-system architecture:
MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL
WP154 package posture:
DECISION_AND_ROADMAP_ONLY
External dependencies installed or activated:
0
Paper-trading authority granted:
NO
Live-trading authority granted:
NO
WP155 implemented:
NO
```

This document is repo truth for architecture and adoption governance. It is
not an implementation plan with execution authority, a profitability claim,
or evidence that any listed dependency is approved.

## 2. Merge Lineage And Post-WP153 Baseline

The WP154 preflight was performed on 2026-07-26 after fetching `origin`.

| Lineage fact | Verified value |
|---|---|
| PR #153 | `MERGED` |
| PR #153 final implementation head | `53085b79aff84ab717af8be373dd70746ba20d11` |
| PR #153 merge commit | `471239088cc91a90bc0002f86cc429163027eeeb` |
| synchronized local `main` | `471239088cc91a90bc0002f86cc429163027eeeb` |
| `origin/main` | `471239088cc91a90bc0002f86cc429163027eeeb` |
| lineage relation | current `main` equals the PR #153 merge commit; it does not contain a later commit |

WP153 accepted exactly one synthetic, in-memory project dry run and one
research-memory receipt. It accepted zero real workflow measurement runs and
measured zero real workflow research-value metrics. Its 22 Wave 1 results are
synthetic harness outputs, not real alpha, strategy, paper-readiness, or
live-readiness evidence.

The dependency baseline remains `pyproject.toml` with no runtime dependencies
and a test-only `pytest>=8.0` optional dependency. There is no lock file. The
existing stdlib public Polymarket adapter remains the active public-data path.
The official Polymarket clients remain uninstalled as project dependencies.

## 3. Authority / Non-Authority Posture

WP154 crosses none of the Centralized Boundary Group Reference groups in
`docs/ai/codex/PROTECTED_PATHS.md`: `credentials/secrets`,
`authenticated clients`, `wallet/account behavior`, `order placement/cancel`,
`execution gateway`, `paper engine`, `scheduler/bot loop`, `runtime/daemon`,
`dashboard/deployment`, `dependency/lock changes`, `external code copying`,
or `generated artifacts`.

WP154 authorizes only documentation, stable status, repo-truth reconciliation,
deferred-item registration, and deterministic documentation tests. It does not
authorize:

- installation, activation, vendoring, forking, or copying of external code;
- dependency, lock, workflow, configuration, or runtime changes;
- provider, model, or Hermes runtime calls;
- credentials, wallets, accounts, keys, signing, or private endpoints;
- Polymarket product/runtime network calls or market-data collection;
- real workflow measurement, replay, backtest, paper, or live engines;
- strategies, signals, orders, fills, accounting, risk, reconciliation, or
  execution behavior;
- schedulers, workers, daemons, services, dashboards, or background tasks;
- capital deployment; or
- WP155 implementation.

Workflow Git/GitHub synchronization, primary-source architecture research, and
PR publication are workflow network use. They do not create product, runtime,
account, provider, or market network behavior.

## 4. Repo Capability Inventory

### 4.1 Classification Vocabulary

| State | Meaning |
|---|---|
| `IMPLEMENTED_AND_TESTED` | A bounded implementation surface and repository tests exist. |
| `IMPLEMENTED_LIMITED_OR_MANUAL` | An implementation exists but is local, manual, finite, or operationally incomplete. |
| `CONTRACT_OR_RUNBOOK_ONLY` | Documentation or a validation contract exists without the claimed runtime behavior. |
| `SYNTHETIC_TEST_ONLY` | Test/fixture evidence exists but is not operational or real-workflow evidence. |
| `ABSENT` | No relevant implementation exists. |
| `EXTERNALLY_PROPOSED` | An external component is listed for evaluation only. |
| `SEPARATELY_GATED` | A future capability requires a distinct approved work package. |

### 4.2 Post-WP153 Inventory

| Capability | Current state | Current repo evidence | Limitation / authority |
|---|---|---|---|
| public market metadata and bounded order-book observations | `IMPLEMENTED_LIMITED_OR_MANUAL` | stdlib public adapter, explicit finite polling/capture, snapshot tests | manual/explicit public GET only; not a point-in-time production dataset |
| normalized records, local snapshots, catalog, quality, and inspection replay | `IMPLEMENTED_AND_TESTED` | `src/data_layer/polymarket/` and tests | JSONL/local research design; replay is inspection, not fills |
| market research-priority scoring and review queue | `IMPLEMENTED_AND_TESTED` | scoring/features/queue modules and tests | research triage only; not expected return or a signal |
| resolution ambiguity labels and local research review | `IMPLEMENTED_AND_TESTED` | bounded data-layer validators and tests | no canonical relation graph or executable resolution-integrity engine |
| wallet profiling, copyability evaluation, reports, and candidate contracts | `IMPLEMENTED_AND_TESTED` | local/offline wallet modules and tests | fixtures/local inputs; profitability does not imply copyability; no auto-copy |
| Hermes/research-brain structured advisory chain | `IMPLEMENTED_LIMITED_OR_MANUAL` | validators, packets, manual export, runbooks, lineage tests | local/manual/advisory; no connected Hermes/provider/model runtime |
| assisted-research experiment | `SYNTHETIC_TEST_ONLY` | one-case precomputed local dry-run harness | zero adapter/provider calls and no performance claim |
| research-value measurement contract and Wave 1 harness | `IMPLEMENTED_AND_TESTED` | WP151 contract and WP152 deterministic package | 22 Wave 1 metrics only; 17 Wave 2 metrics blocked |
| project research-value evidence | `SYNTHETIC_TEST_ONLY` | WP153 synthetic in-memory receipt | zero real workflow runs and zero real metrics measured |
| strategy-validation handoff | `CONTRACT_OR_RUNBOOK_ONLY` | wallet paper-strategy candidate contract and validator | a candidate is not a deterministic strategy signal |
| point-in-time columnar research data foundation | `ABSENT` | no canonical PIT schema, partitions, correction semantics, or columnar store | Phase A and WP155 are separately gated |
| preregistration and experiment registry | `ABSENT` | no immutable experiment registry or OOS/cost evidence lineage | Phase D is separately gated |
| relation/resolution-integrity graph | `ABSENT` | no canonical graph schema or deterministic relation engine | Phase C is separately gated |
| replay/fill simulation | `ABSENT` | chronological inspection only | no queue, fill, latency, fee, cancellation, or settlement model |
| paper strategy input | `CONTRACT_OR_RUNBOOK_ONLY` | candidate-contract design only | no signal, expiry, sizing, or risk-tag input implementation |
| paper order lifecycle | `ABSENT` | documentation scaffold | no deterministic state machine or journal |
| portfolio/accounting/PnL | `ABSENT` | no implementation | no ledger, invariants, costs, positions, or settlement |
| deterministic risk/safe mode/kill switch | `ABSENT` | documentation scaffold | no implemented paper or live controls |
| reconciliation | `ABSENT` | execution-gateway scaffold only | no order/fill/position/cash recovery or invariant checks |
| observability and operations | `ABSENT` | monitoring/paper scaffolds | no telemetry naming, metrics, alerts, ownership, or runbooks |
| external adoption candidates | `EXTERNALLY_PROPOSED` | Section 9 registry | `LISTED != APPROVED`; all require separate decisions |
| paper core and restricted live | `SEPARATELY_GATED` | Phases G and J | no authority is granted by WP154 |

This inventory preserves the WP150 capability counts for its 20-stage local
workflow: 13 implemented/tested, four limited/manual, two contract/runbook
only, and one synthetic-only. WP152 and WP153 add a bounded measurement
harness and synthetic receipt; they do not close the paper-domain gaps.

## 5. Locked Finished-System Architecture

The intended end state is exactly:

```text
MEASURABLE_ALPHA_FACTORY_PLUS_DETERMINISTIC_TRADING_KERNEL
```

It has two authority-separated planes.

### 5.1 Research / Alpha-Factory Plane

Its purpose is to discover markets worth investigating, reject weak candidates
early, produce traceable hypotheses, run preregistered experiments, measure
out-of-sample and cost-adjusted evidence, retain negative and inconclusive
results, and produce paper-eligible proposals only after deterministic gates
pass.

Permitted AI/Hermes roles are market and source research, candidate-triage and
related-market suggestions, wallet-behavior research, hypothesis generation,
experiment-design suggestions, critique, red-team review, post-mortem and
failure analysis, regime-change suggestions, performance-improvement
proposals, summarization, and operator decision support.

Every AI/Hermes output is an untrusted advisory record. AI/Hermes cannot
execute, validate, sign, transition, schedule, approve, promote, or authorize.
It cannot hold credentials, create orders, approve risk, control a scheduler,
or grant paper/live status.

### 5.2 Deterministic Trading Kernel

The deterministic kernel has exclusive authority over:

- canonical data identity and point-in-time data validation;
- schema validation;
- experiment registration;
- lineage, versions, and hashes;
- candidate-state transitions;
- replay and fill simulation;
- fees, spread, slippage, latency, and cost calculations;
- paper state and order lifecycle;
- execution state and reconciliation;
- accounting and PnL;
- portfolio and risk limits;
- credentials and secrets;
- scheduler and runtime controls;
- incident controls;
- restricted-live eligibility; and
- live safety and kill switches.

No external framework, AI/Hermes output, dashboard, registry, model, or
orchestrator may weaken or bypass this boundary.

## 6. Locked Alpha-Factory Lineage

The canonical lineage is exact, ordered, and non-skippable:

1. `MARKET_OBSERVATION`
2. `RESEARCH_CANDIDATE`
3. `ALPHA_HYPOTHESIS`
4. `PREREGISTERED_EXPERIMENT`
5. `OUT_OF_SAMPLE_EVIDENCE`
6. `COST_ADJUSTED_RESULT`
7. `PAPER_ELIGIBLE_STRATEGY_PROPOSAL`
8. `PAPER_EVIDENCE`
9. `RESTRICTED_LIVE_ELIGIBILITY`

Every record has a stable ID, version, canonical hash, all direct predecessor
IDs, code version, data snapshot/version, parameters, creation provenance,
and deterministic validation status. Every transition requires deterministic
validation. Negative and inconclusive results are retained.

| Stage | Minimum stage-specific fields | Required evidence | Forbidden interpretation |
|---|---|---|---|
| `MARKET_OBSERVATION` | market/event/token/source IDs; event, observed, and ingestion times; source/resolution snapshots; payload hash; quality state | canonical point-in-time observation and validation receipt | an observation is not a candidate, hypothesis, signal, or order |
| `RESEARCH_CANDIDATE` | observation predecessors; triage reason; rejection criteria; ambiguity/quality flags; reviewer state | deterministic eligibility and provenance checks | research priority is not expected return |
| `ALPHA_HYPOTHESIS` | candidate predecessors; falsifiable claim; mechanism; cohort; horizon; target; failure condition | human-reviewed, versioned, testable statement | a hypothesis is not alpha or approval |
| `PREREGISTERED_EXPERIMENT` | hypothesis predecessors; locked metric, split, exclusions, thresholds, cost model, parameters, stop/failure rules | immutable preregistration receipt created before result evaluation | a changed-after-results plan is not preregistered |
| `OUT_OF_SAMPLE_EVIDENCE` | experiment predecessor; untouched dataset/snapshot IDs; split proof; results; uncertainty; failures | proof that evaluation data was unused for formation, tuning, or threshold selection | in-sample or tuned evidence is not out-of-sample |
| `COST_ADJUSTED_RESULT` | OOS predecessor; fees, spread, slippage, partial fills, latency, failed-cancel, and opportunity-cost assumptions | deterministic calculation receipt and sensitivity/failure evidence | a gross or assumption-free result is not alpha |
| `PAPER_ELIGIBLE_STRATEGY_PROPOSAL` | cost-result predecessor; deterministic input contract; invalidation/expiry; proposed risk tags; open gaps | all prior gates pass and proposal validation receipt | eligibility is not paper authorization |
| `PAPER_EVIDENCE` | eligible-proposal predecessor; approved paper-run IDs; replay/fill/order/accounting/risk/reconciliation receipts | separately authorized paper evidence over declared regimes and failure cases | paper evidence is not restricted-live eligibility |
| `RESTRICTED_LIVE_ELIGIBILITY` | paper-evidence predecessors; operational, incident, risk, reconciliation, and human-approval evidence | separately approved eligibility contract and deterministic gate receipt | eligibility is not live authorization |

An experiment must lock its hypothesis, target, metric, split, exclusion
rules, cost model, and failure criteria before result evaluation. Out-of-sample
data is data not used for hypothesis formation, threshold selection, or
tuning. No positive result may be labeled alpha without both out-of-sample and
cost-adjusted evidence.

## 7. Locked Adoption Sequence

Later phases may not leapfrog unresolved earlier prerequisites.

### PHASE A — POINT-IN-TIME DATA FOUNDATION

Lock canonical market/event/token/source identities, source and
resolution-rule snapshots, append-only observation envelopes, event/observed/
ingestion time, snapshot IDs and hashes, raw/normalized/quarantine separation,
and late/duplicate/correction semantics. Design Parquet/Arrow-compatible
research storage and a bounded DuckDB/Polars evaluation. No scheduler or
persistent production writer is authorized.

### PHASE B — OFFICIAL SDK COMPATIBILITY AND DATA-ADAPTER DECISION

Compare the current stdlib public-client surface with current official
Polymarket SDKs; classify archived clients; evaluate unified-SDK beta and early
0.x risk; evaluate V2 protocol/client requirements; and create a compatibility
and migration matrix. No authenticated trading or automatic migration.

### PHASE C — MARKET-RELATIONSHIP AND RESOLUTION-INTEGRITY GRAPH

Define event/market/token/source/resolution-rule nodes and mutually exclusive,
exhaustive, subset, implication, and temporal relations with deterministic
constraints. NetworkX is a prototype candidate only. A graph database remains
deferred until measured scale/query evidence requires it.

### PHASE D — PREREGISTRATION AND EXPERIMENT REGISTRY

Define immutable experiment specifications, dataset/snapshot lineage,
discovery/selection/OOS partitions, registered metrics and cost models, and
reproducible run receipts. MLflow may be evaluated only as run/artifact
metadata; repository-native deterministic contracts remain authoritative.

### PHASE E — FIRST FALSIFIABLE ALPHA PROGRAMS

Execute only in this priority order: resolution/source integrity and
related-market constraints; wallet intelligence and behavior persistence;
calibration/probability quality/market disagreement; maker research after
fill and queue-position evidence; and BTC/fast-market instrumentation without
a strategy claim before measured latency, fees, fills, and adverse selection.

### PHASE F — ISOLATED NAUTILUSTRADER SPIKE

Prerequisites are a point-in-time dataset, deterministic strategy-input
contract, explicit fill and cost assumptions, and a map of current repo
state/risk/accounting boundaries. The spike answers compatibility questions
only, does not replace the deterministic core by default, and implements no
live node, credentials, or Polymarket adapter.

### PHASE G — PAPER CORE

Only after foundational gaps close: replay/fill, strategy input, order
lifecycle, accounting, portfolio/risk, reconciliation, observability, and
operations. Each protected boundary requires separate authorization.

### PHASE H — OBSERVABILITY

Evaluate OpenTelemetry-compatible trace/metric naming, Prometheus metrics, and
Grafana dashboards/actionable alerts. Dashboards are observational only.
Alerts require owners and runbooks, and telemetry must not expose secrets or
private state.

### PHASE I — PREFECT RESEARCH-JOB ORCHESTRATION

Only deterministic, idempotent research jobs with bounded retries and
concurrency may be considered. Prefect receives no credential, risk, order,
execution, promotion, or paper/live scheduling authority.

### PHASE J — RESTRICTED LIVE

This phase is separately gated after paper evidence and operational readiness.
WP154 grants no restricted-live or live authorization.

## 8. Locked First Alpha-Research Priorities

### PRIORITY 1 — RESOLUTION_SOURCE_INTEGRITY_AND_RELATED_MARKET_CONSTRAINTS

This comes first because it has the strongest deterministic structure, reduces
ambiguous-resolution risk, supports early rejection/inconsistency detection,
and needs neither wallet credentials nor execution. Future evidence must
include normalized resolution rules, source hierarchy and snapshot lineage, a
relation graph, constraint violations, executable outcome/settlement logic
where possible, and false-positive review.

### PRIORITY 2 — WALLET_INTELLIGENCE_AND_BEHAVIOR_PERSISTENCE

Research slower repeatable behavior; separate realized from mark-to-market
performance; prevent look-ahead and survivorship bias; account for selection,
holding period, size, liquidity, and crowding. Copyability is a separate
hypothesis and is not inferred from wallet profitability. Automatic copy
trading is forbidden.

### PRIORITY 3 — CALIBRATION_AND_MARKET_DISAGREEMENT

Define cohorts and horizons, score probability quality with proper scoring
rules, and compare market-implied probability with independent evidence only
through preregistered tests. Disagreement alone is not edge.

### PRIORITY 4 — MAKER_RESEARCH_AFTER_FILL_EVIDENCE

Prerequisites are queue/fill, cancellation/stale-quote, maker/taker fee and
rebate, inventory/adverse-selection, partial-fill, and opportunity-cost
models. No maker strategy is paper-eligible before these exist.

### PRIORITY 5 — FAST_MARKET_INSTRUMENTATION_ONLY

Required measurements are external-reference timestamp quality, Polymarket
observation latency, book depth/spread, fee curve, acknowledgement, fill/
cancel latency, adverse selection, dropped/reordered messages, and regime
dependence. No BTC 5m/15m alpha claim may be based on anecdotal latency.

## 9. Dependency / Repository Adoption Registry

Registry semantics are binding:

```text
LISTED != APPROVED
EVALUATE != ADOPT
ADOPT != ACTIVATE
ACTIVATE != AUTHORIZE
PAPER_ELIGIBLE != PAPER_AUTHORIZED
RESTRICTED_LIVE_ELIGIBLE != LIVE_AUTHORIZED
```

All statuses below were observed from primary/official sources on 2026-07-26.
No row is an installation or activation decision. There is no activation in
WP154.

| candidate ID | project/repository | category / current official status | proposed use | prohibited use | adoption decision / phase | prerequisites | license | security/maintenance checks | benchmark/spike | exit/rejection criteria | separate WP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `POLYMARKET_PY_SDK` | `Polymarket/py-sdk` | official unified Python SDK; developer-tooling docs call it beta; repo is active; package 0.2.0 metadata says production/stable while README preserves 0.x breaking-minor caveat | public-data and compatibility evaluation | credentials, trading activation, automatic migration | `EVALUATE_OFFICIAL_UNIFIED_SDK`; Phase B | PIT/data adapter contract; compatibility matrix; pin/audit plan | MIT | reconcile beta/docs/package-status tension; releases, dependencies, signing/auth surface | compatibility spike required | reject if public-only isolation, determinism, or migration cost fails | YES |
| `POLYMARKET_PY_CLOB_V1` | `Polymarket/py-clob-client` | official repository archived; directs users to unified SDK; legacy V1 unsupported on production | historical compatibility reference only | new adoption, install, copy, runtime use | `DO_NOT_ADOPT_FOR_NEW_WORK`; Phase B | none for reference | MIT | preserve archive/migration evidence | NO | any proposal for new use is rejected | YES for any exception |
| `POLYMARKET_PY_CLOB_V2` | `Polymarket/py-clob-client-v2` | active official V2 client; official docs support V2; repo recommends unified SDK for new projects | compare with unified SDK and current stdlib adapter | activation, auth, orders | `COMPARE_WITH_UNIFIED_SDK_AND_CURRENT_REPO`; Phase B | V2 migration and public-method matrix; dependency audit | MIT | credentials/signing/order surface; release and transitive-dependency review | compatibility spike required | reject if redundant, unsafe to isolate, or migration target supersedes it | YES |
| `POLYMARKET_RUST_V2` | `Polymarket/rs-clob-client-v2` | active typed Rust SDK with CLOB, WebSocket, RTDS, Data, Gamma, and related features | future typed adapter/reference evaluation | Rust migration, credentials, execution implementation | `EVALUATE_FOR_FUTURE_TYPED_EXECUTION_ADAPTER_OR_REFERENCE`; Phase B/F | Rust toolchain/audit gate; adapter boundary map | MIT | cargo audit availability; feature/dependency/auth surface | isolated compatibility spike | reject if language/toolchain cost exceeds bounded value or boundary isolation fails | YES |
| `POLYMARKET_REAL_TIME_DATA_CLIENT` | `Polymarket/real-time-data-client` | active TypeScript WebSocket wrapper; includes public and authenticated topics | reference if a measured data gap requires it | adding TypeScript solely to use it; user/private streams | `REFERENCE_ONLY_UNLESS_REQUIRED_BY_DATA_GAP`; Phase B | documented streaming gap and language-cost decision | MIT | Node audit; auth/topic isolation; reconnect/order semantics | only if a gap is proved | reject without a unique measured gap | YES |
| `POLYMARKET_POLY_MARKET_MAKER` | `Polymarket/poly-market-maker` | official experimental automated market-maker framework; last source push observed 2024-07-05 | pattern reference only | inherited strategy, risk, credentials, or runtime | `REFERENCE_PATTERNS_ONLY`; Phase E | independent license/security/compatibility review before any reuse | MIT | maintenance recency; credential/order/risk assumptions | no adoption spike until maker prerequisites exist | reject copied assumptions or insufficient maintenance/security posture | YES |
| `PARQUET_ARROW` | Apache Parquet / Apache Arrow | active official columnar storage and in-memory interchange specifications | preferred research interchange candidate | persistence before schema/PIT/mutation rules | `PREFERRED_RESEARCH_INTERCHANGE_CANDIDATE`; Phase A | identity, schema, partition, correction, mutation rules | Apache-2.0 | format/version compatibility and schema-evolution review | schema/round-trip benchmark | reject if lineage or correction semantics cannot be preserved | YES |
| `DUCKDB` | `duckdb/duckdb` | active in-process analytical SQL engine; official docs query Parquet and support filter/projection pushdown | local queries over Parquet/Arrow | production database authority or network extension activation | `PREFERRED_LOCAL_ANALYTICS_QUERY_CANDIDATE`; Phase A | representative bounded local workload and deterministic pin | MIT | extension/supply-chain policy; version/reproducibility review | bounded benchmark required | reject if current stdlib/Polars path is simpler or results are not reproducible | YES |
| `POLARS` | `pola-rs/polars` | active columnar DataFrame engine; lazy API supports pushdown, schema checks, and streaming-oriented execution | lazy schema-aware transformations | unbounded migration or opaque nondeterministic transformations | `PREFERRED_TRANSFORMATION_CANDIDATE`; Phase A | representative repo workload and exact output contract | MIT | Python/Rust supply chain; release/pinning review | benchmark against current workloads | reject if complexity, memory, or determinism does not improve | YES |
| `MLFLOW` | `mlflow/mlflow` | active tracking platform for runs, parameters, metrics, datasets, and artifacts | experiment metadata/artifact compatibility evaluation | strategy approval, transition, promotion, deployment, or model authority | `EVALUATE_EXPERIMENT_METADATA_AND_ARTIFACT_TRACKING`; Phase D | repository-native preregistration and receipt contracts first | Apache-2.0 | storage/server/network/default-output and dependency review | isolated metadata spike | reject if it duplicates repo contracts, mutates authority, or adds unjustified service state | YES |
| `NETWORKX` | `networkx/networkx` | active Python graph-analysis library | local graph prototype | graph database inference or production authority | `EVALUATE_GRAPH_PROTOTYPE`; Phase C | canonical graph schema, deterministic constraints, scale/query cases | BSD-3-Clause | package/release audit and algorithm determinism review | prototype benchmark required | reject if stdlib structures suffice or scale/performance fails | YES |
| `NAUTILUSTRADER` | `nautechsystems/nautilus_trader` | active LGPL Rust-native event-driven trading engine spanning backtest/sandbox/live with adapter architecture; no Polymarket adapter is assumed | isolated compatibility comparison after prerequisites | wholesale adoption, live node, Polymarket adapter, credentials, execution authority | `ISOLATED_COMPATIBILITY_SPIKE_AFTER_DATA_AND_CONTRACT_PREREQUISITES`; Phase F | PIT data, strategy-input contract, fill/cost assumptions, boundary map | LGPL-3.0 | license/linking, Rust/Python supply chain, adapter and live-capable surface | isolated spike required | reject if minimal native paper core is safer/smaller or authority isolation fails | YES |
| `PREFECT` | `PrefectHQ/prefect` | active workflow orchestrator; deployments schedule/event-trigger flows and may use workers/work pools | later idempotent research-job orchestration | trading scheduler, credentials, execution, promotion, paper/live scheduling | `DEFER_UNTIL_IDEMPOTENT_RESEARCH_JOBS_EXIST`; Phase I | mature deterministic jobs, bounded retries/concurrency, output receipts | Apache-2.0 | server/cloud/network/storage, worker, retry, and dependency review | orchestration spike after prerequisites | reject if manual execution remains adequate or authority separation cannot be proved | YES |
| `OPENTELEMETRY` | `open-telemetry/opentelemetry-python` | active instrumentation implementation; Python traces/metrics stable and logs development | trace/metric naming standard candidate | secrets/private state or control authority | `PREFERRED_INSTRUMENTATION_STANDARD_CANDIDATE`; Phase H | event/operation naming and sensitive-data policy | Apache-2.0 | exporter/network/data-redaction and signal-stability review | bounded instrumentation spike | reject exporters or semantics that leak data or change behavior | YES |
| `PROMETHEUS_GRAFANA` | `prometheus/prometheus`; `grafana/grafana` | active metrics/alerting and visualization projects | later metrics, dashboards, and actionable alerts | accounting truth, risk/order authority, or dashboard-driven state transition | `PREFERRED_LATER_METRICS_DASHBOARD_ALERTING_CANDIDATES`; Phase H | metrics contract, owners, runbooks, retention/access policy | Apache-2.0 / AGPL-3.0-only | deployment, network, storage, access, licensing, plugin and alert review | operational observability spike | reject if operational burden/licensing exceeds value or alerts lack owners/actions | YES |

## 10. Primary Source Observation Register

Every technical claim above is grounded in a primary/official source. Repository
metadata was also inspected through GitHub on the observation date.

| Source / project | Official URL | Observed status and relevance | Adoption decision / uncertainty | Observation date |
|---|---|---|---|---|
| Polymarket unified Python SDK | https://github.com/Polymarket/py-sdk | official unified public/auth/trading/wallet SDK; active 0.2.0 line | evaluate only; developer-tooling beta label conflicts with package stable classifier and requires reconciliation | 2026-07-26 |
| Polymarket developer tooling | https://docs.polymarket.com/dev-tooling | unified Python/TypeScript SDKs described as beta and being hardened | beta/early-lifecycle risk remains | 2026-07-26 |
| legacy Python CLOB client | https://github.com/Polymarket/py-clob-client | archived; README directs migration to unified SDK | do not adopt for new work | 2026-07-26 |
| Python CLOB V2 client | https://github.com/Polymarket/py-clob-client-v2 | active V2 client; README recommends unified SDK for new projects | compare only; no activation | 2026-07-26 |
| Rust CLOB V2 client | https://github.com/Polymarket/rs-clob-client-v2 | typed CLOB plus WebSocket/RTDS/Data/Gamma feature surfaces | future reference/spike only | 2026-07-26 |
| CLOB V2 migration | https://docs.polymarket.com/v2-migration | V2 live; legacy V1 unsupported; migration requirements are material | Phase B must reconcile current repo and SDK paths | 2026-07-26 |
| Polymarket clients/SDKs | https://docs.polymarket.com/api-reference/clients-sdks | official TypeScript/Python/Rust CLOB V2 clients listed | authentication/order capability requires strict boundary | 2026-07-26 |
| Polymarket market data | https://docs.polymarket.com/market-data/overview | public market-data surfaces documented without auth | research-data relevance only; no endpoint probe in WP154 | 2026-07-26 |
| real-time data client | https://github.com/Polymarket/real-time-data-client | active TypeScript WebSocket wrapper | reference only unless a measured gap exists | 2026-07-26 |
| market maker | https://github.com/Polymarket/poly-market-maker | README calls framework experimental; live-capable assumptions | pattern reference only | 2026-07-26 |
| DuckDB | https://duckdb.org/docs/stable/data/parquet/overview | direct Parquet queries and filter/projection pushdown documented | preferred local query candidate; benchmark required | 2026-07-26 |
| Polars | https://docs.pola.rs/user-guide/lazy/optimizations/ | lazy predicate/projection pushdown documented | preferred transform candidate; benchmark required | 2026-07-26 |
| Apache Arrow | https://arrow.apache.org/docs/format/Columnar.html | language-agnostic in-memory columnar format | preferred interchange candidate; mutation rules remain repo-owned | 2026-07-26 |
| Apache Parquet | https://parquet.apache.org/docs/overview/motivation/ | compressed efficient columnar representation | preferred storage candidate after PIT contract | 2026-07-26 |
| MLflow Tracking | https://mlflow.org/docs/latest/tracking | runs record parameters, metrics, datasets, metadata, and artifacts | metadata evaluation only; never promotion authority | 2026-07-26 |
| NetworkX | https://github.com/networkx/networkx | active Python graph analysis; BSD-3-Clause stated in official repository | prototype candidate only | 2026-07-26 |
| NautilusTrader | https://nautilustrader.io/docs/latest/concepts/overview/ | common backtest/sandbox/live core and event-driven system concepts | isolated compatibility spike only; no Polymarket adapter assumed | 2026-07-26 |
| Prefect deployments | https://docs.prefect.io/v3/concepts/deployments | schedules/event triggers, workers, work pools, retries/concurrency | deferred research jobs only | 2026-07-26 |
| OpenTelemetry Python | https://opentelemetry.io/docs/languages/python/ | traces and metrics stable; logs development | instrumentation standard candidate; log maturity caveat | 2026-07-26 |
| Prometheus | https://prometheus.io/docs/introduction/overview/ | time-series metrics, rules, alerts, dashboard integrations | later observational metrics/alerts | 2026-07-26 |
| Grafana | https://github.com/grafana/grafana | dashboards, metrics/log visualization, and alerting; AGPL-3.0-only | later observational UI; licensing/deployment review required | 2026-07-26 |

Stars, marketing claims, and unverified profitability claims are not adoption
evidence. Source observation is not a security, license-compatibility,
benchmark, or adoption approval.

## 11. Tool-Adoption Decision Test

Every future adoption proposal must answer all of these before a dependency
work package can be approved:

1. What exact repo gap does the tool close?
2. Is that gap implemented, limited, contract-only, synthetic, or absent?
3. What is the smallest reusable component?
4. Can the outcome be achieved with less dependency and boundary risk?
5. Does the tool preserve deterministic replay and lineage?
6. Does it support point-in-time data and no-look-ahead semantics?
7. Can it be isolated behind an adapter?
8. Does it change credential, network, state, execution, or scheduling authority?
9. What data leaves the local environment?
10. What is its license and supply-chain posture?
11. What is its maintenance and release posture?
12. What benchmark or compatibility spike is required?
13. What are the rejection and rollback criteria?
14. What tests prove no authority expansion?
15. Which separate WP authorizes installation, implementation, and activation?

No dependency may be added without a completed decision record, required
security-tooling gates, and separate approval.

## 12. Roadmap Lock-In

All ranges are planning estimates, not commitments. They are measured from the
post-WP153 baseline and may change only through evidence-backed repo-truth
updates.

| Phase family | Objective | Predecessor gates | Expected WP family | Implementation authority | Forbidden scope | Exit evidence | Next decision |
|---|---|---|---|---|---|---|---|
| A. Data/adoption foundation — approximately 6–10 WPs after WP154 | PIT identities, schema, storage/transform benchmarks, SDK decision, graph/registry contracts | WP154 merged; each dependency separately approved | WP155 and follow-on data/adoption contracts/spikes | bounded per approved WP | production writer, scheduler, auth/trading | deterministic schemas, lineage, benchmarks, rejection records | first alpha-program readiness |
| B. First falsifiable alpha engines — approximately 12–20 additional WPs | execute priorities 1–5 with preregistered tests | Phases A–D complete enough; PIT/OOS/cost contracts | research engines and evidence packages | research-only per WP | paper/live promotion, anecdotal edge claims | retained OOS/cost-adjusted positive, negative, and inconclusive evidence | paper-eligibility contract |
| C. Paper/portfolio/risk/reconciliation/monitoring — approximately 20–35 additional WPs | deterministic paper kernel and operations | data, strategy-input, fill/cost, and authority contracts | Phase G/H contract then implementation sequence | protected paper boundaries only when explicitly approved | live state, credentials, external execution | replay/fill, lifecycle, ledger, risk, reconciliation, incident, observability evidence | restricted-live eligibility decision |
| D. Restricted-live v1 — approximately 35–55 WPs remaining | bounded separately authorized live mode | sufficient paper and operational evidence | Phase J gated packages | only explicit future authorization | broad/unrestricted capital or AI control | deterministic eligibility plus human live authorization | bounded production posture |
| E. Bounded production-style system — approximately 45–70 WPs remaining | reliable bounded end-to-end system | restricted-live evidence and sustained operations | later architecture/operations packages | explicit narrow WPs | authority expansion by inference | reproducible operations, incidents, reconciliation, risk, and audit evidence | future maturity decision |

Planning outlook:

- restricted-live v1: approximately 12–18 months;
- bounded production-style system: approximately 18–24 months.

Careful reuse of external components can reduce the range, but it cannot safely
collapse point-in-time, preregistration, OOS, cost, paper, risk,
reconciliation, operational, and human-authorization gates.

## 13. Explicit Deferrals

Every row is registered in `docs/deferred_items_log.md`. None authorizes early
implementation.

| Deferred item | Trigger | Prerequisite | Forbidden early interpretation | Separate approval |
|---|---|---|---|---|
| official Polymarket SDK compatibility/migration decision | current adapter gap or V2 migration need | Phase A identity/PIT requirements and current source refresh | SDK listing means migration/activation | YES |
| Parquet/Arrow PIT storage contract | WP155 approval | canonical identities, time, correction, schema rules | preferred format means writer/database authority | YES |
| DuckDB/Polars bounded benchmark | representative PIT dataset contract | exact workloads and deterministic outputs | preferred candidate means dependency adoption | YES |
| graph schema and NetworkX prototype | relation queries/constraints defined | canonical node/edge identity and false-positive review | prototype means graph database or signal | YES |
| preregistration/experiment registry contract | stable PIT lineage | immutable split/metric/cost/failure fields | registry means strategy approval | YES |
| MLflow compatibility spike | repo-native registry contract exists | authority map and local/storage isolation | tracking/model registry means promotion authority | YES |
| first resolution/source-integrity alpha program | Phase C/D contracts | normalized rules, snapshots, relation constraints | violation means tradable alpha | YES |
| wallet persistence/copyability research | PIT wallet observations approved | bias controls, realized/MTM split, liquidity/crowding | profitable wallet means copyable or auto-copy | YES |
| calibration program | resolved PIT cohorts | proper scores, horizons, OOS partitions | disagreement means edge | YES |
| fill/queue model | granular book/event evidence | timing, fees, cancellations, partial fills, opportunity cost | maker spread means realizable return | YES |
| NautilusTrader compatibility spike | Phase F prerequisites all pass | PIT data, strategy input, fill/cost assumptions, boundary map | spike means core replacement/live adapter | YES |
| observability naming and sensitive-data policy | deterministic paper events defined | owners, redaction, retention, runbooks | dashboard/alert means authority | YES |
| Prefect research-orchestration decision | mature idempotent research jobs | bounded retry/concurrency and receipts | orchestration means trading scheduler | YES |
| paper-core implementation sequence | foundational paper contracts complete | explicit paper boundary authorization | paper-eligible means paper-authorized | YES |
| restricted-live eligibility contract | sufficient paper and operational evidence | risk/reconciliation/incidents/human gate | eligibility means live authorization | YES |

## 14. Compatibility / Impossibility Check

| Requested outcome | Current compatibility | Impossibility / risk | WP154 decision |
|---|---|---|---|
| canonical architecture lock | compatible with Hermes and deterministic-core repo truth | none within docs/status/tests | lock the two-plane architecture |
| exact alpha lineage | compatible as governance | stages 4–9 lack implementations/evidence | lock lineage; do not claim capability |
| PIT columnar foundation | absent | cannot adopt storage/query tools safely before identity/time/correction contracts | Phase A and WP155 first |
| official SDK migration | current stdlib adapter exists; SDK landscape changed materially | beta/status tension, V1/V2 migration, auth/live-capable surfaces | Phase B compatibility WP |
| relation graph | ambiguity/research surfaces exist | no canonical graph schema or constraint engine | Phase C before prototype |
| MLflow | metadata functions are relevant | model/deployment surfaces could confuse authority and add service state | repo-native registry first |
| NautilusTrader | concepts overlap future paper core | no assumed Polymarket adapter; license, integration cost, and live-capable surface | isolated post-prerequisite spike only |
| Prefect | research jobs may later benefit | current jobs are not mature/idempotent; workers/schedules expand runtime boundary | defer to Phase I |
| paper core | foundational domains absent | implementation now would invent missing contracts and cross protected boundaries | Phase G, separately gated |
| restricted live | not compatible with current evidence | zero real workflow metrics and no paper/operational evidence | Phase J, no authority |

## 15. Requirement-To-Evidence Traceability

| Requirement | Stable evidence | Status |
|---|---|---|
| exact PR153 lineage and post-merge baseline | Section 2 and preflight metadata | SATISFIED |
| capability truth without synthetic/paper inflation | Sections 2 and 4 | SATISFIED |
| exact finished-system label and authority split | Section 5 | SATISFIED |
| exact non-skippable nine-stage lineage | Section 6 | SATISFIED |
| minimum fields/evidence/forbidden meaning per stage | Section 6 table | SATISFIED |
| exact adoption phases A–J | Section 7 | SATISFIED |
| exact alpha priorities 1–5 | Section 8 | SATISFIED |
| all 15 registry candidates and adoption semantics | Section 9 | SATISFIED |
| current primary-source observation metadata | Section 10 | SATISFIED |
| future adoption decision test | Section 11 | SATISFIED |
| planning roadmap and estimates | Section 12 | SATISFIED |
| 15 separately gated deferred items | Section 13 and deferred log | SATISFIED |
| compatibility/impossibility review | Section 14 | SATISFIED |
| no source/dependency/lock/workflow implementation | changed-file scope and focused tests | SATISFIED |
| no WP155 implementation | Sections 1 and 17 plus focused tests | SATISFIED |

## 16. Forbidden Interpretations

- Research value is not profitability.
- A synthetic receipt is not real workflow evidence.
- A market observation is not a research candidate.
- A candidate is not a hypothesis, signal, or order.
- A hypothesis is not proven alpha.
- In-sample evidence is not out-of-sample evidence.
- Gross evidence is not cost-adjusted evidence.
- `LISTED != APPROVED`.
- `EVALUATE != ADOPT`.
- `ADOPT != ACTIVATE`.
- `ACTIVATE != AUTHORIZE`.
- `PAPER_ELIGIBLE != PAPER_AUTHORIZED`.
- `RESTRICTED_LIVE_ELIGIBLE != LIVE_AUTHORIZED`.
- AI/Hermes advice is not validation, transition, scheduling, promotion, or
  execution authority.
- MLflow tracking or model registry is not strategy-promotion authority.
- A NetworkX prototype is not a graph-database decision.
- A NautilusTrader spike is not core replacement or a live adapter.
- Prefect research orchestration is not a trading scheduler.
- A dashboard or alert is not accounting, risk, or state authority.
- WP154 does not install, activate, or authorize any dependency.
- WP154 does not grant immediate paper or live readiness.
- WP154 does not implement WP155.

## 17. Next Separately Gated Package

Recommend, but do not implement:

```text
WP155 — POINT_IN_TIME_MARKET_RESEARCH_DATA_FOUNDATION_CONTRACT
```

Its expected scope is canonical observation and snapshot identities;
event/observed/ingestion time; source and resolution-rule snapshots;
raw/normalized/quarantine boundaries; duplicate/late/correction semantics;
immutable lineage and hashes; a Parquet/Arrow schema and partition decision;
and a bounded DuckDB/Polars benchmark plan.

WP155 must add no provider credentials, production writer, scheduler,
strategy, paper, live, order, execution, or capital behavior. It requires
separate approval.

## 18. Non-Authority Statement

WP154 is an architecture/repo-truth/docs/status/tests-only decision package.
It adds no source, dependency, lock, workflow, fixture, configuration, runtime,
provider/model/Hermes call, credential, product network, market-data
collection, persistent writer, scheduler, strategy, signal, order, fill,
paper/live, accounting, risk, reconciliation, execution, capital, copied
external source, or WP155 implementation.

```text
Dependency/lock changes: 0
Provider/model/Hermes runtime calls: 0
Product/runtime network behavior added: 0
Scheduler/background tasks added: 0
External source code copied: 0
WP155 implemented: NO
```
