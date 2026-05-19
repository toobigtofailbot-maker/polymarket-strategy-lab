# Polymarket Snapshot Replay And Normalized Market Catalog

## Purpose

This document describes the offline snapshot replay and normalized market catalog layer added in WP11. It reads WP10 local JSONL snapshot files and builds an in-memory market catalog for research and inspection. No network calls are made. No trading logic exists.

## WP11 Scope

WP11 adds:

- `src/data_layer/polymarket/snapshot_reader.py` — reads WP10 JSONL snapshot files and manifests.
- `src/data_layer/polymarket/market_catalog.py` — builds a normalized in-memory market catalog from loaded records.
- `src/data_layer/polymarket/snapshot_replay.py` — offline replay/iteration helpers for chronological and grouped inspection.
- `tools/polymarket/inspect_snapshot_catalog.py` — manual CLI inspection tool (offline only, no `--allow-network` needed).
- `docs/polymarket_snapshot_replay_catalog.md` — this document.

WP11 does not add:

- Trading logic, order placement, order cancellation, signing, or execution.
- Strategy signals or trade proposals.
- Authenticated clients or credential reading.
- Runtime dependencies (Python standard library only).
- Database, scheduler, bot loop, automated polling, or deployment setup.
- Production readiness.
- Network calls of any kind.

## WP10 Input Files Used

WP11 reads from `local_data/polymarket/snapshots/` (git-ignored):

| File | Content |
|---|---|
| `market_metadata_snapshots.jsonl` | One JSON record per line; each is a `MarketMetadataSnapshotRecord` dict |
| `order_book_snapshots.jsonl` | One JSON record per line; each is an `OrderBookSnapshotRecord` dict |
| `manifest_*.json` | One JSON file per snapshot run; each is a `SnapshotManifest` dict |

These files are produced only by `tools/polymarket/capture_market_snapshots.py` (requires `--allow-network`). WP11 does not produce or modify these files.

## Data Read

- Market metadata records: snapshot_id, captured_at_utc, source, adapter_version, market_id, condition_id, question, market_status, outcome_labels, token_ids, resolution_date, category, raw_field_names, read_only_provenance.
- Order-book records: snapshot_id, captured_at_utc, source, adapter_version, token_id, bids, asks, raw_field_names, read_only_provenance.
- Manifest records: snapshot_id, created_at_utc, tool_name, work_package, markets_requested, markets_written, order_books_requested, order_books_written, network_used, output_files, notes.

## Data Explicitly Not Read

- Full raw API payloads (WP10 never stored them).
- Credentials, API keys, private keys, wallet state, or user positions.
- Any live or real-time market feed.

## Catalog Model

`MarketCatalog` is an in-memory data structure built from a list of `MarketMetadataSnapshotRecord` instances. It provides:

- `get_market(market_id)` — latest record for a market_id by `captured_at_utc`.
- `get_market_history(market_id)` — all records for a market_id, oldest first.
- `get_latest_markets()` — dict of market_id → latest record across all markets.
- `find_by_token_id(token_id)` — market_id owning a given token_id.
- `find_by_condition_id(condition_id)` — market_id for a given condition_id.
- `summary()` — dict with market count, token count, category distribution, active/inactive counts, and snapshot_id coverage.
- `list_market_ids()` — sorted list of all known market_ids.
- `count()` — total unique market count.

The catalog has no trading authority, no order authority, no execution authority, and no scheduling authority.

## Replay Model

`snapshot_replay.py` provides deterministic finite iterators over loaded records:

- `iter_market_records_chronological(records)` — yields records sorted by `captured_at_utc` ascending.
- `group_records_by_snapshot_id(records)` — groups records into a dict keyed by `snapshot_id`.
- `get_snapshot_timeline(records)` — returns a list of `(snapshot_id, captured_at_utc)` tuples sorted by timestamp.
- `replay_snapshots(records, max_steps=None)` — finite iterator yielding `(step, snapshot_id, records_in_snapshot)` tuples. Does not sleep, loop forever, or simulate live data.

Replay is offline file inspection only. It is not paper trading. It is not simulation. It is not execution.

## CLI Inspection Behavior

`tools/polymarket/inspect_snapshot_catalog.py`:

