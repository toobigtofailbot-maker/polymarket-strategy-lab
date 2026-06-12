# Research Data Foundation Direction

## A. Status

- WP: WP50 (direction lock merged); WP51 (feature extraction foundation merged); WP52 (long-term roadmap merged); WP53 (data-integrity hardening merged); WP54 (governance hardening merged); WP55 (resolution ambiguity taxonomy/manual-label workflow merged); WP56 (label schema validation merged); WP57 (local feature extraction from validated labels merged); WP60A (agent-neutral startup layer merged); WP61 (architecture direction lock-in and microstructure quality metadata merged); WP62 (cross-market relationship metadata merged); WP63 (resolution source hierarchy metadata merged); WP64 (research queue/report/session packet merged); WP65 (local research queue export/operator runbook on branch)
- Package class: DOCS_ONLY_DIRECTION_LOCK_MERGED; LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED; LONG_TERM_ROADMAP_MERGED; DATA_INTEGRITY_HARDENING_MERGED; GOVERNANCE_HARDENING_MERGED; RESOLUTION_AMBIGUITY_TAXONOMY_MERGED; RESOLUTION_AMBIGUITY_LABEL_SCHEMA_VALIDATION_MERGED; RESOLUTION_AMBIGUITY_LABEL_FEATURE_EXTRACTION_MERGED; ARCHITECTURE_DIRECTION_MERGED; LOCAL_OFFLINE_READ_ONLY_MICROSTRUCTURE_QUALITY_MERGED; LOCAL_OFFLINE_READ_ONLY_CROSS_MARKET_RELATIONSHIP_METADATA_MERGED; LOCAL_OFFLINE_READ_ONLY_RESOLUTION_SOURCE_HIERARCHY_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_REPORT_SESSION_PACKET_MERGED; LOCAL_OFFLINE_READ_ONLY_RESEARCH_QUEUE_EXPORT_OPERATOR_RUNBOOK_ON_BRANCH
- WP50 merge commit: 180a6547114824890851d6ba7e34ab96e7ddd4b8
- WP51 merge commit: c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f
- WP52 merge commit: 259fac091a3b8d0d22aaab13345f440d5a958af2
- WP53 merge commit: 7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6
- WP54 merge commit: fb45fb849b0641e2007ef66f50bfd5725354b8f0
- WP55 merge commit: b019bb825924d52057225455886c3ca45af9e925
- WP56 merge commit: a310e641eb790bd3906d054d703dd11945180e6c
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SOURCE_CHANGE_IN_WP50; LOCAL_OFFLINE_READ_ONLY_FEATURE_MODULE_ADDED_IN_WP51; LOCAL_OFFLINE_READ_ONLY_FEATURE_MODULE_HARDENED_IN_WP53; NO_SRC_CHANGE_IN_WP54; NO_SRC_CHANGE_IN_WP55; LOCAL_OFFLINE_READ_ONLY_LABEL_SCHEMA_VALIDATOR_ADDED_IN_WP56; LOCAL_OFFLINE_READ_ONLY_LABEL_FEATURE_EXTRACTION_ADDED_IN_WP57
- Tools impact: NO_TOOLS_CHANGE_IN_WP55; NO_TOOLS_CHANGE_IN_WP56; NO_TOOLS_CHANGE_IN_WP57
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Hermes impact: NO_HERMES_RUNTIME
- Agent runtime impact: NO_AGENT_RUNTIME
- Feature extraction implementation: NO_FEATURE_EXTRACTION_IMPLEMENTATION_IN_WP50; LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED_IN_WP51; DATA_INTEGRITY_HARDENING_MERGED_IN_WP53; NO_FEATURE_EXTRACTION_IN_WP54; NO_FEATURE_EXTRACTION_IN_WP55; NO_FEATURE_EXTRACTION_IN_WP56; RESOLUTION_AMBIGUITY_LABEL_FEATURE_EXTRACTION_MERGED_IN_WP57; MICROSTRUCTURE_QUALITY_MERGED_IN_WP61; CROSS_MARKET_RELATIONSHIP_METADATA_MERGED_IN_WP62; RESOLUTION_SOURCE_HIERARCHY_MERGED_IN_WP63; RESEARCH_QUEUE_REPORT_SESSION_PACKET_MERGED_IN_WP64; LOCAL_RESEARCH_QUEUE_EXPORT_OPERATOR_RUNBOOK_ON_BRANCH_IN_WP65
- WP51 scope: local/offline/read-only feature extraction foundation only; no CLI/export/report; no microstructure depth/slippage; no resolution ambiguity parser; no strategy/paper/live/execution
- WP52 scope: docs/tests-only long-term bot roadmap and Side 4.0 onboarding lock; no source/tools/runtime/dependency changes
- WP53 scope: local/offline/read-only data-integrity hardening only; provenance/staleness/missing-data enforcement; no CLI/export/report; no advisory consumer; no strategy/paper/live/execution
- WP54 scope: local/offline/stdlib workflow-governance helper hardening; --require-guard-result flag; bundled-WP execution policy docs; no source/runtime/dependency changes
- WP55 scope: docs/tests-only resolution ambiguity taxonomy and manual-label workflow; 14 taxonomy categories; 17-field label schema; local/offline/read-only human review workflow; no parser; no feature extraction; no scorer integration; no source/runtime/dependency changes
- WP56 scope: local/offline/read-only stdlib schema validator for WP55 label records; validates 17 required fields, enum values, manual-review gate, advisory label, forbidden-use notice, source artifact refs, timestamp; optional read-only JSON/JSONL reader; no feature extraction; no scorer integration; no parser; no dependency changes
- WP57 scope: local/offline/read-only feature extraction from validated manual labels; build_resolution_ambiguity_label_index(), resolution_ambiguity sub-dict in market contexts; advisory-only metadata; no parser; no automated extraction; no scorer weight changes; no advisory consumer integration; no CLI/export/report; no dependency changes; future parser/scorer/reporting gates remain explicit
- WP61 scope: architecture planning constraints plus Microstructure Quality V1 metadata; `microstructure_quality` sub-dict in market contexts; local/offline/read-only; no database/dashboard/runtime/deployment/scheduler/bot loop/credentials/network/scorer weight changes/paper-live execution
- WP62 scope: repo-truth reconciliation plus Cross-Market Relationship Metadata V1; `cross_market_relationships` sub-dict in market contexts; deterministic local key comparison only; no semantic matching; no price comparison; no automated equivalence claim; no scorer weight changes; local/offline/read-only
- WP63 scope: repo-truth reconciliation plus Resolution Source Hierarchy Metadata V1; `resolution_source_hierarchy` sub-dict always present in market contexts; deterministic local field presence checks (resolution_date timing, question text source/URL detection); no resolution-rule parser; no source authority judgment; no official-source monitoring; no scorer weight changes; local/offline/read-only
- WP64 scope: repo-truth reconciliation plus Research Queue Ranking, Local Human Review Report, And Research Session Packet V1; new `src/data_layer/market_research_priority_review_queue.py` module; deterministic in-memory queue/report/packet objects; no scorer weight changes; no CLI/export/report file writer; no trading interpretation; no advisory consumer integration; local/offline/read-only

