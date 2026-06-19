# PR Evidence Consistency Guard

## Status

- PR evidence consistency guard status: LOCAL_OFFLINE_STDLIB_GUARD_HARDENED (WP47)
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network access: NONE — the guard is local/offline and does not fetch GitHub
- Applies to: Codex and Claude Code
- Enforcement: run before Ready for review: YES when local PR body draft is available. After WP91, a final comment draft is not required as a guard input — final comments are optional and non-canonical after WP91.

## Purpose

Provide a local, offline, stdlib-only CLI helper that checks PR body and final
comment drafts for consistency and evidence quality before any WP is marked
Ready for review: YES.

WP45 made exact PR evidence reporting mandatory as written policy.
WP46 adds this mechanical guard so evidence drift is caught by a tool,
not manually during review.

**WP91 policy change:** After WP91, mandatory final GitHub evidence comments are retired. The guard is no longer required as a merge gate with a final comment input. After WP91, the PR body alone is the current review evidence surface; the status fragment is the stable non-self-referential record; final comments are optional reviewer clarification only and non-canonical. Absence of a final comment is not a merge blocker after WP91. If a final comment is voluntarily posted, it must not contradict the PR body and must explicitly state it is optional and non-canonical.

## Non-Goals

- Does not fetch or parse live GitHub PR data. The guard is local/offline only.
- Does not post, edit, or comment on GitHub PRs or issues.
- Does not prove that validation commands actually ran or that tests passed.
- Does not replace human review.
- Does not validate that file paths, commit SHAs, or test counts are correct — only that both surfaces are consistent with each other and contain required evidence structure.
- Does not mutate PR bodies, comments, branches, files, or GitHub state.

**Important limitation:** Running the guard only on intermediate drafts is insufficient if the posted PR body or posted evidence comment later changes. If any evidence is updated after posting, copy the final posted text back into local temporary files and re-run the guard before marking Ready for review: YES.

**WP54 posted evidence self-check rule:** Before Ready for review: YES, declare one of the following in both the PR body and the final comment: (1) the guard ran on exact local draft texts that are the texts intended for posting as-is, or (2) the already-posted PR body and current-final evidence comment were copied into local temp files and the guard ran on those copies. If neither condition is satisfied, Ready for review must remain NO. If Claude Code cannot confirm the live GitHub content matches what the guard checked, it must state that limitation and may not claim posted evidence was verified. See `docs/ai/codex/WP_BUNDLING_POLICY.md` for the full posted evidence self-check rule.

## Inputs

| Argument | Required | Description |
|---|---|---|
| `--pr-body PATH` | Yes | Local PR body draft file path |
| `--final-comment PATH` | Yes (WP86–WP90); not required after WP91 | Local final comment draft file path — optional and non-canonical after WP91; absence is not a merge blocker |
| `--expected-head SHA` | No | Expected 40-char head commit SHA — must appear in both files |
| `--required-command TEXT` | No, repeatable | Exact command text that must appear verbatim in both files |
| `--require-standard-network-wording` | No | Require standard network wording in both files |
| `--require-ready-yes` | No | Require "Ready for review: YES" in both files |
| `--format text\|json` | No | Output format (default: text) |
| `--forbid-inline-test-counts` | No | Fail if parenthetical test-count phrases like "(33 tests)" appear outside validation sections |
| `--forbid-placeholder-evidence` | No | Fail if placeholder tokens like `<HEAD_SHA>`, `TBD`, `placeholder`, `actual:`, or fake SHA filler appear |
| `--require-current-final-marker` | No | Fail unless final comment contains "CURRENT FINAL WP EVIDENCE" marker |
| `--forbid-stale-count-tokens TEXT` | No, repeatable | Fail if the supplied stale token appears in either file |
| `--require-posted-evidence-note` | No | Fail unless both files contain a "Guard input source:" line |
| `--require-guard-result` | No | Fail unless both files contain the actual guard result output: result line, checked categories, and exit code |

## CLI Usage

### Minimal invocation

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md
```

### Full WP invocation pattern — Historical WP86–WP90 Only (required final comment)

This pattern applied during the WP86–WP90 transition when a mandatory final comment was required. `--require-current-final-marker` is a WP86–WP90-only flag and is not required after WP91.

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md \
  --expected-head <HEAD_SHA> \
  --required-command "python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries" \
  --required-command "python tools/git/diff_scope_summary.py --base main --head HEAD --package-class <PACKAGE_CLASS> --allowed-prefix docs/ --allowed-prefix tests/ --forbidden-prefix src/ --forbidden-prefix tools/" \
  --required-command "python tools/git/code_blast_radius.py <FULL_ARGUMENTS>" \
  --require-standard-network-wording \
  --require-ready-yes \
  --forbid-inline-test-counts \
  --forbid-placeholder-evidence \
  --require-current-final-marker \
  --require-posted-evidence-note \
  --require-guard-result
```

