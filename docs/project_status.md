# Project Status

- Current phase: WP55 - Repo-Truth Reconciliation And Resolution Ambiguity Taxonomy / Manual-Label Workflow
- Repo state: Local/offline/read-only resolution ambiguity taxonomy/manual-label workflow on branch; WP54 merged
- Merged WPs: WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8, WP9, WP10, WP10-Follow-up, WP11, WP12, WP13, WP14, WP15, WP16, WP17, WP18, WP19, WP20, WP21, WP22, WP23, WP24, WP25, WP26, WP27, WP28, WP29, WP30, WP31, WP32, WP33, WP34, WP35, WP36, WP37, WP38, WP39, WP40, WP41, WP42, WP43, WP44, WP45, WP46, WP47, WP48, WP49, WP50, WP51, WP52, WP53, WP54
- Current branch: `wp55-resolution-ambiguity-taxonomy-manual-label-workflow`
- API integration status: STDLIB_READ_ONLY_PUBLIC_DATA_ACTIVE; MANUAL_EXPLICIT_NETWORK_POLLING_RUNNER_DEV_ONLY; MANUAL_GUARD_ENFORCED_SNAPSHOT_CAPTURE_DEV_ONLY
- Runtime dependency integration status: NOT_STARTED_FOR_NEW_RUNTIME_DEPENDENCIES
- Official client runtime dependency status: NOT_STARTED_FOR_OFFICIAL_CLIENT_RUNTIME
- Live trading status: DISABLED
- Credentials status: NOT_USED
- Execution status: NOT_STARTED
- Official Python client status: SANDBOX_CANDIDATE_ONLY_NOT_PROJECT_DEPENDENCY
- Authenticated client status: FORBIDDEN_UNTIL_APPROVED_WP
- AI-agent layer status: POLICY_ONLY_NOT_IMPLEMENTED
- Agent context export schema status: POLICY_SCHEMA_DEFINED_EXPORTER_IMPLEMENTED_LOCAL_OFFLINE_READ_ONLY
- Agent context exporter status: LOCAL_OFFLINE_READ_ONLY_EXPORTER
- Agent context exporter operator runbook status: LOCAL_OPERATOR_RUNBOOK
- Agent report generation status: LOCAL_OFFLINE_READ_ONLY_REPORT_GENERATOR
- Agent report operator runbook status: LOCAL_ANALYST_REPORT_OPERATOR_RUNBOOK
- Agent/Hermes manual setup decision status: MANUAL_SETUP_DECISION_RECORD_MERGED
- Token-efficiency operating model status: ACTIVE_REPO_TRUTH_GUIDANCE
- Diff/scope summary helper design status: DESIGN_MERGED
- Diff/scope summary helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Validation-output summary helper design status: DESIGN_MERGED
- Validation-output summary helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Code-index / blast-radius helper design status: DESIGN_MERGED
- Code-index / blast-radius helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Memory/status snapshot helper design status: DESIGN_MERGED
- Memory/status snapshot helper implementation status: LOCAL_OFFLINE_READ_ONLY_HELPER_MERGED
- Token-efficiency sequence closeout status: DOCS_ONLY_CLOSEOUT_MERGED
- Local advisory handoff package status: DOCS_ONLY_LOCAL_ADVISORY_HANDOFF_MERGED
- Advisory runtime boundary and consumption design status: DOCS_ONLY_ADVISORY_RUNTIME_BOUNDARY_DESIGN_MERGED
- Local advisory consumer prototype status: LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_MERGED
- Advisory prompt/runbook package status: DOCS_ONLY_ADVISORY_PROMPT_RUNBOOK_MERGED
- Advisory operator workflow hardening status: DOCS_ONLY_ADVISORY_OPERATOR_WORKFLOW_MERGED
- Market research priority scoring layer status: DOCS_ONLY_DESIGN_MERGED; SCHEMA_OUTPUT_CONTRACT_MERGED; CORE_SCORER_MERGED; RESEARCH_DATA_FOUNDATION_DIRECTION_MERGED; FEATURE_EXTRACTION_FOUNDATION_MERGED; LONG_TERM_ROADMAP_MERGED; DATA_INTEGRITY_HARDENING_MERGED
- WP54 bundled-WP execution policy status: WORKFLOW_GOVERNANCE_MERGED
- WP54 guard --require-guard-result flag status: LOCAL_OFFLINE_STDLIB_GUARD_HARDENING_MERGED
- Resolution ambiguity taxonomy/manual-label workflow status: DOCS_SCHEMA_TESTS_ONLY_ON_BRANCH
- Market research priority scoring implementation status: LOCAL_OFFLINE_READ_ONLY_CORE_SCORER_MERGED
- Market research priority scoring feature extraction status: LOCAL_OFFLINE_READ_ONLY_FEATURE_EXTRACTION_FOUNDATION_MERGED
- Market research priority scoring CLI/export/report status: NOT_STARTED
- Research data foundation direction status: DOCS_ONLY_DIRECTION_LOCK_MERGED
- Long-term bot roadmap status: DOCS_ONLY_ROADMAP_MERGED
- Side 4 onboarding lock status: DOCS_ONLY_SIDE4_ONBOARDING_LOCK_MERGED
- PR evidence reporting discipline status: WORKFLOW_GOVERNANCE_MERGED
- PR evidence consistency guard status: LOCAL_OFFLINE_STDLIB_GUARD_MERGED
- Posted PR evidence review hardening status: DOCS_AND_GUARD_HARDENING_MERGED
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY
- Agent runtime status: NOT_STARTED
- Agent execution authority: FORBIDDEN
- Fully autonomous trading agent status: EXCLUDED_FOR_NOW
- Polling status: MANUAL_EXPLICIT_NETWORK_BOUNDED_RUNNER_DEV_ONLY; SNAPSHOT_CAPTURE_MANUAL_EXPLICIT_NETWORK_BOUNDED_GUARD_ENFORCED_DEV_ONLY
- Scheduler status: NOT_STARTED
- Bot loop status: NOT_STARTED
- Sandbox status: OFFICIAL_CLIENT_SANDBOX_DEV_ONLY; DEV_ONLY_READ_ONLY_NO_CREDENTIALS
- Storage status: LOCAL_FILE_SNAPSHOTS_ONLY
- Catalog status: IN_MEMORY_LOCAL_ONLY
- Reporting status: LOCAL_REPORTS_ONLY
- Export status: LOCAL_EXPORTS_ONLY
- External repo audit status: WP2 COMPLETE - 14 concrete repositories audited; 1 non-specific legacy placeholder marked BLOCKED_OR_UNAVAILABLE
- Architecture status: WP3 documentation-only skeleton merged; WP8 adds approved read-only data-layer source under src/data_layer/polymarket/; WP9 adds contract probe tooling and validates three of four endpoint candidates; WP10 adds local file-based snapshot persistence (JSONL) under src/data_layer/polymarket/ and manual capture tool under tools/polymarket/; WP11 adds offline snapshot reader, in-memory market catalog, replay helpers, and manual inspection CLI under src/data_layer/polymarket/ and tools/polymarket/; WP12 adds offline snapshot quality gates, catalog quality metrics, and local report generation under src/data_layer/polymarket/ and tools/polymarket/; WP13 adds offline snapshot deduplication and sanitized local catalog exports under src/data_layer/polymarket/ and tools/polymarket/; WP14 adds official Python client dependency decision and boundary review docs/tests only; WP15 adds official-client sandbox tooling under tools/polymarket/official_client_sandbox/ only; WP16 adds offline polling policy and local rate-limit guard only; WP17 adds a manual finite explicit-network read-only polling runner only; WP18 adds guard-enforced manual snapshot capture using WP16 policy before Gamma and optional CLOB reads; WP19 adds offline guard-aware quality/reporting for WP18 guarded capture manifests; WP20 adds policy/docs/tests only for advisory AI-agent and Hermes read-only boundaries; WP21 adds schema/docs/tests only for a future local read-only agent context export; WP22 adds persistent Codex workflow guidance, templates, checklists, and tests only; WP23 adds a local/offline/read-only agent context JSON exporter only under src/data_layer/agent_context/ and tools/polymarket/; WP24 adds the local operator runbook and doc tests for safe manual exporter use only; WP25 adds deterministic local/offline/read-only report generation from WP23-compatible exports only; WP26 adds operator runbook docs/tests only for safe manual report-generator use; WP27 adds Agent/Hermes manual setup decision record docs/tests only; WP28 adds token-efficiency operating model, concise reporting rules, and reusable WP prompt blocks docs/tests only; WP29 adds design/docs/tests only for the local/offline/read-only diff/scope summary helper; WP30 adds the local/offline/read-only stdlib helper implementation at tools/git/diff_scope_summary.py, focused tests, and user-facing helper doc; WP31 adds design/docs/tests only for a future local/offline/read-only validation-output summary helper; WP32 adds the local/offline/read-only stdlib helper implementation at tools/validation/validation_output_summary.py, focused tests, and user-facing helper doc; WP33 adds docs-only design guidance at docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md for a future advisory code-index / blast-radius helper; WP34 adds the local/offline/read-only stdlib helper implementation at tools/git/code_blast_radius.py, focused tests, and user-facing helper doc; WP35 adds design/docs/tests only for a future local/offline/read-only memory/status snapshot helper at docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md; WP36 adds the local/offline/read-only stdlib helper implementation at tools/git/status_snapshot.py, focused tests, and user-facing helper doc; WP37 adds docs/tests only to consolidate the WP28-WP36 token-efficiency sequence, helper usage order, advisory-only limits, deferred helper gaps, protected-boundary reaffirmation, and next-WP gate; WP38 adds docs/tests only to resume advisory-agent planning through a local advisory handoff package with no runtime, Hermes, LLM, credential, trading, database, dashboard, scheduler, polling, or product behavior; WP39 adds docs/tests only to define the future local advisory consumer boundary and consumption model with no runtime, Hermes, LLM, network, account, trading, database, dashboard, scheduler, polling, dependency, source, tools, or product behavior; WP40 adds a local/offline/read-only deterministic advisory consumer prototype under tools/advisory/local_advisory_consumer.py with explicit local_data inputs only, stdout by default, optional ignored advisory output, and no runtime, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, or src/ changes; WP41 adds docs/tests only for human-operated advisory prompt/runbook templates and operator review steps with no runtime, prompt runner, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, tools/, or src/ changes; WP42 adds docs/tests only for human-operated advisory workflow hardening connecting WP40 and WP41 with evidence, stop/reject gates, decision logging, and future-WP conversion rules, with no runtime, prompt runner, LLM, Hermes, network, account, trading, database, dashboard, scheduler, polling, dependency, lock-file, tools/, or src/ changes; WP43 reconciles docs/project_status.md with actual repo truth after WP42 merge, adding a focused project-status docs test, with no runtime, dependency, lock-file, tools/, or src/ changes; WP44 adds docs-only design for a future Market Research Priority Scoring Layer at docs/market_research_priority_scoring_layer.md and a focused docs test, with no runtime, source, tools, dependency, or lock-file changes; WP45 adds docs/tests-only workflow/governance PR evidence reporting hardening across AGENTS.md, docs/ai/codex/ workflow docs, docs/work_package_template.md, docs/review_checklist.md, and a focused docs test, with no runtime, source, tools, dependency, or lock-file changes; WP46 adds a local/offline/stdlib governance helper at tools/git/pr_evidence_consistency_guard.py with focused tests under tests/tools/git/ and docs under docs/ai/codex/, with no runtime, source, dependency, or lock-file changes; WP47 hardens the guard with five new optional flags (--forbid-inline-test-counts, --forbid-placeholder-evidence, --require-current-final-marker, --forbid-stale-count-tokens, --require-posted-evidence-note) and updates workflow docs/tests/review checklists to enforce current-final evidence markers and forbid parenthetical test counts in file lists, with no runtime, source, dependency, or lock-file changes; WP48 adds docs/tests-only schema and output contract for the future Market Research Priority Scoring Layer at docs/market_research_priority_scoring_output_contract.md, defining top-level output schema, market object schema, score components, advisory-only labels, staleness/provenance/missing-data contracts, forbidden fields, safe and invalid examples, and future implementation gates, with no runtime, source, tools, dependency, or lock-file changes; WP49 adds a local/offline/read-only core scorer under src/data_layer/market_research_priority_scoring.py (stdlib-only, in-memory output only, no network, no file writes, no CLI, no export, no report writer, no runtime/product/trading behavior) with focused tests at tests/test_market_research_priority_scoring_core.py, and updates docs to reflect WP48 merged and WP49 core scorer on branch; WP50 adds docs-only research-data foundation direction lock and deferred items update with no source, tools, dependency, or lock-file changes; WP51 adds the local/offline/read-only stdlib feature extraction foundation at src/data_layer/market_research_priority_features.py, focused tests, and docs updates; WP52 adds docs-only long-term bot-completion roadmap and Side 4 onboarding lock with no source, tools, dependency, or lock-file changes; WP53 hardens src/data_layer/market_research_priority_features.py with provenance/staleness/missing-data enforcement (provenance_degraded flag, provenance_weakness_reasons, future-timestamp detection, missing_question/missing_market_status detection), focused tests, and docs updates with no new dependency or lock-file changes; WP54 hardens tools/git/pr_evidence_consistency_guard.py with a new --require-guard-result flag (category P — requires actual guard result line, checked categories, and exit code in both PR body and final comment), adds docs/ai/codex/WP_BUNDLING_POLICY.md with bundling policy and follow-up classification, and updates workflow/governance docs and tests with no src/, Polymarket-tooling, dependency, or lock-file changes.
- Deferred items status: WP9 marks WP8-D001 READY_FOR_WP (three endpoints confirmed, CLOB /health unconfirmed); long-running runtime/data deferred items remain unchanged unless explicitly listed later; WP38 resolves WP37-D001 only for selecting and documenting the local advisory handoff path, not for runtime/product implementation; WP39 resolves WP38-D001 only for docs-only advisory runtime boundary and consumption design completion, not for advisory consumer implementation; WP40 resolves WP38-D002 and WP39-D001 only for the deterministic local/offline/read-only advisory consumer prototype scope, not for runtime/LLM/Hermes/trading implementation; WP41 resolves WP39-D002 and WP40-D001 only for docs-only advisory prompt/runbook package scope, not for runtime/LLM/Hermes/provider/account/trading implementation; WP42 resolves WP41-D001 only for docs-only advisory consumer integration review / operator workflow hardening scope; WP40-D002 remains OPEN because LLM/Hermes/provider integration is not designed or implemented; WP41-D002 remains OPEN because provider/Hermes decision refresh is not performed; WP42-D001 and WP42-D002 are OPEN; WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain OPEN; WP20-D001 remains READY_FOR_MANUAL_SETUP_DECISION; WP27-D001, WP20-D003, WP8-D002, WP16-D002, WP17-D001, and WP17-D002 remain OPEN and unchanged; security checks are run/assessed in WP42; WP43 resolves no deferred items; all WP42-forward deferred items remain unchanged; security checks are run/assessed in WP43; WP44 resolves no existing deferred items; WP44 adds WP44-D001 (Market Research Priority Scoring implementation not started, OPEN, P3) and WP44-D002 (Score laundering mitigation not enforced by implementation, OPEN, P3); WP45 resolves no existing deferred items; security checks are run/assessed in WP45; WP46 resolves no existing deferred items; WP46 adds WP46-D001 (guard validates local PR body/final comment drafts only, not live GitHub PR data, OPEN, P4); security checks are run/assessed in WP46; WP47 resolves no existing deferred items; WP47 adds WP47-D001 (guard still does not fetch live GitHub PR body/comments, OPEN, P4; WP47 hardens local posted-evidence discipline and current-final markers but intentionally avoids GitHub API/network/auth behavior; any future requirement to validate already-posted GitHub content automatically is deferred to a future approved GitHub-aware helper WP with explicit network/auth boundary); security checks are run/assessed in WP47; WP48 resolves no existing deferred items; WP48 adds WP48-D001 (Market Research Priority Scoring implementation not started after schema/output contract, OPEN, P3) and WP48-D002 (schema/output contract not enforced by implementation yet, OPEN, P3); WP44-D001 and WP44-D002 remain OPEN because implementation is still not started; security checks are run/assessed in WP48; WP49 resolves WP44-D001, WP44-D002, WP48-D001, and WP48-D002 only for the local/offline/read-only core scorer scope; WP49 adds WP49-D001 (feature extraction from local/offline artifacts not started, OPEN, P3), WP49-D002 (CLI/export/report writer not started, OPEN, P3), and WP49-D003 (core scorer not integrated with advisory consumer or market catalog, OPEN, P3); security checks are run/assessed in WP49; WP50 resolves no existing deferred items; WP50 adds WP50-D001 (research direction locked, but implementation sequencing still requires explicit future WPs, OPEN, P3); security checks are run/assessed in WP50; WP51 resolves WP49-D001 only for the narrow local/offline/read-only basic feature extraction foundation scope; WP49-D002 and WP49-D003 remain OPEN; WP50-D001 remains OPEN; WP51 adds WP51-D001 (provenance/staleness hardening beyond foundation not started, OPEN, P3), WP51-D002 (resolution-rule ambiguity extraction not started, OPEN, P3), WP51-D003 (microstructure quality feature extraction beyond basic availability not started, OPEN, P3), and WP51-D004 (CLI/export/report writer not started, OPEN, P3); security checks are run/assessed in WP51; WP52 resolves no existing deferred items; WP52 adds WP52-D001 (long-term roadmap locked, but milestone implementation remains gated by explicit future WPs, OPEN, P3); security checks are run/assessed in WP52; WP53 resolves WP51-D001 only for the narrow provenance/staleness/missing-data hardening scope implemented in WP53; WP53 adds WP53-D001 (resolution-rule ambiguity extraction still not started, OPEN, P3), and WP53-D002 (microstructure quality feature extraction still not started, OPEN, P3); WP49-D002, WP49-D003, WP50-D001, WP51-D002, WP51-D003, WP51-D004, and WP52-D001 remain OPEN; security checks are run/assessed in WP53; WP54 resolves no existing implementation deferred items; WP54 adds WP54-D001 (GitHub-posted evidence still requires human or Claude manual verification because the guard remains local/offline and does not fetch live GitHub PR content, OPEN, P4); security checks are run/assessed in WP54.
- Generated artifact status: WP6 guardrails active; WP7 gitleaks binary in ignored tools/.bin/ (not committed); local_data/ is ignored and generated outputs must not be committed; WP23 agent context exports output remains under ignored local_data/agent_context_exports/; WP25 agent context report output remains under ignored local_data/agent_context_reports/; WP40 optional advisory consumer output remains under ignored local_data/advisory_outputs/ only.
- Next intended WP: after WP55 merge, recommended next WP is WP56 — Repo-Truth Reconciliation And Resolution Ambiguity Local Feature Extraction From Manual Labels (local/offline/read-only; consume only manual labels and existing local metadata; no parser; no LLM; no report writer; no strategy; no execution; no credentials; no scheduler; no Hermes runtime). Do not suggest strategy runtime, paper trading, live trading, official-client runtime integration, scheduler, wallet/copy-trading, production polling, Hermes install, LLM provider runtime, autonomous agent runtime, or execution as next WP. Do not draft any next WP until explicitly approved after WP55 is merged.

