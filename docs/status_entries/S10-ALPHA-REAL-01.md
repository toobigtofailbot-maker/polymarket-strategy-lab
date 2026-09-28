# S10-ALPHA-REAL-01 Status

## Identity

- WP ID: `S10-ALPHA-REAL-01` — First Real Non-Wallet Alpha Evidence Seed
- Base: `f74e183a514d21a28013bf433c79126a68c72389`
- Predecessor: PR #199 / `S10-TEST-WS-01`, head `99c300421f3404a68b573674d1d6d09e8c363412`, MERGED at
  the base SHA; qualification capability predecessor PR #198 / `S10-GATE-QUAL-01`, head
  `ec97a25b3e3174bfa71e3799110e729247dfa026`, merged at `d7891ed63b4c58c9cc150cd0c750c262ca8e5a74`
- Package class: `FIRST_REAL_NON_WALLET_ALPHA_EVIDENCE_SEED`; size L
- Governance: RUNTIME, risk 3, capital at risk USD 0; no draftability certificate required
- Frozen package: prompt SHA-256 `c7f607f1f388b33b696c228b5393eace5048bbeb87d06343323d52ca5c39e5ea`,
  spec SHA-256 `9745d4ceb68c7332d1faed7c10509a949507943191ecd956c51c65bf9edd8e5d` (materialized
  byte-for-byte)
- Scope: exactly 12 paths; no `src/` change; dependencies, locks and workflows unchanged
- Branch: `claude/s10-alpha-real-01-seed-746777` (the pinned existing clean session branch)
- Readiness: `IMPLEMENTATION_READY` (governance track RUNTIME, minimum RUNTIME, 12 files)
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body (created Ready for Review, never Draft).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit
  containing itself.
- Merge commit: not merged; merge NOT AUTHORIZED by the executor
- Merge authorized: NO

## Current State

- Current S10-ALPHA-REAL-01 state: ALPHA_REAL_01_SUPPORTIVE
- Real research-child launch occurred: YES (exactly one; launch count 1)
- Attempt consumed: YES (attempt-01; no rerun, no replacement, no attempt-02)
- Real Alpha lineage created from provider research: YES
- Side13 research disposition: RESEARCH_SUPPORTIVE (decision file SHA-256
  `e31d98dd5909ceaa77759932103f878d5c26624366e140ac07a395f8966e96dd`)
- S10-QUAL-REAL-01 draft eligibility: YES (DRAFT-ELIGIBLE only)
- S10-QUAL-REAL-01: NOT AUTHORIZED
- Gate C: NOT AUTHORIZED
- Capital/orders: 0

Phase A delivers the manual foreground operator `tools/alpha/run_s10_alpha_real_01.py` (prepare,
verify-local, run-real, verify-run, build-review-bundle, verify-review, finalize-alpha,
verify-final), its focused tests, the contract `docs/alpha_real_non_wallet_seed_contract.md` and
bounded repo-truth updates. Tests use the merged FakeHermesBackend behind the operator capture
backend and temporary registries only.

- Frozen research program: NWS-resolved Polymarket daily-rain / precipitation markets; research
  question byte-identical to the frozen package.
- Runtime bounds (not yet activated): merged `run_controlled_hermes_research`,
  `DEFAULT_HERMES_INVOCATION_POLICY`, `context_mode=False`; maximum controller executions 1,
  maximum research-child launches 1; rerun, replacement, content/schema rerun and fallbacks 0;
  USD 5 accepted REPORTED estimated-cost ceiling (not invoice-attested).
- Expected ids: request
  `hermesresearchrequest:sha256:efca8c27a92b32282cac6bee0a7a6d2455da590bdc54f6b883bfc16308bfdf2d`,
  candidate `alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`,
  family `alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`.
- Tool-side full-draft capture/revalidation closes the merged `ValidatedResearchDraft` list gap
  without a `src/` change (deferred S10-ALPHA-REAL-01-D001).
- The merged Alpha registry accepts divergent sibling episodes, so finalize-alpha enforces an
  exact expected record-set check (empty -> atomic append; exact -> IDEMPOTENT_FINALIZED_SUCCESS;
  otherwise ALPHA_FINALIZATION_CONFLICT).
- The pinned dedicated research home `C:\Users\dersu\polymarket-alpha-real-01\hermes-home` was
  set up manually by Karl (HUMAN_CREDENTIAL_SETUP_REQUIRED closed); the operator never read,
  created or echoed credential content.
- RESEARCH_SUPPORTIVE is not qualified, OOS positive, executable edge, profitable, paper ready,
  live ready or Gate C.

## Post-Runtime Verified Evidence (attempt-01)

- Phase-A commit (implementation and runtime execution head):
  `4db1cb8e4ffa9cb6122f064faab82d379c74ad44`; operator, tests, prompt and spec bytes are unchanged
  after the runtime. The post-runtime reconciliation changes only six predetermined docs paths.
