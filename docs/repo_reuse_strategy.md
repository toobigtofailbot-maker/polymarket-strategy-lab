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

No code may be copied without documented license compatibility. No untrusted external repo code may place live orders. Official Polymarket V2 clients are candidate core dependencies, but still need version pinning and security review before use.

External repos are cloned only into audit workspaces during audit WPs, not merged into source by default. Git submodules are not preferred for the early MVP unless explicitly approved.

