# Pull Request Checklist

- [ ] AI coding agent used stated: Codex / Claude Code / other
- [ ] Shared startup file read: `AI_CODING_AGENT_START_HERE.md`
- [ ] Tool-specific adapter read: `CODEX_START_HERE.md` / `CLAUDE_START_HERE.md` / other
- [ ] I read `AGENTS.md`
- [ ] Scope matches WP
- [ ] Full WP final report posted as PR comment (optional after WP91 — absence is not a merge blocker; PR body is the current review evidence surface)
- [ ] PR body is not the only final report (after WP91: PR body alone is sufficient; final comment is optional)
- [ ] Base verification included
- [ ] Required previous merge commit verified
- [ ] Required previous files verified
- [ ] Remote Main Sync Gate passed
- [ ] Generated Artifact Guard passed after final commit
- [ ] Full pytest passed after final commit
- [ ] `docs/project_status.md` security wording updated to current WP
- [ ] Unavailable semgrep/pip-audit or other tools not called passed
- [ ] No generated artifacts/local_data/venvs/security outputs committed
- [ ] No dependency/lock files changed unless scoped
- [ ] Ready for review: YES/NO stated
- [ ] No live trading code added
- [ ] No external repo code copied before audit
- [ ] No secrets committed
- [ ] Repo-truth docs updated
- [ ] Tests run
- [ ] Safety confirmations included
- [ ] Files changed listed
- [ ] Known limitations documented
- [ ] Validation summary includes exact commands and result counts
- [ ] Unavailable security tools reported as UNAVAILABLE/SKIPPED (not passed)
- [ ] Final PR comment is optional after WP91; if posted, it is non-canonical (see `docs/ai/codex/FINAL_COMMENT_POLICY.md` and `docs/ai/codex/CONCISE_REPORTING_RULES.md`)
- [ ] No raw full test logs in PR comment unless needed to diagnose failure
- [ ] Package size class (S/M/L/XL) stated in PR body
- [ ] Bundle risk class confirmed: no mode boundary crossed
- [ ] No forbidden bundle type present (see `docs/ai/codex/WP_BUNDLING_POLICY.md`)
- [ ] Follow-up process-defect classification section present and accurate
- [ ] Guard input source line states: PR body is current review evidence surface (after WP91; final comment is optional and non-canonical)
- [ ] `docs/project_status.md` reconciled after prior WP merge in this same WP
- [ ] Negative test matrix declared (`Negative test matrix required: YES / NO`)
- [ ] Status fragment committed: `docs/status_entries/WP<NN>.md` (WP86+)
- [ ] Status fragment consistent with PR body on all key fields
- [ ] Requirement-to-evidence traceability table included (M/L/XL WPs)
- [ ] Compatibility/impossibility table included (nontrivial WPs)
- [ ] Authority/Non-Authority Posture declared in WP definition
- [ ] Hard Merge Gate result recorded before any edits
- [ ] Context Budget defined and followed

## AI Coding Agent

AI coding agent used:
Shared startup file read:
Tool-specific adapter read:

## Summary

## Work Package

## Negative Test Matrix

```
Negative test matrix required: YES / NO
```

(If YES, list categories covered. If NO, explain why not applicable.)

## Status Fragment (WP86+)

```
Status fragment path: docs/status_entries/WP<NN>.md
Status fragment committed: YES/NO
Status fragment consistent with PR body: YES/NO
Status fragment is stable/non-self-referential (no current live PR head as fixed SHA): YES/NO
Status fragment uses "Validated implementation commit:" (not "Head commit:") for in-review SHA: YES/NO
```

## One-Shot Readiness Gate (WP92+)

Product WP gate (report/export/loader/validator WPs):
```
- repo-truth phrase sweep: PASS / NOT_APPLICABLE
- PR body/status fragment contradiction matrix: PASS
- status fragment stable/non-self-referential: PASS
- result-object field coverage: PASS / NOT_APPLICABLE
- serializer losslessness: PASS / NOT_APPLICABLE
- full public output scan: PASS / NOT_APPLICABLE
- invalid-output no-echo: PASS / NOT_APPLICABLE
- validation tier complete: PASS
- guards: PASS
```

Policy WP gate (workflow/policy/template/docs WPs):
```
- canonical-doc set reviewed: PASS / NOT_APPLICABLE
- repo-truth phrase sweep: PASS / NOT_APPLICABLE
- old-policy phrase hits classified: PASS / NOT_APPLICABLE
- templates aligned: PASS / NOT_APPLICABLE
- PR review checklist aligned: PASS / NOT_APPLICABLE
- validation matrix aligned: PASS / NOT_APPLICABLE
- status-fragment guidance aligned: PASS / NOT_APPLICABLE
- workflow docs tests updated: PASS / NOT_APPLICABLE
- contradiction matrix updated if policy changes: PASS / NOT_APPLICABLE
- no product/source/tool/dependency changes: PASS / NOT_APPLICABLE
```

See `docs/ai/codex/REPO_TRUTH_POLICY_GUARD.md` for full gate definitions.

## Evidence Architecture (WP88+)

```
Evidence architecture: Model D (after WP91)
PR body is current review evidence surface: YES/NO
Status fragment is stable/non-self-referential: YES/NO
Final comment is optional/non-canonical (not required for merge readiness after WP91): YES/NO
If final comment posted: does not contradict PR body: YES/NO/NOT_APPLICABLE
Evidence contradiction matrix checked: YES/NO — no invalid combinations present
```

## Compatibility / Impossibility Table (nontrivial WPs)

| Required behavior | Controlling repo mechanism | Files likely needed | Allowed in this WP? | Compatible? | Action |
|---|---|---|---:|---:|---|
| (fill for validator/report/schema/export/workflow/L+XL WPs) | | | | | |

## Requirement-to-Evidence Traceability (M/L/XL WPs)

| Requirement | Source WP section | Evidence location | Status |
|---|---|---|---|
| (fill for M, L, XL size class WPs) | | | |

## Posted GitHub Evidence Verification — Optional After WP91

After WP91, a final GitHub evidence comment is optional and non-canonical. Absence of a final comment is not a merge blocker after WP91.

If an optional final comment is posted, it must not contradict the PR body and must state: "This comment is optional and non-canonical; the PR body is the current review evidence surface."

## Tests Run

## Safety Confirmations

## Files Changed

## Known Limitations

