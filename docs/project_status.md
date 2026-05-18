# Project Status

- Current phase: WP5 - Security Tooling Completion Follow-Up + Remote Main Sync Gate
- Repo state: security tooling completion and remote-main sync gate on branch
- Merged WPs: WP1, WP2, WP3, WP4
- Current branch: `wp5-security-tooling-completion`
- Next intended WP: WP6 - Read-Only Polymarket Client Adapter Evaluation, only if gitleaks or an approved equivalent, semgrep, and pip-audit are available or explicitly accepted as sufficient for dev-only read-only client evaluation. Otherwise WP6 - Security Tooling Completion Follow-Up II.
- Live trading status: DISABLED
- API integration status: NOT STARTED
- Runtime dependency integration status: NOT STARTED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged
- Deferred items status: WP5 marks semgrep and pip-audit READY_FOR_WP; gitleaks, npm audit, and cargo audit remain deferred.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
