# Hermes Candidate-Review Manual Research Request-To-Response Session Chain Operator Runbook

## Purpose

This runbook documents a manual, local, offline, read-only, in-memory compatibility exercise through the independently merged WP132 request and WP133 response contracts. It creates no product output or authority.

## Position After WP134

WP134 documents manual use of the WP133 response API. WP135 now documents how a human may construct one WP132 request and, after research performed outside this package, independently construct one WP133 response before manually reviewing selected linkage fields. No source implementation changes.

## Authority And Non-Authority

The operator may construct synthetic caller mappings, call existing validators, and compare sanitized values manually. This grants no adapter, converter, bridge, transfer, prompt, model, provider, Hermes, tool, browser, source or citation verification, network, storage, runtime, paper, live, execution, risk, credential, recommendation, probability, score, rank, priority, strategy-promotion, or PR-approval authority.

## Operator Preconditions

Use synthetic non-real content in a clean repository. Use no market, account, private, credential, live-source, or generated research content. Human review remains required at every step.

## Existing WP132 Request API

The module is `src/data_layer/hermes_candidate_review_manual_research_request.py`. Its public functions are `validate_candidate_review_manual_research_request`, `build_candidate_review_manual_research_request`, and `assert_candidate_review_manual_research_request`; assertion failure is exactly `INVALID_MANUAL_RESEARCH_REQUEST`. `REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS` contains these 29 fields: `request_id`, `source_wp_context`, `source_briefing_packet_reference`, `selected_candidate_reference`, `request_label`, `research_question`, `research_question_type`, `approved_source_references`, `source_requirement_labels`, `citation_requirement_labels`, `evidence_requirement_labels`, `required_response_sections`, `research_scope`, `known_uncertainties`, `known_missing_data`, `falsification_checks_to_perform`, `operator_research_instructions`, `operator_review_instructions`, `refusal_behavior`, `failure_behavior`, `max_source_count`, `max_citation_count`, `max_output_words`, `timeout_seconds`, `max_retry_count`, `human_review_required`, `created_by_operator_note`, `non_authority_notice`, and `safety_flags`. `REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS` defines the exact required flags. The schema includes scalar strings, non-empty string sequences, five bounded integers, exact human review, and exact safety flags. All request content is explicit caller content.

## Existing WP133 Response API

The module is `src/data_layer/hermes_candidate_review_manual_research_response.py`. Its public functions are `validate_candidate_review_manual_research_response`, `build_candidate_review_manual_research_response`, and `assert_candidate_review_manual_research_response`; assertion failure is exactly `INVALID_MANUAL_RESEARCH_RESPONSE`. `REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS` contains these 30 fields: `response_id`, `source_wp_context`, `source_request_reference`, `source_briefing_packet_reference`, `selected_candidate_reference`, `response_label`, `research_question`, `research_question_type`, `question_restatement`, `source_summary`, `resolution_rule_analysis`, `evidence_for`, `evidence_against`, `source_conflicts`, `uncertainties`, `known_missing_data`, `falsification_checks_performed`, `limitations`, `what_would_change_the_conclusion`, `operator_review_notes`, `cited_source_references`, `source_assessment_labels`, `completion_labels`, `response_sections`, `operator_next_manual_step`, `reviewer_acknowledgement`, `human_review_required`, `created_by_operator_note`, `non_authority_notice`, and `safety_flags`. `REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS` defines the exact required flags. Response content is explicit caller content; no response is generated and no source or citation is verified. Contract-valid does not mean factually correct.

## Chain Model

WP132 and WP133 remain independent validators. No chain validator, no chain/session record, session object, adapter, or automatic transfer exists. The human constructs two mappings independently. After both validate, selected sanitized values are compared manually as review evidence only; the comparison grants no product or runtime authority.

## No Adapter Or Automatic Transfer

No request field is copied into the response. No converter, mapper, transfer utility, inferred default, auto-repair, chain builder, or session builder is used. The synthetic fixtures independently hard-code their values.

## Step 1 — Construct The Request Explicitly

Supply every WP132 field directly, including exact allowlist labels, five bounded integers, `human_review_required is True`, the exact safety flags, and the full non-authority notice.

## Step 2 — Validate The Request

