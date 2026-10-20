# S10-CI-SEC-02 Status Entry

## Identity

- WP ID: S10-CI-SEC-02
- Title: Gitleaks Default-Rule Restoration
- Package class / size / risk: SECURITY_TOOLING_SECRET_SCAN_RULE_RESTORATION / M / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-ci-sec-02-gitleaks-default-rules
- Frozen base: 0c158e061d3ab5039997c6b4e736da0da9507d37
- Predecessor: PR #245 / S10-HERMES-OAUTH-JOURNAL-01, head e178c389f09feadd01956cc278ca045e35a49823, merged at the base
- PR and current live head: see GitHub PR metadata and the PR body (draft)
- Authorization: Karl, 2026-10-20 — exact ten-path package including the spec-guard root-path mapping; draft PR authorized; hosted CI not triggered while GitHub billing is blocked
- Evidence mode: BLOCKED_NOT_READY
- State: IMPLEMENTED_DRAFT_PR / SIDE19_REVIEW_PENDING / HOSTED_CI_NOT_RUN / NOT_MERGE_READY
- Ready for review: NO
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
  rules; the legacy allowlist keeps only the exact WP14-D002 regex, bound to its `| WP14-D002 |`
  table cell and matched against the line (the same phrase in any other row is still scanned);
  the whole-file path exclusion is removed.
- `.gitleaksignore`: 19 exact `commit:path:rule:line` fingerprints, each manually classified as a
  synthetic test fixture, constructed placeholder, public sample token or documentation prose. No
  path, directory, rule or wildcard entry.
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
  commit count depends on the local refs present): 19 findings before `.gitleaksignore`, 0 after,
  on 2026-10-20 in a clone holding the origin branches at `0c158e0` (541 non-merge commits) and
  in this worktree's local refs (557-558 commits). Every one of the 19 is classified and
  fingerprinted.
- All-refs merge-inclusive scan (788 commits; all branches and pull refs): 37 findings = 19
  fingerprinted + 18 merge-diff re-occurrences whose matched values are byte-identical (SHA-256
  compared, never printed) to fingerprinted values. Zero unclassified findings.
- Runner proof in a scratch clone: gitleaks row PASS on clean history; FINDING_OR_ERROR after a
  scratch commit planting a runtime-assembled synthetic token; the pre-repair WP15 configuration
  returns PASS for that same planted commit (the defect).
- `tests/test_gitleaks_secret_scan_gate.py`: configuration-shape test, 14-row configuration
  negative matrix, fingerprint grammar and 7-row negative matrix, and three binary-backed detection
  tests. These skip without a gitleaks binary that supports `dir` (hosted CI: see
  S10-CI-SEC-02-D001).
- `.gitleaksignore` fingerprints contain commit SHAs, so they apply to `gitleaks git` (the runner's
  mode) only; a `gitleaks dir` working-tree scan still reports the present fixtures, and a history
  rewrite would invalidate them.
- Independent review (fresh-context reviewer) on head a0a1438: PASS_WITH_NOTES, no blockers; its
  in-scope notes (WP14 allowlist test made discriminating, row-bound regex, commit-count wording,
  git-mode fingerprint note, binary `dir` probe) are corrected in the following commit and D004
  records the advisory scope-summary limitation.

## Authority / Non-Authority Posture

FAST, Risk 2. No `src/**`, workflow, dependency, runner, credential, product network, deployment,
Hermes, strategy, paper, execution, order, live or capital authority. No hosted Actions, no
visibility or settings change, no history rewrite. PR #246 untouched. Capital/orders: USD 0 / 0.
Independent Side19 acceptance and exact-head hosted CI are pending; ready transition and merge are
not authorized.
