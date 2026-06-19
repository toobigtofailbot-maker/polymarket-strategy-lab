# WP Execution Report

**After WP91:** A full final report as a top-level PR comment is optional and non-canonical. The PR body is the current review evidence surface. Absence of a final comment is not a merge blocker after WP91. If an optional final comment is posted, it must state it is optional/non-canonical and must not contradict the PR body.

## Required Sections

A. Work Package ID / package class / package size class

B. Branch / base / head SHA

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

N. Follow-up process-defect classification

O. Guard input source

P. Status fragment (WP86+): docs/status_entries/WP<NN>.md committed: YES/NO

Q. Requirement-to-evidence traceability (M/L/XL WPs)

R. Open escalations / assumptions

S. Ready for review: YES/NO

## Reporting Rules

- Identify the actual branch, base branch, head commit, and PR link.
- State exact validation commands, result counts, and exit codes where available.
- State whether tests were run after the final commit.
- State whether the generated-artifact guard was run after the final commit.
- State whether current-WP `docs/project_status.md` wording was checked.
- If validation cannot be run, do not claim merge-ready.
- Do not use "passed" wording for unavailable tools.
- After WP91, the PR body is sufficient as the current review evidence surface. A final top-level PR comment is optional and non-canonical; absence is not a merge blocker after WP91.

## PR Body And Final Comment Evidence Discipline

**After WP91:** The PR body must comply with the following rules before Ready for review: YES. A final top-level PR comment is optional and non-canonical after WP91. If posted, it must not contradict the PR body and must state it is optional/non-canonical. See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` for the full policy, examples, and reviewer guidance.

**Exact validation command requirement:**
Every validation step must appear as the exact full command invocation — all flags, arguments, and paths. Abbreviated forms and ellipses (`...`) are forbidden in validation evidence.

**No ellipses or placeholder commands:**
Do not write `python -m pytest tests/test_foo.py ...` or `python tools/git/status_snapshot.py ...`. The full command with all actual flags must appear verbatim.

**Exact result counts:**
State the exact number of tests passed, failed, errors, and skipped. State warning counts. State exit codes where available. Do not use approximate wording such as "most passed" or "tests passed" without counts.

**PR body and status fragment consistency:**
If a re-run after the final commit produces updated counts, update the PR body before requesting review. After WP91, if an optional final comment is posted, the counts must not contradict the PR body.

**Stale count correction required:**
If a count in the PR body or final PR comment is known to be stale (e.g. the test suite grew or a helper was added), correct it before Ready for review: YES.

**Network usage wording accuracy:**
If Remote Main Sync Gate, `git fetch`, `git pull`, `git push`, or PR publication ran, do not claim "no network was used." Use the standard distinction wording:

> Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior.

**PR evidence consistency guard:**
Run `tools/git/pr_evidence_consistency_guard.py` on the local PR body draft before Ready for review: YES. After WP91, if an optional final comment is posted, also run the guard against it. Report the exact guard invocation and result (PASS/FAIL) in the PR body (and in the optional final comment if posted). If the guard fails, correct all failures before requesting review. Do not commit local draft files. See `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.

**Current final evidence marker requirement (Historical WP86–WP90 only; not active after WP91):**

**After WP91:** A final comment is not required. If an optional final comment is posted, the CURRENT FINAL WP EVIDENCE marker is not required; the comment must state it is optional and non-canonical.

**Historical WP86–WP90 only:** The final top-level PR comment must start with or contain:

> CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments

This marker was required when the comment superseded earlier evidence comments so reviewers could identify the current evidence.

**Guard input source requirement:**
The PR body must include a "Guard input source:" line. After WP91, only the PR body guard input source is required. If a final comment is voluntarily posted, it may also include a guard input source line.
Example: `Guard input source: exact local drafts intended for posting`

**No inline test counts in file lists:**
Do not write test counts in file-list descriptions or summary parentheticals.
Test counts belong only in validation result sections.

