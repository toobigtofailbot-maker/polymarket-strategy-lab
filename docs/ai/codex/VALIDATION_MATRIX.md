# Validation Matrix

## Package Classes By Risk Level

Package classes are grouped by risk level. Each class defines its minimum validation surface. Higher risk classes require stronger gates.

### Risk Level 0 — Docs / Workflow Only (Lowest Risk)

| Package class | Focused tests | Adjacent tests | Full pytest | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| docs-only policy WP | Doc content tests | Repo truth index | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| schema-only WP | Schema doc tests | Repo truth index | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow-docs-tests-only WP | Workflow/template tests | Project status / arch boundary | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow/governance WP | Workflow docs/template tests, focused docs tests, exact PR evidence reporting check | Project status wording check, network usage wording check | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| docs-tests-workflow-governance-hardening | All workflow/governance WP checks | Bundle risk class, follow-up classification | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |
| workflow-governance-docs-tests-state-machine | All workflow/governance WP checks, state machine doc present | Evidence mode declared | Required | Required | Required | Report unavailable | Required if posting claimed | Required (WP86+) |

All Risk Level 0 WPs must also confirm:
- Package size class stated.
- No `src/`, `tools/` (unless explicitly scoped), dependency, or lock-file changes.
- Exact PR evidence reporting discipline.
- Network usage wording accurate.
- Current-final evidence marker in final comment.
- Guard input source stated.
- Evidence mode declared (PUBLIC_VERIFIER_PASS / PRIVATE_REPO_MANUAL_VERIFIED / BLOCKED_NOT_READY).

### Risk Level 1 — Local/Offline Source (Low Risk)

| Package class | Focused tests | Adjacent tests | Full pytest | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| validator WP | Focused validator tests, negative-test matrix | Adjacent schema tests, architecture boundary | Required | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| report/output WP | Focused report tests, advisory output safety | Adjacent schema and boundary tests | Required | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| local/offline source WP | Focused unit tests, negative-test matrix | Architecture boundary | Required | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| local report/export WP | Offline tests with local fixtures | No credential/network tests | Required | Required | Required | gitleaks if available | Required if posting claimed | Required (WP86+) |
| github-aware-readonly-workflow-helper WP | Focused helper tests with fake responses | Docs workflow tests | Required | Required | Required | gitleaks if available | Required — posted verifier after PR posted | Required (WP86+) |

All Risk Level 1 WPs must also confirm:
- Output under ignored `local_data/` only (for report/export WPs).
- No credentials, no private endpoints, no account queries.
- Negative-test matrix present when adding validators, scorers, parsers, or filters.
- Advisory output safety helper used for output WPs if available.
- Recursive forbidden-terms scan for output surfaces.

### Risk Level 2 — Data Ingestion / External Data (Medium Risk)

| Package class | Focused tests | Adjacent tests | Full pytest | Diff scope | Artifact guard | Security | GitHub evidence re-fetch | Status fragment |
|---|---|---|---|---|---|---|---|---|
| read-only public-data WP | Offline tests; explicit-network smoke only if scoped | Boundary/scope tests | Required | Required | Required | gitleaks + pip-audit if available | Required | Required (WP86+) |
| official-client sandbox WP | Isolated sandbox tests, no `src/` import | No runtime/auth tests | Required | Required | Required | gitleaks + pip-audit | Required | Required (WP86+) |
| security/tooling WP | Tool availability checks, generated-artifact controls | Honest unavailable reporting | Required | Required | Required | All available tools | Required | Required (WP86+) |

### Risk Level 3 — Paper / Scheduler / Bot Loop (High Risk — Blocked Until Authorized)

| Package class | Minimum validation |
|---|---|
| future paper-trading package | Blocked until explicitly authorized; must prove mode separation, no live fallback, deterministic simulation boundaries. All Level 1+2 gates plus paper-mode boundary proof. |
| data ingestion WP | Blocked unless explicitly authorized; stronger rate-limit, credential, and network-boundary gates required. |
| runtime dependency WP | Blocked unless explicitly authorized by repo truth and active WP; dependency audit required; stronger security and dependency-audit gates required. |
| scheduler/bot loop WP | Blocked until explicitly authorized with kill switch, rate-limit evidence, and observability plan. |

### Risk Level 4 — Credentials / Execution / Live (Highest Risk — Blocked)

| Package class | Minimum validation |
|---|---|
| credential/auth WP | Blocked until `docs/live_trading_authorization.md` updated and credential boundary WP explicitly authorized. |
| execution WP | Blocked; requires separate authorization and risk-engine review. |
| future live-trading package | Blocked until explicitly authorized in repo truth and `docs/live_trading_authorization.md`; strongest safety, security, risk, and review gates required. |

### PR Review Package

| Package class | Validation |
|---|---|
| PR review package | PR metadata, changed files, comments, checks, final report comment, validation evidence, safety boundaries, exact PR evidence reporting discipline, status fragment, and requirement-to-evidence traceability inspected. |

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

## github-aware-readonly-workflow-helper WP

Minimum validation:
- Focused helper tests with fake GitHub API responses (no real network in unit tests).
- No auth/token/env-secret reading verified in tests.
- Docs workflow tests.
- Full pytest after final commit.
- Generated artifact guard.
- Diff scope summary.
- Code blast radius.
- PR evidence consistency guard (local).
- Posted PR evidence verifier after PR is posted.

Required guard invocation example:
```bash
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body pr_body.txt \
  --final-comment final_comment.txt \
  --expected-head <HEAD_SHA> \
  --require-guard-result \
  --require-current-final-marker \
  --require-posted-evidence-note \
  --forbid-placeholder-evidence \
  --forbid-inline-test-counts \
  --require-standard-network-wording \
  --require-ready-yes
```

Required posted verifier invocation after PR is posted:
```bash
python tools/git/posted_pr_evidence_verifier.py \
  --repo toobigtofailbot-maker/polymarket-strategy-lab \
  --pr <PR_NUMBER> \
  --expected-head <HEAD_SHA> \
  --require-current-final-marker \
  --require-guard-result \
  --require-ready-yes \
  --require-standard-network-wording \
  --forbid-placeholder-evidence \
  --forbid-inline-test-counts \
  --format text
```

Ready for review: YES requires local guard PASS and one complete evidence mode (see `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`):
- `PUBLIC_VERIFIER_PASS`: posted verifier exit 0 required.
- `PRIVATE_REPO_MANUAL_VERIFIED`: posted verifier UNAVAILABLE with exit code required; reason required; all manual live verification fields required.
- `BLOCKED_NOT_READY`: Ready for review must be NO.

Evidence mode does not replace validation. Validation proves code/docs state. Evidence mode proves PR reporting state. They are independent assessments.

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
