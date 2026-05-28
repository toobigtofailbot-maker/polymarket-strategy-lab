# Memory / Status Snapshot Helper Design

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
- Snapshot authority: ADVISORY_ONLY_NOT_REPO_TRUTH

WP35 is design-only. No helper is implemented. No snapshot output is generated.
No persistent memory file is created. No repo-truth file is replaced.

## 2. Purpose

The future memory / status snapshot helper would create a concise, sanitized,
repo-truth-derived snapshot of the current project state for quick orientation
before WP drafting or PR review.

Repeated WP drafting and PR review require re-reading the same repo-truth status
files (project_status.md, deferred_items_log.md, repo_truth_index.md, etc.).
A controlled snapshot can reduce that repeated context load by pre-extracting
and summarizing the key orientation fields.

The helper is not a memory authority. It cannot replace repo-truth files.
It does not grant permissions, authorize work, or replace any required check.
It is a read-only orientation aid that summarizes what can already be found by
reading repo-truth files directly.

## 3. Non-Goals

WP35 and the first implementation WP must not add:

- Memory/status snapshot helper implementation.
- Snapshot generator implementation.
- Persistent memory file or memory store.
- Generated snapshot output.
- Command runner or subprocess execution.
- Validation wrapper or replacement.
- Repo-truth replacement of any kind.
- Automatic PR approval.
- Automatic file modification.
- Network calls of any kind.
- LLM integration.
- Hermes integration.
- Agent runtime.
- Trading or execution authority.
- Credentials, private keys, wallet data, or private endpoint access.
- External memory engine (e.g., chromadb, llama-index, mem0) — future design
  may mention these as rejected options requiring separate explicit approval;
  they are not authorized.

## 4. Authority Model

Repo truth always wins. A snapshot is advisory only.

A snapshot must cite its source repo-truth input files so consumers can
verify the information is current.

A snapshot is stale until explicitly compared with current main and latest
merge commit. A snapshot that has not been staleness-checked cannot be
treated as current project state.

A snapshot cannot override:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- Active WP text.
- PR diff and final PR comment.

A snapshot cannot approve work. A snapshot cannot authorize merge-ready status.

## 5. Future Helper Constraints

A future approved implementation must satisfy:

- Standard-library only. No new dependency or lock-file change in first
  implementation.
- Local/offline/read-only. No network calls. No git remote calls.
- No command execution beyond local file reads.
- No repo mutation. No staged or committed output by default.
- Default output is stdout summary only. No file written by default.
- Optional JSON/Markdown output only under ignored
  `local_data/status_snapshots/` if a future WP explicitly allows it.
- Stale snapshot warnings are mandatory for any saved output.
- Must never include secrets, credentials, private keys, wallet data, private
  endpoint data, account data, or generated market data.
- Must not read prohibited input sources.
- Must not weaken validation, skip required checks, or replace human review.

## 6. Intended Future Modes

### Stdout orientation mode

Default mode. No file is written. Emits a concise project-state summary to
stdout. Safe to run at any time before WP drafting or PR review.

### Snapshot file mode

Optional. Writes a snapshot under ignored `local_data/status_snapshots/`.
A saved snapshot must include commit SHA, branch, generated timestamp, input
file list or hashes, and helper version/schema. A saved snapshot must warn
if current HEAD differs from snapshot commit.

### Compare/staleness mode

Optional. Compares a saved snapshot's metadata to current repo state. Reports
staleness only. Does not update repo-truth files. Does not alter the snapshot
itself.

### Design-only mode

WP35 is design-only mode. No helper is implemented. No snapshot is generated.
No file is written. No tool exists at `tools/git/status_snapshot.py`.

## 7. Intended Future CLI Shape

The following CLI is design-only. No implementation exists. Any actual CLI
must be approved and implemented in a later WP.

```text
python tools/git/status_snapshot.py --format text

python tools/git/status_snapshot.py --format json

python tools/git/status_snapshot.py --format json \
  --output local_data/status_snapshots/wp35_status.local.json

python tools/git/status_snapshot.py \
  --check-stale local_data/status_snapshots/wp35_status.local.json
```

Proposed future flags:

