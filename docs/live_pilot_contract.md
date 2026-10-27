# S10-ALPHA-AUTO-PILOT-01 — dormant attended NBA pilot

Karl authorized software implementation of the exact certified 14-path package.
This contract grants no real credentials, account access, signing, orders, capital,
host changes, deployment, unattended operation or merge. LIVE TRADING STATUS stays
DISABLED. All Centralized Boundary Group Reference entries in
`docs/ai/codex/PROTECTED_PATHS.md` remain controlled by the certified package.

## Foreground interface and authority

`run_pilot_once(*, policy_path, owner_record_path, owner_record_sha256, state_root,
feeder_root, dependencies=None)` composes the existing native orchestrator. Its
only CLI subcommand is `python -m src.live_pilot.pilot run`, with explicit
`--policy`, `--owner-record`, `--owner-record-sha256`, `--state-root`, `--feeder-root`.
Import performs no operation. There is no timer, daemon, retry, alternate-order
path or new custody provider. The factory must be the exact native
InteractiveGateBSecretProvider; each authenticated native session remains attended
TTY/no-echo. The composer calls native methods directly, without the separate
live_orch CLI confirmation phrase. A valid owner record is additionally required.

The dedicated, policy-bound state root is per wallet and must not be shared with
another native caller. A kernel-held pilot-run.lock precedes every native call,
including gateway opening and its RESTARTED event. Contention refuses with zero
native calls. Process death releases the pilot lock; native wallet locking and
recovery ordering are unchanged. Explicit roots and input paths reject symlink /
reparse traversal and credential-like directories; feeder_root is a strict child
of state_root. Owner/policy files are read only. Terminals use exclusive files
under state_root/terminals and are flushed/fsynced. An unusable state root cannot
persist a terminal: its closed return explicitly reports terminal_persisted=false.

## Inputs and bounded policy

The exact certified prompt section 4.3 is the normative policy/owner schema.
Both documents are bounded to 65536 bytes, UTF-8 without BOM, duplicate/unknown
keys rejected, and must equal sorted compact ensure_ascii=False canonical JSON
bytes without a newline. Monetary values are finite plain decimal strings;
counts/seconds are integers excluding bool. The policy digest is SHA256 of the
raw file bytes; it is not itself owner authority. The separately supplied owner
record path and full external SHA256 must pass digest, canonical schema, scope
and validity-window checks, in that order. Karl creates the record at the separate
activation gate; this software never creates or stores one.

The code ceilings cannot be widened: <=2 admissions per rolling24h, <=USD10 native
total commitment including unresolved reserve/unredeemed positions, <=USD5 per
order including fee reserve. Feeder age <=1800s; bound Hermes age <=86400s; observed
loss thresholds <=native5/7.5/10. Tighter positive limits are permitted; margin0
is valid and the stress scenario must strictly exceed it. No clamping. A policy
can authorize only one exact version, host/release, dedicated wallet/signer and
NBA_MONEYLINE_PREGAME_V1/FOK/BUY predicate for at most seven days.

## Invocation, final guard and economics

After validation, sample/latch PILOT_KILL, then reconcile even when killed.
Non-ready reconciliation or any latched kill ends the invocation before intake.
Reconstruct probabilities/identities/rules from completed PR254/255 CYCLE raw
ESPN/Gamma sources, receipt digests and terminal input hashes; never trust derived
forecasts or scores. Per-event latest receipt time/numeric ordinal is deterministic;
identity conflicts/duplicate pairs reject. Source age is nonnegative and bounded;
games must not have started. Source data conveys no authority.

For each verified pair, use that token's own fresh native snapshot best ask as
the sole limit, with exact-two-decimal shares=policy order cap/limit (no rounding
or price search). Native minimums, depth, ticks, fee-inclusive caps and delay0
must pass. Intent literals are BUY/AGGRESSIVE_TAKER/FOK/post_only=false/expiry null.
Stress is shares*min(max(p-.10,0),.5)-shares*limit-native_fee-.005*shares,
strictly above the whole-order margin. This is a conditional full-fill stress
scenario, not unconditional order EV, executable-edge proof or expected profit.
Rank passing pairs by descending stress, ascending start_ns, then lexical token_id.
Only the winner reaches native GateC/preflight/canary; no fallback after failure.

The pilot-owned closure runs inside the existing wallet lock, after local signing
and final native host/geoblock/window checks and before admission. It rechecks the
raw policy/owner record, kill, market binding, all admitted episodes in24h,
native account/risk commitment and loss values. It reruns public native
verify_permit_authority for the same exact permit/intent/stores, rejecting late
lifecycle pause/revoke/head/policy/allocation change or superseding Hermes. It
then resamples time and repeats pregame, every source-receipt age and bound Hermes
decision_time age, including time spent at TTY/signing. Event start is exclusive;
maximum ages are inclusive. No new permit, candidate or limit is substituted.

The single native non-None call-site block resamples time after guard success,
rechecks the exact native permit window, and supplies that time to both admission
calls. Expiry during guard I/O yields PERMIT_EXPIRED and zero admission/transmit.
None preserves the historical native behavior and clock sequence. Guard raise,
non-None return or arbitrary exception cannot admit or transmit. Native durable
ADMISSION->CREATE_STARTED, unknown-response reserve, recovery and consumed-permit
semantics remain authoritative; no second transmit, SELL or redemption is added.

## Evidence and activation

R001/R002 are the two named hook nodes in tests/execution_gateway/test_live_orch.py.
R003-R012 are the exact named nodes in tests/live_pilot/test_pilot.py. The negative
matrix covers malformed/null/type/empty/duplicate/unknown/case keys, nonfinite or
out-of-range values, exact owner digests/windows, stale/future sources and
assessment, event-start boundaries, kill timing, caps/concurrency, native late
authority, native expiry during guard I/O, precision/depth/minimum/fee refusal,
restart replay and sanitized exclusive terminals. Free-text wording filters are
not introduced; their spelling-variant category is N/A. Positive controls include
zero margin, canonical owner record and valid native FOK economics.

Stable implementation evidence belongs in docs/status_entries/S10-ALPHA-AUTO-PILOT-01.md
and the exact-head PR body. Full tests/security, exact scope/readiness, hosted CI
and independent implementation/Side22 review remain required before acceptance.
Deployment, owner eligibility/wallet, custody and capital authorization, attended
canary reconciliation/clean no-CREATE proof, unattended Hermes selection, SELL,
redemption and scaling remain separately gated successors. Revert the14 paths to
remove this dormant composer; no underlying risk/store/GateB/C schema changes exist.
