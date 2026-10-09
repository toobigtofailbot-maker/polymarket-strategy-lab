# Private Production Control Center — S10-CC-PROD-01

## Authority and compatibility

Karl authorized repository implementation of the corrected readiness-passing package
on 2026-10-09, after certificate-free RUNTIME deterministic readiness. Frozen base:
`10320087b9c16672d42fd0eaa50ded7e349b7a3a`; PR #230 head:
`f004c545e0ddd1d483c16d17045b880926d0c59e`, merged at that base.
Scope is exactly the thirteen paths in `docs/wp_specs/S10-CC-PROD-01/wp_spec.json`.
The protected-boundary source is the Centralized Boundary Group Reference in
`docs/ai/codex/PROTECTED_PATHS.md`. Only opt-in presentation and a dormant nonroot
service template are added. Host installation/start, Tailscale, credentials,
account access, economic commands, risk, execution, orders and live activation
remain separately gated by Karl. Capital/orders: USD 0 / 0. Merge is Karl-only.

`CockpitConfig.frontend_dist` is appended after all existing fields. None preserves
API-only startup. `--frontend-dist` opts in; the existing constructor positions,
CLI flags, loopback host, 31 API paths/methods, JSON errors, domain loaders, CORS,
SSE and TTY-only command bootstrap are unchanged. Commands are default OFF and
are never enabled by the new service. No browser auth/cookie or command class is added.

## Closed static surface

The caller supplies an absolute trusted directory with a regular `index.html` and
`assets/`. Startup rejects missing paths, symlinked root/ancestors/index/assets or
asset descendants, hidden/unsafe names, source-map files and non-build file types.
Only `/`, `/overview`, `/markets`, `/experiments`, `/strategies`, `/hermes`, `/alpha`,
`/ops`, `/paper`, `/audit` and `/assets/<approved-file>` serve GET/HEAD. Index is
HTML; assets use explicit JS/CSS/image/font MIME types. Every served response has
`Cache-Control: no-store`, `X-Content-Type-Options: nosniff` and
`Referrer-Policy: no-referrer`. No directory listing or wildcard HTML fallback.
Unknown API/static paths and missing assets return 404. Source trees, dotfiles,
node_modules, Storybook and MSW workers cannot be served. Build safety is rechecked
on requests; assets are operator-owned and runtime-read-only to prevent replacement
races. No frontend build runs during application startup.

## Exact release and external assets

The existing `tools/deployment/runtime_baseline.py build-release` and `verify-release`
remain the release authority. Build a clean exact implementation SHA release using
those commands. Build the frontend from the SAME exact verified source SHA in a
separate disposable build workspace with Node **24.18.0** and its committed lock:

```sh
npm --prefix src/operator_cockpit_frontend ci
npm --prefix src/operator_cockpit_frontend run typecheck
npm --prefix src/operator_cockpit_frontend audit --audit-level=high
npm --prefix src/operator_cockpit_frontend run build -- --outDir /absolute/external/build-dist
```

The output must be outside the immutable tracked release. Stage it, without adding
or modifying tracked release contents, at
`/var/lib/polymarket/control_center/assets/<exact-sha>/dist`. Record the source SHA,
release manifest digest, locked Node/npm versions, build commands and per-file
SHA-256/size inventory outside the release. Verify staged files against that
inventory, including index/assets and exact SHA association. Wrong SHA, missing
inventory, extra file or digest mismatch stops promotion. Do not serve a dev/preview
server, Storybook, MSW worker or source maps. Re-run original `verify-release` after
staging; it must still succeed without admitting generated assets into its inventory.

The separately authorized host operator may install the already-pinned cockpit
extra (`fastapi==0.141.1`, `uvicorn==0.52.4`) in the release `.venv`, using a disposable
verified source copy as the existing base installer does. Restore root ownership,
read/execute permissions and runtime non-writability afterwards; verify pins,
`pip check`, runtime-user import/execute and `verify-release --allow-activation-artifacts`.
`.venv` is an existing explicitly permitted activation artifact; tracked release
files remain immutable. Base bootstrap stays base-only and is not modified.

## Dormant unit and nonsecret configuration

