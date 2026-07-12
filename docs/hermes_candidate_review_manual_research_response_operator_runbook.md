# Hermes Candidate-Review Manual Research Response Operator Runbook

## Purpose

This runbook describes manual, local, offline, read-only construction and inspection of one synthetic response through the merged WP133 contract. It creates no product output or authority.

## Position After WP133

WP133 provides `src/data_layer/hermes_candidate_review_manual_research_response.py`. Contract-valid means structurally valid caller input only; it does not mean research-valid or factually correct.

## Authority And Non-Authority

The operator may construct synthetic caller content and call the existing API in memory. This grants no prompt, model, provider, Hermes, tool, network, source-verification, storage, export, runtime, paper, live, execution, risk, credential, recommendation, probability, score, rank, or priority authority.

## Operator Preconditions

Use synthetic non-real content, no market/account/private data, no credentials, no live source, and a clean repository. Human review remains required.

## Exact WP133 Public API

Constants: `ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS`, `ALLOWED_RESEARCH_RESPONSE_SECTION_LABELS`, `ALLOWED_RESEARCH_SOURCE_ASSESSMENT_LABELS`, `ALLOWED_RESEARCH_COMPLETION_LABELS`, `REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS`, and `REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS`.

The frozen `HermesCandidateReviewManualResearchResponseResult` exposes exactly `is_valid`, `research_response`, `errors`, `warnings`, `response_label`, `source_assessment_labels`, `completion_labels`, `response_sections`, and `safety_flags`.

Public functions are `validate_candidate_review_manual_research_response`, `build_candidate_review_manual_research_response`, and `assert_candidate_review_manual_research_response`. Assertion failure is exactly `INVALID_MANUAL_RESEARCH_RESPONSE`. Private helpers are not public API.

## Exact Manual Input Schema

All 30 required top-level fields are: `response_id`, `source_wp_context`, `source_request_reference`, `source_briefing_packet_reference`, `selected_candidate_reference`, `response_label`, `research_question`, `research_question_type`, `question_restatement`, `source_summary`, `resolution_rule_analysis`, `evidence_for`, `evidence_against`, `source_conflicts`, `uncertainties`, `known_missing_data`, `falsification_checks_performed`, `limitations`, `what_would_change_the_conclusion`, `operator_review_notes`, `cited_source_references`, `source_assessment_labels`, `completion_labels`, `response_sections`, `operator_next_manual_step`, `reviewer_acknowledgement`, `human_review_required`, `created_by_operator_note`, `non_authority_notice`, and `safety_flags`.

No unknown top-level field is accepted. No field is populated automatically, no request object is converted, no source or citation is verified, and all content is explicit caller input. Raw/free-form mappings and `extras`, `payload`, `context`, or `metadata` are rejected and never passed through.

## Exact Scalar Fields

Each of these 15 fields must be a non-empty `str`: `response_id`, `source_wp_context`, `source_request_reference`, `source_briefing_packet_reference`, `selected_candidate_reference`, `research_question`, `research_question_type`, `question_restatement`, `source_summary`, `resolution_rule_analysis`, `operator_review_notes`, `operator_next_manual_step`, `reviewer_acknowledgement`, `created_by_operator_note`, `non_authority_notice`.

Reject `None`, number, boolean, bytes, mapping, list, tuple, set, blank string, and nested prompt, response, model/provider, or tool objects.

## Exact Sequence Fields

Each must be a non-empty `list[str]` or `tuple[str, ...]`, with every element a non-empty string: `evidence_for`, `evidence_against`, `source_conflicts`, `uncertainties`, `known_missing_data`, `falsification_checks_performed`, `limitations`, `what_would_change_the_conclusion`, `cited_source_references`, `source_assessment_labels`, `completion_labels`, `response_sections`.

Empty sequences, scalar strings, mappings, nested containers, numbers, booleans, bytes, mixed invalid elements, and nested prompt/model/tool/response objects are rejected. Caller order is preserved; there is no sorting or deduplication, and duplicate labels are invalid.

## Exact Labels

`response_label` is one exact member of `ALLOWED_MANUAL_RESEARCH_RESPONSE_LABELS`: `RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW`, `RESPONSE_INCOMPLETE_MISSING_SOURCES`, `RESPONSE_INCOMPLETE_MISSING_CITATIONS`, `RESPONSE_INCOMPLETE_EVIDENCE_CONFLICT`, `RESPONSE_INCOMPLETE_MISSING_DATA`, `RESPONSE_INCOMPLETE_FALSIFICATION_PENDING`, `RESPONSE_REJECTED_UNSAFE_OR_FORBIDDEN_CONTENT`, or `RESPONSE_DEFERRED_PENDING_OPERATOR_ACTION`.

