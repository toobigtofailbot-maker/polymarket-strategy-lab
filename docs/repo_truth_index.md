# Repo Truth Index

Repo-truth files are authoritative project memory. They override chat memory, old handoffs, and ad hoc instructions unless explicitly updated by a later approved work package.

## Authority Hierarchy

1. `AGENTS.md` - Codex rulebook and protected operating rules.
2. `docs/project_charter.md` - project objective, scope, risk posture, and strategic direction.
3. `docs/project_status.md` - current phase, branch, merged WPs, and open decisions.
4. `docs/deferred_items_log.md` - deferred material issues, unavailable tools, blocked security checks, and postponed decisions.
5. `CODEX_START_HERE.md` - Codex startup sequence and stop rules.
6. `docs/ai/codex/README.md` - Codex operating modes and workflow precedence.
7. `docs/ai/codex/WP_EXECUTION_REPORT.md` - mandatory WP final report PR comment format.
8. `docs/ai/codex/VALIDATION_MATRIX.md` - package-class validation guidance.
9. `docs/ai/codex/PR_REVIEW_CHECKLIST.md` - Codex PR review discipline.
10. `docs/ai/codex/PROJECT_STATUS_UPDATE_RULES.md` - current-WP status wording rules.
11. `docs/ai/codex/PROTECTED_PATHS.md` - Codex protected path and boundary guidance.
12. `docs/source_repo_registry.md` - candidate external source repositories and audit status.
13. `docs/repo_reuse_strategy.md` - allowed external repo reuse paths and constraints.
14. `docs/repo_reuse_decision_matrix.md` - WP2 candidate repository reuse decisions.
15. `docs/official_python_client_dependency_decision.md` - WP14 official Python client dependency decision.
16. `docs/polymarket_client_boundary_review.md` - WP14 official client boundary rules.
17. `docs/ai_agent_integration_policy.md` - WP20 AI-agent advisory-only integration policy.
18. `docs/hermes_readonly_boundary.md` - WP20 Hermes read-only boundary and manual setup policy.
19. `docs/agent_model_registry.md` - WP20 allowed advisory agent role registry.
20. `docs/agent_context_export_schema.md` - WP21 read-only advisory agent context export schema contract.
21. `docs/agent_context_exporter.md` - WP23 local/offline/read-only agent context exporter boundary and usage.
22. `docs/agent_context_exporter_operator_runbook.md` - WP24 local operator runbook for safe manual exporter use.
23. `docs/agent_context_report_generator.md` - WP25 local/offline/read-only analyst report generator boundary and usage.
24. `docs/agent_context_report_operator_runbook.md` - WP26 local operator runbook for safe manual analyst report generation.
25. `docs/agent_hermes_manual_setup_decision_record.md` - WP27 decision record defining manual setup gates and approval steps before any future Hermes or agent runtime work.
26. `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` - WP28 token-efficiency operating model: context hygiene, validation-output summarization, concise reporting, reusable prompt-block rules, and future helper-tool design gates.
27. `docs/ai/codex/CONCISE_REPORTING_RULES.md` - WP28 mandatory concise final-report format and omission rules for Codex and Claude Code.
28. `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` - WP28 reusable standard blocks for preflight, security, validation, reporting, safety, generated artifacts, and stop/escalation.
29. `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` - WP29 design-only document for the local/offline/read-only diff scope summary helper; WP30 added implementation decisions in Section 14.
30. `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md` - WP30 user-facing reference for the implemented local/offline/read-only diff scope summary helper (`tools/git/diff_scope_summary.py`).
31. `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` - WP31 design document for the local/offline/read-only validation-output summary helper; WP32 added implementation decisions in Section 17.
32. `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md` - WP32 user-facing reference for the implemented local/offline/read-only validation output summary helper (`tools/validation/validation_output_summary.py`).
33. `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` - WP33 design document for the advisory code-index / blast-radius helper; WP34 added implementation decisions in Section 19.
34. `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md` - WP34 user-facing reference for the implemented local/offline/read-only code-index / blast-radius advisory helper (`tools/git/code_blast_radius.py`).
35. `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` - WP35 design document for the local/offline/read-only memory/status snapshot helper; WP36 added implementation decisions in Section 19.
36. `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md` - WP36 user-facing reference for the implemented local/offline/read-only memory/status snapshot helper (`tools/git/status_snapshot.py`).
37. `docs/ai/codex/TOKEN_EFFICIENCY_SEQUENCE_CLOSEOUT.md` - WP37 docs-only closeout for the WP28-WP36 token-efficiency helper sequence; defines advisory helper usage order, deferred helper gaps, protected-boundary reaffirmation, and the next-WP resumption gate.
38. `docs/local_advisory_handoff_package.md` - WP38 docs-only local advisory handoff package defining allowed advisory capabilities, forbidden runtime/trading capabilities, manual setup status, and the recommended post-WP38 path.
39. `docs/advisory_runtime_boundary_consumption_design.md` - WP39 docs-only advisory runtime boundary and local advisory consumption design for future local/offline/read-only advisory consumers.
40. `docs/local_advisory_consumer_prototype.md` - WP40 local/offline/read-only deterministic advisory consumer prototype usage and boundary reference.
41. `docs/advisory_prompt_runbook_package.md` - WP41 docs-only human-operated advisory prompt/runbook package for safe local/offline/read-only advisory use.
42. `docs/advisory_consumer_operator_workflow.md` - WP42 docs-only operator workflow hardening for safe human-operated use of the local advisory consumer and prompt/runbook package.
43. `docs/market_research_priority_scoring_layer.md` - WP44 docs-only design for the future local/offline/read-only Market Research Priority Scoring Layer; defines research_priority_score, allowed/forbidden inputs and outputs, score laundering risk, staleness/provenance requirements, human-review requirements, and future implementation gates. Updated in WP48 to reference the output contract.
44. `docs/market_research_priority_scoring_output_contract.md` - WP48 docs-only schema and output contract for the future local/offline/read-only Market Research Priority Scoring Layer; defines top-level output schema, market object schema, score components, advisory-only labels, staleness/provenance/missing-data contracts, forbidden fields, safe and invalid examples, and future implementation gates. Updated in WP49 to reflect core scorer on branch.
45. `src/data_layer/market_research_priority_scoring.py` - WP49 local/offline/read-only core scorer for the Market Research Priority Scoring Layer; stdlib-only, in-memory output only, no network, no file writes, no CLI, no export, no feature extraction, no advisory consumer integration, no runtime/product/trading behavior; implements compute_research_priority_score, build_market_research_priority_output, validate_market_research_priority_output, assert_market_research_priority_output, and contains_forbidden_output_fields per the WP48 contract.
46. `docs/research_data_foundation_direction.md` - WP50 docs-only direction lock recording final research-phase decisions after WP49 merge; authoritative for: final research-phase direction, approved near-term research-data foundation candidate sequence, blocked directions and non-signal boundaries, and onboarding future chats for scoring/research-foundation work. It does not override docs/project_status.md for current state, docs/deferred_items_log.md for deferred items, or docs/market_research_priority_scoring_output_contract.md for schema/output contract. Updated in WP51 to reflect WP50 merge and WP51 feature extraction foundation on branch.
47. `src/data_layer/market_research_priority_features.py` - WP51 local/offline/read-only feature extraction foundation; WP53 data-integrity hardening (provenance_degraded flag, provenance_weakness_reasons, provenance_warning, future_timestamp_detected, missing_question, missing_market_status detection); stdlib-only, in-memory output only, no network, no file writes, no CLI, no export/report; bridges MarketMetadataSnapshotRecord, OrderBookSnapshotRecord, and SnapshotManifest objects into prepared run_context and market_context dicts compatible with the WP49 core scorer; implements build_manifest_index, index_order_books_by_token_id, extract_market_research_priority_context, extract_market_research_priority_contexts, build_market_research_priority_run_context, and extract_from_snapshot_dir per the WP48 output contract, WP51 scope, and WP53 hardening.
48. `docs/long_term_bot_completion_roadmap.md` - WP52 docs-only long-term bot-completion roadmap and Side 4.0 onboarding lock (merged); authoritative for: long-term bot-completion roadmap, milestone and WP-range planning estimates, Side 4.0 onboarding context, and phase sequencing at planning level. Does not override `docs/project_status.md` for current state, `docs/deferred_items_log.md` for deferred items, `docs/research_data_foundation_direction.md` for locked near-term research-data direction, `docs/market_research_priority_scoring_output_contract.md` for score/output schema, or any future approved implementation WP. Planning guidance only — not authorization for any future phase.
49. `docs/ai/codex/PR_EVIDENCE_REPORTING_DISCIPLINE.md` - WP45 mandatory PR evidence reporting discipline for Codex and Claude Code; defines exact validation command requirements, no-ellipsis rule, network usage wording distinction, PR body and final comment consistency requirements, stale count correction gate, and reviewer action for evidence defects. Updated in WP54 with posted evidence self-check rule.
50. `docs/ai/codex/PR_EVIDENCE_CONSISTENCY_GUARD.md` - WP46 user-facing reference for the local/offline/stdlib PR evidence consistency guard (`tools/git/pr_evidence_consistency_guard.py`); defines purpose, non-goals, CLI usage, guard checks, pass/fail behavior, limitations, and relationship to WP45 evidence reporting discipline. Updated in WP47 with new flags (K–O), required workflow, and WP47 hardening limitations. Updated in WP54 with posted evidence self-check limitation note and new flag P (`--require-guard-result`).
51. `docs/ai/codex/POSTED_PR_EVIDENCE_REVIEW_HARDENING.md` - WP47 optional reference doc describing the failure pattern from PR #47, current-final evidence marker, posted evidence vs draft evidence, why inline test counts are forbidden, reviewer workflow, Claude Code / Codex workflow, known limitation (no GitHub API fetch), and deferred WP47-D001.
52. `docs/ai/codex/WP_BUNDLING_POLICY.md` - WP54 bundled-WP execution policy; defines risk-class bundling principle, package size classes (S/M/L/XL), allowed and forbidden bundle examples, L-package requirements, stop/report triggers, follow-up process-defect classification categories, and posted evidence self-check rule.
53. `docs/architecture_principles.md` - platform architecture principles.
54. `docs/architecture_skeleton.md` - WP3 non-runtime architecture skeleton.
55. `docs/runtime_boundaries.md` - protected runtime boundary rules.
56. `docs/interface_contracts.md` - conceptual interface contracts for future implementation.
57. `docs/mode_separation.md` - historical, read-only, paper, and live mode separation.
58. `docs/security_tooling_requirements.md` - required future security and dependency-audit tooling gates.
59. `docs/security_tooling_status.md` - current security-tool availability and scan status.
60. `docs/security_tooling_installation.md` - approved security-tool installation and verification guidance.
61. `docs/security_tooling_completion.md` - WP5 project-local security tooling and Remote Main Sync Gate outcomes.
62. `docs/data_semantics.md` - shared data definitions.
63. `docs/wallet_copy_trading_semantics.md` - wallet and copy-trading terminology.
64. `docs/risk_semantics.md` - risk definitions and initial posture.
65. `docs/live_trading_authorization.md` - live trading gate and authorization table.
66. `docs/security_and_secrets.md` - credential and incident rules.
67. `docs/codex_execution_guidelines.md` - work-package execution process.
68. `docs/work_package_template.md` - reusable WP template.
69. `docs/review_checklist.md` - review readiness checklist.
70. `docs/testing_requirements.md` - current and future test requirements.

Codex workflow docs are authoritative for Codex execution guidance, but they do not outrank `AGENTS.md`, `docs/project_status.md`, `docs/deferred_items_log.md`, or active work-package constraints.

Any material policy or architecture change must update the relevant repo-truth file in the same WP.