## A1. Long-Term Roadmap Cross-Reference

Long-term bot-completion planning and Side 4.0 onboarding context are now
locked in `docs/long_term_bot_completion_roadmap.md` (added in WP52).

That document contains:
- Current simple-state summary and self-driving-car analogy
- Current repo-built components
- Missing major capabilities
- Four milestone labels and planning WP-range estimates
- Ten-phase roadmap with analogies
- What the roadmap does not approve
- Side 4.0 onboarding summary

**The roadmap does not approve implementation beyond the current direction.**
The research-data foundation remains the immediate approved track. Each future
phase in the roadmap requires its own explicitly approved work package.

## B. Purpose

This document records the final research-phase decisions for the
polymarket-strategy-lab project in repo truth. It exists to prevent drift when
onboarding a new Side chat, Claude Code/Codex session, or reviewer. Repo truth
in this document overrides chat memory, old handoffs, and ad hoc instructions.

Any future session, agent, or reviewer must read this document alongside
`docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/market_research_priority_scoring_layer.md`,
`docs/market_research_priority_scoring_output_contract.md`, and
`docs/deferred_items_log.md` before drafting any work package or implementation.

## C. Repo-Truth Basis

- WP50 is merged at commit `180a6547114824890851d6ba7e34ab96e7ddd4b8`.
- WP49 is merged at commit `3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d`.
- WP49 core scorer (`src/data_layer/market_research_priority_scoring.py`) is
  merged: stdlib-only, in-memory output only, no network, no file writes, no
  CLI, no export, no feature extraction, no advisory consumer integration, no
  runtime/product/trading behavior.
- WP51 is merged: local/offline/read-only feature extraction foundation at
  `src/data_layer/market_research_priority_features.py`. Bridges existing local
  snapshot artifacts into prepared scorer input dicts. No network, no writes,
  no CLI, no export/report, no trading/execution behavior.
- WP53 is merged: data-integrity hardening to `src/data_layer/market_research_priority_features.py`
  (provenance_degraded flag, provenance_weakness_reasons, future-timestamp detection,
  missing_question/market_status detection).
