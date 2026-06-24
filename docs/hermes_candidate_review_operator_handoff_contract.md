# Hermes Candidate-Review Operator Handoff Contract

## 1. Purpose

This document defines the human-operator handoff contract for candidate-review
Hermes research-chain outputs. It is an advisory research workflow contract
only. It tells a human operator what a future handoff surface must provide,
what the operator must inspect, which research decision labels are allowed, and
which unsafe interpretations must be rejected.

WP105 grants no trade, order, live, paper, risk, credential, runtime,
scheduler, dashboard, or prompt execution authority. It does not create a
source schema, report writer, exporter, CLI, Hermes runtime, scheduler,
database, network behavior, paper/live path, execution path, risk path,
credential path, prompt runner, or model/provider integration.

## 2. Relationship to WP99-WP104

WP99 locked the advisory output validator foundation. WP100 locked the
in-memory Hermes context-packet builder foundation. WP101 locked the in-memory
context-packet dry-run receipt foundation. WP102 locked the in-memory manual
research dry-run operator review foundation. WP103 locked candidate-review
context-packet integration. WP104 locked the in-memory manual chain smoke
helper.

The candidate-review research chain is:

```text
WP103 candidate-review context packet
-> WP101 dry-run receipt
-> WP102 manual operator review
-> WP104 chain smoke
```

WP105 defines the operator-facing handoff contract around that chain. It does
not imply an implemented report writer, file export, CLI, automatic Hermes run,
model/provider call, prompt runner, scheduler, or runtime process.

## 3. Operator Handoff Object Contract

The following are required conceptual fields for a future handoff object. They
are documentation-level fields only, not a new source schema in WP105.

| Conceptual group | Required meaning |
|---|---|
| `handoff_identity` | Stable handoff identifier, contract version, chain identifier, generated-by component name, and deterministic owner. |
| `source_chain_summary` | Summary of the WP103 -> WP101 -> WP102 -> WP104 chain stages used to produce the candidate-review research handoff. |
| `packet_stage_summary` | Operator-readable summary of the candidate-review context-packet stage, including whether the packet stage passed and which neutral reason codes applied if it did not. |
| `receipt_stage_summary` | Operator-readable summary of the dry-run receipt stage, including checked source references, readiness checks, and neutral failure codes if applicable. |
| `operator_review_stage_summary` | Operator-readable summary of the manual operator review stage, including source-review checks and neutral failure codes if applicable. |
| `source_review_checklist` | Checklist showing whether each required source-review check was completed. |
| `evidence_and_provenance` | Source references, provenance status, evidence summary, and manually inspectable artifact references. |
| `staleness_and_missing_data` | Staleness status, known missing data, data quality warnings, and coverage limits. |
| `uncertainty_and_limitations` | Uncertainty notes, assumptions, limitations, and boundary notes. |
| `falsification_checks` | Checks or observations that would falsify the research handoff or require rejection. |
| `human_decision_record` | One allowed research workflow decision label, operator identifier or role, timestamp concept, and rationale using neutral language. |
| `next_research_step` | Specific next manual research step or deterministic validation step. |
| `safety_flags` | Required safety flags listed in Section 4. |
| `rejection_reasons` | Neutral rejection reason codes and short non-echoing descriptions when the handoff is rejected or invalid. |

Missing conceptual groups must make a future handoff invalid.

## 4. Required Safety Flags

Every future handoff must preserve:

| Safety flag | Required value |
|---|---|
| `advisory_only` | `true` |
| `human_review_required` | `true` |
| `no_execution_authority` | `true` |
| `no_runtime_authority` | `true` |
| `no_credential_authority` | `true` |
| `no_paper_or_live_authority` | `true` |
| `no_prompt_execution` | `true` |
| `no_file_or_network` | `true` unless a future WP explicitly authorizes a local file writer or network behavior |
| `no_strategy_promotion_authority` | `true` |
| `no_pr_approval_authority` | `true` |

Safety flags are mandatory and take precedence over any other field. If another
field conflicts with these flags, the future handoff is invalid.

## 5. Operator Decision Vocabulary

Allowed decision labels are:

