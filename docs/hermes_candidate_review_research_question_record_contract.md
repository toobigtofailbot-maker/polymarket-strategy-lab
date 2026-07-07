# Hermes Candidate-Review Research Question Record Contract

## Purpose

WP120 defines only the research question record contract for a future
manual/local/offline/advisory-only candidate-review research workflow.

WP120 is docs/status/tests-only. It authorizes no implementation, parser,
writer, schema, storage, runtime, Hermes execution, automation, trading, or
generated artifact.

This contract preserves the advisory-only nature of the Hermes-assisted
candidate-review research workflow and prevents research questions from
becoming trading instructions.

## Workflow Context

WP118 is the intake contract for manual/local/offline/advisory-only
human-reviewed selection of already-valid upstream candidate-review packets or
export artifacts.

WP119 is the operator runbook for the manual/local/offline/advisory-only
workflow after WP118 intake and before future schemas, storage, prompt
templates, or implementation.

The research question record sits after intake selection and before any manual
Hermes prompt adaptation or advisory output review. The record is a
human-authored planning surface, not a runtime object or decision engine.

## Required Future Record Fields

The following are contractual future field concepts only. WP120 does not create
a schema implementation, dataclass, parser, writer, loader, storage path,
validator, or machine-readable record object.

- `record_id`
- `source_wp_context`
- `selected_candidate_reference`
- `intake_basis`
- `research_question`
- `research_question_type`
- `evidence_references_to_check`
- `uncertainty_notes`
- `known_missing_data`
- `limitations`
- `falsification_checks_to_perform`
- `forbidden_interpretation_flags`
- `human_review_required`
- `next_manual_step`
- `created_by_operator_note`
- `non_authority_notice`

These fields are planning concepts for a future approved WP. They have no
execution authority and do not define a storage location or serialization
format.

## Allowed Research Question Types

Allowed research question types are non-executing triage families only:

- resolution-rule ambiguity;
- evidence quality gap;
- source conflict;
- wallet/signal uncertainty;
- cross-market inconsistency;
- market-structure/microstructure concern;
- stale/missing data risk;
- operator uncertainty requiring deeper research;
- source-provenance weakness;
- falsification-check need.

## Forbidden Research Question Types

The following research question types are forbidden:

- buy/sell/hold/short/trade/order/execute questions;
- expected-return questions as trade instructions;
- fair-value questions as trade instructions;
- alpha/edge questions as trade instructions;
- position sizing/allocation questions;
- paper/live/deployment readiness questions;
- execution/risk/order instructions;
- PR approval or merge readiness questions;
- credential/account/private-state access questions;
- prompt-runner/runtime/model-provider instruction questions;
- dashboard/scheduler/bot-loop instruction questions.

## Evidence and Preflight Requirements

A future research question record must require:

- upstream intake passed WP118;
- source provenance explicit;
- evidence references manually inspectable;
- uncertainty, missing data, and limitations explicit;
- no raw model/Hermes output treated as fact;
- no credentials/private/account/order/paper/live/runtime data;
- no generated artifact commit;
- no trading/readiness/approval language.

## Human Review Requirement

Human review is required for every research question record.

A research question record cannot authorize implementation, strategy
promotion, paper/live readiness, execution, risk changes, PR approval, or merge
readiness.

## Future Gates

Separate approved WPs are required for:

- concrete schema or dataclass implementation;
- parser/loader;
- writer/storage path;
- validation receipt integration;
- prompt template pack;
- manual Hermes prompt adaptation guide;
- advisory output validation receipt;
- human decision/follow-up record format;
- automation/report pipeline/dashboard;
- Hermes runtime/provider/model/prompt execution;
- paper/live/execution/risk/order/credentials/scheduler/dependency/workflow
  behavior;
- committed generated artifacts.

## Non-Authority Statement

WP120 is docs/status/tests-only and does not implement or authorize any runtime
or trading behavior. It does not create a record object, schema class, parser,
writer, loader, storage path, CLI behavior, validator change, Hermes prompt
runner, model/provider integration, automation, report pipeline, dashboard,
paper/live behavior, execution/risk/order behavior, credentials, workflow,
dependency, or generated artifact.
