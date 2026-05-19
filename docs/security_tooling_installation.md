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

## Project-Local Installation Path

WP5 approves a project-local security tooling environment for security tools only:

```powershell
python tools/security/setup_project_security_tools.py
python tools/security/verify_project_security_tools.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
```

The setup script creates or reuses `.venv-security/` and installs only `semgrep` and `pip-audit` there. This is not runtime dependency integration and does not approve venue clients, copied external code, or live/API execution.

Do not commit `.venv-security/`, `tools/.bin/`, scan output, binaries, or local reports.

## Project-Local Gitleaks Path (WP7)

WP7 adds a project-local gitleaks acquisition path. The script downloads the pinned release binary into `tools/.bin/` (ignored, never committed). No global or system installation is performed.

```powershell
python tools/security/setup_project_gitleaks.py
python tools/security/verify_project_gitleaks.py
```

The setup script:
1. Verifies `tools/.bin/` is git-ignored before writing anything there.
2. Verifies no files under `tools/.bin/` are tracked or staged.
3. Downloads the pinned gitleaks binary from the official GitHub release URL.
4. Verifies the SHA256 checksum against the official release checksums file.
5. Verifies the binary runs `gitleaks version` successfully.

After successful setup, run the scan:

```powershell
python tools/security/run_available_security_checks.py
```

The scan command used is `gitleaks git --redact` (v8+ git-history scan syntax).

**If gitleaks cannot be acquired safely** (network failure, checksum mismatch, etc.):
- The script exits non-zero and documents the blocker.
- WP3-D001 remains DEFERRED.
- Do not force a global/system installation.
- Document the blocker in `docs/deferred_items_log.md`.

**Do not commit**:
- `tools/.bin/gitleaks` or `tools/.bin/gitleaks.exe`
- Scan output files
- Any binary under `tools/.bin/`

The verify script (`tools/security/verify_project_gitleaks.py`) reports availability without installing or scanning anything. It always exits 0.

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
