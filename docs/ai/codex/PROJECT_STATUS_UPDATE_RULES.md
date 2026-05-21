# Project Status Update Rules

1. Current phase must name the active WP while the branch is open.
2. Repo state must use branch-state phrasing while the PR is open.
3. Merged WPs list must include only already merged WPs, not the current open WP.
4. Architecture and status lines must add current WP changes accurately.
5. Security status must refer to the current WP if checks were run or assessed in the current WP.
6. Do not leave stale phrases such as "scan passed in WP20" when working on WP21, WP22, or later WPs.
7. Semgrep or pip-audit unavailable means unavailable or skipped, not passed.
8. Next intended WP must be conservative and conditional.
9. Deferred items must not be resolved unless their exact resolution condition is satisfied.
10. After merge, the next WP must re-verify `main` and update branch/current-phase wording from merged-state evidence.
