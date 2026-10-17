# S10-ALPHA-03A — finite discovery -> offline decision -> research-paper evidence proof

**Authority:** Karl's bounded authorization of the S10-ALPHA-03A package, 2026-10-17. It covers a local, offline Phase-0 proof first, then the six-path implementation, publication and hosted CI.
**Executor:** Claude Code.
**Branch:** `claude/s10-alpha03a-foreground-discovery-proof`.
**Frozen main:** `79bb186a70e1fe51ee9c7f631324eec72079fdf8`.
**Predecessor:** PR #243, head `9c6d4e76041b1321439aace69f77768977b0c568`, merged at frozen main.

**Governance:** RUNTIME, risk 3. No certificate is required. Native readiness is `IMPLEMENTATION_READY`, run before any edit.
**Authority flags:** no credentials, network, scheduler, execution or live authority.

**State:** IMPLEMENTED_LOCAL. Merge ready: NO (Karl merges manually after SIDE20). This fragment is stable and non-self-referential. The live PR head, CI and full-suite counts are in the PR body and the external evidence ZIP.

## Phase-0 no-code result

**Result:** `FINITE_MANIFEST_GAP_PROVEN`.

The probe ran in scratch only, with zero network and native fixtures. It composed:

- the ALPHA-02 universe, triage and queue over a native PIT store;
- the AUTO-01 world stores;
- three AUTO-02 `run_one_cycle` occurrences;
- a WP173 research-paper session.

Each component verified itself, and every source store stayed byte-unchanged. A menu built by ad-hoc glue equalled the native AUTO-01 fixture menu exactly. The native code still lacks three things:

- **G1:** nothing maps queue rows to an AUTO-01 menu, and nothing persists `RESEARCH_NEEDED` or overflow.
- **G2:** an interrupted occurrence is returned but never journaled, and no record lists occurrences or attempted/completed/interrupted totals.
- **G3:** no single digest binds sources, universe, queue, menu, occurrences, paper and assessment for cold replay.

## Scope

Exactly six paths:

- the operator `tools/alpha/run_discovery_learning_proof.py`;
- its seven named tests R001–R007;
- the contract `docs/discovery_learning_foreground_proof_contract.md`;
- this fragment;
- the byte-exact prompt and spec.

Nothing under `src/`, no historical guard, dependency, workflow or configuration changed. Simulating the six paths against 82 historical changed-path and status guard files needed no seventh file.

## Design

- **Phases:** `prepare` freezes byte copies of the explicitly named stores outside the repository. `run` composes the native chain once, and `verify` cold-replays it with a backend that fails on dispatch.
- **Ledger:** STARTED is written before work, and each occurrence gets exactly one terminal. A crash is classified once as `INTERRUPTED_OR_UNKNOWN` and never redispatched.
- **Manifest:** one write-once, sanitized, content-addressed manifest with conclusion `PLUMBING_ONLY`, `VERIFIED_OUTCOME_FEEDBACK_OBSERVED` or `BLOCKED`.
- **Fail closed:** a socket guard blocks the run on any network attempt.
- **Feedback:** stays native. Only the eligible preview with exact identity is `DECISION_LINKED_NONCAUSAL`, and abstentions are `NOT_APPLICABLE_FEEDBACK`.

There is no provider, OAuth, model, market or account call. There is no paper or live order, policy or risk change, scheduler or new registry.
