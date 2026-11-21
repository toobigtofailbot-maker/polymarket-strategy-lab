# 06 — Three real learning loops, bounded optimization and no self-modification

**Status:** Stage A/B target engineering contracts. Existing native `forecast_evaluation.py`, `learning_feedback.py`, `autonomous_feedback.py`, Alpha research episodes and hermes/strategy manager are the primary computation and storage surfaces. A9 may **recommend** changes, not apply them. No new live Alpha/strategy data is collected during this program; authentic post-discovery outcome scoring is a later permission gate.

## Loop 1 — Scientific/decision-quality feedback (A3/A4/A8)

```text
Native frozen question+rule/source/PIT cutoff
  → genuine witnessed A3 first-pass forecast and A4 blind first-pass falsification
  → immutable forecast/abstain/uncertainty+method version and full selection denominator
  → [only once true outcomes later permitted] authenticated resolved outcome cohort
  → existing forecast_evaluation.score_one/score_cohort + learning_feedback.score_frozen/diagnostics
  → versioned ResearchMethodProposal / what-would-change-the-conclusion
  → Side25/owner-governed method routing version for subsequent tasks (no retroactive edits)
```

**Engineering-only Stage A proof:** frozen binary-score fixtures with original forecast timestamp `t0`, independent outcome `t1>t0`, missing/ambiguous label, abstentions, duplicate/corrected outcome and matched cohort. Demonstrate native scorer and exact denominator; mark fixture `SYNTHETIC_VALIDATION`, not `REAL_OOS`. Hard failures: prediction produced after seeing outcome, post-hoc probability rewrite, family/version mixing, resolver conflict, source evidence after cutoff, excluding non-responders. Use native temporal split and old forecasts; **do not** run new WP170 prospective OOS or strategy profit searches now. Later actual model calibration only with independently qualified real source/time outcomes.

**Measurements:** Brier/log scores (proper binary formula only for resolved valid labels), calibration buckets with sample sizes, paired matched cohorts, coverage/abstention, conflict detection & false alarms, temporal leakage count, root causes (missing source, wrong rule, uncopyable wallet, unavailable book); compare to frozen price-only/naive and native-only baselines. No guarantee that more agents means better scores; use confidence intervals and pre-specified thresholds rather than invented improvements.

## Loop 2 — Agent routing, reliability and provider-cost efficiency (coordinator/A8/A9)

**Measurable sequence:** append-only attempt journal and trusted child witness → per-role terminal (`SKIPPED`, `REFUSED`, `COMPLETED_CONSUMED`, `FAILED`, `TIMED_OUT_UNKNOWN`) → calculate actual useful/cold-verified outputs per total admitted task, provider+tool usage where witnessed, input/output tokens (if trustworthy), latency percentiles and cost/unknown-cost → propose one versioned routing/profile change → blind paired frozen evaluation against prior policy → **owner-approved** non-economic routing policy release → reversible later cycle. Routing policies never modify source cutoff, qualification or hard trading authority.

**Required accounting fields:** campaign/task/role/parent/child IDs, complete admitted/refused/skipped and retry denominator, charged attempts vs unresolved attempts, model/backend/pin/profile ID, requested and effective tool inventory, source bytes/tokens, verified claims, consumer head, stop cause, wall/monotonic latency, per-role provider spending when independently reported or `COST_UNKNOWN`. Do not synthesize model cost from a guessed subscription; unknown is **not $0** and blocks further spending if budget could be exceeded. No fallback to another provider/model without new owner grant.

**Optimization candidates after measured need:** (1) deterministic/lexical source filter before an LLM; (2) model tier based on objective uncertainty/source ambiguity; (3) skip A4 on low-risk trivial cases only if later ablation doesn't degrade relevant true conflict recall; (4) compact source packets while preserving exact citations; (5) content-addressed, immutable *public-source* result cache keyed by source+cutoff+model/tool/policy; (6) bounded batching with no transitive permissions; (7) native scoring/fee calculations in Python rather than tokens. **Do not** bring in vector store/DSPy/OTel/MCP/LangGraph automatically. Only add a dependency when the same-case benchmark shows an actual gap with measurable incremental value and maintenance/license review.

**Candidate thresholds, not promises:** a route change must meet predefined acceptance criteria on *fixed* blind tests: zero increased unsafe tool exposure, zero citation/source cutoff regressions, zero lost task denominator, zero duplicate charges/dispatches on recovery, and positive supported metric (valid claims/$, completed consumer traces/hour or error reduction). Unknown metrics must remain `NOT_MEASURED`. Delay preference for cheap model only when measured quality is not harmed. Versioned rollback restores old routing table while leaving immutable previous source/consumer receipts untouched.

