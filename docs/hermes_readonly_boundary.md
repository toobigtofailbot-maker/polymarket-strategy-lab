# Hermes Read-Only Boundary

## Current Status

- Hermes not installed.
- No repo dependency.
- No commands rely on Hermes.
- No Hermes config in repo.
- No Hermes memory or persistence.
- No Hermes network permission.
- No Hermes account connection.
- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY.

WP20 records boundary policy only. Hermes is not required for the repository, is not installed by this work package, and is not a runtime dependency.

WP21 adds a schema-only contract for future local read-only agent context exports in `docs/agent_context_export_schema.md`. Hermes may later consume compliant local context exports only after a future approved setup and human review path. WP21 adds no Hermes runtime, dependency, setup, config, account connection, network permission, memory store, or command authority.

WP23 adds a local/offline/read-only context exporter that writes JSON only under ignored `local_data/agent_context_exports/` when explicitly requested. Hermes may later consume exported local JSON only after future manual setup and an approved work package. WP23 does not install, configure, or depend on Hermes and adds no Hermes network permission, memory store, account connection, runtime, or command authority.

WP24 adds `docs/agent_context_exporter_operator_runbook.md` for safe manual exporter operation. Hermes remains not installed, not configured, and not a runtime dependency.

## Future Work Codex Can Likely Handle Automatically

In future approved work packages, Codex can likely handle:

- repo-truth policy docs;
- local read-only context schema;
- local export command using existing local files only after a future approved exporter WP;
- prompt templates;
- operator instructions;
- tests enforcing no execution authority;
- static safety checks.

These future items still require normal repo-truth review and must not bypass protected runtime boundaries.

## Future Manual User Decisions

The user must likely handle or explicitly approve:

- installing Hermes if selected;
- choosing local, VPS, or cloud runtime;
- choosing model or API provider;
- providing provider keys outside the repo;
- approving exact allowed commands;
- approving network access if ever used;
- approving memory or persistence location;
- reviewing generated reports manually.

## Proposed Future Read-Only Command Classes

A future approved Hermes or agent setup may be limited to:

- read local docs;
- read local generated reports under ignored `local_data/` only if the user runs them locally;
- run local offline report commands only after future work packages authorize them;
- no mutation commands without human review and the normal Codex work-package flow.

## Forbidden Command Classes

The following command classes are FORBIDDEN:

- any command reading `.env`;
- any command reading credential or key files;
- any command invoking authenticated clients;
- any command placing, canceling, or signing orders;
- any command starting a scheduler, daemon, or bot loop;
- any command modifying configs automatically;
- any command pushing or merging branches unless explicitly routed through Codex workflow and human review.

## Manual Setup Note

WP20 does not provide Hermes installation instructions. Setup instructions will be created in a future work package only if Hermes is selected and after the manual environment choice is approved.

