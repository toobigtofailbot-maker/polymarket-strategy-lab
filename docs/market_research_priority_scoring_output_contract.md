# Market Research Priority Scoring Output Contract

## A. Status

- Package status: DOCS_ONLY_SCHEMA_OUTPUT_CONTRACT_MERGED; CORE_SCORER_MERGED; FEATURE_EXTRACTION_MERGED; DATA_INTEGRITY_HARDENING_MERGED; RESOLUTION_AMBIGUITY_TAXONOMY_ON_BRANCH
- WP: WP48 (schema/contract merged); WP49 (core scorer merged); WP51 (feature extraction foundation merged); WP52 (long-term roadmap merged); WP53 (data-integrity hardening merged); WP54 (governance hardening merged); WP55 (resolution ambiguity taxonomy/manual-label workflow on branch)
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: WP48 — NO_SRC_CHANGE; WP49 — LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_ADDED; WP51 — LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_ADDED; WP53 — LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_HARDENED; WP55 — NO_SRC_CHANGE
- Tooling impact: NO_NEW_TOOLING
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- Agent runtime impact: NO_AGENT_RUNTIME
- Scoring implementation: LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_MERGED
- Feature extraction implementation: LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED; DATA_INTEGRITY_HARDENING_MERGED; RESOLUTION_AMBIGUITY_TAXONOMY_DOCS_ONLY_ON_BRANCH
- CLI/export/report implementation: NOT_STARTED
- Advisory consumer integration: NOT_STARTED

This document is the binding schema and output contract. WP48 defined the
contract (docs-only). WP49 adds the local/offline/read-only core scorer at
src/data_layer/market_research_priority_scoring.py (stdlib-only, in-memory
output only, no network, no file writes, no CLI, no export, no report writer,
no feature extraction, no advisory consumer integration, no runtime behavior).

## B. Purpose

This document defines the formal schema and output contract for the future
local/offline/read-only Market Research Priority Scoring Layer designed in WP44.

The contract is binding for any future implementation work package. No scoring
logic is implemented in WP48.

The design document for this layer is at
`docs/market_research_priority_scoring_layer.md`.

Any future implementation work package must:
- satisfy all gates in this contract;
- be explicitly approved by the user after this schema WP is merged;
- add tests that enforce all required fields, labels, bounds, and penalties
  defined here.

## C. Non-Signal Boundary

**`research_priority_score` is not a trading signal.**

It is explicitly **not** any of the following:

- not a trading signal
- not expected return
- not investment advice
- not position sizing
- not execution confidence
- not opportunity scoring
- not a recommendation to buy, sell, enter, exit, size, leverage, trade,
  paper trade, or live trade

Any output that implies `research_priority_score` is a trading signal,
expected return, or execution instruction is forbidden.

## D. Required Top-Level Output Object

Any future implementation must produce a top-level output object named:

```
market_research_priority_scoring_output
```

Required top-level fields:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Contract schema version, e.g. `"1.0"` |
| `generated_at_utc` | string | ISO-8601 UTC timestamp when output was generated |
| `run_id` | string | Unique identifier for this scoring run |
| `source_artifacts` | object | Provenance of all input artifacts used |
| `advisory_label` | string | Must be exactly `"ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"` |
| `human_review_required` | boolean | Must be `true` |
| `scope` | object | Description of the market candidate set scored |
| `markets` | array | List of market objects (see Section E) |
| `contract_warnings` | array | Top-level warnings (staleness, provenance gaps, etc.) |
| `forbidden_use_notice` | string | Explicit statement of forbidden uses |

`forbidden_use_notice` must state: this output is not a trading signal, not
expected return, not position sizing, and not an execution instruction.

## E. Required Market Object

Each object in the `markets` array must include all of the following fields:

| Field | Type | Description |
|---|---|---|
| `market_id` | string | Unique market identifier from local snapshot |
| `question` | string | Market question text from local snapshot |
| `category` | string or null | Market category if available |
| `active_status` | boolean or null | Whether market is active in local data |
| `research_priority_score` | number | Bounded [0.0, 1.0]; see Section F |
| `score_rank` | integer | Rank within this scoring run (1 = highest priority) |
| `score_components` | object | Component breakdown; see Section G |
| `staleness` | object | Staleness metadata; see Section H |
| `provenance` | object | Provenance metadata; see Section I |
| `missing_data` | object | Missing-data flags; see Section J |
| `quality_gates` | object | Quality gate status; see Section K |
| `component_explanation` | string | Human-readable summary of what drove this rank |
| `advisory_label` | string | Must be exactly `"ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"` |
| `forbidden_use_notice` | string | Explicit statement of forbidden uses per market |

