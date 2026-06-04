# Market Research Priority Scoring Layer

## 1. Status

- Package status: DOCS_ONLY_DESIGN_MERGED; SCHEMA_OUTPUT_CONTRACT_MERGED; CORE_SCORER_ON_BRANCH
- WP: WP44 (design merged); WP48 (schema/contract merged); WP49 (core scorer on branch)
- Runtime impact: NO_RUNTIME_CHANGE
- Tooling impact: NO_NEW_TOOLING
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Source impact: WP44 — NO_SRC_CHANGE; WP49 — LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_ADDED
- Validation impact: NO_VALIDATION_WEAKENING
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE
- Agent runtime impact: NO_AGENT_RUNTIME
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- LLM/provider impact: NO_LLM_PROVIDER_RUNTIME
- Trading impact: NO_TRADING_EXECUTION
- Scoring implementation: LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_ON_BRANCH
- Feature extraction implementation: NOT_STARTED
- CLI/export/report implementation: NOT_STARTED
- Advisory consumer integration: NOT_STARTED

WP44 added this design doc (docs-only). WP48 defined the binding output
contract. WP49 adds the local/offline/read-only core scorer at
`src/data_layer/market_research_priority_scoring.py` (stdlib-only, in-memory
output only, no network, no file writes, no CLI, no export, no feature
extraction, no advisory consumer integration, no runtime behavior).

The formal schema and output contract for this layer is defined in
`docs/market_research_priority_scoring_output_contract.md` (WP48, merged).
Any future implementation must follow that contract.

## 2. Purpose

This document defines a design for a future Market Research Priority Scoring
Layer — local/offline/read-only tooling that ranks Polymarket markets for
human research priority.

The layer is intended to help a human researcher decide which markets deserve
deeper manual study first. It does not issue trading signals, expected-return
estimates, position sizing, buy/sell recommendations, or execution instructions.

## 3. Existing Repo Foundation

The repo already provides local/offline/read-only market data infrastructure
that a future scoring layer may consume:

- `src/data_layer/polymarket/public_client.py` — public read-only data adapter
- `src/data_layer/polymarket/snapshot_persistence.py` — local JSONL snapshot persistence
- `src/data_layer/polymarket/snapshot_reader.py` — offline snapshot reader and replay
- `src/data_layer/polymarket/market_catalog.py` — in-memory market catalog
- `src/data_layer/polymarket/snapshot_quality.py` — snapshot quality gates and metrics
- `src/data_layer/polymarket/catalog_exports.py` — sanitized local catalog exports
- `src/data_layer/polymarket/local_reports.py` — local research report generation
- `docs/advisory_consumer_operator_workflow.md` — local advisory operator workflow
- `docs/advisory_prompt_runbook_package.md` — human-operated advisory prompt/runbook package

All existing sources are local/offline/read-only and carry no trading, execution,
credential, or strategy authority.

## 4. Design Boundary

The Market Research Priority Scoring Layer is:

- **Design-only in this WP.** No implementation is added.
- **Local/offline/read-only.** Any future implementation must read only
  repo-approved local snapshot, catalog, quality, and export artifacts.
- **Research triage only.** Its only authorized purpose is ranking markets for
  human researcher attention. It has no strategy, signal, or execution authority.
- **Human-review required.** No output may be used without human inspection and
  review of provenance, staleness, and component details.
- **Bounded above strategy.** It must never be promoted into a strategy module,
  risk engine, paper-trading engine, or execution path without a fully separate
  approved work package, safety review, and human authorization.

The layer is explicitly below the following protected boundaries:
strategy, signal, risk, paper trading, execution, dashboard, scheduler,
Hermes, LLM, credentials, runtime, database, and live trading.

## 5. Terminology

The following terms are used consistently in this design:

| Term | Definition |
|---|---|
| `research_priority_score` | The safe name for any composite ranking value produced by this layer. Means human research triage priority only. |
| Market Research Priority Scoring Layer | The overall design package for the future tooling. |
| Research triage | The process of ranking markets for human manual study priority. |
| Component feature | One measurable data completeness or quality attribute that contributes to the score. |
| Staleness flag | A label indicating that input data may be old and should be treated with reduced confidence. |
| Provenance flag | A label indicating which local artifact or snapshot capture session produced the input data. |
| Score laundering | The risk that a user treats `research_priority_score` as a trading signal despite advisory-only wording. |

The following terms are forbidden as output or design semantics in this layer:
trade signal, alpha score, expected return, buy recommendation, sell
recommendation, entry, exit, position sizing, leverage recommendation,
liquidation-sensitive parameter, execution confidence, profitable opportunity,
opportunity score. These terms may appear only in explicit "forbidden output"
or "non-goal" sections.

