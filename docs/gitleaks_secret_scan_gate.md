# Gitleaks Secret Scan Gate

## Purpose

This document records the WP7 gitleaks secret-scanning gate: setup strategy, source, version, commands run, scan result, and deferred-item impact. It is status evidence only. It does not authorize runtime dependency integration, copied external code, venue API integration, or live trading.

## Why Gitleaks Is Required

Gitleaks detects committed credentials, API keys, tokens, private keys, mnemonics, and other secret material in git repositories and file trees. It is required before:

- External dependency runtime integration.
- Vendoring or copying external source code into runtime paths.
- Venue API (Polymarket, Kalshi) integration.
- Any live or paper-trading execution path.

This requirement is documented in `docs/security_tooling_requirements.md` and tracked as WP3-D001 in `docs/deferred_items_log.md`.

## WP7 Setup Strategy

WP7 uses a project-local binary acquisition path:

1. `tools/security/setup_project_gitleaks.py` checks ignore protection for `tools/.bin/` before writing anything there.
2. It verifies no files under `tools/.bin/` are tracked or staged.
3. If gitleaks is already available on PATH or in `tools/.bin/`, no download is attempted.
4. If not available, the script downloads the pinned release asset from the official GitHub release URL.
5. It fetches the official checksums file and verifies the SHA256 of the downloaded archive.
6. The binary is extracted into `tools/.bin/` (ignored, never committed).
7. The script verifies the binary runs `gitleaks version` before declaring success.

No global, system, user, winget, choco, brew, apt, npm, cargo, or pip --user installation is performed.

## Gitleaks Source and Version

- **Pinned version**: 8.27.2
- **Release tag**: v8.27.2
- **Source**: GitHub Releases — `https://github.com/gitleaks/gitleaks/releases/download/v8.27.2/`
- **Asset (Windows x64)**: `gitleaks_8.27.2_windows_x64.zip`
- **Checksum file**: `gitleaks_8.27.2_checksums.txt` (fetched from the same release)
- **SHA256 of archive**: `3c6a58efa70e991d7816a8bd87d1db797818017fcb67cbf1861394b404a70a42`
- **Checksum verification**: VERIFIED — SHA256 matched the official release checksums file.
- **Source category**: PROJECT_LOCAL_BIN

## Project-Local Path

| Path | Purpose | Ignored? | Committed? |
|---|---|---|---|
| `tools/.bin/` | Holds ignored project-local security binaries | Yes (`.gitignore` line 56) | No |
| `tools/.bin/gitleaks.exe` | Pinned gitleaks binary (Windows) | Yes (directory is ignored) | No |
| `security-scan-output/` | Optional scan output (not written by default) | Yes (`.gitignore` line 58) | No |

The `.gitignore` rule `tools/.bin/` covers all contents of that directory.

## Commands Run

