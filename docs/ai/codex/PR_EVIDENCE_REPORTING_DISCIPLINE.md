# PR Evidence Reporting Discipline

## Status

- PR evidence reporting discipline status: WORKFLOW_GOVERNANCE_MANDATORY
- Applies to: Codex and Claude Code
- Enforcement: mandatory for every WP before Ready for review: YES
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE

## Purpose

Require exact, honest, and consistent PR evidence in every work package PR body and final top-level PR comment so reviewers never need to request the same corrections manually.

**After WP91:** PR evidence reporting discipline applies to the PR body and the stable/non-self-referential status fragment. Final GitHub comments are optional and non-canonical. Absence of a final comment is not a merge blocker after WP91. If an optional final comment is posted, it must not contradict the PR body.

## Rule 1 — Exact Validation Commands Required

The PR body and the final top-level PR comment must include the exact full command invocation used for every validation step. This means all flags, arguments, and paths must appear verbatim.

**After WP91:** The PR body is the required surface for exact validation command evidence. A final comment is not required. If a final comment is voluntarily posted, it must not contradict the PR body.

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

**After WP91:** The PR body and status fragment must not contradict each other. If an optional final comment is posted, it must not contradict the PR body. No final comment is required for merge readiness.

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

**After WP91:** Required evidence fields apply to the PR body. Status fragments may reference stable validation evidence. Optional final comments are not required to contain command evidence.

## Rule 7 — Unavailable Tool Honesty

Unavailable security tools must be reported as UNAVAILABLE/SKIPPED or SKIPPED_NOT_PRESENT. They must not be described as passed.

Required helper commands that do not exist must be reported as SKIPPED_NOT_PRESENT with exact reason. Do not imply they were run.

## Rule 8 — Current Final Evidence Comments Must Be Marked (WP86–WP90 Only; Optional After WP91)

**After WP91:** Final GitHub evidence comments are optional and non-canonical. Rule 8 applies only if a final comment is voluntarily posted.

If a final comment is voluntarily posted after WP91, it should state it is optional and non-canonical, and must not contradict the PR body.

**Through WP90 (historical):** When posting a new final evidence comment that superseded older comments, the new comment was required to start with:

> CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments

Old evidence comments may remain visible on the PR. Reviewers must identify the current final evidence comment by this marker, not by scroll position or date. If the posted final evidence changes after the initial comment (e.g., a re-run corrects counts), the updated comment must include the current-final marker.

## Rule 9 — Inline Test Counts in File Lists Are Forbidden

Do not write test counts in parenthetical file-list descriptions or summary
phrases such as "focused tests (34 tests)" or "tests (33 tests)". These counts
drift when the test suite changes and are not treated as validation evidence.

**Acceptable:** Put test counts only in the validation result section:

```
python -m pytest tests/tools/git/test_pr_evidence_consistency_guard.py -v
→ 49 passed, 0 failed, 0 errors; exit 0
```

**Not acceptable:** `tests/tools/git/test_pr_evidence_consistency_guard.py (49 focused tests)`

## Rule 10 — Exact Posted Evidence or Exact Local-to-Be-Posted Evidence Must Be Checked

The PR evidence consistency guard must be run on:
- The exact local draft text intended for posting as the PR body and current final evidence comment; or
- The exact text that was copied from the already-posted GitHub PR body and current final evidence comment.

Running the guard only on intermediate or earlier drafts is insufficient if
the posted content later changed. Intermediate draft checks do not count as
verification of posted evidence.

**After WP91:** The guard must be run on the PR body draft. A final comment draft is not required after WP91.

## Rule 11 — Supersede Stale Older Comments Explicitly (WP86–WP90 Only)

**After WP91:** Final comments are optional. If no final comment is posted, nothing to supersede.

**Through WP90 (historical):** If an earlier evidence comment contains stale counts, stale SHA, or incorrect evidence, the current final evidence comment must explicitly state that it supersedes earlier comments. Use the required marker:

> CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments

Reviewers must not treat stale earlier comments as current if a newer comment with this marker explicitly supersedes them.

## Rule 13 — Posted Evidence Self-Check Source Must Be Declared (WP54)

The local guard checks local text files only. It does not fetch or validate live GitHub PR body or posted PR comments.

Before setting Ready for review: YES, Claude Code must satisfy one of the following conditions and state which was used in both the PR body and the final comment:

1. **Guard ran on exact local drafts intended for posting.** The PR body and current final evidence comment texts are the exact texts that will be posted (or were just posted) without further change. State: "Guard input source: exact local drafts intended for posting."

2. **Guard ran on copied posted GitHub content.** The already-posted PR body and the latest current-final evidence comment were copied into local temporary files and the guard was run on those copies. State: "Guard input source: copied from posted GitHub PR body and current-final comment."

