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

- State the exact command.
- State exit code or pass/fail result.
- State test counts (passed, failed, error) for pytest.
- State warning counts if relevant.
- State artifact path or output path if any.

Failure output must be detailed enough to diagnose the root cause. Do not truncate failure snippets.

## Unavailable Tools

- Unavailable security tools (semgrep, pip-audit, etc.) must be reported as UNAVAILABLE/SKIPPED.
- Do not report unavailable tools as passed.
- Reporting a tool as UNAVAILABLE is not a failure condition for docs-only WPs, but the status must be stated honestly.

## Omission Rules

- Do not omit failed checks from the report.
- Do not omit unavailable tools from the security section.
- Do not hide boundary drift, scope expansion, or deferred items.
- Do not paste full raw test logs in PR comments unless needed to diagnose a failure — the summary counts are sufficient otherwise.

## PR Body

The PR body contains the review checklist, summary, files changed, safety confirmations, and known limitations. It is a complement to the final report comment, not a replacement.
