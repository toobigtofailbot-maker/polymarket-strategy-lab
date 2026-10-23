# Security Tooling Status

## Purpose

This document records local security-tool availability and scan results through WP15. It is status evidence only; it does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## S10-NDFD-GRIB-01 Optional NDFD GRIB2 Decoder Security Posture

S10-NDFD-GRIB-01 adds one optional extra `ndfd-grib` with the exact ECMWF ecCodes family
(`eccodes==2.48.0`, Apache-2.0; `eccodeslib==2.48.0.26` on non-Windows, which pulls the binary
`eckitlib==2.1.1.26`). The family is installed from binary wheels only; no ecCodes source is built,
vendored or copied, and no base pin, lock file or existing CI job changes. The authoritative audit of
the resolved base-plus-`ndfd-grib` closure is the hosted `ndfd-grib-dependency-audit` job
(ubuntu-24.04 / Python 3.12, `pip check` plus `pip-audit`); the existing `dependency-audit` job is
unchanged. Tests decode only the committed official NDFD fixture and make zero external requests; no
secret, credential, product API, schedule or trading path is involved.

| Tool | Availability | Result | S10-NDFD-GRIB-01 boundary |
|---|---|---|---|
| pip-audit (hosted `ndfd-grib-dependency-audit`) | HOSTED_CI | See exact-head PR checks | Resolved base + `ndfd-grib` closure on ubuntu-24.04 / Python 3.12 |
| pip-audit (local Docker `python:3.12` replica) | LOCAL_CONTAINER | See S10-NDFD-GRIB-01 PR body | Pre-push replica of the same closure; non-authoritative |
| pip check | INTERPRETER / HOSTED_CI | See exact-head PR checks | Base closure plus the extra coexist on both decoder targets |
| gitleaks / Semgrep (project-local) | See S10-NDFD-GRIB-01 PR body | Reported exactly as run; an unavailable tool is UNAVAILABLE, never PASS | Worktree scan of the 19-path change |
| npm audit / cargo audit | NOT_APPLICABLE | SKIPPED_NOT_APPLICABLE | No Node or Rust dependency change |

## WP175 Restricted Live Canary Security Posture

WP175 changes no dependency, lock, workflow, or generated artifact. The Gate-C
module consumes only the private WP174B Gate-B session handle; no secret,
signature, raw SDK response, raw exception, IP, country, region, or local
artifact path is persisted or emitted. `GATE_C_CREATE_STARTED` is durable
before the single `post_order` transmit and ambiguous outcomes are never
retried. Pytest uses fake clients and synthetic secrets only; real economic
CREATE count and capital at risk remain zero. Gate-C activation is pending a
separate exact-head human decision and the strategy qualification prerequisite
is currently unavailable.

## WP174 Status Summary

WP174 adds the exact released dependency `polymarket-client==0.10.0` and replaces
`websockets==17.1` with the SDK-compatible exact pin `websockets==15.0.1`. The
official SDK is used behind a narrow repo-owned Gate-A-only adapter; no external
source is copied or vendored. Project-local gitleaks 8.27.2, Semgrep 1.176.1, and
pip-audit 2.10.1 all pass on the implementation worktree. `python -m pip check`
and exact-version/public-import assertions pass. Real secret loading and real SDK
mutation remain constructor-locked behind the separately required Gate B; live
capital remains behind Gate C and WP175.

| Tool | Availability | Result | WP174 boundary |
|---|---|---|---|
| gitleaks 8.27.2 | PROJECT_LOCAL_BIN | PASS | No secret finding; only fake/nonfunctional public fixture identity is used |
| Semgrep 1.176.1 | PROJECT_LOCAL_VENV | PASS | Gate-A source and tests scanned; no finding |
| pip-audit 2.10.1 | PROJECT_LOCAL_VENV | PASS | No known vulnerability in the resolved project environment |
| pip check | INTERPRETER | PASS | Exact SDK/WebSocket pins coexist with the project dependency closure |
| npm audit | NOT_APPLICABLE | SKIPPED_NOT_APPLICABLE | No root package.json dependency change |
| cargo audit | NOT_APPLICABLE | SKIPPED_NOT_APPLICABLE | No Cargo.lock |

