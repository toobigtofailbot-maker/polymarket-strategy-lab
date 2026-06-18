# Protected Paths And Boundaries

This document is the central boundary source for all WPs. Future WPs must reference this document rather than repeating inconsistent forbidden lists.

Each boundary group below defines a protected mode. Crossing a boundary requires an explicit authorization gate in the active WP. A doc mentioning a boundary group does not authorize crossing it.

Codex, Claude Code, and all AI coding agents must stop and escalate before touching these areas unless the active work package explicitly authorizes them:

- Live trading paths and live authorization.
- Credentials, secrets, `.env` loading, private keys, wallet keys, mnemonics, passphrases, tokens, and authenticated headers.
- Authenticated clients, private endpoints, account queries, private trade queries, and private order queries.
- Order, execution, signing, submission, cancellation, OMS, reconciliation, risk caps, risk engine, and execution gateway paths.
- Scheduler, daemon, service loop, background worker, bot loop, retry loop, `while True`, and `time.sleep` runtime behavior.
- Database, dashboard, deployment, production service, or monitoring stack paths.
- Runtime dependencies, development dependencies, package manager files, and lock files.
- Official-client runtime integration or imports under `src/`.
- External copied code, vendored code, or unaudited external repo reuse.
- Generated artifacts, `local_data/`, local virtual environments, security-tool outputs, `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, `security-scan-output/`, `.venv-official-client/`, and `official-client-sandbox-output/`.

Workflow docs and templates may mention protected behavior to forbid it. Mentioning a protected path does not authorize implementation.

## Specific Protected File Examples

The following files are protected from workflow-governance WPs:
- `src/data_layer/market_research_priority_scoring.py`
- `src/data_layer/market_research_priority_features.py`
- `src/data_layer/resolution_ambiguity_labels.py`

The following directories are protected unless explicit product/tooling WP:
- `tools/polymarket/` — Polymarket-specific tooling
- `tools/advisory/` — advisory tooling
- `tools/agent/` — agent tooling
- `tools/validation/` — validation tooling

The following are always protected:
- `local_data/` — generated/local-output only, never committed
- `requirements.txt`, `pyproject.toml`, `package.json`, lock files — dependency files
- `.env`, `.env.*`, key files, wallet files, credential files — secret files

Note: `tools/git/posted_pr_evidence_verifier.py` is allowed in WP58 only because it is explicitly scoped as a workflow-governance helper.

## Centralized Boundary Group Reference

Every WP must verify it does not cross any of the following boundary groups. Reference this list in the WP's Authority / Non-Authority Posture section instead of repeating a partial list:

| Boundary Group | Scope | Authorization Gate |
|---|---|---|
| credentials/secrets | `.env`, private keys, API tokens, wallet keys, mnemonics, passphrases | Credential/auth WP explicitly authorized with user approval |
| authenticated clients | L1/L2 clients, private endpoints, account queries, private order queries | Credential boundary WP must first complete |
| wallet/account behavior | wallet reads, account queries, balance checks via authenticated path | Authenticated client WP must first complete |
| order placement/cancel | order submission, cancellation, OMS, reconciliation | Execution WP explicitly authorized; live trading auth doc updated |
| execution gateway | risk caps, risk engine, kill switch, signing, submission | Execution WP with strongest safety gates |
| paper engine | paper order model, paper fill model, paper PnL, paper portfolio ledger | Paper WP explicitly authorized with mode separation proof |
| scheduler/bot loop | `while True`, `time.sleep`, daemon, service loop, background worker, retry loop | Scheduler WP with rate-limit evidence, kill switch, observability |
| runtime/daemon | production service, bot loop, polling daemon | Runtime WP explicitly authorized |
| dashboard/deployment | Streamlit, Grafana, monitoring stack, production deployment | Dashboard WP explicitly authorized |
| dependency/lock changes | `requirements.txt`, `pyproject.toml`, `package.json`, lock files | Dependency WP with security audit |
| external code copying | vendored code, copied source from external repo | License/security audit required before copy |
| generated artifacts | `local_data/`, `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, `security-scan-output/`, `.venv-official-client/`, `official-client-sandbox-output/` | Never committed; must be in `.gitignore` |

WPs must cite this table's boundary group names in their Authority / Non-Authority Posture section to confirm which boundaries are not crossed.
