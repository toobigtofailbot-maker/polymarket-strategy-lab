# Hermes Candidate-Review Research Candidate Queue Operator Runbook

## Purpose

WP127 documents safe manual use of the WP126 research candidate queue contract. This runbook is manual, local, offline, and advisory-only. It creates no operational authority.

## Position After WP126

WP126 provides deterministic in-memory builders and validators for one candidate queue item and a non-empty queue package. WP127 adds operator guidance and a temp-only synthetic smoke exercise; it does not modify that source module.

## Operator Preconditions

- Work with explicit in-memory mappings only.
- Use synthetic, non-real fixture data only for the smoke test.
- Confirm every required safety flag is exactly `True` and `human_review_required` is exactly `True`.
- Inspect every supplied field before passing it to the WP126 builder.
- Stop if the proposed exercise needs real market data, real account/private state, credentials, model output, persistence, or any automated input.

## Safe Manual Candidate Item Assembly

1. Create a new mapping containing every required WP126 candidate item field.
2. Use an allowed candidate label and one or more allowed reason labels.
3. Keep summaries, evidence references, limitations, uncertainty, and the next step synthetic and neutral.
4. Include the complete non-authority notice and exact safety flags.
5. Call `build_candidate_review_research_candidate_queue_item` and inspect the result without writing it anywhere.

## Safe Manual Queue Package Assembly

1. Create a new mapping containing every required WP126 queue package field.
2. Put at least one already-inspected valid candidate item mapping in `candidate_items`.
3. Use an allowed queue label, the complete non-authority notice, and exact safety flags.
4. Call `build_candidate_review_research_candidate_queue_package` and inspect the result in memory.
5. Treat acceptance only as deterministic contract acceptance of the supplied mapping.

## Synthetic Smoke Fixture Boundary

The smoke test uses safe synthetic non-real fixture data and explicit in-memory mappings only. Pytest `tmp_path` is used solely to prove it remains empty. The exercise creates no file output and invokes no storage, export, report, CLI, automation, prompt execution, runtime behavior, network/API/product/account behavior, credentials, account access, paper/live behavior, execution, risk, orders, market discovery, market data ingestion, scoring, or ranking.

## Human Review Boundary

Human review remains required. Valid queue output means only that the deterministic queue contract accepted the supplied mapping. It does not rank opportunities, identify edges, authorize research priority, approve trading, establish factual truth, or approve any downstream action.

## Cleanup / Repo Hygiene

Discard synthetic mappings after the exercise. Generated outputs must not be committed. Do not write to `local_data/` or any repository path. Confirm the temporary directory remains empty and the worktree contains only approved WP127 files.

## Forbidden Interpretations

WP127 does not create file output, storage, export, report, CLI, automation, discovery, ingestion, scoring, ranking, prompt execution, Hermes runtime/provider/model/prompt-runner behavior, network/API/product/account behavior, credentials/private state, account access, paper/live behavior, execution, risk, orders, scheduler, dashboard, bot-loop, or daemon authority. Contract acceptance is not strategy promotion, PR approval, merge readiness, research-priority authorization, or trading approval.

## Future Gates

Any persistence, export/report, CLI, prompt execution, Hermes runtime, automation, discovery, ingestion, scoring/ranking, credential, account, paper/live, execution, risk, order, scheduler, dashboard, bot-loop, or daemon work requires a separate approved work package.

## Non-Authority Statement

WP127 is docs/status/tests plus a temp-only smoke exercise. It uses the existing WP126 deterministic contract with explicit in-memory synthetic mappings and grants no source implementation, runtime, storage, automation, research-priority, or trading authority.