## WP168 Status Summary

WP168 adds exactly one further direct runtime dependency, `nautilus_trader==1.231.0`
(base install only — no `polymarket` extra `py-clob-client-v2`, no Redis, no network),
on top of the WP167 pins, keeping the Python floor `>=3.12,<3.15`. NautilusTrader is
installed from upstream and is **not vendored or modified**; its upstream LGPL-3.0
notices are preserved and its live/authenticated surface is not used. Gitleaks, semgrep,
and pip-audit remain `NOT_AVAILABLE` from project-local paths in this worktree, consistent
with the historical baseline; they are never claimed to have run when they did not.
`python -m pip check` passes with no broken requirements after the exact pins (WP167 pins
plus `nautilus_trader==1.231.0`) are installed together. As with WP167, the authoritative
WP168 dependency audit runs in the hosted CI `dependency-audit` job on ubuntu-24.04 /
Python 3.12, whose isolated environment installs only the exact pins plus pytest and
pip-audit, so its `pip-audit` sees WP168's actual dependency closure rather than the
polluted local global interpreter. WP168 adds no credentials, no product/runtime network,
and no copied external code.

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
| pip-audit (hosted CI) | AVAILABLE | HOSTED_CI | `python -m pip_audit` | `.github/workflows/ci.yml` dependency-audit job | PASS on the exact final validated hosted run (isolated WP167 closure) | WP3-D004 remains READY_FOR_WP | Available and run in hosted CI only, not in this local environment; the authoritative WP167 audit is the isolated ubuntu-24.04 / Python 3.12 CI job auditing only the WP167 dependency closure. The exact live run at the current PR head is recorded in the PR body. |
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

## WP169 Public Market Truth Realtime Data Plane Security Posture

WP169 adds exactly one direct runtime dependency, `websockets==17.1` (BSD-3-Clause; install-not-vendor), for the public Market WebSocket data plane. The authoritative dependency audit runs in the hosted `dependency-audit` job in `.github/workflows/ci.yml`, which installs only the exact pins (`pyarrow==25.0.1`, `duckdb==1.5.5`, `polars==1.44.1`, `nautilus_trader==1.231.0`, `websockets==17.1`) plus pytest and pip-audit, so `pip-audit` sees WP169's actual application dependency closure rather than the polluted local environment. Project-local gitleaks and Semgrep must be AVAILABLE and scan the final source with no material finding; any material finding is a HARD STOP. Local pip-audit availability is recorded but is not misrepresented as the application dependency-closure audit; the exact final hosted result is recorded in the PR body.

WP169 introduces credential-like input handling that fails closed: secret-bearing RPC URLs are impossible (only the enum provider `drpc` maps to the committed public no-query URL), no authenticated header or credential is read, and all diagnostic surfaces are recursively no-echo scanned so URLs, headers, paths, response bodies, and raw invalid inputs never leak.

## WP174B Gate-B Production Credential Security Posture

WP174B adds no dependency; the exact installed pins (`polymarket-client==0.10.0`, `websockets==15.0.1`) are unchanged, so the hosted `dependency-audit` job and `pip-audit` closure are unaffected. Project-local gitleaks and Semgrep must be AVAILABLE and scan the final source (including `src/execution_gateway/gate_b.py` and `gate_b_operator.py`) with no material finding; any material finding is a HARD STOP.

