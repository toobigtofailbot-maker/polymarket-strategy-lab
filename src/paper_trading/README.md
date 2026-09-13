# WP173 Serious Paper Trading Runtime

This package implements deterministic simulated-paper orders, hard pre-order paper
risk, exact spot-token accounting, an append-only SQLite journal, restart
reconciliation, finite replay, and a manually launched foreground reader over an
explicit local WP169 store.

It has simulated-paper authority only. It contains no credential, signing,
authenticated client, real order, paper-to-live fallback, or live-trading path. The
WP169 input is opened with SQLite `mode=ro`; WP170/WP172 evidence is validated and
bound but never modified. See `docs/serious_paper_trading_contract.md`.