- Reads from `local_data/polymarket/snapshots/` by default (configurable with `--input-dir`).
- Prints a sanitized summary: file counts, manifest count, market record count, unique market count, token count, category summary, latest snapshot timestamp, and a small sample of market IDs/questions.
- Optional `--show-markets N` shows N sample markets.
- Optional `--market-id MARKET_ID` shows detail for one market.
- Optional `--strict` raises on malformed JSONL lines instead of skipping.
- Optional `--summary-json PATH` exports a sanitized summary JSON to a local ignored path (must be under `local_data/`).
- Handles missing snapshot directory or files gracefully (prints a notice and exits 0).
- Does not make network calls.
- Does not require or use credentials.
- Does not run continuously.
- Does not schedule polling.

## Local Output Behavior

If `--summary-json` is used:

- Output path must be under `local_data/` (validated at runtime).
- No raw large payloads are written.
- No credentials are written.
- The output file must be listed in `.gitignore` via the `local_data/` catch-all rule already present.

## Offline-Only Guarantee

The replay/catalog layer is offline-only. All code in `snapshot_reader.py`, `market_catalog.py`, `snapshot_replay.py`, and `inspect_snapshot_catalog.py`:

- Does not import `urllib`, `http.client`, `requests`, `aiohttp`, `socket`, or any network library.
- Does not call `PolymarketPublicClient` or any network adapter.
- Does not read `.env` files.
- Does not read credentials.
- Does not use `--allow-network`.
- Does not make network calls.

## No Network Access

WP11 adds no network calls. It reads only local files produced by the WP10 snapshot capture tool (which requires `--allow-network` to run).

## No Strategy / Trading Authority

WP11 adds no strategy signals, no trade proposals, no order placement, no order cancellation, no signing, no execution, and no authenticated clients.

The following method names are explicitly prohibited in all WP11 source:

- `place_order`, `create_order`, `post_order`, `submit_order`, `cancel_order`, `sign_order`
- `execute_trade`, `trade`, `buy`, `sell`
- `generate_signal`, `create_trade_proposal`

## No Production Readiness Claim

WP11 is research infrastructure only. It is not production-ready. It is not suitable for automated deployment, scheduling, or high-frequency use.

## Relationship To WP10-D001 And WP10-D002

**WP10-D001** (snapshot schema not production-stable): WP11 reads WP10 schemas defensively (malformed lines are skipped, not crashed on). This does not stabilize the schema. WP10-D001 remains OPEN.

**WP10-D002** (snapshot output not database-backed): WP11 builds an in-memory catalog from JSONL files but adds no database. WP10-D002 remains OPEN. A future WP may migrate to SQLite after schema stabilization.

## Future Transition To SQLite / Database

WP11 is JSONL-only and in-memory-only. If a future WP requires queryable, persistent market data, a migration to SQLite (or another local database) should be proposed in a dedicated WP after:

- WP10-D001 schema is declared stable.
- A concrete query requirement is documented.
- Approved scope explicitly authorizes the database dependency.

## Next WP Recommendation

- **WP12 — Snapshot Quality Gates And Local Research Reports**: add schema validation on load, coverage metrics, JSONL deduplication logic, and exportable research reports (Markdown or CSV) to `local_data/`.
- Or **WP12 — Snapshot Replay Follow-Up**: if reader/catalog/replay issues surface during local testing of WP11.

## WP12 Addendum

WP12 adds offline snapshot quality gates and local research reports on top of the WP11 reader/catalog/replay layer. Snapshot replay/catalog data can now be evaluated through structured quality issues, catalog quality metrics, and sanitized Markdown/JSON reports.

Reports remain offline-only and local-data-only. They read WP10/WP11 local snapshot files, make no network calls, and write only under ignored `local_data/polymarket/reports/` when explicitly requested.

WP12 adds no database, no backtesting, no strategy signals, no trade proposals, no scheduler, no bot loop, no authenticated client, and no execution authority.

## Safety Statement

The WP11 snapshot replay and catalog layer:

- Is offline-only and reads only local files.
- Does not call Polymarket APIs.
- Does not capture new network data.
- Does not create strategy signals.
- Does not create trade proposals.
- Does not place, cancel, sign, or simulate orders.
- Does not authenticate.
- Does not read credentials.
- Does not write outside ignored local paths.
- Is not a database, scheduler, bot loop, or production service.
- Must not be used for automated or frequent market scanning until WP8-D002 (rate-limit policy) is resolved.
