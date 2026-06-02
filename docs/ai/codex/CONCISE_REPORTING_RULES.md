# Concise Reporting Rules

## Applies To

Codex and Claude Code.

## Mandatory Final PR Comment

The final PR comment is mandatory before requesting review. The PR body does not replace this final report comment. This rule cannot be waived for token savings.

## Concise Report Format

Every final PR comment must include the following sections (concise but evidence-complete):

**A. Work Package ID / package class**
**B. Branch / base / required previous merge commit**
**C. Changed files** — exact list of added and modified files
**D. Validation summary** — see rules below
**E. Boundary check** — confirm no forbidden scope, no runtime/source/tooling implementation, no dependencies/lock files, no Hermes/LLM/agent runtime, no credentials/network/trading
**F. Deferred items changed** — new, updated, or resolved entries
**G. Open issues / assumptions**
**H. Ready for review: YES/NO**

## Validation Summary Rules

For each validation command in the final report:

- State the exact command — the full invocation with all flags and arguments. Do not abbreviate with ellipses (`...`) or placeholder text.
- State exit code or pass/fail result.
- State test counts (passed, failed, error) for pytest.
- State warning counts if relevant.
- State artifact path or output path if any.

Failure output must be detailed enough to diagnose the root cause. Do not truncate failure snippets.

Concise reporting may compress raw output logs. It must not abbreviate the command invocation itself. The rule is: compress the output, never the command.

## Unavailable Tools

- Unavailable security tools (semgrep, pip-audit, etc.) must be reported as UNAVAILABLE/SKIPPED.
- Do not report unavailable tools as passed.
- Reporting a tool as UNAVAILABLE is not a failure condition for docs-only WPs, but the status must be stated honestly.

## Omission Rules

- Do not omit failed checks from the report.
- Do not omit unavailable tools from the security section.
- Do not hide boundary drift, scope expansion, or deferred items.
- Do not paste full raw test logs in PR comments unless needed to diagnose a failure — the summary counts are sufficient otherwise.
- Do not abbreviate validation commands with ellipses or placeholder text.
- Do not omit exact test counts, warning counts, or skipped-tool reasons.
- Do not use approximate wording such as "tests passed" without stating the exact counts.

## Network Usage Wording Rule

Concise reporting must use accurate network usage wording. If Remote Main Sync Gate, `git fetch`, `git pull`, `git push`, or PR publication ran, do not claim "no network was used."

Use the standard distinction wording:

> Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior.

Accurate classification is mandatory even when the concise format is applied. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`.

## PR Body

The PR body contains the review checklist, summary, files changed, safety confirmations, and known limitations. It is a complement to the final report comment, not a replacement.

## Future Validation-Output Summary Helper

A future local validation-output summary helper (designed in `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md`) may support concise reporting by producing structured command-result summaries. However, the helper must not replace command execution, required validation evidence, or the mandatory final PR comment. Using the helper does not waive any section of this document.
