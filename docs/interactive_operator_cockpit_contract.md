# WP171 — Interactive Operator Cockpit MVP

## Authority and posture

WP171 is a local operator view over already-validated WP169 market-truth and WP170
experiment-registry evidence. It is read-only and non-authoritative. It grants no
credential, authenticated/private account, acquisition, strategy, promotion, paper,
portfolio, risk, order, execution, live-trading, Hermes, provider/model, scheduler,
daemon, deployment, hosted-database, alert-dispatch, or external product-network
authority. Capital at risk is USD 0 and merge authority is NO.

The browser may communicate with the FastAPI process on loopback only. The backend
opens only explicit caller-selected local SQLite files. WP169 direct reads use SQLite
URI `mode=ro`, validate application/user versions and exact required table columns,
and execute fixed bounded reads. WP170 reads use its existing complete-history
`load_and_verify_experiment_registry` API, which opens URI read-only and validates
the exact registry schema and hash chain. No endpoint accepts SQL or a filesystem path.

## Frozen backend contract

`CockpitConfig(market_truth_path, experiment_registry_path)` is immutable. Either
path may be `None`, meaning not configured; path values never appear in output.
`create_app(config)` has no import-time I/O or background activity.

The exact domain route set is:

- `GET /api/health`
- `GET /api/overview`
- `GET /api/market-truth/recent`
- `GET /api/experiments`
- `GET /api/experiments/{experiment_id}`
- `GET /api/audit/recent`

There is no domain POST, PUT, PATCH, or DELETE route. List endpoints accept only
`limit`: missing means 50, ASCII integer 1 through 100 is accepted, and every other
value returns HTTP 400. WP171 has no offset, status/source filter, free-text search,
cursor browser, checkpoint browser, SSE, or WebSocket.

Cockpit-owned errors have exactly `{"error":{"code":"<TOKEN>"}}`. The tokens and
HTTP mappings are `INVALID_INPUT`/400, `NOT_FOUND`/404,
`SOURCE_UNAVAILABLE`/503, and `INTERNAL_ERROR`/500. Precedence is request
validation, source validation, absent valid experiment, then unexpected internal
failure. Errors never echo exceptions, SQL, caller text, paths, environment values,
usernames, or tracebacks.

## Frozen success models

List responses are `{"items":[...],"count":N,"limit":N}`, where count is only the
number returned. Experiment detail is `{"item":{...}}`.

Health contains `status` (`OK` or `DEGRADED`), `read_only:true`, and WP169/WP170
`configured` and `readable` booleans. Overview contains `read_only:true`;
market-truth normalized/accepted/quarantined/open-gap counts and nullable latest
receive time; experiment/lifecycle/evidence counts; and bounded recent-activity
counts.

Market Truth projects only observation ID, source/event kind, optional event/market/
asset IDs, optional event time, receive time, observation status, closed error codes,
and book readiness. It is newest-first by stored archive order. Raw bytes, canonical
payload, hashes, provenance, source cursors, archive sequences, and local paths are
excluded.

Experiments are newest-first by registry sequence and expose validated WP170 IDs,
trial, preregistration time, latest lifecycle state, exact `result_status`, and OOS
exposure ordinal. Detail adds dataset/manifest/feature/label/split/metric/baseline/cost
reference and receipt IDs. `OOS_CRITERIA_MET_UNCOSTED` stays exactly that; the UI
may say “First look” for ordinal 1 and “Reused / diagnostic” later, but never
“profitable”, “tradeable”, or a recommendation.

Audit is a deterministic newest-first bounded merge of safe WP170 lifecycle/evidence
receipts and available WP169 gap events: source, nullable record/experiment ID, kind,
sequence, status, and time only.

## Frontend and operation

The React/TypeScript/Vite client has exactly four primary views: Overview, Market
Truth, Experiments, and Audit / Health. It provides loading, empty, success,
backend/source error, experiment detail, and manual refresh states. It has no CDN,
router, chart, component, or state-management dependency and no trading controls.

Install and run locally:

```text
python -m pip install -e ".[cockpit]"
python -m src.operator_cockpit --market-truth-store PATH.sqlite3 --experiment-registry PATH.sqlite3
npm --prefix src/operator_cockpit_frontend ci
npm --prefix src/operator_cockpit_frontend run dev
```

The exact Python cockpit pins are `fastapi==0.141.1` (MIT) and
`uvicorn==0.52.4` (BSD-3-Clause). The exact frontend pins are React/ReactDOM
`19.3.0`, Vite `8.3.0`, TypeScript `7.0.2`, and React type packages `19.3.0`.
CI uses Node `24.18.0` LTS.

## Evidence and successor

The committed WP prompt/spec/certificate, focused tests, lockfile, dependency audits,
full repository suite, exact-head hosted checks, and re-fetched PR body are the
evidence. Evidence mode is `PRIVATE_REPO_MANUAL_VERIFIED`; the PR body is canonical
and a final comment is optional/non-canonical.

WP172 — Hermes Runtime + Alpha Factory is separately gated. WP171 implements no
WP172 capability. Do not merge without independent Side review and explicit user
authorization.