`tools/deployment/systemd/polymarket-control-center.service` is a committed optional
template, not installed, enabled or started by the existing bootstrap or target.
It uses `polymarket:polymarket`, the existing bounded research slice, current release
Python, loopback port 8000, bounded restart, strict read-only filesystem protection,
no privilege escalation and localhost-only IP access. SSE uses the existing opt-in
streaming flag. It never reads trading credentials or command tokens and never writes domain stores.

Only a separately authorized operator creates root-owned, nonsecret
`/etc/polymarket/deployment/control-center.env` (not a repository file):

```text
PM_CC_MARKET_TRUTH_STORE=/absolute/path/to/existing/market.sqlite3
PM_CC_EXPERIMENT_REGISTRY=/absolute/path/to/existing/experiments.sqlite3
PM_CC_FRONTEND_DIST=/var/lib/polymarket/control_center/assets/<exact-sha>/dist
```

Replace these documentation placeholders with verified absolute paths, never secrets.
All three values are required; optional paper/gateway/lifecycle/Hermes/Alpha stores
are not guessed or wired automatically. Use systemd's `${VAR}` single-argument
substitution, not a shell. Missing config fails startup. A missing/unreadable domain
store retains the existing sanitized unavailable projection; it grants no authority.
Validate the unit with `systemd-analyze verify` on the real Linux operator host before
installation/enablement. Verify cgroup IP filtering is supported and enforced;
unsupported filtering stops activation rather than weakening the unit. The original
research/critical slice limits, critical probe, backups and SSH-only UFW are unchanged.

## Karl-only post-merge private operator gate

These are future operator checks, not authorization from this WP:

1. Obtain Karl's explicit host/private-activation approval after merge. Verify exact
   host/release SHA, release integrity, extras, asset inventory/permissions and config.
2. Preserve SSH-only public inbound UFW: no 8000/443 public listener or new public port.
   Require a narrow tailnet grant/ACL and the actual private HTTPS prerequisites.
3. Install/verify the optional unit without enabling commands. With separate approval,
   enable/start it; verify listening only at `127.0.0.1:8000`, commands disabled,
   known SPA GET/HEAD, all existing APIs and bounded SSE connection/disconnect.
4. Authorized private ingress reference only:
   `tailscale serve --bg --https=443 http://127.0.0.1:8000`, then
   `tailscale serve status`. Never Funnel/public. Prove an authorized tailnet identity
   succeeds and a denied identity cannot access the service. VPN access grants no
   command, account, execution, Gate C or economic authority.
5. Check bounded restart, reboot survival, logs and rollback on the real host.
   For rollback, stop/disable this optional service and remove its private Serve
   mapping using the authorized operator's recorded previous configuration; restore
   the previous verified release/asset association. Leave original host services,
   store data, firewall and backup/recovery contracts intact.

Real-host proof and Tailscale policy remain Karl's operator gate, not a new software
stack or activation WP by default. S10-DEPLOY-EXEC-01 Phase-B and S10-LIVE-CANARY-01
remain independently gated; S10-ALPHA-03 is a separate software successor.

## Evidence and distinct negative failures

Reuse the existing cockpit, command, stream, architecture and deployment suites.
Only the two approved test files are extended. R001–R013 in the frozen spec bind
SPA serving/headers, path/symlink/source rejection, 31-route/default-off compatibility,
dormant unit, unchanged baseline, external build, authority, existing SSE/commands,
exact scope, available security, full local suite, selected exact-head CI and posted
PR evidence. Local checks and actual availability/counts live in the PR body; the
committed status fragment is stable. Side18 independently reviews; Karl alone merges.

| Failure | Required outcome |
|---|---|
| Legacy API or unattended command changes | Reject; retain API/method and default-off regressions |
| Source/hidden/traversal/symlink or HTML API fallback | Reject startup or request with closed diagnostics |
| Missing or wrong-SHA-associated build | Stop host promotion; verify release and asset inventory |
| Public Funnel/port or broad tailnet access | Stop private activation |
| Host, credential or service activation inside repository implementation | Stop; outside authority |
| Main drift, extra path, failed full suite or selected hosted gate | Stop and report; no merge-ready claim |

Scope Amendment 01: Side18 approved exactly two compatibility-only edits in the
existing stream/command test modules: obsolete CockpitConfig field-order assertions
now include the appended frontend_dist. Exact scope is 13; architecture, behavior
and runtime authority remain unchanged.
