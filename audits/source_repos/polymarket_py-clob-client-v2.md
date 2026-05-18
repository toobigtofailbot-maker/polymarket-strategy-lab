# Source Repo Audit - Polymarket/py-clob-client-v2

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/Polymarket/py-clob-client-v2
- Local temporary path: audits/source_repos/tmp/polymarket_py-clob-client-v2
- Default branch: main
- Audited commit: 394ecc18ab9ab20b48095b0b5c5de0042bdd6bb3
- Latest commit date: 2026-05-07T15:27:04+05:30
- Archived: false
- Stars/forks if available: 112/35
- Registry category: Official client

## Summary
Official current V2 Python CLOB client with pytest coverage for signing, headers, fee/slippage and order construction. Strongest Python dependency candidate after pinning and audit.

## License
- License file: LICENSE
- SPDX / license name: MIT
- Copying allowed: Permissive license appears present, but WP2 approves no copying.
- Attribution required: Yes
- Copyleft concern: No
- License conclusion: MIT

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
- API version: Current V2 CLOB observed.
- V2 CLOB compatible: YES
- Relayer usage: Some builder/relayer-related surfaces observed.
- WebSocket usage: YES/observed
- Market data handling: README/source structure inspected for market data, order book, event, or strategy surfaces.
- Fee/tick/min-size handling: Fee/tick/order sizing helpers and tests observed.
- Known API risks: Official current V2 Python CLOB client with pytest coverage for signing, headers, fee/slippage and order construction. Strongest Python dependency candidate after pinning and audit.

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
- Dangerous scripts: Live order, signing, wallet, relayer, or transaction scripts observed; none were run.
- Network/service assumptions: External API/RPC/WebSocket use requires future review.
- Static scan results: gitleaks NOT RUN - TOOL UNAVAILABLE; semgrep NOT RUN - TOOL UNAVAILABLE.
- Security conclusion: Moderate until dependency and signer review.

## Test And Quality Findings
- Test files: Tests observed.
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
CORE_DEPENDENCY_CANDIDATE

## Rationale
Official current V2 Python CLOB client with pytest coverage for signing, headers, fee/slippage and order construction. Strongest Python dependency candidate after pinning and audit.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; CORE_DEPENDENCY_CANDIDATE; MIT; live trading logic YES.
