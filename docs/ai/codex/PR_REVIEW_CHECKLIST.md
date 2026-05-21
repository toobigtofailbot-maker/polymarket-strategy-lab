# PR Review Checklist

Reviewers and Codex Review Mode must verify:

- PR metadata inspected.
- Base commit equals required previous merge commit when the work package specifies one.
- Changed-file set matches the work package objective.
- Forbidden files and protected paths are untouched.
- Full final report PR comment exists.
- PR body alone is not treated as sufficient.
- `docs/project_status.md` security wording uses the current WP number.
- Unavailable tools are not described as passed.
- Tests were rerun after the final commit.
- Generated-artifact guard was rerun after the final commit.
- No generated artifacts, `local_data/`, local virtual environments, or security outputs are committed.
- No dependency or lock files changed unless explicitly scoped.
- Deferred items were updated accurately.
- Repo-truth docs were updated accurately.
- Safety boundaries remain intact.
- Ready for review: YES/NO is stated.
