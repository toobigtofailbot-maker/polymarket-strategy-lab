# Calibration Harness Design

## 1. Status

- WP: WP66 (calibration harness design merged); WP67 adds local/offline/read-only schema validator
- Package class: local-offline-read-only-calibration-design (WP66); local-offline-read-only-calibration-record-validation (WP67)
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SRC_CHANGE (WP66 docs/schema/tests only); VALIDATOR_ADDED (WP67 adds src/data_layer/calibration_record_validation.py)
- Tools impact: NO_TOOLS_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Calibration implementation status: DESIGN_MERGED (WP66); LOCAL_OFFLINE_READ_ONLY_VALIDATOR_ON_BRANCH (WP67)
- Resolved outcome ingestion status: NOT_STARTED
- Calibration report generator status: NOT_STARTED
- Human review label workflow status: LABELS_DEFINED_DESIGN_ONLY
- WP67 note: WP67 adds a local/offline/read-only calibration record schema validator only. It does not implement resolved outcome ingestion, calibration report generation, fixture loading, human review workflow, or any scoring weight changes. All remaining implementation phases remain deferred per the phase plan below.

## 2. Purpose

Calibration is a local/offline evaluation framework for checking whether
research-priority outputs helped prioritize human research, not whether
they generated trading profit.

This framework will later allow a human reviewer to assess:

```text
Were the markets that ranked highest in the research queue actually
useful for human research study?
```

It will NOT assess:

```text
Were trades on these markets profitable?
Was there alpha or edge?
Should we have bought or sold?
What position size was correct?
What was the expected return?
```

Calibration is a data-quality and research-usefulness audit. It is not a
performance evaluation, not a backtest, and not a trading signal.

## 3. What Calibration Measures

Calibration measures research usefulness across these dimensions:

| Dimension | Description |
|---|---|
| coverage_rate | Fraction of queue items with sufficient data to review |
| missing_data_rate | Fraction of queue items with missing required fields |
| staleness_rate | Fraction of items whose snapshot data was stale at capture time |
| manual_review_rate | Fraction of items flagged for manual source or ambiguity review |
| resolution_source_missing_rate | Fraction of resolved items with no resolution source reference |
| ambiguity_label_rate | Fraction of items with resolution ambiguity labels applied |
| bucket_stability | Whether bucket assignment was stable across snapshot offsets |
| post_resolution_audit_required_rate | Fraction of items requiring post-resolution manual audit |
| human_review_usefulness_label | Whether a reviewer found the item useful to study |

Calibration does NOT measure:

```text
profit / PnL / ROI
expected return
Sharpe ratio
win rate
trade hit rate
fill quality
execution slippage
edge capture
```

Those terms may appear only in the Forbidden Scope section of this document
or in future paper/live deferral sections.

## 4. Calibration Unit

The primary unit of calibration is:

```text
One market context / research queue item at one snapshot time
```

A future calibration record identifies a single market at a single snapshot
moment and tracks whether that item was useful for human research.

Key identity fields for a future calibration record:

```text
market_id
condition_id
question
category
snapshot_time_utc
local_capture_time_utc
research_queue_bucket
research_review_priority
research_priority_score
quality_status
source_metadata_available
manual_source_review_required
resolution_ambiguity_manual_review_required
microstructure_quality_summary
cross_market_candidate_count
```

These fields come from the existing WP49–WP64 pipeline outputs. No new source
fields are defined by this WP.

## 5. Human Review Usefulness Labels

A future calibration record will include a human-assigned usefulness label.
These labels are research-review labels, not trade results.

Allowed labels:

