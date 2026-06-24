# Hermes Candidate-Review Handoff Local Manual Export Contract

## 1. Title and Scope

This document defines the repo-truth contract for a future local manual export
and report artifact layer around the WP106 in-memory candidate-review operator
handoff object. It is a docs/status/tests-only contract. No exporter, writer,
CLI, or source implementation is created in WP107.

WP107 is docs/status/tests-only. No exporter or writer is implemented in WP107.

This contract does not authorize Hermes installation, Hermes runtime, prompt execution,
provider or model calls, network or API access, credentials or private state,
paper or live order or risk behavior, scheduler or dashboard or bot-loop behavior,
dependency changes, or workflow changes.

Any future file writer, export, report writer, or CLI implementation requires
a separate approved WP after this contract is merged.

## 2. Relationship To WP105/WP106

WP105 defined the human-operator handoff contract for the candidate-review
research chain (WP103 -> WP101 -> WP102 -> WP104). WP105 is a docs/status/
tests-only contract. It did not implement any source module, exporter, file
writer, CLI, Hermes runtime, network behavior, or credential path.

WP106 implemented the first deterministic stdlib-only local/offline/read-only
in-memory operator handoff object and validator for the WP105 contract. WP106
is a narrow local/offline/read-only source implementation. It does not widen
any WP105 authority boundary.

WP107 defines the contract for a future local manual export/report artifact
layer that may be built on top of valid WP106 handoff output. WP107 does not
widen any authority defined in WP105 or WP106.

The research chain context is:

```text
WP103 candidate-review context packet
-> WP101 dry-run receipt
-> WP102 manual operator review
-> WP104 chain smoke
-> WP105 operator handoff contract
-> WP106 in-memory handoff object
-> [WP107: future local manual export layer -- not yet implemented]
```

## 3. Future Export Artifact Purpose

A future local manual export artifact produced from valid WP106 handoff output
is a manual review artifact only. Its purpose is to allow a human operator to
read and reason about a completed candidate-review handoff in a portable offline
format without relying solely on in-memory inspection.

A future export artifact is not a trade signal, not a strategy promotion, not a
paper or live readiness statement, not a PR approval, not an execution record,
and not a risk authorization. It is a human-readable summary of a valid WP106
handoff result for offline advisory manual review purposes only.

A future exporter may only operate on valid WP106 handoff output. It must not
operate on arbitrary raw model output, arbitrary caller-supplied data, or
unvalidated input.

A future exporter must be local, offline, and manual only unless a later
separately approved WP explicitly widens that authority.

## 4. Permitted Future Inputs

A future exporter may only accept the following as input:

1. A valid WP106 handoff result object produced by the deterministic
   `build_candidate_review_handoff` function in
   `src/data_layer/hermes_candidate_review_operator_handoff.py`.
2. An explicit local output path for a file write, if a future file writer
   WP explicitly authorizes one.

A future exporter must not accept:
- Arbitrary raw model output or unvalidated LLM/AI output.
- Raw caller-supplied dicts or free-form data that bypasses WP106 validation.
- Network or API data.
- Credentials, private state, or account data.
- Paper or live trading state.
- Execution or order records.

## 5. Permitted Future Output Shape

A future export artifact must contain only the following conceptual groups.
Each group maps to a section in a future export artifact.

| Conceptual group | Required meaning |
|---|---|
| `artifact_identity` | Stable artifact identifier, contract version, source handoff identifier, generated-by component name, and deterministic owner. |
| `source_handoff_identity` | The WP106 handoff identity fields (chain identifier, contract version, handoff identifier, generated-by). |
| `chain_stage_summary` | Operator-readable summary of the WP103 -> WP101 -> WP102 -> WP104 chain stages used in the source handoff. |
| `manual_review_summary` | Operator-readable summary of the WP106 handoff decision label and human decision record. |
| `evidence_and_provenance_summary` | Summary of source references, provenance status, evidence summary, and manually inspectable artifact references from the source handoff. |
| `staleness_and_missing_data_summary` | Summary of staleness status, known missing data, data quality warnings, and coverage limits from the source handoff. |
| `uncertainty_and_limitations_summary` | Summary of uncertainty notes, assumptions, limitations, and boundary notes from the source handoff. |
| `falsification_summary` | Summary of falsification checks from the source handoff. |
| `human_decision_record_summary` | The one allowed research workflow decision label, operator identifier or role, timestamp concept, and rationale using neutral language. |
| `next_manual_research_step` | The specific next manual research step or deterministic validation step from the source handoff. |
| `safety_flags` | All required safety flags listed in Section 6, carried through from the source handoff. |
| `forbidden_scope_notice` | A required plain-text notice stating what this artifact must not be used for. |

Missing conceptual groups must make a future export artifact invalid.

