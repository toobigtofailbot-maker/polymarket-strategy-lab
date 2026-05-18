# Source Repo Audit - chainstacklabs/polymarket-alpha-bot

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/chainstacklabs/polymarket-alpha-bot
- Local temporary path: audits/source_repos/tmp/chainstacklabs_polymarket-alpha-bot
- Default branch: main
- Audited commit: a92af744469696527902986edfcae7cd26c122f5
- Latest commit date: 2026-04-28T18:00:25+02:00
- Archived: false
- Stars/forks if available: 151/32
- Registry category: Related-market / alpha research

## Summary
Research/alpha app using py-clob-client-v2 with token/websocket tests, but includes wallet/trading experiments and OpenRouter dependencies. Clean-room adaptation only.

## License
- License file: LICENSE
- SPDX / license name: Apache-2.0
- Copying allowed: Permissive license appears present, but WP2 approves no copying.
- Attribution required: Yes
- Copyleft concern: No copyleft, but notice and patent terms apply.
- License conclusion: Apache-2.0

## Stack And Runtime
- Language: Python/TypeScript
- Frameworks: See package manifests and README in temporary clone.
- Package manifests: Inspected safe manifests in shallow clone.
- Runtime complexity: Application or bot repository.
- Services required: Polymarket network services depending on repo behavior.
- Build/test scripts observed: Manifest and workflow files inspected; no untrusted build, install, or test commands from external repos were run.

## Polymarket / Kalshi API Compatibility
- Uses Polymarket: YES
- Uses Kalshi: NO
- API version: Current V2 CLOB observed.
- V2 CLOB compatible: YES
- Relayer usage: Not primary or unclear.
- WebSocket usage: YES/observed
- Market data handling: README/source structure inspected for market data, order book, event, or strategy surfaces.
- Fee/tick/min-size handling: Not fully validated; must be rechecked before reuse.
- Known API risks: Research/alpha app using py-clob-client-v2 with token/websocket tests, but includes wallet/trading experiments and OpenRouter dependencies. Clean-room adaptation only.

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
- Wallet tracking: YES/UNCLEAR
- Copy-trading: NO
- BTC short-duration markets: NO
- Related-market / LLM: YES
- Analytics / ingestion: YES
- Other: Related-market / alpha research

## Security Findings
- Secret-like strings: Environment variable references and placeholders were summarized; no production credential was copied into this report.
- Secret handling: Private key/API credential handling observed or likely.
- Dependency concerns: Dependency audit NOT RUN - TOOL UNAVAILABLE.
- Dangerous scripts: Live order, signing, wallet, relayer, or transaction scripts observed; none were run.
- Network/service assumptions: External API/RPC/WebSocket use requires future review.
- Static scan results: gitleaks NOT RUN - TOOL UNAVAILABLE; semgrep NOT RUN - TOOL UNAVAILABLE.
- Security conclusion: Conservative study-only or clean-room posture required.

## Test And Quality Findings
- Test files: Tests observed.
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
CLEAN_ROOM_ADAPTATION

## Rationale
Research/alpha app using py-clob-client-v2 with token/websocket tests, but includes wallet/trading experiments and OpenRouter dependencies. Clean-room adaptation only.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; CLEAN_ROOM_ADAPTATION; Apache-2.0; live trading logic YES.
