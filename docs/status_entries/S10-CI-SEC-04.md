# S10-CI-SEC-04 Status Entry

## Identity

- WP ID: S10-CI-SEC-04
- Title: Hosted Gitleaks Enforcement
- Package class / size / risk: SECURITY_TOOLING_HOSTED_GITLEAKS_GATE / M / 2
- Governance track: FAST; readiness basis DETERMINISTIC (no certificate required)
- Branch: claude/s10-ci-sec-04-hosted-gitleaks-gate
- Frozen base: 58193b50f550a451bff41333d2d21803039be943
- Predecessor: PR #247 / S10-CI-SEC-02, head 28b35d0c3f3de52644f44ba6113a72265401206e, merged at the base
- PR, current live head, Ready for review and hosted CI: live values in the PR body
- Merge authorized: NO (Karl only, after Side21 independent acceptance)
- Authorization: Karl's 2026-10-21 dispatch of the Side21 S10-CI-SEC-04 package

## Trigger

S10-CI-SEC-02-D001: hosted CI installed no gitleaks binary, so the five binary-backed detection
cases skipped on hosted runners and no hosted secret scan ran. PR #247 restored real detection rules,
but enforcement stayed local.

## Repair

Inside the existing required `ci-final-gate` job, before the unchanged final plan verification:

1. exact pull-request head, non-shallow history and base ancestry checks;
2. pinned gitleaks 8.27.2 Linux x64 install with strict SHA-256 verification of the checksum
   manifest and the archive before extraction into `$RUNNER_TEMP`, and a version check;
3. `gitleaks git --redact --exit-code 1 --log-opts="--all"` over the fetched history with the
   committed configuration and fingerprints;
4. the five binary-backed detection cases with a JUnit requirement of 5 tests, 0 skipped,
   0 failures and 0 errors.

The new steps are plain bash (no new `python - <<'PY'` heredoc, which
`tests/tools/ci/test_risk_tier.py` counts). No new job or workflow; triggers, permissions, matrix,
routing, classifier, rulesets, scanner configuration and fingerprints are unchanged.

## Exact Scope (7 paths)

- .github/workflows/ci.yml
- tests/test_codex_workflow_docs.py
- docs/gitleaks_secret_scan_gate.md
- docs/deferred_items_log.md
- docs/status_entries/S10-CI-SEC-04.md
- docs/wp_specs/S10-CI-SEC-04/wp_prompt.txt
- docs/wp_specs/S10-CI-SEC-04/wp_spec.json

## Validation

Focused tests, the gate negative matrix, readiness `--check-diff`, a network-isolated container
rehearsal, the local full suite and the exact-head hosted run are recorded in the PR body.

## Authority / Non-Authority Posture

FAST, Risk 2. Crossed boundaries: the workflow file, docs, tests and governed evidence only. The
workflow fetches only the pinned public gitleaks release asset, its checksum manifest and standard
Python test tooling; no product, trading, provider or account endpoint. No secrets, permission,
ruleset, credential, deployment, Hermes, strategy, paper, execution, order, live or capital authority.
PR #246 untouched. Capital/orders: USD 0 / 0.

Known limit: a pull request can modify the workflow itself, so the gate is enforced in unchanged
workflow runs; workflow changes remain subject to human review and the ruleset.
