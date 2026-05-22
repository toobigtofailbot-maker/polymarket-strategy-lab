# Code Index / Blast-Radius Helper Design

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

No helper is implemented in WP33. This document describes a future helper only.
Implementation requires a separate approved implementation work package.

## 2. Purpose

This design describes a future local code-index / blast-radius helper that would
summarize likely relationships between changed files, nearby tests, and relevant
repo-truth docs for Claude Code and Codex context efficiency.

The helper would be advisory only. It would help locate files and likely
inspection targets, but it would not decide scope, approve changes, or replace
direct inspection.

## 3. Non-Authority

A future helper must never become source of truth. Current merged repo files,
the active work package scope, changed files, tests, validators, and human
review remain authoritative.

The helper must not replace:

- Direct file inspection.
- Changed-file inspection.
- `docs/project_status.md`.
- Artifact, query, validator, or test evidence.
- Required validation commands.
- Human semantic review.
- PR review or merge approval.

The helper must not authorize runtime behavior, protected-path changes, config
changes, schema changes, validator changes, query-layer changes, policy,
scoring, ranking, recommendation, readiness, lifecycle, promotion/demotion, or
downstream authority.

## 4. Intended Future Modes

### On-demand scan mode

The first implementation should prefer on-demand scan mode. It would inspect the
current working tree and explicitly supplied changed files without writing an
index file by default.

### Snapshot/index file mode

Snapshot/index file mode is deferred. A future package may allow a generated
local index only under an ignored output path, with source commit, generation
timestamp, command used, included paths, excluded paths, and advisory-only note.

### Query mode

Query mode is deferred. It may read a fresh approved snapshot or perform an
on-demand scan to answer path-location and likely-test questions. It must not
answer semantic authority questions.

### Design-only mode

WP33 is design-only mode. It creates no helper, no index, and no generated
artifact.

## 5. Intended Future CLI Shape

The following CLI is design-only. Any actual CLI must be approved in a later
implementation WP:

```text
python tools/git/code_blast_radius.py \
  --changed-file docs/project_status.md \
  --changed-prefix docs/ai/codex/ \
  --package-class docs-only \
  --include-tests \
  --include-docs \
  --include-protected-boundaries \
  --format text|json \
  --output local_data/code_blast_radius/wp.local.json \
  --max-results 25 \
  --fail-on-protected-hit \
  --repo-root .
```

Proposed flags:

| Flag | Description |
|---|---|
| `--changed-file` | Changed file to analyze. May be repeated. |
| `--changed-prefix` | Changed path prefix to analyze. May be repeated. |
| `--package-class` | Active WP package class, used only for advisory warnings. |
| `--include-tests` | Include likely related tests in advisory output. |
| `--include-docs` | Include likely related docs in advisory output. |
| `--include-protected-boundaries` | Include protected-boundary notes without reading protected contents. |
| `--format text|json` | Output format. |
| `--output` | Optional output path, restricted to an ignored local output directory. |
| `--max-results` | Maximum advisory related paths per section. |
| `--fail-on-protected-hit` | Exit nonzero when protected-boundary hits are detected. |
| `--repo-root` | Explicit repository root for path normalization. |

## 6. Relationship Model

A future helper may report relationships using only conservative local evidence:

- Direct references: explicit path, module, or symbol mentions in tracked text
  files.
- Naming heuristics: filename, directory, test-name, and doc-name similarity.
- Repo-truth relationships: paths named in repo-truth docs and active workflow
  docs.
- Protected/sensitive relationships: protected paths, sensitive names, or
  boundary docs that require escalation and direct review.

Each relationship must include confidence high/medium/low. Confidence describes
why a path is likely worth inspecting; it is not proof, authority, or approval.

## 7. Suggested Future Inputs

Design-only candidate inputs:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- `docs/ai/codex/`
- `tools/`
- `tests/`
- Selected `docs/` files explicitly scoped by the active WP

Future implementation should exclude or carefully gate:

- `data/`
- `configs/`
- `.claude/`
- Runtime/protected implementation paths
- Large artifacts
- Private files
- Secrets
- Ignored generated outputs

## 8. Suggested Future Outputs

Design-only candidate outputs:

- `repo_root`
- `source_commit`
- `generated_at_utc`
- `package_class`
- `changed_files`
- `changed_prefixes`
- `included_paths`
- `excluded_paths`
- `direct_references`
- `naming_heuristics`
- `repo_truth_relationships`
- `protected_sensitive_relationships`
- `likely_tests`
- `likely_docs`
- `package_class_warnings`
- `stale_index`
- `advisory_note`

## 9. Stale-Index Model

Any future snapshot/index file must be treated as stale when:

