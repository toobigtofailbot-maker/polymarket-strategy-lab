# Project Charter

## Objective

Build a repo-first Polymarket and Kalshi strategy lab that can evaluate, simulate, and eventually operate deterministic trading systems under strict governance and risk controls.

## Scope

- Source-repo due diligence before reuse.
- Research workflows for markets, wallets, strategy candidates, and execution design.
- Deterministic strategy, risk, paper-trading, monitoring, and execution architecture in future WPs.
- Repo-truth documentation and tests that prevent unsafe defaults.

## Non-Goals

- No monolithic magic bot.
- No live trading in WP1.
- No API integration in WP1.
- No external repo cloning, copying, vendoring, or audit in WP1.
- No strategy implementation in WP1.

## Risk Posture

Profitability is unproven and must be measured. Initial live capital, if later authorized, is expected to be 100-1,000 USD. The target daily loss limit is 10 percent of allocated live capital.

## Strategy Areas

Potential future areas include market scanning, market-making, YES/NO arbitrage, hedged arbitrage, cross-market arbitrage, wallet tracking, smart-wallet scoring, controlled copy-trading, dashboarding, monitoring, alerts, and deterministic risk/execution gateways.

## Build Philosophy

Repo truth comes before implementation. Existing source repositories must be audited before reuse. Governance, project memory, and safety gates must exist before code that can affect trading decisions.

## Deterministic Risk And Execution

Strategy modules may propose trades only. Risk approval and execution must be deterministic. AI, Hermes, and Codex cannot override risk decisions or directly place live trades.

## AI, Hermes, And Codex

AI-assisted tools may support research, monitoring, reporting, summaries, and code generation. They must not hold authority to bypass risk controls or execute live trades.

## Dashboard And Deployment Preferences

Streamlit is preferred first for dashboards. The user is currently in Mexico.

Production hosting direction (S10-DEPLOY-PLAN-01, APPROVED_PLANNING_DIRECTION, NOT_PROVISIONED / NOT_DEPLOYED): AlphaVPS, Sofia, Bulgaria; initial tier C8G (4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10); Ubuntu 24.04 LTS / x86-64; ONE consolidated Polymarket VPS with no default separate research/live VPS; upgrades C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence. The future implementation package S10-DEPLOY-01 (Production VPS Runtime Baseline) is NOT AUTHORIZED. See `docs/production_vps_hosting_direction.md`. This supersedes the earlier charter statement that VPS and cloud choices remained open; jurisdiction, geoblocking, latency, reliability, and operational fit remain verification concerns for S10-DEPLOY-01. No purchase, provisioning, deployment, paper, live, or capital authority is granted.

