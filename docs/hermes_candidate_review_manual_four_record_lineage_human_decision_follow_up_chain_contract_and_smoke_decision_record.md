# Hermes Candidate-Review Manual Four-Record Lineage To Human Decision And Follow-Up Chain Contract And Smoke Decision Record

## Purpose

WP138 records whether the merged WP137 four-record manual research lineage can extend through the existing WP123 human-decision and follow-up-task records without changing source or reinterpreting fields. This is a compatibility decision for a separately approved future synthetic smoke, not that smoke's implementation.

## Position After WP137

WP137 independently validates and smoke-tests the explicit `WP121 → WP132 → WP133 → WP122` four-record lineage. WP138 relies on that proven chain and evaluates only the existing WP123 reference surfaces. `WP138 implements no smoke`. `WP138 changes no source`.

## Authority And Non-Authority

Authority is limited to this decision record, a Markdown-only docs test, a stable WP138 status fragment, repo-truth reconciliation, and exact status-test registration. The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` remains binding.

No chain validator, session object, adapter, or automatic transfer is authorized. WP138 grants no source, temp-smoke, six-record product test, prompt, model, provider, Hermes, tool, browser, search, product network, storage, export, report, CLI, scheduler, background task, runtime, recommendation, probability, score, rank, priority, strategy, trading, order, position, risk, credential, account, paper, live, execution, PR-approval, or merge authority.

## Repository Contracts Reviewed

- WP121: `src/data_layer/hermes_candidate_review_research_question_record.py`, including `ALLOWED_RESEARCH_QUESTION_TYPES`, `REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS`, `REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS`, `REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS`, `HermesCandidateReviewResearchQuestionRecordResult`, `validate_candidate_review_research_question_record`, `build_candidate_review_research_question_record`, and `assert_candidate_review_research_question_record`.
- WP122: `src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py`, including its explicit research-question reference, advisory-output reference, checked-source references, and human-review requirement.
- WP123: `src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py`.
  - Human-decision public surface: `ALLOWED_HUMAN_DECISION_LABELS`, `REQUIRED_HUMAN_DECISION_RECORD_FIELDS`, `REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS`, `HermesCandidateReviewHumanDecisionRecordResult`, `validate_candidate_review_human_decision_record`, `build_candidate_review_human_decision_record`, and `assert_candidate_review_human_decision_record`.
  - Follow-up-task public surface: `ALLOWED_FOLLOW_UP_TASK_LABELS`, `REQUIRED_FOLLOW_UP_RESEARCH_TASK_RECORD_FIELDS`, `REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS`, `HermesCandidateReviewFollowUpResearchTaskRecordResult`, `validate_candidate_review_follow_up_research_task_record`, `build_candidate_review_follow_up_research_task_record`, and `assert_candidate_review_follow_up_research_task_record`.
- WP132: `src/data_layer/hermes_candidate_review_manual_research_request.py`.
- WP133: `src/data_layer/hermes_candidate_review_manual_research_response.py`.
- WP136: `docs/hermes_candidate_review_manual_request_response_validation_receipt_chain_contract_and_smoke_decision_record.md`.
- WP137: `docs/hermes_candidate_review_manual_research_question_request_response_validation_receipt_four_record_chain_operator_runbook.md` and its temp-only synthetic smoke.

## Compatibility Finding

| Relationship | Existing fields | Directly compatible? | Decision |
|---|---|---:|---|
| Existing WP121→WP132→WP133→WP122 lineage | WP137 fourteen relationships | YES | preserve |
| WP121 question → WP123 decision | `record_id` ↔ nested decision `record_id` | YES | compare |
| WP122 receipt → WP123 decision | `receipt_id` ↔ nested decision `receipt_id` | YES | compare |
| WP123 decision → WP123 follow-up task | `decision_id` ↔ nested task `decision_id` | YES | compare |
| Receipt checked sources → decision relied-on evidence | string collections | YES for synthetic smoke | subset check |
| WP132 request → WP123 decision | no direct field | NO | do not invent |
| WP133 response → WP123 decision | no direct field | NO | inherit through WP122 only |
| Response findings → accepted/rejected findings | different semantics | NO | prohibit equality |
| Receipt review text → decision basis | different semantics | NO | prohibit copying |
| Decision follow-up summaries → task question | different semantics | NO | prohibit automatic transformation |
| Direct six-record manual smoke | complete explicit lineage | YES, future WP only | approve |
| Source/runtime implementation | outside scope | NO | exclude |

The direct compatibility answers are: WP121 question record to WP123 decision: YES; WP122 validation receipt to WP123 decision: YES; WP123 decision to WP123 follow-up task: YES; WP132 request to WP123 decision: NO; WP133 response to WP123 decision: NO.

## Six-Record Future Smoke Decision

`Six-record future smoke: APPROVED FOR A SEPARATE WP`

Approval is limited to an independently authored, test-only, temp-only synthetic smoke in WP139 or another separately approved package. It creates no present implementation authority.

## Approved Six-Record Topology

`Required future topology: WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task`

The six records are the WP121 research-question record, WP132 manual research request, WP133 manual research response, WP122 advisory-output validation receipt, WP123 human decision record, and WP123 follow-up research task record.

## Direct And Inherited Lineage

Direct lineage consists only of WP121 → WP123 decision, WP122 → WP123 decision, and WP123 decision → WP123 follow-up task. The decision uses its explicit `source_research_question_record_reference` and `source_advisory_output_validation_receipt_reference`; the task uses its explicit `source_human_decision_reference`.

`WP132 and WP133 lineage is inherited through WP121 and WP122`. WP132 and WP133 reach the human decision only through the independently proven WP137 four-record chain. WP123 does not directly validate or reference WP132. WP123 does not directly validate or reference WP133.

## Exact Future Eighteen Linkage Relationships

For a future independently authored synthetic smoke only:

1. WP121 `record_id` equals WP122 `source_research_question_record_reference["record_id"]`.
2. WP121 `selected_candidate_reference` equals WP132 `selected_candidate_reference`.
3. WP121 `selected_candidate_reference` equals WP133 `selected_candidate_reference`.
4. WP121 `research_question` equals WP132 `research_question`.
5. WP121 `research_question` equals WP133 `research_question`.
6. WP121 `research_question_type` equals WP132 `research_question_type`.
7. WP121 `research_question_type` equals WP133 `research_question_type`.
8. WP132 `request_id` equals WP133 `source_request_reference`.
9. WP132 `source_briefing_packet_reference` equals WP133 `source_briefing_packet_reference`.
10. WP132 `required_response_sections` equals WP133 `response_sections`.
11. Every WP133 `cited_source_references` item appears in WP132 `approved_source_references`.
12. WP133 `response_id` equals WP122 `advisory_output_reference["artifact_id"]`.
13. WP133 `cited_source_references` equals WP122 `source_references_checked` for the synthetic smoke.
14. WP121 `record_id` equals WP123 decision `source_research_question_record_reference["record_id"]`.
15. WP122 `receipt_id` equals WP123 decision `source_advisory_output_validation_receipt_reference["receipt_id"]`.
16. WP123 decision `decision_id` equals WP123 follow-up task `source_human_decision_reference["decision_id"]`.
17. Every WP123 decision `evidence_references_relied_on` item appears in WP122 `source_references_checked` for the synthetic smoke.
18. WP121, WP122, WP132, WP133, WP123 decision, and WP123 follow-up task all require `human_review_required is True`.

These are future test-only relationships, not a runtime contract.

## Explicit Non-Linkages

Exact equality and automatic transformation are prohibited between:

- WP133 `evidence_for` and WP123 `accepted_findings`;
- WP133 `evidence_against` and WP123 `rejected_findings`;
- WP122 `unsupported_claims` and WP123 `rejected_findings`;
- WP122 `human_review_notes` and WP123 `decision_basis`;
- WP133 `uncertainties` and WP123 `unresolved_questions`;
- WP123 decision `follow_up_research_tasks` and task `task_question`;
- WP123 decision `follow_up_research_tasks` and task `next_manual_step`;
- WP123 decision label and WP123 follow-up task label;
- WP122 receipt label and WP123 decision label;
- WP132 or WP133 labels and any WP123 label.

Research content is not human judgment, receipt review evidence is not the human decision, a decision summary is not a task object, and the labels have different contract semantics.

## No Field Reinterpretation

Request ID is not a decision reference. Response ID is not a decision reference. A briefing reference is not a decision reference. Receipt review notes are not decision basis. Response evidence is not accepted findings. A decision task summary is not task question. A receipt label is not a decision label. A decision label is not a task label.

No field is renamed, repurposed, inferred, copied automatically, or treated as equivalent enough to create lineage.

## WP123 Compatibility Caveats

1. WP123 contains two public record families in one module.
2. WP123 accepts caller-supplied structured mappings for lineage references.
3. WP123 validates required fields but does not create cross-record lineage.
4. WP123 does not verify source/citation truth.
5. WP123 does not create tasks automatically.
6. WP123 does not transform decision summaries into task content.
7. WP138 does not harden WP123.
8. A future source-hardening package requires separate approval.
9. A successful future smoke would prove structural lineage only.

## Future WP139 Smoke Requirements

`WP139 requires separate approval`. A future smoke must use six independently authored zero-argument fixtures named `_question_record()`, `_request()`, `_response()`, `_receipt()`, `_decision()`, and `_follow_up_task()`.

No fixture may accept, call, read, or derive from another record fixture or result. Matching values must be independently hard-coded. All six validators must run independently before the eighteen linkage assertions. The smoke must prove individually valid records can remain lineage-inconsistent, repair no mismatch, create no chain/session/linkage object, write no file, and leave `tmp_path` empty.

## No Adapter Or Automatic Transfer

No decision generator, task generator, adapter, converter, bridge, mapper, transfer helper, chain builder, session builder, automatic population, inferred lineage, auto-repair, or generated default is authorized. No decision or task content is generated or transferred automatically.

## Contract Validity Versus Lineage Consistency

Individual record validity, existing four-record lineage consistency, decision-reference consistency, follow-up-task-reference consistency, and six-record lineage consistency are separate properties. Factual correctness, research completeness, human approval meaning, and recommendation/readiness are not established by any of them.

A future smoke must prove that individually valid records can remain lineage-inconsistent. Validation never repairs or infers a cross-record relationship.

## Source And Citation Non-Verification Boundary

WP121 evidence references are caller-supplied. WP132 approved references are caller-supplied. WP133 cited references are caller-supplied. WP122 checked references are caller-supplied. WP123 relied-on references are caller-supplied. WP123 task references are caller-supplied.

Equality and subset checks do not verify sources. Human decision validity does not prove factual correctness. Follow-up-task validity does not prove task necessity. WP138 performs no source fetching, source verification, citation verification, browsing, or search.

## Output Surface Inventory

Allowed outputs are this decision-record Markdown file, one focused Markdown-only docs test, one stable WP138 status fragment, project-status and repo-truth updates, exact docs/status/test registrations, and PR/status evidence.

Forbidden outputs include source code, a temp smoke, a six-record product test, chain/session/linkage object, adapter, generated decision, generated follow-up task, prompt/model/tool output, source/citation verification output, file/export/report output, runtime record, recommendation/probability/score/rank/priority output, strategy/order/position/risk decision, and credential/account data.

## Forbidden Interpretations

Semantic relabeling; automatic population; adapters, converters, bridges, mappers, transfer helpers, chain/session builders, inference, repair, or defaults; prompt/model/provider/Hermes/tool behavior; browser/search/source fetching or verification; scheduler/background behavior; storage/export/report/CLI; recommendation, probability, score/rank/priority, edge/alpha/return; trade/order, paper/live readiness, execution/risk override, strategy promotion, or PR approval/merge authority are forbidden.

## Stop Conditions

Stop if implementation would change `src/`, add a temp smoke, reinterpret or automatically copy a field, generate a decision or task, create a chain/session/linkage object, weaken a guard, verify sources or citations, write files, cross a protected boundary, or implement WP139.

## Future Gates

WP139 requires its own approval, branch, PR, independent fixtures, all eighteen post-validation comparisons, valid-but-inconsistent coverage, empty-temp-directory proof, exact no-source/no-runtime boundaries, full validation, and evidence re-fetch. Any WP123 source hardening requires a different separately approved package.

## Decision

- `Six-record future smoke: APPROVED FOR A SEPARATE WP`
- `Required future topology: WP121 → WP132 → WP133 → WP122 → WP123 decision → WP123 follow-up task`
- `WP132 and WP133 lineage is inherited through WP121 and WP122`
- `WP138 implements no smoke`
- `WP138 changes no source`
- `WP139 requires separate approval`
- `No chain validator, session object, adapter, or automatic transfer is authorized`

## Non-Authority Statement

WP138 is a documentation and compatibility-decision package only. It adds no source or smoke, performs no source or citation verification, creates no decision or task, and grants no runtime, model, tool, product-network, storage, trading, paper, live, execution, risk, credential, recommendation, probability, scoring, ranking, priority, or PR authority.