- Runtime authorization: Karl authorized activation envelope SHA-256
  `eee8003c216cfd892f54666c030520ec2b8920d20a52d222401e3e7f48c24af0` after Side13 independent
  envelope review; `prepare` / `verify-local` returned LOCAL_PREFLIGHT_VALID (safe/clean home,
  offline Hermes 0.21.3 version and startup probes PASS) before the launch.
- `run-real`: exit 0, `RUN_VALIDATED`, research-child launch count 1, receipt terminal
  `RESEARCH_DRAFT_VALIDATED`, transport_attempt_count 1, api_call_count 9 (all inside the one
  child), verified provider/model `openai-codex` / `gpt-5.6-sol`, start 2026-09-28T20:12:11Z,
  end 2026-09-28T20:16:34Z.
- Reported token counts: 98,271 input, 7,284 output, 582,611 total (as reported by Hermes).
- Accepted REPORTED estimated cost: USD 0.0 with cost status `included` and cost source `none`
  (not invoice-attested).
- Hermes receipt id
  `hermesresearchreceipt:sha256:69037db6d6df59283da89110998ef17d2854c73c29052039b20acb89ac6cbd0f`;
  request id
  `hermesresearchrequest:sha256:efca8c27a92b32282cac6bee0a7a6d2455da590bdc54f6b883bfc16308bfdf2d`.
- FULL_DRAFT_PROJECTION SHA-256
  `d23f304d57eef4d6dc05ee73afe98227d15dbc5a4334aa630569084b17b78064` (tool-side revalidation
  matched the controller's six retained fields); review bundle SHA-256
  `14ec89f6760d3d2ae0b2c4751ddc8ec647d1e65b2350735d1b5810e622478be6`.
- verify-run: RUN_EVIDENCE_VALID; verify-review: REVIEW_DECISION_VALID
  result_state=RESEARCH_SUPPORTIVE; finalize-alpha: ALPHA_REAL_01_SUPPORTIVE APPEND_COMMITTED;
  verify-final: FINAL_EVIDENCE_VALID ALPHA_REAL_01_SUPPORTIVE s10_qual_real_01_draft_eligible=True.
- Sources: 12 cited, 12 usable, 0 excluded (classes official, reference, public_market_data;
  `content_sha256` null for every source). Source-reference ids:
  `alphasource:sha256:04d839c75c79d07059b4e0cf2f7dd6489250d75c58a5effdb0f0834df83fded5`,
  `alphasource:sha256:1bdd1e499fcf53a72dda134609eb1f8770ea86cbf62b1bb35b27f0bfccce236a`,
  `alphasource:sha256:2dc7bb29edc9311d228f39f7ccf36710c74b67dccf61cc88dbaf9a0e7217c30a`,
  `alphasource:sha256:47655116eacfb649807b79e42565660ff18f1e3b1c210ac04d546fe8f67b75a2`,
  `alphasource:sha256:4bcaba493fe97e20e7c824541671412ca60d6293391552a4e0133a0b36d580ed`,
  `alphasource:sha256:57a4a42e3b815013b3955a1503ac6235fe448ebccfcbe7b8327a61c9cbf68819`,
  `alphasource:sha256:620572eaf6d4b17611d8dc2cf3f3484c4dbc51e096c5aa4fe3f711f0b9aad619`,
  `alphasource:sha256:6fae2f59ab029c06b39784ce710b61cc58359becccccd0251df4d109a052da4b`,
  `alphasource:sha256:929a3bd480eb9bccce3abd4cbe535eb06cdcc4819167f019618d9d1375b49eaf`,
  `alphasource:sha256:a1115a36ad8b202d11f6c05db271233e27deb84fa3177032892024f4961f03f2`,
  `alphasource:sha256:b059c19160c2274f59e57c5cfffb0b81241b31d6d89bbd700ac0e9dc43bdc04b`,
  `alphasource:sha256:dff1e0433281aefd08a96f9575fb89f5f7f525f20b23f2f35ec02bb6a0fc9b19`.
- Candidate id `alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`;
  hypothesis family id `alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`;
  research episode id `alphaepisode:sha256:2e4c0f484649930ba2677bc360070f0e9ba6ef0e09ecd23b383a32ff3b69000c`
  (unique current leaf, result_state RESEARCH_SUPPORTIVE, confidence label `moderate`).
- Dedicated ignored registry `local_data/s10_alpha_real_01/attempt-01/alpha_registry.sqlite3`:
  15 rows (12 sources, 1 candidate, 1 family, 1 episode), head entry hash
  `alpharegistryentry:sha256:4b9a20f7f0e931dfea7cced80a64d7a4be7ccc58e265dbb9ebde15edb2d79847`;
  local final-evidence SHA-256 `961a23eedc790d5b2dfd38b72d4e3909692dd95bb3e76f7d9183f327b9984817`.
- Protected prior AF1/H1 evidence: 34 files, digest
  `77d936982558b5bf5a44d691bb1b544327162662c9e98e9f523a148962bb34bf`, unchanged at verify-final.
- Final terminal: ALPHA_REAL_01_SUPPORTIVE.

Meaning of RESEARCH_SUPPORTIVE here (Side13): the mechanism is sufficiently evidence-grounded and
falsifiable that further deterministic qualification/data-readiness work may be worthwhile. It is
NOT a claim that weather information beats market probability, NOT a qualification PASS, NOT OOS
evidence, NOT executable edge, NOT expected return or profitability and NOT paper/live/Gate-C
authority. Qualification/data readiness is NOT proven: the missing historical-vintage,
price-construction, rule-census, sample/power and PIT facts remain explicit, and S10-QUAL-REAL-01
must independently establish real dataset refs, PIT provenance, sample/power, a B0/B1/B2 or generic
metric plan, critical execution evidence and exact AF1 binding (S10-ALPHA-REAL-01-D005).
QualificationCandidate created: NO. Qualification gate run: NO. Second research launch: NO.

## Authority Posture

- Package class: FIRST_REAL_NON_WALLET_ALPHA_EVIDENCE_SEED
- Implementation authority: YES (Phase A only)
- Report/export authority: NO
- Paper authority: NO
- Execution authority: NO
- Live authority: NO
- Credential authority: NO
- Runtime/scheduler authority: one separately authorized research-child launch only (consumed);
  no scheduler, no rerun
- Canonical evidence authority: operator, focused synthetic tests and docs; one real non-wallet
  Alpha lineage in the dedicated ignored local registry (RESEARCH_SUPPORTIVE)
- Network authority: Phase A used workflow network only (Remote Main Sync Gate git fetch, branch
  push, Ready-for-Review PR publication, hosted-CI observation). The single authorized runtime
  launch used the pinned Hermes child's provider and web-research network (openai-codex /
  gpt-5.6-sol, web-only backend); the operator made no Polymarket product API call