### Post-WP91 invocation pattern (final comment not required)

After WP91, `--final-comment` and `--require-current-final-marker` are not required. Run the guard on the PR body only:

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --expected-head <HEAD_SHA> \
  --required-command "python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries" \
  --required-command "python tools/git/diff_scope_summary.py --base origin/main --head HEAD --package-class <PACKAGE_CLASS> --allowed-prefix docs/ --allowed-prefix tests/ --forbidden-prefix src/ --forbidden-prefix tools/" \
  --require-standard-network-wording \
  --require-ready-yes \
  --forbid-inline-test-counts \
  --forbid-placeholder-evidence \
  --require-posted-evidence-note
```

### JSON output

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md \
  --format json
```

JSON output structure:

```json
{
  "status": "PASS",
  "errors": [],
  "warnings": [],
  "checked_categories": ["A:missing_files", "B:empty_evidence", ...]
}
```

## Required Command Examples

For a local/offline stdlib governance helper WP, the standard required commands are:

```
python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries
```

```
python tools/git/diff_scope_summary.py --base main --head HEAD --package-class local-offline-stdlib-governance-helper --allowed-prefix docs/ --allowed-prefix tests/ --allowed-prefix tools/git/pr_evidence_consistency_guard.py --forbidden-prefix src/
```

```
python tools/git/code_blast_radius.py --changed-file tools/git/pr_evidence_consistency_guard.py --changed-file tests/tools/git/test_pr_evidence_consistency_guard.py --changed-file docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md --package-class local-offline-stdlib-governance-helper --include-docs --include-tests --include-protected-boundaries
```

## Standard Network Wording

The guard checks for this exact string when `--require-standard-network-wording` is set:

> Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior.

## What the Guard Checks

| Category | Check |
|---|---|
| A — Missing files | PR body or final comment file path does not exist |
| B — Empty evidence | Either file is empty |
| C — Ellipses in commands | Command lines or helper names contain "..." |
| D — Required commands | Each --required-command must appear verbatim in both files; known helper names checked for symmetry |
| E — Head SHA | --expected-head must appear in both files; labeled SHAs must not differ between files |
| F — Test counts | "N passed, M failed, K errors" counts must match between files |
| G — Network wording | Standard wording must appear in both files; "no network was used" flagged when standard wording required |
| H — Ready status | "Ready for review: YES" must appear in both files; YES vs NO mismatch flagged |
| I — File counts | Changed-file counts must match if present in both files |
| J — Security honesty | Tool described as "passed" must not also be described as NOT_AVAILABLE/SKIPPED |
| K — Inline test counts | (--forbid-inline-test-counts) Parenthetical test-count phrases like "(33 tests)" are forbidden outside validation sections |
| L — Placeholder evidence | (--forbid-placeholder-evidence) Tokens like `<HEAD_SHA>`, `TBD`, `placeholder`, `actual:`, `TODO`, or fake SHA filler are forbidden |
| M — Current final marker | (--require-current-final-marker) Final comment must contain "CURRENT FINAL WP EVIDENCE" marker — **WP86–WP90 only; not required after WP91** |
| N — Stale count tokens | (--forbid-stale-count-tokens) User-supplied stale tokens must not appear in either file |
| O — Posted evidence note | (--require-posted-evidence-note) Both files must contain a "Guard input source:" line |
| P — Guard result line | (--require-guard-result) Both files must contain: 'PR evidence consistency guard: PASS' or '... FAIL', 'Checked categories:', and an explicit exit code. A command invocation line alone does not satisfy this check. |

## Pass/Fail Behavior

**On PASS (exit code 0):**

```
PR evidence consistency guard: PASS
Checked categories: A:missing_files, B:empty_evidence, C:ellipses_in_commands, ...
```

**On FAIL (exit code 1):**

```
PR evidence consistency guard: FAIL
Checked categories: A:missing_files, B:empty_evidence, ...

2 error(s) found:

  1. [F] Test count mismatch between PR body and final comment.
         PR body counts:       ['68 passed, 0 failed, 0 errors']
         Final comment counts: ['66 passed, 0 failed, 0 errors']
  2. [D] Required command missing from final comment (present in PR body): ...

Fix the above issues in the PR body and/or final comment before setting Ready for review: YES.
```

**On usage error / missing file / unreadable input (exit code 2):**

At the CLI level:
- Missing PR body file → exit 2
- Missing final comment file → exit 2
- PR body or final comment path is a directory (not a regular file) → exit 2
- File exists but is unreadable (OSError) → exit 2
- Argument parser errors → exit 2

The `run_guard()` API (for direct Python callers) still returns `[A]` category errors in its `errors` list when files are not found, and `passed=False`. The CLI translates these to exit 2 before `run_guard` is called.