| Label | Meaning |
|---|---|
| USEFUL_RESEARCH_TARGET | Reviewer found this market worth studying in detail |
| PARTIALLY_USEFUL_RESEARCH_TARGET | Reviewer found partial value; data or resolution limited |
| NOT_USEFUL_DATA_TOO_WEAK | Data quality was insufficient for meaningful research review |
| NOT_USEFUL_RESOLUTION_TOO_AMBIGUOUS | Resolution rule or outcome was too ambiguous to assess |
| NOT_USEFUL_DUPLICATE_OR_OVERLAP | Substantially overlaps another higher-priority market |
| NOT_REVIEWED | Item was not reviewed in this calibration pass |

These labels are assigned by a human reviewer after resolution, not by the
scoring system. The scoring system produces no usefulness label.

## 6. Snapshot Timing Requirements

Calibration must compare research outputs at fixed pre-resolution offsets to
assess whether the scoring was useful before resolution was known.

Future required snapshot timing offsets (design only; not yet implemented):

```text
T-30d  (30 days before scheduled resolution)
T-7d   (7 days before scheduled resolution)
T-24h  (24 hours before scheduled resolution)
T-6h   (6 hours before scheduled resolution)
T-1h   (1 hour before scheduled resolution)
T-15m  (15 minutes before scheduled resolution)
```

These offsets define when a snapshot must have been captured for a
calibration record to be valid at that offset. Gaps in snapshot coverage
at a required offset are recorded as `missing_at_offset`.

Snapshot timing capture is not implemented in this WP. This design defines
the requirement only.

## 7. Calibration Gates

The following gates must be satisfied before a future calibration record
is considered valid:

```text
Do not calibrate if market_id is missing.
Do not calibrate if condition_id is missing.
Do not calibrate if outcome-token mapping is unverified.
Do not calibrate if snapshot_time_utc is missing.
Do not calibrate if local_capture_time_utc is missing.
Do not calibrate if resolution source is missing, unless explicitly
  testing missing-source rates.
Do not use calibration output as a trading signal.
Do not use calibration output as a buy/sell recommendation.
Do not use calibration output as a position-sizing input.
Do not use calibration output as an expected-return estimate.
```

## 8. Non-Signal Boundary

Calibration output is research-usefulness audit data only.

Forbidden interpretations of calibration output:

```text
alpha
edge
opportunity
arbitrage
mispricing
tradability / tradeable / tradable
buy / sell recommendation
entry / exit signal
position size
leverage recommendation
expected return
execution confidence
fill probability
slippage estimate
profitable / PnL / ROI / win rate
Sharpe ratio
signal
```

Allowed interpretations of calibration output:

```text
research usefulness label
human review outcome
data quality assessment
resolution clarity note
source completeness observation
bucket stability observation
coverage rate observation
missingness rate observation
staleness rate observation
manual review rate observation
post-resolution audit requirement
```

## 9. Future Implementation Phases

Calibration implementation is phased. This WP covers Phase 1 only.

| Phase | Description | WP Status |
|---|---|---|
| Phase 1 | Docs/schema design only | WP66 — THIS WP |
| Phase 2 | Local calibration record schema validator | NOT STARTED |
| Phase 3 | Local resolved outcome fixture loader | NOT STARTED |
| Phase 4 | Calibration report generator | NOT STARTED |
| Phase 5 | Human review label workflow | NOT STARTED |
| Phase 6 | Paper/live trading boundary design (future-gated) | DEFERRED |

Phase 2 and later must be approved as separate work packages. No
implementation authority flows from this design document.

## 10. Scope Boundary

This document defines the calibration harness design only.

It does NOT authorize:

```text
Resolved-outcome ingestion from Polymarket API or any external source
Polymarket API calls of any kind
Network access of any kind
Backtesting or paper trading of any kind
Live trading of any kind
Strategy signals or trade recommendations
Score recalibration or weight changes
Scheduler, daemon, database, or dashboard behavior
CLI tools or export tools beyond design
Advisory consumer integration
```

See `docs/resolved_outcome_data_requirements.md` for the companion
resolved-outcome data requirements design.

See `docs/deferred_items_log.md` for calibration-specific deferred items
(WP66-D001 through WP66-D004).
