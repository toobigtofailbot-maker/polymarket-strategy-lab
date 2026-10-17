# Hermes Autonomous Provider Feedback Contract (S10-HERMES-AUTO-02)

Local/offline, default-off vertical step. Not live authority, not a real provider
result, not a scheduler. Governing package: `docs/wp_specs/S10-HERMES-AUTO-02/`.

## Chain

```
pinned Hermes native tool surface (enabled_toolsets=[])  -> OFFLINE_NATIVE_TOOL_SURFACE_CHECKED
  -> StageBRequest (content-addressed, single dispatch, deadline-bound)
  -> OfflineStageBBackend (trusted canned data)            -> StageBResult (producer-owned)
  -> choice provenance record (choiceprovenance:sha256:)   -> AUTO-01 evaluate_once(producer_evidence=...)
  -> native EXEC-FEAS + exploratory Gate C preview (unchanged, non-executable)
  -> verified WP173 research-paper snapshot -> ContextEvidenceItem
  -> native run_hermes_strategy_assessment(trigger="PERFORMANCE_UPDATE", FakeHermesBackend)
  -> one journaled cycle bundle (auto02cycle:sha256:)
```

## R001 tool-free native surface

`src/research_runtime/hermes_controlled_runtime/tool_free_stage_b.py`.
`probe_native_tool_surface` runs the exact pin (`345cd2b057a452236de401d3534b8502a7465e8d`,
v0.21.3) in a child with an empty temporary `HERMES_HOME`, a stripped environment and
denied sockets. It constructs the native `AIAgent(enabled_toolsets=[])` and serializes
the request with native `build_api_kwargs`. The verdict requires all of the following:

- an empty selector and empty definitions;
- empty agent, valid and context-engine tool names after every post-load injection;
- no `tools` or `tool_choice` key in the request;
- only the denied loopback placeholder as a network target;
- a `None` negative control that exposes the default tool universe (so a stub cannot pass).

The CLI `--toolsets` flag is never used. Verified locally on 2026-10-16. Provider-side
tool isolation remains `UNPROVEN`. A tool-call attempt, provider error, model mismatch,
late response, oversize output, non-strict JSON, or any usage, cost or receipt claim is
an invalid terminal. There is no retry and no fallback.

The pinned native conversation loop sends unknown-tool errors back to the model, with
up to 3 retries (`agent/turn_tool_round.py`, `agent/turn_tool_validation.py`). A future
real transport must therefore use one `build_api_kwargs` request plus one client call,
not `run_conversation`.

## R002 provenance

`build_choice_provenance` binds the following to one content address, never storing
raw text:

- raw-output SHA-256, request id, AUTO-01 menu digest, choice-schema digest and model-input digest;
- cutoff, issue, response and deadline clocks;
- model label, claimed strategy version and assessment (TRADE only);
- caller-loaded lifecycle and Hermes heads;
- optional prior paper snapshot id;
- pin and tool-surface fingerprint.

Labels are fixed: `OFFLINE_INJECTED`, `LOCAL_OFFLINE_PRODUCER`, `MODEL_ORIGIN_UNVERIFIED`,
`REAL_PROVIDER_NOT_INVOKED` and `REAL_PROVIDER_PROMOTION_REQUIRES_SEPARATE_EMPIRICAL_AUTHORITY`.
`verify_choice_provenance` rejects forged labels, field edits, extra or missing fields,
schema, output or menu changes, and invalid clocks. Only a producer-owned, non-replayed
`StageBResult` becomes a record. SHA-256 is local binding, not provider attestation.

## R003 AUTO-01 admission

`evaluate_once(..., producer_evidence=None)` is byte-identical to the merged `9ffbdb4`
receipt when the argument is absent. With a record, AUTO-01:

1. verifies it;
2. requires the model's `produced_at_ns` inside the producer window and an equal deadline;
3. requires unchanged store heads (`PRODUCER_STATE_CHANGED`) and an exact claim
   (`PRODUCER_CLAIM_MISMATCH`);
4. relabels only `proof_level` to `OFFLINE_PRODUCER_BOUND`.

Model text still must say `SYNTHETIC_ONLY`. `model_origin_proof` stays `UNVERIFIED`.
The native intent, feasibility, Gate C and permit are unchanged. The preview remains
`NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY`.

