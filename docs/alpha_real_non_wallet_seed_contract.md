# S10-ALPHA-REAL-01 — First Real Non-Wallet Alpha Evidence Seed Contract

Status: Phase-A contract. The frozen package is `docs/wp_specs/S10-ALPHA-REAL-01/`
(prompt SHA-256 `c7f607f1f388b33b696c228b5393eace5048bbeb87d06343323d52ca5c39e5ea`, spec SHA-256
`9745d4ceb68c7332d1faed7c10509a949507943191ecd956c51c65bf9edd8e5d`). The operator is
`tools/alpha/run_s10_alpha_real_01.py`; its tests are `tests/tools/alpha/test_run_s10_alpha_real_01.py`.
Base `f74e183a514d21a28013bf433c79126a68c72389`. Governance track RUNTIME, risk 3, exact 12-path scope.

## 1. Purpose

Produce the first genuine NON-WALLET Alpha Factory research lineage for one frozen research
program, using at most one controlled Hermes v0.21.3 public-web research-child launch, one Side13
result-state decision and the merged Alpha Factory builders/registry unchanged. The contract
separates evidence formation from qualification: it creates no QualificationCandidate and no
S10-GATE-QUAL-01 evaluation.

RESEARCH_SUPPORTIVE is NOT qualified, NOT OOS positive, NOT executable edge, NOT profitable, NOT
paper ready, NOT live ready and NOT Gate C. A negative or inconclusive result is a legitimate
completed research result and stays in canonical Alpha memory.

## 2. Frozen research program

NWS-resolved Polymarket daily-rain / precipitation markets. Exact research question:

> Are contract-specific official NWS precipitation forecasts and observations for Polymarket
> daily-rain markets sufficiently repeatable, point-in-time observable and falsifiable to justify
> later deterministic testing of whether public non-market weather information adds predictive
> information beyond contemporaneous Polymarket market probability?

Forbidden research outputs: current market probability estimate, side/entry/exit recommendation,
position size, expected return, profitability claim, trade/paper/live-ready claim.

## 3. Runtime bounds (separately activated)

- Call path: merged `run_controlled_hermes_research` with `DEFAULT_HERMES_INVOCATION_POLICY`
  (policy id `hermesinvocationpolicy:sha256:18b8f788fa436712b377c81b10bdbd594cdb7afb3844fcc8559fde3b28c25e81`)
  and `context_mode=False`; `run_blind_phase` is not used.
- Expected request id
  `hermesresearchrequest:sha256:efca8c27a92b32282cac6bee0a7a6d2455da590bdc54f6b883bfc16308bfdf2d`
  (provider label `openai-codex`, model label `gpt-5.6-sol`, category `fundamental`, 12 sources,
  300 s, 1,000,000 bytes).
- Maximum controller executions 1; maximum research-child launches 1; automatic controller
  rerun, replacement run, content/schema rerun, provider/model fallback and backend
  fallback/rescue all 0. The one child may make several provider API requests (reported as
  `api_call_count`); the policy's same-provider internal recovery is not a second run.
- USD 5 is the accepted REPORTED estimated-cost ceiling (merged post-run gate), not
  invoice-attested and not a pre-spend limit.
- The Hermes web-only backend may read public HTTPS Polymarket rule/market pages as untrusted
  evidence; the repo/operator makes no Gamma, CLOB, Data API, RPC or WebSocket call.

## 4. Executable, home and human credential checkpoint

Pinned executable `C:\Users\dersu\polymarket-h1-runtime\hermes-agent-v0.21.3\.venv\Scripts\hermes.exe`;
pinned dedicated research home `C:\Users\dersu\polymarket-alpha-real-01\hermes-home` (the AF1 and
H1 homes are not reused). The operator checks names and the merged safe/clean predicates only and
runs the merged offline `--version` / `--help` probes; it never reads, creates, edits or echoes
credential content and never creates the home. A missing home stops
`HUMAN_CREDENTIAL_SETUP_REQUIRED` (non-consuming); Karl performs the OAuth and Firecrawl setup
manually and confirms with `I_CONFIRM_S10_ALPHA_REAL_01_HERMES_HOME_CREDENTIAL_SETUP_COMPLETE`.

## 5. Activation and attempt consumption

