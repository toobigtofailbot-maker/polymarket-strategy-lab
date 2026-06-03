# PR Evidence Consistency Guard

## Status

- PR evidence consistency guard status: LOCAL_OFFLINE_STDLIB_GUARD
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network access: NONE
- Applies to: Codex and Claude Code
- Enforcement: run before Ready for review: YES when local PR body and final comment drafts are available

## Purpose

Provide a local, offline, stdlib-only CLI helper that checks PR body and final
comment drafts for consistency and evidence quality before any WP is marked
Ready for review: YES.

WP45 made exact PR evidence reporting mandatory as written policy.
WP46 adds this mechanical guard so evidence drift is caught by a tool,
not manually during review.

## Non-Goals

- Does not fetch or parse live GitHub PR data.
- Does not post, edit, or comment on GitHub PRs or issues.
- Does not prove that validation commands actually ran or that tests passed.
- Does not replace human review.
- Does not validate that file paths, commit SHAs, or test counts are correct — only that both surfaces are consistent with each other and contain required evidence structure.
- Does not mutate PR bodies, comments, branches, files, or GitHub state.

## Inputs

| Argument | Required | Description |
|---|---|---|
| `--pr-body PATH` | Yes | Local PR body draft file path |
| `--final-comment PATH` | Yes | Local final comment draft file path |
| `--expected-head SHA` | No | Expected 40-char head commit SHA — must appear in both files |
| `--required-command TEXT` | No, repeatable | Exact command text that must appear verbatim in both files |
| `--require-standard-network-wording` | No | Require standard network wording in both files |
| `--require-ready-yes` | No | Require "Ready for review: YES" in both files |
| `--format text\|json` | No | Output format (default: text) |

## CLI Usage

### Minimal invocation

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md
```

### Full WP invocation pattern

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md \
  --expected-head <HEAD_SHA> \
  --required-command "python tools/git/status_snapshot.py --format text --include-deferred --include-helper-inventory --include-next-wp-candidates --include-protected-boundaries" \
  --required-command "python tools/git/diff_scope_summary.py --base main --head HEAD --package-class <PACKAGE_CLASS> --allowed-prefix docs/ --allowed-prefix tests/ --forbidden-prefix src/ --forbidden-prefix tools/" \
  --required-command "python tools/git/code_blast_radius.py <FULL_ARGUMENTS>" \
  --require-standard-network-wording \
  --require-ready-yes
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

**On usage error / missing file (exit code 2):**

File missing errors use exit code 1 (validation failure, category A).
Argument parser errors use exit code 2.

## How Claude Code / Codex Should Use This Guard

1. Write the PR body draft locally (e.g., `local_pr_body.md`).
2. Write the final comment draft locally (e.g., `local_final_comment.md`).
3. Run the guard with all applicable flags before marking Ready for review: YES.
4. If the guard fails, fix the PR body and/or final comment and re-run.
5. Report the exact guard invocation and result (PASS/FAIL) in both the PR body and final comment.
6. Do not commit local draft files unless they are test fixtures under `tests/`.
7. If local drafts were used (not the already-posted GitHub content), state that fact in the PR body and final comment.

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
