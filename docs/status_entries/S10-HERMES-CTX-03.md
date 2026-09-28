# S10-HERMES-CTX-03 — Canonical Public Polymarket Identifier Secret-Scanner Compatibility Repair

Status: implementation complete; independent RUNTIME implementation review recorded in the PR body.

PR and current head: see GitHub PR metadata and PR body. This committed fragment is stable
and does not contain a mutable branch-head SHA; exact-head hosted CI, validation evidence
and the independent review disposition are recorded in the PR body.

Side13 final exact-head review: PENDING.
Merge authorized: NO (Karl decides after Side13 exact-head review).
Successor AF1 runtime attempt: NOT AUTHORIZED by this WP.

## Frozen base and scope

- Base/main and PR #194 / S10-HERMES-CTX-02 merge SHA:
  `15097f70f5f5358879fde73b2b30d26ecdb80402`.
- Governance track RUNTIME, risk level 3, package size class L, exact scope 11.
- Exact changed scope: 11 required = 11 allowed = 11 actual paths.
- Negative matrix: T01-T12 and T15 in
  `tests/research_runtime/hermes_controlled_runtime/test_models.py`; T13-T14 in
  `tests/research_runtime/hermes_controlled_runtime/test_context_controller.py`.

## Trigger and root cause

S10-GATE-AF1 Attempt-03 is CONSUMED: terminal TRUE_STOP / PHASE_B_LOCAL_EVIDENCE_DEFECT, AF1
gate result NONE. Its bounded public population succeeded (exactly 1 public population call);
the first blind case then failed `REQUEST_SECRET_DETECTED` inside `build_research_run_request`
before the Hermes backend was invoked. Hermes/provider/model calls: 0. Firecrawl calls: 0.
Accepted provider cost: USD 0. Attempt-03 is neither an AF1 PASS nor an AF1 FAIL.

Root cause (reproduced offline before any source edit): the context controller serializes
canonical `subject_refs` and exact scope into `public_market_context`, and the repository's
canonical public event identity `event:polymarket:0x<64 hex>` matched the shared generic
long-hex secret rule `\b0x[a-fA-F0-9]{40,}\b`. Canonical market and token ids did not.

## Delivered (repair boundary)

- `src/research_runtime/hermes_controlled_runtime/models.py` only. The generic long-hex rule
  stays in `_SECRET_PATTERNS` unchanged (now also bound to the private name
  `_LONG_HEX_SECRET_PATTERN`).
- A private recognizer `_CANONICAL_PUBLIC_POLYMARKET_ID` matches only exact complete
  canonical public identifiers: `market:polymarket:<decimal>`,
  `event:polymarket:0x<exactly 64 lowercase hex>` (repository condition-id contract
  `^0x[0-9a-f]{64}$`), `event:polymarket:market-<decimal>` and `token:polymarket:<decimal>`
  (decimal: non-empty, no leading zero), case-sensitive, delimited by a closed set of
  characters.
- Malformed-event guard: every occurrence of the literal namespace `event:polymarket:` in
  `public_market_context` must begin an exact, delimited canonical event identifier, or the
  request fails `REQUEST_SECRET_DETECTED`. Malformed canonical-looking event ids (other hex
  lengths, `0X`, uppercase or mixed hex, word-glued suffixes such as `g` or `_x`, glued values,
  empty or `sk-` suffixes) fail closed even where the generic rule would miss them.
- `public_market_context` alone goes through `_require_public_market_context`: the same type,
  non-empty and length checks as `_require_str`; the malformed-event guard; the full `_scan_secret` over a
  validation-only copy with recognized identifiers masked; every other secret rule over the
  original text; `_scan_authority` over the original text. Every other request field still
  uses `_require_str`.
- The stored value and the content-addressed request identity use the original bytes.
- No global or caller-configurable allowlist or digest; no schema version, Hermes
  invocation policy identity, provider, model, toolset, argv, retry, output-parsing,
  context-controller or context-protocol change.

## Authority and residual limits

Network authority: NONE. Credential authority: NONE. Provider authority: NONE.
Real Hermes/provider/model calls: 0. Firecrawl/Polymarket/OAuth calls: 0. Secrets read: 0.
Dependencies/locks/workflows: unchanged. AF1 branch, workspace and Attempt-03 evidence:
untouched. AF1 Attempt-03: CONSUMED, gate result NONE. Another AF1 attempt: NOT AUTHORIZED.
H1 #5: NOT AUTHORIZED. Gate C: NOT AUTHORIZED. Capital/orders: 0.

## Successor boundary

After Side13 final review and Karl's separate merge only: refresh merged main, reconcile the
existing local AF1 branch onto repaired main, add AF1's own live-shaped fixture/regression,
produce and refreeze a new AF1 Phase-A head, and independently close successor-attempt
semantics (continuation of Attempt-03's persisted population versus a fresh population under
a new attempt identity) before any new runtime authorization. This package decides and
authorizes none of those steps; Attempt-03 remains permanently CONSUMED.
