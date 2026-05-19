# Repo Reuse Strategy

## Reuse Categories

- Core dependency: installed and pinned as a dependency after license, security, and API compatibility review.
- Direct fork: forked for maintained divergence after explicit approval.
- Vendored module: copied into source after documented license compatibility and security review.
- Clean-room adaptation: behavior is studied, then reimplemented without copying code.
- Separate service: run independently with clear boundaries and no implicit execution authority.
- Study only: used for ideas, terminology, and audit notes only.
- Avoid: not used due to license, security, maintenance, API, or safety concerns.

Default decision is study only or clean-room adaptation unless license, security, and API compatibility support stronger reuse.

No code may be copied without documented license compatibility. No untrusted external repo code may place live orders. Official Polymarket V2 clients are candidates only until a later approved dependency work package completes version pinning, security review, and boundary review before use.

## WP14 Official Python Client Decision

- `py-clob-client`: `DO_NOT_USE_ARCHIVED`. The old official Python client is archived, no longer maintained, and no longer functional for new or existing integrations.
- `py-clob-client-v2`: `CANDIDATE_FOR_FUTURE_DEV_ONLY_EVALUATION`. Runtime reuse is `NOT_APPROVED`; copied code is `NOT_ALLOWED`; dependency install is `NOT_APPROVED_IN_WP14`; auth/trading use is `FORBIDDEN_UNTIL_EXPLICIT_WP`; MIT license is verified from the repository page, but dependency security review remains pending before installation.
- The current stdlib public adapter remains the active data path.

External repos are cloned only into audit workspaces during audit WPs, not merged into source by default. Git submodules are not preferred for the early MVP unless explicitly approved.

