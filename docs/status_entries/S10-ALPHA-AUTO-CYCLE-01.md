# S10-ALPHA-AUTO-CYCLE-01 — bounded autonomous public-research cadence

## Identity

- Branch: `claude/s10-alpha-auto-cycle-01` (Claude Code isolated worktree; the
  prompt's suggested `codex/` name is advisory).
- Base commit: `7506f62c7d55d3065f928d93971caf6b1d5519a9` (PR #254 merge; PR #254
  head `943689567f4c84ed55232143d8f69069bc03a93e`; PR #253 ancestry verified; no
  open PRs at start).
- Authority: Karl's SIDE22 first-person bootstrap, 26 October 2026; RUNTIME,
  risk 3, exact six-path M package; implementation only after native readiness.
- Current live PR head, exact-head CI and evidence mode: see the PR body; this
  fragment is non-self-referential.
- Merge, deployment, persistent service, live capital and canary operations: NOT AUTHORIZED.

## Readiness normalization

The imported Side22 candidate first failed native readiness:
`READINESS_PACKAGE_GUARD_INVALID` (spec transition failure category
`IMPLEMENTATION_INCOMPLETE` is not a canonical category; replaced with
`SEMANTIC_CONTRADICTION` as in PR254), then
`READINESS_PROMPT_STRUCTURE_INVALID` and `READINESS_RULE_MATRIX_INVALID` (missing
native signals and matrix). One batch appended prompt section 9 restating
sections 1-8 in native vocabulary with a seven-row matrix mapped to the existing
semantic paths and R001-R007. Scope, authority and evidence plan are unchanged.
The gate then returned `IMPLEMENTATION_READY` (RUNTIME, DETERMINISTIC, 6 files,
7 evidence items, 7 rules).

## Implementation and scope

Exactly six additive paths: the foreground driver, its focused tests, the
contract, this fragment and the governed prompt/spec. PR254 files, `src/**`,
protected paths, dependencies, workflows and central status docs are unchanged.
CC's canary branch, worktree, host, credentials and stores are not touched.

`tools/alpha/run_shadow_alpha_auto.py` schedules native PR254 `cycle` and
`update_outcomes` on fixed slots (1-12 cycles, 60-3600 s interval, at most 6 h,
150 s dispatch reserve, no catch-up, drift stop, three-blocked stop, kernel-held
session lock) and derives a ledger-only summary. `status` is cold and write-free.
It adds no source, request, probability, economics, learning or order path. The
summary also reports the venue `secondsDelay` observed in frozen discovery bytes,
because the protected successor's eligibility depends on it.

## Real bounded public run (outside the checkout)

26 October 2026 19:33:55-19:35:32 UTC; `run --max-cycles 2 --interval-seconds 60
--outcome-every 2 --max-runtime-seconds 600`; session `COMPLETED`; cycle dispatches
60.0 s apart. Three native operations: two cycles
(`SHADOW_INTELLIGENCE_REAL_EVIDENCE_PASS`) and one outcome update with zero
requests (no game had started). 54 public GETs (Gamma 2, ESPN 20, CLOB 32), 54
available, 0 failed, 0 unknown; zero provider, account, wallet or order calls.
49 unique NBA moneyline markets / 98 occurrences; 8 forecast events / 16 forecast
occurrences (16 prediction ids because each re-fetch has new source bytes);
32 outcome candidates: 17 scorable, 15 unscorable; native actions NO_TRADE 30,
DEFER 2; reasons NONPOSITIVE_STRESS_EV 17, MINIMUM_OR_DEPTH_UNSUPPORTED 13,
BOOK_STALE 2. Zero RESEARCH scenarios; `NO_ACTIONABLE_EDGE`; zero resolved events.
All 49 markets reported `secondsDelay` 0 at pregame discovery.

Offline `status` and native `verify` re-derived all three operations with zero
fresh attempts. An independent stdlib script (no repo code) recomputed every
source/input/terminal hash (0 mismatches), the counts above and an identical
scratch tree hash before and after `status`. These are software and source
observations, not evidence of predictive skill, fill probability or profit.

## Independent review

One independent read-only review of the driver and tests (separate agent context,
focused tests 25 passed) found no HIGH issue and eleven MEDIUM/LOW findings. All
same-scope findings were fixed in one batch with regressions: requests inside
interrupted operations now land in a bucket (attempted = succeeded + failed +
unknown); the misleading `fresh_attempts: 0` in `run` output was replaced by
`session_public_requests`; skipped slots also record their due outcome update;
interrupted-session markers bind `started.json` and events and are verified;
event operation names are format-checked, bound once and kind-matched; the newest
native operation is bound only when its terminal result equals the returned
result; Ctrl+Break is handled and hard-kill behavior is documented; the runtime cap
is documented as a dispatch cutoff; outcome states are labelled as check
occurrences; vague R004 assertions were made exact; the symlink check is a separate
test node that skips visibly where symlink creation is not permitted. A torn first
write of a new session failing closed matches the native pattern and is unchanged.
The real-run evidence above was produced by the pre-review head `cc2af95`; the
fixes do not change dispatch, requests or native calls.

## Validation

Exact commands and final counts (focused, adjacent PR254, full suite, readiness
`--check-diff`, exact-scope helper, generated-artifact guard, `git diff --check`,
hosted CI) are recorded in the PR body.

## Negative-test matrix

| Category | Evidence |
|---|---|
| Invalid schedule arguments, deadline/reserve, missed slot and its outcome, clock drift, Ctrl+C while waiting | `test_schedule_bounds` |
| Native seams called, no duplicated engine | `test_native_reuse` |
| Failed requests, consecutive blocked stop, session/native lock contention | `test_evidence_denominator` |
| Stale book, unknown fees, changed rule, started game, no outcome lookahead | `test_source_invariants` |
| Zero-write status, interrupt mid-cycle denominators, crash marker, tampered event/marker/operation name/source, unexpected entry, checkout path | `test_restart_safety` |
| Symlinked scratch (skips visibly without symlink privilege) | `test_scratch_symlink_refused` |
| Import isolation, no credential/env/URL surface, hostile metadata | `test_authority_separation` |
| Positive full-fill scenario stays non-actionable; resolved Brier without learned claim | `test_quality_measurement` |

## Limitations

- On Windows, native PR254 lock contention raises an OS error before
  `OPERATION_BUSY`; the driver records `NATIVE_IO_OR_LOCK_ERROR` and fails closed.
  PR254 is outside this scope and unchanged.
- The run window was short: no game resolved, so forecast quality is UNKNOWN.
- Pregame `secondsDelay` 0 is a discovery observation only; live admission must
  be re-checked natively at order time.

## Network

Workflow network: remote Git/GitHub synchronization and PR publication. Product
research network: the bounded public Gamma/CLOB/ESPN GETs above with durable
receipts. Provider inference, account/wallet access, signing, order
placement/cancel, deployment and capital attempts: zero.
