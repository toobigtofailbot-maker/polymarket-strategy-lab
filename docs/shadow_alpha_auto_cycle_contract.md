# S10-ALPHA-AUTO-CYCLE-01 — bounded autonomous public-research cadence on PR254

This is a non-economic research operator. Karl authorized the six-path RUNTIME
package on 26 October 2026 after native readiness. It repeats the merged PR254
operator (`tools/alpha/run_shadow_alpha_cycle.py`) on a finite timed schedule and
summarizes its ledger. It adds no source adapter, probability method, scorer,
economics, learning, canonical store or order path. It does not call Hermes or any
provider, read credentials, touch accounts, sign, place/cancel orders, create Gate C
permits, deploy, install a timer/unit or run detached.

## Operator interface

```powershell
python -B tools/alpha/run_shadow_alpha_cycle.py init --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_auto.py run --scratch-dir C:/outside-checkouts/shadow --max-cycles 2 --interval-seconds 60 --outcome-every 2 --max-runtime-seconds 600
python -B tools/alpha/run_shadow_alpha_auto.py status --scratch-dir C:/outside-checkouts/shadow
python -B tools/alpha/run_shadow_alpha_cycle.py verify --scratch-dir C:/outside-checkouts/shadow
```

Only an explicitly supplied, already initialized PR254 scratch is accepted: no
default path, no auto-init, no URL, credential or provider option. PR254 path
rules apply unchanged (absolute, outside every checkout, no `.git` ancestor,
credential-like directory, symlink or reparse point; exact frozen configuration).
The scratch root may contain only the PR254 configuration/lock/`op-NNNNNN` entries
and this driver's `auto.lock`/`auto-NNNNNN` entries. Any other entry, such as a file
claiming live authority, fails closed (`SCRATCH_UNEXPECTED_ENTRY`).

## Schedule bounds

| Bound | Value |
|---|---|
| Cycles per invocation | 1–12 |
| Interval | 60–3600 s, fixed slot offsets from session start |
| Outcome update | after cycle slot `k` when `k % outcome-every == 0`, once per slot |
| Maximum runtime | 300–21600 s (6 h) including sleeps; default 21600 |
| Dispatch reserve | no native call with < 150 s to the deadline |
| Late tolerance | slot more than 5 s late is `MISSED_LATE`, never run |
| Clock drift | wall vs monotonic elapsed differing by > 5 s ends the session |
| Consecutive native BLOCKED cycles | 3 ends the session |

The monotonic clock is authoritative for wake-up and deadlines; wall time is
recorded and drift-checked. Sleeps are at most 1 s so Ctrl+C/SIGTERM and the
deadline are observed promptly. Missed slots stay visible and are never compressed
into bursts. Slots at or past the deadline are `NOT_REACHED_DEADLINE`; slots lacking
the reserve are `SKIPPED_DEADLINE_RESERVE`. Nothing dispatches after the deadline.
One foreground process per scratch: a kernel-held `auto.lock` (released on process
death) refuses a second session (`AUTO_SESSION_BUSY`). The native per-operation lock
still serializes each native call, so cycles never run concurrently.

## Native reuse and request caps

Each slot calls native `cycle(root)`; outcome slots call native `update_outcomes(root)`.
Those functions keep every PR254 guarantee unchanged: verify history under the
native lock before dispatch, STARTED-first journal, at most 32 fixed-endpoint public
GETs per operation, no retries/redirects/proxies, 120 s acquisition deadline,
pregame-only forecasts, exact rule admission, native venue economics, outcome
lookahead rejection and once-per-event learning credit. The driver never issues a
request itself; worst-case public GETs per session are therefore `32 × (cycles +
outcome slots)` ≤ 768. A native `BLOCKED` terminal (e.g. public source unavailable)
is a recorded occurrence; the next scheduled slot is a new occurrence, not a retry.

A native refusal before its own journal (corrupt history, native lock contention)
ends the session as `FAILED_CLOSED`. On Windows native lock contention surfaces as
an OS error rather than `OPERATION_BUSY`; the driver records
`NATIVE_IO_OR_LOCK_ERROR` and fails closed either way.

## Session evidence and restart semantics

Each `run` verifies the native ledger and prior driver sessions cold, then creates
`auto-NNNNNN/started.json` and appends exclusive, fsynced `event-NNN.json` records:
`DISPATCH_STARTED` before each native call, then one result (`COMPLETED`,
`NATIVE_BLOCKED`, `FAILED_CLOSED`) binding the native operation name and its
terminal SHA-256, or a schedule state (`MISSED_LATE`, `SKIPPED_DEADLINE_RESERVE`,
`NOT_REACHED_DEADLINE`) or `INTERRUPTED`. `terminal.json` binds every event hash
and stores the summary. A session left without terminal (crash) receives only an
`INTERRUPTED_OR_UNKNOWN` marker on the next `run`; its events and every native
sub-ledger are never rewritten. A native operation interrupted mid-cycle is marked
by the native operator itself on its next call and is never redispatched.

`status` and native `verify` are cold: zero public calls and zero writes. `status`
re-runs native verify (full replay) plus driver-session checks; an edited event,
native terminal or source fails closed (`AUTO_JOURNAL_HASH_MISMATCH`,
`AUTO_NATIVE_BINDING_MISMATCH`, native hash/replay codes). These are local
consistency checks, not signatures against an attacker rewriting all hashes.

## Summary semantics

The JSON summary (stdout; human lines on stderr) is derived only from the verified
native ledger. It reports native operations by kind/status; public requests
attempted/succeeded/failed/outcome-unknown and interrupted operations; unique
markets vs market occurrences; unique predictions/events vs forecast occurrences;
outcome candidates scorable/unscorable with native action and reason counts;
resolved-event states, mean Brier/log loss of the publisher forecast vs the market
midpoint when resolved events exist, and the native learning status; and per
session the schedule states. Missing values are `UNKNOWN` or null, never zero.

Evidence classes stay separate: `PUBLISHER_FORECAST_VS_MARKET_MIDPOINT` forecast
quality; `CONDITIONAL_FULL_FILL_SCENARIO_NOT_ACTIONABLE` economics (native
`RESEARCH` scenarios with their conservative if-filled range); per-intended-order
EV `UNKNOWN_UNMEASURED_FILL_RATE`; fill probability `UNKNOWN`; native paper evidence
only if a PR254 `link-paper` occurrence exists; live filled P&L and realized profit
null. `actionability` is `NO_ACTIONABLE_EDGE` unless the native engine itself
emits `SHADOW_CANDIDATE` (it currently never does). `edge_claim` and
`statistical_significance` are `NOT_ESTABLISHED`. `NO_ACTIONABLE_EDGE` is a
successful outcome, not a reason to loosen thresholds.

## Boundaries, successor and rollback

All Centralized Boundary Group Reference entries in
`docs/ai/codex/PROTECTED_PATHS.md` remain closed. The scheduler authority here is a
bounded foreground loop only; no persistent service, VPS/systemd change or
production store. The separately gated PROTECTED `S10-ALPHA-AUTO-PILOT-01` owns any
standing owner policy, unattended signer, Gate C, account/geoblock checks, order
placement and reconciliation; nothing in this package implements or pre-authorizes
it. Revert the six additive paths to remove this capability; PR254 files are
unchanged.
