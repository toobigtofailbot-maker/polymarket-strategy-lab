# Long-Term Bot Completion Roadmap

## A. Status

- WP: WP52 (merged; merge commit 259fac091a3b8d0d22aaab13345f440d5a958af2); WP55 (resolution ambiguity taxonomy/manual-label workflow merged); WP56 (label schema validation merged; merge commit a310e641eb790bd3906d054d703dd11945180e6c); WP57 (local/offline/read-only feature extraction from validated labels merged); WP60A (agent-neutral startup layer merged); WP61 (architecture direction lock-in and microstructure quality metadata merged); WP62 (cross-market relationship metadata merged); WP63 (resolution source hierarchy metadata merged; merge commit e1ab1aa7e0915a3c65afc9eb5a55c58292ef6910); WP64 (research queue/report/session packet merged; merge commit 7795efd45b19ab89c943bd49602449baa67411db); WP65 (local research queue export/operator runbook merged; merge commit 5c5b0c7ef8a2d1f094a2eff6dabbe6fd4be434f7); WP75 (human review label fixture loader merged; PR #76 merge commit 0160ac1c7087625a4596edd541524445bc004bd5); WP76 (wallet intelligence roadmap lock-in merged; PR #77 merge commit 91cd26e4fe16d492fa2f7b319fba176ee60cd9d5); WP77 (wallet intelligence architecture/profile/signal contract on branch)
- Package class: DOCS_ONLY_ROADMAP_MERGED; RESOLUTION_AMBIGUITY_TAXONOMY_MERGED; RESOLUTION_AMBIGUITY_LABEL_SCHEMA_VALIDATION_MERGED; RESOLUTION_AMBIGUITY_LABEL_FEATURE_EXTRACTION_MERGED; ARCHITECTURE_DIRECTION_MERGED; LOCAL_OFFLINE_READ_ONLY_MICROSTRUCTURE_QUALITY_MERGED; LOCAL_OFFLINE_READ_ONLY_CROSS_MARKET_RELATIONSHIP_METADATA_MERGED; LOCAL_OFFLINE_READ_ONLY_RESOLUTION_SOURCE_HIERARCHY_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_REPORT_SESSION_PACKET_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_EXPORT_OPERATOR_RUNBOOK_MERGED; HUMAN_REVIEW_LABEL_FIXTURE_LOADER_MERGED; DOCS_TESTS_ONLY_WALLET_INTELLIGENCE_ROADMAP_LOCKIN_MERGED; DOCS_SCHEMA_TESTS_ONLY_WALLET_INTELLIGENCE_CONTRACT_ON_BRANCH
- Side onboarding lock: SIDE4_ONBOARDING_LOCK_MERGED
- Authority: PLANNING_GUIDANCE_ONLY
- NOT_AUTHORIZATION
- NO_RUNTIME_CHANGE
- NO_SOURCE_CHANGE
- NO_TOOLS_CHANGE
- NO_DEPENDENCY_CHANGE
- NO_NETWORK
- NO_TRADING_EXECUTION
- NO_PAPER_TRADING
- NO_HERMES_RUNTIME
- NO_AGENT_RUNTIME
- NO_CREDENTIALS
- NO_SCHEDULER
- NO_BOT_LOOP
- WP51 merge commit: c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f
- WP53 merge commit: 7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6
- WP54 merge commit: fb45fb849b0641e2007ef66f50bfd5725354b8f0
- WP76 merge commit: 91cd26e4fe16d492fa2f7b319fba176ee60cd9d5

## B. Purpose

This document locks the long-term bot-completion roadmap into repo truth for
future Side chats, Claude Code/Codex sessions, and reviewers.

It explains what is already built, what is missing, and how many WP phases
remain before this project becomes a real paper-trading or live-trading bot.

**This is planning guidance only.** It does not approve any future implementation,
paper trading, live trading, execution, credentials, scheduler, bot loop,
Hermes/agent runtime, wallet-copying, or autonomous agent runtime. Each future
phase requires its own explicitly approved work package.

## C. Current Simple-State Summary

The project currently has blueprints, safety rules, a core scorer, a direction
lock, and the first feature-extraction foundation.

It does not yet have a finished trading bot. It cannot yet decide trades,
simulate realistic fills, place orders, manage live risk, or run autonomously.

**Self-driving-car analogy:** We have the garage rules, the safety checklist,
and the first engine block. The sensors, navigation system, test track, brakes,
steering wheel, dashboard, and road permission are not yet fully built.

More precisely:
- Garage rules and safety checklist → repo governance, protected boundaries,
  Codex workflow discipline
- First engine block → WP49 core scorer + WP51 feature extraction foundation
- Sensors → feature extraction for microstructure, resolution ambiguity,
  calibration data
- Navigation → research strategy layer, hypothesis engine
- Test track → paper-trading engine
- Brakes → risk engine and kill switches
- Steering wheel → live execution gateway
- Dashboard → operational monitoring, reporting, deployment
- Road permission → authenticated client, credentials, live-trading
  authorization

## D. Current Repo-Built Components

The following capabilities are built and merged into repo truth as of WP52:

1. **Repo-truth governance** — AGENTS.md, CODEX_START_HERE.md, authority
   hierarchy, protected-boundary rules, Codex execution guidelines, WP
   template, review checklist, testing requirements.

2. **Codex/PR evidence discipline** — PR evidence reporting discipline
   (WP45), PR evidence consistency guard (WP46), posted PR evidence review
   hardening (WP47), validation matrix, PR review checklist.

3. **Local/offline/read-only snapshot and data layer** — Polymarket public
   endpoint adapter, snapshot capture (WP10/WP18), snapshot reader, market
   catalog (WP11), snapshot quality gates (WP12/WP19), deduplication and
   catalog exports (WP13), read-only polling runner (WP17).

4. **Local artifact quality/reporting basis** — Local reports (WP12/WP19),
   quality gate framework, sanitized catalog export layer.

5. **Advisory read-only/Hermes boundary docs** — AI-agent integration
   policy (WP20), Hermes read-only boundary (WP20), agent model registry
   (WP20), agent context export schema (WP21), advisory runtime boundary
   design (WP39), agent/Hermes manual setup decision record (WP27).

6. **Local advisory consumer/reporting pieces** — Local read-only agent
   context exporter (WP23), analyst report generator (WP25), local advisory
   consumer prototype (WP40), advisory prompt/runbook package (WP41),
   advisory consumer operator workflow (WP42), token-efficiency helper stack
   (WP28-WP37).

7. **Market Research Priority Scoring design** — Docs-only scoring layer
   design (WP44).

8. **Output contract** — Binding schema/output contract (WP48) defining
   top-level fields, score components, advisory-only labels,
   staleness/provenance/missing-data contracts, and forbidden fields.

9. **Core scorer** — Local/offline/read-only core scorer (WP49):
   `src/data_layer/market_research_priority_scoring.py`, stdlib-only,
   in-memory output only, advisory-only.

10. **Feature extraction foundation** — Local/offline/read-only first feature
    extraction module (WP51):
    `src/data_layer/market_research_priority_features.py`, bridges snapshot
    artifacts into prepared scorer inputs.

11. **Research data foundation direction lock** — Locked direction document
    (WP50), approved near-term sequence, blocked directions, non-signal
    semantics.

12. **Resolution ambiguity taxonomy and manual-label workflow** — Docs/schema/tests-only
    taxonomy document (WP55) on branch: 14 ambiguity categories, review status values,
    severity/confidence separation, 17-field manual label schema, local/offline/read-only
    human review workflow. Research-data-quality metadata only; no parser, no feature
    extraction, no scorer integration in WP55.

13. **Architecture direction lock-in** — WP61 adds
    `docs/architecture_decision_record.md` with planning constraints only:
    SQLite first/Postgres later if needed; Streamlit first/Grafana later/Next.js
    only if productizing; local development first/cheap VPS later; rules-based
    plus research-score-driven first; LLM read-only analyst/proposal layer only;
    research-only -> paper -> dry-run -> manual live approval -> restricted live.

14. **Microstructure Quality V1 metadata** — WP61 adds advisory-only
    `microstructure_quality` metadata to prepared market contexts from local
    order-book snapshots only. It is not a score component and does not change
    scorer weights.

15. **Protected boundaries** — Live trading DISABLED; credentials NOT_USED;
    execution NOT_STARTED; authenticated client FORBIDDEN_UNTIL_APPROVED_WP;
    Hermes NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY; agent runtime NOT_STARTED;
    agent execution authority FORBIDDEN; fully autonomous trading agent
    EXCLUDED_FOR_NOW; scheduler NOT_STARTED; bot loop NOT_STARTED.

16. **Wallet intelligence roadmap and contract** — WP76 locks top-wallet
    intelligence as a future advisory research signal layer, not a blind
    copy-trading engine. WP77 adds docs/schema/tests-only architecture,
    watched-wallet profile, registry status, signal contract, copyability status,
    suspicious-flow, and safety-flag design. No wallet data loader, wallet API
    client, real wallet monitoring, automatic copy-trading, paper/live trading,
    credentials, or execution behavior is authorized.

## E. Missing Major Capabilities

The following major capabilities are not yet complete as of WP52. Each
requires one or more explicitly approved future work packages.

- Robust scanner and refresh pipeline for scoring outputs
- Resolution-rule ambiguity feature extraction and automated parser (taxonomy and
  manual-label workflow defined in WP55; automated extraction and parser remain not started)
- Microstructure quality features beyond basic order-book availability
- Local scoring export and report integration (CLI/export/report writer)
- Calibration and resolved-outcome validation harness
- Research strategy layer (hypothesis engine, market-selection logic)
- Paper-trading engine (realistic fill simulation, P&L tracking)
- Risk engine and kill switches (position limits, drawdown gates, emergency
  stops)
- Authenticated client boundary, credentials handling, wallet/signing
  infrastructure
- Live execution gateway (order placement, cancellation, order management)
- Scheduler and bot loop (recurring jobs, health monitoring)
- Operational monitoring, dashboard, and deployment infrastructure

## F. Milestones

These are rough planning ranges, not commitments. Repo truth, implementation
discoveries, and future user decisions may change these estimates.

All ranges are measured from the WP51/WP52 baseline.

| Milestone | Description | Estimated WPs from baseline |
|---|---|---|
| Research Intelligence Bot | A bot that can score, rank, and report market research priorities for human review, with honest data quality signals. Not a trading bot. | 15-25 WPs |
| Paper Trading Bot | A bot that can simulate paper trades with realistic fill assumptions and track simulated P&L, without real orders. | 45-75 WPs |
| Controlled Live Bot | A live bot that can place and cancel real orders in a controlled scope, with human-review gates and kill switches. | 75-110 WPs |
| Robust Autonomous-ish Bot | A bot that can run with reduced human review for defined market categories, with strong risk controls and monitoring. | 100-160 WPs |

Earlier aggressive or minimal estimates are not authorization to skip gates.

## G. Phase Roadmap

Each phase below has a short layman explanation and an analogy. WP ranges are
rough planning estimates from the WP51/WP52 baseline, not commitments.

### Phase 1: Data Foundation and Feature Extraction

**What:** Build all the sensor inputs the bot needs to evaluate markets —
staleness tracking, resolution rule signals, microstructure quality,
provenance enforcement.

**Analogy:** Give the bot eyes.

**Estimated range:** 6-10 WPs

Includes: provenance/staleness hardening, resolution-rule ambiguity taxonomy
and extraction, microstructure quality features, CLI/export/report writer for
local scoring integration.

### Phase 2: Market Understanding, Resolution, and Graphing

**What:** Teach the bot the rules of each market — how markets resolve, which
markets are related, and how to reason about ambiguous resolution.

**Analogy:** Teach the bot the rules of the game.

**Estimated range:** 10-16 WPs

Includes: resolution-rule taxonomy, manual label workflow, basic resolution
metadata extraction, metadata-only cross-market relationship graph.

### Phase 3: Microstructure and Liquidity Quality

**What:** Check the microstructure quality indicators of each market — spread,
depth, slippage. These are data-quality inputs, not trade-readiness signals.

**Analogy:** Check whether the road is drivable.

**Estimated range:** 8-14 WPs

Includes: spread bps, depth buckets, slippage estimates as microstructure
quality indicators and execution realism inputs for later approved simulation
work only. Not tradability. Not execution confidence. No fill-probability
implementation is approved by this roadmap. No trade-readiness signal.

### Phase 4: Scoring Output, Reporting, and Human Workflow

**What:** Build the dashboard-like output that lets a human researcher
understand, trust, and act on the scoring layer before any automation is
added.

**Analogy:** Build the dashboard before adding autopilot.

**Estimated range:** 7-12 WPs

Includes: CLI/export integration, local report generation, advisory consumer
integration, human-review workflow, staleness and quality summaries.

### Phase 5: Calibration and Validation

**What:** Check whether the compass points north — verify that the scoring
layer's outputs correlate with historical reality using resolved outcomes.

**Analogy:** Check whether the compass points north.

**Estimated range:** 8-15 WPs

Includes: resolved-outcome dataset validation, calibration harness design,
score-to-outcome correlation analysis, re-calibration workflow.

### Phase 6: Research Strategy Layer

**What:** Teach the bot how to think about market selection, but not how to
act — build the hypothesis generation and research priority logic.

**Analogy:** Teach the bot how to think, but not act.

**Estimated range:** 8-14 WPs

Includes: research hypothesis engine, market-selection logic, strategy
research framing, advisory-only output with no execution authority.

### Phase 7: Paper Trading

**What:** Run the bot on a flight simulator before flying the real plane —
simulate trades with realistic fill assumptions and track simulated P&L.

**Analogy:** Flight simulator before flying.

**Estimated range:** 12-20 WPs

Includes: paper-trading engine, realistic fill simulation, simulated P&L
tracking, paper-trading safety gates, no real orders.

### Phase 8: Risk Engine and Kill Switches

**What:** Build the brakes — position limits, drawdown gates, emergency stops,
kill switches, and risk controls required before any live order is placed.

**Analogy:** Build the brakes.

**Estimated range:** 10-16 WPs

Includes: position limit guards, drawdown gates, emergency stop logic, kill
switch design, risk engine design, safety gate enforcement.

### Phase 9: Live Execution

**What:** Connect the steering wheel to the real car — build the execution
gateway that places and cancels real orders, with authenticated credentials
and signing.

**Analogy:** Connect the steering wheel to the real car.

**Estimated range:** 14-25 WPs

Includes: authenticated client integration, credentials handling,
order placement and cancellation, order management system, execution boundary
review, live-trading authorization.

### Phase 10: Scheduler, Bot Loop, Monitoring, and Operations

**What:** Let it run without falling asleep — add scheduling, health
monitoring, operational dashboards, alerting, and deployment infrastructure.

**Analogy:** Let it run without falling asleep.

**Estimated range:** 10-18 WPs

Includes: scheduler design, bot loop, health monitoring, alerting,
operational dashboard, deployment infrastructure, incident response.

## H. Total Estimate

| Scope | Estimated WPs from WP51/WP52 baseline |
|---|---|
| Research-only useful bot | 15-25 WPs |
| Paper-trading bot | 45-75 WPs |
| Basic controlled live bot | 75-110 WPs |
| Robust live/autonomous-ish bot | 100-160 WPs |
| **Full serious completion range** | **93-160 WPs** |

These are rough planning ranges. Earlier aggressive or minimal estimates are
not authorization to skip gates.

## I. What Is Not Approved By This Roadmap

This roadmap document does not approve any of the following. Each item
requires its own explicitly approved work package before any implementation
begins:

- Strategy implementation
- Paper trading
- Live trading
- Execution
- Credentials
- Authenticated client
- Wallet and signing
- Order placement
- Scheduler
- Bot loop
- Dashboard, database, or deployment
- Hermes runtime or agent runtime
- Autonomous agent
- Wallet-copying
- Wallet intelligence implementation beyond advisory docs/schema/tests
- Individual wallet ranking
- LLM rule parsing
- Semantic cross-market matching
- Official-source live monitoring
- Any other item not listed as a current repo-built component in Section D

Planning-only documents do not grant implementation authority.

## J. Side 4.0 Onboarding Summary

This section exists to give a new Side 4.0 chat (or future session) the
minimum context needed to continue work safely without relying on stale chat
memory.

### Onboarding Steps

1. **Read repo truth first, not chat memory.** Chat memory may be stale.
   Repo truth is authoritative.

2. **Start with these documents in order:**
   - `docs/project_status.md` — current phase, branch, merged WPs
   - `docs/repo_truth_index.md` — full authority hierarchy
   - `docs/research_data_foundation_direction.md` — locked near-term
     research-data direction
   - `docs/long_term_bot_completion_roadmap.md` — this document
   - `docs/market_research_priority_scoring_layer.md` — scoring layer design
   - `docs/market_research_priority_scoring_output_contract.md` — binding
     output contract
   - `docs/deferred_items_log.md` — all open deferred items

3. **Confirm current main and latest merged PR through GitHub before drafting
   or reviewing.** Run the Remote Main Sync Gate:
   `python tools/git/preflight_sync_main.py --required-commit <LATEST_MERGE_SHA>`

4. **Continue Side 3.0 role and workflow, not start a new project.**
   Side 4.0 should pick up where Side 3.0 left off using the same
   repo-truth-first discipline, one WP at a time, no skipped gates.

5. **Safe next path after WP52 merge:** The immediate next path is
   provenance/staleness/missing-data enforcement hardening, only if
   explicitly approved by the user after WP52 is merged. Alternatively,
   resolution-rule ambiguity taxonomy, microstructure quality feature
   extraction, or another repo-truth-safe WP — each requiring explicit
   approval.

6. **Do not move to strategy, paper/live trading, execution, credentials,
   scheduler/bot loop, wallet-copying, Hermes runtime, or autonomous agent
   runtime** without explicit future WPs. The long-term roadmap in this
   document describes the path but does not authorize it.

### What Side 3.0 Left For Side 4.0

- WP52 adds this roadmap and Side 4.0 onboarding lock.
- WP51 is merged: local/offline/read-only feature extraction foundation at
  `src/data_layer/market_research_priority_features.py`.
- WP49 is merged: local/offline/read-only core scorer at
  `src/data_layer/market_research_priority_scoring.py`.
- Protected boundaries remain unchanged.
- Open deferred items: WP49-D002, WP49-D003, WP50-D001, WP51-D001,
  WP51-D002, WP51-D003, WP51-D004. See `docs/deferred_items_log.md`.

## K. Review Checklist For Future WPs

Use this checklist before marking any future WP as ready for review:

- [ ] Does the WP preserve local/offline/read-only boundaries?
- [ ] Does it accidentally turn the research-priority score into a trade
      signal?
- [ ] Does it add any network or runtime behavior?
- [ ] Does it require credentials, authenticated clients, or signing?
- [ ] Does it require strategy, paper-trading, live-trading, risk, or
      execution approval (none of these are approved by WP52)?
- [ ] Does it change dependency or lock files?
- [ ] Does it correctly update `docs/project_status.md`,
      `docs/repo_truth_index.md`, and `docs/deferred_items_log.md`?
- [ ] Does it pass the PR evidence consistency guard with all WP47 hardening
      flags?
- [ ] Does it include a `CURRENT FINAL WP EVIDENCE` top-level PR comment?
