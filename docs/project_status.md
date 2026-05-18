# Project Status

- Current phase: WP4 - Security Tooling Setup
- Repo state: security-tooling setup on branch
- Merged WPs: WP1, WP2, WP3
- Current branch: `wp4-security-tooling-setup`
- Next intended WP: WP5 - Security Tooling Completion Follow-Up. Switch to WP5 - Read-Only Polymarket Client Adapter Evaluation only after security tooling status is sufficient for dev-only client evaluation.
- Live trading status: DISABLED
- API integration status: NOT STARTED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged
- Deferred items status: WP4 security-tooling update in progress

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
