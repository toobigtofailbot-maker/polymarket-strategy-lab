# Reusable WP Prompt Blocks

## Applies To

Codex and Claude Code.

## Purpose

These blocks reduce repeated boilerplate across work packages. A WP may reference a block by name instead of reproducing the full text. The block text is authoritative; active WP scope, forbidden scope, and acceptance/failure criteria always override blocks where they conflict.

Reusable blocks do not:

- Replace package-specific WP fields.
- Authorize scope expansion beyond the active WP.
- Substitute for actual evidence in the final report.

## Required Per-WP Fields (Not Replaceable By Blocks)

Every WP must still specify:

- WP ID and title
- Governance track expected: FAST / RUNTIME / PROTECTED
- One canonical `BEGIN_GOVERNANCE_AUTHORITY_V1` block mirroring spec risk and
  all sixteen authority booleans
- Branch name
- Required previous merge commit
- Package class
- Objective
- Allowed files (expected new and modified files)
- Forbidden scope
- Package-specific tests
- Acceptance criteria
- Failure criteria

## Standard Preflight Block

1. Confirm local branch is `main`.
2. Confirm working tree is clean (`git status --short`).
3. Run `python tools/git/preflight_generated_artifact_guard.py`. Stop if it fails.
4. Run `python tools/git/preflight_sync_main.py` with `--required-commit <hash>` and `--required-file` flags for all expected previous WP files. Stop if it fails.
5. Confirm local `HEAD` equals `origin/main`.
6. Confirm required previous merge commit is present in `git rev-list HEAD`.
7. Create WP branch only after clean preflight.

See `docs/codex_execution_guidelines.md` for the full sequence.

## Standard Security Check Block

Run in this order:

1. `python tools/security/verify_project_gitleaks.py` — report exit code and result.
2. `python tools/security/check_security_tools.py` — report availability of semgrep, pip-audit, and other tools.
3. `python tools/security/run_available_security_checks.py` — report result for each available tool.

Report unavailable tools as UNAVAILABLE/SKIPPED. Do not report them as passed. Unavailable tools are not a blocker for docs-only / no-dependency WPs, but the status must be stated honestly.

See `docs/security_and_secrets.md` and `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` for summarization rules.

## Standard Validation Block

After all changes are committed:

1. Run `python -m pytest tests/<wp-specific-test>.py` — report counts.
2. Run the track-required stable-candidate broad/full suite — report the exact
   local command/counts or the equivalent exact-head hosted-CI run. PROTECTED
   retains the local full-suite requirement.
3. Run `git diff --check` — confirm no whitespace errors.
4. Run `python tools/git/preflight_generated_artifact_guard.py` — confirm clean.

Do not claim merge-ready if any step fails or is blocked.

See `docs/ai/codex/VALIDATION_MATRIX.md` for package-class validation requirements.

## Standard Final Report Block

Final PR comment must include (concise but evidence-complete):

- WP ID / package class
- Selected and mechanically derived minimum governance track
- Branch / base / required previous merge commit
- Changed files
- Validation summary (commands, exit codes, counts)
- Boundary check (runtime/source/tooling/dependency/Hermes/credentials/trading)
- Deferred items changed
- Open issues / assumptions
- Ready for review: YES/NO

See `docs/ai/codex/CONCISE_REPORTING_RULES.md` and `docs/ai/codex/WP_EXECUTION_REPORT.md`.

## Governance Track Block

Every new WP prompt declares one expected track and one bounded canonical
authority mirror. The mirror is the prompt's normative machine-readable
authority declaration; prose cannot broaden it. Readiness requires its exact
equality with spec `identity.risk_level` and all sixteen `authority` booleans,
then derives the unchanged minimum from those equal values. Missing, duplicate,
malformed, reordered, or mismatching mirrors fail closed. Historical certified
packages before WP171G need no retrofit.

- FAST: Risk 0–2 with no network/scheduler/Hermes-runtime/paper/credential/
  execution/live authority; deterministic readiness, no independent certificate.
- RUNTIME: Risk 3 or authorized network/scheduler/Hermes-runtime/paper, with no
  credential/execution/live authority; deterministic readiness, no independent
  certificate, one combined final implementation reviewer.
- PROTECTED: Risk 4 or credential/execution/live authority; independent immutable
  draftability certificate and strongest review/validation remain mandatory.

All tracks retain exact-diff validation, failed-check blocking, hosted CI, and
independent Side PR review. A package may voluntarily select a stricter track.

## FAST/RUNTIME Contract Compilation Block

Before freezing a spec that references an existing builder, parser, validator,
or API, mechanically smoke-test every frozen literal/config against the real
interface and record PASS/FAIL. This check precedes implementation authorization.

## Standard Safety Boundary Block

Confirm in the final report:

- No runtime source under `src/` added or modified beyond WP scope.
- No dependency or lock files changed.
- No Hermes installation, Hermes runtime dependency, or Hermes config added.
- No agent runtime, agent CLI, scheduler, daemon, or bot loop added.
- No credentials, `.env`, API keys, private keys, wallet keys, or tokens added.
- No LLM dependency, provider SDK, or network calls added.
- No strategy signals, trade proposals, paper trading, or live trading paths added.
- No external code copied before license and security audit.

