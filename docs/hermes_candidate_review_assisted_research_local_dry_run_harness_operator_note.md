# Hermes Candidate-Review Assisted Research Local Dry-Run Harness Operator Note

## Purpose

WP145 provides one bounded local/offline test-oriented controller skeleton for
exercising one existing synthetic WP142 case through an already-materialized
in-memory synthetic response,
the existing deterministic WP133 validator, explicit human review, sanitized
evidence, and mandatory teardown. It is a dry-run harness only.

## Position After WP144

WP144 is merged and remains the controlling harness contract and no-provider
dry-run plan. WP145 implements only the separately approved local skeleton and
test boundary. WP141 remains the provider-neutral experiment contract, WP142
remains the immutable synthetic case/rubric source, and WP143 remains the
architecture and upper-bound decision. No remote experiment is activated.

## What WP145 Implements

Harness implementation status: LOCAL_OFFLINE_TEST_ORIENTED_SKELETON

Controller authority: LOCAL_DETERMINISTIC_EXCLUSIVE

Adapter status: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE

Dry-run case count: 1

Dry-run case ID: GC-P01-COMPLETE-SUPPORTED

Network: FORBIDDEN

Credentials: FORBIDDEN

Hermes installation/invocation: FORBIDDEN

Provider/model call: FORBIDDEN

Stable raw input/output persistence: FORBIDDEN

Temporary filesystem: PYTEST_TMP_PATH_ONLY

Output: SANITIZED_EVIDENCE_ONLY

Deterministic WP133 validation: MANDATORY

Human review: EXPLICIT_CALLER_SUPPLIED_ACKNOWLEDGEMENT_REQUIRED

Automatic downstream records: FORBIDDEN

Paper/live/execution authority: FORBIDDEN

WP146 requires separate approval

The source module exposes the exact input validator, immutable envelope
builder, one-run controller, and sanitized-result assertion helper authorized
by WP145. It has no background behavior or mutable global state.

## What WP145 Does Not Implement

WP145 does not install or invoke Hermes, select or call a provider/model, read
credentials, access a network, fetch or verify sources, create an executable
prompt/configuration artifact, add a provider SDK, load the WP142 fixture from
source code, run more than one case, write files, persist raw input/output,
create WP122/WP123 or other downstream records, or create recommendation,
probability, ranking, strategy, paper/live, execution, risk, order, or trading
behavior.

## Exact One-Case Dry Run

The smoke test reads the existing WP142 JSON fixture in test code, selects
exactly `GC-P01-COMPLETE-SUPPORTED`, copies it into the exact caller-supplied
wrapper, hands the controller one precomputed plain built-in response mapping,
validates that untrusted mapping with WP133, records the bounded case hard-gate evaluation,
requires explicit caller-supplied human review, emits only sanitized evidence,
and proves the original fixture and caller input are unchanged. No fixture is
created or modified.

## State Machine

The immutable controller state constant contains exactly:

1. `NOT_STARTED`
2. `PREFLIGHT`
3. `CASE_LOADED`
4. `INPUT_VALIDATED`
5. `PERMISSIONS_VALIDATED`
6. `BUDGET_VALIDATED`
7. `SESSION_ENVELOPE_BUILT`
8. `EPHEMERAL_SESSION_READY`
9. `PROVIDER_INVOCATION_PENDING`
10. `UNTRUSTED_OUTPUT_CAPTURED`
11. `DETERMINISTIC_VALIDATION_COMPLETE`
12. `RUBRIC_EVALUATION_COMPLETE`
13. `HUMAN_REVIEW_COMPLETE`
14. `SANITIZED_EVIDENCE_COMPLETE`
15. `TEARDOWN_COMPLETE`
16. `COMPLETED`
17. `STOPPED_FAILED_CLOSED`

Success reaches all states through `COMPLETED` and excludes the failure state.
Failure preserves reached-state order, performs teardown, and ends only at
`STOPPED_FAILED_CLOSED`. The caller cannot supply or alter transitions, skip a
state, restart a run, or request background continuation.

## Precomputed Fake-Response Boundary

