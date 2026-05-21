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
