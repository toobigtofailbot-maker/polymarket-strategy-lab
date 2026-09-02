# Security Tooling Status

## Purpose

This document records local security-tool availability and scan results through WP15. It is status evidence only; it does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## WP167 Status Summary

WP167 is the project's first runtime-dependency package. It moves the Python
support floor to `>=3.12,<3.15` and adds exactly three direct runtime
dependencies: `pyarrow==25.0.1`, `duckdb==1.5.5`, `polars==1.44.1`. Before
implementation the project-local security baseline was rerun. Gitleaks, semgrep,
and pip-audit were all `NOT_AVAILABLE` from project-local paths (`tools/.bin/` and
`.venv-security/` are absent in this worktree), consistent with the historical
baseline. `python -m pip check` passed with no broken requirements after the exact
pins were installed.

A local pip-audit was additionally run by installing `pip-audit` into the active
interpreter and auditing the resolved environment. It reported 14 known
vulnerabilities across 6 packages: `idna`, `pip`, `pydantic-settings`, `requests`,
`urllib3`, and `uv`. **None of the three WP167 runtime dependencies
(`pyarrow`, `duckdb`, `polars`) are implicated.** Every flagged package is a
pre-existing package in the shared global interpreter used by unrelated local
projects (two of which, `pionex-risk-monitor` and `solana-mirror-engine`, pip-audit
skipped as not-on-PyPI); WP167 neither adds nor declares any of them in
`pyproject.toml`. The authoritative WP167 dependency audit therefore runs in the
hosted CI `dependency-audit` job on ubuntu-24.04 / Python 3.12, whose isolated
environment installs only the exact WP167 pins plus pytest and pip-audit, so its
`pip-audit` sees WP167's actual dependency closure rather than the polluted local
global environment.

### WP167 Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | NOT_AVAILABLE | NOT_AVAILABLE | `tools/.bin/gitleaks.exe version` | `gitleaks detect --source . --redact` | SKIPPED_NOT_AVAILABLE | WP3-D001 remains READY_FOR_WP | Project-local `tools/.bin/` absent in this worktree; rerun `tools/security/setup_project_gitleaks.py` to restore. |
| semgrep | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH semgrep | `semgrep scan --config auto .` | SKIPPED_NOT_AVAILABLE | WP3-D002 remains READY_FOR_WP | `.venv-security/` absent; rerun `tools/security/setup_project_security_tools.py` to restore. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json`. |
| pip-audit (project-local) | NOT_AVAILABLE | NOT_AVAILABLE | project-local pip-audit | Not run from project-local path | SKIPPED_NOT_AVAILABLE | WP3-D004 remains READY_FOR_WP | Project-local `.venv-security/` absent. |
| pip-audit (interpreter, local) | AVAILABLE | INTERPRETER_INSTALL | `python -m pip_audit --version` | `python -m pip_audit --progress-spinner off` | 14 VULNS IN UNRELATED GLOBAL PACKAGES; WP167 PINS CLEAN | WP3-D004 remains READY_FOR_WP | Findings are in `idna`/`pip`/`pydantic-settings`/`requests`/`urllib3`/`uv`, none of which WP167 adds; `pyarrow`/`duckdb`/`polars` have no reported vulnerabilities. |
| pip-audit (hosted CI) | NOT_RUN | HOSTED_CI | `python -m pip_audit` | `.github/workflows/ci.yml` dependency-audit job | PASS on hosted CI (isolated closure); exact live run at the current PR head is recorded in the PR body | WP3-D004 remains READY_FOR_WP | Not run in this local environment; the authoritative WP167 audit is the isolated ubuntu-24.04 / Python 3.12 CI job auditing only the WP167 dependency closure, which passed. |
| pip check | AVAILABLE | INTERPRETER | `python -m pip check` | `python -m pip check` | PASS | — | No broken requirements after installing the exact pins. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock`. |

### WP167 Commands Run

```bash
python -m pip install "pyarrow==25.0.1" "duckdb==1.5.5" "polars==1.44.1"
python -m pip check
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
python -m pip install pip-audit
python -m pip_audit --progress-spinner off
```

### WP167 Results

- `pip check`: PASS (no broken requirements).
- `pyarrow==25.0.1`, `duckdb==1.5.5`, `polars==1.44.1`: no known vulnerabilities in the local pip-audit run.
- Local pip-audit exit 1 is attributable entirely to unrelated pre-existing global-environment packages, not to any WP167 dependency; the hosted CI dependency-audit job is the authoritative WP167 audit surface.
- gitleaks and semgrep: SKIPPED_NOT_AVAILABLE (project-local tooling absent); unavailable tools are not passing results.
- DuckDB note: local DuckDB execution is observational. Windows Smart App Control (an OS security policy, never disabled or weakened by WP167) may block the pinned native module; when it does, local DuckDB execution is `BLOCKED_BY_WINDOWS_SMART_APP_CONTROL` and DuckDB-dependent tests skip locally with an explicit reason, and when the OS reputation check allows the binary the pinned module loads and those tests run locally. This local state is environmental and can change over time; strict hosted Windows/Linux CI is the authoritative cross-platform DuckDB proof either way. The exact final observed local status is recorded in the PR body.

