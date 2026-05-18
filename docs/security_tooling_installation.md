# Security Tooling Installation

## Purpose

This document records practical installation and verification options for the security tools required before runtime dependency integration, copied external code, venue API integration, or live/API execution.

Security tools are mandatory before runtime dependency integration, vendoring, copied external code, venue API integration, or live/API execution. They are not mandatory for documentation-only work packages.

Passing these scans does not authorize live trading. Live trading remains disabled unless `docs/live_trading_authorization.md` is explicitly updated in a future approved work package.

## Tool Overview

| Tool | Purpose |
|---|---|
| gitleaks | Secret scanning for committed credentials, private keys, tokens, key material, and high-risk patterns. |
| semgrep | Static source-code security and unsafe-pattern scanning. |
| npm audit | Node/TypeScript dependency vulnerability scanning. |
| pip-audit | Python dependency vulnerability scanning. |
| cargo audit | Rust dependency vulnerability scanning. |

## Windows Installation Options

Use a user-approved local or system package manager. Codex must not globally install these tools without explicit user approval.

| Tool | Common options |
|---|---|
| gitleaks | GitHub release binary, package manager install, or approved internal tool image. |
| semgrep | Python package in an approved environment, package manager install, or approved internal tool image. |
| npm audit | Node.js LTS installer or approved Node version manager that provides `npm`. |
| pip-audit | Python package in an approved virtual environment or approved internal tool image. |
| cargo audit | Rust toolchain plus `cargo-audit` installed through an approved Rust tool workflow. |

## Linux/macOS Installation Options

Use a user-approved local or system package manager. Codex must not globally install these tools without explicit user approval.

| Tool | Common options |
|---|---|
| gitleaks | GitHub release binary, package manager install, or approved internal tool image. |
| semgrep | Python package in an approved environment, package manager install, or approved internal tool image. |
| npm audit | Node.js LTS package, approved Node version manager, or approved internal tool image. |
| pip-audit | Python package in an approved virtual environment or approved internal tool image. |
| cargo audit | Rust toolchain plus `cargo-audit` installed through an approved Rust tool workflow. |

## Local Verification Commands

Run these commands from the repository root after installation:

```powershell
gitleaks version
semgrep --version
python -m semgrep --version
npm --version
pip-audit --version
cargo audit --version
python tools/security/check_security_tools.py
```

`semgrep --version` and `python -m semgrep --version` are alternatives. One successful Semgrep invocation is enough for local detection.

## When Each Tool Becomes Mandatory

| Tool | Mandatory before |
|---|---|
| gitleaks | External dependency runtime integration, vendoring, copied code, venue API integration, or live/API execution. |
| semgrep | Copied external code, runtime integration, venue API clients, or live/API execution. |
| npm audit | TypeScript client integration, dashboard/runtime dependency installation, or Node runtime work. |
| pip-audit | Python client integration, Python runtime dependency installation, or Python service work. |
| cargo audit | Any Rust runtime component, if Rust is selected for runtime scope. |

## What To Do If A Tool Is Unavailable

- Do not install global or system tools without explicit user approval.
- Record the unavailable tool in `docs/security_tooling_status.md`.
- Keep or update the related item in `docs/deferred_items_log.md`.
- Treat unavailable tooling as a deferred gate, not as a passing scan.
- Do not begin runtime dependency integration, vendoring, copied external code, venue API integration, or live/API execution until the relevant gate is satisfied or an approved equivalent is documented in repo truth.

## Why Passing Scans Does Not Authorize Live Trading

Security scans only reduce dependency, static-analysis, and credential-leak risk. They do not approve trading behavior, runtime execution, credentials, order placement, risk controls, or live mode. Live trading remains disabled until a future approved work package updates `docs/live_trading_authorization.md` with explicit human approval and tested safety controls.
