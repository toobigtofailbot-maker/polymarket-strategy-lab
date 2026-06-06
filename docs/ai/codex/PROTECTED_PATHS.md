# Protected Paths And Boundaries

Codex must stop and escalate before touching these areas unless the active work package explicitly authorizes them:

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
