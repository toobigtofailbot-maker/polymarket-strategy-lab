# Repo Truth Index

Repo-truth files are authoritative project memory. They override chat memory, old handoffs, and ad hoc instructions unless explicitly updated by a later approved work package.

## Authority Hierarchy

1. `AGENTS.md` - Codex rulebook and protected operating rules.
2. `docs/project_charter.md` - project objective, scope, risk posture, and strategic direction.
3. `docs/project_status.md` - current phase, branch, merged WPs, and open decisions.
4. `docs/deferred_items_log.md` - deferred material issues, unavailable tools, blocked security checks, and postponed decisions.
5. `docs/source_repo_registry.md` - candidate external source repositories and audit status.
6. `docs/repo_reuse_strategy.md` - allowed external repo reuse paths and constraints.
7. `docs/repo_reuse_decision_matrix.md` - WP2 candidate repository reuse decisions.
8. `docs/official_python_client_dependency_decision.md` - WP14 official Python client dependency decision.
9. `docs/polymarket_client_boundary_review.md` - WP14 official client boundary rules.
10. `docs/ai_agent_integration_policy.md` - WP20 AI-agent advisory-only integration policy.
11. `docs/hermes_readonly_boundary.md` - WP20 Hermes read-only boundary and manual setup policy.
12. `docs/agent_model_registry.md` - WP20 allowed advisory agent role registry.
13. `docs/architecture_principles.md` - platform architecture principles.
14. `docs/architecture_skeleton.md` - WP3 non-runtime architecture skeleton.
15. `docs/runtime_boundaries.md` - protected runtime boundary rules.
16. `docs/interface_contracts.md` - conceptual interface contracts for future implementation.
17. `docs/mode_separation.md` - historical, read-only, paper, and live mode separation.
18. `docs/security_tooling_requirements.md` - required future security and dependency-audit tooling gates.
19. `docs/security_tooling_status.md` - current security-tool availability and scan status.
20. `docs/security_tooling_installation.md` - approved security-tool installation and verification guidance.
21. `docs/security_tooling_completion.md` - WP5 project-local security tooling and Remote Main Sync Gate outcomes.
22. `docs/data_semantics.md` - shared data definitions.
23. `docs/wallet_copy_trading_semantics.md` - wallet and copy-trading terminology.
24. `docs/risk_semantics.md` - risk definitions and initial posture.
25. `docs/live_trading_authorization.md` - live trading gate and authorization table.
26. `docs/security_and_secrets.md` - credential and incident rules.
27. `docs/codex_execution_guidelines.md` - work-package execution process.
28. `docs/work_package_template.md` - reusable WP template.
29. `docs/review_checklist.md` - review readiness checklist.
30. `docs/testing_requirements.md` - current and future test requirements.

Any material policy or architecture change must update the relevant repo-truth file in the same WP.