```
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

## Scan Result

### WP14 Rerun

| Item | Value |
|---|---|
| Tool | gitleaks |
| Version | 8.27.2 |
| Source | PROJECT_LOCAL_BIN |
| Command | `tools/.bin/gitleaks.exe git --redact` |
| Result | PASS |
| Findings | None |
| False positives | None |
| Broad suppressions added | No |

### WP7 Initial Gate

| Item | Value |
|---|---|
| Tool | gitleaks |
| Version | 8.27.2 |
| Source | PROJECT_LOCAL_BIN |
| Command | `tools/.bin/gitleaks.exe git --redact` |
| Result | PASS |
| Findings | None |
| False positives | None |
| Broad suppressions added | No |

The scan completed with exit code 0 and reported no findings.

## Findings

WP15 note: a later gitleaks git scan reported a documentation false positive in `docs/deferred_items_log.md` for the exact phrase "credential/key/security boundary". WP15 added a narrow `.gitleaks.toml` allowlist scoped to that file and exact phrase. The scan was rerun and reported no leaks found.

## False-Positive Handling

WP15 observed one documentation false positive and added a minimal `.gitleaks.toml` allowlist rule scoped to one file and one exact phrase. No broad suppressions added.

## S10-CI-SEC-02 Default-Rule Correction

The WP15 `.gitleaks.toml` contained only a legacy `[allowlist]` table and no `[extend]` table.
A project configuration without `[extend] useDefault = true` defines zero rules, and gitleaks
auto-loads `.gitleaks.toml` from the scanned source root, so every `gitleaks git --redact` run by
`tools/security/run_available_security_checks.py` from WP15 onward passed without executing any
detection rule. Legacy allowlist conditions also match independently, so the WP15 `paths` entry
excluded the whole of `docs/deferred_items_log.md` rather than one phrase in it. Earlier
"no leaks found" results from WP15 onward are therefore not detection evidence.

S10-CI-SEC-02 restores the embedded default rule set through the official `[extend] useDefault =
true` mechanism, removes the whole-file path exclusion and keeps only the exact WP14-D002 prose
regex, bound to its `| WP14-D002 |` table cell (line target). Historical synthetic test fixtures
and prose false positives are listed individually by exact fingerprint (`commit:path:rule:line`)
in `.gitleaksignore`; no path, directory, rule, stopword or wildcard exclusion exists. No broad
suppressions added. The fingerprints contain commit SHAs, so they apply to `gitleaks git` (the
runner's mode) only: a `gitleaks dir` working-tree scan still reports the fixtures that remain in
the tree, and any history rewrite would invalidate the fingerprints.
`tests/test_gitleaks_secret_scan_gate.py` enforces the configuration shape with a negative matrix
and, when a gitleaks binary is available, proves a runtime-assembled synthetic token is detected,
clean input passes and the defective WP15 shape detects nothing.

## Deferred Item Impact

- **WP3-D001** (`gitleaks`): Updated from DEFERRED to **READY_FOR_WP**.
  - Gitleaks version 8.27.2 was verified from PROJECT_LOCAL_BIN.
  - SHA256 checksum verified against the official release checksums file.
  - `gitleaks git --redact` scan passed with no findings.
  - Status is READY_FOR_WP (not RESOLVED) because the scan must be rerun before any relevant future runtime/dependency/API/live work.

## Remaining Blockers

- Gitleaks must be rerun before runtime dependency integration, copied external code, venue API integration, or live/API execution.
- If `tools/.bin/gitleaks.exe` is absent (e.g., after a clean checkout), rerun `tools/security/setup_project_gitleaks.py`.
- Semgrep and pip-audit are NOT available locally on this branch (`.venv-security/` was removed during WP6 cleanup). Rerun `tools/security/setup_project_security_tools.py` to restore them.

## Safety Statement

- No global or system installation was performed.
- No credentials, API keys, tokens, private keys, mnemonics, or wallet keys were added.
- No trading logic, live-trading paths, or venue API integration was added.
- The gitleaks binary is ignored and not committed.
- No scan output files containing sensitive detail were committed.
- Generated artifact guard passed before and after setup.

## Next Required Action

Before runtime dependency integration, copied external source code, venue API integration, or live/API execution:

1. Rerun `tools/security/setup_project_gitleaks.py` (if binary is absent) or `tools/security/verify_project_gitleaks.py` (to confirm availability).
2. Rerun `tools/security/run_available_security_checks.py`.
3. Update `docs/security_tooling_status.md` with the new scan result.
4. Update `docs/deferred_items_log.md` if the scan changes status.
5. Restore semgrep and pip-audit via `tools/security/setup_project_security_tools.py` before copied-code or dependency work.

## Generated Artifact Guard Result

The generated artifact guard (`tools/git/preflight_generated_artifact_guard.py`) passed:
- Before setup: PASSED (no tracked or staged generated artifacts).
- After setup: PASSED (gitleaks binary is ignored and not tracked).
- `tools/.bin/gitleaks.exe` is confirmed not tracked by git.
