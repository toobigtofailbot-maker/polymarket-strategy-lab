# S10-CC-UX-01 Status Entry

## Identity and authority

- WP ID: S10-CC-UX-01
- Title: Premium Control Center — Obsidian Research Interactive Prototype (REV B1)
- Package class: PREMIUM_CONTROL_CENTER_VISUAL_PROTOTYPE
- Size / risk / governance track: M / 2 / FAST
- Branch: claude/s10-cc-ux-01-obsidian-prototype
- Frozen base: 7d77af8b45e5eafec0855fc30e17b167a5178636
- Required predecessor: PR #231, merged at the frozen base; head 113cb1af46ec3a02d857cbe2800cd38d0f4a523b.
- Prompt SHA-256: e41e678534435584758e35d20e088f1f45155c0e293eb6342c1eeaac6dd8fb82
- Spec SHA-256: 489f04e9401091089bf3df269d93791afc53950760f19bfce116cbc1b0118253
- Governed artifacts: materialized byte-identical from the Karl-authorized REV B1 bundle.
- Readiness: IMPLEMENTATION_READY / FAST / DETERMINISTIC; certificate not required.
- Implementation authority: Karl explicitly authorized the exact REV B1 nine-file scope on 2026-10-10.
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable
  and non-self-referential; it does not attempt to encode dynamic PR metadata or the SHA of the commit containing itself.
- Validated implementation commit: see exact-head validation evidence in PR body.
- Evidence mode / Ready for review: see verified current PR body; this committed record does not preclaim posted/hosted evidence.
- Visual approval: AWAITING KARL VISUAL APPROVAL. Merge authorized: NO (Karl only).

## Authority posture

Authority / Non-Authority Posture references the Centralized Boundary Group Reference in
docs/ai/codex/PROTECTED_PATHS.md. Frontend presentation only: the three existing frontend
source files, one numerical Storybook-count literal in the existing stream guard, and the
WP/status/project docs. No backend, API, DTO, route, command, session, SSE, scheduler,
Hermes runtime, strategy, paper, execution, live, credential, dependency, lock, workflow,
Storybook/Vite configuration or deployment change. The four frontend source modules stay
exactly `api.ts`, `app.tsx`, `foundation.stories.tsx` and `main.tsx`. Capital/orders: USD 0 / 0.

## Design decision: Obsidian Research

- One composition pass with the installed Apple Design (HIG layout, sidebar and materials
  guidance) and Awesome Design (Linear and Raycast dark systems as comparison only) skills;
  frontend-design guided implementation. No brand identity was copied.
- Layered near-black navy/graphite surfaces, hairline borders, system font stack
  (SF Pro / Segoe UI Variable), tabular numerals, sentence-case labels and colour reserved
  for meaning: teal = evidence/accepted/core, blue = interactive/exploration, amber =
  gaps/quarantine/caution, neutral = reference and not-selected lanes. No glass in the
  content layer, no glow, no decorative chart.
- Shared shell: Obsidian Research brand mark, the nine existing routes grouped in their
  existing order (Evidence / Research / Operations), group eyebrow and a per-route summary
  line, unchanged Refresh, stream indicator, stream notice and authority posture. Mobile
  uses a horizontally scrollable route strip and a single-line posture strip.
- The seven other pages inherit tokens only (panels, tables, pills, tabs, notices); their
  markup and behaviour are unchanged.

## Charts (inside app.tsx, existing DTOs only)

- Overview `ObservationChart`: `normalized_count` is the reference; `accepted_count` and
  `quarantined_count` are drawn on that same scale as subsets ("2 of 4 normalized"), never
  summed; `open_gap_count` stands apart as a separate event count. `latest_received_at` is
  shown as recorded. Recent-activity counts are labelled capped/windowed, not historical
  totals; experiment, lifecycle and evidence counts stay distinct.
- Alpha `QueueAllocationChart` (Discovery Queue tab): core/exploration/audit lane lengths
  against `queue_capacity` as an allocation limit (open slots drawn dashed); deferred,
  skipped-ineligible and skipped-capacity lanes against the recorded
  `universe.market_count`, never against capacity. Provenance strip shows the read-only
  advisory posture, registry sequence, alpha-memory binding (NOT_BOUND when unbound) and
  historical-replay validity. Existing UNAVAILABLE / HEAD_MISMATCH / empty handling is unchanged.
