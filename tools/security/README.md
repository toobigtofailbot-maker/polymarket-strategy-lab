# Security Tools

This directory contains local wrappers for security-tool detection and safe scan execution.

## Utilities

- `check_security_tools.py` detects local availability of required security tools and relevant ecosystem files.
- `run_available_security_checks.py` runs only checks whose tools and project files are already available.
- `setup_project_security_tools.py` creates `.venv-security/` and installs only approved security tools into that project-local environment.
- `verify_project_security_tools.py` reports availability from PATH, `.venv-security/`, and `tools/.bin/` without installing tools or running scans.

## Rules

- Detection, verification, and scan scripts do not install packages.
- The setup script may install only approved security tools into `.venv-security/`.
- `.venv-security/` is generated, ignored, and must never be committed.
- The setup script refuses to create or reuse `.venv-security/` unless ignore protection is active and the path is not tracked or staged.
- No script performs global, system, user, npm, cargo, runtime, or trading dependency installation.
- These scripts do not alter system state.
- These scripts do not add runtime dependencies.
- These scripts do not contact trading or venue APIs.
- These scripts do not read credential material.
- These scripts do not authorize live trading.
- Missing tools are reported as skipped or unavailable, not as passing scans.

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