- WP55 adds resolution ambiguity taxonomy and manual-label workflow at
  `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` on branch
  `wp55-resolution-ambiguity-taxonomy-manual-label-workflow`. Docs/schema/tests only.
  No parser, no automated extraction, no feature extraction from labels, no scorer
  integration, no source changes.
- WP49-D001 (feature extraction from local/offline artifacts) is resolved for
  the narrow WP51 basic feature extraction foundation scope only. Advanced
  feature groups (resolution-rule ambiguity — taxonomy/manual-label workflow
  added in WP55; automated extraction remains deferred; microstructure quality
  remains deferred) remain open (WP51-D002 narrowed, WP51-D003, WP55-D001,
  WP55-D002).
- CLI/export/report writer is not started (WP49-D002 OPEN, WP51-D004 OPEN).
- Advisory consumer / market catalog integration is not started (WP49-D003 OPEN).
- Protected boundaries remain unchanged: live trading DISABLED, credentials
  NOT_USED, execution NOT_STARTED, authenticated client
  FORBIDDEN_UNTIL_APPROVED_WP, Hermes NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY,
  agent runtime NOT_STARTED, agent execution authority FORBIDDEN, fully
  autonomous trading agent EXCLUDED_FOR_NOW, scheduler NOT_STARTED, bot loop
  NOT_STARTED.

## D. Locked Project Direction

The project is moving from broad research into local/offline/read-only research-data foundations.

The next phase is **not** strategy, paper trading, live trading, execution,
credentials, wallet-copying, or autonomous agent runtime.

The first implementation track after this WP should bridge existing
local/offline artifacts (snapshots, catalog exports, local reports) into
prepared scorer inputs. Provenance, staleness, missing-data warnings, and
non-compensatory caps must be built into that foundation from the start so
that future scored outputs carry honest data-quality signals.

Resolution-rule ambiguity, microstructure quality, and metadata-only
cross-market graphing follow after the feature extraction foundation is stable.
Calibration, wallet attention, official-source latency, risk/kill-switch
refresh, paper trading, live trading, and execution remain deferred until their
own explicit pre-condition gates are satisfied.

## D1. WP61 Architecture Direction Lock-In

WP61 locks these future planning constraints without implementing them:

- Database: SQLite first; Postgres later only if justified.
- Dashboard: Streamlit first; Grafana later for runtime metrics; Next.js only if productizing.
- Runtime: local development first; cheap VPS later for a controlled live pilot.
- Strategy: rules-based plus research-score-driven first; LLM read-only analyst/proposal layer only.
- Ladder: research-only -> paper -> dry-run -> manual live approval -> restricted live.

These constraints do not authorize database, dashboard, runtime, scheduler,
credentials, paper/live, or execution work.

## E. Locked Research Conclusions

1. **Market Research Priority Scoring remains non-signal.** The layer produces
   `research_priority_score` for human research triage only. No output field or
   downstream use may reinterpret the score as a trade signal, alpha, edge,
   mispricing, or execution instruction.

2. **`research_priority_score` is human research triage only.** A high score
   means a human researcher should study the market first. It does not mean the
   market is profitable, tradable, mispriced, executable, expected-return
   positive, or worthy of position sizing, buy/sell signals, or strategy output.

3. **High score does not imply any trade-like meaning.** Score outputs must
   never be consumed by trade-decision, signal-generation, or execution code.

4. **Provenance and staleness are data-integrity gates.** Stale or unprovable
   inputs must cap or invalidate score outputs. A score computed from stale
   inputs must not be presented as current.

5. **Critical missing data must cap or invalidate outputs.** Non-compensatory
   caps are required: a missing critical field must lower or block the score,
   not be silently averaged away.

6. **Resolution-rule ambiguity is the strongest research-priority gap, but not proven alpha.**
   Markets with ambiguous resolution rules deserve research attention, not trade deployment.

7. **Microstructure quality is a data-quality gate, not tradability.** Thin
   order books or wide spreads indicate data quality concerns, not trade
   opportunities.

8. **Cross-market graphing starts metadata-only.** Semantic matching or
   correlation-based cross-market links require additional safety review and
   must not begin until metadata-only relationship extraction is validated.

9. **Calibration waits for resolved-outcome data and fixed snapshot offsets.**
   No calibration implementation is approved until a validated resolved-outcome
   dataset exists and snapshot timing offsets are confirmed and fixed.

10. **Wallet attention waits for public data plan, aggregation/anonymization,
    and copy-trading prevention.** No wallet-attention work may begin until a
    public-only data plan is documented, individual wallet ranking is excluded,
    and copy-trading prevention controls are defined.

