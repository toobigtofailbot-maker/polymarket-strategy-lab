# S10-HERMES-CTX-01 — Blind-First Hermes Context Broker

Status: DRAFT (implementation complete; awaiting Side12 independent exact-head review)

PR and current head: see GitHub PR metadata and PR body. This committed fragment is stable
and does not contain a mutable branch-head SHA.

Ready for review: NO until exact-head hosted CI and posted PR evidence are reconciled.
Merge authorized: NO.

## Frozen base and scope

- Base/main and PR #188 merge SHA: `7495427820c892497e9c195a8b130c2d32102c67`.
- Exact changed scope: 34 required = 34 allowed = 34 actual paths, including Amendment 01's
  package-id compatibility, Amendment 02's Hermes allowlist, and Amendment 03's committed-diff
  WP/S10 machine-spec discovery correction.
- Pinned Hermes: v0.21.3, release tag v2026.9.14, source commit 345cd2b.
- Negative matrix: N01-N14 covered by the three focused context modules plus existing
  model, runner, and controller tests.

## Delivered

- Immutable campaign/state/artifact/revision/verification protocol and caller-rooted,
  content-addressed append-only artifact store.
- Blind barrier followed by explicit verified Alpha registry + shared provenance/PIT
  reveal selection; exact reveal identity and deterministic untrusted-data framing.
- Backward-compatible ordinary-H1 behavior plus an explicit required context-claim contract.
- Exact-source grounding, fixed evidence precedence, contradiction/falsification pass, and
  separate structural/substantive quality gates.
- Managed memory/profile/auxiliary/skill/lazy-install/private-URL isolation and expanded
  instruction-bearing research-home preflight.
- Read-only exact-session telemetry projection with hashes/digests and truthful unavailable/
  unknown fields for remote Firecrawl and physical attempt count.

## Authority and residual limits

Real Hermes/provider calls: 0. Real Firecrawl calls: 0. OAuth/credential changes: 0.
Wallet/market network calls: 0. Paper/live/economic orders: 0. H1 #5: NOT AUTHORIZED.
Remote Firecrawl HTTP/redirect telemetry remains UNAVAILABLE. Same-provider recovery is
UNKNOWN_POSSIBLE and exact physical provider attempt count remains UNKNOWN when not directly
attested. HERMES-SI gains no authority. Gate C/capital/orders remain unchanged.

After separate merge authorization and merge, the mandatory successor is S10-WALLET-02;
S10-ALPHA-02 remains after WALLET-02.
