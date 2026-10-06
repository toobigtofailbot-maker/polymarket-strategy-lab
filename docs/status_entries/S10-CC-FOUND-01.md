# S10-CC-FOUND-01 Status Entry

## Identity

- WP ID: S10-CC-FOUND-01
- Title: Control Center Frontend Foundation + Existing Cockpit Compatibility Migration (REV A)
- Package class / size / risk: CONTROL_CENTER_FRONTEND_FOUNDATION / L / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-cc-found-01-control-center-foundation
- Frozen base: 71a83bf1d989b5e0bb8a4feab72132756d1eef15
- Predecessor: PR #221 / S10-LIVE-CANARY-UA-01, head c76b6eeb9157ab578c2655701ab9950d1bd474bd, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO (Karl only; review owner Side17)
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Capability (Foundation only, read-only)

The five existing cockpit views (Overview, Market Truth, Experiments with inline detail, Paper
Operations, Audit / Health) are migrated, with unchanged domain semantics, onto a Control Center
frontend foundation in `src/operator_cockpit_frontend/`:

- `src/api.ts`: typed DTOs for the routes the five views consume, same-origin `/api` base, GET only,
  closed safe error codes (`INVALID_INPUT`, `NOT_FOUND`, `SOURCE_UNAVAILABLE`, `INTERNAL_ERROR`, plus
  frontend `NETWORK_UNAVAILABLE` / `MALFORMED_RESPONSE`), `["cc", family, ...]` query keys and one
  conservative `QueryClient` factory (retry off, no focus/reconnect refetch, `staleTime` Infinity, no
  interval).
- `src/app.tsx`: shell, React Router declarative routes (`/overview`, `/markets`, `/experiments`,
  `/paper`, `/audit`; `/` and unknown paths redirect to `/overview`), the five views and small
  source-owned primitives (button, nav link, status pill, panel, metric, table, load/empty/error
  surfaces). Refresh invalidates only the active route family.
- `src/main.tsx`: root, StrictMode, BrowserRouter, QueryClientProvider, stylesheet.
- `src/styles.css`: semantic design tokens, system fonts; `index.html` is a minimal shell.
- `vite.config.ts`: loopback dev server and a loopback-only `/api` dev proxy to `127.0.0.1:8000`.
- Storybook + MSW: `.storybook/` (CSF Next `definePreview` with msw-storybook-addon v3, no extra
  addons, telemetry off), generated `public/mockServiceWorker.js`, and `src/foundation.stories.tsx`
  with deterministic DTO-shaped reference states. Unmocked `/api` requests get a closed fixture error
  and the Storybook build drops the dev proxy, so no story can reach a backend.

## Exact Dependency Pins

Runtime: react 19.3.0, react-dom 19.3.0, react-router 8.4.0, @tanstack/react-query 5.104.0.
Dev: @types/react 19.3.0, @types/react-dom 19.3.0, typescript 7.0.2, vite 8.3.0, storybook 10.6.1,
@storybook/react-vite 10.6.1, msw 2.15.0, msw-storybook-addon 3.0.3. Node engine 24.18.0. MSW stays on
2.x because msw-storybook-addon v3 declares an msw 2.x peer.

## REV A Scope Correction

The original 20-path issue stopped before writing files
(`S10_CC_FOUND_01_SCOPE_COMPATIBILITY_TEST_REQUIRED`): two historical frontend guards in
`tests/test_operator_cockpit.py` froze the WP171 dependency dictionaries and the `"Overview"` label
location in `src/main.tsx`. REV A folds the primitives into `src/app.tsx` and uses the freed slot for
that test file, with exactly two updates: T01 exact dependency dictionaries now equal the pinned set
(still exact equality, lock root mirror kept); T02 the `"Overview"` label is read from `src/app.tsx`.
No backend or read-only assertion changed.

## Exact Scope (20 paths)

- .github/workflows/ci.yml (cockpit-frontend job gains only `npm run build-storybook`)
- src/operator_cockpit_frontend/{package.json, package-lock.json, index.html, tsconfig.json, vite.config.ts}
- src/operator_cockpit_frontend/src/{main.tsx, app.tsx, api.ts, styles.css, foundation.stories.tsx}
- src/operator_cockpit_frontend/.storybook/{main.ts, preview.ts}
- src/operator_cockpit_frontend/public/mockServiceWorker.js
- tests/test_operator_cockpit.py
- docs/project_status.md, docs/repo_truth_index.md, docs/status_entries/S10-CC-FOUND-01.md
- docs/wp_specs/S10-CC-FOUND-01/{wp_prompt.txt, wp_spec.json}

## Authority / Non-Authority Posture

- Backend `src/operator_cockpit.py` byte-unchanged; 14 GET-only routes and semantics unchanged; no new
  route, DTO, persistence, scheduler, polling, SSE or WebSocket.
- No Strategy/Hermes/Alpha/OPS read model, no protected command, no paper mutation control.
- No deployment, hosting, Tailscale, VPS, firewall or reverse-proxy change.
- No credential, account read, product network, Gate-C, LIVE-ORCH, order, signing, execution or live
  authority. Capital USD 0. Live trading remains DISABLED.
- The live/network lane remains separately blocked on execution-network / geoblock resolution and is
  not changed by this WP; the Control Center lane runs parallel to it.

## Successor Boundary

Next: S10-CC-RESEARCH-01 (read-only StrategyLifecycle, Hermes assessments, Alpha evidence, lineage),
separately gated. Later roadmap: S10-CC-OPS-01, S10-CC-STREAM-01, S10-CC-CMD-01, S10-CC-PROD-01.

## Validation

Focused frontend, Storybook, static N01-N10 checks, adjacent cockpit/workflow tests, readiness, scope,
hygiene, security, one local full suite and the final exact-head hosted matrix are recorded in the PR
body.