The source runner accepts data, not executable callback behavior. Tests may
construct the synthetic response before the call, but the controller invokes no
caller-supplied code. It accepts only a plain built-in mapping recursively
composed of plain strings, booleans, lists, tuples, and mappings; custom mapping
or callable objects fail closed before output capture. Evidence therefore
records `adapter_kind: TEST_ONLY_PRECOMPUTED_FAKE_RESPONSE`,
`adapter_call_count: 0`, and `external_callable_invoked: False`.

## Deterministic Validation

The controller imports and calls the existing
`validate_candidate_review_manual_research_response` API from WP133. It does
not duplicate or replace WP133 validation. Unknown fields, invalid shape,
unsafe content, any non-success response label, missing positive-case completion
posture, unsupported or missing supplied citation labels, recursively detected
source-access claims, forbidden authority, raw/persistent-output fields, and
downstream-record fields fail closed. There is no repair, regeneration,
alternate output, or callback.

## Human Review

The caller separately supplies exactly `reviewer_outcome`,
`human_review_complete`, `human_review_required`, and `reviewer_note`. Both
booleans must be exactly true; the outcome must be bounded and acceptable for
dry-run evidence; and the note must be safe, non-empty, bounded, and must not
claim source/citation verification or automatic approval. The precomputed response
cannot author, infer, or approve this acknowledgement.

## Sanitized Evidence

The result contains identifiers and versions, precomputed-response kind, zero
adapter calls, explicit no-external-callable evidence, deterministic-validation
status, the ten explicitly derived hard-gate results, a
bounded test-evaluation label, reviewer outcome, neutral stop reason, and
teardown result. It excludes the envelope, prompt, synthetic excerpts, raw
adapter output, free-form adapter errors, credentials, paths, provider/model
identifiers, source content, trading data, and downstream records. Invalid
results and exceptions expose neutral codes only.

## Teardown

Every terminal path discards the transient precomputed response, clears the local
session-envelope reference, prevents retry by design, records no stable
output, and reaches `TEARDOWN_COMPLETE` before `COMPLETED` or
`STOPPED_FAILED_CLOSED`. Source code has no filesystem or repository write
surface. Tests prove no external caller code executes and no continued activity.

## Failure Behavior

Missing/invalid cases, unknown wrapper fields, false human-review requirements,
permission or budget violations, the wrong case, callable/custom/non-plain
response objects, WP133 rejection, non-success outcomes, missing completion
labels, recursive unsafe no-echo traps, review failure,
authority/downstream/persistence keys, transition tampering, and input mutation
all fail closed. Failure results preserve only sanitized identifiers that
passed validation, neutral error codes, bounded stop evidence, teardown proof,
and fixed false behavior flags.

## Test-Only Temp Boundary

Only pytest supplies `tmp_path`; the controller receives no path and performs
no file operation. The positive smoke and each failed smoke variant prove
`tmp_path` remains empty. The existing WP142 fixture bytes are unchanged, and
no raw or generated output is written anywhere.

## Forbidden Interpretations

- A local harness skeleton is not a Hermes runtime or provider adapter.
- `PROVIDER_INVOCATION_PENDING` is a deterministic state name, not a provider call.
- A precomputed fake response is data, not a provider/model or caller-code invocation.
- WP133 validity is not factual, source, or citation verification.
- A hard-gate result is not provider performance or production acceptance.
- Human review acknowledgement is not automatic approval or authority transfer.
- Sanitized evidence is not raw-output persistence.
- `tmp_path` proof is not stable output authority.
- Research output is not recommendation, probability, ranking, or trading output.
- WP146 gating does not implement or pre-approve WP146.

## Future WP146 Boundary

`WP146 — Hermes Candidate-Review Assisted Research Local Harness Closeout And Controlled Remote Experiment Readiness Decision V1`

WP146 may assess committed WP145 evidence and decide whether later
provider/model research and a separately approved controlled remote experiment
package are justified. WP146 may not install Hermes, create credentials, call a
provider/model, run remote cases, fetch sources, persist raw output, trade, or
implement WP147. WP146 requires separate approval.

## Non-Authority Statement

WP145 is one local/offline/test-oriented deterministic skeleton and test-only
precomputed-response dry run for one existing synthetic case. It grants no Hermes,
provider, model, credential, network, source, persistence, downstream-record,
recommendation, probability, ranking, strategy, paper/live, execution, risk,
order, trading, acceptance, promotion, runtime, scheduler, or WP146 authority.
