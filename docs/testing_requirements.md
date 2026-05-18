# Testing Requirements

- Governance tests must verify required repo-truth files exist.
- No-live-default tests must verify live trading remains disabled unless explicitly authorized.
- Secret placeholder tests must flag real-looking credentials, private keys, mnemonic labels, and committed `.env` files.
- Future unit tests must cover strategy, risk, data, and utility behavior.
- Future integration tests must cover venue clients only after audit and approval.
- Future paper/live mode tests must prove mode separation.
- Future audit tests must validate source-repo audit artifacts and reuse decisions.
- All tests must be runnable locally.

