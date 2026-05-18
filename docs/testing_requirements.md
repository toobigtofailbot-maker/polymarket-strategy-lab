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
- All tests must be runnable locally.

