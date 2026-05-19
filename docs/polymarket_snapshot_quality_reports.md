# Polymarket Snapshot Quality Reports

## Purpose

WP12 adds offline quality/reporting infrastructure for WP10/WP11 local snapshot data. It helps determine whether existing local JSONL snapshots and the in-memory catalog are usable for future research inspection.

This is offline quality/reporting infrastructure only.

## WP12 Scope

WP12 adds:

- Schema and quality validation for loaded WP10 snapshot records.
- Catalog quality metrics derived from WP11 in-memory catalog tooling.
- Sanitized Markdown and JSON local report rendering.
- A manual CLI that reads local snapshot files and writes reports only when explicit output paths are provided.

WP12 does not add network calls, runtime dependencies, database support, scheduler behavior, bot loops, deployment setup, strategy signals, trade proposals, backtesting, paper trading, order handling, signing, authentication, wallet handling, or credential reading.

## Input Data

WP12 reads WP10/WP11 local snapshot data from git-ignored `local_data/polymarket/snapshots/` by default:

- `market_metadata_snapshots.jsonl`
- `order_book_snapshots.jsonl`
- `manifest_*.json`

It reads WP10/WP11 local snapshot data. It does not call Polymarket APIs. It does not capture new data.

## Output Reports

WP12 can render:

- Sanitized Markdown quality reports.
- Sanitized JSON quality summaries.

Reports include counts, distributions, quality status, issue summaries, deferred constraints, and safety statements. Reports do not include raw large payloads, credentials, private keys, wallet material, or secret placeholders.

## Quality Gate Model

The quality gate returns a structured result from source code. Source code does not exit the process. The manual CLI may translate the result to an exit code only when requested:

- Default: warnings do not fail the quality gate.
- `fail_on_warning=True`: warnings fail the quality gate.
- Errors always fail the quality gate result.
- CLI default exits `0` for research reporting.
- CLI `--fail-on-error` exits `1` when errors exist.
- CLI `--fail-on-warning` exits `1` when warnings or errors fail the gate.

## Quality Severity Model

WP12 uses three severities:

- `INFO`: observation only.
- `WARNING`: quality concern that does not fail the default gate.
- `ERROR`: quality failure that makes snapshot data unsafe for quality-dependent research use.

## Snapshot-Level Checks

WP12 checks:

- Required fields for market records.
- Required fields for order-book records.
- Non-empty `snapshot_id`.
- ISO-like `captured_at_utc`.
- Non-empty `market_id`.
- Non-empty `question`.
- `token_ids` is a list.
- `outcome_labels` is a list.
- Token/outcome length mismatch.
- Duplicate `market_id` within the same `snapshot_id`.
- Duplicate `token_id` mapped to multiple `market_id` values.
- Empty `token_ids`.
- Missing `condition_id`.
- `raw_field_names` is a list.
- `read_only_provenance` contains `public-get-only`.
- Manifest `output_files` is populated.
- Manifest `network_used` values are summarized as provenance, not treated as WP12 network use.
- Malformed lines from `snapshot_reader.py` are included as quality issues.

## Catalog-Level Checks

WP12 summarizes:

- Unique market count.
- Total record count.
- Duplicate market count.
- Token count.
- Category coverage.
- Status distribution.
- Snapshot coverage.
- Latest snapshot timestamp.
- Missing category count.
- Missing resolution date count.
- Order-book coverage by `token_id` when order-book records exist.

## Report Generation Behavior

`tools/polymarket/generate_snapshot_quality_report.py`:

- Reads `local_data/polymarket/snapshots/` by default.
- Handles missing or empty input directories gracefully.
- Prints a sanitized console summary.
- Writes nothing by default.
- Writes Markdown or JSON reports only when explicit output flags are provided.
- Requires report output paths under ignored `local_data/`.
- Rejects output paths under source, docs, tests, tools, repo root, protected paths, or `.git`.

## Offline-Only Guarantee

WP12 is offline-only. It reads local files and in-memory objects only. It does not call Polymarket APIs. It does not capture new data. It makes no network calls.

## No Network Access

WP12 source and tests must not import network libraries, `PolymarketPublicClient`, authenticated clients, or venue adapters. It does not use `--allow-network`.

## No Strategy/Trading Authority

WP12 does not create strategy signals. It does not create trade proposals. It does not place, cancel, sign, or simulate orders. It does not authenticate. It does not read credentials.

## No Backtesting Or Paper Trading

WP12 does not backtest. It does not simulate fills. It does not add paper trading, position tracking, performance simulation, or execution replay.

## No Production Readiness Claim

WP12 is research-only local quality/reporting infrastructure. It is not production-ready and must not be treated as an operational monitoring service.

## Local Output Path Policy

Report files may be written only under ignored `local_data/` if explicitly requested. No report outputs, snapshot files, catalog exports, binaries, caches, or generated artifacts may be committed.

## Relationship To Deferred Items

- WP10-D001 remains OPEN. WP12 validates snapshot quality but does not declare the schema production-stable.
- WP10-D002 remains OPEN. WP12 does not add database support.
- WP11-D001 remains OPEN. WP12 does not persist the catalog or add database-backed indexing.
- WP11-D002 remains OPEN. WP12 quality reports do not make replay backtest-ready.

## Future Transition To Database/Reporting Stack

A future database or dashboard-backed reporting stack may be considered only after schema stability, rate-limit policy, storage requirements, and safety boundaries are documented in an approved work package. WP12 does not add a database, scheduler, bot loop, dashboard, or production service.

## Next WP Recommendation

If WP12 succeeds, the next intended WP is WP13 - Snapshot Deduplication And Catalog Export Hardening. If quality/reporting issues remain, the next intended WP should be WP13 - Snapshot Quality Follow-Up.

## Safety Statement

WP12:

- Is offline quality/reporting infrastructure only.
- Reads WP10/WP11 local snapshot data.
- Does not call Polymarket APIs.
- Does not capture new data.
- Does not create strategy signals.
- Does not create trade proposals.
- Does not backtest.
- Does not simulate fills.
- Does not place, cancel, sign, or simulate orders.
- Does not authenticate.
- Does not read credentials.
- Writes reports only under ignored `local_data/` if explicitly requested.
- Is not a database, scheduler, bot loop, or production service.
- Must not be used for automated/frequent market scanning until WP8-D002 is resolved.