**Ready for review gate:**
Ready for review: YES is forbidden if any of the following remain:
- Ellipses or abbreviated commands in validation evidence in PR body.
- Stale or inaccurate counts in PR body.
- Inaccurate network usage wording.
- PR body contradicts status fragment.
- Unavailable tools described as passed.
- `pr_evidence_consistency_guard.py` fails on local drafts.
- Parenthetical test counts appearing in file lists or summaries.
- Placeholder evidence tokens in PR body.
- "Guard input source:" note missing from PR body.

**After WP91 (not active merge blockers):**
- Missing final top-level PR comment (WP86–WP90 only; absence is not a merge blocker after WP91).
- Final comment missing the current-final evidence marker (WP86–WP90 only; not required after WP91).
- "Guard input source:" note missing from final comment (only required in final comment if a final comment is voluntarily posted after WP91).

## R. Posted GitHub Evidence Verification And Evidence Mode (WP59+)

Before `Ready for review: YES`, declare exactly one evidence mode. Required fields vary by mode.

**Evidence mode block (required in PR body; after WP91, final comment is not required):**

```
Evidence mode: <PUBLIC_VERIFIER_PASS / PRIVATE_REPO_MANUAL_VERIFIED / BLOCKED_NOT_READY>
Posted GitHub evidence verifier: <PASS; exit 0 / UNAVAILABLE; exit <code> / BLOCKED>
```

If `PUBLIC_VERIFIER_PASS`:
```
Verifier command: <exact command>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url> (not required after WP91)
Verified latest current-final comment head SHA: <sha> (not required after WP91)
```

If `PRIVATE_REPO_MANUAL_VERIFIED`:
```
Posted GitHub evidence verifier: UNAVAILABLE; exit <code>
Reason: <private repo / unauthenticated API unavailable / rate limit / access denied>
Manual live GitHub verification performed: YES
Manual verification method: <method>
Verified PR body head SHA: <sha>
Verified latest current-final comment URL: <url or UI-visible marker> (not required after WP91)
Verified latest current-final comment head SHA: <sha> (not required after WP91)
Verified latest current-final comment contains: validation results, local guard result, follow-up classification, network wording, Ready for review (not required after WP91)
```

If `BLOCKED_NOT_READY`:
```
Ready for review: NO
Blocker: <specific reason>
```

**Machine-readable header block in final evidence comments (Historical WP86–WP90 only; not required after WP91):**

**After WP91:** A final comment is not required. If an optional final comment is posted, the machine-readable header block is not required; the comment must state it is optional and non-canonical.

**Historical WP86–WP90 only:**

```
CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments
WP: <WP_ID>
PR: #<PR_NUMBER>
Head SHA: <HEAD_SHA>
Base SHA: <BASE_SHA>
Changed files: <N>
Full pytest: <result>
Evidence mode: <mode>
Local PR evidence guard: PASS/FAIL
Posted GitHub evidence verifier: PASS/UNAVAILABLE/BLOCKED
Manual live GitHub verification: YES/NO/NOT_APPLICABLE
Follow-up correction required: YES/NO
Ready for review: YES/NO
```

The PR body may be a concise index while the final comment carries full detailed evidence, provided required state-machine fields are present and key facts match. Long duplicate narratives in both surfaces are not required.

## Concise Reporting

Apply the concise-reporting format from `docs/ai/codex/CONCISE_REPORTING_RULES.md`:

- Report validation summary counts (command, exit code, pass/fail, test counts, warnings).
- Include failure snippets when any check fails; do not truncate failure evidence.
- Do not paste full raw test logs unless needed to diagnose a failure.
- Report unavailable security tools as UNAVAILABLE/SKIPPED, never as passed.

Concise reporting must not reduce required evidence. Concise reporting may compress raw output logs but must never abbreviate the command invocation itself. If in doubt, include more evidence, not less.
