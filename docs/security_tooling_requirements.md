# Security Tooling Requirements

## Purpose

This document defines security and dependency-audit tooling gates for future runtime work. These tools are not mandatory for documentation-only work packages. They become mandatory before runtime dependency integration, vendoring, forking, copied external code, or live/API execution.

## Tool Requirements

| Tool | Purpose | Mandatory before |
|---|---|---|
| gitleaks | Secret scanning for committed credentials, key material, tokens, and high-risk patterns. | External dependency runtime integration, vendoring, copied code, or live/API execution. |
| semgrep | Static security and code-pattern scanning for risky source patterns. | Copied external code, runtime integration, venue API clients, or live/API execution. |
| npm audit | Node and TypeScript dependency vulnerability scanning. | TypeScript client integration, dashboard/runtime dependency installation, or Node runtime work. |
| pip-audit | Python dependency vulnerability scanning. | Python client integration, Python runtime dependency installation, or Python service work. |
| cargo audit | Rust dependency vulnerability scanning. | Any Rust runtime component, if Rust is selected for runtime scope. |

## Rules

- Documentation-only work packages may proceed without these tools if no runtime dependencies, venue clients, copied code, or live/API execution paths are added.
- Detection and scan wrapper scripts live under `tools/security/`.
- Project-local `.venv-security/` is allowed for security tools only.
- `tools/security/setup_project_security_tools.py` may install only approved security tools into `.venv-security/`.
- Project-local security tool installation is not runtime dependency integration.
- Project-local tool environments and portable binaries must remain ignored and uncommitted.
- The Remote Main Sync Gate is separate from security scanning but mandatory before future WP branch creation.
- Before installing, vendoring, forking, or copying external runtime code, the relevant tool must be installed and run, or an approved equivalent must be documented in repo truth.
- Runtime dependency integration cannot proceed unless relevant checks have been run and documented, or an approved equivalent or explicit user deferral is documented in repo truth.
- Audit output must be documented in the relevant work package artifacts before runtime use is approved.
- A passing scan does not grant live execution authority. Live execution still requires `docs/live_trading_authorization.md` to be explicitly updated in a future approved work package.
- If a required tool is unavailable, add or update an entry in `docs/deferred_items_log.md` and record the current status in `docs/security_tooling_status.md`.
