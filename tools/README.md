# Tools

Repository-local utilities live here.

Tools in this directory have no trading authority. They must not install packages, alter system state, add runtime dependencies, copy external source code, contact venue APIs, read credentials, or enable live trading unless a future approved work package explicitly changes repo truth.

`tools/git/` contains the Remote Main Sync Gate required before future WP branch creation.

`tools/security/` contains security-tool setup, verification, detection, and scan wrappers. Project-local security tooling is allowed only under ignored paths such as `.venv-security/` and `tools/.bin/`.
