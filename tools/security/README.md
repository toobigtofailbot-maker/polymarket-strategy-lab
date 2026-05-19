# Security Tools

This directory contains local wrappers for security-tool detection, setup, and safe scan execution.

## Utilities

- `check_security_tools.py` — Detects local availability of required security tools and relevant ecosystem files.
- `run_available_security_checks.py` — Runs only checks whose tools and project files are already available.
- `setup_project_security_tools.py` — Creates `.venv-security/` and installs only approved security tools (semgrep, pip-audit) into that project-local environment.
- `verify_project_security_tools.py` — Reports availability from PATH, `.venv-security/`, and `tools/.bin/` without installing tools or running scans.
- `setup_project_gitleaks.py` — Downloads the pinned gitleaks binary into ignored `tools/.bin/` with checksum verification. Does not install globally. Verifies ignore protection before writing.
- `verify_project_gitleaks.py` — Reports gitleaks availability from PATH and `tools/.bin/` without installing anything or running scans. Always exits 0.

## Gitleaks Scan Behavior

The scan command used by `run_available_security_checks.py` is:

```
tools/.bin/gitleaks.exe git --redact
```

(`gitleaks git` is the v8+ git-history scan. `--redact` strips secret values from output.)

Run `setup_project_gitleaks.py` before `run_available_security_checks.py` if the binary is absent. The setup script will not write anything unless `tools/.bin/` is git-ignored.

After a clean checkout, `tools/.bin/gitleaks.exe` is absent because binaries are not committed. Rerun `setup_project_gitleaks.py` to restore it.

## Generated Artifact Guard

Run the generated artifact guard before and after security tool setup:

```powershell
python tools/git/preflight_generated_artifact_guard.py
python tools/security/setup_project_gitleaks.py
python tools/git/preflight_generated_artifact_guard.py
```

## Rules

- No script performs global, system, user, winget, choco, brew, apt, npm, cargo, runtime, or trading dependency installation.
- Detection, verification, and scan scripts do not install packages.
- The security-tools setup script may install only approved security tools into `.venv-security/`.
- The gitleaks setup script may download only the pinned gitleaks binary into `tools/.bin/`.
- `.venv-security/` is generated, ignored, and must never be committed.
- `tools/.bin/` is ignored and must never be committed. Binaries placed there are not tracked.
- The setup scripts refuse to write to protected paths unless ignore protection is active and no tracked/staged files exist there.
- No script alters system state.
- No script adds runtime dependencies.
- No script contacts trading or venue APIs.
- No script reads credential material.
- These scripts do not install packages.
- These scripts do not authorize live trading.
- Missing tools are reported as skipped or unavailable, not as passing scans.
- No committed binaries.

## Generated Artifact Recovery

If GitHub Desktop or `git status` shows `.venv-security/` files, do not commit them and do not stage them.

Run:

```powershell
git ls-files -- .venv-security tools/.bin tools/security/.cache security-scan-output
git diff --cached --name-only -- .venv-security tools/.bin tools/security/.cache security-scan-output
python tools/git/cleanup_generated_artifacts.py --apply
python tools/git/preflight_generated_artifact_guard.py
```

If tracked or staged generated files are reported, stop and request explicit remediation before deleting anything.
