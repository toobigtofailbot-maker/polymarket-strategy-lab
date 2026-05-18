# Project Status

- Current phase: WP6 - Local Generated Artifact Cleanup + Ignore Enforcement Guard
- Repo state: generated-artifact cleanup and guardrails on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5
- Current branch: `wp6-local-artifact-cleanup-guard`
- Next intended WP: WP7 - Gitleaks Project-Local Secret Scan Gate Completion
- Live trading status: DISABLED
- API integration status: NOT STARTED
- Runtime dependency integration status: NOT STARTED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged
- Deferred items status: WP5 marks semgrep and pip-audit READY_FOR_WP; gitleaks, npm audit, and cargo audit remain deferred.
- Generated artifact status: WP6 cleanup completed locally; guardrails added to prevent `.venv-security/`, `tools/.bin/`, local security caches, or scan output from being committed.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
