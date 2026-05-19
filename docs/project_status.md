# Project Status

- Current phase: WP8 - Read-Only Polymarket Public Data Adapter Evaluation
- Repo state: first read-only public data adapter on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7
- Current branch: `wp8-readonly-polymarket-adapter-evaluation`
- Next intended WP: WP9 - Polymarket Market Metadata Snapshot Persistence OR WP9 - Official Python Client Dependency Decision (depending on WP8 findings and smoke-test endpoint confirmation)
- Live trading status: DISABLED
- API integration status: READ_ONLY_PUBLIC_DATA_EVALUATION
- Runtime dependency integration status: NOT STARTED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/
- Deferred items status: WP7 marks gitleaks READY_FOR_WP (scan passed, no findings); semgrep and pip-audit remain READY_FOR_WP (require `.venv-security/` restoration); npm audit and cargo audit remain DEFERRED. WP8 adds WP8-D001 (endpoint contract confirmation) and WP8-D002 (rate-limit policy).
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored `tools/.bin/` (not committed).

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
