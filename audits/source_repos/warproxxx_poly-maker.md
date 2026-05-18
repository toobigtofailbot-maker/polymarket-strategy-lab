# Source Repo Audit - warproxxx/poly-maker

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/warproxxx/poly-maker
- Local temporary path: audits/source_repos/tmp/warproxxx_poly-maker
- Default branch: main
- Audited commit: bfacef317b4bdffba1dac28fb3ae44387fec517f
- Latest commit date: 2026-04-06T13:54:51-04:00
- Archived: false
- Stars/forks if available: 1159/429
- Registry category: Third-party bot

## Summary
Popular third-party market maker with websocket, Google Sheets config, post_order/create_order and private-key signing. No tests found; study only.

## License
- License file: LICENSE
- SPDX / license name: MIT
- Copying allowed: Permissive license appears present, but WP2 approves no copying.
- Attribution required: Yes
- Copyleft concern: No
- License conclusion: MIT

## Stack And Runtime
- Language: Python/Node
- Frameworks: See package manifests and README in temporary clone.
- Package manifests: Inspected safe manifests in shallow clone.
- Runtime complexity: Application or bot repository.
- Services required: Polymarket network services depending on repo behavior.
- Build/test scripts observed: Manifest and workflow files inspected; no untrusted build, install, or test commands from external repos were run.

## Polymarket / Kalshi API Compatibility
- Uses Polymarket: YES
- Uses Kalshi: NO
- API version: Compatibility requires future validation.
- V2 CLOB compatible: UNCLEAR
- Relayer usage: Not primary or unclear.
- WebSocket usage: YES/observed
- Market data handling: README/source structure inspected for market data, order book, event, or strategy surfaces.
- Fee/tick/min-size handling: Not fully validated; must be rechecked before reuse.
- Known API risks: Popular third-party market maker with websocket, Google Sheets config, post_order/create_order and private-key signing. No tests found; study only.

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
- Market-making: YES
- Arbitrage: NO
- Wallet tracking: NO
- Copy-trading: NO
- BTC short-duration markets: NO
- Related-market / LLM: NO
- Analytics / ingestion: NO
- Other: Third-party bot

## Security Findings
- Secret-like strings: Environment variable references and placeholders were summarized; no production credential was copied into this report.
- Secret handling: Private key/API credential handling observed or likely.
- Dependency concerns: Dependency audit NOT RUN - TOOL UNAVAILABLE.
- Dangerous scripts: Live order, signing, wallet, relayer, or transaction scripts observed; none were run.
- Network/service assumptions: External API/RPC/WebSocket use requires future review.
- Static scan results: gitleaks NOT RUN - TOOL UNAVAILABLE; semgrep NOT RUN - TOOL UNAVAILABLE.
- Security conclusion: Conservative study-only or clean-room posture required.

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
STUDY_ONLY

## Rationale
Popular third-party market maker with websocket, Google Sheets config, post_order/create_order and private-key signing. No tests found; study only.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; STUDY_ONLY; MIT; live trading logic YES.
