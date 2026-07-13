# Hermes Candidate-Review Manual Research Question-Request-Response-Validation Receipt Four-Record Chain Operator Runbook

## Purpose

This runbook documents a manual, local, offline, read-only, in-memory compatibility exercise across the independently merged WP121, WP132, WP133, and WP122 contracts. It creates no product contract or runtime authority.

## Position After WP136

WP136 rejected an incomplete WP132 → WP133 → WP122 smoke and required the exact test-only topology `WP121 → WP132 → WP133 → WP122`. WP137 implements only the separately authorized documentation and synthetic smoke evidence.

## Authority And Non-Authority

The operator may explicitly construct four synthetic mappings, validate each independently, and compare sanitized values after validation. The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md` remains binding. No source, adapter, converter, bridge, mapper, transfer, chain/session/linkage product object, prompt/model/provider/Hermes/tool behavior, browser/search, product network, storage, runtime, recommendation, probability, scoring, ranking, priority, paper/live, execution/risk/order, credential, or PR-approval authority is granted.

## Operator Preconditions

Use a clean repository and synthetic non-real caller content only. Do not use credentials, private/account/order state, real research, or generated findings. Human review remains required for every record.

## Existing WP121 Research-Question API

`src/data_layer/hermes_candidate_review_research_question_record.py` exposes `validate_candidate_review_research_question_record`, `build_candidate_review_research_question_record`, and `assert_candidate_review_research_question_record`. Its controlling constants are `ALLOWED_RESEARCH_QUESTION_TYPES`, `REQUIRED_RESEARCH_QUESTION_RECORD_FIELDS`, `REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS`, and `REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS`.

## Existing WP132 Request API

`src/data_layer/hermes_candidate_review_manual_research_request.py` exposes `validate_candidate_review_manual_research_request`, `build_candidate_review_manual_research_request`, and `assert_candidate_review_manual_research_request`. `REQUIRED_MANUAL_RESEARCH_REQUEST_FIELDS` and `REQUIRED_MANUAL_RESEARCH_REQUEST_SAFETY_FLAGS` remain unchanged.

## Existing WP133 Response API

`src/data_layer/hermes_candidate_review_manual_research_response.py` exposes `validate_candidate_review_manual_research_response`, `build_candidate_review_manual_research_response`, and `assert_candidate_review_manual_research_response`. `REQUIRED_MANUAL_RESEARCH_RESPONSE_FIELDS` and `REQUIRED_MANUAL_RESEARCH_RESPONSE_SAFETY_FLAGS` remain unchanged.

## Existing WP122 Validation-Receipt API

`src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py` exposes `validate_candidate_review_advisory_output_validation_receipt`, `build_candidate_review_advisory_output_validation_receipt`, and `assert_candidate_review_advisory_output_validation_receipt`. Its controlling constants are `ALLOWED_RECEIPT_LABELS`, `REQUIRED_ADVISORY_OUTPUT_VALIDATION_RECEIPT_FIELDS`, `REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS`, and `REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS`.

## Four-Record Lineage Model

All four records are explicit caller content. Each zero-argument record fixture is independently hard-coded and each validator runs independently. The fourteen comparisons occur only after all four validations succeed; they are test assertions, not a runtime contract.

## No Adapter Or Automatic Transfer

The exact private helpers are `_question_preflight_flags`, `_question_safety_flags`, `_question_notice`, `_question_record`, `_request_flags`, `_request_notice`, `_request`, `_response_flags`, `_response_notice`, `_response`, `_receipt_flags`, `_receipt_notice`, and `_receipt`. The four record fixtures accept zero arguments, do not call or read another record fixture or result, and do not derive, copy, infer, repair, regenerate, serialize, write, or export lineage.

## Step 1 — Construct The WP121 Record Explicitly

Supply every WP121 field directly, including its preflight flags, safety flags, exact human review, and accepted notice.

## Step 2 — Validate The WP121 Record

Call only the existing WP121 validate/build API. Confirm exact fields, neutral empty errors and warnings, sanitized flags, and unchanged input.

## Step 3 — Construct The WP132 Request Explicitly

Supply every WP132 field independently. Do not consume the WP121 fixture or result.

## Step 4 — Validate The WP132 Request

Call only the existing WP132 validate/build API and confirm its exact contract independently.

## Step 5 — Perform Research Outside This Package

Any research occurs outside WP137. This package performs no prompt generation or execution, Hermes/model/provider/tool call, browsing, source fetching, citation checking, or finding generation.

## Step 6 — Construct The WP133 Response Explicitly

Supply every WP133 field independently. Do not consume the WP121 or WP132 fixtures or results.

## Step 7 — Validate The WP133 Response

Call only the existing WP133 validate/build API and confirm its exact contract independently.

## Step 8 — Construct The WP122 Receipt Explicitly

Supply the accepted structured legacy mappings directly. Do not consume any earlier fixture or result.

## Step 9 — Validate The WP122 Receipt

Call only the existing WP122 validate/build API and confirm its exact contract independently.

## Step 10 — Perform Four-Record Lineage Review

Only after all four records validate, perform each explicit equality, sequence, membership, and exact-true check below. A mismatch stops review without repair or output.

## Exact Fourteen Linkage Relationships

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
13. WP133 `cited_source_references` equals WP122 `source_references_checked`.
14. WP121, WP122, WP132, and WP133 all require `human_review_required` exactly `True`.

## Explicit Non-Linkages

Do not equate or transform WP133 `uncertainties` and WP122 `uncertainty_review`; WP133 `limitations` and WP122 `limitations_review`; WP133 `known_missing_data` and WP122 `missing_data_review`; WP133 `falsification_checks_performed` and WP122 `falsification_review`; the WP133 response label and WP122 receipt label; or WP132 requirement labels and WP122 review flags. Research content is not review evidence.

## Contract Validity Versus Lineage Consistency

Individual contract validity and four-record lineage consistency are separate structural questions. Factual correctness, research completeness, recommendation, and readiness are not established. The thirteen mismatch cases are `question_record_reference`, `question_to_request_candidate`, `question_to_response_candidate`, `question_to_request_text`, `question_to_response_text`, `question_to_request_type`, `question_to_response_type`, `request_reference`, `briefing_reference`, `response_sections`, `cited_reference_outside_request`, `response_receipt_artifact`, and `receipt_checked_sources`.

## Mismatch Handling

Stop review. Do not repair, infer, default, copy, transfer, regenerate, persist, export, or construct a chain/session/linkage object. Contract-valid records may remain lineage-inconsistent.

## Source And Citation Non-Verification Boundary

All references are caller-supplied strings. Equality and membership do not fetch sources, verify provenance, verify citation support, or establish factual correctness.

## WP121 And WP122 Compatibility Caveats

WP121 and WP122 predate WP132 and WP133; their fixture shapes and schema strictness differ. WP137 uses a safe scalar `selected_candidate_reference` accepted by the current WP121 validator and the accepted WP122 structured reference mappings. It does not harden or redefine either contract. Source hardening requires a separate approved WP, and a successful smoke does not approve legacy schema quality.

## Temp-Only Synthetic Smoke Boundary

The smoke uses in-memory synthetic data and pytest `tmp_path` only as an emptiness witness. It performs no file output, serialization, storage, network, subprocess, or export; `tmp_path` remains empty.

## Human Review Boundary

The four invalid cases set WP121, WP122, WP132, or WP133 human review false. Each modified record fails closed with an empty normalized record or receipt, no lineage review, no generated peer record, and no file output.

## Failure Handling

The four no-echo cases place `NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_TOOL_CALL_STORAGE_PATH_MODEL_CALL_PROBABILITY_ESTIMATE` into one record at a time. Each fails closed; the trap is absent from the result and assertion exception, and no file is written.

## Cleanup And Repo Hygiene

Confirm `tmp_path` and the repository contain no generated output. Do not commit local data, security artifacts, credentials, or temporary evidence drafts.

## Forbidden Interpretations

This exercise is not a product chain, adapter, automated workflow, factual verification, recommendation, probability estimate, score/rank/priority, strategy decision, runtime service, storage path, paper/live readiness, execution/risk/order decision, credential/account operation, or PR approval.

## Future Gates

Any source hardening, chain object, adapter, prompt/model/tool behavior, real research, verification, persistence, runtime, or trading capability requires a separate approved work package. WP138 is not implemented here.

## Non-Authority Statement

WP137 documents and smoke-tests independently authored WP121 → WP132 → WP133 → WP122 manual lineage only. It adds no source, adapter, runtime, product network, storage, research, factual, recommendation, probability, scoring, ranking, priority, paper, live, execution, risk, order, credential, or PR-approval authority.
