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
- `pr_evidence_consistency_guard.py` was run on local drafts before Ready for review: YES (where local drafts available), and the exact guard invocation and PASS result appear in both PR body and final comment.

See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` and `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` for the full policy, examples, and remediation guidance.
