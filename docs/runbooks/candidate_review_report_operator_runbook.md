# Candidate Review Report Operator Runbook

## 1. Purpose

This runbook documents the safe local workflow for reviewing wallet-signal
paper-strategy candidate fixtures with the WP87 loader, WP89 candidate review
report generator, and WP90 local report exporter.

The workflow is local, offline, import-based, and operator-controlled. It helps
a human inspect whether local candidate contract fixture records loaded safely,
which records passed validation, which records were rejected, and whether a
local Markdown or JSON report was exported for review.

## 2. Scope and Non-Authority

The candidate review report is a local review aid only.

It is not trading advice. It is not a signal. It is not a recommendation. It
does not authorize paper or live trading. It does not authorize order placement.
It does not rank candidates for execution. It does not compute expected return
or position size. It does not use credentials or account access.

This runbook does not create a CLI, runner, scheduler, dashboard, bot loop,
strategy module, paper engine, live path, network ingestion path, or credential
workflow. It documents existing import-based local surfaces only.

## 3. Prerequisites

- Run commands from the repository root.
- Use a refreshed branch based on current `main` when relying on repo truth.
- Keep input fixtures and generated outputs under operator-selected local
  directories such as `local_data/`.
- Do not commit local report exports unless a future approved WP explicitly
  authorizes that.
- Confirm the relevant source and tests exist:
  - `src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py`
  - `src/data_layer/wallet_signal_candidate_review_report.py`
  - `src/data_layer/wallet_signal_candidate_review_report_export.py`
  - `tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py`
  - `tests/test_wallet_signal_candidate_review_report.py`
  - `tests/test_wallet_signal_candidate_review_report_export.py`

## 4. Local Input Fixtures

The fixture loader accepts only explicit local filesystem paths:

- one `.json` file containing one candidate contract record object;
- one directory whose direct child `.json` files are loaded in sorted order.

The loader does not recurse into subdirectories. Non-JSON files in a directory
are ignored. URL-like paths are rejected. Missing paths, unsupported file types,
malformed JSON, and invalid contract records are reported with safe neutral
errors and do not echo raw unsafe input.

Use repo-relative examples in notes and committed docs. Avoid committing local checkout paths.
Avoid drive-letter paths, home paths, or temp paths.

## 5. Candidate Fixture Loading

Use the WP87 import surface directly:

```python
from pathlib import Path

from src.data_layer.wallet_signal_paper_strategy_candidate_fixture_loader import (
    CandidateFixtureLoadResult,
    load_wallet_signal_paper_strategy_candidate_fixtures,
)

fixture_path = Path("local_data/wallet_signal_candidates")
load_result: CandidateFixtureLoadResult = (
    load_wallet_signal_paper_strategy_candidate_fixtures(fixture_path)
)
```

Relevant public result fields:

- `root_path`
- `total_files`
- `loaded_files`
- `valid_records`
- `invalid_records`
- `malformed_files`
- `items`
- `errors`
- `warnings`
- `advisory_label`

Each item records `fixture_path`, `load_status`, `validation_status`,
`is_valid`, `errors`, `warnings`, and `normalized_record`.

## 6. Candidate Review Report Generation

Use the WP89 report generator on the in-memory loader result:

```python
from src.data_layer.wallet_signal_candidate_review_report import (
    CandidateReviewReport,
    build_wallet_signal_candidate_review_report,
    candidate_review_report_to_dict,
    render_wallet_signal_candidate_review_report,
)

report: CandidateReviewReport = build_wallet_signal_candidate_review_report(
    load_result
)
markdown = render_wallet_signal_candidate_review_report(report)
serialized = candidate_review_report_to_dict(report)
```

The report generator consumes only `CandidateFixtureLoadResult`. It performs no
file reads, no file writes, no network calls, no credential access, no account
activity, and no scheduling. Its Markdown is deterministic and uses safe reason
codes for valid, rejected, malformed, missing, and unsupported fixture outcomes.

## 7. Local Report Export

Use the WP90 export layer only when a local file export is intentionally needed:

```python
from pathlib import Path

from src.data_layer.wallet_signal_candidate_review_report_export import (
    FORMAT_JSON,
    FORMAT_MARKDOWN,
    CandidateReviewReportExportResult,
    export_wallet_signal_candidate_review_report,
    candidate_review_report_export_result_to_dict,
)

output_dir = Path("local_data/candidate_review_report_exports/example_run")
export_result: CandidateReviewReportExportResult = (
    export_wallet_signal_candidate_review_report(
        report,
        output_dir,
        formats=(FORMAT_MARKDOWN, FORMAT_JSON),
    )
)
export_summary = candidate_review_report_export_result_to_dict(export_result)
```

