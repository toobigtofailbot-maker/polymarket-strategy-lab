# S10-ALPHA-HUNTER-PILOT-02 Status Entry

## Identity and authority

- WP ID: S10-ALPHA-HUNTER-PILOT-02; Dormant Unattended-Capable NBA/Rain Hunter Live Pilot with Versioned Envelope, Reduce-Only Exit and Reconciled Release.
- Branch: `claude/s10-alpha-hunter-pilot-02`; PR and current live head: see GitHub metadata and the current PR body.
- Base: `e3696526ae66675d725415ca5aecc89957349034` (PR #257 merge; predecessor head `4aa8b5ed41bab48b37a092048a5590066a681359` contained in main).
- Validated implementation commit: `df3a913` (implementation; the frozen package commit is `fd010ef88c87dd452309962bb3b7ed6e4a4acb4d`).
- This is a stable non-self-referential evidence record. Exact-head hosted CI, posted evidence mode and the live review-readiness decision belong to the PR body.
- Package: PROTECTED_DORMANT_UNATTENDED_CAPABLE_MULTI_CATEGORY_LIVE_PILOT; L; risk 4; PROTECTED; originally L / exact 19 paths under the independent V3.1 certificate, amended to XL / exact 21 paths (V3.2, D009) and then XL / exact 23 paths (V3.3, D011), each under a fresh independent certificate (12/12 lenses PASS, no unresolved decisions). Karl authorized zero-economic implementation, including the section 4.1 dormant loosenings, on 2026-10-27.
- Not authorized: merge, real credentials, Session Key/Builder creation, account access, provider (Hermes/Firecrawl) spend, deployment, timer, capital, any real order, Gate C/A3 activation, or a change to `LIVE TRADING STATUS: DISABLED`. O3 not approved; the USD 5 fee-inclusive cap is unchanged.
- Protected boundary groups: `docs/ai/codex/PROTECTED_PATHS.md` Centralized Boundary Group Reference; only the certified paths were changed.

## Frozen inputs

- `wp_prompt.txt` SHA-256 `c20a9aa5ea7477bb5979c4cab4bbcf2da1a7f3583c4a958e1c688b0d8b5102ed`; `wp_spec.json` `5147de8163029fed827bd75749792060b389b5ce715b83ddb815c61929588768`; `draftability_certificate.json` `bc5538cc44573675b46c727ff9afcc625442a4d5f4d90e7f575b6d3cd704fe90`. Installed byte-exact; committed blob hashes re-verified.
- Pre-implementation native readiness with `--certificate`: exit 0, IMPLEMENTATION_READY, `certificate_hash_bound: true`, PROTECTED, 19 scope files / 17 evidence items / 17 rules.

## Exact scope (23 files)

- `src/execution_gateway/live_orch.py`, `src/execution_gateway/gateway.py`, `src/execution_gateway/gate_b.py`, `src/execution_gateway/gate_c.py`
- `src/live_pilot/hunter_cycle.py`, `tools/alpha/run_hunter_pilot.py`
- `tests/live_pilot/test_hunter_cycle.py`, `tests/execution_gateway/test_live_orch.py`, `tests/execution_gateway/test_gateway.py`, `tests/execution_gateway/test_gate_b.py`, `tests/execution_gateway/test_gate_c.py`
- `docs/live_pilot_contract.md`, `docs/live_orchestration_contract.md`, `docs/live_trading_authorization.md`, `docs/deferred_items_log.md`, `docs/status_entries/S10-ALPHA-HUNTER-PILOT-02.md`
- `docs/wp_specs/S10-ALPHA-HUNTER-PILOT-02/wp_prompt.txt`, `wp_spec.json`, `draftability_certificate.json`
- `.gitleaksignore`, `tests/test_gitleaks_secret_scan_gate.py` (V3.2 D009 amendment only)
- `tools/git/diff_scope_summary.py`, `tests/tools/git/test_diff_scope_summary.py` (V3.3 D011 amendment only)

## Implementation summary

- LIVE-ORCH: exact `CAPITAL_PROFILES` table; `LiveOrchCapitalEnvelope.profile` (default `V1_CANARY`); `check_admission_risk` reads the validated profile (V1 decisions unchanged, V1 canary clock-call sequence unchanged); opt-in `HUNTER_PILOT_02` (5 / floor 2 / 30 / 50, no observed-loss stops). Reduce-only `exit_sell`, SELL reconciliation, `verify_sell_permit_authority`, SELL worst-case fee reserve, `CLOSED_RECONCILED` release, `signer_type` threading.
- Gateway: additive opt-in binding keys, SELL linkage rule, `CLOSED_RECONCILED` clean terminal and transition; read adapter `accepted_signer_type` (default OWNER).
- Gate B: `CredentialDirectorySessionKeyProvider` (POSIX no-follow open, post-open fstat identity/owner/mode/size, one 0x 64-hex key, no echo); `GateBIdentityPolicy.signer_type` equality; SESSION_KEY provider check before `acquire()`; `build_aggressive_sell`.
- Gate C: `LiveOrchSellSpec`, `inspect_live_orch_signed_sell`, `LiveOrchMutationBoundary.prepare_sell`; BUY spec/inspector/prepare unchanged.
- Hunter cycle: v2 policy/owner record, intake re-hash and binding, fee truth, sizing, stress EV, exit, breaker and diagnosis, E0 latch, kill, custody suspension, in-lock guard, one terminal. CLI runs hunter `verify` first.

## Validation

- Readiness and guards, test counts, Linux full suite, security scans and hosted CI: recorded in the PR body for the exact head.
- Windows local full suite is not authoritative: Nautilus DLL imports are blocked by Windows Application Control (inherited, S10-LIVE-CANARY-SIWC-01-D002); no host policy or binary changed. The authoritative full suite is the documented isolated Linux fallback on exact `git archive` bytes.
- R007 POSIX credential-file checks skip on Windows by design and were executed on Linux (network none, non-root container).
- Negative matrix required: YES. R001-R017 nodes cover missing/null/wrong-type/empty/duplicate/unknown fields, malformed UTF-8/JSON, nonfinite decimals, case/spelling key variants, stale/future evidence, tamper, ceilings, custody, SELL contract, release and restart cases. Free-text wording filters are not added, so typo variants of such filters are N/A.

## Implementation notes (disclosed)

- The pinned SDK encodes a FOK BUY USDC amount on a 0.01 grid and the native inspector requires exact shares, so the cycle narrows (never widens) the section 4.6 rule size to that grid and rechecks every minimum; the pure 4.6 rule and the R017 matrix are unchanged.
- The credential-directory path is read with `os.getenv`: the existing gateway architecture guard forbids the `os.environ` literal. No secret value comes from the environment.
- Rain eligibility uses a conservative 00:00 UTC cutoff of the target day. The resolved-payout source defaults to UNKNOWN, counted as zero (a loss). `CLOSED_RECONCILED` requires an explicit zero-size position row.

## D009 resolution (V3.2, 21-path XL amendment)

- Karl explicitly authorized on 2026-10-28 a narrow 21-path XL amendment limited to D009; package re-frozen as V3.2 (prompt `58b2c1c81ad476a26ce012f390a899dda658e741f1b84b1abe7e9d801384b6bf`, spec `16b8b6f687e253864da109f3ea5c5e0fdfb75269bc22fb7be586b1694a05456d`).
- A first fresh independent certifier refused at `781bbca` on one stale stop sentence (K2, prompt line 112 "20th path"); fixed at `79acaef`. A second fresh independent certifier issued PASS (12/12 lenses, implementability PASS, no unresolved decisions); certificate raw sha256 `a85cececba4ab89f4bec6a1e7430a0e5c10422648bf26c3f0532f5efdbd5f138`, installed byte-exact at path 17. The implementing session issued no certificate.
- Native readiness with the installed certificate: exit 0, IMPLEMENTATION_READY, `certificate_hash_bound: true`, PROTECTED, 21 scope files / 17 evidence items / 17 rules.
- Correction: `.gitleaksignore` appends only `fd010ef88c87dd452309962bb3b7ed6e4a4acb4d:docs/wp_specs/S10-ALPHA-HUNTER-PILOT-02/wp_spec.json:generic-api-key:211`; `tests/test_gitleaks_secret_scan_gate.py` changes only `EXPECTED_FINGERPRINT_COUNT = 20` to `21`. No rule, allowlist, workflow, history, implementation, economics or authority change. Scope is now 21 files.
- Product code and its tests are byte-identical to the validated implementation commit `df3a913`; earlier full-suite evidence is reused for them, and current affected-check and exact-head CI results are in the PR body.

## D011 resolution (V3.3, 23-path XL amendment)

- Correction of an earlier inaccurate record: at `0df63d8` the advisory command `python -B tools/git/diff_scope_summary.py --base e3696526ae66675d725415ca5aecc89957349034 --head 0df63d89681dcfac2a05748e43f8057b29748976 --wp-spec docs/wp_specs/S10-ALPHA-HUNTER-PILOT-02/wp_spec.json --require-exact-scope` actually exited 1 (`Exact scope pass: false`, `.gitleaksignore` reported as an authority contradiction) while printing a fixed "Exit 0 (summary generated)" line. The earlier PR body recorded exit 0 from that printed text through a pipe, not from the real exit status. Side23 found this; it was reproduced here with the true `$?`.
- Karl authorized a bounded 23-path XL amendment. V3.3 (prompt `015311108170e1fbe7f590c99ca2fc5409b51843a7fe43097ef1507631c2bc1c`, spec `2793c847d819458fa4e06bf357ec9c66de701829be72cfc63d6df20c6c09c1f7`) was certified by a third fresh independent certifier (certificate `4556baf3ab1f08e7642be1005dcf2ba11e3a7ea59cb152097ce42e7bfd961b7c`, 12/12 lenses PASS), installed byte-exact; the implementing session issued no certificate.
- Fix at the source: the helper reuses the canonical `wp_spec_guard.SECURITY_SCAN_CONFIG_PATHS` through its existing guard loader (now loaded once), so exactly `.gitleaks.toml` and `.gitleaksignore` require `local_offline_tooling`; look-alikes stay unauthorized and an unavailable guard fails closed. When exact scope is required and fails, the summary's exit line now says exit 1, matching `main()`. No other authority, scope or exit-code semantics changed.
- Tests: 11 new focused cases (canonical parity, authority-false negatives, seven look-alikes, fail-closed loader, printed-vs-real exit). Red control: 4 of them fail against the unfixed helper; all pass with the fix.
- Exact command results at the final head (real exit codes) are in the PR body.

## Limits

- Zero real provider calls, zero credentials, zero orders, USD 0 capital. No profitable alpha, real Hermes influence, live canary or unattended trading is claimed. Under the unchanged USD 5 cap at Gamma minimum USD 5, zero NBA/rain BUYs are expected until O3 is separately decided; with no BUY, the exit and release paths stay idle.
- Independent Side23 exact-head review and Karl-only merge decision remain required.
