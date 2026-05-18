# Git Tools

## Remote Main Sync Gate

`preflight_sync_main.py` proves that local `main` is clean, fast-forwarded to `origin/main`, and contains the required previous work-package evidence before a new WP branch is created.

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