## 6. Research-Priority Score Definition

A `research_priority_score` is a composite ranking value that:

- Summarizes observable data completeness, snapshot freshness, quality-gate
  status, market activity, category coverage, token/outcome completeness,
  order-book availability, spread structure, visible local liquidity proxy,
  duplicate/conflict flags, and missing-data penalties for a given market.
- Ranks markets in a candidate set relative to each other for human research
  triage priority.
- Is always bounded (for example 0.0–1.0 or 0–100) and decomposed into
  interpretable components so a researcher can see which factors drove the rank.
- Must carry explicit staleness and provenance flags from the underlying snapshot
  and catalog artifacts.
- Must carry an explicit "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" label on any
  output surface.

A higher `research_priority_score` means: this market has more complete, fresh,
and quality-checked local data and therefore warrants earlier human research
attention. It does not mean the market is profitable, safe to trade, or
recommended for any position.

## 7. Explicit Non-Signal Statement

A `research_priority_score` is explicitly **not** any of the following:

- not a trading signal
- not expected return
- not investment advice
- not a buy, sell, entry, or exit recommendation
- not position sizing
- not a leverage recommendation
- not a strategy confidence score
- not an execution confidence score
- not an opportunity score
- not authorization for paper trading or live trading

Any output that implies a `research_priority_score` is a trading signal,
expected return, or execution instruction is forbidden.

## 8. Allowed Future Inputs

A future implementation may read only the following repo-approved local/offline
sources:

- Local JSONL market metadata snapshots under `local_data/polymarket/snapshots/`
- Local JSONL order-book snapshots under `local_data/polymarket/snapshots/`
- Local snapshot manifests under `local_data/polymarket/snapshots/`
- In-memory market catalog data produced by `src/data_layer/polymarket/market_catalog.py`
- Snapshot quality metrics produced by `src/data_layer/polymarket/snapshot_quality.py`
- Sanitized catalog exports produced by `src/data_layer/polymarket/catalog_exports.py`
- Local research reports produced by `src/data_layer/polymarket/local_reports.py`

All inputs must be local files. No live API calls, network calls, authenticated
requests, or real-time data feeds are allowed in any future implementation.

## 9. Forbidden Future Inputs

A future implementation must not read or consume:

- Live Polymarket API data (real-time or near-real-time)
- Authenticated account data or portfolio data
- Private keys, wallet keys, API credentials, or mnemonic material
- External databases, cloud storage, or remote services
- LLM outputs, Hermes decision outputs, or provider-generated signals
- Strategy module outputs or risk engine outputs
- Paper-trading engine results or execution gateway state
- Dashboard state or monitoring service data
- Scheduler state or bot-loop state
- Any data source not explicitly listed in Section 8

## 10. Allowed Future Outputs

A future implementation may produce only:

- A ranked list of markets with `research_priority_score` values and
  component feature breakdowns, explicitly labeled
  "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
- Staleness flags per market indicating snapshot age and provenance
- Component feature values (data completeness, freshness, quality gate status,
  active/inactive, category coverage, token/outcome completeness, order-book
  availability, spread structure, local liquidity proxy, duplicate/conflict
  flags, missing-data penalties, guard/provenance quality)
- Missing-data warnings for markets with insufficient snapshot or order-book
  coverage
- Local file output only (under git-ignored `local_data/` paths)
- Stdout text output for terminal review

## 11. Forbidden Future Outputs

A future implementation must not produce:

- Trade signals or buy/sell recommendations
- Expected-return estimates or profit probability
- Position sizing or leverage recommendations
- Entry or exit recommendations
- Execution instructions or order parameters
- Authorization for any trading activity (paper or live)
- Outputs labeled as `trade_score`, `alpha_score`, `opportunity_score`,
  `confidence_score`, or `expected_return`
- Any output that implies a market is "profitable" or "recommended"
- Outputs consumed directly by strategy modules, risk engines, paper-trading
  engines, or execution gateways without a separate approved work package

## 12. Proposed Feature Categories

The following categories are design guidance only. No source schema or
implementation is added in WP44.

### 12.1 Data Completeness
- Fraction of expected metadata fields populated for a market
- Fraction of expected token/outcome fields populated
- Missing-data penalty for key fields (category, resolution source, question text)

### 12.2 Snapshot Freshness
- Age of the most recent market metadata snapshot for this market
- Age of the most recent order-book snapshot for this market
- Staleness flag when snapshot age exceeds a configurable threshold

### 12.3 Quality-Gate Status
- Result of WP12 snapshot quality gates for this market's records
- Quality metric tier (acceptable / degraded / failing)
- Guard-enforced capture manifest provenance indicator