## 6. Required Safety Flags

Every future export artifact must carry and preserve all required WP105/WP106
safety flags. These flags are mandatory and must appear in the artifact output
with their required values. A conflicting value makes the artifact invalid.

| Safety flag | Required value |
|---|---|
| `advisory_only` | `true` |
| `human_review_required` | `true` |
| `no_execution_authority` | `true` |
| `no_runtime_authority` | `true` |
| `no_credential_authority` | `true` |
| `no_paper_or_live_authority` | `true` |
| `no_prompt_execution` | `true` |
| `no_file_or_network_beyond_explicit_local_manual_export` | `true` |
| `no_strategy_promotion_authority` | `true` |
| `no_pr_approval_authority` | `true` |
| `no_trade_signal` | `true` |
| `no_position_sizing` | `true` |
| `no_expected_return` | `true` |

## 7. Required Human-Review Wording

Every future export artifact must include a human-review wording block. This
block must state, in plain language:

1. The artifact is advisory only and requires human review before any use.
2. The artifact is not a trade recommendation, order instruction, position
   sizing guidance, or expected-return estimate.
3. The artifact must not be used as a strategy promotion, paper or live
   permission, credential access permission, or PR approval.
4. The decision label is a research workflow label only, not a trading
   recommendation.
5. Any next research step cited is a manual research suggestion only, not
   an automated execution instruction.

## 8. Forbidden Interpretation

A future export artifact must never be interpreted as:

- buy, sell, order, or trade instruction;
- trade signal or execution signal;
- expected-return estimate, edge score, or alpha score;
- fair-value estimate or confidence-to-trade score;
- position-sizing advice or entry or exit instruction;
- stop-loss or take-profit instruction;
- paper or live approval or readiness statement;
- strategy promotion or risk override;
- PR approval or merge-readiness claim;
- permission for Hermes to run or execute prompts;
- permission to access credentials, private endpoints, or account data.

These terms appear here only as boundary explanations for what the artifact
is not allowed to mean.

## 9. Forbidden Output Wording Matrix

This section is the explicitly marked forbidden matrix. The canonical document
can mention forbidden words inside this matrix and in boundary explanations,
but future data-bearing export artifacts must not surface them as
recommendations, instructions, copied raw content, reason text, warnings,
limitations, rejection notes, or next-step text.

