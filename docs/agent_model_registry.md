# Agent Model Registry

This registry records policy status for possible AI-agent roles. It is not an implementation plan and does not authorize runtime use.

| Role or capability | Status | Boundary |
|---|---|---|
| Read-only analysis | POLICY_ONLY_NOT_IMPLEMENTED; READ_ONLY_ONLY; NO_EXECUTION_AUTHORITY; FUTURE_WP_REQUIRED | May summarize approved local docs, snapshots, and reports only after future exporter approval. |
| Performance review | POLICY_ONLY_NOT_IMPLEMENTED; READ_ONLY_ONLY; NO_EXECUTION_AUTHORITY; FUTURE_WP_REQUIRED | Advisory review only after authorized logs and schemas exist. |
| Market research | POLICY_ONLY_NOT_IMPLEMENTED; READ_ONLY_ONLY; NO_EXECUTION_AUTHORITY; FUTURE_WP_REQUIRED | Advisory candidates only after rate-limit and data policies allow it. |
| Strategy suggestion | POLICY_ONLY_NOT_IMPLEMENTED; READ_ONLY_ONLY; NO_EXECUTION_AUTHORITY; FUTURE_WP_REQUIRED | Hypotheses and human-review proposals only; no executable trade proposals in WP20. |
| Codex / WP support | POLICY_ONLY_NOT_IMPLEMENTED; READ_ONLY_ONLY; NO_EXECUTION_AUTHORITY; FUTURE_WP_REQUIRED | Repo-truth summaries and candidate WP drafting only; no autonomous PR approval, merge, branch creation, or execution. |
| Fully autonomous trading agent | EXCLUDED_FOR_NOW; NO_BUILD_PATH | Future reconsideration requires explicit repo-truth decision, risk gateway, live authorization, incident response, and human approval. |

All accepted advisory output must flow through human review, approved config changes, or normal Codex work packages before it changes the repository or operating behavior.

