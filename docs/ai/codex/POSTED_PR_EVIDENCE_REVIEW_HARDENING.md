# Posted PR Evidence Review Hardening

## Status

- Status: DOCS_AND_GUARD_HARDENING
- WP: WP47 - Posted PR Evidence Review Hardening
- Applies to: Codex and Claude Code
- Enforcement: mandatory for every WP before Ready for review: YES
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network access: NONE

**After WP91:** Final evidence comments are optional and non-canonical. The CURRENT FINAL WP EVIDENCE marker and the Reviewer Workflow and Claude Code/Codex Workflow described in this document are historical WP47–WP90 practice. After WP91, absence of a final comment is not a merge blocker; the PR body is the primary evidence surface. If an optional final comment is posted, these workflows remain applicable to it.

## Purpose

Harden the PR evidence workflow so future PRs do not require repeated manual
follow-ups for:

- Stale PR body text after evidence corrections.
- Stale or ambiguous final evidence comments when multiple comments were posted.
- Placeholder SHAs or template tokens in PR body or final comment.
- Parenthetical test counts in file lists that drift from actual counts.
- Ambiguity between old evidence comments and the current final evidence comment.

## Failure Pattern from PR #47 (WP46)

During the WP46 review, the PR evidence pattern that required manual follow-up:

1. Implementation was correct.
2. PR body was corrected to current evidence.
3. Older final comments remained visible with stale counts and placeholder SHA.
4. A later comment superseded them but was not explicitly marked as current.
5. Reviewer or tooling could still surface the old comment or a stale cached PR body.
6. File-list descriptions included parenthetical test counts like "focused tests (33 tests)" that later drifted to 34.

WP47 closes this gap by:
- Requiring a current-final evidence marker in superseding comments.
- Forbidding inline test counts in file lists.
- Adding guard flags to detect placeholder evidence.
- Adding guard flags to detect stale count tokens.
- Requiring a "Guard input source:" note in both PR body and final comment.

## Current Final Evidence Marker

When posting a final evidence comment that supersedes older comments, the comment
must start with or contain:

> CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments

This marker is deterministic: reviewers can search for it to identify the current
evidence without scrolling through all comments. It must appear when:

- A follow-up comment replaces stale prior evidence.
- The final evidence comment is updated after a re-run.
- Multiple evidence comments exist on the PR.

## Posted Evidence vs Draft Evidence

The guard (`tools/git/pr_evidence_consistency_guard.py`) reads local text files.
It does not fetch the live GitHub PR body or comments.

This means:
- Running the guard on intermediate drafts does not verify posted evidence.
- If the PR body or final comment changes after posting, the guard must be re-run on the updated text.

**Correct workflow:**

1. Prepare final PR body text locally.
2. Prepare current final evidence comment text locally.
3. Run guard on exact final texts with all applicable flags.
4. Post or update PR body and current final evidence comment.
5. If any posted evidence changes afterward: copy final posted text to local files and re-run guard.
6. Mark Ready for review: YES only after final evidence passes.

**Guard input source line** (required in PR body; required in final comment only if one is posted after WP91):

```
Guard input source: exact local drafts intended for posting
```

or

```
Guard input source: copied posted PR body and current final evidence comment
```

## Why Inline Test Counts Are Forbidden

Parenthetical test counts in file list descriptions are forbidden because they
drift independently from the actual validation results:

**Forbidden:**
```
tests/tools/git/test_pr_evidence_consistency_guard.py (33 focused tests)
```

The count "33" can become stale when tests are added or removed, and it is not
part of the validation result section. A reviewer may not notice it is stale.

**Acceptable:**
```
python -m pytest tests/tools/git/test_pr_evidence_consistency_guard.py -v
→ 49 passed, 0 failed, 0 errors; exit 0
```

Test counts belong only in validation result sections where they appear next to
the command that produced them.

## Reviewer Workflow (Historical WP47–WP90; applies to optional final comments after WP91)

**After WP91:** A final comment is not required. If no final comment exists, skip steps 1 and 4. The PR body alone is sufficient for merge readiness.

1. If a final comment was posted: identify the current final evidence comment by searching for
   the marker "CURRENT FINAL WP EVIDENCE". Do not treat older stale comments as current.
2. Verify you are reading the latest live PR body (or state clearly if using a
   PDF/export/screenshot at a specific point in time).
3. Check no parenthetical test counts appear in file lists or summary lines.
4. Check PR body includes a "Guard input source:" line. If an optional final comment was
   posted, check it also includes a "Guard input source:" line.
5. Check no placeholder evidence tokens appear (`<HEAD_SHA>`, `TBD`, `placeholder`,
   `actual:`, `TODO`, fake SHA filler).
6. Verify the guard was run with WP47 hardening flags and passed.

## Claude Code / Codex Workflow (Historical WP47–WP90; applies to optional final comments after WP91)

**After WP91:** Posting a final comment is optional. If skipping the final comment, run the guard against the PR body draft only (omit `--final-comment` and `--require-current-final-marker`).

1. Prepare final PR body draft (local file).
2. If posting an optional final comment: prepare final evidence comment draft (local file,
   starting with current-final marker).
3. Run guard with WP47 hardening flags on these exact local drafts:
   ```
   python tools/git/pr_evidence_consistency_guard.py \
     --pr-body local_pr_body.md \
     --final-comment local_final_comment.md \
     --expected-head <HEAD_SHA> \
     --require-standard-network-wording \
     --require-ready-yes \
     --forbid-inline-test-counts \
     --forbid-placeholder-evidence \
     --require-current-final-marker \
     --require-posted-evidence-note
   ```
   After WP91, if no final comment is posted, omit `--final-comment` and
   `--require-current-final-marker` from the invocation.
4. Fix any failures and re-run.
5. Post PR body; optionally post current final evidence comment (not required after WP91).
6. Set Ready for review: YES only after guard passes.

## Known Limitation: No GitHub API Fetch

The guard does not fetch live GitHub PR body or comments. It reads only local
files provided via CLI arguments.

This means:
- The guard cannot verify that what was posted matches the local draft.
- It cannot detect edits made to the PR body or comments after posting.
- It cannot detect GitHub-cached or stale versions of PR content.

To mitigate: copy the actual posted PR body and current final evidence comment
text into local files and re-run the guard after any evidence change.

## Future Possible WP: GitHub-Aware Posted Evidence Fetch Guard

A future WP could add a GitHub-aware guard that fetches the live PR body and
current final evidence comment via the GitHub API and runs the same consistency
checks on the actual posted content.

**This is explicitly deferred (WP47-D001).** It requires:
- GitHub API access / authentication.
- Network access within the guard tool.
- Explicit approval as a new WP with clear network/auth boundary.

Do not implement this in WP47 or any subsequent WP without explicit user approval.

## Cross-References

- `tools/git/pr_evidence_consistency_guard.py` — guard implementation
- `tests/tools/git/test_pr_evidence_consistency_guard.py` — guard tests
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` — full CLI reference
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — binding policy
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — Standard PR Evidence block
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — final report format
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks
- `docs/deferred_items_log.md` — WP47-D001 tracking