- Both charts: every series is a keyboard-operable button with aria-pressed, text values
  and relations, a polite live detail region, and a "Show table" plain-table equivalent.
  Selecting a queue lane moves focus to and highlights the matching lane detail without
  changing any recorded state. CSS width transitions are disabled under prefers-reduced-motion.
  No timer, storage, polling, network or new dependency.

## Storybook full demo

`ObsidianResearchFullDemo` (story 36) roots at `/overview` and navigates all nine views
with the existing named GET handlers (overview, market, experiments + detail, strategies +
detail, Hermes + detail, Alpha memory/candidates/episodes/queue/triage, OPS portfolio and
gateway status/audit, paper summary/orders/fills/positions/risk, health, audit). The
protected status read is deliberately unmocked and fails closed through the unchanged
preview catch-all, so the protected surface stays Disabled. The fixture-only notice
`DEMO DATA — NOT LIVE` / `READ-ONLY PROTOTYPE` is rendered by the StoryHost `demo` prop
only; production never renders it.

## Local and browser evidence (external scratch only)

- Readiness (pre-implementation): exit 0, IMPLEMENTATION_READY, 9 paths, 10 evidence items, 10 rules.
- E01 focused set (stream, commands, ops, research): 104 passed during implementation.
- Frontend: `npm ci` from the existing lock (install scripts blocked by npm), typecheck,
  build and build-storybook exit 0; Storybook index lists 36 stories.
- `playwright-cli --version`: 0.1.22, exit 0.
- Real browser (Storybook dev on 127.0.0.1, demo story): all nine routes visited through
  the sidebar with zero unexpected INTERNAL_ERROR / NOT_FOUND / SOURCE_UNAVAILABLE; the only
  non-200 request is the expected `/api/commands/status` 500; commands Disabled on every
  route; experiment, strategy, Hermes and alpha triage drill-downs load. Discovery Queue tab
  activated before the Alpha captures. Desktop 1440x900, laptop 1280x800 and mobile 390x844
  show no horizontal overflow. Keyboard Space/Enter select series, the table toggle shows the
  same four counts, reduced motion yields 0s transitions. Measured WCAG contrast of key text
  pairs: minimum 5.47:1 (12px series relation text).
- Screenshots and Impeccable output live only in the session scratch workspace; nothing was
  written to the repository.
- Final exact-head readiness, security, full-suite and hosted CI evidence: see PR body.

## Impeccable critique and polish (one cycle)

Critique (sequential fallback; sub-agents not used because skill-origin instructions do
not broaden WP scope) scored 30/40 before polish. Detector: Overview 0 findings; Discovery
Queue side-tab (notice side stripe), nested-cards x5 (bordered tables inside lane panels),
line-length (~183 chars). Manual review added the invisible open allocation slot, loose
chart rows, mobile first-screen cost and a plain brand mark. One polish pass: hairline
notice with a 72ch measure, edge-to-edge panel tables, dashed open slots with an explicit
open count, tighter series rows, single-line mobile posture strip, compact demo notice and
a faceted mark. Re-scan: side-tab and nested-cards cleared; remaining cramped-padding on
`.table-wrap` is a confirmed false positive (header and body cells carry 10-12 px padding).

## Limitations

- Only the shell, Overview and Alpha Discovery Queue are redesigned; full rollout to the
  other seven pages is S10-CC-UX-02, separately gated on Karl's visual approval.
- The demo triage fixture resolves only `market:polymarket:alpha`; other triage rows return
  the existing closed NOT_FOUND by design.
- No keyboard shortcuts beyond standard Tab/Enter/Space.
- The repo `npm run storybook` script uses port 6006 with --exact-port; if that port is
  busy, run the same command with another port (see PR body).

## Deferred items

- None added.

## Next WP pointer

- S10-CC-UX-02: Karl-approved Obsidian Research rollout to the remaining seven pages, only after Karl inspects this demo.
