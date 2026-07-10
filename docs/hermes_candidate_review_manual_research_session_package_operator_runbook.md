# Hermes Candidate-Review Manual Research Session Package Operator Runbook

## Purpose

WP125 documents manual, local, offline, advisory-only use of the already-merged WP121 through WP124 in-memory research-session chain. Human review remains required at every stage.

## Position In The WP121-WP124 Chain

The completed in-memory chain is WP121 research question record -> WP122 advisory output validation receipt -> WP123 human decision and follow-up research task records -> WP124 manual research session package. The WP124 builder is in-memory only. The package is a manual research memory surface, not storage and not an export or report artifact.

## Operator Preconditions

Use only already-valid, explicit in-memory mappings produced by the existing builders. Confirm every result is valid, contains neutral diagnostics, requires human review, and contains only manually inspected source references. Do not use real market data, account state, private state, credentials, or real Hermes/model output.

## Safe Manual Session Assembly Steps

1. Build and validate a synthetic WP121 research question record.
2. Build and validate a synthetic WP122 advisory receipt that references the question.
3. Build and validate synthetic WP123 human decision and follow-up task records.
4. Supply the sanitized record mappings to the WP124 package builder.
5. Confirm the package is valid, retains all required non-authority flags, and requires human review.
6. Discard the in-memory fixture data after the review exercise.

## Synthetic Smoke Fixture Boundary

The temp smoke uses safe, synthetic, non-real data and in-memory mappings only. It creates no file output. If a temporary path is needed, pytest `tmp_path` is the only permitted location and it must remain empty. It uses no network, subprocess, environment variables, external dependencies, prompts, Hermes runtime, parser, loader, writer, storage, CLI, export, report, or automation behavior.

## Human Review Boundary

A valid session package means only that the supplied mapping passed the deterministic WP124 in-memory contract and is ready for manual research review. Human review remains required. Validity does not establish factual truth or authorize any downstream action.

## Cleanup / Repo Hygiene

Do not commit a generated session package or any smoke output. Do not write into `local_data/` or another repository path. After testing, verify the worktree contains only the approved documentation, status, and test changes.

## Forbidden Interpretations

The package does not approve trading, strategy promotion, PR approval or merge readiness, paper or live readiness, execution, risk changes, order placement, credentials, account access, private state, Hermes runtime/provider/model/prompt runner, prompt execution, scheduler, dashboard, bot-loop, daemon or other runtime behavior, automation, parser/loader/writer/storage, CLI, export/report behavior, dependencies, workflows, lock changes, or generated artifacts.

## Future Gates

Persistence, export/report, CLI, prompt template packs, manual Hermes prompt adaptation, research queues, calibration, paper trading, live trading, credentials, schedulers, dashboards, automation, and runtime work each require a separate approved WP.

## Non-Authority Statement

WP125 adds docs/status/tests and a temp-only smoke exercise. It creates no source implementation or operational authority. The session package remains advisory-only manual research memory, and acceptance never substitutes for human review.
