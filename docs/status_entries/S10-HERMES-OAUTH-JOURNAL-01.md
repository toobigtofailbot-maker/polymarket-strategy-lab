# S10-HERMES-OAUTH-JOURNAL-01 — atomic OAuth Stage B terminal-journal publication

**Authority:** Karl's targeted-repair authorization, 2026-10-17. It covers one separate minimal WP/PR from clean main.
**Executor:** Claude Code.
**Branch:** `claude/s10-hermes-oauth-journal-atomic-01`.
**Frozen main:** `79bb186a70e1fe51ee9c7f631324eec72079fdf8`.
**Predecessor:** PR #243, head `9c6d4e76041b1321439aace69f77768977b0c568`, merged at frozen main.

**Governance:** RUNTIME, risk 3. No certificate is required, and native readiness is `IMPLEMENTATION_READY`. The authority covers source runtime, Hermes runtime, tests, docs and this WP's own spec artifacts. It does not cover credentials, network, scheduler, execution or live.

**State:** IMPLEMENTED_LOCAL. Merge ready: NO (Karl merges manually after SIDE20). This fragment is stable and non-self-referential. The live PR head, CI and full-suite counts are in the PR body and the external evidence ZIP.

## Defect

Hosted CI run 39048125375 failed in `test_oauth_one_post_crash_replay_no_retry`. It ran on PR #244, job compat ubuntu-24.04 / py3.14.

- **What failed:** in the six-thread step, one losing caller returned `JOURNAL_INVALID`. Exactly one dispatch still occurred.
- **Cause:** `run_oauth_attempt` published the terminal journal with `open("xb")` and then wrote it. A concurrent caller could see the file exist while it was still empty or partial, and fail to parse it.

## Repair

`_publish_terminal` now publishes the terminal in four steps:

1. Write the bytes to a private same-directory `tempfile.mkstemp` file.
2. Flush and `os.fsync` it.
3. `os.link` it into the terminal path. The link is atomic and never overwrites: `FileExistsError` keeps an existing terminal immutable.
4. Always unlink the temporary file.

A crash before the link leaves only the reservation, and `ATTEMPT_ALREADY_RESERVED` blocks any further dispatch. Nothing else changes:

- reservation;
- the one-dispatch maximum;
- no retry and no fallback;
- record bytes and schema;
- statuses;
- replay identity verification;
- the `JOURNAL_INVALID` result for a genuinely corrupted completed journal.

## Scope

Exactly five paths:

- the OAuth module;
- its existing test file, with one new test, `test_oauth_terminal_publication_is_atomic`;
- this fragment;
- the prompt and spec.

## Evidence

- **R001:** the writer pauses deterministically after fsync. Concurrent callers see no terminal and get `ATTEMPT_ALREADY_RESERVED`. The test also covers the overwrite refusal and a crash before publication.
- **R002:** the existing crash/replay/concurrency matrix passes unchanged.
- **Mutation probe:** restoring the pre-fix publication makes R001 fail, because the terminal is visible mid-write.

No OAuth, provider, credential, market or account activity was used.