`prepare` writes the inventory and the activation envelope (bound to the Phase-A head) under
`local_data/s10_alpha_real_01/attempt-01/`. `run-real` requires the envelope SHA-256 named in
Karl's runtime authorization, `I_AUTHORIZE_EXACT_S10_ALPHA_REAL_01_RUNTIME_ENVELOPE`, the
credential confirmation, the unchanged clean head and every local check again. The capture backend
creates the attempt sentinel exclusively immediately before its one delegated `invoke`, so
attempt consumption coincides with the research-child launch. Any earlier failure is
`PRE_RUNTIME_STOP` with zero launches.

## 6. Full-draft capture and revalidation (closes the merged-API gap)

Merged `ValidatedResearchDraft` keeps only request id, summary, confidence, source references,
source URLs and falsification checks. The operator therefore wraps the merged backend, keeps the
bounded stdout in memory, re-applies merged `capture_final_response` and `validate_research_draft`
(receipt request id, 12 sources, context mode off) and requires equality with the controller's
validated draft on those six fields. Only then it builds `FULL_DRAFT_PROJECTION` (summary,
confidence, the eight research lists, and `{title, url, source_class}` sources) and persists that
projection, its SHA-256 and the sanitized receipt. Mismatch is `RUNTIME_FAILURE` /
`DRAFT_REVALIDATION_MISMATCH`. Raw stdout, stderr, environment and credentials are never persisted
or printed.

## 7. Side13 decision

The decision file has exactly `schema_id`, `schema_version`, `wp_id`, `reviewer`, `request_id`,
`hermes_receipt_id`, `full_draft_projection_sha256`, `review_bundle_sha256`, `result_state`, and
selects one of RESEARCH_SUPPORTIVE, NO_EDGE_CURRENTLY, HYPOTHESIS_FALSIFIED, DATA_INSUFFICIENT,
WATCH_FOR_CHANGE. It cannot edit research content; the operator has no default state. A state
whose required list (evidence_for / evidence_against / evidence_against / known_missing_data /
what_would_change_the_conclusion) is empty stops `REVIEW_STATE_EVIDENCE_MISMATCH`.

## 8. Alpha records and registry

Expected candidate id `alphacandidate:sha256:2d1523c8086acf536ad07512e1eaffed9cb9405b65e83c87b89b40ba77ee3add`
and family id `alphafamily:sha256:136000bd56f2fc27cf490cf675ddf2715b0acfc1ee934aa5cdf2579925c208d8`
(lanes HISTORICAL_REPEATABILITY, RESOLUTION_RULES, WEATHER; mechanism key
`nws-public-weather-vs-market-probability`; NON_WALLET). The episode copies the projection lists
verbatim, takes the decision state, producer `HERMES_CONTROLLED_RESEARCH`, the receipt id as
producer receipt and only deterministic evidence ref, and the receipt end time as
`research_as_of`. Sources map official->OFFICIAL, news->NEWS, reference->REFERENCE,
public_market_data->PUBLIC_MARKET_DATA, academic/other_public->OTHER_PUBLIC; `content_sha256` is
null because page bytes were not captured.

The dedicated registry is `local_data/s10_alpha_real_01/attempt-01/alpha_registry.sqlite3`.
finalize-alpha appends the full batch atomically only into an empty registry, returns
`IDEMPOTENT_FINALIZED_SUCCESS` when exactly the expected records are present, and otherwise stops
`ALPHA_FINALIZATION_CONFLICT` (the merged registry itself accepts divergent sibling episodes, so
this exact-set check is mandatory). It reloads and verifies chain, head, ids and counts.

## 9. Terminals and successor

ALPHA_REAL_01_SUPPORTIVE, ALPHA_REAL_01_NON_SUPPORTIVE, ALPHA_REAL_01_INSUFFICIENT,
ALREADY_SATISFIED_EXISTING_ALPHA, RUNTIME_FAILURE, PRE_RUNTIME_STOP. Only a verified unique current
RESEARCH_SUPPORTIVE leaf for the expected candidate/family (or verified
ALREADY_SATISFIED_EXISTING_ALPHA) makes S10-QUAL-REAL-01 eligible to be DRAFTED separately. No
terminal authorizes qualification.

## 10. Non-authority

No src/** change, workflow or dependency change, operator credential access, scheduler, strategy,
paper, execution, live, OMS, risk, orders, signing, Gate C, capital, QualificationCandidate,
S10-GATE-QUAL-01 evaluation, WP170/WP172/WP173, wallet evidence, H1 #5 or merge. Capital at risk:
USD 0. Merge: NOT AUTHORIZED.
