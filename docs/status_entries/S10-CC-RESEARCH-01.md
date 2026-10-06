# S10-CC-RESEARCH-01 Status Entry

## Identity

- WP ID: S10-CC-RESEARCH-01
- Title: Control Center StrategyLifecycle + Hermes Read-Only Research Vertical
- Package class / size / risk: CONTROL_CENTER_STRATEGY_HERMES_RESEARCH_READ_MODEL / L / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-cc-research-01-strategy-hermes-read-model
- Frozen base: 780bf84144439ebc6b1b53f468f257d70707014c
- Predecessor: PR #223 / S10-CC-FOUND-01, head 786d060089c71cc7f26e1b3d543c65011b950b58, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (read-only research vertical)

- `src/operator_cockpit_research.py`: pure projection over `load_strategy_lifecycle_store` and
  `load_hermes_strategy_manager_store` only (no `sqlite3`, open, append, init, second validator or
  second context hash).
- `src/operator_cockpit.py`: two optional `CockpitConfig` fields appended
  (`strategy_lifecycle_path`, `hermes_strategy_manager_path`), two optional CLI flags and four GET
  routes: `/api/strategies`, `/api/strategies/{strategy_version_id}`, `/api/hermes/assessments`,
  `/api/hermes/assessments/{assessment_id}`. The fourteen existing routes are unchanged.
- Context status per assessment: `CURRENT` / `STALE_CONTEXT` / `TARGET_MISSING`, derived only with
  `strategy_lifecycle_context_fingerprint`; display only.
- Latest assessment per strategy only from the verified manager mapping
  `latest_assessment_by_strategy_version`.
- Lineage: exact parent ids root to target, same family, bounded, fail closed.
- Strategy routes remain usable with `latest_hermes_assessment: null` when Hermes is unconfigured or
  unavailable; Hermes routes return `SOURCE_UNAVAILABLE`.
- Frontend: `/strategies` and `/hermes` workspaces (list + component-local detail), query families
  `strategies` / `hermes`, Storybook/MSW states for populated, selected detail, no-Hermes, stale
  context and source-unavailable cases, responsive CSS.
- Contract: `docs/control_center_strategy_hermes_research_contract.md`.

## Scope Amendments (Side17-approved before implementation)

- A: `tests/test_architecture_boundaries.py` adds only the exact `src/operator_cockpit_research.py`
  approved-source entry (after `src/operator_cockpit.py`) and its explanatory wording; all existing
  assertions and the locked trailing ordering are preserved.
- A2: `tests/test_operator_cockpit.py` extends only the exact route-set assertion in
  `test_exact_routes_limits_errors_and_no_mutation_routes` by the four new GET routes; every other
  assertion is unchanged.

## Exact Scope (15 paths)

- src/operator_cockpit.py, src/operator_cockpit_research.py
- tests/test_operator_cockpit_research.py, tests/test_architecture_boundaries.py, tests/test_operator_cockpit.py
- src/operator_cockpit_frontend/src/{api.ts, app.tsx, styles.css, foundation.stories.tsx}
- docs/control_center_strategy_hermes_research_contract.md
- docs/project_status.md, docs/repo_truth_index.md, docs/status_entries/S10-CC-RESEARCH-01.md
- docs/wp_specs/S10-CC-RESEARCH-01/{wp_prompt.txt, wp_spec.json}

## Authority / Non-Authority Posture

- Hermes invocations 0; provider/model calls 0; external product requests 0; credentials 0; account
  reads 0; strategy mutations 0; paper mutations 0; Gate-C actions 0; LIVE-ORCH actions 0;
  signatures/orders 0; capital USD 0; deployment/network changes 0; live DISABLED.
- No dependency, lockfile, workflow, canonical StrategyLifecycle or Hermes source change.
- No Alpha read model or inferred Alpha-to-Strategy linkage (S10-CC-RESEARCH-02).
- Hermes assessments are soft research judgments; context status is never approval, Gate-C
  eligibility, execution feasibility or live permission.

## Successor Boundary

Next: S10-CC-RESEARCH-02 (Control Center Alpha Factory + Evidence / Research Lineage), separately
gated. Later roadmap: S10-CC-OPS-01, S10-CC-STREAM-01, S10-CC-CMD-01, S10-CC-PROD-01. The live/network
lane remains independently governed.

## Validation

Focused research tests, existing cockpit tests, StrategyLifecycle / Hermes strategy-manager
regressions, architecture boundaries, frontend typecheck/build/Storybook build/audit, readiness,
exact scope, hygiene, security, one local full suite and the final exact-head hosted matrix are
recorded in the PR body.