### 12.4 Market Active/Inactive Status
- Whether the market is currently marked as active in local snapshot data
- Whether the market has a known resolution date in local data
- Whether the resolution date is in the past (potentially closed/resolved)

### 12.5 Category Coverage
- Whether a recognized category is present in local metadata
- Whether a resolution source is identified
- Missing-category penalty for markets with no category metadata

### 12.6 Token/Outcome Completeness
- Number of outcomes present in local catalog data
- Whether all expected outcome tokens appear in local order-book data

### 12.7 Order-Book Availability
- Whether any local order-book snapshot exists for this market
- Number of order-book snapshots available locally
- Missing order-book penalty for markets with no local order-book data

### 12.8 Basic Spread / Bid-Ask Structure
- Basic spread or bid-ask gap observable from local order-book data where available
- This feature must be capped or separated so that a tight spread does not
  dominate the `research_priority_score` and create false attractiveness for
  thin markets

### 12.9 Visible Local Liquidity Proxy
- A simple depth proxy (e.g., number of non-trivial bid/ask levels) from local
  order-book data where available
- This feature must be capped or separated to prevent a single liquidity signal
  from creating misleadingly high scores for otherwise incomplete markets

### 12.10 Duplicate/Conflict Flags
- Whether WP13 deduplication found duplicate or conflicting snapshot records
  for this market
- Penalty for markets with unresolved conflicts

### 12.11 Missing Category/Resolution Penalties
- Weighted penalty applied when key metadata is absent
- Prevents markets from scoring highly solely due to order-book data when
  metadata is incomplete

### 12.12 Guard/Provenance Quality
- Whether the snapshot capture session used WP16/WP18 guard enforcement
- Whether the manifest provenance is verified

### 12.13 Deferred-Item Caveats
- Indicator that rate-limit policy is unconfirmed (WP8-D002, WP16-D002)
- Warning label when snapshot freshness cannot be validated due to known
  deferred items

## 13. Proposed Score Output Concepts

The following output concepts are design guidance only. No implementation,
schema, CLI, or report writer is added in WP44.

- `research_priority_score`: float in [0.0, 1.0] (or equivalent bounded range)
- `score_components`: dict of component feature name to component value
- `staleness_flag`: bool — True if any input snapshot exceeds freshness threshold
- `provenance_label`: str — identifies the snapshot manifest(s) used
- `missing_data_warning`: bool — True if order-book or metadata coverage is insufficient
- `advisory_label`: str — always "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
- `score_rank`: int — rank within the candidate market set for this run
- `component_explanation`: str — human-readable summary of which features drove
  the rank

These concepts must not be treated as a source schema. Any future implementation
must define and test the actual schema in a separate approved work package before
implementation.

## 14. Staleness and Provenance Requirements

Any future implementation must enforce:

- Every `research_priority_score` output carries a `staleness_flag` indicating
  whether any input snapshot is older than a configurable threshold.
- Every output carries a `provenance_label` identifying which local snapshot
  manifest(s) produced the input data.
- Outputs with stale data must display an explicit warning to the human reviewer.
- The score for a market with no recent snapshots must be penalized, not
  defaulted to a neutral or high value.
- Researchers must be instructed to re-capture snapshots before acting on any
  output with a staleness flag.

## 15. Score Laundering Risk and Mitigations

### 15.1 Definition

**Score laundering** is the risk that a user treats `research_priority_score`
output as a trading signal, expected return, or buy/sell recommendation despite
explicit advisory-only wording. This risk exists because any numerical ranking
may be misread as investment guidance by users accustomed to signal-based tools.

### 15.2 Mitigations

The following mitigations must be enforced by any future implementation:

1. **Safe naming.** Use `research_priority_score` in all outputs. Forbidden
   names: `trade_score`, `alpha_score`, `opportunity_score`, `confidence_score`,
   `expected_return`. Using a forbidden name in any output is a failing check.

2. **Mandatory advisory labels.** Every output surface must display
   "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" or equivalent. The label must not be
   optional or user-suppressible.

3. **Staleness and provenance flags.** Every output must carry explicit staleness
   and provenance flags. Stale outputs must display a warning.

4. **Cap or separate order-book/liquidity-derived components.** Spread and
   liquidity-proxy features must be capped so that a tight spread or deep book
   cannot alone make a thin or incomplete market appear falsely attractive.

5. **Missing-data penalties.** Markets with missing metadata, missing outcomes,
   or missing order-book snapshots must receive explicit penalties, not neutral or
   high scores.

6. **Output warnings for insufficient coverage.** Any output for a market with
   insufficient snapshot or order-book coverage must carry a
   `missing_data_warning` flag visible to the researcher.

7. **Forbid position sizing, leverage, entry/exit, order, and execution language**
   in all outputs, labels, comments, and documentation.

