# Validation Output Summary Helper Design

## 1. Status

- Design status: DESIGN_ONLY
- Future helper status: NOT_IMPLEMENTED
- Applies to: Claude Code and Codex
- Runtime impact: NO_RUNTIME_CHANGE
- Tooling impact: NO_TOOL_IMPLEMENTATION
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Validation impact: NO_VALIDATION_WEAKENING
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE

No helper is implemented in WP31. This document describes a future helper only.
Implementation requires a separate approved implementation work package.

## 2. Purpose

This design describes a future local validation-output summary helper that would:

- Summarize validation command output in a compact, evidence-complete format.
- Reduce final-report token usage and review load by providing structured command result summaries.
- Help reviewers and executors report command results consistently across all WPs.

The helper is intended to reduce the token cost of PR body and optional final PR comment sections
that currently require copying long validation output. After WP91, a final PR comment is optional.
It does not replace validation:

- It is not a validator and cannot mark checks as passed unless the command actually ran
  and returned a passing result.
- Required validation (pytest, security checks, artifact guard, Remote Main Sync Gate,
  human review) must still run regardless of whether this helper is used.
- Helper output is a summary of evidence, not the evidence itself.

## 3. Non-Goals

The following are explicitly outside the scope of both this design and any future implementation:

- No helper implementation in WP31.
- No command runner added in WP31.
- No validation replacement of any kind.
- No skipping tests, security checks, or required preflight.
- No hiding failed checks or reporting unavailable tools as passed.
- No converting unavailable tools (gitleaks, semgrep, pip-audit) into passed checks.
- No network calls of any kind.
- No LLM integration, inference call, or AI provider SDK.
- No Hermes integration or Hermes runtime dependency.
- No automatic PR approval or approval recommendation.
- No automatic file modification of any kind.
- No trading, execution, strategy, signal, or order authority.
- No generated reports or exports committed to the repository.

## 4. Future Helper Constraints

Any future implementation of this helper must adhere to the following constraints without exception:

- Standard-library only: no external packages, no pip install, no requirements change.
- Local, offline, and read-only: reads only provided log text, files, or stdin, makes no
  network calls, modifies no files.
- No dependency or lock-file changes in any form.
- No network calls: no HTTP, no subprocess that makes HTTP calls, no DNS lookup.
- No command execution unless a future implementation WP explicitly scopes runner mode and
  defines the safety constraints for that mode.
- No repo mutation: the helper summarizes; it never edits, deletes, or stages files.
- Default stdout summary only; no file written unless explicitly requested with an output flag.
- Optional JSON output only under the ignored `local_data/validation_summaries/` directory,
  and only if a future approved implementation WP explicitly permits it.

## 5. Intended Future Modes

### Parser mode

Summarize provided log text, file, or stdin without running any command. The helper reads
pre-captured command output and produces a structured summary. This is the preferred mode
for the first implementation because it does not change validation execution semantics.

### Metadata mode

Summarize manually provided command, exit code, and short output snippet. The caller supplies
the command string, exit code, and optional brief output text; the helper formats and classifies
the result. Also suitable for the first implementation.

### Future runner mode

Deferred. Not part of the first implementation unless a future implementation WP explicitly
approves it and defines the safety boundary for command execution. Runner mode must not be
included without explicit scope approval.

**The first implementation should prefer parser/metadata mode** to avoid changing validation
execution semantics, introducing subprocess execution risk, or complicating safety boundaries.

## 6. Intended Future CLI Shape

The following is a proposed design for the future CLI. This is not an implementation.

```
python tools/validation/validation_output_summary.py \
  --command "python -m pytest" \
  --exit-code 0 \
  --stdout-file local_data/tmp/pytest.out \
  --stderr-file local_data/tmp/pytest.err \
  --check-type full-pytest \
  --format text
```

```
python tools/validation/validation_output_summary.py \
  --from-stdin \
  --command "python -m pytest tests/test_example.py" \
  --exit-code 1 \
  --check-type focused-pytest
```

