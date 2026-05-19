# Runtime Boundaries

## Purpose

Runtime boundaries protect safety-critical execution, risk, credentials, and mode separation. WP3 documents these boundaries only and does not implement runtime behavior.

## Protected Boundaries

- Strategies must not import venue clients directly.
- Strategies cannot place orders directly.
- Strategies must not submit, sign, cancel, reconcile, or route real orders.
- Strategies must not read secrets, private keys, wallet keys, API credentials, passphrases, tokens, or mnemonic material.
- AI, Hermes, and Codex components cannot override risk decisions.
- API clients must sit behind internal adapters in future work packages.
- External repo code cannot become runtime code unless explicitly promoted in a future approved work package after license, security, and compatibility review.
- Live execution requires explicit live authorization, deterministic risk approval, execution gateway controls, and tested safety mechanisms.

## WP3 Boundary State

- No runtime execution exists.
- No order management system exists.
- No reconciliation path exists.
- No risk-cap implementation exists.
- No venue API integration exists.
- No live-trading path exists.

## WP8 Boundary Update

WP8 adds a strictly read-only public data adapter under `src/data_layer/polymarket/`. This adapter:

- Performs public GET requests only.
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Uses Python standard library only.
- Is the only approved executable source in `src/` as of WP8.
- Does not change the status of the execution gateway, risk engine, or paper-trading engine (all remain absent).
- Strategies must not import this adapter directly; data access must flow through approved data-layer boundaries.

All other boundaries from WP3 remain in effect.

## WP10 Boundary Update

WP10 adds local file-based snapshot persistence under `src/data_layer/polymarket/`. This persistence layer:

- Reads public market data via the WP8/WP9 read-only adapter (GET-only).
- Writes normalized JSONL records and JSON manifests to `local_data/polymarket/snapshots/` only.
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Does not authenticate.
- Does not read credentials from any source.
- Uses Python standard library only.
- Is not a database, scheduler, or bot loop.
- Does not run continuously or schedule repeated requests.

`local_data/` is git-ignored. Snapshot files must never be committed.

All boundaries from WP3 and WP8 remain in effect.

## WP11 Boundary Update

WP11 adds offline snapshot replay and normalized market catalog under `src/data_layer/polymarket/`. This layer:

- Reads local JSONL snapshot files produced by WP10 snapshot capture.
- Builds an in-memory market catalog for offline research and inspection.
- Provides deterministic finite replay iterators over snapshot records.
- Provides a manual CLI inspection tool (no `--allow-network` required).
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Does not authenticate.
- Does not read credentials from any source.
- Does not make network calls.
- Uses Python standard library only.
- Is not a database, scheduler, or bot loop.
- Does not run continuously or schedule repeated requests.
- Optional catalog summary output goes to git-ignored `local_data/polymarket/catalog/` only.

All boundaries from WP3, WP8, and WP10 remain in effect.

## WP12 Boundary Update

WP12 adds offline snapshot quality gates and local research reports under `src/data_layer/polymarket/` and `tools/polymarket/`. This layer:

- Reads local JSONL snapshot files and manifests produced by WP10 and loaded by WP11 tooling.
- Builds quality summaries and sanitized local reports for offline research inspection.
- Writes reports only when explicitly requested and only under git-ignored `local_data/polymarket/reports/`.
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Does not authenticate.
- Does not read credentials from any source.
- Does not make network calls.
- Uses Python standard library only.
- Is not a strategy module, backtest, paper-trading engine, database, scheduler, bot loop, execution system, or production service.

All boundaries from WP3, WP8, WP10, and WP11 remain in effect.

## WP13 Boundary Update

WP13 adds offline snapshot deduplication and sanitized local catalog exports under `src/data_layer/polymarket/` and `tools/polymarket/`. This layer:

- Reads local JSONL snapshot files and in-memory catalog data produced by WP10/WP11/WP12 tooling.
- Deduplicates local market and order-book snapshot records deterministically.
- Reports conflicting records instead of silently merging them.
- Writes catalog exports only when explicitly requested and only under git-ignored `local_data/polymarket/exports/`.
- Has no order-placement authority.
- Has no wallet or private-key authority.
- Has no live-trading path.
- Does not authenticate.
- Does not read credentials from any source.
- Does not make network calls.
- Uses Python standard library only.
- Is not a strategy module, backtest, paper-trading engine, database, scheduler, bot loop, execution system, monitoring service, or production service.

All boundaries from WP3, WP8, WP10, WP11, and WP12 remain in effect.
