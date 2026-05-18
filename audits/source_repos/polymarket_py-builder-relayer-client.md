# Source Repo Audit - Polymarket/py-builder-relayer-client

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/Polymarket/py-builder-relayer-client
- Local temporary path: audits/source_repos/tmp/polymarket_py-builder-relayer-client
- Default branch: main
- Audited commit: 6589f36740a2a98736f5b0499f29d2d234c583bc
- Latest commit date: 2026-05-02T02:26:35+05:30
- Archived: false
- Stars/forks if available: 38/16
- Registry category: Official client

## Summary
Official Python relayer client has no license file and exposes private-key/relayer transaction flows. Study only pending license and protected-boundary approval.

## License
- License file: None found
- SPDX / license name: NO_LICENSE
- Copying allowed: No copying until a license is identified.
- Attribution required: Unknown
- Copyleft concern: Unknown
- License conclusion: NO_LICENSE

## Stack And Runtime
- Language: Python
- Frameworks: See package manifests and README in temporary clone.
- Package manifests: Inspected safe manifests in shallow clone.
- Runtime complexity: Library/client package.
- Services required: Polymarket network services depending on repo behavior.
- Build/test scripts observed: Manifest and workflow files inspected; no untrusted build, install, or test commands from external repos were run.

## Polymarket / Kalshi API Compatibility
- Uses Polymarket: YES
- Uses Kalshi: NO
- API version: Compatibility requires future validation.
- V2 CLOB compatible: N/A
- Relayer usage: YES - primary repo purpose.
- WebSocket usage: NO or not primary in shallow scan
- Market data handling: README/source structure inspected for market data, order book, event, or strategy surfaces.
- Fee/tick/min-size handling: Not fully validated; must be rechecked before reuse.
- Known API risks: Official Python relayer client has no license file and exposes private-key/relayer transaction flows. Study only pending license and protected-boundary approval.

## Trading And Execution Behavior
- Places live trades: UNCLEAR
- Cancels orders: NO/UNCLEAR
- Signs orders: YES/UNCLEAR
- Requires private keys: YES/UNCLEAR
- Has paper/simulation mode: NO or not observed
- Has live-mode gate: NO/UNCLEAR
- Has kill-switch: NO project-compatible kill-switch observed.
- Has risk limits: No project-compatible risk limits observed.
- Execution conclusion: No external execution path is approved by WP2.

## Strategy Area
- Market-making: NO
- Arbitrage: NO
- Wallet tracking: NO
- Copy-trading: NO
- BTC short-duration markets: NO
- Related-market / LLM: NO
- Analytics / ingestion: NO
- Other: Official client

## Security Findings
- Secret-like strings: Environment variable references and placeholders were summarized; no production credential was copied into this report.
- Secret handling: Private key/API credential handling observed or likely.
- Dependency concerns: Dependency audit NOT RUN - TOOL UNAVAILABLE.
- Dangerous scripts: No live order script observed in shallow scan; app scripts were not run.
- Network/service assumptions: External API/RPC/WebSocket use requires future review.
- Static scan results: gitleaks NOT RUN - TOOL UNAVAILABLE; semgrep NOT RUN - TOOL UNAVAILABLE.
- Security conclusion: High risk for reuse.

## Test And Quality Findings
- Test files: No substantive tests found or quality unclear in shallow scan.
- CI: Workflow files observed for some repos; no external CI was run.
- Documentation quality: README/docs inspected at a due-diligence level.
- Code organization: Client/library-oriented.
- Error handling: Not exhaustively audited.
- Observability/logging: Not exhaustively audited.
- Maintainability: Based on archive flag, recent commit, tests, and repo shape.

## Useful Patterns
Study only the documented concepts and interface ideas named in the summary. Do not copy source code.

## Risks And Limitations
Findings are based on shallow clone metadata and static inspection. Optional scanners and dependency audits were unavailable.

## Reuse Recommendation
STUDY_ONLY

## Rationale
Official Python relayer client has no license file and exposes private-key/relayer transaction flows. Study only pending license and protected-boundary approval.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; STUDY_ONLY; NO_LICENSE; live trading logic UNCLEAR.
