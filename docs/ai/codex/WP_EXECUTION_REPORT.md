# WP Execution Report

Codex must post a full final report as a top-level PR comment before requesting review. The PR body does not replace this final report.

## Required Sections

A. Work Package ID / package class

B. Branch / base

C. Repo-truth discovery

D. Delivered changes

E. Validation results

F. Validation gates

G. Repo-truth updates

H. Deferred items

I. Forbidden-scope check

J. Generated-artifact check

K. Security checks

L. Network usage

M. PR / push status

N. Open escalations / assumptions

O. Ready for review: YES/NO

## Reporting Rules

- Identify the actual branch, base branch, head commit, and PR link.
- State exact validation commands, result counts, and exit codes where available.
- State whether tests were run after the final commit.
- State whether the generated-artifact guard was run after the final commit.
- State whether current-WP `docs/project_status.md` wording was checked.
- If validation cannot be run, do not claim merge-ready.
- Do not use "passed" wording for unavailable tools.
- PR body alone is not sufficient; the full final report PR comment is mandatory unless PR creation itself is explicitly waived by the active work package.

## Concise Reporting

Apply the concise-reporting format from `docs/ai/codex/CONCISE_REPORTING_RULES.md`:

- Report validation summary counts (command, exit code, pass/fail, test counts, warnings).
- Include failure snippets when any check fails; do not truncate failure evidence.
- Do not paste full raw test logs unless needed to diagnose a failure.
- Report unavailable security tools as UNAVAILABLE/SKIPPED, never as passed.

Concise reporting must not reduce required evidence. If in doubt, include more evidence, not less.
