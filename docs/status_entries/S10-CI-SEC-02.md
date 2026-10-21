# S10-CI-SEC-02 Status Entry

## Identity

- WP ID: S10-CI-SEC-02
- Title: Gitleaks Default-Rule Restoration
- Package class / size / risk: SECURITY_TOOLING_SECRET_SCAN_RULE_RESTORATION / M / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-ci-sec-02-gitleaks-default-rules
- Frozen implementation base (historical identity): 0c158e061d3ab5039997c6b4e736da0da9507d37
- Validation / merge base: 22b4a6a6fa734144fbbb066baa870df3d8b537b6 (main after PR #248 /
  S10-CI-SEC-03 merged; integrated into this branch by a merge commit, original commits kept)
- Predecessor: PR #245 / S10-HERMES-OAUTH-JOURNAL-01, head e178c389f09feadd01956cc278ca045e35a49823, merged at the base
- PR #247 and current live head, draft/Ready state, review state and hosted CI results: see
  GitHub PR metadata and the PR body
- Authorization: Karl, 2026-10-20 — exact ten-path package including the spec-guard root-path
  mapping and draft PR; SIDE20 in-scope correction; Karl 2026-10-21 — one hosted attempt, then the
  Side21 post-#248 main-sync continuation with one exact-head hosted run
- Evidence mode and Ready for review: live values in the PR body
- Merge authorized: NO

## Trigger

The 2026-10-20 read-only pre-publication audit (finding H1) proved the committed `.gitleaks.toml`
(WP15) defined zero detection rules. It held only a legacy `[allowlist]` table and no `[extend]`
table, and gitleaks auto-loads it from the scanned source root. `tools/security/run_available_security_checks.py`
runs `gitleaks git --redact` from the repository root, so every run from WP15 onward passed
vacuously. The legacy allowlist `paths` entry also excluded all of `docs/deferred_items_log.md`,
because legacy allowlist conditions match independently.

## Repair

- `.gitleaks.toml`: `[extend] useDefault = true` (official mechanism) restores the embedded default
  rules. There is no allowlist of any kind (SIDE20 correction: a line allowlist would also hide a
  new secret appended to the WP14-D002 row).
- `.gitleaksignore`: 20 exact `commit:path:rule:line` fingerprints, each manually classified as a
  synthetic test fixture, constructed dummy value, public sample token or documentation prose,
  including the WP14-D002 deferred-log finding `70136bc4ad74eae69a0c0ee960a12a0f852e4df5:docs/deferred_items_log.md:generic-api-key:49`. No path, directory, rule or wildcard
  entry.
- `tools/wp/wp_spec_guard.py`: exactly `.gitleaks.toml` and `.gitleaksignore` now map to
  `local_offline_tooling`. Before this change the guard mapped no root non-dependency path, so no
  governed package could change them. `README.md`, look-alikes and nested copies remain
  `AUTHORITY_CONTRADICTION`.
- The security runner, workflows and CI matrix are unchanged.

## Exact Scope (10 paths)

- .gitleaks.toml
- .gitleaksignore
- tools/wp/wp_spec_guard.py
- tests/tools/wp/test_wp_spec_guard.py
- tests/test_gitleaks_secret_scan_gate.py
- docs/gitleaks_secret_scan_gate.md
- docs/deferred_items_log.md
- docs/status_entries/S10-CI-SEC-02.md
- docs/wp_specs/S10-CI-SEC-02/wp_prompt.txt
- docs/wp_specs/S10-CI-SEC-02/wp_spec.json

## Detection Evidence (local, gitleaks 8.27.2)

- Runner-mode history scan (`gitleaks git`, whose default log options include `--all`, so the
  commit count depends on the local refs present): 20 findings before `.gitleaksignore`, 0 after,
  on 2026-10-20 in this worktree's local refs (558 commits). Every one of the 20 is classified and
  fingerprinted.
- All-refs merge-inclusive scan (791 commits; all branches and pull refs): 39 findings = 20
  fingerprinted + 19 merge-diff re-occurrences whose matched values are byte-identical (SHA-256
  compared, never printed) to fingerprinted values. Zero unclassified findings.
- Same-row proof in a scratch clone: a commit appending a runtime-assembled synthetic token to the
  real WP14-D002 row of `docs/deferred_items_log.md` turns the runner gitleaks row to
  FINDING_OR_ERROR; the earlier row-bound allowlist configuration returns PASS for it.
- Runner proof in a scratch clone: gitleaks row PASS on clean history; FINDING_OR_ERROR after a
  scratch commit planting a runtime-assembled synthetic token; the pre-repair WP15 configuration
  returns PASS for that same planted commit (the defect).
- `tests/test_gitleaks_secret_scan_gate.py`: configuration-shape test (no allowlist), 14-row
  configuration negative matrix, exact fingerprint list including the WP14-D002 fingerprint,
  7-row fingerprint negative matrix, and five binary-backed detection tests (a git-mode test
  proves a secret added to the classified WP14-D002 row is detected; the WP15 and row-bound
  allowlist shapes are both proven blind). These skip without a gitleaks binary that supports
  `dir` (hosted CI: see S10-CI-SEC-02-D001).
- `.gitleaksignore` fingerprints contain commit SHAs, so they apply to `gitleaks git` (the runner's
  mode) only; a `gitleaks dir` working-tree scan still reports the present fixtures, and a history
  rewrite would invalidate them.
- After integrating main 22b4a6a (2026-10-21): `.gitleaks.toml` still contains only `[extend]
  useDefault = true` and `.gitleaksignore` the same 20 fingerprints; the runner-mode scan over
  the local refs (561 non-merge commits) finds no leaks, and the #248 commit and every new
  branch commit including merges (`-m`) contain no finding.
- Hosted history: run 39655818346 on the pre-sync head d154fec (2026-10-21) failed only
  `cockpit-frontend` (`npm audit` on storybook 10.6.1 / vite 8.3.0 advisories outside this scope)
  and therefore `ci-final-gate`; every other job passed. PR #248 / S10-CI-SEC-03 closed those
  advisories and is integrated here; the exact-head result after the sync is in the PR body.
- Independent review (fresh-context reviewer) on head a0a1438: PASS_WITH_NOTES, no blockers; its
  in-scope notes (WP14 allowlist test made discriminating, row-bound regex, commit-count wording,
  git-mode fingerprint note, binary `dir` probe) are corrected in the following commit and D004
  records the advisory scope-summary limitation. Re-review of 84f907c: PASS_WITH_NOTES.
- SIDE20 correction: the row-bound line allowlist was too broad (a new secret appended to the
  WP14-D002 row was ignored). The allowlist is removed and the single historical WP14-D002
  finding is suppressed by its exact fingerprint only, within the same ten-file scope.

## Authority / Non-Authority Posture

FAST, Risk 2. No `src/**`, workflow, dependency, runner, credential, product network, deployment,
Hermes, strategy, paper, execution, order, live or capital authority. Hosted Actions only as
separately authorized single exact-head runs on free standard runners; no visibility or settings
change, no history rewrite. PR #246 untouched. Capital/orders: USD 0 / 0. D001 (mandatory hosted
gitleaks scan) remains separate; this PR's CI does not run a hosted secret scan. Merge is Karl's
decision after independent acceptance.
