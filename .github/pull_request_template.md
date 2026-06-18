# Pull Request Checklist

- [ ] AI coding agent used stated: Codex / Claude Code / other
- [ ] Shared startup file read: `AI_CODING_AGENT_START_HERE.md`
- [ ] Tool-specific adapter read: `CODEX_START_HERE.md` / `CLAUDE_START_HERE.md` / other
- [ ] I read `AGENTS.md`
- [ ] Scope matches WP
- [ ] Full WP final report posted as PR comment
- [ ] PR body is not the only final report
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
- [ ] Final PR comment is concise but evidence-complete (see `docs/ai/codex/CONCISE_REPORTING_RULES.md`)
- [ ] No raw full test logs in PR comment unless needed to diagnose failure
- [ ] Package size class (S/M/L/XL) stated in PR body
- [ ] Bundle risk class confirmed: no mode boundary crossed
- [ ] No forbidden bundle type present (see `docs/ai/codex/WP_BUNDLING_POLICY.md`)
- [ ] Follow-up process-defect classification section present and accurate
- [ ] Current-final evidence comment identified by marker (not older stale comment)
- [ ] Guard input source line states: local drafts or copied posted content
- [ ] `docs/project_status.md` reconciled after prior WP merge in this same WP
- [ ] Posted GitHub evidence verifier run after PR posted (or unavailability stated with manual verification documented)
- [ ] Latest current-final comment URL included in PR body
- [ ] Negative test matrix declared (`Negative test matrix required: YES / NO`)
- [ ] Status fragment committed: `docs/status_entries/WP<NN>.md` (WP86+)
- [ ] Status fragment consistent with final comment on all key fields
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
Status fragment consistent with final comment: YES/NO
Status fragment is stable/non-self-referential (no current live PR head as fixed SHA): YES/NO
Status fragment uses "Validated implementation commit:" (not "Head commit:") for in-review SHA: YES/NO
```

## Evidence Architecture (WP88+)

```
Evidence architecture: Model D
PR body is current review evidence surface: YES/NO
Status fragment is stable/non-self-referential: YES/NO
Final comment is transition-only pointer (not duplicate evidence table): YES/NO
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

## Posted GitHub Evidence Verification

```
Posted GitHub evidence verifier: PASS/FAIL/UNAVAILABLE
Command: python tools/git/posted_pr_evidence_verifier.py ...
Result: ...
Latest current-final comment URL: ...
```

## Tests Run

## Safety Confirmations

## Files Changed

## Known Limitations

