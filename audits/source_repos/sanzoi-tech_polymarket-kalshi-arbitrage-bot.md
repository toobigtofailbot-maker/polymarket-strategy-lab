# Source Repo Audit - sanzoI-tech/polymarket-kalshi-arbitrage-bot

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/sanzoI-tech/polymarket-kalshi-arbitrage-bot
- Local temporary path: audits/source_repos/tmp/sanzoi-tech_polymarket-kalshi-arbitrage-bot
- Default branch: main
- Audited commit: b472413c82060371c8b97b99ba9cfc0b308980a2
- Latest commit date: 2026-05-11T17:10:05+09:00
- Archived: false
- Stars/forks if available: 76/260
- Registry category: Cross-market bot

## Summary
TypeScript Polymarket/Kalshi bot has no license, private-key enabled trading, and no tests found. Avoid.

## License
- License file: None found
- SPDX / license name: NO_LICENSE
- Copying allowed: No copying until a license is identified.
- Attribution required: Unknown
- Copyleft concern: Unknown
- License conclusion: NO_LICENSE

## Stack And Runtime
- Language: TypeScript
- Frameworks: See package manifests and README in temporary clone.
- Package manifests: Inspected safe manifests in shallow clone.
- Runtime complexity: Application or bot repository.
- Services required: Polymarket/Kalshi network services depending on repo behavior.
- Build/test scripts observed: Manifest and workflow files inspected; no untrusted build, install, or test commands from external repos were run.

## Polymarket / Kalshi API Compatibility
- Uses Polymarket: YES
- Uses Kalshi: YES
- API version: Compatibility requires future validation.
- V2 CLOB compatible: UNCLEAR
- Relayer usage: Not primary or unclear.
- WebSocket usage: NO or not primary in shallow scan
- Market data handling: README/source structure inspected for market data, order book, event, or strategy surfaces.
- Fee/tick/min-size handling: Not fully validated; must be rechecked before reuse.
- Known API risks: TypeScript Polymarket/Kalshi bot has no license, private-key enabled trading, and no tests found. Avoid.

## Trading And Execution Behavior
- Places live trades: YES
- Cancels orders: YES/UNCLEAR depending on repo-specific paths.
- Signs orders: YES/UNCLEAR
- Requires private keys: YES/UNCLEAR
- Has paper/simulation mode: NO or not observed
- Has live-mode gate: NO/UNCLEAR
- Has kill-switch: NO project-compatible kill-switch observed.
- Has risk limits: No project-compatible risk limits observed.
- Execution conclusion: No external execution path is approved by WP2.

## Strategy Area
- Market-making: NO
- Arbitrage: YES
- Wallet tracking: NO
- Copy-trading: NO
- BTC short-duration markets: YES/UNCLEAR
- Related-market / LLM: NO
- Analytics / ingestion: NO
- Other: Cross-market bot

## Security Findings
- Secret-like strings: Environment variable references and placeholders were summarized; no production credential was copied into this report.
- Secret handling: Private key/API credential handling observed or likely.
- Dependency concerns: Dependency audit NOT RUN - TOOL UNAVAILABLE.
- Dangerous scripts: Live order, signing, wallet, relayer, or transaction scripts observed; none were run.
- Network/service assumptions: External API/RPC/WebSocket use requires future review.
- Static scan results: gitleaks NOT RUN - TOOL UNAVAILABLE; semgrep NOT RUN - TOOL UNAVAILABLE.
- Security conclusion: High risk for reuse.

## Test And Quality Findings
- Test files: No substantive tests found or quality unclear in shallow scan.
- CI: Workflow files observed for some repos; no external CI was run.
- Documentation quality: README/docs inspected at a due-diligence level.
- Code organization: Bot/application-oriented; not directly aligned to this repo runtime.
- Error handling: Not exhaustively audited.
- Observability/logging: Not exhaustively audited.
- Maintainability: Based on archive flag, recent commit, tests, and repo shape.

## Useful Patterns
Study only the documented concepts and interface ideas named in the summary. Do not copy source code.

## Risks And Limitations
Findings are based on shallow clone metadata and static inspection. Optional scanners and dependency audits were unavailable.

## Reuse Recommendation
AVOID

## Rationale
TypeScript Polymarket/Kalshi bot has no license, private-key enabled trading, and no tests found. Avoid.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; AVOID; NO_LICENSE; live trading logic YES.
