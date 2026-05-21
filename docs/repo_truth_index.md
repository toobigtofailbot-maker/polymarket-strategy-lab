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
25. `docs/architecture_principles.md` - platform architecture principles.
26. `docs/architecture_skeleton.md` - WP3 non-runtime architecture skeleton.
27. `docs/runtime_boundaries.md` - protected runtime boundary rules.
28. `docs/interface_contracts.md` - conceptual interface contracts for future implementation.
29. `docs/mode_separation.md` - historical, read-only, paper, and live mode separation.
30. `docs/security_tooling_requirements.md` - required future security and dependency-audit tooling gates.
31. `docs/security_tooling_status.md` - current security-tool availability and scan status.
32. `docs/security_tooling_installation.md` - approved security-tool installation and verification guidance.
33. `docs/security_tooling_completion.md` - WP5 project-local security tooling and Remote Main Sync Gate outcomes.
34. `docs/data_semantics.md` - shared data definitions.
35. `docs/wallet_copy_trading_semantics.md` - wallet and copy-trading terminology.
36. `docs/risk_semantics.md` - risk definitions and initial posture.
37. `docs/live_trading_authorization.md` - live trading gate and authorization table.
38. `docs/security_and_secrets.md` - credential and incident rules.
39. `docs/codex_execution_guidelines.md` - work-package execution process.
40. `docs/work_package_template.md` - reusable WP template.
41. `docs/review_checklist.md` - review readiness checklist.
42. `docs/testing_requirements.md` - current and future test requirements.

Codex workflow docs are authoritative for Codex execution guidance, but they do not outrank `AGENTS.md`, `docs/project_status.md`, `docs/deferred_items_log.md`, or active work-package constraints.

Any material policy or architecture change must update the relevant repo-truth file in the same WP.

