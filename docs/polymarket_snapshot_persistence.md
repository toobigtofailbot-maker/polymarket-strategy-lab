# Polymarket Snapshot Persistence

## Purpose

This document describes the local file-based snapshot persistence layer added in WP10 for read-only research use. It records the design, scope, output format, safety rules, and deferred constraints governing snapshot capture and storage.

Snapshot persistence is read-only research infrastructure. It does not create strategy signals. It does not create trade proposals. It does not place, cancel, sign, or simulate orders. It does not authenticate. It does not read credentials. It writes only to ignored local paths by default. It is not a scheduler or bot loop.

## WP10 Scope

WP10 adds:

- `src/data_layer/polymarket/snapshot_models.py` — normalized dataclasses for market metadata and order-book snapshot records, a run manifest, and a write result.
- `src/data_layer/polymarket/snapshot_writer.py` — JSONL file writer that validates output paths against approved local roots.
- `src/data_layer/polymarket/snapshot_capture.py` — reusable capture function that calls the read-only adapter and returns snapshot records and a manifest.
- `tools/polymarket/capture_market_snapshots.py` — manual CLI tool gated by `--allow-network`.
- `docs/polymarket_snapshot_persistence.md` — this document.

WP10 does not add:

- Trading logic, order placement, order cancellation, signing, or execution.
- Authenticated clients or credential reading.
- Runtime dependencies (Python standard library only).
- Database, scheduler, bot loop, automated polling, or deployment setup.
- Production readiness.

## Confirmed Endpoint Basis From WP9

WP10 uses only the three endpoints confirmed by WP9 controlled probes (2026-05-18):

| Endpoint | Status | Notes |
|---|---|---|
| `GET https://gamma-api.polymarket.com/markets` | VERIFIED | Returns JSON list; clobTokenIds and outcomes are JSON-encoded strings |
| `GET https://gamma-api.polymarket.com/markets/{id}` | VERIFIED | id must be integer string, not conditionId |
| `GET https://clob.polymarket.com/book?token_id=...` | VERIFIED | Returns bids/asks as lists of {price, size} dicts |
| `GET https://clob.polymarket.com/health` | UNVERIFIED | Returned HTTP 404 in WP9; not used in WP10 |

WP10 does not use CLOB `/health` because WP9 found it returns HTTP 404 and the correct path is unknown (WP9-D001 OPEN).

## Data Captured

- Market metadata: market_id, condition_id, question, market_status, outcome_labels, token_ids, resolution_date, category, raw_field_names (list of API field names present, not the full raw payload).
- Order-book data (optional, off by default): token_id, bids, asks (normalized {price, size} string dicts), raw_field_names.
- Provenance fields on every record: snapshot_id, captured_at_utc, source, adapter_version, read_only_provenance.
- Run manifest: snapshot_id, created_at_utc, tool_name, work_package, markets_requested, markets_written, order_books_requested, order_books_written, network_used, output_files, notes.

## Data Explicitly Not Captured

- Full raw API payloads (only field names are recorded for schema tracking).
- CLOB `/health` response (endpoint unverified, not used).
- Credentials, API keys, private keys, wallet keys, mnemonics, passphrases, or tokens of any kind.
- Order state, fills, balances, positions, or portfolio data.
- Any authenticated or private endpoint data.

## Local Output Directory

Default output path: `local_data/polymarket/snapshots/`

This directory is added to `.gitignore`. Snapshot files must never be committed to the repository. Tests must use `pytest tmp_path`, not the real `local_data/` directory.

The snapshot writer enforces this by validating that the output path contains `local_data` as a path component. To use a different path, callers must pass `_allow_any_output_dir=True` (intended for tests only).

## File Format

- Market metadata snapshots: JSONL (append mode) — `market_metadata_snapshots.jsonl`
- Order-book snapshots: JSONL (append mode) — `order_book_snapshots.jsonl`
- Run manifest: JSON (one file per run) — `manifest_{snapshot_id}.json`

JSONL format supports incremental runs: each capture run appends records to the same JSONL file. Each record is self-contained with its own `snapshot_id` for run attribution.

## Snapshot Record Schema

### MarketMetadataSnapshotRecord

| Field | Type | Description |
|---|---|---|
| snapshot_id | str | Run-level ID (e.g. snap_20260519_143022_000000) |
| captured_at_utc | str | ISO 8601 UTC timestamp |
| source | str | "gamma-api/markets" |
| adapter_version | str | "wp10" |
| market_id | str | Integer string id from Gamma API |
| condition_id | str | Hex conditionId hash |
| question | str | Market question text |
| market_status | str | Active/status field value |
| outcome_labels | list[str] | Parsed outcome labels |
| token_ids | list[str] | Parsed CLOB token IDs |
| resolution_date | str or null | Resolution/end date |
| category | str or null | Market category |
| raw_field_names | list[str] | Sorted list of API response field names |
| read_only_provenance | str | "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only" |

### OrderBookSnapshotRecord

| Field | Type | Description |
|---|---|---|
| snapshot_id | str | Run-level ID |
| captured_at_utc | str | ISO 8601 UTC timestamp |
| source | str | "clob-api/book" |
| adapter_version | str | "wp10" |
| token_id | str | CLOB outcome token ID |
| bids | list[{price, size}] | Bid levels (string values) |
| asks | list[{price, size}] | Ask levels (string values) |
| raw_field_names | list[str] | Sorted list of API response field names |
| read_only_provenance | str | "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only" |

## Manifest Schema

