# Project Status

- Current phase: WP9 - Polymarket Read-Only Endpoint Contract Validation
- Repo state: endpoint contract validation on branch
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8
- Current branch: `wp9-polymarket-readonly-endpoint-contract-validation`
- API integration status: READ_ONLY_PUBLIC_DATA_CONTRACT_VALIDATION
- Runtime dependency integration status: NOT STARTED
- Live trading status: DISABLED
- Credentials status: NOT USED
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); WP8-D002 remains OPEN (rate-limit not confirmed); WP9-D001 added (CLOB /health 404); WP9-D002 added (JSON-encoded string fields, parser updated in WP9); gitleaks READY_FOR_WP (scan passed); semgrep and pip-audit READY_FOR_WP (require .venv-security/ restoration).
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed).
- Next intended WP: WP10 - Polymarket Market Metadata Snapshot Persistence (three endpoints confirmed sufficient for dev-read-only snapshot use)

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
- CLOB /health correct endpoint path unknown (WP9-D001).
- Rate-limit policy not confirmed (WP8-D002).
