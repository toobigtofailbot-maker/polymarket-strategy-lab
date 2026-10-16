# S10-HERMES-TS02 — offline reliability core

State: IMPLEMENTED_LOCAL / SIDE20_REVIEW_PENDING / PROVIDER_TOOLFREE_UNPROVEN / CI_PENDING.
Evidence mode: BLOCKED_NOT_READY for publication. Ready for review: NO (release).
Merge ready: NO. Karl authorized the original local WP and exact eight-file same-run
historical compatibility amendment on 2026-10-16. No publication or merge authority.

Frozen main: 7d1e817793612ffc607ff4278abc4a6c71eb9acd; PR238 predecessor head
fc4c6cd0ddf40ffe8816346c1f88d8cf926d6e05 is an ancestor. Native Remote Main Sync Gate
passed with clean current main before the isolated codex/s10-hermes-ts02-offline-core
worktree at C:/GitHub/polymarket-ts02 was created. Exactly eight approved paths.

New import-safe stdlib-only two_stage.py consumes a producer-owned cold TS01 export
result and bounded untrusted Stage A text, binds source hashes/receipt/clocks/cutoff
and native schema into the handoff, invokes only an injected offline callback, then
uses unchanged native strategy draft validation and consistency rules. Immutable
fsynced reservation/stage records prevent redispatch after failure or interruption.
Cold verification is read-only and fails closed. All terminals remain SYNTHETIC_ONLY;
no accepted strategy decision, real-provider/tool-free proof, usage or cost is fabricated.
The journal omits raw source/model/Stage A text. Local evidence custody is required.

The sole historical compatibility edit appends the two exact TS02 source/test names
under one S10-HERMES-TS02 comment. Baseline, both positive virtual paths and the
third-path negative were exercised; regexes, prior allowlist entries and matching
logic remain byte-identical. Existing Hermes/controller/policy/manager and TS01 APIs,
source files and DDL are unchanged. All protected boundary groups in
docs/ai/codex/PROTECTED_PATHS.md retain their authority boundaries.

Native amended RUNTIME readiness: exit 0 / IMPLEMENTATION_READY / eight paths /
certificate_required=false. Affected baseline: 1073 passed, one inherited datetime
warning. New tests first failed collection because the new module did not exist.
An initial negative fixture used wording outside the unchanged native validator's
specific unsafe patterns; corrected to its actual case-insensitive order-placement
pattern. Focused extended check: six passed. Independent review identified lossy
datetime offset/precision admission; the new parser rejects non-RFC3339 shapes and
excess precision rather than truncating. No native validator or old test was weakened.

R001–R004 map to the four named test_ts02_* behavioral nodes in test_two_stage.py;
R005 maps to its named compatibility node plus the actually executed unchanged
Hermes/TS01 regression families. The contract contains the negative-test matrix.
R006 and the final exact-head full local suite outcome/actual counts are retained
in the terminal external evidence ZIP keyed to the final commit. This stable fragment
does not claim a full-suite result before that command executes. Only that final
receipt establishes TS02_OFFLINE_CORE_VALIDATED; independent SIDE20 acceptance and
later exact-head hosted CI/publication remain separate gates.

Skills: Ponytail kept one additive protocol with no provider adapter or framework;
code-simplifier checked the touched code for unnecessary state/abstraction;
systematic-debugging preserved initial failures and found their specific cause;
native source/reuse/test-plan skills located the real contracts; canonical evidence
and runtime-boundary reviews check exact scope/ancestry/claims; independent code
review audits callback mutation, durable replay and clocks before stable validation.
Full actual commands, exits, reviewer outcomes and skill limits belong in the ZIP.

Workflow network: main sync fetch/pull only. Real source/provider/model/account calls,
credentials, push, PR, hosted CI, deployment, paper/live, orders and capital: zero.
S10-HERMES-TS02-D001 keeps actual provider transport and acceptance separately gated.
