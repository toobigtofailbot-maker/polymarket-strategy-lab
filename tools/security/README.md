# Security Tools

This directory contains local wrappers for security-tool detection and safe scan execution.

## Utilities

- `check_security_tools.py` detects local availability of required security tools and relevant ecosystem files.
- `run_available_security_checks.py` runs only checks whose tools and project files are already available.

## Rules

- These scripts do not install packages.
- These scripts do not alter system state.
- These scripts do not add runtime dependencies.
- These scripts do not contact trading or venue APIs.
- These scripts do not read credential material.
- These scripts do not authorize live trading.
- Missing tools are reported as skipped or unavailable, not as passing scans.
