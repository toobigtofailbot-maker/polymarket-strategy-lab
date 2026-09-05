# Polymarket Read-Only Public Data Adapter

## Status

**READ-ONLY PUBLIC DATA ONLY**

## What This Module Does

This module provides a GET-only interface to public Polymarket market metadata and order-book data. It uses Python standard library only (`urllib`, `json`).

## What This Module Must Never Do

- Send POST, PUT, PATCH, or DELETE requests.
- Read or use credentials, private keys, wallet keys, API tokens, mnemonics, or passphrases.
- Place, sign, or cancel orders.
- Execute trades, buy, or sell.
- Connect to authenticated Polymarket API endpoints.
- Start background loops or scheduled polling.
- Grant live mode to any downstream component.

## No Trading Authority

This module is a data observation layer. It has no order-placement authority, no wallet authority, and no live-trading authority. Future order execution must go through the deterministic risk engine and execution gateway only, after explicit human authorization in `docs/live_trading_authorization.md`.

## Endpoint Contract Status

All endpoints are marked **UNVERIFIED** in WP8. The endpoint paths are derived from public documentation and the WP2 audit of official Polymarket client repos. No claim of production-readiness is made. Endpoint contracts must be confirmed before this adapter is used in automated production workflows.

## Configurable Base URLs

Both the Gamma API base URL and the CLOB API base URL are constructor parameters. Tests use fake base URLs. The smoke test uses the public defaults.

## Usage

```python
from src.data_layer.polymarket import PolymarketPublicClient

client = PolymarketPublicClient()  # uses public defaults
result = client.get_markets(limit=5)
print(result.data)
```

## Dependencies

Python standard library only. No third-party packages.

## WP8 Evaluation Scope

See `docs/polymarket_readonly_adapter_evaluation.md` for the full decision record.

## WP169 — Public Market Truth / Realtime Data Plane

WP169 adds a native public market-truth plane in this package (`market_truth.py`,
`market_truth_store.py`, `market_truth_websocket.py`, `market_truth_data_api.py`,
`market_truth_onchain.py`, `market_truth_runtime.py`) plus the manual CLI
`tools/polymarket/run_public_market_truth.py`. It preserves exact raw bytes before
normalization, normalizes supported Market WebSocket events deterministically without
floats, reconstructs per-asset order books with disconnect/regression/hash-conflict gap
handling healed only by a fresh full snapshot, persists append-only raw/normalized/session/
gap/checkpoint evidence in bounded local SQLite, collects public unauthenticated
Data/Gamma/CLOB GET pages with closed Retry-After handling, decodes public Polygon V2
OrderFilled logs with confirmation and reorg handling, and promotes only eligible accepted
observations through the existing canonical point-in-time record builder.

It adds exactly `websockets==17.1` (BSD-3-Clause; install-not-vendor). It uses public
unauthenticated network only, holds no credentials, and grants no order, OMS, signing,
strategy, paper, live, Hermes, dashboard, or scheduler authority. There is no import-time
network, thread, process, scheduler, or file side effect; the runtime is a manual foreground
process with a caller-supplied bounded duration or explicit stop event. See
`docs/public_market_truth_realtime_data_plane_contract.md` for the full contract.
