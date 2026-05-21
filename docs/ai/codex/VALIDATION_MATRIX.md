# Validation Matrix

## Package Classes

| Package class | Minimum validation |
|---|---|
| docs-only policy WP | Changed-file scope check, focused doc tests, full pytest after final commit, generated-artifact guard after final commit. |
| schema-only WP | Schema doc tests, repo-truth index tests, full pytest after final commit, no runtime implementation paths. |
| workflow/governance WP | Workflow docs/template tests, full pytest after final commit, project-status current-WP wording check. |
| local report/export WP | Offline tests with local fixtures, output under ignored `local_data/`, no credentials, no private endpoints. |
| read-only public-data WP | Offline tests, explicit-network smoke only if scoped, bounded public-data behavior, ignored output under `local_data/`. |
| official-client sandbox WP | Isolated sandbox tests, no project dependency, no `src/` runtime import, explicit-network public read-only probes only if scoped. |
| security/tooling WP | Tool availability checks, generated-artifact controls, honest unavailable-tool reporting, no broad suppressions. |
| runtime dependency WP | Blocked unless explicitly authorized by repo truth and active WP; stronger security and dependency-audit gates required. |
| PR review package | PR metadata, changed files, comments, checks, final report comment, validation evidence, and safety boundaries inspected. |
| future paper-trading package | Blocked until explicitly authorized; must prove mode separation, no live fallback, deterministic simulation boundaries. |
| future live-trading package | Blocked until explicitly authorized in repo truth and `docs/live_trading_authorization.md`; strongest safety, security, risk, and review gates required. |

## All Work Packages

- Changed-file scope check.
- Forbidden-path preservation.
- Generated-artifact guard after final commit.
- Full pytest after final commit unless the active WP explicitly defines a narrower gate and explains why.
- `docs/project_status.md` current-WP wording check.
- Dependency and lock-file preservation unless explicitly scoped.

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