## How Claude Code / Codex Should Use This Guard

**Historical required workflow (WP86–WP90, mandatory final comment):**

1. Prepare final PR body text locally (e.g., `local_pr_body.md`).
2. Prepare current final evidence comment text locally (e.g., `local_final_comment.md`).
3. Run the guard on exact final texts with all applicable flags including WP47 hardening flags.
4. If the guard fails, fix the PR body and/or final comment and re-run.
5. Post or update the PR body and the current final evidence comment.
6. If any posted evidence changes afterward, copy the final posted text back into local temporary files and re-run the guard.
7. Mark Ready for review: YES only after final evidence passes the guard.
8. Report the exact guard invocation AND the full guard result output (result line, checked categories, exit code) in both the PR body and final comment.
9. Include a "Guard input source:" line in both files identifying whether the guard ran on exact local drafts intended for posting or on copied posted GitHub content.
10. Do not commit local draft files unless they are test fixtures under `tests/`.
11. When using `--require-guard-result`: include the literal guard output lines — `PR evidence consistency guard: PASS`, `Checked categories: ...`, and `exit 0` or `exit 1` — in both the PR body and the final comment. The command invocation line alone does not satisfy this check.

**Post-WP91 required workflow (final comment not required):**

1. Prepare final PR body text locally (e.g., `local_pr_body.md`).
2. A final comment is not required after WP91 — skip final comment draft preparation unless a voluntary comment is desired.
3. Run the guard on the PR body using the post-WP91 invocation pattern (no `--final-comment`, no `--require-current-final-marker`).
4. If the guard fails, fix the PR body and re-run.
5. Post or update the PR body. No final comment is required for merge readiness.
6. Mark Ready for review: YES after the guard passes on the PR body.
7. If a final comment is voluntarily posted, it must not contradict the PR body, and must state it is optional and non-canonical.

**Old final comments warning (WP86–WP90 only):** If previous evidence comments exist, the new current final evidence comment must start with "CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments" so reviewers know which comment is current.

**After WP91:** Mandatory current-final-comment requirement is retired. Final comments are optional and non-canonical after WP91. If a final comment is voluntarily posted, it must not contradict the PR body and must explicitly state: "This comment is optional and non-canonical; the PR body is the current review evidence surface." Absence of a final comment is not a merge blocker after WP91.

**No inline test counts in file lists:** Do not put test counts in file list descriptions or summary parentheticals (e.g., "focused tests (34 tests)"). Put counts only in validation result sections.

## Relationship To Posted GitHub Evidence Verifier (WP58)

`pr_evidence_consistency_guard.py` checks local drafts or copied text only. It does not fetch live GitHub PR data.

`posted_pr_evidence_verifier.py` (added in WP58) checks the live GitHub PR body and comments via the public GitHub REST API.

**After WP91, posted GitHub evidence verification is not a required final-comment merge gate.**

Current required evidence check after WP91:
- PR body is current and matches GitHub PR metadata.
- Status fragment is stable/non-self-referential and does not contradict PR body.

Optional after WP91:
- If a final comment is posted, it must not contradict the PR body.

Historical WP58/WP86–WP90 workflow (not active after WP91): the two-step workflow (local draft guard + posted verifier) with mandatory final comment is documented in `docs/ai/codex/POSTED_GITHUB_EVIDENCE_VERIFICATION.md` under its historical section.

## Relationship to WP45 PR Evidence Reporting Discipline

WP45 established `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` as the
authoritative written policy for PR evidence reporting.

WP46 adds this guard as a local mechanical check that detects the most common
evidence inconsistencies before human review. The guard supplements but does
not replace the written policy or human review.

Both apply to all WPs. Running the guard and seeing PASS does not mean evidence
is correct — it means the two local draft surfaces are structurally consistent
and contain required evidence fields. Human review remains mandatory.

## Limitations

- Checks local text drafts only. Does not fetch or validate against the live
  GitHub PR body or posted PR comments.
- Does not prove that any command listed actually ran or that any test actually
  passed. It only verifies that the same command text appears in both surfaces.
- Does not validate that a commit SHA is a real commit in the repo.
- Does not detect all possible evidence defects — only the categories listed
  in the "What the Guard Checks" table above.
- Does not post or edit GitHub content.
- Does not replace pytest, security checks, preflight tools, or human review.

## Cross-References

- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — binding policy (WP45)
- `AGENTS.md` — PR Evidence Reporting Discipline section
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` — Standard PR Evidence Reporting Discipline Block
- `docs/ai/codex/VALIDATION_MATRIX.md` — package-class validation requirements
- `docs/ai/codex/WP_EXECUTION_REPORT.md` — final report format
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks
- `tools/git/pr_evidence_consistency_guard.py` — this guard's implementation
- `tests/tools/git/test_pr_evidence_consistency_guard.py` — guard tests
