# S10-GOV-COPY-01 Status Entry

## Identity

- WP ID: S10-GOV-COPY-01
- Title: Unchanged Copy-Origin Exact-Scope Policy
- Branch: codex/s10-gov-copy-01-copy-origin-scope
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
  and non-self-referential; it does not encode the SHA of the commit containing itself.
- Base commit: a78809ddb62cf143ac85ee297e87f961aa9b61f9
- Predecessor: PR #227 / S10-CC-STREAM-01, head f344979f8f620519175defe627a5829b569b665d, merged at base.
- Package class / size / risk: LOCAL_OFFLINE_STDLIB_GOVERNANCE_HELPER_HARDENING / M / 1
- Governance track: FAST; readiness basis DETERMINISTIC; no certificate required.
- Drafting/finalization: Side18 adopted the exact approved package; Karl authorized bounded Codex execution.
- Merge commit: not merged; merge authorized NO (Karl only).
- Evidence mode / current readiness: see current PR body after final posted verification.

## Policy and authority

This is an explicit narrow governance-policy successor to historical WP159, not a bypass.
Allowed-file classification excludes unchanged C-origin provenance only. Copy-origin forbidden,
protected, generated, dependency/lock and authority checks remain. Rename-origin policies remain.
Actual independently changed sources, destinations and untracked paths remain fully checked;
unique changed count, required presence, fixed Git argv/NUL parser, output and strict exits remain.
Implementation authority is limited to the exact local helper, tests, docs and package below.
No source runtime, dependencies, CI/workflow, helper/product network, credentials, scheduler,
Hermes, strategy, paper, execution, orders, capital or live authority. Capital/orders USD 0 / 0.
Workflow network is used for git/GitHub synchronization and PR push/publication only.

## Exact scope

- tools/git/diff_scope_summary.py
- tests/tools/git/test_diff_scope_summary.py
- docs/ai/codex/WP_SPEC_STANDARD.md
- docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md
- docs/wp_specs/S10-GOV-COPY-01/wp_prompt.txt
- docs/wp_specs/S10-GOV-COPY-01/wp_spec.json
- docs/status_entries/S10-GOV-COPY-01.md
- docs/project_status.md
- docs/repo_truth_index.md

## Validation and negative matrix

The PR body records exact commands, results, counts, environment and final hosted/posted evidence.
Preimplementation deterministic readiness: IMPLEMENTATION_READY / FAST / exit 0.
Focused helper and WP-spec integration tests plus affected workflow/status docs are required.
Editing validation passed the focused suite and affected workflow/status documentation guards.
The linked worktree availability runner reports gitleaks, Semgrep and pip-audit as unavailable
in its local lookup paths; npm/cargo root audits are inapplicable. Existing external local
gitleaks and Semgrep binaries supply supplemental actual-surface scans, with exact commands,
coverage and outcomes in the PR body. The offline Semgrep rule set is bounded to changed Python
files; unavailable checks are not described as passing. No dependency change is introduced.
New tests exercise benign C100/C075, every retained origin safety/authority classifier, invalid
destinations and rename origins, independently changed sources, other exact-scope gates,
strict CLI exits and a real disposable Git C100 fixture. Existing signatures/schema/parser/Git
argv/fail-closed diagnostics remain covered. No new output fields or public helper API.
Stable candidate requires readiness --check-diff, exact scope, artifact/security checks, one
full local suite, exact-head nine-job hosted CI and strict guard on the re-fetched PR body.
Current final guard/result/readiness lives in the PR body; no unearned PASS is recorded here.
No material issue is silently deferred; any new blocked gate outside nine paths requires a stop.

## Follow-up and successor

Follow-up classification: explicit governance-policy correction; no unrelated runtime repair.
Historical WP159 artifacts and PR #228 are unchanged. CMD-01 remains separately blocked.
After governance merge advances main, Side18 must prepare a separately authorized protected
baseline synchronization and independent recertification preserving CMD-01's original twenty paths.
That future continuation is not implemented or authorized here; old CMD-head CI cannot certify it.
Side18 independently reviews this governance PR; Karl alone may merge.