| Flag | Description |
|---|---|
| `--format text\|json\|markdown` | Output format (`--format text|json|markdown`). Default `text`. |
| `--output PATH` | Optional output path (must be under `local_data/status_snapshots/`). |
| `--repo-root DIR` | Explicit repository root. |
| `--include-deferred` | Include open deferred item digest. |
| `--include-helper-inventory` | Include local helper inventory section. |
| `--include-next-wp-candidates` | Include next WP candidate digest. |
| `--include-protected-boundaries` | Include protected boundary status block. |
| `--max-deferred-items N` | Cap number of deferred items in digest. |
| `--check-stale PATH` | Compare a saved snapshot to current repo state. |
| `--fail-on-stale` | Exit nonzero if snapshot is stale. |
| `--fail-on-sensitive-hit` | Exit nonzero if sensitive content detected in output. |

## 8. Intended Safe Input Sources

A future implementation must read only from allowlisted safe sources:

- `AGENTS.md`
- `CODEX_START_HERE.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/deferred_items_log.md`
- `docs/review_checklist.md`
- `docs/testing_requirements.md`
- `docs/ai/codex/README.md`
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`
- Existing helper user-facing docs:
  - `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md`
  - `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md`
  - `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md`
- Security/runtime/live-trading boundary docs:
  - `docs/security_and_secrets.md`
  - `docs/runtime_boundaries.md`
  - `docs/live_trading_authorization.md`

Any extension of this allowlist requires an explicit approved implementation
WP. The helper must not read arbitrary filesystem paths.

## 9. Prohibited Input Sources

A future implementation must never read from:

- `.env`, `.env.*`
- Credential files, private-key files, wallet files, mnemonic files, token
  files.
- local account data
- private endpoint responses
- `local_data/` contents by default
- generated reports or exports by default
- `.venv-*`
- `tools/.bin/`
- security scan raw outputs by default
- official-client sandbox outputs by default
- arbitrary filesystem paths
- network or GitHub API responses
- chat history or user memory outside repo truth

If content from a prohibited source is detected in a safe input file, the
snapshot must be flagged as potentially unsafe and that content must be redacted.

## 10. Intended Output Structure

Both text and JSON summaries should include the following fields when populated:

- summary schema version
- generated timestamp
- repo commit SHA if available
- branch if available
- source repo-truth files used to build the snapshot
- current phase
- latest merged WP and merge commit when known
- current branch/status from repo truth
- protected boundary status block
- helper inventory:
  - diff/scope summary helper (path and status)
  - validation-output summary helper (path and status)
  - code blast-radius helper (path and status)
- open deferred item digest (key open items)
- next WP candidate digest
- current validation and reporting expectations
- generated artifact and output rules
- manual setup decision status
- stale snapshot warning
- advisory-only note
- repo-truth verification reminder
- validation and human-review reminder

## 11. Sanitization and Sensitive-Output Model

A future implementation must not include secrets or suspected secrets in
any output (text, JSON, Markdown, or file).

A future implementation must detect obvious sensitive terms in input/output:

- `API_KEY`
- `PRIVATE_KEY`
- `CLOB_SECRET`
- `CLOB_PASS_PHRASE`
- `MNEMONIC`
- `TOKEN`
- `Bearer`
- Private-key blocks (PEM headers, etc.)

If secret-like content appears in a safe input source:

- Flag the snapshot as potentially unsafe.
- Redact the value (replace with `[REDACTED]`).
- Optionally fail with nonzero exit if `--fail-on-sensitive-hit` is used.

The helper is not a replacement for gitleaks or semgrep. It must not read
prohibited input sources in order to scan for secrets.

## 12. Staleness Model

Saved snapshots must include the following staleness metadata:

- Commit SHA at generation time or `unknown`.
- Branch at generation time or `unknown`.
- Generated timestamp.
- Helper version or schema version.
- Input file list.
- Optional input file hashes if a future WP implementation scopes them.

A snapshot consumer must treat a snapshot as stale if:

- Current HEAD differs from the snapshot commit SHA.
- Current branch differs from the snapshot branch.
- Required repo-truth files changed after snapshot generation.
- Generated timestamp is absent or malformed.
- Schema version is absent or unsupported.

Stale snapshots are not invalid data. They represent the state at generation
time and may still provide useful orientation, but they are not current
authority. Future implementation must print a strong stale warning rather
than silently using old information.

## 13. Snapshot Lifecycle and Storage Policy

Default behavior: no file is generated. The helper prints to stdout and exits.

Optional output file: written only under ignored `local_data/status_snapshots/`
if `--output` is provided.

Generated snapshots must never be staged or committed. The
`local_data/status_snapshots/` path must remain git-ignored.

No tracked memory file is created in WP35 or in the first implementation WP.

No durable project memory outside repo truth. If a future tracked
status summary is ever desired, it requires a separate explicit
repo-governance WP and must not be introduced by this helper.

## 14. Relationship to Existing Helpers

The existing local helpers serve distinct roles:

- **Diff/scope summary helper** (`tools/git/diff_scope_summary.py`): identifies
  changed file scope and flags protected, dependency, and generated output
  warnings for the current WP diff. Implemented in WP30.
- **Validation-output summary helper**
  (`tools/validation/validation_output_summary.py`): summarizes already-run
  validation evidence for final PR reports. Implemented in WP32.
- **Code blast-radius helper** (`tools/git/code_blast_radius.py`): suggests
  likely related files, tests, docs, and boundary attention areas given a set
  of changed files. Implemented in WP34.
- **Future memory/status snapshot helper**
  (`tools/git/status_snapshot.py`, design-only in WP35): summarizes repo-truth
  project state for quick orientation before WP drafting or PR review.

None of these helpers replace mandatory validation, security checks,
direct file inspection, or human review. They are advisory aids only.

## 15. Package-Class Usage

The future helper is advisory for these scenarios:

### WP drafting

Use snapshot to identify current phase, latest merged WP, protected boundaries,
and next WP candidates. Always verify against current repo-truth files before
drafting.

### PR review

Use snapshot only as initial orientation. Inspect the PR diff and repo-truth
files directly before completing review.

### Handoff and onboarding

Use snapshot as a quick start to reduce re-reading all status files. Never
treat a snapshot as final authority.

### Runtime, trading, and security packages

A snapshot cannot authorize protected work. Explicit WP text, repo-truth gates,
security checks, and human review remain required regardless of snapshot content.

## 16. Future Implementation Test Plan

A future implementation WP must include tests covering at minimum:

- Design or source file discovery tests.
- Safe input source allowlist tests — only allowlisted files may be read.
- Prohibited input source rejection tests — `.env`, credential files, etc.
  must be rejected.
- Output path restriction tests — `--output` restricted to
  `local_data/status_snapshots/`.
- Status parsing tests for `docs/project_status.md`.
- Deferred item digest tests.
- Helper inventory tests.
- Next WP candidate extraction tests.
- Stale snapshot metadata tests — commit SHA, branch, timestamp, schema version.
- Sensitive-output redaction tests — `API_KEY`, `PRIVATE_KEY`, `CLOB_SECRET`,
  `CLOB_PASS_PHRASE`, `MNEMONIC`, `TOKEN`, `Bearer`, private-key blocks.
- Advisory-only note and authority reminder tests.
- Text, JSON, and Markdown output tests if scoped.
- No-network, no-command-execution, and no-forbidden-import tests.
- Windows path handling tests.

## 17. Open Design Questions

1. Should the first implementation support JSON output only, or text and JSON
   together?
2. Should Markdown output be included in the first implementation or deferred
   to a follow-up WP?
3. Should input file hashes be included in the first implementation's staleness
   metadata, or only file names and commit SHA?
4. Should `--check-stale` mode be included in the first implementation or
   deferred?
5. Should snapshot output include all open deferred items or only a capped
   digest (e.g., top 10 by priority)?
6. Should snapshot output include security tool availability status or only
   link to repo-truth docs?
7. Should generated snapshots use `.local.json` naming convention enforced
   by the implementation?
8. Should a successful memory/status snapshot implementation fully resolve
   WP28-D001, or only narrow it (since command-output compression remains
   not implemented)?

## 18. Recommended Next WP

- **WP36 - Memory / Status Snapshot Helper Implementation**, if this design is
  accepted and implementation scope is approved by the user.
- **WP36 - Memory / Status Snapshot Helper Design Follow-Up**, if open design
  questions in Section 17 require resolution before implementation.
- **WP36 - Local Advisory Handoff Package**, if the user chooses to resume
  the prior advisory handoff package plan instead of implementing this helper.

No follow-on WP is authorized by this design document. Authorization requires
a separate explicit work package instruction.