8. **Component decomposition.** Every `research_priority_score` must be
   accompanied by its component feature breakdown so the researcher can verify
   what drove the rank.

## 16. Human-Review Requirements

Any future output from the Market Research Priority Scoring Layer:

- Must be labeled "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" on every output surface.
- Must not be consumed programmatically by a strategy module, risk engine,
  paper-trading engine, or execution gateway without a separate approved WP.
- Must be reviewed by a human researcher who verifies staleness flags,
  provenance labels, and component breakdowns before acting on the ranking.
- Must be accompanied by a reminder that the score reflects data completeness
  and snapshot freshness, not market profitability or trading opportunity.
- Must not be forwarded to any LLM or Hermes runtime without explicit human
  review and a separate approved WP defining the forwarding scope.

## 17. Future Implementation Gates

Any future work package proposing to implement the Market Research Priority
Scoring Layer must satisfy all of the following before implementation begins:

1. WP48 defines the formal schema and output contract for `research_priority_score`
   and all component features. See `docs/market_research_priority_scoring_output_contract.md`.
2. The schema WP (WP48) is reviewed and merged.
3. The implementation WP is explicitly approved by the user after WP48 merge.
4. The implementation is local/offline/read-only and does not add runtime
   dependencies, network calls, authenticated requests, or external data sources.
5. The implementation adds tests enforcing advisory-only labels, forbidden-name
   checks, missing-data penalties, staleness flags, cap enforcement on
   order-book/liquidity features, and forbidden-output checks.
6. No implementation reads LLM outputs, Hermes outputs, or strategy signals.
7. No implementation writes to any path outside git-ignored `local_data/`.
8. No implementation is wired into any strategy module, scheduler, bot loop,
   dashboard, paper-trading engine, or execution gateway.

Implementation must not begin until all gates above are satisfied.

## 18. Relationship to Strategy Modules

The Market Research Priority Scoring Layer is strictly below strategy modules in
the architecture. It must not:

- Produce outputs that strategy modules consume directly.
- Be classified as a strategy module in `docs/strategy_module_registry.md`.
- Receive or emit trade signals.
- Be promoted to a strategy confidence score without an explicit authorized WP.

The `docs/strategy_module_registry.md` currently lists no started modules.
This layer is not a strategy module and must not be registered as one.

## 19. Relationship to Advisory Consumer / Reports

The Market Research Priority Scoring Layer is downstream of the existing advisory
infrastructure but must not be integrated without separate human review:

- It may consume sanitized local reports and exports produced by the existing
  advisory infrastructure.
- It must not receive or emit LLM/Hermes outputs.
- Any output it produces that is intended for advisory consumer input must be
  approved through a separate WP defining that handoff contract.
- The local advisory consumer (`tools/advisory/local_advisory_consumer.py`)
  and advisory prompt/runbook package (`docs/advisory_prompt_runbook_package.md`)
  are not modified by this WP.

## 20. Deferred Items Created or Referenced

| ID | Item | Status | Priority |
|---|---|---|---|
| WP44-D001 | Market Research Priority Scoring implementation not started | OPEN | P3 |
| WP44-D002 | Score laundering mitigation not enforced by implementation | OPEN | P3 |

See `docs/deferred_items_log.md` for full entries.

## 21. Protected-Boundary Reaffirmation

WP44 reaffirms all existing protected boundaries unchanged:

- Live trading: DISABLED — no change.
- Execution: NOT_STARTED — no change.
- Credentials: NOT_USED — no change.
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY — no change.
- Agent runtime: NOT_STARTED — no change.
- Agent execution authority: FORBIDDEN — no change.
- Scheduler: NOT_STARTED — no change.
- Bot loop: NOT_STARTED — no change.
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP — no change.
- Official client runtime dependency: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME — no change.
- Strategy modules: no module is started, no module is authorized.
- Paper trading: NOT_STARTED — no change.
- Database: NOT_STARTED — no change.
- Dashboard: NOT_STARTED — no change.
- LLM/provider runtime: NO_LLM_PROVIDER_RUNTIME — no change.

## 22. Non-Goals

The following are explicit non-goals of this design and any future
implementation:

- Generating a trade signal, alpha score, or expected return.
- Providing a buy, sell, entry, or exit recommendation.
- Estimating position sizing or leverage.
- Authorizing paper trading or live trading for any market.
- Replacing human judgment about market research priority.
- Integrating Hermes, LLM providers, or agent runtimes.
- Building a dashboard, scheduler, bot loop, or database.
- Providing real-time or near-real-time market data access.
- Consuming authenticated or account-level data.
- Producing outputs consumed directly by strategy modules or risk engines.
- Implementing scoring logic without WP48 (schema/output contract) merged and
  without explicit user approval of an implementation WP.
