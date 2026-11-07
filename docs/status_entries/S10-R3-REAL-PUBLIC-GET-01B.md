# S10-R3-REAL-PUBLIC-GET-01B

RUNTIME/DETERMINISTIC, exact 7 paths, branch `codex/s10-r3-real-public-get-01b` from clean synchronized main `ec15c9a5feb3d7502e03ecdde5c00ae58f6ea6ba`.
- PR #276 is merged: head `65c8bbac4fdce221ea9ac984cd9cf13f1b8bb7ba`, merge `ec15c9a5feb3d7502e03ecdde5c00ae58f6ea6ba`. Both are in main ancestry, and `origin/main` was exactly that merge at startup.
- PR #268 is open and untouched; nothing is stacked on it. No other same-WP PR or branch existed.
- Karl sent the first-person authorization in the Claude Code conversation: he authorizes `S10-R3-REAL-PUBLIC-GET-01B` and explicitly approves the exact activation record with SHA-256 `a642058790796d4ec4de25c6b03003d0b0c0242c942a9b5c58843ddc4520634a`. That approval covers this pin PR only. The real GET still needs Karl's merge of this PR and a deliberate post-merge operator instruction. Merge NOT authorized; merge stays Karl-only.

`ACTUAL_LIVE_GET_EXECUTED=NO`. No real public request was made while implementing, testing, running CI or preparing the PR.

PR: see GitHub PR metadata and PR body.
Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.

## Readiness

Package `SIDE24_S10_R3_REAL_PUBLIC_GET_01B_CC_EXECUTION_PACKAGE.zip` (sha256 `a931087982e2d63768bfeb2d122897d775fc543a0d085b3a2fc0fe316f176da3`): `SHA256SUMS.txt` verified for all 6 files. Prompt `61c9f34425450f0ecc1081593649ae7d10089cedc43defc420e964f2064f3d52`, spec `c235146e7c290ec52298fda5e88bf9d1df63655f3e0b7325fd9041854d50a100`; both committed byte-identical, no wording repair needed.

- Native gate on the exact package bytes, on clean main before branching: exit 0, `IMPLEMENTATION_READY`, RUNTIME/DETERMINISTIC, certificate_required=false, scope 7, 8 evidence items, 8 normative rules, error_codes empty. No certificate was required or issued.
- First invoked skill after mandatory startup reads: `ponytail` LITE. The other real invocations are listed in the return ZIP skill ledger.

## Owner record and scratch checks (offline)

- The record file's raw bytes (580 bytes, UTF-8, LF, trailing newline) hash to `a642058790796d4ec4de25c6b03003d0b0c0242c942a9b5c58843ddc4520634a`. The record stays in the owner handoff package and is not committed. Tests rebuild the same bytes from its fields.
- Fields: `wp_id` `S10-R3-REAL-PUBLIC-GET-01`, `attempt_id` `R3-SDK-PUBLICGET-20261107-01`, `max_attempts` 1, the exact request URL, `envelope_sha256` `110be3589860cc1e03f69eb41437941ea5685afb25109cd87cc53b722e82a3e9` (equal to the computed envelope), scratch `C:\Users\Public\Documents\polymarket-r3-sdk-one-get-20261107`, window `2026-11-07T00:00:00Z`..`2026-11-21T23:59:59Z`.
- On the intended Windows host, with every socket blocked: `C:\Users\Public\Documents` exists, is a plain directory (no symlink or junction) and is writable (temp file created and removed). The scratch does not exist yet. `Path.resolve()` keeps the record's exact string, and the repo scratch guard accepts it. With the pin set in memory only, `authorize_live` accepted the exact record at both window edges and refused one second outside each edge. The owner scratch was not created.

## Implementation

- `src/data_layer/analytical_research/official_sdk_public_probe.py`: only the pin and its comment changed. `OWNER_ACTIVATION_SHA256 = "a642058790796d4ec4de25c6b03003d0b0c0242c942a9b5c58843ddc4520634a"`. The request guard, envelope, SDK call, transport, receipt and lifecycle are unchanged. A test proves the source equals the merged Phase A blob (`ff651815…`) once the pin line is reverted.
- `tools/alpha/run_official_sdk_public_probe.py` is not edited. `check` now reports `live_activation: PINNED`; `live` and `verify` are unchanged.
- Tests: the two Phase A seal-only assertions now expect the approved pin. The seal refusal is still exercised by setting the pin to `None` in memory. Eight Phase B tests (R001-R008) were added. A module-wide fixture replaces the real egress factory with one that fails the module, and checks that the owner scratch is never created or changed. Every `CLI.live` call injects a transport, and no CLI call receives the owner scratch.
- Docs: contract (approved record table, two-stage owner procedure, local-marker limitation), deferred items `S10-R3-REAL-PUBLIC-GET-01B-D001`..`D003`, and the original `S10-R3-REAL-PUBLIC-GET-01-D001` status now points at the pin.

## Adoption boundary

All 36 R3 rows stay tracked, with 0 owner value acceptances. R3-23 stays `DIRECT_UPSTREAM_INTEGRATED_OPERATIONAL_VALUE_PENDING_OWNER`. It can advance only after a genuinely executed probe, never on this pin. R3-27 CCXT, Hermes, providers, Lane B and PR #268 are unchanged.

## Validation state

LOCAL_VALIDATION_PENDING.

Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body, not here.