## WP55 Repo-Truth Reconciliation And Resolution Ambiguity Taxonomy / Manual-Label Workflow

WP55 - Repo-Truth Reconciliation And Resolution Ambiguity Taxonomy / Manual-Label Workflow
is on branch (`wp55-resolution-ambiguity-taxonomy-manual-label-workflow`).
It reconciles repo truth after WP54 merge and delivers a durable resolution-rule ambiguity
taxonomy, manual-label workflow, and label schema for human research data quality review.

WP55 creates `docs/resolution_ambiguity_taxonomy_manual_label_workflow.md` and updates
`docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It adds focused tests at
`tests/test_resolution_ambiguity_taxonomy_manual_label_workflow_docs.py` and updates
`tests/test_project_status_docs.py`.

WP55 is a docs/tests-only research-governance WP. It defines the resolution-rule ambiguity
taxonomy (14 categories), review status values, severity/confidence separation, manual label
schema (17 required fields), local/offline/read-only manual review workflow, future integration
gate, invalid/valid examples, and deferred items. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no automated parser, no feature extraction, no scorer
integration, no CLI/export/report writer, no runtime, no network, no dependency or lock-file
changes, no Hermes/LLM/provider integration, no credentials, no account access, no trading or
paper trading, no database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP55 reconciles docs/project_status.md after WP54 merge (merge commit
fb45fb849b0641e2007ef66f50bfd5725354b8f0). WP54 is now listed in merged WPs.

WP55 narrows WP51-D002 and WP53-D001 (taxonomy/manual-label workflow addressed; automated
parser and feature extraction remain not started). WP55 adds WP55-D001 (ambiguity labels not
yet consumed by feature extraction, OPEN, P3) and WP55-D002 (automated resolution-rule parser
remains not started, OPEN, P3).

Security checks are run/assessed in WP55.

## WP54 PR Evidence Follow-Up Defect And Bundled-WP Execution Policy Hardening After WP53 Merge

WP54 - PR Evidence Follow-Up Defect And Bundled-WP Execution Policy Hardening After WP53 Merge
is merged (merge commit fb45fb849b0641e2007ef66f50bfd5725354b8f0).
It reconciles repo truth after WP53 merge and locks follow-up process-defect classification,
bundled-WP execution policy, posted evidence self-check rules, and package size class guidance
into durable repo-truth docs and tests.

WP54 creates `docs/ai/codex/WP_BUNDLING_POLICY.md` and updates
`tools/git/pr_evidence_consistency_guard.py` (adds `--require-guard-result` flag, category P),
`tests/tools/git/test_pr_evidence_consistency_guard.py`,
`docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/work_package_template.md`,
`.github/pull_request_template.md`,
`docs/project_status.md`,
`docs/repo_truth_index.md`,
`docs/deferred_items_log.md`,
`docs/review_checklist.md`,
`docs/testing_requirements.md`, and
`tests/test_codex_workflow_docs.py`.

WP54 is a local/offline/stdlib workflow-governance helper hardening WP. It hardens
`tools/git/pr_evidence_consistency_guard.py` with a new `--require-guard-result` flag
and updates workflow/governance docs and tests. It adds no source under `src/`, no
Polymarket/trading/advisory tooling, no runtime, no network, no dependency or lock-file
changes, no Hermes/LLM/provider integration, no credentials, no account access, no trading
or paper trading, no database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP54 reconciles docs/project_status.md after WP53 merge (merge commit
7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6). WP53 is now listed in merged WPs.

WP54 resolves no existing implementation deferred items. WP54 adds WP54-D001
(GitHub-posted evidence still requires human or Claude manual verification because the guard
remains local/offline and does not fetch live GitHub PR content, OPEN, P4).

Security checks are run/assessed in WP54.

## WP53 Repo-Truth Reconciliation And Provenance/Staleness/Missing-Data Enforcement Hardening

WP53 - Repo-Truth Reconciliation And Provenance/Staleness/Missing-Data Enforcement
Hardening is merged (merge commit 7514b1aded39c5f1ca0c5abae4fdae86b6c4f1d6).
It reconciled repo truth after WP52 merge and hardened local/offline/read-only
provenance, staleness, and missing-data enforcement in Market Research Priority
feature contexts.

WP53 updates `src/data_layer/market_research_priority_features.py` with explicit
provenance degraded flag (`provenance_degraded`), provenance weakness reasons,
future-timestamp detection in staleness, missing question and market_status detection,
and a quality-impacting vs informational provenance weakness separation. It updates
`docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`,
`docs/research_data_foundation_direction.md`, `docs/long_term_bot_completion_roadmap.md`,
`docs/market_research_priority_scoring_layer.md`, and
`docs/market_research_priority_scoring_output_contract.md`. It adds focused tests at
`tests/test_market_research_priority_features.py`.

WP53 is a local/offline/read-only source-implementation and docs/tests WP. It adds
no CLI/export/report writer, no advisory consumer integration, no market catalog
integration, no runtime/product/trading behavior, no Hermes/LLM/provider integration,
no credentials, no network, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed. No dependency or lock-file changes.

WP53 reconciles docs/project_status.md after WP52 merge (merge commit
259fac091a3b8d0d22aaab13345f440d5a958af2). WP52 is now listed in merged WPs.

WP53 marks WP51-D001 RESOLVED (narrow provenance/staleness/missing-data hardening
scope only). WP53 adds WP53-D001 (resolution-rule ambiguity extraction still not
started, OPEN, P3) and WP53-D002 (microstructure quality feature extraction still
not started, OPEN, P3). WP49-D002, WP49-D003, WP50-D001, WP51-D002, WP51-D003,
WP51-D004, and WP52-D001 remain OPEN.

Security checks are run/assessed in WP53.

## WP52 Long-Term Bot Roadmap And Side 4 Onboarding Lock-In After WP51 Merge

WP52 - Long-Term Bot Roadmap And Side 4 Onboarding Lock-In After WP51 Merge is
merged (merge commit 259fac091a3b8d0d22aaab13345f440d5a958af2).
It reconciles repo truth after WP51 merge and locks the long-term bot-completion
roadmap plus Side 4.0 onboarding context into durable repo-truth documentation.

WP52 adds `docs/long_term_bot_completion_roadmap.md` as the new docs-only
roadmap and Side 4.0 onboarding lock. It updates `docs/project_status.md`,
`docs/repo_truth_index.md`, `docs/research_data_foundation_direction.md`, and
`docs/deferred_items_log.md`. It adds focused tests at
`tests/test_long_term_bot_completion_roadmap_docs.py`.

WP52 is a docs/tests-only WP. It adds no source under `src/`, no tools
implementation, no runtime, no network, no dependency or lock-file changes, no
Hermes/LLM/provider integration, no credentials, no account access, no trading
or paper trading, no database/dashboard/scheduler/polling/product behavior, and
no generated outputs committed.

WP52 reconciles docs/project_status.md after WP51 merge (merge commit
c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f). WP51 is now listed in merged WPs.

WP52 adds WP52-D001 (long-term roadmap locked, but milestone implementation
remains gated by explicit future WPs, OPEN, P3). No existing implementation
deferred items are resolved by WP52.

Security checks are run/assessed in WP52.

## WP51 Market Research Priority Feature Extraction Foundation

WP51 - Market Research Priority Feature Extraction Foundation is merged
(merge commit c57b9c0adcc044f8bd9ed01a6368f2fafdbe222f).
It adds the first narrow local/offline/read-only feature-extraction foundation
for the Market Research Priority Scoring Layer implemented in WP49.

WP51 adds `src/data_layer/market_research_priority_features.py` as a new
stdlib-only local/offline/read-only feature extraction module. It adds focused
tests at `tests/test_market_research_priority_features.py` and updates
`docs/project_status.md`, `docs/repo_truth_index.md`,
`docs/deferred_items_log.md`, `docs/research_data_foundation_direction.md`,
`docs/market_research_priority_scoring_layer.md`, and
`tests/test_architecture_boundaries.py`.

WP51 bridges existing approved local/offline Polymarket snapshot artifacts into
prepared scorer input dictionaries. The feature module reads
`MarketMetadataSnapshotRecord`, `OrderBookSnapshotRecord`, and `SnapshotManifest`
objects; extracts basic metadata/provenance/staleness/missing-data feature
inputs; and produces prepared `run_context` and `market_context` dictionaries
compatible with `build_market_research_priority_output()` from WP49.

WP51 is a local/offline/read-only source-implementation WP. The feature
extraction module is stdlib-only, in-memory output only, no network, no file
writes, no CLI, no export, no report writer, no advisory consumer integration,
no runtime/product/trading behavior, no Hermes/LLM/provider integration, no
credentials, no account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed. No dependency or lock-file changes.

WP51 reconciles docs/project_status.md after WP50 merge (merge commit
180a6547114824890851d6ba7e34ab96e7ddd4b8). WP50 is now listed in merged WPs.

WP51 marks WP49-D001 RESOLVED (narrow WP51 basic feature extraction foundation
scope only). WP51 adds WP51-D001 (provenance/staleness hardening beyond
foundation not started), WP51-D002 (resolution-rule ambiguity extraction not
started), WP51-D003 (microstructure quality feature extraction beyond basic
availability not started), and WP51-D004 (CLI/export/report writer not started).

Security checks are run/assessed in WP51.

## WP50 Research Data Foundation Direction Lock-In After WP49 Merge

WP50 - Research Data Foundation Direction Lock-In After WP49 Merge is merged
(merge commit 180a6547114824890851d6ba7e34ab96e7ddd4b8).
It reconciles repo truth after WP49 merge and locks the completed Polymarket
research-phase decisions into durable repo-truth documentation.

WP50 adds `docs/research_data_foundation_direction.md` as a new docs-only
direction lock recording the final research-phase decisions, approved near-term
sequence, blocked directions, non-signal semantics, and new-chat onboarding
summary. It updates `docs/project_status.md`, `docs/repo_truth_index.md`, and
`docs/deferred_items_log.md`, and adds a focused docs test at
`tests/test_research_data_foundation_direction_docs.py`.

WP50 is a docs/tests-only repo-truth reconciliation and research-direction
decision lock WP. It adds no runtime source under `src/`, no scoring
implementation, no feature extraction implementation, no CLI/export/report
writer, no dependency or lock-file changes, no Hermes/LLM/provider integration,
no credentials, no network/account access, no trading or paper trading, no
database/dashboard/scheduler/polling/product behavior, and no generated
outputs committed.

WP50 reconciles docs/project_status.md after WP49 merge (merge commit
3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d). WP49 is now listed in merged WPs.

WP50 preserves WP49-D001, WP49-D002, and WP49-D003 as OPEN. WP50 adds
WP50-D001 (research direction locked, but implementation sequencing still
requires explicit future WPs, OPEN, P3).

Security checks are run/assessed in WP50.

## WP49 Market Research Priority Scoring Core Implementation

WP49 - Market Research Priority Scoring Core Implementation is merged
(merge commit 3ee02a7c31a1d4f5d599fdb1d5ffa83d6fca1d6d).
It implements the first minimal local/offline/read-only core scorer for the
Market Research Priority Scoring Layer defined in WP44 (design) and WP48
(output contract).

WP49 adds `src/data_layer/market_research_priority_scoring.py` as a new
stdlib-only local/offline/read-only core scorer module. It adds focused tests
at `tests/test_market_research_priority_scoring_core.py` and updates
`docs/market_research_priority_scoring_output_contract.md`,
`docs/market_research_priority_scoring_layer.md`, `docs/project_status.md`,
`docs/repo_truth_index.md`, `docs/deferred_items_log.md`, and
`tests/test_market_research_priority_scoring_output_contract_docs.py`.

WP49 is a local/offline/read-only source-implementation WP. The core scorer
is stdlib-only, in-memory output only, no network, no file writes, no CLI,
no export, no report writer, no feature extraction from real artifacts, no
advisory consumer integration, no runtime/product/trading behavior, no
Hermes/LLM/provider integration, no credentials, no account access, no
trading or paper trading, no database/dashboard/scheduler/polling/product
behavior, and no generated outputs committed. No dependency or lock-file
changes.

WP49 reconciles docs/project_status.md after WP48 merge (merge commit
9e9d6cb1434cb831006f75ed142899ff2ebc675b). WP48 is now listed in merged WPs.

WP49 resolves WP44-D001, WP44-D002, WP48-D001, and WP48-D002 only for the
local/offline/read-only core scorer scope. WP49 adds WP49-D001 (feature
extraction from local/offline artifacts not started, OPEN, P3), WP49-D002
(CLI/export/report writer not started, OPEN, P3), and WP49-D003 (core scorer
not integrated with advisory consumer or market catalog, OPEN, P3). All
WP48-forward deferred items that are not resolved by WP49 remain unchanged.

Security checks are run/assessed in WP49.

## WP48 Market Research Priority Scoring Schema / Output Contract

WP48 - Market Research Priority Scoring Schema / Output Contract is merged
(merge commit 9e9d6cb1434cb831006f75ed142899ff2ebc675b).
It defines the formal schema and output contract for the future local/offline/read-only
Market Research Priority Scoring Layer designed in WP44.

WP48 adds `docs/market_research_priority_scoring_output_contract.md` as a new binding
docs-only output contract. It updates `docs/market_research_priority_scoring_layer.md`
to reference the new contract and update status. It adds a focused docs test at
`tests/test_market_research_priority_scoring_output_contract_docs.py` and updates
`tests/test_market_research_priority_scoring_layer_docs.py`, `docs/project_status.md`,
`docs/repo_truth_index.md`, and `docs/deferred_items_log.md`.

WP48 is a docs/tests-only schema and output-contract WP. It adds no runtime source under
`src/`, no scoring implementation, no CLI tooling, no JSON writer, no report writer,
no dependency or lock-file changes, no Hermes/LLM/provider integration, no credentials,
no network/account access, no trading or paper trading, no database/dashboard/scheduler/
polling/product behavior, and no generated outputs committed.

WP48 reconciles docs/project_status.md after WP47 merge (merge commit
8436ce1c75b705b1154a6edcb9c4c1a7d0615ab4). WP47 is now listed in merged WPs.

WP48 resolves no existing deferred items. WP44-D001 and WP44-D002 remain OPEN because
implementation is still not started. WP48 adds WP48-D001 (Market Research Priority Scoring
implementation not started after schema/output contract, OPEN, P3) and WP48-D002
(schema/output contract not enforced by implementation yet, OPEN, P3). All WP47-forward
deferred items remain unchanged.

Security checks are run/assessed in WP48.

## WP47 Posted PR Evidence Review Hardening

WP47 - Posted PR Evidence Review Hardening is merged
(historical branch: `wp47-posted-pr-evidence-review-hardening`).
It hardened the PR evidence workflow so future PRs do not require repeated manual
follow-ups for stale PR body text, stale final comments, placeholder SHAs, stale
inline test counts, or ambiguity between old and current evidence comments.

WP47 updates `tools/git/pr_evidence_consistency_guard.py` with five new optional
flags: `--forbid-inline-test-counts`, `--forbid-placeholder-evidence`,
`--require-current-final-marker`, `--forbid-stale-count-tokens`, and
`--require-posted-evidence-note`. It updates
`tests/tools/git/test_pr_evidence_consistency_guard.py` with focused tests for
all new flags, and updates `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md`,
`docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`, and
`docs/project_status.md`. It also adds a new optional doc at
`docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md` and updates
`docs/repo_truth_index.md` and `docs/deferred_items_log.md`.

WP47 is a local/offline stdlib governance-helper hardening WP. It adds no runtime
source under `src/`, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP47 reconciles docs/project_status.md after WP46 merge (merge commit
47e349bdc6eb1eb084d9b944e8aa66874730e08b). WP46 is now listed in merged WPs.

WP47 resolves no existing deferred items. WP47 adds WP47-D001 (guard still does
not fetch live GitHub PR body/comments, OPEN, P4). All WP46-forward deferred
items remain unchanged.

Security checks are run/assessed in WP47.

## WP46 PR Evidence Consistency Guard Helper

WP46 - PR Evidence Consistency Guard Helper is merged
(historical branch: `wp46-pr-evidence-consistency-guard-helper`).
It adds a local/offline/stdlib-only CLI helper at
`tools/git/pr_evidence_consistency_guard.py` that checks PR body and final
comment drafts for consistency before Ready for review: YES.

WP46 adds `tools/git/pr_evidence_consistency_guard.py` as the guard helper,
`tests/tools/git/test_pr_evidence_consistency_guard.py` as focused tests,
and `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` as the user-facing reference.
It updates `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`,
`docs/project_status.md`,
`docs/repo_truth_index.md`, and
`docs/deferred_items_log.md`.

WP46 is a local/offline stdlib governance helper WP. It adds no runtime source
under `src/`, no dependency or lock-file changes, no Hermes/LLM/provider
integration, no credentials, no network/account access, no trading or paper
trading, no database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP46 resolves no existing deferred items. WP46 adds WP46-D001 (guard validates
local PR body/final comment drafts only, not live GitHub PR data). All
WP45-forward deferred items remain unchanged.

Security checks are run/assessed in WP46.

## WP45 Codex / Claude PR Evidence Reporting Hardening

WP45 - Codex / Claude PR Evidence Reporting Hardening is merged
(historical branch: `wp45-pr-evidence-reporting-hardening`).
It hardens workflow docs and review guidance so that exact PR evidence reporting
is mandatory for every future Codex / Claude Code work package.

WP45 adds `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` as a new central
workflow reference and updates `AGENTS.md`,
`docs/ai/codex/WP_EXECUTION_REPORT.md`,
`docs/ai/codex/PR_REVIEW_CHECKLIST.md`,
`docs/ai/codex/VALIDATION_MATRIX.md`,
`docs/ai/codex/CONCISE_REPORTING_RULES.md`,
`docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md`,
`docs/work_package_template.md`,
`docs/review_checklist.md`,
`docs/repo_truth_index.md`, and
`docs/project_status.md`.
It adds a focused docs test at
`tests/test_pr_evidence_reporting_discipline_docs.py`.

WP45 is docs/test-only. It adds no implementation, helper tooling, workflow
runner, prompt runner, runtime source, tools implementation, dependency or
lock-file changes, LLM/Hermes provider integration, credentials,
network/account access, trading or paper trading,
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP45 resolves no existing deferred items. All WP44-forward deferred items remain
unchanged.

Security checks are run/assessed in WP45.

## WP44 Market Research Priority Scoring Layer Design

WP44 - Market Research Priority Scoring Layer Design is merged
(historical branch: `wp44-market-research-priority-scoring-layer-design`).
It adds `docs/market_research_priority_scoring_layer.md` as a docs-only design
for a future local/offline/read-only Market Research Priority Scoring Layer,
updates `docs/repo_truth_index.md` and `docs/deferred_items_log.md`, and adds
a focused docs test at
`tests/test_market_research_priority_scoring_layer_docs.py`.

WP44 is docs/test-only. It adds no implementation, schema, CLI, report writer,
scoring logic, workflow runner, prompt runner, runtime source, tools
implementation, dependency or lock-file changes, LLM/Hermes provider integration,
credentials, network/account access, trading or paper trading,
database/dashboard/scheduler/polling/product behavior, and no generated outputs
committed.

WP44 resolves no existing deferred items. WP44 adds WP44-D001 (Market Research
Priority Scoring implementation not started, OPEN, P3) and WP44-D002 (Score
laundering mitigation not enforced by implementation, OPEN, P3). WP40-D002,
WP41-D002, WP42-D001, WP42-D002, WP28-D001, WP30-D001, WP32-D001, WP34-D001,
WP36-D001, and WP36-D002 remain OPEN.

Security checks are run/assessed in WP44.

## WP40 Local Advisory Consumer Prototype Update

WP40 - Local Advisory Consumer Prototype is merged.
It adds `tools/advisory/local_advisory_consumer.py`,
`docs/local_advisory_consumer_prototype.md`, and focused tests for a
deterministic local/offline/read-only advisory consumer prototype.
Historical WP40 branch status before merge was
LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_ON_BRANCH; current WP40 status is
LOCAL_OFFLINE_READ_ONLY_ADVISORY_CONSUMER_MERGED.

The prototype consumes only explicitly provided local files under
`local_data/agent_context_exports/` and `local_data/agent_context_reports/`.
It writes no file by default and may write optional advisory output only under
ignored `local_data/advisory_outputs/`.

The prototype supports text and JSON output, sensitive-like content redaction,
review questions, risk/uncertainty notes, human-review checklist output, and
repo-truth/validation reminders. It is advisory-only and human-review-required.

WP40 adds no runtime source under `src/`, no dependency or lock-file changes,
no Hermes/LLM/provider integration, no credentials, no network/account access,
no trading or paper trading, no database/dashboard/scheduler/polling/product
behavior, and no generated outputs committed.

WP38-D002 and WP39-D001 are resolved only for this deterministic
local/offline/read-only advisory consumer prototype scope. WP39-D002 and
WP40-D001 are resolved by WP41 only for docs-only advisory prompt/runbook
package scope. WP40-D002 remains OPEN for the remaining LLM/Hermes/provider
integration gap.

Security checks were run/assessed in WP40.

## WP43 Repo-Truth Status Reconciliation After WP42 Merge

WP43 - Repo-Truth Status Reconciliation After WP42 Merge is on branch
(`wp43-repo-truth-status-reconciliation-after-wp42-merge`).
It updates `docs/project_status.md` to reflect WP42 merge (commit
6b93576842f862faafbc0b25d54104cd1826e28e) and adds a focused project-status
docs test at `tests/test_project_status_docs.py`.

WP43 is docs/test-only. It adds no implementation, workflow runner, prompt
runner, runtime source, tools implementation, dependency or lock-file changes,
LLM/Hermes provider integration, credentials, network/account access, trading or
paper trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP43 resolves no deferred items. WP40-D002, WP41-D002, WP42-D001, WP42-D002,
WP28-D001, WP30-D001, WP32-D001, WP34-D001, WP36-D001, and WP36-D002 remain
OPEN.

Security checks are run/assessed in WP43.

## WP42 Advisory Consumer Operator Workflow Hardening Update

WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening is
merged (merge commit 6b93576842f862faafbc0b25d54104cd1826e28e).
It adds `docs/advisory_consumer_operator_workflow.md` and focused docs tests
for the end-to-end human-operated advisory workflow.

The workflow connects repo-truth verification, explicit local artifact
selection, freshness/provenance checks, optional WP40 local advisory consumer
use, WP41 manual prompt/runbook use, forbidden-input and forbidden-output
rejection gates, decision logging, and conversion of any accepted observation
into a separate approved WP.

WP42 is docs/test-only. It adds no implementation, workflow runner, prompt
runner, runtime source, tools implementation, dependency or lock-file changes,
LLM/Hermes provider integration, credentials, network/account access, trading or
paper trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP41-D001 is resolved only for docs-only advisory consumer integration review /
operator workflow hardening scope. WP40-D002 and WP41-D002 remain OPEN because
LLM/Hermes/provider integration and provider/Hermes decision refresh are not
designed, selected, or implemented.

Security checks are run/assessed in WP42.

Historical next-WP candidates after WP42 were WP43 - Provider/Hermes Decision Refresh, WP43 - Local Advisory Workflow Follow-Up, and another explicitly approved safe repo-truth WP. WP43 selects the repo-truth status reconciliation path only.

## WP41 Advisory Prompt/Runbook Package Update

WP41 - Advisory Prompt/Runbook Package is merged.
It adds `docs/advisory_prompt_runbook_package.md` and focused docs tests for
human-operated advisory prompt templates and operator review steps.

The package covers read-only market-state analysis, performance review from
local reports/exports, market research question planning, strategy hypothesis
narrative, and Codex / WP planning support. All outputs remain
ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

WP41 is docs/test-only. It adds no implementation, prompt runner, runtime
source, tools implementation, dependency or lock-file changes, LLM/Hermes
provider integration, credentials, network/account access, trading or paper
trading, database/dashboard/scheduler/polling/product behavior, and no
generated outputs committed.

WP39-D002 and WP40-D001 are resolved only for docs-only advisory prompt/runbook
package scope. WP40-D002 remains OPEN because LLM/Hermes/provider integration is
not designed or implemented. WP41 adds WP41-D001 and WP41-D002 for the remaining
advisory consumer workflow-hardening and provider/Hermes decision-refresh gaps.

Security checks are run/assessed in WP41.

Historical next-WP candidates after WP41 were WP42 - Advisory Prompt/Runbook Package Follow-Up, WP42 - Advisory Consumer Integration Review / Operator Workflow Hardening, and WP42 - Provider/Hermes Decision Refresh. WP42 selects the advisory consumer operator workflow hardening path only.

## WP39 Advisory Runtime Boundary And Consumption Design Update

WP39 - Advisory Runtime Boundary And Consumption Design is merged.
It adds `docs/advisory_runtime_boundary_consumption_design.md` and focused
docs tests to define the future local/offline/read-only advisory consumer
boundary and consumption model.
Historical WP39 planning also named WP40 - Advisory Runtime Boundary Design Follow-Up as an alternative follow-up label before the current WP40 prototype was selected.

WP38 - Local Advisory Handoff Package is merged. The previous WP38 alternative
next path, WP39 - Local Advisory Handoff Follow-Up, is historical context only;
WP39 selects the advisory runtime boundary and consumption design path.

The design defines allowed input sources, forbidden input sources, allowed
output types, forbidden output types, deterministic local advisory model,
LLM/Hermes separation, security/sanitization requirements, human-review
requirements, and future WP40 prototype constraints.

WP39 is docs/test-only. It adds no advisory consumer implementation, no runtime
source, no tools implementation, no dependencies, no lock files, no generated
outputs, no Hermes/LLM/provider runtime, no credentials, no network/account
access, no trading, no database/dashboard/scheduler/polling/product behavior,
and no protected-boundary change.

WP38-D001 is resolved only for docs-only design completion. WP38-D002 remains
OPEN because the local advisory consumer prototype is not implemented. WP39
adds WP39-D001 for the unimplemented local advisory consumer prototype and
WP39-D002 for the unimplemented advisory prompt/runbook package.

Security checks were run/assessed in WP39.

## WP37 Token Efficiency Sequence Closeout / Repo Truth Consolidation Update

WP37 - Token Efficiency Sequence Closeout / Repo Truth Consolidation is merged.
It added `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md` and kept the
post-closeout next-WP gate explicit. Before WP38 was selected, the allowed
candidate paths included WP38 - Local Advisory Handoff Package, WP38 - Token Efficiency Closeout Follow-Up, or another explicitly approved safe repo-truth WP. WP38 selects the local advisory handoff package path only.

## WP33 Code Index / Blast-Radius Helper Design Update

WP33 is a Tier 1 docs-only code-index / blast-radius helper design package. It
creates `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` and updates
`docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` and
`docs/project_status.md`, plus repo-truth review and testing guidance for the
design.

The design records guidance for a future advisory helper, including
source-of-truth boundary, allowed behavior, disallowed behavior, suggested
inputs/outputs, freshness/staleness rules, protected-boundary handling, future
CLI/JSON shape, future tests, manual-step rule, implementation prerequisites,
stop conditions, and future implementation requirements.

Manual steps for this package: none.

WP33 does not implement a code-index helper, does not create generated index
files, does not reduce validation, and does not implement validation wrappers,
command-running wrapper modes, memory files, runtime behavior, paper/live
behavior, OMS, risk, safe mode, schemas, validators, query-layer code, policy,
scoring, ranking, recommendations, approval, promotion/demotion, readiness,
lifecycle, or downstream authority.

After merge, the next token-efficiency improvement package may be drafted from
refreshed `main`, likely memory/status snapshot design, code-index
implementation, or another approved efficiency package, subject to no stop
trigger and no competing `docs/project_status.md` PR.

## WP34 Code Index / Blast-Radius Helper Implementation Update

WP34 is a local-tooling implementation WP. It implements the advisory helper
designed in WP33 under `tools/git/code_blast_radius.py`, adds focused tests
at `tests/tools/git/test_code_blast_radius.py`, and adds the user-facing
reference at `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md`.

The helper is:

- local/offline/read-only;
- standard-library only (no new dependency);
- on-demand scan mode only (no persistent index);
- advisory only (does not replace validation, security checks, or human review);
- no network, no command execution, no file mutation by default;
- optional output restricted to `local_data/code_blast_radius/`.

WP34 resolves WP30-D002 for the tested local/offline/read-only stdlib code-index
/ blast-radius helper scope. WP28-D001, WP30-D001, and WP32-D001 remain OPEN.
WP34 adds WP34-D001 for persistent snapshot/index file mode not implemented.

Security checks were run/assessed in WP34.

Manual steps for this package: none.

## WP36 Memory / Status Snapshot Helper Implementation Update

WP36 is a local-tooling implementation WP. It implements the advisory helper
designed in WP35 under `tools/git/status_snapshot.py`, adds focused tests
at `tests/tools/git/test_status_snapshot.py`, and adds the user-facing
reference at `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md`.

The helper is:

- local/offline/read-only;
- standard-library only (no new dependency);
- no command execution (reads local .git files directly; handles git worktrees);
- advisory only (does not replace repo truth, validation, security checks, or human review);
- no network, no command execution, no file mutation by default;
- optional output restricted to `local_data/status_snapshots/`.

Implemented features: text and JSON output, safe input allowlist, deferred item
digest, helper inventory, next WP candidates, protected boundary status,
staleness metadata, `--check-stale`, `--fail-on-stale`, sensitive redaction,
`--fail-on-sensitive-hit`. Markdown output deferred (exits 2). Input file hashes
deferred.

WP36 resolves WP35-D001 for the tested local/offline/read-only stdlib helper
scope. WP28-D001, WP30-D001, WP32-D001, and WP34-D001 remain OPEN.
WP36 adds WP36-D001 (Markdown output deferred) and WP36-D002 (input file hashes
deferred).

Security checks were run/assessed in WP36.

Manual steps for this package: none.

## WP35 Memory / Status Snapshot Helper Design Update

WP35 is a docs-only design package. It creates
`docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` and updates
`docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md`,
`docs/ai/codex/README.md`, plus repo-truth and testing guidance for the design.

The design records guidance for a future advisory helper, including design
status, authority model, safe and prohibited input sources, intended future
modes, CLI shape, output structure, sanitization model, staleness model,
snapshot lifecycle and storage policy, relationship to existing helpers, future
implementation test plan, open design questions, and recommended next WP.

WP35 does not implement a memory/status snapshot helper, does not create
generated snapshot output, does not add persistent memory files, does not add
command runners, does not reduce validation, and does not implement network
access, Hermes, LLM, credentials, or trading functionality.

WP35 adds WP35-D001 for memory/status snapshot helper implementation not
started. WP28-D001, WP30-D001, WP32-D001, and WP34-D001 remain OPEN.

Security checks were run/assessed in WP35.

Manual steps for this package: none.

## Open Decisions

- Final live execution language and service boundaries remain undecided.
- Whether future architecture uses the official Python V2 client, TypeScript V2 client, or both behind internal adapters. The Python V2 client is candidate-only and not installed in WP14/WP15/WP16.
- Whether relayer clients are needed; they remain study-only until license and protected-boundary review.
- Whether cross-market/Kalshi work belongs in a later research-only WP.
- VPS or cloud deployment jurisdiction and operational model.
- Dashboard scope for first Streamlit prototype.
- Security tooling setup must run before runtime dependency integration, copied code, vendoring, or live/API execution.
- CLOB /health correct endpoint path unknown (WP9-D001).
- Rate-limit policy not confirmed (WP8-D002).
- Automated, scheduled, or higher-frequency public market-data polling requires a future approved WP with authoritative rate-limit evidence and repo-truth updates.
- AI-agent and Hermes integrations remain advisory-only. WP23 implements a local/offline/read-only context exporter only, WP24 documents safe manual operator use for that exporter, WP25 adds deterministic local/offline/read-only report generation only, and WP26 documents safe manual report-generator operation. Any future runtime selection, provider choice, command approval, network permission, memory policy, or installation requires future human approval and repo-truth work packages.
