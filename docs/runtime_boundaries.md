# Runtime Boundaries

## Purpose

Runtime boundaries protect safety-critical execution, risk, credentials, and mode separation. WP3 documents these boundaries only and does not implement runtime behavior.

## Protected Boundaries

- Strategies must not import venue clients directly.
- Strategies cannot place orders directly.
- Strategies must not submit, sign, cancel, reconcile, or route real orders.
- Strategies must not read secrets, private keys, wallet keys, API credentials, passphrases, tokens, or mnemonic material.
- AI, Hermes, and Codex components cannot override risk decisions.
- API clients must sit behind internal adapters in future work packages.
- External repo code cannot become runtime code unless explicitly promoted in a future approved work package after license, security, and compatibility review.
- Live execution requires explicit live authorization, deterministic risk approval, execution gateway controls, and tested safety mechanisms.

## WP3 Boundary State

- No runtime execution exists.
- No order management system exists.
- No reconciliation path exists.
- No risk-cap implementation exists.
- No venue API integration exists.
- No live-trading path exists.