- Source commit SHA differs from current `HEAD`.
- Relevant files changed after generation.
- Active package touches paths outside the indexed scope.
- Index generation command, included paths, or excluded paths are unknown.
- Tool version or schema version is unknown.

If stale or missing, Claude Code and Codex must regenerate under explicit
package scope or ignore the index. A stale index must not be used as evidence or
as a substitute for direct repo inspection.

## 10. Package-Class Awareness

A future helper may emit package-class warnings for patterns such as:

- Docs-only or design WP touching source/runtime paths.
- Design WP adding helper implementation files.
- Local-report/export WP touching credentials, network, or trading paths.
- Read-only public-data WP touching private, authenticated, or official-client
  paths.
- Runtime-dependency WP without explicit dependency authorization.
- Live-trading WP without explicit live-trading authorization.

Package-class warnings are advisory. They do not replace active WP scope,
validators, tests, or human review.

## 11. Excluded Paths and Sensitive-Content Model

A future implementation must avoid secrets, private data, and protected content.
It must not read or summarize `.env` values, private keys, wallet keys,
mnemonics, passphrases, API keys, tokens, exchange credentials, private endpoint
responses, private account data, or large raw data files.

Protected/runtime paths must be excluded by default or reported only as
protected boundary notes. If `--include-protected-boundaries` is used, the helper
may identify that a protected path exists or was touched, but it must not read
protected implementation contents unless a later WP explicitly authorizes that
behavior.

## 12. Validation-Preservation Rules

A future helper must not reduce validation. It cannot replace:

- Focused tests.
- Full pytest.
- Generated artifact guard.
- Remote Main Sync Gate.
- Security checks and honest unavailable-tool reporting.
- `git diff --check`.
- Direct changed-file inspection.
- Human review.
- The mandatory final PR comment.

The helper cannot authorize merge-ready status by itself.

## 13. Future Implementation Test Plan

Any future implementation WP must include tests covering at minimum:

- Advisory output only and validation reminder presence.
- On-demand scan mode without output file creation by default.
- Snapshot/index file staleness detection.
- Direct reference relationship detection.
- Naming heuristic relationship detection.
- Repo-truth relationship detection.
- Protected/sensitive relationship handling.
- confidence high/medium/low output.
- Package-class awareness warnings.
- Excluded paths and sensitive-content filtering.
- Output path restrictions for `--output`.
- `--fail-on-protected-hit` behavior.
- JSON/text output schema.
- No mutation of repo files.
- No network calls or external service calls.
- No dependency additions.
- Windows path normalization.

## 14. Open Design Questions

1. Should the first implementation support only on-demand scan mode, or also
   write an optional ignored snapshot/index file?
2. Should `--include-protected-boundaries` report only matched path names, or
   also cite the protected-boundary repo-truth doc that caused the warning?
3. Should protected hits default to exit 0 with warnings, or should
   `--fail-on-protected-hit` become the default for docs-only and design WPs?
4. Should relationship confidence be rule-only, or should future implementation
   allow a configurable scoring table?
5. Should query mode be deferred until a snapshot/index file mode exists?

## 15. Recommended Next WP

The recommended next WP after this design is accepted is either:

- WP34 - Code Index / Blast-Radius Helper Implementation, if the user approves a
  local/offline/read-only standard-library implementation; or
- WP34 - Code Index / Blast-Radius Helper Design Follow-Up, if open design
  questions need resolution before implementation.

No follow-on WP is authorized by this design document. Authorization requires a
separate explicit work package instruction.

## 16. Manual-Step Rule

Manual steps for this package: none.

Manual steps may become relevant only if a later implementation package requires
local setup. The default expected future implementation should be repo-local,
standard-library-only, and require no manual user setup.

## 17. Stop Conditions

Stop before implementation if:

- The helper would need external services or dependency additions.
- The helper would need protected runtime contents.
- The helper would create generated index files intended for commit.
- The design would weaken validation or direct inspection.
- The active package touches paths outside the approved scan scope.
- Staleness rules cannot be enforced or reported clearly.
- Secrets or private files could be included.
- The wording or behavior implies source-of-truth, approval, readiness,
  lifecycle, promotion/demotion, or downstream authority.

## 18. Future Implementation Package Requirements

A future implementation WP must remain narrow, local, offline, read-only, and
standard-library-only unless explicitly approved otherwise. It must update repo
truth, add focused tests, run required validation, and preserve the rule that the
helper is advisory only.

No implementation is authorized by this design document. No generated code
index, AST summary, symbol index, dependency graph, blast-radius tool,
validation wrapper, memory file, runtime integration, or protected-path
authority is created here.
