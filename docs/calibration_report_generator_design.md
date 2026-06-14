# Calibration Report Generator Design

## 1. Status

- WP: WP69 (calibration report generator design only); updated in WP70 and WP71
- Package class: local-offline-read-only-calibration-report-design
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SRC_CHANGE (WP69 docs/schema/tests only); WP71 adds report generator source
- Tools impact: NO_TOOLS_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Report generator implementation status: IN_MEMORY_REPORT_OBJECT_IMPLEMENTED_WP71 (DESIGN_ONLY_NOT_IMPLEMENTED for CLI/export/file writing — those remain deferred)
- Metric computation implementation status: LOCAL_OFFLINE_READ_ONLY_METRIC_COMPUTATION_IMPLEMENTED_WP70
- Advisory label: ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT
- WP70 note: WP70 adds local/offline/read-only metric computation only at `src/data_layer/calibration_metric_computation.py`. It computes research-quality metrics (coverage, missingness, staleness, review burden, bucket distribution, label distribution) from loaded calibration records. It does not implement the calibration report generator, CLI/export, network ingestion, database storage, or any trading/performance metrics. Report generator implementation was deferred as WP70-D001.
- WP71 note: WP71 implements the in-memory report object at `src/data_layer/calibration_report_generator.py`. It builds a frozen `LocalCalibrationReport` dataclass from already-loaded records or a WP68 load result, using WP70 metrics. It does not write files, export reports, add a CLI, fetch outcomes, access the network, compute trading/performance metrics, or integrate with a database/dashboard/scheduler. CLI/export/file writing and dashboard/database behavior remain deferred (WP71-D001 through WP71-D004).

## 2. Report Purpose

The calibration report is:

```text
A local/offline human-readable summary of research-usefulness calibration
results, intended to show whether the research queue helped prioritize
human review of resolved market outcomes.
```

The calibration report is NOT:

```text
a profitability report
a trading performance report
a strategy backtest
a paper-trading report
a live-trading report
a signal report
a portfolio performance report
a win-rate or hit-rate report
```

This report is research-data-quality and human-review-usefulness audit only.

## 3. Report Inputs

A future report implementation should consume local records loaded and
validated by WP68/WP67 components.

### 3.1 Allowed Conceptual Inputs

```text
validated calibration records (from WP68 fixture loader)
record validation results (from WP67 schema validator)
human review usefulness labels
research queue bucket assignments
data-quality fields
resolution-source completeness fields
ambiguity/source review flags
snapshot timing metadata
snapshot timing offset availability
post-resolution audit warning flags
exclusion reason fields
```

### 3.2 Forbidden Inputs

```text
account trades
account positions
account orders
account fills
wallet balances
execution logs
paper-trading ledger
live-trading ledger
profit / PnL / ROI fields
expected return fields
strategy signal fields
```

No account, order, fill, wallet, execution, paper-trading, or live-trading
input is permitted in the calibration report.

## 4. Report Sections

A future report should contain the following sections:

| Section | Description |
|---|---|
| Report identity | Report type, advisory label, scope flags, generated timestamp |
| Input fixture summary | Fixture path, file count, record count |
| Validation summary | Valid count, invalid count, warning count |
| Coverage summary | Coverage rate across input records |
| Missingness summary | Missing required field rates |
| Staleness summary | Staleness rate across snapshot offsets |
| Resolution-source completeness summary | Rate of records with resolution source metadata |
| Manual-review burden summary | Rate of records flagged for manual source or ambiguity review |
| Research queue bucket summary | Distribution of records across bucket categories |
| Human-review usefulness label summary | Distribution of usefulness label assignments |
| Post-resolution audit warnings | Records flagged for post-resolution manual audit |
| Excluded-record summary | Records excluded from calibration with reasons |
| Data-quality interpretation notes | Human-readable notes about data quality |
| Forbidden interpretation notice | Explicit statement of what the report must not be used for |
| Future work / deferred implementation | What remains unimplemented |

## 5. Report Output Contract

The future report generator should return a report object with the following
conceptual shape:

```python
{
    "report_type": "LOCAL_CALIBRATION_REPORT_V1",
    "advisory_label": "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT",
    "report_scope": {
        "local_offline_read_only": True,
        "no_network": True,
        "no_trading": True,
        "no_profitability_metrics": True,
        "no_strategy_output": True,
        "no_paper_trading": True,
        "no_live_trading": True,
    },
    "input_summary": {
        "fixture_path": "...",
        "record_count": 0,
        "source_file_count": 0,
    },
    "validation_summary": {
        "valid_record_count": 0,
        "invalid_record_count": 0,
        "warning_count": 0,
    },
    "coverage_summary": {
        "coverage_rate": 0.0,
    },
    "missingness_summary": {
        "missing_required_field_rate": 0.0,
    },
    "staleness_summary": {
        "staleness_rate": 0.0,
    },
    "resolution_source_summary": {
        "source_metadata_available_rate": 0.0,
        "resolution_source_missing_rate": 0.0,
    },
    "manual_review_summary": {
        "manual_review_required_rate": 0.0,
        "ambiguity_review_required_rate": 0.0,
    },
    "bucket_summary": {
        "bucket_distribution": {},
    },
    "human_review_usefulness_summary": {
        "human_review_usefulness_label_distribution": {},
    },
    "excluded_record_summary": {
        "excluded_record_count": 0,
        "exclusion_reasons": [],
    },
    "warnings": [],
    "post_resolution_audit_warning_count": 0,
    "forbidden_interpretation_notice": (
        "This report is research-usefulness audit data only. "
        "It must not be used as a trading signal, expected-return estimate, "
        "buy/sell recommendation, position-sizing input, or portfolio metric."
    ),
}
```

