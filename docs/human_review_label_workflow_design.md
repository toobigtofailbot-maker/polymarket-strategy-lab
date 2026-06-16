# Human Review Label Workflow Design

## 1. Status

- WP: WP73 (human review label workflow design merged)
- Package class: local-offline-read-only-human-review-label-workflow-design
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SRC_CHANGE
- Tools impact: NO_TOOLS_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Human review label workflow status: DESIGN_SCHEMA_TESTS_ONLY
- Label implementation status: NOT_STARTED
- Label editor status: NOT_STARTED
- Label loader status: LOCAL_OFFLINE_READ_ONLY_FIXTURE_LOADER_IMPLEMENTED_WP75
- Label validator status: LOCAL_OFFLINE_READ_ONLY_VALIDATOR_IMPLEMENTED_WP74
- Label report integration status: NOT_STARTED
- Automated labeling status: FORBIDDEN
- LLM labeling status: FORBIDDEN

## 2. Purpose

This document defines the human review labeling workflow for local calibration records.

The purpose of human review labeling is:

```text
A manual analyst annotation workflow for recording whether a reviewed market
was useful for research calibration.
```

It is NOT:

```text
a trade outcome label
a profitability label
a buy/sell label
a scoring-weight update
an automated judgment
an LLM-generated label
a signal of any kind
a performance indicator
```

The design answers:

```text
How should a human analyst mark whether a reviewed market was useful for
research calibration?
```

It must NOT answer:

```text
Was this a good trade?
Should the bot buy or sell?
How much should we size?
What was expected return?
Should the score weights change automatically?
```

## 3. Non-Signal Boundary

This workflow is a manual research-usefulness annotation layer only.

Labels produced by this workflow:

- may be aggregated for data quality assessment;
- may inform future calibration review workflows;
- must not be used as trade signals;
- must not change research_priority_score automatically;
- must not trigger strategy, paper trading, or live trading behavior;
- must not be interpreted as buy/sell recommendations;
- must not be interpreted as profitability or expected-return indicators.

Forbidden wording in positive capability descriptions:

- alpha, edge, opportunity, arbitrage, mispricing
- trade, trading, tradability, tradeable, tradable
- buy, sell, entry, exit, position size, leverage
- expected return, execution confidence, fill probability, slippage
- profitable, profit, PnL, ROI, win rate
- Sharpe, signal, strategy return, portfolio return
- auto-label, LLM label

Allowed positive wording:

- human review, manual label, research usefulness
- data quality, resolution clarity, source completeness
- market overlap context, review notes, review state
- calibration support, second review, excluded from calibration

## 4. Label Unit

One label record is:

```text
one human review label for one market context / calibration record at one review time
```

A label record annotates a snapshot of a specific market at a specific review time.

Required identity fields:

```text
market_id
condition_id
question
snapshot_time_utc
review_time_utc
reviewer_id_or_alias
```

Notes:

- Real names or credentials are not required.
- `reviewer_id_or_alias` may be a pseudonym or internal reviewer identifier.
- `review_time_utc` is the time the label was applied, not the time of market resolution.
- `snapshot_time_utc` is the time the calibration record snapshot was captured.

## 5. Allowed Human Review Usefulness Labels

```text
USEFUL_RESEARCH_TARGET
PARTIALLY_USEFUL_RESEARCH_TARGET
NOT_USEFUL_DATA_TOO_WEAK
NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS
NOT_USEFUL_DUPLICATE_OR_OVERLAP
NOT_REVIEWED
REVIEW_BLOCKED_INSUFFICIENT_CONTEXT
```

Label semantics:

- `USEFUL_RESEARCH_TARGET` — the market and its associated data were sufficiently
  clear and complete to serve as a useful calibration research target.
- `PARTIALLY_USEFUL_RESEARCH_TARGET` — the market was useful for some aspects of
  calibration review but had notable gaps or ambiguities.