## F. Required Score Field

`research_priority_score` is defined as:

- **Type:** number (float)
- **Bounded range:** [0.0, 1.0] inclusive
- **Higher means:** higher priority for human research triage only — this
  market has more complete, fresh, and quality-checked local data and therefore
  warrants earlier human researcher attention
- **Must not indicate:** profitability, trade attractiveness, expected return,
  or investment suitability
- **Forbidden names:** `alpha`, `opportunity`, `edge`, `expected_return`,
  `signal`, `trade_score`, `confidence_score`

A higher score does **not** mean the market is profitable, safe to trade, or
recommended for any position. It means only that the available local data
is more complete and fresh.

## G. Required Score Components

`score_components` is an object. Each component represents one measurable
data-completeness or quality attribute. The following components are required
by this contract. Future implementation must define all of them:

### data_completeness
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** fraction of expected metadata fields populated
- **Forbidden interpretation:** not a measure of market quality or attractiveness
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** fraction of key metadata fields present (category,
  question text, resolution source, outcome tokens)

### snapshot_freshness
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** recency of most recent local snapshot for this market
- **Forbidden interpretation:** not a measure of market liquidity or price accuracy
- **Direction:** higher is better (more recent)
- **Capped:** yes — at 1.0; stale snapshots must score 0.0 or very low
- **Required explanation:** age of most recent metadata snapshot relative to
  freshness threshold

### quality_gate_status
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** result of WP12 snapshot quality gates (acceptable = 1.0,
  degraded = 0.5, failing = 0.0)
- **Forbidden interpretation:** not a measure of market trustworthiness for trading
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** quality gate tier from last captured snapshot

### market_activity_metadata
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** whether market is active and has a non-past resolution
  date in local data
- **Forbidden interpretation:** not a signal of market opportunity
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** active flag and resolution date availability in
  local snapshot

### category_coverage
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** whether a recognized category and resolution source
  are present in local metadata
- **Forbidden interpretation:** not a signal of research importance by category
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** category and resolution source presence in local data

### token_outcome_completeness
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** fraction of expected outcome tokens present in local
  catalog data
- **Forbidden interpretation:** not a signal of token value or tradability
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** fraction of outcome tokens present in local catalog

### order_book_availability
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** whether any local order-book snapshot exists for this market
- **Forbidden interpretation:** not a signal of market liquidity for trading purposes
- **Direction:** higher is better
- **Capped:** yes — at 1.0
- **Required explanation:** whether local order-book snapshot data exists

### spread_structure_observed
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** whether a basic bid-ask structure is observable in local
  order-book data
- **Forbidden interpretation:** not a measure of spread attractiveness for trading;
  must be capped so spread cannot alone dominate the composite score
- **Direction:** higher is better (structure observable)
- **Capped:** yes — must be capped or weighted to prevent tight-spread markets
  from appearing falsely attractive
- **Required explanation:** whether spread structure is observable in local data;
  note that this component is deliberately capped to prevent score laundering

### visible_local_liquidity_proxy
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** a simple proxy for observable local data depth (e.g.
  number of non-trivial bid/ask levels) from local order-book data
- **Forbidden interpretation:** not a measure of actual market liquidity for
  trading; must be capped to prevent thin markets from appearing falsely
  attractive due to incidental order-book depth
- **Direction:** higher is better (more data observable)
- **Capped:** yes — must be capped or separated; a single liquidity signal
  must not create misleadingly high scores for otherwise incomplete markets
- **Required explanation:** local data depth proxy; note deliberately capped

### duplicate_conflict_penalty
- **Type:** number
- **Bounded range:** [-1.0, 0.0] (penalty-only)
- **Allowed meaning:** penalty when WP13 deduplication found duplicate or
  conflicting snapshot records for this market
- **Forbidden interpretation:** not a signal of market data quality for trading
- **Direction:** penalty-only (0.0 means no penalty)
- **Capped:** yes — at 0.0 (cannot be positive)
- **Required explanation:** whether deduplication conflicts exist for this market

### missing_data_penalty
- **Type:** number
- **Bounded range:** [-1.0, 0.0] (penalty-only)
- **Allowed meaning:** penalty for missing metadata fields, missing outcome
  tokens, or missing order-book snapshots