| Decision label | Meaning |
|---|---|
| `ACCEPT_FOR_MANUAL_RESEARCH_REVIEW` | The operator may continue manual research review using the cited evidence. |
| `REJECT_FOR_INSUFFICIENT_EVIDENCE` | Evidence is not enough for further manual review. |
| `REJECT_FOR_STALE_OR_MISSING_DATA` | Staleness or missing data blocks further review. |
| `REJECT_FOR_RESOLUTION_AMBIGUITY` | Resolution ambiguity blocks further review. |
| `REJECT_FOR_UNSAFE_OR_FORBIDDEN_OUTPUT` | Unsafe or forbidden content appeared. |
| `NEEDS_SOURCE_RECHECK` | Source references must be manually rechecked. |
| `NEEDS_DETERMINISTIC_VALIDATION` | A deterministic local validation step is required. |
| `DEFER_PENDING_MORE_CONTEXT` | More context is needed before deciding. |

These labels are research workflow labels only. They are not trading
recommendations, strategy approvals, risk approvals, PR approvals, or
paper/live permissions.

## 6. Forbidden Interpretation

The handoff must never be interpreted as:

- buy/sell/order instruction;
- trade signal;
- expected-return estimate;
- fair-value estimate;
- edge score;
- confidence-to-trade score;
- position-sizing advice;
- paper/live approval;
- strategy promotion;
- risk override;
- PR approval or merge-readiness claim;
- permission for Hermes to run or execute prompts;
- permission to access credentials/private endpoints/account data.

These terms appear here only as boundary explanations for what the handoff is
not allowed to mean.

## 7. Forbidden Output / Wording Matrix

This section is the explicitly marked forbidden matrix. The canonical document
can mention forbidden words inside this matrix and in boundary explanations,
but future data-bearing handoff outputs must not surface them as
recommendations, instructions, copied raw content, reason text, warnings,
limitations, rejection notes, or next-step text.

| Forbidden token or phrase | Future handoff requirement |
|---|---|
| `buy` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `sell` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `order` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `trade` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `execute` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `position` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `position_size` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `entry` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `exit` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `stop_loss` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `take_profit` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `expected_return` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `edge` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `alpha` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `fair_value` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `live_ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `paper_ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `approve_pr` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `merge_ready` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `credential` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `private_key` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `api_key` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `secret` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `passphrase` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `wallet` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `provider` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `model call` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |
| `prompt execution` | Reject or avoid outside this explicitly marked forbidden matrix and boundary explanations. |

## 8. Raw Metadata / Free-Form Mapping Policy

Future handoff outputs must not include raw/free-form metadata blobs. A future
implementation must recursively scan keys and values. Unsafe caller-provided
input must not be echoed in errors, warnings, limitations, rejection reasons,
or notes.

Errors and rejection details should use neutral codes. No-unsafe-echo is a
hard requirement for all public handoff surfaces.

## 9. Source-Review Checklist

The operator-facing checklist must require:

- source references present;
- source references manually inspectable;
- provenance status explicit;
- staleness status explicit;
- known missing data explicit;
- uncertainty notes explicit;
- limitations explicit;
- falsification checks explicit;
- next research step explicit;
- human decision record explicit.

## 10. Fail-Closed Policy

Missing required conceptual groups must make a future handoff invalid.

Any forbidden output, unsafe echo, raw metadata blob, credential-like content,
order/trade-like content, runtime/prompt-runner content, or
paper/live/execution/risk content must make a future handoff invalid.

Invalid handoffs must be empty or neutral and must not echo unsafe content.

## 11. Future Implementation Guidance

A future WP may implement an in-memory handoff object only after this contract
is merged. A separate future WP is required for any file export/report writer.
A separate future WP is required for any CLI. A separate future WP is required
for any network/API/product behavior. A separate future WP is required for any
Hermes runtime/model/provider/prompt execution.

No future WP may use this contract to authorize paper/live/execution/risk or
credentials.

## 12. Operator Runbook Summary

Human operator steps:

1. Verify source refs.
2. Check stage summaries.
3. Inspect evidence, provenance, and staleness.
4. Review uncertainty, limitations, and falsification checks.
5. Choose one allowed research decision label.
6. Record next research step.
7. Reject if any forbidden or unsafe content appears.

## 13. Non-Goals

WP105 explicitly does not create or authorize:

- source implementation in WP105;
- report writer;
- exporter;
- CLI;
- Hermes runtime;
- prompt execution;
- network/API behavior;
- credentials/account/private endpoints;
- paper/live/execution/risk/order/scheduler/dashboard/bot-loop/deployment/dependency behavior.
