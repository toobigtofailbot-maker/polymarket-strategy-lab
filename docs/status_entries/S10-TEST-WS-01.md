# S10-TEST-WS-01 Status

- WP: `S10-TEST-WS-01` — Deterministic Reconnect Synchronization in Market WebSocket Tests
- Base: `d7891ed63b4c58c9cc150cd0c750c262ca8e5a74`
- Predecessor: PR #198 / `S10-GATE-QUAL-01`, head `ec97a25b3e3174bfa71e3799110e729247dfa026`, MERGED at
  the base SHA (`isDraft=false`)
- Package class: `DETERMINISTIC_TEST_SYNCHRONIZATION_REPAIR`; size M
- Governance: FAST, risk 1, capital at risk USD 0; no draftability certificate required
- Scope: exactly 8 paths; tests-only; dependencies, locks and workflows unchanged; zero `src/` paths
- Branch: `codex/s10-test-ws-01-deterministic-reconnect-sync`
- Readiness: `IMPLEMENTATION_READY` (governance track FAST, minimum FAST, 8 files)
- Authorization: Side13 Option B (all four wall-clock-sensitive reconnect tests)
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body (created Ready for Review, never Draft).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit
  containing itself.
- Merge commit: not merged; merge NOT AUTHORIZED by the executor
- Merge authorized: NO

## Trigger

Hosted CI run 36437422894 (PR #198, head `ec97a25`), compat job windows-2022 / py3.12, failed
`test_non_store_limit_failed_append_reconnects_not_silently_continues` with `assert 1 >= 2`. The
test slept a fixed 1.4 s assuming the real first reconnect backoff (`_BACKOFF_SCHEDULE[0] == 1` s)
had completed; on a slow runner stop landed during RECONNECT_WAIT and no second socket opened.
Timing flake, not a product regression. The same pattern existed in three sibling tests.

## Change

`tests/data_layer/polymarket/test_market_truth_websocket.py` gains two helpers
(`_wait_for_condition`, `_polling`) with a finite 30 s bound: on timeout the runner is stopped,
awaited with the same bound, and `pytest.fail` names the missing condition (never a hang).

| Test | Synchronization (replaces fixed sleeps) |
|---|---|
| `test_reconnect_uses_current_subscription_set_not_original` | first-connection payload sent; all three dynamic updates sent on socket #1; reconnect subscription payload actually emitted on socket #2 before stop |
| `test_normal_book_gaps_are_persisted_and_healed` | durable OPEN `TIMESTAMP_REGRESSION` gap row before queueing the fresh book; HEALED gap row itself before stop |
| `test_continuity_fault_triggers_reconnect_wait` | bounded `asyncio.Event` for socket #1 open, then for reconnect socket #2 open |
| `test_non_store_limit_failed_append_reconnects_not_silently_continues` | bounded `asyncio.Event` for reconnect socket #2 open |

The real 1 s product backoff is exercised unchanged. All existing assertions are unchanged.
`src/` changes: 0; `_BACKOFF_SCHEDULE`: UNCHANGED; backoff/sleeper injection API: NONE.

## Local Proofs (uncommitted, local-only)

- 20x repetition of the four repaired tests: 20/20 runs passed (4 passed each).
- Slow-runner simulation (uncommitted pytest plugin stretching the first backoff to 3 s): the four
  repaired tests pass; the four pre-WP tests from `main` all fail under the same plugin,
  reproducing the CI flake class.
- Red sensitivity (uncommitted mutations of a scratch copy): suppressing the disconnect, the
  healing book, the continuity fault, or the non-store-limit append failure each fails clearly
  within 30 s with `timed out after 30.0s waiting for <condition>`; none hangs.

## Authority Posture

- Implementation authority: YES (this exact FAST tests-only package)
- Network authority: none for product/runtime/API/account behavior; workflow network only for
  the Remote Main Sync Gate (git fetch), branch push, Ready-for-Review PR publication and
  hosted-CI observation
- Strategy / paper / execution / live / credential / scheduler / dependency / workflow authority: NO
- Gate C: NOT AUTHORIZED; capital/orders: 0

## Scope Boundary

Changed files (exactly 8):
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/status_entries/S10-TEST-WS-01.md`
- `docs/wp_specs/S10-TEST-WS-01/wp_prompt.txt`
- `docs/wp_specs/S10-TEST-WS-01/wp_spec.json`
- `tests/data_layer/polymarket/test_market_truth_websocket.py`
- `tests/test_project_status_docs.py`
- `tests/test_repo_truth_docs.py`

No deferred item is created or resolved.