| Field | Type | Description |
|---|---|---|
| snapshot_id | str | Run-level ID shared with records |
| created_at_utc | str | ISO 8601 UTC timestamp |
| tool_name | str | "capture_market_snapshots" |
| work_package | str | "WP10" |
| markets_requested | int | markets_limit passed to tool |
| markets_written | int | Records actually written |
| order_books_requested | int | Token IDs attempted |
| order_books_written | int | Order-book records written |
| network_used | bool | Always true for live capture |
| output_files | list[str] | Output file paths |
| notes | str | Free-text provenance note |

## Provenance Fields

Every snapshot record carries:

- `snapshot_id`: groups all records from the same capture run.
- `captured_at_utc`: ISO 8601 UTC timestamp of capture.
- `source`: identifies the API endpoint used.
- `adapter_version`: identifies the WP version that wrote the record (wp10).
- `read_only_provenance`: constant string "polymarket-strategy-lab/wp10-snapshot-persistence/public-get-only" confirming no trading authority.

## Write-Safety Rules

1. The snapshot writer must only write to directories containing `local_data` as a path component.
2. The writer must not write to `src/`, `tests/`, `docs/`, `audits/`, `tools/`, `.git/`, or the repo root.
3. Path validation is enforced by `_validate_output_path()` in `snapshot_writer.py`.
4. The `_allow_any_output_dir=True` parameter bypasses path validation. It is intended for tests using `pytest tmp_path` only.
5. The writer does not make network calls. It only reads data passed to it by the capture function.
6. The writer does not write credentials, tokens, private keys, wallet keys, mnemonics, or `.env` values.
7. Full raw API payloads are not stored. Only normalized fields and sorted field name lists are written.
8. The default output directory (`local_data/polymarket/snapshots/`) is git-ignored.
9. Snapshot files must never be committed to the repository.

## No Automated Polling

WP10 adds no scheduler, automated polling loop, bot loop, cron job, or repeated-request mechanism. Snapshot capture is manual-only, triggered by explicit CLI invocation with `--allow-network`. Each invocation captures one batch and exits.

## No Production Readiness Claim

WP10 snapshot persistence is research infrastructure only. It is not production-ready. The snapshot schema may change in later WPs. Snapshots written in WP10 may not be forward-compatible with future schema versions.

## Rate-Limit Constraint

Rate-limit policy for public Gamma and CLOB endpoints is not confirmed (WP8-D002 OPEN). A single low-volume WP9 probe returned no 429 responses, but this does not confirm sustained rate limits. WP10 snapshot capture must not be used for automated or frequent scanning until WP8-D002 is resolved. Default limits are conservative: `--markets-limit 3`, no order books by default.

## Deferred Item Impact

| Item | Status | Impact on WP10 |
|---|---|---|
| WP8-D001 | READY_FOR_WP | WP10 uses only the three confirmed endpoints |
| WP8-D002 | OPEN | Rate-limit policy unconfirmed; no automated polling added |
| WP9-D001 | OPEN | CLOB /health not used in WP10 |
| WP9-D002 | READY_FOR_WP | Snapshot capture uses updated parser; JSON-encoded fields handled correctly |
| WP10-D001 | OPEN | Snapshot schema not yet production-stable |
| WP10-D002 | OPEN | Snapshot output not yet database-backed |

## Future Transition To Database

WP10 uses JSONL files only. A future work package may migrate snapshots to a local database (e.g., SQLite) or a structured catalog. The snapshot record schema is designed to be stable enough to parse into a database table. Migration would require a separate approved work package with explicit scope, dependency audit, and schema mapping.

## WP11 Addendum — Snapshot Replay And Catalog

WP11 adds offline tooling that reads WP10 snapshot JSONL files and builds an in-memory market catalog:

- `src/data_layer/polymarket/snapshot_reader.py` — reads market metadata and order-book JSONL files and manifests.
- `src/data_layer/polymarket/market_catalog.py` — builds a normalized in-memory market catalog for offline research.
- `src/data_layer/polymarket/snapshot_replay.py` — offline replay/iteration helpers; deterministic and finite.
- `tools/polymarket/inspect_snapshot_catalog.py` — manual CLI inspection tool; offline-only, no `--allow-network` needed.

The WP11 replay/catalog layer is offline-only. It reads WP10 snapshot files. It does not call Polymarket APIs. It does not capture new network data. It does not create strategy signals. It does not create trade proposals. It does not place, cancel, sign, or simulate orders. It does not authenticate. It does not read credentials. It does not write outside ignored local paths. It is not a database, scheduler, bot loop, or production service.

WP10-D001 (snapshot schema not stable) and WP10-D002 (no database) remain OPEN. WP11 does not resolve either item. WP11-D001 (catalog not database-backed) and WP11-D002 (replay is inspection-only) are added in WP11.

## Next WP Recommendation

If WP10 succeeds and snapshots are verified as usable research data:

- **WP11 - Snapshot Replay And Normalized Market Catalog**: read snapshot JSONL files, build a local queryable market catalog, and add replay/inspection tooling for research use.

If WP10 output schema or safety issues remain unresolved:

- **WP11 - Snapshot Persistence Follow-Up**: address schema stability, test coverage gaps, or write-safety edge cases before proceeding to catalog or replay work.

## Safety Statement

This module:

- Performs public GET requests only, via the WP8/WP9 read-only adapter.
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Does not authenticate.
- Does not read credentials from environment, files, or any other source.
- Writes only to ignored local paths (`local_data/`) by default.
- Does not run continuously or schedule repeated requests.
- Uses Python standard library only.
- Is not production-ready.
- Must not be used for automated or frequent scanning until WP8-D002 is resolved.
