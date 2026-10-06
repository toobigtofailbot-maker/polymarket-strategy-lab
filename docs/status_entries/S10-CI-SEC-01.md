# S10-CI-SEC-01 Status Entry

## Identity

- WP ID: S10-CI-SEC-01
- Title: Dependency-Security CI Closure
- Package class / size / risk: SECURITY_TOOLING_DEPENDENCY_CI_CLOSURE / M / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-ci-sec-01-dependency-security-ci-closure
- Frozen base: f9a0bae6a69d008862e6466f1fe532bc9416de5d
- Predecessor: PR #220 / S10-CI-OPT-01, head d6899e205f0652c7314216016d95cd17e6f01f46, merged at the base
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Ready for review: NO until all final evidence passes (live value in the PR body)
- Merge authorized: NO
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Trigger

PR #221 exact-head hosted run 37415989950 failed three audit jobs on advisories published after the
last green run (PR #220 run 37376320007):

- `cockpit-frontend`: `source-map-js` 1.2.1, GHSA-68fv-2mgg-jv7q / CVE-2026-93749, high; patched 1.2.2.
  Development-only, via `postcss` (`^1.2.1`) under `vite`.
- `dependency-audit` and `ndfd-grib-dependency-audit`: `fsspec` 2026.2.0, CVE-2026-104851 /
  GHSA-27vj-qcqg-25rc, high; fixed 2026.6.0. Exact-pinned transitively by `nautilus_trader==1.231.0`.

## Repair

- Frontend (real patch, no waiver): `npm update source-map-js --package-lock-only --ignore-scripts`
  on Node 24.18.0 / npm 11.16.0 moved only `node_modules/source-map-js` version, resolved URL and
  integrity to 1.2.2. `package.json`, the parent range and every other lock node are unchanged.
- Python (one exact temporary exception): `dependency-audit` and `ndfd-grib-dependency-audit` run
  exactly `python -m pip_audit --ignore-vuln CVE-2026-104851`. No other job, ID, wildcard, `|| true`,
  `continue-on-error`, `--no-deps`, skipped step or pin change; `pip check` is unchanged. Every other
  finding still fails CI.
- Rejected alternatives: forcing `fsspec` 2026.6.0 conflicts with the exact Nautilus pin; the
  NautilusTrader 2.x line is prerelease and is not a production migration path.

## Exception Removal Trigger

`CVE-2026-104851` is ignored only because the repository's current stable production pin
`nautilus_trader==1.231.0` resolves `fsspec==2026.2.0`. Remove the exception when a separately
authorized, stable, project-compatible NautilusTrader upgrade resolves a non-vulnerable `fsspec`
version (at least the advisory's fixed line 2026.6.0) and that upgraded closure passes compatibility,
`pip check`, dependency audit and the required full validation. A Nautilus prerelease alone is not a
removal path for production. This WP does not authorize that migration.

## Package Correction (Side 17, pre-implementation)

The first readiness run stopped before implementation: the merged spec guard requires
`source_runtime` authority for any `src/` path, including the exact-scope lockfile. Side 17
authorized `source_runtime: true` solely for that reason, a plain `Governance track expected: FAST`
line, removal of the invalid `pyproject.toml` forbidden prefix (still excluded by exact scope) and
the readiness-required negative-test, report-back and rule-matrix sections. The lockfile edit made
before readiness was reverted and reapplied after `IMPLEMENTATION_READY`; the reapplied diff was
byte-identical to the verified one.

## Exact Scope (8 paths)

- .github/workflows/ci.yml
- src/operator_cockpit_frontend/package-lock.json
- tests/test_codex_workflow_docs.py
- docs/project_status.md
- docs/repo_truth_index.md
- docs/status_entries/S10-CI-SEC-01.md
- docs/wp_specs/S10-CI-SEC-01/wp_prompt.txt
- docs/wp_specs/S10-CI-SEC-01/wp_spec.json

## Regression Evidence

- `tests/test_codex_workflow_docs.py`: exact two-job exception, single ignored ID, no masking, pip check
  retained, Nautilus pin unchanged, no direct `fsspec` pin, lock resolves `source-map-js` 1.2.2,
  `package.json` has no direct `source-map-js`, status/repo truth record the reason and removal trigger,
  plus a mutation negative matrix. The existing S10-CI-OPT-01 "audit removed" mutation now targets the
  new exact audit command; its intent is unchanged.
- Validation results (focused, adjacent NDFD guard, frontend gate, readiness, hygiene, local full suite,
  final exact-head hosted matrix) are recorded in the PR body.

## Authority / Non-Authority Posture

- Product/runtime source logic: unchanged (the only `src/**` path is the frontend lockfile)
- Python pins / `pyproject.toml`: unchanged
- PR #221: untouched; separately paused pending this closure
- Credentials / account access / product network: NO
- Deployment / Hermes / strategy / scheduler / paper: NO
- Execution / signing / orders: 0
- Capital: USD 0
- Live: DISABLED

## Successor

Security repair merge -> update PR #221 to the new main -> fresh exact-head PR #221 CI -> Side review
-> Karl merge -> new release SHA rebind/deploy/currentness -> public Gamma/CLOB/geoblock smoke ->
resume the first-canary flow. Each step is separately gated; this WP authorizes none of them.
