# Validation Matrix

## Package Classes

| Package class | Minimum validation |
|---|---|
| docs-only policy WP | Changed-file scope check, focused doc tests, full pytest after final commit, generated-artifact guard after final commit, exact PR evidence reporting check. |
| schema-only WP | Schema doc tests, repo-truth index tests, full pytest after final commit, no runtime implementation paths, exact PR evidence reporting check. |
| workflow/governance WP | Workflow docs/template tests, focused docs tests, full pytest after final commit, project-status current-WP wording check, exact PR evidence reporting check, network usage wording check. |
| docs-tests-workflow-governance-hardening | All workflow/governance WP checks plus: package size class stated, risk-class bundle justification, follow-up classification section, guard input source line, posted evidence self-check declaration, no forbidden bundle type, current-final evidence marker. |
| local report/export WP | Offline tests with local fixtures, output under ignored `local_data/`, no credentials, no private endpoints, exact PR evidence reporting check. |
| read-only public-data WP | Offline tests, explicit-network smoke only if scoped, bounded public-data behavior, ignored output under `local_data/`, exact PR evidence reporting check. |
| official-client sandbox WP | Isolated sandbox tests, no project dependency, no `src/` runtime import, explicit-network public read-only probes only if scoped, exact PR evidence reporting check. |
| security/tooling WP | Tool availability checks, generated-artifact controls, honest unavailable-tool reporting, no broad suppressions, exact PR evidence reporting check. |
| runtime dependency WP | Blocked unless explicitly authorized by repo truth and active WP; stronger security and dependency-audit gates required; exact PR evidence reporting check. |
| PR review package | PR metadata, changed files, comments, checks, final report comment, validation evidence, safety boundaries, and exact PR evidence reporting discipline inspected. |
| future paper-trading package | Blocked until explicitly authorized; must prove mode separation, no live fallback, deterministic simulation boundaries. |
| future live-trading package | Blocked until explicitly authorized in repo truth and `docs/live_trading_authorization.md`; strongest safety, security, risk, and review gates required. |

## All Work Packages

- Changed-file scope check.
- Forbidden-path preservation.
- Generated-artifact guard after final commit.
- Full pytest after final commit unless the active WP explicitly defines a narrower gate and explains why.
- `docs/project_status.md` current-WP wording check.
- Dependency and lock-file preservation unless explicitly scoped.
- Exact PR evidence reporting discipline: exact full validation commands in PR body and final PR comment (no ellipses, no abbreviated commands, no placeholder text), accurate network usage wording, consistent counts between PR body and final comment, and stale counts corrected before Ready for review: YES. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`.
- PR evidence consistency guard: run `tools/git/pr_evidence_consistency_guard.py` on exact local drafts intended for posting (or on copied posted GitHub content if evidence was posted before the guard ran). Include WP47 hardening flags where local PR body/final comment drafts are available:
  ```
  python tools/git/pr_evidence_consistency_guard.py --pr-body <FINAL_PR_BODY_TEXT> --final-comment <CURRENT_FINAL_EVIDENCE_COMMENT_TEXT> --expected-head <HEAD_SHA> --required-command "python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries" --required-command "python tools/git/diff_scope_summary.py --base main --head HEAD --package-class local-offline-stdlib-governance-helper-hardening --allowed-prefix docs/ --allowed-prefix tests/ --allowed-prefix tools/git/pr_evidence_consistency_guard.py --forbidden-prefix src/" --require-standard-network-wording --require-ready-yes --forbid-inline-test-counts --forbid-placeholder-evidence --require-current-final-marker --require-posted-evidence-note
  ```
  If the guard fails, Ready for review must be NO. Report exact guard invocation and result in both PR body and final comment. See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.

## Docs, Schema, And Workflow WPs

- Focused doc tests.
- Full pytest.
- No runtime/source changes unless explicitly scoped.

## Validation-Output Summarization

Apply the summarization rules from `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`:

- Report exact command, exit code (if available), pass/fail, test counts, warning count, and output path for each validation step.
- Include failure snippets when any check fails.
- Do not summarize away failure evidence.
- Do not report unavailable tools as passed.

A future validation-output summary helper (designed in `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md`) may summarize validation results in a compact format. However, all mandatory validation commands remain mandatory regardless of whether the helper is used. The helper summarizes evidence; it does not replace it. Design docs do not authorize implementation until a separate approved implementation WP.

## Read-Only Public-Data WPs

- Offline tests.
- Explicit-network smoke only if scoped.
- Output stays under ignored `local_data/`.
- No credentials, authentication, private endpoints, account queries, or private data.

## Runtime, Dependency, Paper, And Live WPs

These package classes are blocked unless explicitly authorized by repo truth and the active work package. They require stronger security, dependency, safety, and review gates than docs-only or schema-only work.
