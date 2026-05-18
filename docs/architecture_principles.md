# Architecture Principles

- Build a modular platform, not a monolithic bot.
- Use shared data, risk, and execution layers across strategies.
- Strategy modules produce `TradeProposal` objects only.
- The risk engine approves or rejects proposals deterministically.
- The execution gateway places or cancels orders only after risk approval.
- Maintain strict read-only, paper, and live mode separation.
- Live mode must require explicit authorization, visible controls, tested kill-switches, and bounded risk.
- TypeScript is likely preferred for the live execution gateway pending WP2 and architecture decisions.
- Python is likely preferred for research, wallet analytics, Streamlit dashboards, and batch jobs pending final architecture decision.
- Rust and Java repositories are to be studied first, not adopted in MVP core without explicit decision.

