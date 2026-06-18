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
- `pr_evidence_consistency_guard.py` was run with WP47 hardening flags and `--require-guard-result` on exact local drafts or on copied posted content before Ready for review: YES, and the exact guard invocation AND full guard result output (result line, checked categories, exit code) appear in both PR body and final comment.
- Full guard result output is present in both PR body and final comment: 'PR evidence consistency guard: PASS' or '... FAIL', 'Checked categories:', and 'exit 0' or 'exit 1'. A guard command invocation line alone does not satisfy this check.

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

## Posted GitHub Evidence Verification And Evidence Mode (WP58+/WP59+)

Reviewer must confirm:

**Evidence mode checks:**
1. Evidence mode declared in both PR body and final comment? (one of: `PUBLIC_VERIFIER_PASS`, `PRIVATE_REPO_MANUAL_VERIFIED`, `BLOCKED_NOT_READY`)
2. If `PUBLIC_VERIFIER_PASS`: verifier exit 0 is present; live PR was accessible to the public unauthenticated API.
3. If `PRIVATE_REPO_MANUAL_VERIFIED`: verifier unavailable/exit code documented; reason documented; all manual live verification fields complete (method, verified PR body head SHA, verified comment URL, verified comment head SHA, verified comment contains required fields).
4. If `BLOCKED_NOT_READY`: Ready for review is NO. Do not merge.
5. Latest current-final comment contains current head SHA.
6. PR body does not call manual verification "posted verifier PASS."

**Standard comment checks:**
- Latest current-final evidence comment is not merely present but:
  - Latest by timestamp (not an older stale comment).
  - Contains current head SHA.
  - Contains guard result line.
  - Contains checked categories.
  - Contains exit code.
  - Contains `Ready for review: YES`.
  - Contains `Guard input source:`.
- Older stale current-final comments are superseded by the latest.
- Reviewer did not rely on PR body alone.
- Negative test matrix present when applicable (see `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md`).

See `docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md` for full evidence mode definitions and required fields.

## Status Fragment Checks (WP86+)

Reviewer must confirm:

- `docs/status_entries/WP<NN>.md` exists and is committed on the PR branch.
- Status fragment head commit matches the PR head SHA.
- Status fragment authority posture matches the PR body and WP definition.
- Status fragment validation summary is consistent with the final comment validation results.
- Status fragment evidence mode matches the final comment evidence mode.
- Status fragment and PR body do not contradict each other on: changed files, test counts, evidence mode, or Ready for review status.

If status fragment is missing or inconsistent, the PR is not merge-ready.

## Requirement-to-Evidence Traceability Checks (WP86+, M/L/XL WPs)

Reviewer must confirm for M, L, and XL package size class WPs:

- Requirement-to-evidence traceability table is present in the PR body.
- Every row in the table has a status of SATISFIED or OPEN.
- OPEN rows are acceptable only with documented justification for deferral.
- No `Ready for review: YES` with open unaccepted rows.

## Not-Merge-Ready Review Self-Diagnosis (WP86+)

When a reviewer finds a PR not merge-ready, the AI coding agent must include a self-diagnosis block in the follow-up response before resubmitting:

```
Root cause:
Preventable: YES/NO
What should have caught it:
Immediate process change:
Durable guidance change needed: YES/NO
If YES, describe:
Follow-up defect category: (A/B/C/D/E/F/G/H/I)
```

Classification categories (from `docs/ai/codex/WP_BUNDLING_POLICY.md`):
- A = Evidence/reporting failure
- B = Repo-truth/status reconciliation failure
- C = Validation not rerun after final change
- D = Scope drift
- E = Boundary/protected-scope risk
- F = Implementation logic defect
- G = Test coverage gap
- H = External/tooling/environment limitation
- I = Reviewer-requested clarification without defect

Reviewer checks:
- Self-diagnosis block present when a same-PR follow-up correction was required.
- Classification matches the actual defect type.
- "Durable guidance change needed: YES" triggers a deferred item or future WP if no immediate fix is possible.

## Compatibility / Impossibility Table Checks (WP86+, Nontrivial WPs)

Reviewer must confirm for validator, report, schema, export, collector, workflow, L/XL, or evidence-policy WPs:

- Compatibility/impossibility table present in PR body.
- All rows with "not compatible" or "not allowed" are either resolved or explicitly deferred with justification.
- No `Ready for review: YES` if any row was incompatible and unresolved.

## Evidence Contradiction Matrix Checks (WP88+)

Reviewer must block merge if any of the following combinations are present:

| Combination found | Required action |
|---|---|
| `NOT_VERIFIED` + `Ready for review: YES` | Block merge |
| `PR body and final comment compared after posting: NO` + `Ready for review: YES` | Block merge |
| `LOCAL_DRAFT_VERIFIED` claimed as posted GitHub evidence | Block merge |
| Status fragment claims current live PR head as fixed SHA | Block merge |
| Status fragment uses `Head commit:` for currently-in-review head | Block merge |
| PR body and final comment report different current live PR head | Block merge |
| Final comment claims verification without post-posting re-fetch | Block merge |
| Multiple final evidence comments without `CURRENT FINAL WP EVIDENCE` marker on latest | Block merge |
| Status fragment and PR body disagree on validation summary | Block merge |
| Ready for review appears as YES in one surface and NO in another | Block merge |

Reviewer must also confirm:

- Status fragment uses `Validated implementation commit:` (not `Head commit:`) for the in-review validated SHA.
- Status fragment includes the required non-self-referential wording for current live PR head.
- Follow-up responses include a self-diagnosis block classifying root cause (not just the symptom).

## Result-Object Field-Coverage Checks (WP88+, Result/Report/Loader/Validator WPs)

Reviewer must confirm for WPs that introduce result objects, loaders, validators, or report generators:

- Field-coverage gate documented: all public fields enumerated and classified.
- Test proves `{f.name for f in fields(ResultType)} <= set(serialized)` or equivalent recursive scan.
- Invalid result objects are scanned, not only valid result objects.
- If a manual serializer is used, a field-coverage test is present.
- No manual serializer silently omits advisory_label, warnings, notices, or metadata fields.