```
python tools/validation/validation_output_summary.py \
  --command "python tools/security/run_available_security_checks.py" \
  --exit-code 0 \
  --check-type security \
  --tool-availability semgrep=unavailable \
  --tool-availability pip-audit=unavailable
```

### Proposed flags

The output format is controlled by `--format text|json` (default: `text`).

| Flag | Description |
|---|---|
| `--command` | Exact command string that was run (display only; not executed by helper). |
| `--exit-code` | Exit code returned by the command. |
| `--check-type` | Check classification: `full-pytest`, `focused-pytest`, `security`, `artifact-guard`, `sync-gate`, `smoke`, `diff-scope`, `git-check`, or `other`. |
| `--stdout-file` | Path to a file containing captured stdout from the command. |
| `--stderr-file` | Path to a file containing captured stderr from the command. |
| `--from-stdin` | Read command output from stdin instead of a file. |
| `--format text\|json` | Output format: `text` (default) or `json`. |
| `--max-failure-lines` | Maximum number of failure-context lines to include in the summary (default: 30). |
| `--tool-availability` | Declare a tool's availability status as `name=available`, `name=unavailable`, or `name=skipped`. May be repeated. |
| `--output` | Write summary output to this path; restricted to `local_data/validation_summaries/`. |
| `--fail-on-missing-required-evidence` | Exit non-zero if a mandatory check type has no evidence (no exit code, no output). |

## 7. Intended Input Sources

A future implementation should accept input from:

- explicit command string (display only; the helper does not execute it).
- exit code provided by the caller.
- stdout/stderr snippets or files captured from the actual command run.
- pytest result lines (passed, failed, error, warning counts from `pytest` output).
- Generated artifact guard output from `tools/git/preflight_generated_artifact_guard.py`.
- Remote Main Sync Gate output from `tools/git/preflight_sync_main.py`.
- security tool availability output from `tools/security/run_available_security_checks.py`.
- diff/scope helper output from `tools/git/diff_scope_summary.py`.
- Optional local smoke command output where relevant to the WP package class.

## 8. Intended Output Structure

Both text and JSON summaries should include:

- **command**: exact command string that was run.
- **check type**: classification from the `--check-type` flag.
- **exit code**: integer exit code or `unknown` if not provided.
- **status**: one of PASS / FAIL / SKIPPED / UNAVAILABLE / PARTIAL / ERROR (see Section 9).
- **pass count**: number of passing tests/checks, when parseable.
- **fail/error count**: number of failing/errored tests/checks, when parseable.
- **warning count**: number of warnings, when parseable.
- **unavailable tools list**: tools declared or detected as unavailable.
- **generated output paths**: any output paths mentioned in the command output.
- **failure snippet**: abbreviated failure output for diagnosis.
- **truncation indicator**: explicit flag when output was truncated.
- **mandatory evidence present**: yes/no assertion for required check types.
- **validation reminder**: explicit statement that this summary does not replace required validation.
- **raw log retention note**: note that full raw logs may remain local and uncommitted.

## 9. Status Classification Rules

The future helper must apply the following rules when assigning a status to a summarized result:

- **PASS**: exit code is 0 and there is no explicit failure marker in the output.
- **FAIL**: exit code is nonzero and not a known unavailable/skipped case.
- **UNAVAILABLE**: the tool did not run because it is not installed or not configured on
  this system. Applies to gitleaks, semgrep, pip-audit, and similar optional tools.
- **SKIPPED**: the check is explicitly optional or not applicable to this WP (e.g., no
  `Cargo.lock` so cargo audit is not applicable).
- **PARTIAL**: only some sub-tools or sub-checks ran (e.g., one security tool available,
  others not).
- **ERROR**: invalid input, inconsistent evidence, or internal helper error.

**Critical rules:**

- Unavailable semgrep, pip-audit, or gitleaks must not be summarized as PASS.
- A missing command result (no exit code, no output, no evidence) must not be summarized as PASS.
- A SKIPPED status for a mandatory check type is an ERROR condition.
- The helper may not upgrade a FAIL or UNAVAILABLE status to PASS based on any heuristic.