- Dependency-change authority: NO

## Scope Boundary

Changed files (exactly 12):
- `docs/alpha_real_non_wallet_seed_contract.md`
- `docs/deferred_items_log.md`
- `docs/long_term_bot_completion_roadmap.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/status_entries/S10-ALPHA-REAL-01.md`
- `docs/wp_specs/S10-ALPHA-REAL-01/wp_prompt.txt`
- `docs/wp_specs/S10-ALPHA-REAL-01/wp_spec.json`
- `tools/alpha/run_s10_alpha_real_01.py`
- `tests/tools/alpha/test_run_s10_alpha_real_01.py`
- `tests/test_project_status_docs.py`
- `tests/test_repo_truth_docs.py`

Forbidden prefixes: `src/`, `.github/workflows/`, `local_data/`, `credentials/`, `secrets/`,
`agent_memory/`, `agent_runtime/`, dependency and lock files.

## Validation Summary

Post-runtime reconciliation: verify-final rerun PASS; focused docs tests PASS; exact six-path
post-runtime diff; operator/test/prompt/spec bytes unchanged; results recorded in the PR body.

D006 micro-amendment (Side13-authorized, test-only, after the runtime): the non-hermetic
`test_cli_prepare_prints_closed_code_only` now injects the missing-home checkpoint through the
operator `check_home` seam instead of depending on the real pinned research home; exactly three
paths changed (this fragment, the deferred log and the operator test file). Operator, `src/`,
prompt and spec bytes are unchanged. Runtime evidence remains the exact original attempt-01
evidence; no second research launch occurred; the Alpha registry was not mutated and the terminal
remains ALPHA_REAL_01_SUPPORTIVE. A fresh authoritative full suite and new exact-head hosted CI are
recorded in the PR body.


- Focused tests: `python -m pytest -q tests/tools/alpha/test_run_s10_alpha_real_01.py` -> PASS
- Docs tests: `python -m pytest -q tests/test_project_status_docs.py tests/test_repo_truth_docs.py` -> PASS
- Full pytest: `python -m pytest -q` -> recorded in the PR body for the exact tested head
- Readiness: `python tools/wp/wp_readiness_gate.py --wp docs/wp_specs/S10-ALPHA-REAL-01/wp_prompt.txt --spec docs/wp_specs/S10-ALPHA-REAL-01/wp_spec.json --repo-root . --check-diff --base f74e183a514d21a28013bf433c79126a68c72389 --head HEAD` -> IMPLEMENTATION_READY
- Generated artifact guard, `pip check`, `git diff --check`: recorded in the PR body
- Security checks: recorded in the PR body; unavailable scanners are reported UNAVAILABLE, never PASS

## Deferred Items

- Added: S10-ALPHA-REAL-01-D001 (merged draft list retention), D002 (receipt binds no response
  digest), D003 (webpage content bytes not captured), D004 (cost evidence reported-estimate only),
  D005 (qualification/data readiness not proven; handed to S10-QUAL-REAL-01), D006 (non-hermetic
  operator CLI test; RESOLVED_IN_PR200_D006_MICRO_AMENDMENT).
