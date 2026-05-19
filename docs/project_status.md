# Project Status

- Current phase: WP7 - Gitleaks Project-Local Secret Scan Gate Completion
- Repo state: gitleaks secret scan gate on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6
- Current branch: `wp7-gitleaks-secret-scan-gate`
- Next intended WP: WP8 - Read-Only Polymarket Client Adapter Evaluation (gitleaks is READY_FOR_WP; all security tools must be rerun before runtime dependency integration, copied code, or live/API work)
- Live trading status: DISABLED
- API integration status: NOT STARTED
- Runtime dependency integration status: NOT STARTED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged
- Deferred items status: WP7 marks gitleaks READY_FOR_WP (scan passed, no findings); semgrep and pip-audit remain READY_FOR_WP (require `.venv-security/` restoration); npm audit and cargo audit remain DEFERRED.
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored `tools/.bin/` (not committed).

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
