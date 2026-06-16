# Calibration Report Export Operator Runbook

## 1. Purpose

This runbook describes how a human operator can explicitly generate a local
calibration report from local calibration record fixtures and export it as JSON
or Markdown for research review.

The export tool answers:

> Can a human operator explicitly generate a local calibration report briefing
> from local calibration record fixtures?

It does NOT answer:

> Can the system automatically run reports?
> Can it fetch resolved outcomes?
> Can it publish dashboards?
> Can it score trading performance?
> Can it decide what to trade?

This is an explicit, manual, local-only, offline-only operation.

---

## 2. Advisory Notice

**ADVISORY-ONLY LOCAL CALIBRATION REPORT.**

All output from this tool is advisory-only research-usefulness audit data. It
is not a trading signal, not expected return, not position sizing, and not an
execution instruction.

Do not use any field, rate, count, bucket label, or section heading in the
report output as a basis for trading decisions.

---

## 3. Prerequisites

- Python 3.11 or later, installed and available in your shell.
- The `polymarket-strategy-lab` repository cloned locally.
- Local calibration record JSON fixture files available at an explicit local
  path. Do not point the tool at URLs or remote paths.
- Run commands from the repository root directory.

---

## 4. Local Input Fixture Expectations

The `--input` flag accepts three fixture shapes:

### 4.1 Single JSON object file

A file containing one calibration record object at the JSON root:

```json
{
  "_notice": "ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT",
  "_schema_version": "calibration_record_v1",
  "_status": "RESEARCH_QUALITY_ONLY_NOT_TRADING",
  "identity": { ... },
  "snapshot_metadata": { ... },
  "research_queue_state": { ... },
  "resolved_outcome": { ... },
  "human_review": { ... },
  "calibration_validity": { ... }
}
```

### 4.2 JSON list file

A file containing a JSON array of calibration record objects at the JSON root:

```json
[
  { ... record 1 ... },
  { ... record 2 ... }
]
```

### 4.3 Directory of direct-child *.json files

A directory whose immediate children are individual `.json` calibration record
files (not recursive). Files are loaded sorted by filename:

```
local_data/calibration_fixtures/
    record_001.json
    record_002.json
    record_003.json
```

Non-JSON files in the directory are ignored. Subdirectories are not descended
into.

### 4.4 URL-like inputs are rejected

The tool does not accept `http://`, `https://`, `ftp://`, or `ftps://` input
paths. Only explicit local file system paths are accepted.

---

## 5. Example Commands

### 5.1 JSON output to stdout

```bash
python -m tools.calibration.local_calibration_report_export \
    --input local_data/calibration_fixtures/my_records.json \
    --format json
```

### 5.2 Markdown output to stdout

```bash
python -m tools.calibration.local_calibration_report_export \
    --input local_data/calibration_fixtures/my_records.json \
    --format markdown
```

### 5.3 Markdown output to an explicit local file

```bash
python -m tools.calibration.local_calibration_report_export \
    --input local_data/calibration_fixtures/my_records.json \
    --format markdown \
    --output local_data/calibration_reports/report.md
```

### 5.4 JSON output to an explicit local file

```bash
python -m tools.calibration.local_calibration_report_export \
    --input local_data/calibration_fixtures/my_records.json \
    --format json \
    --output local_data/calibration_reports/report.json
```

### 5.5 Including records that have loader-level warnings

By default the tool exits 1 if the WP68 loader returns errors (e.g. path not
found, invalid JSON). If you want to proceed even when individual records are
invalid against the schema, this is the default behavior — individual record
validation failures do not cause exit 1. Only loader-level errors (missing
paths, bad JSON, URL-like paths) cause exit 1 by default.

---

## 6. Supported Flags

| Flag | Required | Description |
|---|---|---|
| `--input` | Yes | Local path to a JSON file or directory of *.json files. |
| `--format json\|markdown` | No (default: json) | Output format. |
| `--output` | No (default: stdout) | Explicit local output path. |
| `--include-invalid-records` | No | Proceed even if loader returns errors. |

---

## 7. Stdout Behavior

If `--output` is not provided, the report is printed to stdout. Stderr shows
any warnings or error messages.

You can pipe stdout to other tools or redirect to a file manually:

```bash
python -m tools.calibration.local_calibration_report_export \
    --input my_records.json --format json > my_report.json
```

---

## 8. Explicit Output Path Behavior

If `--output` is provided, the tool writes only to that path and prints
`Written to: <path>` on stderr.

The output path must not point into tracked repository directories (`src/`,
`tests/`, `docs/`, `tools/`, `.github/`). Symlinks that resolve into those
directories are also rejected.

If the output path is unsafe, the tool exits with code 2.

---

## 9. Recommended Ignored Output Location

Store generated calibration report files under:

```
local_data/calibration_reports/
```

This directory is git-ignored. Generated reports must not be committed to the
repository.

---

## 10. How to Read Report Sections

### report_type

Always `LOCAL_CALIBRATION_REPORT_V1`. Confirms the report object version.

### advisory_label

Always `ADVISORY_ONLY_RESEARCH_USEFULNESS_AUDIT`. Confirms this is not a
trading or performance report.

### report_scope

Safety flags confirming what the report does not do: no network, no trading, no
profitability metrics, no paper trading, no live trading, no file writes.

