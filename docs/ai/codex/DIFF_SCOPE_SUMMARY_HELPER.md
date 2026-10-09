# Diff Scope Summary Helper

## 1. Status

- Helper status: LOCAL_OFFLINE_READ_ONLY_TOOLING_IMPLEMENTED
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Validation impact: NO_VALIDATION_REPLACEMENT
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE

## 2. Purpose

The diff scope summary helper summarises local git diff scope for Claude Code / Codex PR review.
It reduces the token load of PR reviews and WP executions by pre-computing information that
reviewers currently derive manually from `git diff` output and file lists.

It does not replace human review, required validation, security checks, preflight tools, the
generated artifact guard, the Remote Main Sync Gate, or the PR body current evidence surface
(final PR comment is optional after WP91).

## 3. Commands

### Help

```
python tools/git/diff_scope_summary.py --help
```

### Basic

```
python tools/git/diff_scope_summary.py --base main --head HEAD --package-class docs-only
```

### With explicit allowed/forbidden scope

```
python tools/git/diff_scope_summary.py \
  --base main \
  --head HEAD \
  --package-class docs-only \
  --allowed-prefix docs/ \
  --allowed-prefix tests/ \
  --forbidden-prefix src/
```

### JSON stdout

```
python tools/git/diff_scope_summary.py \
  --base main \
  --head HEAD \
  --package-class docs-only \
  --format json
```

### Strict warning mode

```
python tools/git/diff_scope_summary.py \
  --base main \
  --head HEAD \
  --package-class docs-only \
  --fail-on-warning
```

### Optional output file (ignored path only)

```
python tools/git/diff_scope_summary.py \
  --base main \
  --head HEAD \
  --package-class docs-only \
  --format json \
  --output local_data/diff_scope_summaries/wp30_scope.local.json
```

## 4. CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--base` | `main` | Base ref (commit hash, branch, or `origin/main`) |
| `--head` | `HEAD` | Head ref |
| `--package-class` | `unspecified` | Active WP package class |
| `--allowed-file` | (repeatable) | Specific file path allowed in this WP |
| `--allowed-prefix` | (repeatable) | Directory prefix allowed in this WP |
| `--forbidden-prefix` | (repeatable) | Additional directory prefix forbidden in this WP |
| `--format` | `text` | Output format: `text` or `json` |
| `--output` | (none) | Write output to file (must be under `local_data/diff_scope_summaries/`) |
| `--fail-on-warning` | off | Exit 1 if any warnings are present |

## 5. Exit Codes

| Code | Meaning |
|---|---|
| 0 | Summary generated successfully (even if warnings are present) |
| 1 | Warnings found and `--fail-on-warning` was used |
| 2 | Usage or configuration error (invalid output path, etc.) |

Exit codes do not replace validation. A `0` exit does not mean pytest passed, security checks
passed, or the PR is ready for merge. The validation reminder always appears in the output.

## 6. Output Interpretation

The summary includes:

- **Changed files** — total count with added/modified/deleted/renamed breakdown.
- **Files by status** — grouped by git status code.
- **Out-of-scope files** — files not matching any `--allowed-file` or `--allowed-prefix` rule
  (only flagged when at least one allow rule is provided).
- **Protected-path hits** — built-in protected paths (`.env`, `tools/hermes/`, `agent_runtime/`,
  credential-like names, etc.) plus explicit `--forbidden-prefix` hits.
- **Dependency/lock changes** — `pyproject.toml`, `requirements*.txt`, `*.lock`,
  `package.json`, `Cargo.toml`, etc.
- **Generated-artifact/local-output paths** — `local_data/`, `.venv-security/`, `tools/.bin/`,
  `.sarif`, `__pycache__/`, etc.
- **Package-class warnings** — misalignment between declared WP package class and changed files.
- **git diff --check result** — whitespace errors.
- **Validation reminder** — explicit statement that the summary does not replace required checks.
- **Suggested review attention areas** — per-category review prompts.
- **Warning count** and **exit behaviour** note.

## 7. Safety

- **Local only** — reads only local git metadata from the working repository.
- **Offline** — makes no network calls of any kind.
- **Read-only** — does not edit, stage, delete, or modify any file.
- **No network** — no HTTP, no subprocess network calls, no DNS.
- **No dependency** — Python standard library only; no pip install, no requirements change.
- **No mutation** — flags and reports only; never edits or stages.
- **No secrets scanning replacement** — security tools (gitleaks, semgrep) remain separate.
- **No validation replacement** — does not replace pytest, preflight tools, security checks,
  the Remote Main Sync Gate, the generated artifact guard, or human review.
- **No automatic approval** — the helper output does not constitute PR approval.

## 8. Non-Goals

- No PR approval or approval recommendation.
- No security scanning (gitleaks, semgrep, pip-audit replacement).
- No pytest replacement.
- No trading, runtime, agent, Hermes, or LLM behavior.
- No network calls.
- No file mutation.
- No dependency changes.
- No generated artifacts committed to repo.

## 9. Output Path Restriction

The optional `--output` flag writes to a file only under the git-ignored path
`local_data/diff_scope_summaries/`. Output outside this directory is rejected with exit code 2.
Path traversal (`..`) is rejected. Absolute paths outside the allowed directory are rejected.

Generated output under `local_data/diff_scope_summaries/` must never be committed or staged.

## 10. Design Decisions (resolved in WP30)

See `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` Section 14 (WP30 Implementation
Decisions) for the full record of how open design questions were resolved.

Key decisions:
- Default behavior: exit 0 even when warnings are present.
- `--fail-on-warning`: exit 1 when any warning is present.
- JSON output implemented; `--format text|json` flag available.
- CLI flags only; no config file in WP30.
- Built-in protected patterns plus explicit `--forbidden-prefix`; no runtime doc parsing.
- Explicit `--base`/`--head` with defaults `main`/`HEAD`.

## 11. Spec-mode exact scope and copy origins (S10-GOV-COPY-01)

`--wp-spec docs/wp_specs/<WP>/wp_spec.json` activates schema 2.0 exact-scope
reporting. `--require-exact-scope` requires that mode and exits 1 when exact scope
fails; required Git-operation or invalid-spec/usage failures exit 2. Exit 0 is
an actual scope PASS only when `exact_scope_pass` is true. Sections 4–5 describe
legacy advisory behavior; their default exit-0 rule does not waive strict scope.
Manual scope/package/output flags cannot be combined with spec mode.

The spec-mode Git command remains `diff --name-status -z --find-renames=50%
--find-copies=50% --find-copies-harder <base>...<head>`. Parsed entries retain
`old_path` and `status_detail` copy provenance; the existing output field set
is unchanged, and copied destinations remain grouped under status `C`.

S10-GOV-COPY-01 supersedes historical WP159 section 14 only for allowed-file
classification of copy-origin provenance. `allowed_scope_paths` includes actual
changed/untracked destinations and rename origins. An unchanged benign `C`
origin outside the allowed set does not add an out-of-scope file. An independently
changed source remains an actual changed path and must be allowed; a copy
destination must always be allowed. Rename source and destination policy is
unchanged. Origin provenance adds neither changed count nor required presence.

`policy_paths` still includes all rename/copy origins for forbidden prefixes,
built-in protected paths, generated artifacts, dependency/lock hazards and
path-level authority. The new distinction never excuses an unsafe or unauthorized
source or destination. Unique count, required-file presence, untracked scanning,
whitespace and Git-failure checks, deterministic sorting, helper signatures,
output fields and legacy schema are unchanged. No WP-specific exemptions or
Git copy-detection reconfiguration are permitted.
