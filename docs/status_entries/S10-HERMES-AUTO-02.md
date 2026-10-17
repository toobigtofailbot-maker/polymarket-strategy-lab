# S10-HERMES-AUTO-02 — tool-free producer / provenance-bound choice / paper feedback

Authority: Karl's local/offline Claude Code authorization, 2026-10-16. Executor: Claude
Code. Branch: `claude/s10-hermes-auto-02-provider-feedback`. Frozen main
`9ffbdb438226216aa59aa7a532bfb0899247a7f4`. Predecessor: PR #240 head
`50ea1654d2640e5f8fd74e508c7d6faeee8d31ba`, merged at frozen main.

State: IMPLEMENTED_LOCAL / SIDE20_REVIEW_PENDING. Evidence mode: BLOCKED_NOT_READY for
publication. Ready for review: NO (no PR authorized). Merge ready: NO.

Scope: exactly twelve paths.

- Two new Hermes child modules.
- The additive AUTO-01 method.
- Three focused test files.
- The contract `docs/hermes_autonomous_provider_feedback_contract.md`.
- This fragment.
- The governing prompt and spec.
- Exact literals in two historical Hermes guards. The input/output guard also needs the
  two new test literals, because its `hermes.*runtime` pattern matches the test directory.
- `tests/test_architecture_boundaries.py` is unchanged. Hypothetical unknown siblings
  stay rejected.

Native readiness corrections, all structural; scope, authority and requirements are
unchanged:

- The prompt gained `Governance track expected: RUNTIME` and a section-8 anchor block
  (objective, authority/non-authority, hard stops, evidence plan, successor, report-back).
- The spec's non-canonical fourth state transition (`EVIDENCE_INCOMPLETE`) was removed.
- R006 now names a single unambiguous node. The old duplicate name exists in both guard files.

Pre-implementation proof: the exact pin 345cd2b, probed offline with
`enabled_toolsets=[]`, showed zero effective model-facing tools after native post-load
injection, and no `tools` key in the serialized request. The `None` control exposed the
default tools. The only network target was the denied loopback placeholder. A real
provider transport remains DISABLED / NOT PROVEN. Provider-side tool isolation is UNPROVEN.

Results: the offline injected choice is producer-bound and labelled
OFFLINE_PRODUCER_BOUND / MODEL_ORIGIN_UNVERIFIED. It reaches the unchanged native
EXEC-FEAS / Gate C preview. A verified simulated research-paper snapshot drives the next
native PERFORMANCE_UPDATE assessment through a FakeHermesBackend. Every denial is a
journaled denominator outcome, and replays never redispatch. All fixtures are SYNTHETIC.

The external evidence ZIP records the final SHA, the focused and full-suite counts, and
the skills ledger. This fragment does not anticipate them.

Zero provider/model calls, credential access, product network, account, orders, capital,
scheduler or deployment. Workflow network was limited to a read-only git fetch.
Independent CURRENT SIDE20 review is required. The successor S10-HERMES-AUTO-02-REAL-01
is separately gated.
