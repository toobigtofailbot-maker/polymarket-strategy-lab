# Candidate Review Workflow Local Smoke Receipt

## 1. Purpose

This receipt records a local/offline smoke check for the candidate review
operator workflow documented in
`docs/runbooks/candidate_review_report_operator_runbook.md`.

It verifies that the documented WP87 fixture loader, WP89 candidate review
report generator, and WP90 local export layer can be exercised through existing
import surfaces without adding a CLI, source implementation, tool, dependency,
runtime behavior, paper behavior, live behavior, network/API behavior, account
access, or credential workflow.

## 2. Verified Repo Surfaces

Verified import surfaces:

- `CandidateFixtureLoadResult`
- `load_wallet_signal_paper_strategy_candidate_fixtures`
- `CandidateReviewReport`
- `build_wallet_signal_candidate_review_report`
- `candidate_review_report_to_dict`
- `render_wallet_signal_candidate_review_report`
- `CandidateReviewReportExportResult`
- `export_wallet_signal_candidate_review_report`
- `candidate_review_report_export_result_to_dict`

Verified source files:

- `src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py`
- `src/data_layer/wallet_signal_candidate_review_report.py`
- `src/data_layer/wallet_signal_candidate_review_report_export.py`

Verified fixture/test surfaces:

- `tests/fixtures/wallet_signal_paper_strategy_candidates/`
- `tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py`
- `tests/test_wallet_signal_candidate_review_report.py`
- `tests/test_wallet_signal_candidate_review_report_export.py`
- `tests/test_candidate_review_workflow_smoke_receipt.py`

## 3. Local Smoke Path

The local smoke path is import-only:

1. Load existing local test fixtures with
   `load_wallet_signal_paper_strategy_candidate_fixtures`.
2. Build an in-memory report with
   `build_wallet_signal_candidate_review_report`.
3. Render/serialize the report with
   `render_wallet_signal_candidate_review_report` and
   `candidate_review_report_to_dict`.
4. Export Markdown and JSON files to a pytest `tmp_path` directory with
   `export_wallet_signal_candidate_review_report`.
5. Serialize the export result with
   `candidate_review_report_export_result_to_dict`.

No CLI is introduced by this WP.
The smoke receipt verifies existing import surfaces only.

## 4. What Was Exercised

The smoke test exercises the existing local fixture directory and asserts:

- one valid record, two invalid records, and one malformed file are represented
  in the loader/report path;
- the report summary agrees with the loader result;
- Markdown and JSON exports are written only under the test-local output
  directory;
- export filenames remain fixed to `candidate_review_report.md` and
  `candidate_review_report.json`;
- generated file contents do not contain forbidden unsafe variants from the
  existing candidate-review output tests;
- generated file contents do not include the absolute checkout path, home-path
  markers, or drive-letter path markers;
- export result statuses are the expected allowlisted local write statuses.

## 5. What Was Not Exercised

The smoke receipt does not exercise:

- new source implementation;
- new CLI behavior;
- new tools;
- network/API ingestion;
- credentials or account/private endpoint access;
- scheduler, dashboard, daemon, or bot-loop behavior;
- paper strategy implementation;
- paper order models, portfolio ledgers, fill models, PnL computation,
  expected-return computation, or position sizing;
- live trading, order placement, cancellation, or risk override behavior;
- strategy promotion or candidate ranking for execution.

## 6. Non-Authority / Safety Notes

This receipt is a local workflow verification record only. It is not trading advice,
not a signal, not a recommendation, and not canonical evidence for any runtime
behavior.

The operator workflow remains local, offline, import-based, and human-reviewed.
It does not authorize paper or live trading. It does not authorize order placement
or cancellation. It does not authorize strategy promotion, candidate ranking for
execution, expected-return computation, position-size computation, network/API
behavior, account access, credentials, scheduler behavior, dashboard behavior,
or bot-loop behavior.

## 7. Validation Commands

Focused smoke and runbook checks:

```bash
python -m pytest tests/test_runbook_docs.py -v
python -m pytest tests/test_candidate_review_workflow_smoke_receipt.py -v
```

Loader/report/export API checks:

```bash
python -m pytest tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py tests/test_wallet_signal_candidate_review_report.py tests/test_wallet_signal_candidate_review_report_export.py -v
```

Related docs/status/boundary/workflow checks:

```bash
python -m pytest tests/test_project_status_docs.py tests/test_architecture_boundaries.py tests/test_codex_workflow_docs.py -v
```

Full and guard checks:

```bash
python -m pytest
git diff --check
python tools/git/preflight_generated_artifact_guard.py
python tools/git/diff_scope_summary.py --base origin/main --head HEAD --package-class workflow-docs-tests-only --allowed-prefix docs/ --allowed-prefix tests/test_runbook_docs.py --allowed-prefix tests/test_project_status_docs.py --allowed-prefix tests/test_architecture_boundaries.py --allowed-prefix tests/test_codex_workflow_docs.py --allowed-prefix tests/test_candidate_review_workflow_smoke_receipt.py --allowed-prefix tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py --allowed-prefix tests/test_wallet_signal_candidate_review_report.py --allowed-prefix tests/test_wallet_signal_candidate_review_report_export.py --forbidden-prefix src/ --forbidden-prefix tools/ --forbidden-prefix .github/workflows/ --forbidden-prefix local_data/ --forbidden-prefix requirements.txt --forbidden-prefix pyproject.toml --forbidden-prefix package.json
python tools/security/run_available_security_checks.py
```

## 8. Stable Status Fragment Policy Compliance

WP94 keeps the stable status-fragment policy from WP93 final follow-up.
The committed status fragment uses stable references for PR identity and current
live head:

- `PR: see GitHub PR metadata and PR body.`
- `Current live PR head: see GitHub PR metadata and PR body.`

It does not use `PR: TBD` with Ready YES, does not store a fixed current live
PR head SHA, and does not use `LOCAL_DRAFT_VERIFIED` as the final active
evidence state with Ready YES.

## 9. Known Limitations / Deferred Items

- The workflow remains import-based only; no CLI exists for this candidate
  review workflow.
- The smoke output is temp/local-only; no generated Markdown or JSON export is
  committed.
- WP90-D001 remains OPEN for future paper strategy implementation under a
  separate approved WP and protected-boundary review.
- WP91-D001 and WP92-D001 remain OPEN for any future GitHub-aware private
  evidence verifier.
- Existing runtime, paper, live, credential, network/API, scheduler, dashboard,
  bot-loop, and dependency deferred items remain unchanged.

## 10. Next WP Suggestion

Suggested next class: docs/design-only paper-strategy preparation or another
workflow receipt package from refreshed `main`.

The next WP should not implement paper strategy behavior, runtime behavior,
network/API behavior, credentials, scheduler/dashboard/bot-loop behavior, or
live trading unless a later approved package explicitly authorizes that scope.