**Empirical promotion gate.** The only path to a real-provider label is a separately
authorized successor (S10-HERMES-AUTO-02-REAL-01) with genuine runtime evidence, its
own journal namespace and fresh Karl authority. Changing a flag or string never promotes.

## R004 paper feedback

`run_paper_performance_update` follows these steps:

1. requires a `FakeHermesBackend`;
2. requires a research-only binding (no live or Gate C eligibility, USD 0) whose candidate
   is in the strategy version's evidence refs;
3. requires an existing store file;
4. requires a native verified snapshot with exact binding, candidate, spec, version,
   code, subjects and scope;
5. requires evidence at or before the cutoff, and a cutoff strictly after the latest
   assessment for that version;
6. calls the native manager with `PERFORMANCE_UPDATE` and `trigger_ref` = snapshot id.

Facts include orders, fills, rejected orders, risk denials, fill ratio, fees,
slippage/spread/adverse costs, pending markouts, and realized and unrealized paper PnL.
Unrealized PnL stays `None`/UNKNOWN, never zero. Missing marks or non-positive totals
are `CONTRADICTING`. The paper store is opened read-only in effect (bytes unchanged).
There is no paper order, and no policy, allocation or lifecycle mutation. The label is
`RESEARCH_PAPER_SIMULATED` with `live_pnl_claim=False`.

## R005 cycle evidence

`run_one_cycle` produces one bundle per request id. Its outcomes are `ELIGIBLE_PREVIEW`,
`NO_TRADE`/`PAUSE`/`REASSESS`, `REJECTED`/`INCONCLUSIVE`, the invalid Stage B terminals,
`PROVENANCE_OR_STORE_INVALID`, `INTERRUPTED_BLOCKED`, `JOURNAL_INVALID` and
`TOOL_SURFACE_OR_REQUEST_REJECTED`. The bundle holds ids, statuses and reason codes only:
no paths, prompts, raw output or secrets. An exact replay returns the stored bundle with
zero redispatch. An existing reservation without a terminal blocks permanently and
never overwrites a journal. The TS02 journal is untouched.

**Decision-to-performance linkage (SIDE20 correction).** Inside `run_one_cycle`,
`paper_feedback` reaches the manager only when **all** of these hold:

- AUTO-01 returned `ELIGIBLE_PREVIEW`;
- the feedback `strategy_version_id` equals the receipt's natively validated
  `strategy_version_id`;
- `expected_binding.candidate_id` equals the receipt's `candidate_id`;
- the supplied lifecycle snapshot head equals the receipt's `lifecycle_head`;
- the Hermes manager store is the cycle's own store.

Any mismatch is `REJECTED` / `FEEDBACK_LINEAGE_MISMATCH` (`decision_linkage=MISMATCH`), with
no manager invocation and no assessment write. A linked update records
`decision_linkage=DECISION_LINKED` plus the linked AUTO-01 receipt id, candidate and strategy.

`DECISION_LINKED` means the update concerns the identical verified candidate, strategy, lifecycle
head and manager store. It does not mean the paper outcome was caused by this preview: this WP
places no paper order, and linkage is identity-based, not decision-relative in time.

Malformed feedback arguments return `FEEDBACK_INPUT_INVALID`, and the cycle is still journaled.

Non-trade, rejected, inconclusive or invalid decisions stay denominator records. Their feedback
is `DEFERRED_NOT_DECISION_LINKED`, so an unrelated outcome is never credited to that decision.
The standalone `run_paper_performance_update` remains available for earlier verified paper
sessions; it carries no decision-linkage claim.

**Prior paper reference.** A cold-verified prior-paper input does not exist yet, so
`prior_paper_snapshot_id` must be `None`. Otherwise:

- the cycle returns `PRIOR_PAPER_SNAPSHOT_UNVERIFIED` before any dispatch or journal write;
- `build_choice_provenance` and `verify_choice_provenance` reject any non-`None`
  `paper_snapshot_id`.

The record field is reserved for a future verified input.

## Non-authority

No real provider/model/Firecrawl call, credential or home access, product network,
account, wallet, order, capital, scheduler, deployment, push, PR, hosted CI or merge.
H1 web-only policy, controller and runner, TS01/TS02, Alpha, STRAT-LIFE, EXEC-FEAS,
Gate C, the WP173 engine, gateway and risk are unchanged.
