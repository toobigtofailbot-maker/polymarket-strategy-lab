# PR Evidence Reporting Discipline

## Status

- PR evidence reporting discipline status: WORKFLOW_GOVERNANCE_MANDATORY
- Applies to: Codex and Claude Code
- Enforcement: mandatory for every WP before Ready for review: YES
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE

## Purpose

Require exact, honest, and consistent PR evidence in every work package PR body and final top-level PR comment so reviewers never need to request the same corrections manually.

## Rule 1 — Exact Validation Commands Required

The PR body and the final top-level PR comment must include the exact full command invocation used for every validation step. This means all flags, arguments, and paths must appear verbatim.

**Acceptable:**

```
python -m pytest tests/test_pr_evidence_reporting_discipline_docs.py -v
→ 24 passed, 0 failed, 0 errors in 0.12s; exit 0
```

**Not acceptable:**

```
python -m pytest tests/test_pr_evidence_reporting_discipline_docs.py ...
→ passed
```

## Rule 2 — No Ellipses or Abbreviated Command Placeholders

Ellipses (`...`) must not appear in validation command evidence. Abbreviated helper commands, shortened flag sets, and placeholder command text are forbidden in PR body and final PR comment validation sections.

The concise-reporting model allows summarizing raw output logs. It does not allow abbreviating the command itself.

**Acceptable:** Summarize output counts concisely. State the exact command.

**Not acceptable:** `python tools/git/status_snapshot.py ...` or `python -m pytest ... -v`.

## Rule 3 — Accurate Network Usage Wording

PR body and final PR comment must use accurate network usage wording.

If Remote Main Sync Gate, `git fetch`, `git pull`, `git push`, or PR publication used network, do not say "no network was used."

**Standard wording for workflow/governance WPs:**

> Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior.

If the WP adds any runtime/API/product/account network behavior, the wording must state exactly what was added. If this WP's forbidden scope includes such behavior, stop — do not add it.

## Rule 4 — PR Body and Final PR Comment Consistency

The PR body and the final top-level PR comment must not contradict each other. Key fields that must match:

- test counts (passed, failed, errors, skipped)
- helper command invocations and their results
- network usage wording
- files changed list
- deferred items added or resolved
- Ready for review status

If a final re-run produces updated counts, update both the PR body and the final comment before marking Ready for review: YES.

## Rule 5 — Correct Counts Before Ready for Review

Stale counts, stale summaries, and stale wording must be corrected before Ready for review: YES.

If the PR body says "seven tests pass" but the actual suite has eight, the PR body must be corrected. If the final comment lists a different count than the actual run, the final comment must be corrected.

Ready for review: NO if any count or summary is known to be inaccurate.

## Rule 6 — Required Evidence Fields

For each validation command in the PR body and final PR comment:

| Field | Requirement |
|---|---|
| Exact command | Full invocation, all flags, no ellipses |
| Exit code | Numeric or pass/fail if not numeric |
| Test counts | passed / failed / errors / skipped (for pytest) |
| Warning count | If any warnings were emitted |
| Skipped tools | Report as SKIPPED_NOT_PRESENT or UNAVAILABLE/SKIPPED with reason |

## Rule 7 — Unavailable Tool Honesty

Unavailable security tools must be reported as UNAVAILABLE/SKIPPED or SKIPPED_NOT_PRESENT. They must not be described as passed.

Required helper commands that do not exist must be reported as SKIPPED_NOT_PRESENT with exact reason. Do not imply they were run.

## Rule 8 — Run PR Evidence Consistency Guard Before Ready for Review

When local PR body and final comment drafts are available, run
`tools/git/pr_evidence_consistency_guard.py` before setting Ready for review: YES.

The guard checks consistency between the two evidence surfaces and detects the
most common defects: ellipses in commands, required commands missing from one
surface, head SHA mismatch, test count mismatch, network wording gaps, and
security tool honesty conflicts.

**If the guard fails, Ready for review must be NO until all failures are corrected and the guard passes.**

Report the exact guard invocation and result (PASS/FAIL) in both the PR body and final comment.

If local draft files are used (not the already-posted GitHub content), state that fact. Do not commit local draft files.

See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` for full CLI reference.

## Ready-for-Review Gate

Ready for review: YES requires all of the following to be true:

- [ ] Exact full validation commands appear in PR body (no ellipses).
- [ ] Exact full validation commands appear in final PR comment (no ellipses).
- [ ] Network usage wording is accurate.
- [ ] PR body and final PR comment are consistent (matching counts and results).
- [ ] No stale counts or stale summary text.
- [ ] Unavailable tools reported honestly.
- [ ] Final top-level PR comment is posted (not only the PR body).
- [ ] `pr_evidence_consistency_guard.py` run on local drafts and result reported (where local drafts available).

If any item is NO, set Ready for review: NO and correct the evidence before requesting review.

## Reviewer Action When Evidence Is Defective

If a reviewer finds any of the following, the PR is not merge-ready:

- Ellipses in validation command evidence.
- Abbreviated helper command invocations.
- Network wording that says "no network" when git/PR network was used.
- PR body and final PR comment that contradict each other on counts or results.
- Stale counts that do not match the last reported test run.
- Unavailable tools described as passed.
- Missing final top-level PR comment.

Correct action: mark follow-up required; do not merge.

## Applies To

All WPs executed by Codex and Claude Code on this repository.

## Examples

### Acceptable PR Body Validation Section

```
### Tests

**Focused test:**
python -m pytest tests/test_pr_evidence_reporting_discipline_docs.py -v
→ 24 passed, 0 failed, 0 errors; exit 0

**Full suite:**
python -m pytest
→ 312 passed, 0 failed, 0 errors, 2 warnings; exit 0

**Whitespace check:**
git diff --check
→ no whitespace errors; exit 0

**Generated artifact guard:**
python tools/git/preflight_generated_artifact_guard.py
→ Generated artifact guard passed; exit 0
```

### Not Acceptable PR Body Validation Section

```
### Tests

python -m pytest tests/test_pr_evidence_reporting_discipline_docs.py ...
→ passed

Full suite passed.

git diff --check → ok
```

### Acceptable Network Wording

> Network was used only for Remote Main Sync Gate / git remote synchronization
> and PR push/publication. This WP adds no runtime network behavior, no API
> polling, no account access, and no product network behavior.

### Not Acceptable Network Wording

> No network was used.

(Incorrect if `git fetch`, `git pull`, `git push`, or PR publication ran.)

## Cross-References

- `AGENTS.md` — binding Codex and Claude Code operating rules
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — final report format
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` — concise reporting rules
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — Standard PR Evidence Reporting Discipline Block
- `docs/ai/codex/VALIDATION_MATRIX.md` — package-class validation requirements
- `docs/work_package_template.md` — WP template with evidence discipline section
- `docs/review_checklist.md` — reviewer-facing evidence checks