- **Forbidden interpretation:** not a signal of research priority
- **Direction:** penalty-only (0.0 means no missing data)
- **Capped:** yes — at 0.0 (cannot be positive)
- **Required explanation:** which data fields are missing and their penalty weight

### guard_provenance_quality
- **Type:** number
- **Bounded range:** [0.0, 1.0]
- **Allowed meaning:** whether the snapshot capture session used WP16/WP18
  guard enforcement and whether manifest provenance is verified
- **Forbidden interpretation:** not a signal of data correctness for trading
- **Direction:** higher is better (guard-enforced capture)
- **Capped:** yes — at 1.0
- **Required explanation:** whether guard-enforced capture provenance is
  confirmed for this market's snapshots

### deferred_item_caveat_penalty
- **Type:** number
- **Bounded range:** [-1.0, 0.0] (penalty-only)
- **Allowed meaning:** penalty or warning flag when known deferred items
  (e.g. WP8-D002 unconfirmed rate limits, WP16-D002 unconfirmed venue
  rate-limit policy) affect confidence in the scoring inputs
- **Forbidden interpretation:** not a signal of market quality
- **Direction:** penalty-only (0.0 means no applicable deferred item)
- **Capped:** yes — at 0.0 (cannot be positive)
- **Required explanation:** which deferred items apply and their impact

## H. Staleness Contract

`staleness` is a required object in every market record.

Required fields:

| Field | Type | Description |
|---|---|---|
| `staleness_flag` | boolean | True if any input snapshot exceeds freshness threshold |
| `snapshot_age_seconds` | number or null | Age of most recent snapshot in seconds |
| `freshness_threshold_seconds` | number | Configured threshold for stale detection |
| `stale_inputs` | array | List of stale input artifact IDs |
| `staleness_warning` | string or null | Human-readable staleness message if stale |
| `requires_recapture_before_use` | boolean | True if data is stale and should be recaptured |

**Staleness rules:**

- Stale data must penalize `snapshot_freshness` to near 0.0 or set the
  market output to a degraded status. Stale data must **never** default
  to a high or neutral score.
- When `staleness_flag` is true, `staleness_warning` must contain a
  non-empty message instructing the researcher to recapture snapshots.
- When `staleness_flag` is true, `requires_recapture_before_use` must be true.
- A market with no recent snapshots must receive a low `snapshot_freshness`
  score, not a neutral or default score.

## I. Provenance Contract

`provenance` is a required object in every market record.

Required fields:

| Field | Type | Description |
|---|---|---|
| `snapshot_manifest_ids` | array | List of snapshot manifest IDs used |
| `source_export_paths` | array | List of local snapshot/export file paths used |
| `capture_session_ids` | array | Capture session identifiers |
| `guard_policy_version` | string or null | WP16/WP18 guard policy version if guard-enforced |
| `quality_report_ids` | array | Quality report identifiers used |
| `input_artifact_types` | array | Types of input artifacts (snapshot, catalog, export, etc.) |

**Provenance rules:**

- Every output must identify source artifacts. Missing or empty
  `snapshot_manifest_ids` and `source_export_paths` must force a
  warning or degraded status.
- Missing provenance must never silently pass through as a valid output.
- If no provenance can be established, the market object must carry
  a `missing_data_warning` and a reduced `guard_provenance_quality` score.

## J. Missing-Data Contract

`missing_data` is a required object in every market record.

Required fields:

| Field | Type | Description |
|---|---|---|
| `missing_data_warning` | boolean | True if order-book or metadata coverage is insufficient |
| `missing_metadata_fields` | array | List of missing expected metadata field names |
| `missing_order_book` | boolean | True if no local order-book snapshot exists |
| `missing_outcome_tokens` | boolean | True if outcome tokens are absent or incomplete |
| `missing_category` | boolean | True if category metadata is absent |
| `missing_resolution_source` | boolean | True if resolution source is absent |
| `insufficient_coverage_reason` | string or null | Reason description if coverage is insufficient |

**Missing-data rules:**

- Missing data must penalize `research_priority_score` via `missing_data_penalty`.
- Missing data must never be hidden or silently absorbed into a high score.
- If `missing_data_warning` is true, `missing_data_penalty` must be non-zero.

## K. Quality Gates Contract

`quality_gates` is a required object in every market record.

Required fields:

