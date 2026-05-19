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
