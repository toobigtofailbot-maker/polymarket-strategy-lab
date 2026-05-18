# Git Tools

## Remote Main Sync Gate

`preflight_sync_main.py` proves that local `main` is clean, fast-forwarded to `origin/main`, and contains the required previous work-package evidence before a new WP branch is created.

It runs the generated artifact guard when the guard script is present on the current revision. It never deletes generated artifacts.

Run it before creating or reusing any WP branch:

```powershell
python tools/git/preflight_sync_main.py --required-commit 6992be5b7c3f77ba5b895997c282a5f5a9f1636e --required-file docs/security_tooling_status.md --required-file tools/security/check_security_tools.py
```

The gate verifies:

- `git fetch origin --prune` succeeds.
- `git switch main` succeeds.
- `git pull --ff-only origin main` succeeds.
- The working tree is clean after sync.
- Local `HEAD` equals `origin/main`.
- Required previous WP commits and files are present.

Do not stack a new WP on a prior WP branch. Do not manually merge prior WP branches locally. Do not continue from stale local `main`.

## Generated Artifact Guard

`preflight_generated_artifact_guard.py` fails if any allowlisted generated local artifact path is missing ignore protection, visible in `git status --short`, staged, or tracked.

Run it before creating a WP branch and before final review:

```powershell
python tools/git/preflight_generated_artifact_guard.py
```

The guard checks only these generated paths:

- `.venv-security/`
- `tools/.bin/`
- `tools/security/.cache/`
- `security-scan-output/`

If the guard fails and the files are untracked and unstaged, run the cleanup script:

```powershell
python tools/git/cleanup_generated_artifacts.py --apply
```

## Generated Artifact Cleanup

`cleanup_generated_artifacts.py` is dry-run by default. It requires `--apply` to remove anything.

The cleanup script:

- Deletes only `.venv-security/`, `tools/.bin/`, `tools/security/.cache/`, and `security-scan-output/`.
- Refuses to delete if any file under those paths is tracked.
- Refuses to delete if any file under those paths is staged.
- Prints every path it would remove or removes.
- Does not stage, commit, push, merge, install, or contact APIs.

Generated dependency files, local security-tool environments, portable binaries, local caches, and scan outputs must never be committed.
