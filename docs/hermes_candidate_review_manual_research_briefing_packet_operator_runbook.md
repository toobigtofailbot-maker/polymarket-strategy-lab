# Hermes Candidate-Review Manual Research Briefing Packet Operator Runbook

## Purpose

This runbook documents manual, local, offline, in-memory use of the existing WP130 API in `src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py`. It uses synthetic, non-real content, writes nothing, and grants no research, runtime, or trading authority.

## Position After WP130

Every WP130 field is explicit human/caller input, and the operator constructs the mapping manually. No WP121→WP130, WP128→WP130, or WP129→WP130 adapter exists; no reusable conversion helper exists; and no automatic population or generated default exists.

## Operator Preconditions

Use only the existing WP130 validator/build/assert API in an isolated local Python session. Use synthetic fixtures only. Do not use real market or account data, credentials or private state, a network or API, discovery or ingestion, Hermes, a model or provider, prompt execution, or any persistence tooling.

## Exact Manual Input Schema

The exact scalar fields are `briefing_id`, `source_wp_context`, `source_research_question_record_reference`, `selected_candidate_reference`, `research_question`, `research_question_type`, `resolution_rule_context`, `evidence_gap_summary`, `uncertainty_summary`, `known_missing_data`, `limitations`, `operator_research_instructions`, `operator_next_manual_step`, `created_by_operator_note`, and `non_authority_notice`. Each must be a non-empty `str`; mappings, lists, tuples, numbers, booleans, bytes, blank strings, and nested response objects are rejected.

The exact sequence fields are `source_references_to_inspect`, `falsification_checks_to_perform`, and `required_response_sections`. Each must be a non-empty `list[str]` or `tuple[str, ...]`, and every element must be a non-empty string. Empty sequences, scalar strings, nested containers, mappings, numbers, booleans, bytes, and mixed or nested response objects are rejected.

The remaining exact fields are `briefing_label`, `human_review_required`, and `safety_flags`, governed by the existing WP130 allowlists and exact flag contract. Sequence order is preserved only as operator-supplied order; it is not rank, score, recommendation, priority, or importance.

## Step 1 — Prepare Synthetic Briefing Content

Manually write safe, synthetic, non-real scalar and sequence content. The question, references, gaps, limitations, checks, instructions, and notes are all caller-authored. Do not use real market/account data, model output, generated research text, or a generated prompt.

## Step 2 — Build The Safety Flags

Construct `safety_flags` from `REQUIRED_RESEARCH_BRIEFING_PACKET_SAFETY_FLAGS`, with the exact required keys and every value exactly `True`. Flags describe boundaries; they do not grant authority.

## Step 3 — Build The Non-Authority Notice

Supply the exact bounded WP130 notice concepts: advisory only; manual; local; offline; read only; human review required; explicit caller content only; and every required non-authority exclusion. The notice must not authorize any forbidden behavior.

## Step 4 — Validate And Build The Packet

Pass the manually constructed mapping to `validate_candidate_review_manual_research_briefing_packet` or `build_candidate_review_manual_research_briefing_packet`. Use `assert_candidate_review_manual_research_briefing_packet` only when a neutral `INVALID_MANUAL_RESEARCH_BRIEFING_PACKET` exception is appropriate.

## Step 5 — Inspect The Sanitized Result

Inspect the sanitized result in memory. Confirm the output keys equal the WP130 required fields, question text and sequence order are unchanged, flags are exact, and `human_review_required` is exactly `True`. A valid packet means only that schema, labels, flags, notice, and forbidden-content gates passed. It does not establish factual correctness, source authority, research completion, conclusion, edge, recommendation, priority, implementation approval, trading approval, or PR approval.

Response-section labels request future manual research structure only. They are labels only: they contain no response text, generate no response, invoke no Hermes/model/provider, constitute no prompt, and authorize no prompt execution.

## Failure Handling

Missing fields, malformed scalar or sequence shapes, unknown authority fields, or unsafe content must fail closed with an empty packet and neutral error. Never repair, infer, generate, default, echo, persist, or forward rejected input. Human review is mandatory before any later use.

## Temp-Only Smoke Boundary

The smoke uses synthetic fixtures and pytest `tmp_path` only as an emptiness witness. `tmp_path` remains empty. No file, prompt, response, model output, export, report, or committed artifact is produced.

## No Generated Research Output

This workflow generates no question, prompt, response, conclusion, finding, recommendation, score, rank, priority, research output, or model output. It performs no prompt generation or execution and makes no model, provider, or Hermes call.

## Human Review Boundary

Human review is mandatory. Contract-valid does not mean factually correct, source-authoritative, complete, recommended, prioritized, implementation-approved, trading-approved, PR-approved, or merge-ready.

## Cleanup And Repo Hygiene

End the local session, confirm `tmp_path` and the repository contain no generated output, and run the generated-artifact guard plus diff-scope checks. Retain no credentials, private state, prompt, response, export, report, storage object, or temporary artifact.

## Forbidden Interpretations

This runbook creates no adapter or helper; no automatic population; no question/prompt/response/conclusion/finding generation; no prompt runner; no model/provider/Hermes behavior; no discovery/ingestion; no automatic selection; no scoring/ranking/priority/recommendation; no parser/loader/writer/storage/database; no CLI/export/report; no credentials/private state; no scheduler/background task/dashboard/bot loop/daemon; no paper/live/execution/risk/order; and no strategy promotion, PR approval, dependency, workflow, or lock-file authority.

## Future Gates

Any future adapter, automation, generated research capability, prompt execution, provider integration, discovery/ingestion, persistence, writer, storage, CLI, export, report, runtime, or trading capability requires a separate approved work package and its own protected-boundary review.

## Non-Authority Statement

This package is documentation and temp-only synthetic test evidence only. It grants no source, research-generation, runtime, network, credential, account, storage, export, paper, live, execution, risk, order, strategy-promotion, PR-approval, or merge-readiness authority.
