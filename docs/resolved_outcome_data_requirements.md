# Resolved Outcome Data Requirements

## 1. Status

- WP: WP66 (resolved outcome data requirements design merged); WP67 adds local structural validator
- Package class: local-offline-read-only-calibration-design (WP66); local-offline-read-only-calibration-record-validation (WP67)
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SRC_CHANGE (WP66); VALIDATOR_ADDED (WP67)
- Tools impact: NO_TOOLS_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Resolved outcome ingestion status: NOT_STARTED_DESIGN_ONLY
- Ingestion implementation: NOT_AUTHORIZED_BY_THIS_DOCUMENT
- WP67 note: As of WP67, resolved outcome records that follow the WP66 calibration_record_v1 schema can be structurally validated locally using `validate_calibration_record` in `src/data_layer/calibration_record_validation.py`. Structural validation does not constitute ingestion. Resolved outcome ingestion from Polymarket or any external source remains unauthorized and deferred (WP66-D002).

## 2. Purpose

This document defines the minimum data fields required for a future
local/offline resolved-outcome record to be usable in calibration.

It answers the question:

```text
What data will we need later to check whether a research queue item
was clearly resolved and could support a calibration review?
```

It does NOT answer:

```text
Was this market profitable to trade?
What was the expected return?
Should we have taken a position?
What was the win rate or PnL on this outcome?
```

Resolved outcome records are research audit inputs only. They are not
trading performance records.

## 3. Minimum Resolved Outcome Fields

A future resolved outcome record must include at minimum:

| Field | Description |
|---|---|
| market_id | Polymarket market identifier |
| condition_id | Polymarket condition identifier |
| resolved_outcome | The winning outcome token or label as recorded at resolution |
| resolution_status | One of: RESOLVED, VOID, CANCELLED, DISPUTED, PENDING |
| resolution_time_utc | ISO-8601 UTC timestamp of resolution |
| resolution_source_url_or_reference | URL or documentary reference for the resolution source |
| resolution_source_type | One of: OFFICIAL_WEBSITE, NEWS_ARTICLE, PLATFORM_ANNOUNCEMENT, MANUAL_REVIEW, UNKNOWN |
| resolution_rule_text_snapshot_available | Boolean: whether a snapshot of the resolution rule text was captured before resolution |
| resolution_dispute_or_ambiguity_flag | Boolean: whether any dispute or ambiguity was noted at resolution |
| final_market_status | Platform-reported final market status at time of record |
| outcome_token_mapping_verified | Boolean: whether outcome tokens were verified against the resolved_outcome label |

All fields are required except where noted below. Records missing required
fields must be flagged as incomplete and excluded from calibration unless
explicitly testing missing-field rates.

## 4. Optional Extended Fields

Optional fields for richer calibration analysis:

```text
resolution_announcement_url
resolution_announcer
resolution_delay_from_scheduled_utc
platform_resolution_notes
manual_reviewer_id
manual_review_timestamp_utc
dispute_resolution_notes
```

Optional fields must not be required for basic calibration validity.

## 5. Resolution Status Values

Allowed values for `resolution_status`:

| Value | Meaning |
|---|---|
| RESOLVED | Market resolved with a clear winning outcome |
| VOID | Market was voided; no outcome recorded |
| CANCELLED | Market was cancelled before resolution |
| DISPUTED | Resolution was disputed; outcome may be contested |
| PENDING | Resolution not yet finalized at time of record |

PENDING records must not be used in calibration unless explicitly testing
coverage at pre-resolution offsets.

## 6. Resolution Source Type Values

Allowed values for `resolution_source_type`:

| Value | Meaning |
|---|---|
| OFFICIAL_WEBSITE | Primary authoritative official source |
| NEWS_ARTICLE | News reporting used as resolution reference |
| PLATFORM_ANNOUNCEMENT | Polymarket or platform-issued resolution notice |
| MANUAL_REVIEW | Human reviewer determination with documentation |
| UNKNOWN | Source type not identified at time of record |

UNKNOWN source type must trigger a `resolution_source_missing_rate`
increment in calibration metrics.

## 7. Non-Signal Boundary

Resolved outcome records are research data quality inputs only.

Forbidden interpretations of resolved outcome records:

```text
alpha / edge
profitability / PnL / ROI
win rate / hit rate
Sharpe ratio
expected return
trading signal / buy / sell
position size
execution quality
slippage
fill probability
```

Resolved outcome records tell us whether the market resolved clearly and
whether the resolution was auditable. They do not tell us whether a
position would have been profitable.

## 8. Local/Offline Scope Constraint

Resolved outcome records in this design are local/offline only.

This design does NOT authorize:

```text
Polymarket API calls to fetch resolution data
Automated resolution data ingestion from any external source
Network calls of any kind
Scheduled or recurring data fetches
Credentials or authenticated client access
Database-backed resolution record storage
Dashboard-backed resolution display
```

A future approved work package must be created before any resolved-outcome
ingestion, API access, or automated data fetch is implemented.

## 9. Relationship To Calibration Record

A calibration record (defined in `docs/calibration_harness_design.md`)
joins a research queue snapshot record with a resolved outcome record on:

```text
market_id + condition_id
```

Both records must be available and valid before a calibration record can
be created. A calibration record inherits the non-signal boundary from
both the research queue snapshot and the resolved outcome record.

## 10. Deferred Implementation

Implementation of resolved outcome record ingestion, storage, and
validation is deferred.

See `docs/deferred_items_log.md` item WP66-D002.

No implementation authority flows from this document. Any future ingestion
work requires an explicitly approved work package with:

- Explicit network boundary definition
- Explicit credential policy (if any API authentication is needed)
- Explicit non-signal boundary enforcement
- Full repo-truth update
