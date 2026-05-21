# Diff Scope Summary Helper Design

## 1. Status

- Design status: DESIGN_ONLY
- Future helper status: NOT_IMPLEMENTED
- Applies to: Claude Code and Codex
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Validation impact: NO_VALIDATION_WEAKENING
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE

No helper is implemented in WP29. This document describes a future helper only. Implementation requires a separate approved implementation work package.

## 2. Purpose

This design describes a future local diff/scope summary helper that would:

- Summarize the set of changed files between two Git refs.
- Detect whether changed files match the allowed scope declared by the active work package.
- Flag protected-path hits without modifying any file.
- Flag dependency or lock-file changes without modifying any file.
- Flag generated-artifact or `local_data/` path hits without modifying any file.
- Produce package-class alignment warnings when the WP scope and changed-file set appear misaligned.
- Output a concise, human-readable summary to stdout by default.

The helper is intended to reduce the token load of PR reviews and WP executions by pre-computing information that reviewers currently derive manually from `git diff` output and file lists. It does not replace human review, required validation, security checks, or the mandatory final PR comment.

## 3. Non-Goals

The following are explicitly outside the scope of both this design and any future implementation:

- No helper implementation in WP29.
- No replacement of full pytest, preflight tools, security checks, or human review.
- No GitHub API access or network dependency of any kind.
- No runtime source analysis beyond local file names and diff metadata.
- No LLM integration, inference call, or AI provider SDK.
- No Hermes integration or Hermes runtime dependency.
- No trading, execution, strategy, signal, or order authority.
- No automatic PR approval or approval recommendation.
- No automatic file modification of any kind.
- No secrets scanning; security tools remain fully separate.
- No generated reports or exports committed to the repository.

## 4. Future Helper Constraints

Any future implementation of this helper must adhere to the following constraints without exception:

- Standard-library only: no external packages, no pip install, no requirements change.
- Local, offline, and read-only: reads only local git metadata and file names, makes no network calls, modifies no files.
- No dependency or lock-file changes in any form.
- No network calls: no HTTP, no subprocess that makes HTTP calls, no DNS lookup.
- No generated output committed to the repository.
- No mutation of repo files: the helper flags and reports; it never edits, deletes, or stages.
- Stdout summary by default; no file written unless explicitly requested with an output flag.
- Optional JSON output only under the ignored `local_data/` directory, and only if a future approved implementation WP explicitly permits it.

## 5. Intended Future CLI Shape

The following is a proposed design for the future CLI. This is not an implementation.

```
python tools/git/diff_scope_summary.py \
  --base main \
  --head HEAD \
  --package-class docs-only \
  --allowed-file docs/project_status.md \
  --allowed-prefix docs/ai/codex/ \
  --forbidden-prefix src/ \
  --forbidden-prefix tools/hermes/
```

### Proposed flags

| Flag | Description |
|---|---|
| `--base` | Base ref (e.g. `main`, a commit hash, or `origin/main`). |
| `--head` | Head ref (e.g. `HEAD`, a branch name, or a commit hash). |
| `--package-class` | Active WP package class (e.g. `docs-only`, `design`, `local-report`, `runtime-dependency`). |
| `--allowed-file` | Specific file path allowed in this WP. May be repeated. |
| `--allowed-prefix` | Directory prefix allowed in this WP. May be repeated. |
| `--forbidden-prefix` | Directory prefix forbidden in this WP. May be repeated. |
| `--format` | Output format: `text` (default) or `json` (future option). |
| `--output` | Write output to this path (must be under `local_data/` if used). |

### Intended concise summary output structure

A future implementation should produce a summary containing at minimum:

- Base and head refs used.
- Changed file count (added, modified, deleted separately).
- Full list of added, modified, and deleted files.
- Files outside the declared allowed scope (out-of-scope files).
- Protected-path hits (files matching patterns from repo-truth protected-path docs).
- Dependency or lock-file changes detected.
- Generated-artifact or `local_data/` path hits.
- Package-class warnings (see Section 9).
- Validation reminder: explicit statement that this summary does not replace pytest, security checks, or human review.
- Suggested review attention areas based on the above.
- Exit status (see Section 10).

## 6. Intended Input Sources

A future implementation should derive its information from:

- `git diff --name-status <base>...<head>` — file change list with status flags (A/M/D).
- `git diff --stat <base>...<head>` — file-level change statistics.
- `git diff --check` — whitespace error detection.
- Active WP-provided allowed and forbidden path lists (supplied via CLI flags or a small config file).
- Repo-truth protected-path documentation (`docs/ai/codex/PROTECTED_PATHS.md` and related docs).
- Local `.gitignore` or generated-artifact rules when relevant to flag uncommitted outputs.

The helper must not call any external network resource to derive these inputs.

## 7. Intended Output Modes

