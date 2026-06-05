# WP Bundling Policy

## Status

- WP bundling policy status: WORKFLOW_GOVERNANCE_MANDATORY
- Applies to: Codex and Claude Code
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network access: NONE
- Enforcement: mandatory for every WP draft before branch creation

## Purpose

Define when multiple changes may be bundled into one work package and when they must not be.

The goal is to let larger, coherent WPs run faster without widening the safety surface. Bundling is allowed only when it stays inside one safety class, serves one objective, and has one coherent validation surface.

## Risk-Class Bundling Principle

A WP may bundle multiple related changes only when they remain within the same safety class, share one objective, have one coherent validation surface, and have an explicit changed-file set.

A WP must not bundle across mode boundaries. The following boundaries require separate explicit approval gates:

- research-only
- local reporting
- paper trading
- credentials
- execution
- scheduler/bot loop
- Hermes runtime
- live trading

Crossing any mode boundary within a single WP requires explicit user authorization and a stop/escalate review before proceeding.

## Package Size Classes

| Class | Description | Approximate Changed-File Budget |
|---|---|---|
| S | Docs/tests-only, narrow objective | Up to 5 changed files |
| M | Narrow local/offline implementation or docs/tests bundle | Up to 10 changed files |
| L | Bundled local/offline/read-only implementation or workflow hardening | Up to 15–20 changed files |
| XL | Forbidden unless explicitly approved by user and justified before drafting | Requires explicit user authorization before drafting |

Package size class must be stated in the WP definition and in the PR body.

XL is not automatically approved by any prior WP or bundling policy entry. It requires a fresh explicit user authorization for each occurrence.

## Allowed Bundle Examples

The following bundle types are allowed within a single WP, subject to risk-class and file-budget constraints:

- Repo-truth reconciliation combined with a narrow implementation in the same safety class.
- Docs plus tests plus one small local/offline source module.
- Schema or contract clarification plus focused tests.
- Helper governance plus docs/tests.
- Deferred-item cleanup plus status updates.
- PR evidence workflow hardening plus related docs/tests.
- Multiple workflow-governance docs updated together when they share one objective and one validation surface.

## Forbidden Bundle Examples

The following bundle types must not appear in a single WP regardless of file count:

- Research scoring combined with trade recommendation wording.
- Data/report writer combined with buy/sell/entry/exit/sizing language.
- Microstructure quality combined with slippage/fill/trade execution model.
- Paper trading combined with live trading.
- Credentials combined with order placement.
- Scheduler or bot loop combined with execution.
- Strategy logic combined with risk engine.
- Hermes or agent runtime combined with execution authority.
- Dependency or runtime integration bundled with feature logic unless explicitly approved with a separate boundary review.

## L-Package Requirements

An L-size work package must include all of the following in the WP definition and PR body:

- Why this bundle is safe within one risk class.
- Why all changed files belong to the same objective.
- What is explicitly excluded from scope.
- What the rollback surface is.
- The changed-file budget with actual count.
- A mode-boundary table confirming no boundary is crossed.
- Focused tests covering all new policy or implementation content.
- Full pytest after final commit.
- Current-final evidence consistency with the guard (including `--require-guard-result`) before Ready for review: YES.

## Stop and Report Triggers

Stop immediately and escalate to the user if any of the following occurs during WP execution:

- The implementation requires crossing a risk-class or mode boundary not authorized in the WP.
- The actual changed-file count will exceed the declared budget.
- An unexpected dependency or lock-file change appears.
- Source directories (src/, tools/polymarket/, tools/advisory/, tools/agent/, tools/validation/) are unexpectedly needed.
- Any protected boundary (live trading, credentials, execution, Hermes, scheduler, bot loop) would move from its current status.
- A follow-up correction changes the PR body or final evidence after the guard was last run.

Do not continue past a stop trigger without explicit user guidance.

## Follow-Up Process-Defect Classification

Every review follow-up that required a correction must be classified in the PR evidence.

### Classification Categories

| Code | Category |
|---|---|
| A | Evidence/reporting failure |
| B | Repo-truth/status reconciliation failure |
| C | Validation not rerun after final change |
| D | Scope drift or changed-file-set drift |
| E | Boundary/protected-scope risk |
| F | Implementation logic defect |
| G | Test coverage gap |
| H | External/tooling/environment limitation |
| I | Reviewer-requested clarification without implementation defect |

### Required Fields When a Follow-Up Occurs

```
Follow-up correction required: YES/NO
Classification:
Cause:
Resolution:
Systemic assessment:
Separate hardening WP needed: YES/NO
If NO, why not:
```

### Follow-Up Rules

- If a cause is recurring or systemic, Claude Code must propose a separate hardening WP unless explicitly deferred by the user.
- A follow-up must not be hidden by saying no follow-up corrections were required when one occurred.
- If no follow-up occurred, state that explicitly using the required fields with YES/NO = NO.

### When No Follow-Up Occurred

```
Follow-up correction required: NO
Classification: none
Cause: none
Resolution: none
Systemic assessment: no new process-defect signal observed in this WP
Separate hardening WP needed: NO
If NO, why not: no follow-up occurred
```

## Posted Evidence Self-Check Rule

The local guard validates local text drafts only. It does not fetch or validate live GitHub PR body or posted PR comments.

Before setting Ready for review: YES, Claude Code must satisfy one of the following conditions and state which one was used:

1. The guard was run on exact local draft texts that are intended for posting as-is (the PR body and current final evidence comment). State: "Guard input source: exact local drafts intended for posting."
2. The already-posted PR body and latest current-final evidence comment were copied into local temporary files, and the guard was run on those copied texts. State: "Guard input source: copied from posted GitHub PR body and current-final comment dated [date]."

The guard must be run with `--require-guard-result`. The full guard result output — `PR evidence consistency guard: PASS` or `... FAIL`, `Checked categories: ...`, and `exit 0` or `exit 1` — must appear in both PR body and final comment. A guard command invocation line alone does not satisfy this requirement.

If any posted evidence changes after the last guard run, the guard must be rerun on the updated content or Ready for review must remain NO.

If Claude Code cannot verify that the live GitHub PR body and latest current-final evidence comment match what the guard checked, it must state that limitation explicitly in the final evidence. It must not claim posted evidence was verified when only pre-post local drafts were checked.

## Cross-References

- `AGENTS.md` — binding Codex and Claude Code operating rules
- `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` — mandatory PR evidence reporting policy
- `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` — local offline guard reference
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md` — reviewer checks including bundle-risk check
- `docs/work_package_template.md` — WP template with bundling policy fields
- `docs/review_checklist.md` — reviewer-facing bundle checks
- `.github/pull_request_template.md` — PR template with follow-up classification
