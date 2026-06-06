# Pull Request Checklist

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

## Summary

## Work Package

## Negative Test Matrix

```
Negative test matrix required: YES / NO
```

(If YES, list categories covered. If NO, explain why not applicable.)

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