See `AGENTS.md` and `docs/runtime_boundaries.md`.

## Standard Generated Artifact Block

Before and after every WP:

- Run `python tools/git/preflight_generated_artifact_guard.py`.
- Confirm `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, `security-scan-output/`, `.venv-official-client/`, `official-client-sandbox-output/`, and `local_data/` are not in staged or committed files.
- Never commit generated artifacts, local environment files, or report/export outputs.

See `docs/codex_execution_guidelines.md`.

## Standard Stop/Escalation Block

Stop and report (do not continue) if:

- `main` is stale, diverged, dirty, or missing required previous WP evidence.
- Generated artifacts are visible before branch creation.
- Required previous merge commit is absent.
- Implementation requires new tooling, external dependencies, runtime code, network calls, or generated artifacts.
- Documentation would weaken validation, imply validation can be skipped, or authorize forbidden behavior.
- Tests fail.
- Security checks fail in a way that blocks the WP.
- PR cannot be created.

See `CODEX_START_HERE.md` stop rules and `AGENTS.md` escalation rules.

## Standard PR Evidence Reporting Discipline Block

Applies to: Codex and Claude Code. Mandatory for every WP.

**After WP91:** Final GitHub evidence comments are optional and non-canonical. Absence of a final comment is not a merge blocker after WP91. Required evidence surfaces after WP91 are the PR body and the stable/non-self-referential status fragment. If an optional final comment is posted, it must not contradict the PR body and must state it is optional and non-canonical.

Before setting Ready for review: YES, verify all of the following:

**Exact validation commands:**
- Every validation step in the PR body must use the exact full command invocation — all flags, arguments, and paths. No ellipses (`...`). No abbreviated helper commands. No placeholder text.
- After WP91, if an optional final comment is posted, every validation step in it must use the same exact full command invocations.
- Example of required form: `python -m pytest tests/test_foo.py -v` (not `python -m pytest tests/test_foo.py ...`).

**Exact result counts:**
- State the exact numbers: passed, failed, errors, skipped, warnings, exit code.
- Do not use approximate wording such as "tests passed" without counts.
- If the suite count changed after a re-run, update the PR body. After WP91, if an optional final comment is posted, update it too.

**Network usage wording:**
- If Remote Main Sync Gate, `git fetch`, `git pull`, `git push`, or PR publication ran, do not write "no network was used."
- Use: "Network was used only for Remote Main Sync Gate / git remote synchronization and PR push/publication. This WP adds no runtime network behavior, no API polling, no account access, and no product network behavior."

**PR body and status fragment consistency:**
- Test counts, command results, files changed, and network wording must match between the PR body and the status fragment.
- After WP91, if an optional final comment is posted, it must not contradict the PR body.

**Stale counts:**
- Correct any stale count before Ready for review: YES.

**Unavailable tools:**
- Report unavailable security tools as UNAVAILABLE/SKIPPED or SKIPPED_NOT_PRESENT with exact reason.
- Do not describe unavailable tools as passed.

**Current final evidence marker (Historical WP86–WP90 only; not required after WP91):**
- After WP91, a final comment is not required. If an optional final comment is posted, the CURRENT FINAL WP EVIDENCE marker is not required; the comment must state it is optional and non-canonical.
- **Historical WP86–WP90 only:** The final top-level PR comment must start with or contain:
  `CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments`

**No inline test counts in file lists:**
- Do not put test counts in file-list descriptions or summary parentheticals (e.g., "focused tests (34 tests)"). These counts drift.
- Put test counts only in validation result sections.

**PR evidence consistency guard (with WP47 hardening flags):**
- Before setting Ready for review: YES, run `tools/git/pr_evidence_consistency_guard.py` on exact local drafts intended for posting or on copied posted GitHub content.
- Running only on intermediate drafts is insufficient if the posted content later changed.
- If the guard fails, fix all failures and re-run before marking Ready for review: YES.
- Report the exact guard invocation and result (PASS/FAIL) in the PR body. After WP91, if an optional final comment is posted, also report the guard result there.
- Include a "Guard input source:" line in the PR body. After WP91, if an optional final comment is posted, it may also include a guard input source line.

```
python tools/git/pr_evidence_consistency_guard.py \
  --pr-body local_pr_body.md \
  --final-comment local_final_comment.md \
  --expected-head <HEAD_SHA> \
  --required-command "<FULL_STATUS_SNAPSHOT_COMMAND>" \
  --required-command "<FULL_DIFF_SCOPE_COMMAND>" \
  --required-command "<FULL_CODE_BLAST_RADIUS_COMMAND>" \
  --require-standard-network-wording \
  --require-ready-yes \
  --forbid-inline-test-counts \
  --forbid-placeholder-evidence \
  --require-current-final-marker \
  --require-posted-evidence-note
```

**Ready for review gate:**
- Ready for review: YES is forbidden if any evidence defect listed above remains uncorrected.
- Ready for review: YES is forbidden if `pr_evidence_consistency_guard.py` fails on local drafts.
- Ready for review: YES is forbidden if the final comment lacks the current-final evidence marker when superseding old comments (Historical WP86–WP90 only; not required after WP91).
- Ready for review: YES is forbidden if file lists contain parenthetical test counts.

See `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` and `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`.
