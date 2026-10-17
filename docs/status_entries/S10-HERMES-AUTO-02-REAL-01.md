# S10-HERMES-AUTO-02-REAL-01 — dormant one-request Hermes Codex wire / honest origin

Authority: Karl's local/offline Claude Code execution authorization, 2026-10-16. Executor:
Claude Code. Branch: `claude/s10-hermes-auto02-real01-one-request`. Frozen main
`7c62419ba5d7cb1d3edf61d96a0cb3039b16650f`. Predecessor: PR #241 head
`722e8feec18f31aeeda0f0b0b7ddd9f19eb403e4`, merged at frozen main.

State: IMPLEMENTED_LOCAL / SIDE20_REVIEW_PENDING. Evidence mode: BLOCKED_NOT_READY for
publication. Ready for review: NO (no PR authorized). Merge ready: NO.

Scope: exactly twelve paths.

- One new Hermes child module (`real_provider_stage_b.py`).
- Additive seams in `autonomous_feedback.py` and AUTO-01 `autonomous_opportunity_cycle.py`.
- Three focused test files.
- The contract `docs/hermes_real_provider_stage_b_contract.md`.
- This fragment.
- The governing prompt and spec.
- Exact literals plus a hostile-sibling negative in two historical Hermes guards. The
  architecture guard is unchanged.

Native readiness correction (structural only): the prompt's section-8 anchors gained the
`Negative test matrix:` and `Successor boundary:` signals. Scope, authority and
requirements are unchanged.

Exact-pin offline findings:

- The final post-SDK wire has no tools and goes to the approved endpoint.
- The SDK runs with `max_retries=0`.
- Every one of 16 fake scenarios emits exactly one generation POST.
- AIAgent init would make an authenticated `/codex/models` probe; sterile config
  suppresses it.
- Native `run_codex_stream` retries once, so it is bypassed.
- The Codex assembler echoes the requested model, so model identity stays
  `MODEL_IDENTITY_UNVERIFIED`.

Every record is `OFFLINE_WIRE_SIMULATED`, `PROVIDER_NOT_INVOKED` and
`REAL_ORIGIN_UNVERIFIED`. The AUTO-01 real-origin seam fails closed, and legacy and
offline-producer receipts are byte-identical to the frozen main.

The external evidence ZIP records the final SHA, the focused and full-suite counts, and
the skills ledger. This fragment does not anticipate them.

Zero provider/model calls, credential or auth-store access, product network, account,
orders, capital, scheduler or deployment. Workflow network was limited to a read-only git
fetch and read-only PR metadata. Independent CURRENT SIDE20 review is required. The
successor S10-HERMES-AUTO-02-REAL-01-ACTIVATION is a separately PROTECTED one-call
authorization.
