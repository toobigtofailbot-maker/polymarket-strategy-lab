# Hermes Candidate-Review Local Manual Export CLI Smoke Receipt

## Purpose

WP116 records a docs/status/tests-only smoke receipt for the WP115 local
manual export CLI wrapper. WP116 adds no implementation and does not modify
`tools/hermes_candidate_review_manual_export_cli.py`.

## Receipt

The existing WP115 focused tests already prove the CLI command path is coherent
under pytest `tmp_path`: a strict WP108 artifact-result JSON envelope can be
loaded from a temp local JSON file and exported through the WP109 writer to a
temp local `.md` or `.txt` path.

WP116 adds operator-facing documentation and focused docs/status tests for that
path. It does not commit generated artifact content, does not add a report
pipeline, and does not create new CLI behavior.

## Boundary

The smoke receipt is documentation only. It adds no source implementation under
`src/`, no CLI implementation change under `tools/`, no Hermes runtime/provider/
model/prompt runner behavior, no product/runtime/API/account network behavior,
no credentials/private state, no paper/live behavior, no execution/risk/order
behavior, no scheduler/dashboard/bot-loop behavior, no dependency/workflow/
lock-file changes, and no committed generated artifacts.
