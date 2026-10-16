# S10-HERMES-TS01 - Trusted Research Evidence

Status: IMPLEMENTED_LOCAL; independent SIDE20 acceptance pending. Ready for review: NO.
Evidence mode: BLOCKED_NOT_READY for publication (not authorized); no posted-GitHub verification claimed.

## Authority and lineage

Karl authorized the original local eight-path WP and the 2026-10-16 SIDE20 same-run FAST correction. Frozen base: f3791826ca4f7723372e3caa103addcc7fe7aef6; predecessor PR237 head b2c66358c78baf7e06296302bfd08a1e0089517a is an ancestor. Existing worktree C:/GitHub/polymarket-ts01, branch codex/s10-hermes-ts01. The native Remote Main Sync Gate passed. No new branch or WP was started for the amendment.

Historical standalone wp_spec_guard.py missing-certificate command: exit 2 / USAGE_ERROR, an erroneous package instruction, resolved by Karl's amendment. The controlling native FAST readiness command returned exit 0 / IMPLEMENTATION_READY / is_ready=true / certificate_required=false / error_codes=[]. Canonical prompt/spec payloads remain byte-exact extracts; no certificate or guard was changed.

## Implemented scope

Exactly eight paths: two existing source modules, two existing test modules, canonical prompt/spec, this status fragment and the deferred log. Additive collect_trusted_research_pair / export_trusted_research_pair reuse PublicMarketDataClient.get_page and archive_page_attempts. Capture is producer-owned and opt-in, with canonical allowlist URL/params, HTTP status for archived attempts, UTC request/response/receive clocks, monotonic duration, immutable raw identity/hash/length. Only Gamma market-by-id and the first distinct canonical token returned in ordered clobTokenIds link to one CLOB book; book asset/condition and bounded levels are checked.

TS01-only urllib transport disables redirects and environment proxies and reads at most max_response_bytes+1, with defensive Content-Length checks. Existing client behavior/signatures remain frozen. Raw attempts are archived before parsing, and no receipt is promoted for incomplete/failed acquisition. A cross-process exclusive lock serializes cooperative producers; a flushed same-directory temporary receipt is verified cold and atomically renamed, with directory fsync on POSIX. Existing admitted repeats do not reacquire or overwrite; conflicting receipts fail closed.

The private cold raw lookup opens SQLite mode=ro/query_only in one read transaction, rechecks the existing DDL/integrity and active bounds, and rederives frozen raw/occurrence IDs and exact bytes. Export rechecks canonical receipt digest/shape, clocks, source/cursor/URL/params/status, selected 2xx occurrences and Gamma-to-book link. Missing/partial/foreign/tampered evidence returns NOT_ADMITTED without body/path echo or archive writes. No schema, raw-write, old test expectations or public store method set changed.

Proof: trusted local producer witness only. INJECTED transport is explicitly labelled in receipt/export. Fixtures do not prove real upstream observation, signed HTTP provenance, quote freshness, tradability or profitability. A locally editable sidecar is not a signature against an operator who rewrites it and recomputes its digest; the archive and sidecar remain trusted operator evidence. An equivalent copied archive with the exact selected rows proves that same content membership, not a physical-file identity. Interrupted admission can leave a fail-closed lock requiring separate operator inspection; no stale-lock deletion/recovery service is added.

## Validation and evidence

Installed wp-predraft-inspector / wp-minimum-test-plan locator evidence is reused: both python -I -B runs returned SOURCE_LOCATED. Their original nonisolated Python3.14 inspect.py collision and resolution are preserved. verification-before-completion, ponytail and systematic-debugging instructions were read and applied. No delegation or new framework.

Four new assertion-bearing nodes cover R001-R004 in the two scoped test files. Baseline comparison: all four fail on the frozen source because the TS01 capability is absent. Existing WP169 regression family plus new nodes: 116 passed on Windows Python3.14 (one existing datetime warning). Linux Python3.12 focused plus deferred/repo-truth/status checks: 392 passed (one existing datetime warning). Initial focused failures (private-method compatibility and explicit SQLite closure on Windows) were corrected within scope and retained in external logs. No old test or frozen guard was weakened.

Native final readiness --check-diff, exact-scope summary, generated-artifact guard, whitespace, API/DDL/identity/old-test preservation proof and one authoritative stable-HEAD full suite are recorded with actual argv/exits/counts in the terminal ZIP, bound to the exact committed head. This fragment does not predeclare the full-suite result; any failing mandatory check means BLOCKED, regardless of implementation status. The reused validation image is s10-live-orch-validate:py312 (sha256:b0d8417044f711132dd2d458a46e7cceaf2fc0e8168910a6556a9eafbd4b04bd); pip check passed. Validation has network=none, read-only source/root, dropped capabilities, no-new-privileges, noexec /tmp, a dedicated disposable executable /fixtures area, and writable output-only local_data tmpfs. No dependency installed/changed.

Negative matrix: missing/null/type/empty/malformed/duplicate IDs, tokens and receipt fields; wrong host/redirect/proxy; size/Content-Length; non-2xx/retry exhaustion/timeout; invalid/reversed/future-relative-to-receive clocks; raw/DDL/store/receipt tamper; absent rows/store/receipt; overwrite conflict, actual concurrent producers, atomic-promotion interruption, active store bounds and idempotence. Wording/credential-string/strategy-spelling filter categories are inapplicable: no wording filter is implemented. Existing authority scans remain unchanged.

## Boundaries and successor

See docs/ai/codex/PROTECTED_PATHS.md Centralized Boundary Group Reference. Only explicitly scoped offline acquisition/storage evidence changes are made. Credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/locks and external code copying boundaries are not crossed. Generated evidence/environments are external/ignored and never committed.

Workflow network: earlier git fetch/pull only. Product/source/provider/model/account calls: zero; no push, PR, Actions, merge, deployment, paper/live activation, credentials, orders or capital. See deferred items S10-HERMES-TS01-D001 (resolved FAST gate) and D002 (real acquisition/TS02 separately gated). Return one terminal ZIP to Karl for CURRENT SIDE20; publication/CI/merge remain separate owner decisions.
