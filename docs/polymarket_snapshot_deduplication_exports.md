# Polymarket Snapshot Deduplication And Catalog Exports

## Purpose

WP13 adds deterministic deduplication and sanitized local catalog export helpers for WP10/WP11/WP12 local snapshot tooling.

This is offline local data hygiene/export infrastructure only.

## WP13 Scope

WP13 adds:

- Deterministic deduplication for local market snapshot records.
- Deterministic deduplication for local order-book snapshot records.
- Sanitized JSON-compatible catalog export rendering.
- Simple sanitized CSV market export rendering.
- A manual offline CLI for reading local snapshots, optional deduplication, catalog building, and explicit local exports.

WP13 does not add trading logic, strategy signals, trade proposals, backtesting, paper trading, order placement, order cancellation, signing, wallet/private-key handling, authenticated clients, credentials, `.env` loading, live-trading paths, runtime dependencies, database support, network calls, automated polling, schedulers, bot loops, background workers, or deployment setup.

## Input Data

WP13 reads WP10/WP11/WP12 local snapshot/catalog/quality data. By default, the manual CLI reads ignored local files from:

- `local_data/polymarket/snapshots/`
- `market_metadata_snapshots.jsonl`
- `order_book_snapshots.jsonl`
- `manifest_*.json`

It does not call Polymarket APIs. It does not capture new data.

## Output Exports

WP13 writes export files only when explicitly requested. Allowed output location:

- `local_data/polymarket/exports/`

No committed snapshot files, report files, catalog export files, generated artifacts, or large raw payloads are allowed.

## Deduplication Model

Deduplication operates on records already loaded by `snapshot_reader.py`. It does not mutate input lists. Output is deterministic.

Exact duplicate records are removed. Conflicting records are retained and reported as conflicts. WP13 does not silently merge conflicting records and does not choose a winner by price, order-book content, category, status, question text, or any trading interpretation.

## Deduplication Keys

Market exact deduplication key:

- `snapshot_id`
- `market_id`
- `captured_at_utc`
- `condition_id`
- `tuple(token_ids)`
- `tuple(outcome_labels)`

Order-book exact deduplication key:

- `snapshot_id`
- `token_id`
- `captured_at_utc`
- normalized bids
- normalized asks

Conflict reporting uses local record identity:

- Market identity: `snapshot_id`, `market_id`, `captured_at_utc`
- Order-book identity: `snapshot_id`, `token_id`, `captured_at_utc`

## Conflict Handling

Records with identical full content are dropped after the first occurrence. Records sharing identity with different content are retained and reported. Conflict reports are inspection metadata only and do not infer trading meaning.

## Catalog Export Model

Catalog export helpers render sanitized data from the WP11 in-memory `MarketCatalog`. Exports include:

- `generated_at_utc`
- `export_type`
- `unique_market_count`
- `token_count`
- category distribution
- status distribution
- market summaries
- token-to-market mappings
- condition-to-market mappings
- deduplication summary
- safety statement

Market summaries include only:

- `market_id`
- `condition_id`
- `question`
- `market_status`
- `category`
- `resolution_date`
- `captured_at_utc`
- `snapshot_id`
- `outcome_labels`
- `token_ids`

No raw source payloads are included. WP13 does not export order-book price ladders.

## Export File Formats

WP13 supports:

- Sanitized JSON-compatible catalog export data.
- Simple CSV text for market summaries using Python standard library `csv`.

Writers do nothing unless explicitly called with an output path.

## Offline-Only Guarantee

WP13 is offline-only. It reads local files and in-memory objects only. It does not call Polymarket APIs. It does not capture new data. It makes no network calls.

## No Network Access

WP13 source and tests must not import network libraries, `PolymarketPublicClient`, authenticated clients, or venue adapters. The export CLI has no `--allow-network` option.

## No Strategy/Trading Authority

WP13 does not create strategy signals. It does not create trade proposals. It does not place, cancel, sign, or simulate orders. It does not authenticate. It does not read credentials.

## No Backtesting Or Paper Trading

WP13 does not backtest. It does not simulate fills. It does not add paper trading, position tracking, performance simulation, or execution replay.

## No Database Support

WP13 does not add SQLite, DuckDB, SQLAlchemy, Polars, pandas, indexes, migrations, or any database-backed catalog. Catalogs remain in-memory and exports remain local files.

## No Production Readiness Claim

WP13 is research-only local data hygiene/export infrastructure. It is not production-ready and must not be treated as an operational monitoring service.

## Local Output Path Policy

Export files may be written only under ignored `local_data/` if explicitly requested. Export writers reject paths outside `local_data/` and paths that cross protected repo areas such as `src`, `docs`, `tests`, `tools`, `audits`, repo root, or `.git`.

## Relationship To Deferred Items

- WP10-D001 remains OPEN. WP13 does not declare the snapshot schema production-stable.
- WP10-D002 remains OPEN. WP13 does not add database support.
- WP11-D001 remains OPEN. WP13 does not make the catalog persisted or database-backed.
- WP11-D002 remains OPEN. WP13 does not make replay backtest-ready.
- WP12-D001 remains OPEN. WP13 does not promote quality gates into CI or production policy.
- WP12-D002 remains OPEN. WP13 does not add dashboard-backed reporting.
- WP13-D001 tracks that catalog exports are local-file only and not database-backed.
- WP13-D002 tracks that deduplication policy is research-only and not production canonical.

## Future Transition To Database/Reporting Stack

A future database, dashboard, or reporting stack may be considered only after schema stability, rate-limit policy, storage requirements, security tooling, and runtime boundaries are documented in an approved work package. WP13 must not be used for automated/frequent market scanning until WP8-D002 is resolved.

## Next WP Recommendation

If WP13 succeeds, the next intended WP is WP14 - Official Python Client Dependency Decision And Boundary Review. If deduplication or export issues remain, the next intended WP should be WP14 - Snapshot Deduplication Follow-Up.

## Safety Statement

WP13:

- Is offline local data hygiene/export infrastructure only.
- Reads WP10/WP11/WP12 local snapshot/catalog/quality data.
- Does not call Polymarket APIs.
- Does not capture new data.
- Does not create strategy signals.
- Does not create trade proposals.
- Does not backtest.
- Does not simulate fills.
- Does not place, cancel, sign, or simulate orders.
- Does not authenticate.
- Does not read credentials.
- Writes exports only under ignored `local_data/` when explicitly requested.
- Is not a database, scheduler, bot loop, or production service.
- Must not be used for automated/frequent market scanning until WP8-D002 is resolved.
