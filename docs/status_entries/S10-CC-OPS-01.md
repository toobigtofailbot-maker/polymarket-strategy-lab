# S10-CC-OPS-01 Status Entry

## Identity

- WP ID: S10-CC-OPS-01
- Title: Control Center Portfolio / Risk / Runtime Operations Read Model
- Package class / size / risk: CONTROL_CENTER_PORTFOLIO_RISK_RUNTIME_OPS_READ_MODEL / L / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-cc-ops-01-portfolio-risk-runtime-read-model
- Frozen base: 2685429aca6c0b655308a562a693d3075c1994a4
- Predecessor: PR #225 / S10-CC-RESEARCH-02, head d4075ea344a318897e5cd755eb691a2bd45daa89, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (read-only portfolio-operations projection)

- New pure module `src/operator_cockpit_ops.py`: reads StrategyLifecycle only through
  `load_strategy_lifecycle_store` (valid, non-null `StrategyLifecycleSnapshot`) and calls the
  canonical `evaluate_portfolio_capacity(snapshot, evaluated_at_ns)` exactly once per request. No
  `sqlite3`, open, append, init, second validator, capacity arithmetic, paper / gateway / LIVE-ORCH /
  Gate-C / EXEC-FEAS / deployment / network / subprocess import.
- `src/operator_cockpit.py`: one GET route `/api/ops/portfolio` over the existing
  `strategy_lifecycle_path` (no new config field or flag); any query -> 400 `INVALID_INPUT`; one
  `time.time_ns()` read per request after query validation; closed `503 SOURCE_UNAVAILABLE`. Total
  `/api` routes: 25.
- Response: `read_only`, `evaluated_at_ns`, `lifecycle_store_head_entry_hash`, `active_policy` (null or
  the exact same-snapshot policy with all 17 money/count limits), canonical `capacity`,
  `strategy_reservations` (window truth at the backend time, health, exact canonical per-strategy
  capacity result or null/[] when none, active restrictions; ordered active-first, risk band, label,
  id) and fixed `non_authority` flags. No active policy and canonical capacity rejection are HTTP 200
  domain states.
- Frontend: one `/ops` route ("Operations"), `ops` query family with five OPS-owned keys (the four
  paper/gateway keys read the existing endpoints unchanged), manual refresh only; Portfolio
  Authority, Recorded Runtime / Gateway, Simulated Paper Risk, Strategy Reservations and Recent
  Recorded Gateway Events sections, each with its own query state; six Storybook/MSW OPS states;
  responsive CSS without page-level overflow at 375 px.
- Contract: `docs/control_center_ops_read_model_contract.md`.

## Historical Compatibility Edits

- `tests/test_operator_cockpit.py`: the exact `/api` route-set assertion extends by
  `/api/ops/portfolio` only (25 routes).
- `tests/test_operator_cockpit_research.py`: the primary frontend route guard extends by `/ops` only;
  the two exact `/api` route-count assertions move from 24 to 25 mechanically; the word-boundary
  mutation guard and `/api/health` exact-key semantics are unchanged.
- `tests/test_architecture_boundaries.py`: one exact `src/operator_cockpit_ops.py` allowlist entry with
  explanatory wording (no wildcard, no other entry).

## Exact Scope (16 paths)

- src/operator_cockpit.py, src/operator_cockpit_ops.py
- tests/test_operator_cockpit_ops.py, tests/test_operator_cockpit.py,
  tests/test_operator_cockpit_research.py, tests/test_architecture_boundaries.py
- src/operator_cockpit_frontend/src/{api.ts, app.tsx, styles.css, foundation.stories.tsx}
- docs/control_center_ops_read_model_contract.md
- docs/project_status.md, docs/repo_truth_index.md, docs/status_entries/S10-CC-OPS-01.md
- docs/wp_specs/S10-CC-OPS-01/{wp_prompt.txt, wp_spec.json}

## Authority / Non-Authority Posture

- StrategyLifecycle mutations 0; paper mutations 0; gateway mutations 0; credentials 0; account reads
  0; LIVE-ORCH / preflight / canary / reconcile actions 0; Gate-C / EXEC-FEAS actions 0;
  host-currentness or geoblock requests 0; product network 0; signatures/orders 0; capital USD 0;
  live DISABLED.
- No new persistence, dependency, lockfile, workflow or canonical StrategyLifecycle / paper / gateway
  source change; `src/strategy_lifecycle/**`, `src/paper_trading/**` and `src/execution_gateway/**`
  are byte-unchanged.
- Budget reservations are never actual account exposure; paper values are never merged with
  reservation economics; recorded gateway state is never promoted to current account, host or
  network truth, Gate-C eligibility or live readiness; no incident/alert registry is invented.

## Successor Boundary

After Side17 review and Karl merge, next separately gated: S10-CC-STREAM-01 (streaming / freshness /
gap / resync), then S10-CC-CMD-01, S10-CC-PROD-01. OPS-01 authorizes none of them. The live/network
lane remains independently governed.

## Validation

Focused OPS tests (O01-O18), existing cockpit and research tests, architecture boundaries,
StrategyLifecycle / gateway / paper regressions, frontend typecheck/build/Storybook build/smoke/audit,
readiness, exact scope, hygiene, security, one local full suite and the final exact-head hosted matrix
are recorded in the PR body.