This is a design contract only. No implementation is added in this WP.

## 6. Allowed Metric Definitions

The following metrics are safe to define and compute in a future
report generator:

```text
record_count
valid_record_count
invalid_record_count
warning_count
coverage_rate
missing_required_field_rate
staleness_rate
manual_review_required_rate
source_metadata_available_rate
resolution_source_missing_rate
ambiguity_review_required_rate
bucket_distribution
human_review_usefulness_label_distribution
excluded_record_count
post_resolution_audit_warning_count
```

These metrics describe data quality and research-usefulness only.

### 6.1 Forbidden Metrics

The following metrics must NEVER appear as positive report outputs:

```text
profit
PnL
ROI
expected return
Sharpe ratio
win rate
trade hit rate
fill quality
execution slippage
edge capture
strategy return
portfolio return
alpha
arbitrage
opportunity score
tradability / tradeable / tradable
```

If those terms appear anywhere in this document outside this section,
they appear only as explicitly forbidden scope.

## 7. Human Interpretation Guidance

### 7.1 Allowed Interpretations

A human reviewing the report may conclude:

```text
The research queue appears more or less useful for prioritizing human review.
Certain data fields are frequently missing and reduce calibration confidence.
Certain bucket categories need more resolved-outcome source review.
Some records should be excluded from calibration due to missing required fields.
More resolved-outcome data is needed before calibration results are reliable.
Staleness in snapshot data at certain timing offsets reduces calibration quality.
```

### 7.2 Forbidden Interpretations

A human reviewing the report must NOT conclude:

```text
Use the queue as a trading strategy or signal.
Treat a high-priority bucket as a buy or sell signal.
Use report results as expected return or position-sizing guidance.
Treat human-review usefulness labels as profitability labels.
Use calibration metrics to update scorer weights without explicit WP approval.
Infer market mispricing, arbitrage, or edge from any report metric.
```

## 8. Non-Signal Boundary

This report is not a signal, not a trade recommendation, not a backtest,
and not a portfolio performance report.

Forbidden positive capability wording that must not appear in this
document or any future report generator:

```text
alpha / edge / opportunity / arbitrage / mispricing
tradeable / tradable / tradability
buy / sell / entry / exit
position size / leverage
expected return / execution confidence / fill probability / slippage
profitable / profit / PnL / ROI / win rate / Sharpe
signal / strategy return / portfolio return
```

The above terms appear in this section only as explicitly forbidden scope.

## 9. Future Implementation Phases

Calibration report generation is phased:

| Phase | Description | WP Status |
|---|---|---|
| Phase 1 | Calibration harness design | WP66 — MERGED |
| Phase 2 | Calibration record schema validator | WP67 — MERGED |
| Phase 3 | Resolved outcome fixture loader | WP68 — MERGED |
| Phase 4 | Calibration report generator design | WP69 — MERGED |
| Phase 5 | Calibration metric computation implementation V1 | WP70 — MERGED |
| Phase 6 | Calibration report generator implementation V1 (in-memory only) | WP71 — ON BRANCH |
| Phase 7 | Human review label workflow integration | NOT STARTED (WP71-D002) |
| Phase 8 | Calibration trend comparison across snapshots | NOT STARTED |
| Phase 9 | Scoring-weight review policy | NOT STARTED (WP71-D003) |
| Phase 10 | Paper/live trading boundary design (future-gated) | DEFERRED (WP71-D004) |

Phases 5 through 10 require separate explicit work package approval.
No implementation authority flows from this design document.

## 10. Scope Boundary

This document defines the calibration report generator design only.

It does NOT authorize:

```text
Calibration metric computation implementation
Calibration report generator implementation
Human review label workflow implementation
Scoring weight updates based on calibration results
Resolved-outcome ingestion from Polymarket API or any external source
Network access of any kind
Backtesting or paper trading of any kind
Live trading of any kind
Strategy signals or trade recommendations
Scheduler, daemon, database, or dashboard behavior
CLI tools or export tools beyond design
Advisory consumer integration
```

See `docs/calibration_harness_design.md` for the calibration harness design.

See `docs/resolved_outcome_data_requirements.md` for resolved-outcome data
requirements.

See `docs/schemas/calibration_report_v1.example.json` for the optional
static example report output shape.

See `docs/deferred_items_log.md` for WP69 deferred items
(WP69-D001 through WP69-D004).
