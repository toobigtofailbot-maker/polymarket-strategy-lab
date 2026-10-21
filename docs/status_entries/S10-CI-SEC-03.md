# S10-CI-SEC-03 Status Entry

## Identity

- WP ID: S10-CI-SEC-03
- Title: Frontend Security Advisory Closure
- Package class / size / risk: SECURITY_FRONTEND_DEV_DEPENDENCY_PATCH / M / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-ci-sec-03-frontend-advisory
- Frozen base: 0c158e061d3ab5039997c6b4e736da0da9507d37
- Predecessor: PR #245 / S10-HERMES-OAUTH-JOURNAL-01, head e178c389f09feadd01956cc278ca045e35a49823, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review / hosted CI: live values in the PR body
- Merge authorized: NO (Karl only, after Side21 independent acceptance)
- Authorization: Karl's 2026-10-21 dispatch of the Side21 package, plus the dispatched Side21 seventh-path amendment

## Trigger

Hosted run 39655818346 (PR #247 exact head) passed every Python, NDFD and audit job, but
`cockpit-frontend` failed `npm audit --audit-level=high` and `ci-final-gate` failed closed. The
advisories were published after the last green `main`-based run, against exact-pinned frontend
devDependencies:

- `storybook` 10.6.1: critical, GHSA-f2ph-cmg5-wxc8 (fixed 10.6.3);
- `vite` 8.3.0: high, GHSA-9jrq-w75r-8gcw, GHSA-rq7h-c2jc-7f22, GHSA-vfpm-58rq-9qcg and launch-editor
  GHSA-698v-4r3x-3vcv, GHSA-r825-w8mm-5pxw, GHSA-587h-7wmj-h5pm (fixed 8.3.5).

Every pull request against `0c158e0` fails the required `ci-final-gate` until these are closed.

## Repair

- `package.json` devDependencies only: `storybook` 10.6.1 → 10.6.3, `@storybook/react-vite`
  10.6.1 → 10.6.3 (its 10.6.3 release peers `storybook ^10.6.3`), `vite` 8.3.0 → 8.3.5. Every other
  field and pin is unchanged; `msw-storybook-addon` 3.0.3 accepts storybook 10.6.3.
- `package-lock.json` on Node 24.18.0 / npm 11.16.0 with `--ignore-scripts`. npm also re-resolved
  `@babel/helpers`, `@babel/traverse`, `browserslist` (with its data packages) and `resolve`, which no
  new range requires; those entries were restored, and npm reports the lock "up to date". The 25
  remaining version moves are each forced by a declared range (checked with npm's semver):
  - `storybook` and `@storybook/{react-vite,react,react-dom-shim,builder-vite}` 10.6.1 → 10.6.3;
  - `vite` 8.3.0 → 8.3.5;
  - `postcss` 8.5.28 → 8.5.31 (vite `^8.5.30`) and `nanoid` 3.3.18 → 3.3.20 (postcss `^3.3.20`);
  - `rolldown` 1.2.8 → 1.2.15 (vite `~1.2.14`), its 14 platform bindings, and `@oxc-project/types`
    0.149.0 → 0.155.0 (rolldown `=0.155.0`).
  No package is added or removed; `source-map-js` stays resolved at the patched 1.2.2.
- `tests/test_operator_cockpit.py`: the three versions in the exact devDependencies object.
- `tests/test_codex_workflow_docs.py` (seventh-path amendment): every postcss version vite 8.3.5
  accepts declares `source-map-js: ^1.2.2`, so the S10-CI-SEC-01 parent-range assertion changes
  from `^1.2.1` to `^1.2.2`. Its assertions on the resolved 1.2.2 version, URL, integrity,
  `dev: true` and absence as a direct dependency are unchanged.
- No workflow, audit threshold, ignore, `overrides`, `npm audit fix --force`, Python dependency or
  product source change.

## Exact Scope (7 paths)

- src/operator_cockpit_frontend/package.json
- src/operator_cockpit_frontend/package-lock.json
- tests/test_operator_cockpit.py
- tests/test_codex_workflow_docs.py
- docs/status_entries/S10-CI-SEC-03.md
- docs/wp_specs/S10-CI-SEC-03/wp_prompt.txt
- docs/wp_specs/S10-CI-SEC-03/wp_spec.json

## Validation

Local results (frontend commands, `npm audit`, focused tests, readiness `--check-diff`, full suite)
and the exact-head hosted run with all job conclusions are recorded in the PR body.

## Authority / Non-Authority Posture

FAST, Risk 2. `source_runtime` is true solely because the frontend package files live under `src/`;
the crossed protected group is `dependency/lock changes`. No product or runtime logic, workflow,
credential, product network, deployment, Hermes, strategy, paper, execution, order, live or capital
authority. PR #246 and PR #247 are untouched. D001 (mandatory hosted gitleaks scan) remains a
separate pending WP. Capital/orders: USD 0 / 0.
