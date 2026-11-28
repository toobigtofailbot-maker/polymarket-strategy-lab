# S10-CAP-NINE-ROLE-COORD-01

B4: finite conditional nine-role coordination over existing sealed native receipts. An offline coordination
diagnostic of exactly 11 paths. Branch `codex/s10-cap-nine-role-coord-01` was cut from clean synchronized main
`5666a33` (merge of PR #286, head `67b53d6`). PR #268 is open, separately owned and untouched; nothing is stacked
on it.

## Identity

- WP ID: S10-CAP-NINE-ROLE-COORD-01
- Title: B4 — Finite conditional nine-role native receipt coordination (W08)
- Branch: codex/s10-cap-nine-role-coord-01
- PR: see GitHub PR metadata and PR body.
- Base commit: 5666a3347f6f56215e290f2cbea90926ce9e4877
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and the PR body. This status fragment does not encode dynamic PR metadata or the SHA of the commit that contains it.
- Merge commit: (fill after merge)
- Evidence mode: recorded in the PR body (selected under docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md from the posted-body verifier result)

## Authority Posture

- Package class: RUNTIME, Risk 3, offline coordination diagnostic (`OFFLINE_ENGINEERING_COORDINATION_DIAGNOSTIC`).
- Implementation authority: YES, Side26's exact B4 grant under Karl's standing software-development authorization, conditional on native readiness.
- Report/export authority: YES (PR and report-back only).
- Hermes runtime / dispatch authority: NO. No new W01 delegation, Hermes child, model or provider call.
- Scheduler authority: NO (one finite manual operator; no daemon, loop or timer).
- Strategy, paper, execution and live authority: NO.
- Credential and dependency-change authority: NO.
- Canonical evidence authority: none; writes only to a caller-named external scratch.
- Network authority: none for runtime, product, source or provider APIs. Workflow network only: git fetch/push, GitHub PR publication and hosted CI.
- Protected boundary groups (docs/ai/codex/PROTECTED_PATHS.md): all untouched.

## Readiness

- The native readiness gate ran on the actual checkout before any source edit: exit 0, `IMPLEMENTATION_READY`, scope 11, 12 evidence items, 12 requirements. The frozen prompt and spec bytes are identical to the package.
- The diff-mode gate and the exact-scope summary results are recorded in the PR body.

## Implementation

Contract: `docs/nine_role_coordination_contract.md`.

- `nine_role_coordination.py` (pure): closed manifest; write-once plan with domain-tagged identities; fixed nine-slot routing over five routes; one typed consumer per eligible role A1-A7 reading native fields by exact key; atomic A3/A4 W01 pair; journal state machine with strict replay; quarantine; receipt core with totals, handoffs, capability rows, authority and false claims.
- `run_nine_role_coordination.py`: `run` / `resume` / `verify`. Exact layout and lstat caps before any hash; native B3 Parquet footer bounds before any hash; byte-identical frozen copies; one unmodified native top-level `verify` per case; exclusive fsynced journal files written only when legal; one never-stolen writer lock; socket block gating the seal; read-only cold verify with a whole-scratch witness.
- No native module changed or imports B4; B2 and B3 code identities equal their merged-base values.

## Historical native lineage (built at merged base 5666a33 in an isolated worktree, exact pin 345cd2b)

- B2 admitted: `b2research:sha256:0bd43845a723bbf0f505667f0aa232272f18433e7fd9cd2fd0bf4a1e4380d100`.
- B2 with native A6 REFUSED (`NATIVE_REFUSED:PROFILE_REFERENCE_INVALID`): `b2research:sha256:bca7c6972059352ddc9f8d5d746e49d67c61a59654ac0230e6d9494ad70e7567`.
- B3 over the admitted B2 (A7 PARTIAL, point FEASIBLE, replay NOT_SUPPLIED): `b3research:sha256:78e0cd424e28f6a058880cccc8c1659d15315b16181d791272473c730e594e16`.
- B2 code identity `9ccd7b6c…fade0a`, B3 code identity `5f78ea2f…7736ee` at base. The candidate replays these trees cold from immutable copies (R008); their bytes are unchanged afterwards.

## Two-case campaign (R007, local exact pin)

Case-01 = B2 with A6 natively refused, `FULL_SHARED_CASE`; case-02 = B3, `FULL_SHARED_CASE`.

| Role | case-01 | case-02 |
|---|---|---|
| A1, A2 | COMPLETED_CONSUMED / ADMITTED | COMPLETED_CONSUMED / ADMITTED |
| A3, A4 | COMPLETED_CONSUMED / completed | COMPLETED_CONSUMED / completed |
| A5 | COMPLETED_CONSUMED / ADMITTED | COMPLETED_CONSUMED / ADMITTED |
| A6 | COMPLETED_CONSUMED / REFUSED | COMPLETED_CONSUMED / ADMITTED |
| A7 | SKIPPED / B3_NOT_SUPPLIED | COMPLETED_CONSUMED / PARTIAL |
| A8 | SKIPPED / W09_PENDING | SKIPPED / W09_PENDING |
| A9 | SKIPPED / W10_PENDING | SKIPPED / W10_PENDING |

Denominators: 9 planned slots per case, 18 total; 13 completed consumed, 5 skipped, 0 refused, 0 failed,
0 quarantined; 35 journal events; zero sockets, zero dispatches; caller inputs byte-identical; cold verify
`VERIFIED`. The B4 receipt id depends on the B4 code identity and is recorded in the PR body.

The frozen R007 text names a "B2 source route" and also a native A6 refusal and B2 A7 not supplied, which a
`SOURCE_REVIEW` case cannot show (A3-A7 are not requested there). R007 therefore runs both readings over the same
pinned receipts: the campaign above, and a literal one with pinned B2 admitted `SOURCE_REVIEW` (A1/A2 consumed, A3-A7
`NOT_REQUESTED`, A8/A9 skipped) plus the same B3 `FULL_SHARED_CASE` (18 slots: 9 consumed, 9 skipped), both cold
verified.

## Restart trace (R006)

- Interrupt after `CASE_VERIFY_STARTED(case-01)`: the lock unwinds; resume writes `CASE_VERIFY_QUARANTINED`, skips case-01 roles `CASE_NOT_VERIFIED`, proceeds to case-02 and seals; the native verifier is entered once per case.
- Interrupt after `ROLE_STARTED(A3)` on the pinned two-case campaign: resume records A3 `QUARANTINED` (`INTERRUPTED_IN_FLIGHT`), skips A4-A6 `PREREQUISITE_NOT_CONSUMED:A3`, completes case-02 (A1-A7 consumed, A7 PARTIAL) and seals; one logical attempt per subject.
- Terminal journal with an interrupted seal: resume seals with no new event. A sealed scratch resumes as `SEALED_VERIFIED` without writing.
- Stale lock, torn, empty, gapped or alien journal files and a changed plan refuse with closed codes and no write.
- A socket attempt during a case verify is journaled as `CASE_VERIFY_QUARANTINED` / `NETWORK_ATTEMPT_BLOCKED` and the run stops unsealed; resume never retries it and seals with that reason visible. The seal's own native re-verify is gated too.

## Independent implementation review

One combined independent reviewer (RUNTIME matrix) returned PASS_WITH_NOTES on an intermediate tree. After fp-check, the true positives were fixed in this PR: the distinct network quarantine, an explicit R008 historical skip, the literal R007 campaign, the D004 code, the manifest-bytes and exact-receipt-bytes binding, and the specific recompute refusal code. The remaining notes are documented in the contract: empty directories, an A3 delivered alone after an A4 interruption, lock edge cases and the CRLF code identity. A seal-gate finding was a false positive from a deliberate mid-experiment snapshot. The current gate has a regression that fails without it.

## Requirement-to-evidence traceability

| Req | Node |
|---|---|
| R001 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_exact_native_case_lineage |
| R002 | tests/data_layer/analytical_research/test_nine_role_coordination.py::test_b4_route_matrix_and_denominator |
| R003 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_pinned_child_origin_pair |
| R004 | tests/data_layer/analytical_research/test_nine_role_coordination.py::test_b4_role_consumers_native_states |
| R005 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_journal_intent_before_call |
| R006 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_resume_quarantine_and_progress |
| R007 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_actual_pinned_two_case_campaign |
| R008 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_native_predecessor_compatibility |
| R009 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_scratch_bounds_authority |
| R010 | tests/tools/alpha/test_run_nine_role_coordination.py::test_b4_seal_exact_cold_verify |
| R011 | tests/data_layer/analytical_research/test_nine_role_coordination.py::test_b4_capability_and_successor_boundaries |
| R012 | tests/data_layer/analytical_research/test_nine_role_coordination.py::test_b4_terminal_denominators_and_failures |

## Capability accounting

Two concept rows (R3-21 pmxt-dev/pmxt-mcp, R3-29 valory-xyz/trader) are static historical references:
`CONCEPT_ONLY` / `PARTIAL_CONCEPT_UNACCEPTED`, not invoked, owner disposition PENDING. The other 34 IDs, including
the B3 rows, are unchanged.

## Limits and deferrals

See `docs/deferred_items_log.md` S10-CAP-NINE-ROLE-COORD-01-D001 to D007: hosted pin absence, no new dispatch,
A8/A9 pending (W09/W10), hard-kill recovery (W11/W12), carried B3 D001-D008 including the R007 split, concept-only
capability rows, and the PR #268 deferred-log collision.
