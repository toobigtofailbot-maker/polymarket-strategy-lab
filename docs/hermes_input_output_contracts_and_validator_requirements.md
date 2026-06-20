# Hermes Input/Output Contracts And Validator Requirements

## Status And Authority

- Contract status: WP97_REPO_TRUTH_DOCUMENTATION_LEVEL_CONTRACT_REQUIREMENTS
- Package: WP97 - Hermes Input/Output Contracts And Validator Hardening V1
- Scope: docs/status/tests-only contract and validator requirements lock-in
- Runtime authority: NONE
- Execution authority: NONE
- Paper authority: NONE
- Live authority: NONE
- Credential authority: NONE
- Hermes installation, connection, provider, and model authority: NONE
- Source schema, source validator, prompt-pack, runbook, exporter, parser, context-packet, and runtime artifact authority: NONE

This document defines documentation-level Hermes input/output contract
requirements and future deterministic validator requirements. It is not a
machine-readable schema, not a runtime artifact, not a prompt pack, not an
operator runbook, not an exporter, not a parser, and not a source-code
validator. It creates no JSON schema, YAML schema, Python dataclass, Pydantic
model, CLI validator, runtime validator, context-packet generator, prompt
runner, Hermes runtime, provider/model configuration, credential path, network
behavior, paper behavior, live behavior, execution behavior, risk behavior,
scheduler behavior, dashboard behavior, bot-loop behavior, source module, tool
module, dependency change, or lock-file change.

Hermes remains not installed, not connected, not a runtime dependency, and not
authorized for execution or control.

## Relationship To WP95 And WP96

WP95 is the accepted Hermes research-brain execution plan at
`docs/hermes_research_brain_execution_plan.md`. WP96 is the Hermes advisory
foundation architecture at
`docs/hermes_advisory_foundation_research_brain_architecture.md`.

WP97 documents Phase 2: Hermes input/output contracts and validator
requirements. It does not override WP95 or WP96. The safe interpretation is the
one that preserves broad Hermes research freedom, deterministic-core control
responsibilities, and human review before any behavior changes.

## Broad Research Freedom And Deterministic Core

Hermes should remain a powerful adaptive research brain for market research,
edge discovery, hypothesis generation, experiment design, strategy critique,
future WP recommendations, failure analysis, performance-improvement ideas,
wallet and candidate review, regime monitoring, cross-market inconsistency
analysis, resolution-rule ambiguity review, and microstructure/slippage realism
review. The phrase cross-market inconsistency analysis is intentionally
preserved as a broad research family.

The phrase microstructure/slippage realism review is intentionally preserved as a broad research family.

The deterministic core remains responsible for execution, validation, risk,
state, accounting, credentials, order lifecycle, live safety, kill switch, audit
logs, and strategy-promotion gates. Hermes output cannot override, bypass,
approve, or replace those responsibilities.

## Common Input Field Concepts

Future Hermes inputs must use documentation-level field concepts equivalent to:

- `artifact_id` or equivalent reference;
- `artifact_type`;
- `source_refs`;
- `provenance_status`;
- `staleness_status`;
- `data_quality_warnings`;
- known missing-data fields;
- `human_review_required`;
- `advisory_only`;
- `forbidden_use_notice`;
- deterministic owner;
- forbidden-use notice.

These field concepts are requirements for future design. They are not a
machine-readable schema in WP97.

## Input Family Contracts

Each future input family below must include source artifact references,
provenance fields, staleness fields, data-quality warnings, known missing-data
fields, an advisory-only notice, a human-review-required flag, a deterministic
owner, and a forbidden-use notice.

| Input family | Documentation-level contract requirement |
|---|---|
| repo-truth summary packet | References current repo-truth docs, status fragments, deferred items, validation state, and known stale areas; cannot replace direct repo inspection. |
| market research candidate packet | References candidate artifacts, market-source provenance, staleness, missing fields, ambiguity warnings, and deterministic owner for validation. |
| wallet/candidate review packet | References only authorized wallet/candidate review artifacts and local deterministic outputs; no account access or private endpoint input. |
| resolution ambiguity packet | References resolution labels, ambiguity taxonomy, source artifacts, missing-source notes, and reviewer confidence limits. |
| cross-market relationship packet | References deterministic relationship metadata and explicitly rejects automated equivalence or semantic matching authority. |
| microstructure/slippage realism packet | References authorized microstructure artifacts and stale/liquidity warnings; no executable price or fill instruction authority. |
| paper-result/failure-review packet | References only future authorized paper-result artifacts; no live account state, order authority, or paper execution decision authority. |
| performance-review packet | References deterministic performance artifacts, missing metric warnings, and human-review limits; no strategy promotion approval. |
| experiment-design packet | References hypothesis artifacts, falsification plan, missing data, and deterministic validation owner; no implementation approval. |

## Common Output Field Concepts

Future Hermes outputs must use documentation-level field concepts equivalent to:

- `artifact_id` or equivalent reference;
- `artifact_type`;
- `source_refs`;
- `provenance_status`;
- `staleness_status`;
- `data_quality_warnings`;
- `human_review_required`;
- `advisory_only`;
- `forbidden_use_notice`;
- `confidence_level`;
- `uncertainty_notes`;
- `assumptions`;
- `falsification_checks`;
- `deterministic_validation_handoff`;
- `recommended_next_review_step`.