## 10. Failure-Snippet and Truncation Rules

- Include enough failure text to diagnose the root cause; never include huge raw logs by default.
- Preserve the first meaningful failure section and the final summary section when possible.
- Always state explicitly when output was truncated (e.g., "output truncated at 30 lines; full
  log retained locally").
- Raw logs may remain local and uncommitted; the summary must state this.
- The `--max-failure-lines` flag controls how many lines of failure context to include.
- A truncated snippet that hides a failure is an ERROR condition; when in doubt, include more.

## 11. Required Validation Preservation Rules

The future helper output cannot replace or eliminate the requirement for any of the following:

- **focused tests**: must run after scope-relevant changes.
- **full pytest**: must run after the final commit on every WP.
- **generated artifact guard**: must run after the final commit on every WP.
- **Remote Main Sync Gate**: must pass before branch creation on every WP.
- **security checks**: gitleaks, semgrep, pip-audit must be run and their availability
  honestly reported; UNAVAILABLE is not the same as PASSED.
- **git diff --check**: whitespace and line-ending check must run.
- **human review**: no helper output substitutes for human review of the PR.
- **final PR comment**: optional after WP91; if posted, it must contain the same evidence
  structure as required by `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`.
  **Historical WP86–WP90 only:** the final report PR comment was mandatory regardless of
  whether the helper was used.

**The helper cannot authorize merge-ready status by itself.** A summary generated by this
helper does not constitute approval, passing validation, or merge readiness.

## 12. Security and Sensitive-Output Model

Any future implementation must enforce the following security constraints:

- Must not read `.env`, credential files, private keys, wallet files, tokens, local account
  data, private endpoint responses, or arbitrary file paths.
- Must operate on content explicitly passed via flags or stdin only.
- Must avoid echoing suspected secrets from logs into the summary output.
- If secret-like patterns are detected in log output (e.g., lines matching common secret
  patterns), the summary should flag and stop or redact in a future implementation.
- No secrets scanning replacement: gitleaks and semgrep remain fully separate tools.
- The helper does not validate whether security checks passed; it only summarizes provided
  security tool output.

## 13. Package-Class Usage

The helper should produce useful summaries for each WP package class:

- **docs/design WPs**: summarize focused doc tests, full pytest, artifact guard, security
  tool availability, git diff --check.
- **local tooling WPs**: additionally summarize CLI help/smoke output and helper-focused
  tests.
- **public-data WPs**: summarize explicit network usage evidence and local output paths.
- **security WPs**: distinguish unavailable tool vs failed scan vs passed scan; never
  conflate these three states.
- **report/export WPs**: summarize generated local output paths and non-commit confirmation.

## 14. Future Implementation Test Plan

A future implementation WP must include tests covering at minimum:

- **pytest pass/fail/warning parser tests**: parse pytest output for passed/failed/error/warning
  counts; handle both short and long output formats.
- **generated artifact guard parser tests**: detect PASS/FAIL from artifact guard output;
  confirm no artifacts committed state is parsed correctly.
- **Remote Main Sync Gate parser tests**: detect PASS/FAIL from sync gate output; confirm
  required commit and required file presence results are parsed.
- **security tool unavailable/skipped/passed/failed tests**: correctly classify each tool
  availability state; confirm unavailable is never upgraded to passed.
- **status classification tests**: PASS/FAIL/UNAVAILABLE/SKIPPED/PARTIAL/ERROR rules are
  enforced per Section 9.
- **failure-snippet truncation tests**: snippets respect `--max-failure-lines`; truncation
  is indicated when applied.
- **secret-like output handling tests**: lines matching secret patterns are flagged or
  redacted; summary does not echo secrets.
- **JSON/text output tests**: both formats parse correctly; JSON contains all required fields;
  text output contains validation reminder.
- **output path restriction tests**: `--output` accepts only paths under
  `local_data/validation_summaries/`; rejects path traversal, absolute paths, and
  outside-directory targets.
- **no-network/no-forbidden import tests**: source must not import requests, httpx, aiohttp,
  websockets, socket, openai, anthropic, langchain, hermes, py_clob_client.
- **Windows path handling tests**: paths using backslash separators are handled correctly;
  path comparison is case-insensitive on Windows.

## 15. Open Design Questions

The following questions must be resolved by a future implementation WP before writing code:

1. **First implementation mode**: should the first implementation be parser-only, metadata-only,
   or parser + metadata mode? Metadata mode is simpler; parser mode is more powerful but
   requires format-specific parsing for each check type.
2. **JSON output in first implementation**: should `--format json` be included in the first
   implementation, or deferred until there is a confirmed consumer?
3. **Output files in first implementation**: should `--output` to `local_data/validation_summaries/`
   be allowed in the first implementation, or stdout-only initially?
4. **Secret-like output handling strictness**: should the first implementation flag and stop,
   flag and redact, or only warn when secret-like patterns are detected in log output? Stopping
   is safest but may interrupt valid use; redaction is complex; warning is minimal.
5. **Runner mode**: should runner mode ever be allowed in any future implementation, or remain
   permanently forbidden? Allowing runner mode simplifies the workflow but introduces subprocess
   execution risk and complicates safety boundaries.
6. **Security subtool matrix summarization**: how should the helper summarize multi-tool security
   output (e.g., a matrix where gitleaks is unavailable, semgrep is unavailable, pip-audit is
   unavailable) without hiding any of the unavailable states?

## 17. WP32 Implementation Decisions

WP32 implemented the local validation output summary helper resolving the open design questions
from Section 15. Implementation is at `tools/validation/validation_output_summary.py`.
User-facing documentation is at `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md`.

Resolved choices:

- **First implementation mode**: parser + metadata mode implemented. Accepts `--stdout-text`,
  `--stderr-text`, `--from-stdin`, and (under restricted path) `--stdout-file` / `--stderr-file`.
  Runner mode remains forbidden and unimplemented.

- **JSON output**: `--format text|json` implemented. Default format is `text`. JSON prints to
  stdout or to the optional restricted output file.

- **Output files**: default behavior writes no file. `--output` may write text or JSON only
  under repo-relative `local_data/validation_summaries/`. Absolute paths, path traversal,
  and paths outside this prefix are rejected with exit code 2.

- **Input files**: `--stdout-file` and `--stderr-file` accepted only under repo-relative
  `local_data/validation_summaries/inputs/`. Absolute paths, traversal, and credential-like
  filenames are rejected.

- **Secret-like output handling**: detection and redaction implemented. Matching values are
  replaced with `[REDACTED]` in returned output. `secret_like_output_detected: true` is set
  in the summary. A safety warning is included in text output. `--fail-on-secret` forces
  nonzero exit when secrets are detected.

- **Security subtool matrix**: `--tool-availability name=status` flag is repeatable. Valid
  statuses: `available`, `passed`, `failed`, `unavailable`, `skipped`, `skipped_not_available`,
  `skipped_not_applicable`. Mixed states classify as PASS / FAIL / PARTIAL / UNAVAILABLE
  per Section 9 rules. Invalid status strings exit 2.

- **Exit behavior**: exit 0 when summary generated (even if summarised status is FAIL).
  Exit 1 when `--fail-on-missing-required-evidence` or `--fail-on-secret` is triggered.
  Exit 2 for usage/config errors.

Historical design content above is preserved intact.

## 16. Recommended Next WP

The user may choose one of the following for WP32:

- **WP32 - Validation Output Summary Helper Implementation**: if this design is accepted and
  the open questions in Section 15 are resolved to the user's satisfaction (particularly the
  mode, JSON, output-path, and secret-handling questions).
- **WP32 - Validation Output Summary Helper Design Follow-Up**: if gaps remain or the open
  questions require a clarifying design iteration before implementation.
- **WP32 - Local Advisory Handoff Package**: if the user chooses to resume the old advisory
  handoff plan instead of implementing helper tooling at this time.

No follow-on WP is authorized by this design document. Authorization requires a separate
explicit work package instruction.
