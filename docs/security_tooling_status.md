# Security Tooling Status

## Purpose

This document records local security-tool availability and scan results through WP7. It is status evidence only; it does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## WP7 Status Summary

WP7 added a project-local gitleaks acquisition path under ignored `tools/.bin/` and downloaded gitleaks v8.27.2 with checksum verification. The `gitleaks git --redact` scan ran and passed with no findings. WP3-D001 is updated from DEFERRED to READY_FOR_WP. No global or system installation was performed. No runtime trading dependencies were added.

Semgrep and pip-audit are NOT currently available locally because `.venv-security/` was removed during WP6 cleanup. Rerun `tools/security/setup_project_security_tools.py` to restore them before any semgrep or pip-audit work.

## WP7 Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | AVAILABLE | PROJECT_LOCAL_BIN | `tools/.bin/gitleaks.exe version` | `tools/.bin/gitleaks.exe git --redact` | PASS | WP3-D001 updated to READY_FOR_WP | Version 8.27.2; checksum verified; scan passed with no findings. |
| semgrep | NOT_AVAILABLE | NOT_AVAILABLE | `.venv-security/Scripts/semgrep.exe --version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D002 remains READY_FOR_WP | `.venv-security/` absent; rerun setup_project_security_tools.py to restore. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists; npm was not installed. |
| pip-audit | NOT_AVAILABLE | NOT_AVAILABLE | `.venv-security/Scripts/pip-audit.exe --version` | Not run | SKIPPED_NOT_AVAILABLE | WP3-D004 remains READY_FOR_WP | `.venv-security/` absent; rerun setup_project_security_tools.py to restore. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock` exists; Rust/cargo-audit were not installed. |

## WP7 Commands Run

```powershell
python tools/security/setup_project_gitleaks.py
python tools/security/verify_project_gitleaks.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
python tools/git/preflight_generated_artifact_guard.py
```

Scan command executed:

```
tools/.bin/gitleaks.exe git --redact
```

## WP7 Results

- `gitleaks`: AVAILABLE from PROJECT_LOCAL_BIN; version 8.27.2; checksum verified; `gitleaks git --redact` scan PASSED with no findings.
- `semgrep`: NOT_AVAILABLE (`.venv-security/` absent after WP6 cleanup).
- `npm audit`: NOT_APPLICABLE (no `package.json`).
- `pip-audit`: NOT_AVAILABLE (`.venv-security/` absent after WP6 cleanup).
- `cargo audit`: NOT_APPLICABLE (no `Cargo.lock`).

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
- WP6 removed the generated local `.venv-security/` directory during allowlisted artifact cleanup, so current local availability may show `semgrep` and `pip-audit` as unavailable until `tools/security/setup_project_security_tools.py` is rerun with ignore protection active.
- Unavailable tools are not passing results.
- Not-applicable ecosystem scans do not resolve deferred items for future runtime work.
- Passing scans still do not authorize live trading.

## WP6 Generated Artifact Cleanup Note

WP6 added `tools/git/cleanup_generated_artifacts.py` and `tools/git/preflight_generated_artifact_guard.py`, then hardened `tools/security/setup_project_security_tools.py` to refuse `.venv-security/` creation unless ignore protection is active and no generated artifact files are tracked or staged.

## Deferred Item Impact

WP3-D001 is `READY_FOR_WP` because gitleaks v8.27.2 was verified from PROJECT_LOCAL_BIN and the scan passed. WP3-D002 and WP3-D004 remain `READY_FOR_WP` (semgrep and pip-audit require `.venv-security/` to be restored). WP3-D003 and WP3-D005 remain `DEFERRED`.

## Next Required Action

Before runtime dependency integration, copied external code, venue API integration, or live/API execution:

1. Rerun `tools/security/setup_project_gitleaks.py` if the binary is absent.
2. Rerun `tools/security/setup_project_security_tools.py` to restore semgrep and pip-audit.
3. Rerun `tools/security/run_available_security_checks.py`.
4. Update this status document and `docs/deferred_items_log.md` with results.
