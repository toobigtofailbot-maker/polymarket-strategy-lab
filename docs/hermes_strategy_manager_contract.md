# Hermes Strategy Manager Contract (S10-HERMES-STRAT-01)

Status: V2.1 soft strategy judgment core; current bounded implementation target / implemented
candidate. Implementation: `src/research_runtime/hermes_controlled_runtime/strategy_manager.py`
plus the additive default-off strategy mode in `models.py`, `policy.py` and `controller.py`.
Frozen package: `docs/wp_specs/S10-HERMES-STRAT-01/`.

## 1. Authority split

```text
Humans define the outer blast radius (global PortfolioAuthorityPolicy).
Hermes makes soft strategy/lifecycle judgments inside that envelope.
Deterministic code owns hard account/execution safety.
```

Two Hermes surfaces exist and must not be confused:

- **Generic controlled research primitive** (unchanged): one research-only raw Hermes run,
  untrusted output, no direct strategy, execution or live authority. With `strategy_mode`
  off (the default) its generic and context behavior, schemas, envelopes and receipts are
  byte-identical to the pre-WP behavior.
- **HERMES-STRAT layer** (new): verified STRAT-LIFE context + bounded evidence + existing
  controlled Hermes run + strategy-mode output schema + deterministic repository validation =
  canonical soft Hermes strategy decision (`HermesStrategyAssessment`).

Raw model bytes never acquire repository authority: every raw draft authority flag
(`advisory_only`, `human_review_required`, `no_execution_authority`, ...) is still required
to be exactly true. Only the separately authorized deterministic validator in
`strategy_manager.py` turns a strictly validated strategy-mode draft into the canonical
record. The canonical record has no per-strategy human-approval field and no hidden
reasoning field.

## 2. Strategy-mode output contract

Contract id `hermes-strategy-assessment-draft-output-contract/1.0.0` = all generic draft
fields + exactly one required `strategy_assessment` object (no unknown fields):

| Field | Domain |
|---|---|
| `lifecycle_action` | CONTINUE, SCALE, REDUCE, ADAPT, PAPER, QUARANTINE, RETIRE |
| `recommended_health_state` | HEALTHY, WATCH, DEGRADED, QUARANTINED, RETIRED (never NEW) |
| `risk_direction` | UNCHANGED, INCREASE, DECREASE, PAPER_ONLY, ZERO |
| `target_risk_band` | null or PAPER, EXPLORATORY_LIVE, VALIDATED_LIVE, MATURE_LIVE |
| `adaptation_recommendation` | null, or `{kind, summary, parameter_updates}` for ADAPT |

The generated schema, the validator and the consistency rules derive from the same
constants in `models.py`. Obvious consistency rules (fail closed, no scoring/ranking):
CONTINUE -> UNCHANGED; SCALE -> INCREASE and health not QUARANTINED/RETIRED; REDUCE ->
DECREASE; PAPER -> PAPER_ONLY and band PAPER; QUARANTINE -> QUARANTINED, ZERO, null band;
RETIRE -> RETIRED, ZERO, null band; ADAPT -> never INCREASE. Adaptation is null unless ADAPT;
PARAMETER_UPDATE needs a non-empty map of existing parameter names with canonical JSON values
(no float/NaN/Infinity); MATERIAL_REDESIGN carries an empty map. No child StrategyVersion is
created; only a future child passed through the STRAT-LIFE builder may receive a canonical
adaptation class.

## 2a. Dedicated validated strategy projection

For `strategy_mode=true` the authoritative validator produces one immutable
`ValidatedStrategyResearchProjection` (nullable `strategy_projection` on `ValidatedResearchDraft`
and `HermesControlledRunResult`; null in generic/context mode). It preserves exactly the request
id, research summary, confidence label, the eight research-quality lists, the sanitized source
references (URL digests and classes; no raw URL) and the validated `strategy_assessment`, and only
exists after every raw authority flag passed validation. Raw Hermes JSON is parsed only by that
validator; `strategy_manager.py` never parses or reparses captured raw output and builds the
canonical assessment from the projection alone.

## 3. Model-facing context

Built deterministically from the exact verified `StrategyLifecycleSnapshot` in the existing
request text fields (existing 4096-character hard bounds unchanged):

- `research_question`: strategy identity (version/family/parent ids, label, evidence posture,
  adaptation class, code identity, `execution_rule_sha256`, `adaptive_bounds_sha256`), current
  lifecycle state (`current_health_state`; the allocation RECORD as `current_allocation_id`,
  `current_allocation_risk_band`, `current_allocation_budget_usd`,
  `current_allocation_valid_from_ns`, `current_allocation_valid_until_ns` — all five null without
  a record; active restriction ids; active policy id; `strategy_lifecycle_context_sha256`), trigger
  and information cutoff. The allocation is described with its exact validity window only: no
  `current_risk_band` / `current_active_budget_usd` names and no derived active, capacity,
  executable or live-authority claim.
