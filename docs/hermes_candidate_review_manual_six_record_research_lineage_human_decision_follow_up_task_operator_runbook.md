# Hermes Candidate-Review Manual Six-Record Research Lineage, Human Decision, And Follow-Up Task Operator Runbook

## Purpose

This runbook documents a manual, local, offline, read-only, in-memory structural review across six independently merged record contracts: WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task. It creates no product chain, factual finding, decision, task, or runtime authority.

## Position After WP138

WP138 approved this exact six-record synthetic smoke only for a separate package. WP139 supplies the separately authorized runbook and temp-only test evidence while leaving every source validator unchanged. WP132 and WP133 decision lineage is inherited through WP121 and WP122; WP123 has no direct WP132 or WP133 reference.

## Authority And Non-Authority

The operator may explicitly author six synthetic mappings, validate and build each independently, and compare sanitized fields only after all six validations succeed. The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` remains binding. No adapter, converter, bridge, mapper, transfer, chain/session/linkage product object, decision generator, task generator, source fetch, citation verification, file output, prompt/model/provider/Hermes/tool behavior, product network, storage, runtime, recommendation, probability, scoring, ranking, priority, paper/live, execution/risk/order, credential, or PR authority is granted.

## Operator Preconditions

Use a clean repository and synthetic non-real caller content only. Do not use credentials, private/account/order state, real research, or generated findings. External human review must occur before the decision is explicitly authored. Human review remains required for all six records.

## Existing WP121 Research-Question API

`src/data_layer/hermes_candidate_review_research_question_record.py` exposes `validate_candidate_review_research_question_record`, `build_candidate_review_research_question_record`, and `assert_candidate_review_research_question_record`. The smoke uses `REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS`, `REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS`, and `REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS` unchanged.

## Existing WP132 Request API

`src/data_layer/hermes_candidate_review_manual_research_request.py` exposes `validate_candidate_review_manual_research_request`, `build_candidate_review_manual_research_request`, and `assert_candidate_review_manual_research_request`. `REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS` and `REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS` remain unchanged.

## Existing WP133 Response API

`src/data_layer/hermes_candidate_review_manual_research_response.py` exposes `validate_candidate_review_manual_research_response`, `build_candidate_review_manual_research_response`, and `assert_candidate_review_manual_research_response`. `REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS` and `REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS` remain unchanged.

## Existing WP122 Validation-Receipt API

`src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py` exposes `validate_candidate_review_advisory_output_validation_receipt`, `build_candidate_review_advisory_output_validation_receipt`, and `assert_candidate_review_advisory_output_validation_receipt`. The smoke uses `REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS`, `REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS`, and `REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS` unchanged.

## Existing WP123 Human-Decision API

`src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py` exposes `validate_candidate_review_human_decision_record`, `build_candidate_review_human_decision_record`, and `assert_candidate_review_human_decision_record`. `REQUIRED_HUMAN_DECISION_RECORD_FIELDS` and `REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS` remain unchanged.

## Existing WP123 Follow-Up-Task API

The same WP123 module exposes `validate_candidate_review_follow_up_research_task_record`, `build_candidate_review_follow_up_research_task_record`, and `assert_candidate_review_follow_up_research_task_record`. `REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS` and the shared WP123 safety flags remain unchanged.

## Six-Record Manual Lineage Model

All six record fixtures are independently hard-coded zero-argument functions. All six validators and all six builders run independently. No validation or build result becomes another fixture input. The eighteen lineage checks occur only after validation and are test assertions, not a runtime contract or combined result object.

The exact seventeen helpers are `_question_preflight_flags`, `_question_safety_flags`, `_question_notice`, `_question_record`, `_request_flags`, `_request_notice`, `_request`, `_response_flags`, `_response_notice`, `_response`, `_receipt_flags`, `_receipt_notice`, `_receipt`, `_wp123_flags`, `_wp123_notice`, `_decision`, and `_follow_up_task`.

## No Adapter, Decision Generator, Or Task Generator

The six record fixtures accept zero arguments, never call or read another record fixture, and never consume another result. Matching values are explicitly and independently hard-coded. Nothing derives, copies, infers, repairs, defaults, transfers, serializes, writes, or exports lineage. The human decision is explicitly authored after external human review. The follow-up task is explicitly authored and is not generated from the decision.

## Step 1 — Construct The WP121 Record Explicitly

Supply every WP121 field directly, including preflight flags, safety flags, exact human review, and the accepted notice.

## Step 2 — Validate The WP121 Record

Call the existing WP121 validator and builder independently. Confirm exact fields, empty errors and warnings, sanitized flags, and unchanged caller input.

## Step 3 — Construct The WP132 Request Explicitly

Supply every WP132 field independently. Do not consume the WP121 fixture or result.

## Step 4 — Validate The WP132 Request

Call the existing WP132 validator and builder independently and confirm its exact contract.

## Step 5 — Perform Research Outside This Package

Any research occurs outside WP139. This package performs no prompt generation or execution, Hermes/model/provider/tool call, browsing, source fetching, citation checking, factual assessment, or finding generation.

## Step 6 — Construct The WP133 Response Explicitly

Supply every WP133 field independently. Do not consume any earlier fixture or result.

## Step 7 — Validate The WP133 Response

Call the existing WP133 validator and builder independently and confirm its exact contract.

## Step 8 — Construct The WP122 Receipt Explicitly

Supply the accepted structured legacy mappings directly. Do not consume any earlier fixture or result.

## Step 9 — Validate The WP122 Receipt

Call the existing WP122 validator and builder independently and confirm its exact contract.

## Step 10 — Perform Human Review Outside This Package

A human independently reviews the supplied material outside WP139. Validation does not perform that review or prove its quality. Only after that external review may the caller explicitly author a decision mapping.

## Step 11 — Construct The WP123 Human Decision Explicitly

Supply every decision field directly, including the caller-authored WP121 and WP122 references. Do not derive accepted findings, rejected findings, basis, unresolved questions, or follow-up summaries from another fixture.

## Step 12 — Validate The WP123 Human Decision

Call the existing WP123 decision validator and builder independently. Validation checks the individual record contract; it does not verify cross-record truth or create a decision.

## Step 13 — Construct The WP123 Follow-Up Task Explicitly

Supply every task field directly, including the caller-authored decision reference. Do not generate task content from the decision's follow-up summaries.

## Step 14 — Validate The WP123 Follow-Up Task

Call the existing WP123 task validator and builder independently. Validation checks the individual task contract; it does not prove task necessity or create a task.

## Step 15 — Perform Six-Record Lineage Review

Only after all six records validate, perform the eighteen explicit comparisons below. A mismatch stops review without repair, inference, transfer, regeneration, combined output, or file output.

## Exact Eighteen Linkage Relationships

1. WP121 `record_id` equals WP122 nested question-record ID.
2. WP121 candidate equals WP132 candidate.
3. WP121 candidate equals WP133 candidate.
4. WP121 question equals WP132 question.
5. WP121 question equals WP133 question.
6. WP121 question type equals WP132 question type.
7. WP121 question type equals WP133 question type.
8. WP132 request ID equals WP133 source-request reference.
9. WP132 briefing reference equals WP133 briefing reference.
10. WP132 required sections equal WP133 response sections.
11. Every WP133 cited source appears in WP132 approved sources.
12. WP133 response ID equals WP122 nested artifact ID.
13. WP133 cited sources equal WP122 checked sources.
14. WP121 record ID equals WP123 decision nested question-record ID.
15. WP122 receipt ID equals WP123 decision nested receipt ID.
16. WP123 decision ID equals WP123 task nested decision ID.
17. Every WP123 decision relied-on evidence reference appears in WP122 checked sources.
18. All six normalized records require `human_review_required is True`.

## Existing Six Non-Linkages

1. Response `uncertainties` differs from receipt `uncertainty_review`.
2. Response `limitations` differs from receipt `limitations_review`.
3. Response missing data differs from receipt missing-data review.
4. Response falsification content differs from receipt falsification review.
5. Response label differs from receipt label.
6. Request requirement labels are disjoint from receipt review flags.

## Additional Ten Non-Linkages

7. Response `evidence_for` differs from decision `accepted_findings`.
8. Response `evidence_against` differs from decision `rejected_findings`.
9. Receipt `unsupported_claims` differs from decision `rejected_findings`.
10. Receipt `human_review_notes` differs from decision `decision_basis`.
11. Response `uncertainties` differs from decision `unresolved_questions`.
12. Decision `follow_up_research_tasks` is not the task question.
13. Decision `follow_up_research_tasks` is not the task next-manual-step.
14. Decision label differs from task label.
15. Receipt label differs from decision label.
16. Request, response, receipt, decision, and task labels are all contract-distinct.

Research content, review evidence, human judgment, and task content remain distinct.

## Contract Validity Versus Lineage Consistency

Individual contract validity and six-record lineage consistency are separate structural questions. Factual correctness, source truth, research completeness, human-decision quality, task necessity, recommendation, probability, and readiness are not established.

## Seventeen Valid-But-Inconsistent Cases

The exact cases are `question_receipt_record_reference`, `question_to_request_candidate`, `question_to_response_candidate`, `question_to_request_text`, `question_to_response_text`, `question_to_request_type`, `question_to_response_type`, `request_response_reference`, `briefing_reference`, `response_sections`, `cited_reference_outside_request`, `response_receipt_artifact`, `receipt_checked_sources`, `question_decision_record_reference`, `receipt_decision_reference`, `decision_task_reference`, and `decision_evidence_outside_receipt`.

Each case changes exactly one relationship. `cited_reference_outside_request` co-adjusts response citations, receipt checked references, and decision relied-on evidence; `receipt_checked_sources` co-adjusts receipt checked references and decision relied-on evidence; `decision_evidence_outside_receipt` changes only decision relied-on evidence. These are explicit caller mutations, not repair or regeneration.

## Mismatch Handling

Stop review. Do not repair, infer, default, copy, transfer, regenerate, persist, export, or construct a chain/session/linkage object. All six records may remain individually valid while exactly one of the seventeen non-human-review lineage relationships is false.

## Human Review Boundary

The six failure cases select only one of question, request, response, receipt, decision, or follow-up task, set only `human_review_required` to `False`, validate only that selected record, and require an invalid result with its normalized record or receipt exactly `{}`. No peer fixture is generated and `tmp_path` remains empty.

## Unsafe No-Echo Boundary

The six unsafe cases place one forbidden authority-and-secret trap into the selected question, request, response, receipt, decision, or follow-up-task field. Each validator fails closed, the normalized surface is `{}`, the trap is absent from every public result field and `repr(result)`, the assertion exception does not echo it, and `tmp_path` remains empty.

## Source And Citation Non-Verification Boundary

All references are caller-supplied strings. Equality, sequence, membership, and subset checks do not fetch sources, verify provenance, verify citation support, prove factual correctness, or prove research completeness.

## WP123 Compatibility Caveats

WP123 contains two record families in one module, accepts caller-supplied structured references, validates required fields rather than cross-record truth, and neither verifies sources/citations nor generates decisions or tasks. WP139 does not harden WP123. A successful smoke proves structural consistency only.

## Temp-Only Synthetic Smoke Boundary

The smoke uses in-memory synthetic data. Pytest `tmp_path` is an emptiness witness only: no code writes to it, no file is written anywhere, and `tmp_path` remains empty in every runtime test.

## Cleanup And Repo Hygiene

Confirm `tmp_path` and the repository contain no generated output. Do not commit local data, security artifacts, credentials, temporary evidence drafts, or any serialized synthetic record.

## Forbidden Interpretations

This exercise is not a product chain, adapter, automatic workflow, source verification, factual finding, generated decision, generated task, recommendation, probability estimate, score/rank/priority, strategy decision, runtime service, storage path, paper/live readiness, execution/risk/order decision, credential/account operation, or PR approval.

## Future Gates

Any source hardening, adapter, chain/session/linkage object, prompt/model/tool behavior, real research, verification, persistence, runtime, or trading capability requires a separate approved work package. WP140 is not implemented here and remains separately gated.

## Non-Authority Statement

WP139 documents and temp-smoke-tests six independently authored existing records with eighteen post-validation relationships, sixteen explicit non-linkages, seventeen valid-but-inconsistent cases, six human-review failures, and six unsafe no-echo failures. It adds no repair, inference, transfer, adapter, decision/task generation, chain/session/linkage product object, source, runtime, product network, storage, paper, live, execution, risk, order, credential, recommendation, probability, scoring, ranking, priority, or PR authority.
