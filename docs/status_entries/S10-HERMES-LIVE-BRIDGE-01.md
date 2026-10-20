# S10-HERMES-LIVE-BRIDGE-01 — witnessed OAuth choice + canonical assessment -> read-only live preflight

**Authority:** Karl explicitly authorized the certified R3 implementation on 2026-10-19. He then authorized the complete R4 ten-path package the same day, covering implementation, commit, push, PR and hosted CI.
**Executor:** Claude Code.
**Branch:** `claude/s10-hermes-live-bridge-01`.
**Frozen main:** `0c158e061d3ab5039997c6b4e736da0da9507d37`.
**Predecessor:** PR #245, merged at frozen main.

**Governance:** PROTECTED, risk 4. An independent R4 certificate (sha256 `846d6207…6d27`) binds prompt `bb39a3a3…cf85` and spec `0417a337…e03f`. With that certificate, native `wp_spec_guard` returns PASS and `wp_readiness_gate` returns `IMPLEMENTATION_READY` for 10 files. The R3 certificate no longer applies.

**State:** IMPLEMENTED_LOCAL. Merge ready: NO; Karl merges manually after the SIDE20 assessment. This fragment is stable and non-self-referential. The live PR head, CI and full-suite counts are in the PR body and the external evidence ZIP.

## Revisions

- **R3:** the eight certified paths were implemented first.
- **Blocker:** the full suite then showed that two existing tests pin `tests/test_architecture_boundaries.py` byte-for-byte to older commits. They reject the required exact `APPROVED_SRC_SCOPES` entry, and without that entry the architecture guard rejects the new source file.
- **R4:** adds exactly those two test paths. Each now requires the two-line bridge entry exactly once and removes only that entry before its original historical comparison:
  - `test_autonomous_opportunity_cycle.py`: AUTO-01 equality against `7d1e817`;
  - `test_autonomous_feedback.py`: AUTO-02 byte equality against `9ffbdb4`.

  All original sibling, ordering and named-guard negatives are unchanged. A duplicated entry, a sibling, a parent wildcard or any other byte change still fails both tests.

## Design

- **Composer:** `live_preflight_bridge.run_live_preflight_bridge` runs these steps in order:
  - witness check;
  - AUTO-01 `admit_oauth_choice`;
  - native strategy check (latest canonical assessment and its matching run record);
  - fresh venue, then native intent, feasibility and Gate C permit;
  - `LiveOrchestrator.preflight` only.
- **Refused seams:** secret-provider, client and pause.
- **Abstention:** NO_TRADE, PAUSE and REASSESS return ABSTAIN with zero permit, venue read and preflight.
- **Labels:**
  - `SYNTHETIC_ONLY` stays a label only.
  - Assessment provenance is reported as labels, never as proof.
  - Any injected seam gives OFFLINE_TEST_ONLY / PROTOCOL_ONLY.
- **Tests:** R001–R006 are in `tests/research_runtime/test_live_preflight_bridge.py`, offline only.

## Call counts

Provider 0, OAuth dispatch 0, credential 0, account/private session 0, order 0, capital 0. Neither the implementation nor the tests used runtime or product network.