Source-assessment, completion, and response-section values come only from their public allowlist constants. They are caller-recorded structure, do not verify sources, contain no generated section content, and establish no correctness, approval, recommendation, or readiness.

## Exact Safety Flags

Build `{flag: True for flag in REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS}`. Every flag must be present and exactly `True`; `1`, `"true"`, false, null, and missing values are invalid. Safe extras are sanitized away; unsafe extras fail closed. Flags are boundaries, not authority grants.

## Step 1 — Prepare Synthetic Response Content

Write every scalar and sequence explicitly using synthetic content only. Use no real market/account/private data, credential, live source, model output, generated response, or copied unsafe metadata.

## Step 2 — Select Structural Labels

Select exact allowlist labels with no duplicate or invented label. Labels are structure only and never approval or recommendation.

## Step 3 — Build The Safety Flags

Use the merged required-flags constant and exact boolean `True`; infer no permission.

## Step 4 — Build The Non-Authority Notice

Supply a notice containing every WP133 negative concept: advisory only; manual, local, offline, read only; human review required; explicit caller content only; response contract only; and not prompt generation/execution, model/provider, Hermes, tool selection/invocation, network/API, source fetching/verification, citation verification, market-data ingestion, discovery automation, automated selection, scoring/ranking, priority calculation, recommendation, probability estimation, factual correctness/conclusion, strategy, execution, risk, credentials, paper/live, strategy promotion, PR approval, storage/writer, export/report, CLI, or scheduler/background task. It is caller-supplied, grants no authority, and must contain no permission, verification, correctness, recommendation, or readiness claim. Do not infer or rebuild it with a product helper.

## Step 5 — Validate Or Build The Response

Call only `validate_candidate_review_manual_research_response` or `build_candidate_review_manual_research_response`. Create no other product helper.

## Step 6 — Inspect The Sanitized Result

Confirm validity, the exact field set, unchanged caller text and order, reconstructed flags, `human_review_required is True`, and no unknown or recommendation/probability/score/rank/priority/prompt/model/tool/execution output.

## Step 7 — Use The Assert Helper Only For Neutral Failure

Use `assert_candidate_review_manual_research_response` only for exact neutral failure. `INVALID_MANUAL_RESEARCH_RESPONSE` never includes caller content.

## Failure Handling

On invalid input stop: do not repair, infer, default, generate, echo, persist, export, forward, retry through a model, fetch sources, or create a partial record. Human review precedes any later action.

## Source And Citation Non-Verification Boundary

`cited_source_references` and source-assessment labels are caller-supplied strings/labels. The validator accesses no source and confirms no URL, provenance, freshness, citation support, or factual truth. Contract-valid does not mean research-valid.

## Sequence Ordering Is Not Ranking

Preserved order implies no score, rank, priority, confidence, importance, probability, or recommendation.

## Temp-Only Synthetic Smoke Boundary

The smoke uses synthetic fixtures and `tmp_path` only as an emptiness witness. It uses no real URL or credential, no network, no subprocess, no environment variable, no serialization, no file output, and no committed artifact; `tmp_path` remains empty.

## No Adapter Or Automatic Field Transfer

No WP132→WP133 or WP130→WP133 adapter, request/briefing converter, reusable field-transfer helper, automatic population, or generated default exists. References remain explicit strings and the operator manually constructs the entire mapping.

## No Generated Research Output

This process generates no question, prompt, response, evidence, conclusion, finding, recommendation, probability, score, rank, or priority.

## Human Review Boundary

Structural validity never replaces human review, approval, source evaluation, or later separately authorized action.

## Cleanup And Repo Hygiene

Create no output file. Confirm the temporary directory and repository are free of generated output and do not commit local/security artifacts.

## Forbidden Interpretations

The record is not buy/sell/hold/short, trade/order, entry/exit, stop-loss/take-profit, position sizing/allocation, bet/wager, edge/alpha/fair-value/expected-return/ROI/PnL, probability, readiness, approval, recommendation, credential/account state, prompt/model/Hermes/tool behavior, automation, persistence, report, export, CLI, paper/live, execution, or risk output. Such terms appear here only as normative prohibitions.

## Future Gates

Any adapter, real research, source acquisition/verification, prompt/model/Hermes/tool use, network, persistence, runtime, or trading capability requires a separate approved WP.

## Non-Authority Statement

WP134 documents and tests manual use of WP133 only. It grants no product, factual, research, recommendation, probability, scoring, ranking, priority, prompt, model, tool, network, storage, runtime, paper, live, execution, risk, credential, PR-approval, or merge-readiness authority.
