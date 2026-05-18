# Security Tooling Status

## Purpose

This document records WP5 local security-tool availability and scan results. It is status evidence only; it does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## WP5 Status Summary

WP5 added a project-local security-tooling pathway under ignored `.venv-security/` and installed only `semgrep` and `pip-audit` there. No global or system package installation was performed. No runtime trading dependencies were added.

## Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | NOT_AVAILABLE | NOT_AVAILABLE | `gitleaks version` or `tools/.bin/gitleaks version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D001 remains DEFERRED | No PATH or project-local binary detected during WP5. |
| semgrep | AVAILABLE | PROJECT_LOCAL_VENV | `.venv-security/Scripts/semgrep.exe --version` | `.venv-security/Scripts/semgrep.exe scan --config auto .` | PASS | WP3-D002 marked READY_FOR_WP | Version check returned `1.163.0`; scan passed. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists; npm was not installed. |
| pip-audit | AVAILABLE | PROJECT_LOCAL_VENV | `.venv-security/Scripts/pip-audit.exe --version` | `.venv-security/Scripts/pip-audit.exe --progress-spinner off` | PASS | WP3-D004 marked READY_FOR_WP | Version check returned `pip-audit 2.10.0`; no known vulnerabilities found. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock` exists; Rust/cargo-audit were not installed. |

## Commands Attempted

```powershell
python tools/security/check_security_tools.py
python tools/security/verify_project_security_tools.py
python tools/security/setup_project_security_tools.py
python tools/security/verify_project_security_tools.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
python -m pytest
```

## Results

- `gitleaks`: skipped because no PATH or project-local binary was available.
- `semgrep`: available from `.venv-security/`; scan passed.
- `npm audit`: skipped because no `package.json` exists.
- `pip-audit`: available from `.venv-security/`; scan passed with no known vulnerabilities found.
- `cargo audit`: skipped because no `Cargo.lock` exists.

## Limitations

- This status reflects the local WP5 environment only.
- Unavailable tools are not passing results.
- Not-applicable ecosystem scans do not resolve deferred items for future runtime work.
- Passing scans still do not authorize live trading.

## Deferred Item Impact

WP3-D002 and WP3-D004 are `READY_FOR_WP` because project-local tools are available and scans passed. WP3-D001, WP3-D003, and WP3-D005 remain `DEFERRED`.

## Next Required Action

Before runtime dependency integration, copied external code, venue API integration, or live/API execution, provide gitleaks or an approved equivalent, rerun the wrappers in `tools/security/`, update this status document, and update `docs/deferred_items_log.md`.