11. **Official-source latency waits for release timestamp data.** No
    official-source latency implementation is approved until authoritative
    release timestamp data exists in local artifacts.

12. **Risk/kill-switch refresh is required before paper/live work, not before
    current research-data foundation work.** The current research-data
    foundation track does not require a risk/kill-switch refresh, but no
    paper-trading or live-trading WP may begin until that refresh is complete.

## F. Approved Near-Term Sequence

The following is a candidate implementation sequence, not a set of drafted or
approved work packages. Each item requires explicit user approval before a WP
is drafted.

1. Feature extraction from local/offline artifacts (snapshots, catalog exports,
   local reports) into prepared scorer inputs.
2. Provenance/staleness/missing-data enforcement hardening across all scorer
   inputs.
3. Resolution-rule ambiguity taxonomy and manual label workflow.
4. Basic resolution metadata feature extraction.
5. Microstructure quality feature extraction.
6. Metadata-only cross-market relationship graph.
7. Calibration validation harness design.
8. Wallet-attention data plan.
9. Official-source latency research plan.
10. Risk/kill-switch research refresh before any paper/live work.
11. Execution realism / paper-trading design only after data quality and
    microstructure foundations are stable.

No item in this list is approved until the user explicitly approves it after
WP50 is merged.

## G. Blocked Directions

The following are explicitly blocked until their respective pre-condition gates
are approved in separate future work packages:

- Live trading
- Credentials and API secrets
- Authenticated clients
- Private keys, wallets, signing
- Order placement/cancellation
- Execution gateway
- Strategy runtime
- Paper-trading runtime
- Scheduler/bot loop
- Hermes/agent runtime
- Autonomous trading agent
- Wallet copy-trading
- Individual wallet ranking
- Position sizing
- Expected-return outputs
- Trade-like fields or hidden trade signals
- LLM-based rule parsing without safeguards
- Semantic cross-market matching
- Official-source live monitoring
- Source/news scraping
- Performance claims

## H. Safe Output Language

The following field names are blocked as score outputs. They may appear only in
clearly labelled blocked/forbidden sections of docs or tests — never as active
output fields or as names of variables carrying score-like values:

`alpha_score`, `opportunity_score`, `edge_score`, `expected_return`,
`fair_value`, `profit_probability`, `trade_signal`, `buy_signal`,
`sell_signal`, `entry_price`, `exit_price`, `stop_loss`, `take_profit`,
`position_size`, `leverage`, `execution_confidence`, `tradability_score`,
`liquidity_score` (when used as a trade-readiness claim), `copy_trade_signal`,
`smart_money_score`, `trade_recommendation`, `paper_trade_authorized`,
`live_trade_authorized`.

Any field name that implies trade-readiness, profitability, or execution
authority must be rejected even if not explicitly listed above.

## I. Future-WP Gating Rules

1. Verify live repo truth before every future WP. Run the Remote Main Sync
   Gate and confirm the required previous merge commit before creating a
   branch.

2. No WP may widen from local/offline/read-only into network/runtime/product
   behavior without explicit user approval and a new protected-boundary
   review.

3. Feature extraction must read only existing approved local/offline artifacts
   (local_data/ snapshots, catalog exports, local reports). It must not add
   network calls, API polling, or live data capture.

4. Public-data capture, CLI/export/report integration, advisory consumer
   integration, wallet activity, official-source monitoring, calibration
   implementation, paper trading, and risk engine all require separate
   explicit WPs with their own safety gates.

5. Every future scoring output must preserve the `advisory_label:
   ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED` field and the
   `human_review_required: true` flag. No automation may bypass these fields.

6. The direction document you are reading is locked repo truth. Future sessions
   must not contradict it without an explicit approved WP that supersedes it.

## J. New-Chat Onboarding Summary

**Repo truth overrides this document if changed by a later approved WP.** This
document is authoritative only until superseded.

Before drafting any implementation or WP:

1. Read `docs/project_status.md` for current phase, branch, and merged WPs.
2. Read `docs/repo_truth_index.md` for the full authority hierarchy.
3. Read this document for the locked research-phase direction.
4. Read `docs/market_research_priority_scoring_layer.md` for scoring layer
   design constraints.
5. Read `docs/market_research_priority_scoring_output_contract.md` for the
   binding output contract.
6. Read `docs/deferred_items_log.md` for all open deferred items.

Do not draft any implementation WP until you have verified current main and
confirmed the previous merge commit using the Remote Main Sync Gate.

**The immediate approved direction is research-data foundation, not trading bot
execution.** The next implementation track is feature extraction from existing
local/offline artifacts, not strategy, paper trading, live trading, execution,
wallet-copying, or autonomous agent runtime.