| Field | Type | Description |
|---|---|---|
| `quality_status` | string | One of: ACCEPTABLE, DEGRADED, FAILING, UNKNOWN |
| `quality_warnings` | array | List of quality warning messages |
| `dedupe_conflict_flag` | boolean | True if deduplication found conflicts |
| `guard_enforced_capture` | boolean | True if snapshot was captured with guard enforcement |
| `deferred_item_caveats` | array | List of applicable deferred item IDs |

## L. Advisory Labels and Forbidden-Use Notice

Every top-level output object and every market object must include:

- `advisory_label`: must be exactly the string `"ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"`
- `human_review_required`: must be `true`
- `forbidden_use_notice`: must contain clear text stating that this output is
  not a trading signal, not expected return, not position sizing, and not an
  execution instruction

The advisory label must not be optional, user-suppressible, or configurable
to any other value.

## M. Forbidden Fields

The following fields are **forbidden** in any output from a future
implementation. A future implementation must have tests that assert these
fields are absent from every output object:

- `trade_signal`
- `alpha_score`
- `opportunity_score`
- `expected_return`
- `profit_probability`
- `buy_recommendation`
- `sell_recommendation`
- `entry`
- `exit`
- `position_size`
- `leverage`
- `execution_confidence`
- `order_params`
- `strategy_signal`
- `paper_trade_authorization`
- `live_trade_authorization`

## N. Forbidden Output Wording

Output text, labels, comments, and documentation in any future implementation
must not use the following terms in contexts that imply trading actions:

- buy
- sell
- trade
- enter
- exit
- position
- size
- leverage
- execute
- profitable
- opportunity
- alpha
- edge
- expected return

These words may appear **only** in explicit forbidden-use sections, non-signal
boundary statements, or documentation that describes what this layer does
**not** do. They must not appear in score labels, explanations, or any field
name that implies research-triage output is a trading recommendation.

## O. Safe Example Output

The following is a safe example of a compliant output structure. This is
documentation only — no JSON writer or schema file is created in WP48.

```json
{
  "schema_version": "1.0",
  "generated_at_utc": "2026-06-03T12:00:00Z",
  "run_id": "run-20260603-001",
  "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
  "human_review_required": true,
  "forbidden_use_notice": "This output is not a trading signal, not expected return, not position sizing, and not an execution instruction. It is for human research triage only.",
  "source_artifacts": {
    "snapshot_manifest_ids": ["manifest-20260603-001"],
    "capture_session_ids": ["session-20260603-001"]
  },
  "scope": {
    "candidate_market_count": 1,
    "scoring_run_type": "local_offline_research_triage"
  },
  "contract_warnings": [],
  "markets": [
    {
      "market_id": "0xabc123",
      "question": "Will event X occur before date Y?",
      "category": "politics",
      "active_status": true,
      "research_priority_score": 0.72,
      "score_rank": 1,
      "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
      "human_review_required": true,
      "forbidden_use_notice": "This score is not a trading signal, not expected return, not position sizing, and not an execution instruction.",
      "score_components": {
        "data_completeness": 0.9,
        "snapshot_freshness": 0.8,
        "quality_gate_status": 1.0,
        "market_activity_metadata": 1.0,
        "category_coverage": 1.0,
        "token_outcome_completeness": 0.75,
        "order_book_availability": 1.0,
        "spread_structure_observed": 0.5,
        "visible_local_liquidity_proxy": 0.4,
        "duplicate_conflict_penalty": 0.0,
        "missing_data_penalty": -0.1,
        "guard_provenance_quality": 1.0,
        "deferred_item_caveat_penalty": -0.05
      },
      "staleness": {
        "staleness_flag": false,
        "snapshot_age_seconds": 3600,
        "freshness_threshold_seconds": 86400,
        "stale_inputs": [],
        "staleness_warning": null,
        "requires_recapture_before_use": false
      },
      "provenance": {
        "snapshot_manifest_ids": ["manifest-20260603-001"],
        "source_export_paths": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
        "capture_session_ids": ["session-20260603-001"],
        "guard_policy_version": "wp18-guard-v1",
        "quality_report_ids": ["quality-20260603-001"],
        "input_artifact_types": ["market_metadata_snapshot", "order_book_snapshot"]
      },
      "missing_data": {
        "missing_data_warning": false,
        "missing_metadata_fields": [],
        "missing_order_book": false,
        "missing_outcome_tokens": false,
        "missing_category": false,
        "missing_resolution_source": false,
        "insufficient_coverage_reason": null
      },
      "quality_gates": {
        "quality_status": "ACCEPTABLE",
        "quality_warnings": [],
        "dedupe_conflict_flag": false,
        "guard_enforced_capture": true,
        "deferred_item_caveats": ["WP8-D002", "WP16-D002"]
      },
      "component_explanation": "High research priority: complete metadata, fresh snapshots, quality gate ACCEPTABLE, guard-enforced capture. Minor penalty for missing outcome token and rate-limit policy deferred items."
    }
  ]
}
```

