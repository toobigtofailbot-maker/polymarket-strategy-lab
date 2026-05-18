# Source Repo Audit - MrFadiAi/Polymarket-bot

## Audit Metadata
- Audit date: 2026-05-18
- Auditor: Codex
- Repo URL: https://github.com/MrFadiAi/Polymarket-bot
- Local temporary path: audits/source_repos/tmp/mrfadiai_polymarket-bot
- Default branch: main
- Audited commit: 82647014e0c355a5684e09666d8a0a522234640d
- Latest commit date: 2026-01-11T23:28:19+01:00
- Archived: false
- Stars/forks if available: 43/16
- Registry category: Third-party bot

## Summary
Broad SDK/bot/dashboard repo with dry-run/private-key trading references, many examples, and unclear V2 parity. Study only.

## License
- License file: LICENSE
- SPDX / license name: MIT
- Copying allowed: Permissive license appears present, but WP2 approves no copying.
- Attribution required: Yes
- Copyleft concern: No
- License conclusion: MIT

## Stack And Runtime
- Language: TypeScript
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
- Known API risks: Broad SDK/bot/dashboard repo with dry-run/private-key trading references, many examples, and unclear V2 parity. Study only.

## Trading And Execution Behavior
- Places live trades: UNCLEAR
- Cancels orders: NO/UNCLEAR
- Signs orders: YES/UNCLEAR
- Requires private keys: YES/UNCLEAR
- Has paper/simulation mode: YES/claimed or scripts observed
- Has live-mode gate: YES/UNCLEAR, not project-approved
- Has kill-switch: NO project-compatible kill-switch observed.
- Has risk limits: No project-compatible risk limits observed.
- Execution conclusion: No external execution path is approved by WP2.

## Strategy Area
- Market-making: NO
- Arbitrage: NO
- Wallet tracking: YES/UNCLEAR
- Copy-trading: YES/UNCLEAR
- BTC short-duration markets: NO
- Related-market / LLM: NO
- Analytics / ingestion: NO
- Other: Third-party bot

## Security Findings
- Secret-like strings: Environment variable references and placeholders were summarized; no production credential was copied into this report.
- Secret handling: Private key/API credential handling observed or likely.
- Dependency concerns: Dependency audit NOT RUN - TOOL UNAVAILABLE.
- Dangerous scripts: No live order script observed in shallow scan; app scripts were not run.
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
Broad SDK/bot/dashboard repo with dry-run/private-key trading references, many examples, and unclear V2 parity. Study only.

## Required Follow-Up
Before any future use: revalidate license, run dependency/security audits, pin versions, verify API compatibility, and require an approved WP for any runtime integration.

## Final Decision For Registry
AUDITED; STUDY_ONLY; MIT; live trading logic UNCLEAR.
