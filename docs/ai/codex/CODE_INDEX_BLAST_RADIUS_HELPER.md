# Code Index / Blast-Radius Helper

## 1. Status

- Helper status: LOCAL_OFFLINE_READ_ONLY_TOOLING_IMPLEMENTED
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Command execution impact: NO_COMMAND_EXECUTION
- Validation impact: NO_VALIDATION_REPLACEMENT
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE
- Persistent index status: NOT_IMPLEMENTED

Implemented in WP34 as a local/offline/read-only standard-library-only helper
under `tools/git/code_blast_radius.py`. No runtime or product code was changed.

## 2. Purpose

The helper summarizes likely related files, tests, docs, protected-boundary
attention areas, dependency/lock attention, generated-output attention,
package-class warnings, and low-confidence notes for Codex and Claude Code.

It reduces context usage by surfacing likely inspection targets without
requiring manual directory traversal. It does not replace validation, repo-truth
verification, direct file inspection, or human review.

## 3. Commands

### Help

```
python tools/git/code_blast_radius.py --help
```

### Basic (docs-only package)

```
python tools/git/code_blast_radius.py \
  --changed-file docs/project_status.md \
  --package-class docs-only \
  --include-docs \
  --include-tests
```

### Local tooling package

```
python tools/git/code_blast_radius.py \
  --changed-file tools/git/code_blast_radius.py \
  --package-class local-tooling \
  --include-tests \
  --include-docs
```

### JSON output

```
python tools/git/code_blast_radius.py \
  --changed-file tools/git/code_blast_radius.py \
  --package-class local-tooling \
  --include-tests \
  --include-docs \
  --format json
```

### Protected boundary strict mode

```
python tools/git/code_blast_radius.py \
  --changed-file src/example.py \
  --package-class docs-only \
  --include-protected-boundaries \
  --fail-on-protected-hit
```

Expected exit code: 1 (protected hit detected). Report as EXPECTED_EXIT_1, not
failure.

### Optional output file

```
python tools/git/code_blast_radius.py \
  --changed-file docs/project_status.md \
  --package-class docs-only \
  --format json \
  --output local_data/code_blast_radius/wp34_scope.local.json
```

## 4. Exit Codes

| Code | Meaning |
|---|---|
| 0 | Advisory summary generated. Warnings may be present. |
| 1 | Protected boundary hit(s) detected and `--fail-on-protected-hit` was used. |
| 2 | Usage or configuration error. |

The helper exit code never replaces actual validation command exit codes.
Exit 0 does not mean validation passed. Exit 1 from `--fail-on-protected-hit`
signals a protected-boundary warning, not a test failure.

## 5. CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--changed-file PATH` | (none) | Changed file (repo-relative). Repeatable. |
| `--changed-prefix PREFIX` | (none) | Changed path prefix (repo-relative). Repeatable. |
| `--package-class CLASS` | `unspecified` | Active WP package class (advisory warnings only). |
| `--include-tests` | off | Include likely related tests in output. |
| `--include-docs` | off | Include likely related docs in output. |
| `--include-protected-boundaries` | off | Report protected/sensitive path attention areas. |
| `--format text\|json` | `text` | Output format. |
| `--output PATH` | none | Optional output file (must be under `local_data/code_blast_radius/`). |
| `--max-results N` | `25` | Maximum advisory paths per section. |
| `--fail-on-protected-hit` | off | Exit 1 when protected boundary hits are detected. |
| `--repo-root DIR` | `.` | Repository root directory. |
| `--no-ast` | off | Disable stdlib ast import parsing for .py files. |

## 6. Safety Properties

- **Local only**: filesystem scanning only; no git command execution.
- **Offline**: no network calls; no HTTP/socket/websocket imports.
- **Read-only**: does not edit, stage, or commit any file.
- **No network**: no requests/httpx/aiohttp/socket/websockets imports.
- **No dependency**: Python standard library only.
- **No command execution**: no subprocess; no os.system.
- **No mutation by default**: no output file unless `--output` is provided.
- **No persistent index**: each run is fresh on-demand scan.
- **No secrets scanning replacement**: does not scan secret contents.
- **No validation replacement**: does not replace pytest, security checks, or human review.
- **No automatic approval**: cannot authorize merge-ready status.
- **No protected content reading**: `--include-protected-boundaries` flags path names and categories; it does not read protected file contents.

## 7. Output Sections

### Text output includes

- Schema version, mode, package class, stale-index status
- Changed files and prefixes
- Likely tests (when `--include-tests`)
- Likely docs (when `--include-docs`)
- Repo-truth files to inspect
- Direct text references
- Protected boundary attention (when `--include-protected-boundaries`)
- Dependency/lock attention
- Generated output attention
- Package-class warnings
- Unknown/low-confidence notes
- Truncation notes
- Advisory-only note
- Validation reminder
- Human-review reminder

### JSON output includes all of the above plus

- Sorted keys and indent 2 for stable parsing
- `summary_schema_version` field
- UTF-8 encoding with trailing newline

## 8. Relationship Detection

The helper uses conservative local heuristics only:

1. **Direct text references**: path string and stem mentions in local text files.
2. **Naming heuristics**: `test_<module>.py` patterns, doc-name similarity.
3. **Repo-truth relationship rules**: known repo-truth file relationships
   (e.g., `docs/repo_truth_index.md` → `docs/project_status.md`).
4. **Python AST imports**: stdlib `ast` import parsing for `.py` files
   (disable with `--no-ast` if needed).

Confidence is rated high/medium/low. It describes why a path is likely worth
inspecting; it is not proof, authorization, or approval.

## 9. Protected/Dependency/Generated Attention

Protected patterns include at minimum:

- `src/` (protected runtime source)
- `tools/hermes/`, `agent_runtime/`, `agent_memory/`
- `.env`, `.env.*`
- Credential-like filenames (private key, wallet key, mnemonic, etc.)
- Dependency/lock files

Dependency/lock attention flags common Python, Node, and Cargo dependency and
lock files.

Generated-output attention flags `local_data/`, `.sarif`, `.coverage`,
`security-scan-output/`, and `official-client-sandbox-output/`.

## 10. Non-Goals

The helper does not:

- Approve PRs or authorize merge-ready status.
- Replace security scans, pytest, preflight tools, or human review.
- Replace direct file inspection.
- Maintain a persistent code index.
- Use Tree-sitter, external indexers, LLMs, or network services.
- Affect trading, runtime, agent, or Hermes behavior.
- Execute git commands or shell commands.
- Modify any repository file.
- Stage or commit any file.

## 11. Output Path Restriction

The `--output` flag is optional. No file is written by default.

If `--output` is used, the path must be repo-relative and under
`local_data/code_blast_radius/`. Absolute paths and traversal are rejected with
exit 2. Output files must not be staged or committed.

## 12. Design Reference

See `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` for the WP33
design document and WP34 implementation decision record.