## Loop 3 — Bot Improvement Engineer (A9): governed software improvement, not self-edit

**Only input:** read-only sanitized source inventory, GitHub CI job status and evidence head, diffs with secret scanning, host resource/incident summaries with personal/account fields removed, task cost/quality denominators and 36-row adoption backlog. A9 may access no SSH/credential files, wallet, account APIs, web permission grant, filesystem write tools, order/signing or privileged MCP. Native static test logs have precedence over model prose.

**Proposed minimal immutable `BotImprovementProposal v1`:**

| Field | Required meaning |
|---|---|
| `proposal_id`, `producer_role=A9`, `source_release_sha`, `recorded_at` | content-addressed, canonical developer-evidence lineage; *not* an implementation PR |
| `affected_capability_ids`, `affected_agent_ids`, `current_call_path`, `missing_actual_consumer` | exact original commitments/roles that would benefit; no vanity improvement |
| `problem_and_falsifiable_hypothesis`, `input_evidence_ids`, `observed_metric`, `unknowns` | grounded failure, no speculative speedup as measured fact |
| `recommended_reuse_method`, `minimal_candidate_patch_scope`, `upstream_pin_and_license` | one bounded route vs native replacement vs evaluated non-adoption |
| `test_protocol`, `negative_cases`, `holdout_policy`, `expected_benefit_test` | repeatable before/after; hard safety and evidence gates |
| `risk_level`, `permission_changes`, `runtime_cost_cap`, `backout_plan`, `owner_decision_needed` | protected boundaries, explicit approvals; never self-granted |
| `status=PROPOSED_UNREVIEWED`, `consumer=SIDE25_INTAKE` | no autonomous write/dispatch/merge/runtime change |

**Actual consumer proof:** A9 produces a well-formed proposal on a real **sanitized fixed CI-like failure fixture**, Side25 intake/decision reads and acknowledges exact proposal ID (can use existing review artifacts, no new database), and a negative case involving risk/keys is refused with no code modification. A subsequent Karl-authorized WP and exact-head independent PR review are *external actions*; A9 can assess whether the intended acceptance metric later improved but cannot grant completion status.

## Fixed ablation and holdout protocol

| Pre-committed test lane | What is actually invoked | Outcome required |
|---|---|---|
| B0 native-only | deterministic source/triage/quote/math/scoring with zero model | correctness, coverage, latency and cost baseline |
| B1 single-source research role | one genuine pinned Hermes parent in isolated fake/offline model runner | incremental claims/quality, permission and provenance |
| B2 A3/A4 paired | genuine upstream two-child delegation, independent blinded first-pass, then native cooperation | true child witness+quote and conflict fixture; measure false positives, not just disagreements |
| B3 conditional nine-role route | only roles justified by task predicates; native A5–A8 and read-only A9 | per-role triggered/skipped/refused counts, consumer linkage, crash replay, terminal usage |

**Dataset:** hold a fixed labelled engineering fixture set (source/rule/claims, wallets, related markets, book gaps, failure injected data) and a sealed holdout with same-case comparisons, source cutoff and model/prompt versions bound before running. Developer tests may see development fixtures; only independent reviewer sees sealed final holdout. A provider model test after owner's technical witness authorization measures software behavior, **not trading edge**. Genuine later-market outcomes are forbidden before owner full-system unlock.

**Ablation truth:** model duplication can share correlated errors; independent sessions do not imply independent evidence or models. Require A4 legitimate-positive as well as adversarial-negative fixtures. A9 suggestion count is not benefit; acceptance is verified reproducibility and later externally reviewed improvement. Report uncertainty and regression, including token savings that *worsen* correctness.

## State, persistence, rollback and permissions

- Suggested policy chain: `PROPOSED → SIDE25_REVIEWED → OWNER_APPROVED_NON_ECONOMIC → VERSIONED_ACTIVATED → SUPERSEDED/ROLLED_BACK`. Only an approved routine coordinating policy may become active; no qualified strategy/capital/order authority can flow from these states.
- Proposed feedback action cannot rewrite `ResearchEpisode`, immutable forecast, original study denominator, license/permissions or provider grant; replay reads original exact SHA and may only append permitted later linked proposal.
- Restart: unfinished provider attempt stays `UNKNOWN_RESULT_QUARANTINED`, no invisible retry or model re-billing; read-only recovery reconciles actual session event and ledger before continuing.
- Versioned cost ceiling/route rules are separate from owner economic policies; no agent can change hard risk, Gate B/C, signer or live permissions.
- This improvement architecture adds **no new database by default**. Store feedback and proposals via existing append-only research/manager/Side25 review surfaces where their schemas permit; implement a narrow immutable record only if no existing object can express the necessary linkage.