Call only the existing WP132 validate or build function. Confirm exact fields, empty errors and warnings, unchanged caller input, exact flags, and an in-memory sanitized request. Stop neutrally on invalid input.

## Step 3 — Perform Research Outside This Package

Any human research occurs outside this repository package and runtime. WP135 does not generate or execute a prompt, invoke Hermes/model/provider/tools, fetch a source, verify a citation, or create findings.

## Step 4 — Construct The Response Explicitly

Independently supply every WP133 field. Do not pass the request mapping or request result into response construction. References and text are explicit caller content.

## Step 5 — Validate The Response

Call only the existing WP133 validate or build function. Confirm exact fields, empty errors and warnings, unchanged caller input, exact flags, and an in-memory sanitized response. Stop neutrally on invalid input.

## Step 6 — Perform Manual Linkage Review

Only after both records validate, compare the eight relationships below explicitly. A mismatch stops manual review; it creates no partial artifact, repair, inferred value, replacement, or regenerated response.

## Exact Linkage Fields

| Request field | Response field | Synthetic relationship |
|---|---|---|
| `request_id` | `source_request_reference` | exact equality |
| `source_briefing_packet_reference` | `source_briefing_packet_reference` | exact equality |
| `selected_candidate_reference` | `selected_candidate_reference` | exact equality |
| `research_question` | `research_question` | exact equality |
| `research_question_type` | `research_question_type` | exact equality |
| `required_response_sections` | `response_sections` | exact sequence equality |
| `approved_source_references` | `cited_source_references` | every cited reference appears in approved references |
| `human_review_required` | `human_review_required` | both exactly `True` |

These are WP135 smoke assertions, not a new product contract. No runtime helper enforces them and no field is copied automatically.

## Contract Validity Versus Chain Consistency

A request may be independently contract-valid and a response may be independently contract-valid while the pair remains chain-inconsistent. Contract validity does not establish chain consistency; chain consistency does not establish factual correctness, research completeness, recommendation, probability, strategy, paper readiness, live readiness, execution authority, or PR approval.

## Mismatch Handling

Stop the manual linkage review. Do not repair, infer, default, transfer, regenerate, persist, export, or create a chain/session record. Retain no partial output.

## Source And Citation Non-Verification Boundary

Approved and cited references are caller-supplied strings. Neither validator accesses a source or verifies a URL, provenance, freshness, citation support, or factual truth.

## Sequence Ordering Is Not Ranking

Preserved sequence order and synthetic sequence equality imply no score, rank, priority, confidence, importance, probability, or recommendation.

## Temp-Only Synthetic Smoke Boundary

The smoke uses synthetic fixtures, in-memory results, and pytest `tmp_path` only as an emptiness witness. It performs no file output, no network access, and no storage. No subprocess, environment, serialization, export, report, or committed artifact is produced; `tmp_path` remains empty.

## No Generated Research Output

WP135 generates no research question, prompt, response, evidence, conclusion, finding, recommendation, probability, score, rank, priority, strategy, or action.

## Human Review Boundary

Both records require `human_review_required is True`. Structural validity and linkage review never replace human source evaluation or approval.

## Failure Handling

Invalid records fail closed with empty normalized records and neutral diagnostics. Unknown/free-form metadata is rejected. Invalid caller content is not echoed, repaired, forwarded, or used to construct the other record.

## Cleanup And Repo Hygiene

Confirm `tmp_path` and the repository contain no generated output. Do not commit local data, security artifacts, credentials, or temporary files.

## Forbidden Interpretations

The exercise is not an adapter, automated workflow, factual verification, recommendation, probability estimate, score/rank/priority, strategy decision, paper/live readiness, order/execution/risk decision, credential/account operation, runtime service, persistence path, report/export, or PR approval. Terms here are normative prohibitions only.

## Future Gates

Any chain validator, session object, adapter, real research, prompt/model/Hermes/tool use, source acquisition or verification, persistence, runtime, or trading capability requires a separate approved WP.

## Non-Authority Statement

WP135 documents and tests an explicit manual two-record compatibility chain only. It grants no product, source, factual, research, recommendation, probability, scoring, ranking, priority, prompt, model, tool, network, storage, runtime, paper, live, execution, risk, credential, strategy-promotion, PR-approval, or merge-readiness authority.
