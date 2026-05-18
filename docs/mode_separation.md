# Mode Separation

## Purpose

Mode separation prevents accidental escalation from research, read-only, or paper behavior into live trading. WP3 documents mode boundaries only.

## Modes

| Mode | Purpose | Order authority |
|---|---|---|
| historical | Uses stored or historical data for research and analysis. | None. |
| live-read-only | Observes current market or wallet data without order placement. | None. |
| paper | Simulates orders and portfolio behavior without touching real venues. | Simulated only. |
| live | Places or cancels real orders after authorization and risk approval. | Disabled until explicitly authorized. |

## Rules

- Live-read-only may observe data but not place orders.
- Paper may simulate but not place real orders.
- Live is disabled until `docs/live_trading_authorization.md` is explicitly updated in a future approved work package.
- No fallback from paper to live is allowed.
- No config value may enable live by default.
- No strategy, monitoring process, AI assistant, Hermes component, or Codex-generated module may bypass deterministic risk approval.
