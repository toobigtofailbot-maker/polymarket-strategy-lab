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

## PR Body And Final Comment Evidence Discipline

The PR body and the final top-level PR comment must both comply with the following rules before Ready for review: YES. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` for the full policy, examples, and reviewer guidance.

**Exact validation command requirement:**
Every validation step must appear as the exact full command invocation — all flags, arguments, and paths. Abbreviated forms and ellipses (`...`) are forbidden in validation evidence.

**No ellipses or placeholder commands:**
Do not write `python -m pytest tests/test_foo.py ...` or `python tools/git/status_snapshot.py ...`. The full command with all actual flags must appear verbatim.

**Exact result counts:**
State the exact number of tests passed, failed, errors, and skipped. State warning counts. State exit codes where available. Do not use approximate wording such as "most passed" or "tests passed" without counts.

**PR body and final PR comment consistency:**
If a re-run after the final commit produces updated counts, update both the PR body and the final PR comment before requesting review. The two must not contradict each other.

**Stale count correction required:**
If a count in the PR body or final PR comment is known to be stale (e.g. the test suite grew or a helper was added), correct it before Ready for review: YES.

**Network usage wording accuracy:**
If Remote Main Sync Gate, `git fetch`, `git pull`, `git push`, or PR publication ran, do not claim "no network was used." Use the standard distinction wording:

> Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior.

**PR evidence consistency guard:**
Run `tools/git/pr_evidence_consistency_guard.py` on local PR body and final comment drafts before Ready for review: YES. Report the exact guard invocation and result (PASS/FAIL) in both the PR body and final comment. If the guard fails, correct all failures before requesting review. Do not commit local draft files. See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.

**Ready for review gate:**
Ready for review: YES is forbidden if any of the following remain:
- Ellipses or abbreviated commands in validation evidence.
- Stale or inaccurate counts.
- Inaccurate network usage wording.
- PR body and final PR comment inconsistency.
- Missing final top-level PR comment.
- Unavailable tools described as passed.
- `pr_evidence_consistency_guard.py` fails on local drafts.

## Concise Reporting

Apply the concise-reporting format from `docs/ai/codex/CONCISE_REPORTING_RULES.md`:

- Report validation summary counts (command, exit code, pass/fail, test counts, warnings).
- Include failure snippets when any check fails; do not truncate failure evidence.
- Do not paste full raw test logs unless needed to diagnose a failure.
- Report unavailable security tools as UNAVAILABLE/SKIPPED, never as passed.

Concise reporting must not reduce required evidence. Concise reporting may compress raw output logs but must never abbreviate the command invocation itself. If in doubt, include more evidence, not less.
