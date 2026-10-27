# S10-HERMES-ALPHA-HUNTER-01 Status Entry

## Identity and authority

- WP ID: S10-HERMES-ALPHA-HUNTER-01; Multi-Category Hermes Alpha Hunter (research only).
- Branch: `claude/s10-hermes-alpha-hunter-01`; PR and current live head: see GitHub metadata and current PR body.
- Base: `f0184b5d6ea1319884e403aeeb2b4ea026ec5650` (PR #256 merge).
- Validated implementation commit: `2fc29d288e747762ff85e8ba940f9e63d622d517` (A4, full local suite and combined independent review).
- This is a stable non-self-referential evidence record. Final exact-head hosted CI, posted evidence mode and live review-readiness decision belong to the PR body; this fragment records local implementation evidence.
- Package: BOUNDED_FOREGROUND_MULTI_CATEGORY_RESEARCH_CANDIDATE_HUNTER; M; risk 3; RUNTIME. Karl authorized the original implementation and A4 on 2026-10-27.
- A4 authorizes exactly one additional file and one assertion change: historical D005 row present exactly once, rather than global last line. All other historical test source and deferred-log history preserved.
- Paper / execution / live / credential / dependency-change / deployment / merge authority: NO. Research artifacts have no execution authority. Live trading DISABLED; USD 0 / orders 0.
- Protected boundary groups: `docs/ai/codex/PROTECTED_PATHS.md` Centralized Boundary Group Reference; protected trading, credential, configuration, dependency, workflow and deployment paths unchanged.

## Exact scope (8 files)

- `tools/alpha/run_alpha_hunter.py`
- `tests/tools/alpha/test_alpha_hunter.py`
- `tests/test_repo_truth_docs.py` (only the one A4 assertion)
- `docs/alpha_hunter_contract.md`
- `docs/deferred_items_log.md` (append-only)
- `docs/status_entries/S10-HERMES-ALPHA-HUNTER-01.md`
- `docs/wp_specs/S10-HERMES-ALPHA-HUNTER-01/wp_prompt.txt`
- `docs/wp_specs/S10-HERMES-ALPHA-HUNTER-01/wp_spec.json`

## Validation

- Prompt SHA-256 `a8758c8f592455066906f83c983b6df0ad93f538a0962ba0d3c9eac0f4188c9e`; spec SHA-256 `f94a3e975c35d72f16b52b5b9ac792e15741df0ff124d00373ca6a852a4f9115`.
- Deterministic readiness before correction and candidate `--check-diff`: IMPLEMENTATION_READY, RUNTIME, 8 scope files / 13 evidence items / 12 normative rules, exit 0. No PROTECTED certificate required.
- `python -B -m pytest -q -p no:cacheprovider tests/test_repo_truth_docs.py::test_s10_deploy_plan_01_repo_truth` -> 1 passed in 0.63s, exit 0.
- Authoritative isolated Linux full suite: `/usr/local/bin/python -B -m pytest -q -p no:cacheprovider -ra` through the pinned, network-none/read-only/non-root Docker sandbox -> 14194 passed, 15 skipped, 125 warnings in 538.33s (0:08:58); exit 0. Image `sha256:1dea619cf5d724cd42aa18f7bedbc7b9f1e18e0841c84a488718771622c269bf`; CPython 3.12.14; exact validated source SHA asserted by bootstrap. Complete Docker command, warnings and skipped reasons retained at `C:/Users/dersu/AppData/Local/Temp/hunter-amendment-20261027/`.
- Combined independent implementation review: PASS at the validated implementation commit; no confirmed blockers. Missing/duplicate historical rows reject; later appended rows pass. Actual blobs prove exactly one historical assertion changed, all deferred history preserved, and product code/hunter tests unchanged from the earlier fully reviewed implementation.
- Combined review report SHA-256 `3393d8ce5222b52a2192226ad1dda4f3937413d5205310edeec0cf725555adf4`, in the external evidence directory. It incorporates the prior full implementation review and six offline probe groups by verified blob identity. Original standalone pre-fix reviewer narrative was not recovered; actual fix diff, recovered probe and fresh separate-context evidence were inspected.
- Reused prior focused evidence: 19 passed; adjacent 456 passed, 3 skipped; historical mutation report 18/18 red. Fresh full suite above is the current local compatibility gate.
- Windows full run at the same candidate: 29 failed, 14130 passed, 35 skipped, 2 warnings in 1218.44s, exit 1; failures are Nautilus DLL imports blocked by Windows Application Control. The host policy and native binaries were not changed. The documented isolated Linux path was used; its focused environment check passed 94 tests with 123 warnings before the authoritative full run.
- Initial Linux collection stopped with 6 PROFILE_INVALID errors / 1 warning due to temporary-copy CRLF conversion. The snapshot was rebuilt from exact Git archive bytes; all 1207 tracked file bytes and the unchanged profile hash were verified, and the profile loader passed. No repository file or hash guard changed; setup failure log retained.
- Initial byte-correct Linux full run: 6 failed, 14188 passed, 15 skipped, 125 warnings; POSIX storage guards rejected synthetic HOME under world-writable /tmp. Only sandbox HOME moved to a private uid1000 mode0700 tmpfs under /home; all six failures then passed (18 deselected). Final full run uses a read-only Linux-local volume with bootstrap exact-byte verification. No source, guard or host policy changed; earlier run retained.
- Exact scope summary: PASS, eight files, zero warnings. Generated-artifact and whitespace guards: PASS. No protected/dependency/lock/generated-file hits.
- Gitleaks 8.27.2 candidate commit-range scan: zero leaks, exit 0. Semgrep CE 1.176.1: 200 applicable rules on all three changed Python files, zero findings; first run had one rule timeout on the historical test, then that file reran with `--timeout 60`, zero findings/errors and exit 0. No rule suppression, Pro or cross-file assurance claim.
- Six unchanged direct runtime pins reuse the prior pip-audit 2.10.1 result: no known vulnerabilities, exit 0, two hash recommendations; direct-pin scope only. Hosted resolved-closure audits are reported in the current PR body.
- Negative matrix required: YES. R001-R012 focused nodes cover applicable malformed/type/null/empty, time, source independence, identity/conflict, budget/origin, authority/endpoint and restart/integrity negatives. Wording typo/case categories 13/14 are inapplicable: no new wording filter. A4 reviewer probes cover absent/duplicate/single/appended-row cases.
- Prior failed full run at `d926dac29381b4329608e0ec8d3a5e721d43b340`: 1 failed, 14158 passed, 35 skipped, 125 warnings; old global-EOF assertion. Failure and reproduction logs are retained under `C:/Users/dersu/AppData/Local/Temp/hunter-finish-20261027/`. A4 resolves this conflict; no history was moved or deleted.
- This final evidence update changes only this fragment and appended D010/D011 evidence rows. Its affected checks, final committed head, local guard, hosted CI and live evidence are recorded in the PR body.

## Public evidence and limits

- Existing bounded public run (2026-10-27 18:31:47-18:32:14 UTC), reused without a repeat: 59 public GETs; zero account/order/wallet/credential attempts. NBA: 55 markets -> 8 assessed -> 2 positive-margin tokens, both small-order-unfit. Rain: 14 markets -> 4 assessed -> 8 BOOK_STALE tokens. Selected 0.
- Fresh prior cold verification: VERIFIED, 1 operation, 0 network, 0 Hermes dispatches, exit 0. No executable code changed since that verification.
- PUBLIC_SCREENER_NO_HERMES; HERMES_NOT_RUN_BUDGET_ZERO; UNSATISFIED_REAL_INFERENCE_NOT_DEMONSTRATED. Real Hermes inference remains UNPROVEN. No REAL_HERMES_PASS, calibration, guaranteed fill, profitability or live authority claim.
- Workflow network: git synchronization/push, GitHub publication/inspection, hosted CI, Semgrep rule/version metadata and dependency advisory lookup. Product network remains the earlier bounded public run; this amendment's checks and probes are offline except workflow/security tooling. No paid inference, credentials, account access, real orders, deployment or capital operations.

## Deferred items and review handoff

- D001-D007 retain the operational limitations: real inference authorization, Firecrawl state, minimum-order semantics, fee disagreement, fee-inclusive cap constraint, unchanged shadow transport observation and V2/crypto exclusions.
- D008 was the historical seven-file scope blocker; A4 plus appended D010 resolves it. The original row/history remains preserved.
- D011 records the local Windows native-module limitation and successful isolated Linux validation; exact-head hosted Windows checks remain separate.
- D009 retains the legacy posted-verifier comment requirement. Actual verifier outcome and permitted live manual evidence mode are documented in the PR body; no false private-repo or verifier-PASS claim.
- Local implementation review disposition: PASS. Final independent Side PR review and Karl-only merge decision remain separate. Follow-up implementation correction required: NO; operational follow-ups remain separately gated.
- Suggested successor: S10-ALPHA-HUNTER-PILOT-02, PROTECTED and separately gated; no new WP started or authorized here.
