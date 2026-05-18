# Strategy Module Registry

No module is started. Live trading is not allowed for any module until explicitly authorized in `docs/live_trading_authorization.md`.

| Module | Objective | Status | Live trading allowed? | Dependencies | Repo references to audit later |
|---|---|---|---|---|---|
| Market scanner | Discover candidate markets and anomalies. | NOT STARTED | No, until explicitly authorized | Market data source | Official clients |
| Wallet intelligence | Track public wallet behavior and features. | NOT STARTED | No, until explicitly authorized | Public permitted wallet data | Third-party wallet tools if found later |
| Smart-wallet scoring | Score wallets using public data only. | NOT STARTED | No, until explicitly authorized | Wallet intelligence | None yet |
| Copy-trading paper/live-gated module | Convert eligible wallet events into gated proposals. | NOT STARTED | No, until explicitly authorized | Wallet score, risk engine | Bot repos in registry |
| YES/NO arbitrage scanner | Detect same-market YES/NO pricing anomalies. | NOT STARTED | No, until explicitly authorized | Market data | Official clients, bot repos |
| Gabagool / hedged arbitrage scanner | Detect hedged multi-leg opportunities. | NOT STARTED | No, until explicitly authorized | Market data, risk model | Bot repos |
| Related-market / duplicate-market scanner | Find overlapping markets and duplicate exposure. | NOT STARTED | No, until explicitly authorized | Market metadata | Cross-market bot repos |
| Polymarket-Kalshi cross-market arbitrage scanner | Compare related markets across venues. | NOT STARTED | No, until explicitly authorized | Polymarket and Kalshi data | Cross-market bot repos |
| Market-making module | Propose maker quotes under inventory limits. | NOT STARTED | No, until explicitly authorized | Order book data, risk engine | Polymarket market-maker repos |
| Dashboard/monitoring | Show mode, risk, proposals, tests, and status. | NOT STARTED | No, until explicitly authorized | Streamlit likely | None yet |
| Paper-trading engine | Simulate fills and PnL. | NOT STARTED | No, until explicitly authorized | Data semantics, simulator | None yet |
| Risk engine | Deterministically approve or reject proposals. | NOT STARTED | No, until explicitly authorized | Risk semantics | None yet |
| Execution gateway | Execute approved orders only in authorized modes. | NOT STARTED | No, until explicitly authorized | Risk engine, credentials later | Official clients |
| AI/Hermes monitoring/reporting assistant | Summarize research, monitoring, and status. | NOT STARTED | No, until explicitly authorized | Logs and read-only data | None yet |