**If any posted evidence changes after the guard's last run, the guard must be rerun on the updated content.** If Claude Code cannot confirm the live GitHub content matches what the guard checked, it must state that limitation and may not claim posted evidence was verified.

Running the guard only on pre-posting drafts that differ from what was posted is insufficient. Running the guard only on intermediate drafts is insufficient.

**After WP91:** The "Guard input source" declaration belongs in the PR body. A final comment is not required after WP91. If no final comment is posted, only the PR body guard input source needs to be declared.

## Rule 12 — Run PR Evidence Consistency Guard Before Ready for Review (with WP47 + WP54 Flags)

When local PR body and final comment drafts are available, run
`tools/git/pr_evidence_consistency_guard.py` with WP47 hardening flags and the
WP54 `--require-guard-result` flag before setting Ready for review: YES.

The guard checks consistency between the two evidence surfaces and detects the
most common defects: ellipses in commands, required commands missing from one
surface, head SHA mismatch, test count mismatch, network wording gaps, security
tool honesty conflicts, and missing guard result output.

**If the guard fails, Ready for review must be NO until all failures are corrected and the guard passes.**

Report the exact guard invocation AND the full guard result output (result line, checked categories, and exit code) in both the PR body and final comment. A guard command invocation line alone does not satisfy this requirement.

If local draft files are used (not the already-posted GitHub content), state that fact. Do not commit local draft files.

See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` for full CLI reference.

**After WP91:** The guard runs on the PR body. A final comment is not required after WP91. See the post-WP91 invocation pattern in `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.

## Rule 14 — Live Posted GitHub Evidence Verification And Evidence Mode Selection (WP59+)

Passing the local guard is necessary but not sufficient if GitHub content was posted or edited afterward.

Before `Ready for review: YES`, Claude Code must select exactly one evidence mode per `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md`:

- `PUBLIC_VERIFIER_PASS` — verifier ran and returned exit 0.
- `PRIVATE_REPO_MANUAL_VERIFIED` — verifier unavailable (exit 3 or other); manual live verification performed with all required fields.
- `BLOCKED_NOT_READY` — manual verification incomplete or blocked; Ready must be NO.

**Critical distinction:**

`PUBLIC_VERIFIER_FAIL` means the verifier ran and detected a posted evidence defect (stale head, missing final comment, missing guard result, mismatched SHAs, or other verifier-detected issue). Result: `Ready for review: NO`.

`PUBLIC_VERIFIER_UNAVAILABLE` means the public unauthenticated verifier cannot access the repo/PR/comments due to private repo, access denied, rate limit, or tool/network limitation. Result: not itself a defect. May proceed only through `PRIVATE_REPO_MANUAL_VERIFIED` if all manual fields are complete.

**Do not write `Posted GitHub evidence verifier: PASS` unless the verifier actually returned exit 0.**

**Manual live verification must be reported as manual live verification, not as posted verifier PASS.**

PR body and final comment must both include the evidence mode declaration, verifier command and result, and all required mode fields after WP59.

The ready-for-review checklist must include:
- Evidence mode declared.
- If `PUBLIC_VERIFIER_PASS`: verifier exit 0 present and live PR accessible.
- If `PRIVATE_REPO_MANUAL_VERIFIED`: verifier unavailable/exit code documented, reason documented, all manual live verification fields complete.
- Latest current-final comment URL.
- Confirmation that the latest current-final comment head SHA matches the PR head SHA.

**After WP91:** Latest current-final comment URL and confirmation of current-final comment head SHA are not required after WP91. The evidence mode declaration belongs in the PR body only. A final comment is not required for merge readiness.

## Ready-for-Review Gate

Ready for review: YES requires all of the following to be true:

- [ ] Exact full validation commands appear in PR body (no ellipses).
- [ ] Network usage wording is accurate.
- [ ] No stale counts or stale summary text.
- [ ] Unavailable tools reported honestly.
- [ ] No parenthetical test counts in file lists or summary sections.
- [ ] No placeholder evidence tokens in PR body.
- [ ] PR body includes a "Guard input source:" line.
- [ ] Guard input source line declares whether guard ran on exact local drafts intended for posting or on copied posted GitHub content.
- [ ] `pr_evidence_consistency_guard.py` run with applicable hardening flags on exact local drafts or on copied posted content, and result reported.
- [ ] Full guard result output (result line, checked categories, exit code) appears in PR body — not just the command invocation.
- [ ] Evidence mode declared in PR body (one of: `PUBLIC_VERIFIER_PASS`, `PRIVATE_REPO_MANUAL_VERIFIED`, `BLOCKED_NOT_READY`).
- [ ] Evidence mode is not `BLOCKED_NOT_READY` (if it is, Ready must be NO).
- [ ] If `PUBLIC_VERIFIER_PASS`: verifier actually returned exit 0 — not called PASS based on manual inspection.
- [ ] If `PRIVATE_REPO_MANUAL_VERIFIED`: all required manual verification fields present; verifier UNAVAILABLE + exit code documented; reason documented.
- [ ] If a final comment was voluntarily posted: final comment does not contradict PR body and does not claim canonical evidence authority.