## WP15 Status Summary

WP15 reran the project-local security baseline before implementation. Gitleaks v8.27.2 was available from ignored `tools/.bin/`. The first scan reported a documentation false positive in `docs/deferred_items_log.md` for the exact phrase "credential/key/security boundary"; WP15 added a narrow `.gitleaks.toml` allowlist scoped to that file and exact phrase, then reran the scan successfully. Semgrep and pip-audit were unavailable because `.venv-security/` is absent after generated artifact cleanup. WP15 adds no runtime dependency, no external repo code, no copied source, no venue API client in runtime paths, and no live/API execution path.

No pip-audit run was performed against `.venv-official-client/` because the official-client sandbox package was not installed during the required default command path.

## WP15 Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | AVAILABLE | PROJECT_LOCAL_BIN | `tools/.bin/gitleaks.exe version` | `tools/.bin/gitleaks.exe git --redact` | PASS | WP3-D001 remains READY_FOR_WP | Version 8.27.2; scan passed after a narrow documentation false-positive allowlist. |
| semgrep | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH semgrep | Not run | SKIPPED_NOT_AVAILABLE | WP3-D002 remains READY_FOR_WP | `.venv-security/` absent; no runtime dependency added. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists. |
| pip-audit | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH pip-audit | Not run | SKIPPED_NOT_AVAILABLE | WP3-D004 remains READY_FOR_WP | `.venv-security/` absent; no project dependency added; sandbox package not installed in required default path. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock` exists. |

## WP15 Commands Run

```powershell
python tools/security/verify_project_gitleaks.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
tools/.bin/gitleaks.exe git --redact --verbose
python tools/security/run_available_security_checks.py
```

## WP14 Status Summary

WP14 reran the project-local security baseline before implementation. Gitleaks v8.27.2 was available from ignored `tools/.bin/` and `gitleaks git --redact` passed with no findings. Semgrep and pip-audit were unavailable because `.venv-security/` is absent after generated artifact cleanup. WP14 adds no runtime dependency, no external repo code, no copied source, no venue API client, and no live/API execution path, so unavailable semgrep and pip-audit remain documented but do not block this documentation-only work package.

## WP14 Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | AVAILABLE | PROJECT_LOCAL_BIN | `tools/.bin/gitleaks.exe version` | `tools/.bin/gitleaks.exe git --redact` | PASS | WP3-D001 remains READY_FOR_WP | Version 8.27.2; scan passed with no findings. |
| semgrep | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH semgrep | Not run | SKIPPED_NOT_AVAILABLE | WP3-D002 remains READY_FOR_WP | `.venv-security/` absent; no runtime dependency added. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists. |
| pip-audit | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH pip-audit | Not run | SKIPPED_NOT_AVAILABLE | WP3-D004 remains READY_FOR_WP | `.venv-security/` absent; no runtime dependency added. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock` exists. |

## WP14 Commands Run

```powershell
python tools/security/verify_project_gitleaks.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
```

## WP13 Status Summary

WP13 reran the project-local security baseline before implementation. Gitleaks v8.27.2 was available from ignored `tools/.bin/` and `gitleaks git --redact` passed with no findings. Semgrep and pip-audit were unavailable because `.venv-security/` is absent after generated artifact cleanup. WP13 adds no runtime dependency, no external repo code, no copied source, no venue API client, and no live/API execution path, so unavailable semgrep and pip-audit remain documented but do not block this offline-only work package.

## WP13 Tool Status Table

| Tool | Availability | Source | Version command | Scan command attempted | Result | Deferred item impact | Notes |
|---|---|---|---|---|---|---|---|
| gitleaks | AVAILABLE | PROJECT_LOCAL_BIN | `tools/.bin/gitleaks.exe version` | `tools/.bin/gitleaks.exe git --redact` | PASS | WP3-D001 remains READY_FOR_WP | Version 8.27.2; scan passed with no findings. |
| semgrep | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH semgrep | Not run | SKIPPED_NOT_AVAILABLE | WP3-D002 remains READY_FOR_WP | `.venv-security/` absent; no runtime dependency added. |
| npm audit | NOT_APPLICABLE | NOT_APPLICABLE | `npm --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D003 remains DEFERRED | No `package.json` exists. |
| pip-audit | NOT_AVAILABLE | NOT_AVAILABLE | project-local or PATH pip-audit | Not run | SKIPPED_NOT_AVAILABLE | WP3-D004 remains READY_FOR_WP | `.venv-security/` absent; no runtime dependency added. |
| cargo audit | NOT_APPLICABLE | NOT_APPLICABLE | `cargo audit --version` | Not run | SKIPPED_NOT_APPLICABLE | WP3-D005 remains DEFERRED | No `Cargo.lock` exists. |

## WP13 Commands Run

```powershell
python tools/security/verify_project_gitleaks.py
python tools/security/check_security_tools.py
python tools/security/run_available_security_checks.py
```

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
