# `src/research_runtime/`

Research-runtime boundary: local, offline, event-driven replay/runtime capabilities that
**consume** the canonical data layer but are architecturally distinct from it. Unlike
`src/data_layer/` (which owns canonical point-in-time truth, provenance, and analytical
dataset identity), `src/research_runtime/` hosts derived research runtime state produced by
adopted third-party engines.

This boundary is README-only except for the explicitly approved package(s) below.

## Approved packages

- `nautilus_offline/` (WP168) — NautilusTrader offline kernel, `ParquetDataCatalog`
  adoption, and deterministic offline replay over verified WP167 pmxt-v2 external history.
  Local/offline only. No live data client, no execution client, no authenticated Polymarket
  client, no credentials, no WebSocket/Data API, no scheduler, no strategy/alpha, no
  order/fill/paper/live authority. Canonical WP167/PIT truth is read-only; the Nautilus
  catalog/replay output is derived research runtime state, never canonical. See
  [`docs/nautilus_offline_kernel_contract.md`](../../docs/nautilus_offline_kernel_contract.md).