- `research_objective`: the assessment objective ("current only through the stated information
  cutoff") and the compact bounded evidence block; `evidence_index` i is
  `input_evidence_refs[i - 1]` of the record.
- `public_market_context`: thesis, universe, entry/exit rules, parameters and subject refs.

Never forwarded: `account_scope_ref`, credentials, private account material, raw local paths
and raw `execution_rule` content (bound by SHA-256 only; execution economics belong to
S10-EXEC-FEAS-01). Nothing is truncated or summarized: an over-bound context, prompt or
command line fails `STRATEGY_CONTEXT_LIMIT_EXCEEDED` before any Hermes spawn.

## 4. Strategy-local currentness

`strategy_lifecycle_context_sha256` = sha256 of the canonical JSON of
`{schema_id: hermes-strategy-lifecycle-context, schema_version, strategy_version_id,
current_health_state, current_allocation (id, policy, band, budget, validity) | null,
active_restriction_receipt_ids (sorted), active_policy_id | null}`. It is the semantic
currentness key; `lifecycle_store_head_entry_hash` is retained as audit provenance only, so an
unrelated strategy-only mutation never invalidates the assessment. This package does not apply
a stale decision.

## 5. Evidence, trigger, cutoff

- Triggers: INITIAL_ASSESSMENT, PERFORMANCE_UPDATE, EVIDENCE_UPDATE, REGIME_CHANGE,
  ADAPTATION_REVIEW, RESTRICTION_REVIEW, OPERATOR_REASSESSMENT; `trigger_ref` null or one
  bounded non-secret non-path opaque reference. No trigger launches Hermes by itself.
- Cutoff: whole-second UTC `YYYY-MM-DDTHH:MM:SSZ`; evidence newer than the cutoff rejects.
  Evidence timestamps may carry fractional seconds; ordering compares UTC instants, never raw
  strings (cutoff `2026-10-03T12:00:00Z` vs evidence `2026-10-03T12:00:00.500Z` -> EVIDENCE_INVALID).
- Evidence: before use, every supplied `ContextEvidenceItem` is rebuilt with the existing canonical
  builder; the rebuilt `evidence_id` and canonical fields must equal the supplied ones or the item
  is EVIDENCE_INVALID. `StrategyAssessmentEvidence` reuses the existing
  `ContextEvidenceItem.evidence_id` (no second identity); at most 12 unique ADMISSIBLE items intersecting the sorted
  subject refs, each with a non-empty <=160-character non-secret non-path summary.
- Subject refs contain the strategy version and family ids plus optional canonical public
  market/event/token or evidence subjects; never wallet/account/credential material.
- Evidence posture guides the research approach; there is no universal trade-count, Sharpe,
  sample-size, QUAL/WP170/WP172 gate.

## 6. Records

- `HermesStrategyRunRecord` (`hermesstrategyrun:sha256:`): strategy, fingerprint, store head,
  trigger, cutoff, runtime request/receipt/policy ids, provider/model, Hermes version, terminal
  status, times, cost evidence, decision time, fixed no-credential/order/execution/live flags.
  Built only after the runtime receipt identity is revalidated.
- `HermesStrategyAssessment` (`hermesstrategyassessment:sha256:`): predecessor, run binding,
  context, subject/evidence refs, validated summary and research-quality lists, the five
  strategy fields, `adaptation_recommendation_json`, decision time,
  `canonical_soft_strategy_decision = true` and fixed no-credential, no-portfolio-policy,
  no-hard-risk-override, no-paper-execution, no-order, no-execution, no-live flags.
- Each id = prefix + sha256(canonical JSON of every other field); canonical JSON is the
  STRAT-LIFE domain (sort_keys, compact, ensure_ascii false, no floats/NaN).

## 7. Store

One explicit caller-selected `.sqlite3` file (no default path, no directory creation):
`s10-hermes-strategy-manager-store`, schema 1, application id 0x48534D31 (1213418801),
DELETE / FULL / foreign_keys ON, kinds HERMES_STRATEGY_RUN and HERMES_STRATEGY_ASSESSMENT,
no-UPDATE/no-DELETE triggers, entry hash over sequence/kind/id/strategy/payload hash/previous,
bounds 100,000 records / 262,144 bytes per record / 536,870,912 aggregate, full verified
replay on every open, no migration. The predecessor of a new assessment is the replay-derived
latest same-strategy assessment (or null); a same-strategy assessment that lands first makes
the commit `ASSESSMENT_PREDECESSOR_STALE`. Unrelated strategies never block each other.

Commit semantics: failed controlled run -> run record only; successful run with invalid or
inconsistent strategy output -> run record only; valid output -> run record + assessment in one
transaction (a stale predecessor rolls the pair back and then records the run alone). No
second Hermes invocation ever repairs output or persistence.

## 8. Decision semantics and non-authority

The assessment is a soft strategy decision, not a hard authorization. CONTINUE implies no
allocation increase. SCALE stays downstream gated: no allocation, band or policy change, no
EXEC-FEAS satisfaction, no Gate-C permit. REDUCE / PAPER / RETIRE are recorded only; later
orchestration applies valid STRAT-LIFE changes. QUARANTINE is strategy-local and never a global
kill. ADAPT proposes only. HERMES-STRAT never writes or opens the STRAT-LIFE store, holds no
credential, signs nothing, places/cancels no order, creates no paper session, mutates no
PortfolioAuthorityPolicy and runs no scheduler or background loop. Hard deterministic
ownership of credentials/signing, venue/access validity, durable mutation, reconciliation,
global capital/exposure/loss ceilings, kill state and shared-state integrity is unchanged.

## 9. Boundaries after this package

S10-STRAT-LIFE-01 is merged. S10-EXEC-FEAS-01 remains the next core V2.1 package after
HERMES-STRAT review and merge. S10-CC-FOUND-01 is NOT AUTHORIZED / NOT STARTED until
S10-HERMES-STRAT-01 actually merges; the Control Center remains NOT STARTED. ALPHA-03 is
parallel and non-blocking; DATA-03 is unchanged and non-blocking; S10-DEPLOY-01 host
activation is separate; Gate C is unchanged; live trading remains DISABLED; capital/orders
USD 0 / 0.
