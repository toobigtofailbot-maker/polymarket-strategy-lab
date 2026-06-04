# Research Data Foundation Direction

## A. Status

- WP: WP50 (direction lock merged); WP51 (feature extraction foundation merged); WP52 (long-term roadmap on branch)
- Package class: DOCS_ONLY_DIRECTION_LOCK_MERGED; LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED; LONG_TERM_ROADMAP_ON_BRANCH
- WP50 merge commit: 180a6547114824890851d6ba7e34ab96e7ddd4b8
- WP51 merge commit: c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SOURCE_CHANGE_IN_WP50; LOCAL_OFFLINE_READ_ONLY_FEATURE_MODULE_ADDED_IN_WP51
- Tools impact: NO_TOOLS_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Paper trading impact: NO_PAPER_TRADING
- Hermes impact: NO_HERMES_RUNTIME
- Agent runtime impact: NO_AGENT_RUNTIME
- Feature extraction implementation: NO_FEATURE_EXTRACTION_IMPLEMENTATION_IN_WP50; LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED_IN_WP51
- WP51 scope: local/offline/read-only feature extraction foundation only; no CLI/export/report; no microstructure depth/slippage; no resolution ambiguity parser; no strategy/paper/live/execution
- WP52 scope: docs/tests-only long-term bot roadmap and Side 4.0 onboarding lock; no source/tools/runtime/dependency changes

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
- WP51 adds the first local/offline/read-only feature extraction foundation at
  `src/data_layer/market_research_priority_features.py` on branch
  `wp51-market-research-priority-feature-extraction-foundation`. It bridges
  existing local snapshot artifacts into prepared scorer input dicts. No network,
  no writes, no CLI, no export/report, no trading/execution behavior.
- WP49-D001 (feature extraction from local/offline artifacts) is resolved for
  the narrow WP51 basic feature extraction foundation scope only. Advanced
  feature groups (provenance hardening, resolution-rule ambiguity, microstructure
  quality) remain deferred (WP51-D001, WP51-D002, WP51-D003).
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
