# S10-DEPLOY-01 Status Entry

## Identity

- WP ID: S10-DEPLOY-01
- Title: Research Platform Runtime Baseline
- Branch: codex/s10-deploy-01-research-runtime-baseline
- Base commit: 0b14c951c4546ebc28e0d129643da4ad4615ce2e
- Required predecessor: PR #208, head d5f61c086cbef74010856be88134e04c0e81a06d
- PR and current live head: see GitHub metadata and the PR body
- Merge commit: not merged
- Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED; live fields belong in the PR body

## Authority / Non-Authority Posture

- Package class / size / risk: RESEARCH_PLATFORM_RUNTIME_BASELINE / L / 3
- Exact implementation authority: 19 paths under the amended package
- Local offline tooling: YES, `tools/deployment/` only
- Source runtime: NO
- Network: bounded public post-merge smoke/bootstrap semantics only
- Scheduler: host telemetry timer only
- Credentials, Hermes, strategy, paper, execution, live: NO
- Capital/orders: USD 0 / 0
- Protected boundary groups not crossed: credentials/secrets, authenticated clients,
  wallet/account behavior, order placement/cancel, execution gateway, paper engine,
  dependency/lock changes, external code copying, generated artifacts

## Implemented Baseline

- Native Ubuntu 24.04 x86-64 + systemd + venv mechanism
- Deterministic tracked-file release builder and strict verifier
- Persistent `/var/lib/polymarket` layout and atomic current-release link
- Exact bounded research slice and reserved critical slice
- Sanitized once-per-minute telemetry with bounded rotation and interval-delta CPU/I/O sampling
- SQLite-aware hashed backup and isolated integrity-checked restore drills
- Exact SSH-only inbound UFW proof with conflicting ALLOW/LIMIT and routed-rule rejection
- Recoverably idempotent venv metadata/dependency verification and base-project install only; no optional cockpit extra
- Closed sanitized bootstrap operational failures
- Human-only provider/SSH boundary and credential-free host release
- One frozen bounded public WP169 smoke after merge only
- Closed research-only capacity dispositions
- DATA-03 unchanged; later execution coexistence proof remains required

## Validation Summary

- Pre-implementation readiness: PASS, IMPLEMENTATION_READY (RUNTIME), 19 paths,
  26 evidence items, 15 normative rules
- `tools/deployment/` authority classification: PASS
- Full-changed-set guard discovery: PASS; no 20th path required
- Focused deployment, docs, Bash syntax, readiness/check-diff, artifact guard,
  diff hygiene, security, authoritative full suite, and exact-head hosted CI:
  recorded with exact commands/results in the PR body after final validation

## Negative Test Matrix

- Required: YES
- Covers dirty/wrong HEAD, unsafe/secret release content, file-set/hash tamper,
  wrong host facts, sanitized manifests/telemetry, bounded rotation, symlink/secret
  backup rejection, restore overwrite/tamper/SQLite corruption, closed capacity
  outputs, exact smoke-success receipts, missing telemetry, interval CPU/I/O,
  exact systemd controls, scheduler isolation, SSH-only ALLOW/LIMIT firewall proof,
  partial-venv recovery, closed bootstrap failures, base-only installation, no sshd mutation, and no
  container/second-host mechanism.

## Deferred Post-Merge Activation

- VPS provisioned / host bootstrap / public smoke / backup-restore drill / reboot
  proof: NO; separately authorized human activation closure required after merge
- Execution coexistence proof: deferred until a real candidate reaches WP172 PASS
- DATA-03 and ALPHA-03: not started or changed by this package

## Ready For Review

- Ready for review: governed by the current PR body after exact-head CI and live
  PRIVATE_REPO_MANUAL_VERIFIED evidence
- Merge authorized: NO