### input_summary

Counts of total, valid, and invalid records loaded from the input fixtures.

### validation_summary

WP67 schema validation warning counts for the loaded records.

### coverage_summary

`coverage_rate`: fraction of loaded records that passed schema validation.
A low coverage rate means many fixtures have structural issues.

### missingness_summary

`missing_required_field_rate`: fraction of records with missing required fields.

### staleness_summary

`staleness_rate`: fraction of records whose snapshot timing offset is missing or
not within the allowed set (`T_MINUS_7_DAYS`, `T_MINUS_3_DAYS`, `T_MINUS_1_DAY`).

### resolution_source_summary

Rates for source metadata availability and resolution source URL/reference
missingness.

### manual_review_summary

Rates for records flagged as requiring manual source review or ambiguity review.

### bucket_summary

Distribution of records across research queue buckets (`REVIEW_FIRST`,
`MANUAL_SOURCE_REVIEW_REQUIRED`, `REVIEW_LATER`, `DATA_QUALITY_BLOCKED`,
`DEPRIORITIZED`).

### human_review_usefulness_summary

Distribution of human review usefulness labels applied to the records.

### excluded_record_summary

Count of records excluded from calibration and post-resolution audit warning
count.

### warnings

List of data quality warnings produced during metric computation. Common
warnings: `no_records`, `all_records_invalid`, `missing_required_field_rate_high`,
`resolution_source_missing_rate_high`, `manual_review_required_rate_high`.

### forbidden_interpretation_notice

Fixed advisory notice. Always present. Not configurable.

---

## 11. What the Report Does Not Mean

The calibration report does NOT indicate:

- Which markets were profitable to trade.
- What the expected return of any market was.
- What position size was appropriate.
- Which markets have alpha or edge.
- Whether to buy or sell any outcome token.
- What the Sharpe ratio of any strategy was.
- What the win rate of any model was.
- How execution quality compared across markets.
- Whether any fill or slippage was acceptable.

---

## 12. Forbidden Interpretations

Do not interpret any field, rate, count, bucket, section, or label in this
report as:

- a trading signal;
- a buy/sell recommendation;
- an expected return;
- a position size;
- an execution instruction;
- an indication of any actionable research conclusion.

Human review is required before any use of this report content in a research
workflow.

---

## 13. Troubleshooting

### Exit code 1 — input error or load failure

Check that:
- The `--input` path exists and is readable.
- The file is valid JSON.
- The path is not a URL (e.g. `http://...`).
- The directory contains at least one `.json` file if a directory was passed.
- The `--format` flag is `json` or `markdown` (not another string).

### Exit code 2 — unsafe output path

Check that `--output` does not point into `src/`, `tests/`, `docs/`, `tools/`,
`.github/`, or a symlink that resolves into one of those directories. Use
`local_data/calibration_reports/` instead.

### No output / empty stdout

If the input file was loaded but the report shows zero records, verify the
input fixture has at least one valid JSON object or list entry.

### Warnings in the report

High rates of `missing_required_field_rate_high` or
`resolution_source_missing_rate_high` indicate fixture data quality issues, not
tool errors. Review the fixture schema against the WP67 validator requirements.

---

## 14. No Network

This tool makes no network calls. It reads only the explicitly provided local
input path. It writes only to stdout or an explicitly provided local output
path.

If you see network-related errors, check that no proxy, VPN, or OS hook is
intercepting file reads.

---

## 15. No Credentials

This tool uses no credentials, API keys, private keys, wallet files, `.env`
files, or authenticated sessions.

Do not provide secrets through environment variables or file paths to this tool.

---

## 16. No Scheduler

This tool is invoked explicitly by a human operator only. It has no built-in
scheduler, cron job, daemon, polling loop, or auto-run behavior.

If you want to run this tool on a schedule, you must set up an explicit
approved external scheduler outside the tool itself, subject to future approved
scope authorization.

---

## 17. No Dashboard or Database

This tool writes to stdout or an explicit local file only. It does not write to
any database, dashboard, monitoring service, report history store, or cache.

---

## 18. No Trading

This tool does not execute, propose, or recommend any trades. It does not
generate buy/sell orders, position sizes, execution instructions, or advisory
outputs that should feed into a trading workflow.

---

## 19. WP Context

This runbook was added in WP72 — Post-WP71 Repo-Truth Reconciliation And Local
Calibration Report Export V1.

The export tool uses:
- WP68 `load_resolved_outcome_fixtures` for input loading.
- WP71 `build_calibration_report_from_load_result` for in-memory report generation.

It does not duplicate the loader or report generator logic.

---

## 20. Human Review Labels Note (WP73)

WP73 added `docs/human_review_label_workflow_design.md`, which defines how a human analyst
can label whether a reviewed market was useful for research calibration.

Human review labels are **design-stage only** in WP73. They are not yet integrated into
this export tool or the report generator output. The `human_review_usefulness_label` field
visible in calibration records is a field defined in the calibration record schema (WP66/WP67)
but does not yet benefit from the full WP73-designed label workflow, validator, or fixture loader.

Label/report integration is deferred per WP73-D003. Until a future approved WP implements
label/report integration, this tool's output does not include separately authored WP73-format
human review label records.