WP174B handles a real signer private key, so its security boundary is fail-closed and no-echo by construction: the key is accepted only through an interactive `getpass` no-echo prompt (never argv, a file, a pipe, or the environment), held in an opaque non-serializable in-memory lease whose value is never exposed through `repr`/`str`/serialization and is cleared on close (physical memory zeroization is never claimed). L2 credentials are derived in memory and never persisted. The raw SDK client, credentials, private key, API key, secret, and passphrase are never exposed as public attributes, committed, logged, journaled, emitted to the cockpit, or placed in exceptions or PR evidence; raw SDK exceptions are replaced by a closed sanitized error vocabulary. Adversarial secret-sentinel tests prove recursive no-echo across every output surface. No real secret is used by pytest, CI, security scanners, or reviewers; the only real-secret use is the operator's local no-echo empty-wallet smoke, whose sanitized receipt (content-addressed public fields only) is the sole consumed evidence and is never committed. If any scanner or log ever captured a real secret, it is a protected incident requiring key rotation, and the secret is never written into the incident record.


## Historical blocked checkpoint (superseded by amended S10-HERMES-SEC-PROFILE-01)

The independent certificate and exact prompt/spec passed native pre-implementation gates on the frozen PR #250 base `f2b8916fe2bd377b0790278f4be5dad85568d367`. Karl requested execution of the certified WP on 2026-10-23. The sixteen-file draft implementation is incomplete and NOT_MERGE_READY; no full-suite, final independent review or acceptance CI PASS is claimed.

The shared profile guard rejected the earlier local shadow: it had **83 distributions**, while the certified Windows profile binds **68**. The 15 extras include pip, edge-tts, boto3/botocore and their dependencies. Creation timestamps coincide with the earlier predraft native probe. The earlier 67-row zero-match audit preceded that probe and does not attest its later changed environment. The original source/lock bytes and all five candidate target versions remained unchanged; installed inventory did not.

A fresh task-owned scratch install from the exact candidate lock restored the approved **68-distribution profile** (`75e3bcea7af741fe599594a744eeb043d494973f79a5291286e60b325a17e4a8`), with `uv sync --locked` and `uv pip check` both exit 0. A socket-denied native reproduction with supported `security.allow_lazy_installs: false` and a child-process audit guard kept that profile identical before/after. It observed **0 explicit-empty tools and 17 control tools**, not the certified 18; `text_to_speech` was absent. No production installation or account/provider operation occurred.

The smallest proposed correction is independent review of a narrowly amended, recertified prompt/spec: explicitly disable lazy installation in every sterile child home, prevent installer subprocess escape, compare inventory before/after probing, and freeze the genuinely observed sealed control toolset instead of asserting the historical 18. Do not add unreviewed optional dependencies or relax identity validation to preserve a count. The current certificate/prompt/spec bytes remain unchanged; no amendment is implemented under them. Linux evidence remains separately gated and unobserved.

D005 remains OPEN. Credentials/OAuth, host promotion, model/account endpoints, capital/orders and merge remain unauthorized. LIVE TRADING STATUS: DISABLED. USD 0; orders 0.


A second immutable-artifact blocker was observed before committing: repository `* text=auto` normalizes the supplied CRLF JSON. Certified working spec SHA256 `318b958031c69b6792336761f822b24534f61d9ae939f00e2a9275a33677917f` becomes staged LF SHA256 `13a37ece07fbd9f8141a6cce9ca404bf33c4ec44749ef272a1f1146b990d5ff1`; policy `df4bb5bdf20249614e1887a64c9d6d71e03834668be67ae765e837ec2af41ac7` becomes `eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680`. Prompt and certificate bytes do not change. Staging was undone; no normalized artifact was committed, and no Git filter/plumbing or seventeenth .gitattributes edit was used. Reissue the amended prompt/spec/policy with LF raw bytes and an independent certificate covering those exact bytes. No PR, commit, push, full-suite or hosted acceptance run was performed after this hard stop; the implementation remains an uncommitted local checkpoint.


## S10-HERMES-SEC-PROFILE-01 amended implementation (2026-10-23)

