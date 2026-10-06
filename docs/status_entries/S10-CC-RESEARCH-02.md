# S10-CC-RESEARCH-02 Status Entry

## Identity

- WP ID: S10-CC-RESEARCH-02
- Title: Control Center Alpha Factory + Evidence / Research Lineage
- Package class / size / risk: CONTROL_CENTER_ALPHA_RESEARCH_MEMORY_DISCOVERY_READ_MODEL / L / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-cc-research-02-alpha-evidence-lineage
- Frozen base: e8fbba6436020d543816e1be3fd45ad9c74dffd7
- Predecessor: PR #224 / S10-CC-RESEARCH-01, head 4dd11f1b35bf49cb14d3e03d257f775926ddf116, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (read-only Alpha Factory + Discovery projection)

- `src/operator_cockpit_research.py` (the existing approved module) gains pure projections over
  `load_and_verify_alpha_factory_registry` and `load_and_verify_alpha_discovery_registry` only (no
  `sqlite3`, open, append, init, repair, second validator, path discovery or environment read).
- `src/operator_cockpit.py`: two optional `CockpitConfig` fields appended
  (`alpha_factory_registry_path`, `alpha_discovery_registry_path`), two CLI flags
  (`--alpha-factory-registry`, `--alpha-discovery-registry`) and six GET routes:
  `/api/alpha/memory`, `/api/alpha/candidates`, `/api/alpha/candidates/{candidate_id}`,
  `/api/alpha/episodes/{research_episode_id}`, `/api/alpha/discovery/queue`,
  `/api/alpha/discovery/triage/{market_triage_decision_id}`. Total `/api` routes: 24.
- Research memory: registry summary; candidates by registry sequence DESC then id ASC; candidate
  lineage (same-snapshot families, episodes, source references, opaque deterministic evidence refs);
  research leaves per exact (candidate, family) lineage, several allowed; full episode evidence.
- Discovery: latest recorded queue = greatest registry sequence; policy / universe / lane-grouped
  triage from the same snapshot; external universe completeness `UNPROVEN`; triage detail with
  universe market and material change; Alpha-memory resolution `NOT_BOUND` / `UNAVAILABLE` /
  `HEAD_MISMATCH` / `RESOLVED` using the stored `matched_*` ids and an exact bound-head match only.
- Sources are independent: either layer stays usable when the other is unavailable.
- Frontend: one `/alpha` workspace (Research Memory and Discovery Queue tabs), `alpha` query family
  with six key families, manual refresh only, Storybook/MSW states for populated, candidate,
  episode/reopen lineage, source-unavailable, queue, triage + material change, Alpha unavailable and
  head-mismatch cases; responsive CSS without page-level horizontal overflow.
- Contract: `docs/control_center_alpha_research_contract.md`.

## Historical Compatibility Edits

- `tests/test_operator_cockpit.py`: the exact route-set assertion extends by the six Alpha GET routes
  only.
- `tests/test_architecture_boundaries.py`: explanatory wording only; the existing exact
  `src/operator_cockpit_research.py` approval is reused (no new entry, no wildcard).
- `tests/test_operator_cockpit_research.py`: the RESEARCH-01 R16 Alpha exclusion is replaced by a
  narrower verified-read-only Alpha boundary test; the merged frontend guard's corrupted word-boundary
  regex (literal backspace bytes) is restored to its intended `\b...\b` form.

## Exact Scope (15 paths)

- src/operator_cockpit.py, src/operator_cockpit_research.py
- tests/test_operator_cockpit_research.py, tests/test_operator_cockpit.py, tests/test_architecture_boundaries.py
- src/operator_cockpit_frontend/src/{api.ts, app.tsx, styles.css, foundation.stories.tsx}
- docs/control_center_alpha_research_contract.md
- docs/project_status.md, docs/repo_truth_index.md, docs/status_entries/S10-CC-RESEARCH-02.md
- docs/wp_specs/S10-CC-RESEARCH-02/{wp_prompt.txt, wp_spec.json}

## Authority / Non-Authority Posture

- Alpha Factory mutations 0; Alpha Discovery mutations 0; Hermes invocations 0; provider/model calls
  0; external product/source requests 0; credentials 0; account reads 0; strategy mutations 0; paper
  mutations 0; qualification actions 0; Gate-C actions 0; LIVE-ORCH actions 0; signatures/orders 0;
  capital USD 0; deployment/network changes 0; live DISABLED.
- No new persistence, dependency, lockfile, workflow or canonical Alpha / StrategyLifecycle / Hermes
  source change.
- No Strategy/Hermes inferred Alpha join; no qualification or AF1 history synthesis.
- `RESEARCH_SUPPORTIVE` is never qualification, executable edge, profitability or trading authority;
  discovery priority is research allocation, never strategy selection or trade priority.

## Successor Boundary

After Side17 review and Karl merge the Control Center Research phase is complete. Next, separately
gated: S10-CC-OPS-01 (Portfolio / Risk / Runtime Operations Read Model), then S10-CC-STREAM-01,
S10-CC-CMD-01, S10-CC-PROD-01. The live/network lane remains independently governed.

## Validation

Focused research tests, existing cockpit tests, architecture boundaries, Alpha Factory / Alpha
Discovery / StrategyLifecycle / Hermes strategy-manager regressions, frontend
typecheck/build/Storybook build/audit, readiness, exact scope, hygiene, security, one local full suite
and the final exact-head hosted matrix are recorded in the PR body.
