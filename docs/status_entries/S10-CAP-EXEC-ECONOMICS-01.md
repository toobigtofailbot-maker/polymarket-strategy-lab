# S10-CAP-EXEC-ECONOMICS-01

B3: shared-PIT A7 execution-economics diagnostic over the merged B2 receipt and the existing native producers.
An offline diagnostic of exactly 11 paths. Branch `codex/s10-cap-exec-economics-01` was cut from clean synchronized
main `55fee02` (merge of PR #285, head `045f3f1`). PR #268 is open, separately owned and untouched; nothing is
stacked on it.

## Identity

- WP ID: S10-CAP-EXEC-ECONOMICS-01
- Title: B3 — Shared-PIT A7 execution-economics diagnostic (point mechanics + optional native replay refusal)
- Branch: codex/s10-cap-exec-economics-01
- PR: see GitHub PR metadata and PR body.
- Base commit: 55fee0293c1687812d3fdf64d5099e4d5b4ab530
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and the PR body. This status fragment is stable and non-self-referential; it does not try to encode dynamic PR metadata or the SHA of the commit that contains it.
- Merge commit: (fill after merge)
- Evidence mode: recorded in the PR body (selected under docs/ai/codex/WP_EXECUTION_STATE_MACHINE.md from the posted-body verifier result)

## Authority Posture

- Package class: B3_OFFLINE_SHARED_CASE_EXECUTION_ECONOMICS_DIAGNOSTIC.
- Implementation authority: YES. This is Side26's exact B3 grant under Karl's standing software-development authorization, conditional on native readiness.
- Report/export authority: YES (PR and report-back only).
- Paper authority: NO. This includes simulated paper creation; WP173 is called only to prove its refusal.
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Strategy mutation authority: NO. The StrategyVersion is a caller-frozen synthetic fixture.
- Source/data acquisition authority: NO. Synthetic venue bodies and a synthetic PMXT-format file only; Synpath is not invoked.
- Model/provider spend authority: NO (zero provider, LLM or Hermes calls in B3)
- Runtime/scheduler authority: NO (one finite manual operator; no daemon or loop)
- Canonical evidence authority: offline SYNTHETIC_TEST_ONLY receipts only; no canonical store writes.
- Network authority: none for runtime, product, source or provider APIs. Workflow network only: git fetch/push, GitHub PR publication and hosted CI.
- Dependency-change authority: NO
- Protected boundary groups (docs/ai/codex/PROTECTED_PATHS.md): all untouched. These are credentials/secrets, authenticated clients, wallet/account, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts.

## Readiness

- The native readiness gate ran on the actual checkout before any source edit: exit 0, `IMPLEMENTATION_READY`, scope 11, 12 evidence items.
- Two non-semantic fixes to the frozen prompt; the spec bytes are identical to the package:
  - Trailing spaces were stripped from 7 lines so that `git diff --check` passes.
  - In section 4, "Receipt outer keys exactly schema_id=…" now reads "Receipt outer fields exactly schema_id=…". The pinned gitleaks 8.27.2 `generic-api-key` rule fired on the keyword "keys" next to the quoted schema literal (a false positive). An ignore entry would need a 12th path.
- The gate was rerun on the fixed prompt with the same result (11/12/12).
- The package and committed prompt SHA-256 values are recorded in the PR body with the gate output.

## Implementation

Contract: `docs/execution_economics_spine_contract.md`.

- `execution_economics_spine.py` steps:
  - Closed case validation.
  - `select_leg`: one A5 `ADMITTED` model that contains the target, one A7-pointer basket and exactly one target leg by market id and YES/NO side.
  - `bind_snapshot`: frozen REL request, then the cold-verified SRC-01 grounding, then native REL `_venue_snapshots`. The snapshot id must equal the B2 leg and the REL `BOUND` record, and acquisition must not be later than the decision.
  - `assess_point`: native StrategyVersion/ExecutionIntent loaders, then `assess_execution_feasibility` at the REL clock, plus full recomputation and round trip, with a `{value, unit}` projection.
  - `replay_diagnostic`: WP167 describe, then WP168/172 market truth, then `assess_executable_edge` on non-OOS WP170 records, an in-memory serialization round trip, then the required WP173 `WP172_BINDING_INVALID`.
  - A7 role, the seven-ID ledger, and core/finalize.
- `run_execution_economics_spine.py` has two commands:
  - `run`: write-once scratch, socket block, lstat caps before hashing, then freeze and re-hash, a nested B2 cold verify, Parquet footer bounds, and the receipt.
  - `verify`: read-only, with a full recompute and exact canonical core bytes.
- Every native producer and the roadmap archive are byte-unchanged; no native module imports B3.

## Validation Split (Side26-approved)

The Windows host has the exact Hermes pin, but its application-control policy blocks the pyarrow and nautilus native libraries. The Linux container runs those libraries but cannot run the Windows-only pin. The work is split as follows (deferred row D002):

- **R007 (host).** Real pinned B1-A, then a complete B2 run, then a B3 run with replay `NOT_SUPPLIED`, with cold verify, zero sockets and byte-identical caller inputs.
- **R004, R005, R012 (container and hosted CI).** These run the real WP167/168/172 diagnostic and the WP173 refusal over the same native B2 world. They do so through the pure module and through the operator's compute path, where only the nested B2 verifier is a recorder.
- **B1-B float drift.** A B2 scratch built on the host does not cold-verify in the container. This is a pre-existing B1-B difference (deferred row D003), so B3 verifies B2 only on the platform that produced it.