- Default: concise stdout summary (text format).
- Optional `--format json` in a future implementation.
- No Markdown report generated unless a future approved WP explicitly scopes it.
- No file written by default.
- Optional output file only under the git-ignored `local_data/` directory, if and only if a future approved implementation WP explicitly approves it.
- No binary output, no log file, no archive.

## 8. Safety And Protected-Path Model

The future helper must follow these safety rules:

- The helper flags; it never modifies. A protected-path hit is a review escalation signal, not an automatic build failure unless the active WP's own rules say so.
- Dependency and lock-file changes must always be highlighted in the summary.
- Generated artifacts must always be highlighted in the summary.
- The helper does not perform secrets scanning. Secrets scanning requires gitleaks or an approved equivalent and remains fully separate.
- The helper does not replace pytest, security checks, preflight tools, the generated artifact guard, the Remote Main Sync Gate, or the mandatory final PR comment.
- The helper output, if written to `local_data/`, must never be committed.
- No exit status value may be used to bypass required validation.

## 9. Package-Class Awareness

A future implementation should produce package-class warnings for at minimum the following misalignment patterns:

- A docs-only policy WP with changed files touching runtime source under `src/`.
- A design WP that adds files under `tools/` or `src/` (i.e., implementation files).
- A local report or export WP that touches credentials, network, or trading files.
- A read-only public-data WP that touches private, authenticated, or official-client files.
- A runtime dependency WP that was not explicitly authorized in repo truth.
- A future live-trading package that does not carry a corresponding update to `docs/live_trading_authorization.md`.

These warnings are informational. They do not replace human judgment or block the WP automatically unless the WP's own rules say so.

## 10. Exit Status Design

- `0`: summary generated and no helper-level warnings detected.
- `1`: warnings found (out-of-scope files, protected-path hits, dependency/lock changes, package-class misalignment) but helper completed successfully.
- `2`: usage or configuration error (missing required flag, invalid ref, unknown package class).

The helper must not use any exit status to bypass required validation steps. A `0` exit from the helper does not mean pytest passed, security checks passed, or the PR is ready for merge. The validation reminder in the output must always appear regardless of exit status.

A future implementation may choose whether out-of-scope warnings exit `1` or `0`, but the choice must be documented and tested (see open design question in Section 12).

## 11. Future Implementation Test Plan

A future implementation WP must include tests covering at minimum:

- Fixture-based tests using synthetic `git diff --name-status` output; no live git required.
- Protected path detection: files matching protected prefixes trigger expected warnings.
- Dependency and lock-file detection: `requirements*.txt`, `pyproject.toml`, `setup.cfg`, `setup.py`, `Pipfile`, `package.json`, `Cargo.toml`, `*.lock` files are correctly flagged.
- Generated artifact detection: `local_data/` paths, `.venv-security/`, `.venv-official-client/`, `tools/.bin/`, `*.sarif` and similar patterns are correctly flagged.
- Package-class warning tests: each misalignment pattern in Section 9 produces the expected warning.
- No-network test: no socket, HTTP, or subprocess network call is made during any test or during normal execution.
- No external-dependency test: no imports of non-stdlib packages are present in the helper.
- Output format tests: text and JSON output (if implemented) match the declared schema.
- Windows path handling tests: paths using backslash separators are normalized and correctly compared.

## 12. Open Design Questions

The following questions must be resolved by the future implementation WP before writing code:

1. **Warning exit status**: should the presence of out-of-scope files or protected-path hits cause exit `1` or remain exit `0` with a visible warning? The tradeoff is between strict enforcement (exit `1`) and flexibility for informational-only use.
2. **JSON support in first implementation**: should the first implementation include `--format json`, or defer JSON until there is a confirmed consumer?
3. **Metadata sourcing**: how much active-WP metadata should be passed via CLI flags versus read from a small local config file? CLI flags are simpler; a config file avoids long command lines but adds another file to manage.
4. **Protected-path parsing**: should the future helper parse protected-path patterns from `docs/ai/codex/PROTECTED_PATHS.md` at runtime, or should the patterns be hardcoded from the doc and updated manually? Parsing is more flexible; hardcoding is simpler and more predictable.
5. **Base ref strategy**: should the helper always compare against the local `main` branch, or against the PR base commit (which may differ if `main` has advanced since branching)?

## 13. Recommended Next WP

The user may choose one of the following for WP30:

- **WP30 - Local Diff And Scope Summary Helper Implementation**: if this design is accepted and the open questions in Section 12 are resolved to the user's satisfaction.
- **WP30 - Diff Scope Summary Helper Design Follow-Up**: if design gaps remain or the open questions require a clarifying design iteration before implementation.
- **WP30 - Local Advisory Handoff Package**: if the user chooses to resume the advisory handoff plan instead of implementing helper tooling at this time.

No follow-on WP is authorized by this design document. Authorization requires a separate explicit work package instruction.