| Forbidden token or phrase | Future artifact requirement |
|---|---|
| `buy` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `sell` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `order` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `trade` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `execute` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `position` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `position size` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `entry` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `exit` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `expected return` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `edge` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `alpha` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `fair value` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `live ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `paper ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `deployment ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `trade ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `tradeable` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `approve PR` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `merge ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `credential` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `private key` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `API key` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `secret` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `passphrase` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `wallet` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `provider` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `model call` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `prompt execution` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `prompt runner` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `Hermes runtime` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `scheduler` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `bot loop` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `daemon` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `network poller` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |

## 10. Raw Metadata / Free-Form Data Policy

Future export artifacts must not serialize or echo raw or free-form metadata
blobs from any source. A future exporter must:

1. Only serialize fields that are explicitly defined in the permitted output
   shape (Section 5) of this contract.
2. Recursively scan all fields in the WP106 handoff result before including
   them. Any field not in the permitted output shape must be excluded.
3. Reject any raw/free-form metadata keys at any nesting depth. Key patterns
   that must be excluded include: `raw_metadata`, `free_form_metadata`,
   `caller_metadata`, `arbitrary_metadata`, `raw_input`, `untrusted_input`,
   `notes_raw`, `warnings_raw`, `reason_text_raw`, `custom`, `extras`,
   `metadata`, `freeform`, and similar patterns.
4. Not echo unsafe caller-supplied input in any output field, error message,
   warning, rejection notice, or artifact text.

Errors and rejection details must use neutral codes only. No-unsafe-echo is a
hard requirement for all future export artifact surfaces.

## 11. No Unsafe Echo Policy

A future exporter must never echo unsafe caller input in any output surface.

This applies to:
- All artifact text fields.
- Error messages produced by the exporter.
- Warning messages produced by the exporter.
- Rejection notices produced by the exporter.
- Any log output produced by the exporter.
- Any file content written by the exporter.

Unsafe content includes: forbidden wording families (Section 9), raw/free-form
metadata keys or values (Section 10), credential-like content, trade-like
content, execution-like content, runtime or prompt-runner content, and any
content that would violate the WP105 forbidden output matrix.

Errors must use neutral codes such as `INVALID_HANDOFF_INPUT`,
`FORBIDDEN_CONTENT_DETECTED`, `RAW_METADATA_NOT_ALLOWED`,
`MISSING_REQUIRED_SAFETY_FLAG`, and similar neutral identifiers.

## 12. Future Implementation Gate

Any future implementation of this local manual export layer requires a
separately approved work package after WP107 is merged.

The future implementation gate requires:

1. WP107 must be merged before any exporter implementation WP begins.
2. The implementation WP must reference this contract document.
3. The implementation WP must implement only the permitted output shape
   (Section 5) and no additional fields or capabilities.
4. The implementation WP must not widen any authority boundary defined in
   WP105 or WP106 or this WP107 contract.
5. A future exporter must be local, offline, and manual only unless a later
   separately approved WP explicitly widens that authority.
6. A file writer or export path requires its own separate approved WP.
7. A CLI requires its own separate approved WP.
8. Any network, API, or product behavior requires its own separate approved WP.
9. Any Hermes runtime, model, provider, or prompt execution requires its own
   separate approved WP.
10. Any paper, live, execution, risk, order, scheduler, dashboard, or bot-loop
    behavior is forbidden in all export WPs and requires explicit authority from
    a separately approved WP with explicit scope.
11. No future export WP may use this contract to authorize credentials, private
    state, account access, or authenticated endpoint access.

## 13. Validation Expectations For Future Source Implementation

A future source implementation of this contract must satisfy at minimum:

1. It must only accept valid WP106 handoff result objects as input. Invalid
   WP106 handoff input must cause the exporter to fail closed and produce
   no artifact output.
2. It must verify all required safety flags are present and true before
   producing any artifact output.
3. It must verify all required conceptual groups are present before producing
   any artifact output.
4. It must verify the decision label is one of the allowed WP106 labels before
   including it in artifact output.
5. It must recursively scan for forbidden wording families in all data-bearing
   fields before producing artifact output. Forbidden content must cause
   fail-closed behavior.
6. It must reject raw or free-form metadata keys before producing artifact
   output.
7. It must not echo unsafe content in any output surface including error
   messages, warnings, or rejection notices.
8. It must produce only the permitted conceptual output groups defined in
   Section 5 of this contract.
9. It must include the required safety flags section in the artifact output
   with all required flags set to true.
10. It must include the required human-review wording block in the artifact
    output.
11. It must include the required forbidden scope notice in the artifact output.
12. It must be local, offline, and manual only. It must not make network
    requests, access credentials, call external APIs, or invoke the Hermes
    runtime.
13. It must be stdlib-only or use only explicitly approved internal project
    imports. It must not add new third-party dependencies.
14. All tests for the future implementation must use a negative test matrix
    covering all forbidden content families, all safety flag requirements,
    all required conceptual groups, fail-closed behavior, and no-unsafe-echo
    behavior.

Allowed decision labels that must be accepted by a future implementation:

- `ACCEPT_FOR_MANUAL_RESEARCH_REVIEW`
- `REJECT_FOR_INSUFFICIENT_EVIDENCE`
- `REJECT_FOR_STALE_OR_MISSING_DATA`
- `REJECT_FOR_RESOLUTION_AMBIGUITY`
- `REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT`
- `NEEDS_SOURCE_RECHECK`
- `NEEDS_DETERMINISTIC_VALIDATION`
- `DEFER_PENDING_MORE_CONTEXT`

## 14. Operator Runbook Summary

A human operator using a future local manual export artifact should:

1. Verify the artifact was produced from a valid WP106 handoff result.
2. Verify all required safety flags are present and true in the artifact.
3. Read the forbidden scope notice before acting on any artifact content.
4. Inspect the source handoff identity to confirm the artifact matches the
   expected candidate-review handoff.
5. Review the chain stage summary to understand which research-chain stages
   produced the underlying handoff.
6. Review the manual review summary and the decision label. The decision label
   is a research workflow label only. It is not a trading recommendation.
7. Inspect the evidence and provenance summary. Verify source references are
   manually inspectable.
8. Review staleness, missing data, uncertainty, limitations, and falsification
   summary sections.
9. Check the next manual research step. Act on it only through manual research
   action, not automated execution.
10. Reject the artifact if any forbidden wording, unsafe echo, credential-like
    content, trade-like content, execution-like content, or runtime/prompt
    content appears anywhere in the artifact.

## 15. Deferred Items

The following items are deferred and not resolved by WP107:

- WP107-D001: Local manual export/report artifact writer implementation is
  deferred. Requires a separately approved implementation WP after WP107 merge.
  (OPEN, P3)
- WP107-D002: CLI implementation for the local manual export layer is deferred.
  Requires a separately approved implementation WP. (OPEN, P3)
- WP107-D003: Any network, API, or product behavior for the export layer is
  deferred and requires explicit authority from a later separately approved WP.
  (OPEN, P4)
- WP107-D004: Hermes runtime, model, provider, or prompt execution integration
  with the export layer is deferred and requires explicit authority from a later
  separately approved WP. (OPEN, P4)
