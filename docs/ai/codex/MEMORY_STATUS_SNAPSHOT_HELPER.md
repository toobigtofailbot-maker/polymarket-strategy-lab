# Memory / Status Snapshot Helper

## 1. Status

- Helper status: LOCAL_OFFLINE_READ_ONLY_TOOLING_IMPLEMENTED
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Command execution impact: NO_COMMAND_EXECUTION
- Validation impact: NO_VALIDATION_REPLACEMENT
- Repo-truth impact: NO_REPO_TRUTH_REPLACEMENT
- Snapshot authority: ADVISORY_ONLY_NOT_REPO_TRUTH
- Persistent memory status: NOT_IMPLEMENTED

## 2. Purpose

The memory / status snapshot helper summarizes repo-truth project state for
Claude Code / Codex orientation before WP drafting or PR review. It reduces
repeated context load by pre-extracting key orientation fields from standard
repo-truth files into a concise, sanitized summary.

It does not replace repo-truth files, security checks, pytest, preflight
tools, or human review. It is a read-only orientation aid only.

## 3. Commands

### Help

```
python tools/git/status_snapshot.py --help
```

### Basic text summary

```
python tools/git/status_snapshot.py --format text
```

### JSON summary

```
python tools/git/status_snapshot.py --format json
```

### Full orientation output

```
python tools/git/status_snapshot.py --format text \
  --include-deferred \
  --include-helper-inventory \
  --include-next-wp-candidates \
  --include-protected-boundaries
```

### JSON with optional output file

```
python tools/git/status_snapshot.py \
  --format json \
  --include-deferred \
  --include-helper-inventory \
  --include-next-wp-candidates \
  --output local_data/status_snapshots/wp36_status.local.json
```

### Staleness check

```
python tools/git/status_snapshot.py \
  --check-stale local_data/status_snapshots/wp36_status.local.json
```

### Staleness check with strict exit

```
python tools/git/status_snapshot.py \
  --check-stale local_data/status_snapshots/wp36_status.local.json \
  --fail-on-stale
```

## 4. CLI Flags

| Flag | Description |
|---|---|
| `--format text\|json` | Output format. Default `text`. `markdown` is not implemented and exits 2. |
| `--output PATH` | Optional repo-relative output path under `local_data/status_snapshots/`. Default: no file written. |
| `--repo-root DIR` | Repository root. Default: current directory. Must contain `AGENTS.md`, `docs/project_status.md`, `docs/repo_truth_index.md`. |
| `--include-deferred` | Include open deferred item digest. |
| `--include-helper-inventory` | Include local helper tool inventory. |
| `--include-next-wp-candidates` | Include next WP candidate digest from `docs/project_status.md`. |
| `--include-protected-boundaries` | Include protected boundary status block. |
| `--max-deferred-items N` | Cap deferred items in digest (default 20, must be ≥ 1). |
| `--check-stale PATH` | Check staleness of a saved JSON snapshot under `local_data/status_snapshots/`. |
| `--fail-on-stale` | Exit 1 if `--check-stale` finds the snapshot stale. |
| `--fail-on-sensitive-hit` | Exit 1 if sensitive content is detected in output. |

## 5. Exit Codes

- **0** — Snapshot generated or stale check completed without strict failure.
- **1** — `--fail-on-stale` with stale snapshot detected, or `--fail-on-sensitive-hit` with sensitive content detected.
- **2** — Usage or config error (missing required repo-root files, invalid output path, `--format markdown`, `--max-deferred-items < 1`).

Helper exit codes never replace actual validation command exit codes.

## 6. Output Interpretation

The snapshot includes:

- **current phase** — from `docs/project_status.md`
- **latest merged WP / merge commit** — from `docs/project_status.md` (conservative extract)
- **current branch from repo truth** — from `docs/project_status.md`
- **helper inventory** — diff/scope, validation-output, code blast-radius, and status snapshot helpers (with `--include-helper-inventory`)
- **deferred digest** — capped list of OPEN deferred items (with `--include-deferred`)
- **next WP candidates** — from `docs/project_status.md` next-intended-WP line (with `--include-next-wp-candidates`)
- **protected boundaries** — live trading, credentials, agent authority, Hermes status (with `--include-protected-boundaries`)
- **generated artifact / output rules** — reminder that no output is committed
- **stale warning** — always present; snapshot represents state at generation time
- **advisory-only note** — always present; snapshot is not repo truth
- **repo-truth verification reminder** — always present
- **validation / human-review reminder** — always present

## 7. Staleness Model

Every saved snapshot includes `repo_commit_sha`, `repo_branch`, `generated_timestamp_utc`,
`summary_schema_version`, and `source_files_used`. A snapshot is stale if:

- Commit SHA differs from current HEAD
- Branch differs
- Schema version is absent or unsupported
- Timestamp is absent

Use `--check-stale` to compare. Use `--fail-on-stale` to enforce strict staleness exit code.

## 8. Sensitive-Output Sanitization

The helper detects and redacts obvious secret-like values in any source file output:
`API_KEY`, `PRIVATE_KEY`, `CLOB_SECRET`, `CLOB_PASS_PHRASE`, `MNEMONIC`, `TOKEN`,
long Bearer tokens, and PEM private key blocks. Raw values are never echoed.

This is not a replacement for gitleaks or semgrep. Run security checks separately.

## 9. Safe Input Allowlist

The helper reads only these repo-relative source files:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- `docs/review_checklist.md`
- `docs/testing_requirements.md`
- `docs/ai/codex/README.md`
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`
- `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md`
- `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md`
- `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md`
- `docs/security_and_secrets.md`
- `docs/runtime_boundaries.md`
- `docs/live_trading_authorization.md`

The helper never reads `.env`, credential files, private-key files, `local_data/`
contents, `src/`, arbitrary filesystem paths, network responses, or generated outputs.
There is no CLI flag to read arbitrary input files.

## 10. Output Restriction

Default: no file is written. Optional output only under
`local_data/status_snapshots/` when `--output` is provided. Absolute paths,
traversal (`..`), and paths outside `local_data/status_snapshots/` are rejected.
Generated snapshots must never be staged or committed.

## 11. Non-Goals

The helper does not:

- Replace repo truth
- Replace security checks (gitleaks, semgrep, pip-audit)
- Replace pytest or preflight tools
- Execute git commands or any external commands
- Make network calls
- Import subprocess, requests, or any network/LLM library
- Modify or stage repo files
- Create persistent tracked memory files
- Approve PRs or authorize work
- Implement trading, execution, or agent runtime behavior

## 12. Relationship to Other Helpers

- **Diff/scope summary** (`tools/git/diff_scope_summary.py`): WP diff scope and protected-prefix warnings. Implemented WP30.
- **Validation-output summary** (`tools/validation/validation_output_summary.py`): summarizes already-run validation evidence. Implemented WP32.
- **Code blast-radius** (`tools/git/code_blast_radius.py`): suggests related files, tests, docs, and boundary areas. Implemented WP34.
- **Status snapshot** (`tools/git/status_snapshot.py`): summarizes repo-truth project state for orientation. Implemented WP36.

None of these helpers replace mandatory validation, security checks, direct file
inspection, or human review. They are advisory aids only.
