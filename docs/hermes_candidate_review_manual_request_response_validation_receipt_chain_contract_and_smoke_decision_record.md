# Hermes Candidate-Review Manual Request-Response-Validation Receipt Chain Contract And Smoke Decision Record

## Purpose

WP136 records the compatibility decision for extending the merged WP135 manual request-to-response chain toward the existing WP122 advisory-output validation receipt. It defines future test-only lineage without implementing a smoke, source helper, adapter, or runtime path.

## Position After WP135

WP135 proves only an independently authored WP132 request to WP133 response chain. WP136 changes no source and does not extend that smoke. `WP136 implements no smoke`.

## Authority And Non-Authority

Authority is limited to this decision record, its Markdown-only docs test, stable status evidence, and repo-truth reconciliation. The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` remains binding: credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying, and generated artifacts are not crossed.

WP136 grants no source, helper, smoke, prompt, model, provider, Hermes, tool, browser, search, product network, storage, export, report, CLI, scheduler, runtime, recommendation, probability, scoring, ranking, priority, strategy, trading, order, position, risk, credential, paper, live, execution, PR-approval, or merge-readiness authority.

## Repository Contracts Reviewed

- WP121: `src/data_layer/hermes_candidate_review_research_question_record.py`, controlling `record_id`, `selected_candidate_reference`, `research_question`, `research_question_type`, and `human_review_required`.
- WP122: `src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py`, controlling `source_research_question_record_reference`, `advisory_output_reference`, `source_references_checked`, `receipt_label`, and `human_review_required`.
- WP132: `src/data_layer/hermes_candidate_review_manual_research_request.py`, controlling `request_id`, `source_briefing_packet_reference`, `selected_candidate_reference`, `research_question`, `research_question_type`, `approved_source_references`, `required_response_sections`, and `human_review_required`.
- WP133: `src/data_layer/hermes_candidate_review_manual_research_response.py`, controlling `response_id`, `source_request_reference`, `source_briefing_packet_reference`, `selected_candidate_reference`, `research_question`, `research_question_type`, `cited_source_references`, `response_sections`, and `human_review_required`.
- WP135: `docs/hermes_candidate_review_manual_research_request_response_session_chain_operator_runbook.md`, which owns the two-record request-to-response linkage contract only.

## Compatibility Finding

| Relationship | Existing fields | Directly compatible? | Decision |
|---|---|---:|---|
| WP121 record → WP122 question reference | `record_id` ↔ nested receipt `record_id` | YES | preserve |
| WP121 candidate → WP132 candidate | selected-candidate references | YES | compare |
| WP121 candidate → WP133 candidate | selected-candidate references | YES | compare |
| WP121 question → WP132 question | research question | YES | compare |
| WP121 question → WP133 question | research question | YES | compare |
| WP121 type → WP132 type | explicit strings | YES | compare |
| WP121 type → WP133 type | explicit strings | YES | compare |
| WP132 request → WP133 response | WP135 linkage contract | YES | preserve |
| WP133 response → WP122 advisory reference | response ID ↔ nested artifact ID | YES, explicit future fixture | compare |
| WP133 cited sources → WP122 checked sources | string sequences | YES for synthetic smoke | compare |
| WP132/WP133 → WP122 question reference without WP121 | no field | NO | prohibit |
| Briefing reference → question-record reference | different meanings | NO | prohibit |
| Request ID → question-record reference | different meanings | NO | prohibit |
| Direct three-record smoke | incomplete lineage | NO | reject |
| Four-record manual smoke | explicit complete lineage | YES, future WP | approve |

WP132 and WP133 contain no exact field that safely represents WP122's research-question-record reference.

## Direct Three-Record Smoke Decision

`Direct three-record smoke: NOT APPROVED`

The sequence `WP132 request → WP133 response → WP122 validation receipt` is incomplete because it cannot provide WP122's explicit WP121 research-question-record lineage without inventing or reinterpreting a field.

## Approved Four-Record Topology

`Required future topology: WP121 → WP132 → WP133 → WP122`

This is the only approved future topology. It is a specification for a separately approved synthetic temp-only smoke, not an implementation or runtime chain.

## Why WP121 Is Required

`WP121 research-question lineage is mandatory` because WP122 requires `source_research_question_record_reference`, and the accepted nested reference identifies a WP121 research-question record by `record_id`. Neither WP132 nor WP133 owns that identifier.

## Exact Future Linkage Contract

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
10. WP132 `required_response_sections` equals WP133 `response_sections` for the synthetic smoke.
11. Every WP133 `cited_source_references` item appears in WP132 `approved_source_references`.
12. WP133 `response_id` equals WP122 `advisory_output_reference["artifact_id"]`.
13. WP133 `cited_source_references` equals WP122 `source_references_checked` for the synthetic smoke.
14. WP121, WP122, WP132, and WP133 all require `human_review_required` exactly `True`.

These relationships are future test assertions only, not a new runtime contract.

## Explicit Non-Linkages

The following are not exact-equality lineage fields:

- WP133 `uncertainties` and WP122 `uncertainty_review`;
- WP133 `limitations` and WP122 `limitations_review`;
- WP133 `known_missing_data` and WP122 `missing_data_review`;
- WP133 `falsification_checks_performed` and WP122 `falsification_review`;
- WP133 response label and WP122 `receipt_label`;
- WP132 requirement labels and WP122 review flags.

One side contains research content while the other records review evidence. Equality would be semantic laundering, and automatic transformation is forbidden.

## No Field Reinterpretation

No field may be renamed, repurposed, or treated as “equivalent enough.” In particular, `request_id`, `source_request_reference`, `source_briefing_packet_reference`, `selected_candidate_reference`, `response_id`, and `advisory_output_reference` must never be treated as a research-question-record reference.

## WP122 Compatibility Caveats

1. WP122 predates WP132 and WP133.
2. Its accepted test fixture uses structured mappings for lineage references.
3. Its schema discipline differs from the newer WP132/WP133 contracts.
4. WP136 does not harden WP122.
5. WP136 does not add unknown-field rejection.
6. WP136 does not change result or assertion behavior.
7. A future smoke must use the existing accepted WP122 fixture shape.
8. Any source hardening requires a separate WP.

## Future WP137 Smoke Requirements

`WP137 requires separate approval`. If approved, it must use four independent zero-argument fixtures named `_question_record()`, `_request()`, `_response()`, and `_receipt()`.

No fixture helper may accept, read, or derive from another fixture or result. Values must be independently hard-coded. All four validators must run separately, with linkage assertions only after validation. The smoke must test valid-but-inconsistent cases; perform no repair, inference, transfer, or regeneration; create no chain/session/linkage object; produce no file output; and prove `tmp_path` remains empty. WP136 creates none of these fixtures or tests.

## No Adapter Or Automatic Transfer

No adapter, converter, bridge, mapper, transfer helper, chain builder, session builder, automatic population, inferred lineage, auto-repair, or generated default is authorized. No automatic transfer occurs between any record.

## Contract Validity Versus Lineage Consistency

Each validator establishes only that its own mapping is contract-valid. Cross-record equality establishes separate lineage consistency. A valid record may still be inconsistent with another valid record, and no validator result authorizes repair or regeneration.

## Source And Citation Non-Verification Boundary

The proposed comparisons preserve synthetic strings only. They do not fetch, browse, search, verify, or validate sources or citations, and they do not establish factual correctness, findings, conclusions, recommendations, probabilities, or readiness.

## Output Surface Inventory

Allowed outputs are one decision-record Markdown file, one Markdown-only docs test, one WP136 status fragment, project-status and repo-truth updates, exact compatibility registrations if required, and PR/status evidence.

Forbidden outputs include source code, a temp smoke, a validator, chain/session/linkage object, adapter, generated record, prompt/model/tool output, source/citation verification output, file/export/report output, runtime record, recommendation/probability/score/rank/priority, strategy/order/position/risk decision, and credential/account data.

## Forbidden Interpretations

Briefing, request, response, candidate, and advisory identifiers are not semantic aliases for the WP121 question-record identifier. This record does not approve automation, runtime verification, factual correctness, recommendation, probability, scoring, ranking, priority, strategy promotion, paper/live readiness, execution, risk decisions, or credentials.

## Stop Conditions

Stop if any implementation would omit WP121, reinterpret a field, copy values automatically, import all four product contracts into a WP136 test, add a temp smoke, change `src/`, create a chain/session/linkage object, verify sources or citations, write files, or cross a protected boundary.

## Future Gates

A future WP137 must receive separate approval, preserve the four-record topology, use the accepted WP122 nested mapping shape, use independent fixtures and validators, test valid-but-inconsistent records, keep output temp-only and empty, and rerun all required safety and scope gates. Any WP122 source hardening requires another separately authorized WP.

## Decision

- `Direct three-record smoke: NOT APPROVED`
- `Required future topology: WP121 → WP132 → WP133 → WP122`
- `WP121 research-question lineage is mandatory`
- `WP136 implements no smoke`
- `WP136 changes no source`
- `WP137 requires separate approval`

## Non-Authority Statement

WP136 is a documentation and decision package only. It creates no product contract object, execution authority, runtime behavior, network behavior, storage behavior, research output, factual claim, trading authority, or permission to implement WP137.
