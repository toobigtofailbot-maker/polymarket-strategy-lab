# Testing Requirements

- Governance tests must verify required repo-truth files exist.
- No-live-default tests must verify live trading remains disabled unless explicitly authorized.
- Secret placeholder tests must flag real-looking credentials, private keys, mnemonic labels, and committed `.env` files.
- Future unit tests must cover strategy, risk, data, and utility behavior.
- Future integration tests must cover venue clients only after audit and approval.
- Future paper/live mode tests must prove mode separation.
- Future audit tests must validate source-repo audit artifacts and reuse decisions.
- Deferred-items tests must verify `docs/deferred_items_log.md` exists, required statuses are documented, required unavailable security/dependency tools are tracked, and every item row has status, priority, reason, required-before, and resolution condition fields.
- Architecture-boundary tests must verify WP3 architecture docs exist, `src/` contains README-only scaffolding, strategies cannot place orders directly, live trading remains disabled, and security tooling gates are documented before runtime dependency integration.
- Security tooling tests must verify required documentation and scripts exist.
- Security tooling script tests must verify tooling wrappers do not install packages or alter system state.
- Security tooling script tests must verify tooling wrappers do not authorize live trading.
- Remote main sync gate tests must verify the gate script exists, contains fetch, fast-forward pull, clean-worktree, `HEAD` to `origin/main`, previous-WP commit, and previous-WP file checks, and that repo-truth docs require the gate before WP branch creation.
- Security tooling completion tests must verify project-local security setup and verification scripts exist, local security-tool paths are ignored, forbidden global/system/user install commands are absent, and WP5 status docs record actual outcomes.
- Generated artifact guard tests must verify cleanup scripts are allowlist-only and refuse tracked or staged generated files.
- Security setup tests must verify `.venv-security/` ignore protection is checked before environment creation.
- Gitleaks gate tests must verify: `setup_project_gitleaks.py` and `verify_project_gitleaks.py` exist; `docs/gitleaks_secret_scan_gate.md` exists; `.gitignore` protects `tools/.bin/` and `security-scan-output/`; setup script checks ignore protection before writing; setup script contains no forbidden install commands (winget, choco, brew, apt, npm install -g, cargo install, pip install --user); setup script contains no trading/API/secret terms; `verify_project_gitleaks.py` exits 0; `run_available_security_checks.py` detects gitleaks project-local binary; `docs/security_tooling_status.md` references WP7; `docs/deferred_items_log.md` contains WP7 Gitleaks Secret Scan Gate Update.
- WP3-D001 may only be marked READY_FOR_WP in tests if scan evidence exists in the deferred items log or security tooling status.
- Read-only adapter tests (WP8+) must mock network; no automated test may require live network access.
- Network smoke tests must require explicit `--allow-network` opt-in; they must not be collected or run by pytest.
- Adapter boundary tests must confirm: no POST/PUT/PATCH/DELETE methods, no credentials, no private-key fields, no disallowed method names (place_order, create_order, post_order, submit_order, cancel_order, sign_order, execute_trade, trade, buy, sell), and no signing imports.
- Approved executable source scope under `src/data_layer/polymarket/` must not weaken tests blocking trading/execution code in other src/ directories.
- All tests must be runnable locally.
- Contract probe tool tests must be offline; no pytest test may require live network. (WP9+)
- Network validation tools must require `--allow-network` before making any network call. (WP9+)
- Response-shape parser changes must include offline fixtures or mocks covering both JSON-encoded string inputs and plain Python list inputs. (WP9+)
- Endpoint verification metadata tests must confirm: only WP9-probed endpoints are marked verified; CLOB /health remains unverified; verified entries carry verified_in_wp and verified_at_utc fields. (WP9+)

