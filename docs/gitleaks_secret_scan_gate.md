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
true` mechanism and removes every allowlist: `.gitleaks.toml` contains only `[extend]`. All
classified historical findings, synthetic test fixtures and prose false positives including the
WP14-D002 deferred-log line (`70136bc4ad74eae69a0c0ee960a12a0f852e4df5:docs/deferred_items_log.md:generic-api-key:49`), are listed individually by exact fingerprint
(`commit:path:rule:line`) in `.gitleaksignore`; no path, directory, rule, regex, stopword or
wildcard exclusion exists. A secret later added to any line, including the WP14-D002 row, is a new
commit and therefore a new finding. No broad suppressions added. The fingerprints contain commit SHAs, so they apply to `gitleaks git` (the
runner's mode) only: a `gitleaks dir` working-tree scan still reports the fixtures that remain in
the tree, and any history rewrite would invalidate the fingerprints.
`tests/test_gitleaks_secret_scan_gate.py` enforces the configuration shape with a negative matrix
and, when a gitleaks binary is available, proves a runtime-assembled synthetic token is detected,
clean input passes and the defective WP15 shape detects nothing.

## S10-CI-SEC-04 Hosted Enforcement in ci-final-gate

Hosted CI now runs real secret detection inside the existing required `ci-final-gate` job (ruleset
`main-protection` requires that check), before its final plan verification:

1. The checkout must be the exact pull-request head with full, non-shallow history, and the base
   commit must be an ancestor of the head.
2. The official gitleaks 8.27.2 release asset `gitleaks_8.27.2_linux_x64.tar.gz` and its checksum
   manifest are downloaded over HTTPS (fail on any HTTP error). The manifest must match its pinned
   SHA-256 `37c3277907a277499370e980d13d8497215d49c69809668dc8841dbabd574dc0`; it must contain exactly
   one entry for the asset, equal to the pinned archive SHA-256
   `141c3b2dede46d8b3a53b47116da756bd223decc0374797559a6b50ecba5590c`; and the archive is verified
   with `sha256sum --check --strict` before only the `gitleaks` binary is extracted into
   `$RUNNER_TEMP`. The binary must report version 8.27.2. The best-effort
   `tools/security/setup_project_gitleaks.py` is not used for hosted proof.
3. `gitleaks git --redact --exit-code 1 --log-opts="--all"` scans the full fetched history with the
   committed `.gitleaks.toml` (embedded default rules, no allowlist) and the 20 exact fingerprints in
   `.gitleaksignore`. The log states the actual denominator; `refs/pull/*` are not fetched by the
   checkout and are not covered.
4. The five binary-backed cases in `tests/test_gitleaks_secret_scan_gate.py` run with the verified
   binary and the JUnit report must show 5 tests, 0 skipped, 0 failures and 0 errors.

Any download, checksum, version, scan, finding, skip or test failure fails the job, so
`CI_FINAL_GATE_PASS` is printed only after all four succeed. No broad suppressions added.

Limits: the pinned hashes prove consistency with the official release as published (the asset
digest, the manifest and a direct computation agreed when pinned); they are not an independent
maintainer signature. A pull request can modify `.github/workflows/ci.yml` itself, so this gate is
enforced in unchanged workflow runs, with workflow changes subject to human review and the ruleset;
it is not an independent, unbypassable policy control. Compatibility legs still skip the
binary-backed cases; the final gate is the hosted detection evidence.

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
