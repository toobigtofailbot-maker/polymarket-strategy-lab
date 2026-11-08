# S10-R3-ORACLE-UPSTREAM-01

RUNTIME/Risk3/L, exactly 14 paths. Branch `codex/s10-r3-oracle-upstream-01` (PR #278) is a clean-history rebuild cut from clean synchronized main
`e9099c438ddf779a4ae4d6438c8d5923bd6eceec`.

- PR #277 is merged: head `7492d96694f5eb4bf64e00615b8378819476744c`, merge `e9099c438ddf779a4ae4d6438c8d5923bd6eceec`.
- PR #268 is open and untouched at `9a5a00cd61effa4e28b82f830427440b23aba86c`.
- Karl's corrected first-person bootstrap authorizes two things:
  - copying the five pinned Oracle3 files to `src/data_layer/analytical_research/oracle3/`;
  - the minimal hash-verified importlib alias.
- Karl's CI-closure bootstrap authorizes three further changes:
  - the re-frozen prompt and spec wording;
  - one SDK-probe test-setup repair;
  - one guarded `--force-with-lease` replacement of this PR branch only, over blocked old head `69ae15a11e527e658b55f856be8fdf6336d089ab`.
- Merge: NO (Karl only).

## Readiness

- **First package (top-level `oracle3/`):** stopped before branching. The native gate returned `READINESS_PACKAGE_GUARD_INVALID`: 10× `AUTHORITY_CONTRADICTION`, because root paths have no authority class.
- **Second package (13 paths):** prompt `4e366f8e…` and spec `aebc7b4f…` were IMPLEMENTATION_READY. The work was published as PR #278 with the old history. That head's hosted CI was blocked twice:
  - a date-expired SDK-probe test that was also red on main;
  - 4 gitleaks findings on a slash-separated prose list in that frozen prompt and spec, introduced by the old first commit.
- **CI-closure package (current):** prompt SHA-256 `6789574f3963cb4dc15050248a6897fe41284965d8508cf57f03eb17aff07987`, spec SHA-256 `0a36e0b9c79c25228c1c010b52101cb2e409f75fcb3adcc54aa02fe64c8cf60d` (package `SHA256SUMS.txt` verified).
  - The native gate ran on those exact bytes on clean detached main, before the branch rebuild and before any source change.
  - Result: exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 14, 8 evidence items, 8 normative rules.
  - No repair was needed, and the committed files are byte-identical.

## Implementation

Contract: `docs/oracle3_upstream_reuse_contract.md`.

- **Source reuse:** the five upstream files were copied verbatim at `267fb7c48dae7c4ff8922c02a3a223443e51bf0b` after the Apache-2.0 + NOTICE (MIT ancestry) and stdlib-only import-closure review. All Git blobs match. Nothing is installed and there are no dependency changes.
- **Alias:** the bridge verifies all five blobs, then executes the verified bytes as `oracle3`, `oracle3.fees` and `oracle3.arbitrage`. The package has an empty `__path__`. Foreign modules are never overwritten. `sys.path` and the environment are not touched.
- **Call path:** frozen copy of a REL-01 scratch -> unchanged native REL `verify` (VERIFIED) -> native COST_KNOWN best asks + explicit `PolymarketSchedule` (TEST_ONLY rate or per-market frozen Gamma `feeSchedule` via upstream `from_gamma_market`) -> genuine `oracle3.arbitrage.check_constraint` -> per-basket parity vs native -> content-addressed receipt -> cold verify with sockets blocked.
- **Abstentions:** default, category, expired, absent or native-bound fees; non-explicit Gamma fee terms; unsupported upstream fee terms; non-admissible real-world classes (cross-venue, rule conflict or orientation, mechanical identity, timing); missing quote or depth; LOCAL_REAL_PIT without confirmed rules.
- **Authority:** RESEARCH_ONLY. Every case is `tradable: false`. Native REL/SRC/PIT/execution modules are byte-identical (REL code identity unchanged).
- **CI-closure test repair:** `tests/tools/alpha/test_official_sdk_public_probe.py::test_probe_negative_security_and_adversarial_matrix` now forges `acquired_start_utc` one second after the same receipt's own `acquired_end_utc` instead of using a fixed calendar instant. The expected `ACQUISITION_TIME_CONFLICT` assertion is unchanged. Probe production code, the owner activation pin and its window are untouched.

## Outcome (SANITIZED_SYNTHETIC REL-01 corpus, 49 models)

- Upstream `check_constraint` invoked 3 times (`v01` COMPLEMENT, `v07` EVENT_SUM, `v08` EXCLUSIVITY); 46 cases abstained, with every reason counted.
- 5 baskets compared, all `EXACT` against native (single-level books, aligned rates).
- Variant evidence shows systematic differences honestly:
  - A two-level book gives `SIGN_MISMATCH`: upstream's full-fill top-of-book edge is negative after the native depth sweep.
  - A shallow book with a TEST_ONLY rate of 0.03 gives `SIGN_AGREES_VALUE_DELTA`.
- Real-world verified 0; tradable 0.
- Adoption: R3-03 / R3-03-FEES `SELECTIVE_UPSTREAM_CODE_REUSE`, `CONDITIONAL_NOT_VALUE_VERIFIED`, owner acceptance pending. The other 34 of 36 ids are unchanged. The R3-23 GET stays unconsumed.

## Validation state

VALIDATED on rebuilt implementation commit `48c595006a23dcd7b7b9e1cc55a7c8196cba13b1`, the only commit before this status-only record. Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.

- **History:**
  - Old head `69ae15a11e527e658b55f856be8fdf6336d089ab` was replaced by one guarded `--force-with-lease` against that exact head.
  - `git merge-base --is-ancestor a045fae HEAD` is false, and no remote branch or tag contains `a045fae`.
  - `origin/main..HEAD` holds only the new commits.
- **Native gates on `48c5950`:**
  - The diff gate (`--check-diff --base origin/main --head HEAD`) gave exit 0, `IMPLEMENTATION_READY`, scope 14, with `diff_scope` checked.
  - The exact-scope helper gave exit 0 with 0 warnings.
  - The generated-artifact guard passed.
- **Named tests (Windows host, Python 3.14):** all 8 R001–R008 evidence-plan nodes pass. The focused and neighbor set passed 170, with 5 skipped (gitleaks-binary tests without a local binary). That set is the Oracle3 parity, SDK probe, SDK search, contract parity, related-market, source-grounding, architecture-boundary and gitleaks-gate tests.
- **SDK-probe repair:**
  - The test fails on unchanged main `e9099c4` and passes after the repair.
  - A mutation with equal start and end times fails the unchanged `ACQUISITION_TIME_CONFLICT` assertion.
- **Full suite (Linux):** docker image `s10-canary-siwc-validation:20261024`, `--network none --read-only`, clean LF clone at `48c5950`, Python 3.12.14, `python -B -m pytest -q -p no:cacheprovider --basetemp /tmp/full -ra`. Result: 14736 passed, 15 skipped (pre-existing environment gates), 0 failed.
- **Hosted CI on `48c5950`:** run `42531179125` passed 11/11 jobs.
  - The four compat full suites had 0 failed: ubuntu 14722 passed / 14 skipped; windows 14715 passed / 21 skipped.
  - The pinned gitleaks 8.27.2 full-history scan covered 636 commits: "no leaks found".
  - The 5 binary-backed detection tests passed, with 0 skipped.
- **Security:**
  - Upstream blobs were verified in the committed tree.
  - No `.gitleaksignore`, scanner, CI, dependency or lockfile change.
  - Boundary review: BOUNDARY_INTACT.
