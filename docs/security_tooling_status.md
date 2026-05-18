# Security Tooling Status

## Purpose

This document records WP4 local security-tool availability and scan results. It is status evidence only; it does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## WP4 Status Summary

WP4 created local detection and scan wrapper scripts under `tools/security/`. Local detection was attempted on this machine. No global or system package installation was performed.

## Tool Status Table

| Tool | Availability | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|
| gitleaks | NOT_AVAILABLE | `gitleaks version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D001 remains DEFERRED | Tool was not detected on PATH during WP4. |
| semgrep | NOT_AVAILABLE | `semgrep --version` or `python -m semgrep --version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D002 remains DEFERRED | CLI and Python module invocation were not detected during WP4. |
| npm audit | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists, but npm audit is not resolved for future Node/TypeScript work. |
| pip-audit | NOT_AVAILABLE | `pip-audit --version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D004 remains DEFERRED | Python project metadata exists, but no runtime dependencies are installed by WP4. |
| cargo audit | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.toml` or `Cargo.lock` exists and Rust is not selected for runtime scope. |

## Commands Attempted

```powershell
gitleaks version
semgrep --version
python -m semgrep --version
npm --version
pip-audit --version
cargo audit --version
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
python -m pytest
```

## Results

- `gitleaks`: skipped because the tool is not available locally.
- `semgrep`: skipped because the CLI and Python module invocation are not available locally.
- `npm audit`: skipped because no `package.json` exists.
- `pip-audit`: skipped because the tool is not available locally.
- `cargo audit`: skipped because no Rust manifest or lockfile exists.
- WP4 added repeatable scripts and tests so future work packages cannot ignore missing relevant gates.

## Limitations

- This status reflects the local WP4 environment only.
- Unavailable tools are not passing results.
- Not-applicable ecosystem scans do not resolve deferred items for future runtime work.
- Passing future scans still does not authorize live trading.

## Deferred Item Impact

WP3-D001 through WP3-D005 remain `DEFERRED` unless a later approved work package installs or verifies the relevant tool or documents an approved equivalent. WP3-D007 remains `DEFERRED` because official CLOB client dependency security review has not started.

## Next Required Action

Before runtime dependency integration, copied external code, venue API integration, or live/API execution, install or otherwise provide approved equivalents for the relevant tools, rerun the wrappers in `tools/security/`, update this status document, and update `docs/deferred_items_log.md`.