Every future output must include advisory-only output language, a
human-review-required flag, evidence summary, source artifact references,
confidence or uncertainty statement, assumptions, falsification path,
deterministic validation handoff, rejected interpretation warning, and a
forbidden-action statement.

## Output Family Contracts

| Output family | Documentation-level contract requirement |
|---|---|
| research hypothesis | Advisory hypothesis only, with evidence summary, assumptions, uncertainty, falsification checks, and next human review step. |
| experiment proposal | Advisory experiment design only, with deterministic validation handoff and no implementation approval. |
| market/candidate critique | Critique only, with source refs, rejected interpretations, and no buy/sell/hold or candidate promotion authority. |
| wallet-signal critique | Critique only, with provenance, stale/missing-data warnings, and no copy-trading, account action, or position sizing authority. |
| cross-market inconsistency note | Advisory inconsistency note only, with no automated equivalence claim or trading instruction. |
| resolution ambiguity warning | Advisory ambiguity warning only, with source limits, reviewer confidence limits, and manual review requirement. |
| microstructure realism critique | Realism critique only, with no entry price, exit price, limit price, stop loss, take profit, or order instruction. |
| strategy critique | Critique only, with no strategy promotion approval, config mutation, runtime change, or merge-readiness claim. |
| failure-analysis note | Failure analysis only, with no risk override, execution restart, scheduler instruction, or final decision authority. |
| performance-improvement idea | Advisory improvement idea only, with falsification path and future WP handoff; no automatic parameter update. |
| future-WP suggestion | Planning suggestion only; cannot approve its own WP, approve PRs, claim merge readiness, or bypass Codex workflow. |

## Forbidden Output Matrix

Hermes output must not act as or imply any of the following:

| Forbidden category | Rule |
|---|---|
| buy/sell/hold/enter/exit instruction | Forbidden as instruction, decision, signal, or executable trade direction |
| position sizing | Forbidden as allocation, quantity, sizing, or auto-applied parameter |
| allocation | Forbidden as account, capital, bankroll, or portfolio allocation instruction |
| entry price / exit price / limit price as instruction | Forbidden as order or execution instruction |
| stop loss / take profit as instruction | Forbidden as executable risk or order parameter |
| order placement/cancel/sign/submit instruction | Forbidden for order lifecycle authority |
| risk override | Forbidden |
| live readiness approval | Forbidden |
| paper/live execution decision | Forbidden |
| strategy promotion approval | Forbidden |
| config mutation | Forbidden |
| scheduler/bot-loop instruction | Forbidden |
| credential request | Forbidden |
| private endpoint request | Forbidden |
| account data request | Forbidden |
| PR approval | Forbidden |
| merge-readiness claim | Forbidden |
| final decision authority | Forbidden for trade, risk, runtime, paper/live, PR, or strategy-promotion decisions |

## Validator Requirements

Future deterministic validators must fail closed. WP97 does not implement those
validators.

Future validators must include:

- recursive scan over top-level fields;
- recursive scan over nested keys;
- recursive scan over nested values;
- scan over metadata/free-form text;
- scan over warnings;
- scan over limitations;
- scan over advisory notices;
- scan over examples;
- scan over Markdown examples where relevant;
- no raw unsafe echo from invalid inputs into public result fields;
- safe quarantine/diagnostic policy if invalid input must be referenced;
- negative-test matrix requirement before any future validator implementation;
- invalid examples must become tests;
- fail-closed behavior when required advisory-only, human-review-required, or forbidden-use fields are missing;
- prohibition on validators auto-applying, executing, scheduling, mutating config, approving PRs, approving strategy promotion, or approving paper/live behavior.

Invalid example categories for future tests include forbidden trade
instructions, sizing/allocation, executable price parameters, order lifecycle
instructions, risk override, credential/private endpoint/account data requests,
scheduler/bot-loop instructions, merge-readiness claims, strategy promotion
approval, and missing advisory/human-review/forbidden-use fields.

## Human Review And Deterministic Handoff

Hermes output is advisory only. Accepted Hermes output may become a future
human-reviewed WP, deterministic validation task, or manual research task.
Accepted Hermes output may become a future human-reviewed WP only after human
review and deterministic handoff.
Hermes cannot directly mutate repo truth, configs, paper/live state, execution
state, risk state, scheduler state, or PR status.

Human review and deterministic validation are required before behavioral
changes. Research/workbench artifacts have no execution authority unless a
later approved WP promotes them through repo truth.

## Future Implementation Gates

WP97 explicitly defers:

- actual machine-readable schemas;
- source validators;
- prompt packs;
- operator runbooks;
- context-packet exporters;
- Hermes runtime/manual run process;
- paper assistant integration;
- live review assistant integration.

A possible next WP may be Hermes research prompt pack and operator runbooks, or
a narrower Hermes contract validator implementation WP if Karl decides validator
code should precede prompts. This document does not authorize either path; each
requires a later approved WP with its own scope and boundary checks.

## Plan-Change Rule

Material changes to WP95, WP96, or this WP97 contract-and-validator
requirements document must update repo-truth docs in the same work package or an
approved follow-up. Chat memory and PR comments alone are not authoritative.
Dynamic PR state belongs in GitHub metadata and the PR body. Committed status
docs remain stable post-merge.
