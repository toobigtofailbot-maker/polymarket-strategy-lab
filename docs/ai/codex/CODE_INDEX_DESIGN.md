# Code-Index Design

## Scope and non-authority

This document is design-only. It does not implement a code-index or blast-radius
helper, does not create or commit generated index files, does not reduce
validation, and does not alter repo-truth precedence.

A future code index is advisory only. It must never become source of truth,
semantic authority, merge authority, or approval authority. Current merged repo
files remain source of truth. The active package scope remains source of truth
for the package.

## Problem statement

Codex and Claude Code often need to locate likely files quickly while preserving
direct inspection discipline. A stale or overbroad index could become
pseudo-truth, hide repo drift, or encourage skipping changed-file inspection.

## Design goal

Design a future local helper that may summarize repo structure, likely file
locations, and narrow blast-radius hints for context efficiency while preserving
repo-truth, direct inspection, validation, and protected-boundary rules.

## Source-of-truth boundary

The index may help locate files, summarize stable structure, and suggest likely
inspection targets. It must not replace:

- Direct file inspection.
- Changed-file inspection.
- `docs/project_status.md`.
- Artifact, query, validator, or test evidence.
- Required validation commands.
- Side semantic review.
- Human review or PR approval.

The index must not authorize implementation, runtime behavior, protected-path
changes, schema changes, validator changes, query-layer changes, policy,
scoring, ranking, recommendation, readiness, lifecycle, promotion/demotion, or
downstream authority.

## Allowed future index behavior

A future implementation may, if explicitly scoped by a later WP:

- Produce advisory path summaries for repo-local files.
- Group likely inspection targets by docs, tools, tests, and explicitly scoped
  research metadata.
- Summarize stable module names, safe docstrings, safe signatures, and high-level
  dependency hints.
- Mark protected paths as protected and non-authoritative.
- Report stale or missing index state.
- Exit nonzero when stale-index checks fail, if that behavior is explicitly
  approved and tested.

## Disallowed behavior

A future implementation must not:

- Treat index output as repo truth.
- Use a stale index without regeneration or direct verification.
- Replace direct file reads, changed-file review, validators, integrity views,
  scoped pytest, full pytest, artifact/query evidence, or Side semantic review.
- Read or summarize secrets, `.env` values, private keys, wallet keys, tokens,
  exchange credentials, private data files, large raw data files, or protected
  implementation content unless a later package explicitly allows it.
- Send repo contents to external services.
- Add dependencies without explicit later approval.
- Embed full source files.
- Modify, stage, delete, or generate committed repo files by default.
- Create runtime, paper/live, OMS, risk, safe-mode, schema, validator,
  query-layer, policy, scoring, ranking, recommendation, approval, readiness,
  lifecycle, promotion/demotion, or downstream authority.

## Suggested future index inputs

These inputs are design-only candidates. A later implementation WP must approve
the exact scope before code is written:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/ai/codex/`
- `tools/`
- `tests/`
- `research/` metadata paths if explicitly scoped
- Selected `docs/research_pipeline/` files if explicitly scoped

A future implementation should exclude or carefully gate:

- `data/`
- `configs/`
- `.claude/`
- Runtime/protected implementation paths
- Large artifacts
- Private files
- Secrets

## Suggested future index outputs

These outputs are design-only candidates:

- `repo_root`
- `source_commit`
- `generated_at_utc`
- `index_scope`
- `excluded_paths`
- `path_summaries`
- `module_summaries`
- `test_summaries`
- `doc_summaries`
- `protected_path_notes`
- `staleness_rules`
- `advisory_note`

A future generated index must include generation timestamp, source commit SHA,
command used, included path prefixes, excluded path prefixes, and an
advisory-only note.

## Freshness and staleness rules

A future generated index must be treated as stale when:

- Source commit SHA differs from current `HEAD`.
- Relevant files changed after generation.
- Active package touches paths outside the indexed scope.
- Index generation command or exclusions are unknown.

If stale or missing, Codex must regenerate under explicit package scope or ignore
the index. A stale index must not be used as evidence, authority, or a substitute
for direct repo inspection.

## Protected-boundary handling

Protected/runtime paths must be excluded by default or marked protected and
non-authoritative. A future helper must not summarize protected-path contents
unless a later package explicitly scopes and approves that behavior.

Protected-path hits must be escalation signals, not permission to edit protected
runtime boundaries. Runtime execution, OMS, reconciliation, risk caps, bounded
overlay semantics, safe mode, configs, live-trading paths, schemas, validators,
and query-layer code remain outside this design.

## Suggested future CLI shape

The following CLI is design-only. Any actual CLI must be approved in a later
implementation WP:

```text
python tools/dev/code_index.py --scope docs-ai
python tools/dev/code_index.py --scope tools-dev
python tools/dev/code_index.py --scope tests
python tools/dev/code_index.py --json
python tools/dev/code_index.py --check-stale
python tools/dev/code_index.py --output <path>
```

The current repo uses `tools/git/` and `tools/validation/` for existing helpers;
a later implementation WP must choose the final path and document the choice.

## Suggested future JSON shape

```json
{
  "repo_root": "C:/GitHub/polymarket-strategy-lab",
  "source_commit": "<git-sha>",
  "generated_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "index_scope": ["docs/ai/codex/"],
  "excluded_paths": ["data/", "configs/", ".claude/"],
  "path_summaries": [],
  "module_summaries": [],
  "test_summaries": [],
  "doc_summaries": [],
  "protected_path_notes": [],
  "staleness_rules": [],
  "advisory_note": "Advisory only. Does not replace repo-truth inspection."
}
```

## Suggested future tests

Any future implementation must include tests proving:

- Advisory output only.
- Stale-index detection.
- Protected-path exclusion or protected marking.
- No repo mutation.
- No dependency addition.
- No external calls.
- No secrets or private-file inclusion.
- Direct-inspection and validation reminders remain present.
- JSON output, if implemented, matches the approved shape.
- Windows path handling is correct.

## Manual-step rule

Manual steps for this design package: none.

Manual steps may become relevant only if a later implementation package requires
local setup. The default expected future implementation should be repo-local,
standard-library-only, and require no manual user setup.

## Implementation prerequisites

Before any implementation WP, repo truth must approve:

- Exact helper path and CLI.
- Exact included and excluded path prefixes.
- Output mode and whether file output is allowed.
- Staleness detection behavior and exit codes.
- Protected-path handling.
- Test plan and validation requirements.

The future helper must be local-only and standard-library-only unless a later
package explicitly approves dependencies. It must not send repo contents to
external services.

## Stop conditions

Stop before implementation if:

- The helper would need external services or dependency additions.
- The helper would need protected runtime contents.
- The helper would create generated index files intended for commit.
- The design would weaken validation or direct inspection.
- The active package touches paths outside the approved index scope.
- Staleness rules cannot be enforced or reported clearly.
- Secrets or private files could be included.
- The wording or behavior implies source-of-truth, approval, readiness,
  lifecycle, promotion/demotion, or downstream authority.

## Future implementation package requirements

A future implementation WP must remain narrow, local, offline, read-only, and
standard-library-only unless explicitly approved otherwise. It must update repo
truth, add focused tests, run required validation, and preserve the rule that the
index is advisory only.

No implementation is authorized by this design document. No generated code index,
repo map, AST summary, symbol index, dependency graph, blast-radius tool,
validation wrapper, memory file, runtime integration, or protected-path authority
is created here.
