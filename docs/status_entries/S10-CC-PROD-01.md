# S10-CC-PROD-01 Status Entry

## Identity and authority

- WP ID: S10-CC-PROD-01
- Title: Private Production Control Center — Read-Only Serving
- Package class: PRIVATE_READ_ONLY_CONTROL_CENTER_SERVING
- Size / risk / governance track: L / 3 / RUNTIME
- Branch: codex/s10-cc-prod-01-private-read-only-serving
- Frozen base: 10320087b9c16672d42fd0eaa50ded7e349b7a3a
- Required predecessor: PR #230, merged at frozen base; head f004c545e0ddd1d483c16d17045b880926d0c59e.
- Prompt SHA-256: b30c8876bc897282a6e3a29e0059f08154dd5296c52ca2a138cf1c72d8a929ec
- Spec SHA-256: 00b4b287d703c41b0e397f1259a6081edd13bb347867376e4b6625adea7545b4
- Readiness: IMPLEMENTATION_READY / RUNTIME / DETERMINISTIC; certificate not required.
- Implementation authority: Karl explicitly authorized the corrected readiness-passing package; Side18 subsequently approved Scope Amendment 01 (exact 13 paths, two obsolete field-order assertions only).
- Isolated-clone fallback: local main = origin/main = frozen base and clean tree proved before branch creation; shared checkout preserved.
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
  and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.
- Validated implementation commit: see exact-head validation evidence in PR body.
- Evidence mode / Ready for review: see verified current PR body; this committed record does not preclaim posted/hosted evidence.
- Merge authorized: NO (Karl only). Independent Side18 review remains required.

## Capability and protected boundaries

Opt-in trusted Vite index/assets serving reuses FastAPI/Starlette in the same
loopback process. Ten explicit SPA paths and closed assets GET/HEAD have no-store,
nosniff and no-referrer headers. Symlinks, traversal, hidden/source/development files
and API fallback are rejected. Original API-only default, 31 API paths/methods,
SSE, domain readers, CORS and TTY-only default-off commands are unchanged.
The dedicated polymarket nonroot unit is dormant, read-only, research-slice-bound,
restart-limited and IP-restricted to localhost; base bootstrap does not install/start it.
Build/digest/SHA association is a separately verified operator prerequisite, with
assets outside the immutable tracked release and only existing pinned extras used.

Authority / Non-Authority Posture references the Centralized Boundary Group Reference
in docs/ai/codex/PROTECTED_PATHS.md. Only repository presentation and the dormant
dashboard/deployment and runtime/daemon template portions are crossed. Credentials,
authenticated clients, wallet/accounts, order placement/cancel, execution gateway,
paper engine, scheduler/bot loop, dependency/locks, external copying and generated
artifacts remain uncrossed. Host/Tailscale/GitHub settings/command activation: NONE.
Capital/orders: USD 0 / 0. Original bootstrap, verifier, SSH-only firewall, slice controls,
critical probe, telemetry and backups unchanged. No product network/API calls.
Workflow traffic is remote sync/push/PR/CI; validation supply-chain traffic includes
locked npm install/audit and available security checks, distinct from product traffic.

## Scope and evidence

Exact thirteen required = allowed paths are the frozen spec's sole scope authority:

- src/operator_cockpit.py
- tests/test_operator_cockpit.py
- tests/test_operator_cockpit_stream.py
- tests/test_operator_cockpit_commands.py
- tools/deployment/systemd/polymarket-control-center.service
- tests/deployment/test_runtime_baseline.py
- tools/deployment/README.md
- docs/control_center_production_contract.md
- docs/project_status.md
- docs/repo_truth_index.md
- docs/status_entries/S10-CC-PROD-01.md
- docs/wp_specs/S10-CC-PROD-01/wp_prompt.txt
- docs/wp_specs/S10-CC-PROD-01/wp_spec.json

R001–R013 traceability remains in the frozen spec and current PR body. New test cases stay
in the original two approved families; the two approved legacy field-order assertions alone are updated; existing commands/streams/architecture/releases are
reused. Negative matrix: API/method or unattended-command drift rejects; source/path/
symlink leakage rejects; missing/wrong-SHA assets stop promotion; public ingress or
broad tailnet policy stops activation; host/credential activation is outside authority;
main drift, extra scope or failed mandatory evidence blocks merge readiness.
Final focused/adjacent/Windows and Linux availability, exact commands/counts, one
stable-head authoritative full local suite, Node build/high audit, available security,
artifact guard, exact scope/readiness, selected exact-head hosted CI and posted-body
strict evidence guard are recorded honestly in the PR body, with no stale numeric
claims in this stable fragment. Runtime Linux systemd verification, actual IP-filter
support, private allowed/denied access, restart/reboot and rollback require Karl's
separate real-host operator decision; a repository PASS never substitutes for them.

## Local pre-push validation

- Focused and directly adjacent regression command:
  `python -m pytest -q -p no:cacheprovider tests/test_operator_cockpit.py tests/deployment/test_runtime_baseline.py tests/test_operator_cockpit_stream.py tests/test_operator_cockpit_commands.py tests/test_architecture_boundaries.py`
  completed with 180 passed / 10 skipped / 1 warning / exit 0. Windows symlink
  privilege and existing optional platform dependencies account for the skips.
- Complementary cached Linux Python 3.12 prod01 selection: 16 passed / 99 deselected /
  1 warning / exit 0, including all six real symlink rejection variants.
- Node 24.18.0 locked install, typecheck, external Vite production build and high audit
  passed (zero npm vulnerabilities); generated assets remain outside the repository.
- Scoped existing-tool Semgrep p/security-audit: zero findings, exit 0.
- The clone-local available-check runner reports unavailable tools as SKIPPED_NOT_AVAILABLE;
  existing external tools are invoked separately where available. Existing tool deferrals
  are retained; no availability is represented as an executed PASS.
- systemd-analyze is unavailable on this Windows host and cached validation image;
  the package explicitly conditions local verification on availability. Static unit guards
  execute; actual unit/IP-filter enforcement remains the frozen Karl-only host gate.
- Artifact guard PASS. Final stable-head full suite, exact diff/readiness, supplemental
  security results, hosted jobs and re-fetched posted evidence are the PR-body evidence surface.

## Deferred and successor boundary

No new material deferral is introduced. Existing tool-availability deferrals remain
unchanged and actual checks report availability honestly. Real-host activation is
already the frozen separately authorized operator gate, not new implementation scope.
S10-ALPHA-03 is a parallel separately gated successor; S10-DEPLOY-EXEC-01 Phase-B and
S10-LIVE-CANARY-01 remain independently gated. No new activation architecture or WP.