The exporter writes fixed filenames only:

- `candidate_review_report.md`
- `candidate_review_report.json`

It writes both formats by default. It accepts an operator-selected output
directory, creates that directory if needed, overwrites deterministically, and
returns byte counts and SHA-256 checksums for the written files.

Write exports only to an operator-selected local output directory. Do not point
exports at tracked repo directories such as `docs/`, `src/`, `tests/`, `tools/`,
or `.github/`. Do not commit local export outputs unless a future approved WP
explicitly authorizes that.

## 8. Reading The Report Safely

Read the report as a local validation summary:

- `valid_records` means local fixtures passed the WP84 contract validator.
- `invalid_records` means local fixtures did not pass contract validation.
- `malformed_files` means local JSON could not be parsed as a supported record.
- `missing_or_unsupported_paths` means the operator-selected path was missing,
  URL-like, or otherwise unsupported.
- `warning_count` is a review aid only.

None of these statuses authorizes strategy design, paper trading, live trading,
order placement, account activity, candidate execution, expected-return
estimation, or position sizing.

## 9. Validation Before Use

Before relying on a local report or export, run the focused validation commands
from the repository root:

```bash
python -m pytest tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py -v
python -m pytest tests/test_wallet_signal_candidate_review_report.py -v
python -m pytest tests/test_wallet_signal_candidate_review_report_export.py -v
```

For WP evidence or PR readiness, also run the WP-required docs/status/boundary,
full-suite, and guard commands from the active WP package. Local operator report
generation does not replace repo validation.

## 10. Troubleshooting

| Symptom | Likely Cause | Safe Response |
|---|---|---|
| Missing path result | Input path does not exist | Check the local path and rerun with an explicit local file or directory. |
| Unsupported path result | Input is URL-like or not a JSON file/directory | Use a local `.json` file or a direct-child JSON directory. |
| Empty directory error | Directory has no direct-child `.json` files | Add local fixture JSON files or point at the correct directory. |
| Malformed fixture item | JSON cannot be parsed or root is not an object | Fix or remove the local fixture; do not copy raw malformed content into committed docs. |
| Rejected record | Contract validator rejected the candidate | Treat it as a local validation failure, not as a strategy conclusion. |
| Export files appear in `git status` | Output path may be tracked or not ignored | Stop, do not stage generated exports, and move them under an ignored local path. |

## 11. Known Limitations / Deferred Items

- No CLI exists for this candidate review workflow in WP93 scope.
- The workflow is import-based only.
- The exporter writes only the two fixed filenames listed above.
- The workflow does not ingest wallet data from a network or API source.
- The workflow does not monitor real wallets.
- The workflow does not produce paper strategy implementation artifacts.
- The workflow does not implement paper order models, portfolio ledgers, fill
  models, PnL computation, expected-return computation, or position sizing.
- WP90-D001 remains open for future paper strategy implementation, pending a
  separate approved WP and protected-boundary review.
- WP91-D001 and WP92-D001 remain open for any future GitHub-aware private
  evidence verifier; they do not affect local operator report generation.

## 12. Boundary Checklist

- network/API used: NO
- credentials used: NO
- account/private endpoint access: NO
- order placement/cancel: NO
- paper/live/runtime touched: NO
- scheduler/dashboard/bot loop touched: NO
- strategy promotion authority: NO
- candidate ranking for execution: NO
- expected-return/position-size computation: NO

## 13. Related Tests / Docs

Related source:

- `src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py`
- `src/data_layer/wallet_signal_candidate_review_report.py`
- `src/data_layer/wallet_signal_candidate_review_report_export.py`

Related tests:

- `tests/test_wallet_signal_paper_strategy_candidate_fixture_loader.py`
- `tests/test_wallet_signal_candidate_review_report.py`
- `tests/test_wallet_signal_candidate_review_report_export.py`
- `tests/test_runbook_docs.py`

Related repo-truth docs:

- `docs/wallet_signal_paper_strategy_contract.md`
- `docs/wallet_intelligence_research_signal_roadmap.md`
- `docs/ai/codex/REPO_TRUTH_POLICY_GUARD.md`
- `docs/status_entries/WP87.md`
- `docs/status_entries/WP89.md`
- `docs/status_entries/WP90.md`
- `docs/status_entries/WP92.md`
- `docs/status_entries/WP93.md`
