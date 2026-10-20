# S10-HERMES-LIVE-BRIDGE-01 — witnessed OAuth choice + canonical assessment -> read-only live preflight

**Authority:** Karl's explicit instruction of 2026-10-19 to implement the certified R3 package within its scope.
**Executor:** Claude Code.
**Branch:** `claude/s10-hermes-live-bridge-01`.
**Frozen main:** `0c158e061d3ab5039997c6b4e736da0da9507d37`.
**Predecessor:** PR #245, merged at frozen main.

**Governance:** PROTECTED, risk 4. The independent certificate (sha256 `56ee9f6a…bdf5`) binds prompt `00353511…6136` and spec `0508b324…e033`. Before any edit, native `wp_spec_guard` returned PASS and `wp_readiness_gate --certificate` returned `IMPLEMENTATION_READY`.

**State:** BLOCKED_NOT_READY (scope contradiction). Merge ready: NO. This fragment is stable and non-self-referential.

## Blocker

The certified eight-path scope cannot pass the existing suite:

- **Without the allowlist entry:** the architecture guard `test_no_executable_files_exist_under_src_except_approved_scope` rejects the new `src/research_runtime/live_preflight_bridge.py`.
- **With the entry:** two existing tests pin `tests/test_architecture_boundaries.py` byte-for-byte to older commits, and both fail:
  - `tests/research_runtime/test_autonomous_opportunity_cycle.py::test_architecture_exact_approval_preserves_all_original_guards` allows only the AUTO-01 addition relative to `7d1e817`;
  - `tests/research_runtime/hermes_controlled_runtime/test_autonomous_feedback.py::test_auto02_historical_hermes_guards_exact_allowlist_and_sibling_negative` requires a zero `git diff` against `9ffbdb4`. Its folder is a forbidden prefix in this WP.

No legitimate existing approved scope can hold the composer: P036 forbids `hermes_controlled_runtime`, and every other approved scope is unrelated. The smallest correction is a two-path amendment, for ten paths in total. Each of those two tests also strips the exact two-line bridge entry before its historical comparison. This was proven locally: with both edits applied, 59 of 59 relevant tests passed, and the edits were then reverted.

## Implemented (in-scope, local)

- **Composer:** `live_preflight_bridge.run_live_preflight_bridge` runs the witness check, AUTO-01 `admit_oauth_choice`, the native strategy check (latest assessment plus matching run record), the fresh venue, intent, feasibility and Gate C permit, and then only `LiveOrchestrator.preflight`.
- **Abstention:** NO_TRADE, PAUSE and REASSESS give ABSTAIN with zero permit, venue read and preflight.
- **Labels:** `SYNTHETIC_ONLY` is preserved as a label. Assessment provenance is reported as labels only. Any injected seam gives OFFLINE_TEST_ONLY / PROTOCOL_ONLY.
- **Tests:** R001–R006 are in `tests/research_runtime/test_live_preflight_bridge.py`, offline only, with 8 cases passing.
- **Regressions:** 321 regression tests pass across AUTO-01/02, OAuth Stage B, LIVE-ORCH, Gate C, P036, the official-client banned-term guards and the architecture guard. The only failures are the two pinned tests named above.

## Call counts

Provider 0, OAuth dispatch 0, credential 0, account/private session 0, order 0, capital 0. No real network was used by the implementation or the tests.