- `NOT_USEFUL_DATA_TOO_WEAK` — the market lacked enough data completeness or source
  quality to support a useful calibration review.
- `NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS` — the resolution rule or outcome was too
  ambiguous to support a reliable calibration review.
- `NOT_USEFUL_DUPLICATE_OR_OVERLAP` — the market substantially overlaps with another
  market already reviewed, reducing its independent calibration value.
- `NOT_REVIEWED` — the record exists but has not yet been reviewed by a human analyst.
- `REVIEW_BLOCKED_INSUFFICIENT_CONTEXT` — the reviewer could not complete a meaningful
  review because required context (source, resolution rule, snapshot data) was missing.

These labels are research-usefulness oriented. They are not trade labels,
profitability labels, or buy/sell labels.

## 6. Allowed Confidence Labels

```text
LOW
MEDIUM
HIGH
NOT_APPLICABLE
```

Notes:

- `NOT_APPLICABLE` is appropriate when the label is `NOT_REVIEWED`.
- Confidence labels reflect the reviewer's confidence in their research-usefulness
  assessment, not trading confidence, execution confidence, or profitability confidence.
- Probability, expected value, and trading-confidence wording are forbidden.

## 7. Allowed Primary Reasons

```text
SOURCE_CLARITY
RESOLUTION_RULE_CLARITY
DATA_COMPLETENESS
MARKET_OVERLAP_CONTEXT
QUEUE_BUCKET_RELEVANCE
AMBIGUITY_TOO_HIGH
SOURCE_MISSING
OUTCOME_MAPPING_UNCLEAR
DUPLICATE_OR_OVERLAP
NOT_ENOUGH_CONTEXT
```

Reason semantics:

- `SOURCE_CLARITY` — the resolution source was clear and accessible.
- `RESOLUTION_RULE_CLARITY` — the resolution rule was well-defined and unambiguous.
- `DATA_COMPLETENESS` — all required calibration record fields were populated.
- `MARKET_OVERLAP_CONTEXT` — related markets were identified and contextualized.
- `QUEUE_BUCKET_RELEVANCE` — the research queue bucket assignment matched expectation.
- `AMBIGUITY_TOO_HIGH` — ambiguity in resolution rule or data was too high for review.
- `SOURCE_MISSING` — the resolution source URL or reference was absent.
- `OUTCOME_MAPPING_UNCLEAR` — the mapping from token outcomes to resolution was unclear.
- `DUPLICATE_OR_OVERLAP` — a substantially overlapping market was already reviewed.
- `NOT_ENOUGH_CONTEXT` — the reviewer lacked sufficient context to complete the review.

## 8. Required Reason Fields

Optional but structured reason fields:

```text
primary_reason
secondary_reasons
review_notes
confidence_level
requires_followup_review
```

- `primary_reason` — the most important factor determining the label.
- `secondary_reasons` — list of additional factors; may be empty.
- `review_notes` — free-text analyst commentary; must not include forbidden terms.
- `confidence_level` — one of: LOW, MEDIUM, HIGH, NOT_APPLICABLE.
- `requires_followup_review` — boolean; true if the reviewer believes a second review
  is needed.

## 9. Workflow States

Safe manual workflow states:

```text
NOT_REVIEWED
IN_REVIEW
LABEL_APPLIED
NEEDS_SECOND_REVIEW
EXCLUDED_FROM_CALIBRATION
```

State semantics:

- `NOT_REVIEWED` — the calibration record has not entered any review workflow.
- `IN_REVIEW` — a reviewer has started but not yet completed the review.
- `LABEL_APPLIED` — a human review label has been applied and recorded.
- `NEEDS_SECOND_REVIEW` — the initial reviewer flagged the label as needing
  independent review.
- `EXCLUDED_FROM_CALIBRATION` — the record has been explicitly excluded from
  calibration aggregation.

The following automated state is explicitly forbidden:

