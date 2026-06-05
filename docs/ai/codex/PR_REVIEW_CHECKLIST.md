# PR Review Checklist

Reviewers and Codex Review Mode must verify:

- PR metadata inspected.
- Base commit equals required previous merge commit when the work package specifies one.
- Changed-file set matches the work package objective.
- Forbidden files and protected paths are untouched.
- Full final report PR comment exists.
- PR body alone is not treated as sufficient.
- `docs/project_status.md` security wording uses the current WP number.
- Unavailable tools are not described as passed.
- Tests were rerun after the final commit.
- Generated-artifact guard was rerun after the final commit.
- No generated artifacts, `local_data/`, local virtual environments, or security outputs are committed.
- No dependency or lock files changed unless explicitly scoped.
- Deferred items were updated accurately.
- Repo-truth docs were updated accurately.
- Safety boundaries remain intact.
- Ready for review: YES/NO is stated.

## PR Evidence Reporting Discipline Checks

Reviewers must also verify the following evidence discipline checks. If any item fails, the PR is not merge-ready; mark follow-up required rather than merging.

- All validation commands in the PR body use exact full invocations (no ellipses, no placeholder text, no abbreviated flags).
- All validation commands in the final PR comment use exact full invocations (no ellipses, no placeholder text, no abbreviated flags).
- Helper validation commands (`status_snapshot.py`, `diff_scope_summary.py`, `code_blast_radius.py`, `preflight_sync_main.py`, `preflight_generated_artifact_guard.py`) appear with all flags used, not abbreviated.
- No `...` appears after any command name in validation evidence sections.
- Network usage wording accurately distinguishes git/PR workflow network use from runtime/API/product/account network behavior.
- If `git fetch`, `git pull`, `git push`, or PR publication ran, the PR does not claim "no network was used."
- PR body and final PR comment are consistent: test counts, command results, files changed, and network wording must match.
- No stale counts appear in the PR body or final PR comment (counts must reflect the actual last run after the final commit).
- Unavailable security tools are reported as UNAVAILABLE/SKIPPED or SKIPPED_NOT_PRESENT, not as passed.
- Final top-level PR comment is present (not only the PR body).
- Ready for review: YES is not set if any evidence defect remains uncorrected.
- `pr_evidence_consistency_guard.py` was run with WP47 hardening flags on exact local drafts or on copied posted content before Ready for review: YES, and the exact guard invocation and PASS result appear in both PR body and final comment.

**WP47 additional reviewer checks (posted evidence hardening):**
- Identify the current final evidence comment by the marker "CURRENT FINAL WP EVIDENCE". Do not treat older stale comments as current if a newer comment with this marker explicitly supersedes them.
- Verify that the reviewer is reading the latest live PR body (or clearly state if using a PDF/export/screenshot of the PR body at a specific point in time).
- No parenthetical test counts appear in file lists or summary lines (e.g., "tests (34 tests)" is forbidden outside validation result sections).
- The final PR body and current final evidence comment guard invocation includes WP47 hardening flags where practical: `--forbid-inline-test-counts`, `--forbid-placeholder-evidence`, `--require-current-final-marker`, `--require-posted-evidence-note`.
- Both PR body and final comment include a "Guard input source:" line.

**WP54 additional reviewer checks (bundling policy and follow-up classification):**
- Reviewer checks the package size class (S/M/L/XL) is stated in the PR body.
- Reviewer checks the bundle is within one risk class (no mode boundary crossed).
- Reviewer checks no forbidden bundle type is present (see `docs/ai/codex/WP_BUNDLING_POLICY.md` for the forbidden bundle list).
- Reviewer checks the follow-up classification section is accurate: if a follow-up occurred it must be classified; if none occurred it must say so explicitly.
- Reviewer reads the latest current-final evidence comment, not an older superseded comment.
- Reviewer checks that the PR body and latest current-final comment both reflect any follow-up classification.
- Reviewer checks the "Guard input source:" line states whether guard ran on exact local drafts intended for posting or on copied posted content.
- Reviewer checks whether evidence was based on local drafts or copied posted GitHub content; if local drafts, reviewer may wish to verify that the posted content matches.
- Reviewer checks whether `docs/project_status.md` was reconciled after the prior WP's merge in this same WP.
- Reviewer checks that the current WP's security wording in `docs/project_status.md` names the current WP number, not a prior WP.

See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`, `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`, and `docs/ai/codex/WP_BUNDLING_POLICY.md` for the full policy, examples, and remediation guidance.
