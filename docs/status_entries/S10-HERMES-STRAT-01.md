# S10-HERMES-STRAT-01 Status Entry

## Identity

- WP ID: S10-HERMES-STRAT-01
- Title: Hermes Strategy Manager Core — V2.1 Soft Strategy Judgment
- Branch: codex/s10-hermes-strat-01-strategy-manager-core
- Base commit: dab28ee45c1f8267248d52601c90d3f3509034f9
- Required predecessor: PR #210 / S10-STRAT-LIFE-01, head d3c98d7530c8cec6b65e5d76492f1d7da8edf783,
  merge dab28ee45c1f8267248d52601c90d3f3509034f9
- Scope amendment: Scope Amendment 01 (Side15) — 22 paths, XL_FOR_SCOPE_ONLY
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Authority / Non-Authority Posture

- Package class / size / risk: HERMES_STRATEGY_MANAGER_CORE / XL (XL_FOR_SCOPE_ONLY) / 3
- Governance track: RUNTIME
- Exact implementation authority: 22 paths (20 original + 2 historical Hermes compatibility guards)
- Authority expansion from amendment: NONE
- Source runtime: YES — additive default-off strategy mode in the existing controlled Hermes
  runtime (models.py, policy.py, controller.py) plus the new strategy_manager.py
- Hermes runtime: YES (existing network-capable controlled runtime; deterministic fake backend
  only; real provider/model calls: 0)
- Strategy: YES — canonical soft strategy judgment only
- Credentials, scheduler, paper, execution, live: NO
- Direct STRAT-LIFE mutation: NO; PortfolioAuthorityPolicy mutation: NO
- Dependency, workflow, tools change: NO
- Capital/orders: USD 0 / 0
- Protected boundary groups not crossed: credentials/secrets, authenticated clients,
  wallet/account behavior, order placement/cancel, execution gateway, paper engine,
  scheduler/bot loop, daemon, dashboard / Control Center / deployment, dependency/lock
  changes, external code copying, generated artifacts

## Implemented Capability

- Default-off `strategy_mode` in the existing controlled runtime with the distinct
  `hermes-strategy-assessment-draft-output-contract/1.0.0`; generic and context modes unchanged;
  context_mode and strategy_mode mutually exclusive
- Closed strategy vocabularies, exact strategy_assessment validator and obvious action/risk
  consistency rules sharing one source of truth with the generated schema
- Strategy-local `strategy_lifecycle_context_sha256` (store head retained as provenance only)
- StrategyAssessmentEvidence bound to existing ContextEvidenceItem ids (<= 12, ADMISSIBLE,
  cutoff-safe, subject-related, bounded non-secret non-path summaries)
- HermesStrategyRunRecord (`hermesstrategyrun:sha256:`) for successful and failed runs
- HermesStrategyAssessment (`hermesstrategyassessment:sha256:`) canonical soft strategy decision
- Append-only hash-chained manager store, application id 1213418801, strategy-local
  predecessor chain, atomic run+assessment commit
- Foreground `run_hermes_strategy_assessment`: exactly one controlled Hermes run, no retry,
  fallback, scheduler, child StrategyVersion or STRAT-LIFE write

## Repo-Truth Reconciliation

- S10-STRAT-LIFE-01: MERGED (PR #210)
- S10-HERMES-STRAT-01: current bounded implementation target / implemented candidate
- Raw generic Hermes research stays research-only and untrusted; HERMES-STRAT decisions are
  canonical soft strategy decisions, not hard authorizations
- Historical universal "Hermes can never make strategy lifecycle decisions" target wording:
  superseded, history retained
- S10-EXEC-FEAS-01: next core package after HERMES-STRAT review and merge
- S10-CC-FOUND-01: NOT AUTHORIZED / NOT STARTED until HERMES-STRAT merges; Control Center NOT STARTED
- ALPHA-03: parallel / non-blocking; DATA-03: unchanged and non-blocking
- S10-DEPLOY-01 host activation: separate; Gate C: unchanged; live: DISABLED

## Validation Summary

- Pre-implementation readiness: PASS, IMPLEMENTATION_READY (RUNTIME), 22 paths,
  81 evidence items, 35 normative rules
- Historical Hermes compatibility guards: additions-only exact path exceptions
- Focused HERMES-STRAT tests, Hermes regression, STRAT-LIFE compatibility,
  architecture/status docs, compatibility guards, readiness/check-diff, artifact guard, diff
  hygiene, security, authoritative full suite and exact-head hosted CI: recorded with exact
  commands/results in the PR body after final validation

## Negative Test Matrix

- Required: YES
- Covers missing/retired strategy; non-admissible, future, unrelated, duplicate, excess and
  unsafe evidence; invalid cutoff/trigger; over-bound context; mode conflict; unknown/missing/
  invalid strategy fields (case variants); inconsistent action/risk; non-ADAPT adaptation;
  unknown parameter key; float/NaN/Infinity; non-empty material redesign; runtime failure;
  invalid strategy output; forged receipt; tampered run/assessment ids; stale predecessor;
  store symlink/hardlink, schema/application-id drift, payload/chain tamper, UPDATE/DELETE,
  bounds; forbidden imports.
- Not applicable: new trade-like wording filters (existing Hermes validator scans reused).

## Successor Boundary

- Establishes only HERMES_STRATEGY_MANAGER_CORE_MERGED after merge
- Next core package after review and merge: S10-EXEC-FEAS-01
- S10-CC-FOUND-01 becomes eligible to draft/start in parallel only after this package merges
- Parallel and unchanged: S10-ALPHA-03, S10-DEPLOY-01 host activation closure, DATA-03
- No successor starts automatically; no executable feasibility or live permission is established

## Ready For Review

- Ready for review: governed by the current PR body after exact-head CI and live
  PRIVATE_REPO_MANUAL_VERIFIED evidence
- Merge authorized: NO