This example:
- uses `research_priority_score` (not a forbidden name)
- includes advisory label on both top-level and market objects
- includes staleness and provenance objects
- includes missing-data flags
- does not contain any forbidden fields (`trade_signal`, `alpha_score`, etc.)
- does not imply trading action

## P. Invalid Example Output

The following is an **invalid** example showing forbidden fields. Any future
implementation producing output like this fails the contract:

```json
{
  "opportunity_score": 0.85,
  "alpha_score": 0.72,
  "expected_return": 0.15,
  "buy_recommendation": true,
  "entry": "YES",
  "position_size": 0.05,
  "leverage": 1.0,
  "execution_confidence": 0.9,
  "trade_signal": "LONG",
  "live_trade_authorization": false
}
```

**Why this fails:**

- `opportunity_score` — forbidden field; implies trading opportunity
- `alpha_score` — forbidden field; implies alpha/edge
- `expected_return` — forbidden field; implies investment return
- `buy_recommendation` — forbidden field; implies trading action
- `entry` — forbidden field; implies execution instruction
- `position_size` — forbidden field; implies position sizing
- `leverage` — forbidden field; implies leverage
- `execution_confidence` — forbidden field; implies execution authority
- `trade_signal` — forbidden field; is a direct trading signal
- `live_trade_authorization` — forbidden field; implies trading authorization
  even when set to `false` (the field itself is forbidden)

A future implementation must have tests asserting all of these fields are
absent from every output surface.

## Q. Future Implementation Gates

Any future work package proposing to implement the Market Research Priority
Scoring Layer must satisfy all of the following before implementation begins:

1. This schema/output contract WP (WP48) is merged and included in the
   merged-WPs list in `docs/project_status.md`.
2. The implementation is explicitly approved by the user after WP48 is merged.
   Do not draft an implementation WP until explicitly approved.
3. The implementation imports no network, auth, or runtime dependencies unless
   explicitly approved in a separate WP.
4. The implementation reads only approved local/offline artifacts from
   `local_data/polymarket/snapshots/`, `local_data/polymarket/exports/`,
   or other repo-approved ignored local paths.
5. The implementation writes only to git-ignored `local_data/` paths or stdout.
6. The implementation has tests enforcing:
   - all forbidden fields are absent from every output;
   - advisory labels are present on every top-level and market object;
   - `research_priority_score` is bounded in [0.0, 1.0];
   - missing-data penalties apply when data is missing;
   - staleness flag is present and stale inputs lower the score;
   - provenance is required and missing provenance triggers warnings;
   - `human_review_required` is always `true`;
   - `forbidden_use_notice` is always present and non-empty.
7. No implementation is wired into any strategy module, scheduler, bot loop,
   dashboard, paper-trading engine, or execution gateway.
8. No implementation reads LLM outputs, Hermes outputs, or strategy signals.
9. No implementation uses authenticated API endpoints, credentials, or
   wallet keys.

Implementation must not begin until all gates above are satisfied.

## R. Deferred Items

| ID | Item | Status | Priority |
|---|---|---|---|
| WP48-D001 | Market Research Priority Scoring implementation not started after schema/output contract | OPEN | P3 |
| WP48-D002 | Schema/output contract not enforced by implementation yet | OPEN | P3 |
| WP55-D001 | Resolution ambiguity labels not yet consumed by feature extraction or scoring | OPEN | P3 |
| WP55-D002 | Automated resolution-rule parser remains not started | OPEN | P3 |

WP55 adds `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` as a
docs/schema/tests-only reference for resolution-rule ambiguity review. Future feature
extraction from ambiguity labels may add a reviewed ambiguity component to scoring outputs
only after a separately approved WP satisfies the integration gate conditions in that
document. No new output fields are added to this contract by WP55.

See `docs/deferred_items_log.md` for full entries.

## S. Protected-Boundary Reaffirmation

WP48 reaffirms all existing protected boundaries unchanged:

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
