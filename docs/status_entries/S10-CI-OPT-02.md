# S10-CI-OPT-02 Status Entry

## Identity and authority

- Title: Risk-Based Local-First CI Optimization
- Package class: WORKFLOW_GOVERNANCE_CI_RISK_OPTIMIZATION
- Size / risk / governance track: L / 2 / FAST
- Branch: codex/s10-ci-opt-02-risk-based-local-first
- Frozen base: e3e8673024c6921e794df8bf0aa4fcea3825dab1
- Required predecessor: PR #228 / S10-CC-CMD-01, MERGED at the frozen base;
  head 3e365771ce23a6be0f95b0d8c14faad95202e4c3.
- Earlier governance predecessor: PR #229, MERGED at
  101c7f44604553cf2f8d2166725b266435ab4047; ancestor of the frozen base.
- Exact implementation scope: 13 paths, required = allowed in the frozen spec.
- Corrected frozen prompt SHA-256:
  1263a6471d5ab1e8c16366452a925dfd5d479c7e87f699e56dda9a955dce5f69
- Corrected frozen specification SHA-256:
  6842c4673c3c47a7d6618210f2ab42cc9340e4b9aad9c8b3e1d98ad7ec824367
- Readiness: IMPLEMENTATION_READY / FAST / DETERMINISTIC; certificate not required.
- Karl explicitly authorized implementation of this exact corrected package after
  the readiness PASS. Readiness itself grants no authority.
- Dedicated isolated clone fallback: the shared checkout remains on its previous
  WP branch. Isolated main/origin/main matched live main with a clean tree before
  branch creation; only delivered frozen artifacts were subsequently added.
- PR and current live head: see GitHub metadata and the PR body.
- Ready for review: NO until final exact-head validation and posted evidence pass.
- Merge authorized: NO (Karl only). Routing activation: NOT AUTHORIZED / OFF.

## Capability

- Base-owned stdlib classifier parses full NUL-delimited Git change provenance
  including rename/copy origins, deletes and file modes, validates available WP
  authority mirrors and refuses malformed, missing or contradictory evidence.
- Tier 1 requires positive benign evidence or a pure isolated stdlib helper with
  its matching test. Tier 2 covers substantive noncritical research and ordinary
  app/deployment changes; RUNTIME/Risk 3 and research schedulers alone do not
  escalate. Actual sensitive changes, CI/security policy, dependencies/native ABI
  or unknown compatibility impact require Tier 3.
- Plans bind base/head, reasons, explicit nonempty OS/Python/smoke matrix and job
  flags. Activated workflow planning and final verification execute the base
  classifier, never a classifier supplied by the PR.
- Default absent/false/malformed switch uses fixed Tier 3 even on the first base
  without a classifier. Bootstrap requires all nine legacy legs plus classify and
  ci-final-gate. No audit exception is added; CVE-2026-104851 remains the sole ignore
  in the two existing Python audits. Strict native/SDK/DuckDB/NDFD and frontend
  checks remain on every required full job.
- The unique non-matrix ci-final-gate runs after failures, compares the plan with
  independently recomputed expectations, and requires success for selected jobs
  and skipped for nonrequired jobs. Skips never count as a required PASS.
- Matrix aggregation still requires independent expanded-row inspection.
- Draft suppression, original PR triggers and same-PR cancellation remain;
  hosted CI is final verification after one stable local full suite, never the
  development iteration loop. No duplicate push-main workflow is introduced.

## Authority / Non-Authority Posture

Only workflow governance, local offline tooling, evidence policy, docs, tests and
one CI workflow are authorized. All Centralized Boundary Group Reference groups
in docs/ai/codex/PROTECTED_PATHS.md remain uncrossed: credentials/secrets,
authenticated clients, wallet/account behavior, order placement/cancel, execution
gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment,
dependency/lock changes, external code copying and generated artifacts.
CI metadata/supply-chain workflow traffic is distinct from product network.
Product source, configs, dependencies/locks, services, credentials, scheduler,
Hermes runtime, strategy, paper, execution and live behavior are unchanged.
Capital/orders: USD 0 / 0. No repository settings change or activation.

## Validation and traceability

R001-R014 remain mapped in the frozen specification. Local focused negative
families cover benign and research eligibility, protected impact, full provenance,
base trust, default-off bootstrap, exact plans, failed/cancelled/skipped required
jobs and policy/audit/native regressions. Scope discovery confirmed current
full-changed-set guards derive the active 13 paths from this WP's spec/status;
no compatibility file outside scope is authorized.
Exact commands, actual counts, security tool availability, YAML checks, local
full suite, eleven expanded hosted rows, posted evidence mode/guard and runner
minutes belong in the PR body. This stable record does not assert unperformed
final evidence or independent Side18 approval.

## Successor boundary

Karl must separately verify trusted required ci-final-gate protection and authorize
CI_RISK_ROUTING_ENABLED=true after merge. main was observed unprotected; required
status enforcement is not claimed. First five eligible postactivation PRs report
actual raw runner-minutes against the eight-run 36.3-minute baseline. No dashboard,
scheduler or second workflow. S10-CC-PROD-01 remains separately gated.
