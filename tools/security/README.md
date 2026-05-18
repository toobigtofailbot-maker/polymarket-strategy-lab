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
- No script performs global, system, user, npm, cargo, runtime, or trading dependency installation.
- These scripts do not alter system state.
- These scripts do not add runtime dependencies.
- These scripts do not contact trading or venue APIs.
- These scripts do not read credential material.
- These scripts do not authorize live trading.
- Missing tools are reported as skipped or unavailable, not as passing scans.