```text
AUTO_LABELED_BY_LLM  (FORBIDDEN — not an allowed workflow state)
```

## 10. Quality Gates

A label must meet the following conditions to be considered valid for future use:

```text
A label must not be considered final without market identity.
A label must not be considered final without reviewer alias.
A label must not be considered final without review_time_utc.
A label must not change research_priority_score automatically.
A label must not trigger strategy, paper trading, or live trading behavior.
A label must remain manually applied until explicit future automation approval.
```

Specifically:

- `market_id`, `condition_id`, `question`, and `snapshot_time_utc` are required.
- `reviewer_id_or_alias` is required.
- `review_time_utc` is required.
- All other fields are optional in the design stage.

## 11. Interaction with Calibration

Future calibration use of human review labels is limited to research-quality purposes:

Allowed calibration uses:

```text
aggregate human-review usefulness distribution
compare usefulness labels by queue bucket
identify recurring missing-data patterns
identify source ambiguity problems
support future manual scoring review
```

Forbidden calibration uses:

```text
automatic scoring weight changes
trade signals
expected return
strategy selection
position sizing
paper/live execution
```

Human review labels must not propagate into:

- the research priority scorer weights or thresholds;
- the advisory consumer output as a signal;
- any paper or live trading execution path.

## 12. Future Implementation Phases

The human review label workflow is design-only in WP73. WP74 implements the local label record validator (Phase 2). Remaining phases are deferred.

Future phases (not authorized beyond WP74 scope):

1. **WP73** (merged): design/schema only.
2. **WP74** (merged): Local label record validator — validates label records against this schema. Implemented in `src/data_layer/human_review_label_validation.py`. Local/offline/read-only, stdlib-only, no file I/O, no network, no automation.
3. Local label fixture loader — loads label records from explicit local paths.
4. Label merge/join with calibration records — joins labels to calibration records.
5. Report integration — includes label aggregates in calibration reports.
6. Optional manual export — exports label records to stdout or explicit local paths.
7. Scoring-weight review policy design — designs the gate for using label patterns
   in a future scoring weight review, subject to explicit approval and non-signal
   boundary review.
8. Any automation/LLM labeling requires separate explicit approval, risk review, and
   protected-boundary review. No automated or LLM-based labeling is authorized.

No future phase is authorized by this design document. Each phase requires separate
explicit user approval and a scoped work package.

## 13. Forbidden Scope

This workflow design document must not be interpreted as authorization for:

- a human review label editor implementation;
- a CLI or export tool for label records;
- calibration report or report exporter changes;
- calibration report generator changes;
- metric computation changes;
- resolved outcome ingestion;
- Polymarket API calls;
- network access;
- web scraping;
- database storage;
- dashboard display;
- scheduler;
- LLM/agent auto-labeling;
- advisory consumer integration;
- strategy proposal;
- expected return model;
- profit/PnL/ROI calculations;
- win-rate or hit-rate calculations;
- trade recommendation;
- scoring weight changes;
- paper trading;
- live trading;
- order placement, cancellation, or status tracking;
- credentials or authenticated client use;
- dependency or lock-file changes.

## 14. Relationship to Existing Design Documents

- `docs/calibration_harness_design.md` — overall calibration harness design; WP73 adds the
  human review label design phase.
- `docs/calibration_report_generator_design.md` — calibration report generator design; labels
  are design-stage only and not yet integrated into report output.
- `docs/calibration_report_operator_runbook.md` — operator runbook for calibration report
  export; labels are not yet integrated.
- `docs/resolved_outcome_data_requirements.md` — resolved outcome field requirements.
- `docs/deferred_items_log.md` — deferred items tracking human review label implementation.

## 15. Schema Reference

A static advisory-only example label record is defined at:

```text
docs/schemas/human_review_label_record_v1.example.json
```

This example is advisory only, not an implementation specification or runtime schema.