**After WP91:** A final top-level PR comment is no longer required for merge readiness. The following checklist items from the WP86–WP90 transition period are retired as mandatory requirements (they apply only if a final comment is voluntarily posted):

- Final top-level PR comment is posted (optional after WP91; not required for merge readiness)
- Final top-level PR comment starts with "CURRENT FINAL WP EVIDENCE" if it supersedes older comments (optional after WP91)
- Both PR body and final comment are consistent (only if a final comment is posted)
- Both PR body and final comment include a "Guard input source:" line (only if a final comment is posted)
- Full guard result output appears in both PR body and final comment (only if a final comment is posted)
- Evidence mode declared in both PR body and final comment (only if a final comment is posted)

If any required item is NO, set Ready for review: NO and correct the evidence before requesting review.

## Reviewer Action When Evidence Is Defective

If a reviewer finds any of the following, the PR is not merge-ready:

- Ellipses in validation command evidence.
- Abbreviated helper command invocations.
- Network wording that says "no network" when git/PR network was used.
- PR body and final PR comment that contradict each other on counts or results.
- Stale counts that do not match the last reported test run.
- Unavailable tools described as passed.
- Missing final top-level PR comment (WP86–WP90 only; after WP91, absence is not a merge blocker — see `docs/ai/codex/FINAL_COMMENT_POLICY.md`).

Correct action: mark follow-up required; do not merge.

**After WP91:** Absence of a final top-level PR comment is not a defect. If an optional final comment is posted and contradicts the PR body, mark follow-up required.

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

## Rule 15 — Local Drafts Do Not Count As Posted GitHub Evidence (WP86+)

A local draft written on disk — even if it is byte-for-byte identical to what will be posted — is `LOCAL_DRAFT_VERIFIED`, not `POSTED_GITHUB_API_VERIFIED` and not `MANUAL_UI_VERIFIED`.

Required evidence tokens:

| Evidence type | Token |
|---|---|
| Local draft only — guard ran on files not yet posted | `LOCAL_DRAFT_VERIFIED` |
| Posted GitHub PR body/comment confirmed via API (verifier exit 0) | `POSTED_GITHUB_API_VERIFIED` |
| Posted GitHub PR body/comment confirmed via manual UI inspection | `MANUAL_UI_VERIFIED` |
| Not verified | `NOT_VERIFIED` |

When a WP claims a posted GitHub PR body or posted final evidence comment is verified, the actor must re-fetch that posted GitHub state after posting. Drafting and checking locally without re-fetching is `LOCAL_DRAFT_VERIFIED`.

`Ready for review: YES` with `LOCAL_DRAFT_VERIFIED` is only allowed when the WP package class explicitly permits it (e.g., the active WP selects `PRIVATE_REPO_MANUAL_VERIFIED` and documents manual UI inspection as the verification method).

## Rule 16 — Status Fragments As Committed Evidence Records (WP86+)

Every WP from WP86 onward must commit a status fragment at `docs/status_entries/WP<NN>.md` on the WP branch.

The status fragment is a committed evidence record. It is the preferred primary evidence surface because it cannot be accidentally superseded by a later GitHub comment.

The status fragment must be consistent with the PR body on all key fields: head commit, changed files, validation results, evidence mode, and Ready for review status. After WP91, if an optional final comment is posted, the status fragment must not contradict it either.

If the status fragment and the PR body contradict each other, the PR is not merge-ready. After WP91, a final comment is not required, but if posted, it must not contradict the status fragment or PR body.

See `docs/status_entries/README.md` for the required format.

## Cross-References

- `AGENTS.md` — binding Codex and Claude Code operating rules
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — final report format
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` — concise reporting rules
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — Standard PR Evidence Reporting Discipline Block
- `docs/ai/codex/VALIDATION_MATRIX.md` — package-class validation requirements
- `docs/work_package_template.md` — WP template with evidence discipline section
- `docs/review_checklist.md` — reviewer-facing evidence checks
- `docs/status_entries/README.md` — committed per-WP evidence fragment convention (WP86+)
- `docs/ai/codex/WP_DRAFTING_STANDARD.md` — full evidence model and drafting standard (WP86+)
