# Hermes Candidate-Review Manual Queue Selection To Research Question Chain Operator Runbook

## Purpose

This runbook documents a manual, local, offline, advisory-only, in-memory compatibility exercise using synthetic, non-real fixtures. It writes no output and grants no execution authority.

## Position In The WP126 → WP128 → WP121 Chain

The exact order is WP126 → WP128 → WP121: WP126 validates a candidate item and non-empty queue; WP128 validates an explicit human selection and caller-supplied research-question handoff; WP121 validates the manually assembled final research-question record.

## Operator Preconditions

Use only the existing public builders, an isolated local Python session, and synthetic non-real mappings. Confirm human review remains mandatory, the working tree is clean, and no market discovery, market-data ingestion, credentials, private state, network, Hermes runtime, provider, model, or prompt execution is involved.

## Assemble And Validate A Candidate Queue

Build one safe synthetic WP126 candidate item, then a non-empty queue containing it. Inspect the validated result in memory. Queue order is not priority and must never be transformed into scoring, ranking, recommendation, prioritization, or a priority calculation.

## Perform Explicit Human Selection

The human operator—not software—inspects the queue and explicitly selects one candidate. Manually author the WP128 selection mapping. No automatic candidate choice, auto-selection, scoring, ranking, recommendation, or priority interpretation occurs.

## Supply Proposed Research-Question Text

Question text is explicit caller input. WP128 does not generate, infer, rewrite, complete, or default question text. Missing or unsafe proposed text stops the exercise without generating anything.

## Build The WP128 Handoff

Manually assemble the WP128 handoff from the validated selection reference and caller-supplied question. Validate it in memory. Contract acceptance is structural and safety-bounded; it does not establish factual truth or approve research priority.

## Manually Assemble The WP121 Research-Question Record

WP128-to-WP121 transfer is manual. The operator explicitly maps bounded safe handoff values into a WP121 record; no automatic adapter, conversion helper, hidden bridge, parser, loader, writer, storage path, database, CLI, export, report, or persistence behavior is created.

## Validate The WP121 Record

Run the existing WP121 builder/validator on the explicit mapping and inspect its neutral result. Acceptance does not authorize implementation, strategy promotion, PR approval, merge readiness, paper/live readiness, execution, risk, orders, or trading.

## Synthetic Smoke Boundary

All fixtures are synthetic and non-real. The smoke uses only in-memory mappings and pytest `tmp_path` as an emptiness witness. No outputs are written or committed, and no discovery or ingestion occurs.

## Human Review And Non-Authority Boundary

Human review remains mandatory at selection, question drafting, transfer, and final-record review. Every record remains advisory-only. Contract-valid means neither factually correct nor recommended nor approved.

## Cleanup And Repo Hygiene

End the local session, confirm `tmp_path` remains empty, run the generated-artifact guard, and inspect the diff. Do not retain generated output, local data, private data, credentials, or temporary artifacts in the repository.

## Forbidden Interpretations

Do not interpret queue order as priority; do not infer automatic selection, recommendation, scoring, ranking, prioritization, question generation, authority through references, or automatic WP128-to-WP121 transfer. This runbook adds no Hermes runtime/provider/model/prompt execution, scheduler, dashboard, bot loop, network/API/account behavior, persistence/export/CLI, paper/live/execution/risk/order behavior, or credentials/private state.

## Future Gates

Any adapter, automation, discovery/ingestion, persistence/tooling, Hermes execution, research-priority decision, implementation, paper/live, or trading capability requires a separate approved future work package and its own human review and protected-boundary gates.

## Non-Authority Statement

This deterministic contract-compatibility runbook is manual, local, offline, advisory-only, in-memory, synthetic, and non-authoritative. It creates no automatic adapter and confers no factual, research-priority, implementation, PR-approval, merge-readiness, paper/live, execution, risk, order, or trading authority.