Karl explicitly authorized resuming the same sixteen-file uncommitted checkpoint.
The newly independent Side21 certificate, prompt and spec pass the native guard and
IMPLEMENTATION_READY gate. Current normative policy SHA256 is
`eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680`.
The previous certificate/hash and 18-tool criteria in the historical checkpoint
above are superseded; its 83-package drift and earlier audit remain historical facts.

The shared verifier reads the exact pin-owned interpreter's isolated metadata,
requires the complete approved inventory and immutable dependency inputs, and
rechecks after native children. All sterile configs disable lazy installs and
stripped environments set HERMES_DISABLE_LAZY_INSTALLS=1. Offline probe/fake-wire
and mock OAuth children deny process execution before Hermes imports. Future
separately authorized real OAuth retains its browser opener; no real login runs here.
Windows requires the exact seventeen observed default tools and zero explicit tools.
Linux's 64-distribution policy is a derived equality target, with native tool count
UNOBSERVED; installation, audit and native proof precede separate host promotion.
Owner-controlled immutable source is assumed; race-proof hostile-host attestation
is not claimed.

Mandatory profile digests bind StageBRequest, Real01Request, OAuthPlanRequest,
preflight eligibility, wire reports, origin/provenance records and their canonical
hashes. Legacy missing-profile evidence is ineligible without rewriting history.
ID-token/JWKS parsing uses a single sanitized ID_TOKEN_INVALID path, RS256 and
required claims, fresh options, a 64-KiB token limit, 1-MiB streamed JWKS limit,
at most 100 keys and one matching RSA signature key. Explicit null alg/use rejects;
absent optional members remain supported. PyJWT's historical no-published-fix
advisory caveat remains; bounded regressions do not establish a universal vendor fix.
Four-format Pillow smoke tests do not prove every optional image route safe.

Current Windows candidate: 68 installed distributions, 67 audited requirements
(editable Hermes excluded), dependency consistency exit 0 and post-probe audit exit
0 with zero known vulnerabilities. Full-suite and exact-head CI results remain the
PR's live evidence; no completion or merge readiness is inferred from these checks.
D005 OPEN; OAuth/credentials NOT AUTHORIZED; LIVE TRADING STATUS: DISABLED;
USD 0; orders 0. Production and retained host pin are untouched.


Security scan qualification: Semgrep 1.176.1 scanned all four changed source modules
with p/python and p/security-audit (200 applicable rules, zero scan errors). One
subprocess-injection alert at capture_offline_wire is a FALSE POSITIVE under the
explicit immutable owner-controlled pin assumption: verified pin-owned executable,
constant Python program, list argv with shell disabled, and untrusted scenario/model
bytes confined to stdin. R001 rejects out-of-pin/metacharacter executable paths before
launch; R002 denies subprocess/shell escapes; R003 denies mismatched wire launch.
No scanner exclusion, suppression or security risk acceptance was added. Independent
implementation review remains required. Gitleaks source scan found zero leaks;
whole working-tree scan reports 19 alerts, all on unchanged baseline lines, including
historical negative fixtures. Existing findings are not reported as a clean
whole-repository scan. No new finding line was introduced.


Final local validation: sealed Windows native focused suite25 passed without skips;
R001-R007 each pass as exact separate commands; adjacent95 and architecture51 pass.
After native construction, the matching68-distribution inventory and67-row audit
remain exact, audit exit0 with zero known vulnerabilities. The existing local Linux
image ran the complete repository suite offline with strict DuckDB, no installation:
14028 passed,15 skipped,125 warnings,exit0. Windows broad validation was interrupted
after the same pyarrow._dataset Application Control block reproduced on untouched
main; it is not PASS. The offline Linux repository suite is not Linux Hermes
installation/security-profile/control-count evidence. Actual final-head hosted CI,
posted evidence and independent Side21 review are governed by the live PR body;
merge remains Karl-only after required independent approval.
